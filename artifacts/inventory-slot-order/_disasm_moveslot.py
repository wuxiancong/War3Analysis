#!/usr/bin/env python3
"""Deep-dive moveslot handler + inventory slot array patterns (1.26 game.dll)."""
from __future__ import annotations

import struct
from pathlib import Path

from capstone import Cs, CS_ARCH_X86, CS_MODE_32

PATH = Path(r"C:\War3Analysis\samples\1.26.0.6401\game.dll")
data = PATH.read_bytes()
IMAGE_BASE = 0x6F000000
# 1.26: .text RAW==VA for first sections (file_off == rva for .text/.rdata roughly)
# From previous parse: RAW==VA for .text and .rdata


def va_to_file(va: int) -> int:
    return va - IMAGE_BASE


def file_to_va(fo: int) -> int:
    return IMAGE_BASE + fo


md = Cs(CS_ARCH_X86, CS_MODE_32)


def disasm(va: int, size: int = 0x120, title: str = "") -> None:
    fo = va_to_file(va)
    print(f"\n===== {title or hex(va)} VA={va:08X} file+0x{fo:X} =====")
    for insn in md.disasm(data[fo : fo + size], va):
        print(f"  {insn.address:08X}: {insn.mnemonic:8} {insn.op_str}")


# Moveslot dispatcher already found: jae -> call 0x6F0F1810
disasm(0x6F102680, 0x120, "order-dispatch before moveslot")
disasm(0x6F0F1810, 0x200, "moveslot handler 6F0F1810")

# Find useslot range: look for cmp with 0xD002D followed by cmp 0xD0028 nearby
pat_d = struct.pack("<I", 0xD002D)
idx = 0
print("\n===== search cmp .. 0xD002D contexts =====")
while True:
    i = data.find(pat_d, idx)
    if i < 0:
        break
    # show preceding 16 bytes hex + disasm window
    va = file_to_va(i)
    print(f"\nhit file+0x{i:X} VA={va:08X}")
    start = max(0, i - 0x20)
    disasm(file_to_va(start), 0x60, f"near D002D @{va:08X}")
    idx = i + 1

# Find CAbilityInventory RTTI / typeinfo
name = b".?AVCAbilityInventory@@"
i = data.find(name)
print(f"\nRTTI name at file+0x{i:X}" if i >= 0 else "\nno RTTI name")
# Also search MSVC decorated / simple
for n in [b"CAbilityInventory", b".?AVCInventoryBar@@", b"CInventoryBar"]:
    i = data.find(n)
    print(f"{n!r} -> file+0x{i:X} VA={file_to_va(i):08X}" if i >= 0 else f"{n!r} NONE")

# Xref-ish: find immediate pushes of address of "CAbilityInventory" string
s = data.find(b"CAbilityInventory")
s_va = file_to_va(s)
pat = struct.pack("<I", s_va)
print(f"\nstring VA={s_va:08X}, xref immediates:")
idx = 0
refs = []
while len(refs) < 20:
    i = data.find(pat, idx)
    if i < 0:
        break
    refs.append(i)
    idx = i + 1
for fo in refs:
    print(f"  file+0x{fo:X} VA={file_to_va(fo):08X}")
    disasm(file_to_va(max(0, fo - 0x10)), 0x40, f"xref usestring @{file_to_va(fo):08X}")
