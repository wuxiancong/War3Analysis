# -*- coding: utf-8 -*-
"""
War3Launcher RemoteControl (127.0.0.1:6120) 客户端、日志增量读取器与状态解析器。
严格遵守：不修改 War3Launcher / hooker 任何源码，仅复用现有 RemoteControl 命令与日志格式。
"""
import json
import os
import re
import socket
import subprocess
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


# 默认日志目录（可通过环境变量 WAR3_LOG_DIR 覆盖）
DEFAULT_LOG_DIR = os.environ.get("WAR3_LOG_DIR", r"C:\War3Run\War3Launcher\logs")
DEFAULT_RC_HOST = "127.0.0.1"
DEFAULT_RC_PORT = int(os.environ.get("WAR3_RC_PORT", "6120"))

# 允许通过 say 工具发送的白名单命令前缀（防误触发危险或未审计的地图/调试命令）
SAY_WHITELIST_PREFIXES = (
    "-score start laning",
    "-score end",
    "-score status",
    "-items",
    "-buy ",
    "-use ",
    "-skills",
    "-learn ",
    "-autolearn ",
    "-lasthit",
    "-deny",
    "-safe",
    "-unsafe",
    "-push",
    "-back",
    "-stop",
    "-hold",
)

# 普通聊天文本禁止以 '-' 开头（除非匹配上述白名单）
OK_CONFIRM_NOTE = "注意：RemoteControl 返回 OK 仅表示命令已发出，是否真正生效必须调用 get_state 核对游戏状态。"


class LogTail:
    """增量日志读取器（参考 War3Launcher/scripts/ai_lane_test.py 的 Tail）。
    AiUnit.log / game_stats.log 通常达数 MB，每次只读取新增的完整行，支持文件截断/轮转复位。
    """

    def __init__(self, path: str, start_at_end: bool = True):
        self.path = path
        if start_at_end and os.path.exists(path):
            self.pos = os.path.getsize(path)
        else:
            self.pos = 0

    def reset_to_end(self) -> None:
        self.pos = os.path.getsize(self.path) if os.path.exists(self.path) else 0

    def read_new_lines(self) -> List[str]:
        if not os.path.exists(self.path):
            return []
        size = os.path.getsize(self.path)
        if size < self.pos:
            # 日志文件被截断或轮转
            self.pos = 0
        with open(self.path, "rb") as f:
            f.seek(self.pos)
            data = f.read()
        cut = data.rfind(b"\n") + 1
        if cut <= 0:
            return []
        self.pos += cut
        return data[:cut].decode("utf-8", "replace").splitlines()


def check_war3_running() -> bool:
    """检测本机 war3.exe 是否运行中（超时保守返回 True，避免卡顿误判退出）。"""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq war3.exe"],
            capture_output=True,
            text=True,
            errors="replace",
            timeout=15,
        ).stdout
        return "war3.exe" in out.lower()
    except Exception:
        return False


class RemoteControlClient:
    """同步行协议客户端，仅允许连接本机回环地址。"""

    def __init__(self, host: str = DEFAULT_RC_HOST, port: int = DEFAULT_RC_PORT, timeout: float = 5.0):
        if host not in ("127.0.0.1", "localhost"):
            raise ValueError(f"安全红线：仅允许连接本机回环地址，拒绝 {host}")
        self.host = host
        self.port = port
        self.timeout = timeout

    def send(self, command: str) -> Tuple[bool, str]:
        """发送单行命令并返回 (ok, raw_reply)。"""
        line = command.replace("\r", " ").replace("\n", " ").strip()
        if not line:
            return False, "ERR empty command"
        try:
            with socket.create_connection((self.host, self.port), timeout=self.timeout) as sock:
                sock.settimeout(self.timeout)
                sock.sendall((line + "\n").encode("utf-8"))
                reply = sock.makefile(encoding="utf-8", errors="replace").readline().strip()
            return reply.startswith("OK"), reply
        except OSError as exc:
            return False, f"ERR connection failed: {exc}"


class LandmarkResolver:
    """地标名（英文 key / 中文名 / 别名）到 (x, y) 的解析器。"""

    def __init__(self, json_path: Optional[str] = None):
        if json_path is None:
            json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "landmarks.json")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.landmarks: Dict[str, Dict[str, Any]] = data.get("landmarks", {})
        self._index: Dict[str, str] = {}
        for key, info in self.landmarks.items():
            self._index[key.lower()] = key
            zh = info.get("zh", "")
            if zh:
                self._index[zh.lower()] = key
            for alias in info.get("aliases", []):
                self._index[alias.lower()] = key

    def resolve(self, name: str) -> Optional[Tuple[str, float, float, str]]:
        key = self._index.get(name.strip().lower())
        if not key:
            return None
        info = self.landmarks[key]
        return key, float(info["x"]), float(info["y"]), info.get("zh", key)

    def list_keys(self) -> List[str]:
        return sorted(self.landmarks.keys())


