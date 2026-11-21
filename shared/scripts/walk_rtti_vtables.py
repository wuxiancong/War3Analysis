#!/usr/bin/env python3
"""Walk MSVC RTTI vtables and print tiny field-getter slots."""
import struct
from pathlib import Path

import capstone
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")


def load(path):
    return Path(path).read_bytes(), pefile.PE(path, fast_load=True)


def rva_of_offset(pe, off):
    return pe.get_rva_from_offset(off)


def find_vtable(data, pe, type_name: bytes):
    """Return vtable RVA (slot 0) for an MSVC type descriptor name."""
    base = pe.OPTIONAL_HEADER.ImageBase
    idx = data.find(type_name + b"\x00")
    if idx < 0:
        return None
    td_off = idx - 8  # pVFTable, spare, name
    td_rva = rva_of_offset(pe, td_off)
    td_va = base + td_rva
    # COL contains a pointer to TD. Search rdata.
    pat = struct.pack("<I", td_va)
    cols = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        start = i + 1
        cols.append(i)
        if len(cols) > 8:
            break
    text = None
    for s in pe.sections:
        if s.Name.startswith(b".text"):
            text = s
            break
    tlo = base + text.VirtualAddress
    thi = tlo + max(text.Misc_VirtualSize, 1)
    vtables = []
    for col_off in cols:
        col_rva = rva_of_offset(pe, col_off)
        # COL may start before the TD pointer. vtable[-1] points at COL start.
        # Try the TD pointer location and a few dwords before as COL base.
        for back in range(0, 6):
            col_base_rva = col_rva - back * 4
            col_va = base + col_base_rva
            p = struct.pack("<I", col_va)
            s0 = 0
            while True:
                j = data.find(p, s0)
                if j < 0:
                    break
                s0 = j + 1
                # next dword should be code (vtable[0])
                if j + 8 > len(data):
                    continue
                slot0 = struct.unpack_from("<I", data, j + 4)[0]
                if tlo <= slot0 < thi:
                    vt_rva = rva_of_offset(pe, j + 4)
                    vtables.append(vt_rva)
    # unique
    out = []
    for v in vtables:
        if v not in out:
            out.append(v)
    return out


def walk(data, pe, vt_rva, limit=80):
    base = pe.OPTIONAL_HEADER.ImageBase
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    tlo = base + text.VirtualAddress
    thi = tlo + text.Misc_VirtualSize
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    lines = []
    for i in range(limit):
        off = pe.get_offset_from_rva(vt_rva + i * 4)
        fn = struct.unpack_from("<I", data, off)[0]
        if not (tlo <= fn < thi):
            lines.append("slot +0x%X END noncode 0x%X" % (i * 4, fn))
            break
        frva = fn - base
        foff = pe.get_offset_from_rva(frva)
        blob = data[foff : foff + 24]
        insns = list(md.disasm(blob, frva))
        # keep only short getters
        texti = "; ".join("%s %s" % (ins.mnemonic, ins.op_str) for ins in insns[:6])
        interesting = any(op in texti for op in ("+ 0x", "[ecx", "[esi", "[eax"))
        short = any(ins.mnemonic == "ret" for ins in insns[:5])
        if short and interesting:
            lines.append("+0x%03X  0x%X  %s" % (i * 4, frva, texti))
    return "\n".join(lines)


def dis_one(data, pe, rva, n=25):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    off = pe.get_offset_from_rva(rva)
    blob = data[off : off + 0x80]
    lines = []
    for ins in md.disasm(blob, rva):
        lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret" and len(lines) > 2:
            break
        if len(lines) >= n:
            break
    return "\n".join(lines)


def main():
    path = r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll"
    data, pe = load(path)
    names = [
        b".?AVCUnit@@",
        b".?AVCOrder@@",
        b".?AVCOrderTarget@@",
        b".?AVCOrderPoint@@",
        b".?AVCAbilityMove@@",
        b".?AVCWidget@@",
        b".?AVCAbilityAttack@@",
    ]
    # also prefix search for path-like
    parts = ["# 1.26 rtti vtables\n"]
    for n in names:
        vts = find_vtable(data, pe, n) or []
        parts.append("## %s vtables %s\n" % (n.decode(), ", ".join(hex(v) for v in vts) or "none"))
        for vt in vts[:2]:
            parts.append("### vt 0x%X getters\n```\n%s\n```\n" % (vt, walk(data, pe, vt, 90)))

    # extra class names containing Path or Waypoint
    blob_names = []
    start = 0
    while True:
        i = data.find(b".?AVC", start)
        if i < 0:
            break
        end = data.find(b"@@", i)
        if end < 0 or end - i > 80:
            start = i + 4
            continue
        name = data[i : end + 2]
        if any(k in name.lower() for k in (b"path", b"way", b"collid", b"move", b"order", b"widget", b"unit")):
            blob_names.append(name.decode("latin1", "replace"))
        start = end + 2
    parts.append("## class names\n")
    for n in sorted(set(blob_names)):
        parts.append("- %s\n" % n)

    for label, rva in (("DataField540", 0x29C540), ("DataField580", 0x29C580), ("PosConvert", 0x4885A0)):
        parts.append("## %s\n```\n%s\n```\n" % (label, dis_one(data, pe, rva, 30)))

    # spot-check older GetUnitFlyHeight / CurrentOrder / X call
    pe.close()
    (OUT / "1.26-rtti.md").write_text("".join(parts), encoding="utf-8")
    print("classes", len(set(blob_names)))
    print("wrote rtti")

    # older versions field offsets via fly height and current order
    old = [
        ("1.0.17", r"D:\Qt\workspace\War3Launcher\versions\1.0.17.5988\game.dll", 0x2C0FB0, 0x2C53F0, 0x2BF640, 0x2BFD90),
        ("1.21", r"D:\Qt\workspace\War3Launcher\versions\1.21.0.6263\game.dll", 0x2C46A0, 0x2C8AE0, 0x2C2D30, 0x2C3480),
        ("1.24.4", r"D:\Qt\workspace\War3Launcher\versions\1.24.4.6387\game.dll", 0x3C68E0, 0x3C82C0, 0x3C6050, 0x3C6350),
    ]
    oparts = ["# older offset spot check\n"]
    for tag, p, fly, order, ux, ms in old:
        d, pe2 = load(p)
        oparts.append("## %s\n### fly\n```\n%s\n```\n### order\n```\n%s\n```\n### x\n```\n%s\n```\n### speed\n```\n%s\n```\n" % (
            tag, dis_one(d, pe2, fly, 18), dis_one(d, pe2, order, 40), dis_one(d, pe2, ux, 22), dis_one(d, pe2, ms, 28)))
        pe2.close()
    (OUT / "older-spot.md").write_text("".join(oparts), encoding="utf-8")
    print("wrote older")


if __name__ == "__main__":
    main()
