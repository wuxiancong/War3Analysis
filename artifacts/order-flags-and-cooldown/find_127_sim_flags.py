# -*- coding: utf-8 -*-
"""
定位 1.27 Game.dll 中模拟端消费 CNetCommandUnitOrderBasic/Point/TargetImage 的函数：
方法：搜索对 0x6F2760D0 / 0x6F276530 同类 CSelectionWar3 函数（0x270000..0x27A000）的调用，
以及搜索读取 [reg+18h] 并将 bit 2 (0x04) / bit 6 (0x40) 解包传给 CSelectionWar3 / CUnit 的指令。
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)
tname, tva, tvs, tro, trs = pe.get_section(".text")
text = pe.data[tro:tro+trs]

# 在 0x146000..0x350000 中搜索 "cmp byte ptr [reg+14h], 10h" 或 "movzx reg, word ptr [reg+18h]" 紧跟 test 40h / 4h
# 更直接：搜索 0x6F24FD06 附近的事件分发，以及搜索 "test byte ptr [reg+18h], 40h" (F6 4? 18 40)
print("=== 搜索 F6 4? 18 40 (test byte ptr [reg+18h], 40h) ===")
hits = []
for i in range(len(text) - 4):
    if text[i] == 0xF6 and (text[i+1] & 0xF8) == 0x40 and text[i+2] == 0x18 and text[i+3] == 0x40:
        hits.append(f"0x{tva + i:06X}")
print(f"  hits ({len(hits)}): {hits}")

print("\n=== 搜索 F6 4? 18 04 (test byte ptr [reg+18h], 04h) ===")
hits2 = []
for i in range(len(text) - 4):
    if text[i] == 0xF6 and (text[i+1] & 0xF8) == 0x40 and text[i+2] == 0x18 and text[i+3] == 0x04:
        hits2.append(f"0x{tva + i:06X}")
print(f"  hits ({len(hits2)}): {hits2}")

print("\n=== 搜索 0F B7 ?? 18 (movzx reg, word ptr [reg+18h]) 在 0x180000..0x350000 ===")
hits3 = []
start = 0x180000 - tva
end = 0x350000 - tva
for i in range(max(0, start), min(len(text) - 4, end)):
    if text[i] == 0x0F and text[i+1] == 0xB7 and (text[i+2] & 0xC0) == 0x40 and text[i+3] == 0x18:
        # 看看后面 40 字节内有没有 0x40 或 0x04 或 0x100
        win = text[i:i+48]
        if b"\x40" in win and (b"\x04" in win or b"\x01\x00" in win):
            hits3.append(f"0x{tva + i:06X}")
print(f"  hits ({len(hits3)}): {hits3[:30]}")
