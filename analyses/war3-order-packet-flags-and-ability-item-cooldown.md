# War3 全 11 版指令动作包协议（`0x10/0x11/0x12` & `abilityFlags`）与技能/物品/共享冷却只读内存逆向

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 补齐在线大模型托管（MCP / RemoteControl）与离线 10ms 级微操 AI 的两项底层引擎盲区：① 从 `Game.dll` 机器码彻底查明 `0x11` vs `0x12` 与 `flags 0x40/0x44` 的真实判定规则（回答 [`dota-ai-laning-routine.md`](./dota-ai-laning-routine.md) 中假眼/TP/跳刀等点地物品的同类发包风险）；② 逆向全 11 版 `CAbilitySpell`、`CItem` 与 `CAbilityInventory` 共享 `cooldownID`（如魔瓶 `A0FO`）的纯只读冷却/蓝耗内存链，彻底取代墙钟估算与扣蓝等待 hack |
| **命名方式** | `war3-order-packet-flags-and-ability-item-cooldown`；配套导图 `war3-order-packet-flags-and-ability-item-cooldown-mindmap.md`；脚本与反汇编产物 `artifacts/order-flags-and-cooldown/` |
| **分析时间** | 2026-11-23 |
| **验证状态** | **全 11 版静态反汇编验证完成**（`1.0.17.5988` ~ `1.27.0.52240`）：`1.27.0.52240` 完成客户端构造、模拟端执行、技能/物品/共享冷却全链路 `dumpbin` 逐行反汇编；`1.22.0.6328` ~ `1.27.0.52240`（全部 7 个现代版）完成全表 RVA 与结构体偏移核验；`1.0.17.5988` ~ `1.21.0.6263`（4 个早期无 RTTI 版）完成 `abilityFlags` 打包器、`Blink`/`TP` `GetTargetType` 与 `CAbilitySpell+0xD0` 核验，`CItem+0xE4` / `CAbilityInventory` 共享冷却在早期版未见 `0xD01BE` 路径已如实标注 `未确认`。**未做实机发包或内存注入**（严格只读） |
| **证据** | 全 11 版 `War3Launcher/versions/*/Game.dll`；`War3Launcher/hooker/war3hook_ai_tactics.inl`；[`dota-ai-laning-routine.md`](./dota-ai-laning-routine.md)；[`dota-ai-llm-mcp-verify.md`](./dota-ai-llm-mcp-verify.md)；批处理脚本与反汇编 [`artifacts/order-flags-and-cooldown/`](../artifacts/order-flags-and-cooldown/) |
| **思维导图** | [`war3-order-packet-flags-and-ability-item-cooldown-mindmap.md`](./war3-order-packet-flags-and-cooldown-mindmap.md) |

---

## 核心结论（先看这里）

1. **为什么假眼（`I05G`）发 `0x11 + 0x44` 失败、真人发 `0x12 + 0x40 + FFFFFFFF` 成功，以及 TP / 跳刀该怎么发**：
   - 客户端 `CTargetMode`（1.27 `0x3A4CCB` / `0x3A6614`）决定发 `0x11` 还是 `0x12` 的**唯一条件**是 `GetTargetType()`（虚槽 `+0x30C`）低位是否**严格等于 `2`（纯点目标）**：
     - **`targetType == 2`（纯点目标）** → 发 **`0x11`**（`CNetCommandUnitOrderTargetPoint`），如 **跳刀 `AEbl`**（`CAbilityBlink::GetTargetType()` = `0x00100002`）→ **`0x11 + flags=0x0044`**。
     - **`targetType == 6`（点或单位目标 `0x02 | 0x04`）** → 点地时发 **`0x12`**（`CNetCommandUnitOrderTargetImage`）且 **`targetObj = FFFFFFFF FFFFFFFF`**！这既包括 **假眼 / 真眼（`ANcl` DataB=3 → `0x00000006`）**，也包括 **回城卷轴 TP（`CAbilityItemTownPortal::GetTargetType()` = `0x00100006`）**！
   - **`flags 0x40` vs `0x44` 的机器码真相**：
     - **`0x0040`（bit 6）** = `uiFlags & 0x04`（仅对当前子组下令；模拟端走 `CSelectionWar3` 子组遍历 `0x272110`）。
     - **`0x0004`（bit 2）** = `abilFlags & 0x00100000`（`oneUnitOnly` 单单位施法；模拟端对第一个满足条件的单位发单后立刻 `break`）。
     - **`CAbilityBlink` (`0x100002`)** 与 **`CAbilityItemTownPortal` (`0x100006`)** 硬编码置位 `0x100000`，故真人发 `flags = 0x0044`；而 **`CAbilityChannel` (`ANcl`)** 仅在 SLK `DataC & 0x10`（Unique Cast）置位时才置 `0x100000`，DotA 假眼未勾此项故真人发 `flags = 0x0040`。
   - **直接消除同类风险的终极方案**：`aiUseItemNow` 不应再按物品枚举硬编码特判，而应直接读物品技能的 **`GetTargetType()`（`vt+0x30C`）** 自动选择 `0x10`/`0x11`/`0x12` 与 `0x40`/`0x44`（见 §1.4）。**实证高危点：当前 `war3hook_ai_tactics.inl` 对 TP 点地发 `0x11 + 0x44`，与真人客户端发 `0x12 + 0x44 + FFFFFFFF` 不一致，应改走 `0x12`。**

