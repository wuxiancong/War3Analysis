# -*- coding: utf-8 -*-
r"""
离线轨迹回放与参数敏感度模拟器 (simulate_param_tuning.py)
按照任务要求：「用记录里兵的轨迹，假设英雄按新规则走，估计前距与横向覆盖误差」：
1. 方法 A（固定小兵轨迹 Pre-Leak 回放）：
   直接用记录里小兵的真实轨迹 creeps_real(t)，让英雄从 t=0 按【现行参数】vs【新参数】走，
   对比在原漏兵时刻 t_leak（或全程）英雄的前距 gap(t) = hs(t) - front_s(t) 以及对漏兵的横向覆盖误差 |hl(t) - cl_leak(t)|；
2. 方法 B（空间走廊闭环阻挡回放 Spatial-Corridor Replay）：
   每只小兵沿其记录的空间轨迹曲线 cl_i(s) 前进；当英雄挡在该兵前方 (0 <= hs - cs <= 58 且 |hl - cl_i(cs)| <= 48) 时，
   该兵被英雄身体卡住 (cs <= hs - 38，即引擎 CPoSeparate 阻挡)，若 |hl - cl_i(cs)| > 48 且 cs > hs + 20 则判定为漏兵。
输出到 D:\Qt\workspace\War3Analysis\artifacts\block-records\simulation_report.txt
"""
import os
import glob
import math
from collections import defaultdict

DATA_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\data\cm"
OUT_SIM = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\simulation_report.txt"

K_AI_LANES = {
    "top": {"raxX": -6368.0, "raxY": -4480.0, "towerX": -6112.0, "towerY": 1568.0, "spawnX": -6176.0, "spawnY": -4184.0},
    "mid": {"raxX": -4640.0, "raxY": -5152.0, "towerX": -1504.0, "towerY": -1824.0, "spawnX": -4792.0, "spawnY": -5496.0},
    "bot": {"raxX": -4032.0, "raxY": -6784.0, "towerX": 4960.0, "towerY": -6752.0, "spawnX": -3816.0, "spawnY": -6752.0},
}
for k, L in K_AI_LANES.items():
    vx, vy = L["towerX"] - L["raxX"], L["towerY"] - L["raxY"]
    length = math.hypot(vx, vy)
    L["ux"], L["uy"], L["len"] = vx / length, vy / length, length

def proj_lane(lane_key, x, y):
    L = K_AI_LANES[lane_key]
    ox, oy, ux, uy = L["spawnX"], L["spawnY"], L["ux"], L["uy"]
    return (x - ox) * ux + (y - oy) * uy, (x - ox) * (-uy) + (y - oy) * ux

def interp_cl_at_s(s_curve, l_curve, s_val):
    """在记录的小兵空间轨迹 (s_curve, l_curve) 上插值位置 s_val 处的横向坐标 cl"""
    if not s_curve:
        return 0.0
    if s_val <= s_curve[0]:
        return l_curve[0]
    if s_val >= s_curve[-1]:
        return l_curve[-1]
    for k in range(len(s_curve) - 1):
        if s_curve[k] <= s_val <= s_curve[k + 1]:
            ds = s_curve[k + 1] - s_curve[k]
            if ds < 0.1:
                return l_curve[k]
            ratio = (s_val - s_curve[k]) / ds
            return l_curve[k] + ratio * (l_curve[k + 1] - l_curve[k])
    return l_curve[-1]

