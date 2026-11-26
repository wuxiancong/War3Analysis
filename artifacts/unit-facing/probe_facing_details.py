# -*- coding: utf-8 -*-
"""
单线程轻量验证：
1. 1.27 0x7518A0..0x751910 确认 0x6FB59460 乘数写入值（180/pi = 57.29578f）
2. 1.27 CUnit+0x164 虚表 +0x1C (GetFacingRad) 反汇编（确认读 +0x90 与归一化范围 [0, 2pi)）
3. 核查 Nfir / Hjai 在地图 SLK 与基础 patch UnitData.slk 中的 turnRate / propWin
4. 全部 11 版本 GetUnitFacing RVA、180/pi 乘数全局 RVA、及 1.27/1.26/1.20.4 入口核验
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\stealth-rune-route")
from parse_sight_and_doodads import parse_slk_clean

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-facing\facing_all11_verify.txt")


def find_native_exact(pe: PE32, name: str):
    srvas = pe.find_string_rvas(name)
    tsec = pe.get_section(".text")
    for srva in srvas:
        sva = pe.image_base + srva
        refs = pe.find_all_bytes(b"\xBA" + struct.pack("<I", sva), ".text")
        for ref in refs:
            lns_after = disasm(pe.path, pe.image_base, ref, 0x12)
            for ln in lns_after[1:4]:
                m = re.search(r"mov\s+ecx,([0-9A-F]{8})h", ln)
                if m:
                    rva = int(m.group(1), 16) - pe.image_base
                    if rva != 0x70A0C0 and tsec.vaddr <= rva < tsec.vaddr + tsec.vsize:
                        return rva
            lns_before = disasm(pe.path, pe.image_base, max(0x1000, ref - 0x0A), 0x0F)
            for ln in reversed(lns_before):
                m = re.search(r"mov\s+ecx,([0-9A-F]{8})h", ln)
                if m:
                    rva = int(m.group(1), 16) - pe.image_base
                    if tsec.vaddr <= rva < tsec.vaddr + tsec.vsize:
                        return rva
    return None


def main():
    out = []
    pe127 = PE32(dll_path_for("1.27.0.52240"))

    # 1. 0x6FB59460 乘数初始化代码 & 查 0x6F7518B0 附近及 180/pi 写入处
    out.append("=== 1. 1.27 乘数 0x6FB59460 初始化/引用 @ 0x7518B0 ===")
    out.extend(disasm(pe127.path, pe127.image_base, 0x7518B0, 0x60))

    # 同时搜 .rdata / .data 里 57.29578 (180/pi = 0x42652EE1 / 0x42652EE0) 或 180.0f / pi
    # 检查 0x6FB59460 在文件里的原始值以及前后相邻浮点（如 pi, 2*pi, pi/180）
    out.append("\n=== 2. 1.27 0x6FB59440..0x6FB59480 附近常量表（文件原始字节） ===")
    for rva in range(0xB59440, 0xB59484, 4):
        v = pe127.read_u32_rva(rva)
        if v is not None:
            fv = struct.unpack("<f", struct.pack("<I", v))[0]
            out.append(f"  0x{rva:06X}: 0x{v:08X} ({fv:.6g})")
        else:
            out.append(f"  0x{rva:06X}: (BSS/uninitialized in file)")

    # 查找写 0x6FB59460 的启动初始化函数（直接搜 60 94 B5 6F 全部出现位置，不限于 .text）
    raw_refs = pe127.find_all_bytes(struct.pack("<I", 0x6FB59460), ".text")
    out.append(f"\nAll raw .text occurrences of 0x6FB59460: {[hex(x) for x in raw_refs]}")

    # 3. 查 1.27 CUnit+0x164 虚表 +0x1C (GetFacingRad)
    # 搜 CUnit 构造函数写入 [esi+164h] 的虚表，或通过 RTTI 找 CPos / CAgentBaseAbs
    pos_vts = pe127.find_rtti_vtables("Pos")
    out.append(f"\n=== 3. 1.27 含 Pos 的 RTTI 虚表 (前10): {[hex(x) for x in pos_vts[:10]]} ===")
    # 直接在 1.27 搜 lea eax, [ecx+90h] 或 mov eax, [ecx+90h] 在虚表 +0x1C 指向的函数
    for vt in pos_vts[:15]:
        va1c = pe127.read_u32_rva(vt + 0x1C)
        if va1c and va1c > pe127.image_base:
            r1c = va1c - pe127.image_base
            lns = disasm(pe127.path, pe127.image_base, r1c, 0x50)
            txt = "\n".join(lns)
            if "+90h" in txt or "+00000090h" in txt:
                out.append(f"  HIT! vt=0x{vt:06X}, vt+0x1C=0x{r1c:06X}:")
                out.extend(["    " + l for l in lns[:25]])

    # 4. 核查 Nfir / Hjai 在基础 SLK 与 6.83d 地图 SLK 中的 turnRate & propWin
    out.append("\n=== 4. Nfir / Hjai 在基础 SLK 与 6.83d 地图 SLK 中的 turnRate / propWin ===")
    slk_paths = [
        Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Units_UnitData.slk"),
        Path(r"D:\Qt\workspace\War3Analysis\artifacts\neutral-stack\UnitData.slk\UnitData.slk"),
    ]
    for sp in slk_paths:
        if not sp.exists():
            continue
        cols, rows = parse_slk_clean(sp)
        c2i = {v: k for k, v in cols.items()}
        out.append(f"File: {sp}")
        for y, r in sorted(rows.items()):
            uid = r.get(1, "")
            if uid in ("Nfir", "Hjai", "Hamg", "Edem", "Ulic", "Oshd", "ugho", "edry", "ebal"):
                out.append(
                    f"  {uid:6s} (Y={y:4d}): turnRate={r.get(c2i.get('turnRate',0),'?')}, "
                    f"propWin={r.get(c2i.get('propWin',0),'?')}, movetp={r.get(c2i.get('movetp',0),'?')}"
                )

    # 5. 全 11 版本 GetUnitFacing RVA & 180/pi 乘数全局 RVA 提取
    out.append("\n=== 5. 全部 11 版本 GetUnitFacing & 180/pi 乘数全局 RVA ===")
    out.append(f"{'Version':14s} | {'GetUnitFacing':13s} | {'Rad2Deg Global':14s} | {'CUnit::GetPos(vt+B8)':20s} | {'RetReg':6s}")
    out.append("-" * 80)
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        r_guf = find_native_exact(pe, "GetUnitFacing")
        mult_rva = None
        if r_guf:
            lns = disasm(pe.path, pe.image_base, r_guf, 0x90)
            # 在 GetUnitFacing 里查找 push 6Fxxxxxxh（指向 .data/.bss 乘数，紧跟 call softfloat_mul）
            for ln in lns:
                m = re.search(r"(?:push|mov\s+\w+,)\s+([0-9A-F]{8})h", ln)
                if m:
                    va = int(m.group(1), 16)
                    r = va - pe.image_base
                    if 0x700000 < r < pe.image_size:
                        mult_rva = r
        # 检查 CUnit vt+0xB8 (1.22+ via RTTI)
        cunit_vts = pe.find_rtti_vtables(".?AVCUnit@@")
        pos_fn = None
        if cunit_vts:
            va = pe.read_u32_rva(cunit_vts[0] + 0xB8)
            if va and va > pe.image_base:
                pos_fn = va - pe.image_base
        fg = f"0x{r_guf:06X}" if r_guf else "—"
        fm = f"0x{mult_rva:06X}" if mult_rva else "—"
        fp = f"0x{pos_fn:06X}" if pos_fn else "—"
        out.append(f"{ver:14s} | {fg:13s} | {fm:14s} | {fp:20s} | EAX")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {OUT}")


if __name__ == "__main__":
    main()
