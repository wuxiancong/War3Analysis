#!/usr/bin/env python3
"""Scan game.dll for GuardDistance / SetUnitCreepGuard / related natives."""
import struct
from pathlib import Path

import pefile

VERSIONS = [
    "1.26.0.6401",
    "1.27.0.52240",
    "1.24.4.6387",
    "1.25.1.6397",
    "1.24.1.6374",
    "1.23.0.6352",
    "1.22.0.6328",
    "1.21.0.6263",
    "1.20.4.6074",
]
ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\neutral-stack")
OUT.mkdir(parents=True, exist_ok=True)

STRINGS = [
    "GuardDistance",
    "MaxGuardDistance",
    "GuardReturnTime",
    "CreepCampPathingCellDistance",
    "CreepCallForHelp",
    "SetUnitCreepGuard",
    "RemoveGuardPosition",
    "RecycleGuardPosition",
    "RemoveAllGuardPositions",
]

def file_rva(pe, file_off):
    for s in pe.sections:
        raw, size = s.PointerToRawData, s.SizeOfRawData
        if raw <= file_off < raw + size:
            return s.VirtualAddress + (file_off - raw)
    return None

def rva_to_off(pe, rva):
    return pe.get_offset_from_rva(rva)

def find_cstr(data, pe, name):
    needle = name.encode() + b"\x00"
    hits = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        prev = data[i - 1] if i else 0
        if prev == 0 or prev == 0x0A or prev == 0x0D:
            rva = file_rva(pe, i)
            if rva is not None:
                hits.append((i, rva))
        start = i + 1
    return hits

def find_native_reg(data, image_base, str_rva):
    """Find mov edx, strVA; mov ecx, funcVA pattern (1.26 style JASS native table)."""
    va = image_base + str_rva
    funcs = []
    # BA imm32 = mov edx, imm
    pat = b"\xBA" + struct.pack("<I", va)
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        # look nearby for B9 imm32 (mov ecx, func)
        window = data[i:i+32]
        for j in range(len(window) - 5):
            if window[j] == 0xB9:
                func_va = struct.unpack_from("<I", window, j + 1)[0]
                if image_base < func_va < image_base + 0x1000000:
                    funcs.append(func_va - image_base)
            if window[j] == 0xB8:
                func_va = struct.unpack_from("<I", window, j + 1)[0]
                if image_base < func_va < image_base + 0x1000000:
                    funcs.append(("eax", func_va - image_base))
        start = i + 1
    # also push imm / lea variants: scan for raw VA pointers to string
    ptr = struct.pack("<I", va)
    start = 0
    ptr_hits = []
    while True:
        i = data.find(ptr, start)
        if i < 0:
            break
        rva = file_rva(pe_global, i) if False else None
        ptr_hits.append(i)
        start = i + 1
    return funcs, ptr_hits

def find_ptr_to_va(data, pe, image_base, str_rva):
    va = image_base + str_rva
    ptr = struct.pack("<I", va)
    offs = []
    start = 0
    while True:
        i = data.find(ptr, start)
        if i < 0:
            break
        rva = file_rva(pe, i)
        if rva is not None:
            offs.append(rva)
        start = i + 1
    return offs

def disasm_stub(data, pe, rva, n=64):
    """Hex dump of function start."""
    try:
        off = pe.get_offset_from_rva(rva)
    except Exception:
        return ""
    chunk = data[off:off+n]
    return " ".join(f"{b:02X}" for b in chunk)

lines = []
for ver in VERSIONS:
    dll = ROOT / ver / "game.dll"
    if not dll.exists():
        lines.append(f"## {ver}: MISSING\n")
        continue
    pe = pefile.PE(str(dll), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT']])
    data = Path(dll).read_bytes()
    image_base = pe.OPTIONAL_HEADER.ImageBase
    lines.append(f"## {ver}  ImageBase=0x{image_base:X}  size={len(data)}\n")
    for name in STRINGS:
        hits = find_cstr(data, pe, name)
        if not hits:
            lines.append(f"- {name}: not found\n")
            continue
        for file_off, rva in hits[:3]:
            ptrs = find_ptr_to_va(data, pe, image_base, rva)
            funcs, raw_hits = find_native_reg(data, image_base, rva)
            lines.append(f"- {name}: strRVA=0x{rva:X} file=0x{file_off:X} ptrRVAs={[hex(p) for p in ptrs[:8]]}\n")
            # decode native regs
            flat = []
            for f in funcs:
                if isinstance(f, tuple):
                    flat.append(f"{f[0]}=0x{f[1]:X}")
                else:
                    flat.append(f"0x{f:X}")
                    lines.append(f"    stub: {disasm_stub(data, pe, f)}\n")
            if flat:
                lines.append(f"    nativeRegs: {flat}\n")
            lines.append(f"    rawVARefs: {len(raw_hits)}\n")
    lines.append("\n")

out_path = OUT / "guard_string_scan.md"
out_path.write_text("".join(lines), encoding="utf-8")
print(f"wrote {out_path} ({len(lines)} lines)")
