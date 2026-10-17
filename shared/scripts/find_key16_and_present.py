#!/usr/bin/env python3
import struct
from pathlib import Path

data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()
TEXT_RAW = 0x400
TEXT_VA = 0x6F001000
TEXT_RSZ = 0x94D000
tb = data[TEXT_RAW:TEXT_RAW+TEXT_RSZ]

def off_to_va(off):
    return TEXT_VA + (off - TEXT_RAW)

def findall(buf, pat, base=0):
    out=[]; s=0
    while True:
        i=buf.find(pat,s)
        if i<0: break
        out.append(base+i); s=i+1
    return out

print("=== push 0x16 (6A 16) in .text ===")
hits=findall(tb, b"\x6A\x16", TEXT_RAW)
print("count", len(hits))
for h in hits:
    va=off_to_va(h)
    print(f"  0x{va:08X}  {data[h-6:h+18].hex(' ')}")

print("\n=== mov r32, 0x16 ===")
for op in range(0xB8, 0xC0):
    pat=bytes([op, 0x16,0,0,0])
    hs=findall(tb, pat, TEXT_RAW)
    for h in hs[:20]:
        print(f"  {op:02X} 0x{off_to_va(h):08X} {data[h-4:h+12].hex(' ')}")

print("\n=== cmp [mem], 0x16  (83 3D xx xx xx xx 16) ===")
# too many 83 3D; filter imm=16
s=0; n=0
while n<30:
    i=tb.find(b"\x83\x3D", s)
    if i<0: break
    if i+6 < len(tb) and tb[i+6]==0x16:
        h=TEXT_RAW+i
        print(f"  0x{off_to_va(h):08X} {data[h:h+12].hex(' ')}")
        n+=1
    s=i+1

print("\n=== D3DPRESENT_INTERVAL_IMMEDIATE 0x80000000 in CGx range 0x6F0E0000-0x6F0F8000 ===")
lo=0x6F0E0000; hi=0x6F0F8000
lo_off=lo-TEXT_VA+TEXT_RAW; hi_off=hi-TEXT_VA+TEXT_RAW
region=data[lo_off:hi_off]
pat=struct.pack("<I", 0x80000000)
s=0; n=0
while True:
    i=region.find(pat,s)
    if i<0: break
    h=lo_off+i
    prev=data[h-3:h+4]
    print(f"  0x{off_to_va(h):08X} ctx={data[h-8:h+8].hex(' ')}")
    n+=1; s=i+1
print("count", n)

print("\n=== mov [r+0x34], imm  (C7 4x 34 / C7 80 34 00 00 00) in CGx range ===")
for pat in [b"\xC7\x40\x34", b"\xC7\x41\x34", b"\xC7\x42\x34", b"\xC7\x43\x34",
            b"\xC7\x45\x34", b"\xC7\x46\x34", b"\xC7\x47\x34",
            b"\xC7\x80\x34\x00\x00\x00", b"\xC7\x81\x34\x00\x00\x00",
            b"\xC7\x82\x34\x00\x00\x00", b"\xC7\x83\x34\x00\x00\x00",
            b"\xC7\x86\x34\x00\x00\x00", b"\xC7\x87\x34\x00\x00\x00"]:
    hs=findall(region, pat, lo_off)
    for h in hs:
        print(f"  {pat.hex()} 0x{off_to_va(h):08X} {data[h:h+12].hex(' ')}")

print("\n=== xrefs to video table / lockfb table base ===")
for va in [0x6F950DC0,0x6F950DC8,0x6F950DD0,0x6F950E00,0x6F950E90,0x6F950E98,
           0x6F950F28, 0x6F95135C, 0x6FBDABE8, 0x6FBDABEC]:
    pat=struct.pack("<I", va)
    hs=findall(data, pat)
    print(f"VA 0x{va:08X} hits={len(hs)}")
    for h in hs[:8]:
        fva = None
        if TEXT_RAW <= h < TEXT_RAW+TEXT_RSZ:
            fva=off_to_va(h)
            loc='.text'
        else:
            loc='other'
            fva=h
        print(f"  file=0x{h:X} {loc} va_or_file=0x{fva:X} ctx={data[h-6:h+10].hex(' ')}")

print("\n=== wglSwapLayerBuffers function xrefs (calls to 0x6F0F0CC0) ===")
# E8 rel32 to 0x6F0F0CC0
target=0x6F0F0CC0
# scan E8
s=0; n=0
while n<20:
    i=tb.find(b"\xE8", s)
    if i<0: break
    if i+5<=len(tb):
        rel=struct.unpack_from("<i", tb, i+1)[0]
        dest=off_to_va(TEXT_RAW+i)+5+rel
        if dest==target:
            print(f"  call from 0x{off_to_va(TEXT_RAW+i):08X}")
            n+=1
    s=i+1
    if s>len(tb): break

# IDirect3DDevice9::Present is typically call [eax+44h] or similar vtable slot 17
print("\n=== call [reg+0x44] in CGx range (possible Present) ===")
for mod in range(8):
    # FF 50 44 / FF 51 44 ...
    pat=bytes([0xFF, 0x50+mod, 0x44])
    hs=findall(region, pat, lo_off)
    for h in hs[:10]:
        print(f"  0x{off_to_va(h):08X} {data[h-8:h+8].hex(' ')}")
