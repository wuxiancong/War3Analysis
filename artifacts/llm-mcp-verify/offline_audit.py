# -*- coding: utf-8 -*-
"""
独立离线核验脚本（阶段一）：
不引用原文档作为证据，直接从 War3 1.27 Game.dll 反汇编、war3map.j 原文、
以及 DotA 6.83d 提取数据中核验：
  - A2: EL0 可靠金钱数组定义与读写
  - A5/B1: D7O / GN1 / WS / XS 买活完整逻辑与触发条件
  - A5/B2: JQO / JSO / JTO 防御塔强化逻辑 + Game.dll OrderId 表核查 "coldarrows"
  - A6: FL1 定义及所有 FL1("...") 事件键
  - B3: 信使单位 FourCC 与全部技能/OrderId
  - B4: TP 回城卷轴吸附建筑规则与半径
  - A1/A4/A5/B5: 1.27 Game.dll 反汇编核验 CAbility+0x30/+0x34, GetFloatGameState, CTimer, OrderId 表, 0x10~0x12 flags
"""
import os
import re
import struct
import subprocess
import pefile

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
DLL_127 = r"D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\Game.dll"
WAR3MAP_J = r"D:\Qt\workspace\War3Script\war3map.j"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-verify\offline_audit_part1.txt"


def fourcc(n: int) -> str:
    try:
        return struct.pack(">I", n).decode("ascii")
    except Exception:
        return f"0x{n:08X}"


def extract_jass_func(jlines, func_name, max_lines=120):
    """提取 war3map.j 中指定函数的完整原文及行号。"""
    pat = re.compile(rf"^\s*function\s+{re.escape(func_name)}\b")
    for idx, ln in enumerate(jlines):
        if pat.match(ln):
            out = []
            for k in range(idx, min(len(jlines), idx + max_lines)):
                out.append(f"L{k+1}: {jlines[k]}")
                if jlines[k].strip() == "endfunction":
                    break
            return out
    return [f"[NOT FOUND] function {func_name}"]


