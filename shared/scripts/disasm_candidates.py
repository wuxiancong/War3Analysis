#!/usr/bin/env python3
import struct
from pathlib import Path

data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()
e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
opt = e_lfanew + 24
image_base = struct.unpack_from("<I", data, opt + 28)[0]
nsec = struct.unpack_from("<H", data, e_lfanew + 6)[0]
optsz = struct.unpack_from("<H", data, e_lfanew + 20)[0]
sec0 = opt + optsz
sections = []
for i in range(nsec):
    off = sec0 + i * 40
    name = data[off : off + 8].split(b"\x00", 1)[0].decode()
    vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
    sections.append((name, va, vsz, raw, rsz))


def va_to_off(va):
    rva = va - image_base
    for name, sva, vsz, raw, rsz in sections:
        if sva <= rva < sva + max(vsz, rsz):
            return raw + (rva - sva)
    return None


def off_to_va(off):
    for name, va, vsz, raw, rsz in sections:
        if raw <= off < raw + rsz:
            return image_base + va + (off - raw)
    return None


def find_all(buf, needle):
    out = []
    i = 0
    while True:
        j = buf.find(needle, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def func_start(va, back=0x200):
    off = va_to_off(va)
    start = max(0, off - back)
    chunk = data[start:off]
    # look for 0xCC run then typical prologue
    for rel in range(len(chunk) - 3, -1, -1):
        if chunk[rel : rel + 3] in (b"\xcc\xcc\xcc", b"\xc3\xcc\xcc", b"\xc2\x04\x00"):
            # next non-int3
            k = rel
            while k < len(chunk) and chunk[k] in (0xCC,):
                k += 1
            if k < len(chunk):
                cand = start + k
                if data[cand] in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0x81, 0xA1, 0x6A, 0x68, 0x51, 0x52):
                    return off_to_va(cand)
    return None


try:
    from capstone import Cs, CS_ARCH_X86, CS_MODE_32
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = False
except Exception as e:
    print("no capstone", e)
    md = None


def disasm(va, n=80):
    off = va_to_off(va)
    blob = data[off : off + n * 8]
    print(f"\n---- DISASM 0x{va:08X} ----")
    if md is None:
        print(blob[:64].hex(" "))
        return
    c = 0
    for insn in md.disasm(blob, va):
        print(f"  0x{insn.address:08X}  {insn.mnemonic:8} {insn.op_str}")
        c += 1
        if c >= n:
            break


# timeGetTime thunk uses
thunk = 0x6F02C31A
print("timeGetTime thunk bytes", data[va_to_off(thunk) - 8 : va_to_off(thunk) + 8].hex(" "))
# E8 rel to thunk
# find FF 15 04 E9 94 6F already found as thunk itself
# find CALL thunk: E8 rel32 where next+rel = thunk
text = [s for s in sections if s[0] == ".text"][0]
_, tva, _, traw, trsz = text
calls = []
tb = data[traw : traw + trsz]
i = 0
target = thunk
while True:
    j = tb.find(b"\xe8", i)
    if j < 0:
        break
    rel = struct.unpack_from("<i", tb, j + 1)[0]
    src = image_base + tva + j
    dest = src + 5 + rel
    if dest == target:
        calls.append(src)
    i = j + 1
print("calls to timeGetTime thunk", len(calls), [hex(x) for x in calls[:30]])

# also CALL 0x6F02C31A via jmp table? already have thunk

for va in [
    0x6F154C60,
    0x6F154C7F,
    0x6F154D00,
    0x6F155050,
    0x6F161C00,
    0x6F35D2D0,
    0x6F35C680,
    0x6F023E00,
    0x6F0EC520,
    0x6F0F2680,
    0x6F3B0C20,
]:
    fs = func_start(va)
    print(f"near 0x{va:08X} guessed func_start={hex(fs) if fs else None}")

disasm(0x6F154C50, 70)
disasm(0x6F154D00, 40)
disasm(0x6F155060, 50)
disasm(0x6F161BE0, 80)
disasm(0x6F35D2D0, 50)
disasm(0x6F35C680, 40)
disasm(0x6F0EC520, 60)

# find CALL [IAT Sleep] function starts
print("\nSleep call function starts:")
for va in [0x6F154C99, 0x6F15508D, 0x6F155861, 0x6F162BCD, 0x6F1648B2, 0x6F1660C6, 0x6F167233]:
    print(hex(va), "->", hex(func_start(va) or 0))
