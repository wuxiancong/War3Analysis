# DotA 6.83d 吃大药、吃净化药水及全部主动物品机制逆向与命令设计

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Antigravity AI Agent |
| **分析目的** | 逆向 DotA v6.83d 吃大药（治疗药膏）、吃净化药水及全部主动物品在地图脚本（SLK/JASS）与 War3 引擎 `game.dll` 中的底层实现，厘清各类主动物品的协议差异，并建立统一的 AI 命令区分规范 |
| **命名方式** | `dota-6.83d-active-items-and-consumables-reverse`；建议统一主动使用命令 `-use` / `/use`（别名 `-item` / `/item`），配合 `-items`、`-tree`、`-buy` 使用 |
| **分析时间** | 2026-11-19 |
| **验证状态** | 静态逆向 100% 完成（`DotA v6.83d.w3x` SLK/TXT、`War3x.mpq`/`War3Patch.mpq` 对照、`War3Script/war3map.j` 触发器、11 版本 `game.dll` RVA 与反汇编验证）；实机发包联调待后续 `-use`/`-items` 编码后验证 |
| **证据来源** | `DotA v6.83d.w3x`、`War3x.mpq`、`War3Patch.mpq`、`D:\Qt\workspace\War3Script\war3map.j`、`D:\Qt\workspace\War3Launcher\versions\*\game.dll`、`D:\Qt\workspace\War3Analysis\artifacts\ability-orders\orders-1.27.json` |
| **配套思维导图** | [`dota-6.83d-active-items-and-consumables-reverse-mindmap.md`](./dota-6.83d-active-items-and-consumables-reverse-mindmap.md) |

---

## 一、核心结论置顶

1. **所有主动物品的激活操作都属于同一个引擎入口（`useslot1..6`）**：
   - 在 `game.dll` 中，所有背包主动使用操作统一由 **`CAbility::GetItemSlotOrderId()`** 读取物品技能所属栏位偏移 `[this + 0xAC] + 0x000D0028` 生成 **`useslot1..6`（`0x000D0028` ~ `0x000D002D`）**，协议层上**不再区分**具体是哪件物品技能的四字符码（FourCC）。
   - 真正决定发送 **`Action 0x10`（无目标 15B）**、**`Action 0x11`（点地 23B）** 还是 **`Action 0x12`（目标对象 31B）**，以及**是否打断当前移动/攻击/施法**的，是物品首个主动技能虚表槽 **`vtable[+0x30C]`（`GetOrderFlags()`）** 返回的标志位：
     - 低 4 位 `0x1` → **无目标（`Action 0x10`）**；
     - 低 4 位 `0x2` → **点地（`Action 0x11`）**；
     - 低 4 位 `0x4` → **目标对象（`Action 0x12`，单位 / 树木 / 物品）**；
     - 低 4 位 `0x6`（`= 0x2 | 0x4`）→ **点地或目标双模式（`Action 0x11` 或 `Action 0x12`）**；
     - 高位 **`0x02000000`** → **瞬发不打断标志**（开启/切换时不打断移动、攻击、隐身或持续施法，如臂章、希瓦、隐刀、战鼓类同源基类等）。
2. **吃大药与吃净化药水在引擎层与脚本层 100% 同源，但走 `Action 0x12` 单位目标**：
   - 二者与有水魔瓶共用同一个 C++ 类 **`CAbilityRegeneration`（`AIrg`）**（`+0x308` 订单 ID 固定返回 `0x000D0281` / `852609`）。
   - War3 原版对战中的 `AIpr`（药膏）与 `AIpl`（小净瓶）配置了 `DataD1 = 1`（无目标），而 DotA 6.83d 将大药（`I05F` / `AIpr`）和净化药水（`I05D` / `AIpl`）的 **`DataD1`（`irl4`「没有目标要求」）改成 `0`**。
   - 反汇编 `CAbilityRegeneration::GetOrderFlags()`（`1.26` `0x10BE00` / `1.27` `0x526DC0`）证实：当 `DataD1 == 0.0f` 时返回 **`0x00300004`**（必须走 **`Action 0x12` 目标包**，可对自己或友方英雄使用）；有水魔瓶（`A0FO`）保留 `DataD1 = 1`，返回 **`0x00200001`**（走 **`Action 0x10` 无目标**）。
   - DotA 同时把 `item` 加进 `AIpr`/`AIpl` 的 `targs1` 中，使玩家双击物品本身时发出 `GetSpellTargetUnit() == null` 的 `0x12` 施法事件，由 JASS **`N2O`（L22316–22339）** 用马甲 `'e00E'` 对自己施放回复效果；AI 直接用 **`0x12` 指向目标英雄句柄** 即可，无需模拟双击。
3. **四组重点装备对比速查表**：

| 对比组 | 是否完全同逻辑？ | 核心差异与发包外壳 |
| :--- | :--- | :--- |
| **跳刀 / 隐刀 / 推推棒** | **不同**（外壳全不同） | 跳刀 `AEbl` → **`0x11` 点地**；隐刀 `AOwk` → **`0x10` 无目标（瞬发 `0x02000001`）**；推推棒 `ANcl(B=1)` → **`0x12` 单位目标**（支持友/敌/己）。 |
| **切换假腿 vs 切换臂章** | **主流程相同，C++ 标志有别** | 二者都是 **`0x10` 无目标 + JASS `RemoveItem` + `FD1` 原位换格更换 FourCC**（假腿 `NZO` 3 态轮转；臂章 `NJO` 开关 2 态互换）。区别：假腿用 `AEfk`（`0x00200001` 常规瞬发），臂章用 `AIam`（**`0x02000001` 瞬发不打断**，可在移动/隐身/平 A 间隙无损切）。 |
| **笛子 vs 梅肯** | **AI 发包完全相同** | 二者均走 **`0x10` + `0x00200001`**，无需目标，范围由地图脚本/引擎决定（笛子 `AEfk` + `YTO` 925 码魔抗盾；梅肯 `AIda` +2 甲 + `YYO` 775 码回 250 HP）。 |
| **赤红甲 / 希瓦 / BKB** | **均走 `0x10`，瞬发打断标志不同** | 协议都是 **`0x10` 无目标**，但基类不同：赤红甲 `AEfk`（`0x00200001`，`YMO` 775 码套格挡盾）；**希瓦 `AIam`（`0x02000001` 瞬发不打断动作/引导）**；BKB `AHwe`（`0x00300001`，`YVO` 挂 `'A0FY'` 魔免且 `NYO` 自动按 10→4 秒原位降级 FourCC）。 |

---

## 二、吃大药（Healing Salve）与吃净化药水（Clarity Potion）深度逆向

### 1. DotA 6.83d 物编 / 技能配置（与原版 War3 对比）

从 `DotA v6.83d.w3x` 的 `Units\ItemData.slk`、`Units\AbilityData.slk` 与 `War3x.mpq`/`War3Patch.mpq` 对比提取：

