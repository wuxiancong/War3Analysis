# DotA 6.83d 英雄使用技能（Cast）深度逆向与 AI 控制体系设计（结合现有代码审计）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Antigravity AI Agent（Planning + Execution） |
| **分析目的** | 系统盘点已有英雄施法分析文档与 `War3Launcher/hooker/war3hook_ai.cpp` 现有实现；深度逆向 `game.dll`（1.0.17 ~ 1.27.0.52240）技能对象模型、`CAbilitySpell` 实时冷却/蓝耗/沉默/控制态、Action `0x10/0x11/0x12` `Flags` 位掩码及 DotA 6.83d 全 112 英雄边界案例，为后续完整 AI 施法升级提供工程蓝图 |
| **命名方式** | `dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design`；命令沿用并扩展 `-cast` / `-learn` / `-skills` / `-autolearn`（对应 `/cast`、`/learn`、`/skills`、`/autolearn`） |
| **分析时间** | 2026-11-19 |
| **验证状态** | **全静态逆向实证完成**：基于 `D:\Qt\workspace\War3Launcher\versions\*\game.dll`（全部 11 个版本）反汇编、`DotA v6.83d` 物编（`war3map.w3a`、`Units_AbilityData.slk`、`*AbilityFunc.txt`、`*AbilityStrings.txt`）、`War3Bot/images/dota_data.json` 与 `War3Script/war3map.j` 实证；**本阶段仅产出文档，不改 C++/服务端源码**，实机动态联调归入后续实现阶段 |
| **相关文档** | [`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md)、[`dota-ai-human-lasthit-learn-cast.md`](./dota-ai-human-lasthit-learn-cast.md)、[`dota-hero-skill-point-learn-flow.md`](./dota-hero-skill-point-learn-flow.md)、[`dota-ai-skill-command-implementation.md`](./dota-ai-skill-command-implementation.md)、[`warcraft-iii-skill-key-remap.md`](./warcraft-iii-skill-key-remap.md)、[`dota-6.83d-active-items-and-consumables-reverse.md`](./dota-6.83d-active-items-and-consumables-reverse.md) |
| **配套思维导图** | [`dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design-mindmap.md`](./dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design-mindmap.md) |

---

## 一、核心结论（结论先行）

### 1.1 直接回答：现有分析文档有没有分析英雄如何使用技能？

**有，但仅覆盖了“协议外壳 + MVP 4 格静态表”层面，刻意跳过了 `game.dll` 技能对象内部机制；结合当前代码审计，实际存在 8 类严重缺失与错误。**

| 已有文档 | 日期 | 已覆盖内容 | 明确未覆盖的盲区 |
| :--- | :---: | :--- | :--- |
| [`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md) | 2026-11-16 | 网络 Action `0x10`（无目标）/ `0x11`（点地）/ `0x12`（单位目标）帧结构、`OrderId` vs `FourCC` 区别、与 `-useitem`（`useslot1..6`）隔离 | 第 1 节明确写明「交付注入不必深挖 `game.dll`」，未分析 `CAbilitySpell`、实时冷却、沉默、蓝耗、`Flags` 位掩码 |
| [`dota-ai-human-lasthit-learn-cast.md`](./dota-ai-human-lasthit-learn-cast.md) | 2026-11-16 | `extract_game_orders.py`（344 条 `0xD0xxx`）、`build_skill_table.py`、`DotaHeroSkillAbbrev.h` 生成、MVP `learn`/`autolearn`/`cast`/`skills` 编码与冰女/斯温测试 | 只覆盖 1~4 号主槽与 1 级静态属性；对假被动/假主动、友方目标、开关法球、第 5~6 槽及动态召唤技能完全盲区 |
| [`dota-hero-skill-point-learn-flow.md`](./dota-hero-skill-point-learn-flow.md) & [`dota-ai-skill-command-implementation.md`](./dota-ai-skill-command-implementation.md) | 2026-11-16 | 按 `O` 发 `0x66` + 发 `0x10 + FourCC` 升级技能与属性附加、`learn` 与 `cast` 动词划分 | 属**加点（Learn）**专用文档，非施法；未定位 `CAbilityHero + 0x90` 真技能点字段 |
| [`warcraft-iii-skill-key-remap.md`](./warcraft-iii-skill-key-remap.md) | 2026-11-07 | 客户端本地输入拦截 `0x6F382150`（hook `0x3821C6`）、4×3 命令卡热键查找 `0x6F35E390` | 纯本地键盘映射，不涉及 AI 无 UI 发包与引擎校验 |

### 1.2 本次深度逆向与全代码审计的核心发现

1. **无需猜状态，可直接从 `game.dll` 读取 100% 真实引擎状态（附全 11 版 RVA）**：
   - 遍历 `CUnit + 0x1DC / +0x1E0` 句柄对链表（经 `ResolveAgent` 得 `CAbility*`，后继在 `CAbility + 0x24 / +0x28`），可枚举英雄**当下实际拥有的一切技能**——包括**祈求者 10 个祈唤技能、拉比克窃取技能、末日吞噬野怪技能、影魔中/远炮、帕克灵动之翼、变体精灵转力量/替身**，彻底摆脱 `skills[4]` 静态数组限制。
   - 在 `CAbilitySpell` 对象上可直接零同步风险读取：
     - 自定义技能码 `[+0x34]`、基类码 `vtable[+0x1C]()`、真实等级 `[+0x50] + 1`；
     - 真实冷却：标志位 `[+0x20] & 0x200`（`0x400` 暂停）+ 嵌入的 `CAgentTimer`（`[+0xD0]`）虚表 `[+0x18]` 或直接调 `CAbilitySpell::GetCooldownRemaining`（`1.26: 0x037E70` / `1.27: 0x3F72B0`）读剩余秒数，总冷却在 `[+0xB0]`；
     - 真实蓝耗与校验：`vtable[+0x3D4]` / `vtable[+0x370]`；禁用计数 `[+0x3C] > 0`；单技能沉默/控场锁 `[+0x44] > 0`；
     - 引擎原生七步全检函数 `CAbilitySpell::CheckCanCast`（`vtable[+0x3DC]`，`1.26: 0x050880`），返回 `0` 即代表不禁用/非幻象/够蓝/无 CD/未沉默/满足条件/有充能；
     - 英雄当前正在执行的命令 `CUnit + 0x19C / +0x1A0` → `COrder + 0x24`（实时判断前摇/持续施法是否结束，不再盲等固定 `guardMs`）；真实未用技能点在 `*(CUnit + 0x1F0) + 0x90`。
2. **`Action 0x10 / 0x11 / 0x12` 的 `Flags`（包 `[1..2]` / `CNetCommand + 0x18`）位掩码实证完成**：
   - `0x0001`（bit 0）：**Shift 队列排队（Queued）**——不打断当前施法/移动，写入 `COrder + 0x20 |= 4` 并入单位命令队列（跳刀接大、沙王摇大接跳刀、帕克 Shift 飞剑的核心）。
   - `0x0002`（bit 1）+ `0x0100`（bit 8）：瞬发/插队分支，走 `0x6F2A0770`。
   - `0x0010`（bit 4）：选中组上下文标记（`0x6F2CD2E1`）。
   - `0x0020`（bit 5）：持续施法抑制检查及清队控制标志（`0x6F2CA928` + `0x6F2C9010` arg1）。
   - `0x0040`（bit 6）：**仅当前子组执行（Subgroup）**（`1` 走 `0x6F421E00`，`0` 遍历全部选中单位 `0x6F421AF0`）。
3. **当前代码（`war3hook_ai.cpp`、`DotaHeroSkillAbbrev.h`、`build_skill_table.py`、`NetworkManager.cpp`、`War3Server`）审计出 8 类直接影响实战的问题**：
   - 4 个核心主动技（水人复制 `A0G8`、炸弹埋雷 `A05J`、夜魔大 `A03K`、影魔大 `A29J`）被错标成 `PASSIVE`；
   - 4 个被动技（幻影冲锋 `A0YK`、法术护盾 `A0KY`、腐蚀外表 `A0MM`、腐肉堆积 `A06D`，均基于 `AIdd`）被错标成主动 `defend (0xD0057)`；
   - 水人敏捷转换 `A0KX` 被错标成 `UNIT (0x12)`，实证应为 `NONE (0x10)` 开关；
   - 25 个开关/自动施法/变身双命令技能只存了 1 个 `orderId`，导致关不掉毒蛇/魔法盾/腐烂、也不能手点法球不拉小兵仇恨；
   - 16 个纯友方技 + 8 个敌友双目标技在 `AUTO` 下全部误找敌方英雄，且 `"ally"` 被硬编码错映射到 `AI_CAST_TARGET_ALLY_CREEP`（小兵）；
   - `slot > 4` 被一刀切丢弃，影魔中远炮 `A0FH`/`A0F0`、帕克 `A0SA`、昆卡 `A13D`、火猫 `A2JL`、凤凰 `A1Z2` 及卡尔 10 技能全失明；
   - 448 个主槽中 139 个蓝耗/78 个冷却/15 个射程随等级变化却只存了 1 级，且施法前不检死活/沉默/CD/蓝量，还把 `UNIT_OR_POINT` 死锁在 `0x12`（无法点地破林肯）；
   - `War3Server/src/bnetd/command.cpp` 与 `War3Launcher/managers/NetworkManager.cpp` 完全未注册 `/cast`、`/learn`、`/skills`、`/autolearn`（聊天窗口发指令无效）。

