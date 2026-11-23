# 任务：敌方施法前摇、持续施法 / TP 读条与危险技能弹道 / 特效的只读感知（AI 托管躲技能与打断）

**给**：Cursor Grok　**布置时间**：2026-11-23　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 为什么做（托管游戏的核心盲区）

截至 2026-11-23，`War3Analysis` 已基本补齐 AI 托管所需的「自身状态 + 合法发包」链路：
- 移动与碰撞绕行：`war3-unit-movement-fields.md`、`war3-unit-collision-and-repath.md`
- 普攻补刀、护甲、攻速、普攻弹道（`CMissile`）与高低地丢失：`war3-lasthit-combat-data.md`、`war3-lasthit-miss-vision.md`
- 自身技能/物品发包（`0x10/0x11/0x12`、`flags`）、冷却与蓝耗：`dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md`、`war3-order-packet-flags-and-ability-item-cooldown.md`
- 视野/迷雾、塔与小兵仇恨、死亡/复活/买活：`war3-threat-map-pathing-vision.md`、`war3-tower-creep-aggro.md`、`dota-hero-death-respawn-buyback.md`

但 AI 要真正替玩家打完一局（尤其是面对真人对手），还缺一块**致命的实战感知能力——看不懂敌方正在放什么技能**：
1. **无法打断敌方 TP / 持续施法大招**：看到敌人原地不动，不知道是在站桩补刀、在读 TP，还是在摇黑洞 / 极寒领域 / 地震，也不知道还剩多少秒读条结束；
2. **无法在敌方抬手瞬间交保命（BKB / 吹风 / 跳刀 / 推推 / 切臂章）**：`war3-unit-movement-fields.md` 已读出 `COrder+0x24`（`orderId`）与 `+0x48/+0x50`（目标点），但 **`COrder` 目标单位字段仍标记为「未确认」**，且未逆向 `CAbilitySpell` 正在施法/前摇/引导中的状态与计时器，导致不知道敌人指向技是不是冲着自己放的；
3. **无法躲避非指向性技能（`dota-ai-tactics-library.md` §6 `dodge` 阻塞项）**：如白虎月神之箭、屠夫肉钩、火女光击阵、船长洪流、影魔影压、卡尔天火等，在 DotA 6.83d 里分别通过引擎技能弹道、隐藏马甲单位（dummy unit）或地面特效实现，目前 AI 对这类威胁完全失明。

本任务目标：在不触碰迷雾作弊红线的前提下，为「离线 10ms 微操（躲技能 / 打断 / 交 BKB）」和「在线大模型（MCP 事件流）」提供**纯只读、零调用风险**的敌方施法与危险威胁感知规格。

---

## A. `COrder` 目标单位与 `CAbilitySpell` 施法阶段（`game.dll`）

补完你在 `war3-unit-movement-fields.md` 留下的「指令目标单位未确认」，并打通 `CAbilitySpell` 的实时施法状态机：

1. **`COrder` / `COrderTarget` / `COrderPoint` 完整布局**：
   - 从 `CUnit + 0x19C / +0x1A0` → `ResolveAgent` → `COrder*` 出发，区分 `COrder`（无目标）、`COrderPoint`（点目标）、`COrderTarget`（单位/物体目标）的虚表与字段偏移；
   - 钉死 **`COrderTarget` 目标单位代理句柄对（`CAgentPtr<CWidget>`）偏移**（说明为何上次 4 条 `attack` 样本里 `+0x2C/+0x38/+0x58` 全为 `0xFFFFFFFF`：那些是 `COrderPoint` 攻击地面路点，还是目标在另一偏移？）；
   - 确认能否从 `COrder` 直接读出「是否正在执行（已进射程开始抬手）vs 仍在跑向射程途中」。
2. **`CAbilitySpell` 施法前摇 / 持续施法 / 后摇实时状态与计时器**：
   - 类似 `CAbilityAttack` 的三个内嵌 `CAgentTimer`（`+0x1D8/+0x1EC/+0x200`），逆向 `CAbilitySpell`（及其子类 `CAbilityChannel` / `CAbilityItemTownPortal`）在**施法前摇（cast point）**、**持续施法（channeling，含 TP / 黑洞 / 冰女大 / 沙王摇大）**、**施法后摇（cast backswing）**期间：
     - 标志位（`+0x20` 的 `0x1000` / `0x4000` 或其他位）具体哪一位代表「前摇中 / 引导中 / 后摇中」；
     - 对应内嵌 `CAgentTimer` 的精确偏移，能否复用 `node = *(u32*)(timer + 0x0C); rem = *(f32*)(node + 4) - *(f32*)(*(u32*)(node + 0x0C) + 0x40)` 纯只读算出剩余前摇 / 剩余引导秒数；
     - 施法目标点 `(tx, ty)` 或目标单位是否也缓存在 `CAbilitySpell` 对象上（如果是，给出偏移）。
3. **给出纯只读判定函数设计**：
   - `inspectUnitCasting(CUnit* u)` → `{orderId, abilityFourCC, phase: IDLE|APPROACHING|CAST_POINT|CHANNELING|BACKSWING, remainSec, targetX, targetY, targetUnit}`。

---

## B. 敌方技能弹道、马甲直线技能与地面预警特效（`game.dll` + DotA 6.83d `war3map.j`）

对比 `war3-lasthit-combat-data.md` 已逆向的普攻 `CMissile`，查清 DotA 6.83d 四类高危敌方威胁在运行时的真实载体：

