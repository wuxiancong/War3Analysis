# DotA 6.83d 玩法数据逆向：从受保护地图还原网页对战所需的全部数值

日期：2026-11-09 ~ 2026-11-10
样本：`D:\Maps\DotA v6.83d.w3x`（8,296,502 字节）、`C:\Program Files (x86)\iCCup Warcraft III\War3Patch.mpq`（1.26 基准常量）
产物：`War3Angular/public/assets/dota/gameplay-data.json`、`War3Angular/public/assets/maps/dota683/pathing.json`
脚本：`War3Angular/scripts/build-gameplay-data.cjs`、`War3Angular/scripts/build-pathing.cjs`、`War3Analysis/shared/scripts/mpq_extract_known.cjs`
证据摘录：`War3Analysis/artifacts/dota-web-gameplay/`
思维导图：[dota-6.83d-web-gameplay-data-reverse-mindmap.md](dota-6.83d-web-gameplay-data-reverse-mindmap.md)

> 范围说明：本次是**地图数据与脚本层**的逆向（MPQ / SLK / Profile / JASS / wpm / doo），**没有**对 `game.dll` 做新的 Ghidra/REA 反汇编。
> 引擎公式（护甲减伤、攻击循环）来自 `MiscGame.txt` 常量与公开的 WC3 机制，结论里凡是未经二进制或实机验证的都单独标出。

## 1. 结论速览

| # | 结论 | 证据 | 置信度 |
|---|---|---|---|
| 1 | 地图是 SLK 优化图：没有 `(listfile)`、没有 `war3map.w3u/w3t`，但标准路径的 `Units\*.slk` 与 `Units\*Func/Strings.txt` 全部在包内，可按文件名哈希直接命中 | `mpq_extract_known.cjs` 命中 62 个文件 | 高（已复现） |
| 2 | DotA 用 `war3mapMisc.txt` 覆盖了三围系数、经验表、攻击/护甲克制表 | `artifacts/dota-web-gameplay/war3mapMisc.txt` | 高 |
| 3 | 英雄面板可由 SLK + 上述系数完全算出，与游戏内显示一致 | 复仇之魂 攻击 39-53、护甲 3.78（见 §4） | 高（与公开数值吻合，未做内存对照） |
| 4 | 小兵经验不是脚本硬编码，而是引擎 `GrantNormalXP` 递推公式的自然结果 | 2/3/4 级 = 41/62/88（见 §5） | 高 |
| 5 | 出兵由单个 30 秒周期触发器驱动，近战数 `NI`、远程数 `SI`、每 7 波一辆攻城车、兵营存活标志决定普通/超级兵 | `war3map.j` 行 23185-23383、27846-27852 | 高 |
| 6 | 商店卖的是占位单位 `h0xx`（`Sellunits`），不是物品；真实物品码要经 War3Bot `dota_data.json` 的 `shopCode → realCode` 映射 | Profile `Sellunits` + `dota_data.json` | 高 |
| 7 | 物品被动加成可按技能基类 `code` 归并，`Aspb`(魔法书) 需递归展开 `DataA` | 193 件物品中 127 件解析出加成 | 中（未覆盖光环/法球类） |
| 8 | `war3map.wpm` 含地形与装饰物通行章，但**不含树**；树要从 `war3map.doo` 按 128 码补盖 | §7 | 高 |
| 9 | `YTlb` 不是树，是悬空（z≈1152）的视线阻断器；误当树会把近卫泉水出口封死 | §7 复现过程 | 高（已复现并修正） |
| 10 | 主动技能里大量是 `ANcl`(Channel) 空壳，真实效果在 JASS 触发器；`DataB` 给出目标方式 | `AbilityData.slk` | 高 |

## 2. 从受保护地图取文件

地图保护去掉了 `(listfile)`，`getFileNames()` 只返回 `File00000000…`（1298 个）。MPQ 的查找本来就是「路径名 → 哈希」，所以只要知道标准路径就能直接 `get()`：

```powershell
node D:\Qt\workspace\War3Analysis\shared\scripts\mpq_extract_known.cjs "D:\Maps\DotA v6.83d.w3x" C:\temp\dota683
```

