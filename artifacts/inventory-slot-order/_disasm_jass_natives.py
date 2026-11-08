#!/usr/bin/env python3
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

PATH = Path(r"C:\War3Analysis\samples\1.26.0.6401\game.dll")
data = PATH.read_bytes()
IMAGE_BASE = 0x6F000000
md = Cs(CS_ARCH_X86, CS_MODE_32)


def disasm(va: int, size: int = 0x120, title: str = "") -> None:
    fo = va - IMAGE_BASE
    print(f"\n===== {title} VA={va:08X} =====")
    for insn in md.disasm(data[fo : fo + size], va):
        print(f"  {insn.address:08X}: {insn.mnemonic:8} {insn.op_str}")


# From registration:
# UnitItemInSlot -> 0x6F3C7730
# UnitInventorySize -> 0x6F3C8F00
# UnitHasItem nearby 0x6F3C76F0
# Also UnitDropItemSlot / UnitAddItemToSlotById - scan nearby registrations from previous dump
disasm(0x6F3C7730, 0x100, "JASS UnitItemInSlot")
disasm(0x6F3C8F00, 0x80, "JASS UnitInventorySize")
disasm(0x6F3C76F0, 0x50, "JASS UnitHasItem?")

# Find UnitAddItemToSlotById impl from reg block around 6F3D6487
# Read a wider registration window
disasm(0x6F3D6460, 0x100, "JASS inventory natives registration block")

# Helper 0x6F0419C0 appears to assign item into a slot record (12-byte)
disasm(0x6F0419C0, 0x80, "SlotAssign? 6F0419C0")
# 0x6F021A00 read slot item
disasm(0x6F021A00, 0x60, "SlotRead? 6F021A00")
# Resolve item handle 0x6F4786B0
disasm(0x6F4786B0, 0x60, "ResolveHandle 6F4786B0")

# Find first-empty-slot logic: often loops i=0..size-1 looking for empty handle (-1,-1)
# Search for pattern near CAbilityInventory methods: cmp eax,-1 after and of two dwords at slot
# Already seen in moveslot. Look for UnitAddItem path.
# From earlier UnitAddItem registration - find ecx value
# Grep registration for UnitAddItem string
import struct

sva = IMAGE_BASE + data.find(b"UnitAddItem\x00")
# may find UnitAddItemById first; locate exact
idx = 0
while True:
    i = data.find(b"UnitAddItem", idx)
    if i < 0:
        break
    # null-terminated exact?
    end = data.find(b"\x00", i)
    name = data[i:end]
    print(f"found {name!r} at {IMAGE_BASE+i:08X}")
    idx = i + 1

for exact in [b"UnitAddItem\x00", b"UnitAddItemById\x00", b"UnitAddItemToSlotById\x00", b"UnitDropItemSlot\x00", b"UnitRemoveItemFromSlot\x00"]:
    i = data.find(exact)
    if i < 0:
        print(exact, "missing")
        continue
    sva = IMAGE_BASE + i
    pref = struct.pack("<I", sva)
    r = data.find(pref)
    print(exact.decode().strip("\x00"), "str", hex(sva), "ref", hex(IMAGE_BASE + r) if r >= 0 else None)
    if r >= 0:
        # typically: mov edx, str; mov ecx, impl
        disasm(IMAGE_BASE + r - 0x10, 0x30, exact.decode().strip("\x00") + " reg")
