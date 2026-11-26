# -*- coding: utf-8 -*-
"""
单线程轻量探测 1.27.0.52240：
1. 搜索 0x000D0019 (hold) / 0x000D0012 (move) / 0x000D0003 (smart) / 0x000D0016 (patrol) 订单处理函数
   - 验证 hold 带坐标 (0x11/0x12) 是否忽略坐标
   - 验证 move/smart 目标=自己 是否被忽略
2. 搜索 CNetData / 锁步回合间隔 (turn length / latency) 相关函数与全局偏移
3. 检查 1.27 CPoPosCl (0x11CFD0 上游调用者) 里的寻路到达判定距离容差
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

OUT_DIR = Path(r"D:\Qt\workspace\War3Analysis\artifacts\inplace-turn")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def find_e8_callers(pe: PE32, target_rva: int):
    sec = pe.get_section(".text")
    start, end = sec.raw_ptr, sec.raw_ptr + sec.raw_size
    raw = pe.raw
    out = []
    pos = start
    while True:
        idx = raw.find(b"\xE8", pos, end)
        if idx < 0 or idx + 5 > end:
            break
        rel = struct.unpack_from("<i", raw, idx + 1)[0]
        call_rva = pe.off_to_rva(idx)
        if call_rva + 5 + rel == target_rva:
            out.append(call_rva)
        pos = idx + 1
    return out


def main():
    pe = PE32(dll_path_for("1.27.0.52240"))
    out = []

    # 1. 搜索 0x000D0019 (holdposition) 在 .text 中的引用
    for label, oid in [("hold 0xD0019", 0x000D0019), ("patrol 0xD0016", 0x000D0016), ("smart 0xD0003", 0x000D0003)]:
        hits = pe.find_all_bytes(struct.pack("<I", oid), ".text")
        out.append(f"=== {label}: {len(hits)} hits, first 6={[hex(x) for x in hits[:6]]} ===")
        for h in hits[:3]:
            out.append(f"  -- around 0x{h:06X} --")
            out.extend(["    " + l for l in disasm(pe.path, pe.image_base, max(0x1000, h - 0x10), 0x38)])

    # 2. 查 StepTurnAndMove (0x11CFD0) 的调用者（看到达判定与 +0x8C/+0x90 更新）
    callers = find_e8_callers(pe, 0x11CFD0)
    out.append(f"\n=== 1.27 StepTurnAndMove (0x11CFD0) callers: {[hex(x) for x in callers]} ===")
    for c in callers[:2]:
        out.append(f"  -- caller around 0x{c:06X} --")
        out.extend(["    " + l for l in disasm(pe.path, pe.image_base, max(0x1000, c - 0xA0), 0xE0)])

    # 3. 查锁步回合间隔字符串 / 常量（如 "latency" / "TurnLength" / "NetGame" / RTTI CNetGame）
    for pat in ("CNetGame", "CGameWar3", "CNetData", "NetProvider"):
        vts = pe.find_rtti_vtables(pat)
        if vts:
            out.append(f"RTTI {pat}: {[hex(x) for x in vts[:4]]}")

    for s in ("latency", "TurnLength", "m_turn", "W3GS", "GameSpeed"):
        srvas = pe.find_string_rvas(s)
        if srvas:
            out.append(f"String '{s}': {[hex(x) for x in srvas[:4]]}")

    p = OUT_DIR / "probe_lockstep_orders_127.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {p}")


if __name__ == "__main__":
    main()