命中的关键文件（字节数）：

| 文件 | 大小 | 用途 |
|---|---|---|
| `Scripts\war3map.j` | 3,026,043 | 全部触发器（混淆变量名，单位码写成十进制整数） |
| `war3mapMisc.txt` | 1,758 | 游戏常量覆盖 |
| `Units\UnitBalance.slk` | 603,499 | 1923 行：生命/护甲/移速/三围/赏金/等级 |
| `Units\UnitWeapons.slk` | 712,364 | 攻击间隔/前摇/骰子/射程/攻击类型/武器类型 |
| `Units\UnitUI.slk` / `UnitData.slk` / `UnitAbilities.slk` | — | 模型路径与缩放 / 转身速度与种族 / 技能列表 |
| `Units\AbilityData.slk` | 1,247,984 | 4373 个技能逐级 Cool/Cost/Rng/Area/Dur/DataA..I 与基类 `code` |
| `Units\ItemData.slk` | 273,930 | 1020 个物品：价格/技能列表/使用次数 |
| `Units\*UnitFunc/Strings.txt`、`*AbilityFunc/Strings.txt`、`Item*.txt` | — | UTF-8 中文名称、逐级提示、图标、弹道、`Sellunits` |
| `war3map.wpm` / `war3map.doo` / `war3map.w3e` | 262,160 / 218,340 / 116,568 | 通行图 / 装饰物与树 / 地形 |

未命中：`war3map.w3u`、`war3map.w3t`、`war3map.w3r`、`war3map.imp`、`war3mapUnits.doo`（优化器已把对象数据并入 SLK，预置单位改由脚本创建）。

`war3map.j` 只有 `\r` 换行；下文行号指 `tr '\r' '\n'` 之后的行号（共 97,289 行）。单位码以整数出现，例如 `'esen'` = `0x6573656E` = `1702061422`。

## 3. `war3mapMisc.txt`：DotA 覆盖的常量

与 1.26 `Units\MiscGame.txt` 对照（只列影响战斗的项）：

| 键 | 1.26 默认 | DotA 6.83d | 含义 |
|---|---|---|---|
| `StrHitPointBonus` | 25 | **19** | 每点力量生命 |
| `StrRegenBonus` | 0.05 | **0.03** | 每点力量回血/秒 |
| `IntManaBonus` | 15 | **13** | 每点智力魔法 |
| `IntRegenBonus` | 0.05 | **0.04** | 每点智力回蓝/秒 |
| `AgiDefenseBonus` / `AgiDefenseBase` | 0.30 / -2 | **0.14 / -1** | 敏捷护甲 |
| `AgiAttackSpeedBonus` | 0.02 | **0.01** | 每点敏捷攻速 |
| `MaxUnitSpeed` / `MinUnitSpeed` | 400 / 150 | **522 / 100** | 移速上下限 |
| `MaxHeroLevel` | 10 | **25** | |
| `NeedHeroXP` | 200（公式） | **显式 24 项**：200,500,900,1400,2000,2600,3200,4400,5400,6000,8200,9000,10400,11900,13500,15200,17000,18900,20900,23000,25200,27500,29900,32400 | 升到 2..25 级的累计经验 |
| `GlobalExperience` / `HeroExpRange` | 1 / 1200 | **0 / 0** | 关闭引擎分经验，改由脚本分配 |
| `MoveSpeedBonusesStack` | 0 | 0 | 鞋类不叠加 |
| `DefenseArmor` | 0.06 | 未覆盖 → 0.06 | 护甲减伤系数 |

克制表（列顺序 small, medium, large, fort, normal, hero, divine, none）：

| 攻击类型 | small | medium | large | fort | normal | hero | divine | none |
|---|---|---|---|---|---|---|---|---|
| Normal | 1.00 | 1.50 | 1.25 | 0.70 | 1.00 | 0.75 | 0.05 | 1.00 |
| Pierce | 2.00 | 0.75 | 0.75 | 0.35 | 1.00 | 0.50 | 0.05 | 1.50 |
| Siege | 1.00 | 0.50 | 1.25 | 1.50 | 1.00 | 0.75 | 0.05 | 1.00 |
| Magic | 1.25 | 0.75 | 2.00 | 0.35 | 1.00 | 0.75 | 0.05 | 1.00 |
| Chaos | 1.00 | 1.00 | 1.00 | 0.40 | 1.00 | 1.00 | 1.00 | 1.00 |

