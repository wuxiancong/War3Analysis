import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
shops = json.load(open(os.path.join(HERE, 'shops.json'), encoding='utf-8'))

# (unitId, abbrev, 中文, team) team: 0=两方基地各有一份(按阵营就近选) 1=近卫专属 2=天灾专属 3=野外(边路/神秘)
SHOPS = [
    ('nC38', 'sena',      '饰品商人 希娜',     0),
    ('n01K', 'weapons',   '武器商人',          0),
    ('hC95', 'cache',     '奎尔瑟兰的密室',    1),
    ('nC35', 'cache',     '恶魔遗物',          2),
    ('e025', 'consumable','奇迹古树',          1),
    ('u00Q', 'consumable','崩碎之穴',          2),
    ('n002', 'support',   '支援法衣',          0),
    ('n009', 'gateway',   '圣物关口',          0),
    ('n00V', 'arcane',    '秘法圣所',          0),
    ('n00W', 'ancient',   '远古兵器',          0),
    ('n00X', 'enchanted', '附魔古物',          0),
    ('n0HE', 'protect',   '保护领地',          0),
    ('uC74', 'secret',    '黑市商人 雷拉格斯', 3),
    ('u00Z', 'side_lab',  '地精实验室',        3),
    ('u010', 'side_merchant', '地精商人',      3),
]
EN_FIX = {'h02D': 'Sentry Wards', 'h0D3': 'Smoke of Deceit', 'h0EI': 'Shadow Amulet'}
# 常用短别名（按 英文 slug → 追加别名）
ALIAS = {
    'scroll_of_town_portal': ['tp'], 'ancient_tango_of_essifation': ['tango'], 'healing_salve': ['salve'],
    'clarity_potion': ['clarity'], 'ironwood_branch': ['branch', 'gg'], 'boots_of_speed': ['boots'],
    'kelens_dagger': ['blink', 'dagger'], 'dust_of_appearance': ['dust'], 'sentry_wards': ['sentry', 'wards'],
    'animal_courier': ['courier', 'chicken'], 'flying_courier': ['flycourier'], 'empty_bottle': ['bottle'],
    'magic_stick': ['stick'], 'magic_wand': ['wand'], 'black_king_bar': ['bkb'], 'smoke_of_deceit': ['smoke'],
    'gem_of_true_sight': ['gem'], 'quelling_blade': ['qb'], 'stout_shield': ['stout'], 'power_treads': ['treads', 'pt'],
    'phase_boots': ['phase'], 'boots_of_travel': ['bot'], 'hand_of_midas': ['midas'], 'ring_of_basilius': ['basilius'],
    'mekansm': ['mek'], 'force_staff': ['force'], 'aghanims_scepter': ['aghs', 'scepter'], 'divine_rapier': ['rapier'],
    'monkey_king_bar': ['mkb'], 'the_butterfly': ['butterfly'], 'sange_and_yasha': ['sny'], 'eye_of_skadi': ['skadi'],
    'heart_of_tarrasque': ['heart'], 'linkens_sphere': ['linken'], 'manta_style': ['manta'], 'assault_cuirass': ['ac'],
    'shivas_guard': ['shiva'], 'blade_mail': ['blademail'], 'mask_of_madness': ['mom'], 'helm_of_the_dominator': ['hotd'],
    'stygian_desolator': ['deso'], 'buriza_do_kyanon': ['buriza', 'crit'], 'cranium_basher': ['basher'],
    'battle_fury': ['bf'], 'lothars_edge': ['lothar', 'sb'], 'guinsoos_scythe_of_vyse': ['sheep', 'hex', 'guinsoo'],
    'orchid_malevolence': ['orchid'], 'euls_scepter_of_divinity': ['eul'], 'refresher_orb': ['refresher'],
    'arcane_boots': ['arcane_boots', 'mana_boots'], 'tranquil_boots': ['tranquil'], 'urn_of_shadows': ['urn'],
    'vladmirs_offering': ['vlad'], 'khadgars_pipe_of_insight': ['pipe'], 'ring_of_aquila': ['aquila'],
    'poor_mans_shield': ['pms'], 'soul_ring': ['soulring'], 'wraith_band': ['wraith'], 'null_talisman': ['null'],
    'bracer': ['bracer'], 'gauntlets_of_strength': ['gauntlets'], 'slippers_of_agility': ['slippers'],
    'mantle_of_intelligence': ['mantle'], 'circlet_of_nobility': ['circlet'], 'ultimate_orb': ['ult_orb'],
    'ring_of_protection': ['rop'], 'ring_of_regeneration': ['ror'], 'sobi_mask': ['sobi'], 'ring_of_health': ['roh'],
    'void_stone': ['void'], 'orb_of_venom': ['venom'], 'observer_wards': ['obs'],
}

