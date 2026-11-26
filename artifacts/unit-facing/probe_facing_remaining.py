# -*- coding: utf-8 -*-
"""
单线程轻量核验剩余全部细节：
1. 搜索全部本地 SLK 中的 Nfir (Shadow Fiend) turnRate / propWin
2. 提取 1.0.17~1.21.0 的 GetUnitFacing 实现及 180/pi (0x42652EE1) 全局常量 RVA
3. 反汇编 1.27 NIpse::CPoPos (vt=0x9607A8) +0x1C 与 CUnit+0x164 虚表 +0x1C，确认 +0x90 读取与 [0, 2pi) 归一化
4. 检查 1.27 +0x8C / +0x90 步进更新与 CAbilityAttack (0x47CE00附近) 出手前转身门控
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\unit-facing\facing_remaining_verify.txt")


def main():
    out = []

    # 1. 搜索 artifacts 下所有含 UnitData 的 SLK 中的 Nfir 与 Hjai
    out.append("=== 1. 搜索全部 SLK 中的 Nfir / Hjai turnRate & propWin ===")
    root = Path(r"D:\Qt\workspace\War3Analysis\artifacts")
    for p in root.rglob("*UnitData*.slk"):
        if not p.is_file():
            continue
        txt = p.read_text(encoding="utf-8", errors="replace")
        if '"Nfir"' in txt or '"Hjai"' in txt:
            out.append(f"File: {p}")
            lines = txt.splitlines()
            # 找 Nfir / Hjai 行及后 20 行
            for target in ('"Nfir"', '"Hjai"'):
                for i, ln in enumerate(lines):
                    if target in ln and ln.startswith("C;"):
                        out.append(f"  Hit {target} @ L{i+1}: " + " | ".join(lines[i : i + 18]))
                        break

    # 2. 1.0.17 ~ 1.21.0 GetUnitFacing 反汇编与 0x42652EE1 (57.29578f) 常量 RVA
    out.append("\n=== 2. 1.0.17~1.21.0 GetUnitFacing 与全部 11 版本 0x42652EE1 (180/pi) 全局 RVA ===")
    early_guf = {
        "1.0.17.5988": 0x2BFCA0,
        "1.0.20.6048": 0x2BFCA0,
        "1.20.4.6074": 0x2BFDC0,
        "1.21.0.6263": 0x2C3390,
    }
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        cands = pe.find_all_bytes(struct.pack("<I", 0x42652EE1), ".data")
        if not cands:
            cands = pe.find_all_bytes(struct.pack("<I", 0x42652EE1), ".rdata")
        # 校验相邻 -4 字节是否为 2*pi (0x40C90FDB)
        exact = []
        for c in cands:
            prev = pe.read_u32_rva(c - 4)
            if prev == 0x40C90FDB:
                exact.append(c)
        out.append(f"  {ver:14s}: 180/pi (prev=2pi) = {[hex(x) for x in exact]} | all_42652EE1={[hex(x) for x in cands[:4]]}")

    pe1017 = PE32(dll_path_for("1.0.17.5988"))
    out.append("\n--- 1.0.17 GetUnitFacing @ 0x2BFCA0 ---")
    out.extend(disasm(pe1017.path, pe1017.image_base, 0x2BFCA0, 0x75))

    # 3. 1.27 CUnit+0x164 虚表与 NIpse::CPoPos (0x9607A8) +0x1C
    pe127 = PE32(dll_path_for("1.27.0.52240"))
    out.append("\n=== 3. 1.27 CUnit+0x164 包装对象与 +0x90/+0x8C 读取核验 ===")
    # 找 CUnit 构造函数中写 [reg+164h] 的指令，或直接查 NIpse::CPoPos (0x9607A8) 的虚表前 0x40 字节
    out.append("1.27 NIpse::CPoPos vt @ 0x9607A8:")
    for slot in range(0x00, 0x40, 4):
        va = pe127.read_u32_rva(0x9607A8 + slot)
        rva = va - pe127.image_base if va and va > pe127.image_base else 0
        out.append(f"  vt+0x{slot:02X} = 0x{rva:06X}")

    # 反汇编 CUnit::GetPosNode wrapper: 1.27 0x668DA0 (`lea eax, [ecx+164h]; ret`) -> 查谁写 [esi+164h]
    # 搜 CUnit ctor：1.27 CUnit vt = 0xA4A704，找 mov dword ptr [reg], 6FA4A704h
    cunit_ctors = pe127.find_xrefs_to_va(pe127.image_base + 0xA4A704, ".text")
    out.append(f"1.27 CUnit vt xrefs: {[hex(x) for x in cunit_ctors[:5]]}")
    if cunit_ctors:
        clns = disasm(pe127.path, pe127.image_base, cunit_ctors[0], 0x100)
        for ln in clns:
            if "164h" in ln or "vt" in ln:
                out.append("  ctor: " + ln)

    # 4. 1.27 0x11CFD0 (CPoPosCl::StepTurnAndMove) 与 +0x8C/+0x90 更新（验证角度归一化与转身逻辑）
    out.append("\n=== 4. 1.27 CPoPosCl::StepTurnAndMove @ 0x11CFD0 (及周围角度归一化) ===")
    out.extend(disasm(pe127.path, pe127.image_base, 0x11CFD0, 0xA0))

    # 5. 1.27 CAbilityAttack 0x47CDC0..0x47CE70（查攻击前摇开始前是否检查朝向）
    out.append("\n=== 5. 1.27 CAbilityAttack 挥刀前检查 @ 0x47CDC0..0x47CE70 ===")
    out.extend(disasm(pe127.path, pe127.image_base, 0x47CDC0, 0xB0))

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {OUT}")


if __name__ == "__main__":
    main()