| 样本 / 物品 | 商店假单位 | 背包真码 | 技能 ID | 基类 `code` | `DataD1` (`irl4`) | 回复参数 | 可用目标 `targs1` | 底层结果 |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :--- |
| **原版药膏 (`War3x`)** | — | `hslv` | `AIpr`/`AIrl` | `AIrg` | **`1`** | 400 HP / 45s | 友方有机单位 | 无目标对自己喝（`0x10`） |
| **原版小净瓶 (`War3x`)** | — | `plcl` | `AIpl` | `AIrg` | **`1`** | 100 MP / 30s | 友方有机单位 | 无目标对自己喝（`0x10`） |
| **DotA 吃大药 (`Salve`)** | `h029` (110g) | **`I05F`** | **`AIpr`** | `AIrg` | **`0`** | `DataA1=400`, `Dur1=10` (40/s) | `air,friend,ground,invulnerable,item,neutral,organic,self,vulnerable` | **必须选目标 (`0x12`)**；`DataC1=3` 满血可用；`DataE1=1` 受击驱散 |
| **DotA 吃小蓝 (`Clarity`)** | `h028` (50g) | **`I05D`** | **`AIpl`** | `AIrg` | **`0`** | `DataB1=150`, `Dur1=40` (3.75/s) | 同上 | **必须选目标 (`0x12`)**；`DataC1=3` 满蓝可用；`DataE1=1` 受击驱散 |
| **DotA 马甲小蓝（双击自施）** | — | — | **`A1WA`** | `AIrg` | **`0`** | `DataB1=150`, `Dur1=40` | 同上（`BuffID1=BIrg,B02Z`） | 由 `'e00E'` 马甲对施法者发 order `852609` |
| **DotA 有水魔瓶 (`Bottle`)** | `h02B` (700g) | `I0AN`/`I0AO`/`I0AP` | **`A0FO`** | `AIrg` | **`1`** | `DataA1=135`, `DataB1=70`, `Dur1=3` | `air,ground,friend,vuln,invu,self,organic,neutral` | **无目标 (`0x10`)**，对自己立刻生效（`Cool1=0.5s`） |

`AbilityMetaData.slk` + `WorldEditStrings.txt` 对 `AIrg` 系列字段的官方定义：
- `irl1` (`DataA1`) = **生命回复**
- `irl2` (`DataB1`) = **魔法回复**
- `irl3` (`DataC1`) = **完整时可用**（位 1 允许满血用，位 2 允许满蓝用；`3` = 满血满蓝均可使用）
- `irl4` (`DataD1`) = **没有目标要求**（boolean：`1` = No Target，`0` = Target Unit）
- `irl5` (`DataE1`) = **进攻的同时驱散**（受到玩家/敌方伤害或攻击触发驱散）

### 2. `game.dll` 内 `CAbilityRegeneration::GetOrderFlags()` 汇编实证

`CAbilityRegeneration` 在 `1.26.0.6401` 的虚表 RVA 为 `0x8CAC04`（`1.27.0.52240` 为 `0x9FA65C`）：
- `vtable[+0x308]`（`GetOrderId()`）：
  - `1.26` `0x10BDF0` / `1.27` `0x545300`：`mov eax, 000D0281h; ret`（即十进制 `852609`，`useslot` 反查内部转换时仍依托物品技能的 `Order` 属性）。
- `vtable[+0x30C]`（`GetOrderFlags()`）：

```asm
; 1.26.0.6401 @ 0x6F10BE00 (RVA 0x10BE00)
6F10BE00: push ecx
6F10BE01: mov  eax, dword ptr [ecx+50h]   ; 取当前技能等级参数块
6F10BE04: push eax
6F10BE05: lea  eax, [esp+4]
6F10BE09: push eax
6F10BE0A: call 6F02EB30                   ; 读取 DataD1 (irl4 = 没有目标要求) float
6F10BE0F: fld  dword ptr [eax]
6F10BE11: fld  dword ptr ds:[6FAAE470h]   ; 常量 0.0f
6F10BE17: fucompp
...
6F10BE1E: mov  eax, 200001h               ; DataD1 != 0.0f → 无目标标志 0x00200001 (Action 0x10)
6F10BE23: jp   6F10BE2A
6F10BE25: mov  eax, 300004h               ; DataD1 == 0.0f → 目标对象标志 0x00300004 (Action 0x12)
6F10BE2A: pop  ecx
6F10BE2B: ret
```

`1.27.0.52240 @ 0x6F526DC0 (RVA 0x526DC0)` 逻辑完全一致，仅浮点指令升级为 `movss xmm0, [eax]; ucomiss xmm0, ds:[6FBB81D4h]`，同样在 `0x00200001` 与 `0x00300004` 之间二选一。

### 3. DotA 6.83d 脚本双击自施路径（`War3Script/war3map.j` `N2O`/`N3O` L22316–22339）

DotA 玩家习惯按两下大药/小蓝给自己贴药膏，这并非引擎原生支持，而是 **DotA 物编 + JASS 触发器协作** 的结果：
1. 物编 `targs1` 里加入了 `item`。当玩家先按药水快捷键再左键点自己物品栏里的同一格时，客户端向服务端发出 **`Action 0x12`**，目标网络对象为该 `item` 句柄。
2. 引擎触发 `EVENT_UNIT_SPELL_EFFECT` 后，因为目标不是单位，`GetSpellTargetUnit()` 返回 `null`。
3. **`N3O()` → `N2O()`**（L22316–22335）捕获 `'AIpl'`（`1095331948`）与 `'AIpr'`（`1095331954`）：
   - 当 `GetSpellTargetUnit() == null` 时，在施法者脚下创建隐形马甲单位 `'e00E'`（`1697656901`）；
   - 如果是小蓝 `'AIpl'`，给马甲添加 `'A1WA'`（`1093752641`）；如果是大药 `'AIpr'`，给马甲添加 `'AIpr'`（`1095331954`）；
   - 调用 `IssueTargetOrderById(I01, 852609, SWI)`（`852609 = 0x000D0281`，即 `CAbilityRegeneration` 原生订单号），立即给触发者 `SWI` 挂上回蓝/回血 Buff。

> [!TIP]
> **AI 使用建议**：AI 不需要向物品句柄发双击动作，直接通过 `aiResolveUnitObjectIds(heroOrAlly, &t1, &t2, nullptr)` 取自己或友方英雄的 `obj1/obj2`，构造 31 字节 `Action 0x12 + useslot(0xD0028 + slot)` 即可直接贴给自己或残血/缺蓝队友（贴队友时若超过施法距离，引擎 `COrderTarget` 会先寻路靠近）。使用前注意判断 `g_aiHeroLossRate == 0` 且周围无敌方单位，用后短时间内禁止主动平 A 招小兵仇恨导致药效被打断。

---

## 三、War3 引擎「使用物品」统一机制与全 11 版本 RVA 表

### 1. `useslot1..6` 分发机制

