# -*- coding: utf-8 -*-
"""
深入反汇编 1.27 CAbilityAttack 代码区 [0x472000..0x483000]：
1. 构造函数 0x474820..0x474B00 (完整字段布局)
2. 定位启动/读写 +0x1D8 / +0x1EC / +0x200 / +0x1B0 / +0x1C0 / +0x6C / +0x158 / +0x16C / +0x2B8 的核心成员函数
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\probe_attack_127_detail.txt"


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def log(s=""):
        lines.append(s)

    # 1. 搜 [0x472000..0x483000] 内所有对 +0x1D8 / +0x1EC / +0x200 / +0x1B0 / +0x1C0 / +0x6C / +0x2B8 的引用
    lo, hi = 0x472000, 0x483000
    s_off, e_off = pe.rva_to_off(lo), pe.rva_to_off(hi)

    log("=== 1. CAbilityAttack 代码区 [0x472000..0x483000] 关键偏移引用统计 ===")
    hits_by = {}
    for name, off in [
        ("timer_1D8", 0x1D8),
        ("timer_1EC", 0x1EC),
        ("timer_200", 0x200),
        ("ias_1B0", 0x1B0),
        ("slow_1C0", 0x1C0),
        ("bat_158", 0x158),
        ("dmpt_16C", 0x16C),
        ("wpnIdx_2B8", 0x2B8),
        ("atkType_F4", 0xF4),
    ]:
        pat = struct.pack("<I", off)
        res = []
        p = s_off
        while p < e_off:
            j = pe.raw.find(pat, p, e_off)
            if j < 0:
                break
            res.append(pe.off_to_rva(j))
            p = j + 1
        hits_by[name] = res
        log(f"  {name:12s} (+0x{off:X}): {len(res)} hits -> {[hex(x) for x in res]}")

    # 2. 反汇编 +0x1D8 和 +0x1EC 的主要使用点（排除构造函数 0x474800..0x474B00）
    log("\n=== 2. +0x1D8 引用处反汇编 ===")
    for h in hits_by["timer_1D8"]:
        if 0x474800 <= h <= 0x474B50:
            continue
        log(f"  --- around 0x{h:X} ---")
        lines.extend("    " + l for l in disasm(dll, base, h - 0x35, 0x75))

    log("\n=== 3. +0x1B0 / +0x1C0 (攻速倍率) 引用处反汇编 ===")
    for h in hits_by["ias_1B0"]:
        if 0x474800 <= h <= 0x474B50:
            continue
        log(f"  --- around 0x{h:X} ---")
        lines.extend("    " + l for l in disasm(dll, base, h - 0x20, 0x65))

    log("\n=== 4. +0x158 (BAT) / +0x16C (前摇) 引用处反汇编 ===")
    for h in hits_by["bat_158"][:4] + hits_by["dmpt_16C"][:4]:
        if 0x474800 <= h <= 0x474B50:
            continue
        log(f"  --- around 0x{h:X} ---")
        lines.extend("    " + l for l in disasm(dll, base, h - 0x20, 0x65))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")
    for l in lines[:15]:
        print(l)


if __name__ == "__main__":
    main()