def disasm(dll, base, rva, sz):
    va1, va2 = base + rva, base + rva + sz
    res = subprocess.run([DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [ln.strip() for ln in res.stdout.splitlines() if re.match(r"^\s+[0-9A-F]{8}:", ln)]


def lookup_order_ids_in_127(data, pe, order_names):
    """在 1.27 Game.dll 的 OrderId 字符串注册表中直接查 order string -> 0xD0xxx 映射。"""
    base = pe.OPTIONAL_HEADER.ImageBase
    text = [s for s in pe.sections if s.Name.startswith(b".text")][0]
    tblob = data[text.PointerToRawData : text.PointerToRawData + text.SizeOfRawData]
    trva = text.VirtualAddress
    results = {}
    for name in order_names:
        target = b"\x00" + name.encode("ascii") + b"\x00"
        pos = data.find(target)
        hits = []
        while pos >= 0:
            rva = pe.get_rva_from_offset(pos + 1)
            if rva is not None:
                va = base + rva
                pat = struct.pack("<I", va)
                k = 0
                while True:
                    j = tblob.find(pat, k)
                    if j < 0:
                        break
                    # 检查前后 24 字节内是否有 0x000D0xxx 常量
                    win = tblob[max(0, j - 24) : min(len(tblob), j + 28)]
                    for off in range(0, len(win) - 3):
                        val = struct.unpack_from("<I", win, off)[0]
                        if 0x000D0000 <= val <= 0x000D0400:
                            hits.append((f"0x{trva + j:X}", f"0x{val:08X}"))
                    k = j + 1
            pos = data.find(target, pos + 1)
        results[name] = sorted(set(hits))
    return results


def main():
    os.makedirs(os.path.dirname(OUT_TXT), exist_ok=True)
    lines = []
    def log(s=""):
        lines.append(s)

    jlines = open(WAR3MAP_J, "r", encoding="utf-8", errors="replace").read().splitlines()

    # 1. A2: EL0 可靠金钱
    log("=== 1. A2: war3map.j 中的 EL0 ===")
    el0_hits = [f"L{i+1}: {l.strip()[:140]}" for i, l in enumerate(jlines) if re.search(r"\bEL0\b", l)]
    log(f"  共 {len(el0_hits)} 处引用，前 25 处：")
    lines.extend("  " + h for h in el0_hits[:25])

    # 2. A6: FL1 函数及所有事件键
    log("\n=== 2. A6: war3map.j 中的 FL1 定义与事件键 ===")
    lines.extend("  " + x for x in extract_jass_func(jlines, "FL1", 40))
    fl1_keys = {}
    for i, l in enumerate(jlines, 1):
        for m in re.finditer(r'\bFL1\s*\(\s*"([^"]+)"', l):
            k = m.group(1)
            fl1_keys.setdefault(k, []).append(i)
    log(f"  FL1 静态字符串键 ({len(fl1_keys)} 种):")
    for k, lnos in sorted(fl1_keys.items()):
        log(f"    \"{k}\": {len(lnos)} 处, 首现 L{lnos[0]} -> {jlines[lnos[0]-1].strip()[:120]}")
    # 也查非字面量调用 FL1(var, ...)
    dyn_fl1 = [f"L{i}: {l.strip()[:120]}" for i, l in enumerate(jlines, 1) if re.search(r'\bFL1\s*\([^"]', l)]
    log(f"  FL1 动态键调用 ({len(dyn_fl1)} 处，前 15 处):")
    lines.extend("    " + x for x in dyn_fl1[:15])

    # 3. A5/B1: 买活 D7O / GN1 / WS / XS
    log("\n=== 3. A5/B1: 买活 D7O / GN1 / 触发注册 ===")
    for fn in ["D7O", "GN1", "GV1"]:
        log(f"  --- function {fn} ---")
        lines.extend("  " + x for x in extract_jass_func(jlines, fn, 80))
    for i, l in enumerate(jlines, 1):
        if "D7O" in l or "GN1" in l or "integer array XS" in l or "integer array WS" in l:
            log(f"  [REF] L{i}: {l.strip()[:140]}")

    # 4. A5/B2: Glyph JQO / JSO / JTO
    log("\n=== 4. A5/B2: Glyph JQO / JSO / JTO ===")
    for fn in ["JQO", "JSO", "JTO"]:
        log(f"  --- function {fn} ---")
        lines.extend("  " + x for x in extract_jass_func(jlines, fn, 70))

    # 5. B3: 信使单位与技能 (在 war3map.j 中搜索 n00I/n022 及 courier/deliver/retrieve/burst)
    log("\n=== 5. B3: war3map.j 信使相关 ===")
    # n00I=1848651849, n022=1848652338, n021=1848652337, n004=1848651828, n018=1848652088, n01C=1848652099, n01G=1848652103
    courier_ids = {
        "1848651849": "n00I",
        "1848652338": "n022",
        "1848652337": "n021",
        "1848651828": "n004",
        "1848652088": "n018",
        "1848652099": "n01C",
        "1848652103": "n01G",
    }
    for cid, cc in courier_ids.items():
        hits = [f"L{i}: {l.strip()[:130]}" for i, l in enumerate(jlines, 1) if cid in l]
        log(f"  {cc} ({cid}): {len(hits)} 处")
        lines.extend("    " + h for h in hits[:6])

    # 6. B4: TP 回城卷轴 (搜索 575 / 525 / Town Portal / A02O / tpsc)
    log("\n=== 6. B4: TP 回城卷轴相关 (war3map.j) ===")
    tp_hits = [f"L{i}: {l.strip()[:130]}" for i, l in enumerate(jlines, 1)
               if any(k in l for k in ["575", "525", "1093677647", "1227895881", "1093744708", "teleport", "townportal"])]
    log(f"  匹配 {len(tp_hits)} 处（前 20 处）：")
    lines.extend("  " + h for h in tp_hits[:20])

    # 7. 1.27 Game.dll: OrderId 表核查 & GetFloatGameState & CUnit::FindAbility
    log("\n=== 7. 1.27 Game.dll OrderId 表核查 ===")
    raw = open(DLL_127, "rb").read()
    pe = pefile.PE(DLL_127, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    order_check = lookup_order_ids_in_127(raw, pe, [
        "coldarrows", "coldarrowstarg", "frostarrows",
        "load", "unload", "unloadall", "unloadallinstant",
        "blink", "berserk", "windwalk", "frenzy",
        "useslot1", "smart", "attack", "move", "stop", "holdposition",
        "dropitem", "moveslot1", "townportal", "channel",
    ])
    for k, v in order_check.items():
        log(f"  {k:20s} -> {v}")

    log("\n=== 8. 1.27 GetFloatGameState (0x1E2500) 反汇编 ===")
    lines.extend("  " + l for l in disasm(DLL_127, base, 0x1E2500, 0x90))

    log("\n=== 9. 1.27 CUnit::FindAbility (0x46F440) 反汇编 ===")
    lines.extend("  " + l for l in disasm(DLL_127, base, 0x46F440, 0x110))

    pe.close()
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
