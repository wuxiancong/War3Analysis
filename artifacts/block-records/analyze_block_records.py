# -*- coding: utf-8 -*-
r"""
全面解析卡兵实测记录（15个CSV + human_block_20261118_0711.log + AiUnit.log 真人录制）：
1. 按「路 × 模式(ai/human) × 光环期(加速406/减速244/常速325) × 成绩(满分0漏/漏1只/漏2只+)」对所有波次分类；
2. 统计每组的分布（p10 / p50中位数 / p90）：
   - 出兵时英雄等兵位 hero_s0、最前兵出生位 front_s0、初始前距 gap_0、起步时刻 t_walk 与起步前距 gap_walk；
   - 前距随车道距离 s 的分段变化；
   - 英雄与最前兵/整波中位的横向差 |lat_err|；
   - 英雄前进速度、横移速度、站住时间占比；
   - 每次漏兵发生时的精确画像：车道位置 s、世界坐标、横向哪一侧(cl - hl)、近战还是远程(由t=0出生坐标区分)、当时前距与英雄横移速度、前排跨度。
输出详尽报告到 D:\Qt\workspace\War3Analysis\artifacts\block-records\block_records_stats.txt
并导出结构化 JSON 到 D:\Qt\workspace\War3Analysis\artifacts\block-records\all_waves_parsed.json
"""
import os
import re
import json
import glob
import math
from collections import defaultdict

DATA_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\data\cm"
HUMAN_MID_LOG = r"D:\Qt\workspace\War3Analysis\artifacts\creep-block\human_block_20261118_0711.log"
AIUNIT_LOG = r"C:\War3Run\War3Launcher\logs\AiUnit.log"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\block_records_stats.txt"
OUT_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\all_waves_parsed.json"

K_AI_LANES = {
    "top": {
        "idx": 0, "name": "近卫上路",
        "raxX": -6368.0, "raxY": -4480.0, "towerX": -6112.0, "towerY": 1568.0,
        "spawnX": -6176.0, "spawnY": -4184.0,
        "meleeSpawn": (-6160.0, -4064.0), "rangedSpawn": (-6192.0, -4304.0),
    },
    "mid": {
        "idx": 1, "name": "近卫中路",
        "raxX": -4640.0, "raxY": -5152.0, "towerX": -1504.0, "towerY": -1824.0,
        "spawnX": -4792.0, "spawnY": -5496.0,
        "meleeSpawn": (-4752.0, -5344.0), "rangedSpawn": (-4832.0, -5648.0),
    },
    "bot": {
        "idx": 2, "name": "近卫下路",
        "raxX": -4032.0, "raxY": -6784.0, "towerX": 4960.0, "towerY": -6752.0,
        "spawnX": -3816.0, "spawnY": -6752.0,
        "meleeSpawn": (-3536.0, -6784.0), "rangedSpawn": (-4096.0, -6720.0),
    },
}

for k, L in K_AI_LANES.items():
    vx = L["towerX"] - L["raxX"]
    vy = L["towerY"] - L["raxY"]
    length = math.hypot(vx, vy)
    L["ux"] = vx / length
    L["uy"] = vy / length
    L["len"] = length
    L["spawn_along_rax"] = (L["spawnX"] - L["raxX"]) * L["ux"] + (L["spawnY"] - L["raxY"]) * L["uy"]

def proj_lane(lane_key, x, y, use_spawn_origin=True):
    L = K_AI_LANES[lane_key]
    ox = L["spawnX"] if use_spawn_origin else L["raxX"]
    oy = L["spawnY"] if use_spawn_origin else L["raxY"]
    ux, uy = L["ux"], L["uy"]
    s = (x - ox) * ux + (y - oy) * uy
    l = (x - ox) * (-uy) + (y - oy) * ux
    return s, l

def pct(arr, q):
    if not arr:
        return 0.0
    s = sorted(arr)
    idx = (len(s) - 1) * q / 100.0
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (idx - lo)

def fmt_dist(arr, digits=1):
    if not arr:
        return "无样本"
    p10 = pct(arr, 10)
    p50 = pct(arr, 50)
    p90 = pct(arr, 90)
    mean = sum(arr) / len(arr)
    return f"中位={p50:.{digits}f} (p10={p10:.{digits}f}, p90={p90:.{digits}f}, 均值={mean:.{digits}f}, n={len(arr)})"

