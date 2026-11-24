# -*- coding: utf-8 -*-
"""
MCP Server 离线单元测试：
使用本地临时随机端口的假 RemoteControl TCP 服务器与模拟日志片段，
完全不连接真实 6120 端口，不启动或干扰 war3.exe / War3Launcher。
"""
import os
import socket
import tempfile
import threading
import unittest

from rc_client import (
    DotaController,
    LandmarkResolver,
    LogTail,
    RemoteControlClient,
    is_say_allowed,
    parse_ai_unit_lines,
    parse_game_stats_lines,
)


class FakeRemoteControlServer:
    """模拟 127.0.0.1:<随机空闲端口> 的行协议 RemoteControl 服务器。"""

    def __init__(self, ai_log_path: str, stats_log_path: str):
        self.ai_log_path = ai_log_path
        self.stats_log_path = stats_log_path
        self.received: list[str] = []
        self._stop = threading.Event()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.bind(("127.0.0.1", 0))
        self.port = self._sock.getsockname()[1]
        self._sock.listen(8)
        self._sock.settimeout(0.2)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                data = conn.makefile("r", encoding="utf-8", errors="replace").readline().strip()
                self.received.append(data)
                reply = self._handle(data)
                conn.sendall((reply + "\n").encode("utf-8"))

    def _handle(self, cmd: str) -> str:
        if cmd == "status":
            return "OK enabled=1 running=1 state=Completed lastError=none remote=127.0.0.1:6120 testMode=1"
        if cmd == "units":
            with open(self.ai_log_path, "a", encoding="utf-8") as f:
                f.write(
                    "[01:35:10.100] ┌── [Units] 英雄 0x00100123 位置(-512, -390) 血:680 阵营:1 | 半径 1200 内 3 个（跟踪总数 55）\n"
                    "[01:35:10.101] │ esen 0x00100201 玩家:1 单位 血:550/550 掉血:0/s 位置(-450, -350) 距离:74\n"
                    "[01:35:10.102] │ H00H 0x00100301 玩家:7 单位 血:420/700 掉血:35/s 位置(-180, -110) 距离:435\n"
                    "[01:35:10.103] │ H00Q 0x00100302 玩家:8 单位 血:800/800 掉血:0/s 位置(3000, 3000) 距离:4850\n"
                    "[01:35:10.104] └── [Units] 结束\n"
                    "[01:35:10.105] [对线] 视野：中路 游戏钟 185s 金钱:745 蓝:240/390 等级:4\n"
                )
            with open(self.stats_log_path, "a", encoding="utf-8") as f:
                f.write("[2026-11-23 01:35:10.050] ⏱️ 当前游戏时间: 03:05\n")
            return "OK units queued"
        if cmd == "say -items":
            with open(self.ai_log_path, "a", encoding="utf-8") as f:
                f.write(
                    "[01:35:10.110] ┌── [Items] 英雄 0x00100123 位置(-512, -390) 当前 6 格背包\n"
                    "[01:35:10.111] │ 栏位 1 | I0AN | 魔瓶(有水) | 充能:x3 | h=0x00100501 | 就绪\n"
                    "[01:35:10.112] │ 栏位 2 | I05G | 假眼 | 充能:x2 | h=0x00100502 | 就绪\n"
                    "[01:35:10.113] │ 栏位 3 | <空>\n"
                    "[01:35:10.114] └── [Items] 结束\n"
                )
            return "OK say queued"
        if cmd.startswith(("move ", "say ")):
            return f"OK dispatched: {cmd}"
        return f"ERR unknown: {cmd}"

    def close(self) -> None:
        self._stop.set()
        self._sock.close()
        self._thread.join(timeout=1.0)


