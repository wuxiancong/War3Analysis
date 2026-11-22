# -*- coding: utf-8 -*-
"""
全版本批量逆向脚本：扫描 D:\Qt\workspace\War3Launcher\versions\ 下所有 War3 版本，
提取「看局面」所需的全部 25 个 JASS 原生 RVA，以及关键内部函数与结构体偏移验证：
  - CUnit::FindAbility (从 GetUnitAbilityLevel 追踪)
  - CUnit::ResetCooldown & CAbilitySpell::ResetCooldown + 验证 +0x20 & 0x200 与 +0xD0 CTimer 偏移
  - CUnit::CountBuffsEx & ResolveAgent + 验证 +0x1DC 链表偏移
  - IsUnitDetected 内部检测函数
只读分析，不修改任何游戏文件或源码。
"""
import json
import os
import re
import struct
import subprocess
import pefile

VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"
DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp\all_versions_rva.json"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp\all_versions_rva.txt"

NATIVES = [
    "GetLocalPlayer",
    "GetPlayerState",
    "GetFloatGameState",
    "GetHeroLevel",
    "GetHeroXP",
    "GetHeroSkillPoints",
    "GetHeroStr",
    "GetHeroAgi",
    "GetHeroInt",
    "GetUnitState",
    "GetWidgetLife",
    "GetUnitAbilityLevel",
    "UnitItemInSlot",
    "GetItemTypeId",
    "GetItemCharges",
    "UnitResetCooldown",
    "UnitCountBuffsEx",
    "IsUnitVisible",
    "IsUnitDetected",
    "IsUnitFogged",
    "IsUnitMasked",
    "IsLocationVisibleToPlayer",
    "IsUnitType",
    "GetUnitCurrentOrder",
    "GetUnitMoveSpeed",
]


def find_native(pe, data, tblob, name):
    """在 .text 段中定位 JASS 原生注册模式（兼容 mov edx/ecx 与 push 两种编译器生成模式）。"""
    base = pe.OPTIONAL_HEADER.ImageBase
    # 兼容字符串末尾 \x00，避免匹配到更长的子串前缀，要求前字节为 \x00
    target = b"\x00" + name.encode("ascii") + b"\x00"
    start = 0
    while True:
        pos = data.find(target, start)
        if pos < 0:
            break
        str_off = pos + 1
        rva = pe.get_rva_from_offset(str_off)
        if rva is not None:
            va = base + rva
            pat = struct.pack("<I", va)
            k = 0
            while True:
                j = tblob.find(pat, k)
                if j < 0:
                    break
                # 模式 1: mov edx, str_va (BA); mov ecx, fn_va (B9)
                if j >= 1 and j + 9 < len(tblob) and tblob[j - 1] == 0xBA and tblob[j + 4] == 0xB9:
                    fn_va = struct.unpack_from("<I", tblob, j + 5)[0]
                    return fn_va - base
                # 模式 2: mov ecx, fn_va (B9); mov edx, str_va (BA)
                if j >= 6 and tblob[j - 6] == 0xB9 and tblob[j - 1] == 0xBA:
                    fn_va = struct.unpack_from("<I", tblob, j - 5)[0]
                    return fn_va - base
                # 模式 3: push str_va (68); push fn_va (68) 或 mov reg, fn_va (1.28+ MSVC)
                if j >= 1 and j + 9 < len(tblob) and tblob[j - 1] == 0x68:
                    # 检查前后 12 字节内的 push imm32 或 mov ecx/edx, imm32
                    if tblob[j + 4] == 0x68:
                        fn_va = struct.unpack_from("<I", tblob, j + 5)[0]
                        if base < fn_va < base + 0x1000000:
                            return fn_va - base
                    if j >= 6 and tblob[j - 6] == 0x68:
                        fn_va = struct.unpack_from("<I", tblob, j - 5)[0]
                        if base < fn_va < base + 0x1000000:
                            return fn_va - base
                    if j >= 6 and tblob[j - 6] in (0xB9, 0xBA):
                        fn_va = struct.unpack_from("<I", tblob, j - 5)[0]
                        if base < fn_va < base + 0x1000000:
                            return fn_va - base
                    if tblob[j + 4] in (0xB9, 0xBA):
                        fn_va = struct.unpack_from("<I", tblob, j + 5)[0]
                        if base < fn_va < base + 0x1000000:
                            return fn_va - base
                k = j + 1
        start = pos + 1
    return None