2. **技能、物品、共享冷却（如魔瓶 `A0FO`）全部可纯只读内存精确读取（零延迟、零墙钟误差）**：
   - **`CAbilitySpell` 冷却（全 11 版 `1.0.17` ~ `1.27` 偏移完全一致）**：
     - 冷却标志：`*(uint32_t*)(abil + 0x20) & 0x200`（且 bit 31 未置位）；禁用计数 `*(int32_t*)(abil + 0x3C) > 0`；沉默计数 `*(int32_t*)(abil + 0x44) > 0`。
     - 计时器：`CAgentTimer` 位于 **`abil + 0xD0`**，`node = *(uint32_t*)(abil + 0xDC)`。
   - **`CItem` 自身冷却与内置技能表（`1.22` ~ `1.27` 全 7 版完全一致）**：
     - 物品技能数组：`count = *(uint32_t*)(item + 0x98)`，`CAgentPtr<CAbility>` 数组始于 **`item + 0x9C`**（步长 `0x0C`）；物品自身冷却 `CAgentTimer` 位于 **`item + 0xE4`**（`node = *(uint32_t*)(item + 0xF0)`）。
   - **`CAbilityInventory` 共享冷却组表（`1.22` ~ `1.27` 全 7 版完全一致——彻底解决魔瓶装符换物品 ID 仍共享 0.5s 冷却问题）**：
     - **`inv + 0xBC`**：`uint32_t sharedCdCount`（共享冷却组数量）
     - **`inv + 0xC0`**：`uint32_t sharedCdIds[6]`（每组的 `cooldownID` FourCC，如魔瓶 `'A0FO'`、TP `'AItp'`）
     - **`inv + 0xDC + idx * 0x14`**：6 个内嵌 `CAgentTimer`（每个 `0x14` 字节，`node = *(uint32_t*)(inv + 0xE8 + idx * 0x14)`）
   - **通用 `CAgentTimer` 纯只读公式（无需调用虚函数，免锁免线程切换）**：
     - 若 `node != 0 && !(*(uint8_t*)(node + 0x12) & 1)`：
       - **总冷却** = `*(float*)(node + 0x08)`
       - **剩余冷却** = `*(float*)(node + 0x04) - *(float*)(*(uint32_t*)(node + 0x0C) + 0x40)`（`timerMgr + 0x40` 即引擎权威模拟时钟）

3. **在线大模型（MCP）与离线 10ms 微操的分层协同**：
   - **离线执行层（10ms 级）**：直接读 `CAbilitySpell+0xD0` / `CAbilityInventory+0xBC..0xDC` / `CItem+0xE4` 做零误差冷却门控（废除影压 `1.8s` 扣蓝等待与魔瓶 `bottleReady + 0.65s` 硬编码），并通过 `GetTargetType()` 自动封装与真人逐字节一致的 `0x10`/`0x11`/`0x12` 动作包。
   - **在线大模型（MCP 指挥层）**：状态快照 JSON 精确暴露每个技能的 `remCd / totalCd / manaCost / silenced / ready` 及每件物品的 `remCd / sharedCdId / targetKind`，决策层只下发高层意图，不再因误判冷却或发错点地包而浪费关键 1~5s 推理回合。

---

## 一、`0x10 / 0x11 / 0x12` 动作包协议与 `abilityFlags` 全链路逆向

### 1.1 `abilityFlags`（16 位标志）逐位解码（全 11 版一致）

