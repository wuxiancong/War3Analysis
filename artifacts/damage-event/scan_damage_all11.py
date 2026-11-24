# -*- coding: utf-8 -*-
"""
极速低负载扫描全部 11 个 War3 版本的伤害事件核心 RVA：
- 经 push 0x00080234 (68 34 02 08 00, EVENT_UNIT_DAMAGED) 直接定位 CUnit::DispatchEventUnitDamaged
- 经 E8 相对调用反查唯一调用者 CUnit::NotifyDamaged 及再上层 CUnit::ApplyDamage
- 经字符串 xref 提取 GetEventDamage / GetEventDamageSource / UnitDamageTarget 原生 RVA
- 记录全部 11 版本的入口指令字节（供 Inline Hook 核验）
"""
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps")
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\damage-event\damage_all11_rva.txt")


def find_func_start(pe: PE32, inside_rva: int, max_back=0x60):
    """从函数内部向前回溯到 CC CC / 90 90 填充后的函数入口，或标准 push ebp; mov ebp,esp"""
    off = pe.rva_to_off(inside_rva)
    if off is None:
        return None
    raw = pe.raw
    # 1. 优先找 55 8B EC (push ebp; mov ebp, esp) 或 6A FF 68 (SEH prologue)
    for back in range(1, max_back):
        p = off - back
        if p < 2:
            break
        if raw[p : p + 3] == b"\x55\x8B\xEC":
            return inside_rva - back
        if raw[p : p + 3] == b"\x6A\xFF\x68" and raw[p - 1] in (0xCC, 0x90, 0xC3):
            return inside_rva - back
        if raw[p - 2 : p] == b"\xCC\xCC" and raw[p] != 0xCC:
            return inside_rva - back
    return None


def find_e8_callers(pe: PE32, target_rva: int):
    """在 .text 段查找所有 E8 rel32 调用 target_rva 的 RVA"""
    sec = pe.get_section(".text")
    start, end = sec.raw_ptr, sec.raw_ptr + sec.raw_size
    raw = pe.raw
    out = []
    pos = start
    while True:
        idx = raw.find(b"\xE8", pos, end)
        if idx < 0 or idx + 5 > end:
            break
        rel = struct.unpack_from("<i", raw, idx + 1)[0]
        call_rva = pe.off_to_rva(idx)
        if call_rva + 5 + rel == target_rva:
            out.append(call_rva)
        pos = idx + 1
    return out


def find_native_rva(pe: PE32, name: str):
    """修复 dumpbin 空格格式：mov ecx,6Fxxxxxxh 或 push 6Fxxxxxxh"""
    srvas = pe.find_string_rvas(name)
    text_sec = pe.get_section(".text")
    for srva in srvas:
        sva = pe.image_base + srva
        refs = pe.find_xrefs_to_va(sva, ".text")
        for ref in refs:
            lns = disasm(pe.path, pe.image_base, max(0x1000, ref - 0x10), 0x26)
            for ln in lns:
                m = re.search(r"(?:mov\s+ecx,|push\s+)([0-9A-F]{8})h", ln)
                if m:
                    va = int(m.group(1), 16)
                    rva = va - pe.image_base
                    if rva != srva and text_sec.vaddr <= rva < text_sec.vaddr + text_sec.vsize:
                        if rva == 0x70A0C0:
                            continue
                        return rva
    return None


def fmt(v):
    return f"0x{v:06X}" if isinstance(v, int) else "—"


def main():
    out = []
    hdr = (
        f"{'Version':14s} | {'ApplyDamage':11s} | {'NotifyDmg':10s} | {'DispatchEvt':11s} | "
        f"{'GetEvtDmg':10s} | {'GetEvtSrc':10s} | {'UnitDmgTgt':10s} | {'ApplyCalls':10s}"
    )
    out.append("=== 全部 11 版本伤害结算核心函数与原生 RVA 总表 ===")
    out.append(hdr)
    out.append("-" * len(hdr))

    prologues = []
    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        r_ged = find_native_rva(pe, "GetEventDamage")
        r_ges = find_native_rva(pe, "GetEventDamageSource")
        r_udt = find_native_rva(pe, "UnitDamageTarget")

        # 经 push 0x00080234 (68 34 02 08 00) 精确定位 CUnit::DispatchEventUnitDamaged
        hits = pe.find_all_bytes(b"\x68\x34\x02\x08\x00", ".text")
        r_disp = None
        r_notify = None
        r_apply = None
        apply_call_cnt = 0

        for h in hits:
            fstart = find_func_start(pe, h, max_back=0x60)
            if not fstart:
                continue
            callers = find_e8_callers(pe, fstart)
            if callers:
                # NotifyDamaged 是 DispatchEventUnitDamaged 的唯一（或主要）调用者，函数很短
                for c in callers:
                    nf = find_func_start(pe, c, max_back=0x40)
                    if nf:
                        ncallers = find_e8_callers(pe, nf)
                        if len(ncallers) >= 2:
                            r_disp = fstart
                            r_notify = nf
                            apply_call_cnt = len(ncallers)
                            # ApplyDamage 是 NotifyDamaged 的调用者（回溯较长，最多 0x500）
                            # 取第一个调用点回溯到 CC CC / push ebp
                            r_apply = find_func_start(pe, ncallers[0], max_back=0x400)
                            break
            if r_disp:
                break

        # 若 ApplyDamage 未通过回溯定位，用 CUnit vtable + 0x120 校验
        vts = pe.find_rtti_vtables(".?AVCUnit@@")
        if vts and r_apply is None:
            va = pe.read_u32_rva(vts[0] + 0x120)
            if va and va > pe.image_base:
                r_apply = va - pe.image_base

        out.append(
            f"{ver:14s} | {fmt(r_apply):11s} | {fmt(r_notify):10s} | {fmt(r_disp):11s} | "
            f"{fmt(r_ged):10s} | {fmt(r_ges):10s} | {fmt(r_udt):10s} | {apply_call_cnt:<10d}"
        )

        # 输出关键版本的入口前 6 条指令（确认 __fastcall / __thiscall 调用约定一致）
        if r_notify:
            pl = disasm(pe.path, pe.image_base, r_notify, 0x18)
            prologues.append(f"[{ver}] NotifyDamaged @ {fmt(r_notify)}: " + " ; ".join(x.split(":", 1)[1].strip()[18:].strip() for x in pl[:5]))
        if r_disp:
            dl = disasm(pe.path, pe.image_base, r_disp, 0x12)
            prologues.append(f"[{ver}] DispatchEvt   @ {fmt(r_disp)}: " + " ; ".join(x.split(":", 1)[1].strip()[18:].strip() for x in dl[:4]))

    out.append("\n=== 全部 11 版本入口指令核验（确认调用约定与前 5+ 字节可挂钩） ===")
    out.extend(prologues)

    OUT.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {len(out)} lines to {OUT}")


if __name__ == "__main__":
    main()
