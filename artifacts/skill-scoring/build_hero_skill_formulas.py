# -*- coding: utf-8 -*-
"""Build DotA 6.83d all-hero skill damage/geometry table for cast scoring.

Sources:
  - War3Bot/images/dota_data.json          hero -> skills
  - artifacts/ability-orders/dota_hero_skills.json  cast metadata
  - artifacts/ability-orders/map/*AbilityStrings.txt  tip damage text
  - artifacts/ability-orders/map/Units_AbilityData.slk  Area/Rng/Cool/Cost/Data*
  - War3Script/war3map_*.j                 curated JASS overrides
  - artifacts/scoring/*/Units_UnitWeapons.slk  castpt (hero)
"""
from __future__ import annotations

import collections
import json
import os
import re
from datetime import datetime, timezone

ROOT = r"D:\Qt\workspace"
ART = os.path.join(ROOT, "War3Analysis", "artifacts")
OUT_DIR = os.path.join(ART, "skill-scoring")
MAP = os.path.join(ART, "ability-orders", "map")
SCORE_BASE = os.path.join(ART, "scoring", "base")

# ---------- helpers ----------
def fcc_int(code: str) -> int:
    return sum(ord(c) << (8 * (3 - i)) for i, c in enumerate(code))


def parse_ini_sections(path: str) -> dict:
    secs: dict[str, dict] = {}
    sec = None
    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return secs
    with f:
        for raw in f:
            line = raw.strip("\r\n")
            m = re.match(r"^\[(\w{4})\]$", line)
            if m:
                sec = m.group(1)
                secs.setdefault(sec, {})
                continue
            if not sec or "=" not in line:
                continue
            k, v = line.split("=", 1)
            secs[sec][k.strip()] = v.strip()
    return secs


def parse_slk(path: str) -> dict:
    cols, rows, cur_y, x = {}, collections.defaultdict(dict), 0, None
    with open(path, encoding="latin-1") as f:
        for line in f:
            if not line.startswith("C;"):
                continue
            parts = line.rstrip("\r\n").split(";")
            val = None
            for p in parts[1:]:
                if p.startswith("X"):
                    x = int(p[1:])
                elif p.startswith("Y"):
                    cur_y = int(p[1:])
                elif p.startswith("K"):
                    val = p[1:].strip('"')
            if x is None or val is None:
                continue
            if cur_y == 1:
                cols[x] = val
            else:
                rows[cur_y][cols.get(x, x)] = val
    return {r["alias"]: r for r in rows.values() if "alias" in r}


def parse_weapons_castpt() -> dict[str, float]:
    """unitId -> castpt seconds."""
    out = {}
    candidates = []
    for mpq in ("War3Patch.mpq", "War3x.mpq", "war3.mpq"):
        p = os.path.join(SCORE_BASE, mpq, "Units_UnitWeapons.slk")
        if os.path.exists(p):
            candidates.append(p)
    map_w = os.path.join(ART, "scoring", "map")
    for root, _, files in os.walk(map_w) if os.path.isdir(map_w) else []:
        for fn in files:
            if fn.endswith("UnitWeapons.slk"):
                candidates.append(os.path.join(root, fn))
    for path in candidates:
        try:
            by = parse_slk(path)
        except OSError:
            continue
        for alias, row in by.items():
            if "castpt" in row:
                try:
                    out[alias] = float(row["castpt"])
                except ValueError:
                    pass
    return out


def strip_wc3_color(s: str) -> str:
    return re.sub(r"\|c[0-9a-fA-F]{8}", "", s).replace("|r", "").replace("|n", "\n")


def split_levels(text: str) -> list[str]:
    if not text:
        return []
    # Prefer quoted CSV-like tips first
    if text.startswith('"') and '","' in text:
        parts = re.findall(r'"([^"]*)"', text)
        if parts:
            return parts
    # Comma-separated unquoted level tips (Chinese DotA style)
    parts = text.split(",")
    return [p.strip() for p in parts if p.strip()]


NUM = r"(\d+(?:\.\d+)?)"