def parse_status_reply(reply: str) -> Dict[str, Any]:
    """解析 RemoteControl `status` 返回行，如 `OK enabled=1 running=1 state=Completed ...`。"""
    ok = reply.startswith("OK")
    fields: Dict[str, str] = {}
    for m in re.finditer(r"(\w+)=([^\s]+)", reply):
        fields[m.group(1)] = m.group(2)
    return {"ok": ok, "raw": reply, "fields": fields}


def parse_ai_unit_lines(lines: List[str]) -> Dict[str, Any]:
    """解析 AiUnit.log 新增片段，提取英雄、视野内单位、背包物品与对线游戏钟。"""
    hero: Dict[str, Any] = {}
    units: List[Dict[str, Any]] = []
    items: List[Dict[str, Any]] = []
    clock_sec: Optional[int] = None
    in_units_block = False
    in_items_block = False

    # 正则严格对应 war3hook_ai.cpp:L2428-2437 与 war3hook_ai_tactics.inl:L1654-1671
    re_units_hdr = re.compile(
        r"\[Units\]\s*英雄\s+(0x[0-9A-Fa-f]+)\s+位置\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)\s+血:(\d+(?:\.\d+)?)\s+阵营:(\d+)"
    )
    re_unit_row = re.compile(
        r"│\s*(\S+)\s+(0x[0-9A-Fa-f]+)\s+玩家:(-?\d+)\s+(建筑|单位)\s+血:(\d+(?:\.\d+)?)/(\d+(?:\.\d+)?)\s+掉血:(-?\d+(?:\.\d+)?)/s\s+位置\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)\s+距离:(\d+(?:\.\d+)?)"
    )
    re_items_hdr = re.compile(
        r"\[Items\]\s*英雄\s+(0x[0-9A-Fa-f]+)\s+位置\((-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)\)"
    )
    re_item_row = re.compile(
        r"│\s*栏位\s*(\d+)\s*\|\s*([A-Za-z0-9_]{4})\s*\|\s*([^|]+?)\s*\|\s*充能:([^|]+?)\s*\|\s*h=(0x[0-9A-Fa-f]+)\s*\|\s*(.+)$"
    )
    re_clock = re.compile(r"游戏钟\s*(-?\d+)s")
    re_gold = re.compile(r"(?:金钱|现金|金币)[:：\s]*(\d+)")
    re_mana = re.compile(r"(?:蓝|MP)[:：\s]*(\d+(?:\.\d+)?)(?:/(\d+(?:\.\d+)?))?")
    re_lvl = re.compile(r"(?:等级|Lv\.?)[:：\s]*(\d+)")

    for line in lines:
        mc = re_clock.search(line)
        if mc:
            clock_sec = int(mc.group(1))

        # 顺带从对线/状态日志里抓取可选的蓝/等级/金钱补充信息
        if "[对线]" in line or "[Tactic]" in line or "[Status]" in line:
            mg = re_gold.search(line)
            if mg:
                hero["gold"] = int(mg.group(1))
            mm = re_mana.search(line)
            if mm:
                hero["mp"] = float(mm.group(1))
                if mm.group(2):
                    hero["max_mp"] = float(mm.group(2))
            ml = re_lvl.search(line)
            if ml:
                hero["level"] = int(ml.group(1))

        m_uh = re_units_hdr.search(line)
        if m_uh:
            in_units_block = True
            units = []  # 以最新一块 [Units] 为准
            team_id = int(m_uh.group(5))
            hero.update(
                {
                    "handle": m_uh.group(1),
                    "x": float(m_uh.group(2)),
                    "y": float(m_uh.group(3)),
                    "hp": float(m_uh.group(4)),
                    "team": "dire" if team_id == 2 else "radiant",
                    "team_id": team_id,
                }
            )
            continue
        if "[Units] 结束" in line:
            in_units_block = False
            continue
        if in_units_block:
            m_ur = re_unit_row.search(line)
            if m_ur:
                units.append(
                    {
                        "type_id": m_ur.group(1),
                        "handle": m_ur.group(2),
                        "owner_id": int(m_ur.group(3)),
                        "is_structure": m_ur.group(4) == "建筑",
                        "hp": float(m_ur.group(5)),
                        "max_hp": float(m_ur.group(6)),
                        "loss_rate": float(m_ur.group(7)),
                        "x": float(m_ur.group(8)),
                        "y": float(m_ur.group(9)),
                        "dist": float(m_ur.group(10)),
                    }
                )
            continue

        m_ih = re_items_hdr.search(line)
        if m_ih:
            in_items_block = True
            items = []  # 以最新一块 [Items] 为准
            hero.setdefault("handle", m_ih.group(1))
            hero["x"] = float(m_ih.group(2))
            hero["y"] = float(m_ih.group(3))
            continue
        if "[Items] 结束" in line:
            in_items_block = False
            continue
        if in_items_block:
            m_ir = re_item_row.search(line)
            if m_ir:
                chg_raw = m_ir.group(4).strip()
                charges = int(chg_raw[1:]) if chg_raw.startswith("x") and chg_raw[1:].isdigit() else None
                items.append(
                    {
                        "slot": int(m_ir.group(1)),
                        "type_id": m_ir.group(2),
                        "name": m_ir.group(3).strip(),
                        "charges": charges,
                        "handle": m_ir.group(5),
                        "cooldown_text": m_ir.group(6).strip(),
                    }
                )

    return {
        "hero": hero,
        "units": units,
        "items": items,
        "ai_clock_sec": clock_sec,
    }


