# -*- coding: utf-8 -*-
"""
单线程轻量探测：
1. DotA 6.83d Units_UnitData.slk / Units_UnitUI.slk 中 Nfir(影魔)、Hjai(冰女) 及常见英雄的 turnRate / propWin
2. 1.27.0.52240 GetUnitFacing 原生入口、内部实现、0x6FB59460 乘数写入者、+0x8C/+0x90 读写链
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import PE32, disasm, dll_path_for

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\stealth-rune-route")
from parse_sight_and_doodads import parse_slk_clean

OUT_DIR = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-facing")
OUT_DIR.mkdir(parents=True, exist_ok=True)
MAP = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")


def find_native_127(pe: PE32, name: str):
    srvas = pe.find_string_rvas(name)
    tsec = pe.get_section(".text")
    for srva in srvas:
        sva = pe.image_base + srva
        refs = pe.find_all_bytes(b"\xBA" + struct.pack("<I", sva), ".text")
        for ref in refs:
            lns = disasm(pe.path, pe.image_base, ref, 0x12)
            for ln in lns[1:4]:
                m = re.search(r"mov\s+ecx,([0-9A-F]{8})h", ln)
                if m:
                    rva = int(m.group(1), 16) - pe.image_base
                    if rva != 0x70A0C0 and tsec.vaddr <= rva < tsec.vaddr + tsec.vsize:
                        return rva
    return None


def main():
    out = []

    # 1. 解析 Units_UnitData.slk & Units_UnitUI.slk 里的 turnRate / propWin
    for fn in ("Units_UnitData.slk", "Units_UnitUI.slk"):
        cols, rows = parse_slk_clean(MAP / fn)
        c2i = {v: k for k, v in cols.items()}
        out.append(f"=== {fn} cols matching turn/prop/mov/spd ===")
        out.append(str({k: v for k, v in c2i.items() if any(w in k.lower() for w in ("turn", "prop", "mov", "unit"))}))
        targets = ["Nfir", "Hjai", "Edem", "Hamg", "Ulic", "Oshd", "N01I", "H001", "ugho", "edry"]
        for y, r in sorted(rows.items()):
            uid = r.get(1, "")
            if uid in targets:
                vals = {k: r.get(c2i[k], "?") for k in ("turnRate", "propWin", "movetp", "moveHeight") if k in c2i}
                out.append(f"  {uid:6s} (Y={y:4d}): {vals}")

    # 2. 1.27 GetUnitFacing 原生与内部调用链
    pe = PE32(dll_path_for("1.27.0.52240"))
    r_guf = find_native_127(pe, "GetUnitFacing")
    r_gux = find_native_127(pe, "GetUnitX")
    out.append(f"\n=== 1.27 GetUnitFacing @ 0x{r_guf:06X} (GetUnitX @ 0x{r_gux:06X}) ===")
    if r_guf:
        lns = disasm(pe.path, pe.image_base, r_guf, 0x60)
        out.extend(lns)
        # 追踪其调用的内部子函数
        for ln in lns:
            m = re.search(r"\bcall\s+([0-9A-F]{8})$", ln)
            if m:
                sub = int(m.group(1), 16) - pe.image_base
                out.append(f"\n--- sub 0x{sub:06X} ---")
                out.extend(disasm(pe.path, pe.image_base, sub, 0x70))

    # 3. 查 1.27 0x6FB59460 (rad->deg 乘数) 的所有 .text 引用（看谁在启动时写入它）
    va_mult = 0x6FB59460
    xrefs = pe.find_xrefs_to_va(va_mult, ".text")
    out.append(f"\n=== 1.27 xrefs to 0x{va_mult:08X} ({len(xrefs)} total) ===")
    for xr in xrefs[:10]:
        out.append(f"  xref @ 0x{xr:06X}:")
        out.extend(["    " + l for l in disasm(pe.path, pe.image_base, max(0x1000, xr - 0x10), 0x28)])

    p = OUT_DIR / "probe_facing_127.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {p}")


if __name__ == "__main__":
    main()
