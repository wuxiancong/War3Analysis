# Replay recorded creep HP: when would each predictor fire, and would that single shot have been the last hit?
import sys, bisect, collections, statistics

rec = sys.argv[1]
series = collections.defaultdict(list)
times, dmg = [], {}
for line in open(rec, encoding='utf-8-sig', errors='replace'):
    c = line.rstrip('\n').split(',', 9)
    if c[0] != 'trace':
        continue
    t = float(c[1])
    if t > 238.5:            # hero died here
        break
    times.append(t)
    for u in c[9].split(';'):
        p = u.split(':')
        if len(p) == 6:
            series[p[0]].append((t, float(p[3]), p[1], p[2]))
            dmg[t] = float(c[5])

creeps = []
for o, s in series.items():
    if s[-1][1] > 80 or s[-1][0] >= times[-1] - 0.5 or len(s) < 12:
        continue             # did not die in view
    nxt = times[bisect.bisect_right(times, s[-1][0])]
    creeps.append((s, nxt))


def hp_at(s, death, t):
    if t >= death:
        return 0.0
    i = bisect.bisect_right([x[0] for x in s], t) - 1
    return s[max(i, 0)][1]


def rate_ema(s, i):
    r = 0.0
    for a, b in zip(s[max(0, i - 25):i], s[max(1, i - 24):i + 1]):
        dt = b[0] - a[0]
        if dt > 0:
            r = r * 0.6 + max(0.0, (a[1] - b[1]) / dt) * 0.4
    return min(60.0, r)


def window(sec, cap):
    def f(s, i):
        j = i
        while j > 0 and s[i][0] - s[j][0] < sec:
            j -= 1
        dt = s[i][0] - s[j][0]
        return min(cap, max(0.0, (s[j][1] - s[i][1]) / dt)) if dt >= 0.5 else 0.0
    return f


def mult(side_type):
    return 1 / 1.12 if side_type in ('esen', 'ugho') else 1.0


def run(rate_fn, horizon, assumed, bias=0.0):
    out = collections.Counter()
    for s, death in creeps:
        res = 'never'
        for i, (t, hp, side, typ) in enumerate(s):
            if side == 'a' and hp >= (300 if typ == 'edry' else 550) * 0.5:
                continue
            d = dmg[t] * mult(typ)
            if hp - rate_fn(s, i) * assumed <= d * (1.0 + bias):
                h = hp_at(s, death, t + horizon)
                res = 'late' if h <= 0.405 else ('hit' if h <= d * 1.08 else 'early')
                break
        out[res] += 1
    return out


print('creeps that died in view:', len(creeps))
for horizon in (1.25, 1.45, 1.65):
    print('== real time from decision to impact %.2fs' % horizon)
    cases = [
        ('current: EMA cap60, latency ignored', rate_ema, horizon - 0.45, 0.0),
        ('EMA cap60, latency included', rate_ema, horizon, 0.0),
    ]
    for sec in (1.5, 2.0, 3.0, 4.0):
        for cap in (60.0, 120.0, 999.0):
            cases.append(('window %.1fs cap%d, latency included' % (sec, cap), window(sec, cap), horizon, 0.0))
    res = []
    for name, fn, a, b in cases:
        r = run(fn, horizon, a, b)
        res.append((r['hit'], name, r))
    top = res[:2] + sorted(res[2:], key=lambda x: -x[0])[:5]
    for hit, name, r in top:
        print('  hit %2d early %2d late %2d never %2d  %s' % (hit, r['early'], r['late'], r['never'], name))
