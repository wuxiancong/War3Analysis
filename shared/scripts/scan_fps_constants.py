#!/usr/bin/env python3
"""Scan a PE for FPS-limit related strings, imports, and numeric constants."""
import struct
import sys
from collections import defaultdict
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


def dump_hex(data, off, n=24):
    return data[off : off + n].hex(" ")


def main():
    path = Path(sys.argv[1])
    data = path.read_bytes()
    image_base, sections = read_pe_maps(data)
    print(f"file={path} size={len(data)} image_base=0x{image_base:08X}")
    print("sections:")
    for name, va, vsz, raw, rsz in sections:
        print(f"  {name:8} VA=0x{va:08X} VSz=0x{vsz:X} Raw=0x{raw:X} RSz=0x{rsz:X}")

    strings = [
        b"maxfps",
        b"MaxFPS",
        b"MAXFPS",
        b"FPS:",
        b"/fps",
        b"fps",
        b"lockfb",
        b"Lockfb",
        b"LOCKFB",
        b"refreshrate",
        b"vsync",
        b"VSync",
        b"VSYNC",
        b"WaitForVerticalBlank",
        b"wglSwapInterval",
        b"D3DPRESENT",
        b"PresentInterval",
        b"nativefullscr",
        b"timeGetTime",
        b"QueryPerformanceCounter",
        b"QueryPerformanceFrequency",
        b"Sleep",
    ]
    print("\n=== strings ===")
    for s in strings:
        hits = find_all(data, s)
        print(f"{s!r}: {len(hits)} hits")
        for h in hits[:20]:
            va, sec = file_to_va(h, image_base, sections)
            ctx = data[max(0, h - 8) : h + len(s) + 24]
            printable = "".join(chr(b) if 32 <= b < 127 else "." for b in ctx)
            print(f"  file=0x{h:X} va={('0x%08X' % va) if va else '-'} sec={sec} ctx={printable}")

    # 32-bit LE immediates of interest
    constants = {
        "60": struct.pack("<I", 60),
        "64": struct.pack("<I", 64),
        "200": struct.pack("<I", 200),
        "300": struct.pack("<I", 300),
        "float_60": struct.pack("<f", 60.0),
        "float_64": struct.pack("<f", 64.0),
        "float_200": struct.pack("<f", 200.0),
        "float_1_60": struct.pack("<f", 1.0 / 60.0),
        "float_16_666": struct.pack("<f", 16.666666),
        "float_0_015625": struct.pack("<f", 1.0 / 64.0),
        "double_1_60": struct.pack("<d", 1.0 / 60.0),
        "double_1_64": struct.pack("<d", 1.0 / 64.0),
        "D3DPRESENT_INTERVAL_ONE": struct.pack("<I", 1),  # too common, skip later
        "0x3C888889": bytes.fromhex("8988883C"),  # 1/60 float exact common encoding
        "0x3C888889_alt": struct.pack("<I", 0x3C888889),
    }
    # Filter to .text / .rdata only for numeric dumps
    interesting_secs = {".text", ".rdata", ".data"}
    print("\n=== selected constants in .text/.rdata/.data (capped) ===")
    for name, pat in constants.items():
        if name == "D3DPRESENT_INTERVAL_ONE":
            continue
        hits = find_all(data, pat)
        shown = 0
        print(f"{name} ({pat.hex()}): {len(hits)} raw hits")
        for h in hits:
            va, sec = file_to_va(h, image_base, sections)
            if sec not in interesting_secs:
                continue
            # For integer 60/64/200/300, require nearby CMP/MOV encodings roughly:
            # CMP r/m32, imm32 = 81 /7 ; CMP EAX,imm32 = 3D
            if name in {"60", "64", "200", "300"}:
                prev = data[h - 1] if h > 0 else 0
                prev2 = data[h - 2] if h > 1 else 0
                if prev not in (0x3D,) and not (prev2 == 0x81 and (prev & 0xF8) == 0xF8) and prev not in (
                    0xB8,
                    0xB9,
                    0xBA,
                    0xBB,
                    0xBC,
                    0xBD,
                    0xBE,
                    0xBF,
                ):
                    continue
            print(f"  file=0x{h:X} va={('0x%08X' % va) if va else '-'} sec={sec} prev={dump_hex(data, max(0,h-6), 16)}")
            shown += 1
            if shown >= 40:
                print("  ... truncated ...")
                break

    # Look for CMP EAX, 0x40 / CMP EAX, 0x3C (8-bit) near text
    print("\n=== CMP EAX, imm8 0x3C/0x40 in .text (capped) ===")
    for imm in (0x3C, 0x40):  # 60, 64
        pat = bytes([0x83, 0xF8, imm])
        hits = find_all(data, pat)
        print(f"CMP EAX, {imm}: {len(hits)}")
        shown = 0
        for h in hits:
            va, sec = file_to_va(h, image_base, sections)
            if sec != ".text":
                continue
            print(f"  file=0x{h:X} va=0x{va:08X} ctx={dump_hex(data, h-8, 24)}")
            shown += 1
            if shown >= 25:
                break


if __name__ == "__main__":
    main()