- **`CAbility::GetItemSlotOrderId()`**：
  - `1.26.0.6401 @ RVA 0x037860` / `1.27.0.52240 @ RVA 0x400500`：
    ```asm
    test dword ptr [ecx+20h], 20000000h
    je   slot_calc
    mov  eax, 0D0295h
    ret
    slot_calc:
    mov  eax, dword ptr [ecx+0ACh]  ; 物品在 CAbilityInventory 中的槽位索引 0..5
    add  eax, 0D0028h               ; 返回 useslot1..6 (0xD0028..0xD002D)
    ret
    ```
- **`CAbilityInventory` 收到 `0x10`/`0x11`/`0x12` 中的 `0xD0028..0xD002D` 后**：
  - 将 `orderId - 0xD0028` 还原为 `slot ∈ [0, 5]`（如 `1.26 @ 0x0F1951..0x0F1962`：`add eax, 0FFF2FFD8h`），从英雄背包槽取出对应 `CItem`，找到其首个可主动施放的 `CAbility`，由该 `CAbility` 的 `GetOrderFlags()` 决定目标校验及执行。

### 2. 全 11 版本 `game.dll` 关键 RVA 对照表

> 以下偏移均在 `D:\Qt\workspace\War3Launcher\versions\*\game.dll`（11 个版本）实测扫描与反汇编验证：

| `game.dll` 版本 | `CAbility::GetItemSlotOrderId` | `CAbilityRegeneration::GetOrderId (+0x308)` | `CAbilityRegeneration::GetOrderFlags (+0x30C)` | `CAbilityRegeneration` 虚表 RVA | `CAbilityInventory` 虚表 RVA |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | `0x46D660` | `0x585EF0` | `0x585F00` | —（无 RTTI 导出符号） | — |
| `1.0.20.6048` | `0x46DB60` | `0x5863F0` | `0x586400` | — | — |
| `1.20.4.6074` | `0x46E0D0` | `0x586CD0` | `0x586CE0` | — | — |
| `1.21.0.6263` | `0x472000` | `0x58AD90` | `0x58ADA0` | — | — |
| `1.22.0.6328` | `0x036FD0` | `0x10B3A0` | `0x10B3B0` | `0x8B9AEC` | `0x8A5FD4` |
| `1.23.0.6352` | `0x038510` | `0x10C8E0` | `0x10C8F0` | `0x8CDC2C` | `0x8BA114` |
| `1.24.1.6374` | `0x0385C0` | `0x10C990` | `0x10C9A0` | `0x8DCD64` | `0x8C924C` |
| `1.24.4.6387` | `0x0385A0` | `0x10C9A0` | `0x10C9B0` | `0x8DCD64` | `0x8C924C` |
| `1.25.1.6397` | `0x037860` | `0x10BDF0` | `0x10BE00` | `0x8CAC04` | `0x8B70EC` |
| `1.26.0.6401` | `0x037860` | `0x10BDF0` | `0x10BE00` | `0x8CAC04` | `0x8B70EC` |
| `1.27.0.52240` | `0x400500` | `0x545300` | `0x526DC0` | `0x9FA65C` | `0x9FAB6C` |

> 说明：`1.0.17`~`1.21.0` 使用特征字节扫描精确定位了三个函数的代码 RVA，未额外反推虚表地址；`War3Launcher` 发包只发 Action 字节流，**不需要**把这几个分析 RVA 写入 Hook 偏移表。

### 3. 各物品基类的 `GetOrderFlags()`（`vtable[+0x30C]`）分类汇总（`1.26` 实测）

| 物品基类 `code` | C++ RTTI 类名 | `+0x30C` 返回值 | 低 4 位目标掩码 | 是否带瞬发不打断标志 (`0x02000000`) | 对应发包外壳 | DotA 6.83d 代表物品 |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| `AIam` | `CAbilityAttributeMod` | `0x02000001` | `0x1` 无目标 | **是** | `0x10` | 臂章、希瓦的守护 |
| `AOwk` | `CAbilityWindWalk` | `0x02000001` | `0x1` 无目标 | **是** | `0x10` | 洛萨之锋(隐刀)、相位鞋、暗影护符 |
| `Absk` | `CAbilityBerserkerRage` | `0x02000001` | `0x1` 无目标 | **是** | `0x10` | 疯狂面具 |
| `AEfk` | `CAbilityFanOfKnives` | `0x00200001` | `0x1` 无目标 | 否 | `0x10` | 假腿、烟斗、赤红甲、魔棒/杖、魂戒、刃甲、绿杖、王者、天鹰、林肯(被动旧版)、蝴蝶 |
| `AIda` | `CAbilityItemDefenseAoe` | `0x00200001` | `0x1` 无目标 | 否 | `0x10` | 梅肯斯姆、玄冥盾牌 |
| `AImr` | `CAbilityItemManaRestoreAoe` | `0x00200001` | `0x1` 无目标 | 否 | `0x10` | 秘法鞋、先祖韧鼓、诡计之雾 |
| `AItb` | `CAbilityItemDetectByBuff` | `0x00200001` | `0x1` 无目标 | 否 | `0x10` | 显影之尘（注：非点地 `CAbilityItemDetectAoe`） |
| `AIra` | `CAbilityItemRestore` | `0x00200001` | `0x1` 无目标 | 否 | `0x10` | 奶酪 |
| `AIfs` | `CAbilityFigurine` | `0x00200001` | `0x1` 无目标 | 否 | `0x10` | 刷新球、死灵书 1~3 级 |
| `AOmi` | `CAbilityMirrorImage` | `0x00000001` | `0x1` 无目标 | 否 | `0x10` | 幻影斧（近/远） |
| `AHwe` | `CAbilityWaterElemental` | `0x00300001` | `0x1` 无目标 | 否 | `0x10` | 黑皇杖（BKB 10~4s）、动物/飞行信使 |
| `AIrg` | `CAbilityRegeneration` | **动态：`0x00200001` / `0x00300004`** | `DataD1!=0` → `0x1` / `==0` → `0x4` | 否 | `0x10` / `0x12` | 有水魔瓶 (`0x10`) / 大药、净化药水 (`0x12`) |
| `ANcl` | `CAbilityChannel` | **动态：读 `DataB1`**（+ `0x01000000` 若 `DataC1 & 2`） | `0`→`0x1` / `1`→`0x4` / `2`→`0x2` / `3`→`0x6` | 否 | 按 `DataB1` 定 | `0`: 装符魔瓶、金箍棒、辉耀、撒旦；`1`: 推推、羊刀前身除外(风杖/林肯/骨灰/电锤/勋章/支配/阿托斯/虚灵/天堂/空瓶)；`2`: 血精石；`3`: **真眼/假眼 (`0x11` 或 `0x12`)** |
| `AEbl` | `CAbilityBlink` | `0x00100002` | `0x2` 点地 | 否 | `0x11` | 科勒的匕首（跳刀） |
| `ANto` | `CAbilityTornado` | `0x00100002` | `0x2` 点地 | 否 | `0x11` | 回城卷轴（TP）、远行鞋（飞鞋） |
| `AHbz` | `CAbilityBlizzard` | `0x01100002` | `0x2` 点地 | 否 | `0x11` | 纷争面纱 |
| `Aeat` | `CAbilityEatTree` | `0x00108004` | `0x4` 对象目标 | 否 | `0x12` | 吃树、分享吃树、压制之刃（近/远） |
| `Aprg` | `CAbilityPurge` | `0x00108004` | `0x4` 对象目标 | 否 | `0x12` | 净魂之刃 1/2 级 |
| `ANab` / `ANfd` / `ANso` / `AOhx` / `AHtb` / `AIil` | 各类单体目标类 | `0x00100004` | `0x4` 对象目标 | 否 | `0x12` | 迈达斯之手、达贡 1~5、紫怨、羊刀、深渊之刃 |

