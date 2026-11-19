# DotA 6.83d 吃树（Tango）与砍树（Quelling Blade）逆向分析及 AI 接口设计

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Antigravity AI Agent |
| **分析目的** | 完整逆向 DotA v6.83d 地图与 War3 引擎的吃树、砍树及树木存储/枚举机制，为 `War3Launcher` 提供安全、全版本兼容的 AI 查树/吃树/砍树接口 |
| **命名方式** | `dota-6.83d-eat-and-cut-tree-reverse`；对外主指令：`-tree cut|eat|list` 与 `/tree cut|eat|list`（兼容别名 `trees`、`eattree`/`tango`、`cuttree`/`quell`/`chop`） |
| **分析时间** | 2026-11-19 |
| **验证状态** | 静态分析 100% 完成（MPQ/JASS/SLK + 11 版本 `game.dll` 反汇编）；代码已落地并进入编译/联调验证 |
| **证据来源** | `DotA v6.83d.w3x`、`War3Script/war3map.j`、`War3Launcher/versions/*/game.dll` |
| **配套思维导图** | [`dota-6.83d-eat-and-cut-tree-reverse-mindmap.md`](./dota-6.83d-eat-and-cut-tree-reverse-mindmap.md) |

---

## 一、核心结论摘要

1. **吃树与砍树在 DotA 6.83d 与 War3 引擎底层完全同源**：
   - **普通吃树**（背包真码 `I05C`）挂接原生技能 `Aeat`；**分享吃树**（背包真码 `I0Q6` / `I0Q9`）挂接自定义技能 `A2VG`；**压制之刃 / 补刀斧**（近战 `I0HR` / 远程 `I0HP`）挂接自定义技能 `A1FD`（`Tree Chop`）。
   - 三者（`Aeat`、`A2VG`、`A1FD`）的引擎基技能全部为 **`Aeat`**（C++ 类 `CAbilityEatTree`，指令串 `"eattree"` = `0x000D00B2`）。
   - **DotA 6.83d 狂战斧（`I099`）没有主动砍树技能**（`abilList=A05A,A0IO,ACce,A09T`、`usable` 为空；狂战斧加砍树是 DotA 6.84 引入）。
2. **动作包与目标标识完全明确（Action `0x12`，31 字节）**：
   - 玩家通过物品栏使用吃树/补刀斧时，不直接发送 `0xD00B2`，而是发送 **Action `0x12` + `orderId = 0x000D0028 + slot`（`useslot1..6`）**，携带 `(target.x, target.y)` 和树木的 64 位网络对象 ID `*(uint32_t*)(CDestructable* + 0x0C)` / `*(uint32_t*)(CDestructable* + 0x10)`，与已有 `aiOrderTarget` 字节格式逐字节一致。
   - 若英雄与目标树距离超出施法距离（吃树 `100`，补刀斧 `350`），引擎 `COrderTarget` 会自动寻路靠近到施法距离后再执行 `CAbilityEatTree`。
3. **为什么不能用 Hook `CreateDestructable` 找地图树**：
   - `DotA v6.83d.w3x` 的正常地图树木全部预放置在 **`war3map.doo`** 中（共 5198 个装饰/可破坏物，其中符合 DotA `RJI` 树木谓词的 **3675 棵**：`ATtr` 2061 + `NTtw` 1551 + `NTtc` 63），由 `game.dll` 读图时在 C++ 层直接生成，不经过 JASS `CreateDestructable`。
   - 正确做法：在游戏主线程只读调用 `game.dll` 内部与 JASS `EnumDestructablesInRect` 完全同构的 **`EnumWidgetsInRect`**（空间四叉树区域查询，`mask = 0x04FB0000`），配合 `CDestructable` 虚表及 **`GetWidgetWorldPos`** 瞬时枚举英雄附近任意存活树木。

---

## 二、DotA 6.83d 地图数据与脚本逆向证据

### 1. 物品数据（`Units\ItemData.slk` / `Units\ItemStrings.txt` / `War3Script/war3map.j`）

