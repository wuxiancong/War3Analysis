import re, sys, math, statistics as S
lines = open(sys.argv[1], encoding='utf-8-sig').read().splitlines()
pat = re.compile(r'真人坐标 第 (\d+) 波 t=([\d.]+) 英雄 (-?\d+),(-?\d+) \| 兵(.*)$')
home = (-4575.0, -5138.0); L = math.hypot(*home); dx, dy = -home[0]/L, -home[1]/L
P = lambda x, y: (x-home[0])*dx + (y-home[1])*dy
Q = lambda x, y: (x-home[0])*(-dy) + (y-home[1])*dx
good = {1, 5, 6, 7}
waves = {}
for ln in lines:
    m = pat.search(ln)
    if m and int(m[1]) in good:
        cr = {c[1]: (float(c[2]), float(c[3])) for c in re.finditer(r'([0-9A-F]{4}):(-?\d+),(-?\d+)', m[5])}
        waves.setdefault(int(m[1]), []).append((float(m[2]), float(m[3]), float(m[4]), cr))

def pct(a, p): a = sorted(a); return a[min(len(a)-1, int(p*len(a)))]
ahead, latoff, hspd, fspd, gap_when_start, start_pos = [], [], [], [], [], []
path = {}   # proj bucket -> lateral of front creep
for w, rows in waves.items():
    moved = False; prev = None
    for t, hx, hy, cr in rows:
        if not cr: continue
        cps = [(P(*p), Q(*p), k) for k, p in cr.items()]
        fp, fl, fk = max(cps)
        hp, hl = P(hx, hy), Q(hx, hy)
        for cp, cl, _ in cps:
            path.setdefault(int(cp // 200) * 200, []).append(cl)
        if prev:
            dt = t - prev[0]
            hs = math.hypot(hx-prev[1], hy-prev[2]) / dt
            if not moved and hs > 60:
                moved = True; gap_when_start.append(hp - fp); start_pos.append((round(hp), round(hl), round(t, 2)))
            if fk in prev[3]:
                fspd.append(math.hypot(cr[fk][0]-prev[3][fk][0], cr[fk][1]-prev[3][fk][1]) / dt)
            if t >= 3.0:
                hspd.append(hs)
        if t >= 3.0:
            ahead.append(hp - fp); latoff.append(hl - fl)
        prev = (t, hx, hy, cr)

print('waves', sorted(waves))
print('hero start (proj, lat, t when starts moving):', start_pos)
print('gap hero-front when hero starts moving:', [round(g) for g in gap_when_start])
print('ahead (t>=3s) p10/p50/p90:', [round(pct(ahead, p)) for p in (.1, .5, .9)], 'min', round(min(ahead)))
print('|latOff| (t>=3s) p50/p80/p95:', [round(pct([abs(v) for v in latoff], p)) for p in (.5, .8, .95)])
print('hero speed (t>=3s) p50:', round(pct(hspd, .5)), ' share standing(<60):', f'{sum(s<60 for s in hspd)/len(hspd):.0%}')
print('front creep speed p50:', round(pct(fspd, .5)), ' share front creep stalled(<60):', f'{sum(s<60 for s in fspd)/len(fspd):.0%}', ' mean:', round(S.mean(fspd)))
print('creep path: proj bucket -> median lateral (n)')
for b in sorted(path):
    if len(path[b]) >= 20: print(f'  {b:5d}..{b+200:5d}: lat {S.median(path[b]):6.0f}  (p10 {pct(path[b], .1):5.0f}, p90 {pct(path[b], .9):5.0f}, n={len(path[b])})')
