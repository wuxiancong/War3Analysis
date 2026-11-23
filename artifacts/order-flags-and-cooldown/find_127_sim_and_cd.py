# -*- coding: utf-8 -*-
"""
定位 1.27 Game.dll 中：
1. 模拟端真正执行 0x10/0x11/0x12 的函数（搜索 0xA0010 在事件表/代码中的注册，或 CPlayerWar3/CSelectionWar3 RTTI）
2. 追踪 0x63AC50 之后（CItem 冷却/共享冷却）以及 CAbilitySpell 冷却启动函数
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)

print("=== 1. RTTI: CSelectionWar3 / CPlayerWar3 / CAbilityInventory / CUnit ===")
for key in ("CSelectionWar3", "CPlayerWar3", "COrder", "CGameWar3"):
    for tname, vts in sorted(pe.find_rtti_vtables(key)):
        if len(tname) > 45:
            continue
        vt_str = ", ".join(f"(off=0x{o:X}, vt=0x{v:06X})" for o, v in vts)
        print(f"  {tname}: {vt_str}")

# 2. 在 .text 中搜索 0x000A0010..0x000A0015 附近：其实 CGameWar3 用 CNetCommand 的 actionId (0x10..0x15) 或者在 CPlayerWar3 里有 0x000A0000 基准！
tname, tva, tvs, tro, trs = pe.get_section(".text")
text = pe.data[tro:tro+trs]
print("\n=== 2. 搜索 0x000A0000 / 0x000A000E / 0x000A000F / 0xFFF5FFF0 (-0xA0010) ===")
for val in (0x000A0000, 0x000A000F, 0xFFF5FFF0, 0xFFF5FFEF, 0xFFF5FFEE):
    pat = struct.pack("<I", val)
    pos = 0
    hits = []
    while True:
        idx = text.find(pat, pos)
        if idx == -1:
            break
        pos = idx + 1
        hits.append(f"0x{tva + idx:06X}")
    print(f"  0x{val:08X}: {hits[:20]}")

# 3. 搜索 CItem cooldownID / CAbilitySpell +0x20 置 0x200 的地方（冷却开始！）
print("\n=== 3. 搜索 or dword ptr [reg+20h], 200h (81 4? 20 00 02 00 00) ===")
hits = []
for i in range(len(text) - 7):
    if text[i] == 0x81 and (text[i+1] & 0xF8) == 0x48 and text[i+2] == 0x20 and text[i+3:i+7] == b"\x00\x02\x00\x00":
        hits.append(f"0x{tva + i:06X}")
print(f"  or [reg+20h], 200h ({len(hits)}): {hits[:25]}")
