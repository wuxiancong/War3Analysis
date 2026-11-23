# DotA 团战「关键英雄（Key Target）」动态评估与集火 / 贴身大招选人

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Cursor Auto / Composer |
| **分析目的** | 为 `war3hook_ai_tactics.inl` 提供可落地的团战关键目标权重 $w_{\text{key}}(e)$：用全版本只读内存字段评估敌方每位英雄的输出 / 控制 / 斩杀 / 可达性，驱动集火与 AOE（含影魔 `A29J` 等）贴身选点；覆盖 DotA 6.83d **全部 112 英雄**控制先验，而非单英雄特例 |
| **命名方式** | `dota-teamfight-key-target-scoring`；配套数据 `artifacts/teamfight-key-target/hero_control_threat_683d.json` |
| **分析时间** | 2026-11-23 |
| **覆盖版本** | `War3Launcher/versions/` 全部 **11** 版 `game.dll`（`1.0.17.5988` ~ `1.27.0.52240`）；结构偏移以既有全版本核验为准并在此汇总 |
| **验证状态** | 静态：全英雄控制表由 `dota_data.json` + `dota_hero_skills.json` 生成（112/112）；只读字段 / 冷却链复用既有全版本反汇编结论。**未做本轮实机注入**；C++ 草案可离线单测 |
| **相关文档** | [`war3-order-packet-flags-and-ability-item-cooldown.md`](./war3-order-packet-flags-and-ability-item-cooldown.md)、[`war3-lasthit-combat-data.md`](./war3-lasthit-combat-data.md)、[`dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md`](./dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md)、[`dota-6.83d-active-items-and-consumables-reverse.md`](./dota-6.83d-active-items-and-consumables-reverse.md)、任务 [`tasks/grok-hero-skill-damage-and-cast-scoring.md`](../tasks/grok-hero-skill-damage-and-cast-scoring.md)（$w_{\text{key}}$ 消费者） |
| **配套产物** | [`artifacts/teamfight-key-target/hero_control_threat_683d.json`](../artifacts/teamfight-key-target/hero_control_threat_683d.json)、[`hero_control_threat_683d.md`](../artifacts/teamfight-key-target/hero_control_threat_683d.md)、[`build_control_threat_table.py`](../artifacts/teamfight-key-target/build_control_threat_table.py) |

---

## 〇、结论先行

1. **关键目标不是「最近」或「人群中心」**：团战应最大化
   $$\text{Score}_{\text{focus}}(e)=w_{\text{key}}(e),\qquad
     \text{Score}_{\text{AOE}}(p)=\sum_{e\in Hit(p)} w_{\text{key}}(e)\cdot\text{ExpectedDmg}(e,p)$$
2. **四维只读输入**（对任意敌方英雄通用，零发包风险）：
   - **DPS**：`CAbilityAttack` 的 `dmgBase+bonus`、`ias`、英雄等级、背包威胁标签；
   - **Control**：`CAbilitySpell` 等级 + `+0xD0` 剩余冷却 × 全英雄控制先验表；
   - **Killability**：`life/maxLife`、护甲、`+0x158` 魔免计数、隐身 / 逃生物品 CD；
   - **Reachability**：几何距离 × 我方跳刀 / 隐刀 / BKB 是否就绪。
3. **阶段权重**：开团先手偏 **控制未交**；残局收割偏 **高 DPS × 残血**。
4. **全 112 英雄**控制先验已落盘；运行时仍以内存冷却为准——表只回答「哪些技能算威胁」。
5. **工程入口**：纯逻辑 `aiRankTeamfightTargets(...)`，可直接合入 `war3hook_ai_tactics.inl`，不调原生。

---

## 一、团战评估输入源（全版本只读）

### 1.1 字段总览（`1.22`~`1.27` 结构同构；早期版见下表注）