def parse_game_stats_lines(lines: List[str]) -> Dict[str, Any]:
    """解析 game_stats.log 新增片段，提取地图当前游戏时间与 KDA 更新。"""
    map_clock_sec: Optional[int] = None
    map_clock_str: Optional[str] = None
    kda_updates: List[Dict[str, Any]] = []

    re_time = re.compile(r"当前游戏时间:\s*(\d+):(\d+)")
    re_kda = re.compile(r"玩家\s*(\d+)\s*\|\s*(击杀数\(Kills\)|死亡数\(Deaths\)|助攻数\(Assists\))更新:\s*(\d+)")

    for line in lines:
        mt = re_time.search(line)
        if mt:
            mm, ss = int(mt.group(1)), int(mt.group(2))
            map_clock_sec = mm * 60 + ss
            map_clock_str = f"{mm:02d}:{ss:02d}"
        mk = re_kda.search(line)
        if mk:
            kda_updates.append({"player_id": int(mk.group(1)), "metric": mk.group(2), "value": int(mk.group(3))})

    return {
        "map_clock_sec": map_clock_sec,
        "map_clock_str": map_clock_str,
        "kda_updates": kda_updates,
    }


def is_say_allowed(text: str) -> Tuple[bool, str]:
    """白名单校验：仅允许白名单命令前缀，或不含 '-' 前缀的普通队内沟通文本。"""
    s = text.strip()
    if not s:
        return False, "消息不能为空"
    if len(s) > 120:
        return False, "消息过长（上限 120 字符）"
    if "\n" in s or "\r" in s:
        return False, "禁止包含换行符"
    if s.startswith("-"):
        low = s.lower()
        for prefix in SAY_WHITELIST_PREFIXES:
            if low == prefix.strip() or low.startswith(prefix):
                return True, "匹配白名单命令前缀"
        return False, f"命令前缀不在白名单内：{s.split()[0]}"
    return True, "普通聊天文本"


