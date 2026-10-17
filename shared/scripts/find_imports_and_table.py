#!/usr/bin/env python3
import struct
from pathlib import Path

data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()

def u16(o): return struct.unpack_from("<H", data, o)[0]
def u32(o): return struct.unpack_from("<I", data, o)[0]

e_lfanew = u32(0x3C)
coff = e_lfanew + 4
nsec = u16(coff + 2)
optsz = u16(coff + 16)
opt = coff + 20
magic = u16(opt)
assert magic == 0x10B
image_base = u32(opt + 28)
dd_off = opt + 96
imp_rva, imp_sz = u32(dd_off + 8), u32(dd_off + 12)
iat_rva, iat_sz = u32(dd_off + 96), u32(dd_off + 100)

sec0 = opt + optsz
sections = []
for i in range(nsec):
    off = sec0 + i * 40
    name = data[off:off+8].split(b"\0",1)[0].decode("latin1")
    vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off+8)
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
        if raw <= off < raw + max(rsz,1):
            return image_base + va + (off - raw), name
    return None, None

# parse imports
wanted = {
    b"Sleep", b"SleepEx", b"timeGetTime", b"QueryPerformanceCounter",
    b"QueryPerformanceFrequency", b"GetTickCount", b"GetTickCount64",
    b"timeBeginPeriod", b"NtDelayExecution", b"WaitForSingleObject",
    b"Direct3DCreate9", b"wglSwapLayerBuffers", b"wglSwapBuffers",
    b"SwapBuffers", b"glFinish", b"glFlush",
}
print("=== selected imports ===")
off, _ = rva_to_off(imp_rva)
i = 0
found = {}
while True:
    orig, timedate, chain, name_rva, fts = struct.unpack_from("<IIIII", data, off + i*20)
    if orig == 0 and name_rva == 0 and fts == 0:
        break
    dll_off, _ = rva_to_off(name_rva)
    dll = data[dll_off:].split(b"\0",1)[0]
    thunk_rva = orig if orig else fts
    idx = 0
    while True:
        toff, _ = rva_to_off(thunk_rva + idx*4)
        thunk = u32(toff)
        if thunk == 0:
            break
        if thunk & 0x80000000:
            iname = f"ord_{thunk & 0xFFFF}"
        else:
            hint_off, _ = rva_to_off(thunk & 0x7FFFFFFF)
            iname_b = data[hint_off+2:].split(b"\0",1)[0]
            iname = iname_b.decode("latin1", "replace")
            if iname_b in wanted:
                iat_va = image_base + fts + idx*4
                found[iname] = (dll.decode(), iat_va, image_base + thunk_rva + idx*4)
                print(f"{dll.decode():16} {iname:28} IAT_VA=0x{iat_va:08X}")
        idx += 1
        if idx > 2000:
            break
    i += 1

# xrefs to IAT: FF 15 <iat> or FF 25 <iat>
print("\n=== IAT call xrefs in .text ===")
text = next(s for s in sections if s[0]==".text")
_,_,_, traw, trsz = text
tb = data[traw:traw+trsz]
for name, (dll, iat_va, _) in found.items():
    pat = b"\xff\x15" + struct.pack("<I", iat_va)
    hits=[]
    s=0
    while True:
        j=tb.find(pat,s)
        if j<0: break
        hits.append(traw+j); s=j+1
    print(f"\n{name} CALL hits={len(hits)}")
    for h in hits[:15]:
        va,_=off_to_va(h)
        print(f"  va=0x{va:08X} file=0x{h:X} ctx={data[h-8:h+16].hex(' ')}")

# dump config records near lockfb / maxfps
print("\n=== config table dump around video keys ===")
def cstr(va):
    off,_=va_to_off(va)
    if off is None: return "?"
    end=data.find(b"\0", off)
    return data[off:end].decode("latin1","replace")

# table entries appear 16 bytes: unk ptr, flags, name ptr? From dump:
# lockfb at 0x6F950E98: looking at ctx
# Let's dump from 0x6F950D80 as 16-byte records
base = 0x6F950C80
off,_ = va_to_off(base)
for rec in range(40):
    o = off + rec*16
    a,b,c,d = struct.unpack_from("<IIII", data, o)
    va,_=off_to_va(o)
    names=[]
    for x in (a,c):
        if 0x6F000000 <= x <= 0x6FC00000:
            s=cstr(x)
            if s and all(32<=ord(ch)<127 for ch in s) and 1 < len(s) < 40:
                names.append(s)
    print(f"0x{va:08X}: {a:08X} {b:08X} {c:08X} {d:08X}  {names}")
