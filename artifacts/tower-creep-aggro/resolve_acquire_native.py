#!/usr/bin/env python3
"""Resolve GetUnitAcquireRange / SetUnitAcquireRange native function RVAs from game.dll registration sites."""
from __future__ import annotations

import json
import struct
from pathlib import Path

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\tower-creep-aggro")
XREFS = json.loads((OUT / "string_xrefs_all_versions.json").read_text(encoding="utf-8"))


def pe_info(data: bytes):
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    opt = e_lfanew + 24
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


def rva_to_off(sections, rva):
    for va, vsz, raw, rsz in sections:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None


def off_to_rva(sections, off):
    for va, _vsz, raw, rsz in sections:
        if raw <= off < raw + rsz:
            return va + (off - raw)
    return None


def resolve_native(data, sections, image_base, str_xrefs):
    """Around each string xref, look for `push imm32` of a code pointer (native impl)."""
    candidates = []
    for xr_hex in str_xrefs:
        xr = int(xr_hex, 16)
        off = rva_to_off(sections, xr)
        if off is None:
            continue
        win = data[max(0, off - 40) : off + 40]
        base = max(0, off - 40)
        i = 0
        while i < len(win) - 5:
            if win[i] == 0x68:  # push imm32
                imm = struct.unpack_from("<I", win, i + 1)[0]
                if image_base <= imm < image_base + 0x1000000:
                    rva = imm - image_base
                    # must land in executable-looking section (.text)
                    o2 = rva_to_off(sections, rva)
                    if o2 is not None:
                        # prefer addresses that look like function starts
                        pro = data[o2 : o2 + 3]
                        if pro[:1] in (b"\x55", b"\x53", b"\x56", b"\x57", b"\x8B", b"\x83", b"\x6A") or pro[
                            :2
                        ] == b"\x8B\xff":
                            candidates.append(rva)
            i += 1
    # unique preserve order
    seen = []
    for c in candidates:
        if c not in seen:
            seen.append(c)
    return seen


def main():
    rows = []
    for e in XREFS:
        ver = e["ver"]
        data = (VERSIONS / ver / "game.dll").read_bytes()
        image_base, sections = pe_info(data)
        get_cands = resolve_native(data, sections, image_base, e["GetUnitAcquireRange"]["xrefs"])
        set_cands = resolve_native(
            data, sections, image_base, e.get("SetUnitAcquireRange", {}).get("xrefs", [])
        )
        # CreepCallForHelp: second xref often the gameplay-constant *use*; first is loader
        ccfh = e["CreepCallForHelp"]["xrefs"]
        cfh = e["CallForHelp"]["xrefs"]
        row = {
            "ver": ver,
            "GetUnitAcquireRange_candidates": [hex(x) for x in get_cands],
            "SetUnitAcquireRange_candidates": [hex(x) for x in set_cands],
            "CallForHelp_xrefs": cfh,
            "CreepCallForHelp_xrefs": ccfh,
            # Prefer later xref as "use" when multiple (post-1.22)
            "CallForHelp_use_guess": cfh[1] if len(cfh) >= 2 else (cfh[0] if cfh else None),
            "CreepCallForHelp_use_guess": ccfh[1] if len(ccfh) >= 2 else (ccfh[0] if ccfh else None),
        }
        rows.append(row)
        print(ver, "GetAcq", row["GetUnitAcquireRange_candidates"][:3], "CreepUse", row["CreepCallForHelp_use_guess"])

    (OUT / "native_resolve.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")

    # Known confirmed from war3-lasthit-combat-data.md for cross-check
    known = {
        "1.26.0.6401": 0x3C5D10,
        "1.27.0.52240": 0x1E5F50,
        "1.25.1.6397": 0x3C5AE0,
        "1.24.4.6387": 0x3C5FC0,
        "1.24.1.6374": 0x3C5F00,
        "1.23.0.6352": 0x3C0440,
        "1.22.0.6328": 0x3BE720,
        "1.21.0.6263": 0x2C4450,
    }
    lines = [
        "| 版本 | GetUnitAcquireRange native | SetUnitAcquireRange native (候选) | CallForHelp 使用点(估) | CreepCallForHelp 使用点(估) |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for row in rows:
        ver = row["ver"]
        gets = row["GetUnitAcquireRange_candidates"]
        # prefer known if present in candidates else first candidate
        if ver in known:
            g = hex(known[ver])
            if g not in gets and gets:
                g = f"{hex(known[ver])} (文档确认; 扫描候选 {', '.join(gets[:2])})"
            else:
                g = hex(known[ver])
        else:
            g = gets[0] if gets else "—"
        s = row["SetUnitAcquireRange_candidates"][0] if row["SetUnitAcquireRange_candidates"] else "—"
        lines.append(
            f"| {ver} | `{g}` | `{s}` | `{row['CallForHelp_use_guess']}` | `{row['CreepCallForHelp_use_guess']}` |"
        )
    (OUT / "native_rva_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote native_rva_table.md")


if __name__ == "__main__":
    main()