| 维度 | 读取路径（已在 hook 中部分落地） | 用途 |
| :--- | :--- | :--- |
| 位置 | JASS `GetUnitX/Y`（现有 `aiQueryPosition`） | 距离 / AOE 覆盖 |
| 血量 | `GetWidgetLife` / `GetUnitState(LIFE/MAX_LIFE)`（`aiQueryLife`） | `killScore` |
| 等级 | `GetHeroLevel`（`aiHeroLevel`） | DPS 归一化 |
| 攻防 | `CUnit+0x1E8` → `CAbilityAttack`：`+0xA0` base、`+0xAC` bonus、`+0x1B0` ias、`+0x158` BAT（`aiReadAttackInfo`） | `dpsScore` |
| 护甲 | `CUnit+0xE0` / `+0xE4` defType | 物理斩杀修正 |
| 技能链 | `CUnit+0x1DC/+0x1E0` → `abil+0x24/+0x28`，FourCC `+0x34`，等级 `+0x50`（0-based） | 控制技能枚举 |
| 冷却 | `CAbilitySpell+0xD0` → `readAgentTimer`；标志 `+0x20 & 0x200` | 「大招未交 / 已交」 |
| 背包 | `aiReadInventory`（`UnitItemInSlot` + `aiItemTagOf`） | BKB / 蝴蝶 / 羊刀 / 刷新 / 跳刀 / 隐刀… |
| 魔免态 | `CUnit+0x158`（`IsUnitType` 魔免计数，`>0`）或 Buff 链表含 `'A0FY'`（BKB） | 魔法大招无效 / 物理仍可打 |
| 幻象 | `CUnit+0x5C & 0x40000000` | 权重 ×0（不集火幻象） |

> 血量 / 等级 / 背包今日路径含 JASS 原生只读；攻击 / 护甲 / 冷却 / 技能链可纯内存。团战评分逻辑层不关心来源，只吃 `AiTfHeroSnap` 快照。

### 1.2 `CAbilityAttack` / 护甲 / 冷却 —— 全 11 版偏移与 RVA

**结构偏移（字段布局）**

| 字段 | `1.22.0` ~ `1.27.0` | `1.0.17` ~ `1.21` |
| :--- | :---: | :--- |
| `CUnit → CAbilityAttack*` | **`+0x1E8`** | 早期布局不同，联调勿假定（主力 1.24+） |
| `CUnit → armor / defType` | **`+0xE0` / `+0xE4`** | 未全核（见 lasthit 文档） |
| `CUnit → ability list` | **`+0x1DC` / `+0x1E0`** | `1.22+` 同构 |
| `CAbilitySpell` 等级 / 冷却定时器 | **`+0x50` / `+0xD0`** | **`+0xD0` 全 11 版一致**（cooldown 文档） |
| `CAbilitySpell` 状态标志 | **`+0x20`**（`0x200`=CD 中） | 同左（`1.22+` 实证） |
| `CAbilityAttack` dmg/ias/BAT | **`+0xA0/+0xAC/+0x1B0/+0x158`**（双武器 `idx`） | `1.25~1.27` 一致；更早见 combat 文档 |

**`CAbilitySpell::StartCooldown` / 计时器偏移（全 11 版）** — 摘自 [`war3-order-packet-flags-and-ability-item-cooldown.md`](./war3-order-packet-flags-and-ability-item-cooldown.md)：

| 版本 | `StartCooldown` RVA | 计时器偏移 |
| :--- | :---: | :---: |
| `1.0.17.5988` | `0x46F120` | **`+0xD0`** |
| `1.0.20.6048` | `0x46F620` | **`+0xD0`** |
| `1.20.4.6074` | `0x46FB90` | **`+0xD0`** |
| `1.21.0.6263` | `0x473AC0` | **`+0xD0`** |
| `1.22.0.6328` | `0x0502B0` | **`+0xD0`** |
| `1.23.0.6352` | `0x0517F0` | **`+0xD0`** |
| `1.24.1.6374` | `0x0518A0` | **`+0xD0`** |
| `1.24.4.6387` | `0x0518B0` | **`+0xD0`** |
| `1.25.1.6397` | `0x050B70` | **`+0xD0`** |
| `1.26.0.6401` | `0x050B70` | **`+0xD0`** |
| `1.27.0.52240` | `0x418D20` | **`+0xD0`** |