class TestDotaMcpServerOffline(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.ai_log = os.path.join(self.tmp.name, "AiUnit.log")
        self.stats_log = os.path.join(self.tmp.name, "game_stats.log")
        # 预写旧日志内容，验证 LogTail 只读新增部分
        with open(self.ai_log, "w", encoding="utf-8") as f:
            f.write("[00:00:01.000] 旧日志行，不应被重复解析\n")
        with open(self.stats_log, "w", encoding="utf-8") as f:
            f.write("[2026-11-23 00:00:01.000] ⏱️ 当前游戏时间: 00:01\n")

        self.fake = FakeRemoteControlServer(self.ai_log, self.stats_log)
        self.ctrl = DotaController(
            rc_client=RemoteControlClient(host="127.0.0.1", port=self.fake.port),
            log_dir=self.tmp.name,
            war3_checker=lambda: True,
            poll_wait_sec=0.02,
        )

    def tearDown(self) -> None:
        self.fake.close()
        self.tmp.cleanup()

    def test_game_status(self) -> None:
        res = self.ctrl.game_status()
        self.assertTrue(res["rc_ok"])
        self.assertTrue(res["war3_running"])
        self.assertEqual(res["launcher_status"]["fields"]["state"], "Completed")

    def test_get_state_incremental_and_vision_filter(self) -> None:
        st = self.ctrl.get_state(include_items=True, max_visible_dist=1800.0)
        self.assertTrue(st["ok"])
        self.assertEqual(st["clock_sec"], 185)
        self.assertEqual(st["map_clock_str"], "03:05")
        self.assertEqual(st["hero"]["handle"], "0x00100123")
        self.assertEqual(st["hero"]["hp"], 680.0)
        self.assertEqual(st["hero"]["gold"], 745)
        self.assertEqual(st["hero"]["mp"], 240.0)
        self.assertEqual(st["hero"]["level"], 4)
        self.assertEqual(len(st["items"]), 2)
        self.assertEqual(st["items"][1]["type_id"], "I05G")
        self.assertEqual(st["items"][1]["charges"], 2)
        # 距离 4850 的敌方英雄 H00Q 必须被过滤掉，仅剩友兵 esen 和视野内敌方 H00H
        handles = [u["handle"] for u in st["visible_units"]]
        self.assertIn("0x00100201", handles)
        self.assertIn("0x00100301", handles)
        self.assertNotIn("0x00100302", handles)

    def test_move_to_landmark_and_coords(self) -> None:
        r1 = self.ctrl.move_to(landmark="中路一塔")
        self.assertTrue(r1["ok"])
        self.assertEqual(r1["command"], "move -1664 -1472")
        self.assertIn("get_state", r1["note"])

        r2 = self.ctrl.move_to(landmark="top_rune")
        self.assertTrue(r2["ok"])
        self.assertEqual(r2["command"], "move -2352 1648")

        r3 = self.ctrl.move_to(x=100, y=-200)
        self.assertTrue(r3["ok"])
        self.assertEqual(r3["command"], "move 100 -200")

        r_bad = self.ctrl.move_to(landmark="不存在的地方")
        self.assertFalse(r_bad["ok"])

    def test_laning_stop_buy_and_say_whitelist(self) -> None:
        self.assertEqual(self.ctrl.start_laning()["command"], "say -score start laning")
        self.assertEqual(self.ctrl.stop()["command"], "say -score end")
        self.assertEqual(self.ctrl.buy("obs")["command"], "say -buy obs")

        # 白名单命令允许
        self.assertTrue(self.ctrl.say("-items")["ok"])
        self.assertTrue(self.ctrl.say("miss mid")["ok"])
        # 非白名单 - 命令拦截
        blocked = self.ctrl.say("-gold 99999")
        self.assertFalse(blocked["ok"])
        self.assertIn("白名单拦截", blocked["error"])

    def test_tail_truncation_recovery(self) -> None:
        tail = LogTail(self.ai_log, start_at_end=True)
        self.assertEqual(tail.read_new_lines(), [])
        # 模拟日志轮转截断
        with open(self.ai_log, "w", encoding="utf-8") as f:
            f.write("[00:00:02.000] 轮转后第一行\n")
        lines = tail.read_new_lines()
        self.assertEqual(len(lines), 1)
        self.assertIn("轮转后第一行", lines[0])

    def test_non_loopback_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RemoteControlClient(host="192.168.1.10", port=6120)


if __name__ == "__main__":
    unittest.main(verbosity=2)
