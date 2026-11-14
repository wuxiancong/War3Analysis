import os, re, sys, json, glob

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dota683d')

def read(p):
    b = open(p, 'rb').read()
    for enc in ('utf-8', 'gbk', 'latin-1'):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass

def parse_ini(text):
    out, cur = {}, None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('[') and line.endswith(']'):
            cur = line[1:-1]
            out.setdefault(cur, {})
        elif cur and '=' in line and not line.startswith('//'):
            k, v = line.split('=', 1)
            out[cur][k.strip().lower()] = v.strip()
    return out

def parse_slk(text):
    rows, x, y = {}, 0, 0
    for line in text.splitlines():
        if not line.startswith('C;'):
            continue
        val = None
        for part in line.split(';')[1:]:
            if part.startswith('X'):
                x = int(part[1:])
            elif part.startswith('Y'):
                y = int(part[1:])
            elif part.startswith('K'):
                val = part[1:].strip('"')
        if val is not None:
            rows.setdefault(y, {})[x] = val
    hdr = rows.get(1, {})
    table = {}
    for yy, r in rows.items():
        if yy == 1 or 1 not in r:
            continue
        table[r[1]] = {hdr[c].lower(): v for c, v in r.items() if c in hdr}
    return table

func, strs = {}, {}
for p in glob.glob(os.path.join(D, 'Units_*Func.txt')):
    for k, v in parse_ini(read(p)).items():
        func.setdefault(k, {}).update(v)
for p in glob.glob(os.path.join(D, 'Units_*Strings.txt')):
    for k, v in parse_ini(read(p)).items():
        strs.setdefault(k, {}).update(v)

items = parse_slk(read(os.path.join(D, 'Units_ItemData.slk')))
unitbal = parse_slk(read(os.path.join(D, 'Units_UnitBalance.slk')))
unitui = parse_slk(read(os.path.join(D, 'Units_UnitUI.slk')))

def name(i):
    n = strs.get(i, {}).get('name', '')
    return re.sub(r'\|c[0-9a-fA-F]{8}|\|r|"', '', n)

shops = {u: f['sellunits'].split(',') for u, f in func.items() if f.get('sellunits')}
print('shops with Sellitems:', len(shops), '| items in ItemData.slk:', len(items))
res = []
for u, lst in sorted(shops.items()):
    lst = [i for i in lst if i]
    print(f"\n== {u}  {name(u)!r}  ({len(lst)} items)")
    for i in lst:
        it = unitbal.get(i, {})
        print(f"   {i}  gold={it.get('goldcost','?'):>5}  {name(i)}")
    res.append({'unit': u, 'name': name(u), 'items': [{'id': i, 'gold': unitbal.get(i, {}).get('goldcost'), 'name': name(i)} for i in lst]})
json.dump(res, open(os.path.join(D, '..', 'shops.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
