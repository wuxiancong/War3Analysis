#!/usr/bin/env python3
import struct
from pathlib import Path
from collections import defaultdict

data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()
e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
coff = e_lfanew + 4
nsec = struct.unpack_from("<H", data, coff + 2)[0]
optsz = struct.unpack_from("<H", data, coff + 16)[0]
opt = coff + 20
magic = struct.unpack_from("<H", data, opt)[0]
assert magic == 0x10B
image_base = struct.unpack_from("<I", data, opt + 28)[0]
import_rva, import_size = struct.unpack_from("<II", data, opt + 104)
sec0 = opt + optsz
sections = []
for i in range(nsec):
    off = sec0 + i * 40
    name = data[off : off + 8].split(b"\x00", 1)[0].decode()
    vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
    sections.append((name, va, vsz, raw, rsz))


def rva_to_off(rva):
    for name, va, vsz, raw, rsz in sections:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va), name
    return None, None


def va_to_off(va):
    return rva_to_off(va - image_base)


def off_to_va(off):
    for name, va, vsz, raw, rsz in sections:
        if raw <= off < raw + rsz:
            return image_base + va + (off - raw), name
    return None, None


def read_cstr(rva):
    off, _ = rva_to_off(rva)
    if off is None:
        return None
    end = data.find(b"\x00", off)
    return data[off:end].decode("latin1", "replace")


# parse import descriptors
print("=== imports of interest ===")
off, _ = rva_to_off(import_rva)
iat_map = {}  # iat_va -> name
while True:
    orig, timedate, fwd, name_rva, first_thunk = struct.unpack_from("<IIIII", data, off)
    if orig == 0 and name_rva == 0:
        break
    dll = read_cstr(name_rva)
    thunk_rva = orig or first_thunk
    iat_rva = first_thunk
    i = 0
    while True:
        toff, _ = rva_to_off(thunk_rva + i * 4)
        hint_rva = struct.unpack_from("<I", data, toff)[0]
        if hint_rva == 0:
            break
        iat_va = image_base + iat_rva + i * 4
        if hint_rva & 0x80000000:
            name = f"ord_{hint_rva & 0xFFFF}"
        else:
            noff, _ = rva_to_off(hint_rva)
            name = read_cstr(hint_rva + 2)
        if name in {
            "Sleep",
            "SleepEx",
            "timeGetTime",
            "QueryPerformanceCounter",
            "QueryPerformanceFrequency",
            "timeBeginPeriod",
            "WaitForSingleObject",
            "MsgWaitForMultipleObjects",
            "PeekMessageA",
            "GetTickCount",
            "GetTickCount64",
            "wglSwapBuffers",
            "wglSwapLayerBuffers",
            "SwapBuffers",
            "Direct3DCreate9",
            "DwmFlush",
            "DwmIsCompositionEnabled",
        } or (dll and dll.lower() in ("winmm.dll", "d3d9.dll") and name and "time" in name.lower()):
            print(f"  {dll}!{name} IAT_VA=0x{iat_va:08X} IAT_RVA=0x{iat_rva + i*4:X}")
            iat_map[iat_va] = f"{dll}!{name}"
        if name in ("Sleep", "timeGetTime", "QueryPerformanceCounter", "QueryPerformanceFrequency", "GetTickCount"):
            iat_map[iat_va] = f"{dll}!{name}"
        i += 1
    off += 20

