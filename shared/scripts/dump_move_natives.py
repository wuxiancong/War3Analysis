#!/usr/bin/env python3
"""Disassemble movement natives for 1.26 and 1.27, and list RVAs for all versions."""
import struct
from pathlib import Path

import capstone
import pefile

ROOT = Path(r"D:\Qt\workspace\War3Launcher\versions")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-movement")
OUT.mkdir(parents=True, exist_ok=True)

NAMES = [
    "GetUnitX",
    "GetUnitY",
    "GetUnitFacing",
    "GetUnitMoveSpeed",
    "GetUnitDefaultMoveSpeed",
    "GetUnitCurrentOrder",
    "GetUnitTurnSpeed",
    "GetUnitDefaultTurnSpeed",
    "GetUnitFlyHeight",
    "GetUnitDefaultFlyHeight",
    "GetUnitAcquireRange",
    "GetUnitDefaultAcquireRange",
    "GetUnitPropWindow",
    "GetUnitDefaultPropWindow",
    "SetUnitMoveSpeed",
    "SetUnitFacing",
    "SetUnitX",
    "SetUnitY",
    "SetUnitPosition",
    "SetUnitPathing",
    "GetUnitTypeId",
    "GetUnitState",
    "GetWidgetLife",
]


def file_rva(pe, file_off):
    for s in pe.sections:
        raw, size = s.PointerToRawData, s.SizeOfRawData
        if raw <= file_off < raw + size:
            return s.VirtualAddress + (file_off - raw)
    return None


def find_cstr_rva(data, pe, name):
    needle = name.encode() + b"\x00"
    start = 0
    hits = []
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        prev = data[i - 1] if i else 0
        if prev == 0:
            rva = file_rva(pe, i)
            if rva is not None:
                hits.append(rva)
        start = i + 1
    return hits


def find_func(data, image_base, str_rva):
    """mov edx, nameVA ; mov ecx, funcVA"""
    va = image_base + str_rva
    pat = b"\xBA" + struct.pack("<I", va) + b"\xB9"
    funcs = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        func_va = struct.unpack_from("<I", data, i + 6)[0]
        funcs.append(func_va - image_base)
        start = i + 1
    # also mov edx via other regs? keep unique
    uniq = []
    for f in funcs:
        if f not in uniq and 0x1000 < f < 0x900000:
            uniq.append(f)
    return uniq


def disasm_until(data, rva, limit=220):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    blob = data[rva : rva + 0x600]
    lines = []
    rets = 0
    for ins in md.disasm(blob, rva):
        lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            rets += 1
            if rets >= 2 or (rets == 1 and len(lines) > 25):
                break
        if len(lines) >= limit:
            break
    return "\n".join(lines)


def main():
    versions = sorted(p for p in ROOT.iterdir() if p.is_dir())
    rows = []
    for ver_dir in versions:
        dlls = list(ver_dir.glob("game.dll")) + list(ver_dir.glob("Game.dll"))
        if not dlls:
            continue
        path = dlls[0]
        data = path.read_bytes()
        pe = pefile.PE(str(path), fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        ver = ver_dir.name
        mapping = {}
        for name in NAMES:
            rvas = find_cstr_rva(data, pe, name)
            funcs = []
            for sr in rvas:
                funcs.extend(find_func(data, base, sr))
            # drop the shared stub: the RVA that appears for many different names
            mapping[name] = funcs
        # choose primary: first func that is not the mode of all funcs
        from collections import Counter
        cnt = Counter()
        for fs in mapping.values():
            for f in fs:
                cnt[f] += 1
        stub = cnt.most_common(1)[0][0] if cnt and cnt.most_common(1)[0][1] > 3 else None
        print("==", ver, "stub", hex(stub) if stub else None)
        chosen = {}
        for name, fs in mapping.items():
            primary = None
            for f in fs:
                if f != stub:
                    primary = f
                    break
            if primary is None and fs:
                primary = fs[0]
            chosen[name] = primary
            print("  %-32s %s" % (name, hex(primary) if primary else "MISS"))
        rows.append((ver, chosen, data))
        pe.close()

    # write rva table
    header = ["version"] + NAMES
    lines = ["\t".join(header)]
    for ver, chosen, _ in rows:
        lines.append("\t".join([ver] + [("0x%X" % chosen[n]) if chosen[n] else "" for n in NAMES]))
    (OUT / "native-rvas.tsv").write_text("\n".join(lines), encoding="utf-8")

    # detailed dump for 1.26 and 1.27
    focus = {
        "GetUnitX",
        "GetUnitY",
        "GetUnitFacing",
        "GetUnitMoveSpeed",
        "GetUnitDefaultMoveSpeed",
        "GetUnitCurrentOrder",
        "SetUnitMoveSpeed",
        "SetUnitPathing",
        "GetUnitTurnSpeed",
        "GetUnitFlyHeight",
        "GetUnitAcquireRange",
        "GetUnitTypeId",
    }
    for ver, chosen, data in rows:
        if ver not in ("1.26.0.6401", "1.27.0.52240", "1.24.4.6387", "1.21.0.6263"):
            continue
        parts = ["# %s\n" % ver]
        for name in NAMES:
            if name not in focus:
                continue
            rva = chosen[name]
            if not rva:
                parts.append("## %s MISSING\n" % name)
                continue
            body = disasm_until(data, rva)
            parts.append("## %s 0x%X\n```\n%s\n```\n" % (name, rva, body))
        (OUT / ("%s-disasm.md" % ver)).write_text("\n".join(parts), encoding="utf-8")
        print("wrote", ver)


if __name__ == "__main__":
    main()