| 物品类型 | 商店售卖码 / 缩写 | Powerup 购买壳 | 背包可用真码（实际带技能） | 静音/无主变体（不可用） | 可用技能 / 充能 / 冷却 / 价格 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **普通吃树 (Tango)** | `h02A` (`tango`) | `I057` | **`I05C`** | `I0Q8` (`abilList=_`) | `abilList=Aeat`, `uses=4`, `perishable=1`, CD=0, 125g |
| **分享吃树 (Shared Tango)** | — | `I0Q7` | **`I0Q6`**, **`I0Q9`** | — | `abilList=A2VG`, `uses=1`, `perishable=1`, CD=60s |
| **压制之刃（近战）** | `h07W`, `h08F` (`qb`) | `I0HT` | **`I0HR`** | `I0HV` (`abilList=_`) | `abilList=A1FD,A1AB`, `usable=1`, CD=5s, 225g |
| **压制之刃（远程）** | —（捡起时自动转换） | `I0HU` | **`I0HP`** | `I0HW` (`abilList=_`) | `abilList=A1FD,A1AD`, `usable=1`, CD=5s, 225g |
| **狂战斧 (Battle Fury)** | `h033` | `I09A` | `I099` | `I02B` | `abilList=A05A,A0IO,ACce,A09T`（无砍树技能） |

### 2. 技能参数（`Units\AbilityData.slk` / `Units\NightElfAbilityFunc.txt`）

| 技能 ID | 基类 (`code`) | 显示名称 | `Order`（十六进制 / 十进制） | `Rng1` | `Cool1` | `targs1` | 效果说明 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `Aeat` | `Aeat` | Eat Tree | `eattree` (`0xD00B2` / `852146`) | `100` | `0` | `air,friend,ground,hero,tree` | 吞树触发 `XGO`→`XFO`；对友方英雄触发 `UnitAddItemById(target, 'I0Q6')` |
| `A2VG` | `Aeat` | Eat Tree | `eattree` (`0xD00B2` / `852146`) | `100` | `60` | `tree` | 仅可吃树（不可再分享） |
| `A1FD` | `Aeat` | Tree Chop | `eattree` (`0xD00B2` / `852146`) | `350` | `5` | `tree,ward` | 砍树由引擎执行；对守卫单位（`o004`/`oeye`）由 `MFO` 补 100 点伤害 |
| `A1ZL` / `A1ZM` | `Aeat` | 堕落者 | `eattree` (`0xD00B2` / `852146`) | `100` | `30` | `tree` | 脚本 `MUO`（L22232）在倒树位置招 15 秒马甲单位（非吃树/补刀斧物品） |

### 3. JASS 触发流程（`D:\Qt\workspace\War3Script\war3map.j`）

1. **吃树回血与分享（`XGO`/`XFO`/`XEO`，L19762–L19810）**：
   - `XGO` 监听 `GetSpellAbilityId() == 'Aeat' || 'A2VG'`：
     - 若 `GetSpellTargetDestructable() != null`：当英雄尚未挂有吃树状态（hashtable key `4255 != 1`）时调用 `XFO()`；若已在吃树期间再吃一颗，`XEO` 捕获 `EVENT_UNIT_SPELL_EFFECT` 后把剩余 tick 重置为 `16`。
     - `XFO()` 给英雄添加隐形光环 `'A0PV'`（Buff `'B07L'`），创建 `1s` 周期定时器触发 `XEO`，每次恢复 `115 / 16` HP，共 16 次（16 秒 115 HP）。
     - **脚本中不调用 `KillDestructable`**，树木倒下完全由引擎 `CAbilityEatTree` 完成。
     - 若 `GetSpellTargetUnit() != null`：调用 `UnitAddItemById(GetSpellTargetUnit(), 'I0Q6')` 分享 1 颗吃树。
2. **补刀斧对树与对眼（`MFO`/`MEO`，L22033–L22044）**：
   - `MFO` 仅当 `GetSpellAbilityId() == 'A1FD'` 且 `GetSpellTargetUnit()` 为 `'o004'`（侦察守卫）或 `'oeye'`（岗哨守卫）时对敌方守卫造成 100 点伤害；若目标是树（可破坏物），脚本不做额外处理，由引擎直接砍倒。
3. **树木合法类型集合 `RJI`（L3699–L3701）与树木重生 `AA2`/`AB2`（L28515–L28527）**：
   - `RJI(destructable d)` 识别且仅识别 6 个树木 FourCC：
     - `'NTtc'`（`0x4E547463`）、`'NTtw'`（`0x4E547477`）、`'ATtr'`（`0x41547472`）、`'B002'`（`0x42303032`）、`'B003'`（`0x42303033`）、`'B005'`（`0x42303035`，先知发芽树）。
   - `AB2` 每 5 分钟通过 `EnumDestructablesInRectAll(bj_mapInitialPlayableArea, function AA2)` 复活 `GetDestructableLife < 1`（且非 `B002`/`B003`、且树根无英雄）的树木。

