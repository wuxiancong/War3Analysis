# -*- coding: utf-8 -*-
"""
追踪 1.27 Game.dll 中 0x30ADA0 以及模拟端执行 0x10/0x11/0x12/0x13 动作包的函数。
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)

# 1. 在所有节中搜索 0x000A0010 / 0x000A0011 / 0x000A0012 / 0x000A0013（包括表或事件注册）
for sec_name, va, vs, ro, rs in pe.sections:
    buf = pe.data[ro:ro+rs]
    for val in (0x000A0010, 0x000A0011, 0x000A0012):
        pat = struct.pack("<I", val)
        pos = 0
        hits = []
        while True:
            idx = buf.find(pat, pos)
            if idx == -1:
                break
            pos = idx + 1
            hits.append(f"0x{va + idx:06X}")
        if hits:
            print(f"  [{sec_name}] 0x{val:08X}: {hits}")

# 2. 也搜索 0x000D0028 (useslot1) 在 .text 中的引用，直达模拟端物品栏执行逻辑！
tname, tva, tvs, tro, trs = pe.get_section(".text")
text = pe.data[tro:tro+trs]
print("\n=== 搜索 useslot1 (0x000D0028) / useslot6 (0x000D002D) 在 .text 中的引用 ===")
for val in (0x000D0028, 0x000D002D, 0x000D0022):
    pat = struct.pack("<I", val)
    pos = 0
    hits = []
    while True:
        idx = text.find(pat, pos)
        if idx == -1:
            break
        pos = idx + 1
        hits.append(f"0x{tva + idx:06X}")
    print(f"  0x{val:08X}: {hits}")