def simulate_wave(lane_key, frames, cfg):
    if len(frames) < 5:
        return None
    frames.sort(key=lambda x: x[0])
    t_list = [f[0] for f in frames]

    # 构建每只兵的空间走廊曲线 (s_curve, l_curve) 及逐帧真实位移
    orig_creeps = []
    creep_curves_s = defaultdict(list)
    creep_curves_l = defaultdict(list)
    real_hero = []

    for t, hx, hy, cdict in frames:
        real_hero.append(proj_lane(lane_key, hx, hy))
        cframe = {}
        for cid, (cx, cy) in cdict.items():
            cs, cl = proj_lane(lane_key, cx, cy)
            cframe[cid] = (cs, cl)
            if not creep_curves_s[cid] or cs > creep_curves_s[cid][-1] + 2.0:
                creep_curves_s[cid].append(cs)
                creep_curves_l[cid].append(cl)
        orig_creeps.append(cframe)

    if not orig_creeps[0]:
        return None

    # 统计实测漏兵数
    tower_s = K_AI_LANES[lane_key]["len"] - 300.0
    real_escaped = set()
    first_leak_idx = len(t_list) - 1
    first_leak_cid = None
    for i in range(1, len(t_list)):
        rhs, rhl = real_hero[i]
        if rhs >= tower_s - 250.0:
            break
        for cid, (cs, cl) in orig_creeps[i].items():
            if cid not in real_escaped and cs < tower_s - 250.0 and cs > rhs + 20.0:
                real_escaped.add(cid)
                if first_leak_cid is None:
                    first_leak_idx = i
                    first_leak_cid = cid

    # 初始化模拟小兵与模拟英雄
    sim_creeps = {cid: [cs0, cl0] for cid, (cs0, cl0) in orig_creeps[0].items()}
    front0_s = max(v[0] for v in orig_creeps[0].values())
    front0_l = sorted([v[1] for v in orig_creeps[0].values()])[len(orig_creeps[0]) // 2]
    real_hs0, real_hl0 = real_hero[0]

    # 若原波是门口起卡 (real_hs0 < 1500)，允许测试 wait_lead 调整；若是在二塔/6400 等兵，沿用原起始点+增量
    if real_hs0 < 1500.0 and not cfg.get("use_real_hs0", False):
        hs = front0_s + cfg["wait_lead"]
        hl = front0_l + cfg.get("init_lat_bias", 0.0)
    else:
        hs = real_hs0 + cfg.get("wait_delta", 0.0)
        hl = real_hl0 + cfg.get("init_lat_bias", 0.0)

    # 同时记录「直接按记录里小兵位置算出的纯英雄轨迹 hs_pure(t), hl_pure(t)」用于在 first_leak_idx 对比前距
    hs_pure, hl_pure = hs, hl
    waiting_pure = True
    med_prev_pure = None
    med_vel_pure = 0.0
    gap_at_real_leak = None
    laterr_at_real_leak = None

    waiting_align = True
    med_prev = None
    med_vel = 0.0
    escaped = set()
    prev_creeps = {cid: list(pos) for cid, pos in sim_creeps.items()}
    gaps_trace = []
    lat_errs_trace = []

    def step_hero_controller(cur_hs, cur_hl, cur_waiting, cur_med_prev, cur_med_vel, c_source, prev_source, dt_step):
        cand = []
        for cid, (cs, cl) in c_source.items():
            ps, pl = prev_source.get(cid, (cs, cl))
            vp = max(-100.0, min(400.0, (cs - ps) / dt_step))
            vl = max(-320.0, min(320.0, (cl - pl) / dt_step))
            if cs > cur_hs + 20.0:
                continue
            cand.append((cid, cs, cl, cs + vp * cfg["pred_t"], cl + vl * cfg["pred_t"]))
        if not cand:
            return cur_hs, cur_hl, cur_waiting, cur_med_prev, cur_med_vel, 0.0, 0.0

        cand.sort(key=lambda item: item[3], reverse=True)
        f_cid, front_s, front_l, pred_s, pred_l = cand[0]
        row_cands = [c for c in cand if c[3] >= pred_s - cfg["row_depth"]]
        lo_row = min(c[4] for c in row_cands)
        hi_row = max(c[4] for c in row_cands)
        row_n = len(row_cands)

        aim_lat = pred_l
        if row_n >= 2 and (hi_row - lo_row) <= cfg["row_width_max"]:
            aim_lat = 0.5 * (lo_row + hi_row)

        is_side = (lane_key != "mid")
        if is_side and len(cand) >= 2 and (cur_hs - pred_s) <= cfg["side_med_activate_gap"]:
            near_cands = [c for c in cand if c[3] >= pred_s - 300.0]
            ls = sorted([c[4] for c in near_cands])
            med = ls[len(ls) // 2] if (len(ls) % 2 == 1) else 0.5 * (ls[len(ls)//2 - 1] + ls[len(ls)//2])
            lo_w, hi_w = ls[0], ls[-1]

            if row_n >= 2 and (hi_row - lo_row) <= cfg["row_width_max"]:
                base_aim = 0.5 * (lo_row + hi_row)
            elif row_n == 1 and abs(pred_l - med) > 35.0 and (cur_hs - pred_s) < cfg["lock_front_gap"]:
                pull = min(cfg["single_front_pull"], abs(med - pred_l))
                base_aim = pred_l + (pull if med > pred_l else -pull)
            else:
                base_aim = med

            if cur_med_prev is None:
                cur_med_prev = med
            else:
                v_m = (med - cur_med_prev) / dt_step
                if cfg.get("clamp_med_jump", False) and abs(med - cur_med_prev) > 32.0:
                    v_m = 0.0
                cur_med_vel = 0.6 * cur_med_vel + 0.4 * max(-120.0, min(120.0, v_m))
                cur_med_prev = med

            adj = max(-60.0, min(60.0, cur_med_vel * cfg["drift_predict_s"]))
            if abs(cur_med_vel) > 8.0:
                half_w = 0.5 * (hi_w - lo_w)
                lean = min(cfg["drift_max_lean"], max(0.0, half_w * 0.6))
                adj += lean if cur_med_vel > 0 else -lean
            if cur_hs < cfg["drift_min_s"]:
                adj = 0.0

            # 外侧走廊主动偏置 (当排宽较大时，向该路易漏外侧偏置)
            if cfg.get("outer_guard_bias", 0.0) != 0.0 and (hi_w - lo_w) >= 65.0 and cur_hs >= cfg["drift_min_s"]:
                adj += cfg["outer_guard_bias"]

            aim_lat = base_aim + adj

        gap = cur_hs - pred_s
        lat_err = aim_lat - cur_hl
        if gap > cfg["hold_on"]:
            cur_waiting = True
        elif gap < cfg["walk_on"]:
            cur_waiting = False

        v_max = 280.0
        if cur_waiting:
            if abs(lat_err) > cfg["lat_tol"]:
                step_l = max(-cfg["lat_step"], min(cfg["lat_step"], lat_err))
                dist_t = math.hypot(10.0, step_l)
                move_d = min(dist_t, v_max * 0.85 * dt_step)
                cur_hs += (10.0 / dist_t) * move_d
                cur_hl += (step_l / dist_t) * move_d
        else:
            fwd_step = max(pred_s + 160.0 - cur_hs, 120.0)
            short_step = False
            if is_side and abs(lat_err) > cfg["side_short_lat_thresh"]:
                fwd_step = cfg["side_short_fwd_step"]
                short_step = (fwd_step <= 75.0)
            step_l = max(-100.0, min(100.0, lat_err))
            dist_t = math.hypot(fwd_step, step_l)
            # 实测短距点地 (fwd_step=70) + 大横移时英雄有效前进+横移总速度掉到 ~195/s；fwd_step>=115 时保持 ~260/s
            eff_ratio = 0.72 if short_step else (0.91 if abs(step_l) > 40.0 else 0.96)
            move_d = min(dist_t, v_max * eff_ratio * dt_step)
            if dist_t > 1.0:
                cur_hs += (fwd_step / dist_t) * move_d
                cur_hl += (step_l / dist_t) * move_d

        return cur_hs, cur_hl, cur_waiting, cur_med_prev, cur_med_vel, cur_hs - front_s, abs(cur_hl - front_l)

    for i in range(1, len(t_list)):
        dt = t_list[i] - t_list[i - 1]
        if dt <= 0.01 or dt > 0.6:
            dt = 0.1

        # A. 纯轨迹回放（直接对比原漏兵时刻的前距改善）
        hs_pure, hl_pure, waiting_pure, med_prev_pure, med_vel_pure, g_pure, le_pure = step_hero_controller(
            hs_pure, hl_pure, waiting_pure, med_prev_pure, med_vel_pure, orig_creeps[i], orig_creeps[i - 1], dt
        )
        if i == first_leak_idx and first_leak_cid in orig_creeps[i]:
            cs_lk, cl_lk = orig_creeps[i][first_leak_cid]
            gap_at_real_leak = hs_pure - cs_lk
            laterr_at_real_leak = abs(hl_pure - cl_lk)

        # B. 闭环碰撞回放
        active_sim = {cid: pos for cid, pos in sim_creeps.items() if cid not in escaped}
        if not active_sim or hs >= tower_s - 250.0:
            break
        hs, hl, waiting_align, med_prev, med_vel, g_sim, le_sim = step_hero_controller(
            hs, hl, waiting_align, med_prev, med_vel, active_sim, prev_creeps, dt
        )
        prev_creeps = {cid: list(pos) for cid, pos in sim_creeps.items()}
        gaps_trace.append(g_sim)
        lat_errs_trace.append(le_sim)

        # 推进模拟小兵
        for cid in list(sim_creeps.keys()):
            if cid not in orig_creeps[i] or cid not in orig_creeps[i - 1]:
                continue
            orig_ds = orig_creeps[i][cid][0] - orig_creeps[i - 1][cid][0]
            # 若小兵在原记录里被卡慢，而当前模拟中离英雄还远 (>65)，按基础巡航速度跟上来
            if hs - sim_creeps[cid][0] > 65.0:
                step_ds = max(orig_ds, cfg["creep_base_spd"] * dt * 0.96)
            else:
                step_ds = max(orig_ds, cfg["creep_base_spd"] * dt * 0.88)
            new_cs = sim_creeps[cid][0] + step_ds
            new_cl = interp_cl_at_s(creep_curves_s[cid], creep_curves_l[cid], new_cs)

            # 碰撞检测：圆心横向距离 <= 50 (冰女 32 + 小兵 16~32，考虑网格占位盒 64~96)
            if cid not in escaped:
                if new_cs >= hs - 52.0 and sim_creeps[cid][0] <= hs + 20.0:
                    if abs(new_cl - hl) <= 50.0:
                        new_cs = min(new_cs, hs - 40.0)
                        new_cl = interp_cl_at_s(creep_curves_s[cid], creep_curves_l[cid], new_cs)
                if new_cs > hs + 20.0 and new_cs < tower_s - 250.0:
                    escaped.add(cid)
            sim_creeps[cid] = [new_cs, new_cl]

    if gap_at_real_leak is None:
        gap_at_real_leak = min(gaps_trace) if gaps_trace else 0.0
        laterr_at_real_leak = max(lat_errs_trace) if lat_errs_trace else 0.0

    return {
        "real_leaks": len(real_escaped),
        "sim_leaks": len(escaped),
        "gap_at_leak": gap_at_real_leak,
        "laterr_at_leak": laterr_at_real_leak,
        "med_gap": sorted(gaps_trace)[len(gaps_trace)//2] if gaps_trace else 0.0,
        "med_lat_err": sorted(lat_errs_trace)[len(lat_errs_trace)//2] if lat_errs_trace else 0.0,
    }

def load_target_csv(fname):
    path = os.path.join(DATA_DIR, fname)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = [l.strip().lstrip("\ufeff").lstrip("ï»¿") for l in f if l.strip()]
    wave_traces = defaultdict(list)
    for line in lines:
        if line.startswith("#"):
            continue
        parts = line.split(",")
        if parts[0] == "trace" and len(parts) >= 7:
            w_num = int(parts[1])
            t = float(parts[2])
            hx, hy = float(parts[3]), float(parts[4])
            cdict = {}
            c_coords = parts[5:]
            for ci in range(0, len(c_coords) - 1, 2):
                if c_coords[ci] != "" and c_coords[ci + 1] != "":
                    cdict[f"c{ci//2 + 1}"] = (float(c_coords[ci]), float(c_coords[ci + 1]))
            wave_traces[w_num].append((t, hx, hy, cdict))
    return sorted(wave_traces.items())

def main():
    out = []
    out.append("=" * 120)
    out.append("【离线轨迹回放模拟验证：现行参数 (Baseline) vs 数据驱动新参数 (Tuned)】")
    out.append("=" * 120)

    cfg_bot_base = {
        "use_real_hs0": True, "wait_lead": 590.0, "init_lat_bias": 0.0,
        "pred_t": 0.25, "row_depth": 70.0, "row_width_max": 110.0,
        "side_med_activate_gap": 150.0,
        "lock_front_gap": 150.0, "single_front_pull": 20.0,
        "clamp_med_jump": False, "drift_predict_s": 0.7, "drift_max_lean": 35.0, "drift_min_s": 900.0,
        "outer_guard_bias": 0.0,
        "hold_on": 340.0, "walk_on": 300.0, "lat_tol": 25.0, "lat_step": 40.0,
        "side_short_lat_thresh": 20.0, "side_short_fwd_step": 70.0,
        "creep_base_spd": 318.0,
    }
    cfg_bot_tuned = dict(cfg_bot_base)
    cfg_bot_tuned.update({
        "use_real_hs0": False,
        "wait_lead": 680.0,             # 门口起卡等兵领先从 ~590 提高到 680 (距 spawnX 约 1080)
        "hold_on": 380.0,               # 常速边路(兵325 vs 冰女280) 提前到前距 350 起步，380 站住
        "walk_on": 350.0,
        "row_width_max": 96.0,          # 前排宽度 <= 96 才站中点 (原 110 超过 2*48=96 阻挡极限)
        "lock_front_gap": 140.0,
        "single_front_pull": 10.0,      # 单前排兵仅向中位收 10 (原 20)
        "clamp_med_jump": True,         # 抑制中位切换时的虚假漂移脉冲
        "drift_min_s": 1600.0,          # 下路前 1600 刚出树林禁止漂移修正
        "outer_guard_bias": -15.0,      # 下路向南外侧 (-侧) 预偏 15
        "side_short_lat_thresh": 40.0,  # 横向差 > 40 才缩短前进步长，且步长从 70 提至 115 (消除 187/s 龟速病!)
        "side_short_fwd_step": 115.0,
        "lat_tol": 18.0,
    })

    cfg_top_base = dict(cfg_bot_base)
    cfg_top_base.update({"drift_predict_s": 0.0, "drift_max_lean": 0.0, "creep_base_spd": 318.0})
    cfg_top_v11 = dict(cfg_bot_base)
    cfg_top_tuned = dict(cfg_bot_tuned)
    cfg_top_tuned.update({
        "wait_lead": 520.0,
        "hold_on": 360.0,
        "walk_on": 320.0,
        "drift_min_s": 900.0,
        "drift_predict_s": 0.75,
        "drift_max_lean": 38.0,
        "outer_guard_bias": +14.0,      # 上路向 + 侧(外侧) 预偏 14
    })

    cfg_mid_base = dict(cfg_bot_base)
    cfg_mid_base.update({"hold_on": 220.0, "walk_on": 180.0, "row_width_max": 110.0, "creep_base_spd": 312.0})
    cfg_mid_tuned = dict(cfg_mid_base)
    cfg_mid_tuned.update({"hold_on": 240.0, "walk_on": 200.0, "row_width_max": 96.0, "lat_tol": 18.0})

    datasets = [
        ("近卫下路 7m后常速 (093216+094838)", "bot", ["cm_bot_20261121-093216_5waves_pass0_avg9.csv", "cm_bot_20261121-094838_4waves_pass0_avg34.csv"], cfg_bot_base, cfg_bot_tuned),
        ("近卫上路 常速期 (053614)", "top", ["cm_top_20261121-053614_10waves_pass1_avg37.csv"], cfg_top_base, cfg_top_tuned),
        ("近卫上路 减速期 (055720)", "top", ["cm_top_20261121-055720_4waves_pass3_avg91.csv"], {**cfg_top_v11, "creep_base_spd": 240.0}, {**cfg_top_tuned, "creep_base_spd": 240.0, "wait_lead": 400.0, "walk_on": 280.0, "hold_on": 320.0}),
        ("近卫中路 常速期 (045234)", "mid", ["cm_mid_20261121-045234_23waves_pass20_avg96.csv"], cfg_mid_base, cfg_mid_tuned),
    ]

    for title, lane_key, fnames, c_base, c_tuned in datasets:
        out.append(f"\n>>> 实验组: {title}")
        out.append(f"{'文件与波次':<44} | {'实测漏':>6} | {'现行回放漏':>10} | {'新参回放漏':>10} | {'原漏点现行gap':>13} | {'原漏点新参gap':>13} | {'原漏点现行横差':>14} | {'原漏点新参横差':>14}")
        out.append("-" * 145)
        tot_w = 0
        real_lk_sum = 0
        base_lk_sum = 0
        tuned_lk_sum = 0
        base_perf = 0
        tuned_perf = 0
        gap_gains = []
        lat_gains = []
        for fn in fnames:
            for w_num, frames in load_target_csv(fn):
                rb = simulate_wave(lane_key, frames, c_base)
                rt = simulate_wave(lane_key, frames, c_tuned)
                if not rb or not rt:
                    continue
                tot_w += 1
                real_lk_sum += rb["real_leaks"]
                base_lk_sum += rb["sim_leaks"]
                tuned_lk_sum += rt["sim_leaks"]
                if rb["sim_leaks"] == 0:
                    base_perf += 1
                if rt["sim_leaks"] == 0:
                    tuned_perf += 1
                gap_gains.append(rt["gap_at_leak"] - rb["gap_at_leak"])
                lat_gains.append(rb["laterr_at_leak"] - rt["laterr_at_leak"])
                label = f"{fn[:28]}.. W{w_num:02d}"
                out.append(
                    f"{label:<44} | {rb['real_leaks']:>6} | {rb['sim_leaks']:>10} | {rt['sim_leaks']:>10} | "
                    f"{rb['gap_at_leak']:>+13.1f} | {rt['gap_at_leak']:>+13.1f} | "
                    f"{rb['laterr_at_leak']:>14.1f} | {rt['laterr_at_leak']:>14.1f}"
                )
        if tot_w > 0:
            red = 100.0 * (base_lk_sum - tuned_lk_sum) / max(1, base_lk_sum)
            avg_gg = sum(gap_gains) / len(gap_gains)
            avg_lg = sum(lat_gains) / len(lat_gains)
            out.append("-" * 145)
            out.append(
                f"汇总 ({tot_w} 波): 实测总漏={real_lk_sum} | 现行回放总漏={base_lk_sum} (0漏波={base_perf}/{tot_w}) "
                f"--> 新参数回放总漏={tuned_lk_sum} (0漏波={tuned_perf}/{tot_w}), 预计漏兵减少率 = {red:+.1f}% | "
                f"原漏兵点平均前距提升 = {avg_gg:+.1f}, 横向误差缩减 = {avg_lg:+.1f}"
            )

    text = "\n".join(out)
    with open(OUT_SIM, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_SIM}")

if __name__ == "__main__":
    main()
