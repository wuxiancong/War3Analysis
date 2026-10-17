#!/usr/bin/env python3
from __future__ import annotations

import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
md = Cs(CS_ARCH_X86, CS_MODE_32)


def pe_meta(blob: bytes):
    e_lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
    coff = e_lfanew + 4
    nsec = struct.unpack_from("<H", blob, coff + 2)[0]
    opt = coff + 20
    imagebase = struct.unpack_from("<I", blob, opt + 28)[0]
    opt_size = struct.unpack_from("<H", blob, coff + 16)[0]
    secs = []
    for i in range(nsec):
        o = opt + opt_size + i * 40
        name = blob[o : o + 8].split(b"\x00")[0].decode(errors="replace")
        vsz, va, raw, rsz = struct.unpack_from("<IIII", blob, o + 8)
        secs.append((name, va, raw, vsz, rsz))
    return imagebase, secs


def text(blob, ib, secs):
    for name, va, raw, vsz, rsz in secs:
        if name == ".text":
            return ib + va, raw, rsz, vsz, blob[raw : raw + rsz]
    raise RuntimeError("no text")


def slack(secs):
    for name, va, raw, vsz, rsz in secs:
        extra = rsz - vsz if rsz > vsz else 0
        print(f"    {name:8} VA={va:08X} RAW={raw:08X} VSZ={vsz:08X} RSZ={rsz:08X} extra={extra}")


def scan(path: Path):
    blob = path.read_bytes()
    ib, secs = pe_meta(blob)
    text_va, traw, rsz, vsz, tb = text(blob, ib, secs)
    print("=" * 72, path.parent.name, "text extra", rsz - vsz)

    # SwapEffect DISCARD = 1 at +0x14 (D3D8)
    pat14 = bytes.fromhex("c7461401000000")
    s = 0
    n = 0
    while n < 8:
        i = tb.find(pat14, s)
        if i < 0:
            break
        win = tb[i : i + 80]
        has30 = b"\xC7\x46\x30\x00\x00\x00\x00" in win or b"\xC7\x46\x30\x00\x00\x00\x80" in win
        has1c = b"\xC7\x46\x1C" in win or b"\x89\x46\x1C" in win
        va = text_va + i
        if has30 or has1c:
            print(f"  SwapEffect+14 VA 0x{va:08X} has30={has30} has1c={has1c} {win[:48].hex(' ')}")
            o = traw + i
            for ins in md.disasm(blob[o : o + 90], va):
                print(f"    {ins.address:08X}  {ins.mnemonic:8} {ins.op_str}")
            n += 1
        s = i + 1

    # D3D9 SwapEffect +0x18
    pat18 = bytes.fromhex("c7461801000000")
    s = 0
    n = 0
    while n < 4:
        i = tb.find(pat18, s)
        if i < 0:
            break
        win = tb[i : i + 80]
        has34 = b"\xC7\x46\x34\x00\x00\x00\x00" in win
        if has34:
            va = text_va + i
            print(f"  D3D9 SwapEffect+18/interval VA 0x{va:08X}")
            n += 1
        s = i + 1

    # wglMakeCurrent follow call
    print("  sections:")
    slack(secs)

    # padding at end of .text virtual
    used = min(vsz, rsz)
    tail = tb[used - 16 : used] if used >= 16 else b""
    print(f"  .text tail16 {tail.hex(' ')}")

    # longest mixed pad of CC/90
    best = (0, 0, 0)
    i = 0
    while i < len(tb):
        if tb[i] in (0x90, 0xCC):
            j = i
            while j < len(tb) and tb[j] in (0x90, 0xCC):
                j += 1
            if j - i > best[2]:
                best = (text_va + i, traw + i, j - i)
            i = j
        else:
            i += 1
    print(f"  longest 90/CC run VA 0x{best[0]:08X} off 0x{best[1]:X} len={best[2]}")


def main():
    for d in sorted(ROOT.iterdir()):
        dll = d / "game.dll"
        if dll.exists():
            scan(dll)


if __name__ == "__main__":
    main()
