# -*- coding: utf-8 -*-
"""
深入分析所有现有实测数据（AiUnit.log + records/block/cm/*.csv + artifacts/creep-block/human_block_*.log）：
1. 提取近卫上路 (cm_top_*.csv)、近卫中路 (cm_mid_*.csv + AiUnit.log + human_block)、近卫下路 (cm_bot_*.csv + AiUnit.log)
   在 < 7:00 与 >= 7:00 两个时段、各车道段（出兵口 -> 第一拐点 -> 二塔 -> 一塔 -> 河道交汇）的实测未受阻速度 & 受阻速度。
2. 模拟 + 实测计算六路在「不卡兵」与「卡兵拖延 Δt 秒」下的两军兵线自然交汇点 (x, y) 与距己方一塔距离！
"""
import glob
import math
import os
import re

AI_LOG = r"C:\War3Run\War3Launcher\logs\AiUnit.log"
CSV_GLOB = r"C:\War3Run\War3Launcher\records\block\cm\*.csv"
HUMAN_LOG = r"D:\Qt\workspace\War3Analysis\artifacts\creep-block\human_block_20261118_0711.log"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\deep_wave_profiles.txt"

# kAiLanes[6]: (raxX, raxY, towerX, towerY, name, spawnX, spawnY)
LANES = [
    (-6368.0, -4480.0, -6112.0,  1568.0, "近卫上路", -6176.0, -4184.0),
    (-4640.0, -5152.0, -1504.0, -1824.0, "近卫中路", -4792.0, -5496.0),
    (-4032.0, -6784.0,  4960.0, -6752.0, "近卫下路", -3816.0, -6752.0),
    ( 3392.0,  5792.0, -4704.0,  5920.0, "天灾上路",  2712.0,  5512.0),
    ( 4128.0,  3744.0,  1056.0,   -96.0, "天灾中路",  3992.0,  3816.0),
    ( 6368.0,  2912.0,  6240.0, -2080.0, "天灾下路",  6232.0,  3432.0),
]

# 各路二塔与一塔坐标 (来自 buildings.json)
LANE_TOWERS = {
    0: {"t2": (-6336.0, -1024.0), "t1": (-6112.0,  1568.0), "corner": (-6005.1,  5458.6)},
    1: {"t2": (-3648.0, -2816.0), "t1": (-1504.0, -1824.0), "corner": ( -561.7,  -651.7)},
    2: {"t2": ( -544.0, -6688.0), "t1": ( 4960.0, -6752.0), "corner": ( 5901.5, -6198.9)},
    3: {"t2": (    0.0,  5952.0), "t1": (-4704.0,  5920.0), "corner": (-6005.1,  5458.6)},
    4: {"t2": ( 2496.0,  2048.0), "t1": ( 1056.0,   -96.0), "corner": ( -561.7,  -651.7)},
    5: {"t2": ( 6208.0,   384.0), "t1": ( 6240.0, -2080.0), "corner": ( 5901.5, -6198.9)},
}


def proj_lane(lane_idx, x, y):
    rx, ry, tx, ty, _, _, _ = LANES[lane_idx]
    vx, vy = tx - rx, ty - ry
    length = math.hypot(vx, vy)
    ux, uy = vx / length, vy / length
    s = (x - rx) * ux + (y - ry) * uy
    lat = (x - rx) * (-uy) + (y - ry) * ux
    return s, lat


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


