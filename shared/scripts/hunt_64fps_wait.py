#!/usr/bin/env python3
"""Hunt 1.27 Game.dll software 64-FPS wait / maxfps readers / Sleep+tick loops."""
from __future__ import annotations

import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

SAMPLE = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll")
SAMPLE_126 = Path(r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll")
IMAGE_BASE = 0x6F000000
TEXT_VA = 0x6F001000
TEXT_RAW = 0x400
TEXT_SIZE = 0x94D000

data = SAMPLE.read_bytes()
tb = data[TEXT_RAW : TEXT_RAW + TEXT_SIZE]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = False


def pe_sections(blob: bytes):
    e_lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
    coff = e_lfanew + 4
    nsec = struct.unpack_from("<H", blob, coff + 2)[0]
    opt = coff + 20
    opt_size = struct.unpack_from("<H", blob, coff + 16)[0]
    imagebase = struct.unpack_from("<I", blob, opt + 28)[0]
    sec_off = opt + opt_size
    secs = []
    for i in range(nsec):
        o = sec_off + i * 40
        name = blob[o : o + 8].split(b"\x00")[0].decode()
        vsz, va, rsz, raw = struct.unpack_from("<IIII", blob, o + 8)
        secs.append((name, va, raw, vsz, rsz, imagebase))
    return secs


def file_to_va(blob: bytes, fo: int) -> int | None:
    for name, va, raw, vsz, rsz, imagebase in pe_sections(blob):
        if raw <= fo < raw + rsz:
            return imagebase + va + (fo - raw)
    return None


def va_to_off(va: int) -> int:
    return va - TEXT_VA + TEXT_RAW


def dis(va: int, n: int = 96) -> None:
    o = va_to_off(va)
    print(f"\n==== 0x{va:08X} ====")
    for ins in md.disasm(data[o : o + n], va):
        print(f"  0x{ins.address:08X}  {ins.mnemonic:8} {ins.op_str}")


def find_all(hay: bytes, needle: bytes, base_va: int) -> list[int]:
    out = []
    s = 0
    while True:
        i = hay.find(needle, s)
        if i < 0:
            break
        out.append(base_va + i)
        s = i + 1
    return out


def find_calls(target: int) -> list[int]:
    hits = []
    s = 0
    while True:
        i = tb.find(b"\xE8", s)
        if i < 0 or i + 5 > len(tb):
            break
        rel = struct.unpack_from("<i", tb, i + 1)[0]
        dest = TEXT_VA + i + 5 + rel
        if dest == target:
            hits.append(TEXT_VA + i)
        s = i + 1
    return hits


def find_iat_calls(iat_va: int) -> list[int]:
    """FF 15 <iat>"""
    return find_all(tb, b"\xFF\x15" + struct.pack("<I", iat_va), TEXT_VA)


def parse_imports(blob: bytes) -> dict[str, dict[str, int]]:
    """name -> {func: iat_va} using PE import dir. Returns IAT VAs (imagebase+rva of thunk)."""
    e_lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
    opt = e_lfanew + 24
    magic = struct.unpack_from("<H", blob, opt)[0]
    if magic != 0x10B:
        return {}
    dd = opt + 96
    imp_rva, imp_sz = struct.unpack_from("<II", blob, dd + 8)
    secs = pe_sections(blob)
    imagebase = secs[0][5]

    def rva_to_off(rva: int) -> int | None:
        for name, va, raw, vsz, rsz, ib in secs:
            if va <= rva < va + max(vsz, rsz):
                return raw + (rva - va)
        return None

    out: dict[str, dict[str, int]] = {}
    off = rva_to_off(imp_rva)
    if off is None:
        return out
    while True:
        ilt, _, _, name_rva, iat_rva = struct.unpack_from("<IIIII", blob, off)
        if ilt == 0 and name_rva == 0 and iat_rva == 0:
            break
        no = rva_to_off(name_rva)
        dll = blob[no:].split(b"\x00")[0].decode(errors="replace") if no else "?"
        thunk_rva = ilt or iat_rva
        funcs = {}
        idx = 0
        while True:
            to = rva_to_off(thunk_rva + idx * 4)
            if to is None:
                break
            thunk = struct.unpack_from("<I", blob, to)[0]
            if thunk == 0:
                break
            if thunk & 0x80000000:
                nm = f"ord_{thunk & 0xFFFF}"
            else:
                ho = rva_to_off(thunk + 2)
                nm = blob[ho:].split(b"\x00")[0].decode(errors="replace") if ho else "?"
            funcs[nm] = imagebase + iat_rva + idx * 4
            idx += 1
        out[dll.lower()] = funcs
        off += 20
    return out


print("=== imports of interest ===")
imps = parse_imports(data)
want = [
    "Sleep",
    "GetTickCount",
    "timeGetTime",
    "QueryPerformanceCounter",
    "QueryPerformanceFrequency",
    "WaitForSingleObject",
    "MsgWaitForMultipleObjects",
    "PeekMessageA",
    "PeekMessageW",
    "timeBeginPeriod",
]
for dll, funcs in imps.items():
    for n, va in funcs.items():
        if n in want:
            sites = find_iat_calls(va)
            print(f"{dll}!{n:28} IAT=0x{va:08X}  calls={len(sites)}")
            if n in ("Sleep", "GetTickCount", "timeGetTime") and len(sites) <= 80:
                for s in sites:
                    print(f"    call 0x{s:08X}")

print("\n=== push 0x16 (maxfps slot) in .text ===")
for va in find_all(tb, b"\x6A\x16", TEXT_VA)[:80]:
    o = va_to_off(va)
    print(f"  0x{va:08X}  {data[o:o+16].hex(' ')}")

print("\n=== mov reg, 0x16 imm32 ===")
for prefix, name in [
    (b"\xB8\x16\x00\x00\x00", "eax"),
    (b"\xB9\x16\x00\x00\x00", "ecx"),
    (b"\xBA\x16\x00\x00\x00", "edx"),
    (b"\xBB\x16\x00\x00\x00", "ebx"),
    (b"\xBE\x16\x00\x00\x00", "esi"),
    (b"\xBF\x16\x00\x00\x00", "edi"),
]:
    hits = find_all(tb, prefix, TEXT_VA)
    print(name, len(hits), [hex(x) for x in hits[:12]])

print("\n=== 0.015625f (1/64) imm in .text ===")
for va in find_all(tb, struct.pack("<I", 0x3C800000), TEXT_VA):
    o = va_to_off(va)
    print(f"  0x{va:08X}  pre={data[o-8:o].hex(' ')}  post={data[o:o+8].hex(' ')}")

print("\n=== 15.625f ===")
for va in find_all(tb, struct.pack("<I", 0x417A0000), TEXT_VA):
    print(" ", hex(va))

print("\n=== 0.015625 double ===")
# 0.015625 = 0x3F90000000000000
pat = struct.pack("<Q", 0x3F90000000000000)
print("count", tb.count(pat), [hex(x) for x in find_all(tb, pat, TEXT_VA)[:10]])

# FUN_6f023310 switch: key 0x16 -> eax-5 = 0x11
print("\n=== apply switch table for key 0x16 ===")
# table byte at 0x6f0238bc + 0x11
tbl_va = 0x6F0238BC
idx = 0x11
selector = data[va_to_off(tbl_va + idx)]
print("selector byte", selector)
jt_va = 0x6F023844
case_va = struct.unpack_from("<I", data, va_to_off(jt_va + selector * 4))[0]
print("case va", hex(case_va))
dis(case_va, 80)

# cmp eax, 0x40 (64)
print("\n=== cmp eax, 0x40 (first 40) ===")
hits = find_all(tb, b"\x83\xF8\x40", TEXT_VA)
print("count", len(hits))
for va in hits[:25]:
    print(" ", hex(va))

print("\n=== Sleep(1)/Sleep(0) then nearby GetTickCount-like cmp 0xF ===")
