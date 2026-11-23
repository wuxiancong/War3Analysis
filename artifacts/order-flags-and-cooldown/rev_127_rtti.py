# -*- coding: utf-8 -*-
"""
纯 Python 扫描 1.27 Game.dll 中 CNetCommand* 虚表，以及查找 dumpbin/objdump 进行反汇编。
"""
import sys, os, subprocess, glob
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown\127_rtti_netcmd.txt"

pe = SimplePE32(DLL_PATH)
out = []
out.append("=== 1. RTTI 查找 CNetCommand* 虚表 ===")
for tname, vts in sorted(pe.find_rtti_vtables("CNetCommand")):
    vt_str = ", ".join(f"(off=0x{o:X}, vt=0x{v:06X})" for o, v in vts)
    out.append(f"  {tname}: {vt_str}")
    for o, vt in vts:
        if o == 0:
            funcs = []
            for i in range(10):
                v = pe.read_u32(vt + i*4)
                funcs.append(f"0x{v - pe.image_base:06X}" if v else "0")
            out.append("    vt[0..9]: " + ", ".join(funcs))

out.append("\n=== 2. RTTI 查找 CAbilityInventory / CAbilitySpell / CCooldown / CItem ===")
for key in ("CAbilityInventory", "CAbilitySpell", "CAgentTimer", "CItem", "CCooldown", "CTargetMode"):
    out.append(f"\n-- key: {key} --")
    for tname, vts in sorted(pe.find_rtti_vtables(key)):
        if len(tname) > 55:
            continue
        vt_str = ", ".join(f"(off=0x{o:X}, vt=0x{v:06X})" for o, v in vts)
        out.append(f"  {tname}: {vt_str}")

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"Wrote {len(out)} lines to {OUT_PATH}")
