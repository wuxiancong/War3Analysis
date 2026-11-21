#!/usr/bin/env python3
"""Find CUnit vtable slot +0xB8 (embedded pos), COrder fields, speed epilogue."""
import struct
from pathlib import Path

import capstone
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")


def load(path):
    data = Path(path).read_bytes()
    pe = pefile.PE(path, fast_load=True)
    return data, pe


def section(pe, name):
    for s in pe.sections:
        n = s.Name.split(b"\x00")[0].decode("latin1")
        if n == name:
            return s
    return None


def find_lea_ret(data, pe):
    """Functions: lea eax,[ecx+disp]; ret  OR mov eax, ecx; add eax, disp; ret"""
    text = section(pe, ".text")
    raw = text.PointerToRawData
    va = text.VirtualAddress
    blob = data[raw : raw + text.SizeOfRawData]
    hits = []
    # 8D 41 xx C3
    i = 0
    while True:
        j = blob.find(b"\x8D\x41", i)
        if j < 0 or j + 4 > len(blob):
            break
        if blob[j + 3] == 0xC3:
            disp = blob[j + 2]
            if disp >= 0x80:
                disp -= 0x100
            hits.append((va + j, disp, "lea8"))
        i = j + 1
    # 8D 81 xx xx xx xx C3
    i = 0
    while True:
        j = blob.find(b"\x8D\x81", i)
        if j < 0 or j + 7 > len(blob):
            break
        if blob[j + 6] == 0xC3:
            disp = struct.unpack_from("<i", blob, j + 2)[0]
            hits.append((va + j, disp, "lea32"))
        i = j + 1
    return hits


def vtable_slot(data, pe, func_rva, want_slot=0xB8):
    """Return vtable RVAs where func sits at want_slot."""
    base = pe.OPTIONAL_HEADER.ImageBase
    va = base + func_rva
    pat = struct.pack("<I", va)
    text = section(pe, ".text")
    text_lo = base + text.VirtualAddress
    text_hi = text_lo + text.Misc_VirtualSize
    rdata = section(pe, ".rdata")
    blob = data[rdata.PointerToRawData : rdata.PointerToRawData + rdata.SizeOfRawData]
    rva0 = rdata.VirtualAddress
    found = []
    start = 0
    while True:
        i = blob.find(pat, start)
        if i < 0:
            break
        start = i + 1
        # slot address rva
        slot_rva = rva0 + i
        vt_rva = slot_rva - want_slot
        # vtable[-1] should be an rdata pointer (RTTI), [0] a code pointer
        off_m4 = (vt_rva - 4) - rva0
        if off_m4 < 0 or off_m4 + want_slot + 8 > len(blob):
            continue
        prev = struct.unpack_from("<I", blob, off_m4)[0]
        first = struct.unpack_from("<I", blob, off_m4 + 4)[0]
        if not (text_lo <= first < text_hi):
            continue
        # prev should NOT be code (RTTI in rdata/data)
        if text_lo <= prev < text_hi:
            continue
        found.append(vt_rva)
    return found


def disasm_tail(data, pe, rva, skip, n):
    off = pe.get_offset_from_rva(rva)
    blob = data[off : off + 0x800]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    lines = []
    for ins in md.disasm(blob, rva):
        if ins.address < rva + skip:
            continue
        lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if len(lines) >= n:
            break
    return "\n".join(lines)


def find_strings(data, pe, needle):
    hits = []
    start = 0
    b = needle.encode() if isinstance(needle, str) else needle
    while True:
        i = data.find(b, start)
        if i < 0:
            break
        # rva
        try:
            rva = pe.get_rva_from_offset(i)
        except Exception:
            rva = None
        hits.append((i, rva))
        start = i + 1
        if len(hits) > 12:
            break
    return hits


def main():
    jobs = [
        ("1.26", r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll", 0x2019F0),
        ("1.27", r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll", 0x5DF1E0),
    ]
    parts_all = []
    for tag, path, speed_rva in jobs:
        data, pe = load(path)
        base = pe.OPTIONAL_HEADER.ImageBase
        parts = ["# %s\n" % tag]
        leas = find_lea_ret(data, pe)
        parts.append("lea-ret functions: %d\n" % len(leas))
        # only keep displacements that look like object fields
        interesting = [h for h in leas if h[1] in (0x4, 0x8, 0xC, 0x10, 0x30, 0x5C, 0x64, 0x70, 0x164, 0x1EC) or (0x20 <= h[1] <= 0x220)]
        matched = []
        for rva, disp, kind in interesting:
            vts = vtable_slot(data, pe, rva, 0xB8)
            if vts:
                matched.append((rva, disp, vts[:6]))
        parts.append("## vtable+0xB8 lea eax,[ecx+disp]; ret\n")
        for rva, disp, vts in matched:
            parts.append("- func 0x%X disp +0x%X vtables %s\n" % (rva, disp, ", ".join("0x%X" % v for v in vts)))
        if not matched:
            parts.append("(none)\n")
            # show a few lea hits for debugging
            parts.append("sample leas: " + ", ".join("0x%X:+0x%X" % (r, d) for r, d, k in leas[:15]) + "\n")

        for s in (b".?AVCUnit@@", b".?AVCOrder@@", b".?AVCOrderTarget@@", b".?AVCAbilityMove@@", b"CUnitPathing", b".?AVCPathing@@", b".?AVCWidget@@"):
            hits = find_strings(data, pe, s)
            parts.append("str %s -> %s\n" % (s.decode(), ", ".join("off=0x%X rva=%s" % (o, hex(r) if r else None) for o, r in hits) or "none"))

        parts.append("## speed epilogue\n```\n%s\n```\n" % disasm_tail(data, pe, speed_rva, 0x70 if tag == "1.26" else 0, 70))
        text = "".join(parts)
        (OUT / ("%s-vtable.md" % tag)).write_text(text, encoding="utf-8")
        print(tag, "matched", len(matched), "leas", len(leas))
        pe.close()


if __name__ == "__main__":
    main()
