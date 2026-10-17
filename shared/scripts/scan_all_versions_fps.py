#!/usr/bin/env python3
"""Locate FPS-unlock sites in every War3Launcher versions/*/game.dll."""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_32, Cs

ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
md = Cs(CS_ARCH_X86, CS_MODE_32)


def sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def pe_meta(blob: bytes):
    e_lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
    coff = e_lfanew + 4
    nsec = struct.unpack_from("<H", blob, coff + 2)[0]
    opt = coff + 20
    magic = struct.unpack_from("<H", blob, opt)[0]
    imagebase = struct.unpack_from("<I", blob, opt + 28)[0]
    opt_size = struct.unpack_from("<H", blob, coff + 16)[0]
    sec_off = opt + opt_size
    secs = []
    for i in range(nsec):
        o = sec_off + i * 40
        name = blob[o : o + 8].split(b"\x00")[0].decode(errors="replace")
        vsz, va, rsz, raw = struct.unpack_from("<IIII", blob, o + 8)
        secs.append((name, va, raw, vsz, rsz))
    return imagebase, secs, magic


def rva_to_off(secs, rva: int) -> int | None:
    for name, va, raw, vsz, rsz in secs:
        if va <= rva < va + max(vsz, rsz):
            return raw + (rva - va)
    return None


def va_to_off(imagebase: int, secs, va: int) -> int | None:
    return rva_to_off(secs, va - imagebase)


def off_to_va(imagebase: int, secs, fo: int) -> int | None:
    for name, va, raw, vsz, rsz in secs:
        if raw <= fo < raw + rsz:
            return imagebase + va + (fo - raw)
    return None


def parse_imports(blob: bytes, imagebase: int, secs):
    e_lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
    opt = e_lfanew + 24
    dd = opt + 96
    imp_rva, _ = struct.unpack_from("<II", blob, dd + 8)

    def rva_off(rva):
        return rva_to_off(secs, rva)

    out = {}
    off = rva_off(imp_rva)
    if off is None:
        return out
    while True:
        ilt, _, _, name_rva, iat_rva = struct.unpack_from("<IIIII", blob, off)
        if name_rva == 0 and iat_rva == 0:
            break
        no = rva_off(name_rva)
        dll = blob[no:].split(b"\x00")[0].decode(errors="replace").lower() if no else "?"
        thunk_rva = ilt or iat_rva
        idx = 0
        while True:
            to = rva_off(thunk_rva + idx * 4)
            if to is None:
                break
            thunk = struct.unpack_from("<I", blob, to)[0]
            if thunk == 0:
                break
            if thunk & 0x80000000:
                nm = f"ord_{thunk & 0xFFFF}"
            else:
                ho = rva_off((thunk & 0x7FFFFFFF) + 2)
                nm = blob[ho:].split(b"\x00")[0].decode(errors="replace") if ho else "?"
            out.setdefault(dll, {})[nm] = imagebase + iat_rva + idx * 4
            idx += 1
        off += 20
    return out


def text_range(secs):
    for name, va, raw, vsz, rsz in secs:
        if name == ".text":
            return va, raw, rsz
    raise RuntimeError("no .text")


def find_all(hay: bytes, needle: bytes, base: int) -> list[int]:
    out = []
    s = 0
    while True:
        i = hay.find(needle, s)
        if i < 0:
            break
        out.append(base + i)
        s = i + 1
    return out


def longest_cc(tb: bytes, text_va: int, min_len: int = 48) -> list[tuple[int, int]]:
    best = []
    i = 0
    n = len(tb)
    while i < n:
        if tb[i] == 0xCC:
            j = i
            while j < n and tb[j] == 0xCC:
                j += 1
            ln = j - i
            if ln >= min_len:
                best.append((text_va + i, ln))
            i = j
        else:
            i += 1
    best.sort(key=lambda x: -x[1])
    return best


def dis_at(blob: bytes, imagebase: int, secs, va: int, n: int = 48) -> str:
    o = va_to_off(imagebase, secs, va)
    if o is None:
        return "(unmapped)"
    lines = []
    for ins in md.disasm(blob[o : o + n], va):
        lines.append(f"    {ins.address:08X}  {ins.mnemonic:8} {ins.op_str}")
    return "\n".join(lines)