---

## 二、`game.dll` 英雄技能对象模型与实时状态读取

> 以下结构偏移经由 `1.26.0.6401` 与 `1.27.0.52240` `game.dll` 静态反汇编交叉核对。

### 2.1 `CUnit` 与技能 / 控制态相关字段布局

| 偏移 | 类型 | 字段语义 | 汇编实证来源（`1.26.0.6401` / `1.27.0.52240`） |
| :--- | :--- | :--- | :--- |
| `+0x0C` / `+0x10` | `uint32[2]` | 单位网络对象 ID（`obj1`, `obj2`） | `0x6F2CBB6A`、`0x6F3C73B0`（同 `-move`/`-attack` 使用的 ID 对） |
| `+0x20` | `uint32` | 基础对象状态位（`0x200000`、`0x40000000`） | `0x6F26DE50` / `0x6F037B78`（无效/移除或异常对象判定） |
| `+0x33` | `uint8` | 单位 `FourCC` 首字母 ASCII | `CUnit::GetHeroSkillPoints`（`1.26: 0x282C00`）：减去 `0x41 ('A')` `<= 0x19 ('Z')` 判英雄 |
| `+0x5C` | `uint32` | 单位运行时状态位掩码 | `0x00200000`（`shr 0x15 & 1`）= **`IsUnitPaused`（`0x3C73DA`）**；**`0x40000000`** = **幻象 Illusion（`0x6F03FDCC` / `0x6F05089E`：置位则非真英雄且禁止施法）**；`0x20000000` = 动作/命令锁标志（`0x6F2CAC4A`） |
| `+0x158` / `+0x15C` | `int32` | 魔免 / 状态计数（`IsUnitType` slot 25 / 26） | `0x6F3C7F8D` / `0x6F3C7F99`（`> 0` 为真） |
| `+0x164` | 结构体 | 单位命令代理/目标缓存区起点 | `0x6F2CA84E` / `0x6F2CAC10` |
| **`+0x19C` / `+0x1A0`** | **`uint32[2]`** | **当前活跃 `COrder*` 句柄对** | `GetUnitCurrentOrder`（`1.26: 0x3C7780`、`1.27: 0x1E5F80`）→ `ResolveAgent` → `*(uint32_t*)(COrder + 0x24)` = 正在执行的 `orderId` |
| **`+0x1DC` / `+0x1E0`** | **`uint32[2]`** | **动态 `CAbility*`（含技能与 Buff）链表头** | `CUnit::GetAbility`（`0x0787D0`）、`CUnit::ResetCooldown`（`0x078C38`）、`IsUnitType` 状态枚举（`0x6F07646C`） |
| `+0x1E8` | `CAbilityAttack*` | 内建攻击能力（`'Aatk'`） | `0x6F3C7EE8`（`IsUnitType` 近战/远程等直接读 `+0x1E8`） |
| `+0x1EC` | `CAbilityMove*` | 内建移动能力（`'Amov'`） | `0x6F078C00` 同层内建能力槽 |
| **`+0x1F0`** | **`CAbilityHero*`** | **内建英雄能力（`'AHer'`），`+0x90` 为真未用技能点** | `CUnit::GetHeroSkillPoints`（`1.26: 0x282C00`）先校验首字母大写与非幻象，再解引用 `*(CAbilityHero + 0x90)` |
| `+0x1F4` | `CAbilityBuild*` | 内建建造能力 | 与 `+0x1F8` 同层标准内建指针 |
| `+0x1F8` | `CAbilityInventory*` | 内建背包能力（`'AInv'`） | 已在 [`dota-6.83d-active-items-and-consumables-reverse.md`](./dota-6.83d-active-items-and-consumables-reverse.md) 验证 |

#### 控场状态枚举路径（`IsUnitType` 跳表 `1.26: 0x6F3C7FB4`）

`IsUnitType`（`1.26: 0x3C7E90`）在分支 `11~13` 与 `21~24`（`0x6F076460` ~ `0x6F0766A0`）统一遍历 `CUnit + 0x1DC / +0x1E0` 链表，对每个 `CAbility*`（包含挂在单位身上的晕眩、变羊、缠绕、睡眠、虚无、魔免等 Buff 技能节点）调用固定虚表槽位 `vtable[+0x188]` ~ `vtable[+0x1A0]`；任意一个节点返回非 0 即判定受控。**注**：对英雄自身能否释放技能，直接检查目标 `CAbilitySpell` 的 `[+0x44]`（沉默/禁止计数）+ `CAbilityHero` / `CUnit+0x5C`（Pause/Illusion）+ `vtable[+0x3DC]`（`CheckCanCast`）甚至比逐一猜测 Buff 更精准，因为它**直接走引擎自己的施法门禁逻辑**。

---

### 2.2 动态技能链表枚举算法（解决静态 `skills[4]` 盲区）

```text
CUnit* u = JassHandleToUnit(heroHandle);
handle_pair cur = *(handle_pair*)(u + 0x1DC);   // +0x1DC, +0x1E0
while ((cur.a & cur.b) != 0xFFFFFFFF) {
    CAbility* ab = ResolveAgent(&cur);
    if (!ab) break;
    handle_pair next = *(handle_pair*)(ab + 0x24); // 先保存 next 指针
    bool isHiddenBuff = ((*(uint32_t*)(ab + 0x20)) & 0x20) != 0;
    uint32_t customFourCC = *(uint32_t*)(ab + 0x34);
    uint32_t baseFourCC   = ((GetTypeIdFn)(ab->vtable[0x1C / 4]))(ab);
    int level             = *(int32_t*)(ab + 0x50) + 1;
    // 读取订单、Flags、CD、蓝耗、沉默禁用态...
    cur = next;
}
```

**意义**：无论英雄是否变身（龙骑/熊德/灵魂守卫）、是否通过 `UnitAddAbility` 动态获得了第 5/6 格或替换技（**祈求者 10 个祈唤法术、拉比克偷来的任意敌方大招、末日吞噬野怪技能、影魔中远炮、帕克飞升、昆卡返还、凤凰子技**），全部挂在这条链表中，枚举即所得。

---

### 2.3 `CAbility` / `CAbilitySpell` 对象字段与虚表方法

| 字段偏移 | 类型 | 语义 | 汇编实证证据（`1.26.0.6401` / `1.27.0.52240`） |
| :--- | :--- | :--- | :--- |
| `+0x04` | `uint32` | 引用计数（`dec [esi+4]` 归零析构） | `0x6F078CC4` / `0x6F47172A` |
| **`+0x20`** | **`uint32`** | **技能运行标志位**：<br>• `0x00000020` = Buff/隐藏（非玩家主动槽）<br>• **`0x00000200` = 正在冷却中**<br>• **`0x00000400` = 冷却暂停/屏蔽显示**<br>• `0x00001000` / `0x00004000` = 当前已激活 / 施法中<br>• `0x80000000` = 忽略冷却放行 | `CAbilitySpell::GetCooldownRemaining`（`1.26: 0x037E70`, `1.27: 0x3F72B0`）、`CheckCanCast`（`0x0508C9..D5`）、`CheckOrder`（`0x037B63`） |
| `+0x24` / `+0x28` | `uint32[2]` | 链表下一 `CAbility*` 句柄对 | `0x6F078C70` / `0x6F4716E2` |
| `+0x30` | `CUnit*` | 所属单位直指针（空时回溯 `0x6F472890`） | `0x6F037F28` / `0x6F050974` |
| **`+0x34`** | **`uint32`** | **自定义技能 `FourCC`**（如 `'A1E9'`） | `0x6F037F37`（与 `0x6F32E920` 查物编表对齐） |
| **`+0x3C`** | **`int32`** | **禁用计数（Disabled Count）**：`> 0` 返回错误 **`0xDD`** | `CheckCanCast` `0x6F050883`：`cmp dword ptr [esi+3Ch], 0; jle ...; mov eax, 0DDh`（对应 `SetPlayerAbilityAvailable` 禁用或触发器锁技） |
| **`+0x44`** | **`int32`** | **沉默 / 禁用施法计数**：`> 0` 返回错误 **`0xB9`** | `CheckCanCast` `0x6F0508E7`：`cmp dword ptr [esi+44h], 0; jle ...; mov eax, 0B9h` |
| **`+0x50`** | **`uint32`** | **0-based 技能等级**（实级 = `+1`） | `GetUnitAbilityLevel` 直接返回 `[ab+0x50] + 1`；`0x6F037F3A` 用于物编蓝耗/CD 查询 |
| `+0x9C` | `uint32` | 技能数据区/子类型索引字段 | `1.27: 0x3DA336` |
| **`+0xB0`** | **`float`** | **本次触发冷却的总时长（秒）** | `1.26: 0x037ECE..EE7`（UI 冷却进度 = `Remaining / Total`） |
| **`+0xD0`** | **`CAgentTimer`** | **内嵌冷却计时器对象**（约 0x20B） | `1.26: 0x037E81..96`、`1.27: 0x3F72C4..D3` 调 `+0xD0` 虚表 `+0x18`（`CAgentTimer::GetRemainingTime`，`1.26: 0x477B80`）返回精确剩余冷却秒数 |

