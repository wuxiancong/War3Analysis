# Classify every event of a last-hit record against the AI attack log and the 100 ms trace.
import re, sys, math, collections, datetime

rec, log = sys.argv[1], sys.argv[2]
start = datetime.datetime.strptime(sys.argv[3], '%H:%M:%S.%f')

frames, events = [], []
for line in open(rec, encoding='utf-8-sig', errors='replace'):
    c = line.rstrip('\n').split(',', 9)
    if c[0] == 'trace':
        units = {}
        for u in c[9].split(';'):
            p = u.split(':')
            if len(p) == 6:
                units[p[0]] = (p[1], p[2], float(p[3]), float(p[4]), float(p[5]))
        frames.append(dict(t=float(c[1]), x=float(c[2]), y=float(c[3]), hp=float(c[4]), dmg=float(c[5]),
                           wind=float(c[6]), cd=float(c[7]), target=c[8], u=units))
    elif c[0] == 'event':
        events.append(line.rstrip('\n').split(','))

pat = re.compile(r'^\[(\d\d:\d\d:\d\d\.\d{3})\] \S+ \[(\S+)\] 出手 #(\d+) → (\S+) 0x([0-9A-F]+) 血:(\d+)/\d+ 掉血:(\d+)/s 预计 ([\d.]+)s')
shots = []
for line in open(log, encoding='utf-8', errors='replace'):
    m = pat.match(line)
    if not m:
        continue
    t = (datetime.datetime.strptime(m.group(1), '%H:%M:%S.%f') - start).total_seconds()
    if 0 <= t <= frames[-1]['t'] + 1:
        shots.append(dict(t=t, n=int(m.group(3)), h=m.group(5), hp=float(m.group(6)), rate=float(m.group(7)), eta=float(m.group(8))))


def obj_for(e):
    t, kind, life, typ = float(e[1]), e[5], float(e[6]), e[5]
    best = None
    for f, g in zip(frames, frames[1:] + [dict(u={})]):
        if t - 0.6 <= f['t'] <= t + 0.05:
            for o, u in f['u'].items():
                if u[1] == typ and o not in g['u']:
                    err = abs(u[2] - life) + 20 * abs(t - f['t'])
                    if not best or err < best[0]:
                        best = (err, o)
    return best[1] if best else None


tally = collections.Counter()
for e in events:
    if e[2] == 'hero_death':
        continue
    death, hit, handle = float(e[1]), e[2] == 'hit', e[4]
    obj = obj_for(e)
    mine = [s for s in shots if s['h'] == handle and s['t'] <= death + 0.05]
    info = ''
    if not mine:
        before = [s for s in shots if death - 2.5 <= s['t'] <= death]
        cause = 'no shot: busy on another creep' if before else 'no shot: never became eligible'
        info = 'other shot %.1fs before' % (death - before[-1]['t']) if before else ''
    else:
        s = mine[-1]
        fs = [f for f in frames if s['t'] - 0.02 <= f['t'] <= death and (obj is None or f['target'] == obj)]
        win = [f for f in fs if f['wind'] > 0]
        if not win:
            cause = 'ordered, wind-up never started'
            info = 'creep died %.2fs after order' % (death - s['t'])
        else:
            first = win[0]
            launch = first['t'] + first['wind']
            dist = 400.0
            if obj in first['u']:
                u = first['u'][obj]
                dist = math.hypot(u[3] - first['x'], u[4] - first['y'])
            land = launch + min(dist, 520) / 1200.0
            if death < launch:
                cause = 'late: died during wind-up'
            elif death < land - 0.06:
                cause = 'late: died with shot in flight'
            elif death <= land + 0.14:
                cause = 'near tie with another attacker'
            else:
                cause = 'early: shot landed, creep survived'
            info = 'order->windup %.2fs, land %+.2fs vs death, hp@order %d dmg %d rate %d' % (
                first['t'] - s['t'], land - death, s['hp'], first['dmg'], s['rate'])
    print('%7.2f %-4s %-2s %s %-38s %s' % (death, e[2], e[3], e[5], cause if not hit else '(hit) ' + cause, info))
    if not hit:
        tally[cause] += 1
print('== misses', sum(tally.values()))
for k, v in tally.most_common():
    print('%3d %s' % (v, k))

print('== hero')
d = [float(e[1]) for e in events if e[2] == 'hero_death']
fight = [f['t'] for f in frames if any(u[0] == 'e' for u in f['u'].values())]
print('enemy creeps in view first/last %.1f %.1f' % (fight[0], fight[-1]))
print('frames', len(frames), 'mean gap %.3f' % ((frames[-1]['t'] - frames[0]['t']) / len(frames)))
if d:
    prev = None
    for f in frames:
        if d[0] - 40 <= f['t'] <= d[0] + 1 and (prev is None or f['t'] - prev >= 3 or f['t'] >= d[0]):
            prev = f['t']
            e = [u for u in f['u'].values() if u[0] == 'e']
            a = [u for u in f['u'].values() if u[0] == 'a']
            print('t=%.1f hp=%d pos %d,%d enemy=%d own=%d nearest enemy=%d to enemy T1=%d' % (
                f['t'], f['hp'], f['x'], f['y'], len(e), len(a),
                min([math.hypot(u[3] - f['x'], u[4] - f['y']) for u in e] or [9999]),
                math.hypot(f['x'] - 1056, f['y'] + 96)))
            if f['t'] >= d[0]:
                break
print('last pos', frames[-1]['x'], frames[-1]['y'], 'hp', frames[-1]['hp'])
