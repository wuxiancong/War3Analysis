#!/usr/bin/env python3
"""Disassemble game.dll neighborhoods around moveslot/useslot constants (1.26)."""
from __future__ import annotations

import struct
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    import subprocess
    import sys

    subprocess.check_call([sys.executable, "-m", "pip", "install", "capstone", "-q"])
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32

PATH = Path(r"C:\War3Analysis\samples\1.26.0.6401\game.dll")
data = PATH.read_bytes()

e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
num_sections = struct.unpack_from("<H", data, e_lfanew + 6)[0]
opt_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
image_base = struct.unpack_from("<I", data, e_lfanew + 24 + 28)[0]
sec_off = e_lfanew + 24 + opt_size
sections = []
for i in range(num_sections):
    off = sec_off + i * 40
    name = data[off : off + 8].split(b"\0", 1)[0].decode("ascii", "replace")
    vsize, va, rawsize, rawptr = struct.unpack_from("<IIII", data, off + 8)
    sections.append((name, va, vsize, rawptr, rawsize))
    print(f"section {name:8} VA={va:08X} VSIZE={vsize:08X} RAW={rawptr:08X} RSIZE={rawsize:08X}")


def file_to_va(file_off: int) -> int | None:
    for name, va, vsize, rawptr, rawsize in sections:
        if rawptr <= file_off < rawptr + max(rawsize, 1):
            return image_base + va + (file_off - rawptr)
    return None


def va_to_file(va: int) -> int | None:
    rva = va - image_base
    for name, sec_va, vsize, rawptr, rawsize in sections:
        if sec_va <= rva < sec_va + max(vsize, rawsize):
            return rawptr + (rva - sec_va)
    return None


md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False

interesting = [
    0x1026E0,
    0xF1950,
    0x37870,
    0xF9320,
    0x3C8F70,
    0x3C9060,
    0x92EE30,
    0x147AD0,
    0x229B00,
]


def disasm_at_file(file_off: int, size: int = 0x80) -> None:
    va = file_to_va(file_off)
    print(f"\n===== file+0x{file_off:X} VA={hex(va) if va else '?'} =====")
    chunk = data[file_off : file_off + size]
    if va is None:
        print(chunk[:64].hex())
        return
    for insn in md.disasm(chunk, va):
        mark = ""
        if b"\x22\xd0\x00\x00" in insn.bytes or b"\x28\xd0\x00\x00" in insn.bytes:
            mark = "  <--- order const"
        print(f"  {insn.address:08X}: {insn.mnemonic:8} {insn.op_str}{mark}")


for fo in interesting:
    disasm_at_file(fo, 0xA0)

# Also dump dword table around 0x92EE30
print("\n===== dword table near 0x92EE30 =====")
for i in range(0, 0x80, 4):
    fo = 0x92EE00 + i
    val = struct.unpack_from("<I", data, fo)[0]
    va = file_to_va(fo)
    print(f"  file+0x{fo:X} VA={va:08X} dword=0x{val:08X} ({val})")