`DamageBonusSpells` / `DamageBonusHero` 地图未覆盖。网页端取 Spells 行英雄护甲 0.75（即 DotA 的 25% 基础魔抗），Hero 行沿用 1.26 默认。

**未验证**：技能伤害在引擎内到底走 `Spells` 行还是 `Magic` 行取决于每个技能脚本里 `UnitDamageTarget` 传的 `attacktype`，本次没有逐个技能核对。

## 4. 英雄面板公式（已用公开数值核对）

```
生命     = UnitBalance.HP + floor(力量) × 19
魔法     = UnitBalance.manaN + floor(智力) × 13
护甲     = UnitBalance.def + AgiDefenseBase(-1) + floor(敏捷) × 0.14
攻击     = UnitWeapons.dmgplus1 + (dice1 ~ dice1×sides1) + floor(主属性)
攻击间隔 = cool1 / (1 + 敏捷×0.01 + 装备攻速)
```

核对样例 复仇之魂 `Hvwd`（STR 18 / AGI 27 / INT 15，def 1，dmgplus 10，2d8）：

- 攻击 = 10 + 2..16 + 27 = **39 ~ 53** ✔（与 6.83 资料一致）
- 护甲 = 1 − 1 + 27×0.14 = **3.78** ✔
- 生命 = 150 + 18×19 = **492** ✔

注意：`War3Angular/src/app/replay3d/dota-heroes-archive.ts` 的 `heroAttrsAtLevel` 漏了 `AgiDefenseBase=-1`，算出的护甲偏高 1 点（本次未改动该文件，录像页仍用旧值）。

## 5. 小兵经验：引擎递推公式

`MiscGame.txt` 默认 `GrantNormalXP=25`、`GrantNormalXPFormulaA=1`、`B=5`；DotA 把 `C` 改成 6。按 `f(n) = f(n-1)×A + B×n + C`：

| 单位等级 | 推导 | 经验 | 对应 DotA 单位 |
|---|---|---|---|
| 1 | 25 | 25 | |
| 2 | 25 + 10 + 6 | **41** | 远程兵 `edry`/`unec` |
| 3 | 41 + 15 + 6 | **62** | 近战兵 `esen`/`ugho` |
| 4 | 62 + 20 + 6 | **88** | 攻城车 `ebal`/`umtw` |

三个数与 DotA 6.83 已知的小兵经验完全一致，说明小兵经验就是「单位等级 + 公式」，不需要脚本表。分配范围是脚本做的（`GlobalExperience=0`），网页端按 1300 码内敌方英雄平分近似。

**未验证**：英雄击杀经验与击杀金钱在 6.83 由脚本按连杀/等级差计算，网页端用的是简化式（`200 + 9×等级` 金；经验沿用引擎 `GrantHeroXP` 表）。

## 6. 出兵与成长（`war3map.j`）

证据摘录见 `artifacts/dota-web-gameplay/war3map.j-creep-spawn-excerpt.txt`。

| 行号 | 代码 | 含义 |
|---|---|---|
| 27846-27847 | `TriggerRegisterTimerEventPeriodic(ZG,30.00)` + `TriggerExecute(ZG)` | 出兵触发器，30 秒周期，注册时立即执行一次 |
| 96259 | `TriggerAddAction(ZG,function SPO)` | 出兵动作 = `SPO` |
| 23186 | `local boolean SQO=ModuloInteger(GetTriggerExecCount(ZG),7)==0` | 每第 7 次执行多出攻城单位 |
| 23229-23383 | `CreateNUnitsAtLoc(NI, <近战>, …)` / `CreateNUnitsAtLoc(SI, <远程>, …)` | 每路近战 `NI` 个、远程 `SI` 个 |
| 同上 | `if(HI)then … 1969711215 else … 1966092337` | 兵营标志真 → 普通兵，假 → 超级兵 |
| 91015-91016 | `set NI=3` / `set SI=1` | 初始 3 近战 + 1 远程 |
| 27850-27852 + 96179 | `TriggerRegisterTimerEventSingle(HG,999/1999/2999)` → `SOO: set NI=NI+1` | 近战在 999 / 1999 / 2999 秒各 +1 |
| 27849 + 96177 | `TriggerRegisterTimerEventSingle(GG,2699)` → `SIO: set SI=SI+1` | 远程在 2699 秒 +1 |
| 27848 + 96312 | `TriggerRegisterTimerEventPeriodic(UG,450.00)` → `TQO` | 每 450 秒给双方小兵科技 +1 级 |
| 23018-23033 | `SZO`/`SVO`：`TimerGetElapsed(M) < 7*60` 时加速度修正技能 | 前 7 分钟的兵线相遇点修正 |