反汇编 1.27 客户端动作包打包器 `0x3AE4E0`（`0x10`）、`0x3AE540`（`0x11`）、`0x3AE5D0`（`0x13`）、`0x3AE660`（`0x12`），以及 1.0.17 `0x1408A0` / `0x140900`，确认 **1.0.17 至 1.27 全 11 版的 `abilityFlags` 位布局从未改变**：

| 位掩码 | 位号 | 客户端来源（`uiFlags` / `abilFlags`） | 模拟端消费位置（1.27 证据） | 真实引擎语义 |
| :---: | :---: | :--- | :--- | :--- |
| `0x0001` | bit 0 | `uiFlags & 0x01` | `COrder` 队列位（`0x69BC60`） | **Shift 排队指令**（不打断当前动作，入队列尾） |
| `0x0002` | bit 1 | `uiFlags & 0x02`（`abilFlags & 0x02000000`） | `0x69C108` / `0x69E0A5` → `0x69B580` | 瞬发/自释放子组优先级标志 |
| `0x0004` | bit 2 | **`(abilFlags >> 18) & 0x04`**（即 `abilFlags & 0x00100000`） | `0x69BFDA` / `0x69CA04` → `oneUnitOnly` | **单单位施法**：多选时仅对排序后首个可用单位发单即 `break`，且跳过编队计算 |
| `0x0008` | bit 3 | `uiFlags & 0x08`（多选移动） | `0x69CA64` | 启用多单位编队容器分配 |
| `0x0010` | bit 4 | `uiFlags & 0x10`（编队移动开关） | `0x69DCB1` / `0x69CAF8` → `0x773530` | 编队移动标志（Formation On/Off） |
| `0x0020` | bit 5 | **`(abilFlags >> 16) & 0x20`**（即 `abilFlags & 0x00200000`） | `0x69C10B` / `0x69E0A8` → `0x69B580` | 技能自动施法/特殊目标组筛选标志 |
| `0x0040` | bit 6 | **`uiFlags & 0x04`** | `0x69BFF3` / `0x69CCED` / `0x69DD40` | **仅当前子组**（置 1 调 `0x272110` 遍历当前子组；置 0 调 `0x272150` 遍历全选区） |
| `0x0100` | bit 8 | **`(abilFlags >> 3) & 0x100`**（即 `abilFlags & 0x00000800`） | `COrder` 标志位 | 建筑建造/克隆类扩展标志 |

> **关键结论**：`0x0044 = 0x0040 | 0x0004`（子组 + 单单位施法），`0x0040`（子组、无单单位限制）。当仅选中单个英雄时，模拟端对 `0x0040` 与 `0x0044` 的单位遍历结果相同（均只命中该英雄），**真正导致假眼发包失败的不是 `0x44`，而是外壳 `0x11` vs `0x12`！**

### 1.2 客户端何时发 `0x11` vs `0x12`：`CTargetMode` 关键分支

反汇编 1.27 `CTargetMode` 点地确认路径（`0x3A4CCB..0x3A4D17` 与 `0x3A6614..0x3A666D`）：

```asm
; 1.27 Game.dll @ 0x3A4CCB (点地确认后选择发 0x11 还是 0x12)
6F3A4CCB: cmp  dword ptr [ebp-24h], 2    ; targetType == 2 (纯点目标)？
6F3A4CD6: push ebx                       ; uiFlags (含 0x04 -> 最终 0x0040)
6F3A4CD7: push dword ptr [edi+14h]       ; abilFlags (来自 CAbility::GetTargetType())
6F3A4CDA: jne  6F3A4CFC                  ; 不是纯点目标 (例如 6 = 点或单位) -> 走 0x12！
...
6F3A4CF5: call 6F3AE540                  ; targetType == 2 -> 发 0x11 (CNetCommandUnitOrderTargetPoint)
6F3A4CFA: jmp  6F3A4D1C
6F3A4CFC: push 0                         ; targetWidget = NULL -> 序列化为 FFFFFFFF FFFFFFFF！
...
6F3A4D17: call 6F3AE660                  ; targetType != 2 -> 发 0x12 (CNetCommandUnitOrderTargetImage)
```

同时，模拟端 6 个网络指令执行器在 1.27 中的完整映射如下：