---

## 三、`game.dll` 引擎实现逆向证据

### 1. `CAbilityEatTree` 砍树/吃树执行链（以 1.26.0.6401 为基准，1.27 对照验证）

- **RTTI vtable**：`1.26` `0x8A858C`；`1.27` `0xA23CB8`。
- `vtable[194]`（`+0x308`，`1.26` `0x0BEA00`）：`mov eax, 0xD00B2; ret`，返回原生命令 ID `"eattree"`。
- `vtable[264]`（`+0x420`，`1.26` `0x08B0E0`）核心指令流程：
  1. 获取目标可破坏物对象 `edi`（`[esp+0Ch]`）；
  2. 通过拥有者单位触发 JASS `EVENT_UNIT_SPELL_EFFECT`（`call 6F053040` → DotA 脚本里的 `XGO` 就在这一步执行）；
  3. 调用 `CDestructable::vtable[+0x124](target, &0.0f)`（`1.26` `0x26B100`；与 JASS `KillDestructable` 在 `0x3C5C13` 调的虚槽完全一致）将树木生命值归零杀死；
  4. 调用 `CDestructable::vtable[+0x8C](9, 0, 1)` 播放倒下（death）动画并恢复树桩状态。

### 2. 网络动作包 `0x12` 打包与校验（`CNetCommandUnitOrderTargetImage`）

- 1.26 `CNetCommandUnitOrderTargetImage` 虚表 `0x932CA8`，打包点 `0x2CBB0A..0x2CBC00`：
  - 报文总长 **31 字节**：

| 偏移 | 长度 | 字段名 | 吃树/砍树时的实际值 |
| :--- | :--- | :--- | :--- |
| `+0x00` | 1B | Action ID | `0x12` |
| `+0x01` | 2B | `flags` | `0x0000` |
| `+0x03` | 4B | `orderId` | `0x000D0028 + slot`（`useslot1..6`，`slot ∈ [0, 5]`） |
| `+0x07` | 8B | `itemNetObjId` | `0xFFFFFFFF, 0xFFFFFFFF`（槽位命令不依赖物品网络 ID，引擎在 `0x0F1920` 反查对应格物品） |
| `+0x0F` | 4B | `targetX` (`float`) | 树木世界坐标 X |
| `+0x13` | 4B | `targetY` (`float`) | 树木世界坐标 Y |
| `+0x17` | 4B | `targetObjId1` | `*(uint32_t *)((char *)CDestructable + 0x0C)` |
| `+0x1B` | 4B | `targetObjId2` | `*(uint32_t *)((char *)CDestructable + 0x10)` |

- 实证结论：这与 `war3hook_ai.cpp` 中已有函数 `aiOrderTarget(orderId, tx, ty, obj1, obj2)` 的 31 字节包布局**完全一致**，因此可直接复用现有 `EnqueuePlayerAction` 管道。

### 3. `CDestructable` 对象结构与虚表槽位（1.20–1.27 全版本一致）

| 成员 / 虚槽 | 含义 | 依据（`game.dll` 反汇编） |
| :--- | :--- | :--- |
| `+0x0C` / `+0x10` | 64 位网络对象 ID (`obj1`, `obj2`) | `CNetCommandUnitOrderTargetImage` `0x2CBB6A..0x2CBB7A` 直接读取 `[esi+0Ch]` / `[esi+10h]` |
| `+0x20` | 标志位（bit 4 可见性 / bit 13 标记等） | `CDestructable` 虚表 `+0x10C..+0x120` |
| `+0x30` | 可破坏物 FourCC 类型 ID | `GetDestructableTypeId`：`mov eax, [eax+30h]`（1.21 `0x2BFBE8` / 1.26 `0x3C47BE` / 1.27 `0x1E2041`） |
| `+0x64` / `+0x6C` | 当前生命值 (`float`) / 最大生命值 (`float`) | `CDestructable` 虚表 `+0x12C`（`mov ecx, [ecx+64h]`）与 `+0x130`（`mov ecx, [ecx+6Ch]`） |
| `+0x70` | 内嵌 `CWidgetPos` 位置对象 | `CDestructable` 虚表 `+0xB8`：`lea eax, [ecx+70h]; ret`（1.26 `0x267240` / 1.27 `0x6A44C0`） |
| `vtable[+0x1C]()` | 类标识（RTTI ClassID） | 所有版本 `CDestructable` 返回常数 **`0x2B773364`**（`'+w3d'`；1.21 `0x1897A0` / 1.26 `0x266160` / 1.27 `0x6A4440`） |
| `vtable[+0xB8]()` | 返回 `CWidgetPos*`（供 `GetWidgetWorldPos` 读取 X/Y） | `GetDestructableX` / `GetDestructableY` |
| `vtable[+0x12C](float *out)` | 读取当前生命值 `life` | `GetDestructableLife` |
| `vtable[+0x13C]()` | 判定是否已死亡（`life <= 0.0f` 返回 1，否则 0） | `GetDestructableLife` 先调 `[+0x13C]`，非 0 则返回 `0.0f` |

