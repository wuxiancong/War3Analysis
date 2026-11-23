# -*- coding: utf-8 -*-
"""
1. 搜索 COrder / COrderPoint / COrderTarget 构造调用点（直达模拟端 0x10 / 0x11 / 0x12 执行函数）
2. 打印 CGameWar3EventHandler / CSelectionWar3 / CAbilityInventory / CAbilitySpell 虚表前若干项
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)
tname, tva, tvs, tro, trs = pe.get_section(".text")
text = pe.data[tro:tro+trs]

print("=== 1. 搜索 COrder* 虚表引用（定位构造函数） ===")
for name, vt in [
    ("COrder", 0xA4B030),
    ("COrderPoint", 0xA4B0C0),
    ("COrderTarget", 0xA4B1E8),
    ("COrderTarget2", 0xA4B27C),
]:
    pat = struct.pack("<I", pe.image_base + vt)
    pos = 0
    hits = []
    while True:
        idx = text.find(pat, pos)
        if idx == -1:
            break
        pos = idx + 1
        hits.append(f"0x{tva + idx:06X}")
    print(f"  {name} (vt 0x{vt:06X}): {hits}")

print("\n=== 2. CGameWar3EventHandler (0x965DCC) 虚表 ===")
for i in range(12):
    v = pe.read_u32(0x965DCC + i*4)
    print(f"  vt[{i}] (+0x{i*4:02X}): 0x{v - pe.image_base:06X}")

print("\n=== 3. 搜索 0x000A0010 / 0x000A0011 / 0x000A0012 在 0x3003B6 附近（事件注册） ===")
# 打印 0x24FD06 附近的 0x000A0000 引用
for name, vt in [("CAbilityInventory", 0x9FAB6C), ("CAbilitySpell", 0x997DBC)]:
    print(f"\n=== {name} (vt 0x{vt:06X}) 虚表 [0..35] ===")
    for i in range(36):
        v = pe.read_u32(vt + i*4)
        if v and pe.image_base <= v < pe.image_base + 0x950000:
            if i in (0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,20,24,25,26,27,28,29,30,31,32,33,34,35):
                print(f"  vt[{i:2d}] (+0x{i*4:02X}): 0x{v - pe.image_base:06X}")
