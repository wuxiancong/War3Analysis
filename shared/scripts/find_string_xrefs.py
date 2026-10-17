#!/usr/bin/env python3
import struct
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
        if raw <= file_off < raw + rsz:
            return image_base + va + (file_off - raw), name
    return None, None


def va_to_file(va, image_base, sections):
    rva = va - image_base
    for name, sva, vsz, raw, rsz in sections:
        if sva <= rva < sva + max(vsz, rsz):
            return raw + (rva - sva), name
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


def decode_around(data, h):
    b = data[max(0, h - 8) : h + 12]
    return b.hex(" ")


def main():
    data = Path(r"C:\War3Analysis\samples\1.27.0.52240\game.dll").read_bytes()
    image_base, sections = read_pe_maps(data)
    strings = {
        "maxfps": 0x6F951428,
        "200_near_maxfps": 0x6F95142F,  # guess; print nearby
        "lockfb": 0x6F95139C,
        "refreshrate": 0x6F951328,
        "fps.showminimapsignals": 0x6F98B840,
        "FPS_fmt": 0x6F994009,
        "CGxDevice.cpp": 0x6F95D7EC,
        "CGxDeviceD3d.cpp": 0x6F95D93C,
        "d3d9.dll": None,
        "Direct3DCreate9": None,
        "timeGetTime": 0x6FB55710,
        "Sleep_import": 0x6FB56F54,
        "QueryPerformanceCounter": 0x6FB570F4,
        "wglSwapLayerBuffers": None,
    }
    # resolve some by search
    for name, needle in [
        ("d3d9.dll", b"d3d9.dll"),
        ("Direct3DCreate9", b"Direct3DCreate9"),
        ("wglSwapLayerBuffers", b"wglSwapLayerBuffers"),
        ("CGxDevice.cpp", b"CGxDevice\\CGxDevice.cpp"),
        ("CGxDeviceD3d.cpp", b"CGxDeviceD3d\\CGxDeviceD3d.cpp"),
        ("Sleep_import", b"Sleep\x00"),
        ("timeGetTime", b"timeGetTime"),
    ]:
        i = data.find(needle)
        va, sec = file_to_va(i, image_base, sections)
        print(f"string {name}: file=0x{i:X} va=0x{va:08X} sec={sec}")
        strings[name] = va

    print("\n=== pointer xrefs ===")
    text = [s for s in sections if s[0] == ".text"][0]
    _, tva, _, traw, trsz = text
    text_bytes = data[traw : traw + trsz]

    for name, va in strings.items():
        if va is None:
            continue
        pat = struct.pack("<I", va)
        hits = find_all(data, pat)
        print(f"\n{name} VA=0x{va:08X} ptr_hits={len(hits)}")
        for h in hits[:30]:
            hva, hsec = file_to_va(h, image_base, sections)
            print(f"  file=0x{h:X} va={('0x%08X'%hva) if hva else '-'} sec={hsec} ctx={decode_around(data,h)}")

    # dump ascii around maxfps/lockfb/refreshrate
    print("\n=== video config string cluster ===")
    fo, _ = va_to_file(0x6F951300, image_base, sections)
    blob = data[fo : fo + 0x200]
    parts = blob.split(b"\x00")
    off = 0
    for p in parts:
        if p:
            va = 0x6F951300 + off
            print(f"  0x{va:08X} {p!r}")
        off += len(p) + 1


if __name__ == "__main__":
    main()
