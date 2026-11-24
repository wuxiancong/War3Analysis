# -*- coding: utf-8 -*-
"""
1. 精确校验全部 11 版本的 GetEventDamage / GetEventDamageSource / UnitDamageTarget 原生 RVA（只向后看 ref..ref+0x12，避免误抓前一个原生）
2. 校验 1.0.17 (0x1C0290) 与 1.26 (0x296D10) DispatchEventUnitDamaged 调用约定与前 7 字节原始机器码
3. 读取 Units_UnitAbilities.slk 第 5 列 (abilList) 确认 6.83d 防御塔真视技能与真眼技能
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\stealth-rune-route")
from parse_sight_and_doodads import parse_slk_clean

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\damage-event\verify_exact_all11.txt")

DISPATCH_RVAS = {
    "1.0.17.5988": 0x1C0290,
    "1.0.20.6048": 0x1C0290,
    "1.20.4.6074": 0x1C0300,
    "1.21.0.6263": 0x1C34C0,
    "1.22.0.6328": 0x2961C0,
    "1.23.0.6352": 0x297700,
    "1.24.1.6374": 0x2977C0,
    "1.24.4.6387": 0x297830,
    "1.25.1.6397": 0x296AE0,
    "1.26.0.6401": 0x296D10,
    "1.27.0.52240": 0x65E010,
}


def find_native_exact(pe: PE32, name: str):
    """在 mov edx, name_va 之后的 0x10 字节内找 mov ecx, func_va（或紧邻前的 mov ecx）"""
    srvas = pe.find_string_rvas(name)
    tsec = pe.get_section(".text")
    for srva in srvas:
        sva = pe.image_base + srva
        # 注册指令为 BA <sva> (mov edx, sva)
        refs = pe.find_all_bytes(b"\xBA" + struct.pack("<I", sva), ".text")
        for ref in refs:
            # 先向后看 10 字节（1.22~1.27 模式：mov edx, name; mov ecx, func; call reg）
            lns_after = disasm(pe.path, pe.image_base, ref, 0x12)
            for ln in lns_after[1:4]:
                m = re.search(r"mov\s+ecx,([0-9A-F]{8})h", ln)
                if m:
                    rva = int(m.group(1), 16) - pe.image_base
                    if rva != 0x70A0C0 and tsec.vaddr <= rva < tsec.vaddr + tsec.vsize:
                        return rva
            # 再向前看 10 字节（1.0.17~1.21 模式：mov ecx, func; mov edx, name; call reg）
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
    out.append("=== 1. 全 11 版本原生 RVA 精确核对 & DispatchEventUnitDamaged 前 10 字节机器码 ===")
    out.append(f"{'Version':14s} | {'DispatchEvt':11s} | {'Prologue (first 7 bytes)':26s} | {'GetEvtDmg':10s} | {'GetEvtSrc':10s} | {'UnitDmgTgt':10s}")
    out.append("-" * 96)
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        r_ged = find_native_exact(pe, "GetEventDamage")
        r_ges = find_native_exact(pe, "GetEventDamageSource")
        r_udt = find_native_exact(pe, "UnitDamageTarget")
        drva = DISPATCH_RVAS[ver]
        doff = pe.rva_to_off(drva)
        b7 = " ".join(f"{b:02X}" for b in pe.raw[doff : doff + 7])
        fg = f"0x{r_ged:06X}" if r_ged else "—"
        fs = f"0x{r_ges:06X}" if r_ges else "—"
        fu = f"0x{r_udt:06X}" if r_udt else "—"
        out.append(f"{ver:14s} | 0x{drva:06X}    | {b7:26s} | {fg:10s} | {fs:10s} | {fu:10s}")

    # 2. 验证 1.0.17 0x19FC10 (NotifyDamaged) 调用 0x1C0290 的指令（确认 __thiscall 传参）
    pe1017 = PE32(dll_path_for("1.0.17.5988"))
    out.append("\n=== 2. 1.0.17 NotifyDamaged (0x19FC10) 调用 DispatchEvt (0x1C0290) 核验 ===")
    out.extend(disasm(pe1017.path, pe1017.image_base, 0x19FC10, 0x2A))

    # 3. 验证 6.83d 防御塔 & 真眼技能列表（Units_UnitAbilities.slk col 5 = abilList）
    MAP = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
    acols, arows = parse_slk_clean(MAP / "Units_UnitAbilities.slk")
    out.append("\n=== 3. 6.83d 防御塔/眼技能 (Units_UnitAbilities.slk col 5 = abilList) ===")
    for y, r in sorted(arows.items()):
        uid = r.get(1, "")
        if uid in ("e00R", "u00M", "e011", "u00D", "e00S", "u00N", "e019", "o004", "oeye"):
            out.append(f"  {uid:6s} (Y={y:4d}): abilList={r.get(5, '?')}")

    # 查塔真视技能 A08V / Atru / Adts 在 Units_AbilityData.slk 中的范围
    ab_cols, ab_rows = parse_slk_clean(MAP / "Units_AbilityData.slk")
    ab_c2i = {v: k for k, v in ab_cols.items()}
    out.append(f"\n=== 4. 6.83d 真视技能范围 (Units_AbilityData.slk, Area1 col={ab_c2i.get('Area1')}) ===")
    for y, r in sorted(ab_rows.items()):
        aid = r.get(1, "")
        if aid in ("Atru", "Adts", "A08V", "A014", "A077", "A0C6", "Agyv", "AItb"):
            out.append(f"  {aid:6s} (Y={y:4d}): code={r.get(2,'?')}, Area1={r.get(ab_c2i.get('Area1',0),'?')}, DataA1={r.get(ab_c2i.get('DataA1',0),'?')}")

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {OUT}")


if __name__ == "__main__":
    main()