1. **引擎级指向性技能弹道（如流浪风暴之锤、复仇之魂魔法箭、骷髅王冥火爆击、火枪暗杀）**：
   - 在全局 `g_AgentManager`（1.27 `0xBE40A8` / 1.26 `0xAB7788`）的 `CMissile`（及子类）中，**如何区分普攻弹道与技能弹道**？
   - 能否从 `CMissile` 直接读出关联的技能 `FourCC` / `CAbility*`、施法者、目标单位、当前实时坐标（`CBhPoProjectile`）与弹速（`+0x54`）？给出可只读算出**预计命中剩余时间 `etaSec`** 的结构链。
2. **DotA 脚本马甲直线弹道（典型样本：白虎箭 `Mirana Arrow`、屠夫钩 `Pudge Meat Hook`、船长水/船、蓝猫/发条/火女龙破斩）**：
   - 检索 `War3Script/war3map*.j`，列出上述高频致命技能的底层实现方式：是 `CreateUnit` 马甲（给出马甲单位 FourCC、是否带碰撞/朝向/移速、周期位移计时器），还是 `AddSpecialEffect`？
   - 确认这些马甲单位对敌方客户端是否可见（`IsUnitVisible` 返回值），以及 AI 能否在不看迷雾的前提下，通过单位实时位置 + 朝向（`+0x90`）推算出弹道射线与自身垂直距离。
3. **地面延迟预警与 TP 特效（典型样本：回城卷轴 `AItp` / 飞鞋、火女光击阵、船长洪流、卡尔天火、拉席克撕裂大地）**：
   - `game.dll` 中 `AddSpecialEffect` / `AddSpecialEffectTarget` 创建的 `CEffectImage`（或同类特效对象）是否注册在 `g_AgentManager` 或全局特效链表中？若可枚举，给出模型路径/偏移、世界坐标、创建/绑定单位及可见性判断依据；
   - 若直接扫特效链表跨版本不稳定，请明确说明原因并给出替代方案（例如：TP 靠 `CAbilityItemTownPortal` + 目标建筑/落点马甲检测，火女光击阵靠 `COrderPoint` 落点 + `castPoint` 预判）。

---

## C. 合法视野边界（反作弊红线）

每一类新增读取源（`CUnit` 施法态、`COrderTarget`、`CMissile`、马甲单位、`CEffect`）必须逐项写明：
1. **何时合法可读**：必须以 `IsUnitVisible(caster, localPlayer)`（或目标/弹道/落点所在格 `IsLocationVisibleToPlayer` 为真）为前置闸门；
2. **明确禁止项**：严禁读取迷雾中敌方英雄的读条/TP/落点、严禁读取对敌方隐藏的马甲（如卡尔天火前摇期间敌方不可见的特效/马甲）、严禁借 `CMissile` 或 `COrder` 反推迷雾中施法者坐标；
3. 给出写入 `SharedMemory` / MCP 事件流前的统一过滤规则。

---

## 版本要求

所有用到的 `game.dll` 函数、全局地址、虚表与结构体偏移，按 `.agents/rules/war3-gamedll-all-versions.md` 覆盖 `D:\Qt\workspace\War3Launcher\versions\` 下**全部 11 个版本**并逐版列 RVA：
`1.0.17.5988`、`1.0.20.6048`、`1.20.4.6074`、`1.21.0.6263`、`1.22.0.6328`、`1.23.0.6352`、`1.24.1.6374`、`1.24.4.6387`、`1.25.1.6397`、`1.26.0.6401`、`1.27.0.52240`。
早期版本（`1.0.17` ~ `1.21`）若确实结构不同或内联，逐版核验后标注 `—` 或「未确认」并写明原因，不得未经反汇编直接推算填充。

---

## 先读

- `analyses/war3-unit-movement-fields.md`（你之前的 `CUnit` / `COrder` / `ResolveAgent` 基线）
- `analyses/war3-lasthit-combat-data.md`（`CAbilityAttack` 三计时器 + `CMissile` 在 `g_AgentManager` 的枚举方式）
- `analyses/war3-order-packet-flags-and-ability-item-cooldown.md`（`CAbilitySpell`、`CAgentTimer` 纯只读公式、`CAbilityItemTownPortal`）
- `analyses/dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md`（`CAbilitySpell` 虚表与 `+0x20` 标志位）
- `analyses/war3-threat-map-pathing-vision.md`（视野红线）
- 工具和路径：`.agents/rules/war3-reverse-toolkit.md`

---

## 限制

- **严格只读**：不注入、不写内存、不发游戏指令或网络包、不在游戏线程外调 JASS 原生。
- 不修改 `War3Launcher` / `hooker` / `Scripts`，不编译、不安装、不提交。C++ 接入方案只写进文档，由主会话实现。
- 不自动开局、不关闭用户的 `war3` / `War3Launcher`、不动鼠标键盘。需要实机验证的部分，写成 1 分钟内可执行的只读验证步骤与 Python 采样脚本（放入 `artifacts/`）。
- 不访问远程服务器。

---

## 输出

- 主报告：`analyses/war3-enemy-cast-channel-and-skillshot-detect.md`
- 配套导图：`analyses/war3-enemy-cast-channel-and-skillshot-detect-mindmap.md`
- 扫描脚本、全 11 版 RVA 表、DotA 6.83d 技能载体对照 JSON 与只读实机验证脚本：`artifacts/enemy-cast-skillshot/`
- 开头按 `.agents/rules/war3-analysis-save.md` 写明分析模型、分析目的、命名方式、分析时间、验证状态与证据。
- **第一段先给结论**：AI 怎么零风险只读判断「敌方在放什么技能 / 打谁 / 剩几秒」「敌方是不是在 TP 或摇大」「飞来的弹道/马甲技能能不能躲、怎么躲」，以及哪些项还待实机验证。
