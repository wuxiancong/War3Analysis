# -*- coding: utf-8 -*-
"""3秒轻量补完：1.27 0x03A970(GetFacingRad)、1.27 0x47BE00(攻击前转身检查)、1.0.17-1.21 GetUnitFacing 尾部乘数 RVA"""
import re
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-facing\final_micro_check.txt")
out = []

pe127 = PE32(dll_path_for("1.27.0.52240"))
out.append("=== 1. 1.27 NIpse::CPoPos::GetFacingRad @ 0x03A970 ===")
out.extend(disasm(pe127.path, pe127.image_base, 0x03A970, 0x50))

out.append("\n=== 2. 1.27 CAbilityAttack::CanStartWindup / CheckFacing @ 0x47BE00 ===")
out.extend(disasm(pe127.path, pe127.image_base, 0x47BE00, 0x90))

out.append("\n=== 3. 1.0.17~1.21.0 GetUnitFacing 尾部 (含 180/pi 乘数全局 RVA) ===")
for ver, rva in [
    ("1.0.17.5988", 0x2BFCA0),
    ("1.0.20.6048", 0x2BFCA0),
    ("1.20.4.6074", 0x2BFDC0),
    ("1.21.0.6263", 0x2C3390),
]:
    pe = PE32(dll_path_for(ver))
    lns = disasm(pe.path, pe.image_base, rva + 0x70, 0x60)
    mult = None
    for ln in lns:
        m = re.search(r"push\s+([0-9A-F]{8})h", ln)
        if m:
            r = int(m.group(1), 16) - pe.image_base
            if 0x700000 < r < pe.image_size:
                mult = r
    out.append(f"  {ver}: Rad2Deg Global = {hex(mult) if mult else '—'}")
    if ver == "1.0.17.5988":
        out.extend(["    " + l for l in lns[:25]])

OUT.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {len(out)} lines to {OUT}")
