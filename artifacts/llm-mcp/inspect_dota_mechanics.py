# -*- coding: utf-8 -*-
"""提取 DotA 6.83d war3map.j 中：可靠/不可靠金钱、买活、Glyph、肉山、信使的精确脚本逻辑与 FourCC/坐标。"""
import struct

lines = (
    open(r"D:\Qt\workspace\War3Script\war3map.j", "r", encoding="utf-8", errors="replace")
    .read()
    .replace("\r\n", "\n")
    .replace("\r", "\n")
    .split("\n")
)


def dump(title, start, end):
    print(f"\n=== {title} (L{start}..L{end}) ===")
    for i in range(start - 1, min(end, len(lines))):
        print(f"{i+1}: {lines[i]}")


def i2fcc(n):
    return struct.pack(">I", n).decode("ascii", errors="replace")


# 1. Buyback (around L15651)
dump("Buyback (around L15651)", 15615, 15675)
# 2. Glyph (around L20908)
dump("Glyph (around L20908)", 20895, 20960)
# 3. Roshan (around L13935 & L22940)
dump("Roshan Death/Kill (around L13935)", 13930, 13980)
dump("Roshan Spawn (around L22920)", 22920, 22965)
# 4. Courier FourCCs
print("\n=== Courier FourCCs ===")
for x in [1848651849, 1848652338, 1848652337, 1848651828, 1848652088, 1848652099, 1848652103]:
    print(f"  {x} = {i2fcc(x)}")
# 5. Search reliable gold / gold deduction on death
print("\n=== Reliable gold search (SaveInteger / LoadInteger near PLAYER_STATE_RESOURCE_GOLD) ===")
for i, l in enumerate(lines):
    if "PLAYER_STATE_RESOURCE_GOLD" in l and any(k in l for k in ["SetPlayerState", "GetPlayerState"]):
        if i < 12000:
            print(f"  L{i+1}: {l[:120]}")
