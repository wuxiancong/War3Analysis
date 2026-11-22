# -*- coding: utf-8 -*-
"""
解析 C:\War3Run\War3Launcher\logs\AiUnit.log 中全部 16159 行「🧭 真人坐标」与 records/block/cm/*.csv 中全部 trace，
按 (分路 0..5, 波次, 时段 <7:00 vs >=7:00) 汇总已有未受阻样本与分段速度！
"""
import glob
import math
import os
import re

AI_LOG = r"C:\War3Run\War3Launcher\logs\AiUnit.log"
CSV_GLOB = r"C:\War3Run\War3Launcher\records\block\cm\*.csv"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\existing_waves_summary.txt"

LANES = [
    (-6368.0, -4480.0, -6112.0,  1568.0, "近卫上路", -6176.0, -4184.0),
    (-4640.0, -5152.0, -1504.0, -1824.0, "近卫中路", -4792.0, -5496.0),
    (-4032.0, -6784.0,  4960.0, -6752.0, "近卫下路", -3816.0, -6752.0),
    ( 3392.0,  5792.0, -4704.0,  5920.0, "天灾上路",  2712.0,  5512.0),
    ( 4128.0,  3744.0,  1056.0,   -96.0, "天灾中路",  3992.0,  3816.0),
    ( 6368.0,  2912.0,  6240.0, -2080.0, "天灾下路",  6232.0,  3432.0),
]


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
    raw = open(AI_LOG, "rb").read()
    ltxt = raw.decode("utf-16", errors="ignore") if b"\x00" in raw[:200] else raw.decode("utf-8", errors="replace")

    # 按 session 切分 AiUnit.log 中的 真人坐标
    sessions = []
    cur_sess = {}
    last_w = -1
    pat = re.compile(r"\[(\d+:\d+:\d+\.\d+)\].*真人坐标 第 (\d+) 波 t=([0-9.]+) 英雄 (-?[0-9.]+),(-?[0-9.]+) \| 兵 (.*)")
    for ln in ltxt.splitlines():
        m = pat.search(ln)
        if not m:
            continue
        ts, w_str, t_str, hx_s, hy_s, c_str = m.groups()
        w = int(w_str)
        t = float(t_str)
        hx, hy = float(hx_s), float(hy_s)
        if w < last_w or (w == last_w and cur_sess.get(w) and t < cur_sess[w][-1][0] - 1.0):
            if cur_sess:
                sessions.append(cur_sess)
            cur_sess = {}
        last_w = w
        creeps = []
        for tok in c_str.split():
            if ":" in tok and not tok.endswith(":dead"):
                _, xy = tok.split(":", 1)
                if "," in xy:
                    cx, cy = xy.split(",", 1)
                    creeps.append((float(cx), float(cy)))
        if creeps:
            cur_sess.setdefault(w, []).append((t, hx, hy, creeps, ts))
    if cur_sess:
        sessions.append(cur_sess)

    lines = [f"AiUnit.log 中共解析到 {len(sessions)} 个录制会话："]
    for sidx, sess in enumerate(sessions, 1):
        first_w = min(sess.keys())
        c0x, c0y = sess[first_w][0][3][0]
        lidx = classify_lane(c0x, c0y)
        ts0 = sess[first_w][0][4]
        lines.append(f"\n=== Session #{sidx} (Start={ts0}, Lane={LANES[lidx][4]}, Waves={sorted(sess.keys())}) ===")
        for w, samples in sorted(sess.items()):
            # 全部帧 vs 未受阻帧 (min_hd > 280)
            free = []
            all_pts = []
            for t, hx, hy, cs, _ in samples:
                min_hd = min(math.hypot(cx - hx, cy - hy) for cx, cy in cs)
                projs = [proj_lane(lidx, cx, cy)[0] for cx, cy in cs]
                all_pts.append((t, max(projs), sum(projs) / len(projs), min_hd))
                if min_hd > 280.0:
                    free.append((t, max(projs), sum(projs) / len(projs), min_hd))
            t_all = all_pts[-1][0] - all_pts[0][0]
            v_all = (all_pts[-1][1] - all_pts[0][1]) / t_all if t_all > 0.5 else 0
            if len(free) >= 4 and (free[-1][0] - free[0][0]) >= 0.8:
                dt = free[-1][0] - free[0][0]
                vf = (free[-1][1] - free[0][1]) / dt
                vm = (free[-1][2] - free[0][2]) / dt
                lines.append(f"  Wave {w:2d}: 样本={len(samples):3d} (未受阻={len(free):3d}, t={free[0][0]:.1f}..{free[-1][0]:.1f}s, s={free[0][1]:.0f}..{free[-1][1]:.0f}) | 未受阻前兵={vf:.1f}/s 中心={vm:.1f}/s | 全程前兵={v_all:.1f}/s")
            else:
                lines.append(f"  Wave {w:2d}: 样本={len(samples):3d} (全程受阻, s={all_pts[0][1]:.0f}..{all_pts[-1][1]:.0f}) | 受阻前兵均速={v_all:.1f}/s")

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
