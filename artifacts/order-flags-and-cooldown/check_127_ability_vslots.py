# -*- coding: utf-8 -*-
"""
检查 1.27 Game.dll 中各类主动技能/物品母技能的虚槽 +0x2F8 (0x11主) / +0x2FC (0x12主) / +0x300 (0x11/0x12点地回退) / +0x304 (0x10无目标)
"""
import sys
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)

keys = ["CAbilitySpell", "CAbilityChannel", "CAbilityBlink", "CAbilityTeleport", "CAbilityTownPortal", "CAbilityItem", "CAbilityWard", "CAbilityInventory", "CAbilityEatTree", "CAbilityShockwave", "CAbilityCarrionSwarm"]
for key in keys:
    for tname, vts in sorted(pe.find_rtti_vtables(key)):
        if any(x in tname for x in ("Instance", "Allocator", "Ptr", "Book", "Shield", "Steal", "Bonus")):
            continue
        for o, vt in vts:
            if o == 0:
                slots = {}
                for off in (0x2F8, 0x2FC, 0x300, 0x304):
                    v = pe.read_u32(vt + off)
                    slots[off] = f"0x{v - pe.image_base:06X}" if (v and pe.image_base <= v < pe.image_base + 0x950000) else "N/A"
                print(f"  {tname:32s} vt=0x{vt:06X} | +2F8={slots[0x2F8]} +2FC={slots[0x2FC]} +300={slots[0x300]} +304={slots[0x304]}")
