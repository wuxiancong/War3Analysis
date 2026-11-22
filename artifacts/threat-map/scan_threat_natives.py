#!/usr/bin/env python3
"""Scan all game.dll versions for pathing / vision native name strings and xrefs."""
from __future__ import annotations

import json
import struct
from pathlib import Path

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\threat-map")

KEYS = [
    b"IsTerrainPathable\x00",
    b"IsLocationVisibleToPlayer\x00",
    b"IsUnitVisible\x00",
    b"IsUnitFogged\x00",
    b"IsUnitMasked\x00",
    b"IsUnitDetected\x00",
    b"GetLocalPlayer\x00",
    b"GetLocationZ\x00",
    b"GetDestructableLife\x00",
    b"EnumDestructablesInRect\x00",
    b"FogEnable\x00",
    b"CreateFogModifierRadius\x00",
]


def pe_info(data: bytes):
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    opt = e_lfanew + 24
    if struct.unpack_from("<H", data, opt)[0] != 0x10B:
        return None
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    coff = e_lfanew + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsz = struct.unpack_from("<H", data, coff + 16)[0]
    sec0 = coff + 20 + optsz
    sections = []
    for i in range(nsec):
        off = sec0 + i * 40
        vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append((va, vsz, raw, rsz))
    return image_base, sections


def off_to_rva(sections, off):
    for va, _vsz, raw, rsz in sections:
        if raw <= off < raw + rsz:
            return va + (off - raw)
    return None


def rva_to_off(sections, rva):
    for va, vsz, raw, rsz in sections:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None


def find_all(data: bytes, needle: bytes):
    out, i = [], 0
    while True:
        j = data.find(needle, i)
        if j < 0:
            break
        out.append(j)
        i = j + 1
    return out


def xref_ptrs(data, sections, image_base, str_off):
    str_rva = off_to_rva(sections, str_off)
    if str_rva is None:
        return []
    absva = image_base + str_rva
    pat = struct.pack("<I", absva)
    refs = []
    for off in find_all(data, pat):
        rva = off_to_rva(sections, off)
        if rva is not None:
            refs.append(rva)
    return sorted(set(refs))


def resolve_native_candidates(data, sections, image_base, str_xrefs):
    """Around string xrefs, collect push-imm code pointers (native impl candidates)."""
    cands = []
    for xr_hex in str_xrefs:
        xr = int(xr_hex, 16)
        off = rva_to_off(sections, xr)
        if off is None:
            continue
        win = data[max(0, off - 48) : off + 48]
        base = max(0, off - 48)
        i = 0
        while i < len(win) - 5:
            if win[i] == 0x68:
                imm = struct.unpack_from("<I", win, i + 1)[0]
                if image_base <= imm < image_base + 0xC00000:
                    rva = imm - image_base
                    o2 = rva_to_off(sections, rva)
                    if o2 is not None:
                        pro = data[o2 : o2 + 2]
                        if pro[:1] in (b"\x55", b"\x53", b"\x56", b"\x57", b"\x8B", b"\x83", b"\x6A") or pro == b"\x8B\xff":
                            if rva not in cands:
                                cands.append(rva)
            i += 1
    return cands


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Confirmed natives from prior docs (prefer these when present)
    known = {
        "IsUnitVisible": {
            "1.21.0.6263": 0x2C97C0,
            "1.22.0.6328": 0x3C0D90,
            "1.23.0.6352": 0x3C2C40,  # may need verify
            "1.24.1.6374": 0x3C8700,
            "1.24.4.6387": 0x3C87C0,
            "1.25.1.6397": 0x3C7A50,
            "1.26.0.6401": 0x3C7AF0,
            "1.27.0.52240": 0x1E8E80,
        },
        "GetLocalPlayer": {
            "1.26.0.6401": 0x3BBB60,
            "1.27.0.52240": 0x1E3150,
        },
        "IsLocationVisibleToPlayer": {
            "1.26.0.6401": 0x3C9940,
            "1.27.0.52240": 0x1E7DE0,
        },
        "GetDestructableLife": {
            "1.26.0.6401": 0x3C4890,
            "1.27.0.52240": 0x1E1F70,
        },
        "EnumDestructablesInRect": {
            "1.26.0.6401": 0x3C4A90,
            "1.27.0.52240": 0x1E0140,
        },
    }

    rows = []
    for verdir in sorted(VERSIONS.iterdir()):
        dll = verdir / "game.dll"
        if not dll.exists():
            continue
        data = dll.read_bytes()
        info = pe_info(data)
        if not info:
            continue
        image_base, sections = info
        entry = {"ver": verdir.name, "imageBase": hex(image_base)}
        for key in KEYS:
            name = key[:-1].decode()
            offs = find_all(data, key)
            if not offs:
                entry[name] = {"strRVA": None, "xrefs": [], "nativeGuess": None}
                continue
            str_rva = off_to_rva(sections, offs[0])
            xrefs = xref_ptrs(data, sections, image_base, offs[0])
            cands = resolve_native_candidates(data, sections, image_base, [hex(x) for x in xrefs])
            native = None
            if name in known and verdir.name in known[name]:
                native = hex(known[name][verdir.name])
            elif cands:
                native = hex(cands[0])
            entry[name] = {
                "strRVA": hex(str_rva) if str_rva is not None else None,
                "xrefs": [hex(x) for x in xrefs],
                "nativeCandidates": [hex(c) for c in cands[:4]],
                "nativeGuess": native,
            }
        rows.append(entry)
        print(
            verdir.name,
            "IsTerrainPathable",
            entry["IsTerrainPathable"]["nativeGuess"],
            "IsLocVis",
            entry["IsLocationVisibleToPlayer"]["nativeGuess"],
            "IsUnitVis",
            entry["IsUnitVisible"]["nativeGuess"],
        )

    (OUT / "native_string_xrefs.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Markdown tables
    names = [
        "IsTerrainPathable",
        "IsLocationVisibleToPlayer",
        "IsUnitVisible",
        "IsUnitFogged",
        "IsUnitMasked",
        "IsUnitDetected",
        "GetLocalPlayer",
        "GetLocationZ",
        "GetDestructableLife",
        "EnumDestructablesInRect",
    ]
    lines = ["| 版本 | " + " | ".join(names) + " |", "| :--- | " + " | ".join([" :--- "] * len(names)) + " |"]
    for e in rows:
        cells = [e["ver"]]
        for n in names:
            cells.append(f"`{e[n]['nativeGuess']}`" if e[n]["nativeGuess"] else "—")
        lines.append("| " + " | ".join(cells) + " |")
    (OUT / "native_rva_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT / "native_rva_table.md")


if __name__ == "__main__":
    main()
