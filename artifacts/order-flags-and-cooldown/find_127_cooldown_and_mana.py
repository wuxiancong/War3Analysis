# -*- coding: utf-8 -*-
"""
逆向 1.27 Game.dll 中：
1. CAbilitySpell 冷却启动函数（设置 +0x20 |= 0x200、启动 +0xD0 CAgentTimer，并遍历共享 cooldownID）
2. CItem / CAbilityInventory 的冷却读取与共享冷却（如魔瓶 cooldownID='A0FO'）
3. CAbilitySpell 的蓝耗读取（GetManaCost 虚槽与内存偏移）
方法：搜索对 CAbilitySpell+0xD0 (CAgentTimer) 和 +0x20 & 0x200 的访问，以及 SLK 字段 'Cool' / 'Cost' / 'cooldownID'。
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)
tname, tva, tvs, tro, trs = pe.get_section(".text")
text = pe.data[tro:tro+trs]

# 1. 搜索字符串 "cooldownID" / "Cool" / "Cost" 在 .rdata 中的地址，再找 .text 对它们的引用
print("=== 1. 搜索 cooldownID / Cool 字符串引用 ===")
for s in (b"cooldownID\x00", b"Cost\x00", b"Cool\x00"):
    pos = 0
    while True:
        idx = pe.data.find(s, pos)
        if idx == -1:
            break
        pos = idx + 1
        rva = pe.off_to_rva(idx)
        if rva is None:
            continue
        va = pe.image_base + rva
        pat = struct.pack("<I", va)
        tpos = 0
        refs = []
        while True:
            tidx = text.find(pat, tpos)
            if tidx == -1:
                break
            tpos = tidx + 1
            refs.append(f"0x{tva + tidx:06X}")
        if refs:
            print(f"  {s[:-1].decode()} @ 0x{rva:06X}: refs={refs}")

# 2. 搜索 lea ecx, [reg+0D0h] (8D 8? D0 00 00 00) 在 0x3D0000..0x420000 (CAbilitySpell 模块)
print("\n=== 2. 在 CAbilitySpell 模块 (0x3D0000..0x420000) 搜索 +0xD0 (CAgentTimer) ===")
s_off = 0x3D0000 - tva
e_off = 0x420000 - tva
hits = []
for i in range(s_off, e_off):
    if text[i] == 0x8D and (text[i+1] & 0xC0) == 0x80 and text[i+2:i+6] == b"\xD0\x00\x00\x00":
        hits.append(f"0x{tva+i:06X}")
print(f"  lea reg, [reg+0D0h] ({len(hits)}): {hits[:30]}")

# 3. 搜索 CItem 模块 (0x635000..0x642000) 中对 +0x98 / +0x9C (item abilities) 的引用
print("\n=== 3. 在 CItem 模块 (0x635000..0x642000) 搜索 cooldown 相关（0x200 / +0x98 / +0xD0） ===")
s_off2 = 0x635000 - tva
e_off2 = 0x642000 - tva
hits2 = []
for i in range(s_off2, e_off2):
    if text[i:i+4] == b"\x98\x00\x00\x00" and i >= 2 and text[i-2] in (0x39, 0x3B, 0x8B, 0x83):
        hits2.append(f"0x{tva+i-2:06X}")
print(f"  CItem +0x98 refs ({len(hits2)}): {hits2[:20]}")
