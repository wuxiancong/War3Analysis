# -*- coding: utf-8 -*-
"""
收尾核验脚本：
1. 核验 1.26 (及 1.22~1.26) JASS VM 的 vm->globalTable 精确偏移（区分 globalTable 与 stringTable）
2. 补齐 1.0.17~1.21.0 早期 4 个版本的 G4 (g_jassEnv, GetVM, tlsOff, globalTable)
3. 核验 1.0.17~1.21.0 早期 4 个版本的 G1 (UnitResetCooldown / CAgentTimer / UnitCountBuffsEx / IsUnitDetected 真实实现)
4. 核验 1.0.17~1.21.0 的 Send_0x10/0x11/0x12_XY 入口与 UI_PointDispatch
"""
import json
import re
import struct
from pe_util import ALL_VERSIONS, PE32, disasm, dll_path_for

VERIFIED_RVA = json.load(open(r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp\all_versions_rva_verified.json", encoding="utf-8"))
G4G1 = json.load(open(r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\g4_g1_all11.json", encoding="utf-8"))
OUT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-gaps\verify_early4_and_126.txt"


def calls_in(asm, base):
    out = []
    for i, ln in enumerate(asm):
        m = re.search(r"\b(call|jmp)\s+([0-9A-F]{8})\b", ln)
        if m:
            va = int(m.group(2), 16)
            if base < va < base + 0x1000000:
                out.append((i, m.group(1), va - base))
    return out


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    # 1. 核验 1.22~1.26 的 globalTable 偏移 (搜 CreateGlobal: `cmp edx/eax, 9` + `mov [eax+20h], 0` 在 JassVM_FindFunc 附近)
    log("=== 1. 核验 1.22~1.26 JASS VM vm->globalTable 偏移与 vmIndex_off ===")
    for ver in ["1.22.0.6328", "1.23.0.6352", "1.24.1.6374", "1.24.4.6387", "1.25.1.6397", "1.26.0.6401"]:
        pe = PE32(dll_path_for(ver))
        base = pe.image_base
        lk = int(G4G1[ver]["g4"]["LookupJassFunc"], 16)
        asm_lk = disasm(pe.path, base, lk, 0x30)
        # 在 JassVM_FindFunc 附近 0x150 字节内找 CreateGlobal (含 285Ch 或 2860h 且含 +18h / +20h)
        vf = int(G4G1[ver]["g4"]["JassVM_FindFunc"], 16)
        asm_vf = disasm(pe.path, base, vf, 0x180)
        gt_off = None
        for i, l in enumerate(asm_vf):
            m = re.search(r"\+0000(28[0-9A-F]{2})h\]", l)
            if m:
                # 看下面 25 行有没有 +18h / +20h
                sub = "\n".join(asm_vf[i : i + 25])
                if "18h]" in sub and "20h]" in sub:
                    gt_off = f"+0x{m.group(1)}"
                    break
        # 看 LookupJassFunc 里的 vmIndex 偏移
        m_vi = re.search(r"\[(?:ecx|eax|esi|edx)\+([0-9A-F]+)h\]", "\n".join(asm_lk))
        vi_off = f"+0x{m_vi.group(1)}" if m_vi else "?"
        log(f"  {ver}: LookupFn=0x{lk:X} vmIndex={vi_off}, JassVM_FindFunc=0x{vf:X}, vm_globalTable={gt_off}")
        if ver == "1.26.0.6401":
            log("    [1.26 LookupJassFunc]: " + " | ".join(asm_lk[:6]))

    # 2. 早期 4 个版本 (1.0.17~1.21.0) 的 G4 & G1 核验
    log("\n=== 2. 早期 4 个版本 (1.0.17~1.21.0) G4 (g_jassEnv / JASS VM) 与 G1 核验 ===")
    for ver in ["1.0.17.5988", "1.0.20.6048", "1.20.4.6074", "1.21.0.6263"]:
        pe = PE32(dll_path_for(ver))
        base = pe.image_base
        glp = int(VERIFIED_RVA[ver]["natives"]["GetLocalPlayer"], 16)
        urc = int(VERIFIED_RVA[ver]["natives"]["UnitResetCooldown"], 16)
        ucb = int(VERIFIED_RVA[ver]["natives"]["UnitCountBuffsEx"], 16)
        iud = int(VERIFIED_RVA[ver]["natives"]["IsUnitDetected"], 16)

        # 从 GetLocalPlayer 提取 g_jassEnv
        asm_glp = disasm(pe.path, base, glp, 0x40)
        g_env = None
        for l in asm_glp:
            m = re.search(r"dword ptr ds:\[([0-9A-F]{8})h\]", l)
            if m:
                va = int(m.group(1), 16)
                if base + 0x700000 <= va < base + 0xF00000:
                    g_env = va - base
                    break

        # 找 ExecuteFunc: 在早期版本，ExecuteFunc 字符串在 .rdata，找它在 .text 中被注册的位置
        ef_rva = None
        for srva in pe.find_string_rvas("ExecuteFunc"):
            xs = pe.find_xrefs_to_va(base + srva, ".text")
            for x in xs:
                # 看 x 前后 0x20 字节里的 push imm32 (函数地址)
                asm_reg = disasm(pe.path, base, max(0, x - 0x10), 0x25)
                for l in asm_reg:
                    m = re.search(r"mov\s+\w+,([0-9A-F]{8})h|push\s+([0-9A-F]{8})h", l)
                    if m:
                        cand = int(m.group(1) or m.group(2), 16)
                        if base + 0x2A0000 <= cand <= base + 0x300000:
                            ef_rva = cand - base
                            break
                if ef_rva:
                    break

        # 如果找到 ExecuteFunc，追踪 LookupFn -> GetVM -> globalTable
        lk_rva = vm_find = get_vm = tls_slot = tls_off = gt_off = None
        if ef_rva:
            asm_ef = disasm(pe.path, base, ef_rva, 0x75)
            cs_ef = [c for c in calls_in(asm_ef, base) if c[1] == "call"]
            # 找到调 g_jassEnv 之后的 call
            for i, l in enumerate(asm_ef):
                if g_env and f"{base + g_env:08X}h" in l:
                    post = [c for c in cs_ef if c[0] > i]
                    if post:
                        lk_rva = post[0][2]
                        asm_lk = disasm(pe.path, base, lk_rva, 0x35)
                        cs_lk = calls_in(asm_lk, base)
                        if cs_lk:
                            vm_find = cs_lk[0][2]
                            asm_vf = disasm(pe.path, base, vm_find, 0x180)
                            cs_vf = calls_in(asm_vf[:8], base)
                            if cs_vf:
                                get_vm = cs_vf[0][2]
                                asm_gvm = disasm(pe.path, base, get_vm, 0x45)
                                if asm_gvm and "jmp" in asm_gvm[0]:
                                    cj = calls_in(asm_gvm[:2], base)
                                    if cj:
                                        get_vm = cj[0][2]
                                        asm_gvm = disasm(pe.path, base, get_vm, 0x45)
                                cg = calls_in(asm_gvm, base)
                                if cg:
                                    tls_slot = cg[0][2]
                                    if len(cg) >= 2:
                                        aa = "\n".join(disasm(pe.path, base, cg[1][2], 0x25))
                                        mt = re.search(r"\+0*([0-9A-F]+)h\]", aa)
                                        if mt:
                                            tls_off = f"+0x{mt.group(1)}"
                            for j, lv in enumerate(asm_vf):
                                mg = re.search(r"\+0000(28[0-9A-F]{2})h\]", lv)
                                if mg:
                                    sub = "\n".join(asm_vf[j : j + 25])
                                    if "18h]" in sub and "20h]" in sub:
                                        gt_off = f"+0x{mg.group(1)}"
                                        break
                    break

        log(
            f"  {ver}: g_jassEnv={hex(g_env) if g_env else None}, ExecuteFunc={hex(ef_rva) if ef_rva else None}, "
            f"Lookup={hex(lk_rva) if lk_rva else None}, GetVM={hex(get_vm) if get_vm else None}, "
            f"Tls={hex(tls_slot) if tls_slot else None}, tlsOff={tls_off}, globalTbl={gt_off}"
        )

        # 对 1.21.0 打印 UnitResetCooldown -> CUnit::ResetCooldown 和 UnitCountBuffsEx / IsUnitDetected 的反汇编样本，实锤早期版本布局
        if ver == "1.21.0.6263":
            log("    --- [1.21.0 UnitResetCooldown -> CUnit::ResetCooldown 0x48B330] ---")
            for l in disasm(pe.path, base, 0x48B330, 0x90):
                if any(k in l for k in ["call", "1D", "200h", "D0h", "CUnit", "mov"]):
                    log("      " + l)
            log("    --- [1.21.0 UnitCountBuffsEx @ 0x2CBDF0] ---")
            for l in disasm(pe.path, base, ucb, 0x55):
                log("      " + l)
            log("    --- [1.21.0 IsUnitDetected @ 0x2CA230] ---")
            for l in disasm(pe.path, base, iud, 0x55):
                log("      " + l)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines[:45]))
    print(f"... (total {len(lines)} lines written to {OUT})")


if __name__ == "__main__":
    main()