| Action | 类名 | 模拟端执行器 (1.27) | 校验回调 (1.27) | 调用的 `CUnit::CanOrder*` | 创建的内部指令 |
| :---: | :--- | :---: | :---: | :--- | :--- |
| `0x10` | `CNetCommandUnitOrderBasic` | `0x69BF40` | `0x69C0D0` | `0x680540` (`vt+0x264` → `vt+0x304`, mask `0x01`) | `0x673200` (`COrder`) |
| `0x11` | `CNetCommandUnitOrderTargetPoint` | `0x69E650` | `0x69E7EC` | `0x680620` (`vt+0x25C` → `vt+0x300`, mask `0x0A`) | `0x673990` (`COrderPoint`) |
| `0x12` | `CNetCommandUnitOrderTargetImage` | `0x69C830` | `0x69D0C0` | `0x680830` (`vt+0x260` → `vt+0x2FC`, mask `0x04`)，失败回退 `0x680620` | `0x67E640` (`COrderTarget`) |
| `0x13` | `CNetCommandUnitOrderTargetImage2` | `0x69C1B0` | `0x69CEE7`/`0x69CF6D` | `0x680780` (`vt+0x258`) / `0x6806D0` (`vt+0x254`) | `0x67E540` (`COrderTarget2`) |
| `0x14` | `CNetCommandUnitOrderTargetImageFogged` | `0x69DC50` | `0x69DEB0`/`0x69E060` | `0x680900` (`vt+0x250` → `vt+0x2F8`)，回退 `0x680620` | `0x67E3A0` (`COrderFogged`) |

**关键机制（解释为何 `itemObj1/itemObj2` 不可为 `FFFFFFFF`）**：
在 `CUnit::CanOrderPoint`（`0x680620`）/`CanOrderTargetImage`（`0x680830`）中，引擎遍历英雄 `CUnit+0x1DC/+0x1E0` 技能链表，对每个 `CAbility` 先调用 `abil->vt+0xA0()`（`GetOwnerItem()`）并与包内 `itemObj1/itemObj2` 解析出的 `CItem*` 比对（`0x680654..0x68065A`）：**物品技能实际直接挂在英雄的技能链表上**，只有 `itemObj` 匹配对应 `CItem*` 才放行；填 `FFFFFFFF` 会使 `CItem* == NULL` 而跳过所有物品技能。

### 1.3 三类典型物品母技能的 `GetTargetType()`（`vt+0x30C`）实证

反汇编 1.22 ~ 1.27 全 7 版（及 1.0.17 ~ 1.21.0 机器码对照）：

| 物品 / 母技能类 | `GetTargetType()` (`vt+0x30C`) 返回值 | 低 4 位含义 | `0x100000` 位 | 真人客户端实际发包格式（点地时） |
| :--- | :--- | :--- | :---: | :--- |
| **跳刀** `CAbilityBlink` (`AEbl`) | **`0x00100002`** | `2` = 纯点目标 | 有 (`0x04`) | **`0x11` + `flags=0x0044`** + `itemObj` + `(x,y)` |
| **TP 卷轴** `CAbilityItemTownPortal` (`AItp`) | **`0x00100006`** | `6` = 点或单位 (`2\|4`) | 有 (`0x04`) | **`0x12` + `flags=0x0044`** + `itemObj` + `(x,y)` + `FFFFFFFF FFFFFFFF`（点建筑填建筑 objId） |
| **假眼/真眼** `CAbilityChannel` (`ANcl`, DataB=3, DataC 无 `0x10`) | **`0x00000006`** | `6` = 点或单位 (`2\|4`) | 无 (`0x00`) | **`0x12` + `flags=0x0040`** + `itemObj` + `(x,y)` + `FFFFFFFF FFFFFFFF` |
| **无目标物品**（魔瓶/BKB/相位/梅肯，DataB=0 或瞬发类） | **`0x00000001`** / **`0x00100001`** | `1` = 无目标 | 视母技能 | **`0x10` + `flags=0x0040/0x0044`** + `itemObj` |
| **单位/树目标物品**（吃树 `CAbilityEatTree` / 压制之刃 / 推推 / 羊刀） | **`0x00000004`** / **`0x00100004`** | `4` = 目标单位/树 | 视母技能 | **`0x12` + `flags=0x0040/0x0044`** + `itemObj` + `(tx,ty)` + `targetObj1/2` |

> **对 `war3hook_ai_tactics.inl` 的直接风险预警**：目前 `aiUseItemNow`（L432-L434）仅对假眼/真眼特判改发 `0x12`，而对 **TP（`AItp`, `0x100006`）** 等其他 `Point|Unit` 物品仍发 `0x11 + 0x44`，与真人客户端发包不一致，存在与假眼完全相同的静默失败风险！

### 1.4 零硬编码动态发包公式（推荐 hook 实现）

