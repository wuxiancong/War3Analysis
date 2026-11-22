# -*- coding: utf-8 -*-
"""
独立离线核验脚本（阶段二）：
精确核查：
  1. B1: GZ1 / ZS[] / WS[] / GM1 / XS[] 买活 60 档单位 FourCC 与条件
  2. B2: JPO 与 1.27 Game.dll 0x46B900..0x46B960 ("coldarrows" 精确 OrderId)
  3. B3: L3691/L5352/L5602 信使全集 + D7O 中的 DIO/D4O + 信使技能触发函数与 OrderId
  4. B4: MS0 (575) 与 1093677647 (TP) 完整逻辑
  5. A1: 1.27 CTimer (0x0434F0 / 0x043700) 内部字段布局（剩余冷却 & 总冷却）
  6. A5: 1.27 GetFloatGameState 内层 0x2676D0 / 0x03ADF0 昼夜时间内存偏移
  7. B5: 1.27 Action 0x10/0x11/0x12 abilityFlags bit 0x01 (Shift 队列) 汇编验证
"""
import os
import re
import struct
import subprocess
import pefile

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
DLL_127 = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
WAR3MAP_J = r"D:\Qt\workspace\War3Script\war3map.j"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-verify\offline_audit_part2.txt"


def fourcc(n: int) -> str:
    try:
        return struct.pack(">I", n).decode("ascii")
    except Exception:
        return f"0x{n:08X}"


def extract_jass_func(jlines, func_name, max_lines=90):
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


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    jlines = open(WAR3MAP_J, "r", encoding="utf-8", errors="replace").read().splitlines()

    # 1. B1: GZ1, GM1, ZS[0..5], WS[0..5], DIO, D4O
    log("=== 1. B1: GZ1 / GM1 / ZS / WS / DIO / D4O ===")
    for v, desc in [(1747990581, "D7O_1"), (1747993174, "D7O_2"), (1747993669, "D7O_3"), (1848659508, "D7O_msg")]:
        log(f"  {desc}: {v} = '{fourcc(v)}'")
    for fn in ["GZ1", "GM1", "GH1", "JPO"]:
        log(f"  --- function {fn} ---")
        lines.extend("  " + x for x in extract_jass_func(jlines, fn, 60))
    log("  --- ZS / WS 初始化示例 ---")
    zs_hits = [f"L{i}: {l.strip()}" for i, l in enumerate(jlines, 1) if "set ZS[" in l or "set WS[" in l]
    for h in zs_hits[:12]:
        log("  " + h)
    # 解码前 3 个 ZS
    for h in zs_hits[:6]:
        m = re.search(r"set ZS\[(\d+)\]=(\d+)", h)
        if m:
            log(f"    ZS[{m.group(1)}] = '{fourcc(int(m.group(2)))}'")

    # 2. B3: 信使全集 (L3691, L5352, L5602) 与信使技能
    log("\n=== 2. B3: war3map.j 信使类型与技能 ===")
    for lno in [3691, 5352, 5602]:
        raw_l = jlines[lno - 1].strip()
        log(f"  L{lno}: {raw_l}")
        nums = sorted(set(int(x) for x in re.findall(r"\b1[6-9]\d{8}\b", raw_l)))
        log("    FourCCs: " + ", ".join(f"'{fourcc(n)}'({n})" for n in nums))
    # 查 DIO / D4O
    for fn in ["DIO", "D4O"]:
        log(f"  --- function {fn} ---")
        lines.extend("  " + x for x in extract_jass_func(jlines, fn, 50))
    # 查信使运送/加速技能（搜索 speedburst / burst / deliver / courier 技能订单）
    log("  --- 搜索 war3map.j 中的信使/储藏处 Order 字符串 ---")
    for i, l in enumerate(jlines, 1):
        if any(k in l for k in ["D30[", "courier", "Courier", "burst", "Burst"]) and ("Issue" in l or "Order" in l or "GetSpellAbilityId" in l):
            log(f"    L{i}: {l.strip()[:140]}")

    # 3. B4: MS0 (575) 与 TP (1093677647 = 'A02O'?)
    log("\n=== 3. B4: TP 吸附规则 (MS0 & 1093677647) ===")
    log(f"  1093677647 = '{fourcc(1093677647)}', 1093744708 = '{fourcc(1093744708)}', 1227895881 = '{fourcc(1227895881)}'")
    for i, l in enumerate(jlines, 1):
        if re.search(r"\bMS0\b", l):
            for k in range(max(0, i - 3), min(len(jlines), i + 4)):
                log(f"    L{k+1}: {jlines[k].strip()[:140]}")
            log("    ---")
    # 也看 L22203 附近
    log("  --- L22200..L22245 ---")
    for k in range(22199, min(len(jlines), 22245)):
        log(f"    L{k+1}: {jlines[k].strip()[:140]}")

    # 4. 1.27 Game.dll 反汇编
    pe = pefile.PE(DLL_127, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase

    log("\n=== 4. 1.27 OrderId 表: coldarrows 附近 (0x46B900..0x46B960) ===")
    lines.extend("  " + l for l in disasm(DLL_127, base, 0x46B900, 0x60))

    log("\n=== 5. 1.27 CTimer (0x0434F0 & 0x043700) 布局 ===")
    log("  [0x0434F0]")
    lines.extend("  " + l for l in disasm(DLL_127, base, 0x0434F0, 0x70))
    log("  [0x043700]")
    lines.extend("  " + l for l in disasm(DLL_127, base, 0x043700, 0x90))

    log("\n=== 6. 1.27 GetFloatGameState 内层 (0x2676D0 & 0x03ADF0) ===")
    log("  [0x2676D0]")
    lines.extend("  " + l for l in disasm(DLL_127, base, 0x2676D0, 0x45))
    log("  [0x03ADF0]")
    lines.extend("  " + l for l in disasm(DLL_127, base, 0x03ADF0, 0x45))

    # 7. 搜索 1.27 Action 0x10 / 0x11 / 0x12 处理器（查 CNetCommandUnitOrder 或 0xD0021 / abilityFlags）
    log("\n=== 7. 1.27 CNetCommandUnitOrder / Shift flags ===")
    raw = open(DLL_127, "rb").read()
    for s in [b"CNetCommand", b"CGameUI", b"CTimer", b"CAbilitySpell"]:
        hits = []
        p = 0
        while True:
            i = raw.find(s, p)
            if i < 0:
                break
            end = raw.find(b"\x00", i)
            if 0 < end - i < 64:
                txt = raw[i:end].decode("ascii", errors="ignore")
                if any(k in txt for k in ["Order", "Timer", "AbilitySpell", "Queue"]):
                    hits.append(txt)
            p = i + 1
        log(f"  RTTI/Str '{s.decode()}': {sorted(set(hits))[:15]}")

    pe.close()
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
