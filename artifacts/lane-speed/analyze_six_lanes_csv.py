# -*- coding: utf-8 -*-
"""
分析 sample_six_lanes_live.py 采集到的六路实时数据 (live_six_lanes_trace.csv)：
1. 自动识别每一波 (wave_id) 在六路（近卫上/中/下、天灾上/中/下）的出生时刻 t0、光环状态 (A2V1/A2V0/none) 及光环精确消失时刻（15.0s）。
2. 对每一路、分「前 7 分钟（有光环期）」与「7 分钟后（无光环期）」两个时段，按五段车道区间：
   - 段 1：出兵口 -> 中继重下令区 / 启动段 (0 ~ 800)
   - 段 2：第一拐点 / 前段巡航 (800 ~ 2200)
   - 段 3：二塔前后 (2200 ~ 4000)
   - 段 4：二塔 -> 一塔前（含 15s 光环消失点 ~3600 或 ~6000）
   - 段 5：一塔 -> 河道/拐点交汇区
   统计：实测最前兵均速、整波中心均速、引擎瞬时 max_spd / v_mag、实测波数与样本帧数。
3. 统计每一波在六路上的实际两军交汇点 (x, y) 与距近卫/天灾一塔的距离！
"""
import csv
import math
import os
from collections import defaultdict

IN_CSV = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\live_six_lanes_trace.csv"
OUT_REPORT = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\live_six_lanes_report.txt"

# kAiLanes[6]: (raxX, raxY, towerX, towerY, name, spawnX, spawnY)
LANES = [
    (-6368.0, -4480.0, -6112.0,  1568.0, "近卫上路", -6176.0, -4184.0),
    (-4640.0, -5152.0, -1504.0, -1824.0, "近卫中路", -4792.0, -5496.0),
    (-4032.0, -6784.0,  4960.0, -6752.0, "近卫下路", -3816.0, -6752.0),
    ( 3392.0,  5792.0, -4704.0,  5920.0, "天灾上路",  2712.0,  5512.0),
    ( 4128.0,  3744.0,  1056.0,   -96.0, "天灾中路",  3992.0,  3816.0),
    ( 6368.0,  2912.0,  6240.0, -2080.0, "天灾下路",  6232.0,  3432.0),
]


def proj_lane(lane_idx, x, y):
    rx, ry, tx, ty, _, _, _ = LANES[lane_idx]
    vx, vy = tx - rx, ty - ry
    length = math.hypot(vx, vy)
    ux, uy = vx / length, vy / length
    s = (x - rx) * ux + (y - ry) * uy
    lat = (x - rx) * (-uy) + (y - ry) * ux
    return s, lat


def assign_lane_idx(team, lane_lvl, x, y):
    if lane_lvl in (2, 3, 4):
        base = 0 if team == "rad" else 3
        return base + (lane_lvl - 2)
    # 备用几何归类
    cands = [0, 1, 2] if team == "rad" else [3, 4, 5]
    best_l, best_d = cands[0], 1e18
    for idx in cands:
        rx, ry, tx, ty, _, _, _ = LANES[idx]
        vx, vy = tx - rx, ty - ry
        l2 = vx * vx + vy * vy
        t = max(0.0, min(1.5, ((x - rx) * vx + (y - ry) * vy) / l2))
        d = math.hypot(x - (rx + vx * t), y - (ry + vy * t))
        if d < best_d:
            best_d = d
            best_l = idx
    return best_l