> [!NOTE]
> 上表中看似返回 `0x100002` 的 **TP / 飞鞋（`ANto`）**：虽然底层 `targs1=_`、`CAbilityTornado::+0x30C = 0x00100002`（走 `Action 0x11` 点地包），但 DotA 地图触发器在收到点地坐标后，会自动寻找该坐标附近最近的友方建筑（或兵/眼，视飞鞋/TP 规则）作为传送锚点。AI 直接发 `0x11 + useslot + (buildingX, buildingY)` 即可，与实测完全一致。

---

## 四、四组重点装备机制对比实证

### 1. 跳刀 vs 隐刀 vs 推推棒 —— 是否同一逻辑？

**结论：在「都是 `useslot1..6`」这一点上同源，但在动作协议、目标校验与使用时机上完全不同。**

| 装备 | FourCC | 首技能 & 基类 | `+0x30C` | 发包协议 | 核心逻辑实证 |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **科勒的匕首（跳刀）** | `I04H` | `AIbk` (`AEbl`) | `0x00100002` | **`0x11` 点地** `(x, y)` | `DataA1=1200`, `DataB1=200`, `Cool1=12`, `Rng1=99999`。无魔法消耗；地图受英雄伤害触发 3s 冷却刷新。超出 1200 码会被引擎缩距至 `960`（`4/5 * 1200`）。 |
| **洛萨之锋（隐刀）** | `I09H` | `A017` (`AOwk`) | `0x02000001` | **`0x10` 无目标（瞬发不打断）** | `Dur1=14`, `Cool1=28`, `Cost1=75`, `DataB1=0.2` (20% 移速), `DataC1=175` (破隐一击), `DataD1=1`。`0x02000000` 使其**可以在移动或持续施法（如 TP）期间直接按出隐身而不打断动作**（TP+隐刀逃生）。 |
| **原力法杖（推推棒）** | `I0HI` | `A19M` (`ANcl`, `B=1`) | `0x00100004` | **`0x12` 目标单位** `(tx, ty, t1, t2)` | `DataB1=1`（Unit Target），`Rng1=800`, `Cool1=20`, `Cost1=25`, `targs1=enemies,friend,ground,item,self`。JASS `K4O`（L21095）检查禁用帮助（`LoadBoolean(..., 139)`）后调用 `K2O` 做 `0.04s` 周期位移推动。注意：**对自己用也必须传自身 `(obj1, obj2)` 走 `0x12`**，不能发 `0x10`。 |

### 2. 切换假腿 vs 切换臂章 —— 是否同一逻辑？

**结论：底层切换机制完全属于同一范式（`0x10 useslot` + JASS 原位删除并替换道具 FourCC），但 `AIam` 与 `AEfk` 的不打断标志与业务状态语义不同。**

- **共同点（原位更换物品 ID）**：
  - 两者都依赖 `FD1(hero, newTypeId, slot)`：先记下原槽位 `FF1 = A11(hero, manipulatedItem)`，关闭触发器 `LY0`，`RemoveItem` 后通过占位塞满其它空槽的方式强制让新物品落回原格 `FF1`。所以 AI 切完假腿或臂章**不需要重排格序**。
- **差异实证**：

| 对比维度 | 动力鞋 / 假腿（Power Treads） | 莫尔迪基安的臂章（Armlet） |
| :--- | :--- | :--- |
| **物编状态与顺序** | **`NZO`（L22598–22634）单向 3 态轮转**：<br>`ZL0 (I02T 敏捷)` → `ZM0 (I05Y 力量)` → `ZN0 (I05Z 智力)` → `ZL0 (I02T 敏捷)` | **`NJO`（L22818–22840）2 态互换**：<br>`WT0 (I00Q 关闭)` ↔ `WS0 (I00M 开启)`（另有 `I00T`/`I00S` 兼容变体） |
| **首技能与基类** | `A14A`（基类 **`AEfk`**），`targs1=air,ground,enemy,organic`, `Area1=1` | `A0T7`（关）/ `A0T8`（开），基类 **`AIam`**，`targs1=_` |
| **`+0x30C` 返回值** | `0x00200001`（无 `0x02000000` 瞬发位） | **`0x02000001`（带 `0x02000000` 瞬发不打断位）** |
| **AI 调用要点** | 想切到目标属性必须先读当前槽位 `GetItemTypeId`（`0/1/2` 次 `0x10`） | 开关只有 2 态；极限残血「切臂章」= 开启状态先发一次关→等 100~150ms→再发一次开 |

> 同属「`0x10 useslot` + JASS 原位换 FourCC」的切换装还有：**王者之戒（`I067`↔`I06A`）**、**天鹰之戒（`I0P1`↔`I0P4`）**、**辉耀（`I0A8`↔`I0KP`）**、**金箍棒真击开关（`I0A5`↔`I0K7`）**。其中王者与天鹰是 `AEfk`（`0x00200001`），辉耀与金箍棒是 `ANcl(B=0)`。

### 3. 笛子 vs 梅肯 —— 是否同一逻辑？

**结论：AI 操作与协议层面 100% 是同一逻辑（均发 `Action 0x10 + useslot`）；内部只是基类与 JASS 副作用不同。**

- **卡德加之洞察烟斗（笛子 `I0K6`）**：
  - 首技能 `A1EW`（基类 `AEfk`，`+0x30C = 0x00200001`，CD `60s`，耗蓝 `100`）。
  - JASS **`YRO` → `YTO`（L20525–20540）**：枚举自身 **`925` 码** 内友方非守卫单位，经马甲 `NA0` 添加 `'A1EV'` 后挨个发 `"antimagicshell"` 套 400 点魔法护盾，并由 `YSO` 检查/记录 **50 秒防叠加标记（key `4278`）**。
- **梅肯斯姆（梅肯 `I093`）**：
  - 首技能 `A0CK`（基类 `AIda` `CAbilityItemDefenseAoe`，`+0x30C = 0x00200001`，CD `45s`，耗蓝 `225`，Area `750` 原生群体 +2 护甲）。
  - JASS **`YJO` → `YYO`（L20449–20462）**：枚举自身 **`775` 码** 内友方单位，经 `YXO` 直接回血 `+250 HP`，并写入 **25 秒防叠加标记（key `4258`）**。

