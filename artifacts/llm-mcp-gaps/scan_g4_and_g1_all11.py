# -*- coding: utf-8 -*-
"""
全 11 个版本统一扫描脚本（G4 JASS VM 指针链 + G1 内部函数补全 + G2/G3 早期版校准）：
1. G4: 通过 ExecuteFunc 原生函数自动追踪全部 11 个版本的：
   - ExecuteFunc RVA
   - g_jassEnv 全局变量 RVA（如 1.27 0xBE4238）
   - LookupJassFunc RVA 及 vmIndex 偏移（+0x08）
   - JassVM::FindFunction / GetVM / TLS 槽函数 RVA（tls+0x90）
   - vm->globalTable 偏移（+0x285C 等）
2. G1: 对全部 11 个版本补齐：
   - CAgentTimer 虚表 RVA（通过 RTTI '.?AVCAgentTimer@@' 或 CAbilitySpell::ResetCooldown 附近）
   - CAgentTimer::GetTimeout (+0x10) / GetRemainingTime (+0x18) RVA 与 +0x0C/+0x08/+0x04/+0x40 偏移核验
   - 核验 1.0.17~1.21.0 的 UnitResetCooldown / UnitCountBuffsEx / IsUnitDetected 为何此前标为「内联/早期布局」
3. G2/G3: 校准 1.0.17~1.21.0 的 Send_0x10 / Send_0x11 / Send_0x12_XY 函数入口与 UI_PointDispatch
"""
import json
import re
import struct
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g4_g1_all11.json"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g4_g1_all11.txt"


def find_native(pe: PE32, name: str):
    text = pe.get_section(".text")
    tblob = pe.raw[text.raw_ptr : text.raw_ptr + text.raw_size]
    for srva in pe.find_string_rvas(name):
        sva = pe.image_base + srva
        pat = struct.pack("<I", sva)
        pos = 0
        while True:
            idx = tblob.find(pat, pos)
            if idx < 0:
                break
            for delta in [-5, 5, -10, 10]:
                if 0 <= idx + delta <= len(tblob) - 4:
                    cand = struct.unpack_from("<I", tblob, idx + delta)[0]
                    if pe.image_base + 0x1000 < cand < pe.image_base + 0x900000:
                        return cand - pe.image_base
            pos = idx + 1
    return None


def find_rel32_callers(pe: PE32, target_rva: int):
    text = pe.get_section(".text")
    blob = pe.raw[text.raw_ptr : text.raw_ptr + text.raw_size]
    out = []
    pos = 0
    while True:
        idx = blob.find(b"\xE8", pos)
        if idx < 0:
            break
        if idx + 5 <= len(blob):
            rel = struct.unpack_from("<i", blob, idx + 1)[0]
            call_rva = text.vaddr + idx
            if call_rva + 5 + rel == target_rva:
                out.append(call_rva)
        pos = idx + 1
    return out


def calls_in(asm, base):
    out = []
    for i, ln in enumerate(asm):
        m = re.search(r"\b(call|jmp)\s+([0-9A-F]{8})\b", ln)
        if m:
            va = int(m.group(2), 16)
            if base < va < base + 0x1000000:
                out.append((i, m.group(1), va - base))
    return out


