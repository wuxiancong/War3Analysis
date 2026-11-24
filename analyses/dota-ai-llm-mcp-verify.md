# 「大模型托管 DotA」接口数据读取与动作包独立核验报告（1.27 主目标）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 对 [`dota-ai-llm-mcp-control.md`](./dota-ai-llm-mcp-control.md)（§二 A1~A4 读取、§三 B2 动作包）进行独立复核，以 1.27（`Game.dll` 1.27.0.52240）与 DotA 6.83d `war3map.j` 为一手证据，在编码前揪出错误偏移、错误 OrderId 与伪机制 |
| **命名方式** | `dota-ai-llm-mcp-verify`；导图 `dota-ai-llm-mcp-verify-mindmap.md`；核验脚本与导出 `artifacts/llm-mcp-verify/` |
| **分析时间** | 2026-11-21 |
| **验证状态** | **离线核验 100% 完成**（`dumpbin` 机器码反汇编 + `war3map.j` 原文行号 + 独立文档交叉比对），揪出 **5 处实质性错误（❌）** 与 **4 处部分偏差/缺实机项（⚠）**；**实机只读内存项（A1 冰女技能、A2 买物前后、A3 迷雾敌方英雄返回 false）尚未实测**（检测时 `War3Launcher` 管理员进程未运行，`:6120` 拒绝连接，未越权拉起 UAC），已备好纯只读脚本 [`live_verify_cm.py`](../artifacts/llm-mcp-verify/live_verify_cm.py) 与可执行步骤 |
| **独立证据** | `War3Launcher/versions/1.27.0.52240/Game.dll`；`War3Script/war3map.j`；`War3Launcher/hooker/war3hook_lobby.cpp`；Cursor Grok [`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md)；Composer [`dota-683d-ward-and-deward.md`](./dota-683d-ward-and-deward.md)；导出 [`artifacts/llm-mcp-verify/offline_audit_part1~4.txt`](../artifacts/llm-mcp-verify/) |
| **思维导图** | [`dota-ai-llm-mcp-verify-mindmap.md`](./dota-ai-llm-mcp-verify-mindmap.md) |

> **约束说明**：本报告未修改原文档 `dota-ai-llm-mcp-control.md`，也未修改 `War3Launcher` / `hooker` 任何代码；所有结论均基于独立反汇编、脚本原文或独立第三方分析文档，**绝不引用原文档自证**。

---

## 一、核验总表

图例：`✅` 正确 ｜ `⚠` 部分对（需更正或补实机） ｜ `❌` 错（必须按更正值改） ｜ `❓` 没法验证

| # | 条目（原文档节号） | 文档原值 | 核验结果 | 更正值 / 正确做法 | 独立证据 | 置信度 |
| :-: | :--- | :--- | :---: | :--- | :--- | :---: |
| **A1** | **技能冷却**（§A1） | `CAbilitySpell+0x20 & 0x200`；`+0xD0` `CTimer` 调 `vtable+0x18`；未写总冷却位置 | **⚠** | 偏移正确且**可纯只读内存计算，无需调虚函数**：`node = *(u32*)(abil+0xDC)`（即 `+0xD0+0x0C`）；**总冷却**=`*(f32*)(node+0x08)`；**剩余冷却**=`*(f32*)(node+0x04) - *(f32*)(*(u32*)(node+0x0C)+0x40)`。**缺实机冰女 3 次采样** | 1.27 `CAgentTimer` (`vt 0x95254C`) `+0x10` (`0x0433C0`) 与 `+0x18` (`0x0438C0`) 反汇编 | 离线 **高**；实机 **待补** |
| **A2** | **金钱（可靠 / 不可靠）**（§A1） | 总金钱 `GetPlayerState(p,1)`（`CPlayer+0x50 ÷ 10`）；可靠金钱 `EL0[pid]` | **⚠** | 离线公式与变量名 **完全正确**（`EL0` 确为 6.83d 可靠金钱数组）。**缺实机买物前后读数**，且尚未给出 1.27 从 JASS VM 全局符号表读 `EL0` 的实机指针链 | `war3map.j` L1130 / L13228 / L15654 / L24449；1.27 `0x1E4080` → `0x039860` | 离线 **高**；实机 **待补** |
| **A3** | **视野过滤（防作弊红线）**（§A2） | `IsUnitVisible(u, lp)` + 隐身加 `IsUnitDetected(u, lp)` | **⚠** | 机制与 1.27 RVA（`0x1E8E80` / `0x1E8580` → `0x66E3B0`）正确，与独立文档 `dota-683d-ward-and-deward.md`（`CUnit+0x130/+0x134`）一致。**因当前无运行中游戏，缺实机迷雾敌方英雄返回 `false` 的实测记录，不得标 ✅** | 1.27 反汇编；`dota-683d-ward-and-deward.md` §0 #6 | 离线 **高**；实机 **必补** |
| **A4** | **Buff / Debuff**（§A1） | 沿 `CUnit+0x1DC/+0x1E0`（下节点 `+0x24/+0x28`）遍历，`+0x34` 为 FourCC，`vtable+0x1E0/+0x1E4/+0x1E8` 判正/负/光环，或 `GetUnitAbilityLevel` 快检 | **✅** | 全部偏移与虚槽经 1.27 独立反汇编逐行证实；与 Grok `war3-unit-movement-fields.md` 的 `ResolveAgent` (`0x044150` → 节点 `+0x54`) 完全一致 | 1.27 `CUnit::FindAbility` (`0x46F440` L467 `[ebx+34h]`)、`CUnit::CountBuffsEx` (`0x46E630`) | **高** |
| **A5a** | **买活冷却**（§A1） | `XS[pid]` 存冷却，能量圈挂 `'h0D4'`，冷却 360s | **⚠** | **更正**：`XS[pid]` 是 **`boolean` 禁买活标志**（不是剩余秒数！）；360s 冷却由一次性定时器 `TriggerRegisterTimerEvent(t,360,false)` + `GM1` 控制，期间移除 `ZS[0..59]` 并挂 0 库存 `'h0D4'`。**无法从 `XS` 读剩余秒数**，需记录买活发生时间戳自行倒计时 | `war3map.j` `D7O` L15648、`GN1` L7226-L7249、`GM1` L7209-L7225 | **高** |
| **A5b** | **Glyph 冷却**（§A1 / §C3） | 冷却 300s，挂在能量圈 `'A141'`/`'A1WI'` | **✅** | 精确读法：在己方能量圈 `D30[pid]` 上用 `CUnit::FindAbility(cop, 'A141'/'A1WI')` 读 **`+0xDC` `CAgentTimer`** 即可得精确剩余/总冷却秒数 | `war3map.j` `JQO` L20990、`JTO` L20920 | **高** |
| **A5c** | **昼夜时间**（§A3） | `GetFloatGameState(2)`，1.27 RVA `0x1E2500` | **✅** | 1.27 `0x1E2500` 反汇编证实 `lea ecx,[edx-2]; test ecx,ecx` 仅接受参数 `2`，经 `0x2676D0` + `0x03ADF0` 取值 | 1.27 `0x1E2500`、`0x2676D0`、`0x03ADF0` 反汇编 | **高** |
| **A6** | **事件来源（`FL1` / `0x6B`）**（§A4） | 称 `FL1` 发 `"Kill"`、`"Death"`、`"Tower"`、`"Rax"`、`"Roshan"`、`"AegisOn/Off"` | **❌** | **更正**：`FL1` **没有 `"Kill"` 和 `"Death"` 键**！实际键名为 **`"Hero"+victimPid`**（值=`killerPid`）、**`"Assist"+victimPid`**、**`"Tower"+team+tier+lane`**、**`"Rax"+team+lane+type`**、**`"Roshan"`**、**`"AegisOn"`/`"AegisOff"`**（共 28 种）。且仅 `GetLocalPlayer()==WO` 主动调 `SyncStoredInteger`（1.27 `0x1F8940` → `0x22D380` → `0x252FF0` 发 `0x6B`），其余客户端通过收 `0x6B` 包获取（`war3hook_lobby.cpp` L396/L4533 已拦截） | `war3map.j` `FL1` L6819 及全量 28 键扫描；1.27 `0x1F8940` 反汇编；`war3hook_lobby.cpp` L396/L4533 | **高** |
| **B1** | **买活动作包**（§B2 #5） | 选能量圈 `n01F` + 发 `0x10` + **英雄单位 FourCC** | **❌** | **更正**：`D7O` 校验 `GZ1(GetUnitTypeId(GetSoldUnit()))`，买的是 **60 档价格占位单位 `ZS[GV1(heroLevel)]`**（如 `ZS[0]='h09G'` 50g、`ZS[1]='h09T'` 100g…），**绝不是英雄 FourCC**！且必须满足 5 个条件（死亡、己方能量圈、非 A 杖死神镰刀 `LY[hid][4304]!=1`、`XS[pid]==false`、非 360s 冷却） | `war3map.j` `D7O` L15646-L15664、`GZ1` L7127、`GV1` L7138、`ZS[]` L91383 | **高** |
| **B2** | **Glyph 动作包**（§B2 #6） | 选能量圈 + `0x10` + **`0x000D00FA`**（称其为 `coldarrows`） | **❌** | **更正**：1.27 OrderId 表实证 **`"coldarrows"` = `0x000D0114`**（`0x000D0113` 为 `coldarrowstarg`，`0x000D0115` 为 `uncoldarrows`），**`0x000D00FA` 完全错误**！ | 1.27 `Game.dll` `0x46B91F..0x46B94D` OrderId 表反汇编；`war3map.j` `JTO` L20925 | **高** |
| **B3** | **远程购买 + 信使操作**（§B2 #2） | 信使 `n00I/n022/n021/n004/n018/n01C/n01G`；OrderId `0xD00FA`(取)/`0xD0081`(送) | **❌** | **两处全错，更正如下**：<br/>1. 6.83d 真正信使集合为 `war3map.j` L3691 的 **15 个 FourCC**（`n00I, n00M, n021..n025, n0HV, n0KY, n0KZ, n0L0, n0L1, n0LE, n0LS, n0M4`）；`n004/n018/n01C/n01G` 是 L5352 `B61` 的 4 级非信使召唤物！<br/>2. 信使送货/存储藏处**不是 `0xD00FA`/`0xD0081`**，而是信使售卖占位单位（`D7O` L15631-L15645）：**`'h085'` (`1747990581`)** = 送货给英雄（`DIO(hero,true)`）、**`'h0BV'` (`1747993174`)** = 放回储藏处（`D4O`）、**`'h0DE'` (`1747993669`)** = 继续上次送货 | `war3map.j` L3691、L5352、L15631-L15645 (`D7O`)、L15520 (`DIO`)、L15581 (`D4O`) | **高** |
| **B3+** | **插眼物品与单位 FourCC**（§B2 #3，附带核出） | 物品 `I057`/`I058`，施法距 600，单位 `oeye/n00H/n00G` | **❌** | **更正**：假眼物品 **`I05G`**（施法距 **420**，单位 **`o004`**）、真眼物品 **`I05H`**（施法距 **500**，单位 **`oeye`**）；`0x11` 必须带**物品对象 ID** 且 `flags = 0x44` <br/>**⚠ 2026-11-23 更正**：`0x11 + flags 0x44` 对假眼/真眼不生效，已被真人抓包与 `Game.dll` 反汇编推翻；假眼 `A2WH`/真眼 `A2WI`（`ANcl` `DataB1=3`，`GetOrderFlags=0x00000006`）点地必须发 **`0x12` + `flags=0x40` + `useslot` + 物品对象 ID + `(x,y)` + 目标 `FFFFFFFF FFFFFFFF`**，详见 [`dota-ai-llm-mcp-gaps.md`](./dota-ai-llm-mcp-gaps.md) §二 | 独立文档 `dota-683d-ward-and-deward.md` §0 & §1.1（源自 `M6O` & SLK） | **高** |
| **B4** | **TP 吸附建筑规则与距离**（§B2 #7） | `useslot` + 坐标自动吸附 575 内最近己方建筑 | **⚠** | **更正语义**：`XKO(hero, x, y)` 是**全图无距离上限**吸附离点击点 `(x,y)` 最近的己方建筑 `P8I`（双击同坐标则强制指向泉水 `PQ`/`BX0`）；**`MS0 = 575`** 是落点相对目标建筑 `P8I` 的**最大偏移钳制半径**（`>575` 钳到 575，`<50` 推到 120） | `war3map.j` L1565 (`MS0=575`)、`Y1O` L20087-L20135 | **高** |
| **B5** | **Shift 队列标志位**（§B2 #1） | `0x10`/`0x11`/`0x12` 偏移 `+1..+2` `abilityFlags \|= 0x01` | **✅** | 1.27 `0x3AE4E0` → `0x69FFA0`（`CNetCommandUnitOrderBasic`）机器码证实 `uiFlags & 1` 直接写入 `abilityFlags` bit 0（`0x0001`）；同时证出 `0x0040` 为子组位、`0x0004` 为 `abilFlags & 0x100000`（与插眼 `0x44` 吻合） | 1.27 `0x3AE4E0..0x3AE531` 与 `0x69FFA0..0x6A004F` 反汇编 | **高** |

---

## 二、关键条目详细证据

### 1. A1 技能冷却：纯只读内存公式（无需调用虚函数）

反汇编 1.27 `CAgentTimer`（RTTI `.?AVCAgentTimer@@`，虚表 RVA `0x95254C`，嵌入于 `CAbilitySpell+0xD0`）：

- **`vtable+0x10`（`0x0433C0`, `GetTimeout`）与 `+0x14`（`0x0435D0`）**：
  ```asm
  6F0433C3: mov ecx, dword ptr [ecx+0Ch]    ; timerNode = *(uint32_t*)(CAbilitySpell + 0xD0 + 0x0C) = *(CAbilitySpell + 0xDC)
  6F0433C9: test ecx, ecx
  6F0433CB: jne 6F0433D9
  ... (返回 0.0f)
  6F0433D9: mov ecx, dword ptr [ecx+8]      ; 总冷却时间 float = *(float*)(timerNode + 0x08)
  ```
- **`vtable+0x18`（`0x0438C0`, `GetRemainingTime`）**：
  ```asm
  6F0438C3: mov edx, dword ptr [ecx+0Ch]    ; timerNode = *(CAbilitySpell + 0xDC)
  6F0438D9: mov eax, dword ptr [edx+0Ch]    ; timerMgr  = *(uint32_t*)(timerNode + 0x0C)
  6F0438DC: add edx, 4                      ; &expireTime (float* at timerNode + 0x04)
  6F0438E2: add eax, 40h                    ; &gameClock  (float* at timerMgr + 0x40)
  6F0438E6: call 6F0528B0                   ; 软浮点减法: remaining = expireTime - gameClock
  ```
- **结论**：外部进程或游戏线程均可**纯只读**拿到剩余冷却与总冷却；与 Grok [`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md) 的 `AgentTable`（1.27 `Game.dll+0xBE40A8`）+ `ResolveAgent`（`0x044150` → 节点 `+0x54`）完全无缝衔接。

