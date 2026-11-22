# -*- coding: utf-8 -*-
r"""
批量解析本地 .w3g 录像，生成：
1. replay_corpus_stats.txt：全部本地录像的统计摘要（动作分布、APM、每类操作占比、0x6B 事件、英雄识别）；
2. sample_dataset.jsonl：符合 imitation_dataset_schema.json 的 0.5s 步长模仿学习示例数据集（纯 w3g 动作近似路线）；
3. sample_parsed_replay.json：单场代表录像的完整结构化解析样本（供查阅与调试）。
"""
import os
import glob
import json
from collections import Counter, defaultdict
from w3g_parser import parse_w3g, APM_ACTION_IDS

DATA_DIR = r"D:\Qt\workspace\War3Analysis\artifacts\replay-dataset\data"
OUT_STATS = r"D:\Qt\workspace\War3Analysis\artifacts\replay-dataset\replay_corpus_stats.txt"
OUT_JSONL = r"D:\Qt\workspace\War3Analysis\artifacts\replay-dataset\sample_dataset.jsonl"
OUT_SAMPLE_JSON = r"D:\Qt\workspace\War3Analysis\artifacts\replay-dataset\sample_parsed_replay.json"

def map_action_category(a):
    aid = a["aid_int"]
    okind = a.get("order_kind", "")
    oid = a.get("order_id", "")
    if aid == 0x10:
        if okind == "skill_learn": return "learn_skill"
        if okind in ("shop_or_unit", "hero_pick"): return "buy_item"
        if oid in ("0x000D0004", "0x000D0019"): return "stop_hold"
        if oid in ("0x000D0028", "0x000D0029", "0x000D002A", "0x000D002B", "0x000D002C", "0x000D002D"): return "use_item"
        return "cast_immediate"
    if aid == 0x11:
        if oid in ("0x000D0003", "0x000D0012", "0x000D0016"): return "move"
        if oid in ("0x000D000F", "0x000D0010"): return "attack_ground"
        if oid in ("0x000D0028", "0x000D0029", "0x000D002A", "0x000D002B", "0x000D002C", "0x000D002D"): return "use_item"
        return "cast_point"
    if aid == 0x12:
        t1 = a.get("target_obj1", "0xFFFFFFFF")
        is_ground = (t1 == "0xFFFFFFFF")
        if oid in ("0x000D0003", "0x000D0012", "0x000D0016"):
            return "move" if is_ground else "attack_unit"
        if oid == "0x000D000F":
            return "attack_ground" if is_ground else "attack_unit"
        if oid in ("0x000D0028", "0x000D0029", "0x000D002A", "0x000D002B", "0x000D002C", "0x000D002D"):
            return "use_item"
        return "cast_point" if is_ground else "cast_unit"
    if aid == 0x13:
        return "use_item"
    if aid == 0x14:
        return "cast_point"
    if aid in (0x16, 0x17, 0x18, 0x19, 0x1B, 0x1C, 0x66):
        return "select_or_group"
    if aid in (0x60, 0x68):
        return "ping_or_chat"
    return "noop"

# 动作优先级（当 0.5s 窗口内有多个动作时，选择最具战术代表性的主操作作为标签）
CAT_PRIORITY = {
    "cast_unit": 10, "cast_point": 10, "cast_immediate": 9,
    "use_item": 8, "learn_skill": 8, "buy_item": 7,
    "attack_unit": 6, "attack_ground": 5, "stop_hold": 4,
    "move": 3, "ping_or_chat": 2, "select_or_group": 1, "noop": 0,
}