def scan(path: Path) -> None:
    blob = path.read_bytes()
    imagebase, secs, magic = pe_meta(blob)
    tva, traw, trsz = text_range(secs)
    text_va = imagebase + tva
    tb = blob[traw : traw + trsz]
    imps = parse_imports(blob, imagebase, secs)
    flat = {}
    for dll, funcs in imps.items():
        flat.update(funcs)

    has8 = b"Direct3DCreate8" in blob
    has9 = b"Direct3DCreate9" in blob
    has_maxfps = b"maxfps\x00" in blob
    print("=" * 72)
    print(f"{path.parent.name}  size={len(blob)}  sha={sha256(blob)}")
    print(f"  imagebase=0x{imagebase:08X}  .text VA=0x{text_va:08X} RAW=0x{traw:X} SZ=0x{trsz:X}")
    print(f"  D3D8={has8} D3D9={has9} maxfps={has_maxfps}")
    for name in (
        "wglGetProcAddress",
        "wglMakeCurrent",
        "wglSwapLayerBuffers",
        "wglSwapBuffers",
        "Direct3DCreate8",
        "Direct3DCreate9",
    ):
        if name in flat:
            print(f"  IAT {name:24} 0x{flat[name]:08X}")

    # software 64: A8 04 74 xx 83 E0 FB
    print("  --- software-64 candidates (test al,4 / and eax,~4) ---")
    s = 0
    while True:
        i = tb.find(b"\xA8\x04\x74", s)
        if i < 0:
            break
        if i + 8 <= len(tb) and tb[i + 4 : i + 7] == b"\x83\xE0\xFB":
            va = text_va + i
            win = tb[i : i + 28]
            print(f"  VA 0x{va:08X} off 0x{traw + i:X}  {win.hex(' ')}")
            print(dis_at(blob, imagebase, secs, va, 40))
        s = i + 1

    # also 83 E0 FB followed soon by BA 11 00 00 00 or 8D 53 11
    print("  --- and eax,~4 near edx=0x11 ---")
    s = 0
    while True:
        i = tb.find(b"\x83\xE0\xFB", s)
        if i < 0:
            break
        win = tb[i : i + 24]
        if b"\xBA\x11\x00\x00\x00" in win or b"\x8D\x53\x11" in win or b"\x8D\x56\x11" in win:
            va = text_va + i
            print(f"  VA 0x{va:08X} off 0x{traw + i:X}  {win.hex(' ')}")
        s = i + 1

    # D3D interval immediates
    # D3D8: C7 4x 30 00 00 00 00  (PresentationInterval +0x30)
    # D3D9: C7 4x 34 00 00 00 00
    print("  --- mov [r+30h], 0  (D3D8 interval candidate) ---")
    for modrm, name in [(0x46, "esi"), (0x43, "ebx"), (0x47, "edi"), (0x41, "ecx"), (0x40, "eax"), (0x45, "ebp")]:
        pat = bytes([0xC7, modrm, 0x30, 0, 0, 0, 0])
        hits = find_all(tb, pat, text_va)
        if hits:
            print(f"    [ {name}+30h ] x{len(hits)} first={[hex(h) for h in hits[:6]]}")
    print("  --- mov [r+34h], 0  (D3D9 interval / D3D8 leftover) ---")
    for modrm, name in [(0x46, "esi"), (0x43, "ebx"), (0x47, "edi"), (0x41, "ecx")]:
        pat = bytes([0xC7, modrm, 0x34, 0, 0, 0, 0])
        hits = find_all(tb, pat, text_va)
        if hits:
            print(f"    [ {name}+34h ] x{len(hits)}")
            for h in hits[:8]:
                o = va_to_off(imagebase, secs, h)
                ctx = blob[o - 24 : o + 8].hex(" ") if o else ""
                # prefer nearby push 0x34/0x38 memset
                print(f"      0x{h:08X} ctx {ctx}")

    print("  --- mov [r+2Ch], 1  Flags LOCKABLE? ---")
    for modrm, name in [(0x46, "esi"), (0x43, "ebx"), (0x47, "edi")]:
        pat = bytes([0xC7, modrm, 0x2C, 1, 0, 0, 0])
        hits = find_all(tb, pat, text_va)
        if hits:
            print(f"    [ {name}+2Ch ]=1 x{len(hits)} {[hex(h) for h in hits[:8]]}")

    print("  --- push sizeof present params (0x34 D3D8 / 0x38 D3D9) ---")
    for imm in (0x34, 0x38):
        hits = find_all(tb, bytes([0x6A, imm]), text_va)
        print(f"    push 0x{imm:X} count={len(hits)}")

    # maxfps default 200 near string
    idx = blob.find(b"maxfps\x00")
    if idx >= 0:
        sva = off_to_va(imagebase, secs, idx)
        print(f"  maxfps string VA 0x{sva:08X} file 0x{idx:X}")
        # xrefs in .text
        if sva:
            x = find_all(tb, struct.pack("<I", sva), text_va)
            print(f"    xrefs { [hex(v) for v in x] }")
        # C7 45 FC C8 00 00 00
        for hit in find_all(tb, bytes.fromhex("c745fcc8000000"), text_va):
            print(f"    mov [ebp-4], 200  VA 0x{hit:08X} off 0x{va_to_off(imagebase, secs, hit):X}")
        for hit in find_all(tb, bytes.fromhex("c745f8c8000000"), text_va):
            print(f"    mov [ebp-8], 200  VA 0x{hit:08X}")
        for hit in find_all(tb, b"\x68\xC8\x00\x00\x00", text_va):
            # push 200
            print(f"    push 200 VA 0x{hit:08X}")

    caves = longest_cc(tb, text_va, 48)
    print(f"  INT3 caves >=48: {[(hex(v), n) for v, n in caves[:5]]}")

    # wglMakeCurrent IAT calls
    if "wglMakeCurrent" in flat:
        iat = flat["wglMakeCurrent"]
        calls = find_all(tb, b"\xFF\x15" + struct.pack("<I", iat), text_va)
        print(f"  wglMakeCurrent calls {len(calls)} {[hex(c) for c in calls[:8]]}")
        for c in calls[:3]:
            print(dis_at(blob, imagebase, secs, c, 64))


def main():
    for d in sorted(ROOT.iterdir()):
        dll = d / "game.dll"
        if dll.exists():
            scan(dll)


if __name__ == "__main__":
    main()
