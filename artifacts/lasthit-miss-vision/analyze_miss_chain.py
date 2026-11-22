#!/usr/bin/env python3
"""Deep-dive ShouldMiss chain + all-version RVA confirmation via setg pattern."""
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


def dump(data, ib, secs, rva, n=0x100):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    o = r2o(secs, rva)
    lines = []
    for insn in md.disasm(data[o : o + n], ib + rva):
        lines.append(f"{insn.address - ib:#x}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic.startswith("ret") and insn.address - ib > rva + 0x8:
            break
    return lines


def find_setg_ret8(data, ib, secs, start_rva, window=0x200):
    """Confirm ShouldMiss ends with setg / mov eax,ecx / ret 8."""
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    o = r2o(secs, start_rva)
    if o is None:
        return False, []
    hits = []
    for insn in md.disasm(data[o : o + window], ib + start_rva):
        if insn.mnemonic == "setg":
            hits.append(f"{insn.address - ib:#x}: {insn.mnemonic} {insn.op_str}")
        if insn.mnemonic == "ret" and "8" in insn.op_str:
            hits.append(f"{insn.address - ib:#x}: {insn.mnemonic} {insn.op_str}")
            break
    ok = any("setg" in h for h in hits) and any("ret" in h for h in hits)
    return ok, hits


def caller_context(data, ib, secs, call_rva, back=0x30, forward=0x40):
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    o = r2o(secs, call_rva - back)
    lines = []
    for insn in md.disasm(data[o : o + back + forward], ib + call_rva - back):
        mark = " <<<" if insn.address - ib == call_rva else ""
        lines.append(f"{insn.address - ib:#x}: {insn.mnemonic} {insn.op_str}{mark}")
    return lines


def main():
    # 1.26 deep: callers + 0x2853d0 + damage multiply path
    ver = "1.26.0.6401"
    data = (VERSIONS / ver / "game.dll").read_bytes()
    ib, secs = pe(data)
    helpers = json.loads((OUT / "should_miss_helpers.json").read_text(encoding="utf-8"))[0]
    callers = [int(x, 16) for x in helpers["callers"]]
    caller_info = {hex(c): caller_context(data, ib, secs, c) for c in callers}

    # disasm 0x2853d0
    d2853d0 = dump(data, ib, secs, 0x2853D0, 0x120)
    # find func containing first caller 0xcf899
    # MissDamageReduction apply: after ShouldMiss at 0x2c402e
    after = caller_context(data, ib, secs, 0x2C402E, back=0x20, forward=0x80)

    # All-version confirm
    rows = []
    for e in TABLE:
        v = e["ver"]
        d = (VERSIONS / v / "game.dll").read_bytes()
        ib2, secs2 = pe(d)
        fs = e["ChanceToMiss"]["funcStart"]
        if not fs:
            rows.append({"ver": v, "ShouldMiss": None, "confirmed_setg": False, "note": "no funcStart"})
            continue
        rva = int(fs, 16)
        ok, hits = find_setg_ret8(d, ib2, secs2, rva)
        # Also find callers count
        ncall = 0
        for va, _vsz, raw, rsz in secs2:
            chunk = d[raw : raw + rsz]
            i = 0
            while True:
                j = chunk.find(b"\xe8", i)
                if j < 0:
                    break
                rel = struct.unpack_from("<i", chunk, j + 1)[0]
                at = va + j
                if at + 5 + rel == rva:
                    ncall += 1
                i = j + 1
        rows.append(
            {
                "ver": v,
                "ShouldMiss": fs,
                "ChanceToMiss_str": e["ChanceToMiss"]["strRVA"],
                "ChanceToMiss_useXref": e["ChanceToMiss"]["useXref"],
                "MissDamageReduction_str": e["MissDamageReduction"]["strRVA"],
                "MissDamageReduction_useXref": e["MissDamageReduction"]["useXref"],
                "confirmed_setg_ret8": ok,
                "setg_hits": hits,
                "caller_count": ncall,
            }
        )
        print(v, "ShouldMiss", fs, "setg", ok, "callers", ncall)

    out = {
        "caller_contexts_1_26": caller_info,
        "fn_2853d0": d2853d0,
        "after_shouldmiss_2c402e": after,
        "all_version": rows,
    }
    (OUT / "miss_chain_analysis.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    lines = [
        "| Version | ShouldMiss (func) | setg+ret8 confirmed | callers | ChanceToMiss str | use xref | MissDamageReduction str | use xref |",
        "| :--- | :--- | :---: | :---: | :--- | :--- | :--- | :--- |",
    ]
    for r in rows:
        conf = "yes" if r["confirmed_setg_ret8"] else "NO / 未确认"
        lines.append(
            f"| {r['ver']} | `{r['ShouldMiss']}` | {conf} | {r['caller_count']} | `{r['ChanceToMiss_str']}` | `{r['ChanceToMiss_useXref']}` | `{r['MissDamageReduction_str']}` | `{r['MissDamageReduction_useXref']}` |"
        )
    (OUT / "should_miss_rva_all_versions.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