**`GetCooldownRemaining` / `GetHeroLevel` 等原生 RVA** — 摘自 [`dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md`](./dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md) §3（全 11 行已核，此处不重复抄全表；实现挂版本表即可）。

**工程利好**：`1.22`~`1.27` 冷却 / 技能链 / 攻击字段偏移一致 → hook **不必为评分逻辑写版本分支**，只在解析 `CUnit*` 时用既有版本 RVA。

### 1.3 输出威胁（DPS Threat）

```
avgDmg   = dmgBase + dmgBonus + dice * (sides+1)/2
atkPeriod= BAT / clamp(ias, 0.2, 5.0)
rawDps   = avgDmg / atkPeriod
```

装备倍率（经 `aiReadInventory` 的 `tags[]`，已有枚举）：

| 标签 | 对 `dpsScore` 的建议加成 | 备注 |
| :--- | ---: | :--- |
| `AI_ITEM_BUTTERFLY` | +0.25 | 攻速 + 闪避（输出侧） |
| `AI_ITEM_MKB_ON` | +0.20 | 真击 + 攻速 |
| `AI_ITEM_SATANIC` | +0.15 | 残局吸血威胁 |
| `AI_ITEM_MOM` | +0.15 | 开着时再叠 |
| `AI_ITEM_RADIANCE_ON` | +0.10 | 光环灼烧 |
| `AI_ITEM_HEX` / `ORCHID` / `ABYSSAL` | 计入控制物品，见下 | |
| `AI_ITEM_BKB`（背包有且 CD 好） | 见 Reach/Kill | 「能开魔免输出」 |
| `AI_ITEM_REFRESHER` | +0.20 若大招刚交且刷新就绪 | 二次大招威胁 |

> 黯灭 / 暴击斧等若尚未进 `AI_ITEM_*` 枚举：短期用 FourCC 白名单（`I0**`）扩 `aiItemTagOf`；评分公式预留 `itemDpsMul`。

等级归一：`levelFactor = 0.55 + 0.45 * (heroLevel / 25)`。

### 1.4 控制威胁（Control Threat）—— 全英雄

静态先验：[`hero_control_threat_683d.json`](../artifacts/teamfight-key-target/hero_control_threat_683d.json)（112 英雄）。

| tier | 含义 | 基础权重区间 |
| :--- | :--- | :--- |
| `TEAM_ULT` | 团控大招（黑洞 / 时间结界 / 毁灭 / RP / 回音击 / 海妖之歌…） | 0.80~1.00 |
| `HARD_CC` | 硬控（晕 / 羊 / 枷锁 / 沟壑 / 光击阵…） | 0.70~0.90 |
| `SOFT_CC` | 沉默 / 减速 / 软控 | 0.30~0.60 |
| `NUKE_ULT` | 爆发大但非控（神灭斩 / 魂之挽歌 / 超声…） | 不进 `ccScore`，进 `dpsScore` 或施法评分 |
| `INIT` | 位移先手（闪烁 / 残影…） | 进可达性，弱进控制 |

**运行时修正（关键）**：

$$
\text{readyFactor}(a)=\begin{cases}
1.0 & remCd\le 0 \\
0.15 & remCd>0\text{ 且 }a\text{ 为 TEAM\_ULT/HARD\_CC}\\
0.40 & 0<remCd\le 5\text{s（即将好）}
\end{cases}
$$

$$\text{ccScore}(e)=\max_{a\in Control(e)}\big(w_{\text{tier}}(a)\cdot readyFactor(a)\cdot levelNorm(a)\big)$$

