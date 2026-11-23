# DotA 6.83d 全英雄技能伤害公式与「技能施放评分系统」

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Composer（Cursor Agent） |
| **分析目的** | 从 `war3map.j` + 物编 SLK/Strings 提取全英雄技能伤害/几何参数，设计可落地的 Skill Cast Scoring，拦截空放并服务团战 AOE 选点 |
| **命名方式** | `dota-hero-skill-damage-and-cast-scoring` |
| **分析时间** | 2026-11-23 |
| **地图** | DotA Allstars 6.83d |
| **关联任务** | [`tasks/grok-hero-skill-damage-and-cast-scoring.md`](../tasks/grok-hero-skill-damage-and-cast-scoring.md)、[`tasks/grok-teamfight-key-target-scoring.md`](../tasks/grok-teamfight-key-target-scoring.md) |
| **机器可读表** | [`artifacts/skill-scoring/hero_skill_formulas.json`](../artifacts/skill-scoring/hero_skill_formulas.json)（112 英雄 / 467 技能） |
| **C++ 草案** | [`artifacts/skill-scoring/AiSkillCastScore.h`](../artifacts/skill-scoring/AiSkillCastScore.h) |
| **离线验证** | `python artifacts/skill-scoring/validate_sf_raze_scoring.py` → **8/8 PASS，空放拦截 100%** |

---

## 一、结论摘要

1. **全英雄表已生成**：`dota_data.json` 112 英雄全部入库；每技能含 SLK `Area/Rng/Cool/Cost/DataA..F`、Strings 解析伤害、`scoringClass`、置信度。
2. **任务点名机制已 JASS/物编核对**（非推断）：
   - 影魔影压：圆心 **200/450/700**，半径 **275**（任务写 250 有误；脚本 `GroupEnumUnitsInRange(...,275)`），伤害 **25+75×等级**，`DAMAGE_TYPE_DEATH`。
   - 魂之挽歌：线数 **souls/2**，每线 80/120/160；致残圈 **200/400/700**。
   - 火女光击阵：半径 **225**，延迟 **0.5s**，伤 120/160/200/240；龙破斩：`AOsh` 波，长 **800**、末端半径 **275**。
   - 变体攻击：敏捷/力量比阈值 **0.5 / 1.5**，`dmg = 20×lv + mult×agi`，晕眩/击退随力量比分支（见 §2.3）。
3. **评分模型**：单体 `hitProb × 税后伤害 / 理论最大`；AOE `Σ w_key(e)·ExpectedDmg`；**预期命中=0 且非探视野/逃生 → 0 分并拦截**。
4. **减伤**：物理 `1/(1+0.06A)`；魔法 `×(1−MR)`，英雄基础 MR **25%**，来源乘算；`P6I` 类型 7/8 为纯粹（UNIVERSAL）。

> 半径说明：任务草稿写影压 250；物编 Researchubertip 与 `war3map_7.j QK4` 均为 **275**。运行时 lane 代码用 260 作移动余量，查表应写 **275**。

---

## 二、逆向要点（优先机制）

### 2.1 影魔 `Nfir`

| 技能 | 码 | 几何 | 伤害 | 蓝/CD | 前摇 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 近影压 Z | `A0EY` | 朝向圆心 200，r=275 | 100/175/250/325 | 75 / 10s | 英雄 `castpt`≈0.67（`UnitWeapons`） |
| 中影压 X | `A0FH` | 圆心 450，r=275 | 同上（读自身等级） | 75 / 10s | 同 |
| 远影压 C | `A0F0` | 圆心 700，r=275 | 同上 | 75 / 10s | 同 |
| 魂之挽歌 R | `A29J` | 径向线 `souls/2` + 致残 200/400/700 | 每线 80/120/160 | 150/175/200 · 120/110/100 | Cast=1.0s |

JASS（`war3map_7.j`）：

```jass
// QJ4：影压伤害
UnitDamageTarget(..., 25+75*GetUnitAbilityLevel(...,GetSpellAbilityId()), ..., DAMAGE_TYPE_DEATH)
// QK4：圆心距离 200 / 450 / 700，半径 275
```

**转身容差（评分门控）**：现网 `war3hook_ai_lane.inl` 使用 **≤9°** 才允许放出；评分里 >9° 直接按空放风险 `score=0` 拦截。

**挽歌命中线数**：线均匀 360° 射出；贴身单位立体角更大 → 穿过更多线。评分应用 `w_key` 提高贴身核心的期望线数收益（见关联关键目标任务）。

### 2.2 火女 `H004`

