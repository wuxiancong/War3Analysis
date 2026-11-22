#!/usr/bin/env python3
"""Deepen pathing: walk vtables, find CLrPath ctors/xrefs, merge DotA collision."""
from __future__ import annotations
import json, struct
from pathlib import Path
import pefile, capstone

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-collision")
VERSIONS = {
    "1.24.4.6387": (Path(r"D:\Qt\workspace\War3Launcher\versions\1.24.4.6387\game.dll"), {
        "CMoveReq": 0x93C170, "CAbilityMove": 0x93C1B4, "CLrPath": 0x9654C4,
        "CLrPathingSys": 0x9656F4, "CLrPathingAcc": 0x964894, "COrderPoint": 0x942104,
    }),
    "1.26.0.6401": (Path(r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll"), {
        "CMoveReq": 0x92A010, "CAbilityMove": 0x92A054, "CLrPath": 0x95336C,
        "CLrPathingSys": 0x95359C, "CLrPathingAcc": 0x95273C, "COrderPoint": 0x92FFA4,
    }),
    "1.27.0.52240": (Path(r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll"), {
        "CMoveReq": 0x970788, "CAbilityMove": 0xA34FD8, "CLrPath": 0x961300,
        "CLrPathingSys": 0x95FFAC, "CLrPathingAcc": 0x960300, "COrderPoint": 0xA4B0C0,
    }),
}


def read_slk(path: Path):
    rows, cur_y = {}, 0
    for line in path.read_text(encoding="latin-1", errors="replace").splitlines():
        if not line.startswith("C;"):
            continue
        x = y = val = None
        for part in line.split(";")[1:]:
            if part.startswith("X"): x = int(part[1:])
            elif part.startswith("Y"): y = int(part[1:])
            elif part.startswith("K"): val = part[1:]
        if y is not None:
            cur_y = y
            if x is None: x = 1
        if x is None or val is None: continue
        if len(val) >= 2 and val[0] == '"' and val[-1] == '"': val = val[1:-1]
        rows.setdefault(cur_y, {})[x] = val
    header = rows.get(1, {})
    table = {}
    for y, r in rows.items():
        if y == 1 or 1 not in r: continue
        table[r[1]] = {header.get(x, str(x)): v for x, v in r.items() if x in header}
    return table


