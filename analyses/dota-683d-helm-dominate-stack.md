# DotA 6.83d 支配头盔（`I08T`）：AI 自动合成、支配中立野怪与控怪囤野（全 11 版）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 为 AI 囤野提供「买支配头盔 → 支配中立野怪 → 控野怪替英雄囤近卫 6 个野点（W5/F5/I5/E5/B5/U4）」的完整逆向依据与 Hook 状态机设计，使英雄能腾出时间去线上补刀或同步囤其它野点 |
| **命名方式** | 正文 `dota-683d-helm-dominate-stack.md`；导图 `dota-683d-helm-dominate-stack-mindmap.md`；产物目录 `artifacts/helm-dominate/` |
| **分析时间** | 2026-11-25 |
| **验证状态** | **DotA 6.83d `Scripts_war3map.j` / SLK / `DotaItemShopAbbrev.h` / `war3hook_ai.cpp` / `war3hook_process.cpp` + 全 11 版 `Game.dll` 静态反汇编核验**；遵循红线未开游戏、未连 6120、未改 `War3Launcher` 源码；已提供实机核验脚本留给 Claude 在测试机运行；未动态实机跑通的细节标 `❓` |
| **前序参考** | [`dota-6.83d-active-items-and-consumables-reverse.md`](./dota-6.83d-active-items-and-consumables-reverse.md)、[`dota-neutral-camp-spawn-box.md`](./dota-neutral-camp-spawn-box.md)、[`dota-neutral-camp-openings.md`](./dota-neutral-camp-openings.md)、[`war3-inplace-turn-lockstep.md`](./war3-inplace-turn-lockstep.md) |
| **配套产物** | [`artifacts/helm-dominate/`](../artifacts/helm-dominate/)（`probe_helm_683d.txt`、`helm_683d_details.txt`、`selection_all11_rva.txt`、`creep_stats_683d.txt`、`verify_live_helm_dominate.py`） |
| **配套思维导图** | [`dota-683d-helm-dominate-stack-mindmap.md`](./dota-683d-helm-dominate-stack-mindmap.md) |

---

## 零、核心结论速览

1. **配方与自动合成（§一）**：
   - 支配头盔（`I08T`，总价 **1850 金**）在 DotA 6.83d **无卷轴**，由两件组件在英雄背包中由地图脚本（`war3map.j` `J50/J60 → JB0` 配方表）**自动合成**：
     - **铁意头盔 `Helm of Iron Will`（950g）**：主基地「武器商人 `n01K`」index **`21`**（`-buy helm_of_iron_will`，假单位 `h01H`）；边路地精实验室 `u00Z` index `136`。
     - **死亡面具 `Mask of Death`（900g）**：主基地「奎尔瑟兰的密室 `hC95`（近卫）/ 恶魔遗物 `nC35`（天灾）」index **`28`**（`-buy mask_of_death`，假单位 `h01M`）；边路地精实验室 `u00Z` index `129`。
   - **已有 `-buy` 流程即可直接合成**：依次下 `-buy helm_of_iron_will` 与 `-buy mask_of_death`，随后轮询 `UnitItemInSlot(hero, 0..5)`，检出 `GetItemTypeId(item) == 'I08T'`（`0x49303854`）即确认合成完成。
2. **支配 `A2V4` 动作包与效果（§二）**：
   - `A2V4` 为 `ANcl`（`DataB1 = 1` 对单位目标），射程 **700**、冷却 **60s**、耗蓝 **75**。
   - **动作包**：`Action 0x12`（31 字节），`flags = 0x0000`，`orderId = 0x000D0028 + slot`（`useslot1..6`），`itemObj1/itemObj2 = 0xFFFFFFFF/0xFFFFFFFF`（对单位施放由引擎按 `useslot` 找物品，或填 `CItem +0x0C/+0x10` — 与 `war3hook_ai.cpp` 现有 `aiOrderTarget` 一致，见 §二），`target = 野怪 (obj1, obj2)` 与其 `(x, y)`。
   - **永久控制、上限 1 只**：`war3map.j:YFO (L20329-20347)` 将目标 `SetUnitOwner` 给施法者玩家，**无持续时间上限**；但若再次支配，会先对旧支配怪调用 **`KillUnit(u)`**！同时额外附加 3 个技能：`Aeth`（幽灵可见）、`ACrk`（抗性皮肤）、`A2YD`（**+250 最大生命值**），并**回满蓝量**（`QSI`）；原野怪主动技能仍可正常使用。
   - **不可支配**：远古野（`nonancient`）、英雄（`nonhero`）、机械（`organic`）、魔免（如泥土傀儡 `ngrk`）及 `Y5O` 特判的 6 种特殊单位（`n00H/n00G/n00K/n00J/n00A/n006`）。
