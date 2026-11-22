#!/usr/bin/env python3
"""Deep-dive GuardDistance load sites and SetUnitCreepGuard; find float globals + compare sites."""
import struct
from pathlib import Path
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\neutral-stack")
ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")

def rva_off(pe, rva):
    return pe.get_offset_from_rva(rva)

def file_rva(pe, file_off):
    for s in pe.sections:
        raw, size = s.PointerToRawData, s.SizeOfRawData
        if raw <= file_off < raw + size:
            return s.VirtualAddress + (file_off - raw)
    return None

def dump_around(data, pe, rva, before=32, after=96):
    off = rva_off(pe, rva)
    start = max(0, off - before)
    chunk = data[start:off + after]
    lines = []
    base = file_rva(pe, start)
    for i in range(0, len(chunk), 16):
        row = chunk[i:i+16]
        hx = " ".join(f"{b:02X}" for b in row)
        lines.append(f"  {base+i:08X}: {hx}")
    return "\n".join(lines)

def decode_setcreep(data, pe, rva):
    off = rva_off(pe, rva)
    stub = data[off:off+48]
    # look for or/and [eax+imm], imm or [reg+imm]
    notes = []
    i = 0
    while i < len(stub) - 3:
        # 83 48 xx yy = or dword [eax+xx], yy
        if stub[i:i+2] == b"\x83\x48":
            notes.append(f"or [eax+0x{stub[i+2]:X}], 0x{stub[i+3]:X} @+{i}")
        if stub[i:i+2] == b"\x83\x60":
            notes.append(f"and [eax+0x{stub[i+2]:X}], 0x{stub[i+3]:X} @+{i}")
        if stub[i:i+2] == b"\x83\x08":  # or [eax], imm8 unlikely
            pass
        i += 1
    return notes, " ".join(f"{b:02X}" for b in stub)

def find_float_imm_loads(data, pe, image_base, target_float=600.0):
    """Find movss/fld of 600.0f immediate in .rdata referenced from code near guard strings."""
    # IEEE 600.0f = 0x44160000
    bits = struct.pack("<f", target_float)
    hits = []
    start = 0
    while True:
        i = data.find(bits, start)
        if i < 0:
            break
        rva = file_rva(pe, i)
        if rva is not None:
            # only .rdata-ish (high RVAs)
            if rva > 0x700000:
                hits.append(rva)
        start = i + 1
    return hits[:40]

def xref_imm32(data, pe, image_base, rva):
    va = image_base + rva
    pat = struct.pack("<I", va)
    offs = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        rr = file_rva(pe, i)
        if rr is not None and rr < 0x700000:  # code
            offs.append(rr)
        start = i + 1
    return offs

TARGETS = {
    "1.26.0.6401": {
        "SetUnitCreepGuard": 0x3C5480,
        "GuardDistance_code": [0xC4BA3, 0xD0EFD],
        "MaxGuardDistance_code": [0xC4BC3, 0xCEC1A],
        "GuardReturnTime_code": [0xC4BE3, 0xC8B3C],
    },
    "1.27.0.52240": {
        "SetUnitCreepGuard": 0x1F7450,
        "GuardDistance_code": [0x47B8A3, 0x47F3D6],
        "MaxGuardDistance_code": [0x47603A, 0x47CAA3],
        "GuardReturnTime_code": [0x479C1D, 0x47B883],
    },
}

out = []
for ver, t in TARGETS.items():
    dll = ROOT / ver / "game.dll"
    pe = pefile.PE(str(dll), fast_load=True)
    data = dll.read_bytes()
    ib = pe.OPTIONAL_HEADER.ImageBase
    out.append(f"# {ver} ImageBase=0x{ib:X}\n")
    notes, hexstub = decode_setcreep(data, pe, t["SetUnitCreepGuard"])
    out.append(f"## SetUnitCreepGuard @ 0x{t['SetUnitCreepGuard']:X}\n")
    out.append(f"hex: {hexstub}\n")
    out.append(f"notes: {notes}\n\n")
    for key in ("GuardDistance_code", "MaxGuardDistance_code", "GuardReturnTime_code"):
        out.append(f"## {key}\n")
        for rva in t[key]:
            out.append(f"### code @ 0x{rva:X}\n")
            out.append(dump_around(data, pe, rva, 48, 80) + "\n\n")
            # try to find nearby absolute addresses that look like globals (6Fxxxxxx)
            off = rva_off(pe, rva)
            window = data[off-64:off+96]
            addrs = []
            for j in range(0, len(window)-3):
                val = struct.unpack_from("<I", window, j)[0]
                if 0x6F000000 <= val <= 0x6FFFFFFF:
                    addrs.append((file_rva(pe, off-64+j), val))
            out.append(f"nearby abs addrs: {[(hex(a), hex(v)) for a,v in addrs[:20]]}\n\n")

    # Find 600.0f / 1000.0f / 5.0f constants and their code xrefs (sample)
    out.append("## float immediates 600/1000/5 and sample xrefs\n")
    for name, fval in (("600", 600.0), ("1000", 1000.0), ("5.0", 5.0), ("3.0", 3.0)):
        hits = find_float_imm_loads(data, pe, ib, fval)
        out.append(f"- {name}f rdata hits (first 15): {[hex(h) for h in hits[:15]]}\n")
        # xrefs for first few
        for h in hits[:3]:
            x = xref_imm32(data, pe, ib, h)
            out.append(f"  xrefs->{hex(h)}: {[hex(xx) for xx in x[:12]]}\n")
    out.append("\n")

path = OUT / "guard_deep.md"
path.write_text("".join(out), encoding="utf-8")
print("wrote", path)
