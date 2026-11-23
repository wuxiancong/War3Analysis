# -*- coding: utf-8 -*-
"""
列出 1.27 Game.dll 中 0x69B000..0x69F500 区间内所有模拟端命令执行器（0x10/0x11/0x12/0x13/0x14/0x15）
及其调用的 CUnit::CanOrder* / CUnit::CreateOrder*。
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)
tname, tva, tvs, tro, trs = pe.get_section(".text")
text = pe.data[tro:tro+trs]

targets = {
    0x680540: "CanOrderImmediate(vt+264)",
    0x680620: "CanOrderPoint(vt+25C)",
    0x6806D0: "CanOrderTarget2(vt+254)",
    0x680780: "CanOrderPoint2(vt+258)",
    0x680830: "CanOrderTargetImage(vt+260)",
    0x680900: "CanOrderFogged(vt+250)",
    0x673200: "CreateOrderBasic",
    0x67E3A0: "CreateOrderFogged",
    0x67E640: "CreateOrderTarget",
    0x69BC60: "CUnit::EnqueueOrder",
}

s_off = 0x69B800 - tva
e_off = 0x69F500 - tva
for i in range(s_off, e_off):
    if text[i] == 0xE8:
        rel = struct.unpack_from("<i", text, i + 1)[0]
        dst = tva + i + 5 + rel
        if dst in targets:
            print(f"  0x{tva+i:06X}: call 0x{dst:06X} ({targets[dst]})")
        elif 0x673000 <= dst <= 0x681000:
            # 可能是 CreateOrderPoint / CreateOrderTarget2 等
            print(f"  0x{tva+i:06X}: call 0x{dst:06X} (CUnit_order_other)")
