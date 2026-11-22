"""Scan all War3Launcher/versions/*/game.dll for visibility natives."""
import struct
from pathlib import Path

NAMES = [
    b"IsUnitInvisible\x00",
    b"IsUnitDetected\x00",
    b"IsUnitVisible\x00",
    b"IsUnitHidden\x00",
]

base = Path(r"D:\Qt\workspace\War3Launcher\versions")
out = []

for ver in sorted(base.iterdir()):
    dll = ver / "game.dll"
    if not dll.exists():
        continue
    data = dll.read_bytes()
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    sections = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    size_opt = struct.unpack_from("<H", data, e_lfanew + 0x14)[0]
    sec_off = e_lfanew + 0x18 + size_opt
    image_base = struct.unpack_from("<I", data, e_lfanew + 0x34)[0]

    def file_to_rva(pos):
        for i in range(sections):
            off = sec_off + i * 40
            vsize, vaddr, rsize, roff = struct.unpack_from("<IIII", data, off + 8)
            if roff <= pos < roff + rsize:
                return vaddr + (pos - roff)
        return None

    row = {"ver": ver.name}
    for name in NAMES:
        pos = data.find(name)
        if pos < 0:
            row[name[:-1].decode()] = None
            continue
        rva = file_to_rva(pos)
        abs_addr = (image_base + rva) & 0xFFFFFFFF
        pat = b"\xBA" + struct.pack("<I", abs_addr)
        xref = data.find(pat)
        handler = None
        if xref >= 0:
            # Prefer ecx load immediately after BA (edx=str; ecx=handler; call)
            if xref + 5 < len(data) and data[xref + 5] == 0xB9:
                handler = struct.unpack_from("<I", data, xref + 6)[0] - image_base
            # Or ecx load immediately before BA
            elif xref >= 5 and data[xref - 5] == 0xB9:
                handler = struct.unpack_from("<I", data, xref - 4)[0] - image_base
        row[name[:-1].decode()] = {
            "strRVA": hex(rva),
            "nativeRVA": hex(handler) if handler is not None else None,
        }
    out.append(row)
    print(ver.name, {k: v for k, v in row.items() if k != "ver"})

# Also dump 1.26 helper details
print("\n# CUnit detection-related offsets from IsUnitDetected helper")
print("1.26 helper 0x27A320: reads CUnit+0x130 / +0x134; detection blob +0x2C / +0x74 per player")
print("1.27 helper ~0x66E3B0: same +0x130/+0x134 and +0x2C/+0x74")
