#!/usr/bin/env python3
"""Second-pass: D3D8 present-fill, maxfps default, war3.exe 64-cap, padding caves."""
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


def rva_to_off(secs, rva):
    for name, va, raw, vsz, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None


def va_to_off(ib, secs, va):
    return rva_to_off(secs, va - ib)


def off_to_va(ib, secs, fo):
    for name, va, raw, vsz, rsz in secs:
        if raw <= fo < raw + rsz:
            return ib + va + (fo - raw)
    return None


def text(blob, ib, secs):
    for name, va, raw, vsz, rsz in secs:
        if name == ".text":
            return ib + va, raw, blob[raw : raw + rsz]
    raise RuntimeError("no text")


def pad_runs(tb, text_va, byte, min_len=40):
    out = []
    i = 0
    n = len(tb)
    while i < n:
        if tb[i] == byte:
            j = i
            while j < n and tb[j] == byte:
                j += 1
            if j - i >= min_len:
                out.append((text_va + i, j - i))
            i = j
        else:
            i += 1
    out.sort(key=lambda x: -x[1])
    return out


def dis(blob, ib, secs, va, n=80):
    o = va_to_off(ib, secs, va)
    lines = []
    for ins in md.disasm(blob[o : o + n], va):
        lines.append(f"    {ins.address:08X}  {ins.mnemonic:8} {ins.op_str}")
    return "\n".join(lines)


def find_push_imm_then(tb, text_va, imm, follow: bytes, window=120):
    hits = []
    s = 0
    needle = bytes([0x6A, imm])
    while True:
        i = tb.find(needle, s)
        if i < 0:
            break
        win = tb[i : i + window]
        j = win.find(follow)
        if j >= 0:
            hits.append((text_va + i, text_va + i + j))
        s = i + 1
    return hits


def scan_dll(path: Path):
    blob = path.read_bytes()
    ib, secs = pe_meta(blob)
    text_va, traw, tb = text(blob, ib, secs)
    print("=" * 72)
    print(path.parent.name)

    # D3D8: push 0x34 then mov [reg+30h], 0
    print("  D3D8 push 0x34 then C7 ?? 30 00 00 00 00")
    s = 0
    shown = 0
    while True:
        i = tb.find(b"\x6A\x34", s)
        if i < 0:
            break
        win = tb[i : i + 160]
        for modrm in (0x46, 0x43, 0x47, 0x41, 0x45, 0x40):
            pat = bytes([0xC7, modrm, 0x30, 0, 0, 0, 0])
            j = win.find(pat)
            if j >= 0:
                va = text_va + i
                iva = text_va + i + j
                print(f"    memset@0x{va:08X} interval@0x{iva:08X} off=0x{traw + i + j:X}")
                print(dis(blob, ib, secs, va, 96))
                shown += 1
                break
        s = i + 1
        if shown >= 3:
            break

    # D3D9: push 0x38 then C7 ?? 34 00 00 00 00
    print("  D3D9 push 0x38 then C7 ?? 34 00 00 00 00")
    s = 0
    shown = 0
    while True:
        i = tb.find(b"\x6A\x38", s)
        if i < 0:
            break
        win = tb[i : i + 200]
        for modrm in (0x46, 0x43, 0x47, 0x41):
            pat = bytes([0xC7, modrm, 0x34, 0, 0, 0, 0])
            j = win.find(pat)
            if j >= 0:
                va = text_va + i
                iva = text_va + i + j
                print(f"    memset@0x{va:08X} interval@0x{iva:08X} off=0x{traw + i + j:X}")
                print(dis(blob, ib, secs, va, 120))
                shown += 1
                break
        s = i + 1
        if shown >= 2:
            break

    # lockable flags D3D8 +0x28=1 near interval
    print("  D3D8 Flags [r+28h]=1 count", tb.count(bytes.fromhex("c7462801000000")))

    # maxfps xrefs
    idx = blob.find(b"maxfps\x00")
    if idx >= 0:
        sva = off_to_va(ib, secs, idx)
        print(f"  maxfps VA 0x{sva:08X}")
        pat = struct.pack("<I", sva)
        s = 0
        while True:
            i = tb.find(pat, s)
            if i < 0:
                break
            va = text_va + i
            print(f"    xref 0x{va:08X}  {tb[i-12:i+8].hex(' ')}")
            print(dis(blob, ib, secs, va - 32, 80))
            s = i + 1

    cc = pad_runs(tb, text_va, 0xCC, 40)
    nops = pad_runs(tb, text_va, 0x90, 40)
    print("  CC>=40", [(hex(a), n) for a, n in cc[:4]])
    print("  NOP>=40", [(hex(a), n) for a, n in nops[:4]])


def scan_exe(path: Path):
    blob = path.read_bytes()
    ib, secs = pe_meta(blob)
    text_va, traw, tb = text(blob, ib, secs)
    print(f"  war3.exe imagebase=0x{ib:08X} size={len(blob)}")
    # WH 1.20e pattern
    pat = bytes.fromhex("83e0fb53ba110000008bce")
    i = 0
    found = False
    while True:
        j = tb.find(b"\x83\xE0\xFB", i)
        if j < 0:
            break
        win = tb[j : j + 16]
        if b"\xBA\x11\x00\x00\x00" in win or win.startswith(pat):
            va = text_va + j
            print(f"    EXE and~4/edx11 VA 0x{va:08X} off 0x{traw+j:X} {win.hex(' ')}")
            print(dis(blob, ib, secs, va, 40))
            found = True
        i = j + 1
    if not found:
        # broader in whole file
        k = blob.find(pat)
        print(f"    full-file WH pattern: {hex(k) if k>=0 else None}")
        k2 = 0
        n = 0
        while n < 5:
            j = blob.find(b"\xBA\x11\x00\x00\x00", k2)
            if j < 0:
                break
            if blob[j - 4 : j] == b"\x83\xE0\xFB\x53" or blob[j - 5 : j] == b"\x83\xE0\xFB\x6A\x00":
                print("    file", hex(j), blob[j - 8 : j + 8].hex(" "))
            k2 = j + 1
            n += 1


def main():
    for d in sorted(ROOT.iterdir()):
        dll = d / "game.dll"
        if dll.exists():
            scan_dll(dll)
        exe = d / "war3.exe"
        if exe.exists():
            scan_exe(exe)
        else:
            print("  no war3.exe")


if __name__ == "__main__":
    main()