#### `CAbilitySpell` 关键虚表函数槽位（`1.26.0.6401` 反汇编实证）

| 虚表偏移 | 推断方法名 | 返回值与核心行为 | 实证地址 / 样本 |
| :---: | :--- | :--- | :--- |
| `+0x01C` | `GetBaseTypeId()` | 返回基础技能 `FourCC`（例如 `'ANcl'` / `'AIil'`） | `0x6F1127B0`（`'AIil'`）、`0x6F195610`（`'ANcl'`）等各派生类单行函数 |
| `+0x268` | `CheckRequirements(int)` | 科技树/学习条件满足返回非 0；否则 `CheckCanCast` 返回 `0xB8` | `0x6F0508F8..908` |
| **`+0x308`** | **`GetPrimaryOrderId()`** | **主订单 ID**（开关/自动施法类技能此处是 **On 订单**，如 `manashieldon 0xD026D`、`immolation 0xD00D1`、`replenishmanaon 0xD0245`） | 各技能虚表均含此槽；`ANcl` 在 `0x6F1CE970` 动态返回物编 `DataF` 订单 |
| **`+0x30C`** | **`GetPrimaryOrderFlags()`** | **主订单标志位**：<br>• `0x00000001` (`bit 0`) = 无目标 `Action 0x10`<br>• `0x00000002` (`bit 1`) = 点地 `Action 0x11`<br>• `0x00000004` (`bit 2`) = 目标单位 `Action 0x12`<br>• `0x00000006` (`0x2 \| 0x4`) = 点地或单位均可用<br>• `0x00000040` (`bit 6`) = 被动壳占用（不可施放，如 `AIdd`）<br>• `0x00000400` = 开关 Toggle（`AEim`/`ANms`/`Abrf`）<br>• `0x00006C01` = 开关开启类 Flag（`Arpm`/`Arpl`/`Apsh`）<br>• `0x02000000` = **瞬发不打断当前动作** | `AIil=0x100004`、`AIpm=0x1000002`、`AIct=0x200001`、`AIha=0x200001`、`AIdd=0x40`、`AEim=0x2000401`、`Arpm=0x2006C01`、`ANcl` 动态调用 `0x6F19F440` |
| `+0x314` | `IsDualOrderMode()` | 标识是否区分主动/开关形态 | `0x6F037BA5` / `0x6F0290E5` / `0x6F050913` |
| **`+0x318`** | **`GetOffOrUnorderId()`** | **关闭/解除变身订单**（如 `unimmolation 0xD00D2`、`manashieldoff 0xD026E`、`unbearform 0xD00AB`、`replenishmanaoff 0xD0246`） | `AEim`/`ANms`/`Abrf`/`Arpm`/`Arpl`/`Apsh` 虚表实证 |
| `+0x31C` | `GetOffOrderFlags()` | 关闭订单标志（如 `Arpm=0x2007C01`、`AEim=0x2000401`） | 同上 |
| **`+0x348`** | **`GetManualCastOrderId()`** | **自动施法技能手动单发时的订单 ID**（如 `Arpm` `0xD0244`、`Arpl` `0xD0241`、`Apsh` `0xD0222`） | `0x6F0290FE`、`0x6F04F60D` |
| `+0x34C` | `GetManualCastOrderFlags()` | 手动单发订单标志（如 `Arpm=0x200001` 无目标、`Apsh=0x200001` 无目标） | `0x6F037CAF`、`0x6F04F64F` 家族对比 |
| **`+0x370`** | **`HasEnoughMana(int checkCurrent)`** | 检查英雄当前蓝量 `>= vtable[+0x3D4]()`；不足使 `CheckCanCast` 返回 `0xD1` | `1.26: 0x029080`（实参传 `1`） |
| `+0x3D4` | `GetManaCost()` | 返回当前等级实时蓝耗 | `0x6F029088` 调 `+0x3D4` 后通过 `0x6F283C70` 与单位蓝量比较 |
| **`+0x3DC`** | **`CheckCanCast(int ignoreSilence, int ignoreMana)`** | **引擎原生 7 步全量可施放预检**（传 `(0, 0)`，返回 `0` 即可发包） | **`1.26: 0x050880`**：<br>① `[+0x3C]>0`→`0xDD`（禁用）<br>② `[unit+0x5C]&0x40000000`→`0xDD`（幻象）<br>③ `!+0x370(1)`→`0xD1`（缺蓝）<br>④ `[+0x20]&0x200 && !bit31`→`0xD2`（冷却）<br>⑤ `[+0x44]>0`→`0xB9`（沉默/被控）<br>⑥ `!+0x268(0)`→`0xB8`（不满足条件）<br>⑦ 充能检查失败→`0x54`<br>⑧ 通过→**`0`** |

> **关键发现**：相比自己拼接 `if (mana >= cost && !silenced && cd == 0 ...)`，只要从 `CAbility*` 读取 `GetCooldownRemaining()`、`+0x3D4`（蓝耗）、`+0x50 + 1`（等级）与直接调用只读查询 `vtable[+0x3DC](0, 0)`，既不会产生同步副作用（只读校验不改动任何 `game.dll` 状态），又能获得与 War3 界面灰显完全一致的引擎级权威判断！

---

## 三、全 11 版本 `game.dll` 多版本 RVA 对照表

> 遵循 `war3-reverse-toolkit.md` 多版本规范，以下全部 RVA 均通过脚本对 `D:\Qt\workspace\War3Launcher\versions\*\game.dll` 全部 **11 个版本**按原生注册签名与指令流静态提取并核对。`1.26.0.6401` 与 `1.27.0.52240` 已完成逐行反汇编验证。

### 3.1 JASS 只读/辅助原生函数 RVA（全 11 版）

| 版本号 | `GetUnitAbilityLevel` | `GetHeroSkillPoints` | `GetUnitCurrentOrder` | `UnitResetCooldown` | `IsUnitPaused` | `IsUnitType` | `SetPlayerAbilityAvailable` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | `0x2C4490` | `0x2C2A30` | `0x2C53F0` | `0x2C92F0` | `0x2C4940` | `0x2C7450` | `0x2CD610` |
| `1.0.20.6048` | `0x2C4490` | `0x2C2A30` | `0x2C53F0` | `0x2C92F0` | `0x2C4940` | `0x2C7450` | `0x2CD610` |
| `1.20.4.6074` | `0x2C45B0` | `0x2C2B50` | `0x2C5510` | `0x2C9410` | `0x2C4A60` | `0x2C7570` | `0x2CD730` |
| `1.21.0.6263` | `0x2C7B80` | `0x2C6120` | `0x2C8AE0` | `0x2CC9E0` | `0x2C8030` | `0x2CAB40` | `0x2D0D00` |
| `1.22.0.6328` | `0x3C0530` | `0x3BFA20` | `0x3C0A20` | `0x3C1970` | `0x3C0640` | `0x3C1130` | `0x3C2A70` |
| `1.23.0.6352` | `0x3C2250` | `0x3C1740` | `0x3C2740` | `0x3C3690` | `0x3C2360` | `0x3C2E50` | `0x3C4790` |
| `1.24.1.6374` | `0x3C7D10` | `0x3C7200` | `0x3C8200` | `0x3C9150` | `0x3C7E20` | `0x3C8910` | `0x3CA250` |
| `1.24.4.6387` | `0x3C7DD0` | `0x3C72C0` | `0x3C82C0` | `0x3C9210` | `0x3C7EE0` | `0x3C89D0` | `0x3CA310` |
| `1.25.1.6397` | `0x3C7060` | `0x3C6550` | `0x3C7550` | `0x3C84A0` | `0x3C7170` | `0x3C7C60` | `0x3C95A0` |
| **`1.26.0.6401`** | **`0x3C7290`** | **`0x3C6780`** | **`0x3C7780`** | **`0x3C86D0`** | **`0x3C73A0`** | **`0x3C7E90`** | **`0x3C97D0`** |
| **`1.27.0.52240`** | **`0x1E5EF0`** | **`0x1E2970`** | **`0x1E5F80`** | **`0x1FB270`** | **`0x1E8BC0`** | **`0x1E8CC0`** | **`0x1F6000`** |

