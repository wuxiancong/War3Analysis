# -*- coding: utf-8 -*-
"""
逆向 1.27 Game.dll 的 CAbilityAttack ('Aatk') 全部关键字段：
+0x6C/+0x70 (目标), +0x88..+0xAC (伤害骰子), +0xF4 (攻击类型),
+0x158 (BAT), +0x16C (前摇), +0x1B0 (攻速), +0x1C0 (攻速减速?),
+0x1D8 / +0x1EC / +0x200 (三个 CAgentTimer), +0x2B8 (武器索引)。
策略：
1. 通过 RTTI '.?AVCAbilityAttack@@' 或 FourCC 'Aatk' 定位虚表与构造函数
2. 在 CAbilityAttack 成员函数区域定位对 +0x1D8 / +0x1EC / +0x200 / +0x6C / +0x1B0 / +0x1C0 的所有引用
"""
import sys, struct, re
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\probe_attack_127.txt"


def main():
    dll = dll_path_for("1.27.0.52240")
    pe = PE32(dll)
    base = pe.image_base
    lines = []

    def log(s=""):
        lines.append(s)

    # 1. 查找 CAbilityAttack 虚表
    vts = pe.find_rtti_vtables(".?AVCAbilityAttack@@")
    log(f"=== 1. CAbilityAttack RTTI vtables: {[hex(v) for v in vts]} ===")
    if not vts:
        # 退化用 FourCC 'Aatk' (0x4161746B)
        hits = pe.find_all_bytes(struct.pack("<I", 0x4161746B), ".text")
        log(f"  FourCC 'Aatk' hits: {[hex(h) for h in hits[:6]]}")
        for h in hits[:4]:
            # 找指向该函数头的 .rdata 指针
            for delta in range(0, 8):
                xs = pe.find_all_bytes(struct.pack("<I", base + h - delta), ".rdata")
                if xs:
                    vts.extend([x - 0x1C for x in xs])
                    break
        log(f"  vtable via Aatk: {[hex(v) for v in vts]}")

    # 2. 在 .text 中搜索引用 CAbilityAttack 虚表的构造函数，获取构造函数地址范围（即 CAbilityAttack 代码区！）
    if vts:
        vt = vts[0]
        xrefs = pe.find_xrefs_to_va(base + vt, ".text")
        log(f"  vtable 0x{vt:X} .text xrefs: {[hex(x) for x in xrefs[:10]]}")
        # 找构造函数（通常初始化 +0x1D8, +0x1EC, +0x200 三个 CAgentTimer）
        for x in xrefs[:3]:
            log(f"  --- vtable xref @ 0x{x:X} ---")
            lines.extend("    " + l for l in disasm(dll, base, max(0, x - 0x20), 0xB0))

    # 3. 在 .text 中同时出现 +0x1D8, +0x1EC, +0x200 偏移的函数（CAbilityAttack 核心状态机！）
    text = pe.get_section(".text")
    blob = pe.raw[text.raw_ptr : text.raw_ptr + text.raw_size]
    p_1d8 = struct.pack("<I", 0x1D8)
    p_1ec = struct.pack("<I", 0x1EC)
    p_200 = struct.pack("<I", 0x200)
    p_2b8 = struct.pack("<I", 0x2B8)

    log("\n=== 2. 搜索同时引用 +0x1D8 与 +0x1EC 的 CAbilityAttack 函数 ===")
    pos = 0
    hits_timer = []
    while True:
        i = blob.find(p_1d8, pos)
        if i < 0:
            break
        win = blob[max(0, i - 0x120) : i + 0x120]
        if p_1ec in win:
            rva = text.vaddr + i
            if not hits_timer or rva - hits_timer[-1] > 0x150:
                hits_timer.append(rva)
        pos = i + 1
    log(f"  cluster hits ({len(hits_timer)}): {[hex(h) for h in hits_timer[:15]]}")

    # 4. 搜索 0.5f (0x3F000000) 在 CAbilityAttack 代码区 (hits_timer 所在区域 +/- 0x10000) 附近引用 +0x1D8 的位置！
    if hits_timer:
        lo = min(hits_timer) - 0x8000
        hi = max(hits_timer) + 0x8000
        log(f"\n=== 3. 在 CAbilityAttack 代码区 [0x{lo:X}..0x{hi:X}] 搜 +0x1D8 / +0x1EC / +0x200 / +0x1B0 / +0x1C0 / +0x2B8 ===")
        for label, off in [("timer_1D8", 0x1D8), ("timer_1EC", 0x1EC), ("timer_200", 0x200), ("ias_1B0", 0x1B0), ("slow_1C0", 0x1C0), ("wpnIdx_2B8", 0x2B8), ("bat_158", 0x158), ("dmpt_16C", 0x16C)]:
            pat = struct.pack("<I", off)
            res = []
            s_off = pe.rva_to_off(lo)
            e_off = pe.rva_to_off(hi)
            p = s_off
            while p < e_off:
                j = pe.raw.find(pat, p, e_off)
                if j < 0:
                    break
                res.append(pe.off_to_rva(j))
                p = j + 1
            log(f"  {label:12s} (+0x{off:X}): {len(res)} hits -> {[hex(x) for x in res[:12]]}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[:45]))
    print(f"... total {len(lines)} lines written to {OUT}")


if __name__ == "__main__":
    main()