| 技能 | 码 | 几何 | 伤害 | 其它 |
| :--- | :--- | :--- | :--- | :--- |
| 龙破斩 D | `A01F` | Shockwave：长 800，末端 r≈275，DataD 起点宽提示 200 | 110/180/250/320 | CD 8.5，蓝 100/115/130/145 |
| 光击阵 T | `A027` | 点地圆 r=225，**延迟 0.5s** | 120/160/200/240 + 晕 1.6~2.5s | Rng SLK=625；蓝 SLK 100/110/120/130（tip 写 90… 以 SLK 为准） |
| 神灭斩 G | `A01P` | 单体 | 450/675/950 | 神杖码 `A09Z` 走 `P6I` type7（对非虚无偏纯粹） |

### 2.3 变体精灵 `O00P` 变体攻击 `A0G6`

`war3map_5.j JR3`（`P6I` type1 = 魔法）：

\[
\begin{aligned}
r_{as}&=\mathrm{agi}/\mathrm{str},\quad r_{sa}=\mathrm{str}/\mathrm{agi}\\
\mathrm{mult}&=\begin{cases}
0.25 & r_{as}<0.5\\
0.5\cdot lv & r_{as}>1.5\\
0.25+(r_{as}-0.5)(0.5\cdot lv-0.25) & \text{else}
\end{cases}\\
\mathrm{dmg}&=20\cdot lv + \mathrm{mult}\cdot\mathrm{agi}\\
\mathrm{stun}&=\begin{cases}
0.25 & r_{sa}<0.5\\
0.25+lv & r_{sa}>1.5\\
\text{线性插值} & \text{else}
\end{cases}\\
\mathrm{kb}&\in[100,300]\ \text{按 }r_{sa}\text{ 插值}
\end{cases}
\end{aligned}
\]

射程 600/700/800/900，蓝 100，CD 10。

### 2.4 属性/状态缩放（表内已标 `attr_scaled_unit` / tip）

| 英雄 | 技能 | 公式要点 |
| :--- | :--- | :--- |
| 敌法 `Edem` | `A2WE` 法力虚空 | 缺失蓝量 × 系数，AOE r=500 |
| 死灵法 `U00E` | `A067` 死神镰刀 | 已损血量比例（晕后结算） |
| 天怒 `H0DO` | `A2BG` 神秘之耀 | 点地小圈 r=170 持续伤害 |
| 沉默 `N01A` | `A0LZ` 智慧之刃 | 智力差缩放（tip；表内待 JASS 加深） |

### 2.5 团体 AOE（节选，完整见 JSON）

| 英雄 | 技能 | 半径/形态 | 魔免 |
| :--- | :--- | :--- | :--- |
| 潮汐 `Ofar` | `A29I` 毁灭 | 825/925/1025 扩散 | 魔法 |
| 谜团 `Uktl` | `A1BX` 黑洞 | 400 引导 | **纯粹/穿 BKB**（tip） |
| 神牛 `Otch` | `A0DH` 回音击 | 575 + 回音额外 | 魔法 |
| 沙王 `U00K` | `A06R` 地震 | 300/350/400 脉冲 | 魔法 |
| 蓝猫 `H00S` | `A14O` 球状闪电 | 路径伤害 | 魔法 |
| 猛犸/半人马 `H000` | `A00S` 践踏 | 315 | 魔法 |

---

## 三、伤害减免

### 3.1 护甲（物理）

\[
\text{taken}=\text{raw}\cdot\frac{1}{1+0.06\cdot A}
\]

来源：`Misc/DefenseArmor=0.06`，`CalcArmorReduction`（见 `war3-lasthit-combat-data.md`）。适用于 `P6I` 2/4/5 与普攻物理。

### 3.2 魔抗（魔法）

- 英雄基础 **25%**（`DamageBonusSpells` 对英雄系数 0.75）。
- 多来源 **乘算**：\(MR=1-\prod_i(1-s_i)\)。
- 减抗（毒球/绝灭/虚灵等）作为负来源乘入。
- `P6I`：**1/3→魔法**；**7/8→UNIVERSAL（纯粹）**；7 在虚无上退化为魔法。

影压走引擎 `DAMAGE_TYPE_DEATH`（非 `P6I`），按魔法减免处理。

---

## 四、技能施放评分模型

### 4.1 单体 / 指向性（0~100）

\[
\mathrm{Score}_{ST}=100\cdot \hat{p}_{\mathrm{hit}}\cdot\frac{D_{\mathrm{post}}}{D_{\mathrm{max}}}
\]

- \(\hat{p}_{\mathrm{hit}}\)：前摇 + 弹道/延迟内，用目标速度预测位置后的命中概率（离散几何可取 0/1）。
- **空放**：\(\hat{p}_{\mathrm{hit}}=0\) 且非 `utilityIgnoreEmpty`（探视野/逃生/全局沉默等）→ **score=0 且 block**。
- **补刀魔量性价比**：farm 上下文中，命中残血敌兵数 `<2` 时默认 block；例外：`denyWaiting && mana≥150`（必漏关键兵）将分抬到 ≥60 放行。