> **联机安全警告**：上述 `IssueImmediateOrderById`（`1.26: 0x3CB860` / `1.27: 0x1FB310`）、`IssuePointOrderById`（`1.26: 0x3C8900` / `1.27: 0x1E90A0`）、`IssueTargetOrderById`（`1.26: 0x3C8980` / `1.27: 0x1E9610`）仅供逆向理解单位状态转移使用，**严禁从本地客户端 AI 直接调用**——直接调 JASS 下令原生只改本地模拟状态，不进主机帧同步队列，会立即导致多人联机 **Desync（掉线/不同步）**。AI 下令必须继续走 **`EnqueuePlayerAction`**。

### 3.2 `CUnit` / `CAbilitySpell` 内部核心方法 RVA（`1.22` ~ `1.27` 同构，附 `1.0.17` ~ `1.21` 参考）

| 版本号 | `JassHandleToUnit` | `CUnit::GetAbility` | `CUnit::GetHeroSkillPoints` | `ResolveAgent` | `CUnit::ResetCooldown` | `CAbilitySpell::ResetCooldown` | `CAbilitySpell::GetCooldownRemaining` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | `0x29B1C0` | `0x0F6110`* | `0x0F60B0`* | `0x0F6110`* | `0x087010` | *(内联/早期布局)* | *(内联/早期布局)* |
| `1.0.20.6048` | `0x29B1C0` | `0x0F6110`* | `0x0F60B0`* | `0x0F6110`* | `0x087010` | *(内联/早期布局)* | *(内联/早期布局)* |
| `1.20.4.6074` | `0x29B2E0` | `0x0F6120`* | `0x0F60C0`* | `0x0F6120`* | `0x087010` | *(内联/早期布局)* | *(内联/早期布局)* |
| `1.21.0.6263` | `0x29E5C0` | `0x0F6140`* | `0x0F60E0`* | `0x0F6140`* | `0x087010` | *(内联/早期布局)* | *(内联/早期布局)* |
| `1.22.0.6328` | `0x3B81D0` | `0x077D80` | `0x2820C0` | `0x468A20` | `0x078230` | `0x037550` | `0x0375B0` |
| `1.23.0.6352` | `0x3B9EF0` | `0x079340` | `0x283600` | `0x46A7B0` | `0x079770` | `0x038A90` | `0x038AF0` |
| `1.24.1.6374` | `0x3BE730` | `0x0793F0` | `0x2836C0` | `0x479140` | `0x079820` | `0x038B40` | `0x038BA0` |
| `1.24.4.6387` | `0x3BE7F0` | `0x079400` | `0x283720` | `0x4791C0` | `0x079830` | `0x038B50` | `0x038BB0` |
| `1.25.1.6397` | `0x3BDA80` | `0x0787D0` | `0x2829D0` | `0x478480` | `0x078C00` | `0x037E10` | `0x037E70` |
| **`1.26.0.6401`** | **`0x3BDCB0`** | **`0x0787D0`** | **`0x282C00`** | **`0x4786B0`** | **`0x078C00`** | **`0x037E10`** | **`0x037E70`** |
| **`1.27.0.52240`** | **`0x1D1550`** | **`0x46F440`** | **`0x668FA0`** | **`0x044150`** | **`0x471690`** | **`0x3DA2A0`** | **`0x3F72B0`** |

> 注：`*` 表示 `1.0.17` ~ `1.21.0` 使用旧版对象槽布局或代理校验封装；目前 DotA 6.83d 联调主力集中在 `1.24e` / `1.26a` / `1.27a`，此区间（`1.22` ~ `1.27`）`CUnit` 与 `CAbilitySpell` 结构偏移高度一致，`1.26` 与 `1.27` 经反汇编双核对一致。实际接入 `war3hook` 时仍建议配合版本白名单或特征码校对。

---

## 四、网络动作 `Action 0x10 / 0x11 / 0x12` 帧格式与 `Flags` 实证

### 4.1 三类施法/加点动作包结构（`1.26: 0x6F5407C0..0x6F5409B0`、`0x6F2CB940..0x6F2CBC00`）

| Action | 总长度 | 类名（反汇编虚表） | 载荷布局 | 用途 |
| :---: | :---: | :--- | :--- | :--- |
| **`0x10`** | **15B** | `CNetCommandUnitOrderImmediate`（`vt 0x6F932C90`） | `[0] 0x10`<br>`[1..2] uint16 Flags`<br>`[3..6] uint32 AbilityOrOrderId`<br>`[7..10] 0xFFFFFFFF` / ItemId1<br>`[11..14] 0xFFFFFFFF` / ItemId2 | 1. 加点（填技能 `FourCC` 或 `Aamk`/`A0NR`）<br>2. 无目标主动技能（填 `OrderId 0x000Dxxxx`）<br>3. Toggle 开关/关闭（填 `OrderOn`/`OrderOff`/`Unorder`） |
| **`0x11`** | **23B** | `CNetCommandUnitOrderTargetPoint`（`vt 0x6F932C9C`） | `[0..14]` 同 `0x10`<br>`[15..18] float X`<br>`[19..22] float Y` | 1. 点地技能（如 `A1E9` 冰女新星、`AIpm` 炸弹地雷、`blink`）<br>2. 双模式技能显式点地（`UNIT_OR_POINT`，如穿刺/钩子） |
| **`0x12`** | **31B** | `CNetCommandUnitOrderTargetImage`（`vt 0x6F932CA8`） | `[0..14]` 同 `0x10`<br>`[15..18] float X`<br>`[19..22] float Y`<br>`[23..26] uint32 TargetObjId1`<br>`[27..30] uint32 TargetObjId2` | 1. 单体指向技（友军/敌军/自身/建筑）<br>2. 自动施法法球手动点人（**单发不拉小兵仇恨**） |

> 注：构造器 `0x6F2CBB6A` 实证 `0x12` 发包时，会把目标对象 `[target + 0x0C]`、`[target + 0x10]` 写入对象 ID 槽，同时通过 `vtable[+0xB8]` 取目标实时位置写入 `(X, Y)`。因此 `war3hook_ai.cpp:2513` 即使发送单位目标，也同步刷新 `tx, ty` 再送入 `aiOrderTarget` 是完全符合引擎预期的。

### 4.2 `Flags`（`uint16_t`，包偏移 `[1..2]` → `CNetCommand + 0x18`）逐位实证

通过对 `1.26.0.6401` Action `0x10` 分发链 **`0x6F2CD2E1..0x6F2CD407` → `0x6F2CA800..0x6F2CA954`** 及 `0x6F2CABAB` / `0x6F2CB1BB` / `0x6F2C9010` 反汇编，实证每个二进制位功能如下：

| 位 / 掩码 | 读取位置（`1.26`） | 引擎底层效果 | AI 实战用途 |
| :---: | :--- | :--- | :--- |
| **`0x0001` (bit 0)** | `0x6F2CA865`：`and dl, 1` → `0x6F2CA936` |置位时走 `0x6F2CA936`：设置 `COrder + 0x20 \|= 4`（**Queued**），调 **`0x6F2A0510`（入单位命令队列）**，**不打断正在进行中的移动/施法/引导** | **Shift 连招队列基石**：沙王摇大(`0x10`) + Queue 跳刀(`0x11, Flags\|=1`)、跳刀后无缝 Queue 羊刀/晕眩/大招、修补匠 Shift 刷新连招、帕克发波接 Queue 飞升 |
| `0x0002` (bit 1) | `0x6F2CA86E`：`and dl, 2` → `0x6F2CA8ED`<br>`0x6F2CABC5`：`shr edx, 1` | 未排队且本位置位时，调 `0x6F2A0770(order, bit8)`（即时类/无停顿指令分发路径），并传入 `0x6F2C9010` 第 2 参 | 瞬发切换/零打断类命令兼容位 |
| `0x0010` (bit 4) | `0x6F2CD2E1`：`shr eax, 4; and eax, 1` | 传入 `0x6F47B520` 与编队分发结构体 `[esp+4Ch]` / `[esp+68h]` | 选中集/团队指令上下文标志 |
| `0x0020` (bit 5) | `0x6F2CA87C`：`shr edi, 5; and edi, 1`<br>`0x6F2CABCA`：`shr eax, 5` | 传 `!bit5` 给 `0x6F2A4AB0`，并作为 `0x6F2C9010` 第 1 参控制是否跳过 `[COrder+0x20]&0x40` 状态抑制 | 覆盖/立即执行当前指令控制位 |
| **`0x0040` (bit 6)** | `0x6F2CD303`：`test al, 40h`<br>`0x6F2CABBA`：`shr ecx, 6` | `1` 走 `0x6F421E00`（仅对当前聚焦子组执行）；`0` 走 `0x6F421AF0`（对全部选中单位循环发令） | War3 真人默认发 `0x0040`（单英雄等效；陈/米波/德鲁伊等多控单位可区分只放本体技能还是全队下令） |
| `0x0100` (bit 8) | `0x6F2CA881`：`shr eax, 8; and eax, 1` | 配合 `bit 1` 压栈传给 `0x6F2A0770` | 扩充即时命令标志位 |

