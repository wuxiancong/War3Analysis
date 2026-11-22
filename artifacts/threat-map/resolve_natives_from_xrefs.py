#!/usr/bin/env python3
"""Resolve JASS native impl RVAs by decoding registration sites near name-string xrefs.

War3 registration patterns (observed):
  - 1.22–1.26: mov edx, str; mov ecx, func; push sig; call Register
  - 1.27: often push/lea variants; also BA str / B9 func
  - Early: similar BA/B9 or 68 push
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\threat-map")
XREFS = json.loads((OUT / "native_string_xrefs.json").read_text(encoding="utf-8"))

# Prefer these confirmed values from llm-mcp / eat-tree / fog docs
OVERRIDE = {
    "GetLocalPlayer": {
        "1.0.17.5988": 0x2CC8E0, "1.0.20.6048": 0x2CC8E0, "1.20.4.6074": 0x2CCA00,
        "1.21.0.6263": 0x2CFFD0, "1.22.0.6328": 0x3B6080, "1.23.0.6352": 0x3B7DA0,
        "1.24.1.6374": 0x3BC5E0, "1.24.4.6387": 0x3BC6A0, "1.25.1.6397": 0x3BB930,
        "1.26.0.6401": 0x3BBB60, "1.27.0.52240": 0x1E3150,
    },
    "IsUnitVisible": {
        "1.0.17.5988": 0x2C60D0, "1.0.20.6048": 0x2C60D0, "1.20.4.6074": 0x2C61F0,
        "1.21.0.6263": 0x2C97C0, "1.22.0.6328": 0x3C0D90, "1.23.0.6352": 0x3C2AB0,
        "1.24.1.6374": 0x3C8570, "1.24.4.6387": 0x3C8630, "1.25.1.6397": 0x3C78C0,
        "1.26.0.6401": 0x3C7AF0, "1.27.0.52240": 0x1E8E80,
    },
    "IsUnitFogged": {
        "1.0.17.5988": 0x2C6E20, "1.0.20.6048": 0x2C6E20, "1.20.4.6074": 0x2C6F40,
        "1.21.0.6263": 0x2CA510, "1.22.0.6328": 0x3C0FA0, "1.23.0.6352": 0x3C2CC0,
        "1.24.1.6374": 0x3C8780, "1.24.4.6387": 0x3C8840, "1.25.1.6397": 0x3C7AD0,
        "1.26.0.6401": 0x3C7D00, "1.27.0.52240": 0x1E8640,
    },
    "IsUnitMasked": {
        "1.0.17.5988": 0x2C7020, "1.0.20.6048": 0x2C7020, "1.20.4.6074": 0x2C7140,
        "1.21.0.6263": 0x2CA710, "1.22.0.6328": 0x3C1020, "1.23.0.6352": 0x3C2D40,
        "1.24.1.6374": 0x3C8800, "1.24.4.6387": 0x3C88C0, "1.25.1.6397": 0x3C7B50,
        "1.26.0.6401": 0x3C7D80, "1.27.0.52240": 0x1E8B00,
    },
    "IsUnitDetected": {
        "1.0.17.5988": 0x2C6B40, "1.0.20.6048": 0x2C6B40, "1.20.4.6074": 0x2C6C60,
        "1.21.0.6263": 0x2CA230, "1.22.0.6328": 0x3C0F20, "1.23.0.6352": 0x3C2C40,
        "1.24.1.6374": 0x3C8700, "1.24.4.6387": 0x3C87C0, "1.25.1.6397": 0x3C7A50,
        "1.26.0.6401": 0x3C7C80, "1.27.0.52240": 0x1E8580,
    },
    "IsLocationVisibleToPlayer": {
        "1.0.17.5988": 0x2CDCC0, "1.0.20.6048": 0x2CDCC0, "1.20.4.6074": 0x2CDDE0,
        "1.21.0.6263": 0x2D13B0, "1.22.0.6328": 0x3C2BE0, "1.23.0.6352": 0x3C4900,
        "1.24.1.6374": 0x3CA3C0, "1.24.4.6387": 0x3CA480, "1.25.1.6397": 0x3C9710,
        "1.26.0.6401": 0x3C9940, "1.27.0.52240": 0x1E7DE0,
    },
    "GetDestructableLife": {
        "1.0.17.5988": 0x2BC8C0, "1.0.20.6048": 0x2BC8C0, "1.20.4.6074": 0x2BC9E0,
        "1.21.0.6263": 0x2BFFB0, "1.22.0.6328": 0x3BDB30, "1.23.0.6352": 0x3BF850,
        "1.24.1.6374": 0x3C5310, "1.24.4.6387": 0x3C53D0, "1.25.1.6397": 0x3C4660,
        "1.26.0.6401": 0x3C4890, "1.27.0.52240": 0x1E1F70,
    },
    "EnumDestructablesInRect": {
        "1.0.17.5988": 0x2BCF40, "1.0.20.6048": 0x2BCF40, "1.20.4.6074": 0x2BD060,
        "1.21.0.6263": 0x2C0630, "1.22.0.6328": 0x3BDD30, "1.23.0.6352": 0x3BFA50,
        "1.24.1.6374": 0x3C5510, "1.24.4.6387": 0x3C55D0, "1.25.1.6397": 0x3C4860,
        "1.26.0.6401": 0x3C4A90, "1.27.0.52240": 0x1E0140,
    },
}

NAMES = [
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
    "FogEnable",
    "CreateFogModifierRadius",
]


def pe_sections(data: bytes):
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


def resolve_from_xref(data, sections, image_base, xref_rva):
    """At registration site: look for B9 imm32 / 68 imm32 that point into .text as native."""
    off = rva_to_off(sections, xref_rva)
    if off is None:
        return None
    win = data[max(0, off - 32) : off + 64]
    base = max(0, off - 32)
    hits = []
    i = 0
    while i < len(win) - 5:
        op = win[i]
        if op in (0xB9, 0xB8, 0xBA, 0xBB, 0x68):  # mov reg,imm / push imm
            imm = struct.unpack_from("<I", win, i + 1)[0]
            if image_base <= imm < image_base + 0xC00000:
                rva = imm - image_base
                o2 = rva_to_off(sections, rva)
                if o2 is not None and o2 != off:  # not the string itself
                    # skip if points at our string region (rdata)
                    # prefer code-looking prolog
                    pro = data[o2 : o2 + 3]
                    if pro[:1] in (b"\x55", b"\x53", b"\x56", b"\x57", b"\x8B", b"\x83", b"\x6A", b"\x51") or pro[:2] == b"\x8B\xff":
                        hits.append(rva)
        i += 1
    # unique
    out = []
    for h in hits:
        if h not in out:
            out.append(h)
    # Prefer the one that is NOT equal to known string - already filtered
    # If multiple, prefer first that is in lower half of image (code often before rdata in older; 1.27 code mixed)
    return out


def main():
    results = []
    for e in XREFS:
        ver = e["ver"]
        data = (VERSIONS / ver / "game.dll").read_bytes()
        image_base, sections = pe_sections(data)
        row = {"ver": ver}
        for name in NAMES:
            info = e.get(name) or {}
            if name in OVERRIDE and ver in OVERRIDE[name]:
                row[name] = hex(OVERRIDE[name][ver])
                row[name + "_src"] = "override"
                continue
            xrefs = info.get("xrefs") or []
            all_hits = []
            for xr in xrefs:
                hits = resolve_from_xref(data, sections, image_base, int(xr, 16)) or []
                for h in hits:
                    if h not in all_hits:
                        all_hits.append(h)
            # Heuristic: registration uses mov ecx, native near mov edx, string.
            # Prefer hit closest below first xref in address space among code hits.
            chosen = None
            if all_hits:
                # Prefer addresses that look like 0x2xxxxx / 0x3xxxxx / 0x1Exxxxx (JASS native region)
                scored = []
                for h in all_hits:
                    score = 0
                    if 0x1E0000 <= h <= 0x220000:  # 1.27 native band
                        score += 3
                    if 0x2B0000 <= h <= 0x3D0000:  # classic native band
                        score += 3
                    if 0x3B0000 <= h <= 0x3D0000:
                        score += 2
                    scored.append((score, h))
                scored.sort(key=lambda t: (-t[0], t[1]))
                chosen = scored[0][1]
            row[name] = hex(chosen) if chosen else None
            row[name + "_cands"] = [hex(h) for h in all_hits[:6]]
            row[name + "_src"] = "xref-decode" if chosen else "missing"
        results.append(row)
        print(ver, "IsTerrainPathable", row.get("IsTerrainPathable"), "GetLocationZ", row.get("GetLocationZ"))

    (OUT / "resolved_natives.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    lines = [
        "| 版本 | IsTerrainPathable | IsLocationVisibleToPlayer | IsUnitVisible | IsUnitFogged | IsUnitMasked | IsUnitDetected | GetLocalPlayer | GetLocationZ | GetDestructableLife | EnumDestructablesInRect |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for r in results:
        cells = [r["ver"]]
        for n in [
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
        ]:
            v = r.get(n)
            cells.append(f"`{v}`" if v else "—")
        lines.append("| " + " | ".join(cells) + " |")
    (OUT / "native_rva_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("updated native_rva_table.md")


if __name__ == "__main__":
    main()
