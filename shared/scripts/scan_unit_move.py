#!/usr/bin/env python3
"""Locate JASS movement natives in every game.dll and dump their disassembly."""
import struct
import sys
from pathlib import Path

import capstone
import pefile

ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
NAMES = [
    "GetUnitX",
    "GetUnitY",
    "GetUnitFacing",
    "GetUnitMoveSpeed",
    "GetUnitDefaultMoveSpeed",
    "GetUnitCurrentOrder",
    "GetUnitAcquireRange",
    "GetUnitFlyHeight",
    "GetUnitTurnSpeed",
    "GetUnitPropWindow",
    "GetUnitState",
    "GetUnitTypeId",
    "SetUnitMoveSpeed",
    "SetUnitFacing",
    "SetUnitPosition",
    "IssuePointOrderById",
    "GetUnitX",
]
# unique preserve order
SEEN = []
for n in NAMES:
    if n not in SEEN:
        SEEN.append(n)
NAMES = SEEN

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")
OUT.mkdir(parents=True, exist_ok=True)


def section_span(pe):
    spans = []
    for s in pe.sections:
        va = s.VirtualAddress
        size = max(s.Misc_VirtualSize, s.SizeOfRawData)
        spans.append((va, va + size, s.Name.split(b"\x00")[0].decode("latin1"), s.PointerToRawData, s.SizeOfRawData))
    return spans


def rva_of_file(pe, file_off):
    for s in pe.sections:
        raw = s.PointerToRawData
        size = s.SizeOfRawData
        if raw <= file_off < raw + size:
            return s.VirtualAddress + (file_off - raw)
    return None


def file_of_rva(pe, rva):
    for s in pe.sections:
        va = s.VirtualAddress
        size = max(s.Misc_VirtualSize, s.SizeOfRawData)
        if va <= rva < va + size:
            delta = rva - va
            if delta < s.SizeOfRawData:
                return s.PointerToRawData + delta
    return None


def find_string_rvas(data, pe, text):
    needle = text.encode("ascii") + b"\x00"
    hits = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        # reject if previous byte is alphanumeric (substring)
        if i == 0 or not (48 <= data[i - 1] <= 122):
            rva = rva_of_file(pe, i)
            if rva is not None:
                hits.append(rva)
        start = i + 1
    return hits


def find_native(data, pe, image_base, name):
    """NativeFuncNode: pszName at +0x18, pImplementation at +0x1C."""
    str_rvas = find_string_rvas(data, pe, name)
    results = []
    for srva in str_rvas:
        va = image_base + srva
        pat = struct.pack("<I", va)
        start = 0
        while True:
            i = data.find(pat, start)
            if i < 0:
                break
            start = i + 1
            # implementation sits 4 bytes after the name pointer
            if i + 8 > len(data):
                continue
            impl_va = struct.unpack_from("<I", data, i + 4)[0]
            if impl_va < image_base or impl_va > image_base + 0x2000000:
                continue
            impl_rva = impl_va - image_base
            off = file_of_rva(pe, impl_rva)
            if off is None:
                continue
            # code should start with a typical prologue or at least be in executable section
            b0 = data[off]
            if b0 not in (0x55, 0x53, 0x56, 0x57, 0x8B, 0x83, 0x51, 0x6A, 0x68, 0xA1, 0xB8, 0x33, 0x31, 0xE8, 0xFF, 0xC3, 0x83, 0x81):
                continue
            node_off = i - 0x18
            results.append((impl_rva, srva, node_off))
    # dedupe by impl
    uniq = []
    seen = set()
    for r in results:
        if r[0] in seen:
            continue
        seen.add(r[0])
        uniq.append(r)
    return uniq


def disasm_func(data, pe, rva, max_bytes=0x400, max_ins=180):
    off = file_of_rva(pe, rva)
    if off is None:
        return []
    blob = data[off : off + max_bytes]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False
    out = []
    for ins in md.disasm(blob, rva):
        out.append(ins)
        if len(out) >= max_ins:
            break
        if ins.mnemonic == "ret" and len(out) > 3:
            # stop at first ret after a short body; continue if it's a tiny stub
            if len(out) > 8:
                break
    return out


def fmt(insns):
    lines = []
    for i in insns:
        lines.append("%08X  %-8s %s" % (i.address, i.mnemonic, i.op_str))
    return "\n".join(lines)


def main():
    versions = sorted([p for p in ROOT.iterdir() if p.is_dir()])
    summary = []
    for ver_dir in versions:
        dlls = list(ver_dir.glob("game.dll")) + list(ver_dir.glob("Game.dll"))
        if not dlls:
            continue
        path = dlls[0]
        data = path.read_bytes()
        pe = pefile.PE(str(path), fast_load=True)
        image_base = pe.OPTIONAL_HEADER.ImageBase
        ver = ver_dir.name
        print("===", ver, "base", hex(image_base), "size", hex(len(data)))
        found = {}
        for name in NAMES:
            hits = find_native(data, pe, image_base, name)
            found[name] = hits
            if hits:
                print("  %-28s %s" % (name, ", ".join("0x%X" % h[0] for h in hits)))
            else:
                print("  %-28s NOT FOUND" % name)
        # disassemble the primary hits for the movement natives
        dump_names = [
            "GetUnitX",
            "GetUnitY",
            "GetUnitFacing",
            "GetUnitMoveSpeed",
            "GetUnitDefaultMoveSpeed",
            "GetUnitCurrentOrder",
            "GetUnitTurnSpeed",
            "SetUnitMoveSpeed",
        ]
        parts = ["# %s image_base=0x%08X\n" % (ver, image_base)]
        for name in dump_names:
            hits = found.get(name) or []
            if not hits:
                parts.append("## %s MISSING\n" % name)
                continue
            rva = hits[0][0]
            insns = disasm_func(data, pe, rva)
            parts.append("## %s RVA 0x%X (%d ins)\n```\n%s\n```\n" % (name, rva, len(insns), fmt(insns)))
        outp = OUT / ("%s-natives.md" % ver)
        outp.write_text("\n".join(parts), encoding="utf-8")
        summary.append((ver, found))
        pe.close()

    # compact tsv
    lines = ["version\tname\trva"]
    for ver, found in summary:
        for name, hits in found.items():
            rva = hits[0][0] if hits else 0
            lines.append("%s\t%s\t0x%X" % (ver, name, rva))
    (OUT / "native-rvas.tsv").write_text("\n".join(lines), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
