#!/usr/bin/env python3
"""Inventory capacity + slot array + JASS UnitItemInSlot (1.26)."""
from __future__ import annotations

import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

PATH = Path(r"C:\War3Analysis\samples\1.26.0.6401\game.dll")
data = PATH.read_bytes()
IMAGE_BASE = 0x6F000000
md = Cs(CS_ARCH_X86, CS_MODE_32)


def va_to_file(va: int) -> int:
    return va - IMAGE_BASE


def disasm(va: int, size: int = 0x100, title: str = "") -> None:
    fo = va_to_file(va)
    print(f"\n===== {title or hex(va)} VA={va:08X} =====")
    for insn in md.disasm(data[fo : fo + size], va):
        print(f"  {insn.address:08X}: {insn.mnemonic:8} {insn.op_str}")


# Inventory size getter used by moveslot
disasm(0x6F0E4050, 0x80, "InventorySize getter 6F0E4050")

# Continue moveslot swap body
disasm(0x6F0F19BE, 0x120, "moveslot swap continuation")

# Find UnitItemInSlot registration -> impl
# String at file 0x948228 -> VA 0x6F948228
name_va = IMAGE_BASE + data.find(b"UnitItemInSlot")
print(f"UnitItemInSlot string VA={name_va:08X}")
pat = struct.pack("<I", name_va)
refs = []
start = 0
while len(refs) < 10:
    i = data.find(pat, start)
    if i < 0:
        break
    refs.append(IMAGE_BASE + i)
    start = i + 1
print("xrefs", [hex(r) for r in refs])
for r in refs:
    disasm(r - 0x20, 0x50, f"UnitItemInSlot xref near {r:08X}")

for name in [b"UnitInventorySize", b"UnitAddItemToSlotById", b"UnitDropItemSlot", b"UnitRemoveItemFromSlot"]:
    s = data.find(name)
    sva = IMAGE_BASE + s
    print(f"\n{name.decode()} VA={sva:08X}")
    pref = struct.pack("<I", sva)
    i = data.find(pref)
    if i >= 0:
        disasm(IMAGE_BASE + i - 0x20, 0x50, f"{name.decode()} reg")

# Search typical pattern: slotIndex * 12 + base
# lea reg, [reg+reg*2] ; lea ..., [ebp+reg*4+0x70]
sig = bytes.fromhex("8D0C7F")  # lea ecx,[edi+edi*2] seen in moveslot
# Count occurrences of lea r,[r+r*2] near +0x70 inventory
count = 0
idx = 0
hits = []
while len(hits) < 30:
    i = data.find(b"\x8D\x0C\x7F", idx)  # lea ecx,[edi+edi*2]
    if i < 0:
        break
    # look ahead 16 bytes for +0x70
    window = data[i : i + 24]
    if b"\x70" in window:
        hits.append(IMAGE_BASE + i)
    idx = i + 1
print("\nlea ecx,[edi+edi*2] near 0x70:")
for h in hits[:20]:
    print(hex(h))
    disasm(h, 0x30, "")