---

## 五、结合当前代码的 8 大缺陷定位（112 英雄 + 448 主槽全量审计）

> 对 `War3Launcher/hooker/war3hook_ai.cpp`、`War3Launcher/shared/DotaHeroSkillAbbrev.h`、`War3Analysis/artifacts/ability-orders/build_skill_table.py`、`War3Launcher/managers/AiControlManager.cpp`、`War3Launcher/managers/NetworkManager.cpp` 与 `War3Server/src/bnetd/command.cpp` 逐行核对，并结合 `war3map.w3a`、`Units_AbilityData.slk`、`AbilityFunc.txt`、`AbilityStrings.txt` 与 `1.26 game.dll` 虚表实证，定位以下 **8 大具体问题**。

### 缺陷 1：4 个主动核心/大招被误标为 `DOTA_SKILL_TARGET_PASSIVE`（完全放不出来）

`build_skill_table.py` 因地图/MPQ 文本里缺少 `Order=`（且引擎将这类物品/特殊技能硬编码在 C++ 虚表里），第 195 行直接判 `if not order: tt = PASSIVE`。反汇编 `1.26 game.dll` C++ 虚表与 `war3map.w3a` 蓝耗/CD/目标数据，**4 个关键主动技均被彻底废掉**：

| 英雄（代码） | 槽位与技能码 | 技能名称 | 基类 | `DotaHeroSkillAbbrev.h` 行号与错误现状 | `1.26 game.dll` 虚表实证（`+0x1C`/`+0x308`/`+0x30C`） | `w3a`/`SLK` 实际数值 | 正确修复方案 |
| :--- | :---: | :--- | :---: | :--- | :--- | :--- | :--- |
| **变体精灵 (`O00P`)** | 槽4 `A0G8` | 复制 Replicate | `AIil` | L42：`0x00000, PASSIVE` | `vt 0x6F8E0D5C`：<br>`+0x308 = 0xD0132` (`itemillusion`)<br>`+0x30C = 0x100004` (`bit 2`) | 蓝耗 25，CD 80s，射程 700/1100/1500，`enemies,friend,hero,notself` | **`0xD0132`**, **`UNIT` (`0x12`)**, `side=BOTH` |
| **地精工程师 (`H00K`)** | 槽1 `A05J` | 埋布地雷 Land Mines | `AIpm` | L61：`0x00000, PASSIVE` | `vt 0x6F8DD654`：<br>`+0x308 = 0xD0136`<br>`+0x30C = 0x1000002` (`bit 1`) | 蓝耗 125~205，CD 19~10s，射程 100 | **`0xD0136`**, **`POINT` (`0x11`)** |
| **暗夜魔王 (`Udre`)** | 槽4 `A03K` | 黑暗时间 Darkness | `AIct` | L100：`0x00000, PASSIVE` | `vt 0x6F8C1EA4`：<br>`+0x308 = 0xD028D`<br>`+0x30C = 0x200001` (`bit 0`) | 蓝耗 0，CD 160/120/80s | **`0xD028D`**, **`NONE` (`0x10`)** |
| **影魔 (`Nfir`)** | 槽4 `A29J` | 魂之挽歌 Requiem | `AIha` | L118：`0x00000, PASSIVE` | `vt 0x6F8CA39C`：<br>`+0x308 = 0xD0131`<br>`+0x30C = 0x200001` (`bit 0`) | 蓝耗 150/175/200，CD 120/110/100s | **`0xD0131`**, **`NONE` (`0x10`)** |

> **排重说明**：骷髅王（`NC00`）槽 4 `A01Y`（重生 `AOre`，240s/260s CD）虽在静态表扫描中被筛选出 `Cool > 0`，但它确实是受死触发被动技，保留 `PASSIVE` 是正确的。

---

### 缺陷 2：4 个纯被动技能被误标为 `DOTA_SKILL_TARGET_NONE`（发送无效命令 `defend 0xD0057`）

DotA 用原版 `AIdd`（物品护甲/防御外壳）实现需要图标或动态加护甲/攻速的纯被动技；而 `AbilityFunc.txt` 为 `AIdd` 标了 `Order=defend`，导致 `build_skill_table.py` 将它们生成为可主动点击的无目标技。反汇编 `1.26 game.dll` `AIdd` 虚表（`0x6F895574`）证实：`+0x2F8 = +0x2FC = +0x300 = 0xDD`（禁用占位），且 `+0x30C = 0x40`（**低 4 位为 0，无任何施放位，纯被动占位**）：

| 英雄（代码） | 槽位与技能码 | 技能名称 | `DotaHeroSkillAbbrev.h` 错误现状 | 正确修正 |
| :--- | :---: | :--- | :--- | :--- |
| **幻影长矛手 (`Ogrh`)** | 槽3 `A0YK` | 幻影冲锋 Phantom Rush | L59：`0xD0057, DOTA_SKILL_TARGET_NONE` | **`0x00000, DOTA_SKILL_TARGET_PASSIVE`** |
| **敌法师 (`Edem`)** | 槽3 `A0KY` | 法术护盾 Spell Shield | L72：`0xD0057, DOTA_SKILL_TARGET_NONE` | **`0x00000, DOTA_SKILL_TARGET_PASSIVE`** |
| **蝮蛇 (`EC77`)** | 槽3 `A0MM` | 腐蚀外表 Corrosive Skin | L108：`0xD0057, DOTA_SKILL_TARGET_NONE` | **`0x00000, DOTA_SKILL_TARGET_PASSIVE`** |
| **屠夫 (`U00F`)** | 槽3 `A06D` | 腐肉堆积 Flesh Heap | L115：`0xD0057, DOTA_SKILL_TARGET_NONE` | **`0x00000, DOTA_SKILL_TARGET_PASSIVE`** |

---

### 缺陷 3：变体精灵敏捷转换 `A0KX` 被误标为 `UNIT`（单位目标），实为 `NONE (0x10)`

`DotaHeroSkillAbbrev.h:42` 把水人（`O00P`）槽 3 `A0KX` 标成了 `DOTA_SKILL_TARGET_UNIT`（原因：`build_skill_table.py:142` 把 `replenishmana` 写死为 `UNIT`）。但反汇编 `1.26` `Arpm`（`vt 0x6F91B324`）与 `Arpl`（`vt 0x6F91AE9C`）实证：
- **敏捷转换 `A0KX` (`Arpm`)**：`+0x308 = 0xD0245` (`replenishmanaon`, Flag **`0x2006C01`**)、`+0x318 = 0xD0246` (`replenishmanaoff`, Flag **`0x2007C01`**)、`+0x348 = 0xD0244` (`replenishmana`, Flag **`0x200001`**) —— **三者最低位均是 `bit 0 = 1`（`Action 0x10` 无目标），根本不是 `UNIT` (`0x12`)**！
- 同理，缺失的 5 号槽 **力量转换 `A0KW` (`Arpl`)**：`+0x308 = 0xD0242` (`0x2006C01`)、`+0x318 = 0xD0243` (`0x2007C01`)、`+0x348 = 0xD0241` (`0x200001`)，同样全部走 **`Action 0x10` 无目标**！当前表把 `A0KX` 标成 `UNIT`，会导致 AI 先去搜敌方英雄目标，完全无法自我转属性。

---

### 缺陷 4：25 个“开关（Toggle）/ 自动施法（Autocast）/ 变身”双命令技能只有单一 `orderId`

`DotaHeroSkillSlot` 只有一个 `uint32_t orderId`，导致所有开关与法球只能发主 `orderId`（或者只能开不能关、或者开自动施法与手动单发混为一谈）。经 `war3map.w3a` + `AbilityFunc.txt` + `1.26 game.dll` 虚表扫描，**25 个双命令英雄槽位**完整实证如下：

