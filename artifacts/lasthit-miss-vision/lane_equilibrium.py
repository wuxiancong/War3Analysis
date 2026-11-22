#!/usr/bin/env python3
"""Simple mid-lane meet-point model + CSV backtest (creep centroid proxy)."""
from __future__ import annotations

import json
import math
from pathlib import Path

REC = Path(r"C:\War3Run\War3Launcher\records\lasthit\sf")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-miss-vision")

RAD_T1 = (-1504.0, -1824.0)
DIRE_T1 = (1056.0, -96.0)
RIVER = (-368.0, -656.0)

# Mid axis: parameterize t in [0,1] from Radiant T1 to Dire T1
def axis_point(t: float):
    return (
        RAD_T1[0] + t * (DIRE_T1[0] - RAD_T1[0]),
        RAD_T1[1] + t * (DIRE_T1[1] - RAD_T1[1]),
    )


def project_t(x, y):
    ax = DIRE_T1[0] - RAD_T1[0]
    ay = DIRE_T1[1] - RAD_T1[1]
    den = ax * ax + ay * ay
    if den <= 1e-6:
        return 0.5
    t = ((x - RAD_T1[0]) * ax + (y - RAD_T1[1]) * ay) / den
    return max(0.0, min(1.0, t))


def predict_meet(own_ehp: float, enemy_ehp: float, own_dps: float, enemy_dps: float, meet0: float):
    """
    One-wave discrete model:
    - Waves walk toward each other at equal mid speed → natural meet ~0.5 (river).
    - Extra damage on one side shifts meet toward the damaged side's base.
    meet_shift ≈ k * (enemy_ehp/own_dps - own_ehp/enemy_dps) / T_fight
    Positive shift = toward Dire (enemy pushed into Radiant).
    """
    if own_dps <= 1e-3 or enemy_dps <= 1e-3:
        return meet0, 0.0
    t_own_die = own_ehp / enemy_dps
    t_enemy_die = enemy_ehp / own_dps
    # If enemy dies faster, meet moves toward Dire (Radiant pushes)
    delta = 0.08 * (t_own_die - t_enemy_die)  # calibrated soft gain
    meet = max(0.05, min(0.95, meet0 + delta))
    return meet, delta


def parse_frames(path: Path):
    frames = []
    with path.open(encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            c = line.rstrip("\n").split(",", 9)
            if c[0] != "trace" or len(c) < 10:
                continue
            own = []
            enemy = []
            for u in c[9].split(";"):
                p = u.split(":")
                if len(p) != 6:
                    continue
                side, x, y = p[1], float(p[4]), float(p[5])
                if side == "a":
                    own.append((x, y))
                elif side == "e":
                    enemy.append((x, y))
            if own and enemy:
                ox = sum(p[0] for p in own) / len(own)
                oy = sum(p[1] for p in own) / len(own)
                ex = sum(p[0] for p in enemy) / len(enemy)
                ey = sum(p[1] for p in enemy) / len(enemy)
                # meet proxy = midpoint of centroids projected
                mx, my = (ox + ex) / 2, (oy + ey) / 2
                frames.append(
                    {
                        "t": float(c[1]),
                        "meet_t": project_t(mx, my),
                        "n_own": len(own),
                        "n_enemy": len(enemy),
                    }
                )
    return frames


def main():
    files = sorted(REC.glob("sf_mid_20261121-*.csv"))
    report = []
    for cf in files:
        if "lh0of0" in cf.name or "lh0of1" in cf.name:
            continue
        fr = parse_frames(cf)
        if len(fr) < 10:
            continue
        # Compare naive meet0=0.5 vs observed mean meet; use HP proxy = creep count
        errs = []
        for i in range(0, len(fr) - 1, 5):
            a, b = fr[i], fr[min(i + 5, len(fr) - 1)]
            # crude: equal unit DPS, ehp ∝ count
            pred, _ = predict_meet(a["n_own"] * 500, a["n_enemy"] * 500, a["n_own"] * 20, a["n_enemy"] * 20, 0.5)
            errs.append(abs(pred - b["meet_t"]))
        mean_obs = sum(f["meet_t"] for f in fr) / len(fr)
        mean_err = sum(errs) / len(errs) if errs else None
        report.append(
            {
                "file": cf.name,
                "frames": len(fr),
                "mean_meet_t": round(mean_obs, 4),
                "mean_abs_err_vs_count_model": round(mean_err, 4) if mean_err is not None else None,
                "river_t": round(project_t(*RIVER), 4),
                "safe_if_meet_t_lt": round(project_t(RAD_T1[0] + 700 * 0.5, RAD_T1[1] + 700 * 0.5), 4),
            }
        )
        print(cf.name, "mean_meet", mean_obs, "err", mean_err)

    (OUT / "lane_equilibrium_backtest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