def extract_numbers_after(label_pat: str, text: str) -> list[float] | None:
    m = re.search(label_pat + r"\s*[：:|]?\s*" + NUM + r"(?:[/／]" + NUM + r")*", text)
    if not m:
        return None
    chunk = m.group(0)
    nums = [float(x) for x in re.findall(NUM, chunk)]
    return nums or None


def parse_damage_from_tips(ubertip: str, research: str) -> dict:
    """Heuristic damage / radius / delay extraction from Chinese/English tips."""
    src = research or ubertip or ""
    plain = strip_wc3_color(src)
    levels = []
    # Level-tagged research tips
    for m in re.finditer(
        r"等级\s*(\d+)\s*[|r\s\-–]*[^\n]*?造成\s*" + NUM + r"\s*点",
        plain,
    ):
        levels.append({"level": int(m.group(1)), "damage": float(m.group(2))})
    if not levels:
        for m in re.finditer(
            r"Level\s*(\d+)\s*[^\n]*?(?:Deals|deals|damage)\s*" + NUM,
            plain,
            re.I,
        ):
            levels.append({"level": int(m.group(1)), "damage": float(m.group(2))})
    # Per-level ubertip commas: 「造成XXX点伤害」
    if not levels and ubertip:
        for i, tip in enumerate(split_levels(ubertip), 1):
            t = strip_wc3_color(tip)
            dm = re.search(r"造成\s*" + NUM + r"\s*点", t)
            if not dm:
                dm = re.search(r"(?:deal(?:s|ing)?|Deals)\s*" + NUM + r"\s*(?:point\s+)?damage", t, re.I)
            if dm:
                levels.append({"level": i, "damage": float(dm.group(1))})

    meta = {}
    for key, pats in {
        "area": [r"作用范围", r"范围", r"AoE", r"radius"],
        "range": [r"施法距离", r"Cast Range", r"cast range"],
        "delay": [r"施法延迟", r"延迟", r"Delay"],
        "cast_time": [r"施法时间", r"Cast(?:ing)? [Tt]ime"],
        "cooldown": [r"冷却时间", r"Cooldown"],
        "mana": [r"魔法消耗", r"Mana [Cc]ost"],
    }.items():
        for pat in pats:
            nums = extract_numbers_after(pat, plain)
            if nums:
                meta[key] = nums
                break

    # Damage type markers in tip
    dtype = "unknown"
    if re.search(r"纯粹|无视魔法免疫|DAMAGE_TYPE_UNIVERSAL|Pure", plain, re.I):
        dtype = "pure"
    elif re.search(r"物理|Physical", plain, re.I):
        dtype = "physical"
    elif re.search(r"魔法|Magic|magical", plain, re.I):
        dtype = "magical"

    return {"levels": levels, "meta": meta, "damageTypeHint": dtype, "tipPlain": plain[:400]}


def slk_level_field(row: dict, prefix: str, max_lv: int) -> list:
    out = []
    for lv in range(1, max_lv + 1):
        k = f"{prefix}{lv}"
        if k in row and row[k] not in ("", "_", "-"):
            try:
                out.append(float(row[k]))
            except ValueError:
                out.append(row[k])
        else:
            out.append(None)
    # collapse if all None
    if all(v is None for v in out):
        return []
    return out