def merge_collision():
    base = Path(r"D:\Qt\workspace\War3Analysis\artifacts\scoring\base")
    layers = [
        base / "war3.mpq" / "Units_UnitBalance.slk",
        base / "War3x.mpq" / "Units_UnitBalance.slk",
        base / "War3Patch.mpq" / "Units_UnitBalance.slk",
        Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Units_UnitBalance.slk"),
    ]
    merged = {}
    for p in layers:
        if not p.exists():
            continue
        for uid, row in read_slk(p).items():
            if "collision" in row and row["collision"] not in ("", "-", "_"):
                merged.setdefault(uid, {})["collision"] = float(row["collision"])
                merged[uid]["layer"] = p.name
            # keep spd too if present
            if "spd" in row and row["spd"] not in ("", "-", "_"):
                merged.setdefault(uid, {})["spd"] = float(row["spd"])
    want = ["esen","edry","ebal","ugho","unec","umtw","Hjai","Usyl","hfoo","opeo","Hamg","Obla"]
    out = {u: merged.get(u, {}) for u in want}
    OUT.joinpath("dota_collision_merged.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def disasm(data, pe, rva, n=100, stop_rets=3):
    off = pe.get_offset_from_rva(rva)
    blob = data[off:off+0xC00]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    lines, rets = [], 0
    for ins in md.disasm(blob, rva):
        lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            rets += 1
            if rets >= stop_rets: break
        if len(lines) >= n: break
    return lines


def walk_vtable(data, pe, vt_rva, slots=40):
    base = pe.OPTIONAL_HEADER.ImageBase
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    tlo = base + text.VirtualAddress
    thi = tlo + max(text.Misc_VirtualSize, 1)
    off = pe.get_offset_from_rva(vt_rva)
    out = []
    for i in range(slots):
        slot = struct.unpack_from("<I", data, off + 4*i)[0]
        if not (tlo <= slot < thi):
            break
        rva = slot - base
        # classify tiny getters
        blob = data[pe.get_offset_from_rva(rva): pe.get_offset_from_rva(rva)+16]
        kind = "fn"
        if blob[:3] == b"\x8D\x41" or blob[:3] == b"\x8D\x81":
            kind = "lea"
        elif blob[0] == 0xB8:
            kind = "ret_imm"
        out.append({"slot": i, "rva": rva, "kind": kind})
    return out


def xrefs_to_va(data, pe, va, limit=40):
    """Find .text references to absolute VA (vtable installs etc.)."""
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    blob = data[text.PointerToRawData: text.PointerToRawData + text.SizeOfRawData]
    pat = struct.pack("<I", va & 0xFFFFFFFF)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    hits = []
    start = 0
    while len(hits) < limit:
        i = blob.find(pat, start)
        if i < 0: break
        win = max(0, i-12)
        rva = text.VirtualAddress + win
        for ins in md.disasm(blob[win:win+32], rva):
            if pat in ins.bytes:
                hits.append({"rva": ins.address, "dis": "%s %s" % (ins.mnemonic, ins.op_str)})
                break
        start = i + 1
    return hits


def find_ctor_near(data, pe, xref_rva):
    """Walk back from vtable install to function start, dump body."""
    off = pe.get_offset_from_rva(xref_rva)
    start = max(0, off - 0x200)
    blob = data[start:off+1]
    fn = xref_rva
    for sig in (b"\x55\x8B\xEC", b"\x55\x89\xE5", b"\x53\x56\x57", b"\x56\x8B\xF1", b"\x51\x53\x56"):
        j = blob.rfind(sig)
        if j >= 0:
            fn = xref_rva - (off - start - j)
            break
    return fn, disasm(data, pe, fn, n=120, stop_rets=2)


def analyze(ver, path, vts):
    data = path.read_bytes()
    pe = pefile.PE(str(path), fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    parts = ["# %s deep pathing\n" % ver]
    summary = {"version": ver, "vtables": {}, "xrefs": {}, "ctors": {}}
    for name, vt in vts.items():
        slots = walk_vtable(data, pe, vt, slots=48)
        summary["vtables"][name] = [{"slot": s["slot"], "rva": "0x%X" % s["rva"], "kind": s["kind"]} for s in slots]
        parts.append("## %s vt 0x%X (%d slots)\n" % (name, vt, len(slots)))
        for s in slots[:24]:
            parts.append("- [%02d] 0x%X %s\n" % (s["slot"], s["rva"], s["kind"]))
        # xrefs to vtable VA
        xrefs = xrefs_to_va(data, pe, base + vt, limit=25)
        summary["xrefs"][name] = [{"rva": "0x%X" % x["rva"], "dis": x["dis"]} for x in xrefs]
        parts.append("### xrefs to vt (%d)\n" % len(xrefs))
        for x in xrefs[:15]:
            parts.append("- 0x%X  %s\n" % (x["rva"], x["dis"]))
        # first few mov [reg], vt as ctor candidates
        for x in xrefs[:5]:
            if "mov" in x["dis"] and ("dword ptr" in x["dis"] or "[" in x["dis"]):
                fn, body = find_ctor_near(data, pe, x["rva"])
                summary["ctors"].setdefault(name, []).append({"xref": "0x%X" % x["rva"], "fn": "0x%X" % fn})
                parts.append("### ctor-ish @ 0x%X (from xref 0x%X)\n```\n%s\n```\n" % (fn, x["rva"], "\n".join(body)))
                break
        # dump a few medium slots (not lea/ret_imm) — likely real methods
        interesting = [s for s in slots if s["kind"] == "fn"][:6]
        for s in interesting:
            body = disasm(data, pe, s["rva"], n=50, stop_rets=2)
            parts.append("### method slot%d @ 0x%X\n```\n%s\n```\n" % (s["slot"], s["rva"], "\n".join(body)))
    # Look for path cell size: push 0x20 / cmp with 32 near CLrPathingSys methods
    # Search float 32.0 xrefs from rdata into text near pathing — light
    OUT.joinpath("%s-deep.md" % ver).write_text("".join(parts), encoding="utf-8")
    pe.close()
    return summary


def main():
    coll = merge_collision()
    print("merged collision:")
    for k,v in coll.items():
        print(" ", k, v)
    alls = {}
    for ver,(path,vts) in VERSIONS.items():
        print("deep", ver)
        alls[ver] = analyze(ver, path, vts)
        for name, ctors in alls[ver]["ctors"].items():
            print(" ", name, "ctors", ctors)
    OUT.joinpath("deep_summary.json").write_text(json.dumps(alls, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
