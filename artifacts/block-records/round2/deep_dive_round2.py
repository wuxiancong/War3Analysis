# -*- coding: utf-8 -*-
r"""
第二轮卡兵记录深度逐帧诊断脚本 (deep_dive_round2.py)
重点排查：
1. 下路 114223 前3波(63/54/69) vs 后5波(17~29) 逐帧差异：
   - 兵速P80为何从325升到345~358？（检查前1000~2500未接触段自由巡航速度）
   - 英雄在 s=1500~4200 的停顿帧(v_hs<60)、急转/倒车帧(v_hs<0)、排宽>96触发频率
   - 漏兵前 1.5s 逐帧快照
2. 上路 113623 满分波 W19(100) vs 差波 W13/W15/W16/W18 逐帧差异
3. 上路减速期 055720(91) vs 102009(54) vs 104450(35) vs 105450(62) vs 111403(26) 逐帧差异：
   - 为什么 104450/111403 起步 gap 低至 120~225，且在 s=1000~1800 就大面积漏兵？
   - 检查 t=0..3s 英雄和兵的坐标（是否换了等兵位 / 提前被推 / 横向大摆动）
"""
import os
import math
from collections import defaultdict

DATA_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\data\cm"
OUT_TXT = r"D:\Qt\workspace\War3Analysis\artifacts\block-records\round2\round2_deep_dive.txt"

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

def load_csv(fname):
    path = os.path.join(DATA_DIR, fname)
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = [l.strip().lstrip("\ufeff").lstrip("ï»¿") for l in f if l.strip()]
    waves = {}
    traces = defaultdict(list)
    for line in lines:
        if line.startswith("#"):
            continue
        p = line.split(",")
        if p[0] == "wave":
            waves[int(p[2])] = {"seq": int(p[1]), "score": float(p[3]), "detail": ",".join(p[8:])}
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
    return waves, traces

def pct(vals, p):
    if not vals:
        return 0.0
    s = sorted(vals)
    idx = min(len(s) - 1, max(0, int(len(s) * p)))
    return s[idx]