def main():
    lines = []
    def log(s=""):
        lines.append(s)

    # 1. 计算六路各关键地标（出兵点、中继区、二塔、一塔、路点/河道拐点）的车道投影坐标 s 与横向偏离 lat
    log("=== 1. 六路关键节点车道投影坐标 (以 kAiLanes[i].rax -> tower 为轴) ===")
    for idx, (rx, ry, tx, ty, name, sx, sy) in enumerate(LANES):
        t2x, t2y = LANE_TOWERS[idx]["t2"]
        t1x, t1y = LANE_TOWERS[idx]["t1"]
        cx, cy = LANE_TOWERS[idx]["corner"]
        s_spawn, l_spawn = proj_lane(idx, sx, sy)
        s_t2, l_t2 = proj_lane(idx, t2x, t2y)
        s_t1, l_t1 = proj_lane(idx, t1x, t1y)
        s_cor, l_cor = proj_lane(idx, cx, cy)
        # 拐点到一塔的实际欧氏距离
        d_t1_cor = math.hypot(cx - t1x, cy - t1y)
        log(f"  [{idx}] {name}:")
        log(f"      出兵中点 ({sx:.0f},{sy:.0f}) -> s={s_spawn:.0f}, lat={l_spawn:+.0f}")
        log(f"      二塔     ({t2x:.0f},{t2y:.0f}) -> s={s_t2:.0f}, lat={l_t2:+.0f}")
        log(f"      一塔     ({t1x:.0f},{t1y:.0f}) -> s={s_t1:.0f}, lat={l_t1:+.0f}")
        log(f"      首路点   ({cx:.0f},{cy:.0f}) -> s={s_cor:.0f}, lat={l_cor:+.0f} (距一塔欧氏距离={d_t1_cor:.0f})")

    # 2. 收集所有 CSV trace 波次，按 (路, 波次, 文件) 输出分段速度（包括未受阻段与受阻段）
    log("\n=== 2. CSV 实测波次分段速度 (出兵->第一拐点/二塔->一塔) ===")
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
            cs = []
            for k in range(5, len(parts) - 1, 2):
                if parts[k] and parts[k + 1]:
                    cs.append((float(parts[k]), float(parts[k + 1])))
            if cs:
                waves.setdefault(w, []).append((t, hx, hy, cs))
        if not waves:
            continue
        log(f"\n  [{fn}]")
        for w, samples in sorted(waves.items()):
            c0x, c0y = samples[0][3][0]
            lidx = classify_lane(c0x, c0y)
            # 按车道距离区间统计前兵速度与是否受阻
            pts = []
            for t, hx, hy, cs in samples:
                min_hd = min(math.hypot(cx - hx, cy - hy) for cx, cy in cs)
                ps = [proj_lane(lidx, cx, cy) for cx, cy in cs]
                front_s = max(p[0] for p in ps)
                mean_s = sum(p[0] for p in ps) / len(ps)
                mean_l = sum(p[1] for p in ps) / len(ps)
                pts.append((t, front_s, mean_s, mean_l, min_hd))
            # 按时间段 0..2s, 2..8s, 8..15s, 15s..end 输出
            segs = []
            for t_lo, t_hi in [(0.0, 2.0), (2.0, 8.0), (8.0, 15.0), (15.0, 45.0)]:
                sub = [p for p in pts if t_lo <= p[0] <= t_hi]
                if len(sub) >= 3 and (sub[-1][0] - sub[0][0]) >= 0.5:
                    dt = sub[-1][0] - sub[0][0]
                    vf = (sub[-1][1] - sub[0][1]) / dt
                    vm = (sub[-1][2] - sub[0][2]) / dt
                    free_ratio = sum(1 for p in sub if p[4] > 280.0) / len(sub)
                    segs.append(f"t={sub[0][0]:.1f}..{sub[-1][0]:.1f}s(s={sub[0][1]:.0f}..{sub[-1][1]:.0f}):vf={vf:.0f}/vm={vm:.0f}(free={free_ratio*100:.0f}%)")
            log(f"    W{w:02d} ({LANES[lidx][4]}): " + " | ".join(segs))

    # 3. 精确计算三路在 <7:00 与 >=7:00 的自然交汇点与卡兵拖延收益
    log("\n=== 3. 三路兵线自然交汇点与卡兵收益精确推算 ===")
    # 沿实际折线路径计算：兵从 spawnX,spawnY -> T2 -> T1 -> Corner -> 对方 T1
    for pair_name, rad_idx, dire_idx in [
        ("上路 (近卫劣势路 vs 天灾优势路)", 0, 3),
        ("中路 (近卫中路 vs 天灾中路)", 1, 4),
        ("下路 (近卫优势路 vs 天灾劣势路)", 2, 5),
    ]:
        rx0, ry0 = LANES[rad_idx][5], LANES[rad_idx][6]
        rt1x, rt1y = LANE_TOWERS[rad_idx]["t1"]
        cx, cy = LANE_TOWERS[rad_idx]["corner"]
        dt1x, dt1y = LANE_TOWERS[dire_idx]["t1"]
        dx0, dy0 = LANES[dire_idx][5], LANES[dire_idx][6]

        # 路径分段长度
        d_rad_to_t1 = math.hypot(rt1x - rx0, rt1y - ry0)
        d_rad_t1_to_cor = math.hypot(cx - rt1x, cy - rt1y)
        d_dire_to_t1 = math.hypot(dt1x - dx0, dt1y - dy0)
        d_dire_t1_to_cor = math.hypot(cx - dt1x, cy - dt1y)
        total_track = d_rad_to_t1 + d_rad_t1_to_cor + d_dire_t1_to_cor + d_dire_to_t1

        log(f"\n  [{pair_name}]")
        log(f"    几何路径: 近卫出兵->近卫T1={d_rad_to_t1:.0f}, 近卫T1->拐点={d_rad_t1_to_cor:.0f}, 拐点->天灾T1={d_dire_t1_to_cor:.0f}, 天灾T1->天灾出兵={d_dire_to_t1:.0f} (总长={total_track:.0f})")

        # 模拟函数: 给定时间 t, 初始起飞停顿 t_turn, 前 15s 有效沿路速度 v15, 15s 后有效沿路速度 v_norm, 卡兵额外拖延 delay_s
        def dist_at(t, t_turn, v15, v_norm, delay_s):
            te = max(0.0, t - t_turn - delay_s)
            t1 = min(te, max(0.0, 15.0 - t_turn))
            t2 = max(0.0, te - max(0.0, 15.0 - t_turn))
            return t1 * v15 + t2 * v_norm

        # 实测有效巡航速度（扣除出兵转身与弯道投影 ~95.5% 效率: 325->310, 406.25->392, 243.75->233）
        for period, (r_v15, r_vn, d_v15, d_vn) in [
            ("前 7 分钟 (<7:00)", (
                233.0 if rad_idx == 0 else (392.0 if rad_idx == 2 else 310.0),
                310.0,
                392.0 if dire_idx == 3 else (233.0 if dire_idx == 5 else 310.0),
                310.0,
            )),
            ("7 分钟后 (>=7:00)", (310.0, 310.0, 310.0, 310.0)),
        ]:
            r_turn = 0.8 if rad_idx == 0 else (0.6 if rad_idx == 1 else 0.5)
            d_turn = 0.4 if dire_idx == 3 else (0.15 if dire_idx == 4 else 0.05)
            log(f"    --- {period} (近卫前15s={r_v15:.0f}/后={r_vn:.0f}, 天灾前15s={d_v15:.0f}/后={d_vn:.0f}) ---")
            for r_delay, d_delay, desc in [
                (0.0, 0.0, "双方都不卡（自然基线）"),
                (3.0, 0.0, "近卫卡兵拖延 3.0s"),
                (5.0, 0.0, "近卫卡兵拖延 5.0s"),
                (8.0, 0.0, "近卫卡兵拖延 8.0s"),
                (0.0, 3.0, "天灾卡兵拖延 3.0s"),
                (0.0, 5.0, "天灾卡兵拖延 5.0s"),
                (0.0, 8.0, "天灾卡兵拖延 8.0s"),
            ]:
                # 二分找交汇时间 t_meet
                lo, hi = 0.0, 60.0
                for _ in range(40):
                    mid = 0.5 * (lo + hi)
                    if dist_at(mid, r_turn, r_v15, r_vn, r_delay) + dist_at(mid, d_turn, d_v15, d_vn, d_delay) >= total_track:
                        hi = mid
                    else:
                        lo = mid
                tm = 0.5 * (lo + hi)
                dr = dist_at(tm, r_turn, r_v15, r_vn, r_delay)
                dd = total_track - dr
                # 相对近卫一塔与天灾一塔的距离（正值表示在塔外/河道侧，负值表示已进塔后！）
                rel_rad_t1 = dr - d_rad_to_t1
                rel_dire_t1 = dd - d_dire_to_t1
                note = ""
                if rel_rad_t1 < 650:
                    note = "⚠️ 进近卫一塔射程(<650)！"
                elif rel_dire_t1 < 650:
                    note = "⚠️ 进天灾一塔射程(<650)！"
                log(f"      {desc:22s}: t={tm:4.1f}s | 距近卫出兵={dr:5.0f} (近卫T1外 {rel_rad_t1:+5.0f}) | 距天灾T1外 {rel_dire_t1:+5.0f} {note}")

    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_TXT}")


if __name__ == "__main__":
    main()