「大招未交 → 极高威胁；已交 → 骤降」由此直接实现。卡尔等动态技能：先验表列出祈唤 FourCC，**实战以 `CUnit+0x1DC` 链表是否挂载为准**（见既有施法逆向）。

团控先验 Top（摘录，完整表见产物 MD）：

| controlPrior | 英雄 | 代表技能 |
| ---: | :--- | :--- |
| 1.00 | 谜团 / 虚空 / 潮汐 / 猛犸 / 小牛 / 冰女 / 娜迦 | 黑洞 / 时间结界 / 毁灭 / RP / 回音击 / 极寒 / 海妖之歌 |
| 0.95 | 沉默 / 兽王 / 帕克 / 干扰者 / 末日 / 祸乱 / 军团 / 发条 / 凤凰 / 寒冬 | 全图沉默 / 咆哮 / 梦境 / 静风暴 / 末日 / 恶魔掌控 / 决斗 / 钩爪 / 超新星 / 寒冬诅咒 |
| 0.90 | 影萨 / 狮子 / 屠夫 / Mirana / 昆卡 / 海民 | 羊+枷锁 / 羊+穿刺 / 钩+肢解 / 月神箭 / 船 / 神拳 |

### 1.5 脆弱度与可秒杀性（Killability）

$$
hpFrac=\frac{life}{\max(maxLife,1)},\quad
armorMul=\begin{cases}1/(1+0.06A)&A\ge0\\ 2-(0.94)^{\min(20,-A)}&A<0\end{cases}
$$

- `bkbActive`（`+0x158>0` 或 BKB Buff）：魔法斩杀 ×0.15，物理 ×1；
- `invis` / `lotharReady`：若无真视，`killScore` ×0.3（打不到）；
- `blinkReady` / `forceReady`：逃生好 → `killScore` ×0.7（难锁死）；
- 残血加速：`lowHpBoost = 1 + 1.2*(1-hpFrac)^2`。

### 1.6 位置与可达性（Reachability）

$$
reach(e)=\mathrm{clip}_{0,1}\Big(1-\frac{dist(self,e)-gapcloseRange}{focusRange}\Big)
$$

- `gapcloseRange`：若我方 `AI_ITEM_BLINK`/`LOTHAR` 就绪 → 1200（跳刀）或贴身；
- 影魔贴身大：隐刀 / 跳刀就绪时把「贴脸」视为可达；
- 目标已 BKB：魔法贴身大招 `reach` 对魔伤通道降权（物理挽歌仍有效）。

---

## 二、关键目标权重公式 $w_{\text{key}}(e)$

### 2.1 归一化分量（均映射到约 $[0,1]$）

$$
\begin{aligned}
dpsScore(e) &= \mathrm{norm}\big(rawDps\cdot itemDpsMul\cdot levelFactor\big)\\
ccScore(e)  &= \max_a\big(w_{tier}(a)\cdot readyFactor(a)\cdot levelNorm(a)\big)\\
killScore(e)&= (1-hpFrac)^{1.4}\cdot armorMul^{-0.5}\cdot escapePenalty^{-1}\cdot lowHpBoost\\
reachScore(e)&= reach(e)
\end{aligned}
$$

`norm`：对本帧敌方 5 人做 min-max，避免绝对 DPS 跨期漂移；若仅 1 人可见则用绝对锚点 `rawDps/400`。

### 2.2 阶段混合

| 阶段 `phase` | 判定启发 | $(\alpha_{dps},\alpha_{cc},\alpha_{kill})$ |
| :--- | :--- | :--- |
| `INIT` 开团先手 | 双方平均 `hpFrac>0.55` 或团战时钟 <3s | (0.25, **0.55**, 0.20) |
| `MID` 混战 | 中间态 | (0.40, 0.35, 0.25) |
| `CLEANUP` 残局收割 | 敌方 ≥2 人 `hpFrac<0.35` 或我方人数优势 ≥2 | (**0.45**, 0.15, **0.40**) |