单位码对照：

| 阵营 | 近战 | 远程 | 攻城 | 超级近战 | 超级远程 | 超级攻城 |
|---|---|---|---|---|---|---|
| 近卫 | `esen` 树人 | `edry` | `ebal` | `e00V` | `e00W` | `e026` |
| 天灾 | `ugho` 食尸鬼 | `unec` | `umtw` | `u001` | `u002` | `u00R` |

基础数值（SLK）：近战 550 HP / 护甲 2 / 攻击 19-23 normal / 间隔 1.0 / 前摇 0.467 / 赏金 38-48；远程 300 HP / 21-26 pierce / 射程 500；攻城 550 HP fort / 35-46 siege / 间隔 2.7 / 射程 690。

小兵升级（`UpgradeData.slk`，`TQO` 调的 `R007/R008/R009/R00A/R00C/R00D` 等）：每级 `rhpx` +10~19 生命、`ratx` +1~3 攻击，上限 30 级。网页端统一按「每 450 秒近战 +10 HP +1 攻、远程 +10 HP +2 攻」近似，**没有逐科技区分**。

塔与兵营（SLK）：

| 单位 | 层级 | HP | 护甲 | 攻击 | 间隔 | 射程 |
|---|---|---|---|---|---|---|
| `e00R` | T1 | 1300 | 20 fort | 100-120 normal | 1.0 | 700 |
| `e011` | T2 | 1600 | 25 fort | 120-140 siege | 0.95 | 700 |
| `e00S` | T3 | 1600 | 25 fort | 120-140 siege | 0.95 | 700 |
| `e019` | T4 | 1600 | 30 fort | 120-140 siege | 0.95 | 700 |
| `eaom` / `eaoe` | 近战/远程兵营 | 1500 / 1200 | 15 / 10 | — | — | — |
| `etol` / `unpl` | 世界之树 / 冰封王座 | 4250 | 15 | — | — | — |
| `nfoh` | 泉水 | — | — | 190-199 chaos | 0.15 | 1050 |

注意：`War3Angular/public/assets/maps/dota683/buildings.json` 里个别塔的 `unitId` 与层级不符（例如 `r_t2_top` 标成 `e00R`、`r_t1_mid` 标成 `e011`），天灾建筑没有 `unitId`。网页引擎改为按建筑 id 里的 `t1..t4` 取数值，两方对称；**没有修改 buildings.json**。

## 7. 寻路数据：wpm + 树

- `war3map.wpm`：魔数 `MP3W`，512×512 格，每格 32 码，`& 0x02` 为不可行走。近卫泉水附近实测只出现 `0x40`（可走）、`0xCA`、`0xCE` 三种值，带装饰物的格子正好落在墙上，说明装饰物通行章已烘进 wpm。
- `war3map.doo`：魔数 `W3do`，**版本 7**（每条记录 42 字节，没有 v8 的掉落表字段）。共 5198 个；`ATtr`×2061、`NTtw`×1551、`NTtc`×58 是树。
- 树在运行时盖章，wpm 里没有。按标准树 `4x4` 通行贴图（4×4 格 = 128 码）补盖后阻挡率 27.4% → 40.5%，ASCII 预览能看出三路与河道。
- **踩坑**：最初用 `/^[A-Z]T/` 判树，把 193 个 `YTlb` 也盖了章。`YTlb` 坐标 z=1152（悬空）、成排斜放，是视线阻断器，不挡路。它正好堵在近卫泉水出口，表现是无头模拟里近卫 5 个电脑 12 分钟全是 1 级、金钱不涨。排除 `YT*` 后恢复正常。

