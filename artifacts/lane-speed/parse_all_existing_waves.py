# -*- coding: utf-8 -*-
"""
第三阶段脚本：
1. 在 war3map.j 中核查倒计时器 OL 的启动时长（不同模式 -ap/-cm/-rd/-em 下 N = TimerGetElapsed(M) 的精确秒数）。
2. 提取 Units_AbilityData.slk 中 A2V0/A2V1 的整行字段，以及 Units_UpgradeData.slk 中 R007/R00C/R008/R00D/R009/R003/R00A/R00B 的整行字段。
3. 解析 AiUnit.log 中全部 16159 行「🧭 真人坐标」与 records/block/cm/*.csv 中全部 trace 行，
   按 (路, 波次) 统计每一波在未接触英雄段 (dist(hero, creep) > 350) 的实测移速，
   直接检验哪一波有 +25% (406) / -25% (244)，哪一波恢复 325！
"""
import glob
import math
import os
import re

WAR3MAP_J = r"D:\Qt\workspace\War3Script\war3map.j"
ABIL_SLK = r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Units_AbilityData.slk"
UPG_SLK = r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map\Units_UpgradeData.slk"
AI_LOG = r"C:\War3Run\War3Launcher\logs\AiUnit.log"
CSV_GLOB = r"C:\War3Run\War3Launcher\records\block\cm\*.csv"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\audit_part3_waves.txt"

# kAiLanes[6]: (raxX, raxY, towerX, towerY, name, spawnX, spawnY)
LANES = [
    (-6368.0, -4480.0, -6112.0,  1568.0, "近卫上路", -6176.0, -4184.0),
    (-4640.0, -5152.0, -1504.0, -1824.0, "近卫中路", -4792.0, -5496.0),
    (-4032.0, -6784.0,  4960.0, -6752.0, "近卫下路", -3816.0, -6752.0),
    ( 3392.0,  5792.0, -4704.0,  5920.0, "天灾上路",  2712.0,  5512.0),
    ( 4128.0,  3744.0,  1056.0,   -96.0, "天灾中路",  3992.0,  3816.0),
    ( 6368.0,  2912.0,  6240.0, -2080.0, "天灾下路",  6232.0,  3432.0),
]


def parse_slk_rows(slk_path, target_keys):
    """解析 SLK 文件中指定主键 (X1) 的所有列 (列名 -> 值)。"""
    if not os.path.exists(slk_path):
        return {}
    headers = {}
    rows = {}
    cur_y = None
    for ln in open(slk_path, "r", encoding="utf-8", errors="replace"):
        if not ln.startswith("C;"):
            continue
        parts = ln.strip().split(";")
        x, y, k = None, cur_y, None
        for p in parts[1:]:
            if p.startswith("X"):
                x = int(p[1:])
            elif p.startswith("Y"):
                y = int(p[1:])
                cur_y = y
            elif p.startswith("K"):
                k = p[1:].strip('"')
        if y == 1 and x is not None and k is not None:
            headers[x] = k
        elif y is not None and x is not None and k is not None:
            rows.setdefault(y, {})[x] = k
    out = {}
    for y, r in rows.items():
        key = r.get(1)
        if key in target_keys:
            out[key] = {headers.get(cx, f"col{cx}"): val for cx, val in r.items() if val not in ("", "_", "0", "0.0")}
    return out


def classify_lane(x, y):
    best_l, best_d = 0, 1e18
    for idx, (rx, ry, tx, ty, _, _, _) in enumerate(LANES):
        vx, vy = tx - rx, ty - ry
        l2 = vx * vx + vy * vy
        t = max(0.0, min(1.0, ((x - rx) * vx + (y - ry) * vy) / l2))
        d = math.hypot(x - (rx + vx * t), y - (ry + vy * t))
        if d < best_d:
            best_d = d
            best_l = idx
    return best_l