class DotaController:
    """封装全部指挥层操作，便于 MCP Server 与离线单元测试复用。"""

    def __init__(
        self,
        rc_client: Optional[RemoteControlClient] = None,
        log_dir: str = DEFAULT_LOG_DIR,
        landmarks: Optional[LandmarkResolver] = None,
        war3_checker: Callable[[], bool] = check_war3_running,
        poll_wait_sec: float = 0.25,
    ):
        self.rc = rc_client or RemoteControlClient()
        self.log_dir = log_dir
        self.landmarks = landmarks or LandmarkResolver()
        self.war3_checker = war3_checker
        self.poll_wait_sec = poll_wait_sec
        self.ai_tail = LogTail(os.path.join(log_dir, "AiUnit.log"), start_at_end=True)
        self.stats_tail = LogTail(os.path.join(log_dir, "game_stats.log"), start_at_end=True)
        self._last_state: Dict[str, Any] = {"hero": {}, "units": [], "items": [], "clock_sec": None}

    def game_status(self) -> Dict[str, Any]:
        ok, reply = self.rc.send("status")
        parsed = parse_status_reply(reply)
        return {
            "rc_ok": ok,
            "war3_running": self.war3_checker(),
            "launcher_status": parsed,
            "log_dir": self.log_dir,
        }

    def get_state(self, include_items: bool = True, max_visible_dist: float = 1800.0) -> Dict[str, Any]:
        """发送 units（可选 say -items），等待日志落盘，只读新增部分并合并为结构化 JSON。
        视野安全红线：在 G5 hook 侧 state 命令落地前，仅保留英雄本地合理视野距离内单位，并标注待 hook 侧 IsUnitVisible 强过滤。
        """
        ok_u, rep_u = self.rc.send("units")
        ok_i, rep_i = (True, "SKIPPED")
        if include_items:
            ok_i, rep_i = self.rc.send("say -items")

        if self.poll_wait_sec > 0:
            time.sleep(self.poll_wait_sec)

        ai_lines = self.ai_tail.read_new_lines()
        stats_lines = self.stats_tail.read_new_lines()

        ai_parsed = parse_ai_unit_lines(ai_lines)
        stats_parsed = parse_game_stats_lines(stats_lines)

        # 合并增量缓存
        if ai_parsed["hero"]:
            self._last_state["hero"].update(ai_parsed["hero"])
        if ai_parsed["items"]:
            self._last_state["items"] = ai_parsed["items"]

        # 视野保守过滤：敌方单位仅保留 <= max_visible_dist（防止原型阶段旧 units 输出泄露远端迷雾单位）
        hero_team_id = self._last_state["hero"].get("team_id")
        filtered_units = []
        for u in ai_parsed["units"]:
            owner = u["owner_id"]
            is_ally = (
                (hero_team_id == 1 and 0 <= owner <= 5)
                or (hero_team_id == 2 and 6 <= owner <= 11)
            )
            if is_ally or u["dist"] <= max_visible_dist:
                filtered_units.append(u)
        if ai_parsed["units"] or ok_u:
            self._last_state["units"] = filtered_units

        clock_sec = stats_parsed["map_clock_sec"]
        if clock_sec is None:
            clock_sec = ai_parsed["ai_clock_sec"]
        if clock_sec is not None:
            self._last_state["clock_sec"] = clock_sec

        return {
            "ok": ok_u,
            "rc_replies": {"units": rep_u, "items": rep_i},
            "clock_sec": self._last_state["clock_sec"],
            "map_clock_str": stats_parsed["map_clock_str"],
            "hero": dict(self._last_state["hero"]),
            "items": list(self._last_state["items"]),
            "visible_units": list(self._last_state["units"]),
            "kda_updates": stats_parsed["kda_updates"],
            "new_lines_read": {"ai_unit": len(ai_lines), "game_stats": len(stats_lines)},
            "vision_note": "原型阶段基于现有 units 日志按本地视野半径保守过滤；正式严格迷雾过滤需由 G5 state 命令在 hook 侧调用 IsUnitVisible + IsUnitDetected。",
        }

    def move_to(self, landmark: Optional[str] = None, x: Optional[float] = None, y: Optional[float] = None) -> Dict[str, Any]:
        resolved_name = None
        if landmark:
            found = self.landmarks.resolve(landmark)
            if not found:
                return {
                    "ok": False,
                    "error": f"未知地标：{landmark}",
                    "available_landmarks": self.landmarks.list_keys(),
                }
            resolved_name, x, y, zh = found
        if x is None or y is None:
            return {"ok": False, "error": "必须提供 landmark 或 (x, y) 坐标"}
        cmd = f"move {int(round(x))} {int(round(y))}"
        ok, reply = self.rc.send(cmd)
        return {
            "ok": ok,
            "command": cmd,
            "reply": reply,
            "target": {"landmark": resolved_name, "x": x, "y": y},
            "note": OK_CONFIRM_NOTE,
        }

    def start_laning(self) -> Dict[str, Any]:
        cmd = "say -score start laning"
        ok, reply = self.rc.send(cmd)
        return {"ok": ok, "command": cmd, "reply": reply, "note": OK_CONFIRM_NOTE}

    def stop(self) -> Dict[str, Any]:
        cmd = "say -score end"
        ok, reply = self.rc.send(cmd)
        return {"ok": ok, "command": cmd, "reply": reply, "note": OK_CONFIRM_NOTE}

    def buy(self, item_name: str) -> Dict[str, Any]:
        item = item_name.strip()
        if not item or not re.match(r"^[A-Za-z0-9_\-\u4e00-\u9fff ]{1,32}$", item):
            return {"ok": False, "error": f"非法物品名：{item_name}"}
        cmd = f"say -buy {item}"
        ok, reply = self.rc.send(cmd)
        return {"ok": ok, "command": cmd, "reply": reply, "item": item, "note": OK_CONFIRM_NOTE}

    def say(self, text: str) -> Dict[str, Any]:
        allowed, reason = is_say_allowed(text)
        if not allowed:
            return {"ok": False, "error": f"白名单拦截：{reason}", "whitelist": list(SAY_WHITELIST_PREFIXES)}
        cmd = f"say {text.strip()}"
        ok, reply = self.rc.send(cmd)
        return {"ok": ok, "command": cmd, "reply": reply, "reason": reason, "note": OK_CONFIRM_NOTE}