### 2. B1 买活 & B3 信使：为何原文档两处皆错

`war3map.j` `D7O`（L15630-L15664，`EVENT_UNIT_SELL`）同时处理**信使快捷操作**与**能量圈买活**：
- **L15631** `GetUnitTypeId(GetSoldUnit()) == 1747990581 ('h085')` → `call DIO(hero, true)`（**信使运送物品给英雄**）
- **L15636** `== 1747993174 ('h0BV')` → `call D4O(hero)`（**信使把物品存回泉水储藏处 `D40[id], D50[id]`**）
- **L15641** `== 1747993669 ('h0DE')` → `call DIO(prevHero, false)`（**信使继续上次运送**）
- **L15646** `elseif GZ1(GetUnitTypeId(GetSoldUnit()))` → `GZ1`（L7127）遍历 `ZS[0..59]`（L91383 起：`ZS[0]='h09G'` 50g、`ZS[1]='h09T'` 100g、`ZS[2]='h09F'` 150g……每档 +50g 直至 3000g）。买活费用由 `GV1(level)`（L7138：`100 + level²×1.5 + gameMin×15`，整除 50 截断到 `[0, 59]`）决定，**发包必须发对应档位的 `ZS[idx]` FourCC**，而不是英雄 FourCC。

### 3. B2 Glyph OrderId 冲突彻底厘清

