# -*- coding: utf-8 -*-
"""
精炼 4 条推荐隐蔽路线为 2~3 个干净路点，并在两种起点（己方中路高坡 & 中路河道交战点）
以及往返双方向（去符 / 回线）下全量复核可走性、War3 寻路绕行与敌方视野（含全部外塔 + 中路兵线）。
同时生成最终版 SVG 叠图。
"""
from __future__ import annotations

import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from analyze_stealth_routes import (
    DotaMap,
    RAD_MID_T1,
    DIRE_MID_T1,
    TOP_RUNE,
    BOT_RUNE,
    MID_MEET,
    RAD_MID_STAND,
    DIRE_MID_STAND,
    SF_SPEED,
    TOWER_DAY_SIGHT,
    TOWER_NIGHT_SIGHT,
    CREEP_DAY_SIGHT,
    CREEP_NIGHT_SIGHT,
    CLAUDE_ROUTES,
    path_length,
    eval_route_visibility,
    write_svg_overlay,
    OUT_DIR,
)

# 其他可能邻近的敌方防御塔坐标（6.83d 常见位置，核查是否会扫到符路）
# 注：仅作辅助安全余量检查，核心依据仍是双方中路一塔
OTHER_TOWERS = {
    "radiant": [  # 近卫面对的天灾其他塔
        ("Dire Mid T2", (2496.0, 1280.0)),
        ("Dire Top T1", (-4864.0, 5632.0)),
        ("Dire Bot T1", (6144.0, -1664.0)),
    ],
    "dire": [  # 天灾面对的近卫其他塔
        ("Rad Mid T2", (-3584.0, -3328.0)),
        ("Rad Top T1", (-6144.0, 1536.0)),
        ("Rad Bot T1", (4864.0, -6144.0)),
    ],
}

# 候选精简 2~3 路点方案（兼顾：1. 全部直通或低绕行比；2. 白天 0 塔视野；3. 尽量避开中路兵线；4. 贴树/高地；5. 适配 aiStealthNext 350码到达判定）
REFINED_WPS = {
    "rad_bot": [(-464.0, -1584.0), (1468.0, -2960.0), (2320.0, -2672.0)],
    "rad_top": [(-1648.0, -784.0), (-1840.0, 200.0)],
    "dire_top": [(-400.0, 560.0), (-1360.0, 1136.0)],
    "dire_bot": [(1100.0, -600.0), (1712.0, -1296.0)],
}


def seg_point_dist(ax, ay, bx, by, px, py):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2)) if l2 > 1.0 else 0.0
    return math.hypot(ax + t * dx - px, ay + t * dy - py)


def run_multi_astar(dmap: DotaMap, pts, bbox):
    out = []
    segs_info = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        st_ok = dmap.straight_walkable(a[0], a[1], b[0], b[1])
        sp = dmap.astar(a, b, bbox=bbox)
        sd = math.hypot(b[0] - a[0], b[1] - a[1])
        ad = path_length(sp)
        segs_info.append((a, b, st_ok, sd, ad, ad / max(1.0, sd)))
        if out and sp:
            out.extend(sp[1:])
        else:
            out.extend(sp)
    return out, segs_info


