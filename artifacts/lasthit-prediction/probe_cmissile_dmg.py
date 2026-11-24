# -*- coding: utf-8 -*-
"""
1. 反汇编 1.27 CMissile 核心物理推进与命中结算 (vt+0xA8=0x6B35B0, vt+0xAC=0x6B0000, vt+0xB4=0x6AFB60, vt+0xBC=0x6B2450)
   确认：到达当帧扣血 vs 下一帧、2D 水平匀速 vs 弧度影响、发射点 launchX/Y 与命中判定距离
2. 扫描全 11 版 7x8 伤害倍率表基址 (Row 0 Spells) 与 DefenseArmor (0.06f) 全局地址
"""
import json, re, struct, sys
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\cmissile_and_dmg_all11.txt"


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    pe27 = PE32(dll_path_for("1.27.0.52240"))
    base27 = pe27.image_base

    log("=== 1. 1.27 CMissile 关键虚函数 (0x6AFB60 / 0x6B0000 / 0x6B2450 / 0x6B35B0) ===")
    for name, rva, sz in [
        ("vt+0xB4 (0x6AFB60)", 0x6AFB60, 0x160),
        ("vt+0xAC (0x6B0000)", 0x6B0000, 0x180),
        ("vt+0xBC (0x6B2450)", 0x6B2450, 0xD0),
        ("vt+0xA8 (0x6B35B0)", 0x6B35B0, 0xC0),
    ]:
        log(f"\n--- {name} ---")
        lines.extend("  " + l for l in disasm(pe27.path, base27, rva, sz))

    log("\n=== 2. 全 11 版 7x8 伤害倍率表基址 (Row0 Spells = NormalRow - 0x20) 与 DefenseArmor (0.06f) ===")
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        base = pe.image_base
        row1_rva = None
        for srva in pe.find_string_rvas("DamageBonusNormal"):
            xs = pe.find_xrefs_to_va(base + srva, ".text")
            if xs:
                asm = disasm(pe.path, base, xs[0], 0x50)
                for l in asm:
                    # 匹配 mov dword ptr [esi+6FBEC368h], eax 或 mov dword ptr [reg+6Fxxxxxxh], reg
                    m = re.search(r"dword ptr \[[^\]]*\+([0-9A-F]{8})h\]", l)
                    if m:
                        va = int(m.group(1), 16)
                        if base + 0x700000 <= va < base + 0x1000000:
                            row1_rva = va - base
                            break
                break
        tbl_rva = (row1_rva - 0x20) if row1_rva else None

        armor_rva = None
        for srva in pe.find_string_rvas("DefenseArmor"):
            xs = pe.find_xrefs_to_va(base + srva, ".text")
            if xs:
                asm = disasm(pe.path, base, xs[0], 0x55)
                for l in asm:
                    m = re.search(r"dword ptr ds:\[([0-9A-F]{8})h\]", l)
                    if m:
                        va = int(m.group(1), 16)
                        if base + 0x700000 <= va < base + 0x1000000:
                            armor_rva = va - base
                            break
                break
        s_tbl = hex(tbl_rva) if tbl_rva else "None"
        s_row = hex(row1_rva) if row1_rva else "None"
        s_arm = hex(armor_rva) if armor_rva else "None"
        log(f"  {ver:13s} | DmgBonusTbl(Row0)={s_tbl:10s} | NormalRow(Row1)={s_row:10s} | DefenseArmor={s_arm}")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT}")
    for l in lines[-14:]:
        print(l)


if __name__ == "__main__":
    main()