$$
w_{\text{key}}(e)=\big(\alpha_{dps}\,dps+\alpha_{cc}\,cc+\alpha_{kill}\,kill\big)\cdot (0.55+0.45\,reach)\cdot illusionMask
$$

可选：`focusLock` 已锁定目标时给 +0.15 粘性，避免每帧换人。

### 2.3 与技能施放评分的接口

任务 [`grok-hero-skill-damage-and-cast-scoring.md`](../tasks/grok-hero-skill-damage-and-cast-scoring.md) 定义：

$$\text{Score}_{\text{AOE}}(p)=\sum_{e\in Hit(p)} w_{\text{key}}(e)\cdot ExpectedDmg(e,p)$$

本文件只生产 $w_{\text{key}}$；`ExpectedDmg` 由技能几何 + 魔抗 / 护甲表提供。

### 2.4 影魔魂之挽歌（`A29J`）贴身选点示例

> 影魔仅为 **AOE 加权选点**样例；`w_key` 本身对全英雄通用。

6.83d 机制要点（地图文案 + 既有技能表）：

- 无目标 `0x10`，Order `0xD0131`（表内曾误标 PASSIVE，施法文档已证主动）；
- 灵魂线自身边向外；**距施法者越近，命中线数越多、伤害越高**；
- CD 约 120/110/100s，蓝 150/175/200。

设敌方站位（影魔为原点，单位码）：

| 角色 | 位置 | 状态 | $w_{\text{key}}$（INIT 阶段示意） |
| :--- | :--- | :--- | ---: |
| E1 潮汐（毁灭未交） | (180, 40) | 满血坦克，大招就绪 | **0.92** |
| E2 影萨（羊/枷锁未交） | (220, -80) | 脆皮辅助，双控就绪 | **0.88** |
| E3 敌法 | (650, 100) | 半血核心 | 0.55 |
| E4 矮人火枪 | (120, 200) | 酱油满血 | 0.28 |
| E5 树精 | (90, 160) | 酱油满血 | 0.22 |

候选点：

| 方案 | 站位点 | 覆盖 | 加权分（线数×伤害×$w$ 简化） | 结论 |
| :--- | :--- | :--- | ---: | :--- |
| A 人群中心炸酱油 | (100, 180) 盖 E4+E5+边缘 E1 | 3 人但两酱油 | ≈ $0.28+0.22+0.40=0.90$ | 差 |
| B 贴身潮汐（关键团控） | (160, 30) 满线打 E1，带一点 E2 | 核心控 | ≈ $0.92\times1.0+0.88\times0.6≈1.45$ | **优** |
| C 贴身影萨 | (200, -60) 满线 E2 | 先手辅助 | ≈ $0.88\times1.0+0.92\times0.5≈1.34$ | 优（控优时） |

**结论**：人数最多 ≠ 最优；INIT 阶段贴未交大的团控 / 先手辅助，分数显著高于「炸 3 个酱油」。CLEANUP 阶段若潮汐大招已交且敌法 15% 血，则 $w$ 翻转优先贴敌法。

---

## 三、C++ 纯逻辑草案（合入 `war3hook_ai_tactics.inl`）

### 3.1 数据结构与 API

