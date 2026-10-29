#!/usr/bin/env python3
from __future__ import annotations

import struct
from pathlib import Path

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

md = Cs(CS_ARCH_X86, CS_MODE_32)
ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")


def dig(ver: str) -> None:
    g = next(
        f
        for f in (ROOT / ver).iterdir()
        if f.name.lower() == "game.dll"
    )
    pe = pefile.PE(str(g), fast_load=True)
    pe.parse_data_directories([])
    raw = g.read_bytes()
    base = pe.OPTIONAL_HEADER.ImageBase
    foff = raw.find(b"ERROR_ID_BADPASSWORD\x00")
    srva = pe.get_rva_from_offset(foff)
    sva = base + srva
    imm = struct.pack("<I", sva)
    xrefs: list[int] = []
    start = 0
    while True:
        i = raw.find(imm, start)
        if i < 0:
            break
        if i > 0 and raw[i - 1] == 0xB9:
            xr = pe.get_rva_from_offset(i)
            if xr < 0xA00000:
                xrefs.append(xr)
        start = i + 1
    print("====", ver, "xrefs", [hex(x) for x in xrefs])
    account = None
    for xr in xrefs:
        off = pe.get_offset_from_rva(xr)
        if 0xE8 in raw[off + 4 : off + 12]:
            account = xr
            break
    if account is None:
        account = xrefs[0]
    print("account xref", hex(account))
    off = pe.get_offset_from_rva(account)
    func = None
    for back in range(0x2000):
        o = off - back
        if raw[o : o + 3] == b"\x55\x8B\xEC":
            func = pe.get_rva_from_offset(o)
            break
        if (
            raw[o : o + 5] == b"\x8B\xFF\x55\x8B\xEC"
        ):  # hotpatch mov edi,edi; push ebp; mov ebp,esp
            func = pe.get_rva_from_offset(o)
            break
    print("func", hex(func) if func else None)
    start = max(account - 0x18, 0x1000)
    blob = raw[pe.get_offset_from_rva(start) : pe.get_offset_from_rva(start) + 0x60]
    for insn in md.disasm(blob, base + start):
        mark = " <<<" if insn.address == base + account else ""
        print(f"  {insn.address:08X}: {insn.mnemonic:8} {insn.op_str}{mark}")


if __name__ == "__main__":
    for v in [
        "1.20.4.6074",
        "1.22.0.6328",
        "1.23.0.6352",
        "1.24.1.6374",
        "1.24.4.6387",
        "1.25.1.6397",
        "1.26.0.6401",
    ]:
        try:
            dig(v)
        except Exception as exc:  # noqa: BLE001
            print(v, "ERR", exc)