### 4. 只读空间枚举函数签名与全 11 版本 RVA 对照表

- **`EnumWidgetsInRect`**（从 `EnumDestructablesInRect` 内部定位，全版本特征调用）：
  ```cpp
  // 协议：__fastcall，4 个栈上参数（callee ret 10h）
  // mask = 0x04FB0000（四叉树层位掩码，全版本一致），cb 返回 1 表示继续枚举
  typedef void (__fastcall *GameEnumWidgetsInRectFn)(
      const float rect[4], // { minX, minY, maxX, maxY }
      uint32_t mask,       // 0x04FB0000u
      uint32_t zero1,      // 0
      uint32_t zero2,      // 0
      int (__fastcall *cb)(void *widget, void *userData),
      void *userData);
  ```
- **`GetWidgetWorldPos`**（从 `GetDestructableX` 内部定位，与 `CDestructable::vtable[+0xB8]` 配合）：
  ```cpp
  // 协议：__thiscall，1 个栈上参数（callee ret 4），写入 xyz[3] 世界坐标
  typedef void *(__thiscall *GameGetWidgetWorldPosFn)(void *posObj, float outXYZ[3]);
  ```
- **全 11 版本 `game.dll` RVA 表**（已通过 `D:\Qt\workspace\War3Launcher\versions\*\game.dll` 扫描并交叉比对 `1.21` / `1.26` / `1.27` 汇编指令证实）：

| `game.dll` 版本 | `EnumWidgetsInRect` | `GetWidgetWorldPos` | `EnumDestructablesInRect` (JASS) | `GetDestructableX` (JASS) | `GetDestructableLife` (JASS) | `GetDestructableTypeId` (JASS) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `1.0.17.5988` | `0x081600` | `0x089530` | `0x2BCF40` | `0x2BC510` | `0x2BC8C0` | `0x2BC430` |
| `1.0.20.6048` | `0x081600` | `0x089530` | `0x2BCF40` | `0x2BC510` | `0x2BC8C0` | `0x2BC430` |
| `1.20.4.6074` | `0x081600` | `0x089530` | `0x2BD060` | `0x2BC630` | `0x2BC9E0` | `0x2BC550` |
| `1.21.0.6263` | `0x081600` | `0x089530` | `0x2C0630` | `0x2BFC00` | `0x2BFFB0` | `0x2BFB20` |
| `1.22.0.6328` | `0x459740` | `0x464710` | `0x3BDD30` | `0x3BDA70` | `0x3BDB30` | `0x3BDA50` |
| `1.23.0.6352` | `0x45B4D0` | `0x4664A0` | `0x3BFA50` | `0x3BF790` | `0x3BF850` | `0x3BF770` |
| `1.24.1.6374` | `0x469E60` | `0x474E30` | `0x3C5510` | `0x3C5250` | `0x3C5310` | `0x3C5230` |
| `1.24.4.6387` | `0x469EE0` | `0x474EB0` | `0x3C55D0` | `0x3C5310` | `0x3C53D0` | `0x3C52F0` |
| `1.25.1.6397` | `0x4691A0` | `0x474170` | `0x3C4860` | `0x3C45A0` | `0x3C4660` | `0x3C4580` |
| `1.26.0.6401` | `0x4693D0` | `0x4743A0` | `0x3C4A90` | `0x3C47D0` | `0x3C4890` | `0x3C47B0` |
| `1.27.0.52240` | `0x02F3F0` | `0x03B720` | `0x1E0140` | `0x1E2050` | `0x1E1F70` | `0x1E2030` |

