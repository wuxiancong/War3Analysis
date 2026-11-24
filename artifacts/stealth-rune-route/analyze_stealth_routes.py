# -*- coding: utf-8 -*-
"""
DotA 6.83d 隐蔽看符路线全量核验与最优路径规划器：
1. 解析 war3map.wpm（通行网格 32x32）、war3map.w3e（悬崖层与斜坡 128x128）、war3map.doo（树木与视线阻挡物 YTlb）
2. 核验 Claude 现有 4 条隐蔽路线的路点可走性、段间直通性、实际 A* 寻路绕行轨迹
3. 沿每条路线每 50 码采样，计算敌方中路一塔（白1900/夜800）+ 中路交战小兵（白850/夜800）的真实视线暴露（含高地挡低地 + 树木 occH=230 + YTlb 遮挡）
4. 使用视野惩罚 A* 规划 4 条更优隐蔽路线，简化为可直接写入 aiStealthNext 的路点序列，并对比直线耗时（影魔移速 305）
5. 生成矢量叠图 artifacts/stealth-rune-route/stealth_routes_overlay.svg 与完整文本报告
"""
from __future__ import annotations

import heapq
import json
import math
import struct
from pathlib import Path

MAP_DIR = Path(r"D:\Qt\workspace\War3Analysis\artifacts\ward-deward\map")
OUT_DIR = Path(r"D:\Qt\workspace\War3Analysis\artifacts\stealth-rune-route")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# 关键坐标（来自 war3hook_ai_lane.inl / kAiLanes）
RAD_MID_T1 = (-1504.0, -1824.0)
DIRE_MID_T1 = (1056.0, -96.0)
TOP_RUNE = (-2352.0, 1648.0)
BOT_RUNE = (3008.0, -2832.0)

# 中路常规交战点与双方中单标准对线站位
MID_MEET = (-450.0, -450.0)
RAD_MID_STAND = (-800.0, -950.0)   # 近卫中路高坡对线位
DIRE_MID_STAND = (-100.0, -100.0)  # 天灾中路高坡对线位

SF_SPEED = 305.0

# 视野半径（SLK 核验值）
TOWER_DAY_SIGHT = 1900.0
TOWER_NIGHT_SIGHT = 800.0
CREEP_DAY_SIGHT = 850.0
CREEP_NIGHT_SIGHT = 800.0

# Claude 现有 4 条隐蔽路线（war3hook_ai_lane.inl L395-398）
CLAUDE_ROUTES = {
    "rad_bot": {
        "name": "近卫 → 下路符",
        "team": "radiant",
        "start": RAD_MID_STAND,
        "goal": BOT_RUNE,
        "enemy_t1": DIRE_MID_T1,
        "wps": [(-412.0, -1482.0), (1468.0, -3060.0)],
    },
    "rad_top": {
        "name": "近卫 → 上路符",
        "team": "radiant",
        "start": RAD_MID_STAND,
        "goal": TOP_RUNE,
        "enemy_t1": DIRE_MID_T1,
        "wps": [(-1596.0, -330.0), (-2232.0, 80.0)],
    },
    "dire_top": {
        "name": "天灾 → 上路符",
        "team": "dire",
        "start": DIRE_MID_STAND,
        "goal": TOP_RUNE,
        "enemy_t1": RAD_MID_T1,
        "wps": [(-520.0, -76.0), (-1224.0, 704.0)],
    },
    "dire_bot": {
        "name": "天灾 → 下路符",
        "team": "dire",
        "start": DIRE_MID_STAND,
        "goal": BOT_RUNE,
        "enemy_t1": RAD_MID_T1,
        "wps": [(3160.0, -2232.0)],
    },
}


# ---------------- 1. 地图解析 ----------------

