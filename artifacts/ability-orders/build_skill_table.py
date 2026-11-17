"""Build DotA hero skill table: hero -> slots (FourCC, hotkey, maxLevel, orderId, targetType).

Inputs:
  dota_data.json (War3Bot/images)            hero -> skills (code/slot/hotkey/maxLevel), attrCode
  war3map.w3a (DotA 6.83d object data)        custom ability -> base ability + field overrides
  *AbilityFunc.txt (War3Patch > War3x > war3) base ability -> Order= string
  orders.json (from game.dll 1.27)            order string -> order id
Outputs (argv): header path, json path
"""
import json, struct, sys, os, re, collections

ROOT = 'D:/Qt/workspace'
ART = ROOT + '/War3Analysis/artifacts/ability-orders'
DATA = json.load(open(ROOT + '/War3Bot/images/dota_data.json', encoding='utf-8'))
ORDERS = json.load(open(sys.argv[3], encoding='utf-8'))
W3A = ROOT + '/War3Angular/scratch/dota683_extract/war3map.w3a'

# ---------- base ability order strings ----------
base_order = {}
for mpq in ('war3.mpq', 'War3x.mpq', 'War3Patch.mpq'):  # later overrides earlier
    d = os.path.join(ART, mpq)
    if not os.path.isdir(d): continue
    for fn in os.listdir(d):
        if not (fn.endswith('AbilityFunc.txt') or fn.endswith('AbilityStrings.txt')): continue
        sec = None
        for line in open(os.path.join(d, fn), encoding='latin-1'):
            line = line.strip()
            m = re.match(r'^\[(\w{4})\]$', line)
            if m: sec = m.group(1); continue
            if sec and line.lower().startswith('order='):
                base_order[sec] = line.split('=', 1)[1].strip().strip('"').lower()

# 数据文件里没有 Order= 键、由引擎硬编码默认 Order 的主动基础技能（DotA 英雄技能用到的）
ENGINE_DEFAULT_ORDER = {
    'ANfb': 'firebolt',      # 火焰箭（单位）
    'AHdr': 'drain',         # 吸取魔法（单位）
    'ANms': 'manashieldon',  # 魔法护盾（开关，无目标）
    'AHca': 'coldarrows',    # 冰箭（法球，单位）
    'AOwd': 'ward',          # 毒蛇守卫（点地）
}
for k, v in ENGINE_DEFAULT_ORDER.items():
    base_order.setdefault(k, v)

# ---------- w3a parse (format v1/v2, with level+dataptr) ----------
def parse_w3a(path):
    b = open(path, 'rb').read()
    pos = 0
    ver = struct.unpack_from('<i', b, pos)[0]; pos += 4
    objs = {}
    def rd_str(p):
        e = b.index(b'\0', p); return b[p:e].decode('utf-8', 'replace'), e + 1
    for table in range(2):
        n = struct.unpack_from('<i', b, pos)[0]; pos += 4
        for _ in range(n):
            orig = b[pos:pos+4].decode('latin-1'); new = b[pos+4:pos+8]; pos += 8
            if ver >= 3:
                sets = struct.unpack_from('<i', b, pos)[0]; pos += 4
            else:
                sets = 1
            mods = []
            for _s in range(sets):
                if ver >= 3: pos += 4  # set flag
                nm = struct.unpack_from('<i', b, pos)[0]; pos += 4
                for _m in range(nm):
                    fid = b[pos:pos+4].decode('latin-1'); vt, lvl, dp = struct.unpack_from('<iii', b, pos+4); pos += 16
                    if vt == 0: val = struct.unpack_from('<i', b, pos)[0]; pos += 4
                    elif vt in (1, 2): val = struct.unpack_from('<f', b, pos)[0]; pos += 4
                    elif vt == 3: val, pos = rd_str(pos)
                    else: raise ValueError('bad type %d at %d' % (vt, pos))
                    pos += 4  # end token
                    mods.append((fid, vt, lvl, dp, val))
            nid = new.decode('latin-1') if new != b'\0\0\0\0' else orig
            objs[nid] = {'base': orig, 'mods': mods}
    return objs

OBJ = parse_w3a(W3A)

