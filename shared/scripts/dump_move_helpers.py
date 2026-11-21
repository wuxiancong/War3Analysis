#!/usr/bin/env python3
"""Proper RVA disassembly of movement helpers. 1.27 raw!=va."""
import struct
from pathlib import Path

import capstone
import pefile

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")


def load(path):
    data = Path(path).read_bytes()
    pe = pefile.PE(path, fast_load=True)
    return data, pe


def rva_to_off(pe, rva):
    return pe.get_offset_from_rva(rva)


def disasm(data, pe, rva, n=160, stop_rets=3):
    off = rva_to_off(pe, rva)
    blob = data[off : off + 0x800]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    lines = []
    rets = 0
    for ins in md.disasm(blob, rva):
        lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic in ("ret", "retn"):
            rets += 1
            if rets >= stop_rets:
                break
        if len(lines) >= n:
            break
    return "\n".join(lines)


def main():
    targets = {
        "1.26.0.6401": {
            "path": r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll",
            "funcs": {
                "GetWidgetWorldPos": (0x4743A0, 40, 1),
                "MoveSpeedGetter": (0x26DE20, 80, 2),
                "MoveSpeedSetter": (0x26DE00, 40, 1),
                "DefaultMoveHero": (0x26EAF0, 80, 2),
                "UnitDataLookup": (0x29C500, 50, 2),
                "TurnSpeedRead": (0x474B10, 40, 1),
                "FacingConvert": (0x6EEE20, 40, 2),
                "GetUnitDefaultMoveSpeed_tail": (0x3C58EF, 40, 2),
                "AcquireRange": (0x276A00, 50, 2),
                "JassHandleToUnit": (0x3BDCB0, 60, 2),
                "ResolveAgent": (0x4786B0, 40, 2),
            },
        },
        "1.27.0.52240": {
            "path": r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll",
            "funcs": {
                "GetUnitX": (0x1E66B0, 40, 2),
                "GetUnitY": (0x1E66F0, 40, 2),
                "GetUnitFacing": (0x1E6130, 80, 2),
                "GetUnitMoveSpeed": (0x1E62E0, 80, 2),
                "GetUnitDefaultMoveSpeed": (0x1E6040, 90, 2),
                "GetUnitCurrentOrder": (0x1E5F80, 70, 2),
                "GetUnitTurnSpeed": (0x1E6640, 40, 2),
                "GetUnitFlyHeight": (0x1E61A0, 30, 2),
                "GetWidgetWorldPos": (0x03B720, 40, 1),
                "GetUnitTypeId": (0x1E6670, 25, 2),
                "JassHandleToUnit": (0x1D1550, 50, 2),
            },
        },
    }
    for ver, spec in targets.items():
        data, pe = load(spec["path"])
        parts = ["# %s helpers\n" % ver]
        for name, (rva, n, rets) in spec["funcs"].items():
            try:
                body = disasm(data, pe, rva, n=n, stop_rets=rets)
            except Exception as e:
                body = "ERR %s" % e
            parts.append("## %s 0x%X\n```\n%s\n```\n" % (name, rva, body))
        (OUT / ("%s-helpers.md" % ver)).write_text("\n".join(parts), encoding="utf-8")
        print("wrote", ver)
        pe.close()


if __name__ == "__main__":
    main()
