# -*- coding: utf-8 -*-
r"""
卡兵记录第二轮深度诊断脚本 (artifacts/block-records/round2/analyze_round2.py)
聚焦 3 个核心问题：
1. 下路常速期 cm_bot_20261121-114223 (8波: 63/54/69 vs 17/29/26/24/18) 前 3 波好、后 5 波差的决定性原因；
2. 上路常速期 cm_top_20261121-113623 (8波: avg 51) 新参数下的漏兵 4 个关键量诊断 (对比旧版 053614)；
3. 上路减速期波动 91 -> 54 -> 35 -> 62 -> 26 (055720 / 102009 / 104450 / 105450 / 111403) 逐波根因对比。
输出到 D:\Qt\workspace\War3Analysis\artifacts\block-records\round2\round2_diag.txt
"""
import os
import re
import math
from collections import defaultdict

DATA_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\data\cm"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\round2\round2_diag.txt"

K_AI_LANES = {
    "top": {"raxX": -6368.0, "raxY": -4480.0, "towerX": -6112.0, "towerY": 1568.0, "spawnX": -6176.0, "spawnY": -4184.0},
    "bot": {"raxX": -4032.0, "raxY": -6784.0, "towerX": 4960.0, "towerY": -6752.0, "spawnX": -3816.0, "spawnY": -6752.0},
}
for k, L in K_AI_LANES.items():
    vx, vy = L["towerX"] - L["raxX"], L["towerY"] - L["raxY"]
    length = math.hypot(vx, vy)
    L["ux"], L["uy"], L["len"] = vx / length, vy / length, length
    L["spawn_along_rax"] = (L["spawnX"] - L["raxX"]) * L["ux"] + (L["spawnY"] - L["raxY"]) * L["uy"]

def proj_lane(lane_key, x, y):
    L = K_AI_LANES[lane_key]
    ox, oy, ux, uy = L["spawnX"], L["spawnY"], L["ux"], L["uy"]
    return (x - ox) * ux + (y - oy) * uy, (x - ox) * (-uy) + (y - oy) * ux

def pct(arr, q):
    if not arr: return 0.0
    s = sorted(arr)
    idx = (len(s) - 1) * q / 100.0
    lo, hi = int(math.floor(idx)), int(math.ceil(idx))
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (idx - lo)

def load_csv(fname):
    path = os.path.join(DATA_DIR, fname)
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = [l.strip().lstrip("\ufeff").lstrip("ï»¿") for l in f if l.strip()]
    lane_key = "top" if "_top_" in fname else "bot"
    waves = []
    traces = defaultdict(list)
    for line in lines:
        if line.startswith("#"):
            continue
        p = line.split(",")
        if p[0] == "wave" and len(p) >= 9:
            w = {
                "attempt": int(p[1]), "wave": int(p[2]), "score": float(p[3]),
                "pass_line": float(p[4]), "result": p[5], "seconds": float(p[6]),
                "joinSeconds": float(p[7]), "detail": p[8],
            }
            m = re.search(r"(\w+)\s+leak\s+(\d+)/(\d+)\s+[\d.]+s\s+leakScore\s+([\d.]+)\s+delay\s+([\d.]+)s\s+delayScore\s+([\d.]+)", p[8])
            if m:
                w.update({
                    "end_type": m.group(1), "leak_cnt": int(m.group(2)), "creep_cnt": int(m.group(3)),
                    "leak_score": float(m.group(4)), "delay_s": float(m.group(5)), "delay_score": float(m.group(6)),
                })
            waves.append(w)
        elif p[0] == "trace" and len(p) >= 7:
            wn = int(p[1])
            t = float(p[2])
            hx, hy = float(p[3]), float(p[4])
            cdict = {}
            cc = p[5:]
            for ci in range(0, len(cc) - 1, 2):
                if cc[ci] != "" and cc[ci + 1] != "":
                    cdict[f"c{ci//2+1}"] = (float(cc[ci]), float(cc[ci + 1]))
            traces[wn].append((t, hx, hy, cdict))
    return lane_key, waves, traces