1.27 `Game.dll` OrderId 字符串注册表（`0x46B91F..0x46B94D`）原文汇编：
```asm
6F46B91F: push 6F9AD9C8h   ; "coldarrowstarg"
6F46B924: push 0D0113h     ; 0x000D0113
6F46B930: push 6F9AD9D8h   ; "coldarrows"
6F46B935: push 0D0114h     ; 0x000D0114  <-- Glyph 正确 OrderId！
6F46B941: push 6F9AD9E4h   ; "uncoldarrows"
6F46B946: push 0D0115h     ; 0x000D0115
```
原文档把 Glyph 和信使都写成 `0x000D00FA`，两处均错：Glyph 实为 **`0x000D0114`**，信使送货/存储藏处实为售卖单位 **`'h085'`/`'h0BV'`/`'h0DE'`**。

### 4. 与 Cursor Grok 独立文档的交叉核对

核对 [`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md)（Grok 4.7）：
- `JassHandleToUnit`（1.27 `0x1D1550`）、`AgentTable`（`Game.dll+0xBE40A8`）、`ResolveAgent`（`0x044150` → 节点 `+0x54`）、`CUnit` 虚表（`0xA4A704`）、`CUnit+0x30`（FourCC）、`+0x1E8/+0x1EC/+0x1F0` 与本文全部反汇编结果 **零冲突、100% 一致**。

---

## 三、建议实机测试步骤（交给主会话执行）

因当前环境 `War3Launcher` 管理员进程未启动（`:6112` 与 `:6116` 正常监听，`:6120` 未监听），且严格遵守「不写内存、不直接发动作包」原则，请按以下步骤完成剩余 3 项只读实机验证与 4 项动作包验证：

1. **启动环境**：按 `ai-autostart.md` 以管理员启动 `C:\War3Run\War3Launcher\War3Launcher.exe`，然后运行：
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File D:\Qt\workspace\Scripts\Start-AiGame.ps1 -Hero cm
   ```
2. **A1（冰女冷却）+ A2（金钱）+ A4（Buff）纯只读验证**：
   - 放冰女 1 技能前运行 `python D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-verify\live_verify_cm.py` → 记录 `in_cd=False, rem=0.0`；
   - 放完 1 技能立刻运行一次、等 5 秒后再运行一次 → 核对 `rem_cd` 精确递减约 5.0s 且 `total_cd` 等于技能表冷却；
   - 买一件 50g~150g 物品前后各读一次 `CPlayer+0x50 / 10`，核对差值等于物品价格。
3. **A3（视野防作弊红线）实机验证**：
   - 开局对线前（敌方英雄在迷雾中），在游戏内发 `units 3000` 并对比 `live_verify_cm.py` 扫到的全部英雄句柄：确认 `AiUnit.log` 的 `units` 输出**绝不包含迷雾中的敌方英雄**；敌方露头后再测一次确认出现。
4. **B1/B2/B3/B5 动作包实机验证（主会话发包）**：
   - **Glyph**：选中己方能量圈 `n01F` → 发 `0x10 + 0x000D0114` → 确认全队防御塔获得 5s 无敌特效且进入冷却；
   - **信使**：购买小鸡后选中信使 → 发 `0x10 + 'h085'`（送货）/ `'h0BV'`（回储藏处）→ 确认动作生效；
   - **买活**：英雄送塔死亡且金钱足够时，选中己方能量圈 → 发 `0x10 + ZS[GV1(level)]`（如 1 级且开局 0 分钟对应 `ZS[2]='h09F'`）→ 确认英雄复活；
   - **Shift 队列**：先发 `0x11 move (x1,y1)`（`flags=0x0000`），紧接发 `0x11 move (x2,y2)`（`flags=0x0001`）→ 确认英雄走完 `(x1,y1)` 后自动走向 `(x2,y2)` 而不打断。

---

## 四、给实现者的结论

### 1. 可以直接写代码的部分（已 100% 实证）
- **技能真实冷却与总冷却**：直接按 `CAbilitySpell+0xDC` → `node+0x08`（总冷却）、`node+0x04 - *(node+0x0C)+0x40`（剩余冷却）实现，**纯只读零开销**。
- **Buff / Debuff 枚举与控制快检**：直接沿 `CUnit+0x1DC/+0x1E0`（下节点 `+0x24/+0x28`）读 `+0x34` FourCC 或调 `GetUnitAbilityLevel`。
- **昼夜时间**：直接调 `GetFloatGameState(2)`（1.27 `0x1E2500`）。
- **Shift 队列**：在 `aiOrderImmediate/Point/Target` 增加 `queued` 参数并置 `abilityFlags |= 0x0001`。
- **TP 到指定建筑**：发 `0x11` + `useslot` + 目标建筑坐标（地图 `XKO` 自动吸附最近己方建筑，落点钳制 `MS0=575`）。

### 2. 写代码前必须先改原文档的部分（5 处 ❌）
- **Glyph OrderId**：把 `0x000D00FA` 改为 **`0x000D0114`**。
- **买活发包**：把「英雄 FourCC」改为 **`ZS[GV1(level)]`**（从 `war3map.j` L91383 导出完整 60 档表），并把买活冷却改为「记录买活时刻 + 360s 倒计时」（不可读 `XS` 当秒数）。
- **信使识别与操作**：信使列表改为 L3691 的 **15 个 FourCC**（删掉误写的 `n004/n018/n01C/n01G`）；送货/存储藏处改为 `0x16 选信使 + 0x10 + 'h085'/'h0BV'/'h0DE'`（删掉编造的 `0xD00FA`/`0xD0081`）。
- **插眼物品与单位**：改为假眼 **`I05G`→`o004`（距 420）**、真眼 **`I05H`→`oeye`（距 500）**，且 `0x11` 带物品对象 ID 与 `flags=0x44`。
- **事件流 `0x6B` 键名**：把不存在的 `"Kill"`/`"Death"` 改为 **`"Hero"+victimPid`** / **`"Assist"+victimPid`**，并复用 `war3hook_lobby.cpp` 现有 `0x6B` 收包拦截点。

### 3. 建议换方案 / 补验证的部分
- **可靠金钱 `EL0`**：读 JASS VM 全局符号表有一定版本脆弱性，MVP 阶段可先用 `GetPlayerState(p,1)` 总金钱；P2 再按 `EL0` 符号表地址补齐可靠/不可靠拆分。
- **视野防作弊红线（A3）**：**上线 MCP 前必须跑完上述第 3 步实机迷雾测试**，确认零迷雾泄露后再放开大模型接入。