def build_jsonl_samples(parsed, step_ms=500, max_steps_per_player=600):
    """将单场解析结果按 0.5s 网格切成模仿学习样本 (state -> action)"""
    match_id = parsed["header"]["file"]
    patch = parsed["header"]["patch_version"]
    dur_ms = parsed["parsed_duration_ms"]
    players = parsed["meta"]["players"]

    actions_by_pid = defaultdict(list)
    for a in parsed["actions"]:
        actions_by_pid[a["pid"]].append(a)

    # 整理 0x6B 升级/补刀事件
    ev_by_t = sorted(parsed["events"], key=lambda e: e["t_ms"])

    samples = []
    for pid, pinfo in players.items():
        p_acts = actions_by_pid.get(pid, [])
        if len(p_acts) < 10:
            continue
        # 按 500ms 桶分箱
        buckets = defaultdict(list)
        for a in p_acts:
            b = (a["t_ms"] // step_ms) * step_ms
            buckets[b].append(a)

        approx_x, approx_y = None, None
        pos_conf = 0.0
        hero_lvl = 1
        lh, dn, kills, deaths = 0, 0, 0, 0
        learned = []
        recent_cats = []
        last_sel = []

        ev_idx = 0
        n_steps = min(max_steps_per_player, int(dur_ms // step_ms) + 1)
        for s_idx in range(n_steps):
            t_cur = s_idx * step_ms
            # 推进到 t_cur 的 0x6B 事件
            while ev_idx < len(ev_by_t) and ev_by_t[ev_idx]["t_ms"] <= t_cur:
                ev = ev_by_t[ev_idx]
                ev_idx += 1
                if ev.get("source") == "0x6B":
                    k = ev.get("key", "")
                    if k.startswith("Level") and ev.get("val") == pid:
                        try:
                            hero_lvl = max(hero_lvl, int(k[5:]))
                        except ValueError:
                            pass
                    elif k.startswith("CSK") and ev.get("val") == pid:
                        lh += 1
                    elif k.startswith("CSD") and ev.get("val") == pid:
                        dn += 1

            # 本 0.5s 窗口内的动作
            w_acts = buckets.get(t_cur, [])
            best_act = None
            best_cat = "noop"
            best_pri = -1
            for a in w_acts:
                c = map_action_category(a)
                if c == "learn_skill":
                    learned.append(a.get("order_name", ""))
                if a.get("selected"):
                    last_sel = a["selected"]
                if CAT_PRIORITY[c] > best_pri:
                    best_pri = CAT_PRIORITY[c]
                    best_cat = c
                    best_act = a

            # 估算英雄位置（仅用动作目标坐标的指数滑动近似，标注低置信度 0.35）
            if best_act and "x" in best_act and "y" in best_act:
                tx, ty = best_act["x"], best_act["y"]
                if abs(tx) < 8500 and abs(ty) < 8500:
                    if approx_x is None:
                        approx_x, approx_y = tx, ty
                    else:
                        approx_x = 0.7 * approx_x + 0.3 * tx
                        approx_y = 0.7 * approx_y + 0.3 * ty
                    pos_conf = 0.35

            if t_cur < 105000:
                phase = "pre_horn"
            elif t_cur < 600000:
                phase = "laning_0_10m"
            elif t_cur < 1500000:
                phase = "mid_10_25m"
            else:
                phase = "late_25m_plus"

            sample = {
                "schema_version": "1.0",
                "match_id": match_id,
                "patch": patch,
                "t_ms": t_cur,
                "pid": pid,
                "team": pinfo.get("team", 0),
                "hero": pinfo.get("hero_code", "") or "Unknown",
                "state_source": "w3g_action_proxy",
                "state": {
                    "game_phase": phase,
                    "hero_pos": {
                        "x": round(approx_x, 1) if approx_x is not None else None,
                        "y": round(approx_y, 1) if approx_y is not None else None,
                        "confidence": pos_conf,
                    },
                    "hero_level": hero_lvl,
                    "hp_ratio": None,
                    "mp_ratio": None,
                    "gold_reliable": None,
                    "gold_unreliable": None,
                    "last_hits": lh,
                    "denies": dn,
                    "kills": kills,
                    "deaths": deaths,
                    "learned_skills": list(learned),
                    "inventory_slots": [None] * 6,
                    "selected_units": list(last_sel[:4]),
                    "nearby_units": [],
                    "recent_action_hist": list(recent_cats[-5:]),
                },
                "action": {
                    "category": best_cat,
                    "order_id": best_act.get("order_id") if best_act else None,
                    "order_name": best_act.get("order_name") if best_act else None,
                    "target_x": best_act.get("x") if best_act else None,
                    "target_y": best_act.get("y") if best_act else None,
                    "target_obj1": best_act.get("target_obj1") if best_act else None,
                    "action_count_in_window": len(w_acts),
                },
            }
            samples.append(sample)
            if best_cat != "noop":
                recent_cats.append(best_cat)

    return samples

def main():
    w3g_files = sorted(glob.glob(os.path.join(DATA_DIR, "*.w3g")))
    out = []
    out.append(f"共扫描本地录像副本: {len(w3g_files)} 场 (目录: {DATA_DIR})")
    out.append("=" * 115)

    total_actions = 0
    total_events_6b = 0
    total_chats = 0
    aid_counter = Counter()
    cat_counter = Counter()
    order_counter = Counter()
    ev6b_key_counter = Counter()
    all_apms = []
    jsonl_samples = []
    saved_sample_json = False

    out.append(f"{'录像文件名':<46} | {'版本':<5} | {'时长s':>6} | {'玩家与英雄':<32} | {'总动作':>6} | {'APM':>6} | {'0x6B数':>6} | {'聊天数':>5}")
    out.append("-" * 135)

    for idx, path in enumerate(w3g_files):
        try:
            res = parse_w3g(path)
        except Exception as e:
            out.append(f"{os.path.basename(path):<46} | PARSE ERROR: {e}")
            continue

        dur_s = res["parsed_duration_ms"] / 1000.0
        n_acts = len(res["actions"])
        n_6b = sum(1 for e in res["events"] if e.get("source") == "0x6B")
        n_chat = len(res["chats"])
        total_actions += n_acts
        total_events_6b += n_6b
        total_chats += n_chat

        p_strs = []
        max_apm = 0.0
        for pid, p in res["meta"]["players"].items():
            if p["apm_actions"] > 0:
                p_strs.append(f"{p['name']}({p['hero_code'] or '?'})")
                all_apms.append(p["apm"])
                max_apm = max(max_apm, p["apm"])
        p_summary = ", ".join(p_strs)[:32]

        out.append(
            f"{res['header']['file']:<46} | {res['header']['patch_version']:<5} | {dur_s:>6.1f} | "
            f"{p_summary:<32} | {n_acts:>6} | {max_apm:>6.1f} | {n_6b:>6} | {n_chat:>5}"
        )

        for a in res["actions"]:
            aid_counter[a["aid"]] += 1
            cat_counter[map_action_category(a)] += 1
            if "order_name" in a:
                order_counter[f"{a['order_id']} {a['order_name']}"] += 1

        for e in res["events"]:
            if e.get("source") == "0x6B":
                ev6b_key_counter[f"{e['mkey']}:{e['key']}"] += 1

        # 对前 3 场最丰富的录像生成示例 JSONL（并保存第 1 场完整 JSON）
        if not saved_sample_json and n_acts > 500:
            with open(OUT_SAMPLE_JSON, "w", encoding="utf-8") as fj:
                json.dump({
                    "header": res["header"],
                    "meta": res["meta"],
                    "parsed_duration_ms": res["parsed_duration_ms"],
                    "sample_actions_first_50": res["actions"][:50],
                    "sample_events_first_50": res["events"][:50],
                    "chats": res["chats"][:30],
                }, fj, ensure_ascii=False, indent=2)
            saved_sample_json = True

        if len(jsonl_samples) < 3000:
            jsonl_samples.extend(build_jsonl_samples(res, step_ms=500, max_steps_per_player=1000))

    # 写 JSONL 示例数据集
    with open(OUT_JSONL, "w", encoding="utf-8") as fjl:
        for s in jsonl_samples:
            fjl.write(json.dumps(s, ensure_ascii=False) + "\n")

    out.append("\n" + "=" * 115)
    out.append(f"【汇总统计】总动作={total_actions} | 总 0x6B 事件={total_events_6b} | 总聊天={total_chats} | 生成 JSONL 样本={len(jsonl_samples)} 条")
    if all_apms:
        s_apm = sorted(all_apms)
        out.append(f"活跃玩家 APM 分布 (n={len(s_apm)}): 最小={s_apm[0]:.1f}, 中位={s_apm[len(s_apm)//2]:.1f}, 均值={sum(s_apm)/len(s_apm):.1f}, 最大={s_apm[-1]:.1f}")

    out.append("\n--- 1. 按底层 Action ID 分布 ---")
    for k, v in aid_counter.most_common():
        out.append(f"  {k:<8}: {v:>7} ({100.0 * v / max(1, total_actions):5.2f}%)")

    out.append("\n--- 2. 按模仿学习高层操作类别 (action.category) 分布 ---")
    for k, v in cat_counter.most_common():
        out.append(f"  {k:<18}: {v:>7} ({100.0 * v / max(1, total_actions):5.2f}%)")

    out.append("\n--- 3. Top 20 高频 OrderId / FourCC ---")
    for k, v in order_counter.most_common(20):
        out.append(f"  {k:<55}: {v:>7}")

    out.append("\n--- 4. Top 20 高频 0x6B GameCache 事件 ---")
    for k, v in ev6b_key_counter.most_common(20):
        out.append(f"  {k:<35}: {v:>7}")

    text = "\n".join(out)
    with open(OUT_STATS, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Wrote stats ({len(text)} chars) to {OUT_STATS} and {len(jsonl_samples)} samples to {OUT_JSONL}")

if __name__ == "__main__":
    main()
