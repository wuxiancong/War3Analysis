#!/usr/bin/env python3
"""Disassemble leash compare sites; dump more context; hunt guard home fields."""
import struct
from pathlib import Path
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\neutral-stack")
ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")

def dump(pe, data, rva, size=0x120):
    off = pe.get_offset_from_rva(rva)
    chunk = data[off:off+size]
    lines = []
    for i in range(0, len(chunk), 16):
        row = chunk[i:i+16]
        hx = " ".join(f"{b:02X}" for b in row)
        asc = "".join(chr(b) if 32 <= b < 127 else "." for b in row)
        lines.append(f"{rva+i:08X}  {hx:<48}  {asc}")
    return "\n".join(lines)

def find_func_start(data, pe, rva, max_back=0x200):
    off = pe.get_offset_from_rva(rva)
    for i in range(0, max_back):
        o = off - i
        if o < 1:
            break
        # CC CC prologue or typical prologue
        if data[o] == 0x55 and data[o+1] == 0x8B and data[o+2] == 0xEC:
            return pe.get_rva_from_offset(o) if hasattr(pe, 'get_rva_from_offset') else None
        # int3 padding before function
        if i > 0 and data[o] == 0xCC and data[o+1] != 0xCC:
            # next byte starts func
            cand = o + 1
            return file_rva(pe, cand)
        if data[o] == 0xCC and data[o+1] == 0xCC and data[o+2] != 0xCC:
            return file_rva(pe, o+2)
    return None

def file_rva(pe, file_off):
    for s in pe.sections:
        raw, size = s.PointerToRawData, s.SizeOfRawData
        if raw <= file_off < raw + size:
            return s.VirtualAddress + (file_off - raw)
    return None

sites = {
    "1.26.0.6401": {
        "GuardDistance_use": 0xD0EFD,
        "MaxGuardDistance_use": 0xCEC1A,
        "GuardReturnTime_use": 0xC8B3C,
        "SetUnitCreepGuard": 0x3C5480,
    },
    "1.27.0.52240": {
        "GuardDistance_use": 0x47F3D6,
        "MaxGuardDistance_use": 0x47603A,
        "GuardReturnTime_use": 0x479C1D,
        "SetUnitCreepGuard": 0x1F7450,
    },
}

out = []
for ver, s in sites.items():
    pe = pefile.PE(str(ROOT/ver/"game.dll"), fast_load=True)
    data = (ROOT/ver/"game.dll").read_bytes()
    out.append(f"# {ver}\n")
    for name, rva in s.items():
        # find start by scanning back for CC CC or 55 8B EC
        off = pe.get_offset_from_rva(rva)
        start = None
        for i in range(0, 0x400):
            o = off - i
            if data[o:o+3] == b"\x55\x8B\xEC":
                start = file_rva(pe, o); break
            if i > 4 and data[o] == 0xCC and data[o+1] == 0xCC and data[o+2] not in (0xCC,):
                # might be end of pad
                pass
            if data[o] == 0xCC and data[o+1] != 0xCC and i > 0:
                # candidate: but many false positives
                pass
        # also try: aligned after double CC
        for i in range(0, 0x400):
            o = off - i
            if data[o] == 0xCC and data[o+1] != 0xCC:
                # check if looks like code start (push/mov/sub)
                if data[o+1] in (0x55, 0x56, 0x53, 0x51, 0x57, 0x8B, 0x83, 0x81, 0x6A, 0x68, 0x33):
                    start2 = file_rva(pe, o+1)
                    out.append(f"## {name} ref@0x{rva:X}  guessedStart@0x{start2:X} (cc-pad)\n")
                    out.append(dump(pe, data, start2, 0x180) + "\n\n")
                    break
        else:
            out.append(f"## {name} ref@0x{rva:X} (no start; dump around)\n")
            out.append(dump(pe, data, max(0, rva-0x40), 0x160) + "\n\n")

(OUT/"guard_funcs.md").write_text("".join(out), encoding="utf-8")
print("done", len(out))
