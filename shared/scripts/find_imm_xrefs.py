#!/usr/bin/env python3
"""查找 PE 中对某个字符串（或任意 VA）的立即数引用（push imm32 / mov r32,imm32 / 任意 4 字节小端出现）。

不依赖 capstone/pefile，配合 MSVC dumpbin /DISASM /RANGE 做定点反汇编。

用法:
  python -I find_imm_xrefs.py <game.dll> --string EmailBindPanel [--string ...]
  python -I find_imm_xrefs.py <game.dll> --va 0x6F967BF4
"""
import argparse
import struct


def read_pe(data: bytes):
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
        name = data[off:off + 8].split(b"\x00", 1)[0].decode("latin1")
        vsz, va, rsz, raw = struct.unpack_from("<IIII", data, off + 8)
        chars = struct.unpack_from("<I", data, off + 36)[0]
        sections.append((name, va, vsz, raw, rsz, chars))
    return image_base, sections


def file_to_va(off, image_base, sections):
    for name, va, vsz, raw, rsz, _ in sections:
        if raw <= off < raw + rsz:
            return image_base + va + (off - raw), name
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pe")
    ap.add_argument("--string", action="append", default=[])
    ap.add_argument("--va", action="append", default=[])
    args = ap.parse_args()

    data = open(args.pe, "rb").read()
    image_base, sections = read_pe(data)
    code = [s for s in sections if s[5] & 0x20000000]  # IMAGE_SCN_MEM_EXECUTE

    targets = []
    for s in args.string:
        needle = s.encode("latin1") + b"\x00"
        pos = data.find(needle)
        while pos != -1:
            # 只接受以 \0 开头的完整字符串
            if pos == 0 or data[pos - 1] == 0:
                va, sec = file_to_va(pos, image_base, sections)
                if va:
                    targets.append((s, va))
            pos = data.find(needle, pos + 1)
    for v in args.va:
        targets.append((v, int(v, 16)))

    print(f"image_base=0x{image_base:08X}")
    for label, va in targets:
        pat = struct.pack("<I", va)
        print(f"== {label} @ VA 0x{va:08X} (RVA 0x{va - image_base:X})")
        for name, sva, vsz, raw, rsz, _ in code:
            blob = data[raw:raw + rsz]
            p = blob.find(pat)
            while p != -1:
                ref_va = image_base + sva + p
                prev = blob[p - 1] if p > 0 else 0
                kind = {0x68: "push", 0xB8: "mov eax", 0xB9: "mov ecx", 0xBA: "mov edx",
                        0xBB: "mov ebx", 0xBE: "mov esi", 0xBF: "mov edi"}.get(prev, f"op {prev:02X}")
                print(f"   xref imm @ 0x{ref_va:08X} (RVA 0x{ref_va - image_base:X}) [{kind}]")
                p = blob.find(pat, p + 1)


if __name__ == "__main__":
    main()