# ---------- 优化地图：Units\AbilityData.slk（alias→code 基础技能 + DataB1/C1/F1）+ 地图内 *AbilityFunc.txt ----------
def parse_slk(path):
    # SLK：X / Y 省略时沿用上一条记录的值（优化器大量省略 X）
    cols, rows, cur_y, x = {}, collections.defaultdict(dict), 0, None
    for line in open(path, encoding='latin-1'):
        if not line.startswith('C;'): continue
        parts = line.rstrip('\r\n').split(';')
        val = None
        for p in parts[1:]:
            if p.startswith('X'): x = int(p[1:])
            elif p.startswith('Y'): cur_y = int(p[1:])
            elif p.startswith('K'): val = p[1:].strip('"')
        if x is None or val is None: continue
        if cur_y == 1: cols[x] = val
        else: rows[cur_y][cols.get(x, x)] = val
    return {r['alias']: r for r in rows.values() if 'alias' in r}

MAP = ART + '/map'
SLK = parse_slk(MAP + '/Units_AbilityData.slk') if os.path.exists(MAP + '/Units_AbilityData.slk') else {}
map_order = {}
if os.path.isdir(MAP):
    for fn in os.listdir(MAP):
        if not (fn.endswith('AbilityFunc.txt') or fn.endswith('AbilityStrings.txt')): continue
        sec = None
        for line in open(os.path.join(MAP, fn), encoding='latin-1'):
            line = line.strip()
            m = re.match(r'^\[(\w{4})\]$', line)
            if m: sec = m.group(1); continue
            if sec and line.lower().startswith('order='):
                v = line.split('=', 1)[1].strip().strip('"').lower()
                if v: map_order[sec] = v
print('slk rows', len(SLK), 'map Order= overrides', len(map_order))