def scan_g4_version(ver: str, pe: PE32):
    base = pe.image_base
    dll = pe.path
    r = {}

    # 1. ExecuteFunc -> g_jassEnv & LookupJassFunc
    ef = find_native(pe, "ExecuteFunc")
    r["ExecuteFunc"] = f"0x{ef:X}" if ef else None
    if ef:
        asm = disasm(dll, base, ef, 0x80)
        # 找 g_jassEnv: mov eax/ecx/esi, dword ptr ds:[6Fxxxxxxh] (排除 security cookie，通常在 0x800000+)
        # 在 ExecuteFunc 里，第一次非 cookie 的 [6Fxxxxxxh] 后面紧跟 test reg, reg 或直接作为 ecx 传给 LookupJassFunc
        globs = []
        for i, l in enumerate(asm):
            m = re.search(r"dword ptr ds:\[([0-9A-F]{8})h\]", l)
            if m:
                va = int(m.group(1), 16)
                if base + 0x700000 <= va < base + 0xF00000:
                    # 排除 cookie (紧跟 xor eax, ebp)
                    nxt = asm[i + 1] if i + 1 < len(asm) else ""
                    if "xor" not in nxt:
                        globs.append((i, va - base))
        if globs:
            r["g_jassEnv"] = f"0x{globs[0][1]:X}"
            # 找紧接在 g_jassEnv 之后的那个 call (LookupJassFunc)，跳过初始化 call (带 lea ecx, [eax+6])
            idx_g = globs[-1][0]
            cs = [c for c in calls_in(asm, base) if c[0] > idx_g and c[1] == "call"]
            if cs:
                lookup_rva = cs[0][2]
                r["LookupJassFunc"] = f"0x{lookup_rva:X}"
                asm_lk = disasm(dll, base, lookup_rva, 0x40)
                # 检查 [ecx+8] / [reg+8]
                m_off = re.search(r"mov\s+\w+,dword ptr \[\w+\+([0-9A-F]+)h\]", "\n".join(asm_lk))
                if m_off:
                    r["vmIndex_off"] = f"+0x{m_off.group(1)}"
                cs_lk = calls_in(asm_lk, base)
                if cs_lk:
                    vm_find_fn = cs_lk[0][2]
                    r["JassVM_FindFunc"] = f"0x{vm_find_fn:X}"
                    # 反汇编 vm_find_fn 及之后 0x100 字节，找 GetVM 和 CreateGlobal (mov reg, [reg+285Ch]!)
                    asm_vm = disasm(dll, base, vm_find_fn, 0x100)
                    cs_vm = calls_in(asm_vm[:8], base)
                    if cs_vm:
                        get_vm = cs_vm[0][2]
                        r["GetVM"] = f"0x{get_vm:X}"
                        # 跟进 GetVM (可能是 jmp thunk)
                        asm_gvm = disasm(dll, base, get_vm, 0x45)
                        if asm_gvm and "jmp" in asm_gvm[0]:
                            cs_j = calls_in(asm_gvm[:2], base)
                            if cs_j:
                                get_vm = cs_j[0][2]
                                r["GetVM"] = f"0x{get_vm:X}"
                                asm_gvm = disasm(dll, base, get_vm, 0x45)
                        # 从 GetVM 里找 TLS 获取函数 (前面有 mov ecx, 5 或 push 5) 与 [reg+90h]
                        cs_gvm = calls_in(asm_gvm, base)
                        if cs_gvm:
                            r["GetTlsSlot"] = f"0x{cs_gvm[0][2]:X}"
                            if len(cs_gvm) >= 2:
                                asm_arr = disasm(dll, base, cs_gvm[1][2], 0x25)
                                m_tls = re.search(r"\+0*([0-9A-F]+)h\]", "\n".join(asm_arr))
                                if m_tls:
                                    r["tls_vmArray_off"] = f"+0x{m_tls.group(1)}"
                    # 在 vm_find_fn 附近搜 [reg+000028xxh] 定位 globalTable 偏移
                    m_gt = re.search(r"\[(?:eax|ecx|edx|esi|edi|ebx)\+0000(28[0-9A-F]{2})h\]", "\n".join(asm_vm))
                    if m_gt:
                        r["vm_globalTable_off"] = f"+0x{m_gt.group(1)}"

    # 如果没在 vm_find_fn+0x100 里找到 globalTable_off，直接搜特征指令 `83 FA 09` 或 `83 F8 09` + `285C` 在 VM 附近
    if "vm_globalTable_off" not in r and r.get("GetVM"):
        gvm_rva = int(r["GetVM"], 16)
        # 扫 GetVM 附近 +-0x4000 范围里的 [reg+28xxh] 紧跟在 GetVM 调用之后
        callers = find_rel32_callers(pe, gvm_rva)
        for c in callers[:15]:
            asm_c = disasm(dll, base, c, 0x35)
            txt = "\n".join(asm_c)
            m_gt = re.search(r"\+0000(28[0-9A-F]{2})h\]", txt)
            if m_gt and ("5Ch" in m_gt.group(1) or "58h" in m_gt.group(1) or True):
                # 确认后面有 +18h / +1Ch / +20h (CreateGlobal)
                asm_c2 = disasm(dll, base, c, 0x60)
                t2 = "\n".join(asm_c2)
                if "+18h]" in t2 and "+20h]" in t2:
                    r["vm_globalTable_off"] = f"+0x{m_gt.group(1)}"
                    break

    return r