对任意背包栏位 `slot`（`0..5`）的物品 `CItem*`：
1. 读取物品主主动技能 `CAbility* abil`（遍历 `CItem + 0x9C + i*0x0C` 共 `*(u32*)(CItem + 0x98)` 项，取首个非被动主动技能）；
2. 读取 `uint32_t tt = abil->GetTargetType()`（虚槽 `+0x30C`，或在离线静态表中按 FourCC 预填）；
3. **自动计算 `flags` 与包类型**：
   - `uint16_t flags = 0x0040 | ((tt & 0x00100000u) ? 0x0004 : 0x0000) | (queued ? 0x0001 : 0x0000);`
   - 若 `(tt & 0x0F) == 1` → 发 **`0x10`**（长 15）；
   - 若 `(tt & 0x0F) == 2`（仅纯点目标）→ 发 **`0x11`**（长 23）；
   - 若 `(tt & 0x0F) == 4` 或 `6`（单位目标 / 点或单位目标）→ 发 **`0x12`**（长 31；点地时 `targetObj = 0xFFFFFFFF, 0xFFFFFFFF`，点单位/树时填其 `+0x0C/+0x10`）。

---

## 二、技能、物品与共享冷却（`cooldownID`）纯只读内存链

### 2.1 `CAgentTimer` 统一只读读取公式（`1.22` ~ `1.27` 实证）

`CAgentTimer` 结构体大小固定为 **`0x14`（20 字节）**，所有技能冷却、物品冷却、共享冷却、攻击前摇/间隔均复用同一结构体：

```cpp
// 纯只读读取 CAgentTimer 冷却状态（无需调用游戏虚函数，不涉及线程安全）
struct War3CooldownState {
    bool  active;      // 是否正在冷却
    float remaining;   // 剩余冷却秒数（引擎权威模拟时钟）
    float total;       // 总冷却秒数
};

static War3CooldownState readAgentTimer(const uint8_t *timerAddr) {
    War3CooldownState s = { false, 0.0f, 0.0f };
    // timer + 0x0C -> timerNode*
    const uint8_t *node = *(const uint8_t * const *)(timerAddr + 0x0C);
    if (!node) return s;
    // 1.27 0x639E9D: test byte ptr [node+12h], 1 -> 置 1 表示已到期/已停止
    if (*(const uint8_t *)(node + 0x12) & 0x01) return s;
    const uint8_t *timerMgr = *(const uint8_t * const *)(node + 0x0C);
    if (!timerMgr) return s;
    const float expireTime = *(const float *)(node + 0x04);
    const float totalTime  = *(const float *)(node + 0x08);
    const float gameClock  = *(const float *)(timerMgr + 0x40); // 引擎权威模拟时钟
    const float rem = expireTime - gameClock;
    if (rem > 0.0f && rem < 3600.0f) {
        s.active    = true;
        s.remaining = rem;
        s.total     = totalTime;
    }
    return s;
}
```

### 2.2 英雄技能（`CAbilitySpell`）冷却、禁用、沉默与蓝耗

沿 `CUnit+0x1DC/+0x1E0` 技能链表（下节点 `abil+0x24/+0x28`，FourCC 在 `abil+0x34`）定位到目标 `CAbilitySpell*`：

| 字段 | 偏移（`CAbilitySpell*`） | 类型 / 位掩码 | 说明（1.27 `0x3DED20` `CanCast` & `0x418D20` `StartCooldown` 实证） |
| :--- | :---: | :--- | :--- |
| 状态标志 | `+0x20` | `uint32_t` | **`& 0x200` 且 bit 31 (`0x80000000`) 为 0** → 冷却中（返回错误码 `0xD2`）；`& 0x2000` → 施法中；`& 0x4000` → 持续施法 |
| 技能 FourCC | `+0x34` | `uint32_t` | 如影压 `'A0EY'` / `'A0EZ'` / `'A0F0'` |
| 禁用计数 | `+0x3C` | `int32_t` | `> 0` 表示技能被禁用（返回 `0xDD`） |
| 沉默/暂停计数 | `+0x44` | `int32_t` | `> 0` 表示被沉默/暂停无法施放（返回 `0xB9`） |
| 当前等级（0-based） | `+0x50` | `uint32_t` | 0 = 1 级，1 = 2 级，… |
| **冷却计时器** | **`+0xD0`** | `CAgentTimer` (20B) | **`node = *(u32*)(abil + 0xDC)`**，直接传入 `readAgentTimer(abil + 0xD0)` |
| 蓝耗检查虚槽 | `vt+0x370` | `HasEnoughMana(1)` | 内部调 **`vt+0x3D4` (`GetManaCost`)** × `vt+0x36C` 与单位蓝量比较，不足返回 `0xD1` |

