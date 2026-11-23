# -*- coding: utf-8 -*-
"""
定位 1.27 Game.dll 中：
1. 模拟端处理 0x000A0010 / 0x000A0011 / 0x000A0012 事件的 Handler
2. 客户端调用 0x3AE4E0 / 0x3AE540 / 0x3AE5D0 的所有上层函数（了解何时发 0x11 vs 0x12，何时置 0x04 / 0x40）
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)
text_name, text_va, text_vs, text_ro, text_rs = pe.get_section(".text")
text = pe.data[text_ro:text_ro+text_rs]

print("=== 1. 搜索立即数 0x000A0010 / 11 / 12 / 13 ===")
for val in (0x000A0010, 0x000A0011, 0x000A0012, 0x000A0013):
    pat = struct.pack("<I", val)
    pos = 0
    hits = []
    while True:
        idx = text.find(pat, pos)
        if idx == -1:
            break
        pos = idx + 1
        hits.append(f"0x{text_va + idx:06X}")
    print(f"  0x{val:08X}: {hits}")

print("\n=== 2. 搜索 E8 call 到 0x3AE4E0 / 0x3AE540 / 0x3AE5D0 / 0x3AE660 ===")
for target in (0x3AE4E0, 0x3AE540, 0x3AE5D0, 0x3AE660):
    hits = []
    for i in range(len(text) - 5):
        if text[i] == 0xE8:
            rel = struct.unpack_from("<i", text, i + 1)[0]
            dst = text_va + i + 5 + rel
            if dst == target:
                hits.append(f"0x{text_va + i:06X}")
    print(f"  call 0x{target:06X}: {hits}")
