#!/usr/bin/env python3
import struct
from pathlib import Path

def read_pe_maps(data: bytes):
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    coff = e_lfanew + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsz = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    image_base = struct.unpack_from("<I", data, opt + 28)[0]
    sec0 = opt + optsz
    sections = []
    for i in range(nsec):
        off = sec0 + i * 40
        name = data[off : off + 8].split(b"\x00", 1)[0].decode("latin1")
        vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
        sections.append((name, va, vsz, raw, rsz))
    return image_base, sections

def file_to_va(file_off, image_base, sections):
    for name, va, vsz, raw, rsz in sections:
        if raw <= file_off < raw + max(rsz, 1):
            return image_base + va + (file_off - raw), name
    return None, None

def dump(data, off, n=48):
    return data[max(0, off): off+n].hex(" ")

data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()
image_base, sections = read_pe_maps(data)
targets = {
    "maxfps": 0x6F951428,
    "lockfb": 0x6F95139C,
    "refreshrate": 0x6F951328,
    "fps": 0x6F98B840,
    "FPS_fmt": 0x6F994009,
    "CGxDevice.cpp": 0x6F95D7F6,
    "CGxDeviceD3d.cpp": 0x6F95D93C,
}
print("=== pointer occurrences anywhere ===")
for name, va in targets.items():
    pat = struct.pack("<I", va)
    start=0; n=0
    while True:
        i=data.find(pat, start)
        if i<0: break
        fva, sec = file_to_va(i, image_base, sections)
        print(f"{name} at file=0x{i:X} va={('0x%08X'%fva) if fva else '-'} sec={sec} ctx={dump(data,i-16,48)}")
        n+=1; start=i+1
        if n>=20:
            print("  truncated")
            break
    if n==0:
        print(f"{name}: none")
