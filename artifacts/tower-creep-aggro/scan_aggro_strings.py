#!/usr/bin/env python3
"""Scan all War3Launcher/versions/*/game.dll for aggro-related strings and xrefs."""
from __future__ import annotations

import json
import struct
from pathlib import Path

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\tower-creep-aggro")

KEYS = [
    b"CallForHelp\x00",
    b"CreepCallForHelp\x00",
    b"GetUnitAcquireRange\x00",
    b"SetUnitAcquireRange\x00",
    b"AttackNotifyRange\x00",
]


def pe_info(data: bytes):
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    opt = e_lfanew + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    if magic != 0x10B:
        return None
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    coff = e_lfanew + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsz = struct.unpack_from("<H", data, coff + 16)[0]
    sec0 = coff + 20 + optsz
    sections = []
    for i in range(nsec):
        off = sec0 + i * 40
        name = data[off : off + 8].split(b"\x00", 1)[0].decode("ascii", "ignore")
        vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append((name, va, vsz, raw, rsz))
    return image_base, sections


def rva_to_off(sections, rva):
    for _name, va, vsz, raw, rsz in sections:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None


def off_to_rva(sections, off):
    for _name, va, _vsz, raw, rsz in sections:
        if raw <= off < raw + rsz:
            return va + (off - raw)
    return None


def find_all(data: bytes, needle: bytes):
    out = []
    i = 0
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


def find_func_start(data, sections, rva, back=0x300):
    off = rva_to_off(sections, rva)
    if off is None:
        return None
    start = max(0, off - back)
    best = None
    for i in range(off - start - 1, -1, -1):
        b = data[start + i]
        if b in (0xCC, 0xC3):
            cand = start + i + 1
            if cand > off:
                continue
            nb = data[cand : cand + 3]
            if nb[:1] in (b"\x55", b"\x53", b"\x56", b"\x57", b"\x51", b"\x83", b"\x8B", b"\x6A") or nb[
                :2
            ] == b"\x8B\xff":
                best = cand
                break
    if best is None:
        return rva
    return off_to_rva(sections, best)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for verdir in sorted(VERSIONS.iterdir()):
        dll = verdir / "game.dll"
        if not dll.exists():
            continue
        data = dll.read_bytes()
        info = pe_info(data)
        if not info:
            rows.append({"ver": verdir.name, "error": "not PE32"})
            continue
        image_base, sections = info
        entry = {"ver": verdir.name, "imageBase": hex(image_base), "size": len(data)}
        for key in KEYS:
            name = key[:-1].decode()
            offs = find_all(data, key)
            if not offs:
                entry[name] = {"strRVA": None, "xrefs": [], "funcs": []}
                continue
            str_off = offs[0]
            str_rva = off_to_rva(sections, str_off)
            xrefs = xref_ptrs(data, sections, image_base, str_off)
            funcs = []
            for xr in xrefs:
                fs = find_func_start(data, sections, xr)
                funcs.append({"xrefRVA": hex(xr), "guessFunc": hex(fs) if fs else None})
            entry[name] = {
                "strRVA": hex(str_rva) if str_rva is not None else None,
                "xrefs": [hex(x) for x in xrefs],
                "funcs": funcs,
            }
        rows.append(entry)
        print(
            verdir.name,
            "CFH",
            entry["CallForHelp"]["xrefs"],
            "CreepCFH",
            entry["CreepCallForHelp"]["xrefs"],
            "GetAcq",
            entry["GetUnitAcquireRange"]["xrefs"][:3],
        )

    (OUT / "string_xrefs_all_versions.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    # Compact CSV-like markdown table helpers
    lines = [
        "| 版本 | CallForHelp str | CFH xref(s) | CreepCallForHelp str | CreepCFH xref(s) | GetUnitAcquireRange native xref |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for e in rows:
        if "error" in e:
            continue
        cfh = e["CallForHelp"]
        ccfh = e["CreepCallForHelp"]
        acq = e["GetUnitAcquireRange"]
        lines.append(
            f"| {e['ver']} | `{cfh['strRVA']}` | `{', '.join(cfh['xrefs'])}` | `{ccfh['strRVA']}` | `{', '.join(ccfh['xrefs'])}` | `{', '.join(acq['xrefs'][:2])}` |"
        )
    (OUT / "rva_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote", OUT / "string_xrefs_all_versions.json")
    print("wrote", OUT / "rva_table.md")


if __name__ == "__main__":
    main()
