#!/usr/bin/env python3
"""Deep-dive 1.27 ERROR_ID_BADPASSWORD call sites for analysis docs."""
from __future__ import annotations

import struct
from pathlib import Path

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs

PATH = Path(r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll")


def read_cstr(pe: pefile.PE, raw: bytes, va: int, maxlen: int = 96) -> str:
    base = pe.OPTIONAL_HEADER.ImageBase
    off = pe.get_offset_from_rva(va - base)
    out = []
    for i in range(maxlen):
        b = raw[off + i]
        if b == 0:
            break
        out.append(chr(b) if 32 <= b < 127 else "?")
    return "".join(out)


def first_ecx_key(md: Cs, pe: pefile.PE, raw: bytes, va: int) -> str | None:
    base = pe.OPTIONAL_HEADER.ImageBase
    off = pe.get_offset_from_rva(va - base)
    for insn in md.disasm(raw[off : off + 0x40], va):
        if insn.mnemonic == "mov" and insn.op_str.startswith("ecx, 0x"):
            imm = int(insn.op_str.split(",")[1].strip(), 16)
            return read_cstr(pe, raw, imm)
    return None


def find_calls_to(raw: bytes, pe: pefile.PE, target_rva: int) -> list[int]:
    base_text_rva = 0x1000
    text = next(s for s in pe.sections if s.Name.startswith(b".text"))
    start = text.PointerToRawData
    size = text.SizeOfRawData
    hits = []
    for i in range(start, start + size - 5):
        if raw[i] != 0xE8:
            continue
        rel = struct.unpack_from("<i", raw, i + 1)[0]
        next_rva = (i - start) + base_text_rva + 5
        # .text VA is 0x1000 for this PE
        next_rva = pe.get_rva_from_offset(i) + 5
        if next_rva + rel == target_rva:
            hits.append(pe.get_rva_from_offset(i))
    return hits


def decode_switch(pe, raw, jt_rva, ind_rva, count, md):
    base = pe.OPTIONAL_HEADER.ImageBase
    jt = pe.get_offset_from_rva(jt_rva)
    ind = pe.get_offset_from_rva(ind_rva)
    idx = raw[ind : ind + count]
    n = max(idx) + 1
    targets = [struct.unpack_from("<I", raw, jt + i * 4)[0] for i in range(n)]
    rows = []
    for i, b in enumerate(idx):
        status = i + 1
        key = first_ecx_key(md, pe, raw, targets[b])
        rows.append((status, targets[b], key or "(default/no key)"))
    return rows


def main() -> None:
    pe = pefile.PE(str(PATH))
    raw = PATH.read_bytes()
    base = pe.OPTIONAL_HEADER.ImageBase
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    print("SHA256", __import__("hashlib").sha256(raw).hexdigest().upper())
    print("ImageBase", hex(base))
    print()

    print("=== FUN_2C8E90 switch (event+0x18 status, 1..0x1B) ===")
    for status, tgt, key in decode_switch(pe, raw, 0x2C9060, 0x2C9080, 0x1B, md):
        mark = " <<<" if "BADPASSWORD" in key else ""
        print(f"  status 0x{status:02X} -> {hex(tgt)} {key}{mark}")

    print()
    print("=== Callers of FUN_2C8E90 ===")
    for h in find_calls_to(raw, pe, 0x2C8E90):
        print(f"  call site RVA 0x{h:X}")

    print()
    print("=== Callers of dialog 0x29E8F0 ===")
    callers = find_calls_to(raw, pe, 0x29E8F0)
    print(f"  count={len(callers)}")
    for h in callers[:30]:
        print(f"  0x{h:X}")

    print()
    print("=== BADPASSWORD xref sites / owning funcs ===")
    refs = [0x2C9003, 0x2D4902, 0x2D4A70, 0x2D4BF7, 0x2D9304, 0x2DCD41]
    for rva in refs:
        # walk back for push ebp; mov ebp,esp
        off = pe.get_offset_from_rva(rva)
        func = None
        for back in range(0x1000):
            o = off - back
            if raw[o] == 0x55 and raw[o + 1] == 0x8B and raw[o + 2] == 0xEC:
                prev = raw[o - 1]
                if prev in (0xCC, 0x90, 0xC3, 0x00) or (
                    o >= 3 and raw[o - 3] == 0xC2
                ):
                    func = pe.get_rva_from_offset(o)
                    break
        print(f"  xref 0x{rva:X} func 0x{func:X}" if func else f"  xref 0x{rva:X}")


if __name__ == "__main__":
    main()