| 分类 | 英雄与技能（代码 / 基类） | 单发 / 开启 Order | 关闭 / 解除 Order | 现有代码实际行为 | AI 必须具备的能力 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **纯开关 Toggle（`0x10`）** | 屠夫腐烂 `U00F/A06K` (`AEim`)<br>拉席克脉冲新星 `E01A/A0NE` (`AEim`) | **`0xD00D1`** (`immolation`) | **`0xD00D2`** (`unimmolation`) | 只能发 `0xD00D1` 打开，**永远关不掉**（烧死自己/烧光蓝） | `-cast <slot> on` / `off` / `toggle`（结合 `CheckOrder`/Buff 判当前开关态） |
| **魔法盾开关（`0x10`）** | 美杜莎魔法盾 `H00V/A0MP` (`ANms`)<br>小精灵过载 `O01F/A28Q` (`ANms`) | **`0xD026D`** (`manashieldon`) | **`0xD026E`** (`manashieldoff`) | 只能开 `0xD026D`，无法发 `0xD026E` 关闭 | 支持精确 `on`/`off` |
| **水人双转换（`0x10`）** | 变体精灵敏转 `O00P/A0KX` (`Arpm`)<br>变体精灵力转 `O00P/A0KW` (`Arpl`) | 敏：**`0xD0245`** (`on`)<br>力：**`0xD0242`** (`on`) | 敏：**`0xD0246`** (`off`)<br>力：**`0xD0243`** (`off`) | `A0KX` 误当 `UNIT` 发不出去；`A0KW` 直接被 `slot>4` 丢弃 | 支持 `on/off`，并在开力前先关敏（反之亦然） |
| **形态切换变身（`0x10`）** | 龙骑士古龙形态 / 熊德变形 `N01O/A0AG` / 巨魔近远切换 `N016/A0BE` / `H00V/A1C0` (`Abrf`) | **`0xD00AA`** (`bearform`) | **`0xD00AB`** (`unbearform`) | `N016`（巨魔切斧）若变身后再切回，需知当前态发 `0xD00AB` | 检测 Buff/Morph 态切回 `unbearform` |
| **毒箭法球自动施法** | 小黑冰箭 `Emoo/A0DY`、`N01A/A0LZ`、`H00Q/A0QN`、`EC77/A09V`、`U00P/A0OI` (`AEpa`)；黑鸟奥数天球 `U006/A0BH` (`ANpa`) | 手动点人 (`0x12`)：**`0xD011E`** (`AEpa`) / **`0xD0279`** (`ANpa`) | 自动开关 (`0x10`)：<br>开 **`0xD011F`** / **`0xD027A`**<br>关 **`0xD0120`** / **`0xD027B`** | 当前仅支持 `0x12` 手动单点，**无法开启/关闭自动施法** | **核心战术意义**：对线期 AI **必须用 `0x12` 单发点敌方英雄（W 键法球走 A 不拉小兵仇恨）**，推塔/团战才开 `Autocast` |
| **常规技能自动施法** | 小鹿推进/魅惑 `Emoo/A0DX` (`0xD006B/C/D`)<br>蓝胖嗜血 `Hmkg/A083` & 黑贤套子 `H00N/A0R7` (`0xD0085/86/87`)<br>巫妖冰甲 `Ulic/A08R` (`0xD0101/1EA/1EB`)<br>巫妖/猛犸 `A053` / `A037` & 小克火箭 `E004/A04Q` (`0xD0062/63/64`)<br>帕克相位转移 `N00B/A0SB` (`0xD0222/23/24`)<br>赏金/大鱼标记 `A0B4` / `A034` (`0xD00B5/B6/B7`) | 单次施法：前 1 项 (`0x12` 或 `0x10`) | 自动施法开关 (`0x10`)：第 2 / 第 3 项 | 全缺自动施法 `On`/`Off` 订单，冰甲/嗜血等也缺友方选人（见缺陷 5） | `cast <slot> on|off` 控制自动施法，`cast <slot> [target]` 单发 |

> （另有少数原版结构字段借用如 `H004/A01P` 莉娜神灭斩借 `charm`、`U00K/A0H0` 借 `voodoo`，属单发技能，实以 `targs1` 为准。）

---

### 缺陷 5：16 个纯友方目标技 + 8 个敌友双目标技在 `AUTO` 下全部误打敌方英雄，`ally` 错映射到友方小兵

检查 `war3hook_ai.cpp`:
- **L2448**：`else mode = AI_CAST_TARGET_ENEMY_HERO;` —— 只要参数不是固定点地，无论什么 `UNIT` / `UNIT_OR_POINT` 技能，`AUTO` 一律强制找**最近敌方英雄**！
- **L2397 & L3238**（以及 `AiControlManager.cpp:830`）：`"ally"` 映射到 `AI_CAST_TARGET_ALLY_CREEP`，而 `aiFindCastTarget` 里 **`AI_CAST_TARGET_ALLY_CREEP` 只筛选 `!s.hero && s.ownerId == allyCreep`** —— **目前连选一个友方英雄的代码分支都不存在！**

通过解析全量 `war3map.w3a` 的 `atar` 与 `SLK targs1`，**16 个纯友方目标技能**（不含已修正为 `0x10` 的 `A0KX` 则为 15 个真单位友方技）与 **8 个敌友双目标技能**清单如下：

| 类别 | 英雄与技能（代码 / Order / TargetType） | 现有错误行为 |
| :--- | :--- | :--- |
| **纯友方/自身单位技能（15 个真 `0x12` 技）** | `Hamg/A01Z`（大树活体护甲，可救建筑与队友）、`Hmkg/A083`（蓝胖嗜血术）、`Harf/A08N`（全能洗礼）、`E02K/A2J2`（军团强攻）、`N0MU/A2QI`（土猫 `thunderclap`）、`N0MU/A2TI`（土猫残岩交互）、`Udea/A0MF`（死骑无光之盾）、`N01W/A0OR`（暗牧薄葬）、`H00N/A0R7`（黑暗贤者离子外壳）、`Ulic/A08R`（巫妖冰甲）、`Ulic/A053`、`UC11/A037`（猛犸授予力量）、`UC18/A02N`（莱恩吸蓝*注：可对含蓝友/敌或野怪*）、`Usyl/A2ZO` & `U006/A2ZS`（`notself` 单位技） | 当用户或 AI 执行 `-cast <slot>`（`AUTO`）时，全部跑去找敌方英雄，**导致全能对敌人放奶、死骑给敌人套无光之盾失败、军团给敌人放强攻无效、暗牧不对残血队友套薄葬**！ |
| **敌友双目标技能（8 个 `UNIT` / `UNIT_OR_POINT`）** | `Ucrl/A0BZ`（小小投掷）、`N0MU/A2UU`（土猫巨石翻滚/踢）、`N0MD/A2SG`（神谕命运敕令）、`U00F/A06I`（屠夫肉钩，可钩救友军）、`U00P/A0OJ`（黑鸟星体禁锢，可保己方/关敌方）、`E01C/A0AS`（全能或术士暗言术奶队友/伤敌人）、`Eevi/A07Q`（魂守换血，必换残血友或满血敌！）、`E02H/A1S8`（毒狗崩裂禁锢，救队友躲爆发/关敌先手） | `AUTO` 下永远当作纯攻击技只打敌人，无法“救队友”；显式写 `-cast <slot> ally` 却只搜小兵，还是选不到队友英雄 |

---

### 缺陷 6：5/6 号槽位与动态子技能全部被截断（`build_skill_table.py:221` 与 `war3hook_ai.cpp:2416`）

1. **`build_skill_table.py:221` 硬编码 `if s['slot'] > 4: continue`**，且 `DotaHeroSkillEntry` 在 `DotaHeroSkillAbbrev.h:33` 定死为 `DotaHeroSkillSlot skills[4]`，加上 `war3hook_ai.cpp:2416` 硬写 **`|| slot == 5`** 拒绝施放 5 号位——导致 `War3Bot/images/dota_data.json` 中真实存在第 5/6 槽位的英雄全部丢失核心技能：

