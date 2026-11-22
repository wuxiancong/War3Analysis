# -*- coding: utf-8 -*-
"""
二阶段补齐：反汇编 CUnit::ResetCooldown / CUnit::CountBuffsEx，提取 AiControlManager 命令表，定位 war3map.j 肉山与信使技能。
"""
import os
import re
import subprocess
import pefile

DUMPBIN = r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx64\x64\dumpbin.exe"
VERSIONS_DIR = r"D:\Qt\workspace\War3Launcher\versions"
LAUNCHER_DIR = r"D:\Qt\workspace\War3Launcher"
OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\llm-mcp\re_gaps_report2.txt"


def disasm_range(dll_path: str, rva_start: int, size: int) -> str:
    pe = pefile.PE(dll_path, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    va1 = base + rva_start
    va2 = va1 + size
    cmd = [DUMPBIN, "/nologo", "/disasm", f"/range:0x{va1:X},0x{va2:X}", dll_path]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return "\n".join(ln for ln in res.stdout.splitlines() if re.match(r"^\s+[0-9A-F]{8}:", ln))


def find_game_dll(ver_prefix: str) -> str:
    for name in os.listdir(VERSIONS_DIR):
        if name.startswith(ver_prefix):
            p = os.path.join(VERSIONS_DIR, name, "Game.dll")
            if os.path.exists(p):
                return p
    return ""


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    # 1. 反汇编 CUnit::ResetCooldown 和 CUnit::CountBuffsEx (1.27 & 1.26)
    for ver, funcs in [
        ("1.27", [("CUnit::ResetCooldown", 0x471690, 0x100), ("CUnit::CountBuffsEx", 0x46E630, 0x160)]),
        ("1.26", [("CUnit::ResetCooldown", 0x078C00, 0x100), ("CUnit::CountBuffsEx", 0x076E60, 0x160)]),
    ]:
        dll = find_game_dll(ver)
        log(f"=== {ver} ({dll}) ===")
        for name, rva, sz in funcs:
            log(f"\n[{name} @ RVA 0x{rva:X}]")
            log(disasm_range(dll, rva, sz))

    # 2. 提取 AiControlManager::handleRemoteCommand 中所有命令分支
    log("\n=== AiControlManager::handleRemoteCommand 命令分支 ===")
    acm_path = os.path.join(LAUNCHER_DIR, "managers", "AiControlManager.cpp")
    txt = open(acm_path, "r", encoding="utf-8", errors="replace").read()
    # 查找所有 QStringLiteral("...") 在 handleRemoteCommand 内 (L295..L1666)
    acm_lines = txt.splitlines()
    body = "\n".join(acm_lines[294:1666])
    verbs = sorted(set(re.findall(r'(?:verb|action|cmd|sub|token|parts\.at\(0\)|parts\[0\])\s*==\s*(?:QStringLiteral\()?"([a-zA-Z0-9_\-]+)"', body)))
    log(f"  匹配到的命令动词 ({len(verbs)}): {', '.join(verbs)}")
    # 顺便找所有 == QStringLiteral("...") 出现在 if/else if 条件里的
    if_verbs = sorted(set(re.findall(r'if\s*\([^;\n]*==\s*QStringLiteral\("([a-zA-Z0-9_\-]+)"\)', body)))
    log(f"  if 条件 QStringLiteral ({len(if_verbs)}): {', '.join(if_verbs)}")

    # 3. 定位 war3map.j 查肉山坐标和信使技能
    log("\n=== 定位 war3map.j ===")
    j_candidates = []
    for base_dir in [r"D:\Qt\workspace\War3Analysis", r"D:\Qt\workspace\War3Script"]:
        if not os.path.isdir(base_dir):
            continue
        for root, _, files in os.walk(base_dir):
            for fn in files:
                if fn.lower() == "war3map.j":
                    j_candidates.append(os.path.join(root, fn))
    log(f"  找到 war3map.j: {j_candidates}")
    if j_candidates:
        jtxt = open(j_candidates[0], "r", encoding="utf-8", errors="replace").read()
        jlines = jtxt.splitlines()
        log("  --- 肉山相关 (1848651852='n00L' / Roshan / D4) ---")
        cnt = 0
        for idx, ln in enumerate(jlines, 1):
            if any(k in ln for k in ["1848651852", '"Roshan"', '"AegisOn"', "D4=Rect", "KB=Rect"]):
                log(f"    L{idx}: {ln.strip()[:140]}")
                cnt += 1
                if cnt >= 25:
                    break
        # 查找肉山刷新点 CreateUnit(..., 1848651852, ...)
        for idx, ln in enumerate(jlines, 1):
            if "CreateUnit" in ln and "1848651852" in ln:
                for k in range(max(0, idx - 3), min(len(jlines), idx + 3)):
                    log(f"    [CreateRoshan] L{k+1}: {jlines[k].strip()[:140]}")

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_PATH}")


if __name__ == "__main__":
    main()
