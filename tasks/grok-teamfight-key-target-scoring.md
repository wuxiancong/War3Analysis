# 任务：团战「关键英雄（Key Target）」动态评估与集火/贴身大招选人逻辑

**给**：Cursor Grok（或独立深度逆向会话）　**布置时间**：2026-11-22　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 背景

在 DotA 团战中，AOE 爆发（如影魔贴身大招 `A29J`）或先手控制/集火不能只看「离我最近」或「覆盖人数最多」，必须精准锁定**本次团战的关键人物**——通常是敌方**输出最高的核心**，或**拥有团控/关键先手技能且尚未交大**的英雄。

## 目标与交付物

分析结果请保存到：
- `D:\Qt\workspace\War3Analysis\analyses\dota-teamfight-key-target-scoring.md`

## 具体任务

### 1. 基于 `Game.dll`（全 11 版本核验）与现有只读内存字段，确定团战评估输入源
梳理每个敌方英雄当前可零风险只读获取的实时特征：
- **输出威胁（DPS Threat）**：实时攻击力（`base + bonus`）、攻速（`ias`）、英雄等级、关键输出装备（BKB / 蝴蝶 / 黯灭 / 暴击 / 羊刀 / 刷新等，经 `aiReadInventory` 读取）；
- **控制威胁（Control Threat）**：英雄硬控/团控技能槽位等级与当前冷却状态（参考 `war3-order-packet-flags-and-ability-item-cooldown.md` 的 `CAbilitySpell` 冷却读取），区分「大招未交（极高威胁）」与「大招已交（威胁骤降）」；
- **脆弱度与可秒杀性（Killability）**：当前血量、最大血量、护甲/魔抗、是否有逃生/魔免状态（BKB Buff / 隐身 / 跳刀冷却）；
- **位置与可达性（Reachability）**：与我方英雄的距离、是否有 BKB/隐刀/跳刀可瞬间贴身（如影魔隐刀/跳刀贴身大招）。

### 2. 建立可量化的关键目标权重公式 $w_{\text{key}}(e)$
- 输出分 `dpsScore(e)`、控制分 `ccScore(e)`、斩杀收益分 `killScore(e)` 的归一化权重设计；
- 区分不同团战阶段：开团先手期（优先秒关键团控/未交大核心）vs 残局收割期（优先高 DPS 残血目标）；
- 结合 `grok-hero-skill-damage-and-cast-scoring.md` 给出影魔大招贴身选点示例（对比「站人群中间炸 3 个酱油」vs「贴身满线炸敌方关键核心/控制」的评分差异）。

### 3. 给出纯逻辑 C++ 实现草案与离线测试案例
- 设计不依赖原生的 `aiRankTeamfightTargets(...)` 函数签名与 5v5 典型团战测试用例，方便直接合入 `war3hook_ai_tactics.inl`。
