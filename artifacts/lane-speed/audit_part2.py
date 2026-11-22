# -*- coding: utf-8 -*-
"""
第二阶段深度核查脚本：
1. 提取 war3map.j 中 SGO / SHO / ZG 刷兵触发器启动逻辑 / L27800..L27860 号角启动逻辑，
   精确计算 TimerGetElapsed(M) < 420 对应的真实游戏钟时间与波次！
2. 解码 TQO (每 450s 升级) 的 8 个科技 FourCC，并在 UpgradeData.slk 中核查是否含移速加成。
3. 提取 AbilityData.slk 中 A2V1 / A2V0 及 BuffData.slk 中 B0H2 / B0H1 的完整字段。
4. 检查 C:\War3Run\War3Launcher\lane_paths.txt、position_marks.txt 及 AiUnit.log 中已记录的所有路基线/轨迹。
"""
import os
import re
import struct

WAR3MAP_J = r"D:\Qt\workspace\War3Script\war3map.j"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\audit_part2_report.txt"


def fourcc(n: int) -> str:
    try:
        return struct.pack(">I", n).decode("ascii")
    except Exception:
        return f"0x{n:08X}"


def extract_jass_func(jlines, func_name, max_lines=100):
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


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    jlines = open(WAR3MAP_J, "r", encoding="utf-8", errors="replace").read().splitlines()

    # 1. SGO / SHO / SPO 下半段 (L23320..L23380)
    log("=== 1. SGO / SHO 与 SPO 下半段 ===")
    for fn in ["SGO", "SHO"]:
        log(f"--- function {fn} ---")
        lines.extend("  " + x for x in extract_jass_func(jlines, fn, 30))
    log("--- SPO L23320..L23375 ---")
    for k in range(23319, min(len(jlines), 23375)):
        log(f"  L{k+1}: {jlines[k]}")

    # 2. ZG 刷兵触发器与 L27790..L27875 号角时间 N 的精确关系
    log("\n=== 2. ZG 刷兵触发器与号角时间 N (L27790..L27875) ===")
    for k in range(27789, min(len(jlines), 27875)):
        log(f"  L{k+1}: {jlines[k]}")
    log("--- 搜索 ZG 的所有引用 ---")
    for i, l in enumerate(jlines, 1):
        if re.search(r"\bZG\b", l):
            log(f"  L{i}: {l.strip()[:140]}")

    # 3. TQO 科技升级 FourCC 解码与检索
    log("\n=== 3. TQO (每 450s 升级) 科技 FourCC ===")
    tqo_ids = [1378889783, 1378889795, 1378889784, 1378889796, 1378889785, 1378889779, 1378889793, 1378889794]
    for tid in tqo_ids:
        log(f"  {tid} = '{fourcc(tid)}'")
    for i, l in enumerate(jlines, 1):
        if "TQO" in l:
            for k in range(max(0, i - 3), min(len(jlines), i + 5)):
                log(f"  L{k+1}: {jlines[k].strip()[:140]}")
            log("  ---")

    # 4. 查找已提取的 SLK 文件 (AbilityData.slk / UpgradeData.slk)
    log("\n=== 4. 查找工作区中的 SLK 文件 ===")
    slk_files = []
    for root, _, files in os.walk(r"D:\Qt\workspace\War3Analysis"):
        for fn in files:
            if fn.lower().endswith(".slk"):
                slk_files.append(os.path.join(root, fn))
    log(f"  找到 SLK 文件: {slk_files}")
    for sf in slk_files:
        txt = open(sf, "r", encoding="utf-8", errors="replace").read()
        for key in ["A2V0", "A2V1", "B0H1", "B0H2", "R007", "R00J", "R008", "R00K", "R009", "R003", "R00H", "R00I"]:
            if key in txt:
                log(f"  [{os.path.basename(sf)}] hit {key}:")
                for ln in txt.splitlines():
                    if f'"{key}"' in ln:
                        log(f"    {ln[:160]}")

    # 5. 检查 C:\War3Run\War3Launcher\lane_paths.txt 与 position_marks.txt
    log("\n=== 5. C:\\War3Run\\War3Launcher 下的 lane_paths.txt / position_marks.txt ===")
    for fn in ["lane_paths.txt", "position_marks.txt", "lane_marks.txt", "scores.csv"]:
        fp = os.path.join(r"C:\War3Run\War3Launcher", fn)
        if os.path.exists(fp):
            content = open(fp, "r", encoding="utf-8", errors="replace").read().splitlines()
            log(f"  [{fn}] ({len(content)} lines):")
            for l in content[:20]:
                log("    " + l[:160])

    # 6. 统计 AiUnit.log 中各路的基线与轨迹波次
    log("\n=== 6. AiUnit.log 中各路记录检索 ===")
    ai_log = r"C:\War3Run\War3Launcher\logs\AiUnit.log"
    if os.path.exists(ai_log):
        raw = open(ai_log, "rb").read()
        ltxt = raw.decode("utf-16", errors="ignore") if b"\x00" in raw[:200] else raw.decode("utf-8", errors="replace")
        for line in ltxt.splitlines():
            if any(k in line for k in ["卡兵路线：", "兵线路径：", "基线（不卡）", "卡兵评分 第", "拖延 第"]):
                log("  " + line.strip()[:160])

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
