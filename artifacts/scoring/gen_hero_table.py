"""Generate War3Launcher/hooker/war3hook_hero_stats.inl from hero_stats.json.
usage: python -I gen_hero_table.py <hero_stats.json> <out.inl>
Model: Claude Opus 5.5, 2026-11-20 (scoring system, see War3Analysis/analyses/dota-ai-scoring-system.md).
"""
import json, sys

H = json.load(open(sys.argv[1], encoding='utf-8'))
lines = [
    '// war3hook_hero_stats.inl —— DotA 6.83d 112 个可选英雄的基础移速 / 攻击数据（评分系统用）',
    '// 自动生成：War3Analysis/artifacts/scoring/gen_hero_table.py（数据：地图 SLK + *UnitFunc.txt，',
    '// 地图没改的字段取 war3.mpq → War3x.mpq → War3Patch.mpq 的默认值）。不要手改，改脚本后重新生成。',
    '// 字段：类型 ID、选人序号、移速、射程、是否远程（射程 > 200）、攻击前摇、弹道速度（近战 0）、基础攻击间隔',
    'struct AiHeroStat { uint32_t id; uint16_t index; uint16_t moveSpeed; uint16_t range; uint8_t ranged;',
    '                    float damagePoint; uint16_t missileSpeed; float bat; const char *abbrev; };',
    'static const AiHeroStat kAiHeroStats[] = {',
]
for h in H:
    i = h['id']
    lines.append('    { DOTA_FOURCC("%s"), %d, %d, %d, %d, %.2ff, %d, %.2ff, "%s" },'
                 % (i, h['index'], round(h['moveSpeed']), round(h['range']), 1 if h['ranged'] else 0,
                    h['damagePoint'], round(h['missileSpeed']), h['bat'], h['abbrev']))
lines.append('};')
lines.append('')
lines.append('static const AiHeroStat *aiFindHeroStat(uint32_t typeId)')
lines.append('{')
lines.append('    for (const AiHeroStat &h : kAiHeroStats) if (h.id == typeId) return &h;')
lines.append('    return nullptr;')
lines.append('}')
open(sys.argv[2], 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')
print('wrote', len(H), 'heroes ->', sys.argv[2])