def read_w3e(path: Path):
    data = path.read_bytes()
    assert data[:4] == b"W3E!"
    o = 13
    n_ground = struct.unpack_from("<I", data, o)[0]
    o += 4 + n_ground * 4
    n_cliff = struct.unpack_from("<I", data, o)[0]
    o += 4 + n_cliff * 4
    width, height = struct.unpack_from("<ii", data, o)
    o += 8
    cx, cy = struct.unpack_from("<ff", data, o)
    o += 8
    cliff = [[0] * width for _ in range(height)]
    ramp = [[False] * width for _ in range(height)]
    gz = [[0.0] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            gh, _wf, tex_flags, _var, cl = struct.unpack_from("<HHBBB", data, o)
            o += 7
            cliff[y][x] = cl & 0x0F
            ramp[y][x] = bool(tex_flags & 0x10)
            gz[y][x] = (gh - 8192) / 512.0
    return {"w": width, "h": height, "cx": cx, "cy": cy, "cliff": cliff, "ramp": ramp, "gz": gz}


def read_wpm(path: Path):
    data = path.read_bytes()
    assert data[:4] == b"MP3W"
    w, h = struct.unpack_from("<II", data, 8)
    grid = data[16 : 16 + w * h]
    return {"w": w, "h": h, "grid": grid}


def read_doo_blockers(path: Path):
    """提取所有树木（ATtr/NTtw/NTtc）与视线阻挡物（YTlb）"""
    data = path.read_bytes()
    assert data[:4] == b"W3do"
    ver, _subver, count = struct.unpack_from("<III", data, 4)
    o = 16
    trees = []       # (x, y, tid)
    los_blocks = []  # (x, y, tid)
    for _ in range(count):
        tid = data[o : o + 4].decode("ascii", "replace")
        x, y, z = struct.unpack_from("<fff", data, o + 8)
        flags, life = struct.unpack_from("<BB", data, o + 36)
        o += 38
        if ver >= 8:
            item_sets = struct.unpack_from("<I", data, o + 4)[0]
            o += 8
            for _ in range(item_sets):
                n_items = struct.unpack_from("<I", data, o)[0]
                o += 4 + n_items * 8
        o += 4
        if tid in ("ATtr", "NTtw", "NTtc"):
            trees.append((x, y, tid))
        elif tid in ("YTlb", "YTfb", "YTpb"):
            los_blocks.append((x, y, tid))
    return trees, los_blocks


class DotaMap:
    def __init__(self):
        self.w3e = read_w3e(MAP_DIR / "war3map.w3e")
        self.wpm = read_wpm(MAP_DIR / "war3map.wpm")
        self.trees, self.los_blocks = read_doo_blockers(MAP_DIR / "war3map.doo")

        self.cx = self.w3e["cx"]
        self.cy = self.w3e["cy"]
        self.pw = self.wpm["w"]
        self.ph = self.wpm["h"]

        # 基础通行网格：bit 0x02 = NoWalk
        self.walk = bytearray(self.pw * self.ph)
        raw_grid = self.wpm["grid"]
        for idx in range(self.pw * self.ph):
            self.walk[idx] = 0 if (raw_grid[idx] & 0x02) else 1

        # 统计 wpm 原生是否已把树木标为不可走
        tree_already_blocked = 0
        for tx, ty, _ in self.trees:
            gx, gy = self.world_to_cell(tx, ty)
            if 0 <= gx < self.pw and 0 <= gy < self.ph and self.walk[gy * self.pw + gx] == 0:
                tree_already_blocked += 1
        self.tree_wpm_blocked_ratio = tree_already_blocked / max(1, len(self.trees))

        # 叠加树木（2x2 格 = 64x64）与视线/路径阻挡物（YTlb 4x4 格）到动态通行网格
        # 同时构建 32x32 视线遮挡网格（0=无遮挡，1=树 occH=230，2=YTlb occH=1000）
        self.walk_with_trees = bytearray(self.walk)
        self.occ_grid = bytearray(self.pw * self.ph)
        self.occ_cliff = bytearray(self.pw * self.ph)

        for tx, ty, _ in self.trees:
            gx, gy = self.world_to_cell(tx, ty)
            cl = self.cliff_at(tx, ty)
            for dy in (-1, 0):
                for dx in (-1, 0):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < self.pw and 0 <= ny < self.ph:
                        idx = ny * self.pw + nx
                        self.walk_with_trees[idx] = 0
                        if self.occ_grid[idx] < 1:
                            self.occ_grid[idx] = 1
                            self.occ_cliff[idx] = cl

        for bx, by, tid in self.los_blocks:
            gx, gy = self.world_to_cell(bx, by)
            cl = self.cliff_at(bx, by)
            r = 2 if tid == "YTlb" else 1
            for dy in range(-r, r):
                for dx in range(-r, r):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < self.pw and 0 <= ny < self.ph:
                        idx = ny * self.pw + nx
                        if tid in ("YTpb", "YTlb"):
                            # YTlb 仅挡视线（War3 DestructableData YTlb pathTex=""），YTpb 挡路径
                            pass
                        if tid == "YTpb":
                            self.walk_with_trees[idx] = 0
                        if tid in ("YTlb", "YTfb"):
                            self.occ_grid[idx] = 2
                            self.occ_cliff[idx] = cl

        # 英雄碰撞安全膨胀 1 格（影魔碰撞 24，保证不挤 32 码单格死缝）
        self.walk_hero = bytearray(self.walk_with_trees)
        for gy in range(1, self.ph - 1):
            row = gy * self.pw
            for gx in range(1, self.pw - 1):
                if self.walk_with_trees[row + gx] == 0:
                    continue
                # 若四邻有不可通行格，检查是否形成 1 格窄缝（对侧不可通行）
                n_blk = (
                    (self.walk_with_trees[row + gx - 1] == 0)
                    + (self.walk_with_trees[row + gx + 1] == 0)
                    + (self.walk_with_trees[row - self.pw + gx] == 0)
                    + (self.walk_with_trees[row + self.pw + gx] == 0)
                )
                if n_blk >= 3:
                    self.walk_hero[row + gx] = 0

    def world_to_cell(self, wx: float, wy: float):
        gx = int(math.floor((wx - self.cx) / 32.0))
        gy = int(math.floor((wy - self.cy) / 32.0))
        return gx, gy

    def cell_to_world(self, gx: int, gy: int):
        return self.cx + (gx + 0.5) * 32.0, self.cy + (gy + 0.5) * 32.0

    def is_walkable(self, wx: float, wy: float, hero_margin=False) -> bool:
        gx, gy = self.world_to_cell(wx, wy)
        if not (0 <= gx < self.pw and 0 <= gy < self.ph):
            return False
        g = self.walk_hero if hero_margin else self.walk_with_trees
        return g[gy * self.pw + gx] == 1

    def cliff_at(self, wx: float, wy: float) -> int:
        i = int(round((wx - self.cx) / 128.0))
        j = int(round((wy - self.cy) / 128.0))
        i = max(0, min(self.w3e["w"] - 1, i))
        j = max(0, min(self.w3e["h"] - 1, j))
        return self.w3e["cliff"][j][i]

    def ramp_at(self, wx: float, wy: float) -> bool:
        i = int(round((wx - self.cx) / 128.0))
        j = int(round((wy - self.cy) / 128.0))
        i = max(0, min(self.w3e["w"] - 1, i))
        j = max(0, min(self.w3e["h"] - 1, j))
        return self.w3e["ramp"][j][i]

    def straight_walkable(self, ax: float, ay: float, bx: float, by: float, step=16.0) -> bool:
        d = math.hypot(bx - ax, by - ay)
        n = max(1, int(math.ceil(d / step)))
        for k in range(n + 1):
            t = k / n
            if not self.is_walkable(ax + (bx - ax) * t, ay + (by - ay) * t):
                return False
        return True

    def has_los(self, ox: float, oy: float, tx: float, ty: float, radius: float, obs_cliff_override=None) -> tuple[bool, str]:
        """
        War3 视线判定（返回 (是否可见, 阻挡原因)）：
        1. 距离 > radius -> 不可见
        2. 目标悬崖层 > 观察者悬崖层 -> 高地挡低地
        3. 沿射线每 24 码采样：
           - 中间地形悬崖层 > max(cl_obs, cl_tgt) -> 地形/悬崖挡视线
           - 命中树木格（occH=230 > 1层悬崖128，故 tree_cliff*128 + 230 > ray_z 时挡视线）或 YTlb（occH=1000）
        """
        dist = math.hypot(tx - ox, ty - oy)
        if dist > radius:
            return False, "out_of_range"
        if dist < 48.0:
            return True, "visible"

        cl_obs = obs_cliff_override if obs_cliff_override is not None else self.cliff_at(ox, oy)
        cl_tgt = self.cliff_at(tx, ty)

        # 高地挡低地（注：若目标在斜坡 ramp 上，从低处看斜坡可能边缘可见，保守按严格 cliff > 判挡）
        if cl_tgt > cl_obs:
            return False, f"high_ground({cl_tgt}>{cl_obs})"

        z_obs = cl_obs * 128.0 + 96.0   # 单位/塔视线高度基准
        z_tgt = cl_tgt * 128.0 + 64.0
        max_cl = max(cl_obs, cl_tgt)

        steps = max(2, int(dist / 24.0))
        # 跳过起点附近 48 码（观察者自身/塔身周围）与终点附近 24 码
        for k in range(2, steps):
            t = k / steps
            px = ox + (tx - ox) * t
            py = oy + (ty - oy) * t
            cl_p = self.cliff_at(px, py)
            if cl_p > max_cl:
                return False, f"cliff_block({cl_p}>{max_cl})"
            gx, gy = self.world_to_cell(px, py)
            if 0 <= gx < self.pw and 0 <= gy < self.ph:
                occ = self.occ_grid[gy * self.pw + gx]
                if occ == 2:
                    return False, "ytlb_block"
                elif occ == 1:
                    tree_top = self.occ_cliff[gy * self.pw + gx] * 128.0 + 230.0
                    ray_z = z_obs + (z_tgt - z_obs) * t
                    if tree_top > ray_z:
                        return False, "tree_block"
        return True, "visible"

    def snap_walkable(self, wx: float, wy: float, max_r=6):
        gx, gy = self.world_to_cell(wx, wy)
        if 0 <= gx < self.pw and 0 <= gy < self.ph and self.walk_with_trees[gy * self.pw + gx]:
            return gx, gy
        for r in range(1, max_r + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    nx, ny = gx + dx, gy + dy
                    if 0 <= nx < self.pw and 0 <= ny < self.ph and self.walk_with_trees[ny * self.pw + nx]:
                        return nx, ny
        return gx, gy

    def astar(self, start_xy, goal_xy, cost_fn=None, bbox=None):
        """在 32x32 网格上跑 8 邻域 A*（禁止穿斜角墙）"""
        sx, sy = self.snap_walkable(*start_xy)
        gx, gy = self.snap_walkable(*goal_xy)
        if bbox is None:
            minx, maxx, miny, maxy = 0, self.pw - 1, 0, self.ph - 1
        else:
            minx, maxx, miny, maxy = bbox

        pw = self.pw
        walk = self.walk_with_trees
        start_id = sy * pw + sx
        goal_id = gy * pw + gx

        pq = [(0.0, start_id)]
        gscore = {start_id: 0.0}
        parent = {}
        closed = set()

        nbrs = [
            (1, 0, 32.0), (-1, 0, 32.0), (0, 1, 32.0), (0, -1, 32.0),
            (1, 1, 45.2548), (1, -1, 45.2548), (-1, 1, 45.2548), (-1, -1, 45.2548),
        ]

        while pq:
            _f, cur = heapq.heappop(pq)
            if cur in closed:
                continue
            closed.add(cur)
            if cur == goal_id:
                break
            cx = cur % pw
            cy = cur // pw
            cg = gscore[cur]
            for dx, dy, step_len in nbrs:
                nx, ny = cx + dx, cy + dy
                if not (minx <= nx <= maxx and miny <= ny <= maxy):
                    continue
                nid = ny * pw + nx
                if nid in closed or walk[nid] == 0:
                    continue
                # 斜向防穿墙角
                if dx != 0 and dy != 0:
                    if walk[cy * pw + nx] == 0 or walk[ny * pw + cx] == 0:
                        continue
                mult = cost_fn(nx, ny) if cost_fn else 1.0
                ng = cg + step_len * mult
                if ng < gscore.get(nid, 1e18):
                    gscore[nid] = ng
                    parent[nid] = cur
                    h = math.hypot((gx - nx) * 32.0, (gy - ny) * 32.0)
                    heapq.heappush(pq, (ng + h, nid))

        if goal_id not in parent and goal_id != start_id:
            return []
        path = []
        cur = goal_id
        while cur != start_id:
            path.append(self.cell_to_world(cur % pw, cur // pw))
            cur = parent[cur]
        path.append(self.cell_to_world(sx, sy))
        path.reverse()
        return path


def path_length(pts) -> float:
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def resample_polyline(pts, step=50.0):
    """按每 50 码等距采样"""
    if not pts:
        return []
    out = [(pts[0][0], pts[0][1], 0.0)]
    acc = 0.0
    next_s = step
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        seg = math.hypot(bx - ax, by - ay)
        if seg < 1e-6:
            continue
        while acc + seg >= next_s:
            t = (next_s - acc) / seg
            out.append((ax + (bx - ax) * t, ay + (by - ay) * t, next_s))
            next_s += step
        acc += seg
    out.append((pts[-1][0], pts[-1][1], acc))
    return out


def eval_route_visibility(dmap: DotaMap, pts, enemy_t1, creep_pts):
    """按每 50 码采样，统计白天/夜晚敌方塔视野与中路兵线视野暴露段"""
    samples = resample_polyline(pts, 50.0)
    t1_day_hits = []
    t1_night_hits = []
    creep_day_hits = []
    creep_night_hits = []
    any_day_hits = []

    for x, y, s in samples:
        v_td, _ = dmap.has_los(enemy_t1[0], enemy_t1[1], x, y, TOWER_DAY_SIGHT)
        v_tn, _ = dmap.has_los(enemy_t1[0], enemy_t1[1], x, y, TOWER_NIGHT_SIGHT)
        v_cd = any(dmap.has_los(cx, cy, x, y, CREEP_DAY_SIGHT)[0] for cx, cy in creep_pts)
        v_cn = any(dmap.has_los(cx, cy, x, y, CREEP_NIGHT_SIGHT)[0] for cx, cy in creep_pts)
        if v_td:
            t1_day_hits.append((s, x, y))
        if v_tn:
            t1_night_hits.append((s, x, y))
        if v_cd:
            creep_day_hits.append((s, x, y))
        if v_cn:
            creep_night_hits.append((s, x, y))
        if v_td or v_cd:
            any_day_hits.append((s, x, y, ("T1" if v_td else "") + ("+C" if v_cd else "")))

    def to_segments(hits):
        if not hits:
            return []
        segs = []
        st = prev = hits[0]
        for h in hits[1:]:
            if h[0] - prev[0] > 75.0:
                segs.append((st[0], prev[0], (st[1], st[2]), (prev[1], prev[2])))
                st = h
            prev = h
        segs.append((st[0], prev[0], (st[1], st[2]), (prev[1], prev[2])))
        return segs

    return {
        "total_len": path_length(pts),
        "n_samples": len(samples),
        "t1_day_len": len(t1_day_hits) * 50.0,
        "t1_night_len": len(t1_night_hits) * 50.0,
        "creep_day_len": len(creep_day_hits) * 50.0,
        "creep_night_len": len(creep_night_hits) * 50.0,
        "any_day_len": len(any_day_hits) * 50.0,
        "t1_day_segs": to_segments(t1_day_hits),
        "creep_day_segs": to_segments(creep_day_hits),
        "any_day_segs": to_segments(any_day_hits),
    }


def simplify_waypoints(dmap: DotaMap, path, max_wps=4):
    """用贪心直通可见跳跃把 A* 网格路径压缩为最少的可直通路点"""
    if len(path) <= 2:
        return []
    # 先抽稀到每 96 码一个候选点
    cands = [path[0]]
    for p in path[1:-1]:
        if math.hypot(p[0] - cands[-1][0], p[1] - cands[-1][1]) >= 96.0:
            cands.append(p)
    cands.append(path[-1])

    kept = [cands[0]]
    i = 0
    while i < len(cands) - 1:
        # 找最远且直通可走的点
        best = i + 1
        for j in range(len(cands) - 1, i, -1):
            if dmap.straight_walkable(cands[i][0], cands[i][1], cands[j][0], cands[j][1], step=16.0):
                best = j
                break
        kept.append(cands[best])
        i = best
    # 去掉起点和终点，返回中间路点
    wps = kept[1:-1]
    # 若超过 max_wps，尽量合并弯曲最小的点（保持直通或无额外暴露）
    return [(round(x), round(y)) for x, y in wps]


def main():
    dmap = DotaMap()
    lines = []
    lines.append(f"=== DotA 6.83d 地图加载完成 ===")
    lines.append(f"w3e: {dmap.w3e['w']}x{dmap.w3e['h']}, center=({dmap.cx}, {dmap.cy})")
    lines.append(f"wpm: {dmap.pw}x{dmap.ph} (每格 32 码)")
    lines.append(f"树木数量: {len(dmap.trees)} (ATtr/NTtw/NTtc), 视线阻挡物: {len(dmap.los_blocks)} (YTlb/YTfb/YTpb)")
    lines.append(f"wpm 原生已标不可走的树木占比: {dmap.tree_wpm_blocked_ratio*100:.1f}%")
    lines.append(f"悬崖层检查: 近卫中一塔={dmap.cliff_at(*RAD_MID_T1)}, 天灾中一塔={dmap.cliff_at(*DIRE_MID_T1)}, "
                 f"中路交战={dmap.cliff_at(*MID_MEET)}, 上符={dmap.cliff_at(*TOP_RUNE)}, 下符={dmap.cliff_at(*BOT_RUNE)}")
    lines.append("")

    # 裁剪搜索区域：覆盖中路、上下符点、双野区（世界坐标 [-4500, 4500] x [-4500, 3500]）
    bx0, by0 = dmap.world_to_cell(-4200, -4400)
    bx1, by1 = dmap.world_to_cell(4400, 3200)
    bbox = (max(0, bx0), min(dmap.pw - 1, bx1), max(0, by0), min(dmap.ph - 1, by1))

    # 敌方中路小兵交战点模型：河道交战中心 (-450, -450) 及敌侧前排小兵（向敌方偏移 180 码）
    creeps_for_team = {
        "radiant": [(-450.0, -450.0), (-320.0, -320.0)],  # 近卫面对的天灾兵
        "dire": [(-450.0, -450.0), (-580.0, -580.0)],     # 天灾面对的近卫兵
    }

    svg_data = {}

    for key, cfg in CLAUDE_ROUTES.items():
        start = cfg["start"]
        goal = cfg["goal"]
        enemy_t1 = cfg["enemy_t1"]
        creeps = creeps_for_team[cfg["team"]]
        wps = cfg["wps"]

        lines.append("=" * 80)
        lines.append(f"【{cfg['name']}】 ({key}) | 起点 {start} → 终点 {goal} | 敌方中一塔 {enemy_t1}")
        lines.append("-" * 80)

        # A. 直线可行最短路径（War3 直接右键符点的真实路径）
        direct_path = dmap.astar(start, goal, bbox=bbox)
        direct_vis = eval_route_visibility(dmap, direct_path, enemy_t1, creeps)
        lines.append(f"[基线：直接右键符点 A*] 路程={direct_vis['total_len']:.0f} 码 ({direct_vis['total_len']/SF_SPEED:.2f}s)")
        lines.append(f"  白天塔暴露={direct_vis['t1_day_len']:.0f} 码, 夜晚塔暴露={direct_vis['t1_night_len']:.0f} 码, "
                     f"中路兵暴露(白)={direct_vis['creep_day_len']:.0f} 码, 合并白天暴露={direct_vis['any_day_len']:.0f} 码")
        if direct_vis["t1_day_segs"]:
            lines.append(f"  塔白天暴露段: {[(round(a), round(b), (round(p1[0]), round(p1[1])), (round(p2[0]), round(p2[1]))) for a,b,p1,p2 in direct_vis['t1_day_segs']]}")

        # B. 核验 Claude 现有路点可走性 + 实际 A* 拼接轨迹
        full_pts = [start] + wps + [goal]
        lines.append(f"\n[Claude 现有路点核验] 路点: {wps}")
        for idx, (wx, wy) in enumerate(wps):
            ok = dmap.is_walkable(wx, wy)
            cl = dmap.cliff_at(wx, wy)
            dt1 = math.hypot(wx - enemy_t1[0], wy - enemy_t1[1])
            vis_td, why_td = dmap.has_los(enemy_t1[0], enemy_t1[1], wx, wy, TOWER_DAY_SIGHT)
            lines.append(f"  WP{idx+1} ({wx:.0f}, {wy:.0f}): walkable={ok}, cliff={cl}, dist_T1={dt1:.0f}, T1_day_vis={vis_td} ({why_td})")

        claude_actual_path = []
        for i in range(len(full_pts) - 1):
            a, b = full_pts[i], full_pts[i + 1]
            straight_ok = dmap.straight_walkable(a[0], a[1], b[0], b[1])
            seg_path = dmap.astar(a, b, bbox=bbox)
            s_dist = math.hypot(b[0] - a[0], b[1] - a[1])
            a_dist = path_length(seg_path)
            detour_ratio = a_dist / max(1.0, s_dist)
            # 找偏离直线最远的点（看 War3 寻路往哪绕）
            max_dev = 0.0
            dev_pt = a
            vx, vy = b[0] - a[0], b[1] - a[1]
            l2 = max(1.0, vx * vx + vy * vy)
            for px, py in seg_path:
                t = max(0.0, min(1.0, ((px - a[0]) * vx + (py - a[1]) * vy) / l2))
                dev = math.hypot(px - (a[0] + t * vx), py - (a[1] + t * vy))
                if dev > max_dev:
                    max_dev = dev
                    dev_pt = (px, py)
            lines.append(
                f"  段 {i+1} ({a[0]:.0f},{a[1]:.0f})->({b[0]:.0f},{b[1]:.0f}): "
                f"直通={straight_ok}, 直线={s_dist:.0f}, A*={a_dist:.0f} (绕行比 {detour_ratio:.2f}x), "
                f"最大偏离={max_dev:.0f} 码 @ ({dev_pt[0]:.0f},{dev_pt[1]:.0f})"
            )
            if claude_actual_path and seg_path:
                claude_actual_path.extend(seg_path[1:])
            else:
                claude_actual_path.extend(seg_path)

        claude_vis = eval_route_visibility(dmap, claude_actual_path, enemy_t1, creeps)
        lines.append(f"  [Claude 实际 A* 总览] 路程={claude_vis['total_len']:.0f} 码 ({claude_vis['total_len']/SF_SPEED:.2f}s, "
                     f"比直线多 {(claude_vis['total_len']-direct_vis['total_len'])/SF_SPEED:+.2f}s)")
        lines.append(f"  白天塔暴露={claude_vis['t1_day_len']:.0f} 码, 夜晚塔暴露={claude_vis['t1_night_len']:.0f} 码, "
                     f"中路兵暴露(白)={claude_vis['creep_day_len']:.0f} 码, 合并白天暴露={claude_vis['any_day_len']:.0f} 码")
        if claude_vis["t1_day_segs"]:
            lines.append(f"  塔白天暴露段: {[(round(a), round(b), (round(p1[0]), round(p1[1])), (round(p2[0]), round(p2[1]))) for a,b,p1,p2 in claude_vis['t1_day_segs']]}")
        if claude_vis["creep_day_segs"]:
            lines.append(f"  兵线白天暴露段: {[(round(a), round(b), (round(p1[0]), round(p1[1])), (round(p2[0]), round(p2[1]))) for a,b,p1,p2 in claude_vis['creep_day_segs']]}")

        # C. 视野惩罚 A* 寻找更优隐蔽路线
        # 预计算 bbox 内每格的视野代价表（极快）
        vis_cache = {}
        def stealth_cost(nx, ny):
            cid = ny * dmap.pw + nx
            if cid in vis_cache:
                return vis_cache[cid]
            wx, wy = dmap.cell_to_world(nx, ny)
            c = 1.0
            # 绝对避开敌方一塔白天视野（权重 x80）
            if math.hypot(wx - enemy_t1[0], wy - enemy_t1[1]) <= TOWER_DAY_SIGHT + 64.0:
                v_td, _ = dmap.has_los(enemy_t1[0], enemy_t1[1], wx, wy, TOWER_DAY_SIGHT + 32.0)
                if v_td:
                    c += 80.0
                else:
                    # 在 1900 圈内但被树/高地挡住，给极轻微安全余量惩罚，优先走完全出圈或深林后
                    c += 0.3
            # 避开中路小兵视野（权重 x15）
            for cx, cy in creeps:
                if math.hypot(wx - cx, wy - cy) <= CREEP_DAY_SIGHT + 64.0:
                    if dmap.has_los(cx, cy, wx, wy, CREEP_DAY_SIGHT + 32.0)[0]:
                        c += 15.0
                        break
            # 轻度远离中路河道交战点（1000 码内小幅加权，促使贴树/走野区）
            d_mid = math.hypot(wx - MID_MEET[0], wy - MID_MEET[1])
            if d_mid < 1000.0:
                c += 0.4 * (1.0 - d_mid / 1000.0)
            vis_cache[cid] = c
            return c

        opt_raw = dmap.astar(start, goal, cost_fn=stealth_cost, bbox=bbox)
        opt_wps = simplify_waypoints(dmap, opt_raw)

        # 用简化路点按实际 War3 A* 拼接复核（确保不因简化重新绕进视野）
        opt_pts_all = [start] + opt_wps + [goal]
        opt_actual = []
        for i in range(len(opt_pts_all) - 1):
            seg = dmap.astar(opt_pts_all[i], opt_pts_all[i + 1], bbox=bbox)
            if opt_actual and seg:
                opt_actual.extend(seg[1:])
            else:
                opt_actual.extend(seg)

        opt_vis = eval_route_visibility(dmap, opt_actual, enemy_t1, creeps)
        extra_dist = opt_vis["total_len"] - direct_vis["total_len"]
        extra_sec = extra_dist / SF_SPEED

        lines.append(f"\n[推荐更优隐蔽路线] 简化路点 ({len(opt_wps)} 个): {opt_wps}")
        lines.append(f"  路程={opt_vis['total_len']:.0f} 码 ({opt_vis['total_len']/SF_SPEED:.2f}s), "
                     f"比直线多 {extra_dist:+.0f} 码 ({extra_sec:+.2f}s @ 移速305)")
        lines.append(f"  白天塔暴露={opt_vis['t1_day_len']:.0f} 码, 夜晚塔暴露={opt_vis['t1_night_len']:.0f} 码, "
                     f"中路兵暴露(白)={opt_vis['creep_day_len']:.0f} 码, 合并白天暴露={opt_vis['any_day_len']:.0f} 码")
        if opt_vis["t1_day_segs"]:
            lines.append(f"  塔白天暴露段: {[(round(a), round(b), (round(p1[0]), round(p1[1])), (round(p2[0]), round(p2[1]))) for a,b,p1,p2 in opt_vis['t1_day_segs']]}")
        if opt_vis["any_day_segs"]:
            lines.append(f"  合并白天暴露段: {[(round(a), round(b), (round(p1[0]), round(p1[1])), (round(p2[0]), round(p2[1]))) for a,b,p1,p2 in opt_vis['any_day_segs']]}")

        # 校验推荐路点每段是否全部直通
        seg_checks = []
        for i in range(len(opt_pts_all) - 1):
            a, b = opt_pts_all[i], opt_pts_all[i + 1]
            ok = dmap.straight_walkable(a[0], a[1], b[0], b[1])
            seg_checks.append(ok)
        lines.append(f"  各段直通核验: {seg_checks}")

        svg_data[key] = {
            "cfg": cfg,
            "direct": direct_path,
            "claude": claude_actual_path,
            "opt": opt_actual,
            "opt_wps": opt_wps,
        }

    # 保存文本报告
    rep_path = OUT_DIR / "stealth_routes_report.txt"
    rep_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(lines)} lines to {rep_path}")

    # 生成矢量 SVG 叠图（展示地形、树木、双方中一塔白天视野、Claude 路线 vs 推荐隐蔽路线）
    write_svg_overlay(dmap, svg_data, OUT_DIR / "stealth_routes_overlay.svg")
    print(f"Wrote SVG overlay to {OUT_DIR / 'stealth_routes_overlay.svg'}")


def write_svg_overlay(dmap: DotaMap, svg_data: dict, out_path: Path):
    """生成中路 + 上下符点区域的 SVG 通行/树木/视野/路线叠图"""
    xmin, xmax = -3800.0, 4000.0
    ymin, ymax = -4200.0, 2600.0
    scale = 0.14  # 1000 码 = 140px
    W = int((xmax - xmin) * scale)
    H = int((ymax - ymin) * scale)

    def sx(x):
        return (x - xmin) * scale

    def sy(y):
        return (ymax - y) * scale  # SVG Y 轴向下

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="#12161c"/>',
    ]

    # 1. 绘制 128x128 悬崖层级底图
    cliff_colors = {7: "#152536", 8: "#1c334a", 9: "#26382b", 10: "#354a36", 11: "#455942"}
    for j in range(dmap.w3e["h"]):
        wy = dmap.cy + j * 128.0
        if not (ymin - 128 <= wy <= ymax + 128):
            continue
        for i in range(dmap.w3e["w"]):
            wx = dmap.cx + i * 128.0
            if not (xmin - 128 <= wx <= xmax + 128):
                continue
            cl = dmap.w3e["cliff"][j][i]
            col = cliff_colors.get(cl, "#2b2f36")
            x0 = sx(wx - 64)
            y0 = sy(wy + 64)
            sz = 128.0 * scale + 0.5
            s.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{sz:.1f}" height="{sz:.1f}" fill="{col}"/>')

    # 2. 绘制树木
    for tx, ty, _ in dmap.trees:
        if xmin <= tx <= xmax and ymin <= ty <= ymax:
            s.append(f'<circle cx="{sx(tx):.1f}" cy="{sy(ty):.1f}" r="{36*scale:.1f}" fill="#1b5e20" opacity="0.85"/>')

    # 3. 敌方中一塔白天 1900 / 夜晚 800 视野圆
    for label, (tx, ty), col in [
        ("Radiant Mid T1", RAD_MID_T1, "#4fc3f7"),
        ("Dire Mid T1", DIRE_MID_T1, "#ef5350"),
    ]:
        s.append(f'<circle cx="{sx(tx):.1f}" cy="{sy(ty):.1f}" r="{TOWER_DAY_SIGHT*scale:.1f}" fill="{col}" fill-opacity="0.08" stroke="{col}" stroke-dasharray="6,4" stroke-width="1.5"/>')
        s.append(f'<circle cx="{sx(tx):.1f}" cy="{sy(ty):.1f}" r="{TOWER_NIGHT_SIGHT*scale:.1f}" fill="none" stroke="{col}" stroke-dasharray="2,3" stroke-width="1.0"/>')
        s.append(f'<circle cx="{sx(tx):.1f}" cy="{sy(ty):.1f}" r="6" fill="{col}"/>')
        s.append(f'<text x="{sx(tx)+8:.1f}" y="{sy(ty)-6:.1f}" fill="{col}" font-size="12" font-family="sans-serif">{label}</text>')

    # 4. 中路交战小兵视野圆 (850)
    s.append(f'<circle cx="{sx(MID_MEET[0]):.1f}" cy="{sy(MID_MEET[1]):.1f}" r="{CREEP_DAY_SIGHT*scale:.1f}" fill="#ffd54f" fill-opacity="0.06" stroke="#ffd54f" stroke-dasharray="4,4" stroke-width="1.2"/>')

    # 5. 上下符点
    for name, (rx, ry) in [("Top Rune (-2352,1648)", TOP_RUNE), ("Bot Rune (3008,-2832)", BOT_RUNE)]:
        s.append(f'<circle cx="{sx(rx):.1f}" cy="{sy(ry):.1f}" r="7" fill="#ffeb3b" stroke="#000" stroke-width="1.5"/>')
        s.append(f'<text x="{sx(rx)+9:.1f}" y="{sy(ry)+4:.1f}" fill="#ffeb3b" font-size="12" font-family="sans-serif">{name}</text>')

    # 6. 绘制路线：Claude 现有路线（橙红虚线）vs 推荐隐蔽路线（青绿实线）
    def poly(pts, color, width, dash=""):
        if not pts:
            return ""
        d = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in pts[::2] + [pts[-1]])
        da = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<polyline points="{d}" fill="none" stroke="{color}" stroke-width="{width}"{da} stroke-linecap="round"/>'

    opt_colors = {"rad_bot": "#00e676", "rad_top": "#00e5ff", "dire_top": "#b388ff", "dire_bot": "#ffab40"}
    for key, d in svg_data.items():
        s.append(poly(d["claude"], "#ff5252", 2.0, "6,4"))
        s.append(poly(d["opt"], opt_colors[key], 3.0))
        for wx, wy in d["opt_wps"]:
            s.append(f'<circle cx="{sx(wx):.1f}" cy="{sy(wy):.1f}" r="4.5" fill="{opt_colors[key]}" stroke="#000" stroke-width="1"/>')
            s.append(f'<text x="{sx(wx)+6:.1f}" y="{sy(wy)-4:.1f}" fill="#fff" font-size="10" font-family="monospace">({wx},{wy})</text>')

    # 图例
    s.append('<rect x="12" y="12" width="320" height="96" rx="6" fill="#000" fill-opacity="0.72"/>')
    s.append('<text x="22" y="32" fill="#ff5252" font-size="12" font-family="sans-serif">--- 红虚线: Claude 现有 aiStealthNext 实际 A* 路线</text>')
    s.append('<text x="22" y="50" fill="#00e676" font-size="12" font-family="sans-serif">─── 绿/青/紫/橙实线: 推荐隐蔽路线 (附路点坐标)</text>')
    s.append('<text x="22" y="68" fill="#4fc3f7" font-size="12" font-family="sans-serif">○ 蓝/红虚圆: 敌一塔白天 1900 / 夜晚 800 视野</text>')
    s.append('<text x="22" y="86" fill="#ffd54f" font-size="12" font-family="sans-serif">○ 黄虚圆: 中路河道兵线 850 视野 | 深绿点: 树木</text>')
    s.append("</svg>")
    out_path.write_text("\n".join(s), encoding="utf-8")


if __name__ == "__main__":
    main()
