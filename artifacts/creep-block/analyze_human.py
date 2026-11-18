import re, sys, math, statistics as S

lines = open(sys.argv[1], encoding='utf-8-sig').read().splitlines()
pat = re.compile(r'真人坐标 第 (\d+) 波 t=([\d.]+) 英雄 (-?\d+),(-?\d+) \| 兵(.*)$')
home = (-4575.0, -5138.0)
L = math.hypot(*home)
dx, dy = -home[0] / L, -home[1] / L          # lane direction (toward map center)
def proj(x, y): return (x - home[0]) * dx + (y - home[1]) * dy
def lat(x, y):  return (x - home[0]) * (-dy) + (y - home[1]) * dx

waves = {}
for ln in lines:
    m = pat.search(ln)
    if not m: continue
    w, t, hx, hy, rest = int(m[1]), float(m[2]), float(m[3]), float(m[4]), m[5]
    creeps = {}
    for cm in re.finditer(r'([0-9A-F]{4}):(-?\d+),(-?\d+)', rest):
        creeps[cm[1]] = (float(cm[2]), float(cm[3]))
    waves.setdefault(w, []).append((t, hx, hy, creeps))

def fmt(v): return f'{v:7.1f}'
for w, rows in sorted(waves.items()):
    print(f'\n=== wave {w}: {len(rows)} samples, t {rows[0][0]:.2f}..{rows[-1][0]:.2f}')
    print('   t  | heroP  heroL | frontP frontL | ahead  latOff | spreadL | heroSpd frontSpd | nearest creep dist')
    prev = None
    stops = 0; still_run = 0
    speeds = []
    for i, (t, hx, hy, cr) in enumerate(rows):
        if not cr: continue
        hp, hl = proj(hx, hy), lat(hx, hy)
        cps = [(proj(*p), lat(*p), k) for k, p in cr.items()]
        fp, fl, fk = max(cps)
        spread = max(c[1] for c in cps) - min(c[1] for c in cps)
        near = min(math.hypot(p[0] - hx, p[1] - hy) for p in cr.values())
        hs = fs = float('nan')
        if prev:
            dt = t - prev[0]
            if dt > 0:
                hs = math.hypot(hx - prev[1], hy - prev[2]) / dt
                if fk in prev[3]:
                    fs = math.hypot(cr[fk][0] - prev[3][fk][0], cr[fk][1] - prev[3][fk][1]) / dt
        if hs == hs:
            speeds.append(hs)
            if hs < 60: still_run += 1
            else:
                if still_run >= 2: stops += 1
                still_run = 0
        if i % 6 == 0:
            print(f'{t:5.2f} | {fmt(hp)} {fmt(hl)} | {fmt(fp)} {fmt(fl)} | {fmt(hp-fp)} {fmt(hl-fl)} | {fmt(spread)} | {fmt(hs)} {fmt(fs)} | {fmt(near)}')
        prev = (t, hx, hy, cr)
    if speeds:
        print(f'  hero speed median {S.median(speeds):.0f}, share <60 (standing): {sum(s<60 for s in speeds)/len(speeds):.0%}, stop episodes (>=100ms still): {stops}')