def analyze_wave_kinematics(lane_key, frames):
    frames.sort(key=lambda x: x[0])
    # 计算未接触期(gap > 150)的自由兵速、接触期(s in [1500, 4200])英雄停顿/倒车/大横移/宽排(>96)占比
    free_c_spd = []
    free_c_spd_all = []
    contact_frames = 0
    stall_frames = 0      # v_hs < 60 且 gap < 180
    reverse_frames = 0    # v_hs < -10
    big_lat_frames = 0    # |v_hl| > 60
    wide_row_frames = 0   # row_span > 96
    wide_wave_frames = 0  # wave_span > 110
    hero_gap_min_before_leak = 9999.0
    first_leak_info = None
    first_leak_idx = None

    hs_list, hl_list, cproj = [], [], []
    for t, hx, hy, cdict in frames:
        hs, hl = proj_lane(lane_key, hx, hy)
        hs_list.append(hs)
        hl_list.append(hl)
        cp = {cid: proj_lane(lane_key, cx, cy) for cid, (cx, cy) in cdict.items()}
        cproj.append(cp)

    for i in range(1, len(frames)):
        dt = frames[i][0] - frames[i - 1][0]
        if dt <= 0.01 or dt > 0.5:
            continue
        v_hs = (hs_list[i] - hs_list[i - 1]) / dt
        v_hl = (hl_list[i] - hl_list[i - 1]) / dt
        active = [(cid, cs, cl) for cid, (cs, cl) in cproj[i].items() if cs <= hs_list[i] + 20.0]
        if active:
            front_s = max(x[1] for x in active)
            gap = hs_list[i] - front_s
            row = [x[2] for x in active if x[1] >= front_s - 70.0]
            r_span = (max(row) - min(row)) if len(row) >= 2 else 0.0
            w_span = max(x[2] for x in active) - min(x[2] for x in active)
            if first_leak_idx is None:
                if gap < hero_gap_min_before_leak:
                    hero_gap_min_before_leak = gap
            if gap < 220.0:
                contact_frames += 1
                if v_hs < 60.0:
                    stall_frames += 1
                if v_hs < -10.0:
                    reverse_frames += 1
                if abs(v_hl) > 60.0:
                    big_lat_frames += 1
                if r_span > 96.0:
                    wide_row_frames += 1
                if w_span > 110.0:
                    wide_wave_frames += 1
            if gap > 180.0:
                for cid, (cs, cl) in cproj[i].items():
                    if cid in cproj[i - 1]:
                        sp = math.hypot(cs - cproj[i - 1][cid][0], cl - cproj[i - 1][cid][1]) / dt
                        if 50.0 < sp < 500.0:
                            free_c_spd.append(sp)
        for cid, (cs, cl) in cproj[i].items():
            if cid in cproj[i - 1]:
                sp = math.hypot(cs - cproj[i - 1][cid][0], cl - cproj[i - 1][cid][1]) / dt
                if 50.0 < sp < 500.0:
                    free_c_spd_all.append(sp)
            if first_leak_idx is None and cs > hs_list[i] + 20.0 and hs_list[i] < K_AI_LANES[lane_key]["len"] - 550.0:
                first_leak_idx = i
                first_leak_info = (frames[i][0], cid, cs, cl, hs_list[i], hl_list[i])

    # 汇总
    cf = max(1, contact_frames)
    return {
        "free_spd_med": pct(free_c_spd, 0.5),
        "all_spd_p90": pct(free_c_spd_all, 0.9),
        "contact_n": contact_frames,
        "stall_pct": 100.0 * stall_frames / cf,
        "rev_n": reverse_frames,
        "big_lat_pct": 100.0 * big_lat_frames / cf,
        "wide_row_pct": 100.0 * wide_row_frames / cf,
        "wide_wave_pct": 100.0 * wide_wave_frames / cf,
        "first_leak_idx": first_leak_idx,
        "first_leak_info": first_leak_info,
        "hs_list": hs_list, "hl_list": hl_list, "cproj": cproj,
    }