def inspect_wave(lane_key, w, frames):
    frames.sort(key=lambda x: x[0])
    if len(frames) < 3:
        return None
    t0, hx0, hy0, c0 = frames[0]
    hs0, hl0 = proj_lane(lane_key, hx0, hy0)
    c0_proj = {cid: proj_lane(lane_key, xy[0], xy[1]) for cid, xy in c0.items()}
    fs0 = max(v[0] for v in c0_proj.values()) if c0_proj else 0.0
    gap0 = hs0 - fs0

    # 逐帧投影
    ts, hss, hls, fss, fls, gaps, cprojs = [], [], [], [], [], [], []
    for t, hx, hy, cdict in frames:
        if not cdict: continue
        hs, hl = proj_lane(lane_key, hx, hy)
        cp = {cid: (proj_lane(lane_key, xy[0], xy[1])[0], proj_lane(lane_key, xy[0], xy[1])[1], xy[0], xy[1]) for cid, xy in cdict.items()}
        behind = [(cid, v[0], v[1]) for cid, v in cp.items() if v[0] <= hs + 20.0]
        if behind:
            behind.sort(key=lambda x: x[1], reverse=True)
            fs, fl = behind[0][1], behind[0][2]
        else:
            all_c = sorted([(cid, v[0], v[1]) for cid, v in cp.items()], key=lambda x: x[1], reverse=True)
            fs, fl = all_c[0][1], all_c[0][2]
        ts.append(t); hss.append(hs); hls.append(hl); fss.append(fs); fls.append(fl); gaps.append(hs - fs); cprojs.append(cp)

    # 估算兵速 P80 (前 10s 未被挡住的小兵)
    cvels = []
    for i in range(len(ts) - 3):
        if ts[i] > 10.0: break
        dt = ts[i + 3] - ts[i]
        if dt < 0.2 or dt > 1.5: continue
        for cid, v1 in cprojs[i].items():
            if cid in cprojs[i + 3]:
                if abs(hss[i] - v1[0]) > 75.0 or v1[0] > hss[i] + 30.0:
                    vel = (cprojs[i + 3][cid][0] - v1[0]) / dt
                    if 140.0 < vel < 460.0:
                        cvels.append(vel)
    p80_cv = pct(cvels, 80) if cvels else 0.0

    # 起步时刻
    wait_i = 0
    for i in range(len(ts)):
        if gaps[i] <= 650.0:
            wait_i = i; break
    t_walk, gap_walk = None, None
    for i in range(wait_i + 1, len(ts)):
        if hss[i] - hss[wait_i] > 25.0:
            t_walk, gap_walk = ts[i], gaps[i]; break

    # 卡兵段英雄速度、前距
    vhs_all, vhl_all, agaps, stop_n, act_n = [], [], [], 0, 0
    for i in range(len(ts) - 1):
        dt = ts[i + 1] - ts[i]
        if dt < 0.03 or dt > 0.5: continue
        if -15.0 <= gaps[i] <= 380.0:
            vhs = (hss[i + 1] - hss[i]) / dt
            vhl = (hls[i + 1] - hls[i]) / dt
            vhs_all.append(vhs); vhl_all.append(abs(vhl)); agaps.append(gaps[i])
            act_n += 1
            if math.hypot(vhs, vhl) < 35.0: stop_n += 1

    # 漏兵检测
    tower_s = K_AI_LANES[lane_key]["len"] - K_AI_LANES[lane_key]["spawn_along_rax"]
    esc = set()
    leaks = []
    for i in range(1, len(ts)):
        if hss[i] >= tower_s - 250.0: break
        ip = max(0, i - 3)
        dtw = max(0.05, ts[i] - ts[ip])
        vhs_now = (hss[i] - hss[ip]) / dtw
        vhl_now = (hls[i] - hls[ip]) / dtw
        for cid, (cs, cl, cx, cy) in cprojs[i].items():
            if cid in esc: continue
            if cs < tower_s - 250.0 and cs > hss[i] + 20.0:
                esc.add(cid)
                ipre = max(0, i - 5)
                behind_pre = [v for k_c, v in cprojs[ipre].items() if v[0] <= hss[ipre] + 20.0]
                if behind_pre:
                    behind_pre.sort(key=lambda x: x[0], reverse=True)
                    ls_pre = [v[1] for v in behind_pre if v[0] >= behind_pre[0][0] - 300.0]
                    row_ls = [v[1] for v in behind_pre if v[0] >= behind_pre[0][0] - 70.0]
                    wspan = max(ls_pre) - min(ls_pre) if len(ls_pre) >= 2 else 0.0
                    rspan = max(row_ls) - min(row_ls) if len(row_ls) >= 2 else 0.0
                    pre_gap = hss[ipre] - behind_pre[0][0]
                else:
                    wspan, rspan, pre_gap = 0.0, 0.0, hss[ipre] - cs
                leaks.append({
                    "cid": cid, "t": ts[i], "s": cs, "cl": cl, "hl": hls[i], "diff": cl - hls[i],
                    "pre_gap": pre_gap, "rspan": rspan, "wspan": wspan, "vhs": vhs_now, "vhl": vhl_now,
                })

    # 最后一帧英雄和最前兵到达的车道进度
    end_s = max(v[0] for v in cprojs[-1].values())
    return {
        "w": w, "hx0": hx0, "hy0": hy0, "hs0": hs0, "hl0": hl0, "fs0": fs0, "gap0": gap0,
        "p80_cv": p80_cv, "t_walk": t_walk, "gap_walk": gap_walk,
        "gap_p50": pct(agaps, 50), "gap_p10": pct(agaps, 10),
        "vhs_p50": pct(vhs_all, 50), "vhl_p50": pct(vhl_all, 50),
        "stop_pct": 100.0 * stop_n / max(1, act_n),
        "end_s": end_s, "leaks": leaks,
    }