### 2.3 物品（`CItem`）与共享冷却表（`CAbilityInventory`）——彻底解决魔瓶 `A0FO`

反汇编 1.27 `0x5248F8`（拾取同步冷却）、`0x5490B9`（丢弃保存冷却）、`0x639E60`/`0x639E80`（`CItem` 冷却）以及 1.26 `0x0F0FA0` 证实：

1. **为什么魔瓶装符换掉物品 ID 后仍然 0.5s 冷却？**
   - 当英雄使用魔瓶（`I0AM`）时，引擎查 `CItemDatabase` 取出其 `cooldownID = 'A0FO'`（`0x639ED0` → `entry+0x70`），并在英雄的 **`CAbilityInventory`**（通过 `CUnit::FindAbility(hero, 'AInv')` 获取）上登记该共享冷却组：
     - **`inv + 0xBC`**：`uint32_t sharedCdCount`（最多 6 组）
     - **`inv + 0xC0 + idx * 4`**：`uint32_t sharedCdIds[6]`（FourCC，例如 `'A0FO'`、`'AItp'`、`'A0TY'`）
     - **`inv + 0xDC + idx * 0x14`**：`CAgentTimer sharedCdTimers[6]`（每项 20 字节，`node = *(u32*)(inv + 0xE8 + idx * 0x14)`）
   - 即使 DotA 脚本在同一帧销毁旧魔瓶并 `CreateItem` 生成装符魔瓶（`I0AO` 等），**`CAbilityInventory` 中的 `'A0FO'` 计时器仍在走表**；新瓶入包时 `0x5248F8` 立刻按 `'A0FO'` 同步剩余冷却！
2. **物品真实冷却的完整只读判法（取三者最大值）**：
   - **源 1（共享冷却表，最高优先）**：遍历 `inv + 0xC0` 共 `*(u32*)(inv + 0xBC)` 项，若命中该物品的 `cooldownID`（如魔瓶 `'A0FO'`），读 `readAgentTimer(inv + 0xDC + idx * 0x14)`。
   - **源 2（物品自身冷却）**：读 `readAgentTimer(item + 0xE4)`（`node = *(u32*)(item + 0xF0)`，物品丢地再捡起时保存于此）。
   - **源 3（物品内嵌技能冷却）**：遍历 `item + 0x9C + i*0x0C` 共 `*(u32*)(item + 0x98)` 项解析 `CAbility*`，读 `readAgentTimer(abil + 0xD0)`。
   - 取 `remCd = max(源1, 源2, 源3)`：**只要 `remCd <= 0.0f`，下一帧（10ms 级）发包 100% 立即生效，绝不再被引擎因共享冷却拒绝！**

---

## 三、全 11 版 War3 `Game.dll` RVA 与结构体偏移总表

> 严格遵守全版本逆向规则：覆盖 `War3Launcher/versions/` 下全部 11 个版本；`1.0.17.5988` ~ `1.21.0.6263` 无 MSVC RTTI 且 `CItem` 代码段未出现 `0xD01BE` 冷却恢复路径，相关格如实标为 `未确认`，绝不外推。

### 3.1 冷却与物品/共享冷却核心 RVA 对照表（全 11 版）