# ---------- target type of standard bases (no data field) ----------
NONE, UNIT, POINT, UNIT_OR_POINT, PASSIVE = 'none', 'unit', 'point', 'unit_or_point', 'passive'
# Channel 'Ncl2' encoding
NCL_TT = {0: NONE, 1: UNIT, 2: POINT, 3: UNIT_OR_POINT}
# Curated standard-base targeting (by order string): what the engine expects for the action packet
ORDER_TT = {
    # unit target
    'thunderbolt': UNIT, 'holybolt': UNIT, 'chainlightning': UNIT, 'purge': UNIT, 'hex': UNIT, 'entanglingroots': UNIT,
    'faeriefire': UNIT, 'cripple': UNIT, 'curse': UNIT, 'frostnova': UNIT, 'deathcoil': UNIT, 'sleep': UNIT,
    'banish': UNIT, 'polymorph': UNIT, 'slow': UNIT, 'innerfire': UNIT, 'bloodlust': UNIT, 'rejuvination': UNIT,
    'shadowstrike': UNIT, 'manaburn': UNIT, 'acidbomb': UNIT, 'drunkenhaze': UNIT, 'lightningshield': UNIT,
    'forkedlightning': UNIT, 'parasite': UNIT, 'transmute': UNIT, 'charm': UNIT, 'firebolt': UNIT, 'drain': UNIT,
    'lifedrain': UNIT, 'soulburn': UNIT, 'possession': UNIT, 'darkportal': POINT, 'doom': UNIT, 'spiritlink': UNIT,
    'unholyfrenzy': UNIT, 'frostarmor': UNIT, 'antimagicshell': UNIT, 'magicleash': UNIT, 'blackarrowon': PASSIVE,
    'devour': UNIT, 'ensnare': UNIT, 'web': UNIT, 'feedback': PASSIVE, 'disenchant': POINT, 'fingerofdeath': UNIT,
    'controlmagic': UNIT, 'thunderclap': NONE, 'stomp': NONE, 'waterelemental': NONE, 'divineshield': NONE,
    'avatar': NONE, 'bladestorm': NONE, 'windwalk': NONE, 'berserk': NONE, 'roar': NONE, 'howlofterror': NONE,
    'immolation': NONE, 'manashieldon': NONE, 'metamorphosis': NONE, 'starfall': NONE, 'tranquility': NONE,
    'mirrorimage': NONE, 'chemicalrage': NONE, 'elementalfury': NONE, 'locustswarm': NONE, 'stampede': POINT,
    'ravenform': NONE, 'spiritwolf': NONE, 'summongrizzly': NONE, 'summonquillbeast': NONE, 'summonfactory': NONE,
    'animatedead': NONE, 'carrionswarm': POINT, 'shockwave': POINT, 'breathoffire': POINT, 'breathoffrost': POINT,
    'blizzard': POINT, 'flamestrike': POINT, 'rainoffire': POINT, 'earthquake': POINT, 'impale': POINT,
    'blink': POINT, 'deathanddecay': POINT, 'cloudoffog': POINT, 'healingward': POINT, 'serpentward': POINT,
    'stasistrap': POINT, 'silence': POINT, 'monsoon': POINT, 'volcano': POINT, 'clusterrockets': POINT,
    'inferno': POINT, 'massteleport': UNIT_OR_POINT, 'shadowsight': POINT, 'scout': NONE, 'farsight': POINT,
    'flare': POINT, 'blight': POINT, 'freezingbreath': UNIT, 'evileye': POINT, 'spies': NONE, 'tornado': POINT,
    'spellsteal': UNIT, 'autodispel': POINT, 'dispel': POINT, 'phaseshift': NONE, 'phoenixfire': PASSIVE,
    'flamingarrows': UNIT, 'coldarrows': UNIT, 'poisonarrows': UNIT, 'incineratearrow': UNIT,
    'searingarrows': UNIT, 'frenzy': NONE, 'channel': NONE, 'blackarrow': UNIT, 'forceofnature': POINT,
    'ward': POINT, 'eattree': UNIT, 'battleroar': NONE, 'corporealform': NONE, 'etherealform': NONE,
    'recharge': UNIT, 'replenish': UNIT, 'renew': UNIT, 'repair': UNIT, 'restoration': NONE, 'replenishlife': UNIT,
    'replenishmana': UNIT, 'darkconversion': UNIT, 'soulpreservation': UNIT, 'thornyshield': NONE,
    'tauntall': NONE, 'taunt': NONE, 'whirlwind': NONE, 'rainofchaos': POINT, 'darkritual': UNIT,
    'unavatar': NONE, 'rescue': UNIT, 'charge': UNIT, 'grabtree': UNIT, 'creepthunderbolt': UNIT,
    'creepthunderclap': NONE, 'creepdevour': UNIT, 'creepanimatedead': NONE, 'creepheal': UNIT,
    'stoneform': NONE, 'unstoneform': NONE, 'burrow': NONE, 'unburrow': NONE, 'robogoblin': NONE,
    'unrobogoblin': NONE, 'bearform': NONE, 'unbearform': NONE, 'resurrection': NONE, 'reincarnation': PASSIVE,
    'windwalkon': NONE, 'healingspray': POINT, 'acolyteharvest': UNIT, 'auraunholy': PASSIVE,
    'mindrot': UNIT, 'neutraldetectaoe': POINT, 'gold2lumber': NONE, 'lumber2gold': NONE,
    'spiritofvengeance': NONE, 'vengeance': NONE, 'voodoo': NONE, 'wardofshadowsight': POINT,
    'barkskin': NONE, 'unbarkskin': NONE, 'invisibility': UNIT, 'heal': UNIT, 'innerfireon': UNIT,
    'raisedead': NONE, 'unholyfrenzyon': UNIT, 'cyclone': UNIT, 'lavamonster': POINT, 'bloodlustOn': UNIT,
    'selfdestruct': NONE, 'kaboom': UNIT, 'chainlightning2': UNIT, 'avengerform': NONE, 'blackhole': POINT,
    'manaflareon': NONE, 'spiritwolfon': NONE, 'summonphoenix': NONE, 'holdposition': NONE,
    'fanofknives': NONE, 'defend': NONE, 'poisonarrowstarg': UNIT, 'ancestralspirit': UNIT,
    # 有 Order= 但实为被动（不发施法包）
    'bash': PASSIVE, 'engineeringupgrade': PASSIVE, 'demolish': PASSIVE, 'incinerate': PASSIVE,
    'auravampiric': PASSIVE, 'attributemodskill': PASSIVE,
}

def field(mods, fid, level=None):
    vals = [(lv, v) for (f, vt, lv, dp, v) in mods if f == fid]
    if not vals: return None
    if level is not None:
        for lv, v in vals:
            if lv == level: return v
    return sorted(vals)[0][1]

