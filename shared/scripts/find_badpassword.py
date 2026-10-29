#!/usr/bin/env python3
"""Locate ERROR_ID_BADPASSWORD string + code xrefs across War3 game.dll versions."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

NEEDLE = b"ERROR_ID_BADPASSWORD\x00"


def pe_sections(data: bytes):
    e = struct.unpack_from("<I", data, 0x3C)[0]
    image_base = struct.unpack_from("<I", data, e + 0x34)[0]
    nsec = struct.unpack_from("<H", data, e + 6)[0]
    opt = struct.unpack_from("<H", data, e + 20)[0]
    sec = e + 24 + opt
    sections = []
    for i in range(nsec):
        o = sec + i * 40
        vsize, va, rsize, raw = struct.unpack_from("<IIII", data, o + 8)
        sections.append((va, raw, rsize, vsize))
    return image_base, sections


def file_to_rva(sections, off: int):
    for va, raw, rsize, _vsize in sections:
        if raw <= off < raw + rsize:
            return va + (off - raw)
    return None


def main() -> int:
    root = Path(r"D:\Qt\workspace\War3Launcher\versions")
    print(
        f"{'version':<16} {'strFile':>10} {'strRVA':>10} {'strVA':>12}  xrefRVAs(mov ecx)"
    )
    for ver in sorted(root.iterdir()):
        if not ver.is_dir():
            continue
        g = next((f for f in ver.iterdir() if f.name.lower() == "game.dll"), None)
        if g is None:
            print(f"{ver.name:<16} NO game.dll")
            continue
        data = g.read_bytes()
        base, secs = pe_sections(data)
        foff = data.find(NEEDLE)
        if foff < 0:
            print(f"{ver.name:<16} NO STRING")
            continue
        srva = file_to_rva(secs, foff)
        sva = base + srva
        imm = struct.pack("<I", sva)
        xrefs = []
        start = 0
        while True:
            i = data.find(imm, start)
            if i < 0:
                break
            if i > 0 and data[i - 1] == 0xB9:
                xr = file_to_rva(secs, i)
                if xr is not None and xr < 0xA00000:
                    xrefs.append(xr)
            start = i + 1
        xref_s = ",".join(f"0x{x:X}" for x in xrefs) or "-"
        print(
            f"{ver.name:<16} 0x{foff:08X} 0x{srva:08X} 0x{sva:08X}  {xref_s}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
