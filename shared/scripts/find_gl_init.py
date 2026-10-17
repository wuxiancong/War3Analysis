#!/usr/bin/env python3
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()
e = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, e + 6)[0]
optsz = struct.unpack_from("<H", data, e + 20)[0]
opt = e + 24
image_base = struct.unpack_from("<I", data, opt + 28)[0]
dd = opt + 96
imp_rva = struct.unpack_from("<I", data, dd + 8)[0]
sec0 = opt + optsz
sections = []
for i in range(nsec):
    o = sec0 + i * 40
    name = data[o : o + 8].split(b"\0", 1)[0].decode("latin1")
    vsz, va, rsz, raw = struct.unpack_from("<IIII", data, o + 8)
    sections.append((name, va, vsz, raw, rsz))

def rva_to_off(rva):
    for name, va, vsz, raw, rsz in sections:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va), name
    return None, None

def off_to_va(off):
    for name, va, vsz, raw, rsz in sections:
        if raw <= off < raw + max(rsz, 1):
            return image_base + va + (off - raw), name
    return None, None

TEXT_RAW = 0x400
TEXT_VA = 0x6F001000
tb = data[TEXT_RAW : TEXT_RAW + 0x94D000]
md = Cs(CS_ARCH_X86, CS_MODE_32)

wanted = {
    b"wglMakeCurrent",
    b"wglGetProcAddress",
    b"wglSwapLayerBuffers",
    b"glFinish",
    b"ChoosePixelFormat",
    b"SetPixelFormat",
    b"DescribePixelFormat",
}
found = {}
off, _ = rva_to_off(imp_rva)
i = 0
while True:
    orig, timedate, chain, name_rva, fts = struct.unpack_from("<IIIII", data, off + i * 20)
    if orig == 0 and name_rva == 0 and fts == 0:
        break
    thunk_rva = orig if orig else fts
    idx = 0
    while True:
        toff, _ = rva_to_off(thunk_rva + idx * 4)
        thunk = struct.unpack_from("<I", data, toff)[0]
        if thunk == 0:
            break
        if not (thunk & 0x80000000):
            hint_off, _ = rva_to_off(thunk & 0x7FFFFFFF)
            iname = data[hint_off + 2 :].split(b"\0", 1)[0]
            if iname in wanted:
                iat_va = image_base + fts + idx * 4
                found[iname.decode()] = iat_va
                print(f"{iname.decode():24} IAT=0x{iat_va:08X}")
        idx += 1
    i += 1

print("\n=== IAT calls ===")
for name, iat in found.items():
    pat = b"\xff\x15" + struct.pack("<I", iat)
    s = 0
    hits = []
    while True:
        j = tb.find(pat, s)
        if j < 0:
            break
        hits.append(TEXT_VA + j)
        s = j + 1
    print(f"\n{name} n={len(hits)}")
    for va in hits[:12]:
        o = va - TEXT_VA + TEXT_RAW
        print(f"  0x{va:08X}  {data[o-8:o+8].hex(' ')}")

print("\n=== CC padding runs >= 48 in .text near 0x6F0E8000-0x6F0F8000 ===")
lo = 0x6F0E8000 - TEXT_VA + TEXT_RAW
hi = 0x6F0F8000 - TEXT_VA + TEXT_RAW
region = data[lo:hi]
run = 0
start = 0
for i, b in enumerate(region):
    if b == 0xCC:
        if run == 0:
            start = i
        run += 1
    else:
        if run >= 48:
            va = TEXT_VA + (lo - TEXT_RAW) + start
            print(f"  0x{va:08X} len={run}")
        run = 0

print("\n=== disasm wglMakeCurrent sites +/- 40 bytes func-ish ===")
iat = found["wglMakeCurrent"]
pat = b"\xff\x15" + struct.pack("<I", iat)
s = 0
while True:
    j = tb.find(pat, s)
    if j < 0:
        break
    va = TEXT_VA + j
    o = TEXT_RAW + j
    print(f"\n---- call at 0x{va:08X} ----")
    code = data[o - 24 : o + 12]
    for ins in md.disasm(code, va - 24):
        mark = " <<" if ins.address == va else ""
        print(f"  0x{ins.address:08X}  {ins.mnemonic:8} {ins.op_str}{mark}")
    s = j + 1