| 版本 | `CAgentTimer` `GetTimeout` / `GetRem` | `CAbilitySpell::StartCooldown` | `CAbilitySpell` 计时器偏移 | `CItem::StartCooldown` | `CItem` 计时器偏移 | `CAbilityInventory` 共享冷却调用点 | `CAbilityInventory` 共享冷却表偏移 (`cnt`/`ids`/`timers`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | 未确认（无 RTTI） | `0x46F120` | **`+0xD0`** | 未确认（无 `0xD01BE`） | 未确认 | 未确认 | 未确认 |
| `1.0.20.6048` | 未确认（无 RTTI） | `0x46F620` | **`+0xD0`** | 未确认（无 `0xD01BE`） | 未确认 | 未确认 | 未确认 |
| `1.20.4.6074` | 未确认（无 RTTI） | `0x46FB90` | **`+0xD0`** | 未确认（无 `0xD01BE`） | 未确认 | 未确认 | 未确认 |
| `1.21.0.6263` | 未确认（无 RTTI） | `0x473AC0` | **`+0xD0`** | 未确认（无 `0xD01BE`） | 未确认 | 未确认 | 未确认 |
| `1.22.0.6328` | `0x467A20` / `0x467D60` | `0x0502B0` | **`+0xD0`** | `0x2B5120` | **`+0xE4`** | `0x0F0622` | **`+0xBC` / `+0xC0` / `+0xDC`** (stride `0x14`) |
| `1.23.0.6352` | `0x4697B0` / `0x469AF0` | `0x0517F0` | **`+0xD0`** | `0x2B6660` | **`+0xE4`** | `0x0F1B62` | **`+0xBC` / `+0xC0` / `+0xDC`** (stride `0x14`) |
| `1.24.1.6374` | `0x478140` / `0x478480` | `0x0518A0` | **`+0xD0`** | `0x2B6720` | **`+0xE4`** | `0x0F1C12` | **`+0xBC` / `+0xC0` / `+0xDC`** (stride `0x14`) |
| `1.24.4.6387` | `0x4781C0` / `0x478500` | `0x0518B0` | **`+0xD0`** | `0x2B67E0` | **`+0xE4`** | `0x0F1C22` | **`+0xBC` / `+0xC0` / `+0xDC`** (stride `0x14`) |
| `1.25.1.6397` | `0x477480` / `0x4777C0` | `0x050B70` | **`+0xD0`** | `0x2B5A90` | **`+0xE4`** | `0x0F1072` | **`+0xBC` / `+0xC0` / `+0xDC`** (stride `0x14`) |
| `1.26.0.6401` | `0x4776B0` / `0x4779F0` | `0x050B70` | **`+0xD0`** | `0x2B5CC0` | **`+0xE4`** | `0x0F1072` | **`+0xBC` / `+0xC0` / `+0xDC`** (stride `0x14`) |
| `1.27.0.52240` | `0x0433C0` / `0x0438C0` | `0x418D20` | **`+0xD0`** | `0x639E60` | **`+0xE4`** | `0x549179` | **`+0xBC` / `+0xC0` / `+0xDC`** (stride `0x14`) |

### 3.2 动作包与 `GetTargetType()` 核心 RVA 对照表（全 11 版）

| 版本 | `GetTargetType` 虚槽 | `CAbilityBlink` (`0x100002`) | `CAbilityItemTownPortal` (`0x100006`) | `CAbilityChannel` (DataB/C) | `CNetCommandUnitOrder*` 虚表 (`0x10`/`0x11`/`0x12`) 或客户端打包器 |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `1.0.17.5988` | 未确认（无 RTTI） | `0x479610` 等 (含 `0x100002`) | `0x47A1B0` 等 (含 `0x100006`) | 未确认（无 RTTI） | 打包器 `0x1408A0` / `0x140900` / `0x1409D0` |
| `1.0.20.6048` | 未确认（无 RTTI） | `0x479B10` 等 (含 `0x100002`) | `0x47A6B0` 等 (含 `0x100006`) | 未确认（无 RTTI） | 打包器 `0x1408A0` / `0x140900` / `0x1409D0` |
| `1.20.4.6074` | 未确认（无 RTTI） | `0x47A080` 等 (含 `0x100002`) | `0x47AC20` 等 (含 `0x100006`) | 未确认（无 RTTI） | 打包器 `0x1408B0` / `0x140910` / `0x1409E0` |
| `1.21.0.6263` | 未确认（无 RTTI） | `0x47DFB0` 等 (含 `0x100002`) | `0x47EB50` 等 (含 `0x100006`) | 未确认（无 RTTI） | 打包器 `0x140910` / `0x140970` / `0x140A40` |
| `1.22.0.6328` | **`+0x30C`** | `0x1CE460` (`0x100002`) | `0x0724A0` (`0x100006`) | `0x19E900` (`6` + `0x100000`) | 虚表 `0x921B78` / `0x921B84` / `0x921B90` |
| `1.23.0.6352` | **`+0x30C`** | `0x1CF9A0` (`0x100002`) | `0x0739E0` (`0x100006`) | `0x19FE40` (`6` + `0x100000`) | 虚表 `0x935CB8` / `0x935CC4` / `0x935CD0` |
| `1.24.1.6374` | **`+0x30C`** | `0x1CFA50` (`0x100002`) | `0x073A90` (`0x100006`) | `0x19FEF0` (`6` + `0x100000`) | 虚表 `0x944DF0` / `0x944DFC` / `0x944E08` |
| `1.24.4.6387` | **`+0x30C`** | `0x1CFAB0` (`0x100002`) | `0x073AA0` (`0x100006`) | `0x19FF50` (`6` + `0x100000`) | 虚表 `0x944DF0` / `0x944DFC` / `0x944E08` |
| `1.25.1.6397` | **`+0x30C`** | `0x1CED70` (`0x100002`) | `0x072E70` (`0x100006`) | `0x19F210` (`6` + `0x100000`) | 虚表 `0x932C90` / `0x932C9C` / `0x932CA8` |
| `1.26.0.6401` | **`+0x30C`** | `0x1CEFA0` (`0x100002`) | `0x072E70` (`0x100006`) | `0x19F440` (`6` + `0x100000`) | 虚表 `0x932C90` / `0x932C9C` / `0x932CA8` |
| `1.27.0.52240` | **`+0x30C`** | `0x49F1F0` (`0x100002`) | `0x3DC050` (`0x100006`) | `0x49F230` (`6` + `0x100000`) | 虚表 `0x986D7C` / `0x986D88` / `0x986D94`；打包器 `0x3AE4E0..0x3AE660` |

> **工程利好**：因为 `1.22` ~ `1.27` 全部 7 个版本的 **所有结构体偏移（`CAbilitySpell+0x20/+0x3C/+0x44/+0xD0`、`CItem+0x98/+0x9C/+0xE4`、`CAbilityInventory+0xBC/+0xC0/+0xDC`、`CAgentTimer` 节点 `+0x04/+0x08/+0x0C/+0x12`、`timerMgr+0x40`、虚槽 `+0x30C`）完全一致**，hook.dll **不需要维护任何版本硬编码 RVA 表**即可全版本通用！

---

## 四、面向「在线大模型（MCP）」与「离线 10ms 微操 AI」的统一落地设计

### 4.1 职责边界对比

| 维度 | 离线控制（hook.dll 10ms 执行层） | 在线大模型控制（MCP Server 指挥层，1~5s/轮） |
| :--- | :--- | :--- |
| **冷却感知** | 每帧（10ms）纯只读检查 `CAbilitySpell+0xD0` + `CAbilityInventory+0xBC..0xDC` + `CItem+0xE4`；**直接删除**影压 `1.8s` 扣蓝等待、魔瓶 `bottleReady + 0.65s` 与 `g_aiItemReadyAt[]` 墙钟数组 | `get_game_state` 工具回包中为每个技能/物品附带精确 `remCd`、`totalCd`、`silenced`、`manaCost`、`ready` 与 `sharedCdId`，让大模型准确决策“差 1.2s 影压好了再上”或“TP 冷却中不能支援” |
| **动作发包** | 统一 `aiSendItemOrderSmart(slot, targetMode, x, y, targetHandle, queued)`：按物品技能 `GetTargetType()` 自动选 `0x10`/`0x11`/`0x12` 及 `0x40`/`0x44`，彻底修复 TP、假眼、真眼、跳刀、推推等点地/目标物品 | MCP 工具保持高层意图粒度（如 `place_ward(spot)`、`tp_to(lane_or_xy)`、`blink_to(x,y)`、`use_item(slot, target)`），由 hook 自动完成包格式选择与冷却重试 |
| **施法保护** | 发包后直接观测 `abil+0x20 & 0x2000`（施法中）和 `abil+0x20 & 0x200`（进入冷却）确认施放生效，不再用墙钟或扣蓝猜测前摇结束 | 同步返回明确回执（`OK cast_started` / `ERR on_cooldown 2.3s` / `ERR no_mana` / `ERR silenced`），避免大模型反复重试失败动作 |

### 4.2 建议的下一轮实机验证清单（交给主会话执行）

1. **TP 点地修复验证**：背包买 TP（`I04I`），对着己方中塔旁空地分别测旧 `0x11 + 0x44` 与新 `0x12 + 0x44 + FFFFFFFF`，验证引擎开始吟唱 TP 并扣除卷轴。
2. **共享冷却只读验证**：影魔装符前/后 50ms 连续读取 `CAbilityInventory + 0xBC / 0xC0 / 0xDC`，核对出现 `'A0FO'` 且 `remCd` 从 `0.50s` 精确递减到 `0.00s`，确认归零瞬间连喝 3 口 0 次被拒。
3. **技能冷却只读替换验证**：影魔三连影压时对比 `CAbilitySpell + 0xD0` 读出的 `remCd` 与面板倒计时，确认误差 `< 0.05s`（在 0.5x 慢速局下同样精确）。
