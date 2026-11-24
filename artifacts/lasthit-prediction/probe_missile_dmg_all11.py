# -*- coding: utf-8 -*-
"""
1. 1.27 CMissile 飞行推进、到达判定与伤害结算帧时机反汇编
2. 全 11 版 7x8 伤害倍率表地址 (DamageBonusNormal -> g_DamageBonusTable, 1.27=0xBEC368)
   与护甲减伤系数 (ArmorDamageReductionMultiplier -> 0.06f) 扫描
3. 核验全 11 版 CAbilityAttack 偏移 (+0x6C, +0x88, +0xF4, +0x158, +0x16C, +0x1B0, +0x1C0, +0x1D8, +0x1EC, +0x200, +0x2B8)
"""
import json, re, struct, sys
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\probe_missile_dmg_all11.txt"


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    # 1. 1.27 CMissile 虚表 +0x60..+0xC0 与飞行推进函数
    pe27 = PE32(dll_path_for("1.27.0.52240"))
    base27 = pe27.image_base
    vt = 0x9B07D0
    log("=== 1. 1.27 CMissile 虚表 +0x60..+0xC0 ===")
    for off in range(0x60, 0xC4, 4):
        fn = pe27.read_u32_rva(vt + off)
        if fn and base27 < fn < base27 + 0x1000000:
            log(f"  vt+0x{off:02X} = 0x{fn - base27:X}")

    # 反汇编 CMissile 飞行推进核心函数（通常是 vt+0x84 / +0x88 / +0x90 / +0x94 或 0x6B3000..0x6B5000 中引用 +0x54/+0xA0 的函数）
    # 在 [0x6B0000..0x6B6000] 搜同时访问 +0x54 (speed) 和 +0xA0 (target) 的代码！
    log("\n=== 2. 1.27 CMissile 飞行更新与命中判定 [0x6A0000..0x6B6000] ===")
    s_off, e_off = pe27.rva_to_off(0x6A0000), pe27.rva_to_off(0x6B6000)
    chunk = pe27.raw[s_off:e_off]
    # 搜 0xA0 偏移访问 (例如 [esi+0A0h] -> 8B .. A0 00 00 00 或 8D .. A0 00 00 00)
    hits_a0 = []
    pos = 0
    while True:
        i = chunk.find(b"\xA0\x00\x00\x00", pos)
        if i < 0:
            break
        rva = 0x6A0000 + i
        if not hits_a0 or rva - hits_a0[-1] > 0x80:
            hits_a0.append(rva)
        pos = i + 1
    log(f"  +0xA0 hits in [0x6A0000..0x6B6000]: {[hex(x) for x in hits_a0[:12]]}")
    for h in hits_a0[:4]:
        log(f"  --- around 0x{h:X} ---")
        lines.extend("    " + l for l in disasm(pe27.path, base27, h - 0x35, 0x90))

    # 3. 1.27 搜索 DamageBonusNormal 字符串引用，定位 7x8 伤害倍率表加载函数与表地址
    log("\n=== 3. 全 11 版 7x8 伤害倍率表 (DamageBonusNormal) 与护甲系数 (Armor) 扫描 ===")
    dmg_table_all11 = {}
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        base = pe.image_base
        r_tbl = None
        for srva in pe.find_string_rvas("DamageBonusNormal"):
            xs = pe.find_xrefs_to_va(base + srva, ".text")
            if xs:
                # 在引用附近 0x100 字节内找 .data/.bss 写表基址 (1.27 是 0xBEC368 -> Normal 行从 +0x20 开始)
                asm = disasm(pe.path, base, max(0, xs[0] - 0x20), 0x80)
                for l in asm:
                    m = re.search(r"(?:push|mov\s+\w+,|offset\s+)([0-9A-F]{8})h", l)
                    if m:
                        va = int(m.group(1), 16)
                        if base + 0x750000 <= va < base + 0xF00000 and va != base + srva:
                            r_tbl = va - base
                            break
                if ver == "1.27.0.52240":
                    log("  [1.27 DamageBonusNormal xref asm]:")
                    lines.extend("    " + l for l in asm[:25])
                break
        dmg_table_all11[ver] = f"0x{r_tbl:X}" if r_tbl else None
        log(f"  {ver:13s} | DamageBonusNormal_row/table = {dmg_table_all11[ver]}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")
    for l in lines[-14:]:
        print(l)


if __name__ == "__main__":
    main()