```cpp
// ---- Teamfight key-target scoring (pure logic; no natives) ----
enum AiTfPhase : uint8_t { AI_TF_INIT = 0, AI_TF_MID = 1, AI_TF_CLEANUP = 2 };

struct AiTfAbilityThreat {
    uint32_t ability = 0;     // FourCC
    uint8_t  tier = 0;        // 0 none, 1 soft, 2 hard, 3 team_ult, 4 nuke_ult
    float    weight = 0.f;    // prior from table
    int      level = 0;       // 1-based; 0 = not learned
    float    remCd = 0.f;     // seconds; 0 = ready
};

struct AiTfHeroSnap {
    uint32_t handle = 0;
    uint32_t typeId = 0;
    float x = 0, y = 0;
    float life = 0, maxLife = 1;
    int   heroLevel = 1;
    float dmgAvg = 0;         // from aiReadAttackInfo mid
    float ias = 1.f;          // attack speed mult
    float bat = 1.7f;
    float armor = 0;
    bool  magicImmune = false;
    bool  invisible = true;
    bool  illusion = false;
    // inventory flags (from aiReadInventory tags)
    bool hasBkb = false, bkbReady = false;
    bool hasBlink = false, blinkReady = false;
    bool hasLothar = false, lotharReady = false;
    bool hasHex = false, hexReady = false;
    bool hasRefresh = false, refreshReady = false;
    bool hasButterfly = false, hasMkb = false, hasSatanic = false;
    AiTfAbilityThreat threats[8] = {};
    int threatCount = 0;
};

struct AiTfSelfSnap {
    float x = 0, y = 0;
    bool blinkReady = false;
    bool lotharReady = false;
    bool bkbReady = false;
    float gapcloseRange = 0.f;   // 0 or 1200
    float focusRange = 1400.f;
};

struct AiTfRanked {
    int   index = -1;           // into input array
    float wKey = 0;
    float dps = 0, cc = 0, kill = 0, reach = 0;
};

static float aiTfReadyFactor(float remCd, uint8_t tier)
{
    if (remCd <= 0.f) return 1.f;
    if (remCd <= 5.f) return 0.40f;
    return (tier >= 2) ? 0.15f : 0.25f; // hard/team ult drop hard when spent
}

static float aiTfDpsScore(const AiTfHeroSnap &e)
{
    const float period = (e.bat > 0.1f) ? (e.bat / (e.ias < 0.2f ? 0.2f : (e.ias > 5.f ? 5.f : e.ias))) : 1.f;
    float raw = (period > 0.05f) ? (e.dmgAvg / period) : 0.f;
    float mul = 1.f;
    if (e.hasButterfly) mul += 0.25f;
    if (e.hasMkb)       mul += 0.20f;
    if (e.hasSatanic)   mul += 0.15f;
    if (e.hasRefresh && e.refreshReady) mul += 0.15f;
    const float lf = 0.55f + 0.45f * ((e.heroLevel < 1 ? 1 : e.heroLevel) / 25.f);
    return raw * mul * lf; // caller min-max normalizes
}

static float aiTfCcScore(const AiTfHeroSnap &e)
{
    float best = 0.f;
    for (int i = 0; i < e.threatCount; ++i) {
        const AiTfAbilityThreat &a = e.threats[i];
        if (a.tier == 0 || a.tier == 4 || a.level <= 0) continue; // skip nuke_ult here
        const float ln = 0.6f + 0.4f * (a.level >= 3 ? 1.f : (a.level / 3.f));
        float s = a.weight * aiTfReadyFactor(a.remCd, a.tier) * ln;
        if (e.hasHex && e.hexReady) s = (std::max)(s, 0.85f); // item hex
        if (s > best) best = s;
    }
    if (e.hasHex && e.hexReady) best = (std::max)(best, 0.85f);
    return best;
}

static float aiTfKillScore(const AiTfHeroSnap &e)
{
    const float maxL = e.maxLife > 1.f ? e.maxLife : 1.f;
    const float frac = e.life / maxL;
    const float A = e.armor;
    const float armorMul = (A >= 0.f) ? (1.f / (1.f + 0.06f * A))
                                      : (2.f - std::pow(0.94f, (std::min)(20.f, -A)));
    float esc = 1.f;
    if (e.blinkReady || e.lotharReady) esc *= 0.7f;
    if (!e.visible) esc *= 0.3f;
    if (e.magicImmune) { /* physical focus still ok; magic consumers see flag */ }
    const float low = 1.f + 1.2f * (1.f - frac) * (1.f - frac);
    return std::pow(1.f - frac, 1.4f) * std::sqrt(1.f / (armorMul > 0.05f ? armorMul : 0.05f)) * (1.f / esc) * low * 0.15f;
}

static float aiTfReachScore(const AiTfSelfSnap &self, const AiTfHeroSnap &e)
{
    const float dx = e.x - self.x, dy = e.y - self.y;
    const float dist = std::sqrt(dx * dx + dy * dy);
    const float effective = dist - self.gapcloseRange;
    if (effective <= 0.f) return 1.f;
    if (effective >= self.focusRange) return 0.f;
    return 1.f - effective / self.focusRange;
}

static AiTfPhase aiTfDetectPhase(const AiTfHeroSnap *enemies, int n, int allyAlive, int enemyAlive)
{
    int low = 0; float sumFrac = 0.f; int m = 0;
    for (int i = 0; i < n; ++i) {
        if (enemies[i].illusion || enemies[i].life <= 0.405f) continue;
        const float f = enemies[i].life / (enemies[i].maxLife > 1.f ? enemies[i].maxLife : 1.f);
        sumFrac += f; ++m;
        if (f < 0.35f) ++low;
    }
    const float avg = m ? sumFrac / m : 1.f;
    if (low >= 2 || (allyAlive - enemyAlive) >= 2) return AI_TF_CLEANUP;
    if (avg > 0.55f) return AI_TF_INIT;
    return AI_TF_MID;
}

// Rank up to n enemies into out[0..n-1] by descending wKey. Returns count written.
static int aiRankTeamfightTargets(const AiTfSelfSnap &self,
                                  const AiTfHeroSnap *enemies, int n,
                                  AiTfPhase phase,
                                  AiTfRanked *out, int outCap)
{
    if (!enemies || !out || n <= 0 || outCap <= 0) return 0;
    float alphaD = 0.40f, alphaC = 0.35f, alphaK = 0.25f;
    if (phase == AI_TF_INIT)     { alphaD = 0.25f; alphaC = 0.55f; alphaK = 0.20f; }
    if (phase == AI_TF_CLEANUP)  { alphaD = 0.45f; alphaC = 0.15f; alphaK = 0.40f; }

    float dpsRaw[16]; int m = (std::min)(n, 16);
    float dMin = 1e9f, dMax = 0.f;
    for (int i = 0; i < m; ++i) {
        dpsRaw[i] = enemies[i].illusion ? 0.f : aiTfDpsScore(enemies[i]);
        if (!enemies[i].illusion) { dMin = (std::min)(dMin, dpsRaw[i]); dMax = (std::max)(dMax, dpsRaw[i]); }
    }
    const float dSpan = (dMax > dMin + 1.f) ? (dMax - dMin) : 1.f;

    int written = 0;
    for (int i = 0; i < m && written < outCap; ++i) {
        const AiTfHeroSnap &e = enemies[i];
        if (e.illusion || e.life <= 0.405f) continue;
        AiTfRanked r;
        r.index = i;
        r.dps = (dpsRaw[i] - dMin) / dSpan;
        r.cc = aiTfCcScore(e);
        r.kill = aiTfKillScore(e);
        if (r.kill > 1.f) r.kill = 1.f;
        r.reach = aiTfReachScore(self, e);
        const float mix = alphaD * r.dps + alphaC * r.cc + alphaK * r.kill;
        r.wKey = mix * (0.55f + 0.45f * r.reach);
        out[written++] = r;
    }
    // insertion sort by wKey desc (n<=5)
    for (int i = 1; i < written; ++i) {
        AiTfRanked key = out[i]; int j = i;
        while (j > 0 && out[j - 1].wKey < key.wKey) { out[j] = out[j - 1]; --j; }
        out[j] = key;
    }
    return written;
}
```

