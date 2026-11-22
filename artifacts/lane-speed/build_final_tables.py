# -*- coding: utf-8 -*-
r"""
汇总并计算六路兵线在「前 7 分钟（TimerGetElapsed(M) < 420s）」与「7 分钟后（>= 420s）」的完整分段实测速度表：
- 注意：CPoPos+0x78/+0x7C 是寻路网格锚点（每 ~0.35~0.5s 跳变一次），单步 0.1s 差分若按 522 过滤会剪掉跳变帧；
- 正确计算分段平均速度的方法是：
  1) 区间首尾穿行速度：(s_last - s_first) / (t_last - t_first) 与 2D 路径长 / (t_last - t_first)
  2) 引擎物理步进瞬时速度 v_mag = hypot(vx, vy)（CPoPosCl+0x80/+0x84 * 32.0）
  3) 每波排头兵 (front creep) 与整波中心 (wave center) 在各分段的穿行速度
输出到 D:\Qt\workspace\War3Analysis\artifacts\lane-speed\final_six_lanes_tables.txt
"""
import os
import csv
import math
from collections import defaultdict

OUT_PATH = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\final_six_lanes_tables.txt"
TRACE1_CSV = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\live_six_lanes_trace.csv"
TRACE2_CSV = r"D:\Qt\workspace\War3Analysis\artifacts\lane-speed\live_six_lanes_10hz.csv"

LANES_DEF = {
    "Radiant_Top": (-6600.0, -4000.0, -6300.0, 2200.0),
    "Radiant_Mid": (-5000.0, -4500.0, -1000.0, -1100.0),
    "Radiant_Bot": (-3800.0, -6100.0, 4900.0, -6100.0),
    "Dire_Top":    (4100.0, 5700.0, -4700.0, 5800.0),
    "Dire_Mid":    (4100.0, 3600.0, 200.0, 250.0),
    "Dire_Bot":    (6300.0, 3000.0, 6250.0, -1950.0),
}

def classify_and_project(team, x, y):
    if team == "rad":
        if y - x > 1400.0:
            lane = "Radiant_Top"
        elif x - y > 1200.0:
            lane = "Radiant_Bot"
        else:
            lane = "Radiant_Mid"
    else:
        if y - x > 1000.0 or y > 4300.0:
            lane = "Dire_Top"
        elif x - y > 1200.0 or x > 4800.0:
            lane = "Dire_Bot"
        else:
            lane = "Dire_Mid"
    bx, by, tx, ty = LANES_DEF[lane]
    dx, dy = tx - bx, ty - by
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    rx, ry = x - bx, y - by
    s = rx * ux + ry * uy
    d = rx * (-uy) + ry * ux
    return lane, s, d

LANE_SEGS = {
    "Radiant_Top": [
        ("出兵口→第一拐点", 200, 1500),
        ("第一拐点→二塔前", 1500, 3100),
        ("二塔→15s光环终点", 3100, 3900),
        ("光环终点→一塔", 3900, 6100),
        ("一塔→左上拐角/交汇", 6100, 9200),
    ],
    "Radiant_Mid": [
        ("出兵口→高地坡下", 200, 1400),
        ("高地坡下→二塔", 1400, 2600),
        ("二塔→一塔", 2600, 4650),
        ("一塔→河道交汇", 4650, 5800),
    ],
    "Radiant_Bot": [
        ("出兵口→第一拐点", 200, 1450),
        ("第一拐点→二塔", 1450, 4150),
        ("二塔→15s光环终点", 4150, 6150),
        ("S弯道→一塔", 6150, 8850),
        ("一塔→右下交汇区", 8850, 10800),
    ],
    "Dire_Top": [
        ("出兵口→第一拐点", 100, 2200),
        ("第一拐点→二塔", 2200, 3900),
        ("二塔→15s光环终点", 3900, 6000),
        ("光环终点→一塔", 6000, 7450),
        ("一塔→左上交汇区", 7450, 10200),
    ],
    "Dire_Mid": [
        ("出兵口→第一拐点", 100, 1500),
        ("第一拐点→二塔", 1500, 2600),
        ("二塔→一塔", 2600, 4550),
        ("一塔→河道交汇", 4550, 5800),
    ],
    "Dire_Bot": [
        ("出兵口→第一拐点", -550, 1350),
        ("第一拐点→二塔", 1350, 2850),
        ("二塔→15s光环终点", 2850, 3600),
        ("光环终点→一塔", 3600, 5050),
        ("一塔→右下交汇区", 5050, 7800),
    ],
}