### 4. 赤红甲 vs 希瓦的守护 vs BKB —— 是否同一逻辑？

**结论：三者在发包上均走 `Action 0x10 + useslot` 无目标包，但因引擎基类不同，在「是否瞬发不打断」和「物品降级机制」上有明显区别。**

| 装备 | FourCC | 首技能 & 基类 | `+0x30C` | 关键差异（SLK + `war3map.j` 实证） |
| :--- | :---: | :---: | :---: | :--- |
| **赤红甲 (`Crimson`)** | `I0QY` | `A2YG` (`AEfk`) | `0x00200001` | 无瞬发不打断位；CD `70s`，耗蓝 `0`。JASS **`YNO` → `YMO` → `YLO`（L20476–20512）**：给 `775` 码友方英雄/建筑附加 10 秒近/远程伤害格挡 Buff，并写 **70 秒防叠加标记（key `4346`）**。 |
| **希瓦的守护 (`Shiva`)** | `I00Z` | `A0T9` (`AIam`) | **`0x02000001`** | **带 `0x02000000` 瞬发不打断标志**！可以在 TP 引导、施法或走A过程中无停顿释放；CD `30s`，耗蓝 `100`。JASS **`JEO` → `JCO`（L20766–20792）**：生成扩张冰环并 `0.06s` 定时器对波环内敌人造成 200 伤害与减速。 |
| **黑皇杖 (`BKB`)** | `I0FZ`..`I0P8` | `A11F`..`A2LI` (`AHwe`) | `0x00300001` | 无瞬发不打断位；耗蓝 `0`，CD 按档位 `80→50s` 递减。JASS **`YVO`（L20409–20433）**：给自身加魔法免疫 `'A0FY'`、清负面状态、模型变大（1.4x/3x），同时 **`NYO`（L22762–22817）** 原位依次将 BKB 从 10s (`I0FZ`) 降级到 4s (`I0P8`)。 |

---

## 五、DotA 6.83d 全量主动物品与背包操作分类总表

结合 `DotA v6.83d.w3x` `ItemData.slk` 与 `war3map.j` 商店/合成列表（`FP0`/`JB0`），将所有**玩家实战可获得**的主动物品与背包操作分为 **5 大类**：

### A 类：`Action 0x10` 无目标使用（`useslot1..6`）

#### A1. 瞬发不打断动作类（`GetOrderFlags` 含 `0x02000000`，均为 `0x02000001`）
| 物品 | 背包 FourCC | 技能 / 基类 | CD / 蓝耗 | 说明 |
| :--- | :--- | :--- | :---: | :--- |
| **相位鞋** | `I0GJ` | `A12W` (`AOwk`) | 8s / 0 | 4 秒提速并无视碰撞（`targs1=self`, `DataD1=0`） |
| **洛萨之锋（隐刀）** | `I09H` | `A017` (`AOwk`) | 28s / 75 | 14 秒隐身 +20% 移速 + 175 破隐一击 |
| **暗影护符** | `I0PB` | `A2N1` (`AOwk`) | 0s / 0 | 原地短暂渐变隐身（移动会显形） |
| **疯狂面具** | `I08Y` | `AIxk` (`Absk`) | 25s / 25 | 12 秒攻速移速提升并额外承受 30% 伤害 |
| **希瓦的守护** | `I00Z` | `A0T9` (`AIam`) | 30s / 100 | 极寒冲击扩展冰环（可移动/TP 中释放） |
| **莫尔迪基安的臂章** | `I00Q`↔`I00M` | `A0T7`/`A0T8` (`AIam`) | ~0s / 0 | 开关态原位切换（+力量/攻击但每秒掉血） |

#### A2. 常规无目标消耗 / 团队增益 / 召唤 / 变身类（无 `0x02000000`）
| 物品 | 背包 FourCC | 技能 / 基类 | Flags | CD / 蓝耗 | 说明 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **魔瓶（有水 1~3 充）** | `I0AN`/`I0AO`/`I0AP` | `A0FO` (`AIrg`, `D=1`) | `0x00200001` | 0.5s / 0 | 3 秒回复 135 血 + 70 蓝（受击打断） |
| **魔瓶（装符 6 态）** | `I0H0`/`I0H1`/`I0GX`/`I0GY`/`I0GZ`/`I0RE` | `A0H7` (`ANcl`, `B=0`) | `0x00000001` | 0.5s / 0 | 激活存储的双倍/极速/回复/幻象/隐身/赏金符 |
| **空魔瓶** | `I0AM`/`I0AV` | `A0H6` (`ANcl`, `B=1`) | `0x00100004` | 0.5s / 0 | 注：`targs1=item`，仅当靠近河道神符按装符时触发；通常直接右键(`smart`)神符自动装瓶 |
| **魔棒 / 魔杖** | `I0GC` / `I0HB` | `A0JY` (`AEfk`) | `0x00200001` | 17s / 0 | 按充能回复 `15 * charges` 血蓝 |
| **灵魂之戒（魂戒）** | `I0LL` | `A1Q8` (`AEfk`) | `0x00200001` | 30s / 0 | 扣 150 当前血换 150 临时蓝 |
| **奶酪（Roshan 掉落）** | `I0B1` | `A0K0` (`AIra`) | `0x00200001` | 40s / 0 | 瞬回 2500 HP + 1000 MP |
| **显影之尘（撒粉）** | `I0GH` | `AItb` (`CAbilityItemDetectByBuff`) | `0x00200001` | 60s / 5 | 自身周围 1050 码敌方隐身单位显形 12s |
| **诡计之雾（开雾）** | `I0NG` | `A206` (`AImr`) | `0x00200001` | 90s / 0 | 周围友方英雄与玩家单位集体隐身 |
| **动物信使 / 飞行信使** | `I05J` / `I01D` | `A0B6` / `A0JT` (`AHwe`) | `0x00300001` | 0s / 5 | 放地上召唤小鸡 / 或在场上信使旁将其变鸟 |
| **梅肯斯姆** | `I093` | `A0CK` (`AIda`) | `0x00200001` | 45s / 225 | 775 码回 250 HP（25s 防叠）+ 2 护甲 |
| **玄冥盾牌** | `I066` | `AIda` (`AIda`) | `0x00200001` | 25s / 10 | 750 码友方单位 +2 护甲 |
| **秘法鞋 / 先祖韧鼓** | `I0MI` / `I0NE` | `A0K7` / `A1ZW` (`AImr`) | `0x00200001` | 55s/35；30s/0 | 600 码集体回蓝 +135（L22384）/ 群体加攻移速 |
| **卡德加之洞察烟斗** | `I0K6` | `A1EW` (`AEfk`) | `0x00200001` | 60s / 100 | 925 码友方套 400 魔抗盾（50s 防叠） |
| **赤红甲** | `I0QY` | `A2YG` (`AEfk`) | `0x00200001` | 70s / 0 | 775 码友方英雄/建筑格挡 Buff（70s 防叠） |
| **刃甲 / 幽灵权杖 / 蝴蝶** | `I08O` / `I0JI` / `I0AI` | `A15W` / `A1AC` / `A31F` (`AEfk`) | `0x00200001` | 17/30/35s | 反弹伤害 / 虚无物免 / Flutter 爆发移速 |
| **黑皇杖（BKB 10~4s）** | `I0FZ`..`I0P8` | `A11F`..`A2LI` (`AHwe`) | `0x00300001` | 80~50s / 0 | 魔法免疫（按使用次数自动原位降级） |
| **撒旦之邪力** | `I0AB` | `A1FP` (`ANcl`, `B=0`) | `0x00000001` | 35s / 0 | +175% 吸血爆发 |
| **幻影斧（近/远）** | `I09F` / `I0MU` | `A0B8` / `A1WE` (`AOmi`) | `0x00000001` | 35s/50s / 165 | 躲弹道、弱驱散并分出 2 个幻象 |
| **死灵书 1~3 级 / 刷新球** | `I09T`..`I09Y` / `I0AJ` | `A0HB`.. / `A02W` (`AIfs`) | `0x00200001` | 95s/50；195s/375 | 召唤死灵战士/射手；重置全部技能与物品 CD |

