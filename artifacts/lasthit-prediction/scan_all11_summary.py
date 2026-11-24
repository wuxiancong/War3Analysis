# -*- coding: utf-8 -*-
"""
一次性扫描全部 11 个 War3 版本的：
1. DamageBonus 7x8 伤害倍率表基址（Row 0 Spells / Row 1 Normal / Row 2 Pierce）及 DefenseArmor (0.06f) 全局 RVA
2. CMissile 虚表及 OnImpact (vt+0xBC) / Destroy (vt+0xA8) RVA
3. CAbilityAttack 关键成员偏移跨版本核验（1.0.17 ~ 1.27.0）
4. 1.27 CMissile 飞行步进与到达判定（确认 2D 水平匀速、arc 仅影响视觉 Z 轴、到达距离阈值）
5. 1.27 伤害计算（骰子掷骰 + 护甲减伤公式）简要反汇编证据
"""
import os
import re
import struct
import sys

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\all11_summary.txt"

# 来自 war3hook_ai.cpp kAiMissileVerTable 的 CMissile 虚表 RVA（用于反查 vt+0xBC）
CMISSILE_VTABLES = {
    "1.0.17.5988": 0x7A57E4,
    "1.0.20.6048": 0x7A67FC,
    "1.20.4.6074": 0x7A67FC,
    "1.21.0.6263": 0x7A785C,
    "1.22.0.6328": 0x8AA6B8,
    "1.23.0.6352": 0x8BE7E0,
    "1.24.1.6374": 0x8CD8E8,
    "1.24.4.6387": 0x8CD8E8,
    "1.25.1.6397": 0x8BB738,
    "1.26.0.6401": 0x8BB738,
    "1.27.0.52240": 0x9B07D0,
}

# 之前已验证的 CAbilityAttack 虚表与构造函数 RVA
CATTACK_INFO = {
    "1.0.17.5988": (0x78D6B8, 0x555028),
    "1.0.20.6048": (0x78E6C0, 0x555528),
    "1.20.4.6074": (0x78E6C0, 0x555C48),
    "1.21.0.6263": (0x78F6F8, 0x559CD8),
    "1.22.0.6328": (0x8A1414, 0x0CD822),
    "1.23.0.6352": (0x8B5554, 0x0CED62),
    "1.24.1.6374": (0x8C468C, 0x0CEE12),
    "1.24.4.6387": (0x8C468C, 0x0CEE22),
    "1.25.1.6397": (0x8B252C, 0x0CE1F2),
    "1.26.0.6401": (0x8B252C, 0x0CE1F2),
    "1.27.0.52240": (0x9ADDBC, 0x474822),
}


def find_str_xref_rvAs(pe: PE32, s: bytes):
    """查找字符串在代码段中的 push imm32 引用 RVA"""
    off = pe.raw.find(s + b"\x00")
    if off < 0:
        return None, []
    str_rva = pe.off_to_rva(off)
    if str_rva is None:
        return None, []
    str_va = pe.image_base + str_rva
    pat = b"\x68" + struct.pack("<I", str_va)
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
    return str_rva, refs


def section_name_of_rva(pe: PE32, rva: int):
    for s in pe.sections:
        if s.vaddr <= rva < s.vaddr + max(s.vsize, s.raw_size):
            return s.name
    return None


def d_lines(pe: PE32, rva: int, size: int):
    return disasm(pe.path, pe.image_base, rva, size)


def extract_push_data_rva_nearby(pe: PE32, ref_rva: int, search_back=32, search_fwd=32):
    """在字符串 push 附近查找指向 .data/.bss 的 push imm32 / mov reg, imm32"""
    start = max(0x1000, ref_rva - search_back)
    lines = d_lines(pe, start, search_back + search_fwd)
    cands = []
    for line in lines:
        m = re.search(r"([0-9A-Fa-f]{8}):\s+.*\b(?:push|mov\s+\w+,)\s+(?:offset\s+)?([0-9A-Fa-f]{8})h", line)
        if m:
            ins_rva = int(m.group(1), 16) - pe.image_base
            val = int(m.group(2), 16)
            rva = val - pe.image_base
            if 0x100000 < rva < pe.image_size:
                sname = section_name_of_rva(pe, rva)
                if sname in (".data", ".bss", "DATA"):
                    cands.append((ins_rva, rva, sname))
    return cands


def read_u32_rva(pe: PE32, rva: int):
    return pe.read_u32_rva(rva)


def fmt_hex(v):
    return f"0x{v:06X}" if isinstance(v, int) else "—"


