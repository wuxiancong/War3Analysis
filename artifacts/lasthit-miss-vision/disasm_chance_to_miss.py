#!/usr/bin/env python3
"""Disassemble ChanceToMiss use sites; find function starts and cliff-related calls."""
from __future__ import annotations

import json
import struct
from pathlib import Path

try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
except ImportError:
    Cs = None

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-miss-vision")
XREFS = json.loads((OUT / "chance_to_miss_xrefs.json").read_text(encoding="utf-8"))

# Prefer later xref as "use" (post-1.22 has load+use)
FOCUS = {
    "1.26.0.6401": {"ChanceToMiss": 0x2BEB2A, "MissDamageReduction": 0x2C44BA},
    "1.27.0.52240": {"ChanceToMiss": 0x6B71D3, "MissDamageReduction": 0x6B63D5},
    "1.24.4.6387": {"ChanceToMiss": 0x2BF64A, "MissDamageReduction": 0x2C4FDA},
    "1.22.0.6328": {"ChanceToMiss": 0x2BDF8A, "MissDamageReduction": 0x2C391A},
    "1.21.0.6263": {"ChanceToMiss": 0x1F769E, "MissDamageReduction": 0x1F7A1D},
}


def pe(data: bytes):
    e = struct.unpack_from("<I", data, 0x3C)[0]
    opt = e + 24
    ib = struct.unpack_from("<I", data, opt + 28)[0]
    coff = e + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsz = struct.unpack_from("<H", data, coff + 16)[0]
    sec0 = coff + 20 + optsz
    secs = []
    for i in range(nsec):
        off = sec0 + i * 40
        vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
        secs.append((va, vsz, raw, rsz))
    return ib, secs


def r2o(secs, r):
    for va, vsz, raw, rsz in secs:
        if va <= r < va + max(vsz, rsz):
            return raw + (r - va)
    return None


def o2r(secs, o):
    for va, _vsz, raw, rsz in secs:
        if raw <= o < raw + rsz:
            return va + (o - raw)
    return None


def find_func_start(data, secs, rva, back=0x400):
    off = r2o(secs, rva)
    if off is None:
        return None
    start = max(0, off - back)
    for i in range(off - start - 1, -1, -1):
        if data[start + i] in (0xCC, 0xC3):
            cand = start + i + 1
            if cand > off:
                continue
            nb = data[cand : cand + 3]
            if nb[:1] in (b"\x55", b"\x53", b"\x56", b"\x57", b"\x8B", b"\x83", b"\x6A") or nb[:2] == b"\x8B\xff":
                return o2r(secs, cand)
    return rva


def main():
    md = Cs(CS_ARCH_X86, CS_MODE_32) if Cs else None
    report = []
    for ver, keys in FOCUS.items():
        data = (VERSIONS / ver / "game.dll").read_bytes()
        ib, secs = pe(data)
        entry = {"ver": ver}
        for name, xr in keys.items():
            fs = find_func_start(data, secs, xr)
            entry[name] = {"xref": hex(xr), "funcStart": hex(fs) if fs else None}
            if md and fs is not None:
                off = r2o(secs, fs)
                code = data[off : off + 0x180]
                lines = []
                for insn in md.disasm(code, ib + fs):
                    lines.append(f"  {insn.address - ib:#x}: {insn.mnemonic} {insn.op_str}")
                    if insn.address - ib > fs + 0x120:
                        break
                entry[name]["disasm"] = lines
                # look for float 0.25 / 0.5 loads in function window
                win = data[off : off + 0x200]
                f25 = struct.pack("<f", 0.25)
                f50 = struct.pack("<f", 0.5)
                entry[name]["has_float_0_25"] = f25 in win
                entry[name]["has_float_0_5"] = f50 in win
            print(ver, name, "func", entry[name]["funcStart"], "f0.25", entry[name].get("has_float_0_25"))
        report.append(entry)

    # Full version table: str + preferred use xref (last) + guessed func start
    table = []
    for e in XREFS:
        ver = e["ver"]
        data = (VERSIONS / ver / "game.dll").read_bytes()
        ib, secs = pe(data)
        row = {"ver": ver}
        for name in ("ChanceToMiss", "MissDamageReduction"):
            info = e[name]
            xrefs = [int(x, 16) for x in info["xrefs"]]
            use = xrefs[-1] if xrefs else None
            fs = find_func_start(data, secs, use) if use is not None else None
            row[name] = {
                "strRVA": info["strRVA"],
                "xrefs": info["xrefs"],
                "useXref": hex(use) if use is not None else None,
                "funcStart": hex(fs) if fs else None,
            }
        table.append(row)
        print("table", ver, "CTM", row["ChanceToMiss"]["funcStart"], "MDR", row["MissDamageReduction"]["funcStart"])

    (OUT / "chance_to_miss_disasm.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (OUT / "chance_to_miss_rva_all.json").write_text(json.dumps(table, indent=2), encoding="utf-8")

    lines = [
        "| Version | ChanceToMiss str | use xref | funcStart (guess) | MissDamageReduction str | use xref | funcStart (guess) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for row in table:
        c = row["ChanceToMiss"]
        m = row["MissDamageReduction"]
        lines.append(
            f"| {row['ver']} | `{c['strRVA']}` | `{c['useXref']}` | `{c['funcStart']}` | `{m['strRVA']}` | `{m['useXref']}` | `{m['funcStart']}` |"
        )
    (OUT / "chance_to_miss_rva_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote tables")


if __name__ == "__main__":
    main()
