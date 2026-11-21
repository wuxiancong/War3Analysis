#!/usr/bin/env python3
"""COrderPoint stores, CMoveReq, collision-sized field readers, 1.21 inner offsets."""
import struct
from pathlib import Path

import capstone
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")
PATH = r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll"


def main():
    data = Path(PATH).read_bytes()
    pe = pefile.PE(PATH, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    parts = []

    def dis(rva, n=40):
        off = pe.get_offset_from_rva(rva)
        blob = data[off : off + n * 8]
        lines = []
        for ins in md.disasm(blob, rva):
            lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
            if len(lines) >= n:
                break
            if ins.mnemonic == "ret" and len(lines) > 8:
                break
        return "\n".join(lines)

    # COrderPoint vtable VA
    vt = base + 0x92FFA4
    pat = struct.pack("<I", vt)
    hits = []
    start = 0
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    tblob = data[text.PointerToRawData : text.PointerToRawData + text.SizeOfRawData]
    trva = text.VirtualAddress
    while True:
        i = tblob.find(pat, start)
        if i < 0:
            break
        hits.append(trva + i)
        start = i + 1
        if len(hits) > 15:
            break
    parts.append("# order vtable xrefs %d\n" % len(hits))
    for h in hits[:6]:
        parts.append("## xref 0x%X\n```\n%s\n```\n" % (h - 6, dis(h - 8, 35)))

    # CMoveReq vtable
    name = b".?AVCMoveReq@@"
    idx = data.find(name)
    parts.append("CMoveReq name off 0x%X\n" % idx)

    # scan fld/mov from +0x2CC and +0x2C8 within text, print function-ish context
    for disp_name, disp in (("2CC", b"\xCC\x02\x00\x00"), ("2C8", b"\xC8\x02\x00\x00"), ("2D0", b"\xD0\x02\x00\x00")):
        c = tblob.count(disp)
        parts.append("disp %s count %d\n" % (disp_name, c))

    # unit data field offsets: find call 0x29A8C0 followed within 16 bytes by [eax+disp]
    # E8 rel32 to 0x29A8C0
    target = 0x29A8C0
    fields = []
    i = 0
    while True:
        j = tblob.find(b"\xE8", i)
        if j < 0 or j + 5 > len(tblob):
            break
        rel = struct.unpack_from("<i", tblob, j + 1)[0]
        src = trva + j
        dest = src + 5 + rel
        if dest == target:
            window = tblob[j + 5 : j + 24]
            # look for 8B ?? ?? ?? 00 00 or 8B 40 xx or 8B 80 xx xx xx xx
            fields.append((src, window[:16].hex()))
        i = j + 1
    parts.append("## calls to unitdata lookup %d\n" % len(fields))
    # parse displacements after the call: 8B 48 xx xx xx xx = mov ecx,[eax+disp] if modrm is 0x80/0x88 etc
    disps = {}
    for src, hx in fields:
        off = pe.get_offset_from_rva(src)
        window = data[off + 5 : off + 20]
        # mov r32, [eax+disp32] is 8B modrm disp32 with modrm mod=10 rm=000
        for k in range(len(window) - 6):
            if window[k] == 0x8B and window[k + 1] in (0x80, 0x88, 0x90, 0x98, 0x40, 0x48, 0x50, 0x58, 0x68, 0x70, 0x78):
                modrm = window[k + 1]
                mod = modrm >> 6
                rm = modrm & 7
                if rm != 0:  # want eax
                    continue
                if mod == 2:
                    disp = struct.unpack_from("<I", window, k + 2)[0]
                    disps.setdefault(disp, []).append(src)
                elif mod == 1:
                    disp = window[k + 2]
                    disps.setdefault(disp, []).append(src)
                break
    parts.append("field disps:\n")
    for d in sorted(disps):
        parts.append("- +0x%X  sites %s\n" % (d, ", ".join(hex(s) for s in disps[d][:4])))

    (OUT / "1.26-order-fields.md").write_text("".join(parts), encoding="utf-8")
    print("xrefs", len(hits), "fields", len(disps))
    pe.close()


if __name__ == "__main__":
    main()
