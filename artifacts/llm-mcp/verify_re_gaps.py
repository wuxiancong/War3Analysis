# -*- coding: utf-8 -*-
"""
逆向补齐脚本：验证冷却偏移、Buff 枚举、Shift 队列标志、信使/防御塔强化/肉山坐标以及现有 RemoteControl / Hooker 事件源。
只读分析，不修改任何游戏或 Launcher 源码。
"""
import os
import re
import struct
import subprocess

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"
LAUNCHER_DIR = r"D:\Qt\workspace\War3Launcher"
WAR3MAP_J = r"D:\Qt\workspace\War3Analysis\artifacts\dota683d\war3map.j"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp\re_gaps_report.txt"


def fourcc_from_int(val: int) -> str:
    """将 32 位整数转换为 FourCC 字符串。"""
    return struct.pack(">I", val).decode("latin1", errors="replace")


def disasm_range(dll_path: str, image_base: int, rva_start: int, size: int) -> str:
    """调用 dumpbin 反汇编指定 RVA 范围。"""
    va1 = image_base + rva_start
    va2 = va1 + size
    cmd = [DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll_path]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.stdout


def get_image_base(dll_path: str) -> int:
    """通过 PE 头读取 ImageBase。"""
    import pefile
    pe = pefile.PE(dll_path, fast_load=True)
    return pe.OPTIONAL_HEADER.ImageBase