def dump_window(out, title, frames, hs_list, hl_list, cproj, start_i, end_i):
    out.append(f"  [{title}]")
    out.append("    t    |   hs   hl  | v_hs v_hl | gap  | rowW wavW | front_cl  med_cl | 各兵 (id: s, l)")
    for i in range(max(0, start_i), min(len(frames), end_i + 1)):
        t = frames[i][0]
        hs, hl = hs_list[i], hl_list[i]
        if i > 0:
            dt = max(0.05, frames[i][0] - frames[i - 1][0])
            v_hs = (hs - hs_list[i - 1]) / dt
            v_hl = (hl - hl_list[i - 1]) / dt
        else:
            v_hs, v_hl = 0.0, 0.0
        active = sorted([(cid, cs, cl) for cid, (cs, cl) in cproj[i].items() if cs <= hs + 20.0], key=lambda x: -x[1])
        if active:
            fs, fl = active[0][1], active[0][2]
            gap = hs - fs
            row = [x[2] for x in active if x[1] >= fs - 70.0]
            rw = (max(row) - min(row)) if len(row) >= 2 else 0.0
            ww = max(x[2] for x in active) - min(x[2] for x in active)
            ls = sorted(x[2] for x in active)
            med = ls[len(ls)//2] if len(ls)%2==1 else 0.5*(ls[len(ls)//2-1]+ls[len(ls)//2])
        else:
            gap, rw, ww, fl, med = 0.0, 0.0, 0.0, 0.0, 0.0
        cstr = " ".join(f"{cid}:({cs:.0f},{cl:+.0f})" for cid, (cs, cl) in sorted(cproj[i].items(), key=lambda kv: -kv[1][0]))
        out.append(f"  {t:5.1f}s | {hs:5.0f} {hl:+4.0f} | {v_hs:+4.0f} {v_hl:+4.0f} | {gap:+4.0f} | {rw:4.0f} {ww:4.0f} | {fl:+7.0f} {med:+7.0f} | {cstr}")

def main():
    out = []
    # 1. 下路 114223
    out.append("=" * 120)
    out.append("【1. 近卫下路 114223：前3波 vs 后5波 运动学指标对比】")
    out.append("=" * 120)
    waves, traces = load_csv("cm_bot_20261121-114223_8waves_pass2_avg37.csv")
    out.append(f"{'次':>2} | {'波':>2} | {'分':>5} | {'自由兵速':>8} | {'P90兵速':>7} | {'接触帧':>6} | {'停顿%':>6} | {'倒车帧':>6} | {'大横移%':>7} | {'宽排>96%':>8} | {'宽波>110%':>9} | {'首漏s/t/c':<20}")
    out.append("-" * 120)
    bot_res = {}
    for w in sorted(waves.keys()):
        r = analyze_wave_kinematics("bot", traces[w])
        bot_res[w] = r
        lk = r["first_leak_info"]
        lk_s = f"s={lk[2]:.0f} t={lk[0]:.1f}s {lk[1]}" if lk else "无漏"
        out.append(f"{waves[w]['seq']:2d} | {w:2d} | {waves[w]['score']:5.1f} | {r['free_spd_med']:8.1f} | {r['all_spd_p90']:7.1f} | {r['contact_n']:6d} | {r['stall_pct']:5.1f}% | {r['rev_n']:6d} | {r['big_lat_pct']:6.1f}% | {r['wide_row_pct']:7.1f}% | {r['wide_wave_pct']:8.1f}% | {lk_s}")

    # 打印下路 W25(好波68.9) 在 s=2500~3800 与 W27(差波16.5)、W28(29.3)、W32(24.0) 首漏前 1.8s 快照
    for w, label in [(27, "下路差波 W27(16.5) 首漏前"), (28, "下路差波 W28(29.3) 首漏前"), (32, "下路差波 W32(24.0) 首漏前"), (30, "下路差波 W30(26.2) 首漏前")]:
        r = bot_res[w]
        if r["first_leak_idx"] is not None:
            idx = r["first_leak_idx"]
            dump_window(out, label, traces[w], r["hs_list"], r["hl_list"], r["cproj"], idx - 15, idx + 4)

    # 2. 上路常速期 113623
    out.append("\n" + "=" * 120)
    out.append("【2. 近卫上路 113623：满分波 W19(100) vs 其余 7 波 运动学指标对比】")
    out.append("=" * 120)
    waves, traces = load_csv("cm_top_20261121-113623_8waves_pass1_avg51.csv")
    out.append(f"{'次':>2} | {'波':>2} | {'分':>5} | {'自由兵速':>8} | {'P90兵速':>7} | {'接触帧':>6} | {'停顿%':>6} | {'倒车帧':>6} | {'大横移%':>7} | {'宽排>96%':>8} | {'宽波>110%':>9} | {'首漏s/t/c':<20}")
    out.append("-" * 120)
    top_res = {}
    for w in sorted(waves.keys()):
        r = analyze_wave_kinematics("top", traces[w])
        top_res[w] = r
        lk = r["first_leak_info"]
        lk_s = f"s={lk[2]:.0f} t={lk[0]:.1f}s {lk[1]}" if lk else "无漏"
        out.append(f"{waves[w]['seq']:2d} | {w:2d} | {waves[w]['score']:5.1f} | {r['free_spd_med']:8.1f} | {r['all_spd_p90']:7.1f} | {r['contact_n']:6d} | {r['stall_pct']:5.1f}% | {r['rev_n']:6d} | {r['big_lat_pct']:6.1f}% | {r['wide_row_pct']:7.1f}% | {r['wide_wave_pct']:8.1f}% | {lk_s}")

    for w, label in [(13, "上路差波 W13(35.6) 首漏前"), (16, "上路差波 W16(33.0) 首漏前"), (18, "上路差波 W18(29.2) 首漏前")]:
        r = top_res[w]
        if r["first_leak_idx"] is not None:
            idx = r["first_leak_idx"]
            dump_window(out, label, traces[w], r["hs_list"], r["hl_list"], r["cproj"], idx - 15, idx + 4)

    # 3. 上路减速期 5 场对比：为什么 111403 和 104450 在 s=1000~1800 就大崩盘？
    out.append("\n" + "=" * 120)
    out.append("【3. 近卫上路减速期 5 场对比：055720(91) vs 102009(54) vs 104450(35) vs 105450(62) vs 111403(26)】")
    out.append("=" * 120)
    slow_files = [
        ("055720(91)", "cm_top_20261121-055720_4waves_pass3_avg91.csv"),
        ("102009(54)", "cm_top_20261121-102009_5waves_pass1_avg54.csv"),
        ("104450(35)", "cm_top_20261121-104450_5waves_pass0_avg35.csv"),
        ("105450(62)", "cm_top_20261121-105450_4waves_pass2_avg62.csv"),
        ("111403(26)", "cm_top_20261121-111403_10waves_pass0_avg26.csv"),
    ]
    out.append(f"{'场次':<11} | {'波数':>4} | {'自由兵速':>8} | {'接触停顿%':>9} | {'倒车总帧':>8} | {'大横移%':>7} | {'宽排>96%':>8} | {'宽波>110%':>9}")
    out.append("-" * 95)
    for tag, fn in slow_files:
        ws, trs = load_csv(fn)
        fspds, stalls, revs, blats, wrows, wwavs = [], [], [], [], [], []
        for w in sorted(ws.keys()):
            r = analyze_wave_kinematics("top", trs[w])
            fspds.append(r["free_spd_med"])
            stalls.append(r["stall_pct"])
            revs.append(r["rev_n"])
            blats.append(r["big_lat_pct"])
            wrows.append(r["wide_row_pct"])
            wwavs.append(r["wide_wave_pct"])
        out.append(
            f"{tag:<11} | {len(ws):4d} | {sum(fspds)/len(fspds):8.1f} | {sum(stalls)/len(stalls):8.1f}% | "
            f"{sum(revs):8d} | {sum(blats)/len(blats):6.1f}% | {sum(wrows)/len(wrows):7.1f}% | {sum(wwavs)/len(wwavs):8.1f}%"
        )

    # 逐帧对比 055720 W06(100) vs 105450 W01(75) vs 111403 W03(16.3) 和 W06(18.1) 的前 7 秒！
    for fn, w, label in [
        ("cm_top_20261121-055720_4waves_pass3_avg91.csv", 6, "055720 W06(100分) 前7s (t=0..7s)"),
        ("cm_top_20261121-111403_10waves_pass0_avg26.csv", 3, "111403 W03(16.3分) 全程 (t=0..6.6s)"),
        ("cm_top_20261121-111403_10waves_pass0_avg26.csv", 6, "111403 W06(18.1分) 全程 (t=0..7.1s)"),
        ("cm_top_20261121-104450_5waves_pass0_avg35.csv", 3, "104450 W03(35.2分) t=4.5..8.5s"),
    ]:
        ws, trs = load_csv(fn)
        r = analyze_wave_kinematics("top", trs[w])
        if "t=4.5" in label:
            dump_window(out, label, trs[w], r["hs_list"], r["hl_list"], r["cproj"], 45, 85)
        else:
            dump_window(out, label, trs[w], r["hs_list"], r["hl_list"], r["cproj"], 0, 72)

    text = "\n".join(out)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote {len(text)} chars to {OUT_TXT}")

if __name__ == "__main__":
    main()