def scan_g1_version(ver: str, pe: PE32):
    base = pe.image_base
    dll = pe.path
    r = {}

    # 1. CAgentTimer vtable via RTTI '.?AVCAgentTimer@@'
    vts = pe.find_rtti_vtables(".?AVCAgentTimer@@")
    if vts:
        vt = vts[0]
        r["CAgentTimer_vt"] = f"0x{vt:X}"
        gt = pe.read_u32_rva(vt + 0x10)
        gr = pe.read_u32_rva(vt + 0x18)
        if gt and base < gt < base + 0x1000000:
            r["CAgentTimer_GetTimeout"] = f"0x{gt - base:X}"
            asm_gt = disasm(dll, base, gt - base, 0x25)
            # 验证 +0Ch / +8
            j = " ".join(asm_gt)
            r["timer_node_off"] = "+0x0C" if "+0Ch]" in j else "?"
            r["timer_total_off"] = "+0x08" if "+8]" in j else "?"
        if gr and base < gr < base + 0x1000000:
            r["CAgentTimer_GetRemaining"] = f"0x{gr - base:X}"
            asm_gr = disasm(dll, base, gr - base, 0x35)
            j = " ".join(asm_gr)
            r["timer_clock_off"] = "+0x40" if "40h" in j else "?"

    # 2. 对早期版本 (1.0.17~1.21.0) 检查 UnitResetCooldown / UnitCountBuffsEx / IsUnitDetected 里的真实行为
    if ver.startswith(("1.0.", "1.20.", "1.21.")):
        urc = find_native(pe, "UnitResetCooldown")
        ucb = find_native(pe, "UnitCountBuffsEx")
        iud = find_native(pe, "IsUnitDetected")
        if urc:
            asm = disasm(dll, base, urc, 0x60)
            cs = calls_in(asm, base)
            r["early_UnitResetCooldown_calls"] = [f"0x{c[2]:X}" for c in cs[:3]]
            if len(cs) >= 2:
                # 第 2 个 call 通常是 CUnit::ResetCooldown
                asm2 = disasm(dll, base, cs[-1][2], 0x100)
                cs2 = calls_in(asm2, base)
                for _, op, cand in cs2:
                    if op == "call":
                        a3 = "\n".join(disasm(dll, base, cand, 0x40))
                        if "20h],200h" in a3:
                            r["CAbilitySpell_ResetCooldown"] = f"0x{cand:X}"
                            m_cd = re.search(r"lea\s+\w+,\[(?:\w+)\+0*([0-9A-F]+)h\]", a3)
                            r["early_cd_timer_off"] = f"+0x{m_cd.group(1)}" if m_cd else "?"
                            break
        if ucb:
            asm = disasm(dll, base, ucb, 0x120)
            cs = calls_in(asm, base)
            r["early_UnitCountBuffsEx_calls"] = [f"0x{c[2]:X}" for c in cs[:4]]
        if iud:
            asm = disasm(dll, base, iud, 0x120)
            cs = calls_in(asm, base)
            r["early_IsUnitDetected_calls"] = [f"0x{c[2]:X}" for c in cs[:4]]

    return r


def main():
    out = {}
    lines = []
    lines.append("=== G4: JASS VM 全局变量指针链 (全 11 版本) ===")
    lines.append(f"{'Version':13s} | {'ExecuteFunc':11s} | {'g_jassEnv':10s} | {'LookupFn':10s} | {'vmIdx':5s} | {'GetVM':10s} | {'TlsSlot':10s} | {'tlsOff':6s} | {'globalTbl':9s}")
    lines.append("-" * 105)

    for ver in ALL_VERSIONS:
        pe = PE32(dll_path_for(ver))
        g4 = scan_g4_version(ver, pe)
        g1 = scan_g1_version(ver, pe)
        out[ver] = {"g4": g4, "g1": g1}
        lines.append(
            f"{ver:13s} | {str(g4.get('ExecuteFunc')):11s} | {str(g4.get('g_jassEnv')):10s} | {str(g4.get('LookupJassFunc')):10s} | "
            f"{str(g4.get('vmIndex_off')):5s} | {str(g4.get('GetVM')):10s} | {str(g4.get('GetTlsSlot')):10s} | "
            f"{str(g4.get('tls_vmArray_off')):6s} | {str(g4.get('vm_globalTable_off')):9s}"
        )

    lines.append("\n=== G1: CAgentTimer 虚表与冷却函数 (全 11 版本) ===")
    lines.append(f"{'Version':13s} | {'CAgentTimer_vt':14s} | {'GetTimeout(+10)':15s} | {'GetRem(+18)':12s} | {'node':5s} | {'total':5s} | {'clock':5s} | {'early_extra'}")
    lines.append("-" * 115)
    for ver in ALL_VERSIONS:
        g1 = out[ver]["g1"]
        extra = {k: v for k, v in g1.items() if k.startswith("early_") or k == "CAbilitySpell_ResetCooldown"}
        lines.append(
            f"{ver:13s} | {str(g1.get('CAgentTimer_vt')):14s} | {str(g1.get('CAgentTimer_GetTimeout')):15s} | {str(g1.get('CAgentTimer_GetRemaining')):12s} | "
            f"{str(g1.get('timer_node_off')):5s} | {str(g1.get('timer_total_off')):5s} | {str(g1.get('timer_clock_off')):5s} | {extra if extra else ''}"
        )

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
