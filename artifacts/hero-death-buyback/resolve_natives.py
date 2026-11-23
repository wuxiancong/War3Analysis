#!/usr/bin/env python3
"""Resolve native handler RVAs for UnitAlive / Timer* / ReviveHero across all versions."""
from __future__ import annotations

import json
import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

VERSIONS = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\hero-death-buyback")
NAMES = [
    b"UnitAlive\x00",
    b"IsUnitDeadBJ\x00",
    b"IsUnitAliveBJ\x00",
    b"TimerGetRemaining\x00",
    b"TimerGetElapsed\x00",
    b"ReviveHero\x00",
    b"GetWidgetLife\x00",
]


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


def o2r(secs, o):
    for va, _vsz, raw, rsz in secs:
        if raw <= o < raw + rsz:
            return va + (o - raw)
    return None


def r2o(secs, r):
    for va, vsz, raw, rsz in secs:
        if va <= r < va + max(vsz, rsz):
            return raw + (r - va)
    return None


def findall(d, n):
    out = []
    i = 0
    while True:
        j = d.find(n, i)
        if j < 0:
            break
        out.append(j)
        i = j + 1
    return out


def resolve_handler(data, ib, secs, str_off):
    """Find mov edx, abs(str) then nearby mov ecx, handler / push handler pattern."""
    sr = o2r(secs, str_off)
    if sr is None:
        return None
    absva = ib + sr
    pat = struct.pack("<I", absva)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    for o in findall(data, pat):
        r = o2r(secs, o)
        if r is None:
            continue
        # look back 32 bytes for mov edx/ecx of this imm, and nearby call
        start = max(0, o - 0x40)
        code = data[start : o + 0x30]
        base = ib + (o2r(secs, start) or 0)
        handler = None
        for insn in md.disasm(code, base):
            # mov edx, imm32 OR mov ecx, imm32 where imm is near code
            if insn.mnemonic == "mov" and "0x" in insn.op_str:
                parts = insn.op_str.split(",")
                if len(parts) == 2 and parts[0].strip() in ("edx", "ecx"):
                    try:
                        imm = int(parts[1].strip(), 16)
                    except ValueError:
                        continue
                    if imm == absva:
                        continue
                    # if it's a code RVA+ib in .text
                    if ib < imm < ib + 0xA00000:
                        cand = imm - ib
                        # prefer as handler if previous was edx=string
                        if parts[0].strip() == "ecx":
                            handler = cand
            if insn.mnemonic == "push":
                try:
                    imm = int(insn.op_str, 16)
                    if ib < imm < ib + 0xA00000 and abs(insn.address - (ib + r)) < 0x20:
                        # sometimes handler pushed
                        pass
                except ValueError:
                    pass
        if handler:
            return handler
        # fallback: look at bytes before xref for BA xx (mov edx) and B9 xx (mov ecx)
        # Classic: mov ecx, handler; mov edx, name; push sig; call
        # xref is to name string inside mov edx
        # scan back for B9
        back = data[max(0, o - 0x20) : o]
        for i in range(len(back) - 5, -1, -1):
            if back[i] == 0xB9:  # mov ecx, imm32
                imm = struct.unpack_from("<I", back, i + 1)[0]
                if ib < imm < ib + 0xA00000:
                    return imm - ib
            if back[i] == 0xBA and i + 5 <= len(back):
                imm = struct.unpack_from("<I", back, i + 1)[0]
                if imm == absva:
                    # found mov edx,str — search further back for B9
                    for j in range(i - 1, max(-1, i - 0x18), -1):
                        if j >= 0 and back[j] == 0xB9:
                            himm = struct.unpack_from("<I", back, j + 1)[0]
                            if ib < himm < ib + 0xA00000:
                                return himm - ib
    return None


def main():
    rows = []
    for vd in sorted(VERSIONS.iterdir()):
        dll = vd / "game.dll"
        if not dll.exists():
            continue
        data = dll.read_bytes()
        info = pe(data)
        if not info:
            continue
        ib, secs = info
        entry = {"ver": vd.name}
        for key in NAMES:
            name = key[:-1].decode()
            offs = findall(data, key)
            if not offs:
                entry[name] = {"strRVA": None, "handler": None}
                continue
            sr = o2r(secs, offs[0])
            h = resolve_handler(data, ib, secs, offs[0])
            entry[name] = {"strRVA": hex(sr) if sr is not None else None, "handler": hex(h) if h else "未确认"}
        rows.append(entry)
        print(vd.name, {k: entry[k]["handler"] for k in entry if k != "ver"})

    (OUT / "native_handlers.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = [
        "| Version | UnitAlive | IsUnitDeadBJ | TimerGetRemaining | TimerGetElapsed | ReviveHero | GetWidgetLife |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for e in rows:
        def h(n):
            return e.get(n, {}).get("handler") or "未确认"

        lines.append(
            f"| {e['ver']} | `{h('UnitAlive')}` | `{h('IsUnitDeadBJ')}` | `{h('TimerGetRemaining')}` | `{h('TimerGetElapsed')}` | `{h('ReviveHero')}` | `{h('GetWidgetLife')}` |"
        )
    (OUT / "native_rva_table.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