def dump_file_section(out, title, fname):
    lane_key, waves, traces = load_csv(fname)
    out.append("\n" + "=" * 130)
    out.append(f"【{title}】 文件: {fname} (共 {len(waves)} 波)")
    out.append("=" * 130)
    out.append(f"{'次':>2} | {'波':>2} | {'分':>5} | {'漏/总':>5} | {'结束方式':<7} | {'拖延s':>5} | {'用时s':>5} | {'joinS':>5} | {'兵速P80':>6} | {'初始英雄(x,y)':<14} | {'hs0':>5} | {'hl0':>5} | {'gap0':>5} | {'起gap':>5} | {'前距50/10':<10} | {'v_hs':>5} | {'v_hl':>4} | {'终s':>5}")
    out.append("-" * 160)
    all_leaks = []
    for w in waves:
        info = inspect_wave(lane_key, w, traces.get(w["wave"], []))
        if not info: continue
        xy0 = f"({info['hx0']:.0f},{info['hy0']:.0f})"
        gw = f"{info['gap_walk']:.0f}" if info["gap_walk"] is not None else "-"
        gstr = f"{info['gap_p50']:.0f}/{info['gap_p10']:.0f}"
        out.append(
            f"{w['attempt']:>2} | {w['wave']:>2} | {w['score']:>5.1f} | {w.get('leak_cnt',0)}/{w.get('creep_cnt',4):<3} | "
            f"{w.get('end_type','?'):<7} | {w.get('delay_s',0):>5.1f} | {w['seconds']:>5.1f} | {w['joinSeconds']:>5.1f} | "
            f"{info['p80_cv']:>6.1f} | {xy0:<14} | {info['hs0']:>5.0f} | {info['hl0']:>+5.0f} | {info['gap0']:>5.0f} | "
            f"{gw:>5} | {gstr:<10} | {info['vhs_p50']:>5.0f} | {info['vhl_p50']:>4.0f} | {info['end_s']:>5.0f}"
        )
        for lk in info["leaks"]:
            lk["wave"] = w["wave"]
            lk["attempt"] = w["attempt"]
            all_leaks.append(lk)
    if all_leaks:
        out.append(f"\n  >> 漏兵明细 (共 {len(all_leaks)} 次):")
        for lk in all_leaks:
            out.append(
                f"     次{lk['attempt']} W{lk['wave']:02d} {lk['cid']} t={lk['t']:4.1f}s s={lk['s']:5.0f} | "
                f"cl={lk['cl']:+5.0f} hl={lk['hl']:+5.0f} (差={lk['diff']:+5.0f}) | "
                f"前0.5s前距={lk['pre_gap']:+4.0f} 排宽={lk['rspan']:3.0f} 波宽={lk['wspan']:3.0f} | "
                f"v_hs={lk['vhs']:+5.0f} v_hl={lk['vhl']:+4.0f}"
            )
        plus_n = sum(1 for x in all_leaks if x["diff"] >= 0)
        out.append(
            f"  >> 漏兵汇总: +侧={plus_n} ({100*plus_n/len(all_leaks):.0f}%), -侧={len(all_leaks)-plus_n} | "
            f"s中位={pct([x['s'] for x in all_leaks],50):.0f} | "
            f"前0.5s前距中位={pct([x['pre_gap'] for x in all_leaks],50):.0f} | "
            f"波宽中位={pct([x['wspan'] for x in all_leaks],50):.0f} | "
            f"漏时v_hs中位={pct([x['vhs'] for x in all_leaks],50):.0f}, |v_hl|中位={pct([abs(x['vhl']) for x in all_leaks],50):.0f}"
        )

def main():
    out = []
    # 1. 下路新参数常速期 (8波)
    dump_file_section(out, "一、近卫下路 新参数常速期 (avg 37)", "cm_bot_20261121-114223_8waves_pass2_avg37.csv")
    # 2. 上路新参数常速期 (8波)
    dump_file_section(out, "二、近卫上路 新参数常速期 (avg 51)", "cm_top_20261121-113623_8waves_pass1_avg51.csv")
    # 3. 上路减速期 5 次测试对比 (91 / 54 / 35 / 62 / 26)
    dump_file_section(out, "三A、近卫上路 减速期基准 (avg 91)", "cm_top_20261121-055720_4waves_pass3_avg91.csv")
    dump_file_section(out, "三B、近卫上路 102009 (avg 54)", "cm_top_20261121-102009_5waves_pass1_avg54.csv")
    dump_file_section(out, "三C、近卫上路 104450 (avg 35)", "cm_top_20261121-104450_5waves_pass0_avg35.csv")
    dump_file_section(out, "三D、近卫上路 105450 (avg 62)", "cm_top_20261121-105450_4waves_pass2_avg62.csv")
    dump_file_section(out, "三E、近卫上路 111403 (avg 26)", "cm_top_20261121-111403_10waves_pass0_avg26.csv")

    text = "\n".join(out)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_TXT}")

if __name__ == "__main__":
    main()
