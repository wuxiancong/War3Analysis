#!/usr/bin/env python3
"""Parse DotA 6.83d w3e cliff/height for mid lane; overlay lasthit CSV misses."""
from __future__ import annotations

import csv
import json
import math
import struct
from collections import Counter
from pathlib import Path

MAP = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
OUT = Path(r"D:\Qt\workspace\War3Analysis\artifacts\lasthit-miss-vision")
REC = Path(r"C:\War3Run\War3Launcher\records\lasthit\sf")

# Mid corridor: Radiant mid T1 (-1504,-1824) GV → Dire mid T1 (1056,-96) MX + river
MID_AABB = dict(xmin=-2200, xmax=1600, ymin=-2400, ymax=400)

RAD_MID_T1 = (-1504.0, -1824.0)
DIRE_MID_T1 = (1056.0, -96.0)


def read_w3e(path: Path):
    data = path.read_bytes()
    assert data[:4] == b"W3E!"
    ver = struct.unpack_from("<I", data, 4)[0]
    # tileset char + haveCustomTileset int32 (mdx-m3-viewer War3MapW3e)
    tileset = chr(data[8])
    custom = struct.unpack_from("<i", data, 9)[0]
    o = 13
    n_ground = struct.unpack_from("<I", data, o)[0]
    o += 4
    grounds = []
    for _ in range(n_ground):
        grounds.append(data[o : o + 4].decode("ascii", "replace"))
        o += 4
    n_cliff = struct.unpack_from("<I", data, o)[0]
    o += 4
    cliffs = []
    for _ in range(n_cliff):
        cliffs.append(data[o : o + 4].decode("ascii", "replace"))
        o += 4
    width, height = struct.unpack_from("<ii", data, o)
    o += 8
    center_x, center_y = struct.unpack_from("<ff", data, o)
    o += 8
    # each corner 7 bytes — see mdx-m3-viewer corner.js
    tiles = []
    for y in range(height):
        row = []
        for x in range(width):
            gh, water_and_flags, tex_flags, var, cliff = struct.unpack_from("<HHBBB", data, o)
            o += 7
            # layerHeight = cliff & 0x0F; cliffTexture = cliff >> 4
            cliff_tex = cliff >> 4
            layer_height = cliff & 0x0F
            ramp = bool(tex_flags & 0x10)  # common bit for ramp in flags nibble of texture byte — verify via corner.js
            ground_texture = tex_flags & 0x0F
            # corner.js: groundHeight = (int16 - 8192) / 512
            ground_z = (gh - 8192) / 512.0
            row.append(
                {
                    "gh": gh,
                    "z": ground_z,
                    "cliff": layer_height,
                    "cliff_tex": cliff_tex,
                    "ground_texture": ground_texture,
                    "flags": tex_flags,
                    "var": var,
                    "water": water_and_flags,
                    "ramp": ramp,
                }
            )
        tiles.append(row)
    return {
        "ver": ver,
        "tileset": tileset,
        "width": width,
        "height": height,
        # w3e centerOffset = world position of corner (0,0)
        "center_x": center_x,
        "center_y": center_y,
        "grounds": grounds,
        "cliffs": cliffs,
        "tiles": tiles,
    }


def world_to_tile(w3e, wx, wy):
    # mdx-m3-viewer / peek-fountain: col = round((wx - centerOffset[0]) / 128)
    tw = w3e["width"]
    th = w3e["height"]
    i = int(round((wx - w3e["center_x"]) / 128.0))
    j = int(round((wy - w3e["center_y"]) / 128.0))
    i = max(0, min(tw - 1, i))
    j = max(0, min(th - 1, j))
    return i, j


def tile_at(w3e, wx, wy):
    i, j = world_to_tile(w3e, wx, wy)
    return w3e["tiles"][j][i], i, j