影压专用（与 lane 对齐并修正单兵例外）：

- 朝向误差 `>9°` → 视为空放风险，block。
- `kills≥2` 基础分高；`kills==1` 仅反补例外可过阈值 60。

### 4.2 团体 AOE（0~100）

对候选点集合 \(P\)（英雄脚下网格、敌方质心、朝向采样）：

\[
S(p)=\sum_{e\in\mathrm{Hit}(p)} w_{\mathrm{key}}(e)\cdot \mathbb{E}[Dmg(e,p)]
\]

\[
\mathrm{Score}_{AOE}(p)=100\cdot\frac{S(p)}{\max_{q\in P}S(q)}
\]

\(w_{\mathrm{key}}\) 接入团战关键目标权重（输出威胁 / 未交大控 / 斩杀收益）。影魔大招：贴身高 \(w_{\mathrm{key}}\) 目标以最大化线数 × 伤害。

运行时：**`Score < 60` 禁止施放**（可配置）。

### 4.3 决策伪代码

```text
intent = proposeCast(...)
result = aiScoreSkillCast(intent, casterSnap, enemySnaps)
if result.block: discard / turn-first / re-aim
else: enqueue action when result.score >= threshold
postGame: log result.score as cast quality 0..100
```

---

## 五、C++ 落地接口

头文件草案：[`AiSkillCastScore.h`](../artifacts/skill-scoring/AiSkillCastScore.h)

```cpp
CastScoreResult aiScoreSkillCast(
    const CastIntent& in,
    const CasterSnap& caster,
    const std::vector<UnitSnap>& enemies);
```

- **纯逻辑**：不调 JASS/原生；可用 CSV/JSON 回放。
- 查表：从 `hero_skill_formulas.json` 生成 `SkillFormula` 静态表（或运行时加载）。
- 已实现几何：`ForwardCircle`（影压）、`PointCircleDelayed`（光击阵）、`AttrScaledUnit`（变体攻击）、通用加权 AOE。
- 合入建议：抽离 `war3hook_ai_lane.inl` 中 `evalRazeScore`，统一走本接口；团战大招在 `war3hook_ai_tactics.inl` 调 AOE 分支。

---

## 六、离线验证（影魔影压）

样本：[`sf_raze_offline_cases.json`](../artifacts/skill-scoring/sf_raze_offline_cases.json)

| 用例 | 预期 | 结果 |
| :--- | :--- | :--- |
| 空放（错档位/无兵） | block，score=0 | PASS |
| 朝向偏差 15°/25° | block | PASS |
| 双残血近炮 | 放行，高分 | PASS |
| 单兵低蓝 | block | PASS |
| 单兵+反补等待 | 抬分放行 | PASS |

```text
Empty-cast interception: 4/4 = 100.0%
ALL PASS
```

---

## 七、数据表覆盖说明

| 项 | 数量 |
| :--- | ---: |
| 英雄 | 112 |
| 技能条目（含隐藏槽如影魔 X/C） | 467 |
| 含明确伤害数字（tip/SLK/JASS） | ~207 |
| JASS/重点覆盖覆盖码 | 18（影压三连、挽歌、变体、火女、潮汐/谜团/神牛/沙王/敌法大等） |
| 主动但无「伤害曲线」 | 多为控制/变身/召唤/开关；仍保留射程/CD/蓝/几何 |

重建：

```powershell
python D:\Qt\workspace\War3Analysis\artifacts\skill-scoring\build_hero_skill_formulas.py
python D:\Qt\workspace\War3Analysis\artifacts\skill-scoring\validate_sf_raze_scoring.py
```

后续加深：对 `active without damage` 中的爆发技继续扫 `war3map_*.j` 的 `GetSpellAbilityId()==FourCC` + `P6I`/`UnitDamageTarget`，把 `confidence` 从 `tip+slk` 升到 `jass`。

---

## 八、与现有 hook 的差异修正

| 项 | 旧 | 本分析 |
| :--- | :--- | :--- |
| 影压半径 | lane 用 260（余量） | 真值 **275**；预测可用 260~275 |
| 影压伤害 | `25+75*lv`（已正确） | JASS 确认 |
| 单兵放行 | `castScore≥60` 实际锁死单兵 | 评分器在 `denyWaiting` 时抬到 60 |
| 空放 | 方向硬门控 | 升为通用 `aiScoreSkillCast` 的 `empty`/`facing` 原因码 |
