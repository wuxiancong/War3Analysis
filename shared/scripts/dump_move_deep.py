#!/usr/bin/env python3
"""Follow position, speed, facing, and order field reads."""
import struct
from pathlib import Path

import capstone
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")


def load(path):
    data = Path(path).read_bytes()
    pe = pefile.PE(path, fast_load=True)
    return data, pe


def disasm(data, pe, rva, n=120, stop_rets=2):
    off = pe.get_offset_from_rva(rva)
    blob = data[off : off + 0x900]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    lines = []
    rets = 0
    for ins in md.disasm(blob, rva):
        lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            rets += 1
            if rets >= stop_rets:
                break
        if len(lines) >= n:
            break
    return "\n".join(lines)


def main():
    specs = [
        (
            "1.26-deep",
            r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll",
            {
                "WorldPosFill": (0x4742F0, 80, 2),
                "AmovGetSpeed": (0x201C60, 60, 2),
                "AmovSetSpeed": (0x202F30, 80, 2),
                "HeroDefaultSpeed": (0x208170, 50, 2),
                "IssuePointOrderById": (0x3C8900, 100, 2),
                "AgentLookup": (0x3FA30, 40, 2),
                "FloatMul": (0x6EF000, 20, 1),
            },
        ),
        (
            "1.27-deep",
            r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll",
            {
                "WorldPosFill": (0x3D790, 80, 2),
                "AmovGetSpeed": (0x667BE0, 50, 2),
                "HeroDefaultSpeedCaller": (0x667BC0, 30, 2),
                "TurnSpeedRead": (0x3E0A0, 30, 2),
            },
        ),
    ]
    for name, path, funcs in specs:
        data, pe = load(path)
        parts = ["# %s\n" % name]
        for fn, (rva, n, rets) in funcs.items():
            body = disasm(data, pe, rva, n=n, stop_rets=rets)
            parts.append("## %s 0x%X\n```\n%s\n```\n" % (fn, rva, body))
        # fourcc hits
        for tag in (b"umvs", b"ucol", b"umvh", b"uprw", b"utur", b"uacq", b"upat", b"ucar", b"ucbo"):
            # stored as raw 4 bytes in source order
            c1 = data.find(tag)
            # little-endian dword of the fourcc interpreted as big-endian char constant
            le = tag[::-1]
            c2 = data.find(le)
            parts.append("fourcc %s raw=%s rev=%s\n" % (tag.decode(), hex(c1) if c1 >= 0 else "-", hex(c2) if c2 >= 0 else "-"))
        (OUT / ("%s.md" % name)).write_text("\n".join(parts), encoding="utf-8")
        print("wrote", name, "image", hex(pe.OPTIONAL_HEADER.ImageBase))
        pe.close()


if __name__ == "__main__":
    main()