网页端把 32 码格降采样到 64 码格（4 个细格里 ≥2 个不可走即阻挡）做 8 向 A*，再用视线拉直。**未验证**：与引擎真实寻路（含单位碰撞体积、转身）的路径差异没有实机对比。

## 8. 技能与物品的数据形态

### 技能

- `AbilityData.slk` 的 `code` 是基类。基类自带语义的可以直接用数据驱动，例如 `AHtb`(风暴之锤)：`DataA`=伤害、`Dur/HeroDur`=眩晕。复仇之魂 魔法箭 `A02A`：100/175/250/325 伤害、1.45~1.75 秒、冷却 13~10、耗蓝 110~140、弹道速度 1250，与游戏内一致。
- `ANcl`(Channel) 是空壳：`DataB` = 目标方式（0 无目标 / 1 单位 / 2 点 / 3 单位或点），`DataF` = 借用的命令串，真实效果在 `war3map.j`。这类技能的数值只存在于中文提示文本里。
- 网页端做法：`resolveAbilityFx()` 先看基类，再从 `Ubertip` / `Researchubertip` 的「等级 n - …」行用正则取 伤害 / 眩晕秒数 / 减速百分比 / 治疗量 / 范围。解析不出任何效果的标记 `implemented=false`，UI 里明示「脚本技能·未还原特效」。

**这是近似，不是还原**：位移、召唤、变身、持续施法、多段伤害、任何带条件的效果都不在其中。每个英雄真正可玩的程度要看其技能有多少落在「单体/范围 伤害+控制」这一类。

### 物品

- 商店：Profile 里带 `Sellunits` 的单位。区分出 13 个酒馆（卖英雄）、15 个物品商店（卖占位单位 `h0xx`）、若干信使商店（卖 `h085,h0BV,h0DE`）。
- 占位单位 → 真实物品：`War3Bot/images/dota_data.json` 的 `items[shopCode].realCode`；合成表用同文件的 `recipes`（去重后 92 条可完整解析）。
- 被动加成按基类归并：`AIab` 三围（A 敏 / B 智 / C 力）、`AIat` 攻击、`AIde` 护甲、`AIml` 生命、`AImm` 魔法、`Arel` 回血、`AIrm` 回蓝百分比、`AIas` 攻速、`AIms` 移速、`AIva` 吸血、`AEev` 闪避、`AOcr` 暴击、`AHbh` 重击、`Aspb` 魔法书递归。核对：攻击之爪 `AIt9` → +9 攻击；恐鳌之心 → +300 生命 +40 力量。
- 未覆盖：光环类（`AOae`/`AHab`/`AHad`/`AUau`）、法球、主动技能大部分（只做了闪烁、回城、推推、消耗品回复）。

## 9. 未验证 / 后续

1. 用 Ghidra 工程 `War3_127` 找 `DefenseArmor` 的引用，确认负护甲增伤式 `2 − 0.94^(−a)` 与攻击前摇/后摇状态机；本次只用了公开公式。
2. 逐个英雄读 `war3map.j` 里技能触发器，把 `ANcl` 技能从「提示文本近似」升级为真实实现。
3. 英雄击杀金钱/经验、买活、连杀奖励的脚本公式。
4. 小兵各科技（`R007`…）逐项成长值，替换当前的统一近似。
5. 高低地 25% 丢失（`ChanceToMiss`）、昼夜视野、战争迷雾，网页端都还没有。
6. 修 `buildings.json` 的 `unitId` 与 `dota-heroes-archive.ts` 的护甲基数（影响录像页）。

## 10. 复现

```powershell
cd D:\Qt\workspace\War3Angular
node scripts\build-gameplay-data.cjs     # → heroes=112 abilities=450 items=193 recipes=92 shops=15 taverns=13 units=104
node scripts\build-pathing.cjs           # → wpm 512x512 trees=3676 blocked=40.5%
node scripts\run-game-sim.cjs 20         # 无头 10 电脑对战 20 分钟 + 确定性校验
```
