r"""DotA 6.83d 十二野点「开口 + 拉野路线」逆向（离线，寻路版）：
从野点出生中心在通行网格（war3map.wpm NoWalk 位 + war3map.doo 树木 2x2 格，再要求上下左右邻格可走 ≈ 单位碰撞宽度）
上做 BFS（8 邻接，按真实距离）。能走到「封野盒外 ≥ EXIT_MARGIN」且路程 ≤ MAX_PATH 的格子按方位角分组 = 开口；
每个开口取路程最短的出口格，回溯出路径：
  A（站位）= 路径上离出生点直线距离 STAND 左右、且到出生点视线不被树挡、悬崖层不低于出生点的点
  B（带到）= 出口格（已出封野盒 EXIT_MARGIN）
hook 每波随机选一个开口：站 A、:50~:53 打一下、走到 B。

    python -I camp_routes.py          # 输出 camp_routes.json 与 C++ 表（camp_routes_table.inc）
"""
import heapq
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'stealth-rune-route'))
from analyze_stealth_routes import DotaMap  # noqa: E402
from camp_openings import CAMPS, USER_MARKS, box_exit  # noqa: E402

EXIT_MARGIN = 200.0   # 出口格离封野盒至少这么远（野怪整组被带出盒）
MAX_PATH = 1500.0     # 出口格路程上限（太绕的不算开口：野怪追不了那么远、回巢也慢）
STAND = 520.0         # A 点离出生点的直线距离目标（远程射程 ~500~600；hook 再按真实射程沿 A→出生点方向调整）
SECTOR = 15           # 方位角分组粒度（度）
MERGE_GAP = 1         # 相邻扇区空 ≤ 1 个也算同一个开口
MAX_ROUTES = 6        # 每个野点最多给 hook 几条路线
OTHER_GAP = 300.0     # A / B 离「其他野点」封野盒至少这么远（2026-11-24 实测：贴着别的野点站会被别的野怪打死、把野拉进别的野点）
A_MIN, A_MAX = 480.0, 640.0   # A 离自己出生点的直线距离范围（实测 339 太近，野怪直接上来打）


def make_clear(m):
    """可通行且上下左右邻格可通行（≈ 单位能过、不贴树）"""
    w, h, g = m.pw, m.ph, m.walk_with_trees
    clear = bytearray(w * h)
    for y in range(1, h - 1):
        row = y * w
        for x in range(1, w - 1):
            i = row + x
            if g[i] and g[i - 1] and g[i + 1] and g[i - w] and g[i + w]:
                clear[i] = 1
    return clear


def los_clear(m, ax, ay, bx, by, base_cliff):
    """A→B 视线：途中不穿树 / YTlb，A 的悬崖层不低于出生点"""
    if m.cliff_at(ax, ay) < base_cliff:
        return False
    d = math.dist((ax, ay), (bx, by))
    n = max(1, int(d / 16))
    for k in range(1, n):
        x = ax + (bx - ax) * k / n
        y = ay + (by - ay) * k / n
        gx, gy = m.world_to_cell(x, y)
        if m.occ_grid[gy * m.pw + gx]:
            return False
    return True


def bfs(m, clear, spawn, limit):
    sx, sy = m.world_to_cell(*spawn)
    # 出生点本身可能贴着树：从它附近最近的可通行格开始
    best = None
    for r in range(0, 4):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                i = (sy + dy) * m.pw + sx + dx
                if clear[i] and best is None:
                    best = (sx + dx, sy + dy)
        if best:
            break
    sx, sy = best
    dist = {(sx, sy): 0.0}
    prev = {}
    pq = [(0.0, sx, sy)]
    steps = [(1, 0, 32.0), (-1, 0, 32.0), (0, 1, 32.0), (0, -1, 32.0),
             (1, 1, 45.25), (1, -1, 45.25), (-1, 1, 45.25), (-1, -1, 45.25)]
    while pq:
        d, x, y = heapq.heappop(pq)
        if d > dist.get((x, y), 1e18) or d > limit:
            continue
        for dx, dy, c in steps:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < m.pw and 0 <= ny < m.ph) or not clear[ny * m.pw + nx]:
                continue
            if dx and dy and not (clear[y * m.pw + nx] and clear[ny * m.pw + x]):
                continue   # 斜走不切角
            nd = d + c
            if nd < dist.get((nx, ny), 1e18):
                dist[(nx, ny)] = nd
                prev[(nx, ny)] = (x, y)
                heapq.heappush(pq, (nd, nx, ny))
    return dist, prev