def load_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def analyze_csv(rows, label):
    out = []
    out.append("==================================================================")
    out.append(f"数据集: {label} (总行数={len(rows)})")
    out.append("==================================================================")
    if not rows:
        out.append("  [空数据集]")
        return "\n".join(out)

    unit_trajs = defaultdict(list)
    inst_samples = defaultdict(list) # (lane, seg_name) -> [(v_mag, d, mul, mspd)]

    for r in rows:
        team = r["team"]
        x = float(r["x"])
        y = float(r["y"])
        t = float(r["t_sec"])
        v_mag = float(r["v_mag"])
        mul = float(r["amov_mul"])
        mspd = float(r["max_spd"])
        uid = r["obj1"]
        lane, s, d = classify_and_project(team, x, y)
        unit_trajs[(lane, uid)].append((t, x, y, s, d, v_mag, mul, mspd))
        if v_mag > 50.0:
            for seg_name, s_lo, s_hi in LANE_SEGS[lane]:
                if s_lo <= s < s_hi:
                    inst_samples[(lane, seg_name)].append((v_mag, d, mul, mspd))
                    break

    # 计算每个单兵穿过每个分段的首尾平均速度 (s_end - s_start) / (t_end - t_start)
    # 要求 dt >= 1.2s 且移动中 (排除交战卡死在原地的兵)
    transit_samples = defaultdict(list) # (lane, seg_name) -> [(v_ds, v_2d, d_mean, mul_mean, mspd_mean)]
    for (lane, uid), pts in unit_trajs.items():
        pts.sort(key=lambda item: item[0])
        for seg_name, s_lo, s_hi in LANE_SEGS[lane]:
            in_seg = [p for p in pts if s_lo <= p[3] <= s_hi and p[5] > 50.0]
            if len(in_seg) < 2:
                continue
            t_first, x_first, y_first, s_first = in_seg[0][0], in_seg[0][1], in_seg[0][2], in_seg[0][3]
            t_last, x_last, y_last, s_last = in_seg[-1][0], in_seg[-1][1], in_seg[-1][2], in_seg[-1][3]
            dt = t_last - t_first
            ds = s_last - s_first
            dist2d = math.hypot(x_last - x_first, y_last - y_first)
            if dt < 1.0 or ds < 180.0:
                continue
            v_ds = ds / dt
            v_2d = dist2d / dt
            if v_2d < 150.0 or v_2d > 450.0:
                continue
            d_mean = sum(p[4] for p in in_seg) / len(in_seg)
            mul_mean = sum(p[6] for p in in_seg) / len(in_seg)
            mspd_mean = sum(p[7] for p in in_seg) / len(in_seg)
            transit_samples[(lane, seg_name)].append((v_ds, v_2d, d_mean, mul_mean, mspd_mean))

    for lane in ["Radiant_Top", "Radiant_Mid", "Radiant_Bot", "Dire_Top", "Dire_Mid", "Dire_Bot"]:
        out.append(f"\n--- {lane} ---")
        for seg_name, s_lo, s_hi in LANE_SEGS[lane]:
            arr = transit_samples.get((lane, seg_name), [])
            inst = inst_samples.get((lane, seg_name), [])
            inst_vm = sum(x[0] for x in inst) / len(inst) if inst else 0.0
            inst_ms = sum(x[3] for x in inst) / len(inst) if inst else 0.0
            inst_mul = sum(x[2] for x in inst) / len(inst) if inst else 0.0
            inst_d = sum(x[1] for x in inst) / len(inst) if inst else 0.0
            if arr:
                v_dss = [x[0] for x in arr]
                v_2ds = [x[1] for x in arr]
                v_ds_avg = sum(v_dss) / len(v_dss)
                v_2d_avg = sum(v_2ds) / len(v_2ds)
                v_2d_max = max(v_2ds)
                out.append(
                    f"  {seg_name:<18} (s={s_lo:>5}..{s_hi:<5}): "
                    f"mul={inst_mul:.3f}, 面板={inst_ms:>6.2f}, 引擎v_mag={inst_vm:>5.1f}/s | "
                    f"区间穿行(n={len(arr):>2}): 2D均值={v_2d_avg:>5.1f}/s (排头={v_2d_max:>5.1f}/s), "
                    f"轴向ds/dt={v_ds_avg:>5.1f}/s, 横偏d={inst_d:>+6.1f}"
                )
            elif inst:
                out.append(
                    f"  {seg_name:<18} (s={s_lo:>5}..{s_hi:<5}): "
                    f"mul={inst_mul:.3f}, 面板={inst_ms:>6.2f}, 引擎v_mag={inst_vm:>5.1f}/s | "
                    f"inst_n={len(inst):>3}, 横偏d={inst_d:>+6.1f}"
                )
            else:
                out.append(f"  {seg_name:<18} (s={s_lo:>5}..{s_hi:<5}): 无样本")
    return "\n".join(out)

def main():
    r1 = load_rows(TRACE1_CSV)
    r2 = load_rows(TRACE2_CSV)
    rep = []
    rep.append(analyze_csv(r1, "trace1: live_six_lanes_trace.csv (前7分钟 Waves 1..4)"))
    rep.append("\n\n")
    rep.append(analyze_csv(r2, "trace2: live_six_lanes_10hz.csv (7分钟后 10Hz Waves)"))
    text = "\n".join(rep)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Saved report to {OUT_PATH} ({len(text)} chars)")

if __name__ == "__main__":
    main()