#### A3. 原位切换状态类（无目标 `0x10`，脚本 `RemoveItem` + `FD1` 原位替换 FourCC）
| 物品 | 状态 FourCC 切换序列 | 技能 / 基类 | 说明 |
| :--- | :--- | :--- | :--- |
| **动力鞋（假腿）** | `I02T` (敏) → `I05Y` (力) → `I05Z` (智) → `I02T` | `A14A` (`AEfk`) | 三态单向轮转，切腿省蓝/撑血常见微操 |
| **臂章** | `I00Q` (关) ↔ `I00M` (开) | `A0T7`/`A0T8` (`AIam`) | 见 A1 表，唯一兼具切换机制与 `0x02000001` 的装备 |
| **王者之戒 / 天鹰之戒** | `I067`↔`I06A` / `I0P1`↔`I0P4` | `A269` / `A2KG` (`AEfk`) | 全单位护甲光环 ↔ 仅英雄生效（对线控线） |
| **辉耀 / 金箍棒** | `I0A8`↔`I0KP` / `I0A5`↔`I0K7` | `A1IO` / `A1FO` (`ANcl`, `B=0`) | 开关灼烧光环 / 开关克敌机先真击 |

---

### B 类：`Action 0x11` 点地使用（`useslot1..6` + `(x, y)`）

| 物品 | 背包 FourCC | 技能 / 基类 | Flags | 射程 / CD / 蓝耗 | 说明 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **科勒的匕首（跳刀）** | `I04H` | `AIbk` (`AEbl`) | `0x00100002` | 全图(实效 1200) / 12s / 0 | 瞬移至目标点（超 1200 缩至 960） |
| **纷争面纱** | `I0O3` | `A28D` (`AHbz`) | `0x01100002` | 1000(半径 600) / 30s / 75 | 区域法术易伤 |
| **回城卷轴（TP）/ 远行鞋** | `I05I` / `I06B` | `A1R5` / `A231` (`ANto`) | `0x00100002` | 全图 / 65s(50s) / 75 | 发点地坐标 `(x, y)`，DotA 脚本自动吸附最近友方建筑/单位并引导 3s+ |
| **血精石（主动自杀）** | `I0BK` | `A2TK` (`ANcl`, `B=2`) | `0x00000002` | 150 / 300s / 100 | `ANcl(DataB1=2)` 点地立即自爆自杀并给周围友方回血 |

---

### C 类：`Action 0x12` 对象目标使用（`useslot1..6` + `(tx, ty, obj1, obj2)`）

#### C1. 对友方 / 自身 / 敌方英雄或单位
| 物品 | 背包 FourCC | 技能 / 基类 | 射程 / CD / 蓝耗 | 允许目标范围 |
| :--- | :--- | :--- | :---: | :--- |
| **治疗药膏（大药）** | `I05F` | `AIpr` (`AIrg`, `D=0`) | 近身(500) / 0s / 0 | **自己或友方英雄**（受击断） |
| **净化药水（小蓝）** | `I05D` | `AIpl` (`AIrg`, `D=0`) | 近身(500) / 0s / 0 | **自己或友方英雄**（受击断） |
| **原力法杖（推推）** | `I0HI` | `A19M` (`ANcl`, `B=1`) | 800 / 20s / 25 | 自己、友方或敌方单位（顺朝向推 600 码） |
| **影之灵龛（骨灰）** | `I0KY` | `A1MO` (`ANcl`, `B=1`) | 950 / 7s / 0 | 友方英雄(回血) / 敌方英雄(持续掉血) |
| **林肯法球（主动给盾）** | `I09Z` | `A2VE` (`ANcl`, `B=1`) | 700 / 17s / 0 | 自己或友方英雄 |
| **雷神之锤（大电锤）** | `I0BE` | `A0JL` (`ANcl`, `B=1`) | 600 / 35s / 50 | 自己或友方单位（静电盾） |
| **勇气勋章** | `I0N0` | `A1ZI` (`ANcl`, `B=1`) | 1000 / 7s / 0 | 友方加甲或敌方减甲（**`notself` 不能点自己**） |
| **Eul 的神圣法杖（吹风）** | `I08Z` | `A1T7` (`ANcl`, `B=1`) | 700 / 23s / 75 | **自己或敌方单位**（注意：`targs1` 不含 `allies` 非自己友军） |
| **虚灵之刃（虚灵刀）** | `I0LT` | `A1QD` (`ANcl`, `B=1`) | 800 / 30s / 150 | 自己、友方或敌方英雄 |
| **净魂之刃 1/2 级（散失）** | `I08R` / `I0J9` | `AIpg` (`Aprg`) | 600 / 8s / 0 | 敌方(减速/秒召唤物) / 友方(驱散)，有 8 充能限制 |
| **紫怨 / 羊刀 / 阿托斯** | `I012` / `I0AL` / `I0OL` | `A0FD`/`AChx`/`A2EA` | 900/800/1200 | 敌方单位（沉默增伤 / 变羊 / 减速） |
| **天堂之戟 / 深渊之刃** | `I0OV` / `I0OX` | `A2K4` / `A2K7` | 600 / 140 | 敌方单位（缴械 / 无视魔免眩晕 2s） |
| **达贡之神力 1~5 级** | `I09M`..`I09L` | `A02O`..`A092` (`ANfd`) | 600~800 / 35~15s / 180 | 敌方单位（400~800 魔法爆发） |
| **迈达斯之手（点金）** | `I06D` | `A28Y` (`ANab`) | 600 / 100s / 0 | 非远古敌方/中立**非英雄**小兵或野怪（秒杀换 190g + 2.5x 经验） |
| **支配头盔（支配）** | `I08T` | `A2V4` (`ANcl`, `B=1`) | 700 / 60s / 75 | 非远古敌方/中立非英雄单位（支配为己方召唤物） |