def resolve(code):
    o = OBJ.get(code)
    row = SLK.get(code, {})
    base = row.get('code') or (o['base'] if o else code)
    mods = o['mods'] if o else []
    info = {'code': code, 'base': base}
    tt = None
    order = None
    if base == 'ANcl':
        order = (row.get('DataF1') or field(mods, 'Ncl6', 1) or 'channel').lower()
        t = row.get('DataB1')
        t = int(float(t)) if t not in (None, '', '-') else (field(mods, 'Ncl2', 1) or 0)
        tt = NCL_TT.get(t, NONE)
        opts = row.get('DataC1')
        opts = int(float(opts)) if opts not in (None, '', '-') else (field(mods, 'Ncl3', 1) or 0)
        info['nclOptions'] = opts
        if opts & 1 == 0 and False: pass
    else:
        order = field(mods, 'aord') or map_order.get(code) or map_order.get(base) or base_order.get(base)
    if order and order.lower() not in ORDERS and base_order.get(base, '').lower() in ORDERS:
        order = base_order[base]   # 地图写了引擎不认识的串（如 serpentward）→ 用基础技能默认 Order
    info['orderStr'] = order or ''
    oid = ORDERS.get((order or '').lower(), 0) if order else 0
    info['orderId'] = oid
    if tt is None:
        tt = ORDER_TT.get((order or '').lower())
    if not order or (oid == 0 and tt != PASSIVE): tt = PASSIVE
    info['targetType'] = tt or 'unknown'

    def num(k, default):
        v = row.get(k)
        try: return float(v) if v not in (None, '', '-', '_') else default
        except ValueError: return default
    info['reqLevel'] = int(num('reqLevel', 1))
    info['levelSkip'] = int(num('levelSkip', 2)) or 2          # 缺省 = 游戏常数 Hero Ability Level Skip(2)
    info['range'] = int(min(num('Rng1', 0), 65535))
    info['cost'] = int(min(num('Cost1', 0), 65535))
    info['coolDs'] = int(min(num('Cool1', 0) * 10, 65535))   # 冷却（0.1 秒）
    # 施法保护：施法前摇 + 持续施法（Channel 的 DataA = Follow Through Time）
    follow = num('DataA1', 0) if base == 'ANcl' else 0
    if base in ('AHbz', 'AEtq', 'AEsf', 'ANst', 'ANvc', 'ANrf', 'AHmt', 'ANmo', 'ANdr', 'AHdr'):   # 原生持续施法
        follow = max(follow, num('DataA1', 0) if base != 'AHdr' else 4.0)
    info['guardMs'] = int(min(600 + follow * 1000, 12000))
    return info

heroes = DATA['heroes']
out = {}
stats = collections.Counter()
unknown_orders = collections.Counter()
for hcode, h in heroes.items():
    slots = []
    for s in h['skills']:
        if s['slot'] > 4: continue
        r = resolve(s['code']) if s['code'] else {'code': '', 'orderId': 0, 'targetType': 'unknown', 'orderStr': '', 'base': '',
                                                  'reqLevel': 1, 'levelSkip': 2, 'range': 0, 'guardMs': 600, 'cost': 0, 'coolDs': 0}
        r.update({'slot': s['slot'], 'hotkey': s['hotkey'], 'maxLevel': s['maxLevel']})
        slots.append(r)
        stats[r['targetType']] += 1
        if r['orderId'] == 0 and r['targetType'] != PASSIVE: unknown_orders[(r['base'], r['orderStr'])] += 1
    out[hcode] = {'attrCode': h.get('attrCode') or 'Aamk', 'skills': sorted(slots, key=lambda x: x['slot'])}