# ---------- curated JASS overrides (verified) ----------
JASS_OVERRIDES = {
    "A0EY": {
        "geometry": "forward_circle",
        "centerDist": 200,
        "radius": 275,
        "damageFormula": "25 + 75 * level",
        "damageByLevel": [100, 175, 250, 325],
        "damageType": "magical",
        "p6iType": None,
        "engineDamage": "ATTACK_TYPE_NORMAL + DAMAGE_TYPE_DEATH",
        "manaCost": [75, 75, 75, 75],
        "cooldown": [10, 10, 10, 10],
        "castPointExtra": 0.0,
        "turnToleranceDeg": 9.0,
        "emptyCastBlock": True,
        "scoringClass": "directional_aoe",
        "jass": "war3map_7.j QK4/QJ4",
        "confidence": "jass",
    },
    "A0FH": {
        "geometry": "forward_circle",
        "centerDist": 450,
        "radius": 275,
        "damageFormula": "25 + 75 * GetUnitAbilityLevel(this)",
        "damageByLevel": [100, 175, 250, 325],
        "damageType": "magical",
        "engineDamage": "ATTACK_TYPE_NORMAL + DAMAGE_TYPE_DEATH",
        "manaCost": [75, 75, 75, 75],
        "cooldown": [10, 10, 10, 10],
        "turnToleranceDeg": 9.0,
        "emptyCastBlock": True,
        "scoringClass": "directional_aoe",
        "parent": "A0EY",
        "jass": "war3map_7.j QK4",
        "confidence": "jass",
    },
    "A0F0": {
        "geometry": "forward_circle",
        "centerDist": 700,
        "radius": 275,
        "damageFormula": "25 + 75 * GetUnitAbilityLevel(this)",
        "damageByLevel": [100, 175, 250, 325],
        "damageType": "magical",
        "engineDamage": "ATTACK_TYPE_NORMAL + DAMAGE_TYPE_DEATH",
        "manaCost": [75, 75, 75, 75],
        "cooldown": [10, 10, 10, 10],
        "turnToleranceDeg": 9.0,
        "emptyCastBlock": True,
        "scoringClass": "directional_aoe",
        "parent": "A0EY",
        "jass": "war3map_7.j QK4",
        "confidence": "jass",
    },
    "A29J": {
        "geometry": "radial_lines",
        "lineCountFormula": "souls / 2",
        "damagePerLineByLevel": [80, 120, 160],
        "crippleBands": [
            {"radius": 200, "label": "close"},
            {"radius": 400, "label": "moderate"},
            {"radius": 700, "label": "far"},
        ],
        "slowMs": 0.20,
        "atkReduce": 0.50,
        "crippleDuration": 5.0,
        "castTime": 1.0,
        "manaCost": [150, 175, 200],
        "cooldown": [120, 110, 100],
        "damageType": "magical",
        "scoringClass": "teamfight_aoe_lines",
        "hitLineDecayNote": "Closer units intersect more radial lines; expected lines ~ proportional to solid angle coverage around caster",
        "jass": "war3map_7.j QN4/U24 (A0HG lines + A0HH cripple)",
        "confidence": "jass",
    },
    "A0G6": {
        "geometry": "unit_target",
        "damageFormula": (
            "base=20*level; agiRatio=agi/str; "
            "if agiRatio<0.5: mult=0.25; elif agiRatio>1.5: mult=0.5*level; "
            "else mult=0.25+(agiRatio-0.5)*(0.5*level-0.25); "
            "dmg=base+mult*agi"
        ),
        "stunFormula": (
            "strRatio=str/agi; maxStun=0.25+level; "
            "if strRatio<0.5: stun=0.25; elif strRatio>1.5: stun=maxStun; "
            "else stun=0.25+(strRatio-0.5)*(maxStun-0.25)"
        ),
        "knockbackFormula": (
            "strRatio=str/agi; if <0.5: 100; elif >1.5: 300; else 100+(strRatio-0.5)*200"
        ),
        "threshold": {"agiOverStr": 1.5, "strOverAgi": 1.5},
        "baseDamageByLevel": [20, 40, 60, 80],
        "agiMultMin": 0.25,
        "agiMultMaxByLevel": [0.5, 1.0, 1.5, 2.0],
        "stunMin": 0.25,
        "stunMaxByLevel": [1.25, 2.25, 3.25, 4.25],
        "knockbackMin": 100,
        "knockbackMax": 300,
        "rangeByLevel": [600, 700, 800, 900],
        "manaCost": [100, 100, 100, 100],
        "cooldown": [10, 10, 10, 10],
        "damageType": "magical",
        "p6iType": 1,
        "scoringClass": "attr_scaled_unit",
        "jass": "war3map_5.j JR3",
        "confidence": "jass",
    },
    "A027": {
        "geometry": "point_circle_delayed",
        "radius": 225,
        "delay": 0.5,
        "damageByLevel": [120, 160, 200, 240],
        "stunByLevel": [1.6, 1.9, 2.2, 2.5],
        "range": 625,
        "manaCost": [100, 110, 120, 130],
        "manaCostTip": [90, 100, 110, 125],
        "cooldown": [7, 7, 7, 7],
        "damageType": "magical",
        "emptyCastBlock": True,
        "scoringClass": "delayed_point_aoe",
        "slkBase": "ANin",
        "confidence": "slk+tip",
    },
    "A01F": {
        "geometry": "shockwave_cone",
        "length": 800,
        "endRadius": 275,
        "startWidthHint": 200,
        "damageByLevel": [110, 180, 250, 320],
        "range": 800,
        "manaCost": [100, 115, 130, 145],
        "cooldown": [8.5, 8.5, 8.5, 8.5],
        "damageType": "magical",
        "slkBase": "AOsh",
        "emptyCastBlock": True,
        "scoringClass": "directional_wave",
        "confidence": "slk",
    },
    "A01P": {
        "geometry": "unit_target",
        "damageByLevel": [450, 675, 950],
        "range": 600,
        "manaCost": [280, 420, 680],
        "cooldown": [70, 60, 50],
        "damageType": "magical",
        "p6iTypeAghanim": 7,
        "aghanimCode": "A09Z",
        "scoringClass": "nuke_unit",
        "confidence": "slk+jass_aghanim",
    },
    # --- teamfight AOE (SLK Area + tip damage; pierce flags from tip) ---
    "A29I": {  # Tide Ravage
        "geometry": "self_expanding_ring",
        "radiusByLevel": [825, 925, 1025],
        "damageByLevel": [200, 290, 380],
        "damageType": "magical",
        "stunHint": "2.0s (ring travel)",
        "scoringClass": "teamfight_self_aoe",
        "emptyCastBlock": True,
        "confidence": "slk+tip",
    },
    "A1BX": {  # Enigma Black Hole
        "geometry": "point_circle_channeled",
        "radius": 400,
        "damageType": "pure",
        "piercesBkb": True,
        "scoringClass": "teamfight_channel_aoe",
        "emptyCastBlock": True,
        "confidence": "slk+tip",
    },
    "A0DH": {  # ES Echo Slam
        "geometry": "self_aoe",
        "radius": 575,
        "damageByLevel": [200, 265, 340],
        "echoDamageNote": "plus per-unit echo component from tip/JASS",
        "damageType": "magical",
        "scoringClass": "teamfight_self_aoe",
        "emptyCastBlock": True,
        "confidence": "slk+tip",
    },
    "A06R": {  # SK Epicenter
        "geometry": "self_pulses",
        "radiusByLevel": [300, 350, 400],
        "damageType": "magical",
        "scoringClass": "teamfight_self_aoe",
        "emptyCastBlock": True,
        "confidence": "slk+tip",
    },
    "A0SK": {  # ES Fissure
        "geometry": "line_block",
        "damageByLevel": [125, 175, 225, 275],
        "damageType": "magical",
        "scoringClass": "directional_wave",
        "emptyCastBlock": True,
        "confidence": "tip",
    },
    "A00S": {  # Centaur Hoof Stomp
        "geometry": "self_aoe",
        "radius": 315,
        "damageByLevel": [100, 150, 200, 250],
        "damageType": "magical",
        "scoringClass": "teamfight_self_aoe",
        "emptyCastBlock": True,
        "confidence": "slk+tip",
    },
    "A2WE": {  # AM Mana Void
        "geometry": "unit_target_aoe",
        "radius": 500,
        "damageFormula": "missingMana * (0.6/0.9/1.2)",
        "damageType": "magical",
        "scoringClass": "attr_scaled_unit",
        "confidence": "tip",
    },
    "A067": {  # Necro Reaper's Scythe
        "geometry": "unit_target",
        "damageFormula": "missingHP * (0.4/0.6/0.9) after stun",
        "damageType": "magical",
        "scoringClass": "attr_scaled_unit",
        "confidence": "tip",
    },
    "A2BG": {  # Skywrath Mystic Flare
        "geometry": "point_circle_dps",
        "radius": 170,
        "damageType": "magical",
        "scoringClass": "delayed_point_aoe",
        "emptyCastBlock": True,
        "confidence": "slk+tip",
    },
    "A0L3": {  # Silencer Global Silence
        "geometry": "global",
        "damageType": "none",
        "scoringClass": "utility",
        "utilityIgnoreEmpty": True,
        "emptyCastBlock": False,
        "confidence": "tip",
    },
}

