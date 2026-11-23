# -*- coding: utf-8 -*-
"""
1. 搜索 0x418D20 (CAbilitySpell::StartCooldown) 的所有调用者（找共享冷却逻辑！）
2. 搜索 CAbilitySpell 的 GetManaCost 虚槽（搜 SLK "Cost" 或读 CAbilitySpell+0x50 查表）
3. 搜索 CItem::GetCooldownId / CUnit 共享冷却表
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

print("=== 1. call 0x418D20 (CAbilitySpell::StartCooldown) ===")
print(" ", find_calls(0x418D20))

print("\n=== 2. call 0x043700 (CAgentTimer::Start) in CUnit/CItem/CAbilityInventory (0x520000..0x690000) ===")
hits_t = []
s_off = 0x520000 - tva
e_off = 0x690000 - tva
for i in range(s_off, e_off):
    if text[i] == 0xE8:
        rel = struct.unpack_from("<i", text, i + 1)[0]
        if tva + i + 5 + rel == 0x043700:
            hits_t.append(f"0x{tva + i:06X}")
print(f"  ({len(hits_t)}): {hits_t[:30]}")

print("\n=== 3. 搜索事件 0xD01BE (冷却结束事件) 的引用 ===")
pat = struct.pack("<I", 0x000D01BE)
pos = 0
hits_e = []
while True:
    idx = text.find(pat, pos)
    if idx == -1:
        break
    pos = idx + 1
    hits_e.append(f"0x{tva + idx:06X}")
print("  0xD01BE:", hits_e)

print("\n=== 4. 搜索 RTTI 中含 Cooldown / Timer / Cost 的类 ===")
for key in ("Cooldown", "Shared", "Mana", "Spell"):
    for tname, vts in sorted(pe.find_rtti_vtables(key)):
        if any(x in tname for x in ("Cooldown", "Shared")):
            print(f"  {tname}: {[(hex(o), hex(v)) for o, v in vts]}")