def main():
    if not os.path.exists(IN_CSV):
        print(f"[ERR] {IN_CSV} 不存在")
        return

    # 读取全部行，先确定每个 unit_ptr 的稳定 lane_idx 与 wave_id
    raw_rows = []
    unit_lane_votes = defaultdict(list)
    with open(IN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            t = float(r["t_sec"])
            wid = int(r["wave_id"])
            u = r["unit_ptr"]
            cc = r["fourcc"]
            team = r["team"]
            role = r["role"]
            ll = int(r["lane_lvl"])
            aura = r["aura"]
            x, y = float(r["x"]), float(r["y"])
            vmag = float(r["v_mag"])
            mspd = float(r["max_spd"])
            fdeg = float(r["facing_deg"])
            if ll in (2, 3, 4):
                unit_lane_votes[u].append((0 if team == "rad" else 3) + (ll - 2))
            raw_rows.append((t, wid, u, cc, team, role, ll, aura, x, y, vmag, mspd, fdeg))

    unit_lane = {}
    for u, votes in unit_lane_votes.items():
        if votes:
            unit_lane[u] = max(set(votes), key=votes.count)

    # 按 (wave_id, lane_idx, t) 聚合整波帧
    wave_lane_frames = defaultdict(lambda: defaultdict(list))
    wave_auras = defaultdict(lambda: defaultdict(set))
    for t, wid, u, cc, team, role, ll, aura, x, y, vmag, mspd, fdeg in raw_rows:
        lidx = unit_lane.get(u)
        if lidx is None:
            lidx = assign_lane_idx(team, ll, x, y)
            unit_lane[u] = lidx
        s, lat = proj_lane(lidx, x, y)
        wave_lane_frames[(wid, lidx)][t].append((u, cc, role, aura, x, y, s, lat, vmag, mspd, fdeg))
        if aura != "none":
            wave_auras[wid][lidx].add(aura)

    lines = []
    def log(s=""):
        lines.append(s)

    all_waves = sorted(set(w for w, _ in wave_lane_frames.keys()))
    log(f"=== 六路实测总览：共采集 {len(raw_rows)} 行，波次 {all_waves} ===")

    # 判断每一波属于 <7:00 (boosted_period) 还是 >=7:00 (normal_period)
    wave_is_early = {}
    for w in all_waves:
        auras_in_w = set()
        for lidx in range(6):
            auras_in_w |= wave_auras[w][lidx]
        wave_is_early[w] = bool(auras_in_w)
        t_min = min(min(wave_lane_frames[(w, l)].keys()) for l in range(6) if (w, l) in wave_lane_frames)
        log(f"  Wave {w:2d} (t0={t_min:5.1f}s): early_period={wave_is_early[w]} | auras={dict((LANES[l][4], sorted(wave_auras[w][l])) for l in range(6) if wave_auras[w][l])}")

    # 定义各路的分段区间 (按车道投影 s):
    # (段名, s_min, s_max)
    LANE_SEGMENTS = {
        0: [("1.出兵->中继区(300~900)", 300, 900), ("2.前段东凸弯(900~2200)", 900, 2200), ("3.二塔段(2200~3600)", 2200, 3600), ("4.二塔->一塔(3600~5800)", 3600, 5800), ("5.一塔->上路拐点(5800~9500)", 5800, 9500)],
        1: [("1.出兵->高地坡(-300~700)", -300, 700), ("2.二塔前直道(700~2000)", 700, 2000), ("3.二塔->高地口(2000~3300)", 2000, 3300), ("4.一塔前直道(3300~4500)", 3300, 4500), ("5.一塔->河道交汇(4500~6200)", 4500, 6200)],
        2: [("1.出兵->中继区(200~1000)", 200, 1000), ("2.基地外墙段(1000~3000)", 1000, 3000), ("3.二塔段(3000~4500)", 3000, 4500), ("4.中后段+第一弯(4500~6200)", 4500, 6200), ("5.二弯->一塔(6200~8800)", 6200, 8800), ("6.一塔->下路拐点(8800~10500)", 8800, 10500)],
        3: [("1.出兵->中继区(500~1200)", 500, 1200), ("2.二塔前直道(1200~3000)", 1200, 3000), ("3.二塔段(3000~4500)", 3000, 4500), ("4.中后段(4500~6200)", 4500, 6200), ("5.一塔前弯道(6200~8000)", 6200, 8000), ("6.一塔->上路拐点(8000~9500)", 8000, 9500)],
        4: [("1.出兵->中继区(0~700)", 0, 700), ("2.二塔前直道(700~2000)", 700, 2000), ("3.二塔->中段(2000~3400)", 2000, 3400), ("4.一塔前直道(3400~4800)", 3400, 4800), ("5.一塔->河道交汇(4800~6400)", 4800, 6400)],
        5: [("1.出兵->中继区(-500~800)", -500, 800), ("2.二塔前直道(800~2200)", 800, 2200), ("3.二塔->3600(2200~3600)", 2200, 3600), ("4.3600->一塔(3600~4950)", 3600, 4950), ("5.一塔->交汇区(4950~8500)", 4950, 8500)],
    }

    log("\n=== 六路 × 时段 (<7:00 vs >=7:00) × 车道分段 实测速度详表 ===")
    for lidx in range(6):
        log(f"\n--- [{lidx}] {LANES[lidx][4]} ---")
        for is_early, p_label in [(True, "前 7 分钟 (<7:00, 含边路光环)"), (False, "7 分钟后 (>=7:00, 无光环)")]:
            target_waves = [w for w in all_waves if wave_is_early.get(w) == is_early and w >= 1]
            log(f"  [{p_label}] 覆盖波次: {target_waves}")
            for seg_name, s_lo, s_hi in LANE_SEGMENTS[lidx]:
                vf_list, vm_list, vmag_list, mspd_list, lat_list = [], [], [], [], []
                for w in target_waves:
                    frames = sorted(wave_lane_frames[(w, lidx)].items())
                    if len(frames) < 4:
                        continue
                    t0_wave = frames[0][0]
                    # 提取整波前沿 front_s 在 [s_lo, s_hi] 内且未交战 (t - t0_wave < 27s) 的帧
                    seg_pts = []
                    for t, cs in frames:
                        if t - t0_wave > 28.0:
                            continue
                        # 仅看普通近战/远程兵 (排除落后的攻城车干扰中心)
                        normal_cs = [c for c in cs if c[2] != "siege"] or cs
                        front_s = max(c[6] for c in normal_cs)
                        mean_s = sum(c[6] for c in normal_cs) / len(normal_cs)
                        mean_lat = sum(c[7] for c in normal_cs) / len(normal_cs)
                        avg_vmag = sum(c[8] for c in normal_cs) / len(normal_cs)
                        avg_mspd = sum(c[9] for c in normal_cs) / len(normal_cs)
                        if s_lo <= front_s <= s_hi:
                            seg_pts.append((t, front_s, mean_s, mean_lat, avg_vmag, avg_mspd))
                    if len(seg_pts) >= 3 and (seg_pts[-1][0] - seg_pts[0][0]) >= 0.4:
                        dt = seg_pts[-1][0] - seg_pts[0][0]
                        vf = (seg_pts[-1][1] - seg_pts[0][1]) / dt
                        vm = (seg_pts[-1][2] - seg_pts[0][2]) / dt
                        if 50.0 <= vf <= 480.0:
                            vf_list.append(vf)
                            vm_list.append(vm)
                            vmag_list.append(sum(p[4] for p in seg_pts) / len(seg_pts))
                            mspd_list.append(sum(p[5] for p in seg_pts) / len(seg_pts))
                            lat_list.append(sum(p[3] for p in seg_pts) / len(seg_pts))
                if vf_list:
                    log(f"    {seg_name:28s} | 波数={len(vf_list):2d} | 前兵沿路={sum(vf_list)/len(vf_list):5.1f}/s | 波中心沿路={sum(vm_list)/len(vm_list):5.1f}/s | 瞬时|v|={sum(vmag_list)/len(vmag_list):5.1f} (上限={sum(mspd_list)/len(mspd_list):5.1f}) | 平均横向={sum(lat_list)/len(lat_list):+6.1f}")
                else:
                    log(f"    {seg_name:28s} | 无有效未交战样本")

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {len(lines)} lines to {OUT_REPORT}")


if __name__ == "__main__":
    main()
