#!/usr/bin/env python3
import struct
from pathlib import Path

ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
# D3D9: mov dword [esi+0x34], 0   C7 46 34 00 00 00 00
# D3D9: mov dword [reg+0x34], 0
pats = [
    ("mov_[esi+34h]_0", bytes.fromhex("c7463400000000")),
    ("mov_[eax+34h]_0", bytes.fromhex("c7403400000000")),
    ("mov_[ebx+34h]_0", bytes.fromhex("c7433400000000")),
    ("mov_[edi+34h]_0", bytes.fromhex("c7473400000000")),
    ("mov_[ecx+34h]_0", bytes.fromhex("c7413400000000")),
    ("maxfps", b"maxfps"),
    ("lockfb", b"lockfb"),
    ("Direct3DCreate9", b"Direct3DCreate9"),
    ("Direct3DCreate8", b"Direct3DCreate8"),
    ("wglSwapLayerBuffers", b"wglSwapLayerBuffers"),
]

def pe_maps(data):
    e=struct.unpack_from("<I", data, 0x3C)[0]
    nsec=struct.unpack_from("<H", data, e+6)[0]
    optsz=struct.unpack_from("<H", data, e+20)[0]
    opt=e+24
    image_base=struct.unpack_from("<I", data, opt+28)[0]
    sec0=opt+optsz
    secs=[]
    for i in range(nsec):
        o=sec0+i*40
        name=data[o:o+8].split(b"\0",1)[0].decode("latin1")
        vsz,va,rsz,raw=struct.unpack_from("<IIII", data, o+8)
        secs.append((name,va,vsz,raw,rsz))
    return image_base, secs

def file_to_va(off, ib, secs):
    for name,va,vsz,raw,rsz in secs:
        if raw<=off<raw+rsz:
            return ib+va+(off-raw), name
    return None, None

for ver in sorted(p for p in ROOT.iterdir() if p.is_dir()):
    dll=ver/"game.dll"
    if not dll.exists():
        print(ver.name, "NO game.dll")
        continue
    data=dll.read_bytes()
    ib, secs=pe_maps(data)
    print(f"\n==== {ver.name} size={len(data)} base=0x{ib:08X} ====")
    for name,pat in pats:
        hits=[]
        s=0
        while True:
            i=data.find(pat,s)
            if i<0: break
            va,sec=file_to_va(i, ib, secs)
            hits.append((i,va,sec))
            s=i+1
            if len(hits)>=8: break
        extra=""
        if name.startswith("mov_") and hits:
            extra="  " + " ".join(f"file=0x{h[0]:X}/va={('0x%08X'%h[1]) if h[1] else '-'}" for h in hits)
        print(f"  {name:24} {len(hits):3d}{extra}")
        if name=="maxfps" and hits:
            print(f"    maxfps va={('0x%08X'%hits[0][1]) if hits[0][1] else '-'}")
