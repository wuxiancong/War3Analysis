# -*- coding: utf-8 -*-
"""
用复制出来的 7 份 SF 实测 CSV 做补刀预测模型定量验证与偏差归因（第 5 项）：
1. 量真实飞行时间 vs 两种公式：
   - 旧公式: centerDist / 1200
   - 修正公式: max(0, centerDist - launchY_100) / 1200  (Nfir launchY=100, 碰撞半径/命中半径)
2. 统计所有 7 局的漏刀分类（early / late / window0 / cd / idle / far），
   重点拆解每一刀「early」的：
   - 实际落地时刻兵剩余血量 vs 英雄最低伤害
   - 落地前 1.0 秒内这只兵的实际掉血速率 (HP/s) 与实际受到的攻击次数（识别「低掉血却被高估」案例！）
   - 落地时刻到小兵实际死亡的时间差（量化到底早了多少秒！）
3. 检查游戏速度（从 trace 帧内英雄前摇 wu 倒计时速率 vs trace 墙钟间隔 dt，直接反推每局真实游戏速度倍率！）
"""
import glob, math, os, statistics, sys
sys.path.insert(0, r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-combat")
import lh_miss_classify as L

REC_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\records"
OUT = r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-prediction\sf_csv_validation.txt"


def estimate_game_speed(traces):
    """用连续两帧 trace 之间 wu (游戏秒) 的减少量 / wall_dt (墙钟秒) 反推真实游戏速度倍率"""
    ratios = []
    for i in range(len(traces) - 1):
        a, b = traces[i], traces[i + 1]
        dt = b["t"] - a["t"]
        if 0.05 <= dt <= 0.25 and a["wu"] > 0.15 and b["wu"] > 0.02 and a["tgt"] == b["tgt"]:
            dw = a["wu"] - b["wu"]
            if 0.01 < dw < 0.30:
                ratios.append(dw / dt)
    return statistics.median(ratios) if ratios else 1.0


def analyze_all():
    csvs = sorted(glob.glob(os.path.join(REC_DIR, "*.csv")))
    lines = []
    def log(s=""):
        lines.append(s)

    all_early_details = []
    all_flight_old = []
    all_flight_new = []
    all_flight_game_old = []
    all_flight_game_new = []

    log(f"=== 共分析 {len(csvs)} 份 SF 实测 CSV ===")
    for p in csvs:
        name = os.path.basename(p)
        head, events, traces = L.load(p)
        L.HEAD.clear()
        L.HEAD.update(head)
        rng = float(head.get("range", 500))
        ms = float(head.get("missileSpeed", 1200)) or 1200.0
        gspd = estimate_game_speed(traces)

        # 1. 飞行时间测量（同时算墙钟与换算游戏秒！）
        f_old, f_new, fg_old, fg_new = [], [], [], []
        for e in events:
            if e["res"] != "hit":
                continue
            obj = L.match(e, traces)
            if not obj:
                continue
            rel = [tr for tr in traces if e["t"] - 4 <= tr["t"] <= e["t"] + 0.3]
            fire = None
            for i, tr in enumerate(rel):
                if tr["tgt"] == obj and tr["wu"] > 0.01:
                    nxt = rel[i + 1] if i + 1 < len(rel) else None
                    if nxt is None or nxt["wu"] <= 0.01 or nxt["tgt"] != obj:
                        u = tr["units"].get(obj)
                        if u:
                            # 注意：tr["t"] 是墙钟，tr["wu"] 是游戏秒，离手墙钟 = tr["t"] + tr["wu"] / gspd
                            d = math.hypot(u[3] - tr["hx"], u[4] - tr["hy"])
                            fire = (tr["t"] + tr["wu"] / gspd, tr["t"] + tr["wu"], d)
            if not fire:
                continue
            alive = [tr["t"] for tr in rel if obj in tr["units"] and tr["units"][obj][2] > 0.5]
            if not alive:
                continue
            death_wall = max(alive) + 0.05
            # 真实飞行游戏秒 = (death_wall - fire_wall) * gspd
            meas_game = (death_wall - fire[0]) * gspd
            meas_raw = death_wall - fire[1]
            est_old = fire[2] / ms
            est_new = max(0.0, fire[2] - 100.0) / ms  # Nfir launchY = 100
            f_old.append(meas_raw - est_old)
            f_new.append(meas_raw - est_new)
            fg_old.append(meas_game - est_old)
            fg_new.append(meas_game - est_new)
            all_flight_old.append(meas_raw - est_old)
            all_flight_new.append(meas_raw - est_new)
            all_flight_game_old.append(meas_game - est_old)
            all_flight_game_new.append(meas_game - est_new)

        # 2. 统计 miss 分类并细查 early 刀
        counts = {}
        for e in events:
            if e["res"] == "hit":
                continue
            obj = L.match(e, traces)
            cls, info = L.classify(e, obj, traces, rng) if obj else ("nomatch", "")
            key = f"{e['kind']}:{cls}"
            counts[key] = counts.get(key, 0) + 1
            if cls == "early" and obj:
                hist = [tr for tr in traces if e["t"] - 4 <= tr["t"] <= e["t"] + 0.2 and obj in tr["units"]]
                # 找离手时刻与落地时刻
                rel = [tr for tr in traces if e["t"] - 4 <= tr["t"] <= e["t"] + 0.3]
                fire_t, d_shot = None, 300.0
                for i, tr in enumerate(rel):
                    if tr["tgt"] == obj and tr["wu"] > 0.01:
                        nxt = rel[i + 1] if i + 1 < len(rel) else None
                        if nxt is None or nxt["wu"] <= 0.01 or nxt["tgt"] != obj:
                            u = tr["units"].get(obj)
                            d_shot = math.hypot(u[3] - tr["hx"], u[4] - tr["hy"]) if u else 300.0
                            fire_t = tr["t"] + tr["wu"] / gspd
                if fire_t is not None and hist:
                    imp_t = fire_t + (max(0.0, d_shot - 100.0) / ms) / gspd
                    death_t = hist[-1]["t"] + 0.05
                    # 计算落地前 1.0s 内的实际掉血率
                    pre = [tr for tr in hist if imp_t - 1.0 <= tr["t"] <= imp_t]
                    hp_drop = (pre[0]["units"][obj][2] - pre[-1]["units"][obj][2]) if len(pre) >= 2 else 0.0
                    dt_pre = (pre[-1]["t"] - pre[0]["t"]) if len(pre) >= 2 else 1.0
                    dps = hp_drop / max(0.1, dt_pre)
                    hp_at_imp = pre[-1]["units"][obj][2] if pre else hist[-1]["units"][obj][2]
                    dmg = hist[-1]["dmg"]
                    all_early_details.append({
                        "file": name[:28],
                        "kind": e["kind"],
                        "early_wall_s": death_t - imp_t,
                        "early_game_s": (death_t - imp_t) * gspd,
                        "hp_at_imp": hp_at_imp,
                        "dmg": dmg,
                        "ratio": hp_at_imp / max(1.0, dmg),
                        "dps_1s": dps,
                        "gspd": gspd,
                    })

        log(f"\n[{name}] est_game_speed={gspd:.2f}x | n_flight={len(fg_old)}")
        if fg_old:
            log(f"  飞行误差 (游戏秒口径): 旧(center/1200) median={statistics.median(fg_old):+.3f}s | 新((center-100)/1200) median={statistics.median(fg_new):+.3f}s")
        log(f"  miss 分布: {dict(sorted(counts.items()))}")

    log("\n=== 全 7 局汇总 ===")
    if all_flight_game_old:
        log(f"  总有效补刀飞行样本 n={len(all_flight_game_old)}:")
        log(f"    旧公式 (dist/1200, 游戏秒口径):       median={statistics.median(all_flight_game_old):+.3f}s, mean={statistics.mean(all_flight_game_old):+.3f}s")
        log(f"    新公式 ((dist-100)/1200, 游戏秒口径): median={statistics.median(all_flight_game_new):+.3f}s, mean={statistics.mean(all_flight_game_new):+.3f}s")

    log(f"\n=== 全 7 局 'early' 漏刀深度拆解 (共 {len(all_early_details)} 刀) ===")
    if all_early_details:
        early_gs = [x["early_game_s"] for x in all_early_details]
        ratios = [x["ratio"] for x in all_early_details]
        low_dps = [x for x in all_early_details if x["dps_1s"] < 25.0]
        high_rem = [x for x in all_early_details if x["ratio"] >= 1.5]
        close_01 = [x for x in all_early_details if abs(x["early_game_s"]) <= 0.15]
        log(f"  早了多少游戏秒: median={statistics.median(early_gs):.2f}s, mean={statistics.mean(early_gs):.2f}s, max={max(early_gs):.2f}s")
        log(f"  落地剩余血/伤害比: median={statistics.median(ratios):.2f}x, >=1.5x 占比={len(high_rem)}/{len(all_early_details)} ({100*len(high_rem)/len(all_early_details):.0f}%)")
        log(f"  落地前 1s 实际掉血 < 25 HP/s 的刀数: {len(low_dps)}/{len(all_early_details)} ({100*len(low_dps)/len(all_early_details):.0f}%)")
        log(f"  落地与死亡差 <= 0.15 游戏秒（擦边抢输）: {len(close_01)}/{len(all_early_details)}")
        log("  --- 典型样本 (前 15 刀) ---")
        for x in all_early_details[:15]:
            log(f"    {x['file']} {x['kind']} | 早={x['early_game_s']:.2f}gs (墙{x['early_wall_s']:.2f}s) | 落地血={x['hp_at_imp']:.0f} (dmg={x['dmg']:.0f}, {x['ratio']:.2f}x) | 前1s实际DPS={x['dps_1s']:.1f}/s | 速={x['gspd']:.2f}x")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    analyze_all()