快照填充（游戏线程，有原生 / 内存处）：遍历 `enemyHeroes` → `aiReadAttackInfo` + `aiReadInventory` + 按先验表 FourCC 在技能链上 `readAgentTimer` → 填 `AiTfHeroSnap`。

### 3.2 离线 5v5 测试用例

| ID | 阶段 | 场景 | 期望 Top-1 |
| :--- | :--- | :--- | :--- |
| T1 | INIT | 潮汐毁灭就绪满血 + 3 酱油近身 + 半血敌法远离 | **潮汐**（cc 主导） |
| T2 | INIT | 潮汐毁灭刚交（remCd=120）+ 影萨羊刀就绪 | **影萨** |
| T3 | CLEANUP | 敌法 12% 血有蝴蝶；谜团黑洞已交；两人酱油 80% | **敌法** |
| T4 | MID | 虚空时间结界就绪但距离 2000 无跳刀；近处半血火枪 | 火枪或虚空视 `gapclose`；无跳刀 → **火枪** |
| T5 | INIT | 5 人重叠；影魔选点：中心 3 酱油 vs 贴身未交控猛犸 | AOE 分：**贴身猛犸**更高 |
| T6 | any | 目标为幻象位 | `wKey=0` 不入榜 |
| T7 | INIT | 卡尔已祈唤龙卷风（链表可见）+ remCd=0；对比仅球未祈唤 | 有龙卷风者 `ccScore` 更高 |
| T8 | CLEANUP | 两人残血：BKB 开着的主C vs 无BKB 的法核 | 物理集火可打主C；魔法技能消费者应降权主C |

