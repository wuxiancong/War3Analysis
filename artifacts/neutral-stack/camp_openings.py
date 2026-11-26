r"""DotA 6.83d 十二野点「开口方向」逆向（离线）：
从每个野点出生中心向 72 个方向（每 5°）做射线，按 war3map.wpm 通行位 + war3map.doo 树木（2x2 格）判断能走多远、
站在哪里还能看到出生点（悬崖层不低于出生点）。能走出封野盒 + 250 且可视站位 ≥ 500 的方向 = 开口。

输入：War3Analysis/artifacts/ward-deward/map（wpm / w3e / doo），封野盒与出生点见 dota-neutral-camp-spawn-box.md
输出：camp_openings.json（给 hook 生成表用）+ 控制台摘要

    python -I camp_openings.py
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'stealth-rune-route'))
from analyze_stealth_routes import DotaMap  # noqa: E402

# 封野盒 check rect 与出生中心 spawn（war3map_9.j Rect；dota-neutral-camp-spawn-box.md 第三节）
CAMPS = [
    (1, 'Q4/H4', (3904, -1408, 4960, -640), (4640, -976)),
    (2, 'U4/Z4', (-3552, -768, -2528, 320), (-3216, -256)),
    (3, 'I5/V4', (1056, -5216, 2368, -3744), (1584, -3984)),
    (4, 'O5/W4', (-5120, 3008, -3648, 4320), (-4512, 3408)),
    (5, 'A5/X4', (-3456, 3808, -2656, 4864), (-3088, 4256)),
    (6, 'B5/Y4', (2272, -6080, 3776, -4928), (2960, -5008)),
    (7, 'C5/J4', (-1888, 2208, -992, 3040), (-1648, 2352)),
    (8, 'E5/K4', (2592, -4800, 3744, -3328), (3072, -3712)),
    (9, 'D5/L4', (416, 2624, 1632, 3648), (1232, 3040)),
    (10, 'F5/M4', (-1024, -3808, 192, -2752), (-416, -3584)),
    (11, 'Z5/V5', (-800, 3072, 64, 4032), (-288, 3456)),
    (12, 'W5/X5', (-1728, -5056, -768, -3840), (-1056, -4592)),
]
# 旧文档按「最近的封野盒边」给的建议方向（不看树 / 悬崖），用来对比
DOC_DIR = {1: 'E', 2: 'W', 3: 'N', 4: 'S', 5: 'W', 6: 'N', 7: 'S', 8: 'N', 9: 'E', 10: 'S', 11: 'E', 12: 'E'}
DIR_DEG = {'E': 0, 'N': 90, 'W': 180, 'S': 270}
# 2026-11-24 用户实机标记（冰女，近卫野区）里能确定野点的三组 A→B
USER_MARKS = {12: ((-1451, -4058), (-2642, -3792)), 10: ((-309, -2941), (-659, -1533)), 6: ((3074, -5695), (3638, -6563))}

STEP_DEG = 5
MAX_DIST = 1400.0
SAMPLE = 16.0
SIDE = 24.0           # 射线两侧各 24 码也要能走（近似单位碰撞体积 / 野怪成群通过）
EXIT_MARGIN = 250.0   # 要能走出封野盒边 + 250，野怪才离开检测区
MIN_STAND = 500.0     # 至少能在 500 外（≈ 射程）站着看见出生点


def walkable(m, x, y):
    gx, gy = m.world_to_cell(x, y)
    if not (0 <= gx < m.pw and 0 <= gy < m.ph):
        return False
    return m.walk_with_trees[gy * m.pw + gx] == 1


def box_exit(spawn, box, ang):
    """从出生点沿 ang 方向走出封野盒的距离"""
    x0, y0 = spawn
    minx, miny, maxx, maxy = box
    dx, dy = math.cos(ang), math.sin(ang)
    ts = []
    if dx > 1e-6: ts.append((maxx - x0) / dx)
    if dx < -1e-6: ts.append((minx - x0) / dx)
    if dy > 1e-6: ts.append((maxy - y0) / dy)
    if dy < -1e-6: ts.append((miny - y0) / dy)
    return min(t for t in ts if t >= 0)


def cast(m, spawn, ang, base_cliff):
    """返回 (clear, visible)：能走多远；在多远以内站着仍不低于出生点悬崖层（看得见）"""
    dx, dy = math.cos(ang), math.sin(ang)
    px, py = -dy, dx
    clear = 0.0
    visible = 0.0
    seen_ok = True
    d = SAMPLE
    while d <= MAX_DIST:
        x, y = spawn[0] + dx * d, spawn[1] + dy * d
        if not (walkable(m, x, y) and walkable(m, x + px * SIDE, y + py * SIDE) and walkable(m, x - px * SIDE, y - py * SIDE)):
            break
        clear = d
        if seen_ok and m.cliff_at(x, y) >= base_cliff:
            visible = d
        else:
            seen_ok = False
        d += SAMPLE
    return clear, visible


def angle_of(dx, dy):
    return math.degrees(math.atan2(dy, dx)) % 360


def compass(deg):
    names = ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']
    return names[int(((deg % 360) + 22.5) // 45) % 8]


def main():
    m = DotaMap()
    out = []
    for cid, name, box, spawn in CAMPS:
        base_cliff = m.cliff_at(*spawn)
        rays = []
        for k in range(0, 360, STEP_DEG):
            ang = math.radians(k)
            clear, visible = cast(m, spawn, ang, base_cliff)
            ex = box_exit(spawn, box, ang)
            ok = clear >= ex + EXIT_MARGIN and visible >= MIN_STAND
            rays.append({'deg': k, 'clear': round(clear), 'visible': round(visible), 'exit': round(ex), 'open': ok})
        # 连续开口方向合并（首尾相接）
        n = len(rays)
        groups = []
        if all(r['open'] for r in rays):
            groups = [list(range(n))]
        else:
            start = next(i for i in range(n) if not rays[i]['open'])
            cur = []
            for j in range(1, n + 1):
                i = (start + j) % n
                if rays[i]['open']:
                    cur.append(i)
                elif cur:
                    groups.append(cur)
                    cur = []
            if cur:
                groups.append(cur)
        openings = []
        for g in groups:
            degs = [rays[i]['deg'] for i in g]
            first, last = degs[0], degs[-1]
            width = (last - first) % 360 + STEP_DEG
            center = (first + (width - STEP_DEG) / 2) % 360
            openings.append({
                'center': round(center, 1), 'width': width, 'from': first, 'to': last,
                'minClear': min(rays[i]['clear'] for i in g), 'minVisible': min(rays[i]['visible'] for i in g),
                'maxExit': max(rays[i]['exit'] for i in g), 'compass': compass(center),
            })
        openings.sort(key=lambda o: -o['width'])
        rec = {'id': cid, 'name': name, 'spawn': spawn, 'box': box, 'spawnCliff': base_cliff,
               'openings': openings, 'rays': rays, 'docDir': DOC_DIR[cid]}
        if cid in USER_MARKS:
            a, b = USER_MARKS[cid]
            rec['userA'] = {'deg': round(angle_of(a[0] - spawn[0], a[1] - spawn[1]), 1), 'dist': round(math.dist(a, spawn))}
            rec['userB'] = {'deg': round(angle_of(b[0] - spawn[0], b[1] - spawn[1]), 1), 'dist': round(math.dist(b, spawn))}
        out.append(rec)

    (HERE / 'camp_openings.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    for r in out:
        ops = '; '.join('%s %.0f°(%d°~%d°, 宽 %d°, 可走≥%d 可视≥%d)' % (o['compass'], o['center'], o['from'], o['to'], o['width'],
                                                                      o['minClear'], o['minVisible']) for o in r['openings']) or '无'
        doc_deg = DIR_DEG[r['docDir']]
        doc_ray = next(x for x in r['rays'] if x['deg'] == doc_deg)
        extra = ''
        if 'userA' in r:
            ua = r['userA']
            ua_ray = min(r['rays'], key=lambda x: abs((x['deg'] - ua['deg'] + 180) % 360 - 180))
            extra = ' | 用户 A %.0f° 距 %d（该方向%s）B %.0f°' % (ua['deg'], ua['dist'], '开口' if ua_ray['open'] else '不开',
                                                              r['userB']['deg'])
        print('#%-2d %-6s 悬崖层 %d | 开口：%s | 旧文档 %s（该方向%s：可走 %d 出盒 %d）%s' % (
            r['id'], r['name'], r['spawnCliff'], ops, r['docDir'], '开口' if doc_ray['open'] else '不开',
            doc_ray['clear'], doc_ray['exit'], extra))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