#### C2. 对特殊实体（树木可破坏物）
| 物品 | 背包 FourCC | 技能 / 基类 | 射程 / CD | 目标对象 |
| :--- | :--- | :--- | :---: | :--- |
| **吃树 / 分享吃树** | `I05C` / `I0Q6`,`I0Q9` | `Aeat` / `A2VG` (`Aeat`) | 100 / 0(60)s | **树木 `CDestructable`**（详见 [`dota-6.83d-eat-and-cut-tree-reverse.md`](./dota-6.83d-eat-and-cut-tree-reverse.md)；对友方英雄也可发分享吃树） |
| **压制之刃（近/远补刀斧）** | `I0HR` / `I0HP` | `A1FD` (`Aeat`) | 350 / 5s | **树木 `CDestructable`**（或用 `0x12` 砍敌方真假眼） |

---

### D 类：`0x11` + `0x12` 双模式（真 / 假眼：`CAbilityChannel DataB1 = 3`）

| 物品 | 背包 FourCC | 技能 / 基类 | Flags | 射程 | 实证机制（`war3map.j` `M6O` L21949–21975） |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **侦察守卫（假眼）** | `I05G` | `A2WH` (`ANcl`, `B=3`) | `0x00000006` (`0x2\|0x4`) | 420 | 发 `0x11` 点地 → 在 `(x, y)` 插 7 分钟假眼；发 `0x12` 指向友方英雄 → 把 1 颗假眼递给该队友。 |
| **岗哨守卫（真眼）** | `I05H` | `A2WI` (`ANcl`, `B=3`) | `0x00000006` (`0x2\|0x4`) | 500 | 发 `0x11` 点地 → 在 `(x, y)` 插 4 分钟真眼；发 `0x12` 指向友方英雄 → 把 1 颗真眼递给该队友。 |

*(注：`ItemData.slk` 中还存在 `I0PM` 微光披肩（DotA 6.84+ 占位，未接入商店/配方）、`I0HN` 幽灵药剂 / `I0GF` 毒粉 / `I0KS` 幻象法杖（测试/旧商店）、`I0OE` 收割之刃 / `I0N3` 堕落者（非标准可买/合成物品），常规 DotA 6.83d 对局不会出现。)*

---

### E 类：非 `useslot` 的其他背包 / 商店物品操作（实证协议）

| 操作类型 | Action ID / 总长 | OrderId (Hex) | 逐字节载荷重点（已反汇编 `1.26 @ 0x6F2CBD00..0x6F2CBE11` & `War3Bot client.cpp:9507` 实证） | 用途 |
| :--- | :---: | :---: | :--- | :--- |
| **背包换格** | `0x12`（31B） | `0x000D0022..0x000D0027` (`moveslot1..6`) | `[0]=0x12`, `[1..2]=0x0000`, `[3..6]=orderId`, `[7..14]=0xFF*8`, `[15..22]=(hx,hy)`, **`[23..30]=CItem(obj1, obj2)`** | 引擎根据 `CItem` 反查所在源槽，与目标槽位对调 |
| **丢地上 / 递整组给队友或信使** | **`0x13`（39B）** | **`0x000D0021` (`dropitem`)** | `[0]=0x13`, `[1..2]=0x0000`, `[3..6]=0x000D0021`, `[7..14]=0xFF*8`, `[15..22]=(x,y)`, **`[23..30]=targetObj(丢地为 0xFFFFFFFF*2；给队友为友方 unit obj1/obj2)`**, **`[31..38]=itemObj(CItem +0x0C/+0x10)`** | 扔掉物品，或把**整组吃树/装备**直接移交给队友或信使（右击/拖放等效） |
| **拾取地面物品 / 魔瓶装符** | `0x12`（31B） | `0x000D0003` (`smart`) 或 `0x000D000D` (`getitem`) | 地面物品/神符 `(x, y, obj1, obj2)` | 捡地上装备，或用魔瓶英雄靠近河道神符直接装瓶 |
| **商店购买** | `0x10`（15B） | `soldUnitId`（假单位如 `h029`） | 先选中商店再发，由地图触发器换为背包真物品 | 商店购装 |

#### `JassHandleToItem` 多版本 RVA 表（解析 `CItem*` 的 `+0x0C/+0x10` 网络对象 ID）

因对局号角后 `Handle2Agent` 环停录，换格/丢弃/交接通过 `UnitItemInSlot` 取得 JASS 物品句柄后，调用 `JassHandleToItem`（`__fastcall void*(uint32_t itemHandle)`，带 MSVC/MinGW 兼容 SEH 包装）直接取 `CItem +0x0C/+0x10`：

| War3 版本 | `JassHandleToItem` RVA | 说明 |
| :--- | :---: | :--- |
| `1.0.17` ~ `1.21.0` | `0`（运行期回退） | 回退 `aiFindAgentInRing(itemHandle, 0)` |
| `1.22.0.6328` | `0x3B9070` | 由 `GetItemTypeId` 原生反汇编实证 |
| `1.23.0.6352` | `0x3BAD90` | 同上 |
| `1.24.1.6374` | `0x3BF5D0` | 同上 |
| `1.24.4.6387` | `0x3BF690` | 同上 |
| `1.25.1.6397` | `0x3BE920` | 同上 |
| `1.26.0.6401` | `0x3BEB50` | 同上（已核 `1.26 @ 0x6F2CBDAD..0x6F2CBDBD` 读 `CItem+0x0C/+0x10`） |
| `1.27.0.52240` | `0x1CFC50` | 由 `GetItemTypeId` 原生反汇编实证 |

> [!NOTE]
> **吃树分享的两种操作区别（实证结论）**：
> - **左击吃树 → 点队友（给 1 颗共享吃树）**：发 `Action 0x12` + `useslot1..6` 指向友方英雄。`war3map.j` `XGO`（L19799–19810）检测到 `GetSpellTargetUnit() != null` 时调用 `UnitAddItemById(targetHero, 'I0Q6')` 生成 1 颗 `I0Q6` 并扣除施法者 1 次充能（不可对已是 `I0Q6` 的分享吃树二次分享）。对应命令 **`-tree share [ally|0x<句柄>]`**（或 `-use tango ally`）。
> - **右击/拖放吃树 → 点队友（给整组树）**：发 **`Action 0x13`（39 字节）** + `0x000D0021 dropitem` + 队友 `(obj1, obj2)` + 吃树 `CItem (obj1, obj2)`，将整组树一次交给队友。对应命令 **`-tree give [ally|0x<句柄>]`**（或 `-inv give tango [ally|0x<句柄>]`）。

---

## 六、AI 命令体系区分设计（如何清晰区分所有物品操作）

结合当前仓库已落地的 `-buy` / `-tree` 与规划中的 [`dota-ai-smart-item-buy-and-use.md`](./dota-ai-smart-item-buy-and-use.md)，建议按 **「职责正交的四组短动词」** 区分所有物品相关操作，而不是为几十种物品单独发明几十个顶层命令：

