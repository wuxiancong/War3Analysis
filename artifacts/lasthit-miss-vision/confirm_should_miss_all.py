#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-miss-vision")
TABLE = json.loads((OUT / "chance_to_miss_rva_all.json").read_text(encoding="utf-8"))


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


def main():
    rows = []
    for e in TABLE:
        v = e["ver"]
        d = (VERSIONS / v / "game.dll").read_bytes()
        ib, secs = pe(d)
        fs = e["ChanceToMiss"]["funcStart"]
        if not fs:
            rows.append({"ver": v, "ShouldMiss": None, "has_setg": False})
            continue
        rva = int(fs, 16)
        o = r2o(secs, rva)
        md = Cs(CS_ARCH_X86, CS_MODE_32)
        has_setg = False
        setg_at = None
        for insn in md.disasm(d[o : o + 0x220], ib + rva):
            if insn.mnemonic == "setg":
                has_setg = True
                setg_at = hex(insn.address - ib)
        caller_list = []
        for va, _vsz, raw, rsz in secs:
            chunk = d[raw : raw + rsz]
            i = 0
            while True:
                j = chunk.find(b"\xe8", i)
                if j < 0:
                    break
                rel = struct.unpack_from("<i", chunk, j + 1)[0]
                at = va + j
                if at + 5 + rel == rva:
                    caller_list.append(hex(at))
                i = j + 1
        rows.append(
            {
                "ver": v,
                "ShouldMiss": fs,
                "has_setg": has_setg,
                "setg_at": setg_at,
                "callers": caller_list,
                "ChanceToMiss_str": e["ChanceToMiss"]["strRVA"],
                "ChanceToMiss_use": e["ChanceToMiss"]["useXref"],
                "MDR_str": e["MissDamageReduction"]["strRVA"],
                "MDR_use": e["MissDamageReduction"]["useXref"],
            }
        )
        print(v, fs, "setg", has_setg, setg_at, "ncall", len(caller_list))

    (OUT / "should_miss_rva_confirmed.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = [
        "| Version | ShouldMiss | setg confirmed | setg RVA | callers | ChanceToMiss str | use | MDR str | use |",
        "| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for r in rows:
        conf = "yes" if r["has_setg"] else "未确认"
        callers = ", ".join(f"`{c}`" for c in r["callers"]) if r["callers"] else "未确认"
        lines.append(
            f"| {r['ver']} | `{r['ShouldMiss']}` | {conf} | `{r['setg_at']}` | {callers} "
            f"| `{r['ChanceToMiss_str']}` | `{r['ChanceToMiss_use']}` | `{r['MDR_str']}` | `{r['MDR_use']}` |"
        )
    (OUT / "should_miss_rva_all_versions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