def box_gap(box, x, y):
    minx, miny, maxx, maxy = box
    dx = max(minx - x, 0, x - maxx)
    dy = max(miny - y, 0, y - maxy)
    return math.hypot(dx, dy) if (dx or dy) else -1.0


def other_gap(cid, x, y):
    """点离其他野点封野盒的最近距离（在盒内 = -1）"""
    return min(box_gap(b, x, y) for c, _n, b, _s in CAMPS if c != cid)


def main():
    m = DotaMap()
    clear = make_clear(m)
    out = []
    for cid, name, box, spawn in CAMPS:
        base_cliff = m.cliff_at(*spawn)
        dist, prev = bfs(m, clear, spawn, MAX_PATH)
        # 出口格：已离开封野盒 EXIT_MARGIN
        exits = []
        for (gx, gy), d in dist.items():
            x, y = m.cell_to_world(gx, gy)
            if box_gap(box, x, y) >= EXIT_MARGIN and other_gap(cid, x, y) >= OTHER_GAP:
                ang = math.degrees(math.atan2(y - spawn[1], x - spawn[0])) % 360
                exits.append((d, ang, gx, gy))
        nsec = 360 // SECTOR
        best_in_sec = [None] * nsec
        for e in exits:
            s = int(e[1] // SECTOR) % nsec
            if best_in_sec[s] is None or e[0] < best_in_sec[s][0]:
                best_in_sec[s] = e
        # 相邻有出口的扇区合并成开口
        occupied = [b is not None for b in best_in_sec]
        groups = []
        if any(occupied):
            if all(occupied):
                groups = [list(range(nsec))]
            else:
                start = next(i for i in range(nsec) if not occupied[i])
                cur, gap = [], 0
                for j in range(1, nsec + 1):
                    i = (start + j) % nsec
                    if occupied[i]:
                        cur.append(i)
                        gap = 0
                    elif cur:
                        gap += 1
                        if gap > MERGE_GAP:
                            groups.append(cur)
                            cur, gap = [], 0
                if cur:
                    groups.append(cur)
        routes = []
        # 每个开口里每个有出口的扇区都出一条路线（开口内随机方向），A 点相近（< 150）的去重
        for g in groups:
          for s in g:
            if best_in_sec[s] is None:
                continue
            d, ang, gx, gy = best_in_sec[s]
            # 回溯路径（出生点 → 出口）
            path = [(gx, gy)]
            while path[-1] in prev:
                path.append(prev[path[-1]])
            path.reverse()
            pts = [m.cell_to_world(*c) for c in path]
            # A：路径上直线距离最接近 STAND、能看到出生点的点（优先不超过 STAND+80）
            cand = [p for p in pts if A_MIN <= math.dist(p, spawn) <= A_MAX and other_gap(cid, p[0], p[1]) >= OTHER_GAP
                    and los_clear(m, p[0], p[1], spawn[0], spawn[1], base_cliff)]
            if not cand:
                continue   # 这条路上没有合格站位：不出路线
            a = min(cand, key=lambda p: abs(math.dist(p, spawn) - STAND) + (200 if math.dist(p, spawn) > STAND + 80 else 0))
            b = m.cell_to_world(gx, gy)
            if any(math.dist(a, q['A']) < 150 for q in routes):
                continue
            sec_from = g[0] * SECTOR
            sec_to = (g[-1] + 1) * SECTOR
            routes.append({
                'opening': '%d°~%d°' % (sec_from, sec_to % 360 if sec_to % 360 else 360),
                'sectors': '%d°~%d°' % (s * SECTOR, (s + 1) * SECTOR),
                'A': [round(a[0]), round(a[1])], 'B': [round(b[0]), round(b[1])],
                'aDist': round(math.dist(a, spawn)), 'bPath': round(d),
                'aDeg': round(math.degrees(math.atan2(a[1] - spawn[1], a[0] - spawn[0])) % 360),
                'bDeg': round(ang), 'aSees': los_clear(m, a[0], a[1], spawn[0], spawn[1], base_cliff),
            })
        seen = [q for q in routes if q['aSees']]
        routes = (seen or routes)
        if len(routes) > MAX_ROUTES:   # 按方位均匀抽 MAX_ROUTES 条
            routes = sorted(routes, key=lambda q: q['aDeg'])
            routes = [routes[int(i * len(routes) / MAX_ROUTES)] for i in range(MAX_ROUTES)]
        rec = {'id': cid, 'name': name, 'spawn': spawn, 'box': box, 'routes': routes}
        if cid in USER_MARKS:
            ua, ub = USER_MARKS[cid]
            rec['user'] = {'A': ua, 'B': ub,
                           'aDeg': round(math.degrees(math.atan2(ua[1] - spawn[1], ua[0] - spawn[0])) % 360),
                           'bDeg': round(math.degrees(math.atan2(ub[1] - spawn[1], ub[0] - spawn[0])) % 360),
                           'nearestRouteA': round(min((math.dist(ua, r['A']) for r in routes), default=-1)),
                           'nearestRouteB': round(min((math.dist(ub, r['B']) for r in routes), default=-1))}
        out.append(rec)

    (HERE / 'camp_routes.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    lines = ['// 自动生成：War3Analysis/artifacts/neutral-stack/camp_routes.py（不要手改）',
             '// { 出生 x, y, 封野盒 minX, minY, maxX, maxY, 路线数, { A.x, A.y, B.x, B.y } x 6 }']
    for r in out:
        rs = ', '.join('{ %d.0f, %d.0f, %d.0f, %d.0f }' % (q['A'][0], q['A'][1], q['B'][0], q['B'][1]) for q in r['routes'][:MAX_ROUTES])
        pad = ', '.join(['{ 0, 0, 0, 0 }'] * (MAX_ROUTES - min(MAX_ROUTES, len(r['routes']))))
        lines.append('    { %d.0f, %d.0f, %d.0f, %d.0f, %d.0f, %d.0f, %d, { %s } },   // #%d %s' % (
            r['spawn'][0], r['spawn'][1], *r['box'], min(MAX_ROUTES, len(r['routes'])), ', '.join(x for x in (rs, pad) if x), r['id'], r['name']))
    (HERE / 'camp_routes_table.inc').write_text('\n'.join(lines) + '\n', encoding='utf-8')

    for r in out:
        desc = ' | '.join('%s A(%d,%d) %d°距%d%s → B(%d,%d) %d° 路程 %d' % (
            q['sectors'], *q['A'], q['aDeg'], q['aDist'], '' if q['aSees'] else '(看不见)', *q['B'], q['bDeg'], q['bPath'])
            for q in r['routes']) or '无开口'
        print('#%-2d %-6s %s' % (r['id'], r['name'], desc))
        if 'user' in r:
            u = r['user']
            print('     用户 A(%d,%d) %d° B(%d,%d) %d° | 最近路线 A 差 %d、B 差 %d' % (*u['A'], u['aDeg'], *u['B'], u['bDeg'],
                                                                               u['nearestRouteA'], u['nearestRouteB']))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
