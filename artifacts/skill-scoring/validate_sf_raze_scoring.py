# -*- coding: utf-8 -*-
"""Offline validator: 100% empty-cast interception for Shadow Fiend razes."""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "sf_raze_offline_cases.json")

DIST = {"A0EY": 200.0, "A0FH": 450.0, "A0F0": 700.0}
RADIUS = 275.0
DMG = [100.0, 175.0, 250.0, 325.0]
TURN_TOL = 9.0
BLOCK_BELOW = 60.0
LAND = 0.75  # castpt 0.67 + slack


def ang_gap(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def predict_pos(c, dt):
    # creeps have no facing in samples; treat ms as along +x if only scalar — samples use ms for future motion slack
    # For offline cases ms>0 moves toward decreasing x (escape from facing 0 caster) as worst-case miss model
    if c.get("ms", 0) <= 0:
        return c["x"], c["y"]
    return c["x"] - c["ms"] * dt, c["y"]


def raze_hits(ability, hx, hy, facing, level, creeps, dt=LAND):
    dist = DIST[ability]
    rad = math.radians(facing)
    cx = hx + dist * math.cos(rad)
    cy = hy + dist * math.sin(rad)
    dmg = DMG[level - 1]
    kills = 0
    spreads = []
    for c in creeps:
        x, y = predict_pos(c, dt)
        off = math.hypot(x - cx, y - cy)
        if off <= RADIUS and c["hp"] <= dmg:
            kills += 1
            spreads.append(off)
    spread = (max(spreads) - min(spreads)) if len(spreads) >= 2 else (spreads[0] if spreads else 0.0)
    return kills, spread, cx, cy


def score_raze(ability, level, caster, cast_facing, creeps, deny_waiting):
    facing = cast_facing
    kills, spread, _, _ = raze_hits(ability, caster["x"], caster["y"], facing, level, creeps)
    ang = ang_gap(caster["facing"], cast_facing)
    if kills <= 0:
        return 0.0, kills, True, "empty"
    if ang > TURN_TOL:
        # Direction error: treat as empty-cast risk → hard block
        return max(0.0, 55.0 - ang * 3.5), kills, True, "facing"
    sc = (75.0 if kills >= 2 else 55.0) + (kills - 1) * 15.0
    if spread > 140.0:
        sc -= (spread - 140.0) * 0.25
    sc -= ang * 3.5
    # Task rule: single creep allowed only when deny-waiting (必漏) + enough mana
    mana = caster.get("mana", 0)
    if kills == 1 and deny_waiting and mana >= 150.0:
        sc = max(sc, 60.0)
    sc = max(0.0, min(100.0, sc))
    if kills == 1 and not (deny_waiting and mana >= 150.0):
        return sc, kills, True, "farm_single"
    block = sc < BLOCK_BELOW
    return sc, kills, block, "ok" if not block else "low_score"


def main():
    doc = json.load(open(CASES, encoding="utf-8"))
    failed = []
    empty_cases = 0
    empty_caught = 0
    for case in doc["cases"]:
        sc, kills, block, reason = score_raze(
            case["ability"],
            case["level"],
            case["caster"],
            case["castFacing"],
            case["creeps"],
            case.get("denyWaiting", False),
        )
        exp_block = case["expectBlock"]
        ok = block == exp_block
        if "expectScore" in case:
            ok = ok and abs(sc - case["expectScore"]) < 1e-6
        if "expectScoreMin" in case:
            ok = ok and sc >= case["expectScoreMin"] - 1e-6
        if "expectScoreMax" in case:
            ok = ok and sc <= case["expectScoreMax"] + 1e-6
        # Track empty-cast interception rate
        is_empty = kills <= 0 or reason in ("empty", "facing")
        if is_empty or case["id"].startswith("EMPTY"):
            empty_cases += 1
            if block:
                empty_caught += 1
        status = "PASS" if ok else "FAIL"
        print(f"{status} {case['id']}: score={sc:.1f} kills={kills} block={block} reason={reason} :: {case.get('note','')}")
        if not ok:
            failed.append(case["id"])

    # Require 100% empty interception among EMPTY_* and kills==0 cases
    empty_rate = empty_caught / empty_cases if empty_cases else 1.0
    print(f"\nEmpty-cast interception: {empty_caught}/{empty_cases} = {empty_rate*100:.1f}%")
    if failed:
        print("FAILED:", ", ".join(failed))
        return 1
    if empty_rate < 1.0:
        print("Empty-cast interception < 100%")
        return 2
    print("ALL PASS (including 100% empty-cast block)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