def read_wpm_pathing(path: Path):
    data = path.read_bytes()
    assert data[:4] == b"MP3W"
    ver = struct.unpack_from("<I", data, 4)[0]
    w, h = struct.unpack_from("<II", data, 8)
    grid = list(data[16 : 16 + w * h])
    return {"ver": ver, "width": w, "height": h, "grid": grid}


def wpm_walkable(wpm, w3e, wx, wy):
    # Pathing map: 32x32 cells; same centerOffset as w3e corners
    px = int(round((wx - w3e["center_x"]) / 32.0))
    py = int(round((wy - w3e["center_y"]) / 32.0))
    px = max(0, min(wpm["width"] - 1, px))
    py = max(0, min(wpm["height"] - 1, py))
    flags = wpm["grid"][py * wpm["width"] + px]
    # MP3W flags: 0x02=unwalkable, 0x04=unflyable, 0x08=unbuildable (common mapping)
    return {
        "px": px,
        "py": py,
        "flags": flags,
        "no_walk": bool(flags & 0x02),
        "no_build": bool(flags & 0x08),
        "no_fly": bool(flags & 0x04),
    }


def parse_csv_events(path: Path):
    events = []
    frames = []
    with path.open(encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            c = line.rstrip("\n").split(",", 9)
            if not c:
                continue
            if c[0] == "event":
                # event,t,kind,side,handle,type,life,...
                events.append(c)
            elif c[0] == "trace" and len(c) >= 10:
                units = {}
                for u in c[9].split(";"):
                    p = u.split(":")
                    if len(p) == 6:
                        units[p[0]] = {
                            "side": p[1],
                            "typ": p[2],
                            "hp": float(p[3]),
                            "x": float(p[4]),
                            "y": float(p[5]),
                        }
                frames.append(
                    {
                        "t": float(c[1]),
                        "x": float(c[2]),
                        "y": float(c[3]),
                        "hp": float(c[4]),
                        "dmg": float(c[5]),
                        "wind": float(c[6]),
                        "cd": float(c[7]),
                        "target": c[8],
                        "u": units,
                    }
                )
    return events, frames


def nearest_frame(frames, t, tol=0.15):
    best = None
    for fr in frames:
        d = abs(fr["t"] - t)
        if d <= tol and (best is None or d < best[0]):
            best = (d, fr)
    return best[1] if best else None


def miss_chance_readonly(attacker_cliff: int, target_cliff: int, is_missile: bool) -> float:
    """AI-facing API: probability that engine enters miss path (before RNG)."""
    if not is_missile:
        return 0.0  # melee high-ground path 未确认 via CMissile::Missed
    if target_cliff > attacker_cliff:
        return 0.25  # ChanceToMiss
    return 0.0


def main():
    w3e = read_w3e(MAP / "war3map.w3e")
    wpm = read_wpm_pathing(MAP / "war3map.wpm")
    print("w3e", w3e["width"], w3e["height"], "center", w3e["center_x"], w3e["center_y"])
    print("wpm", wpm["width"], wpm["height"])

    # Sample mid grid every 128
    samples = []
    x0, x1 = MID_AABB["xmin"], MID_AABB["xmax"]
    y0, y1 = MID_AABB["ymin"], MID_AABB["ymax"]
    cliff_counts = Counter()
    for wy in range(y0, y1 + 1, 128):
        for wx in range(x0, x1 + 1, 128):
            tile, i, j = tile_at(w3e, wx, wy)
            cliff_counts[tile["cliff"]] += 1
            samples.append(
                {
                    "x": wx,
                    "y": wy,
                    "i": i,
                    "j": j,
                    "cliff": tile["cliff"],
                    "z": round(tile["z"], 2),
                }
            )

    # Find slope mouths: adjacent tiles with cliff delta >= 1 along mid diagonal corridor
    slopes = []
    by_xy = {(s["x"], s["y"]): s for s in samples}
    for s in samples:
        for dx, dy in ((128, 0), (0, 128), (128, 128), (128, -128)):
            n = by_xy.get((s["x"] + dx, s["y"] + dy))
            if not n:
                continue
            if abs(n["cliff"] - s["cliff"]) >= 1:
                slopes.append(
                    {
                        "from": (s["x"], s["y"], s["cliff"]),
                        "to": (n["x"], n["y"], n["cliff"]),
                        "dcliff": n["cliff"] - s["cliff"],
                    }
                )

    # Ward candidates near mid_river
    mid_river = (-368.0, -656.0)
    ward_cands = []
    for ang in range(0, 360, 15):
        for rad in (200, 350, 500, 650, 800):
            wx = mid_river[0] + rad * math.cos(math.radians(ang))
            wy = mid_river[1] + rad * math.sin(math.radians(ang))
            tile, _, _ = tile_at(w3e, wx, wy)
            path = wpm_walkable(wpm, w3e, wx, wy)
            # Prefer higher cliff than river tile
            river_tile, _, _ = tile_at(w3e, *mid_river)
            if tile["cliff"] <= river_tile["cliff"]:
                continue
            if path["no_build"]:
                continue
            # cast range 420 from typical stand positions on each high ground
            ward_cands.append(
                {
                    "x": round(wx, 1),
                    "y": round(wy, 1),
                    "cliff": tile["cliff"],
                    "z": round(tile["z"], 2),
                    "wpm_flags": path["flags"],
                    "dcliff_vs_river": tile["cliff"] - river_tile["cliff"],
                }
            )

    # Dedup ward cands by 64 grid
    seen = set()
    wards_uniq = []
    for w in sorted(ward_cands, key=lambda z: (-z["dcliff_vs_river"], -z["cliff"])):
        key = (int(w["x"] // 64), int(w["y"] // 64))
        if key in seen:
            continue
        seen.add(key)
        wards_uniq.append(w)
        if len(wards_uniq) >= 12:
            break

    # Overlay three CSVs
    csv_files = [
        REC / "sf_mid_20261121-231144_lh20of44_dn12of43_pts-23_rate37.csv",
        REC / "sf_mid_20261121-225436_lh8of20_dn6of19_pts-11_rate36.csv",
        REC / "sf_mid_20261121-172855_lh9of16_dn5of16_pts-4_rate44.csv",
    ]
    overlays = []
    reason_tally = Counter()
    for cf in csv_files:
        if not cf.exists():
            continue
        events, frames = parse_csv_events(cf)
        game = {"file": cf.name, "misses": [], "hits": 0, "miss_events": 0}
        for e in events:
            if len(e) < 6:
                continue
            kind = e[2]
            if kind == "hero_death":
                continue
            t = float(e[1])
            hit = kind == "hit"
            if hit:
                game["hits"] += 1
                continue
            game["miss_events"] += 1
            fr = nearest_frame(frames, t, tol=0.2)
            hero_x = fr["x"] if fr else None
            hero_y = fr["y"] if fr else None
            # try find dying unit pos from frame units matching type
            tgt_x = tgt_y = None
            typ = e[5] if len(e) > 5 else ""
            if fr:
                for u in fr["u"].values():
                    if u["typ"] == typ:
                        tgt_x, tgt_y = u["x"], u["y"]
                        break
            row = {
                "t": t,
                "kind": kind,
                "type": typ,
                "hero": (hero_x, hero_y),
                "target": (tgt_x, tgt_y),
            }
            if hero_x is None or tgt_x is None:
                row["reason"] = "未知:缺坐标"
                reason_tally[row["reason"]] += 1
                game["misses"].append(row)
                continue
            atk, _, _ = tile_at(w3e, hero_x, hero_y)
            tgt, _, _ = tile_at(w3e, tgt_x, tgt_y)
            row["atk_cliff"] = atk["cliff"]
            row["tgt_cliff"] = tgt["cliff"]
            row["atk_z"] = round(atk["z"], 2)
            row["tgt_z"] = round(tgt["z"], 2)
            # SF is missile hero → high ground miss possible
            mc = miss_chance_readonly(atk["cliff"], tgt["cliff"], True)
            row["engine_miss_chance"] = mc
            if mc > 0:
                row["reason"] = "可能高低地丢失(目标层更高)"
            elif atk["cliff"] == tgt["cliff"]:
                row["reason"] = "同层:非高低地丢失"
            else:
                row["reason"] = "高打低:非丢失"
            reason_tally[row["reason"]] += 1
            game["misses"].append(row)
        overlays.append(game)
        print(cf.name, "miss_events", game["miss_events"], "hits", game["hits"])

    # ASCII cliff map (downsample)
    # print cliff chars for mid region
    xs = sorted({s["x"] for s in samples})
    ys = sorted({s["y"] for s in samples}, reverse=True)
    # compress: every 2nd
    xs2 = xs[::2]
    ys2 = ys[::2]
    lines = []
    header = "y\\x " + "".join(f"{x:5d}"[-2:] for x in xs2)
    lines.append("Mid cliff layer (digit=cliff). AABB " + str(MID_AABB))
    lines.append(header)
    for y in ys2:
        row = f"{y:5d} "
        for x in xs2:
            s = by_xy.get((x, y))
            row += str(s["cliff"]) if s else "?"
        lines.append(row)

    # Refine T1 by scanning high cliff plateaus near expected mid
    # Also dump river cliff
    river_tile, ri, rj = tile_at(w3e, *mid_river)
    meta = {
        "w3e": {
            "width": w3e["width"],
            "height": w3e["height"],
            "center": [w3e["center_x"], w3e["center_y"]],
            "grounds": w3e["grounds"],
            "cliffs": w3e["cliffs"],
        },
        "mid_river": {"xy": mid_river, "cliff": river_tile["cliff"], "z": river_tile["z"]},
        "cliff_hist_mid": dict(cliff_counts),
        "slope_count": len(slopes),
        "slopes_sample": slopes[:40],
        "ward_candidates": wards_uniq,
        "reason_tally": dict(reason_tally),
        "overlays_summary": [
            {
                "file": g["file"],
                "hits": g["hits"],
                "miss_events": g["miss_events"],
                "high_ground_candidate": sum(
                    1 for m in g["misses"] if m.get("engine_miss_chance", 0) > 0
                ),
                "same_layer": sum(1 for m in g["misses"] if m.get("reason", "").startswith("同层")),
                "unknown": sum(1 for m in g["misses"] if "未知" in m.get("reason", "")),
            }
            for g in overlays
        ],
    }

    (OUT / "mid_cliff_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (OUT / "mid_cliff_ascii.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "mid_overlay_misses.json").write_text(
        json.dumps(overlays, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (OUT / "mid_samples.json").write_text(json.dumps(samples, indent=2), encoding="utf-8")

    # markdown summary table for reasons
    md = ["# Mid cliff + miss overlay", "", "## Reason tally (3 games 没补到)", ""]
    md.append("| Reason | Count |")
    md.append("| :--- | ---: |")
    for k, v in reason_tally.most_common():
        md.append(f"| {k} | {v} |")
    md.append("")
    md.append("## Ward candidates (cliff > river, buildable)")
    md.append("")
    md.append("| x | y | cliff | dcliff | wpm_flags |")
    md.append("| ---: | ---: | ---: | ---: | ---: |")
    for w in wards_uniq:
        md.append(f"| {w['x']} | {w['y']} | {w['cliff']} | {w['dcliff_vs_river']} | {w['wpm_flags']} |")
    md.append("")
    md.append("## ASCII")
    md.append("```")
    md.extend(lines[:40])
    md.append("```")
    (OUT / "mid_cliff_overlay.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("reason", dict(reason_tally))
    print("wards", wards_uniq[:5])
    print("river cliff", river_tile["cliff"], "z", river_tile["z"])


if __name__ == "__main__":
    main()