| 英雄（代码） | 槽5 技能码 | 槽6 技能码 | `war3map.w3a` / `AbilityStrings` 实证 OrderId & 目标类型 |
| :--- | :---: | :---: | :--- |
| **影魔 (`Nfir`)** | **`A0FH`** 中炮 [X] | **`A0F0`** 远炮 [C] | `A0FH`: `howlofterror (0xD026C)` **`0x10` 无目标**；`A0F0`: `battleroar (0xD0277)` **`0x10` 无目标**（现表只有近炮 `Z`！） |
| **变体精灵 (`O00P`)** | **`A0KW`** 力量转换 [F] | — | `A0KW` (`Arpl`): `0xD0241` / `0xD0242(on)` / `0xD0243(off)` **`0x10` 无目标** |
| **帕克 (`N00B`)** | **`A0SA`** 灵动之翼 [E] | — | `channel (0xD0278)` **`0x10` 无目标**（飞向幻象法球必用！） |
| **昆卡 (`H06S`)** | **`A13D`** X标记返回 [X] | — | `chemicalrage (0xD02B7)` **`0x10` 无目标** |
| **圣堂刺客 (`E01Y`)** | **`A0RQ`** 触发陷阱 [T] | — | `locustswarm (0xD024C)` **`0x10` 无目标** |
| **灰烬之灵 (`N0M0`)** | **`A2JL`** 火之余烬激活 [R] | — | 与残焰点地 `A2JK` 配套的激活子技（现表只有放残焰，不能飞！） |
| **凤凰 (`E02F`)** | **`A1Z2`** 指定烈火精灵 [F] | **`A1YX`** 烈火精灵 | 释放太阳精灵子技（丢火弹必用） |
| **陈 (`H00A`) / 兽王 (`H00D`)** | **`A2MC`** 忠诚考验传送 / **`A2U5`** 野性呼唤 | — | 陈传送友军 / 兽王召战鹰豪猪双技缺 1 个 |
| **死灵/拉比克/伐木机/神谕/尸王** | `A0NT` / `A27I` / `A2FL` / `A2T6` / `A15K` | `A27K` (拉比克槽2) | 拉比克窃取槽位等被截断 |

2. **运行时由 `war3map.j` 动态 `UnitAddAbility`（共 272 处）替换/添加的子技能与完全动态英雄**：
   - **祈求者（`H00U` 卡尔）10 大祈唤法术**（通过 `A0VF` 元素祈唤 `ambush 0xD00A3` 或 `A1GU` `0xD026C` 动态挂上 2 个活跃技能，现表只有 Q/W/E 球与 R 祈唤，**10 个输出技一个都不会放**）：
     - 急速冷却 `[QQQ]`: `A0VZ`/`A0YA` (`autoentangle 0xD0219`)
     - 幽灵漫步 `[QQW]`: `A0XL`/`A0YD` (`windwalk 0xD00A1`)
     - 寒冰之墙 `[QQE]`: `A0VP`/`A0YH` (`autodispeloff 0xD00A6`)
     - 电磁脉冲 `[WWW]`: `A0VS`/`A0YC` (`animatedead 0xD00F9`)
     - 强袭飓风 `[WWQ]`: `A0VK` (`ancestralspirittarget 0xD020B`)
     - 灵动迅捷 `[WWE]`: `A0VQ`/`A0Y9` (`ancestralspirit 0xD020A`)
     - 阳炎冲击 `[EEE]`: `A0VG`/`A0YI` (`blizzard 0xD0079`)
     - 熔炉精灵 `[EEQ]`: `A0VO`/`A0YG` (`autodispel 0xD00A4`)
     - 混沌陨石 `[EEW]`: `A0VN` (`auravampiric 0xD00F8`)
     - 超震声波 `[QWE]`: `A0VM`/`A0YE` (`auraunholy 0xD00F7`)
   - **其余高价值二段释放 / 停止 / 子技**（均经 `war3map.w3a` / `AbilityStrings.txt` 实证）：
     - 伐木机收回死亡飞锯：`A2E6` (`coldarrows 0xD0114`, `0x10`)
     - 幽鬼降临现实：`A0HA` (`channel 0xD0278`, `0x10` 瞬移幻象)
     - 凤凰烈日炙烤：`A1YY` (`charm 0xD0265`) / 终止 `A1Z3` (`animatedead 0xD00F9`) / 移动开关 `A205` (`immolation 0xD00D1`)
     - 小娜迦停止海妖之歌：`A24E` (`animatedead 0xD00F9`)；大牛收回先祖之魂：`A21J` (`animatedead 0xD00F9`)
     - 光法召回：`A11Y`/`A11Z` (`channel 0xD0278`)；致盲之光：`A11V`/`A11W` (`blizzard 0xD0079`)
     - 巨魔战将近战/远程旋风飞斧：`A21M` (`thunderbolt 0xD007F`) / `A21N` (`thunderclap 0xD0080`)
     - 大地之灵残岩：`A2TH` / `A31G..A31K` (`thunderbolt 0xD007F`)
     - 拉比克法术窃取后的临时技能、末日吞噬获得的野怪技能。
   - **根本性解决方案**：不能靠在静态头文件里穷举几百个动态子技能，而是在 Phase 2 直接利用 **第 2.2 节的 `CUnit + 0x1DC` 实时技能链表探针**——任何挂载在英雄身上的非 Buff `CAbilitySpell` 都能被立刻扫描到其 FourCC、真实等级、真实 `vtable[+0x308]` 订单与 `[+0x30C]` 目标标志位，自动成为可施放目标！

---

### 缺陷 7：随等级变化的数值被忽略 + 缺少施法前安全预检 + `UNIT_OR_POINT` 被锁死在 `0x12`

1. **只存储了 1 级属性**：经脚本统计全 448 个主技能槽，`war3map.w3a` / `SLK` 中：
   - **139 个技能** 的蓝耗随等级变化；
   - **78 个技能** 的冷却时间随等级变化；
   - **15 个技能** 的施法距离随等级变化（如水人复制 `700/1100/1500`、老鹿/小鹿/黑贤等）。
   当前 `DotaHeroSkillSlot`（`DotaHeroSkillAbbrev.h:24-27`）仅有单个 `range`、`manaCost`、`coolDs`。
2. **`aiStartCast`（`war3hook_ai.cpp:2410-2498`）缺少基础安全门槛**：
   - 只检查了 `sk.target != PASSIVE`、`sk.orderId != 0` 与 `aiAbilityLevel(hero, ability) > 0`，**不检查死亡/Paused/幻象、不检查蓝量、不检查技能是否在冷却、不检查沉默/眩晕**——冷却中照样选中英雄、触发真人延迟 `150~900ms`、发无效网络包并把 `g_aiCastGuardUntil` 锁死 `guardMs`（停下补刀傻等！）。
   - 同时 `range` 在 `aiFindCastTarget` 里被放大为 `range * 1.6f + 200.0f`（最高 1800），虽然可用于索敌寻路靠近施法，但缺乏区分“已在施法距离内直接瞬发”与“先走位靠近（`MoveTo`）”的状态机。
3. **`DOTA_SKILL_TARGET_UNIT_OR_POINT` 无法走点地 `0x11`**：
   - `aiStartCast` 第 2474 行写死 `if (sk.target == DOTA_SKILL_TARGET_POINT)` 才发 `0x11`，其余全进 `else` 发 `0x12` 单位包！这导致 **莱恩穿刺（`A0X5`）、小强穿刺（`A0X7`）、屠夫肉钩（`A06I`）、全能/发条/先知等全图或点地兼顾技能** 在选敌时强制走 `0x12` 锁定单位（很容易被**林肯法球**抵挡，也无法预判走位或调整角度多穿几个敌人）。

---

### 缺陷 8：全链路命令入口不完整（游戏内聊天输入 `/cast` / `-cast` 无效）

对比已完整落地的 `-tree` 与 `-use` 管道，当前英雄技能命令链路仅完成了一半：

| 层次 | 文件 | 现状 |
| :--- | :--- | :--- |
| **War3 进程内聊天 Hook** | `War3Launcher/hooker/war3hook_ai.cpp:3216` | ✅ 仅此处实现了本地调试钩子 `handleSkillCommand`（支持 `-learn`/`-cast`/`-autolearn`，注意本地连 `-skills` 都没在 `handleSkillCommand` 处理，只有 `AI_UNIT_CMD_SKILLS` 被 `AiControlManager` 调！） |
| **RemoteControl `:6120`** | `War3Launcher/managers/AiControlManager.cpp:811-860` | ✅ 支持 `learn`/`skill`/`cast`/`autolearn`/`skills`（但 `cast` `"ally"` 错发 `AI_CAST_TARGET_ALLY_CREEP`） |
| **Launcher 游戏通信管线** | `War3Launcher/managers/NetworkManager.cpp` | ❌ **0 处注册** `/learn`、`/cast`、`/skills`、`/autolearn`（无聊天拦截转 IPC） |
| **War3Server 战网命令** | `War3Server/src/bnetd/command.cpp`、`conf/command_groups.conf.in` | ❌ **0 处注册**（联机/局域网大厅聊天输入 `/cast` / `-cast` 被服务器当成未知命令报错，参考 `-tree` 规范必须在服务端同步注册白名单与回调） |

---

## 六、面向后续实现的分阶段工程蓝图（供下阶段照表开发）

> **边界重申**：本节为工程设计蓝图，本次对话不改动代码；后续实施建议分 4 个独立可控的 Phase 推进。

### Phase 1：静态表与服务端命令全链路对齐（0 风险基建）