def main():
    lines = []
    lines.append("=== 1. DamageBonus 7x8 表基址 & DefenseArmor (0.06f) 全 11 版本 ===")
    lines.append(f"{'Version':14s} | {'Row0(Spells)':12s} | {'Row1(Normal)':12s} | {'Row2(Pierce)':12s} | {'DefArmor':12s} | {'LoaderRVA':10s}")
    lines.append("-" * 85)

    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        _, refs_sp = find_str_xref_rvAs(pe, b"DamageBonusSpells")
        _, refs_nm = find_str_xref_rvAs(pe, b"DamageBonusNormal")
        _, refs_pc = find_str_xref_rvAs(pe, b"DamageBonusPierce")
        _, refs_da = find_str_xref_rvAs(pe, b"DefenseArmor")

        r0 = r1 = r2 = rda = loader = None
        if refs_sp:
            loader = refs_sp[0]
            c = extract_push_data_rva_nearby(pe, refs_sp[0], 24, 24)
            if c:
                r0 = c[0][1]
        if refs_nm:
            c = extract_push_data_rva_nearby(pe, refs_nm[0], 24, 24)
            if c:
                r1 = c[0][1]
        if refs_pc:
            c = extract_push_data_rva_nearby(pe, refs_pc[0], 24, 24)
            if c:
                r2 = c[0][1]
        if refs_da:
            # DefenseArmor 可能通过 fstp dword ptr [addr] 写入
            txt_lines = d_lines(pe, max(0x1000, refs_da[0] - 16), 64)
            for line in txt_lines:
                m = re.search(r"(?:fstp|mov)\s+(?:dword ptr\s+)?\[([0-9A-Fa-f]{8})h\]", line)
                if m:
                    rva = int(m.group(1), 16) - pe.image_base
                    if 0x100000 < rva < pe.image_size:
                        rda = rva
                        break
            if rda is None:
                c = extract_push_data_rva_nearby(pe, refs_da[0], 24, 32)
                if c:
                    rda = c[0][1]

        lines.append(
            f"{ver:14s} | {fmt_hex(r0):12s} | {fmt_hex(r1):12s} | {fmt_hex(r2):12s} | {fmt_hex(rda):12s} | {fmt_hex(loader):10s}"
        )

    lines.append("")
    lines.append("=== 2. CMissile 虚表 & OnImpact (vt+0xBC) & Destroy (vt+0xA8) 全 11 版本 ===")
    lines.append(f"{'Version':14s} | {'CMissile vt':12s} | {'vt+0xA8(Dest)':13s} | {'vt+0xBC(Imp)':12s} | {'vt+0x98(Step?)':14s}")
    lines.append("-" * 78)
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        vt = CMISSILE_VTABLES[ver]
        # 检查虚表是否确实在 rdata 且指向 .text
        v_a8 = read_u32_rva(pe, vt + 0xA8)
        v_bc = read_u32_rva(pe, vt + 0xBC)
        v_98 = read_u32_rva(pe, vt + 0x98)
        r_a8 = (v_a8 - pe.image_base) if v_a8 and v_a8 > pe.image_base else None
        r_bc = (v_bc - pe.image_base) if v_bc and v_bc > pe.image_base else None
        r_98 = (v_98 - pe.image_base) if v_98 and v_98 > pe.image_base else None
        lines.append(
            f"{ver:14s} | {fmt_hex(vt):12s} | {fmt_hex(r_a8):13s} | {fmt_hex(r_bc):12s} | {fmt_hex(r_98):14s}"
        )

    lines.append("")
    lines.append("=== 3. CAbilityAttack 构造函数关键偏移核验（抽检 1.0.17 / 1.20.4 / 1.22.0 / 1.26.0 / 1.27.0） ===")
    for ver in ["1.0.17.5988", "1.20.4.6074", "1.22.0.6328", "1.26.0.6401", "1.27.0.52240"]:
        pe = PE32(dll_path_for(ver))
        vt, ctor = CATTACK_INFO[ver]
        # CAbilityAttack 构造函数一般 ~0x160 字节
        txt = "\n".join(d_lines(pe, ctor, 0x160))
        # 提取所有出现的 [+0xXX] 偏移
        offs = sorted(set(int(m, 16) for m in re.findall(r"\+(?:0x)?([0-9A-Fa-f]{2,3})h\]", txt)))
        key_offs = [0x6C, 0x70, 0x84, 0x88, 0x90, 0x94, 0x9C, 0xA0, 0xAC, 0xF4, 0x158, 0x16C, 0x1B0, 0x1C0, 0x1D8, 0x1EC, 0x200, 0x2B8]
        present = [f"0x{o:X}" for o in key_offs if o in offs]
        missing = [f"0x{o:X}" for o in key_offs if o not in offs]
        lines.append(f"{ver:14s} ctor={fmt_hex(ctor)} present={','.join(present)}")
        lines.append(f"{'':14s} missing_in_ctor={','.join(missing)}")

    # 4. 1.27 CMissile 虚表关键更新函数 & 移动步进反汇编
    lines.append("")
    lines.append("=== 4. 1.27 CMissile 虚表与飞行更新 / 命中判定 ===")
    pe127 = PE32(dll_path_for("1.27.0.52240"))
    vt127 = 0x9B07D0
    for slot in range(0x80, 0xD0, 4):
        va = read_u32_rva(pe127, vt127 + slot)
        rva = va - pe127.image_base if va and va > pe127.image_base else 0
        lines.append(f"  CMissile vt+0x{slot:02X} = 0x{rva:06X}")

    # 反汇编 1.27 CMissile vt+0xA8 / vt+0xB4 / vt+0xB8 / vt+0xBC（寻找位置更新与距离判定）
    for slot in (0xA8, 0xB4, 0xB8, 0xBC):
        va = read_u32_rva(pe127, vt127 + slot)
        rva = va - pe127.image_base
        lines.append(f"\n--- 1.27 CMissile vt+0x{slot:02X} @ 0x{rva:06X} ---")
        lines.extend(d_lines(pe127, rva, 0xE0))

    # 5. 1.27 护甲减伤公式（查找引用 DefenseArmor 全局变量的指令）
    lines.append("")
    lines.append("=== 5. 1.27 DefenseArmor 引用处（护甲减伤公式） ===")
    _, refs_da127 = find_str_xref_rvAs(pe127, b"DefenseArmor")
    if refs_da127:
        lines.append(f"DefenseArmor str xref: {[hex(x) for x in refs_da127]}")
        lines.extend(d_lines(pe127, refs_da127[0] - 0x10, 0x60))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