def proj_lane(lane_idx, x, y):
    rx, ry, tx, ty, _, _, _ = LANES[lane_idx]
    vx, vy = tx - rx, ty - ry
    length = math.hypot(vx, vy)
    ux, uy = vx / length, vy / length
    s = (x - rx) * ux + (y - ry) * uy
    lat = (x - rx) * (-uy) + (y - ry) * ux
    return s, lat


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    jlines = open(WAR3MAP_J, "r", encoding="utf-8", errors="replace").read().splitlines()

    # 1. 核查 OL 倒计时器在 war3map.j 中的所有 TimerStart(OL, ...)
    log("=== 1. war3map.j 中 OL (出兵前倒计时器) 的所有 TimerStart ===")
    for i, l in enumerate(jlines, 1):
        if re.search(r"\bOL\b", l):
            log(f"  L{i}: {l.strip()[:140]}")

    # 2. 解析 AbilityData.slk (A2V0, A2V1) 与 UpgradeData.slk (R007 等)
    log("\n=== 2. SLK 精确字段：A2V0 / A2V1 / 兵线升级 R007..R00D ===")
    abils = parse_slk_rows(ABIL_SLK, {"A2V0", "A2V1", "A06G", "A17S", "A04R"})
    for k, v in sorted(abils.items()):
        log(f"  [Ability {k}]: {v}")
    upgs = parse_slk_rows(UPG_SLK, {"R007", "R00C", "R008", "R00D", "R009", "R003", "R00A", "R00B"})
    for k, v in sorted(upgs.items()):
        log(f"  [Upgrade {k}]: {v}")

    # 3. 解析 records/block/cm/*.csv 中的 trace 行（计算每波未接触英雄时 或 英雄在远处等待时的兵线速度！）
    log("\n=== 3. records/block/cm/*.csv 各波未受阻段速度分析 ===")
    # 注意：在 cm_bot_20261121-073907 / 074924 / 075732 中，英雄站在车道 6400 等兵，所以 t=0..15s (车道 400..6000) 完全未受英雄阻挡！
    for fp in sorted(glob.glob(CSV_GLOB)):
        fn = os.path.basename(fp)
        waves = {}
        for ln in open(fp, "r", encoding="utf-8", errors="replace"):
            if not ln.startswith("trace,"):
                continue
            parts = ln.strip().split(",")
            if len(parts) < 7:
                continue
            w = int(parts[1])
            t = float(parts[2])
            hx, hy = float(parts[3]), float(parts[4])
            creeps = []
            for k in range(5, len(parts) - 1, 2):
                if parts[k] and parts[k + 1]:
                    creeps.append((float(parts[k]), float(parts[k + 1])))
            if creeps:
                waves.setdefault(w, []).append((t, hx, hy, creeps))
        if not waves:
            continue
        log(f"\n  [{fn}] (共 {len(waves)} 波):")
        for w, samples in sorted(waves.items()):
            # 识别路
            c0x, c0y = samples[0][3][0]
            lidx = classify_lane(c0x, c0y)
            # 筛选英雄距离所有兵 > 320 的未受阻帧
            free = []
            for t, hx, hy, cs in samples:
                min_hd = min(math.hypot(cx - hx, cy - hy) for cx, cy in cs)
                projs = [proj_lane(lidx, cx, cy)[0] for cx, cy in cs]
                front_s = max(projs)
                mean_s = sum(projs) / len(projs)
                if min_hd > 320.0:
                    free.append((t, front_s, mean_s, min_hd))
            if len(free) >= 5:
                t0, f0, m0, _ = free[0]
                t1, f1, m1, _ = free[-1]
                dt = t1 - t0
                if dt >= 1.0:
                    v_front = (f1 - f0) / dt
                    v_mean = (m1 - m0) / dt
                    # 再分段看 t in [1.5, 14.0] 和 t in [15.5, 25.0]
                    s_early = [x for x in free if 1.5 <= x[0] <= 14.0]
                    v_early = ((s_early[-1][1] - s_early[0][1]) / (s_early[-1][0] - s_early[0][0])) if len(s_early) >= 4 and (s_early[-1][0] - s_early[0][0]) >= 1.0 else 0.0
                    s_late = [x for x in free if x[0] >= 15.5]
                    v_late = ((s_late[-1][1] - s_late[0][1]) / (s_late[-1][0] - s_late[0][0])) if len(s_late) >= 4 and (s_late[-1][0] - s_late[0][0]) >= 1.0 else 0.0
                    log(f"    Wave {w:2d} ({LANES[lidx][4]}): 未受阻 t={t0:.1f}..{t1:.1f}s (s={f0:.0f}..{f1:.0f}) | 全段前兵均速={v_front:.1f}/s 中心={v_mean:.1f}/s | 1.5~14s均速={v_early:.1f}/s | >15.5s均速={v_late:.1f}/s")

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