# Teamfight AOE radius curated (tip/SLK) for common ultimates — extend via tip parser
TEAMFIGHT_HINTS = {
    # Mammoth / Tide / Enigma / Elder Titan / SK / Storm etc. filled when present in hero table
}


def classify_scoring(target_type: str, override: dict | None, tip: dict) -> str:
    if override and "scoringClass" in override:
        return override["scoringClass"]
    tt = (target_type or "").lower()
    if tt in ("passive",):
        return "passive"
    if tt in ("none", "instant") and tip.get("meta", {}).get("area"):
        return "self_aoe"
    if tt in ("point",):
        return "point_aoe"
    if tt in ("unit", "unit_or_point"):
        return "unit_or_hybrid"
    return "generic"


def main():
    data = json.load(open(os.path.join(ROOT, "War3Bot", "images", "dota_data.json"), encoding="utf-8"))
    cast_meta = {}
    cm_path = os.path.join(ART, "ability-orders", "dota_hero_skills.json")
    if os.path.exists(cm_path):
        cast_meta = json.load(open(cm_path, encoding="utf-8"))

    # Merge ability strings (later race files override earlier — map folder has DotA overrides)
    strings: dict[str, dict] = {}
    for fn in sorted(os.listdir(MAP)):
        if not fn.endswith("AbilityStrings.txt"):
            continue
        for code, sec in parse_ini_sections(os.path.join(MAP, fn)).items():
            strings[code] = {**strings.get(code, {}), **sec}

    slk = parse_slk(os.path.join(MAP, "Units_AbilityData.slk"))
    castpt = parse_weapons_castpt()

    heroes_out = {}
    skill_index = {}
    stats = {
        "heroCount": 0,
        "skillCount": 0,
        "withDamageLevels": 0,
        "jassOverrides": 0,
        "passiveSkipped": 0,
    }

    for hero_code, hero in data["heroes"].items():
        hmeta = cast_meta.get(hero_code, {})
        cast_skills = {s["code"]: s for s in hmeta.get("skills", []) if s.get("code")}
        hero_castpt = castpt.get(hero_code)
        skills_out = []
        for sk in hero["skills"]:
            code = sk.get("code") or ""
            if not code or code in ("", "Aamk") or sk.get("name") == "未习得":
                continue
            if code == hero.get("attrCode"):
                continue
            row = slk.get(code, {})
            tip_sec = strings.get(code, {})
            tip_parse = parse_damage_from_tips(
                tip_sec.get("Ubertip", ""), tip_sec.get("Researchubertip", "")
            )
            cm = cast_skills.get(code, {})
            max_lv = int(sk.get("maxLevel") or cm.get("maxLevel") or row.get("levels") or 4)
            try:
                max_lv = int(max_lv)
            except (TypeError, ValueError):
                max_lv = 4

            ov = JASS_OVERRIDES.get(code)
            if ov:
                stats["jassOverrides"] += 1

            target_type = cm.get("targetType") or (
                "passive" if not cm.get("orderId") and sk.get("hotkey") and code.startswith("A") else cm.get("targetType", "unknown")
            )
            # Prefer SLK targs1
            if row.get("targs1") == "none":
                target_type = target_type if target_type not in (None, "unknown") else "none"
            elif row.get("targs1") and "enemies" in str(row.get("targs1")):
                if target_type in (None, "unknown", "passive") and cm.get("orderId"):
                    pass

            entry = {
                "code": code,
                "name": sk.get("name") or tip_sec.get("Name", ""),
                "nameEn": tip_sec.get("Name", ""),
                "hotkey": sk.get("hotkey") or tip_sec.get("Hotkey", ""),
                "slot": sk.get("slot"),
                "isExtra": bool(sk.get("isExtra")),
                "parentCode": sk.get("parentCode") or (ov or {}).get("parent", ""),
                "maxLevel": max_lv,
                "baseAbility": row.get("code") or cm.get("base"),
                "orderId": cm.get("orderId"),
                "orderStr": cm.get("orderStr"),
                "targetType": cm.get("targetType") or target_type,
                "castPointHero": hero_castpt,
                "slk": {
                    "area": slk_level_field(row, "Area", max_lv),
                    "range": slk_level_field(row, "Rng", max_lv),
                    "cool": slk_level_field(row, "Cool", max_lv),
                    "cost": slk_level_field(row, "Cost", max_lv),
                    "cast": slk_level_field(row, "Cast", max_lv),
                    "dur": slk_level_field(row, "Dur", max_lv),
                    "dataA": slk_level_field(row, "DataA", max_lv),
                    "dataB": slk_level_field(row, "DataB", max_lv),
                    "dataC": slk_level_field(row, "DataC", max_lv),
                    "dataD": slk_level_field(row, "DataD", max_lv),
                    "dataE": slk_level_field(row, "DataE", max_lv),
                    "dataF": slk_level_field(row, "DataF", max_lv),
                },
                "tip": {
                    "damageLevels": tip_parse["levels"],
                    "meta": tip_parse["meta"],
                    "damageTypeHint": tip_parse["damageTypeHint"],
                },
                "formula": ov or {},
                "scoringClass": classify_scoring(cm.get("targetType"), ov, tip_parse),
                "confidence": (ov or {}).get("confidence", "tip+slk" if tip_parse["levels"] or row else "metadata"),
            }

            # Prefer SLK DataA as damage when tip empty and DataA looks like damage
            if not tip_parse["levels"] and entry["slk"]["dataA"] and not ov:
                da = [v for v in entry["slk"]["dataA"] if isinstance(v, (int, float))]
                if da and max(da) >= 20:
                    entry["tip"]["damageLevels"] = [
                        {"level": i + 1, "damage": float(v)} for i, v in enumerate(da) if v is not None
                    ]
                    entry["confidence"] = "slk_dataA"

            if entry["tip"]["damageLevels"] or ov:
                stats["withDamageLevels"] += 1
            if entry["scoringClass"] == "passive" or cm.get("targetType") == "passive":
                stats["passiveSkipped"] += 1

            skills_out.append(entry)
            skill_index[code] = {
                "hero": hero_code,
                "heroName": hero.get("name"),
                "skill": code,
                "name": entry["name"],
            }
            stats["skillCount"] += 1

        heroes_out[hero_code] = {
            "name": hero.get("name"),
            "attrCode": hero.get("attrCode"),
            "castPoint": hero_castpt,
            "skills": skills_out,
        }
        stats["heroCount"] += 1

    mitigation = {
        "armor": {
            "k": 0.06,
            "formula": "physTaken = raw * 1/(1 + 0.06*armor); reduction = 0.06*a/(1+0.06*a)",
            "source": "Misc/DefenseArmor + CalcArmorReduction (war3-lasthit-combat-data.md)",
            "appliesTo": ["physical", "p6iType=2/4/5"],
        },
        "magicResist": {
            "baseHero": 0.25,
            "stacking": "multiplicative: totalMR = 1 - product(1 - source_i)",
            "sources": ["base 25%", "cloak/hood/pipe/etc items", "skill auras (e.g. anti-mage spell shield is different)", "Veil/Ethereal reduce resistance"],
            "formula": "magicTaken = raw * (1 - totalMR) * spellAmp",
            "note": "P6I type1 uses DAMAGE_TYPE_FIRE which DotA scripts treat as magical vs hero; type7/8 UNIVERSAL ignore armor+MR unless ethereal converts type7 to magic",
            "source": "war3map_1.j P6I + dota-6.83d-web-gameplay-data-reverse.md",
        },
        "p6iTypes": {
            "1": "magical (NORMAL+FIRE)",
            "2": "physical (HERO+NORMAL)",
            "3": "magical (HERO+MAGIC)",
            "4": "physical pierce",
            "5": "physical normal",
            "6": "HP removal (near-pure, min life clamp)",
            "7": "pure UNIVERSAL; if ethereal -> magic",
            "8": "pure UNIVERSAL",
        },
    }

    scoring = {
        "singleTarget": {
            "score01": "hitProb * postMitigationDmg / theoreticalMaxDmg * 100",
            "hitProb": "predict target pos after castPoint + projectile/delay; 0 if miss and not scout/escape",
            "emptyCast": "hitProb==0 && !utilityFlags => score=0 and block cast",
            "lasthitMana": "if farm context: require kills>=2 OR (kills==1 && denyWaiting && mana high) else block",
        },
        "aoe": {
            "score": "sum_{e in Hit(p)} w_key(e) * ExpectedDmg(e,p)",
            "normalize": "100 * score / max_over_candidates(score)",
            "w_key": "see grok-teamfight-key-target-scoring.md / dota-teamfight-key-target-scoring.md",
            "candidatePoints": "grid around cluster + hero feet for self-centered skills + facing samples for directional",
        },
        "thresholds": {
            "blockBelow": 60,
            "razeTurnToleranceDeg": 9.0,
            "razeDirectionSoftPenaltyDeg": 12.0,
        },
    }

    doc = {
        "meta": {
            "map": "DotA Allstars 6.83d",
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "analyzer": "Composer (Cursor Agent)",
            "purpose": "Data-driven skill cast scoring for War3Launcher/hooker",
            "heroCount": stats["heroCount"],
            "skillCount": stats["skillCount"],
            "stats": stats,
            "sources": [
                "War3Bot/images/dota_data.json",
                "War3Analysis/artifacts/ability-orders/map/Units_AbilityData.slk",
                "War3Analysis/artifacts/ability-orders/map/*AbilityStrings.txt",
                "War3Script/war3map_*.j (curated overrides)",
                "War3Analysis/artifacts/ability-orders/dota_hero_skills.json",
            ],
        },
        "mitigation": mitigation,
        "scoring": scoring,
        "jassOverrideCodes": sorted(JASS_OVERRIDES.keys()),
        "heroes": heroes_out,
        "skillIndex": skill_index,
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "hero_skill_formulas.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)

    # Compact summary CSV for quick grep
    import csv

    sum_path = os.path.join(OUT_DIR, "hero_skill_formulas_summary.csv")
    with open(sum_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "hero",
                "heroName",
                "code",
                "name",
                "hotkey",
                "slot",
                "scoringClass",
                "confidence",
                "dmgL1",
                "areaL1",
                "rangeL1",
                "coolL1",
                "costL1",
            ]
        )
        for hc, h in heroes_out.items():
            for s in h["skills"]:
                dmg = s["tip"]["damageLevels"]
                d1 = dmg[0]["damage"] if dmg else (s["formula"].get("damageByLevel") or [None])[0]
                area = (s["slk"]["area"] or [None])[0] or (s["formula"].get("radius"))
                rng = (s["slk"]["range"] or [None])[0] or s["formula"].get("range")
                cool = (s["slk"]["cool"] or [None])[0]
                cost = (s["slk"]["cost"] or [None])[0]
                w.writerow(
                    [
                        hc,
                        h["name"],
                        s["code"],
                        s["name"],
                        s["hotkey"],
                        s["slot"],
                        s["scoringClass"],
                        s["confidence"],
                        d1,
                        area,
                        rng,
                        cool,
                        cost,
                    ]
                )

    print(json.dumps({"out": out_path, "summary": sum_path, **stats}, ensure_ascii=False))


if __name__ == "__main__":
    main()
