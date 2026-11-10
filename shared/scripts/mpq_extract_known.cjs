// 按已知文件名（哈希探测）从受保护的 w3x / MPQ 中导出游戏性数据表
// 受保护地图没有 (listfile)，只能用标准路径名做哈希命中。
// 用法: node mpq_extract_known.cjs <archive> <outDir> [names.txt]
const fs = require('fs');
const path = require('path');
const MpqArchive = require('D:/Qt/workspace/War3Angular/node_modules/mdx-m3-viewer/dist/cjs/parsers/mpq/archive.js').default;

const [, , arc, outDir, namesFile] = process.argv;

const RACES = ['Campaign', 'Human', 'Orc', 'Undead', 'NightElf', 'Neutral'];
const DEFAULT = [
  'war3map.j', 'Scripts/war3map.j', 'war3map.w3i', 'war3map.wts', 'war3map.w3u', 'war3map.w3t', 'war3map.w3a',
  'war3map.w3b', 'war3map.w3d', 'war3map.w3h', 'war3map.w3q', 'war3mapMisc.txt', 'war3mapSkin.txt', 'war3mapExtra.txt',
  'war3mapUnits.doo', 'war3map.doo', 'war3map.w3e', 'war3map.wpm', 'war3map.w3r', 'war3map.w3c', 'war3map.imp',
  'Units/UnitBalance.slk', 'Units/UnitData.slk', 'Units/UnitUI.slk', 'Units/UnitWeapons.slk', 'Units/UnitAbilities.slk',
  'Units/AbilityData.slk', 'Units/AbilityBuffData.slk', 'Units/ItemData.slk', 'Units/UpgradeData.slk',
  'Units/UnitMetaData.slk', 'Units/AbilityMetaData.slk', 'Units/DestructableData.slk',
  'Units/MiscGame.txt', 'Units/MiscData.txt', 'Units/MiscUI.txt',
  'Units/ItemFunc.txt', 'Units/ItemStrings.txt', 'Units/ItemAbilityFunc.txt', 'Units/ItemAbilityStrings.txt',
  'Units/CommonAbilityFunc.txt', 'Units/CommonAbilityStrings.txt', 'Units/CommandFunc.txt', 'Units/CommandStrings.txt',
  'Scripts/common.j', 'Scripts/Blizzard.j', 'UI/MiscData.txt',
];
for (const r of RACES) {
  for (const k of ['UnitFunc', 'UnitStrings', 'AbilityFunc', 'AbilityStrings', 'UpgradeFunc', 'UpgradeStrings']) {
    DEFAULT.push(`Units/${r}${k}.txt`);
  }
}

const names = (namesFile ? fs.readFileSync(namesFile, 'utf8').split(/\r?\n/).filter(Boolean) : DEFAULT).map((n) =>
  n.split('/').join('\\')
);
const buf = fs.readFileSync(arc);
const a = new MpqArchive();
a.load(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), true);
fs.mkdirSync(outDir, { recursive: true });
for (const n of names) {
  const f = a.get(n);
  if (!f) continue;
  let b;
  try {
    b = Buffer.from(f.bytes());
  } catch (e) {
    console.log('ERR ', n, e.message);
    continue;
  }
  fs.writeFileSync(path.join(outDir, n.split('\\').join('_')), b);
  console.log('OK  ', n, b.length);
}
