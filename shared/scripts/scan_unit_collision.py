#!/usr/bin/env python3
"""Reverse WC3 unit collision + repath markers across game.dll versions."""
from __future__ import annotations
import json, struct, re
from pathlib import Path
import pefile
import capstone

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-collision")
VERSIONS = {
    "1.24.4.6387": Path(r"D:\Qt\workspace\War3Launcher\versions\1.24.4.6387\game.dll"),
    "1.26.0.6401": Path(r"D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll"),
    "1.27.0.52240": Path(r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll"),
}

RTTI_NAMES = [
    b".?AVCMoveReq@@",
    b".?AVCPathingFootprint@@",
    b".?AVCPathingMapIndicator@@",
    b".?AVCAbilityMove@@",
    b".?AVCLrPath@NIpse@@",
    b".?AVCLrPathingAcc@NIpse@@",
    b".?AVCLrPathingSys@NIpse@@",
    b".?AVCOrderPoint@@",
    b".?AVCOrderPoint2@@",
]

STRINGS = [
    b"ucol",
    b"collision",
    b"Collision",
    b"pathing",
    b"Pathing",
    b"CMoveReq",
]


def read_slk(path: Path):
    rows, cur_y = {}, 0
    text = path.read_text(encoding="latin-1", errors="replace")
    for line in text.splitlines():
        if not line.startswith("C;"):
            continue
        x = y = val = None
        for part in line.split(";")[1:]:
            if part.startswith("X"):
                x = int(part[1:])
            elif part.startswith("Y"):
                y = int(part[1:])
            elif part.startswith("K"):
                val = part[1:]
        if y is not None:
            cur_y = y
            if x is None:
                x = 1
        if x is None or val is None:
            continue
        if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
            val = val[1:-1]
        rows.setdefault(cur_y, {})[x] = val
    header = rows.get(1, {})
    table = {}
    for y, r in rows.items():
        if y == 1 or 1 not in r:
            continue
        table[r[1]] = {header.get(x, str(x)): v for x, v in r.items() if x in header or x == 1}
    return table


def extract_slk_collision():
    map_dir = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
    # Prefer UnitBalance; fall back UnitData / UnitUI
    candidates = [
        map_dir / "Units_UnitBalance.slk",
        map_dir / "Units_UnitData.slk",
        map_dir / "Units_UnitUI.slk",
        map_dir / "Units" / "UnitBalance.slk",
    ]
    # Also look for scoring merge inputs
    for p in Path(r"D:\Qt\workspace\War3Analysis\artifacts\scoring").rglob("*UnitBalance*"):
        candidates.append(p)
    found = {}
    for p in candidates:
        if not p.exists():
            continue
        t = read_slk(p)
        sample = {}
        for uid in ("esen", "edry", "ebal", "ugho", "unec", "umtw", "Hjai", "Usyl", "hfoo", "opeo"):
            if uid in t:
                row = t[uid]
                # common keys
                col = None
                for k in row:
                    if str(k).lower() in ("collision", "ucol", "collisionsize"):
                        col = row[k]
                        break
                sample[uid] = {"collision": col, "keys": list(row.keys())[:20], "row_sample": {k: row[k] for k in list(row)[:12]}}
        found[str(p)] = {"count": len(t), "sample": sample, "header_keys": list(next(iter(t.values())).keys())[:40] if t else []}
    OUT.joinpath("slk_collision.json").write_text(json.dumps(found, indent=2, ensure_ascii=False), encoding="utf-8")
    return found


def rva_of_offset(pe, off):
    return pe.get_rva_from_offset(off)


def find_rtti(data, pe, name: bytes):
    base = pe.OPTIONAL_HEADER.ImageBase
    idx = data.find(name + b"\x00")
    if idx < 0:
        return {"name": name.decode(errors="replace"), "td_rva": None}
    td_off = idx - 8
    td_rva = rva_of_offset(pe, td_off)
    # find vtables: dword pointing to COL that points to TD
    td_va = base + td_rva
    pat = struct.pack("<I", td_va)
    cols = []
    start = 0
    while True:
        i = data.find(pat, start)
        if i < 0:
            break
        cols.append(i)
        start = i + 1
        if len(cols) > 12:
            break
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    tlo = base + text.VirtualAddress
    thi = tlo + max(text.Misc_VirtualSize, 1)
    vts = []
    for col_off in cols:
        col_rva = rva_of_offset(pe, col_off)
        for back in range(0, 8):
            col_va = base + col_rva - back * 4
            p = struct.pack("<I", col_va)
            s0 = 0
            while True:
                j = data.find(p, s0)
                if j < 0:
                    break
                s0 = j + 1
                if j + 8 > len(data):
                    continue
                slot0 = struct.unpack_from("<I", data, j + 4)[0]
                if tlo <= slot0 < thi:
                    vt = rva_of_offset(pe, j + 4)
                    if vt not in vts:
                        vts.append(vt)
    return {"name": name.decode(errors="replace"), "td_rva": td_rva, "vtables": vts[:6]}


def xref_imm(data, pe, imm: int, limit=30):
    """Find instructions that load immediate pointing to RVA/VA."""
    base = pe.OPTIONAL_HEADER.ImageBase
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    t_off = text.PointerToRawData
    t_size = max(text.SizeOfRawData, 1)
    blob = data[t_off : t_off + t_size]
    va0 = base + text.VirtualAddress
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False
    hits = []
    # search for little-endian imm bytes
    for target in (imm, base + imm if imm < 0x1000000 else imm):
        pat = struct.pack("<I", target & 0xFFFFFFFF)
        start = 0
        while len(hits) < limit:
            i = blob.find(pat, start)
            if i < 0:
                break
            # disasm a window starting a bit before
            win = max(0, i - 16)
            rva = text.VirtualAddress + win
            for ins in md.disasm(blob[win : win + 32], rva):
                if pat in ins.bytes:
                    hits.append({"rva": ins.address, "dis": "%s %s" % (ins.mnemonic, ins.op_str)})
                    break
            start = i + 1
    return hits


def disasm(data, pe, rva, n=80, stop_rets=2):
    off = pe.get_offset_from_rva(rva)
    blob = data[off : off + 0x800]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    lines, rets = [], 0
    for ins in md.disasm(blob, rva):
        lines.append("%08X  %-8s %s" % (ins.address, ins.mnemonic, ins.op_str))
        if ins.mnemonic == "ret":
            rets += 1
            if rets >= stop_rets:
                break
        if len(lines) >= n:
            break
    return lines


def find_ucol_loads(data, pe):
    """Find 'ucol' fourcc (LE dword) loads in .text — unit data field id."""
    # fourcc 'ucol' as big-endian char constant in source is often stored LE as 'locu'
    tag = b"ucol"
    le = tag[::-1]
    hits = {"raw_off": data.find(tag), "rev_off": data.find(le)}
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    t_off = text.PointerToRawData
    blob = data[t_off : t_off + text.SizeOfRawData]
    imm = struct.unpack("<I", le)[0]
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    sites = []
    start = 0
    while len(sites) < 40:
        i = blob.find(struct.pack("<I", imm), start)
        if i < 0:
            break
        win = max(0, i - 8)
        rva = text.VirtualAddress + win
        for ins in md.disasm(blob[win : win + 24], rva):
            if struct.pack("<I", imm) in ins.bytes:
                sites.append({"rva": "0x%X" % ins.address, "dis": "%s %s" % (ins.mnemonic, ins.op_str)})
                break
        start = i + 1
    hits["imm_sites"] = sites
    return hits


def scan_float32_constants(data, pe, values=(16.0, 32.0, 48.0, 64.0)):
    text = [s for s in pe.sections if s.Name.startswith(b".rdata") or s.Name.startswith(b".data")]
    out = {}
    for v in values:
        pat = struct.pack("<f", v)
        offs = []
        start = 0
        while len(offs) < 20:
            i = data.find(pat, start)
            if i < 0:
                break
            try:
                rva = pe.get_rva_from_offset(i)
            except Exception:
                rva = None
            offs.append({"file_off": i, "rva": ("0x%X" % rva) if rva is not None else None})
            start = i + 1
        out[str(v)] = offs[:12]
    return out


def analyze_version(ver, path: Path):
    data = path.read_bytes()
    pe = pefile.PE(str(path), fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    report = {
        "version": ver,
        "size": len(data),
        "image_base": "0x%X" % pe.OPTIONAL_HEADER.ImageBase,
        "rtti": [],
        "ucol": find_ucol_loads(data, pe),
        "strings": {},
    }
    for name in RTTI_NAMES:
        report["rtti"].append(find_rtti(data, pe, name))
    for s in STRINGS:
        report["strings"][s.decode()] = data.find(s)
    # For each found CMoveReq / CLrPath vtable, dump first slots
    md_parts = ["# %s collision/pathing scan\n" % ver]
    for r in report["rtti"]:
        md_parts.append("## %s\n- td_rva: %s\n- vtables: %s\n" % (
            r["name"],
            ("0x%X" % r["td_rva"]) if r["td_rva"] is not None else "none",
            ", ".join("0x%X" % v for v in r.get("vtables") or []) or "none",
        ))
        for vt in (r.get("vtables") or [])[:2]:
            # dump slot0 function start
            base = pe.OPTIONAL_HEADER.ImageBase
            off = pe.get_offset_from_rva(vt)
            slot0 = struct.unpack_from("<I", data, off)[0] - base
            lines = disasm(data, pe, slot0, n=40, stop_rets=1)
            md_parts.append("### vtable 0x%X slot0 -> 0x%X\n```\n%s\n```\n" % (vt, slot0, "\n".join(lines)))
    # Also search for dword 0x20 (32) used near pathing — skip heavy
    md_parts.append("## ucol imm sites (%d)\n" % len(report["ucol"]["imm_sites"]))
    for s in report["ucol"]["imm_sites"][:25]:
        md_parts.append("- %s : %s\n" % (s["rva"], s["dis"]))
    OUT.joinpath("%s-scan.md" % ver).write_text("".join(md_parts), encoding="utf-8")
    # Follow a few ucol sites: disasm surrounding function
    follow = []
    for s in report["ucol"]["imm_sites"][:8]:
        rva = int(s["rva"], 16)
        # walk back to likely function prolog
        off = pe.get_offset_from_rva(rva)
        start = max(0, off - 0x80)
        # find nearest 55 8B EC or 53 8B or CC CC before
        blob = data[start:off]
        fn = rva
        for sig in (b"\x55\x8B\xEC", b"\x55\x89\xE5", b"\xCC\xCC\x55"):
            j = blob.rfind(sig)
            if j >= 0:
                fn = rva - (off - start - j)
                if sig.startswith(b"\xCC"):
                    fn += 2
                break
        follow.append({"site": s["rva"], "fn_guess": "0x%X" % fn, "dis": disasm(data, pe, fn, n=60, stop_rets=2)})
    OUT.joinpath("%s-ucol-funcs.md" % ver).write_text(
        "\n".join("# %s\n## %s (~%s)\n```\n%s\n```\n" % (ver, f["site"], f["fn_guess"], "\n".join(f["dis"])) for f in follow),
        encoding="utf-8",
    )
    report["ucol_follow"] = [{"site": f["site"], "fn_guess": f["fn_guess"]} for f in follow]
    pe.close()
    return report


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    slk = extract_slk_collision()
    print("slk files", len(slk))
    for p, info in slk.items():
        print(" ", Path(p).name, "units", info["count"], "sample_uids", list(info["sample"]))
    all_rep = {}
    for ver, path in VERSIONS.items():
        print("scanning", ver)
        all_rep[ver] = analyze_version(ver, path)
        # summarize rtti
        for r in all_rep[ver]["rtti"]:
            if r["td_rva"] is not None:
                print(" ", r["name"], "td", hex(r["td_rva"]), "vt", [hex(v) for v in r["vtables"]])
        print("  ucol sites", len(all_rep[ver]["ucol"]["imm_sites"]))
    OUT.joinpath("scan_summary.json").write_text(json.dumps(all_rep, indent=2), encoding="utf-8")
    print("done ->", OUT)


if __name__ == "__main__":
    main()
