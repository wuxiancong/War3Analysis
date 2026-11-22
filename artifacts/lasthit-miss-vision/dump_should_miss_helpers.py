#!/usr/bin/env python3
from __future__ import annotations

import json
import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-miss-vision")
OUT.mkdir(parents=True, exist_ok=True)


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


def dump_ver(ver: str, should_miss_rva: int, focus_helpers: dict[str, int]):
    data = (VERSIONS / ver / "game.dll").read_bytes()
    ib, secs = pe(data)
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    def cstr(abs_a: int):
        o = r2o(secs, abs_a - ib)
        if o is None:
            return None
        return data[o : data.find(b"\x00", o)].decode("ascii", "replace")

    def dump(rva: int, n: int = 0x140):
        o = r2o(secs, rva)
        lines = []
        for insn in md.disasm(data[o : o + n], ib + rva):
            lines.append(f"{insn.address - ib:#x}: {insn.mnemonic} {insn.op_str}")
            if insn.mnemonic.startswith("ret") and insn.address - ib > rva + 0x10:
                break
        return lines

    # strings near ChanceToMiss for this build (resolve via str xrefs already known for 1.26)
    strings = {}
    for key in (b"ChanceToMiss\x00", b"MissDamageReduction\x00", b"miss\x00", b"Miss\x00"):
        o = data.find(key)
        if o >= 0:
            # keep short ascii name
            strings[key[:-1].decode()] = hex(o2r := (lambda oo: next((va + (oo - raw) for va, vsz, raw, rsz in secs if raw <= oo < raw + rsz), None))(o))

    callers = []
    for va, _vsz, raw, rsz in secs:
        chunk = data[raw : raw + rsz]
        i = 0
        while True:
            j = chunk.find(b"\xe8", i)
            if j < 0:
                break
            rel = struct.unpack_from("<i", chunk, j + 1)[0]
            at = va + j
            if at + 5 + rel == should_miss_rva:
                callers.append(hex(at))
            i = j + 1

    helpers = {name: dump(rva) for name, rva in focus_helpers.items()}
    helpers["ShouldMiss"] = dump(should_miss_rva, 0x200)

    # Resolve absolute string pointers used inside ShouldMiss for 1.26-style builds
    sm = helpers["ShouldMiss"]
    abs_strs = []
    for line in sm:
        if "push 0x6f" in line or "mov edx, 0x6f" in line or "mov ecx, 0x6f" in line:
            # extract imm
            for tok in line.replace(",", " ").split():
                if tok.startswith("0x6f") or tok.startswith("0x6F"):
                    try:
                        abs_strs.append((tok, cstr(int(tok, 16))))
                    except Exception:
                        pass
    return {
        "ver": ver,
        "ib": hex(ib),
        "ShouldMiss": hex(should_miss_rva),
        "callers": callers,
        "string_rvas": strings,
        "abs_strings_in_ShouldMiss": abs_strs,
        "helpers": helpers,
    }


def main():
    # Known ShouldMiss RVAs from earlier table (funcStart of ChanceToMiss use)
    focus = {
        "1.26.0.6401": {
            "should": 0x2BEAC0,
            "helpers": {
                "roll_01fd80": 0x01FD80,
                "cmp_0128c0": 0x0128C0,
                "h_0d8df0": 0x0D8DF0,
                "h_0d8dc0": 0x0D8DC0,
                "exempt_0c7de0": 0x0C7DE0,
                "pos_4743a0": 0x4743A0,
                "deref_6eec20": 0x6EEC20,
                "pre_2bea20": 0x2BEA20,
                "pre_2bb960": 0x2BB960,
                "ui_miss_2bb970": 0x2BB970,
            },
        },
        "1.27.0.52240": {
            "should": 0x6B7160,
            "helpers": {},  # fill after pattern match
        },
    }

    results = []
    for ver, cfg in focus.items():
        if ver == "1.27.0.52240":
            # Pattern-scan: find ChanceToMiss push then back to function start already known
            data = (VERSIONS / ver / "game.dll").read_bytes()
            ib, secs = pe(data)
            # Reuse helpers relative by matching unique insn sequence from 1.26 end of ShouldMiss:
            # cmp eax,esi; setg cl; ... ret 8
            # For now dump ShouldMiss only and resolve calls inside
            md = Cs(CS_ARCH_X86, CS_MODE_32)
            rva = cfg["should"]
            o = r2o(secs, rva)
            calls = []
            for insn in md.disasm(data[o : o + 0x200], ib + rva):
                if insn.mnemonic == "call":
                    calls.append(f"{insn.address - ib:#x}: {insn.op_str}")
                if insn.mnemonic.startswith("ret") and insn.address - ib > rva + 0x80:
                    break
            # map call targets as helpers by order similar to 1.26
            cfg["helpers"] = {"ShouldMiss_calls": 0}  # placeholder
            info = dump_ver(ver, rva, {})
            info["call_sites_inside"] = calls
            results.append(info)
        else:
            results.append(dump_ver(ver, cfg["should"], cfg["helpers"]))

    (OUT / "should_miss_helpers.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    # short summary
    for r in results:
        print(r["ver"], "callers", len(r["callers"]), r["callers"][:8])
        print("  abs_strs", r.get("abs_strings_in_ShouldMiss", [])[:8])
        if "roll_01fd80" in r.get("helpers", {}):
            print("  roll", r["helpers"]["roll_01fd80"][:12])
            print("  cmp", r["helpers"]["cmp_0128c0"][:8])
            print("  h1", r["helpers"]["h_0d8df0"][:12])
            print("  exempt", r["helpers"]["exempt_0c7de0"][:10])


if __name__ == "__main__":
    main()