def slug(en):
    s = en.lower().replace("'", '')
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')

by_unit = {s['unit']: s for s in shops}
items, order = {}, []
for si, (uid, sab, szh, team) in enumerate(SHOPS, start=1):
    for it in by_unit[uid]['items']:
        nm = it['name']
        zh, en = (nm.split('|n', 1) + [''])[:2] if '|n' in nm else (nm, '')
        en = EN_FIX.get(it['id'], en).strip()
        zh = zh.strip()
        key = it['id']
        if key not in items:
            items[key] = {'id': key, 'zh': zh, 'en': en, 'gold': int(it['gold'] or 0), 'shops': []}
            order.append(key)
        items[key]['shops'].append(si)

# 同名不同 ID（边路店副本）共用英文 slug：基地版本优先拿到主缩写，边路版本加 side_ 前缀
used, rows = {}, []
for key in order:
    it = items[key]
    base = slug(it['en']) or key.lower()
    side_only = all(SHOPS[s - 1][3] == 3 for s in it['shops'])
    primary = base
    if primary in used:
        primary = ('side_' if side_only else 'alt_') + base
    n = 2
    while primary in used:
        primary = f'{base}_{n}'; n += 1
    used[primary] = key
    al = []
    if primary == base:
        for a in ALIAS.get(base, []):
            if a not in used and a != primary:
                used[a] = key; al.append(a)
    it['abbr'] = primary
    it['aliases'] = al
    rows.append(it)