# find CALL/JMP [IAT]
print("\n=== IAT call sites ===")
interesting = {}
# scan all IAT for Sleep/timeGetTime/QPC by name dump of winmm/kernel32 subset
# reparse collecting those
off, _ = rva_to_off(import_rva)
while True:
    orig, timedate, fwd, name_rva, first_thunk = struct.unpack_from("<IIIII", data, off)
    if orig == 0 and name_rva == 0:
        break
    dll = read_cstr(name_rva)
    thunk_rva = orig or first_thunk
    iat_rva = first_thunk
    i = 0
    while True:
        toff, _ = rva_to_off(thunk_rva + i * 4)
        hint_rva = struct.unpack_from("<I", data, toff)[0]
        if hint_rva == 0:
            break
        iat_va = image_base + iat_rva + i * 4
        if hint_rva & 0x80000000:
            name = f"ord_{hint_rva & 0xFFFF}"
        else:
            name = read_cstr(hint_rva + 2)
        if name in (
            "Sleep",
            "timeGetTime",
            "QueryPerformanceCounter",
            "QueryPerformanceFrequency",
            "GetTickCount",
            "timeBeginPeriod",
            "timeEndPeriod",
        ):
            interesting[iat_va] = f"{dll}!{name}"
        i += 1
    off += 20

text = [s for s in sections if s[0] == ".text"][0]
_, tva, _, traw, trsz = text
textb = data[traw : traw + trsz]


def find_all(buf, needle, base=0):
    out = []
    start = 0
    while True:
        i = buf.find(needle, start)
        if i < 0:
            break
        out.append(base + i)
        start = i + 1
    return out


for iat_va, name in interesting.items():
    pat_ff15 = bytes([0xFF, 0x15]) + struct.pack("<I", iat_va)
    pat_ff25 = bytes([0xFF, 0x25]) + struct.pack("<I", iat_va)
    hits = find_all(data, pat_ff15) + find_all(data, pat_ff25)
    print(f"\n{name} IAT=0x{iat_va:08X} hits={len(hits)}")
    for h in hits[:40]:
        va, sec = off_to_va(h)
        print(f"  file=0x{h:X} va=0x{va:08X} sec={sec} ctx={data[h-8:h+10].hex(' ')}")

# dump video settings pointer table
print("\n=== settings pointer table around 0x6F950E00 ===")
toff, _ = va_to_off(0x6F950C00)
blob = data[toff : toff + 0x400]
for i in range(0, len(blob), 4):
    val = struct.unpack_from("<I", blob, i)[0]
    if 0x6F951000 <= val <= 0x6F951800:
        s_off, _ = va_to_off(val)
        s = data[s_off : s_off + 32].split(b"\x00", 1)[0]
        print(f"  table+0x{i:03X} VA=0x{0x6F950C00+i:08X} -> 0x{val:08X} {s!r}")

# xrefs to table region 0x6F950E00
print("\n=== xrefs to 0x6F950Exx table addresses ===")
for va in range(0x6F950C00, 0x6F951000, 4):
    pat = struct.pack("<I", va)
    hits = find_all(data, pat)
    if hits:
        for h in hits[:5]:
            hva, hsec = off_to_va(h)
            if hsec == ".text":
                print(f"  ptr 0x{va:08X} xref va=0x{hva:08X} ctx={data[h-6:h+8].hex(' ')}")

# PresentationInterval constant 0x80000000 in .text near gfx
print("\n=== 0x80000000 immediates in 0x6F0E0000-0x6F100000 ===")
pat = struct.pack("<I", 0x80000000)
for h in find_all(data, pat):
    va, sec = off_to_va(h)
    if va and 0x6F0E0000 <= va <= 0x6F120000:
        print(f"  va=0x{va:08X} ctx={data[h-10:h+8].hex(' ')}")

# FPS format
idx = data.find(b" FPS:")
print("\nFPS fmt file", hex(idx))
va, _ = off_to_va(idx)
print("FPS fmt va", hex(va) if va else None)
# search nearby format start
for delta in range(0, 40):
    pva = va - delta
    pat = struct.pack("<I", pva)
    hits = [h for h in find_all(data, pat) if off_to_va(h)[1] == ".text"]
    if hits:
        print(f"  xref to 0x{pva:08X} (delta {delta}):")
        for h in hits[:8]:
            print(f"    va=0x{off_to_va(h)[0]:08X} ctx={data[h-8:h+8].hex(' ')}")