def classify_creep_roles(lane_key, frame0_creeps):
    """
    根据第 0 帧各小兵的出生坐标区分 melee (近战) 与 ranged/siege (远程/攻城车)：
    远程兵刷在 rangedRect（沿车道更靠后 240~560 距离），近战刷在 meleeRect。
    """
    L = K_AI_LANES[lane_key]
    msx, msy = L["meleeSpawn"]
    rsx, rsy = L["rangedSpawn"]
    roles = {}
    if not frame0_creeps:
        return roles
    scored = []
    for cid, (cx, cy) in frame0_creeps.items():
        s0, l0 = proj_lane(lane_key, cx, cy)
        dm = math.hypot(cx - msx, cy - msy)
        dr = math.hypot(cx - rsx, cy - rsy)
        scored.append((s0, dr - dm, cid, dm, dr))
    scored.sort(key=lambda item: item[0]) # s0 从小到大（最后面的兵排第一）
    n = len(scored)
    for rank, (s0, diff_rm, cid, dm, dr) in enumerate(scored):
        if n == 4 and rank == 0:
            roles[cid] = "ranged"
        elif n >= 5 and rank <= 1:
            roles[cid] = "ranged/siege"
        else:
            roles[cid] = "melee"
    return roles

def analyze_wave_trace(lane_key, mode, file_name, wave_num, wave_meta, frames):
    if len(frames) < 5:
        return None
    frames.sort(key=lambda x: x[0])

    f0_t, f0_hx, f0_hy, f0_creeps = frames[0]
    roles = classify_creep_roles(lane_key, f0_creeps)

    t_arr = []
    hs_arr = []
    hl_arr = []
    front_s_arr = []
    front_l_arr = []
    med_l_arr = []
    gap_arr = []
    lat_err_front_arr = []
    lat_err_med_arr = []
    row_span_arr = []
    creeps_proj_frames = []

    for t, hx, hy, cdict in frames:
        if not cdict:
            continue
        hs, hl = proj_lane(lane_key, hx, hy)
        cproj = {}
        for cid, (cx, cy) in cdict.items():
            cs, cl = proj_lane(lane_key, cx, cy)
            cproj[cid] = (cs, cl, cx, cy)
        behind = [(cid, v[0], v[1], v[2], v[3]) for cid, v in cproj.items() if v[0] <= hs + 20.0]
        if behind:
            behind.sort(key=lambda item: item[1], reverse=True)
            f_cid, fs, fl, fx, fy = behind[0]
            row_ls = [item[2] for item in behind if item[1] >= fs - 70.0]
            row_span = max(row_ls) - min(row_ls) if len(row_ls) >= 2 else 0.0
            near_ls = sorted([item[2] for item in behind if item[1] >= fs - 300.0])
            med_l = near_ls[len(near_ls) // 2] if near_ls else fl
        else:
            all_items = sorted([(cid, v[0], v[1], v[2], v[3]) for cid, v in cproj.items()], key=lambda item: item[1], reverse=True)
            f_cid, fs, fl, fx, fy = all_items[0]
            row_span = 0.0
            med_l = fl

        t_arr.append(t)
        hs_arr.append(hs)
        hl_arr.append(hl)
        front_s_arr.append(fs)
        front_l_arr.append(fl)
        med_l_arr.append(med_l)
        gap_arr.append(hs - fs)
        lat_err_front_arr.append(hl - fl)
        lat_err_med_arr.append(hl - med_l)
        row_span_arr.append(row_span)
        creeps_proj_frames.append(cproj)

    if len(t_arr) < 5:
        return None

    # 计算前 10 秒内各小兵在未被挡住时的自由巡航速度 (用于精确识别 406 加速 / 244 减速 / 325 常速)
    early_creep_vels = []
    for i in range(len(t_arr) - 4):
        if t_arr[i] > 12.0:
            break
        dt = t_arr[i + 4] - t_arr[i]
        if dt < 0.25 or dt > 1.5:
            continue
        for cid in creeps_proj_frames[i]:
            if cid in creeps_proj_frames[i + 4]:
                # 若该小兵在此刻离英雄 > 70 (未被英雄直接顶住)
                cs_now = creeps_proj_frames[i][cid][0]
                if abs(hs_arr[i] - cs_now) > 75.0 or cs_now > hs_arr[i] + 30.0:
                    ds = creeps_proj_frames[i + 4][cid][0] - cs_now
                    v = ds / dt
                    if 140.0 < v < 460.0:
                        early_creep_vels.append(v)
    p80_creep_v = pct(early_creep_vels, 80) if early_creep_vels else 310.0

    if lane_key == "mid":
        aura_state = "normal_325"
    elif lane_key == "top":
        if p80_creep_v < 275.0 or (wave_num <= 11 and "055720" in file_name):
            aura_state = "slowed_244"
        else:
            aura_state = "normal_325"
    elif lane_key == "bot":
        if p80_creep_v > 350.0:
            aura_state = "boosted_406"
        else:
            aura_state = "normal_325"
    else:
        aura_state = "normal_325"

    hs0 = hs_arr[0]
    hl0 = hl_arr[0]
    fs0 = front_s_arr[0]
    gap0 = gap_arr[0]

    # 起步时刻：从等兵状态（兵靠近到 gap < 900 后）英雄沿车道向前移动超过 25
    t_walk = None
    gap_walk = None
    s_walk = None
    # 找到英雄稳定在等兵位的参考点（若一开始在远方等，取 gap 首次 < 600 时的 hs，否则取 hs0）
    wait_idx = 0
    for i in range(len(t_arr)):
        if gap_arr[i] <= 600.0:
            wait_idx = i
            break
    hs_wait = hs_arr[wait_idx]
    for i in range(wait_idx + 1, len(t_arr)):
        if hs_arr[i] - hs_wait > 25.0:
            t_walk = t_arr[i]
            gap_walk = gap_arr[i]
            s_walk = hs_arr[i]
            break

    v_hero_s_list = []
    v_hero_l_list = []
    v_hero_2d_list = []
    stop_frames = 0
    active_frames = 0
    active_gaps = []
    active_lat_err_front = []
    active_lat_err_med = []
    seg_gaps = defaultdict(list)

    for i in range(len(t_arr) - 1):
        dt = t_arr[i + 1] - t_arr[i]
        if dt < 0.03 or dt > 0.5:
            continue
        if -15.0 <= gap_arr[i] <= 380.0:
            vhs = (hs_arr[i + 1] - hs_arr[i]) / dt
            vhl = (hl_arr[i + 1] - hl_arr[i]) / dt
            vh2d = math.hypot(vhs, vhl)
            v_hero_s_list.append(vhs)
            v_hero_l_list.append(abs(vhl))
            v_hero_2d_list.append(vh2d)
            active_frames += 1
            if vh2d < 35.0:
                stop_frames += 1
            active_gaps.append(gap_arr[i])
            active_lat_err_front.append(abs(lat_err_front_arr[i]))
            active_lat_err_med.append(abs(lat_err_med_arr[i]))
            sbin = int(max(0.0, hs_arr[i]) // 1000) * 1000
            seg_gaps[sbin].append(gap_arr[i])

    stop_ratio = (stop_frames / active_frames) if active_frames > 0 else 0.0

    # 英雄总移动距离（用于过滤真人模式下英雄挂机不动的基线测量波）
    hero_total_move = abs(hs_arr[-1] - hs_arr[0]) + sum(abs(hs_arr[i+1] - hs_arr[i]) for i in range(len(hs_arr)-1))

    tower_s = K_AI_LANES[lane_key]["len"] - K_AI_LANES[lane_key]["spawn_along_rax"]
    escaped_cids = set()
    leak_events = []

    for i in range(1, len(t_arr)):
        hs = hs_arr[i]
        hl = hl_arr[i]
        if hs >= tower_s - 250.0:
            break
        cproj = creeps_proj_frames[i]
        i_prev = max(0, i - 3)
        dt_w = max(0.05, t_arr[i] - t_arr[i_prev])
        vhs_now = (hs_arr[i] - hs_arr[i_prev]) / dt_w
        vhl_now = (hl_arr[i] - hl_arr[i_prev]) / dt_w

        for cid, (cs, cl, cx, cy) in cproj.items():
            if cid in escaped_cids:
                continue
            if cs < tower_s - 250.0 and cs > hs + 20.0:
                was_behind = any(
                    cid in creeps_proj_frames[k] and creeps_proj_frames[k][cid][0] < hs_arr[k] - 5.0
                    for k in range(max(0, i - 20), i)
                )
                escaped_cids.add(cid)
                if not was_behind and hs0 < fs0:
                    continue
                i_pre = max(0, i - 5) # 漏兵前 ~0.5s
                hs_pre = hs_arr[i_pre]
                hl_pre = hl_arr[i_pre]
                cs_pre, cl_pre = creeps_proj_frames[i_pre].get(cid, (cs, cl))[:2]
                # 漏兵前 0.5s 时英雄正在挡的「当时最前兵」(可能不是漏掉的这只!)
                behind_pre = [(k_cid, v[0], v[1]) for k_cid, v in creeps_proj_frames[i_pre].items() if v[0] <= hs_pre + 20.0]
                if behind_pre:
                    behind_pre.sort(key=lambda item: item[1], reverse=True)
                    lead_s_pre = behind_pre[0][1]
                    lead_l_pre = behind_pre[0][2]
                    other_ls = [item[2] for item in behind_pre if item[1] >= lead_s_pre - 300.0]
                    row_ls_pre = [item[2] for item in behind_pre if item[1] >= lead_s_pre - 70.0]
                    span_pre = (max(row_ls_pre) - min(row_ls_pre)) if len(row_ls_pre) >= 2 else 0.0
                    wave_span_pre = (max(other_ls) - min(other_ls)) if len(other_ls) >= 2 else 0.0
                    med_pre = sorted(other_ls)[len(other_ls) // 2] if other_ls else cl_pre
                    front_gap_pre = hs_pre - lead_s_pre
                else:
                    span_pre = 0.0
                    wave_span_pre = 0.0
                    med_pre = cl_pre
                    front_gap_pre = hs_pre - cs_pre

                leak_events.append({
                    "file": file_name,
                    "lane": lane_key,
                    "mode": mode,
                    "aura": aura_state,
                    "wave": wave_num,
                    "cid": cid,
                    "role": roles.get(cid, "unknown"),
                    "t_leak": round(t_arr[i], 2),
                    "s_leak": round(cs, 1),
                    "x_leak": round(cx, 1),
                    "y_leak": round(cy, 1),
                    "creep_lat": round(cl, 1),
                    "hero_lat": round(hl, 1),
                    "lat_diff": round(cl - hl, 1),
                    "side_dir": "+侧" if (cl - hl) >= 0 else "-侧",
                    "pre05_self_gap": round(hs_pre - cs_pre, 1),
                    "pre05_front_gap": round(front_gap_pre, 1),
                    "pre05_lat_diff": round(cl_pre - hl_pre, 1),
                    "pre05_creep_vs_med": round(cl_pre - med_pre, 1),
                    "pre05_row_span": round(span_pre, 1),
                    "pre05_wave_span": round(wave_span_pre, 1),
                    "v_hero_s": round(vhs_now, 1),
                    "v_hero_l": round(vhl_now, 1),
                })

    leak_cnt = wave_meta.get("leak_cnt", len(escaped_cids))
    score = wave_meta.get("score", 100.0 * max(0, 4 - leak_cnt) / 4.0)
    if leak_cnt == 0:
        grade = "0_满分(0漏)"
    elif leak_cnt == 1:
        grade = "1_漏1只"
    else:
        grade = "2_漏2只+"

    return {
        "file": file_name,
        "lane": lane_key,
        "mode": mode,
        "aura": aura_state,
        "wave": wave_num,
        "score": score,
        "leak_cnt": leak_cnt,
        "leak_score": wave_meta.get("leak_score", score),
        "delay_s": wave_meta.get("delay_s", 0.0),
        "delay_score": wave_meta.get("delay_score", 0.0),
        "end_type": wave_meta.get("end_type", "unknown"),
        "grade": grade,
        "p80_creep_v": round(p80_creep_v, 1),
        "hero_total_move": round(hero_total_move, 1),
        "hs0": round(hs0, 1),
        "hl0": round(hl0, 1),
        "fs0": round(fs0, 1),
        "gap0": round(gap0, 1),
        "t_walk": round(t_walk, 2) if t_walk is not None else None,
        "gap_walk": round(gap_walk, 1) if gap_walk is not None else None,
        "s_walk": round(s_walk, 1) if s_walk is not None else None,
        "active_frames": active_frames,
        "stop_ratio": round(stop_ratio * 100.0, 1),
        "gap_p50": round(pct(active_gaps, 50), 1) if active_gaps else None,
        "gap_p10": round(pct(active_gaps, 10), 1) if active_gaps else None,
        "gap_p90": round(pct(active_gaps, 90), 1) if active_gaps else None,
        "lat_front_p50": round(pct(active_lat_err_front, 50), 1) if active_lat_err_front else None,
        "lat_front_p90": round(pct(active_lat_err_front, 90), 1) if active_lat_err_front else None,
        "lat_med_p50": round(pct(active_lat_err_med, 50), 1) if active_lat_err_med else None,
        "v_hero_s_p50": round(pct(v_hero_s_list, 50), 1) if v_hero_s_list else None,
        "v_hero_l_p50": round(pct(v_hero_l_list, 50), 1) if v_hero_l_list else None,
        "v_hero_2d_p50": round(pct(v_hero_2d_list, 50), 1) if v_hero_2d_list else None,
        "seg_gaps": {str(k): round(pct(v, 50), 1) for k, v in seg_gaps.items()},
        "leak_events": leak_events,
    }

def parse_csv_files():
    results = []
    for path in sorted(glob.glob(os.path.join(DATA_DIR, "*.csv"))):
        fname = os.path.basename(path)
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = [line.strip().lstrip("\ufeff").lstrip("ï»¿") for line in f if line.strip()]
        # 优先从文件名和 header 双重确认 lane_key
        if "_top_" in fname:
            lane_key = "top"
        elif "_bot_" in fname:
            lane_key = "bot"
        else:
            lane_key = "mid"
        mode = "ai"
        for line in lines:
            if "hero=" in line and "lane=" in line:
                m_lane = re.search(r"lane=(top|mid|bot)", line)
                m_mode = re.search(r"mode=(\w+)", line)
                if m_lane:
                    lane_key = m_lane.group(1)
                if m_mode:
                    mode = m_mode.group(1)
        wave_metas = {}
        wave_traces = defaultdict(list)
        for line in lines:
            if line.startswith("#"):
                continue
            parts = line.split(",")
            if parts[0] == "wave" and len(parts) >= 9:
                w_num = int(parts[2])
                score = float(parts[3])
                sec = float(parts[6])
                join_sec = float(parts[7])
                detail = parts[8]
                m_det = re.search(r"(\w+)\s+leak\s+(\d+)/(\d+)\s+[\d.]+s\s+leakScore\s+([\d.]+)\s+delay\s+([\d.]+)s\s+delayScore\s+([\d.]+)", detail)
                meta = {"score": score, "seconds": sec, "join_sec": join_sec, "detail": detail}
                if m_det:
                    meta["end_type"] = m_det.group(1)
                    meta["leak_cnt"] = int(m_det.group(2))
                    meta["creep_cnt"] = int(m_det.group(3))
                    meta["leak_score"] = float(m_det.group(4))
                    meta["delay_s"] = float(m_det.group(5))
                    meta["delay_score"] = float(m_det.group(6))
                wave_metas[w_num] = meta
            elif parts[0] == "trace" and len(parts) >= 7:
                w_num = int(parts[1])
                t = float(parts[2])
                hx = float(parts[3])
                hy = float(parts[4])
                creeps = {}
                c_coords = parts[5:]
                for ci in range(0, len(c_coords) - 1, 2):
                    sx, sy = c_coords[ci], c_coords[ci + 1]
                    if sx != "" and sy != "":
                        creeps[f"c{ci//2 + 1}"] = (float(sx), float(sy))
                wave_traces[w_num].append((t, hx, hy, creeps))

        for w_num, frames in sorted(wave_traces.items()):
            meta = wave_metas.get(w_num, {})
            res = analyze_wave_trace(lane_key, mode, fname, w_num, meta, frames)
            if res:
                results.append(res)
    return results

def parse_human_log_file(log_path, source_label):
    if not os.path.exists(log_path):
        return []
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    re_start = re.compile(r"🧭 \[Tactic\] 真人坐标 第 (\d+) 波 开始：(\d+) 只兵，兵营门口 ([-\d.]+),([-\d.]+)")
    re_coord = re.compile(r"🧭 \[Tactic\] 真人坐标 第 (\d+) 波 t=([\d.]+) 英雄 ([-\d.]+),([-\d.]+) \| 兵 (.*)")
    re_score = re.compile(r"🏁 \[Tactic\] 真人卡兵评分 第 (\d+) 波：(\S+) 用时 ([\d.]+)s \| 漏兵 (\d+)/(\d+).*?得分 ([\d.]+)")
    re_res1500 = re.compile(r"📏 \[Tactic\] 真人卡兵结果 第 (\d+) 波：走 ([\d.]+) 用时 ([\d.]+)s（理论 ([\d.]+)s）延迟 ([\d.]+)s")

    sessions = []
    cur_session = None

    for line in lines:
        m_st = re_start.search(line)
        if m_st:
            w_num = int(m_st.group(1))
            hx0, hy0 = float(m_st.group(3)), float(m_st.group(4))
            # 按离三路 spawnX/Y 的最近距离判断分路
            best_lane = min(K_AI_LANES.keys(), key=lambda k: math.hypot(hx0 - K_AI_LANES[k]["spawnX"], hy0 - K_AI_LANES[k]["spawnY"]))
            cur_session = {
                "wave": w_num,
                "lane": best_lane,
                "home": (hx0, hy0),
                "frames": [],
                "meta": {},
            }
            sessions.append(cur_session)
            continue

        if cur_session is None:
            continue

        m_co = re_coord.search(line)
        if m_co and int(m_co.group(1)) == cur_session["wave"]:
            t = float(m_co.group(2))
            hx, hy = float(m_co.group(3)), float(m_co.group(4))
            c_str = m_co.group(5).strip()
            cdict = {}
            for tok in c_str.split():
                if ":" in tok:
                    cid, xy = tok.split(":", 1)
                    if xy != "dead" and "," in xy:
                        cx, cy = xy.split(",", 1)
                        cdict[cid] = (float(cx), float(cy))
            cur_session["frames"].append((t, hx, hy, cdict))
            continue

        m_sc = re_score.search(line)
        if m_sc and int(m_sc.group(1)) == cur_session["wave"]:
            cur_session["meta"]["end_type"] = m_sc.group(2)
            cur_session["meta"]["seconds"] = float(m_sc.group(3))
            cur_session["meta"]["leak_cnt"] = int(m_sc.group(4))
            cur_session["meta"]["creep_cnt"] = int(m_sc.group(5))
            cur_session["meta"]["score"] = float(m_sc.group(6))
            continue

        m_r15 = re_res1500.search(line)
        if m_r15 and int(m_r15.group(1)) == cur_session["wave"]:
            cur_session["meta"]["delay_s"] = float(m_r15.group(5))

    results = []
    for idx, sess in enumerate(sessions):
        frames = sess["frames"]
        if len(frames) < 15:
            continue
        res = analyze_wave_trace(sess["lane"], "human", f"{source_label}#s{idx+1}", sess["wave"], sess["meta"], frames)
        # 过滤真人模式下英雄原地不动 (>90% 时间静止或总移动 < 400) 的纯基线采样波，以及英雄往回走迎面撞兵的非卡兵波
        if res and res["active_frames"] >= 15 and res["hero_total_move"] >= 450.0 and (res["v_hero_s_p50"] or 0) > 40.0:
            results.append(res)
    return results

def main():
    csv_waves = parse_csv_files()
    human_mid_waves = parse_human_log_file(HUMAN_MID_LOG, "human_mid_1118")
    human_aiunit_waves = parse_human_log_file(AIUNIT_LOG, "AiUnit_human")

    all_waves = csv_waves + human_mid_waves + human_aiunit_waves
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_waves, f, ensure_ascii=False, indent=2)

    out = []
    out.append(f"总计解析有效卡兵波次: {len(all_waves)} 波 (15个CSV AI={len(csv_waves)} 波, human_1118={len(human_mid_waves)} 波, AiUnit_human实操={len(human_aiunit_waves)} 波)")
    out.append("=" * 110)

    out.append("\n【一、全部波次分类明细表】")
    out.append(f"{'来源文件':<45} | {'路':<3} | {'模式':<5} | {'光环期':<10} | {'波':>2} | {'分':>5} | {'漏':>2} | {'拖延s':>5} | {'兵速P80':>6} | {'等兵hs0':>7} | {'初始gap0':>8} | {'起步t':>5} | {'起步gap':>7} | {'前距中位':>8} | {'横差中位':>8} | {'站住%':>5}")
    out.append("-" * 180)
    for w in all_waves:
        tw = f"{w['t_walk']:.2f}" if w['t_walk'] is not None else "  -  "
        gw = f"{w['gap_walk']:.0f}" if w['gap_walk'] is not None else "  -  "
        gp50 = f"{w['gap_p50']:.0f}" if w['gap_p50'] is not None else "  -  "
        lp50 = f"{w['lat_front_p50']:.0f}" if w['lat_front_p50'] is not None else "  -  "
        out.append(
            f"{w['file']:<45} | {w['lane']:<3} | {w['mode']:<5} | {w['aura']:<10} | {w['wave']:>2} | "
            f"{w['score']:>5.1f} | {w['leak_cnt']:>2} | {w['delay_s']:>5.1f} | {w['p80_creep_v']:>6.1f} | "
            f"{w['hs0']:>7.0f} | {w['gap0']:>8.0f} | {tw:>5} | {gw:>7} | {gp50:>8} | {lp50:>8} | {w['stop_ratio']:>4.1f}%"
        )

    groups = defaultdict(list)
    for w in all_waves:
        groups[(w["lane"], w["mode"], w["aura"], w["grade"])].append(w)

    out.append("\n\n" + "=" * 110)
    out.append("【二、按「路 × 模式 × 光环期 × 成绩」分组统计对比 (中位数 / p10 / p90)】")
    out.append("=" * 110)
    for gkey in sorted(groups.keys()):
        lane, mode, aura, grade = gkey
        g_waves = groups[gkey]
        out.append(f"\n>>> 分组: 路={lane} | 模式={mode} | 光环期={aura} | 成绩={grade} (共 {len(g_waves)} 波)")
        out.append(f"  得分        : {fmt_dist([w['score'] for w in g_waves])}")
        out.append(f"  拖延秒数    : {fmt_dist([w['delay_s'] for w in g_waves])}")
        out.append(f"  等兵位hs0   : {fmt_dist([w['hs0'] for w in g_waves])}")
        out.append(f"  初始前距gap0: {fmt_dist([w['gap0'] for w in g_waves])}")
        out.append(f"  起步时间t   : {fmt_dist([w['t_walk'] for w in g_waves if w['t_walk'] is not None], 2)}")
        out.append(f"  起步时前距  : {fmt_dist([w['gap_walk'] for w in g_waves if w['gap_walk'] is not None])}")
        out.append(f"  全程前距P50 : {fmt_dist([w['gap_p50'] for w in g_waves if w['gap_p50'] is not None])}")
        out.append(f"  最差前距P10 : {fmt_dist([w['gap_p10'] for w in g_waves if w['gap_p10'] is not None])}")
        out.append(f"  前排横差P50 : {fmt_dist([w['lat_front_p50'] for w in g_waves if w['lat_front_p50'] is not None])}")
        out.append(f"  中位横差P50 : {fmt_dist([w['lat_med_p50'] for w in g_waves if w['lat_med_p50'] is not None])}")
        out.append(f"  英雄前进速  : {fmt_dist([w['v_hero_s_p50'] for w in g_waves if w['v_hero_s_p50'] is not None])}")
        out.append(f"  英雄横移速  : {fmt_dist([w['v_hero_l_p50'] for w in g_waves if w['v_hero_l_p50'] is not None])}")
        out.append(f"  站住时间%   : {fmt_dist([w['stop_ratio'] for w in g_waves])}")
        seg_agg = defaultdict(list)
        for w in g_waves:
            for sb, gv in w["seg_gaps"].items():
                seg_agg[int(sb)].append(gv)
        if seg_agg:
            seg_str = ", ".join(f"s={sb}..{sb+1000}: {pct(vals, 50):.0f}" for sb, vals in sorted(seg_agg.items()))
            out.append(f"  前距随车道s : {seg_str}")

    # 仅汇总 CSV AI 与 真人实操 的漏兵事件
    all_leaks = []
    for w in all_waves:
        all_leaks.extend(w["leak_events"])

    out.append("\n\n" + "=" * 110)
    out.append(f"【三、全部漏兵事件逐次画像 (共 {len(all_leaks)} 次漏兵)】")
    out.append("=" * 110)
    out.append(f"{'文件':<42} | {'路':<3} | {'模式':<5} | {'光环':<10} | {'波':>2} | {'兵ID':<4} | {'兵种':<12} | {'t_leak':>6} | {'车道s':>6} | {'坐标(x,y)':<14} | {'兵横cl':>6} | {'英横hl':>6} | {'横差cl-hl':>9} | {'前0.5s前距':>10} | {'前0.5s波宽':>10} | {'英雄前进v':>9} | {'英雄横移v':>9}")
    out.append("-" * 200)
    for lk in all_leaks:
        xy_s = f"({lk['x_leak']:.0f},{lk['y_leak']:.0f})"
        out.append(
            f"{lk['file']:<42} | {lk['lane']:<3} | {lk['mode']:<5} | {lk['aura']:<10} | {lk['wave']:>2} | "
            f"{lk['cid']:<4} | {lk['role']:<12} | {lk['t_leak']:>5.1f}s | {lk['s_leak']:>6.0f} | {xy_s:<14} | "
            f"{lk['creep_lat']:>+6.0f} | {lk['hero_lat']:>+6.0f} | {lk['lat_diff']:>+9.0f} | "
            f"{lk['pre05_front_gap']:>+10.0f} | {lk['pre05_wave_span']:>10.0f} | {lk['v_hero_s']:>+9.0f} | {lk['v_hero_l']:>+9.0f}"
        )

    out.append("\n--- 按路+模式+光环期汇总漏兵统计 ---")
    leaks_by_lane = defaultdict(list)
    for lk in all_leaks:
        leaks_by_lane[(lk["lane"], lk["mode"], lk["aura"])].append(lk)
    for (lane, mode, aura), lks in sorted(leaks_by_lane.items()):
        melee_n = sum(1 for x in lks if x["role"] == "melee")
        ranged_n = len(lks) - melee_n
        plus_n = sum(1 for x in lks if x["lat_diff"] >= 0)
        minus_n = len(lks) - plus_n
        out.append(f"\n* [{lane} | {mode} | {aura}] 共 {len(lks)} 次漏兵:")
        out.append(f"  - 兵种分布: 近战(melee)={melee_n} ({100*melee_n/len(lks):.0f}%), 远程/车(ranged)={ranged_n} ({100*ranged_n/len(lks):.0f}%)")
        out.append(f"  - 漏兵侧向: +侧(cl>hl)={plus_n} ({100*plus_n/len(lks):.0f}%), -侧(cl<hl)={minus_n} ({100*minus_n/len(lks):.0f}%)")
        out.append(f"  - 漏兵位置s: {fmt_dist([x['s_leak'] for x in lks])}")
        out.append(f"  - 漏兵横向差|cl-hl|: {fmt_dist([abs(x['lat_diff']) for x in lks])}")
        out.append(f"  - 漏前0.5s最前兵前距: {fmt_dist([x['pre05_front_gap'] for x in lks])}")
        out.append(f"  - 漏前0.5s整波横跨度: {fmt_dist([x['pre05_wave_span'] for x in lks])}")
        out.append(f"  - 漏时英雄横移速|v_hl|: {fmt_dist([abs(x['v_hero_l']) for x in lks])}")
        out.append(f"  - 漏时英雄前进速v_hs: {fmt_dist([x['v_hero_s'] for x in lks])}")

    text = "\n".join(out)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_TXT}")

if __name__ == "__main__":
    main()