def find_game_dll(ver_prefix: str) -> str:
    """在 versions 目录下查找对应版本的 Game.dll。"""
    for name in os.listdir(VERSIONS_DIR):
        if name.startswith(ver_prefix):
            p = os.path.join(VERSIONS_DIR, name, "Game.dll")
            if os.path.exists(p):
                return p
    return ""


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    # 1. 解码已知的 FourCC
    log("=== 1. FourCC 解码 ===")
    for v, desc in [
        (1093743665, "Glyph Ability 1 (JQO)"),
        (1093752649, "Glyph Ability 2 (JQO)"),
        (1747993652, "Buyback Cooldown Dummy Stock (GN1)"),
    ]:
        log(f"  {desc}: {v} = 0x{v:08X} = '{fourcc_from_int(v)}'")

    # 2. 反汇编 UnitResetCooldown & UnitCountBuffsEx (1.27 & 1.26)
    log("\n=== 2. 反汇编 UnitResetCooldown / UnitCountBuffsEx ===")
    targets = [
        ("1.27", [
            ("UnitResetCooldown", 0x1FB270, 0x160),
            ("UnitCountBuffsEx", 0x1FAA40, 0x200),
        ]),
        ("1.26", [
            ("UnitResetCooldown", 0x3C86D0, 0x160),
            ("UnitCountBuffsEx", 0x3C83A0, 0x200),
        ]),
    ]
    for ver, funcs in targets:
        dll = find_game_dll(ver)
        if not dll:
            log(f"  [WARN] 未找到 {ver} Game.dll")
            continue
        base = get_image_base(dll)
        log(f"\n--- {ver} ({dll}, ImageBase=0x{base:X}) ---")
        for fname, rva, sz in funcs:
            log(f"\n[{fname} @ RVA 0x{rva:X}]")
            out = disasm_range(dll, base, rva, sz)
            # 过滤空行和文件头
            for ln in out.splitlines():
                if re.match(r"^\s+[0-9A-F]{8}:", ln):
                    log(ln)

    # 3. 扫描 AiControlManager.cpp 中的所有 RemoteControl 命令
    log("\n=== 3. AiControlManager.cpp RemoteControl 全量命令 ===")
    acm_path = os.path.join(LAUNCHER_DIR, "managers", "AiControlManager.cpp")
    if os.path.exists(acm_path):
        txt = open(acm_path, "r", encoding="utf-8", errors="replace").read()
        # 查找所有 cmd == "xxx" 或 cmd.startsWith("xxx") 或 QStringLiteral("xxx")
        cmds = sorted(set(re.findall(r'cmd\s*==\s*(?:QStringLiteral\()?"([a-zA-Z0-9_\-]+)"', txt)))
        starts = sorted(set(re.findall(r'cmd\.startsWith\((?:QStringLiteral\()?"([a-zA-Z0-9_\- ]+)"', txt)))
        log(f"  cmd == (...) ({len(cmds)}): {', '.join(cmds)}")
        log(f"  cmd.startsWith (...) ({len(starts)}): {', '.join(starts)}")
        # 查找 remoteCommand / onRemoteCommand 附近的行号
        for idx, ln in enumerate(txt.splitlines(), 1):
            if "handleRemote" in ln or "processRemote" in ln or "onRemote" in ln or "6120" in ln or "sendAiUnit" in ln:
                log(f"  L{idx}: {ln.strip()[:120]}")

    # 4. 扫描 war3hook_ai.cpp 中 0x10/0x11/0x12/0x13 及 Shift 队列标志
    log("\n=== 4. war3hook_ai.cpp 动作包与 Shift 标志 ===")
    ai_cpp = os.path.join(LAUNCHER_DIR, "hooker", "war3hook_ai.cpp")
    if os.path.exists(ai_cpp):
        for idx, ln in enumerate(open(ai_cpp, "r", encoding="utf-8", errors="replace"), 1):
            if any(k in ln for k in ["aiEnqueue", "0x10", "0x11", "0x12", "0x13", "0x16", "0x19", "shift", "Shift", "queue", "Queue", "0x01"]):
                if "Enqueue" in ln or "flags" in ln or "Shift" in ln or "shift" in ln or "queue" in ln or "0x10" in ln or "0x11" in ln or "0x12" in ln or "0x13" in ln or "0x16" in ln or "0x19" in ln:
                    log(f"  L{idx}: {ln.strip()[:130]}")

    # 5. 扫描 hooker 目录下现有事件钩子 (0x60 聊天, 0x68 Ping, SyncStoredInteger, gameStats)
    log("\n=== 5. hooker 现有事件来源 ===")
    hooker_dir = os.path.join(LAUNCHER_DIR, "hooker")
    if os.path.isdir(hooker_dir):
        for fn in sorted(os.listdir(hooker_dir)):
            if not fn.endswith((".cpp", ".h", ".inl")):
                continue
            fp = os.path.join(hooker_dir, fn)
            content = open(fp, "r", encoding="utf-8", errors="replace").read()
            hits = []
            for kw in ["0x60", "0x68", "SyncStoredInteger", "gameStats", "OnChat", "ChatHook", "Ping", "minimap"]:
                c = content.count(kw)
                if c > 0:
                    hits.append(f"{kw}({c})")
            if hits:
                log(f"  {fn}: {', '.join(hits)}")

    # 6. 扫描 war3map.j 中肉山坐标 & 信使技能
    log("\n=== 6. war3map.j 肉山坐标 & 信使/Glyph 技能 ===")
    j_path = WAR3MAP_J
    if not os.path.exists(j_path):
        # 在 War3Analysis 目录下查找 war3map.j
        for root, _, files in os.walk(r"D:\Qt\workspace\War3Analysis"):
            if "war3map.j" in files:
                j_path = os.path.join(root, "war3map.j")
                break
    log(f"  war3map.j 路径: {j_path}")
    if os.path.exists(j_path):
        jtxt = open(j_path, "r", encoding="utf-8", errors="replace").read()
        # 查找 Roshan (n00L = 1848651852) 创建与坐标
        for idx, ln in enumerate(jtxt.splitlines(), 1):
            if "1848651852" in ln or "n00L" in ln or 'FL1("Roshan"' in ln or "Aegis" in ln:
                log(f"  [Roshan] L{idx}: {ln.strip()[:140]}")
        # 查找信使相关常量/技能
        for idx, ln in enumerate(jtxt.splitlines(), 1):
            if any(k in ln for k in ["n00I", "n022", "n021", "1848651849", "1848652338", "1848652337", "JQO", "JSO", "JTO", "coldarrows"]):
                if len(lines) < 500:
                    log(f"  [Courier/Glyph] L{idx}: {ln.strip()[:140]}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
