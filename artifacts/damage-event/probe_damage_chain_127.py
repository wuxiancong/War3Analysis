# -*- coding: utf-8 -*-
"""
1.27 精确追踪：
1. GetEventDamage / GetEventDamageSource / UnitDamageTarget 原生注册与实现
2. CMissile::ApplyDamage (0x6B1624) 调用的 CUnit 虚函数槽位及实现
3. 核查 6.83d Scripts_war3map.j 中的 1865429044 (o004) / 1868921189 (oeye) / Multiboard 与防御塔真视技能
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\damage-event\probe_damage_chain_127.txt")


def main():
    pe = PE32(dll_path_for("1.27.0.52240"))
    out = []

    # 1. CMissile::ApplyDamage 尾部（确认 call [edx + offset]）
    out.append("=== 1.27 CMissile::ApplyDamage tail @ 0x6B1624 ===")
    out.extend(disasm(pe.path, pe.image_base, 0x6B1624, 0x40))

    # 2. 直接打印 GetEventDamage / GetEventDamageSource / UnitDamageTarget 字符串的所有 .text 引用上下文
    for name in ("GetEventDamage", "GetEventDamageSource", "UnitDamageTarget"):
        srvas = pe.find_string_rvas(name)
        out.append(f"\n=== Native {name} str_rvas={[hex(x) for x in srvas]} ===")
        for srva in srvas:
            sva = pe.image_base + srva
            refs = pe.find_xrefs_to_va(sva, ".text")
            for ref in refs[:3]:
                out.append(f"  xref @ 0x{ref:06X}:")
                lns = disasm(pe.path, pe.image_base, max(0x1000, ref - 0x18), 0x38)
                out.extend(["    " + l for l in lns])

    # 3. 查 CUnit 虚表（RTTI .?AVCUnit@@）
    cunit_vts = pe.find_rtti_vtables(".?AVCUnit@@")
    out.append(f"\n=== 1.27 CUnit vtables: {[hex(x) for x in cunit_vts]} ===")
    if cunit_vts:
        vt = cunit_vts[0]
        # 检查从 0x6B163E 看到的槽位（先读取 0x120 等常见槽位）
        for off in (0x11C, 0x120, 0x124, 0x128):
            va = pe.read_u32_rva(vt + off)
            rva = va - pe.image_base if va and va > pe.image_base else 0
            out.append(f"  CUnit vt+0x{off:03X} = 0x{rva:06X}")

    # 4. 快速查 Scripts_war3map.j 中的 o004(1865429044) / oeye(1868921189) 与 Units_UnitAbilities.slk 塔真视
    j_lines = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Scripts_war3map.j").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    for label, num in [("o004", "1865429044"), ("oeye", "1868921189")]:
        hits = [i + 1 for i, l in enumerate(j_lines) if num in l]
        out.append(f"\n=== war3map.j {label} ({num}): {len(hits)} hits, lines={hits[:15]} ===")
        for ln_no in hits[:5]:
            for k in range(max(0, ln_no - 3), min(len(j_lines), ln_no + 5)):
                out.append(f"  {k+1:6d}: {j_lines[k]}")

    # 查 Units_UnitAbilities.slk 中防御塔技能（e00R, u00M, e011, u00D, e00S, u00N, e019）
    slk = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Units_UnitAbilities.slk").read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    out.append("\n=== Units_UnitAbilities.slk Towers & Wards ===")
    cur_id = ""
    for ln in slk:
        if 'K"e00R"' in ln or 'K"u00M"' in ln or 'K"e011"' in ln or 'K"u00D"' in ln or 'K"e00S"' in ln or 'K"u00N"' in ln or 'K"e019"' in ln or 'K"o004"' in ln or 'K"oeye"' in ln:
            cur_id = ln
            out.append("  " + ln)
        elif cur_id and ln.startswith("C;X2;"):
            out.append("    abilList: " + ln)
            cur_id = ""

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {OUT}")


if __name__ == "__main__":
    main()