> [!NOTE]
> `EnumWidgetsInRect` 内部走只读空间网格扫描（先归一化 rect，再逐格遍历节点并调用用户回调），不会分配 JASS 句柄（`JassHandleTable` 无变更）、不改游戏状态，完全无同步（desync）风险。为确保极端安全，仍只在 `g_sceneState == SceneState::GamePlaying` 的游戏主线程 `aiTick` 上下文中调用，并包裹 SEH 保护。

---

## 四、`War3Launcher` AI 接口设计

### 1. 共享 IPC 协议（`War3Launcher/shared/SharedMemory.h`）

在 `AiUnitCommand` 枚举末尾追加（不重排已有枚举值）：
- `AI_UNIT_CMD_DUMP_TREES`：扫描指定半径内树木/可破坏物并写入 `logs\AiUnit.log`（`target`: `0`=仅 RJI 存活树，`1`=含倒下树，`2`=全部可破坏物；`p3`=半径）。
- `AI_UNIT_CMD_EAT_TREE`：吃树（优先分享吃树 `I0Q6`/`I0Q9`，其次普通吃树 `I05C`）。
- `AI_UNIT_CMD_CUT_TREE`：砍树（压制之刃/补刀斧 `I0HR`/`I0HP`；`fallback` 开启时若无斧或冷却中则回退吃树）。
- `AI_UNIT_CMD_SHARE_TREE`：**左击吃树给队友 1 颗共享吃树**（仅限普通吃树 `I05C` → 发送 `0x12 useslot` 指向友方英雄 `(tx, ty, obj1, obj2)` → 地图触发器 `XGO` 生成 1 颗 `I0Q6` 给队友，60s 共享 CD）。
- `AI_UNIT_CMD_INV` (`AI_INV_GIVE`)：**右击/拖放把整组吃树交给队友**（发送 39 字节 `Action 0x13` + `0xD0021 dropitem` + 队友 `targetObj` + 物品 `CItem (obj1, obj2)`）。

配套枚举 `AiTreeSelectMode`：
- `AI_TREE_SELECT_NEAREST = 0`：英雄周围 `p3` 半径内最近存活树；
- `AI_TREE_SELECT_NEAR_POINT = 1`：点 `(x, y)` 周围 `p3` 半径内最近存活树；
- `AI_TREE_SELECT_BY_OBJID = 2`：按 `CDestructable` 网络对象 ID 匹配（`aux = obj1`，可选 `p1 == 1.0f` 时 `p2` 位模式为 `obj2`）。

### 2. Hook 层实现（`war3hook_ai.cpp` + `war3hook_ai_tactics.inl`）

- 新增原生解析：`AI_NATIVE_GET_ITEM_CHARGES`（`"GetItemCharges"`），顺带在背包日志中显示吃树剩余层数。
- 新增物品标签与冷却：
  - `AI_ITEM_TANGO`（`I05C`，300ms 防连发）；
  - `AI_ITEM_TANGO_SHARED`（`I0Q6`、`I0Q9`，60200ms）；
  - 修正 `AI_ITEM_QUELLING`（`I0HR`、`I0HP`，冷却修正为 `5200ms`，移除购买壳 `I0HT`/`I0HU`）。
- 核心原语：
  - `aiScanTreesAround(cx, cy, radius, out, includeDead, includeAllDestructables)`
  - `aiUseItemOnDestructable(slot, tag, tree, heroDist, now)`（发送 `aiSelectHero()` + `0x12` + `useslot`）
  - `aiExecEatTree(p, now)` / `aiExecCutTree(p, now)` / `aiExecShareTree(p, now)` / `aiExecInv(p, now)`
  - `aiOrderDropItem(...)`（39 字节 `Action 0x13` `dropitem`）与 `aiResolveItemObjectIds(...)`（通过 `JassHandleToItem` 解析 `CItem +0x0C/+0x10`）

### 3. 对外控制接口（`War3Server` + `War3Launcher` 全链路）

