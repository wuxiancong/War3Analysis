r"""补刀记录离线归因：records\lasthit\<英雄>\*.csv → 每个 miss 归到一类。

    python lh_miss_classify.py <csv> [--verbose]

归因（按 trace 每 100ms 一帧）：
  window0  : 这只兵从没进过「血 <= 英雄最低伤害」的窗口（一下从高血被打死）→ 只能靠提前出手 / 影压
  cd       : 窗口期间英雄攻击冷却一直没好（被上一刀占着）
  shot     : 窗口里英雄攻击目标就是它（出手了但没补到：早 / 晚 / 被抢）
  idle     : 窗口里冷却好了、也没打它 → 决策没出手（或在打别的）
  far      : 窗口里离英雄 > 射程 + 100
  nomatch  : trace 里对不上这只兵
"""
import argparse
import collections
import math
import sys


def load(path):
    head, events, traces = {}, [], []
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('# hero='):
                for kv in line[2:].split():
                    k, _, v = kv.partition('=')
                    head[k] = v
            elif line.startswith('# range='):
                for kv in line[2:].split():
                    k, _, v = kv.partition('=')
                    head[k] = v
            elif line.startswith('event,'):
                p = line.split(',')
                events.append(dict(t=float(p[1]), res=p[2], kind=p[3], handle=p[4], type=p[5],
                                   life=float(p[6]), maxl=float(p[7]), dist=float(p[8]), killer=p[9]))
            elif line.startswith('trace,'):
                p = line.split(',', 9)
                units = {}
                for u in p[9].split(';'):
                    q = u.split(':')
                    if len(q) == 6:
                        units[q[0]] = (q[1], q[2], float(q[3]), float(q[4]), float(q[5]))
                traces.append(dict(t=float(p[1]), hx=float(p[2]), hy=float(p[3]), hl=float(p[4]), dmg=float(p[5]),
                                   wu=float(p[6]), cd=float(p[7]), tgt=p[8], units=units))
    return head, events, traces


def match(ev, traces):
    """找事件时刻附近消失的、血最接近 lastLife 的兵。"""
    best, bestScore = None, 1e9
    idx = [i for i, tr in enumerate(traces) if ev['t'] - 1.5 <= tr['t'] <= ev['t'] + 0.3]
    for i in idx:
        tr = traces[i]
        nxt = traces[i + 1] if i + 1 < len(traces) else None
        for o, u in tr['units'].items():
            side = u[0]
            if (ev['kind'] == 'dn') != (side == 'a'):
                continue
            if nxt is not None and o in nxt['units'] and nxt['units'][o][2] > 0.5:
                continue
            sc = abs(u[2] - ev['life']) + abs(tr['t'] - ev['t']) * 20
            if sc < bestScore:
                best, bestScore = o, sc
    return best if bestScore < 60 else None


HEAD = {}


def classify(ev, obj, traces, rng):
    hist = [tr for tr in traces if ev['t'] - 6 <= tr['t'] <= ev['t'] + 0.2 and obj in tr['units']]
    if not hist:
        return 'nomatch', ''
    win = [tr for tr in hist if 0.5 < tr['units'][obj][2] <= tr['dmg'] * 0.98]
    if not win:
        prev = [tr['units'][obj][2] for tr in hist]
        return 'window0', 'min life seen %.0f dmg %.0f' % (min(prev), hist[-1]['dmg'])
    shot = any(tr['tgt'] == obj for tr in hist[-25:])
    if shot:
        # 出手时刻 ≈ 对它抬手的最后一帧之后；落地 = 出手 + 距离 / 弹道速度
        ms = float(HEAD.get('missileSpeed', 1200)) or 1200.0
        rel = [tr for tr in traces if ev['t'] - 6 <= tr['t'] <= ev['t'] + 0.3]
        fire = None
        for i, tr in enumerate(rel):
            if tr['tgt'] == obj and tr['wu'] > 0.01:
                nxt = rel[i + 1] if i + 1 < len(rel) else None
                if nxt is None or nxt['wu'] <= 0.01 or nxt['tgt'] != obj:
                    u = tr['units'].get(obj)
                    d = math.hypot(u[3] - tr['hx'], u[4] - tr['hy']) if u else 300.0
                    fire = (tr['t'] + tr['wu'], tr['t'] + tr['wu'] + max(0.0, d - 100.0) / ms)   # 命中量到碰撞边缘：-100（flight_measure / Gemini 实测）
        if fire is None:
            return 'shot?', 'no windup seen (cancelled / never fired) win %.1fs' % (win[-1]['t'] - win[0]['t'] + 0.1)
        death = hist[-1]['t'] + 0.05
        lifeAt = None
        for tr in hist:
            if tr['t'] <= fire[1]:
                lifeAt = tr['units'][obj][2]
        dmg = hist[-1]['dmg']
        if fire[1] > death + 0.05:
            return 'late', 'impact %.2f death %.2f (+%.2fs)' % (fire[1], death, fire[1] - death)
        return 'early', 'impact %.2f death %.2f life@impact %.0f dmg %.0f' % (fire[1], death, lifeAt or -1, dmg)
    far = all(math.hypot(tr['units'][obj][3] - tr['hx'], tr['units'][obj][4] - tr['hy']) > rng + 100 for tr in win)
    if far:
        return 'far', ''
    ready = [tr for tr in win if tr['cd'] <= 0.15 and tr['wu'] <= 0.01]
    if not ready:
        return 'cd', 'win %.1fs cd>=%.2f' % (win[-1]['t'] - win[0]['t'] + 0.1, min(tr['cd'] for tr in win))
    return 'idle', 'win %.1fs ready %d frames, tgts %s' % (win[-1]['t'] - win[0]['t'] + 0.1, len(ready),
                                                          ','.join(sorted({tr['tgt'] for tr in win})))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('csv')
    ap.add_argument('--verbose', action='store_true')
    a = ap.parse_args()
    head, events, traces = load(a.csv)
    HEAD.update(head)
    rng = float(head.get('range', 500))
    hits = collections.Counter(e['kind'] for e in events if e['res'] == 'hit')
    miss = collections.Counter(e['kind'] for e in events if e['res'] == 'miss')
    print('hero=%s lh %d/%d dn %d/%d traces=%d' % (head.get('hero'), hits['lh'], hits['lh'] + miss['lh'],
                                                   hits['dn'], hits['dn'] + miss['dn'], len(traces)))
    cls = collections.Counter()
    for e in events:
        if e['res'] != 'miss':
            continue
        obj = match(e, traces)
        c, d = classify(e, obj, traces, rng) if obj else ('nomatch', '')
        cls[(e['kind'], c)] += 1
        if a.verbose:
            print('%7.1f %s %s %-6s life %.0f/%.0f dist %.0f killerHero %s  %s' % (e['t'], e['kind'], e['type'], c,
                                                                                  e['life'], e['maxl'], e['dist'], e['killer'], d))
    for k in sorted(cls):
        print('%s %-8s %d' % (k[0], k[1], cls[k]))


if __name__ == '__main__':
    sys.exit(main())
