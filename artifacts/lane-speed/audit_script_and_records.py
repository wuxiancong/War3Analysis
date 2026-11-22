# -*- coding: utf-8 -*-
"""
第一阶段全量分析脚本：
1. 提取 war3map.j 中 SPO / SZO / SVO / AX1 / AW1 / TQO / M 计时器 / N 号角时间 的完整原文，
   核查 A2V1 (+25%) / A2V0 (-25%) 的触发条件、持续时间、7:00 切换点、模式/塔/人数影响、450s 升级影响。
2. 扫描全 11 个 War3 版本 Game.dll 的移速计算链 RVA：
   GetUnitMoveSpeed -> CUnit::GetMoveSpeed -> CAbilityMove::CalcMoveSpeed -> GroupSpeedMin -> StepTurnAndMove -> AddVelocity。
3. 扫描 C:\War3Run\War3Launcher\logs\AiUnit.log (5MB) 与 records\block\cm\*.csv 中已有的各路波次轨迹。
"""
import glob
import json
import os
import re
import struct
import subprocess
import pefile

WAR3MAP_J = r"D:\Qt\workspace\War3Script\war3map.j"
VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"
DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
OUT_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed"
OUT_TXT = os.path.join(OUT_DIR, "audit_part1_report.txt")


def extract_jass_func(jlines, func_name, max_lines=140):
    pat = re.compile(rf"^\s*function\s+{re.escape(func_name)}\b")
    for idx, ln in enumerate(jlines):
        if pat.match(ln):
            out = []
            for k in range(idx, min(len(jlines), idx + max_lines)):
                out.append(f"L{k+1}: {jlines[k]}")
                if jlines[k].strip() == "endfunction":
                    break
            return out
    return [f"[NOT FOUND] {func_name}"]