| 调用入口 | 查询附近树木 | 吃树 (Tango) | 分享 1 颗 / 给整组树 | 砍树 (Quelling Blade) |
| :--- | :--- | :--- | :--- | :--- |
| **C++ `Q_INVOKABLE`** | `dumpTrees(radius, mode)` | `eatTree(radius)` / `eatTreeAt(x, y, radius)` | `shareTree(handle, r)` / `giveTree(handle)` | `cutTree(radius, allowFallback)` / `cutTreeAt(x, y, radius, allowFallback)` |
| **RemoteControl (TCP 6120)** | `tree list [all\|dead] [r]`（别名 `trees`） | `tree eat [x y [r] \| 0x<obj1> \| r]`（别名 `eattree\|tango`） | `tree share [ally\|0x<句柄>]` / `tree give [ally\|0x<句柄>]` | `tree cut [x y [r] \| 0x<obj1> \| r] [fallback]`（别名 `cuttree\|quell\|chop`） |
| **PowerShell CLI** | `.\scripts\ai_control.ps1 tree -- list 800` | `.\scripts\ai_control.ps1 tree -- eat` | `.\scripts\ai_control.ps1 tree -- share` / `give` | `.\scripts\ai_control.ps1 tree -- cut fallback` |
| **游戏内 / 大厅聊天指令** | `-tree list` / `/tree list`（`/trees`、`trees <参数>`；裸 `-trees` 保留给 DotA `-test` 重生树木） | `-tree eat` / `/tree eat`（兼容 `-eattree\|-tango`） | `-tree share [ally\|0x<句柄>]`（1 颗）/ `-tree give [ally\|0x<句柄>]`（整组） | `-tree cut [fallback]` / `/tree cut [fallback]`（兼容 `-cuttree\|-quell\|-chop`） |

> [!NOTE]
> **全链路命令路由说明（`War3Server` + `War3Launcher`）**：
> - **`War3Server` (`src/bnetd/command.cpp` + `conf/command_groups.conf.in`)**：在 `standard_command_table[]` 与 Group `1` 中注册 `/tree`、`-tree`、`/trees`、`-trees`、`/eattree`、`-eattree`、`/tango`、`-tango`、`/cuttree`、`-cuttree`、`/quell`、`-quell`、`/chop`、`-chop`，通过 `_handle_bot_proxy_logic` 回显给发送者自身（避免 `Unknown command.` 或权限组禁用提示），并在游戏内保留**裸 `-trees`** 给 DotA 6.83d `-test` 原生重生树木命令。
> - **`War3Launcher` (`hooker/war3hook_process.cpp` + `war3hook_ai.cpp` + `managers/NetworkManager.cpp`)**：`isTargetBotCommand` / `isCommand` 白名单放行并转发相关命令；游戏内聊天由 `war3hook_ai.cpp::handleAttackCommand` 拦截解析（支持 `cut`/`chop`/`quell`、`eat`/`tango`、`list`/`scan`/`dump`）；启动器聊天框由 `NetworkManager::handleChatCommand` 直接转为 `MSG_TYPE_AI_UNIT_COMMAND` IPC。

---

## 五、后续可复现联调与验证步骤

1. 编译并同步到 `C:\War3Run`（`scripts\Sync-War3Run.ps1 -Build -Component Launcher -StopRunning`），并编译部署 `War3Server` (`bnetd.exe`) 到 `D:\War3Server`。
2. 启动开局（`Scripts\Start-AiGame.ps1 -Hero cm` 或 `-Hero am`）。
3. 进入对局后通过 `ai_control.ps1` 或游戏内 `-tree` / `/tree` 验证：
   - `.\scripts\ai_control.ps1 tree -- list 800`（或游戏内 `-tree list 800` / `/tree list 800`）→ 检查 `C:\War3Run\War3Launcher\logs\AiUnit.log` 是否输出附近 `ATtr`/`NTtw`/`NTtc` 坐标与 `obj1:obj2`；
   - `.\scripts\ai_control.ps1 buy -- tango` → `.\scripts\ai_control.ps1 tree -- eat`（或 `-tree eat` / `/tree eat`）→ 核对 `AiUnit.log` 发送 `0xD0028+slot`、`uses` 减 1、目标树倒下并获得回血；
   - `.\scripts\ai_control.ps1 buy -- qb` → `.\scripts\ai_control.ps1 tree -- cut`（或 `-tree cut` / `/tree cut`）→ 核对 `AiUnit.log` 发送砍树、目标树在 350 码内直接倒下、进入 5s 冷却计时。

