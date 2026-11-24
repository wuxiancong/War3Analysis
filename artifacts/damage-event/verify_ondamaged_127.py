# -*- coding: utf-8 -*-
"""
1. 反汇编 1.27 CUnit::ApplyDamage 尾部 (0x67DF60..0x67E220) 与 CUnit::OnDamaged (0x67F340)
2. 核实 6.83d 小兵 level（Units_UnitBalance.slk）、塔真视范围（Units_AbilityData.slk）、神符提示 FMO（Scripts_war3map.j）
"""
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

pe = PE32(dll_path_for("1.27.0.52240"))
out = []

out.append("=== 1.27 CUnit::ApplyDamage tail @ 0x67DF60 ===")
out.extend(disasm(pe.path, pe.image_base, 0x67DF60, 0x260))

out.append("\n=== 1.27 CUnit::OnDamaged / EVENT_UNIT_DAMAGED dispatcher @ 0x67F340 ===")
out.extend(disasm(pe.path, pe.image_base, 0x67F340, 0x160))

# 2. 解析 Units_UnitBalance.slk 小兵 level 与 Units_UnitAbilities.slk 塔技能
MAP = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\stealth-rune-route")
from parse_sight_and_doodads import parse_slk_clean

cols, rows = parse_slk_clean(MAP / "Units_UnitBalance.slk")
c2i = {v: k for k, v in cols.items()}
out.append(f"\n=== 6.83d 小兵/塔 level (UnitBalance.slk) ===")
out.append(f"level col={c2i.get('level')}, points col={c2i.get('points')}, bounty col={c2i.get('bountydice')}")
targets = ["eaom", "efon", "edry", "ugho", "unec", "ebal", "umtw", "e00R", "u00M", "e011", "u00D", "e00S", "u00N", "e019", "o004", "oeye"]
for y, r in sorted(rows.items()):
    uid = r.get(1, "")
    if uid in targets:
        out.append(f"  {uid:6s} (Y={y:4d}): level={r.get(c2i.get('level', 0), '?')}, sight={r.get(c2i.get('sight', 0), '?')}, nsight={r.get(c2i.get('nsight', 0), '?')}")

# 塔技能列表（Units_UnitAbilities.slk）
acols, arows = parse_slk_clean(MAP / "Units_UnitAbilities.slk")
out.append(f"\n=== 6.83d 塔/眼技能 (Units_UnitAbilities.slk, cols={acols}) ===")
for y, r in sorted(arows.items()):
    uid = r.get(1, "")
    if uid in ("e00R", "u00M", "e011", "u00D", "e00S", "u00N", "e019", "o004", "oeye"):
        out.append(f"  {uid:6s} (Y={y:4d}): abilList={r.get(2, '?')}, auto={r.get(3, '?')}")

# 查 Scripts_war3map.j 中的 function FMO（神符通知是否只发队友）和 GUO（插眼跟踪）
j_lines = (MAP / "Scripts_war3map.j").read_text(encoding="utf-8", errors="replace").splitlines()
for fname in ("function FMO ", "function GUO "):
    for i, l in enumerate(j_lines):
        if l.startswith(fname):
            out.append(f"\n=== war3map.j {fname} @ L{i+1} ===")
            for k in range(i, min(len(j_lines), i + 30)):
                out.append(f"{k+1:6d}: {j_lines[k]}")
                if j_lines[k].strip() == "endfunction":
                    break

p = Path(r"D:\Qt\workspace\War3Analysis\artifacts\damage-event\verify_ondamaged_127.txt")
p.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {len(out)} lines to {p}")
