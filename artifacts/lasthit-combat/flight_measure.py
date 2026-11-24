r"""用补到的刀量真实飞行时间：死亡时刻 - 离手时刻（前摇结束）vs 距离 / 弹道速度。
    python flight_measure.py <csv> [...]
"""
import math, sys, statistics
sys.path.insert(0, __import__('os').path.dirname(__file__))
import lh_miss_classify as L
for path in sys.argv[1:]:
    head, events, traces = L.load(path)
    ms = float(head.get('missileSpeed', 1200))
    out = []
    for e in events:
        if e['res'] != 'hit':
            continue
        obj = L.match(e, traces)
        if not obj:
            continue
        rel = [tr for tr in traces if e['t'] - 4 <= tr['t'] <= e['t'] + 0.3]
        fire = None
        for i, tr in enumerate(rel):
            if tr['tgt'] == obj and tr['wu'] > 0.01:
                nxt = rel[i + 1] if i + 1 < len(rel) else None
                if nxt is None or nxt['wu'] <= 0.01 or nxt['tgt'] != obj:
                    u = tr['units'].get(obj)
                    if u:
                        fire = (tr['t'] + tr['wu'], math.hypot(u[3] - tr['hx'], u[4] - tr['hy']))
        if not fire:
            continue
        alive = [tr['t'] for tr in rel if obj in tr['units'] and tr['units'][obj][2] > 0.5]
        if not alive:
            continue
        death_lo, death_hi = max(alive), max(alive) + 0.1
        est = fire[1] / ms
        out.append(((death_lo + death_hi) / 2 - fire[0], est, fire[1]))
    if out:
        d = [a - b for a, b, _ in out]
        print('%s  n=%d  measured-est: median %+.3f  mean %+.3f  (measured median %.3f, est median %.3f)' % (
            path.split('/')[-1][:40], len(out), statistics.median(d), statistics.mean(d),
            statistics.median(a for a, _, _ in out), statistics.median(b for _, b, _ in out)))