def disasm(dll, base, rva, sz):
    va1, va2 = base + rva, base + rva + sz
    res = subprocess.run([DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ln.strip() for ln in res.stdout.splitlines() if re.match(r"^\s+[0-9A-F]{8}:", ln)]


def calls_in(asm, base):
    out = []
    for i, ln in enumerate(asm):
        m = re.search(r"\b(call|jmp)\s+([0-9A-F]{8})\b", ln)
        if m:
            va = int(m.group(2), 16)
            if base <= va < base + 0x2000000:
                out.append((i, m.group(1), va - base))
    return out


def find_native(pe, data, tblob, name):
    base = pe.OPTIONAL_HEADER.ImageBase
    target = b"\x00" + name.encode("ascii") + b"\x00"
    start = 0
    while True:
        pos = data.find(target, start)
        if pos < 0:
            break
        rva = pe.get_rva_from_offset(pos + 1)
        if rva is not None:
            va = base + rva
            pat = struct.pack("<I", va)
            k = 0
            while True:
                j = tblob.find(pat, k)
                if j < 0:
                    break
                if j >= 1 and j + 9 < len(tblob) and tblob[j - 1] == 0xBA and tblob[j + 4] == 0xB9:
                    return struct.unpack_from("<I", tblob, j + 5)[0] - base
                if j >= 6 and tblob[j - 6] == 0xB9 and tblob[j - 1] == 0xBA:
                    return struct.unpack_from("<I", tblob, j - 5)[0] - base
                k = j + 1
        start = pos + 1
    return None


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    lines = []
    def log(s=""):
        lines.append(s)

    # 1. war3map.j 时间维度与光环核查
    jtxt = open(WAR3MAP_J, "r", encoding="utf-8", errors="replace").read()
    jlines = jtxt.splitlines()
    log("=== 1. war3map.j 时间维度：SPO / SZO / SVO / AX1 / AW1 / TQO ===")
    for fn in ["SPO", "SZO", "SUO", "SVO", "STO", "AX1", "AW1", "TQO", "SSO"]:
        log(f"\n--- function {fn} ---")
        lines.extend("  " + x for x in extract_jass_func(jlines, fn, 130))

    # 搜索 A2V1 (1093813809) 和 A2V0 (1093813808) 的所有出现位置
    log("\n--- A2V1 (1093813809) / A2V0 (1093813808) / B0H2 / B0H1 全图检索 ---")
    for i, l in enumerate(jlines, 1):
        if any(k in l for k in ["1093813809", "1093813808", "1110452274", "1110452273", "SZO", "SVO"]):
            log(f"  L{i}: {l.strip()[:140]}")

    # 搜索计时器 M 和偏移 N 的初始化与出兵号角启动关系
    log("\n--- 计时器 M 与出兵号角时间 N 的定义与启动 ---")
    for i, l in enumerate(jlines, 1):
        if re.search(r"\bTimerStart\s*\(\s*M\b|\bset\s+N\s*=|\bcall\s+SPO\b", l):
            for k in range(max(0, i - 4), min(len(jlines), i + 5)):
                log(f"  L{k+1}: {jlines[k].strip()[:140]}")
            log("  ---")

    # 2. 全 11 个版本 Game.dll 移速计算链 RVA
    log("\n=== 2. 全 11 版本 Game.dll 移速计算链 RVA ===")
    all_vers = sorted(os.listdir(VERSIONS_DIR))
    rva_table = {}
    for ver in all_vers:
        dll = os.path.join(VERSIONS_DIR, ver, "Game.dll")
        if not os.path.exists(dll):
            continue
        raw = open(dll, "rb").read()
        pe = pefile.PE(dll, fast_load=True)
        base = pe.OPTIONAL_HEADER.ImageBase
        text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
        tblob = raw[text.PointerToRawData : text.PointerToRawData + text.SizeOfRawData]

        ms_nat = find_native(pe, raw, tblob, "GetUnitMoveSpeed")
        ts_nat = find_native(pe, raw, tblob, "GetUnitTurnSpeed")
        pw_nat = find_native(pe, raw, tblob, "GetUnitPropWindow")
        pe.close()

        cunit_ms, amov_calc = None, None
        if ms_nat:
            asm1 = disasm(dll, base, ms_nat, 0x120)
            ret_i = next((i for i, l in enumerate(asm1) if l.endswith("ret") or " ret " in l), len(asm1))
            cs1 = calls_in(asm1[: ret_i + 1], base)
            if cs1:
                cunit_ms = cs1[-1][2]
                asm2 = disasm(dll, base, cunit_ms, 0x40)
                cs2 = calls_in(asm2, base)
                if cs2:
                    amov_calc = cs2[-1][2]

        rva_table[ver] = {
            "GetUnitMoveSpeed": f"0x{ms_nat:X}" if ms_nat else "-",
            "CUnit::GetMoveSpeed": f"0x{cunit_ms:X}" if cunit_ms else "-",
            "CAbilityMove::CalcMoveSpeed": f"0x{amov_calc:X}" if amov_calc else "-",
            "GetUnitTurnSpeed": f"0x{ts_nat:X}" if ts_nat else "-",
            "GetUnitPropWindow": f"0x{pw_nat:X}" if pw_nat else "-",
        }
        log(f"  {ver:13s}: {rva_table[ver]}")

    # 反汇编 1.27 与 1.26 的 CAbilityMove::CalcMoveSpeed 内部实现
    for ver in ["1.27.0.52240", "1.26.0.6401"]:
        dll = os.path.join(VERSIONS_DIR, ver, "Game.dll")
        base = pefile.PE(dll, fast_load=True).OPTIONAL_HEADER.ImageBase
        rva_str = rva_table[ver]["CAbilityMove::CalcMoveSpeed"]
        if rva_str != "-":
            log(f"\n--- {ver} CAbilityMove::CalcMoveSpeed @ {rva_str} ---")
            lines.extend("  " + l for l in disasm(dll, base, int(rva_str, 16), 0x120))

    # 3. 汇总 records/block/cm/*.csv 与 AiUnit.log 中的波次概况
    log("\n=== 3. records/block/cm/*.csv 波次概况 ===")
    for fp in sorted(glob.glob(r"C:\War3Run\War3Launcher\records\block\cm\*.csv")):
        fn = os.path.basename(fp)
        txt = open(fp, "r", encoding="utf-8", errors="replace").read()
        hdrs = [l for l in txt.splitlines() if l.startswith("#") or l.startswith("wave,")]
        trace_cnt = sum(1 for l in txt.splitlines() if l.startswith("trace,"))
        log(f"  [{fn}] (trace lines={trace_cnt})")
        for h in hdrs[:15]:
            log("    " + h)

    log("\n=== 4. AiUnit.log 中基线/卡兵统计概况 ===")
    ai_log = r"C:\War3Run\War3Launcher\logs\AiUnit.log"
    if os.path.exists(ai_log):
        # AiUnit.log 可能是 UTF-16LE 或 UTF-8
        raw_log = open(ai_log, "rb").read()
        try:
            ltxt = raw_log.decode("utf-16", errors="ignore") if b"\x00" in raw_log[:200] else raw_log.decode("utf-8", errors="replace")
        except Exception:
            ltxt = raw_log.decode("utf-8", errors="replace")
        measure_lines = [l.strip() for l in ltxt.splitlines() if "📏" in l or "基线" in l or "[评分]" in l or "真人坐标" in l]
        coord_cnt = sum(1 for l in ltxt.splitlines() if "真人坐标" in l)
        non_coord = [l.strip() for l in ltxt.splitlines() if ("📏" in l or "基线" in l or "[评分]" in l or "波" in l) and "真人坐标" not in l and "📍" not in l]
        log(f"  AiUnit.log 总行数={len(ltxt.splitlines())}, 真人坐标行数={coord_cnt}, 关键统计行数={len(non_coord)}")
        for l in non_coord[-60:]:
            log("    " + l[:140])

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
