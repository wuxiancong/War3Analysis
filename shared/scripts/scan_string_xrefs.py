#!/usr/bin/env python3
import struct
import sys
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
        if raw <= file_off < raw + rsz:
            return image_base + va + (file_off - raw), name
    return None, None


def va_to_file(va, image_base, sections):
    rva = va - image_base
    for name, sva, vsz, raw, rsz in sections:
        if sva <= rva < sva + rsz:
            return raw + (rva - sva), name
    return None, None


def find_all(data: bytes, needle: bytes):
    out = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        out.append(i)
        start = i + 1
    return out


def cstr_at(data, off, n=80):
    end = data.find(b"\x00", off)
    if end < 0:
        end = off + n
    return data[off:end].decode("latin1", "replace")


def dump(data, off, n=32):
    return data[off : off + n].hex(" ")


def main():
    data = Path(sys.argv[1]).read_bytes()
    image_base, sections = read_pe_maps(data)
    needles = [
        b"maxfps",
        b"lockfb",
        b"refreshrate",
        b" FPS: %-4.1f",
        b"fps",
        b"CGxDeviceD3d",
        b"CGxDeviceOpenGl",
        b"CGxDevice.cpp",
        b".\\CGxDevice",
        b"showminimapsignals",
        b"provider",
        b"colordepth",
        b"miplevel",
        b"unitshadows",
        b"occlusion",
        b"gamma",
        b"texquality",
    ]
    print("=== string locations ===")
    targets = []
    for s in needles:
        for h in find_all(data, s + b"\x00") or find_all(data, s):
            va, sec = file_to_va(h, image_base, sections)
            print(f"{s!r} file=0x{h:X} va=0x{va:08X} sec={sec} str={cstr_at(data,h)!r}")
            targets.append((s, va, h))
            break

    print("\n=== xrefs in .text (absolute VA pointer) ===")
    text = next(sec for sec in sections if sec[0] == ".text")
    tname, tva, tvsz, traw, trsz = text
    text_bytes = data[traw : traw + trsz]
    for s, va, h in targets:
        pat = struct.pack("<I", va)
        hits = find_all(text_bytes, pat)
        print(f"\n{s!r} VA=0x{va:08X} text_ptr_hits={len(hits)}")
        for rel in hits[:30]:
            foff = traw + rel
            code_va = image_base + tva + rel
            prev = data[foff - 1]
            op = {0x68: "PUSH", 0xB8: "MOV EAX", 0xB9: "MOV ECX", 0xBA: "MOV EDX", 0xBB: "MOV EBX"}.get(prev)
            print(f"  code_va=0x{code_va-1 if op else code_va:08X} op={op or hex(prev)} ctx={dump(data, foff-8, 24)}")

    # CGx source path strings (partial)
    print("\n=== CGx / Present related strings ===")
    for s in [
        b"CGxDeviceD3d",
        b"CGxDeviceOpenGl",
        b"CGxD3d",
        b"Present",
        b"SwapBuffers",
        b"wglSwap",
        b"d3d9.dll",
        b"d3d8.dll",
        b"opengl32",
        b"lock framebuffer",
        b"LockFrame",
        b"frame lock",
        b"FrameRate",
        b"framerate",
        b"max fps",
        b"Max FPS",
    ]:
        hits = find_all(data, s)
        print(f"{s!r}: {len(hits)}")
        for h in hits[:8]:
            va, sec = file_to_va(h, image_base, sections)
            print(f"  file=0x{h:X} va=0x{va:08X} sec={sec} {cstr_at(data, max(0,h-12), 80)!r}")


if __name__ == "__main__":
    main()
