# -*- coding: utf-8 -*-
"""
查找 1.27 Game.dll 中：
1. 0x639E60 (CItem::StartCooldown) / 0x639E80 (CItem::GetRemainingCooldown) 的所有调用者
2. CAbilitySpell 的 GetManaCost 虚槽（定位 CAbilitySpell+0x50 level 和查表函数）
3. CUnit 上是否有共享 cooldownID 表（搜 0x639ED0 调用者）
"""
import sys, struct
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\order-flags-and-cooldown")
from pe_helper import SimplePE32

DLL_PATH = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
pe = SimplePE32(DLL_PATH)
tname, tva, tvs, tro, trs = pe.get_section(".text")
text = pe.data[tro:tro+trs]

def find_calls(target_rva):
    hits = []
    for i in range(len(text) - 5):
        if text[i] == 0xE8:
            rel = struct.unpack_from("<i", text, i + 1)[0]
            if tva + i + 5 + rel == target_rva:
                hits.append(f"0x{tva + i:06X}")
    return hits

for name, rva in [
    ("CItem::StartCooldown (0x639E60)", 0x639E60),
    ("CItem::GetRemCooldown (0x639E80)", 0x639E80),
    ("CItemDB_GetField70 (0x639ED0)", 0x639ED0),
    ("CAbilitySpell_StartCD (0x418D20)", 0x418D20),
]:
    print(f"  call {name}: {find_calls(rva)}")

# 查找 CUnit 内部所有共享冷却逻辑：搜索 CAbilitySpell::vt+0x3DC (0x3DED20，冷却/蓝耗检查!)
print("\n=== 搜索 0x3DED20 (CAbilitySpell::CanCast - 蓝耗+冷却检查!) ===")
print("  direct calls:", find_calls(0x3DED20))
