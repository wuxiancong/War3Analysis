#!/usr/bin/env python3
import struct
from pathlib import Path
import capstone
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")


def disasm(path, items, title):
    data = Path(path).read_bytes()
    pe = pefile.PE(path, fast_load=True)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    parts = ["# %s\n" % title]
    for name, rva, n, rets in items:
        off = pe.get_offset_from_rva(rva)
        blob = data[off : off + 0x500]
        lines = []
        seen_ret = 0
        for ins in md.disasm(blob, rva):
            lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
            if ins.mnemonic == "ret":
                seen_ret += 1
                if seen_ret >= rets:
                    break
            if len(lines) >= n:
                break
        parts.append("## %s 0x%X\n```\n%s\n```\n" % (name, rva, "\n".join(lines)))
    # facing scale constant
    (OUT / ("%s.md" % title)).write_text("\n".join(parts), encoding="utf-8")
    pe.close()
    print("wrote", title)


def main():
    disasm(
        r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll",
        [
            ("PosExtractA", 0x497460, 40, 2),
            ("PosExtractB", 0x38B0B0, 40, 2),
            ("AmovSpeedInner", 0x2019F0, 50, 2),
            ("FacingMaybe", 0x4742F0, 5, 1),
        ],
        "1.26-pos",
    )
    disasm(
        r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll",
        [
            ("PosExtractA", 0x10D790, 40, 2),
            ("PosExtractB", 0x3EBF0, 40, 2),
            ("AmovSpeedInner", 0x5DF170, 50, 2),
            ("FacingRead", 0x3D840, 30, 1),
        ],
        "1.27-pos",
    )


if __name__ == "__main__":
    main()
