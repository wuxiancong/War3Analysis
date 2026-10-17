#!/usr/bin/env python3
import struct
import sys
from pathlib import Path

IMAGE_BASE = 0x6F000000


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


def find_all(data, needle):
    out = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        out.append(i)
        start = i + 1
    return out


def dump(data, off, n=32):
    return data[max(0, off) : off + n].hex(" ")


def main():
    data = Path(sys.argv[1]).read_bytes()
    image_base, sections = read_pe_maps(data)
    targets = {
        "maxfps": 0x6F951428,
        "lockfb": 0x6F95139C,
        "refreshrate": 0x6F951328,
        "fps": 0x6F98B840,
        "FPS_fmt": 0x6F994009,
        "CGxDevice.cpp": 0x6F95D7EC,  # may be approximate
        "CGxDeviceD3d.cpp": 0x6F95D93C,
        "Direct3DCreate9": None,
        "d3d9.dll": None,
        "timeGetTime": 0x6FB55710,
        "Sleep_imp": 0x6FB56F54,
        "wglSwapLayerBuffers": None,
    }
    # locate some strings exactly
    for s in [b"Direct3DCreate9", b"d3d9.dll", b"wglSwapLayerBuffers", b"CGxDevice.cpp"]:
        i = data.find(s)
        va, sec = file_to_va(i, image_base, sections)
        print(f"string {s!r} file=0x{i:X} va=0x{va:08X} {sec}")
        targets[s.decode()] = va

    print("\n=== absolute VA xrefs in .text ===")
    text = next(s for s in sections if s[0] == ".text")
    tname, tva, tvsz, traw, trsz = text
    text_bytes = data[traw : traw + trsz]
    for name, va in targets.items():
        if not va:
            continue
        pat = struct.pack("<I", va)
        hits = []
        start = 0
        while True:
            i = text_bytes.find(pat, start)
            if i < 0:
                break
            hits.append(traw + i)
            start = i + 1
        print(f"\n{name} VA=0x{va:08X} xrefs={len(hits)}")
        for h in hits[:30]:
            va2, _ = file_to_va(h, image_base, sections)
            print(f"  file=0x{h:X} va=0x{va2:08X} ctx={dump(data, h-8, 24)}")


if __name__ == "__main__":
    main()
