"""Extract per-hero movement / attack stats for the 112 pickable DotA 6.83d heroes.

usage: python -I hero_stats.py <map_dir> <launcher_shared_dir> <out_json>
  map_dir:  units SLK / *UnitFunc.txt / *UnitStrings.txt extracted from DotA v6.83d.w3x
            (e.g. War3Analysis/artifacts/ward-deward/map)
  launcher_shared_dir: War3Launcher/shared (DotaHeroSkillAbbrev.h = hero unit IDs in pick order 1..112,
            dota_hero_abbrev.md = abbreviation + Chinese name per pick number)
Model: Claude Opus 5.5, 2026-11-20. Purpose: hero difficulty inputs for the AI scoring system.
"""
import sys, os, re, json, glob


def read_slk(path):
    rows, cur_y = {}, 0
    with open(path, encoding='latin-1') as f:
        for line in f:
            line = line.rstrip('\r\n')
            if not line.startswith('C;'):
                continue
            x = y = val = None
            for part in line.split(';')[1:]:
                if part.startswith('X'):
                    x = int(part[1:])
                elif part.startswith('Y'):
                    y = int(part[1:])
                elif part.startswith('K'):
                    val = part[1:]
            if y is not None:
                cur_y = y
                if x is None:
                    x = 1            # 优化过的 SLK：新行只写 Y，列默认是第 1 列（单位 ID），如 C;Y349;K"H001"
            if x is None or val is None:
                continue
            if len(val) >= 2 and val[0] == '"' and val[-1] == '"':
                val = val[1:-1]
            rows.setdefault(cur_y, {})[x] = val
    header = rows.get(1, {})
    table = {}
    for y, r in rows.items():
        if y == 1 or 1 not in r:
            continue
        table[r[1]] = {header[x]: v for x, v in r.items() if x in header}
    return table


def read_ini_sections(paths, keys):
    """[ID] blocks in *UnitFunc.txt; first value wins."""
    out = {}
    for p in paths:
        cur = None
        with open(p, encoding='latin-1') as f:
            for line in f:
                line = line.strip()
                m = re.match(r'^\[(\w{4})\]$', line)
                if m:
                    cur = m.group(1)
                    continue
                if not cur or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                if k in keys:
                    out.setdefault(cur, {}).setdefault(k, v.split(',')[0])
    return out


def fnum(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def main():
    map_dir, shared, out = sys.argv[1], sys.argv[2], sys.argv[3]
    ids = re.findall(r'^    \{ DOTA_FOURCC\("(\w{4})"\)', open(os.path.join(shared, 'DotaHeroSkillAbbrev.h'), encoding='utf-8').read(), re.M)
    abbr = {}
    for m in re.finditer(r'^\| *(\d+) *\| *`([^`]+)` *\| *([^|]+?) *\|', open(os.path.join(shared, 'dota_hero_abbrev.md'), encoding='utf-8').read(), re.M):
        abbr[int(m.group(1))] = (m.group(2), m.group(3))
    # 分层：游戏基础表（war3 → War3x → War3Patch）在下，地图表在上；地图只写改过的行 / 列，没写的取游戏默认值
    base_root = sys.argv[4] if len(sys.argv) > 4 else None
    layers = []
    if base_root:
        layers += [os.path.join(base_root, m) for m in ('war3.mpq', 'War3x.mpq', 'War3Patch.mpq')]
    layers.append(map_dir)

    def merged(slk):
        t = {}
        for d in layers:
            p = os.path.join(d, slk)
            if not os.path.exists(p):
                continue
            for uid, row in read_slk(p).items():
                t.setdefault(uid, {}).update({k: v for k, v in row.items() if v not in ('', '-', '_')})
        return t

    bal, wep, dat = merged('Units_UnitBalance.slk'), merged('Units_UnitWeapons.slk'), merged('Units_UnitData.slk')
    func = {}
    for d in layers:   # 后面的层覆盖前面的
        for uid, kv in read_ini_sections(glob.glob(os.path.join(d, '*UnitFunc.txt')), {'Missilespeed'}).items():
            func.setdefault(uid, {}).update(kv)
    heroes = []
    for i, uid in enumerate(ids, 1):
        b, w, d = bal.get(uid, {}), wep.get(uid, {}), dat.get(uid, {})
        rng = fnum(w.get('rangeN1'))
        ab, zh = abbr.get(i, ('', ''))
        heroes.append({
            'index': i, 'id': uid, 'abbrev': ab, 'name': zh,
            'primary': b.get('Primary', ''),
            'moveSpeed': fnum(b.get('spd')),
            'turnRate': fnum(d.get('turnRate')),
            'collision': fnum(d.get('collision')),
            'range': rng,
            'ranged': rng > 200.0,           # 射程 ≤ 200 按近战（有的近战英雄武器类型是 missile、射程 140）
            'bat': fnum(w.get('cool1')),
            'damagePoint': fnum(w.get('dmgpt1')),
            'backswing': fnum(w.get('backSw1')),
            'missileSpeed': fnum(func.get(uid, {}).get('Missilespeed')),
            'weaponType': w.get('weapTp1', ''),
            'dice': fnum(w.get('dice1')), 'sides': fnum(w.get('sides1')), 'dmgPlus': fnum(w.get('dmgplus1')),
        })
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(heroes, f, ensure_ascii=False, indent=1)
    missing = [h['id'] for h in heroes if h['moveSpeed'] == 0]
    print('heroes:', len(heroes), 'missing stats:', missing)
    ms = sorted(h['moveSpeed'] for h in heroes if h['moveSpeed'] > 0)
    print('moveSpeed min %.0f p25 %.0f median %.0f p75 %.0f max %.0f' % (ms[0], ms[len(ms) // 4], ms[len(ms) // 2], ms[3 * len(ms) // 4], ms[-1]))
    for k in ('cm', 'wr', 'sniper', 'jugg', 'pudge', 'sf'):
        for h in heroes:
            if h['abbrev'] == k:
                print({x: h[x] for x in ('index', 'id', 'abbrev', 'name', 'moveSpeed', 'range', 'bat', 'damagePoint', 'missileSpeed', 'turnRate', 'collision')})


if __name__ == '__main__':
    main()
