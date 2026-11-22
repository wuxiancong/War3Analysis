#!/usr/bin/env python3
"""For each version, dump bytes around CreepCallForHelp / CallForHelp xrefs and find nearby float 600.0."""
from __future__ import annotations

import json
import struct
from pathlib import Path

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\tower-creep-aggro")
XREFS = json.loads((OUT / "string_xrefs_all_versions.json").read_text(encoding="utf-8"))


def pe_sections(data: bytes):
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    opt = e_lfanew + 24
    coff = e_lfanew + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsz = struct.unpack_from("<H", data, coff + 16)[0]
    sec0 = coff + 20 + optsz
    sections = []
    for i in range(nsec):
        off = sec0 + i * 40
        vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append((va, vsz, raw, rsz))
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    return image_base, sections


def rva_to_off(sections, rva):
    for va, vsz, raw, rsz in sections:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None


def main():
    rows = []
    for e in XREFS:
        ver = e["ver"]
        dll = VERSIONS / ver / "game.dll"
        data = dll.read_bytes()
        image_base, sections = pe_sections(data)
        entry = {"ver": ver}
        for key in ("CallForHelp", "CreepCallForHelp"):
            info = e[key]
            notes = []
            for xr_hex in info["xrefs"]:
                xr = int(xr_hex, 16)
                off = rva_to_off(sections, xr)
                if off is None:
                    continue
                window = data[max(0, off - 64) : off + 96]
                # find float 600.0 = 0x44160000
                f600 = struct.pack("<f", 600.0)
                hits = []
                for i in range(0, len(window) - 3):
                    if window[i : i + 4] == f600:
                        hits.append(i - (off - max(0, off - 64)))
                # also look for push imm of pointer then fld/movss nearby
                snippet = window.hex()
                notes.append(
                    {
                        "xref": xr_hex,
                        "float600_rel_offsets": hits,
                        "bytes": data[off : off + 24].hex(" "),
                    }
                )
            entry[key] = notes
        rows.append(entry)
        print(ver, "CreepCFH", entry["CreepCallForHelp"])

    (OUT / "cfh_xref_bytes.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
