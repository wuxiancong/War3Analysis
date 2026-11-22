# -*- coding: utf-8 -*-
r"""
第二轮卡兵参数与逻辑修复离线轨迹回放验证脚本 (simulate_round2.py)
对比：
  A. 现行 §5.1 代码行为 (Current_v51)：
     - 拿切换后的 aimLat 算 medVel 漂移 + |medVel|>8 阶跃 lean(±35)
     - 边路 medianAim 屏蔽 splitAim（rowW > 96 时退化为站整波中位）
     - |latErr|>40 时 fwd=115, step_l=100（41°斜角）
  B. 第二轮修复方案 (Round2_Fix)：
     - 纯整波中位数 rawMed 算漂移，跳变 >24 时衰减 medVel*=0.3
     - 取消阶跃 lean，改为线性连续修正 adj = clamp(medVel * 0.45, -38, +38)，且在 [900,1300]/[1600,2000] 线性淡入
     - 边路 rowN>=2 且 rowW>96 时激活 splitAim（放弃孤兵、锁大撮 1s）
     - 贴身危险区 gap<85 时限制单步横移 <=65 且 fwd>=150（保证前进速度 >=250/s）
测试数据集：
  1. 近卫下路常速期 114223 (8 波，实测 avg 37)
  2. 近卫上路常速期 113623 (8 波，实测 avg 51)
  3. 近卫上路减速期 111403 (10 波，实测 avg 26)
输出到 D:\Qt\workspace\War3Analysis\artifacts\block-records\round2\round2_sim_report.txt
"""
import os
import math
from collections import defaultdict

DATA_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\data\cm"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\round2\round2_sim_report.txt"