def main():
    dmap = DotaMap()
    bx0, by0 = dmap.world_to_cell(-4200, -4400)
    bx1, by1 = dmap.world_to_cell(4400, 3200)
    bbox = (max(0, bx0), min(dmap.pw - 1, bx1), max(0, by0), min(dmap.ph - 1, by1))

    creeps_for_team = {
        "radiant": [(-450.0, -450.0), (-320.0, -320.0)],
        "dire": [(-450.0, -450.0), (-580.0, -580.0)],
    }

    lines = []
    svg_data = {}

    for key, cfg in CLAUDE_ROUTES.items():
        team = cfg["team"]
        enemy_t1 = cfg["enemy_t1"]
        goal = cfg["goal"]
        creeps = creeps_for_team[team]
        wps = REFINED_WPS[key]

        lines.append("=" * 84)
        lines.append(f"【{cfg['name']}】({key}) 精简推荐路点: {wps}")

        # 1. 逐路点属性核查
        for idx, (wx, wy) in enumerate(wps):
            ok = dmap.is_walkable(wx, wy)
            cl = dmap.cliff_at(wx, wy)
            dt1 = math.hypot(wx - enemy_t1[0], wy - enemy_t1[1])
            vt1, why = dmap.has_los(enemy_t1[0], enemy_t1[1], wx, wy, TOWER_DAY_SIGHT)
            lines.append(f"  WP{idx+1} ({wx:.0f}, {wy:.0f}): walkable={ok}, cliff={cl}, dist_T1={dt1:.0f}, T1_day_vis={vt1} ({why})")

        # 2. 分别测试：己方中路高坡起点 & 中路河道交战起点
        for s_label, start in [("己方高坡起点", cfg["start"]), ("中路河道起点", MID_MEET)]:
            d_seg_t1 = seg_point_dist(start[0], start[1], goal[0], goal[1], enemy_t1[0], enemy_t1[1])
            direct_p = dmap.astar(start, goal, bbox=bbox)
            direct_v = eval_route_visibility(dmap, direct_p, enemy_t1, creeps)

            claude_p, _ = run_multi_astar(dmap, [start] + cfg["wps"] + [goal], bbox)
            claude_v = eval_route_visibility(dmap, claude_p, enemy_t1, creeps)

            opt_p, segs = run_multi_astar(dmap, [start] + wps + [goal], bbox)
            opt_v = eval_route_visibility(dmap, opt_p, enemy_t1, creeps)

            # 检查其他外塔是否能看到任何采样点
            other_hits = []
            for tname, tpos in OTHER_TOWERS[team]:
                ov = eval_route_visibility(dmap, opt_p, tpos, [])
                if ov["t1_day_len"] > 0:
                    other_hits.append((tname, ov["t1_day_len"]))

            extra_d = opt_v["total_len"] - direct_v["total_len"]
            extra_t = extra_d / SF_SPEED

            lines.append(f"\n  [{s_label} {start}] 直线距敌一塔={d_seg_t1:.0f} (aiStealthNext触发<1950: {d_seg_t1 < 1950.0})")
            lines.append(f"    直线A*: 路程={direct_v['total_len']:.0f} ({direct_v['total_len']/SF_SPEED:.2f}s) | "
                         f"塔白={direct_v['t1_day_len']:.0f}, 塔夜={direct_v['t1_night_len']:.0f}, 兵白={direct_v['creep_day_len']:.0f}, 合并={direct_v['any_day_len']:.0f}")
            lines.append(f"    Claude: 路程={claude_v['total_len']:.0f} ({claude_v['total_len']/SF_SPEED:.2f}s, "
                         f"{(claude_v['total_len']-direct_v['total_len'])/SF_SPEED:+.2f}s) | "
                         f"塔白={claude_v['t1_day_len']:.0f}, 塔夜={claude_v['t1_night_len']:.0f}, 兵白={claude_v['creep_day_len']:.0f}, 合并={claude_v['any_day_len']:.0f}")
            lines.append(f"    推荐  : 路程={opt_v['total_len']:.0f} ({opt_v['total_len']/SF_SPEED:.2f}s, {extra_t:+.2f}s / {extra_d:+.0f}码) | "
                         f"塔白={opt_v['t1_day_len']:.0f}, 塔夜={opt_v['t1_night_len']:.0f}, 兵白={opt_v['creep_day_len']:.0f}, 合并={opt_v['any_day_len']:.0f} | 他塔={other_hits}")
            if opt_v["t1_day_segs"]:
                lines.append(f"    推荐塔白暴露段: {[(round(a), round(b), (round(p1[0]), round(p1[1])), (round(p2[0]), round(p2[1]))) for a,b,p1,p2 in opt_v['t1_day_segs']]}")
            if opt_v["any_day_segs"]:
                lines.append(f"    推荐合并暴露段: {[(round(a), round(b), (round(p1[0]), round(p1[1])), (round(p2[0]), round(p2[1]))) for a,b,p1,p2 in opt_v['any_day_segs']]}")
            if s_label == "己方高坡起点":
                for si, (a, b, sok, sd, ad, dr) in enumerate(segs):
                    lines.append(f"      推荐段{si+1} ({a[0]:.0f},{a[1]:.0f})->({b[0]:.0f},{b[1]:.0f}): 直通={sok}, 直线={sd:.0f}, A*={ad:.0f} ({dr:.2f}x)")
                svg_data[key] = {
                    "cfg": cfg,
                    "direct": direct_p,
                    "claude": claude_p,
                    "opt": opt_p,
                    "opt_wps": [(round(x), round(y)) for x, y in wps],
                }

    out_txt = OUT_DIR / "refined_routes_report.txt"
    out_txt.write_text("\n".join(lines), encoding="utf-8")
    write_svg_overlay(dmap, svg_data, OUT_DIR / "stealth_routes_overlay.svg")
    print(f"Wrote {len(lines)} lines to {out_txt}")


if __name__ == "__main__":
    main()