json.dump(out, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('target types:', dict(stats))
print('no orderId (non-passive):', sum(unknown_orders.values()), unknown_orders.most_common(15))

# ---------- C header ----------
TT_ENUM = {'none': 'DOTA_SKILL_TARGET_NONE', 'unit': 'DOTA_SKILL_TARGET_UNIT', 'point': 'DOTA_SKILL_TARGET_POINT',
           'unit_or_point': 'DOTA_SKILL_TARGET_UNIT_OR_POINT', 'passive': 'DOTA_SKILL_TARGET_PASSIVE',
           'unknown': 'DOTA_SKILL_TARGET_UNKNOWN'}
lines = []
lines.append('// 自动生成：War3Analysis/artifacts/ability-orders/build_skill_table.py（勿手改）')
lines.append('// 数据源：War3Bot/images/dota_data.json + DotA 6.83d war3map.w3a + *AbilityFunc.txt + game.dll 1.27 订单表')
lines.append('#pragma once')
lines.append('#include <cstdint>')
lines.append('#include <cstring>')
lines.append('')
lines.append('enum DotaSkillTargetType : uint8_t {')
lines.append('    DOTA_SKILL_TARGET_UNKNOWN = 0,')
lines.append('    DOTA_SKILL_TARGET_NONE,          // 0x10 无目标')
lines.append('    DOTA_SKILL_TARGET_UNIT,          // 0x12 单位目标')
lines.append('    DOTA_SKILL_TARGET_POINT,         // 0x11 点地')
lines.append('    DOTA_SKILL_TARGET_UNIT_OR_POINT, // 0x12 或 0x11')
lines.append('    DOTA_SKILL_TARGET_PASSIVE,       // 被动：不能施放')
lines.append('};')
lines.append('')
lines.append('struct DotaHeroSkillSlot {')
lines.append('    uint32_t ability;   // 技能 FourCC（学习用；高字节为首字符）')
lines.append('    uint32_t orderId;   // 施法 OrderId（0 = 未知）')
lines.append('    uint8_t  target;    // DotaSkillTargetType')
lines.append('    uint8_t  maxLevel;')
lines.append('    char     hotkey;')
lines.append('    uint8_t  reqLevel;  // 学第 1 级所需英雄等级')
lines.append('    uint8_t  levelSkip; // 每学一级所需英雄等级间隔（学第 n+1 级要求 reqLevel + n*levelSkip）')
lines.append('    uint16_t range;     // 1 级施法距离（0 = 无 / 未知）')
lines.append('    uint16_t guardMs;   // 施法保护时长：前摇 + 持续施法，期间补刀例程不按 S')
lines.append('    uint16_t manaCost;  // 1 级耗蓝')
lines.append('    uint16_t coolDs;    // 1 级冷却（0.1 秒）')
lines.append('};')
lines.append('')
lines.append('struct DotaHeroSkillEntry {')
lines.append('    uint32_t heroType;  // 英雄单位 FourCC')
lines.append('    uint32_t attr;      // 属性附加 FourCC（Aamk / A0NR）')
lines.append('    DotaHeroSkillSlot skills[4];')
lines.append('};')
lines.append('')
lines.append('#define DOTA_FOURCC(s) ((uint32_t)(uint8_t)(s)[0] << 24 | (uint32_t)(uint8_t)(s)[1] << 16 | (uint32_t)(uint8_t)(s)[2] << 8 | (uint32_t)(uint8_t)(s)[3])')
lines.append('')
lines.append('static const DotaHeroSkillEntry kDotaHeroSkills[] = {')
for hcode, h in out.items():
    sk = h['skills'] + [{'code': '', 'orderId': 0, 'targetType': 'unknown', 'maxLevel': 0, 'hotkey': '',
                         'reqLevel': 1, 'levelSkip': 2, 'range': 0, 'guardMs': 600, 'cost': 0, 'coolDs': 0}] * (4 - len(h['skills']))
    parts = []
    for s in sk[:4]:
        fc = 'DOTA_FOURCC("%s")' % s['code'] if len(s['code']) == 4 else '0'
        hk = "'%s'" % s['hotkey'][0] if s.get('hotkey') else "'\\0'"
        parts.append('{ %s, 0x%05X, %s, %d, %s, %d, %d, %d, %d, %d, %d }' % (
            fc, s['orderId'], TT_ENUM[s['targetType']], s['maxLevel'], hk,
            s['reqLevel'], s['levelSkip'], s['range'], s['guardMs'], s.get('cost', 0), s.get('coolDs', 0)))
    lines.append('    { DOTA_FOURCC("%s"), DOTA_FOURCC("%s"), { %s } },' % (hcode, h['attrCode'], ', '.join(parts)))
lines.append('};')
lines.append('')
lines.append('inline const DotaHeroSkillEntry *findDotaHeroSkills(uint32_t heroType)')
lines.append('{')
lines.append('    for (const DotaHeroSkillEntry &e : kDotaHeroSkills)')
lines.append('        if (e.heroType == heroType) return &e;')
lines.append('    return nullptr;')
lines.append('}')
lines.append('')
lines.append('// 按技能 FourCC 反查所属英雄与槽位（1..4）；属性附加返回 slot=5')
lines.append('inline const DotaHeroSkillEntry *findDotaSkillOwner(uint32_t ability, int *slot)')
lines.append('{')
lines.append('    for (const DotaHeroSkillEntry &e : kDotaHeroSkills) {')
lines.append('        for (int i = 0; i < 4; ++i)')
lines.append('            if (e.skills[i].ability == ability) { if (slot) *slot = i + 1; return &e; }')
lines.append('    }')
lines.append('    return nullptr;')
lines.append('}')
open(sys.argv[1], 'w', encoding='utf-8-sig', newline='\r\n').write('\n'.join(lines) + '\n')
print('header written', sys.argv[1])
