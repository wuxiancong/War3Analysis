---
title: DotA 6.83d 玩法数据逆向（网页对战数据源）思维导图
markmap:
  colorFreezeLevel: 2
  maxWidth: 420
---

# DotA 6.83d 玩法数据逆向

## 一、取数路径

### 受保护地图
- 无 `(listfile)`，`getFileNames()` 只有 `File000xxxxx`
- 按标准路径名哈希直接命中（62 个文件）
- 脚本：`shared/scripts/mpq_extract_known.cjs`

### 命中的表
- `war3mapMisc.txt`：常量覆盖
- `Units\UnitBalance/Weapons/UI/Data/Abilities.slk`
- `Units\AbilityData.slk`（4373 技能）
- `Units\ItemData.slk`（1020 物品）
- `*Func.txt / *Strings.txt`：UTF-8 中文提示、`Sellunits`
- `war3map.j`（`\r` 换行，单位码为十进制整数）
- `war3map.wpm` / `war3map.doo` / `war3map.w3e`

### 未命中
- `w3u` / `w3t` / `w3r` / `imp`（已并入 SLK）

## 二、常量（war3mapMisc.txt）

### 三围系数
- 力量：19 生命、0.03 回血
- 智力：13 魔法、0.04 回蓝
- 敏捷：0.14 护甲（基数 -1）、0.01 攻速

### 上限
- 英雄 25 级，`NeedHeroXP` 显式 24 项
- 移速 100 ~ 522
- 鞋类移速不叠加

### 克制表
- Normal / Pierce / Siege / Magic / Chaos × 8 种护甲
- 英雄护甲：Normal 0.75、Pierce 0.50、Siege 0.75
- `DefenseArmor` 未覆盖 → 0.06

### 经验
- `GlobalExperience=0`：脚本分经验
- `GrantNormalXPFormulaC=6`

## 三、已核对的公式

### 英雄面板（复仇之魂）
- 攻击 10 + 2d8 + 27 = 39~53 ✔
- 护甲 1 − 1 + 27×0.14 = 3.78 ✔
- 生命 150 + 18×19 = 492 ✔

### 小兵经验递推
- f(n) = f(n-1) + 5n + 6，f(1)=25
- 2 级 41（远程）/ 3 级 62（近战）/ 4 级 88（攻城）✔

## 四、出兵（war3map.j）

### 触发器
- `ZG` 30 秒周期 → `SPO`（行 23185）
- 第 7 次执行加攻城车
- `NI=3` 近战、`SI=1` 远程

### 成长
- 近战 +1：999 / 1999 / 2999 秒
- 远程 +1：2699 秒
- `UG` 每 450 秒科技 +1（生命/攻击）

### 超级兵
- 兵营标志 `HI/ZI/VI…` 假 → `u001/u002/u00R`、`e00V/e00W/e026`

### 建筑数值
- T1 `e00R` 1300 HP / 20 甲 / 100-120
- T2~T4 `e011/e00S/e019` 1600 HP / 25~30 甲 / 120-140 siege
- 兵营 1500 / 1200，基地 4250

## 五、寻路

### wpm
- `MP3W` 512×512，32 码格，`0x02` 不可走
- 含地形 + 装饰物章，不含树

### doo
- 版本 7，每条 42 字节
- 树：`ATtr` / `NTtw` / `NTtc`，按 128 码补盖

### 踩坑
- `YTlb` 是悬空视线阻断器（z≈1152）
- 误盖章 → 近卫泉水出口被封 → 电脑全员 1 级
- 排除 `YT*` 后修复

## 六、技能与物品

### 技能
- 基类自带语义：`AHtb` 等可纯数据驱动
- `ANcl` 空壳：`DataB` = 目标方式，效果在 JASS
- 回退：从中文提示解析 伤害 / 眩晕 / 减速 / 治疗 / 范围
- 解析不出 → `implemented=false`，UI 明示

### 物品
- 商店卖占位单位 `h0xx`（`Sellunits`）
- `dota_data.json`：`shopCode → realCode`、合成表
- 被动按基类归并：`AIab/AIat/AIde/AIml/AImm/Arel/AIrm/AIas/AIms/AIva/AEev/AOcr/AHbh`
- `Aspb` 魔法书递归展开

## 七、未验证

- 没有做新的 game.dll 反汇编（护甲/攻击状态机用公开公式）
- 技能伤害走 Spells 行还是 Magic 行未逐个核对
- 英雄击杀金钱/经验为简化式
- 小兵科技成长为统一近似
- 高低地丢失、昼夜、战争迷雾未实现
- `buildings.json` 个别 `unitId` 与层级不符（未改）
