# -*- coding: utf-8 -*-
"""2秒轻量查看 1.27 CNetData::EnqueueAction (0x851E10) 确认动作入队结构"""
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

pe = PE32(dll_path_for("1.27.0.52240"))
lns = disasm(pe.path, pe.image_base, 0x851E10, 0x90)
Path(r"D:\Qt\workspace\War3Analysis\artifacts\inplace-turn\enqueue_127.txt").write_text("\n".join(lns), encoding="utf-8")
print(f"Wrote {len(lns)} lines")