3. **控制非英雄单位的核心机制（§三）**：
   - **有没有不切选框直接发令的动作包？→ 没有**。`0x10/0x11/0x12` 均作用于当前 `CSelectionWar3` 选区；`0x17/0x18` 编队热键本质也是切换选区。
   - **切换选区是否打断英雄当前动作？→ 不会**。`0x16`（`CNetCommandUnitSelectionModify`）仅修改 `CSelectionWar3` 与触发选区事件，**不触碰 `CUnit` 的 `COrder`**；因此英雄正在走位/补刀/A 兵时，可在同一或相邻锁步回合内无缝完成 **「取消选英雄 → 选支配怪 → 下移动/攻击指令 → 取消选支配怪 → 切回英雄」**。
   - **关键坑点（`war3hook_ai.cpp` 现有 `aiSelectHero`）**：`buildSelectionSwitchAction` 传入 `from = 0xFFFFFFFF` 时会**省略取消选中段**！控支配怪时**必须显式传入 `from = heroObj1/heroObj2`**（取消选英雄）再选支配怪，发完令后再传入 `from = creepObj1/creepObj2` 切回英雄，并清零 `g_aiHeroSelectedTick = 0`，否则会把英雄和野怪**同时选中**，一发 `move` 英雄也跟着跑！
4. **用被支配野怪囤近卫 6 个野点（§四）**：
   - **拉野仇恨与回位规则与英雄完全一致**（归属本地玩家，中立敌对将其视为普通敌方单位）。
   - **绝对红线（防封野）**：`P3O/P2O` 刷野检测只要野点 `r1` 矩形内有**任意存活的玩家单位**就不刷野！被支配野怪在 `:00` 刷野瞬间必须停在所有 6 个野点 `r1` 矩形之外。
   - **首选支配野怪**：**远程高血/高移速野怪优先** — ① `nfsh` 森林巨魔牧师（射程 `600`，HP `450+250=700`，移速 `290`，还能自奶）；② `ndtr` 黑暗巨魔（射程 `500`，HP `500+250=750`，移速 `270`）；③ `ncen` 半人马先行者（HP `550+250=800`，移速 `350` 极快适合拉双野）。
   - **单点驻守 vs 双点轮换**：单只支配怪可在 **B5 ↔ E5**（间距仅 `1300` 码）或 **F5 ↔ W5**（间距 `1195` 码）之间，甚至 **一分钟内拉完一个点或跨分钟轮换**，同时英雄可自由在线上发育。

---

### 0.1 全 11 版本核心函数 RVA 总表