K_AI_LANES = {
    "top": {"raxX": -6368.0, "raxY": -4480.0, "towerX": -6112.0, "towerY": 1568.0, "spawnX": -6176.0, "spawnY": -4184.0},
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
            return l_curve[k] + ((s_val - s_curve[k]) / ds) * (l_curve[k + 1] - l_curve[k])
    return l_curve[-1]

def load_csv(fname):
    path = os.path.join(DATA_DIR, fname)
    traces = defaultdict(list)
    scores = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        for raw in f:
            line = raw.strip().lstrip("\ufeff").lstrip("ï»¿")
            if not line or line.startswith("#"):
                continue
            p = line.split(",")
            if p[0] == "wave":
                scores[int(p[2])] = float(p[3])
            elif p[0] == "trace" and len(p) >= 7:
                w = int(p[1])
                t = float(p[2])
                hx, hy = float(p[3]), float(p[4])
                cdict = {}
                cc = p[5:]
                for ci in range(0, len(cc) - 1, 2):
                    if cc[ci] != "" and cc[ci + 1] != "":
                        cdict[f"c{ci//2+1}"] = (float(cc[ci]), float(cc[ci + 1]))
                traces[w].append((t, hx, hy, cdict))
    return scores, sorted(traces.items())

def simulate_wave(lane_key, frames, cfg):
    if len(frames) < 5:
        return None
    frames.sort(key=lambda x: x[0])
    t_list = [f[0] for f in frames]
    orig_creeps = []
    creep_curves_s = defaultdict(list)
    creep_curves_l = defaultdict(list)
    real_hero = []
    for t, hx, hy, cdict in frames:
        real_hero.append(proj_lane(lane_key, hx, hy))
        cf = {}
        for cid, (cx, cy) in cdict.items():
            cs, cl = proj_lane(lane_key, cx, cy)
            cf[cid] = (cs, cl)
            if not creep_curves_s[cid] or cs > creep_curves_s[cid][-1] + 2.0:
                creep_curves_s[cid].append(cs)
                creep_curves_l[cid].append(cl)
        orig_creeps.append(cf)

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

    sim_creeps = {cid: [cs0, cl0] for cid, (cs0, cl0) in orig_creeps[0].items()}
    hs, hl = real_hero[0]
    if cfg.get("init_hs_override") is not None:
        hs = cfg["init_hs_override"]
        hl = cfg["init_hl_override"]

    hs_pure, hl_pure = hs, hl
    st_pure = {"wait": True, "med_prev": None, "med_vel": 0.0, "lock_until": -1.0, "side_lat": 0.0, "aim_jumps": 0, "prev_aim": None}
    st_sim = {"wait": True, "med_prev": None, "med_vel": 0.0, "lock_until": -1.0, "side_lat": 0.0, "aim_jumps": 0, "prev_aim": None}
    gap_at_leak = None
    laterr_at_leak = None
    escaped = set()
    prev_creeps = {cid: list(pos) for cid, pos in sim_creeps.items()}

    def step_ctrl(t_now, cur_hs, cur_hl, st, c_src, p_src, dt_step):
        cand = []
        for cid, (cs, cl) in c_src.items():
            ps, pl = p_src.get(cid, (cs, cl))
            vp = max(-100.0, min(400.0, (cs - ps) / dt_step))
            vl = max(-320.0, min(320.0, (cl - pl) / dt_step))
            if cs > cur_hs + 20.0:
                continue
            cand.append((cid, cs, cl, cs + vp * 0.25, cl + vl * 0.25))
        if not cand:
            return cur_hs, cur_hl

        cand.sort(key=lambda x: x[3], reverse=True)
        _, front_s, front_l, pred_s, pred_l = cand[0]
        row_cands = [c for c in cand if c[3] >= pred_s - 70.0]
        lo_row = min(c[4] for c in row_cands)
        hi_row = max(c[4] for c in row_cands)
        row_n = len(row_cands)
        aim_lat = pred_l
        if row_n >= 2 and (hi_row - lo_row) <= 96.0:
            aim_lat = 0.5 * (lo_row + hi_row)

        use_split = False
        if cfg["enable_side_split"] and row_n >= 2 and (hi_row - lo_row) > 96.0:
            # 激活 splitAim：按最大横向空隙分两撮，锁兵多的一撮 1s
            near = sorted([c for c in cand if c[3] >= pred_s - 300.0], key=lambda x: x[4])
            if len(near) >= 2:
                cut, best_g = 1, -1.0
                for k in range(1, len(near)):
                    if near[k][4] - near[k - 1][4] > best_g:
                        best_g = near[k][4] - near[k - 1][4]
                        cut = k
                grpA, grpB = near[:cut], near[cut:]
                def grp_aim(g):
                    fp = max(x[3] for x in g)
                    gl = min(x[4] for x in g if x[3] >= fp - 70.0)
                    gh = max(x[4] for x in g if x[3] >= fp - 70.0)
                    return 0.5 * (gl + gh), fp
                aimA, fpA = grp_aim(grpA)
                aimB, fpB = grp_aim(grpB)
                if t_now < st["lock_until"]:
                    pickA = abs(aimA - st["side_lat"]) <= abs(aimB - st["side_lat"])
                else:
                    pickA = (len(grpA) > len(grpB)) if len(grpA) != len(grpB) else (abs(aimA - cur_hl) <= abs(aimB - cur_hl))
                    st["lock_until"] = t_now + 1.0
                aim_lat = aimA if pickA else aimB
                pred_s = fpA if pickA else fpB
                st["side_lat"] = aim_lat
                use_split = True

        if not use_split and len(cand) >= 2 and (lane_key != "bot" or (cur_hs - pred_s) <= 150.0):
            near = [c for c in cand if c[3] >= pred_s - 300.0]
            ls = sorted([c[4] for c in near])
            raw_med = ls[len(ls)//2] if len(ls) % 2 == 1 else 0.5 * (ls[len(ls)//2 - 1] + ls[len(ls)//2])
            lo_w, hi_w = ls[0], ls[-1]
            aim_lat = raw_med
            if row_n >= 2 and (hi_row - lo_row) <= 96.0:
                aim_lat = 0.5 * (lo_row + hi_row)
            elif row_n == 1 and abs(pred_l - raw_med) > 40.0 and (cur_hs - pred_s) < 150.0:
                aim_lat = pred_l + (10.0 if raw_med > pred_l else -10.0)

            # 漂移估算
            med_src = raw_med if cfg["pure_raw_med_drift"] else aim_lat
            if st["med_prev"] is None:
                st["med_prev"] = med_src
            else:
                dm = med_src - st["med_prev"]
                if abs(dm) > cfg["jump_thresh"]:
                    if cfg["decay_vel_on_jump"]:
                        st["med_vel"] *= 0.3
                    st["med_prev"] = med_src
                else:
                    v = max(-120.0, min(120.0, dm / dt_step))
                    st["med_vel"] = st["med_vel"] * 0.6 + v * 0.4
                    st["med_prev"] = med_src

            if cfg["linear_drift_only"]:
                adj = max(-38.0, min(38.0, st["med_vel"] * 0.45))
                s_min = 1600.0 if lane_key == "bot" else 900.0
                ramp = max(0.0, min(1.0, (cur_hs - s_min) / 400.0))
                adj *= ramp
            else:
                adj = max(-60.0, min(60.0, st["med_vel"] * 0.7))
                if abs(st["med_vel"]) > 8.0:
                    lean = min(35.0, max(0.0, 0.5 * (hi_w - lo_w) * 0.6))
                    adj += lean if st["med_vel"] > 0 else -lean
                s_min = 1600.0 if lane_key == "bot" else 900.0
                if cur_hs < s_min:
                    adj = 0.0
            aim_lat = aim_lat + adj

        if st["prev_aim"] is not None and abs(aim_lat - st["prev_aim"]) >= 50.0:
            st["aim_jumps"] += 1
        st["prev_aim"] = aim_lat

        gap = cur_hs - pred_s
        lat_err = aim_lat - cur_hl
        if gap > cfg["hold_on"]:
            st["wait"] = True
        elif gap < cfg["walk_on"]:
            st["wait"] = False

        v_max = 280.0
        if st["wait"]:
            if abs(lat_err) > 18.0:
                step_l = max(-40.0, min(40.0, lat_err))
                dist_t = math.hypot(10.0, step_l)
                move_d = min(dist_t, v_max * 0.85 * dt_step)
                cur_hs += (10.0 / dist_t) * move_d
                cur_hl += (step_l / dist_t) * move_d
        else:
            fwd_step = max(pred_s + 160.0 - cur_hs, 120.0)
            lat_lim = 100.0
            if cfg["tight_gap_speed_guard"] and gap < 85.0:
                fwd_step = max(fwd_step, 150.0)
                lat_lim = 65.0
            elif abs(lat_err) > 40.0:
                fwd_step = 115.0
            step_l = max(-lat_lim, min(lat_lim, lat_err))
            dist_t = math.hypot(fwd_step, step_l)
            # 模拟大角度转向掉速：斜角 > 32° 掉速至 0.80，<=23° 保持 0.96
            ang = math.degrees(math.atan2(abs(step_l), max(1.0, fwd_step)))
            eff = 0.80 if ang > 32.0 else (0.90 if ang > 23.0 else 0.96)
            move_d = min(dist_t, v_max * eff * dt_step)
            if dist_t > 1.0:
                cur_hs += (fwd_step / dist_t) * move_d
                cur_hl += (step_l / dist_t) * move_d
        return cur_hs, cur_hl

    for i in range(1, len(t_list)):
        dt = t_list[i] - t_list[i - 1]
        if dt <= 0.01 or dt > 0.6:
            dt = 0.1
        hs_pure, hl_pure = step_ctrl(t_list[i], hs_pure, hl_pure, st_pure, orig_creeps[i], orig_creeps[i - 1], dt)
        if i == first_leak_idx and first_leak_cid in orig_creeps[i]:
            cs_lk, cl_lk = orig_creeps[i][first_leak_cid]
            gap_at_leak = hs_pure - cs_lk
            laterr_at_leak = abs(hl_pure - cl_lk)

        active_sim = {cid: pos for cid, pos in sim_creeps.items() if cid not in escaped}
        if not active_sim or hs >= tower_s - 250.0:
            break
        hs, hl = step_ctrl(t_list[i], hs, hl, st_sim, active_sim, prev_creeps, dt)
        prev_creeps = {cid: list(pos) for cid, pos in sim_creeps.items()}

        for cid in list(sim_creeps.keys()):
            if cid not in orig_creeps[i] or cid not in orig_creeps[i - 1]:
                continue
            orig_ds = orig_creeps[i][cid][0] - orig_creeps[i - 1][cid][0]
            if hs - sim_creeps[cid][0] > 65.0:
                step_ds = max(orig_ds, cfg["creep_spd"] * dt * 0.96)
            else:
                step_ds = max(orig_ds, cfg["creep_spd"] * dt * 0.88)
            new_cs = sim_creeps[cid][0] + step_ds
            new_cl = interp_cl_at_s(creep_curves_s[cid], creep_curves_l[cid], new_cs)
            if cid not in escaped:
                if new_cs >= hs - 52.0 and sim_creeps[cid][0] <= hs + 20.0:
                    if abs(new_cl - hl) <= 50.0:
                        new_cs = min(new_cs, hs - 40.0)
                        new_cl = interp_cl_at_s(creep_curves_s[cid], creep_curves_l[cid], new_cs)
                if new_cs > hs + 20.0 and new_cs < tower_s - 250.0:
                    escaped.add(cid)
            sim_creeps[cid] = [new_cs, new_cl]

    return {
        "real_leaks": len(real_escaped),
        "sim_leaks": len(escaped),
        "gap_at_leak": gap_at_leak if gap_at_leak is not None else 0.0,
        "laterr_at_leak": laterr_at_leak if laterr_at_leak is not None else 0.0,
        "aim_jumps": st_sim["aim_jumps"],
    }

def main():
    out = []
    out.append("=" * 125)
    out.append("【Round 2 离线轨迹回放验证：现行 §5.1 代码 (Curr) vs 第二轮逻辑修复方案 (R2Fix)】")
    out.append("=" * 125)

    curr_norm = {
        "pure_raw_med_drift": False, "jump_thresh": 32.0, "decay_vel_on_jump": False,
        "linear_drift_only": False, "enable_side_split": False, "tight_gap_speed_guard": False,
        "hold_on": 380.0, "walk_on": 350.0, "creep_spd": 320.0,
    }
    r2_norm = {
        "pure_raw_med_drift": True, "jump_thresh": 24.0, "decay_vel_on_jump": True,
        "linear_drift_only": True, "enable_side_split": True, "tight_gap_speed_guard": True,
        "hold_on": 380.0, "walk_on": 350.0, "creep_spd": 320.0,
    }
    curr_slow = dict(curr_norm, hold_on=320.0, walk_on=280.0, creep_spd=244.0)
    r2_slow = dict(r2_norm, hold_on=340.0, walk_on=300.0, creep_spd=244.0, init_hs_override=510.0, init_hl_override=10.0)

    exps = [
        ("近卫下路常速期 114223 (8波, 实测avg 37)", "bot", "cm_bot_20261121-114223_8waves_pass2_avg37.csv", curr_norm, r2_norm),
        ("近卫上路常速期 113623 (8波, 实测avg 51)", "top", "cm_top_20261121-113623_8waves_pass1_avg51.csv", curr_norm, r2_norm),
        ("近卫上路减速期 111403 (10波, 实测avg 26)", "top", "cm_top_20261121-111403_10waves_pass0_avg26.csv", curr_slow, r2_slow),
    ]

    for title, lane, fn, c_base, c_fix in exps:
        scores, waves = load_csv(fn)
        out.append(f"\n>>> {title}")
        out.append(f"{'波':>3} | {'实测分':>6} | {'实测漏':>6} | {'Curr漏':>6} | {'R2Fix漏':>7} | {'Curr目标跳':>10} | {'R2目标跳':>8} | {'漏点CurrGap':>11} | {'漏点R2Gap':>9}")
        out.append("-" * 92)
        tot_r, tot_b, tot_f, jb, jf, perf_b, perf_f = 0, 0, 0, 0, 0, 0, 0
        gg = []
        for w, fr in waves:
            rb = simulate_wave(lane, fr, c_base)
            rf = simulate_wave(lane, fr, c_fix)
            if not rb or not rf: continue
            tot_r += rb["real_leaks"]
            tot_b += rb["sim_leaks"]
            tot_f += rf["sim_leaks"]
            jb += rb["aim_jumps"]
            jf += rf["aim_jumps"]
            if rb["sim_leaks"] == 0: perf_b += 1
            if rf["sim_leaks"] == 0: perf_f += 1
            gg.append(rf["gap_at_leak"] - rb["gap_at_leak"])
            out.append(
                f"W{w:02d} | {scores.get(w,0):6.1f} | {rb['real_leaks']:>6} | {rb['sim_leaks']:>6} | {rf['sim_leaks']:>7} | "
                f"{rb['aim_jumps']:>10} | {rf['aim_jumps']:>8} | {rb['gap_at_leak']:>+11.1f} | {rf['gap_at_leak']:>+9.1f}"
            )
        red_l = 100.0 * (tot_b - tot_f) / max(1, tot_b)
        red_j = 100.0 * (jb - jf) / max(1, jb)
        out.append("-" * 92)
        out.append(
            f"汇总 ({len(waves)}波): 实测总漏={tot_r} | Curr回放漏={tot_b}(0漏={perf_b}) --> R2Fix回放漏={tot_f}(0漏={perf_f}), "
            f"漏兵减少={red_l:+.1f}% | 目标剧跳(>=50) {jb}-->{jf} ({red_j:+.1f}%) | 原漏点前距均值变化={sum(gg)/max(1,len(gg)):+.1f}"
        )

    text = "\n".join(out)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_TXT}")

if __name__ == "__main__":
    main()
