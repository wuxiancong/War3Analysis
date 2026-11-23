# -*- coding: utf-8 -*-
"""Build DotA 6.83d all-hero control-threat table for key-target scoring."""
from __future__ import annotations

import json
import os
import re
from collections import OrderedDict

ROOT = os.path.dirname(os.path.abspath(__file__))
SKILLS_PATH = os.path.join(ROOT, "..", "ability-orders", "dota_hero_skills.json")
DATA_PATH = r"D:\Qt\workspace\War3Bot\images\dota_data.json"
OUT_JSON = os.path.join(ROOT, "hero_control_threat_683d.json")
OUT_MD = os.path.join(ROOT, "hero_control_threat_683d.md")

# Keyword -> (tier, base_weight). First match wins (order matters).
NAME_RULES = [
    (r"时间结界|Chronosphere", "TEAM_ULT", 1.00),
    (r"黑洞|Black Hole", "TEAM_ULT", 1.00),
    (r"毁灭$|Ravage", "TEAM_ULT", 1.00),
    (r"两极反转|Reverse Polarity", "TEAM_ULT", 1.00),
    (r"回音击|Echo Slam", "TEAM_ULT", 1.00),
    (r"海妖之歌", "TEAM_ULT", 1.00),
    (r"全领域静默|全局沉默|Global Silence", "TEAM_ULT", 0.95),
    (r"过度生长", "TEAM_ULT", 0.90),
    (r"原始咆哮", "TEAM_ULT", 0.95),
    (r"梦境缠绕", "TEAM_ULT", 0.95),
    (r"静态风暴", "TEAM_ULT", 0.95),
    (r"幽灵船", "TEAM_ULT", 0.90),
    (r"决斗", "TEAM_ULT", 0.95),
    (r"寒冬诅咒", "TEAM_ULT", 0.95),
    (r"超新星", "TEAM_ULT", 0.95),
    (r"海象神拳", "TEAM_ULT", 0.90),
    (r"发射钩爪|钩爪发射", "TEAM_ULT", 0.95),
    (r"元素分离", "TEAM_ULT", 0.85),
    (r"奔袭冲撞|Stampede", "TEAM_ULT", 0.80),
    (r"群蛇守卫", "TEAM_ULT", 0.75),
    (r"极寒领域|Freezing Field", "TEAM_ULT", 1.00),
    (r"裂地者|裂地沟壑|大地分裂", "TEAM_ULT", 0.80),
    (r"磁化", "TEAM_ULT", 0.85),
    (r"末日|Doom", "TEAM_ULT", 0.95),
    (r"恶魔的掌握|恶魔掌控|Fiend", "TEAM_ULT", 0.95),
    (r"守护天使", "TEAM_ULT", 0.70),
    (r"上帝之手", "SOFT_CC", 0.55),
    (r"再装填", "SOFT_CC", 0.60),
    (r"雷神之怒", "NUKE_ULT", 0.55),
    (r"神灭斩", "NUKE_ULT", 0.75),
    (r"无敌斩", "NUKE_ULT", 0.80),
    (r"暗杀", "NUKE_ULT", 0.70),
    (r"月蚀", "NUKE_ULT", 0.75),
    (r"自然之怒", "NUKE_ULT", 0.70),
    (r"法力虚空", "NUKE_ULT", 0.80),
    (r"生命突破", "NUKE_ULT", 0.75),
    (r"集中火力", "NUKE_ULT", 0.70),
    (r"召唤飞弹|呼叫飞弹", "NUKE_ULT", 0.75),
    (r"绝杀秘技", "NUKE_ULT", 0.70),
    (r"激怒", "NUKE_ULT", 0.65),
    (r"妖术|^Hex$|变羊", "HARD_CC", 0.90),
    (r"魔法箭", "HARD_CC", 0.70),
    (r"灵魂隔断", "HARD_CC", 0.85),
    (r"冰封禁制|霜冻禁锢", "HARD_CC", 0.75),
    (r"诱捕|Ensnare|渔网|地之束缚|土之环", "HARD_CC", 0.70),
    (r"沟壑|Fissure", "HARD_CC", 0.85),
    (r"光击阵", "HARD_CC", 0.80),
    (r"火焰爆轰", "HARD_CC", 0.75),
    (r"枷锁|束缚击|暗影枷锁", "HARD_CC", 0.85),
    (r"苍穹震击", "HARD_CC", 0.70),
    (r"山崩|Avalanche", "HARD_CC", 0.85),
    (r"^投掷$|Toss$", "HARD_CC", 0.75),
    (r"马蹄践踏|践踏|回音重踏|雷霆一击", "HARD_CC", 0.80),
    (r"神龙摆尾", "HARD_CC", 0.75),
    (r"不稳定化合物", "HARD_CC", 0.70),
    (r"月神之箭", "HARD_CC", 0.90),
    (r"新月之痕", "HARD_CC", 0.75),
    (r"能量齿轮|电池特攻|弹幕冲击", "HARD_CC", 0.70),
    (r"洪流|Torrent", "HARD_CC", 0.80),
    (r"冰封路径", "HARD_CC", 0.80),
    (r"动能力场", "HARD_CC", 0.70),
    (r"雪球", "HARD_CC", 0.80),
    (r"炎阳锁链|燃烬锁链", "HARD_CC", 0.75),
    (r"巨石翻滚", "HARD_CC", 0.70),
    (r"穿刺|地刺|Impale", "HARD_CC", 0.80),
    (r"肉钩|钩子", "HARD_CC", 0.90),
    (r"肢解", "HARD_CC", 0.85),
    (r"星体禁锢", "HARD_CC", 0.75),
    (r"真空", "HARD_CC", 0.80),
    (r"隔空取物|心灵传输", "HARD_CC", 0.75),
    (r"发芽", "HARD_CC", 0.55),
    (r"裂地猛击|裂地猛击", "HARD_CC", 0.75),
    (r"冲锋|冲撞|长大冲撞", "HARD_CC", 0.70),
    (r"掘地穿刺|掘地猛击", "HARD_CC", 0.75),
    (r"^冲击波$|Skewer|长大冲撞", "HARD_CC", 0.75),
    (r"风暴之锤|风暴之锤", "HARD_CC", 0.70),
    (r"雷霆一击", "HARD_CC", 0.70),
    (r"震荡波", "SOFT_CC", 0.35),
    (r"沉默|寂静|邪能禁锢|最后一言|伤残恐惧|烟雾屏|阵风", "SOFT_CC", 0.60),
    (r"奥术诅咒", "SOFT_CC", 0.40),
    (r"冰霜新星|霜冻新星|寒霜诅咒", "SOFT_CC", 0.35),
    (r"恐怖波动", "SOFT_CC", 0.35),
    (r"剑刃风暴", "SOFT_CC", 0.50),
    (r"闪烁|Blink|残影|暗影步|风力前行|波浪形态|球状闪电", "INIT", 0.45),
    (r"时间行走", "INIT", 0.50),
    (r"重置|迁跃", "INIT", 0.55),
]

