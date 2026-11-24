# -*- coding: utf-8 -*-
"""反汇编 1.27 的 CUnit::ApplyDamage (0x67DC40)、GetEventDamage (0x1E21D0)、GetEventDamageSource (0x1E21F0)、UnitDamageTarget (0x1FAB70)"""
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

pe = PE32(dll_path_for("1.27.0.52240"))
out = []
for name, rva, sz in [
    ("GetEventDamage", 0x1E21D0, 0x20),
    ("GetEventDamageSource", 0x1E21F0, 0x70),
    ("UnitDamageTarget", 0x1FAB70, 0x120),
    ("CUnit::ApplyDamage (vt+0x120)", 0x67DC40, 0x280),
]:
    out.append(f"=== 1.27 {name} @ 0x{rva:06X} ===")
    out.extend(disasm(pe.path, pe.image_base, rva, sz))
    out.append("")

p = Path(r"D:\Qt\workspace\War3Analysis\artifacts\damage-event\disasm_damage_127.txt")
p.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {len(out)} lines to {p}")