伪测试（可放 `War3Analysis/artifacts/teamfight-key-target/offline_cases.json` 后续）：

```cpp
// T1 sketch
AiTfHeroSnap e[5] = {};
// e[0] Tide: type Ofar, life=full, threat Ravage tier=3 weight=1 remCd=0
// e[1..3] supports low weight
// e[4] AM half hp far
AiTfSelfSnap self{0,0,false,false,false,0,1400};
AiTfRanked out[5];
int n = aiRankTeamfightTargets(self, e, 5, AI_TF_INIT, out, 5);
assert(n >= 1 && out[0].index == 0);
```

### 3.3 合入步骤（实现阶段，本文不改源码）

1. 将先验 JSON 压成 `kAiHeroControlThreats[]`（或运行时读表）；
2. 在团战 / AOE ult 技巧前调用 `aiRankTeamfightTargets`；
3. 集火：`attack` / 指向性技能目标 = `out[0]`；
4. AOE：枚举候选点，用 $w_{\text{key}}$ 加权（接技能伤害评分任务）；
5. 实机：`tactic` 日志打印 `wKey/dps/cc/kill/reach` 与阶段。

---

## 四、风险与后续

| 项 | 说明 |
| :--- | :--- |
| 控制表假阳性 | 已用 OVERRIDES 修巫医/赏金/痛苦女王等；新英雄名需回归 `build_control_threat_table.py` |
| 拉比克偷大 | 先验按英雄类型不够 → **必须以链表 FourCC 匹配全局威胁字典** |
| 魔抗精确值 | 6.83d 基础 25% + 斗篷等；完整公式归技能伤害评分任务 |
| 早期 `game.dll` | `1.0.17`~`1.21` 部分 `CUnit` 槽未确认；DotA 联调主力 1.24+ |
| 实机标定 | 需用 RemoteControl 录 5v5，对照人类集火目标校准 $\alpha$ |

---

## 五、交付清单

| 文件 | 内容 |
| :--- | :--- |
| 本文 | 公式、只读字段、全版本偏移汇总、C++ 草案、测试用例、影魔选点对比 |
| `artifacts/teamfight-key-target/hero_control_threat_683d.json` | 112 英雄控制 / 大招先验 |
| `artifacts/teamfight-key-target/hero_control_threat_683d.md` | 可读排序表 |
| `artifacts/teamfight-key-target/build_control_threat_table.py` | 可再生成脚本 |
