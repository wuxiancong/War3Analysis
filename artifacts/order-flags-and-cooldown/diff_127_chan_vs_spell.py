# -*- coding: utf-8 -*-
"""
检查 CAbilityChannel (vt 0x9B7744) 与 CAbilitySpell (vt 0x997DBC) 差异的虚函数槽，
特别是 +0x30C (GetTargetType), +0x308 (GetOrderId), 以及 OnPointOrder / OnTargetOrder 的差异！
"""
import sys
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)

vt_spell = 0x997DBC
vt_chan  = 0x9B7744
vt_blink = 0x9C38D0
vt_tp    = 0x9A4068

print("=== CAbilityChannel vs CAbilitySpell 差异虚槽 ===")
for off in range(0, 0x450, 4):
    vs = pe.read_u32(vt_spell + off)
    vc = pe.read_u32(vt_chan + off)
    vb = pe.read_u32(vt_blink + off)
    vt = pe.read_u32(vt_tp + off)
    if vc != vs or off in (0x308, 0x30C, 0x314, 0x348, 0x34C, 0x3DC, 0x3E4, 0x3E8, 0x3EC):
        def fmt(x): return f"0x{x - pe.image_base:06X}" if (x and pe.image_base <= x < pe.image_base + 0x950000) else f"0x{x:08X}"
        if off >= 0x200:
            print(f"  +0x{off:03X}: Spell={fmt(vs)} Chan={fmt(vc)} Blink={fmt(vb)} TP={fmt(vt)}")