| 顶层命令 | 职责边界 | 实现状态 | 说明 |
| :--- | :--- | :---: | :--- |
| **`-buy` / `/buy`** | **商店购买** | ✅ 已实现 | 选中商店发 `0x10 (0x0044 + soldUnitId)`，如 `-buy salve`、`-buy clarity` |
| **`-tree` / `/tree`** | **树木与吃树分享** | ✅ 已实现 | `cut`（砍树）/ `eat`（吃树）/ **`share`（左击给队友 1 颗 `I0Q6`）** / **`give`（右击/拖放给队友整组 `0x13`）** / `list`（扫描） |
| **`-items` / `/items`**（别名 **`-bag` / `/bag`**） | **只读查看英雄 6 格背包** | ✅ 已实现 | 输出 `slot1..6` 的 FourCC、中文名、充能、句柄、估算剩余 CD 到 `logs\AiUnit.log`；注意 **RemoteControl TCP 6120 下无前缀 `items` 保留用于返回商店货架表**，RemoteControl 下查英雄背包请用 `bag` / `inv list` / `items bag` / `-items` |
| **`-use` / `/use`**（别名 **`-item` / `/item`**） | **统一激活 / 切换背包物品** | ✅ 已实现 | 由 `shared/DotaActiveItemAbbrev.h` 元数据表自动选 `0x10`/`0x11`/`0x12` 与目标，支持 60 类主动物品缩写与槽位 `1..6` 显式覆盖、假腿三态切换、臂章 `retoggle` 等 |
| **`-inv` / `/inv`** | **背包换格 / 丢弃 / 交接整组** | ✅ 已实现 | `[list]` / `swap <1..6> <1..6>` (`moveslot 0x12`) / `drop <1..6\|物品> [x y]` (`0x13`) / `give <1..6\|物品> [ally\|0x<句柄>]` (`0x13`) |

### `-use` 命令语法与典型调用方式

设计为 `-use <槽位1..6 | 物品简称> [目标/子模式参数]`（`/` 与 `-` 双前缀、RemoteControl TCP 通用）：

1. **按物品简称直呼，内部按元数据表自动选 `0x10`/`0x11`/`0x12`**：
   - **吃大药 / 小蓝**（自动查表走 `0x12`，默认对自己发，也可指友方或句柄）：
     - `-use salve` / `-use salve self` → 对自己贴大药（`0x12 useslot + heroObj`）
     - `-use salve ally` / `-use salve 0x<handle>` → 给附近最残血友方英雄 / 指定句柄队友贴大药
     - `-use clarity [self|ally|0x<handle>]` → 吃净化药水（小蓝）
   - **无目标装备（自动 `0x10`）**：
     - `-use bottle` / `-use phase` / `-use stick` / `-use wand` / `-use soulring` / `-use pipe` / `-use mek` / `-use crimson` / `-use shiva` / `-use bkb` / `-use dust` / `-use smoke` / `-use manta` / `-use satanic` / `-use refresher` / `-use necro`
   - **状态切换装备（自动计算切换次数 + 原位 FourCC 校验）**：
     - `-use treads [str|agi|int|next]` → 读取当前假腿 FourCC（`I05Y`/`I02T`/`I05Z`），自动连发 `0/1/2` 次 `0x10` 切到目标属性；无参等价 `next`
     - `-use armlet [on|off|toggle|retoggle]` → 只在目标状态与当前 `I00M`/`I00Q` 不一致时才发 `0x10`；`retoggle` 为残血瞬间先关再开
     - `-use basilius [hero|all|toggle]` / `-use aquila [hero|all|toggle]` / `-use radiance [on|off|toggle]` / `-use mkb [on|off|toggle]`
   - **点地装备（自动 `0x11`）**：
     - `-use blink <x> <y>` / `-use blink fountain`（朝泉水跳）/ `-use blink enemy`（敌人方向逃/追）
     - `-use tp [<x> <y> | fountain | ally]` / `-use bot [<x> <y> | fountain]`
     - `-use veil [<x> <y> | enemy]`
   - **单体目标装备（自动 `0x12`）**：
     - `-use force [self|fountain|ally|enemy|0x<handle>]`（对自身/友/敌发 `0x12`）
     - `-use hex` / `-use orchid` / `-use dagon` / `-use atos` / `-use halberd` / `-use abyssal` / `-use eblade` / `-use diffusal` / `-use urn` / `-use medallion` `[enemy|ally|self|0x<handle>]`
     - `-use eul [self|enemy|0x<handle>]`（注意风杖不可对非己友方施放）
     - `-use midas [creep|neutral|0x<handle>]` / `-use hotd [neutral|0x<handle>]`（优先挑大野/高经验单位）
   - **双模式眼位（自动区分 `0x11` 与 `0x12`）**：
     - `-use obs <x> <y>` / `-use sentry <x> <y>` → 点地插眼（`0x11`）
     - `-use obs ally` / `-use obs 0x<handle>` → 给队友递眼（`0x12`）
2. **按栏位直接指定，支持显式覆盖外壳（兼容未收录或自定义用途）**：
   - `-use <1..6> [none | self | ally | enemy | creep | <x> <y> | 0x<handle>]`
   - 例如 `-use 1 none` 强制走 `0x10`，`-use 2 -1500 1200` 强制走 `0x11`，`-use 3 0x1012AB` 强制走 `0x12`。

---

## 七、代码落地状态总览

以下全栈改动已完成代码实现，覆盖 DotA 6.83d 全部 60 类主动/切换/消耗/守卫/移交操作：

1. **`War3Launcher/shared/DotaActiveItemAbbrev.h` + `SharedMemory.h`**：
   - 追加 `AI_UNIT_CMD_SHARE_TREE`、`AI_UNIT_CMD_ITEMS`、`AI_UNIT_CMD_USE`、`AI_UNIT_CMD_INV` 与 `AiUseTargetMode` / `AiUseToggleMode` / `AiInvSubCmd`；
   - 三端共用 `dotaFillTreeSharePayload` / `dotaFillTreeGivePayload` / `dotaFillUseItemPayload` / `dotaFillInvPayload` 统一参数解析。
2. **`War3Launcher/hooker/`（`war3hook_ai.cpp` / `war3hook_ai_tactics.inl` / `war3hook_offsets.cpp`）**：
   - 新增 `JassHandleToItem` 1.22~1.27 RVA 与 `aiInvokeHandleToItem` SEH 包装、`aiOrderDropItem` (39B Action `0x13`)、`aiTickPendingItemToggle`（假腿 2 连切 / 臂章 130ms `retoggle`）；
   - 实现 `aiDumpItems`、`aiExecShareTree`、`aiExecInv`、`aiExecUseItem` 与全量 DotA 6.83d 背包 FourCC 映射。
3. **`War3Launcher` 上层与 `War3Server`**：
   - `war3hook_process.cpp`、`AiControlManager.h/.cpp`、`NetworkManager.cpp`、`scripts/ai_control.ps1` 与 `War3Server` (`src/bnetd/command.cpp` + `command_groups.conf(.in)`) 全链路打通。