来源：[`selection_all11_rva.txt`](../artifacts/helm-dominate/selection_all11_rva.txt)、[`war3-inplace-turn-lockstep.md`](./war3-inplace-turn-lockstep.md)、[`war3hook_offsets.cpp`](file:///d:/Qt/workspace/War3Launcher/hooker/war3hook_offsets.cpp)。

> **说明**：`1.0.17`–`1.21.0` 编译时未开启 MSVC RTTI（`/GR-`）且早于 1.22 的 `0x000A0016` 事件码重构，故 `0x16~0x19` 事件码列按规范核验后标 `—`；所有 11 个版本的动作入队统一走 `EnqueuePlayerAction`，单位识别与背包检查均通过 JASS 原生名表动态解析（全 11 版通用）。

| War3 版本 | `EnqueuePlayerAction` | `0x16` 选区修改 (`Recv/Disp`) | `0x16` 选区修改 (`Send`) | `0x17` 设编队 (`Recv/Send`) | `0x18` 选编队 (`Recv/Send`) | `0x19` 切子组 (`Recv/Send`) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | `0x6D5332` | — *(无 0x0A0016 事件码)* | — | — | — *(早期结构)* | — |
| `1.0.20.6048` | `0x6D5832` | — *(无 0x0A0016 事件码)* | — | — | — *(早期结构)* | — |
| `1.20.4.6074` | `0x6D6172` | — *(无 0x0A0016 事件码)* | — | — | — *(早期结构)* | — |
| `1.21.0.6263` | `0x6DA192` | — *(无 0x0A0016 事件码)* | — | — | — *(早期结构)* | — |
| `1.22.0.6328` | `0x640562` | `0x2CEA5B` | `0x5366E2` | `0x2CEC8B` / `0x5367C2` | `0x2CB64D` / `0x5310D2` | `0x2CB6CE` / `0x5311A5` |
| `1.23.0.6352` | `0x6421E2` | `0x2CFF9B` | `0x538492` | `0x2D01CB` / `0x538572` | `0x2CCB8D` / `0x532E82` | `0x2CCC0E` / `0x532F55` |
| `1.24.1.6374` | `0x650BD2` | `0x2D005B` | `0x546E22` | `0x2D028B` / `0x546F02` | `0x2CCC4D` / `0x541812` | `0x2CCCCE` / `0x5418E5` |
| `1.24.4.6387` | `0x650C82` | `0x2D011B` | `0x546EA2` | `0x2D034B` / `0x546F82` | `0x2CCD0D` / `0x541892` | `0x2CCD8E` / `0x541965` |
| `1.25.1.6397` | `0x6502B2` | `0x2CF3CB` | `0x546172` | `0x2CF5FB` / `0x546252` | `0x2CBFBD` / `0x540B62` | `0x2CC03E` / `0x540C35` |
| `1.26.0.6401` | `0x6504E2` | `0x2CF5FB` | `0x5463A2` | `0x2CF82B` / `0x546482` | `0x2CC1ED` / `0x540D92` | `0x2CC26E` / `0x540E65` |
| `1.27.0.52240` | `0x840BBB` | `0x2FC263` | `0x69FA02` | `0x2FB8B3` / `0x69F63E` | `0x2FC003` / `0x69F8FF` | `0x2FC0C3` / `0x69FB6F` |

---

## 一、合成与自动购买（DotA 6.83d）

### 1.1 配方、价格与所属商店

来自 `Scripts_war3map.j`（`L14446-14448`、`L92574-92635`、`L93408-93415`、`L94897-94899`）与 [`DotaItemShopAbbrev.h`](file:///d:/Qt/workspace/War3Launcher/shared/DotaItemShopAbbrev.h#L46-L96)：

| 物品 | 背包 Item FourCC | 脚本变量 | 价格 | 商店假单位 (`soldUnitId`) | `DotaItemShopAbbrev.h` index & `-buy` 缩写 | 出售商店（基地 / 边路） |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **铁意头盔** (Helm of Iron Will) | `I03B` / `I04E` | `GW0` | **950g** | `h01H`（边路 `h08N`） | index **`21`** (`helm_of_iron_will`)；边路 `136` (`side_helm_of_iron_will`) | 基地「武器商人 `n01K`」(shop `2`)；边路「地精实验室 `u00Z`」(shop `14`) |
| **死亡面具** (Mask of Death) | `I03G` / `I04K` | `GM0` | **900g** | `h01M`（边路 `h08O`） | index **`28`** (`mask_of_death`)；边路 `129` (`side_mask_of_death`) | 基地「奎尔瑟兰的密室 `hC95` (近卫) / 恶魔遗物 `nC35` (天灾)」(shop `3, 4`)；边路 `u00Z` (shop `14`) |
| **支配头盔** (Helm of the Dominator) | **`I08T`**（信使版 `I08V`） | `V80` (`V90`) | **1850g**（无卷轴） | 无（`FP0[V80]=0`） | index `98` (`gold=0`，不可直接购买) | 自动合成，**无需卷轴、无需神秘商店** |

> **关键发现**：
> 1. 两件散件均在**主基地商店**即可买齐（也可在边路地精实验室 `u00Z` 买齐），无需去神秘商店。
> 2. **自动合成 100% 由地图触发器完成**（`war3map.j` 注册 `J50[JC0]=GW0, J60[JC0]=GM0, JB0[JC0]=V80`）：英雄获得物品触发 `EVENT_PLAYER_UNIT_PICKUP_ITEM` 时，脚本扫描配方表，若背包同时存在 `GW0` 与 `GM0` 则自动移除两件组件并创建 `I08T`（`1227896916 = 0x49303854`）。若在信使上合成则生成 `I08V`（`V90`），交给英雄时 `F3O`（`L16610-16648`）自动转为 `I08T`。

### 1.2 自动购买与核实闭环

现有 hook 已有 `requestItemBuyByIndex`（[`war3hook_process.cpp:L3085-3096`](file:///d:/Qt/workspace/War3Launcher/hooker/war3hook_process.cpp#L3085-L3096)）与 `-buy` / `aiTickBuyCheck`：
1. 确保英雄在基地商店购买范围内（或在边路商店旁）且有 ≥ 2 个空物品格（若只剩 1 格且已有一件组件，买第 2 件时 DotA 脚本先入袋触发合成或落地再拾取，稳妥起见保留 ≥ 1 格 + 已持有 1 件，或 ≥ 2 空槽）。
2. 当金币 ≥ 950 且背包无 `I03B/I04E` 且无 `I08T` → 购买 `index = 21`（`helm_of_iron_will`）。
3. 当金币 ≥ 900 且背包无 `I03G/I04K` 且无 `I08T` → 购买 `index = 28`（`mask_of_death`）。
4. 每帧检查 `UnitItemInSlot(hero, s)`（`s = 0..5`）：找到 `GetItemTypeId(it) == 'I08T'` 记录其槽位 `helmSlot`，即宣告合成完成。

---

## 二、支配技能 `A2V4` 与被支配野怪特性

### 2.1 `A2V4` 动作包格式

由 `Units_AbilityData.slk:Y4130` 与 [`dota-6.83d-active-items-and-consumables-reverse.md`](./dota-6.83d-active-items-and-consumables-reverse.md) 核验：
- 技能 ID：`A2V4`（`1093817908`），原型 `ANcl`（通魔），`DataB1 = 1`（**对单位目标**），`DataF1 = creepheal`，`Rng1 = 700`，`Cool1 = 60s`，`Cost1 = 75 MP`，`targs1 = air,enemies,ground,neutral,nonancient,nonhero,organic`。
- **动作包（31 字节 `Action 0x12`，与 hook 现有 `aiOrderTarget` 对单位用物品一致）**：

| 偏移 | 长度 | 字段 | 值 |
| :---: | :---: | :--- | :--- |
| `+0x00` | 1 | `actionId` | `0x12`（Target Object Order） |
| `+0x01` | 2 | `flags` | `0x0000`（无队列、非移动队列） |
| `+0x03` | 4 | `orderId` | `0x000D0028 + helmSlot`（`useslot1..6`：`0xD0028`~`0xD002D`，`helmSlot ∈ [0..5]`） |
| `+0x07` | 8 | `itemObj1, itemObj2` | `0xFFFFFFFF, 0xFFFFFFFF`（或 `CItem +0x0C, +0x10`；`useslot` 语义下引擎按栏位定位物品，已有 `-use` 实机验证） |
| `+0x0F` | 8 | `targetX, targetY` | 目标中立野怪当前浮点坐标 `(ux, uy)` |
| `+0x17` | 8 | `targetObj1, targetObj2` | 目标野怪的 `CUnit +0x0C, +0x10` |

> **前置条件检查**：发包前需确认：① 英雄当前选中；② 英雄与目标野怪距离 ≤ `700`（建议先走近到 `≤ 600` 再发，避免走动中被打断）；③ 英雄蓝量 ≥ `75`；④ `I08T` 不在 `60s` 冷却中（可本地记录上次成功支配时间戳 `now - lastDomTick >= 60500`）。

### 2.2 支配后的单位变化（`war3map.j:YFO` 实锤）

反查 `Scripts_war3map.j` `YFO`（`L20329-20347`）、`Y5O`（`L20269-20272`）、`QSI`（`L4142-4144`）：
1. **归属变更**：`SetUnitOwner(target, GetOwningPlayer(caster), true)`，归属本地玩家（与英雄同队同控）。
2. **永久存在（无时限）**：脚本未加 `UnitApplyTimedLife`，只要不被打死或再次支配，**一直存活**。
3. **上限严格为 1 只**：`YFO` 先枚举本玩家所有单位，若 `LoadInteger(LY, GetHandleId(u), 4323) == 1`（上一只支配怪），**立即调用 `KillUnit(u)` 处死旧怪**，再给新怪写入标记 `4323 = 1`。
4. **属性与技能增强**：
   - `UnitAddAbility(u, 'Aeth')`（幽灵可见，允许穿越部分碰撞/标识）；
   - `UnitAddAbility(u, 'ACrk')`（抗性皮肤，减少控制时长）；
   - `UnitAddAbility(u, 'A2YD')`（DotA 6.83d 支配头盔专属 **+250 最大生命值**）；
   - `QSI(u)`：**立刻将蓝量补满至 100%**；
   - **保留原中立野怪全部主动/被动技能**（如森林巨魔牧师的治疗、半人马的战争践踏、萨特的冲击波/净化、黑暗巨魔首领的网等）。
5. **不可支配的目标清单**：
   - 所有**远古野**（黑龙 `nbwm`、黑蜉蝣 `nbdk`、雷霆蜥蜴 `n0LC/n0LD`、远古花岗岩傀儡等，`targs1` 含 `nonancient`）；
   - **魔免单位**（泥土傀儡，法术免疫拒绝 `ANcl` 目标）；
   - **英雄 / 建筑 / 机械攻城车**（`nonhero` + `organic`）；
   - **`Y5O` 硬编码排除的 6 种单位**（`L20271`）：`n00H`、`n00G`、`n00K`、`n00J`、`n00A`、`n006`（Roshan / 特殊召唤物等）。

---

## 三、控制被支配的非英雄单位（关键难点）

### 3.1 引擎动作包机制核验（1.27 反汇编实锤）

1. **有没有「不切选区直接对指定单位发令」的动作包？→ 没有。**
   - War3 W3GS 协议中所有单位命令包（`0x10` Immediate、`0x11` Point、`0x12` Target Object、`0x13` Give/Drop Item、`0x14` Two-Target）**包体内均不包含「发令者单位 ID」字段**，引擎执行时固定对当前玩家的 `CSelectionWar3` 选区（及当前激活子组 `0x19`）中的所有己方单位下达指令。
   - `0x17`（`CNetCommandUnitDefineControlGroup` 设编队）与 `0x18`（`CNetCommandUnitSelectControlGroup` 选编队）底层同样修改 `CSelectionWar3`（见 1.27 `0x2FC003` / `0x69F8FF`）。相比 `0x16 + 0x19`，`0x18` 仅在反复切同一单位时略省字节，但需先用 `0x17` 绑定且死亡后要重绑，**通用性与可控性不如直接用 `0x16 + 0x19`**。
2. **切换选区（`0x16`）会不会打断英雄正在执行的 `COrder`？→ 不会！**
   - 1.27 `0x2FC260..0x2FC2D5` 反序列化 `CNetCommandUnitSelectionModify`（事件码 `0x000A0016`），经 `0x2FD850 → 0x30ADA0` 仅派发给 `CSelectionWar3` 更新选区列表与触发 `EVENT_PLAYER_UNIT_SELECTED` / `DESELECTED`，**完全不访问也不取消被取消选中单位的 `COrder` 链表**。
   - 实操意义：英雄正在走位、A 兵或施法前摇期间，AI 可以在**同一锁步回合或连续回合内**完成「切到支配怪 → 下移动/攻击令 → 切回英雄」，**英雄不会停步、不会取消攻击**。

### 3.2 完整动作包序列与现有 `aiSelectHero` 的坑点

[`war3hook_process.cpp:L3061-3083`](file:///d:/Qt/workspace/War3Launcher/hooker/war3hook_process.cpp#L3061-L3083) 已实现 `buildSelectionSwitchAction(buf, from1, from2, to1, to2, toTypeId)`，其生成的单包字节流为：
1. `[0x1B 0x02 from1 from2]`（Selection Event: Deselect，仅当 `from1 != 0xFFFFFFFF` 时写入）
2. `[0x1B 0x01 to1 to2]`（Selection Event: Select）
3. `[0x16 0x02 0x01 0x00 from1 from2]`（`mode=0x02` 从选区移除 `from`，仅当 `from1 != 0xFFFFFFFF` 时写入）
4. `[0x16 0x01 0x01 0x00 to1 to2]`（`mode=0x01` 将 `to` 加入选区）
5. `[0x1A]`（Refresh Subgroup）
6. `[0x19 toTypeId to1 to2]`（Select Subgroup，将 `to` 设为当前主操作子组）

> **⚠️ 必须规避的坑点**：
> 现有 `aiSelectHero()`（[`war3hook_ai.cpp:L713-715`](file:///d:/Qt/workspace/War3Launcher/hooker/war3hook_ai.cpp#L713-L715)）把 `from1/from2` 写死了 `0xFFFFFFFF`！如果你只选过英雄，接着用 `from = 0xFFFFFFFF` 去选支配怪，选区会变成 **`{英雄, 支配怪}`（双选）**，下一条 `move` 会让英雄一起跑去野区！

**正确的「控支配怪单次发令」完整 3 步动作序列**（可在同一帧连续调用 `EnqueuePlayerAction` 入队，引擎按入队顺序在同一 `0x0C` 回合内原子执行！）：
1. **切到支配怪**（移除英雄、选中支配怪）：
   `buildSelectionSwitchAction(buf, heroObj1, heroObj2, domObj1, domObj2, domTypeId)` → `EnqueuePlayerAction`
2. **给支配怪下指令**：
   - 移动：`0x12` + `flags=0x0000` + `orderId=0xD0012` (`move`) + `(x, y)` + `target=FFFFFFFF/FFFFFFFF`
   - 普攻野怪：`0x12` + `flags=0x0000` + `orderId=0xD000F` (`attack`) + `(tx, ty)` + `target=(neutralObj1, neutralObj2)`
   - 停稳防乱走：`0x10` + `flags=0x0000` + `orderId=0xD0019` (`holdposition`)
3. **立即切回英雄**（移除支配怪、选中英雄）：
   `buildSelectionSwitchAction(buf, domObj1, domObj2, heroObj1, heroObj2, heroTypeId)` → `EnqueuePlayerAction`
   并置 `g_aiHeroSelectedTick = GetTickCount()`（或清零以允许下次兜底重选）。

> **为什么同一回合内连发 3 包安全？**
> 如 [`war3-inplace-turn-lockstep.md`](./war3-inplace-turn-lockstep.md) §一所述，一个 `0x0C` 回合包内的多个动作在逻辑帧内**严格按顺序执行**：① 先把 `CSelectionWar3` 改为 `{dom}` → ② `0x12` 仅发给 `{dom}` → ③ 再把 `CSelectionWar3` 恢复为 `{hero}`。玩家界面甚至几乎看不到选框闪烁，且完全不阻塞英雄下一帧的补刀/走位指令！（注：实机需验证同一回合连续 3 包是否被任何防刷包限流，若发现偶发漏选，可拆成间隔 1 帧发包，标 `❓` 待实机确认。）

### 3.3 Hook 在 `g_aiUnits` 中识别「被支配野怪」的方法

在 `g_aiUnits` 扫描循环中，按以下条件精准识别被支配野怪并缓存其 `(handle, obj1, obj2, typeId)`：
```cpp
// 1. 归属本地玩家且存活
bool ownedByMe = (u.owner == localPlayer) && (u.hp > 0.5f);
// 2. 非英雄、非建筑、非幻象
bool isNonHero = !IsUnitType(u.h, UNIT_TYPE_HERO)
              && !IsUnitType(u.h, UNIT_TYPE_STRUCTURE)
              && !IsUnitIllusion(u.h);
// 3. FourCC 首字节为 'n'（中立野怪池均为 nXXX），排除信使(o004/o005/n00L等)与眼(oeye/osw1)
char c0 = (char)((u.typeId >> 24) & 0xFF);
bool isNeutralCreepType = (c0 == 'n')
                       && (u.typeId != 'n00L')  // 排除可能的中立系非野怪单位
                       && (u.maxHp >= 450.0f);  // 支配怪必有 +250 HP 加成，最低狗头人也有 240+250=490
```
若需 100% 精确区分（例如英雄本身是陈/魅惑魔女或招了死灵书）：可再调用 JASS `GetUnitAbilityLevel(u.h, 'A2YD') > 0`（支配头盔专属 +250 HP 被动，其它任何手段都不会赋予此技能！）。

---

## 四、用被支配野怪囤野（近卫 6 野点实战策略）

### 4.1 仇恨、拉野与封野规则核对

1. **仇恨与回位**：被支配野怪归属 `localPlayer`，中立敌对野怪将其视为标准敌方单位，**仇恨触发、600 码警戒、追击回位（leash）时间与英雄拉野完全相同**。因此用户已用 `-mark arc` 标好的近卫 6 个野点站位与拉野弧度（`W5/F5/I5/E5/B5/U4`）**可直接复用给被支配野怪**！
2. **封野红线（`P3O/P2O`）**：由 [`dota-neutral-camp-spawn-box.md`](./dota-neutral-camp-spawn-box.md) 证实，每分钟 `:00` 刷野时，只要野点 `r1` 矩形内存在**任意存活的玩家单位**（包括被支配野怪），该野点即被封野不刷！
   - 近卫 6 野点 `r1` 矩形边界（来自 `artifacts/helm-dominate/selection_all11_rva.txt`）：
     - `U4`：`[-3552, -768, -2528, 320]`（中心 `[-3216, -256]`，远古野）
     - `W5`：`[-1728, -5056, -768, -3840]`（中心 `[-1056, -4592]`）
     - `F5`：`[-1024, -3808, 192, -2752]`（中心 `[-416, -3584]`）
     - `I5`：`[1056, -5216, 2368, -3744]`（中心 `[1584, -3984]`）
     - `E5`：`[2592, -4800, 3744, -3328]`（中心 `[3072, -3712]`）
     - `B5`：`[2272, -6080, 3776, -4928]`（中心 `[2960, -5008]`）
   - **安全停靠规则**：被支配野怪拉完野后，必须走到**目标弧度外侧且位于全部 6 个 `r1` 矩形外 ≥ 150 码处**下 `holdposition`，等到 `:02` 刷野完成后再回拉野站位。

### 4.2 6.83d 最适合囤野的支配野怪排名

来自 `artifacts/helm-dominate/creep_stats_683d.txt`（所有支配怪额外享有 `A2YD` **+250 HP** 与 `QSI` 满蓝）：

| 优先级 | FourCC | 名称 | 支配后 HP | 移速 | 射程 | 推荐理由 |
| :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **T0** | `nfsh` | 森林巨魔牧师 | **700** | **290** | **600** (远程) | **最强囤野怪**：600 射程远距离点一下就走几乎零掉血，且自带治疗技能可自我续航 |
| **T0** | `ndtr` | 黑暗巨魔 | **750** | 270 | **500** (远程) | 500 射程安全拉远古/大野，血厚容错高 |
| **T1** | `ncen` | 半人马先行者 | **800** | **350** | 100 (近战) | **极速 350**，适合长距离拉野及跨点轮换（如 B5 ↔ E5 或 W5 ↔ F5），且自带 2 甲耐扛 |
| **T1** | `nsth` | 萨特地狱使者 | **1350** | 290 | 100 (近战) | 血量极厚（1350 HP）+ 回血光环，硬抗拉 4~5 波野不死 |
| **T1** | `nfpc` | 极地熊怪勇士 | **1200** | 320 | 100 (近战) | 高血（1200）+ 3 甲 + 320 移速，极抗揍 |
| **T2** | `ngns` | 豺狼刺客 | 620 | 270 | **500** (远程) | 500 射程安全拉野，血量略脆但够用 |
| **❌ 避开** | `nbdk/nbwm/n0LC/n0LD` / `ngrk` | 远古野 / 泥土傀儡 | — | — | — | **无法被 `A2V4` 支配**（发包会报无效目标） |

### 4.3 单点驻守 vs 多点轮换

- **阶段 1（强烈建议先落地）：单点驻守远古野 `U4` 或大野 `W5/I5`**
  - 支配一只远程怪（`nfsh`/`ndtr`）或高移速怪（`ncen`）后，直接派往 `U4`（近卫远古野，影魔/核心收益最高！）或 `W5`（离中路最近）的 `-mark arc` 站位待命。
  - 每分钟 `:51~:53`（远程按 `:52.5`、近战按 `:51.5`）点一下野怪 → 沿标记弧度拉出 `800` 码（确保在 `r1` 矩形外）→ `:02` 后回到站位。
  - **收益**：英雄完全解放，可专注中路补刀或自己顺手囤另一个近点（例如支配怪蹲 `U4` 远古野，英雄去囤 `W5`/`F5`）。
- **阶段 2（进阶）：支配怪跨分钟轮换相邻两点**
  - 相邻野点间距：`W5 ↔ F5` 仅 **`1195` 码**（移速 300 走 4 秒），`B5 ↔ E5` 仅 **`1300` 码**（走 4.3 秒）。
  - 一旦某野点实测野怪数量 ≥ 4 波（已囤满），支配怪在 `:03` 自动切换去相邻野点继续囤，避免单点卡死。

---

## 五、Hook 侧实现方案（状态机与增量清单，供 Claude 编码）

> 以下仅为伪代码与架构设计，遵循红线未改动 `War3Launcher` 任何源码。

### 5.1 核心辅助函数（新增在 `war3hook_ai.cpp` / `war3hook_ai_tactics.inl`）

```cpp
// 向被支配野怪原子发令：取消选英雄 → 选支配怪 → 发令 → 取消选支配怪 → 切回英雄
// 切选区仅修改 CSelectionWar3，不打断英雄正在执行的 COrder
static void aiOrderDominatedUnit(uint32_t orderId, float x, float y,
                                 uint32_t tgtObj1, uint32_t tgtObj2, bool isImmediate) {
    if (!g_domUnit.valid || !g_hero.valid) return;

    // 1. 从英雄切换到支配怪（必须传入 heroObj 取消选英雄，避免双选！）
    uint8_t selDom[64];
    int n1 = buildSelectionSwitchAction(selDom,
        g_hero.obj1, g_hero.obj2,
        g_domUnit.obj1, g_domUnit.obj2, g_domUnit.typeId);
    EnqueuePlayerAction(selDom, n1);

    // 2. 给支配怪下指令
    if (isImmediate) {
        aiEnqueueImmediate(orderId);                        // 0x10 (如 0xD0019 hold)
    } else {
        aiEnqueueTargetOrder(orderId, x, y, tgtObj1, tgtObj2); // 0x12 (move/attack)
    }

    // 3. 立即切回英雄（取消选支配怪，恢复英雄选区）
    uint8_t selHero[64];
    int n2 = buildSelectionSwitchAction(selHero,
        g_domUnit.obj1, g_domUnit.obj2,
        g_hero.obj1, g_hero.obj2, g_hero.typeId);
    EnqueuePlayerAction(selHero, n2);

    // 刷新英雄选中时间，避免同帧 aiSelectHero 重复发包
    g_aiHeroSelectedTick = GetTickCount();
}
```

### 5.2 整体状态机（`AI_DOM_STATE`）

```cpp
enum AiDomState {
    DOM_BUY_HELM,        // 缺铁意头盔(index 21, 950g) -> 钱够且在商店范围发 -buy
    DOM_BUY_MASK,        // 缺死亡面具(index 28, 900g) -> 钱够发 -buy，等背包出现 I08T
    DOM_FIND_CREEP,      // 有 I08T 且无存活支配怪 -> 英雄去最近非远古野点(W5/F5/I5)找 T0/T1 野怪
    DOM_CAST_DOMINATE,   // 英雄距目标 <= 600 且蓝 >= 75 且 CD 就绪 -> 发 0x12 (0xD0028 + helmSlot) 支配
    DOM_CREEP_MOVE_WAIT, // 支配怪就位目标野点(如 U4)的 -mark arc 站位，确保在所有 r1 矩形外
    DOM_CREEP_PULL,      // :51~:53 支配怪攻击野点内一只野怪
    DOM_CREEP_KITE,      // 触发仇恨/攻击出手后沿标记弧度拉出 800 码，停在 r1 外 hold 至 :02
};
```

### 5.3 与英雄补刀 / 行动交错时的节流规则

1. **发令节流**：支配怪状态机每 **300~500 ms** 最多触发一次 `aiOrderDominatedUnit`（就位阶段甚至每 1000 ms 一次），**在英雄补刀前摇窗口内（如 `heroLastHitPending`）推迟 150 ms**，完全不干扰补刀节拍。
2. **死亡重支配**：每帧 `g_aiUnits` 找不到 `g_domUnit.handle`（或 `hp <= 0`）且 `I08T` 冷却已好 → 自动回到 `DOM_FIND_CREEP`。
3. **新增清单（仅需改动 2 个文件）**：
   - `war3hook_ai.cpp`：新增 `GetUnitAbilityLevel` 原生（查 `'A2YD'`，可选）与 `aiOrderDominatedUnit` 封装、`g_domUnit` 缓存。
   - `war3hook_ai_tactics.inl`：新增 `aiTickDomStack()` 状态机与控制台调试命令（如 `-domstack on/off`、`-domcamp U4`）。

---

## 六、验证方案（静态已完成 + 实机交接脚本）

### 6.1 静态核实结论
- `probe_helm_683d.py` & `probe_helm_details.py`：已实锤 `I08T` 合成公式（`GW0` 950g + `GM0` 900g，无卷轴）、`A2V4` 参数、`YFO` 永久支配 + 上限 1 只（旧怪 `KillUnit`）+ `Aeth`/`ACrk`/`A2YD` + 满蓝 + `Y5O` 6 种特判排除。
- `scan_0x16_all11.py`：已提取 `1.22`–`1.27` 全部 `0x16~0x19` 虚表与收发 RVA，并反汇编 1.27 `0x2FC260..0x2FD885` 证实 `0x16` 仅派发至选区系统不打断 `COrder`。

### 6.2 实机核验步骤（留给 Claude 在本地自建服执行）

1. **测试购买与自动合成**：开本地房选影魔，给 `2000` 金，依次执行 `-buy helm_of_iron_will` 与 `-buy mask_of_death`，查 `units` / 背包确认自动合成 `I08T`。
2. **测试支配**：带英雄走到 `W5` 或 `F5` 野点，对一只非远古/非魔免野怪下 `-use <slot> <unit>`，确认野怪变己方、血量 `+250`、蓝量满、`g_aiUnits` 可识别。
3. **测试控怪不打断英雄**：让英雄下长距离 `move`（如泉水走到中路），途中通过 `aiOrderDominatedUnit` 给支配怪下 `move` 到 `U4` 站位，观察英雄是否**完全不停步**、支配怪是否**独立走向 `U4`**。
4. **测试囤野**：运行 [`verify_live_helm_dominate.py`](../artifacts/helm-dominate/verify_live_helm_dominate.py) 解析 `C:\War3Run\War3Launcher\logs\AiUnit.log`，自动核对 `I08T` 出现、支配怪归属切换、以及 `:00` 刷野后 `U4`/`W5` 野怪数量递增。