def disasm_range(dll_path, base, rva, size):
    """调用 dumpbin 反汇编指定 RVA 范围并返回指令行列表。"""
    va1 = base + rva
    va2 = va1 + size
    cmd = [DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll_path]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ln for ln in res.stdout.splitlines() if re.match(r"^\s+[0-9A-F]{8}:", ln)]


def extract_branch_targets(asm_lines, base):
    """提取反汇编中所有 call / jmp 的目标 RVA。"""
    calls, jmps = [], []
    for ln in asm_lines:
        m = re.search(r"\b(call|jmp)\s+([0-9A-F]{8})\b", ln)
        if m:
            op, va_hex = m.group(1), m.group(2)
            va = int(va_hex, 16)
            if base <= va < base + 0x2000000:
                if op == "call":
                    calls.append(va - base)
                else:
                    jmps.append(va - base)
    return calls, jmps


def analyze_internals(dll_path, base, natives):
    """从已知 JASS 原生入口追踪核心内部函数 RVA 与结构体偏移。"""
    info = {}

    # 1. CUnit::FindAbility <- GetUnitAbilityLevel
    rva = natives.get("GetUnitAbilityLevel")
    if rva:
        asm = disasm_range(dll_path, base, rva, 0x60)
        calls, _ = extract_branch_targets(asm, base)
        # GetUnitAbilityLevel: call HandleToUnit, then call CUnit::FindAbility
        if len(calls) >= 2:
            info["CUnit::FindAbility"] = calls[1]
        info["ability_lvl_off_0x50"] = any("+50h]" in ln for ln in asm)

    # 2. CUnit::ResetCooldown & CAbilitySpell::ResetCooldown <- UnitResetCooldown
    rva = natives.get("UnitResetCooldown")
    if rva:
        asm = disasm_range(dll_path, base, rva, 0x28)
        calls, jmps = extract_branch_targets(asm, base)
        cunit_rc = jmps[-1] if jmps else (calls[1] if len(calls) >= 2 else None)
        if cunit_rc:
            info["CUnit::ResetCooldown"] = cunit_rc
            asm2 = disasm_range(dll_path, base, cunit_rc, 0x100)
            calls2, _ = extract_branch_targets(asm2, base)
            # 验证 CUnit+0x1DC 链表
            info["list_off_0x1DC"] = any("1DCh" in ln for ln in asm2)
            # 在 CUnit::ResetCooldown 中，倒数第 2 个或紧邻 +0x20/inc 后的 call 指向 CAbilitySpell::ResetCooldown
            # 精确识别：逐一检查 callee 前 0x30 字节是否包含 test [reg+20h], 200h 与 +0D0h
            for cand in dict.fromkeys(calls2):
                asm3 = disasm_range(dll_path, base, cand, 0x38)
                joined = "\n".join(asm3)
                if "20h],200h" in joined and "000000D0h" in joined:
                    info["CAbilitySpell::ResetCooldown"] = cand
                    info["cd_off_0x20_0xD0"] = True
                    break
            # 最后一个 call（循环结束后）通常是 CUnit::ResetItemCooldowns
            if calls2:
                # 排除 ResolveAgent 和 RTTI，最后一个有效 call（且不是 ResetCooldown 自身）
                for cand in reversed(calls2):
                    if cand != info.get("CAbilitySpell::ResetCooldown"):
                        asm_ic = disasm_range(dll_path, base, cand, 0x20)
                        c_ic, _ = extract_branch_targets(asm_ic, base)
                        if len(c_ic) >= 2:
                            info["CUnit::ResetItemCooldowns"] = cand
                            break

    # 3. CUnit::CountBuffsEx & ResolveAgent <- UnitCountBuffsEx
    rva = natives.get("UnitCountBuffsEx")
    if rva:
        asm = disasm_range(dll_path, base, rva, 0x45)
        calls, jmps = extract_branch_targets(asm, base)
        cunit_cb = calls[1] if len(calls) >= 2 else (jmps[-1] if jmps else None)
        if cunit_cb:
            info["CUnit::CountBuffsEx"] = cunit_cb
            asm2 = disasm_range(dll_path, base, cunit_cb, 0x50)
            calls2, _ = extract_branch_targets(asm2, base)
            if calls2:
                info["ResolveAgent"] = calls2[0]
            info["buff_list_0x1DC"] = any("1DCh" in ln for ln in asm2)

    # 4. IsUnitDetected 内部函数
    rva = natives.get("IsUnitDetected")
    if rva:
        asm = disasm_range(dll_path, base, rva, 0x50)
        calls, _ = extract_branch_targets(asm, base)
        # HandleToUnit, HandleToPlayer, then CUnit::IsDetected
        if len(calls) >= 3:
            info["CUnit::IsDetected"] = calls[2]

    return info