def cstr(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'

out = []
out.append('''#ifndef DOTA_ITEM_SHOP_ABBREV_H
#define DOTA_ITEM_SHOP_ABBREV_H

// DotA 6.83d 物品商店与货架映射表（由地图数据生成：Units\\*UnitFunc.txt 的 Sellunits、
// *UnitStrings.txt 的 Name、UnitBalance.slk 的 goldcost）。
//
// 要点：DotA 的物品商店卖的是「假单位」(hXXX)，由地图触发器换成真物品，
// 所以购买动作与酒馆买英雄相同：选中商店 → 0x10 动作包（单位码 = soldUnitId）。
//
// 调试：
//   .\\scripts\\ai_control.ps1 buy -- tango
//   .\\scripts\\ai_control.ps1 buy -- h01J 2      （第 2 个参数：同类商店的第几个实例，0/省略 = 自动）
//   .\\scripts\\ai_control.ps1 items              （列出全部物品缩写）
//   游戏内：-buy tango  /  /buy branch
//
// 与其它命令区分：
//   pick → 选定英雄      shop → 选中英雄酒馆      buy → 在物品商店购买

#include <cctype>
#include <cstring>

// team: 0=两方基地各有一份(按本地阵营选) 1=近卫专属 2=天灾专属 3=野外(边路/神秘商店，需英雄在旁)
struct DotaItemShopEntry {
    unsigned index;          // 1..N
    const char *unitId;      // 商店单位 FourCC
    const char *abbrev;
    const char *zhName;
    unsigned team;
};

struct DotaItemEntry {
    unsigned index;          // 1..N
    const char *soldUnitId;  // 货架上的假单位 FourCC（购买动作包里的单位码）
    const char *abbrev;      // 主缩写（英文名 slug）
    const char *zhName;
    const char *enName;
    unsigned gold;           // 货架标价；0 = 合成类（卷轴免费或由触发器结算）
    unsigned shops[2];       // 出售该物品的商店 index（0 = 无）
};

struct DotaItemAliasEntry {
    const char *alias;
    unsigned itemIndex;
};
''')
out.append('static const DotaItemShopEntry kDotaItemShops[] = {')
for si, (uid, sab, szh, team) in enumerate(SHOPS, start=1):
    out.append(f'    {{ {si:2d}, "{uid}", {cstr(sab)}, {cstr(szh)}, {team} }},')
out.append('};\n')
out.append('static const DotaItemEntry kDotaItems[] = {')
cur = None
for i, it in enumerate(rows, start=1):
    it['index'] = i
    s = it['shops'][0]
    if s != cur:
        cur = s
        out.append(f'    // ---- {SHOPS[s-1][2]} ({SHOPS[s-1][0]}) ----')
    sh = (it['shops'] + [0, 0])[:2]
    out.append(f'    {{ {i:3d}, "{it["id"]}", {cstr(it["abbr"])}, {cstr(it["zh"])}, {cstr(it["en"])}, {it["gold"]}, {{ {sh[0]}, {sh[1]} }} }},')
out.append('};\n')
out.append('static const DotaItemAliasEntry kDotaItemAliases[] = {')
for it in rows:
    for a in it['aliases']:
        out.append(f'    {{ {cstr(a)}, {it["index"]} }},   // {it["zh"]}')
out.append('};\n')
out.append('''static const unsigned kDotaItemShopCount = (unsigned)(sizeof(kDotaItemShops) / sizeof(kDotaItemShops[0]));
static const unsigned kDotaItemCount = (unsigned)(sizeof(kDotaItems) / sizeof(kDotaItems[0]));
static const unsigned kDotaItemAliasCount = (unsigned)(sizeof(kDotaItemAliases) / sizeof(kDotaItemAliases[0]));

inline const DotaItemEntry *dotaItemByIndex(unsigned index)
{
    return (index >= 1 && index <= kDotaItemCount) ? &kDotaItems[index - 1] : nullptr;
}

inline const DotaItemShopEntry *dotaItemShopByIndex(unsigned index)
{
    return (index >= 1 && index <= kDotaItemShopCount) ? &kDotaItemShops[index - 1] : nullptr;
}

inline const DotaItemShopEntry *dotaItemShopByUnitId(const char *unitId)
{
    if (!unitId) return nullptr;
    for (unsigned i = 0; i < kDotaItemShopCount; ++i) {
        if (std::strcmp(kDotaItemShops[i].unitId, unitId) == 0)
            return &kDotaItemShops[i];
    }
    return nullptr;
}

// token：序号(1..N) / 主缩写 / 别名 / 假单位 FourCC（不分大小写）
inline bool resolveDotaItemToken(const char *token, unsigned *outIndex)
{
    if (!token || !outIndex)
        return false;
    while (*token == ' ' || *token == '\\t')
        ++token;

    char buf[48];
    unsigned n = 0;
    for (const char *p = token; *p && *p != ' ' && *p != '\\t' && n + 1 < sizeof(buf); ++p)
        buf[n++] = (char)std::tolower(static_cast<unsigned char>(*p));
    buf[n] = '\\0';
    if (n == 0)
        return false;

    bool allDigit = true;
    for (unsigned i = 0; i < n; ++i) {
        if (!std::isdigit(static_cast<unsigned char>(buf[i]))) { allDigit = false; break; }
    }
    if (allDigit) {
        unsigned v = 0;
        for (unsigned i = 0; i < n; ++i)
            v = v * 10u + (unsigned)(buf[i] - '0');
        if (v >= 1 && v <= kDotaItemCount) { *outIndex = v; return true; }
        return false;
    }

    for (unsigned i = 0; i < kDotaItemCount; ++i) {
        if (std::strcmp(buf, kDotaItems[i].abbrev) == 0) { *outIndex = kDotaItems[i].index; return true; }
    }
    for (unsigned i = 0; i < kDotaItemAliasCount; ++i) {
        if (std::strcmp(buf, kDotaItemAliases[i].alias) == 0) { *outIndex = kDotaItemAliases[i].itemIndex; return true; }
    }
    if (n == 4) {
        for (unsigned i = 0; i < kDotaItemCount; ++i) {
            const char *id = kDotaItems[i].soldUnitId;
            bool same = true;
            for (unsigned k = 0; k < 4; ++k) {
                if ((char)std::tolower(static_cast<unsigned char>(id[k])) != buf[k]) { same = false; break; }
            }
            if (same) { *outIndex = kDotaItems[i].index; return true; }
        }
    }
    return false;
}

#endif // DOTA_ITEM_SHOP_ABBREV_H''')

dst = r'D:\\Qt\\workspace\\War3Launcher\\shared\\DotaItemShopAbbrev.h'
open(dst, 'w', encoding='utf-8', newline='\n').write('\n'.join(out) + '\n')
print('items:', len(rows), 'aliases:', sum(len(r['aliases']) for r in rows))
dup = [r for r in rows if r['abbr'].startswith(('alt_', 'side_'))]
print('side/alt:', [(r['id'], r['abbr']) for r in dup])
print('no-en:', [(r['id'], r['zh']) for r in rows if not r['en']])