# Explicit overrides for ambiguous / wrong keyword hits: (hero, ability) -> (tier, weight, note)
# None tier = drop from control table
OVERRIDES = {
    ("Nfir", "A29J"): ("NUKE_ULT", 0.90, "Requiem of Souls — distance-scaled teamfight nuke"),
    ("Nfir", "A0EY"): ("NUKE", 0.35, "Shadowraze near"),
    # false positives
    ("E01A", "A0NE"): (None, 0.0, "Voodoo Restoration heal aura — not Hex"),
    ("Naka", "A004"): ("SOFT_CC", 0.35, "Shuriken Toss nuke/slow — not Tiny Toss"),
    ("UC01", "A306"): ("NUKE_ULT", 0.75, "Sonic Wave nuke — not Skewer"),
    ("H008", "A0FW"): ("SOFT_CC", 0.30, "Viscous Nasal Goo armor/slow"),
    ("H008", "A0GP"): ("NUKE", 0.40, "Quill Spray"),
    ("H008", "A0FV"): ("SOFT_CC", 0.45, "Warpath passive ult"),
}


def classify_name(name: str):
    for pat, tier, weight in NAME_RULES:
        if re.search(pat, name, flags=re.IGNORECASE):
            return tier, weight
    return None, 0.0


def main():
    with open(SKILLS_PATH, "r", encoding="utf-8") as f:
        skill_tbl = json.load(f)
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        dota = json.load(f)
    heroes = dota["heroes"]

    out = OrderedDict()
    out["meta"] = {
        "map": "DotA 6.83d",
        "hero_count": len(heroes),
        "purpose": "Control/ult threat priors for aiRankTeamfightTargets / ccScore",
        "note": (
            "Runtime still reads live level+cooldown from CAbilitySpell; "
            "this table only supplies which abilities matter and base weights."
        ),
    }
    out["heroes"] = OrderedDict()

    uncovered = []
    for hero_code, h in heroes.items():
        zh = h.get("name", hero_code)
        entries = []
        skills = h.get("skills", [])
        # Prefer live names from dota_data; merge codes from skill table for orderId
        st = skill_tbl.get(hero_code, {}).get("skills", [])
        st_by_code = {s["code"]: s for s in st}
        for s in skills:
            if s.get("isExtra"):
                continue
            code = s["code"]
            name = s.get("name") or abilities_name(dota, code)
            tier, weight = classify_name(name)
            note = ""
            if (hero_code, code) in OVERRIDES:
                tier, weight, note = OVERRIDES[(hero_code, code)]
                if tier is None:
                    continue
            if tier is None:
                # Ult slot (maxLevel 3 / req often 6) still get a mild nuke prior
                st_s = st_by_code.get(code, {})
                if s.get("maxLevel") == 3 or st_s.get("reqLevel") == 6:
                    tier, weight, note = "NUKE_ULT", 0.45, "ult slot default (no hard CC keyword)"
                else:
                    continue
            # Passives with zero order and no CC keyword already skipped unless override
            entries.append(
                {
                    "code": code,
                    "name": name,
                    "slot": s.get("slot"),
                    "hotkey": s.get("hotkey"),
                    "tier": tier,
                    "weight": weight,
                    "coolDs": st_by_code.get(code, {}).get("coolDs"),
                    "orderId": st_by_code.get(code, {}).get("orderId"),
                    "notes": note,
                }
            )
        # Invoker (H00U): add dynamic invoked control set (codes from invoker_orb_combos_683d.json)
        if hero_code == "H00U":
            for code, name, tier, weight in [
                ("A0VZ", "急速冷却", "HARD_CC", 0.70),
                ("A0XL", "幽灵漫步", "INIT", 0.40),
                ("A0VP", "寒冰之墙", "SOFT_CC", 0.50),
                ("A0VS", "电磁脉冲", "SOFT_CC", 0.55),
                ("A0VK", "强袭飓风", "HARD_CC", 0.80),
                ("A0VQ", "灵动迅捷", "SOFT_CC", 0.35),
                ("A0VG", "阳炎冲击", "NUKE", 0.65),
                ("A0VO", "熔炉精灵", "SOFT_CC", 0.30),
                ("A0VN", "混沌陨石", "NUKE", 0.60),
                ("A0VM", "超震声波", "SOFT_CC", 0.75),
            ]:
                entries.append(
                    {
                        "code": code,
                        "name": name,
                        "slot": None,
                        "hotkey": None,
                        "tier": tier,
                        "weight": weight,
                        "coolDs": None,
                        "orderId": None,
                        "notes": "invoked dynamic; resolve via CUnit+0x1DC live list",
                    }
                )
        if not entries:
            uncovered.append((hero_code, zh))
        # Hero-level control prior (CC only; NUKE_ULT/INIT feed other scores)
        max_cc = 0.0
        for e in entries:
            if e["tier"] in ("TEAM_ULT", "HARD_CC", "SOFT_CC"):
                max_cc = max(max_cc, e["weight"])
        out["heroes"][hero_code] = {
            "name": zh,
            "controlPrior": round(max_cc, 3),
            "abilities": entries,
        }

    # Fill remaining with keyword-free heroes that still need a row
    for hero_code, zh in [(c, heroes[c]["name"]) for c in heroes if c not in out["heroes"]]:
        out["heroes"][hero_code] = {"name": zh, "controlPrior": 0.0, "abilities": []}

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Markdown summary sorted by controlPrior desc
    rows = sorted(out["heroes"].items(), key=lambda kv: (-kv[1]["controlPrior"], kv[1]["name"]))
    lines = [
        "# DotA 6.83d 全英雄控制/大招威胁先验表",
        "",
        f"- 英雄数: {len(out['heroes'])}",
        f"- 生成脚本: `artifacts/teamfight-key-target/build_control_threat_table.py`",
        f"- 结构化数据: `hero_control_threat_683d.json`",
        "",
        "| 英雄 | FourCC | controlPrior | 关键技能（tier/weight） |",
        "| :--- | :---: | :---: | :--- |",
    ]
    for code, h in rows:
        abs_ = "; ".join(
            f"{a['name']}(`{a['code']}` {a['tier']} {a['weight']})" for a in h["abilities"][:6]
        )
        if not abs_:
            abs_ = "—"
        lines.append(f"| {h['name']} | `{code}` | {h['controlPrior']:.2f} | {abs_} |")
    lines.append("")
    lines.append(f"未匹配到任何控制/大招关键词的英雄数: {len(uncovered)}")
    if uncovered:
        lines.append("")
        lines.append("## 低控制先验（仅靠 DPS/装备评估）")
        for code, zh in uncovered:
            lines.append(f"- {zh} (`{code}`)")
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    n_with = sum(1 for h in out["heroes"].values() if h["abilities"])
    print(f"heroes={len(out['heroes'])} with_abilities={n_with} uncovered={len(uncovered)}")
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_MD}")


def abilities_name(dota, code):
    a = dota.get("abilities", {}).get(code)
    return a.get("name", code) if a else code


if __name__ == "__main__":
    main()
