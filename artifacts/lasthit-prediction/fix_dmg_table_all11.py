# -*- coding: utf-8 -*-
"""
精确提取全部 11 个版本的：
1. DamageBonus 7x8 浮点表基址（Row0 Spells ~ Row6 Hero，每行 8 个 float = 0x20 字节）
2. Armor 减伤函数 RVA（DefenseArmor 字符串引用所在函数）
3. CAbilityAttack 关键成员偏移跨版本验证（修正 dumpbin 8位十六进制偏移正则）
"""
import re
import struct
import sys

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\dmg_table_and_cattack_all11.txt"

CATTACK_CTOR = {
    "1.0.17.5988": 0x555020,
    "1.0.20.6048": 0x555520,
    "1.20.4.6074": 0x555C40,
    "1.21.0.6263": 0x559CD0,
    "1.22.0.6328": 0x0CD810,
    "1.23.0.6352": 0x0CED50,
    "1.24.1.6374": 0x0CEE00,
    "1.24.4.6387": 0x0CEE10,
    "1.25.1.6397": 0x0CE1E0,
    "1.26.0.6401": 0x0CE1E0,
    "1.27.0.52240": 0x474820,
}


def find_str_push_rva(pe: PE32, s: bytes):
    off = pe.raw.find(s + b"\x00")
    if off < 0:
        return None, []
    srva = pe.off_to_rva(off)
    sva = pe.image_base + srva
    pat = b"\x68" + struct.pack("<I", sva)
    refs = []
    pos = 0
    while True:
        idx = pe.raw.find(pat, pos)
        if idx < 0:
            break
        r = pe.off_to_rva(idx)
        if r is not None:
            refs.append(r)
        pos = idx + 1
    return srva, refs


def find_table_addr_around(pe: PE32, ref_rva: int, str_rva: int):
    """在 DamageBonus* 字符串引用前后 0x30 字节内提取非字符串的绝对 VA"""
    lines = disasm(pe.path, pe.image_base, max(0x1000, ref_rva - 0x20), 0x50)
    # 收集所有引用到的可写数据区 RVA（排除字符串本身）
    data_sec = [s for s in pe.sections if s.name in (".data", ".bss", "DATA")]
    res = []
    for ln in lines:
        for m in re.finditer(r"\b([0-9A-F]{8})h\b", ln):
            va = int(m.group(1), 16)
            rva = va - pe.image_base
            if rva == str_rva or rva < 0x100000 or rva >= pe.image_size:
                continue
            for s in data_sec:
                if s.vaddr <= rva < s.vaddr + max(s.vsize, s.raw_size):
                    # 排除指向字符串常量的 .data（早期版本字符串可能在 .data）
                    raw_off = pe.rva_to_off(rva)
                    if raw_off is not None and pe.raw[raw_off : raw_off + 6] == b"Damage":
                        continue
                    if rva not in res:
                        res.append(rva)
    return res, lines


def main():
    out = []
    out.append("=== 1. 全 11 版本 DamageBonus 7x8 表基址 & ArmorReduction 函数 RVA ===")
    out.append(f"{'Version':14s} | {'Row0(Spells)':12s} | {'Row1(Normal)':12s} | {'Row2(Pierce)':12s} | {'Stride':6s} | {'ArmorFnXref':11s}")
    out.append("-" * 82)

    sample_disasm = []
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        s0, r0s = find_str_push_rva(pe, b"DamageBonusSpells")
        s1, r1s = find_str_push_rva(pe, b"DamageBonusNormal")
        s2, r2s = find_str_push_rva(pe, b"DamageBonusPierce")
        _, rda = find_str_push_rva(pe, b"DefenseArmor")

        t0 = t1 = t2 = None
        if r0s:
            c, lns = find_table_addr_around(pe, r0s[0], s0)
            if c:
                t0 = c[0]
            if ver in ("1.20.4.6074", "1.26.0.6401", "1.27.0.52240"):
                sample_disasm.append(f"\n--- {ver} DamageBonusSpells loader @ 0x{r0s[0]:06X} ---")
                sample_disasm.extend(lns)
        if r1s:
            c, _ = find_table_addr_around(pe, r1s[0], s1)
            if c:
                # 选与 t0 差 0x20 的，或第一个
                t1 = next((x for x in c if t0 and x - t0 == 0x20), c[0])
        if r2s:
            c, _ = find_table_addr_around(pe, r2s[0], s2)
            if c:
                t2 = next((x for x in c if t1 and x - t1 == 0x20), c[0])

        stride = f"0x{t1 - t0:X}" if (t0 and t1) else "—"
        f0 = f"0x{t0:06X}" if t0 else "—"
        f1 = f"0x{t1:06X}" if t1 else "—"
        f2 = f"0x{t2:06X}" if t2 else "—"
        fda = f"0x{rda[0]:06X}" if rda else "—"
        out.append(f"{ver:14s} | {f0:12s} | {f1:12s} | {f2:12s} | {stride:6s} | {fda:11s}")

    out.append("")
    out.append("=== 2. 全 11 版本 CAbilityAttack 构造函数关键偏移核验 ===")
    key_offs = [0x6C, 0x70, 0x84, 0x90, 0x9C, 0x158, 0x16C, 0x1B0, 0x1C0, 0x1D8, 0x1EC, 0x200, 0x2B8]
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        ctor = CATTACK_CTOR[ver]
        lns = disasm(pe.path, pe.image_base, ctor, 0x200)
        txt = "\n".join(lns)
        # 匹配 [reg+6Ch] 或 [reg+000001D8h]
        offs = set(int(m, 16) for m in re.findall(r"\+([0-9A-F]{2,8})h\]", txt))
        # 同时检查 lea reg, [esi+1D8h] 等
        hit = [f"+0x{o:X}" for o in key_offs if o in offs]
        out.append(f"{ver:14s} ctor=0x{ctor:06X} ({len(hit)}/{len(key_offs)}): {' '.join(hit)}")

    out.extend(sample_disasm)

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print(f"Wrote {len(out)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