1. **修正并扩展 `build_skill_table.py` 与 `DotaHeroSkillAbbrev.h`**：
   - 修复 **4 个假被动**（`A0G8`/`A05J`/`A03K`/`A29J`）、**4 个 `AIdd` 假主动**（`A0YK`/`A0KY`/`A0MM`/`A06D`）、**水人 `A0KX` (`Arpm`)** 目标类型改为 `NONE`。
   - 保留 `slot == 5 / 6` 中所有**非属性点**自定义技能（将静态槽扩展至最多 `skills[6]` + `attr`，`findDotaHeroSkills` / `aiResolveSkill` 兼容键位 `1..6` 及 `q/w/e/r/d/f`）。
   - 为 `DotaHeroSkillSlot` 增补字段：
     - `uint8_t targetSide`（`0=ENEMY`, `1=ALLY`, `2=BOTH`, `3=SELF`）；
     - `uint32_t orderOnId`、`uint32_t orderOffId`、`uint32_t unorderId`（覆盖全部 25 个开关/法球/变身技）；
     - `uint16_t rangeByLv[4]`、`uint16_t manaCostByLv[4]`、`uint16_t coolDsByLv[4]`（覆盖随等级变化的技能，不再只存 1 级）。
2. **补全全链路命令注册**：
   - 在 `War3Server/src/bnetd/command.cpp` 与 `conf/command_groups.conf.in`（第 1 组用户权限）参照 `/tree` / `/use` 补齐 `/cast`、`-cast`、`/learn`、`-learn`、`/skills`、`-skills`、`/autolearn`、`-autolearn`。
   - 在 `War3Launcher/managers/NetworkManager.cpp` 补齐对应指令解析并走共享内存 IPC `MSG_TYPE_AI_UNIT_COMMAND` 转发至 `war3hook_ai.cpp`。

### Phase 2：接入 `game.dll` 实时技能探针（多版本自适应）

1. 在 `war3hook_ai.cpp` 按构建版本 / 检测版本号挂入第 3 节全版本 RVA 表（优先覆盖 `1.22` ~ `1.27` 主流版，保留优雅降级）。
2. 实现核心探针结构体与只读函数：

```cpp
struct AiLiveAbilityInfo {
    uint32_t customFourCC;     // CAbility + 0x34
    uint32_t baseFourCC;       // vtable[+0x1C]()
    uint32_t orderId;          // vtable[+0x308]() 或 manual +0x348()
    uint32_t orderFlags;       // vtable[+0x30C]()（低4位 1=0x10, 2=0x11, 4=0x12, 6=双模式; Bit25=瞬发不打断）
    uint32_t offOrderId;       // vtable[+0x318]()（Toggle Off / Unbearform / Autocast Off）
    int      level;            // *(int32_t*)(ab + 0x50) + 1
    float    cooldownRem;      // CAbilitySpell::GetCooldownRemaining
    float    cooldownTotal;    // *(float*)(ab + 0xB0)
    int      manaCost;         // vtable[+0x3D4]()
    uint32_t canCastErr;       // vtable[+0x3DC](0, 0): 0=可用, 0xD1=缺蓝, 0xD2=CD, 0xB9=沉默, 0xDD=禁用/幻象
    bool     onCooldown;       // (+0x20 & 0x200) && !(+0x20 & 0x80000000)
    bool     isActiveOrToggle; // +0x20 & 0x1000 / 0x4000 等激活状态
};
```

3. 实现 `aiEnumLiveAbilities(heroHandle, outList)`：遍历 `CUnit + 0x1DC/+0x1E0` 链表（过滤 `[+0x20] & 0x20` Buff、排除 `'Aatk'`/`'Amov'`/`'AHer'`/`'AInv'`、`vtable[+0x30C]() == 0x40` 纯被动占位），直接支持**卡尔 10 技能、拉比克窃取技能、末日吞噬、影魔三炮、帕克二段**等一切动态技能！
4. 扩展 `-skills` 输出与 `AiPlayerLiveState` 10ms 快照：不仅打印静/动态全部技能的 `Lv`、`OrderId`、`CD 剩余/总长`、`Mana`、`CheckCanCast 状态码`，还能读 `*(CAbilityHero + 0x90)` 获取真正未用技能点、`GetUnitCurrentOrder` 实时读取正在执行的 `OrderId`。

### Phase 3：完整 `-cast` 指令语义与 Shift 连招

1. **统一目标参数解析**（修复 `"ally"` 并兼容开关/点地/排队）：
   ```text
   -cast <1..6|q|w|e|r|d|f|FourCC|all> [auto|enemy|creep|allyhero|ally|allycreep|self|none|point x y|x y|0x<句柄>] [on|off|toggle|queue]
   ```
   - `allyhero` / `ally`：优先匹配附近友方英雄（若明确要套小兵/召唤物才用 `allycreep`）；同时尊重技能的 `targetSide`：`ALLY` 技在 `auto` 下找最需要增益/治疗的友军（或自身）；`BOTH` 技支持 `ally`/`enemy` 双选。
   - `point x y`：对 `DOTA_SKILL_TARGET_UNIT_OR_POINT`（如 `A0X5`/`A0X7`/`A06I`）支持按玩家明确意图或策略走 `0x11` 点地（破林肯/预判位置）。
   - `on` / `off` / `toggle`：读取 `orderOnId` / `orderOffId` / `unorderId` 发出 `Action 0x10`。
   - `queue`：构造动作包时置位 **`Flags |= 0x0001`**（Shift 队列连招），不破坏当前正在引导或移动的命令！
2. **智能前摇 / 引导释放锁（取代固定 `guardMs`）**：
   - 发包后在 `aiTickPendingCast` 结合 **`GetUnitCurrentOrder(hero)`** 与目标 `ability.cooldownRem > 0` 监测：只要技能已进入冷却或当前 `orderId` 回落为 idle/move/attack（且非黑洞/冰雨/沙尘等 Channel 中），提前解锁补刀与走位；反之对正在持续引导（Channeling）的大招绝不被普通 `S` 或走位打断（除非紧急撤退或明确 `queue`）。

### Phase 4：战术 AI 自动施法决策层（消费 10ms 状态上报 + 实时探针）

- **对线法球消耗（不拉仇恨）**：对拥有 `AEpa` / `ANpa` 类法球的英雄（小黑、毒龙、神灵、骨弓、沉默、黑鸟），自动使用 `0x12` 单发指定敌方英雄，绝不开自动施法盲平 A；
- **控场与斩杀**：判断敌方处于引导/回城或可被一套带走时，连招先手（或与跳刀/吹风搭配通过 `Flags |= 0x0001` 零帧衔接）；
- **救死与增益（`ALLY` 技）**：监测血量危急队友触发全能洗礼、暗牧薄葬、死骑无光之盾、神谕大招、黑鸟关救人；
- **瞬发无痛切换（`0x02000000`）**：开腐烂/脉冲新星贴身追击、脱离交战或蓝量告急即时发 `0xD00D2` / `0xD026E` 关闭，不再傻烧到死。

---

## 七、后续验证方案（仅当实施编码阶段开启后执行）

1. **编译与同步**：修改完代码后按规范执行 `D:\Qt\workspace\sync_war3run.bat` 编译 `War3Bot` / `War3Launcher` 并增量同步至 `C:\War3Run`；若改动 `War3Server/src/bnetd/command.cpp` 则重编并重启 `bnetd.exe`。
2. **实机对抗用例矩阵（`Scripts\Start-AiGame.ps1` 验证）**：
   - **常规 4 槽与实时探针**：`-hero cm` / `-skills`，验证冷却倒计时、不够蓝（`0xD1`）、冷却中拦截（`0xD2`）、真技能点 `+0x90`。
   - **修正表边界案例**：`-hero sf` 验证影魔 **Z/X/C 三炮** + **魂之挽歌 `0xD0131`**；`-hero morph` 验证水人 **敏/力转 `0x10` 开关**与 **复制 `0x12`**；`-hero techies` 验证埋雷 `0x11`；`-hero ns` 验证黑暗时间 `0x10`；确认敌法/屠夫/小猴/毒龙 4 个 `AIdd` 被动不再报错可放。
   - **友方目标与双模式**：全能 `A08N` / 死骑 `A0MF` / 巫妖 `A08R` `-cast 1 auto` 自动加队友或自身、`-cast <slot> allyhero` 精确锁定队友；莱恩穿刺 `-cast 1 point x y` 走 `0x11` 绕过林肯。
   - **动态链表与连招**：`-hero invoker` / `-hero puck` / `-hero kunkka` 验证 `-skills` 自动发现 `CUnit + 0x1DC` 下动态技能，并用 `-cast <slot> queue` 测试 `Flags |= 0x0001` Shift 队列连招。
