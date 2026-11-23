# -*- coding: utf-8 -*-
"""
1. 查找 CAbilityInventory / CAbilitySpell 的 vt+0x250..0x270（CanOrder / IssueOrder 虚槽）
2. 查找 CAbilityChannel (ANcl, 假眼/真眼母技能!) 的 RTTI 与虚表
3. 搜索调用 0x663000 / 0x663070 / 0x6631A0 的模拟端发单函数
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)

print("=== 1. 查找 CAbilityChannel / CAbilityBlink / CAbilityTeleport / CAbilityInventory RTTI ===")
for key in ("CAbilityChannel", "CAbilityBlink", "CAbilityTownPortal", "CAbilityInventory", "CAbilitySpell"):
    for tname, vts in sorted(pe.find_rtti_vtables(key)):
        if "Instance" in tname or "Allocator" in tname or "Ptr" in tname:
            continue
        for o, vt in vts:
            if o == 0:
                print(f"  {tname}: vt=0x{vt:06X}")
                for slot_off in (0x24C, 0x250, 0x254, 0x258, 0x25C, 0x260, 0x264, 0x268, 0x26C, 0x270):
                    v = pe.read_u32(vt + slot_off)
                    if v and pe.image_base <= v < pe.image_base + 0x950000:
                        print(f"    +0x{slot_off:03X}: 0x{v - pe.image_base:06X}")

tname, tva, tvs, tro, trs = pe.get_section(".text")
text = pe.data[tro:tro+trs]
print("\n=== 2. 搜索调用 0x663070 (COrderPoint) / 0x6631A0 (COrderTarget2) ===")
for target in (0x663000, 0x663070, 0x6631A0):
    hits = []
    for i in range(len(text) - 5):
        if text[i] == 0xE8:
            rel = struct.unpack_from("<i", text, i + 1)[0]
            if tva + i + 5 + rel == target:
                hits.append(f"0x{tva + i:06X}")
    print(f"  call 0x{target:06X}: {hits}")