def main():
    versions = sorted(os.listdir(VERSIONS_DIR))
    results = {}
    lines = []

    for ver in versions:
        vdir = os.path.join(VERSIONS_DIR, ver)
        if not os.path.isdir(vdir):
            continue
        dll = os.path.join(vdir, "Game.dll")
        mod_name = "Game.dll"
        if not os.path.exists(dll):
            dll = os.path.join(vdir, "war3.exe")
            mod_name = "war3.exe"
        if not os.path.exists(dll):
            results[ver] = {"module": None, "natives": {}, "internals": {}}
            continue

        data = open(dll, "rb").read()
        pe = pefile.PE(dll, fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        text_secs = [s for s in pe.sections if s.Name.startswith(b".text")]
        tsec = text_secs[0]
        tblob = data[tsec.PointerToRawData : tsec.PointerToRawData + tsec.SizeOfRawData]

        nat_map = {}
        for n in NATIVES:
            nat_map[n] = find_native(pe, data, tblob, n)
        pe.close()

        internals = analyze_internals(dll, base, nat_map)
        results[ver] = {
            "module": mod_name,
            "image_base": f"0x{base:X}",
            "natives": {k: (f"0x{v:X}" if v is not None else None) for k, v in nat_map.items()},
            "internals": {k: (f"0x{v:X}" if isinstance(v, int) and not isinstance(v, bool) else v) for k, v in internals.items()},
        }
        found_cnt = sum(1 for v in nat_map.values() if v is not None)
        print(f"[{ver}] ({mod_name}): {found_cnt}/{len(NATIVES)} natives, internals={results[ver]['internals']}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # 输出可读汇总表
    vers = list(results.keys())
    hdr = f"{'Symbol':28s} | " + " | ".join(f"{v:13s}" for v in vers)
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for n in NATIVES:
        row = f"{n:28s} | " + " | ".join(f"{(results[v]['natives'].get(n) or '-'):13s}" for v in vers)
        lines.append(row)
    lines.append("-" * len(hdr))
    for ik in [
        "CUnit::FindAbility",
        "CUnit::ResetCooldown",
        "CAbilitySpell::ResetCooldown",
        "CUnit::ResetItemCooldowns",
        "CUnit::CountBuffsEx",
        "ResolveAgent",
        "CUnit::IsDetected",
        "cd_off_0x20_0xD0",
        "list_off_0x1DC",
        "buff_list_0x1DC",
    ]:
        row = f"{ik:28s} | " + " | ".join(f"{str(results[v]['internals'].get(ik, '-')):13s}" for v in vers)
        lines.append(row)

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\nSaved to {OUT_TXT}")


if __name__ == "__main__":
    main()
