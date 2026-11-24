# 大模型托管 DotA 6.83d：逆向缺口补齐（G1–G4）与 RemoteControl/MCP 原型设计（G5）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 补齐 [`dota-ai-llm-mcp-control.md`](./dota-ai-llm-mcp-control.md) 与 [`dota-ai-llm-mcp-verify.md`](./dota-ai-llm-mcp-verify.md) 的 5 项缺口（G1 全 11 版内部函数表、G2/G3 点地物品/技能 `0x11` vs `0x12` 与 `flags 0x40/0x44` 根因规则、G4 JASS VM 全局变量只读指针链、G5 RemoteControl 结构化 `state` 命令设计与 MCP Server 原型） |
| **命名方式** | `dota-ai-llm-mcp-gaps`；导图 `dota-ai-llm-mcp-gaps-mindmap.md`；扫描脚本与导出 `artifacts/llm-mcp-gaps/`；MCP Server 原型 `artifacts/llm-mcp-server/` |
| **分析时间** | 2026-11-23 |
| **验证状态** | **离线静态反汇编与 MCP 离线单元测试全部通过**（`dumpbin` 覆盖 `War3Launcher/versions` 下全部 11 个 `Game.dll`；MCP Server 6 项离线单元测试 + 工具注册全通过）；**实机未测**（遵守红线：未启动 war3，未连 `127.0.0.1:6120`，未改 `War3Launcher`/`hooker` 源码） |
| **证据目录** | `artifacts/llm-mcp-gaps/`（`g2_g3_final11.*`、`g4_g1_all11.*`、`probe_g2_g3_*.txt`、`probe_g4_layout_127.txt`）、`artifacts/llm-mcp-server/` |
| **思维导图** | [`dota-ai-llm-mcp-gaps-mindmap.md`](./dota-ai-llm-mcp-gaps-mindmap.md) |

---

## 一、核心结论总览（先看这里）

| 缺口 | 核心结论 | 状态 / 置信度 |
| :---: | :--- | :---: |
| **G2 + G3** | **点地发 `0x11` 还是 `0x12`、flags `0x40` 还是 `0x44`，100% 由该技能的 `CAbility::GetOrderFlags()`（`vtable[+0x30C]`）决定**：<br/>1. 玩家点击空地时，UI 分流函数（1.27 `0x3A4CCB`）判断 `targetTypeMask = GetOrderFlags() & 0x3FF`：<br/>   - **`== 0x02`（纯点地）** → 发 **`0x11`**（`CNetCommandUnitOrderTargetPoint`）：**跳刀 `I04H` (`AEbl`)**、**TP `A1R5` / 飞鞋 (`ANto`)**、血精石、纷争面纱。<br/>   - **`== 0x06`（点地或单位）** → 即使点空地，也强制 `targetWidget = NULL` 发 **`0x12`**（`CNetCommandUnitOrderTargetObject`，目标对象填 **`FFFFFFFF FFFFFFFF`**）：**假眼 `I05G` (`A2WH`)**、**真眼 `I05H` (`A2WI`)**。<br/>2. **`flags` 的 `0x04` 位**来自 `(GetOrderFlags() >> 18) & 4`（即 `GetOrderFlags() & 0x00100000`）：<br/>   - `AEbl` / `ANto` 返回 `0x00100002`（含 `0x00100000`）→ **`flags = 0x44`**。<br/>   - `ANcl`（`CAbilityChannel`，1.27 `0x49F230`）**不置 `0x00100000`** → 假眼/真眼（`0x00000006`）与推推棒 `I0HI`（`0x00000004`）均为 **`flags = 0x40`**！<br/>3. **好消息**：现有 `hooker` 对 TP、跳刀发 `0x11 + 0x44` **恰好与真人完全一致**，仅假眼/真眼（`ANcl DataB1=3`）必须发 `0x12 + 0x40 + FFFFFFFF FFFFFFFF`（已由 `dota-ai-laning-routine.md` 实机验证）。 | 离线 **高**（11 版汇编 + SLK 实证）；假眼实机已证；TP/跳刀/推推实机 **待测** |
| **G4** | **JASS VM 全局变量只读指针链**（以 `EL0[pid]` 可靠金钱、`XS[pid]` 禁买活为例）：<br/>`g_jassEnv` → `vmIndex = *(g_jassEnv + 0x08)` → `tls = GetTlsSlot(5)` → `vm = *(uint32_t*)(*(tls + 0x90) + vmIndex * 4)` → `globalTable = *(vm + 0x285C)`（`1.24.1~1.27.0`；`1.0.17~1.23.0` 为 **`+0x2858`**）→ 遍历 `TSHashTable`（`buckets = +0x1C`, `mask = +0x24`, 每桶 12B）找 `strcmp(*(char**)(node+0x14), name)==0` → `arr = *(node+0x20)` → 校验 `pid < *(arr+0x08)` 后读 `*(uint32_t*)(*(arr+0x0C) + pid*4)`。<br/>**线程与阶段红线**：必须在**游戏主线程且 `SceneState::GamePlaying`** 阶段只读；读图阶段 `game.dll+0x2BD982` 实证因核心对象未初始化空指针解引用崩溃，且 `globalTable` 可能正在 rehash。 | 离线 **高**（1.22~1.27 完整实证；1.0.17~1.21.0 `GetVM/TlsSlot` 标 ❓）；实机 **待测** |
| **G1** | **补全全部 11 个版本的内部函数与偏移表**：<br/>- `CAgentTimer` 虚表、`GetTimeout(+0x10)`、`GetRemainingTime(+0x18)` 及纯只读公式（`+0x0C/+0x08/+0x04/+0x40`）已覆盖 `1.22.0~1.27.0` 全 7 版（1.0.17~1.21.0 无 RTTI 标 ❓）。<br/>- **纠正旧文档误判**：`1.0.17~1.21.0` 的 `CAbilitySpell::ResetCooldown` 与 `ResolveAgent` 均已找回并反汇编证实——早期 4 版**同样是 `+0x20 & 0x200` + `+0xD0` `CAgentTimer` + `vtable+0x18`**，并非「早期布局不同」！ | 离线 **高**（11 版汇编核验；无证据项已标 ❓） |
| **G5** | 1. **MCP Server 原型已建成并通过 6 项离线单元测试**（`artifacts/llm-mcp-server/`，Python 官方 `mcp` SDK `FastMCP` + `stdio`，仅复用现有 RemoteControl 命令，零修改 `War3Launcher`/`hooker`）。<br/>2. **提供 `gamestate`（RemoteControl 结构化 JSON 命令）完整设计**，每个字段精确到 `hooker` 源码 `文件:行号`，并指出 `AiControlManager.cpp:L308` 已将 `state` 路由为 `status` 别名、以及 `aiDumpUnits` 未做视野过滤的安全缺口。 | 离线单元测试 **6/6 通过**；实机 **未测** |

---

## 二、G2 + G3：点地物品 / 技能的 `0x11` vs `0x12` 与 `flags 0x40/0x44` 完整规则

### 2.1 根因反汇编实证（1.27 `Game.dll`）

#### (1) UI 点地分流：`targetTypeMask == 0x02` 发 `0x11`，`== 0x06` 发 `0x12` 加 `FFFFFFFF FFFFFFFF`

反汇编 1.27 `0x3A4B53..0x3A4D1C`（以及 `0x3A12C4`、`0x3A6614`、`0x3A6EFA` 共 4 处同构点地路径）：

```asm
; 1. 读取当前技能/物品按钮的 GetOrderFlags() 缓存值 [edi+14h]
6F3A4B53: mov  eax, dword ptr [edi+14h]      ; abilFlags = CAbility::GetOrderFlags()
6F3A4B5F: and  eax, 3FFh                     ; targetTypeMask = abilFlags & 0x3FF
6F3A4B64: mov  dword ptr [ebp-24h], eax

; 2. switch (targetTypeMask) 跳转表 0x3A4E88 / 索引表 0x3A4E98：
;    case 0 (-> 0x3A4C76): 0x02 (Point), 0x06 (Point | Unit)  <-- 仅这两种允许点地！
;    case 1 (-> 0x3A4C29): 0x04 (Unit Only)
;    case 2 (-> 0x3A4D66): 0x100 (Build / Drag)

; 3. 玩家点击空地（无目标单位），在 0x3A4CCB 决定发 0x11 还是 0x12：
6F3A4CCB: cmp  dword ptr [ebp-24h], 2        ; 是否为「纯点地」(0x02)？
6F3A4CD6: push ebx                           ; uiFlags (常规操作含 bit2=0x04 -> 包内 0x40)
6F3A4CD7: push dword ptr [edi+14h]           ; abilFlags (bit20=0x00100000 -> 包内 0x04)
6F3A4CDA: jne  6F3A4CFC                      ; != 2 (即 0x06 点地或单位) -> 跳去发 0x12！

; 分支 A: targetTypeMask == 0x02 -> 发 0x11 (CNetCommandUnitOrderTargetPoint)
6F3A4CF5: call 6F3AE540                      ; SendUnitOrder_0x11 -> EnqueueOrder_0x11 (0x69FCD0)
6F3A4CFA: jmp  6F3A4D1C

; 分支 B: targetTypeMask == 0x06 -> targetWidget = NULL (0) -> 发 0x12 (CNetCommandUnitOrderTargetObject)
6F3A4CFC: push 0                             ; targetWidget = NULL！
...
6F3A4D17: call 6F3AE660                      ; SendUnitOrder_0x12_XY -> EnqueueOrder_0x12_XY (0x69FEB0)
```

在 `EnqueueOrder_0x12_XY`（1.27 `0x69FEB0`）中，当 `targetWidget == NULL`（`[ebp+10h] == 0`）时：
```asm
6F69FF2D: mov  eax, dword ptr [ebp+10h]      ; targetWidget
6F69FF30: test eax, eax
6F69FF32: je   6F69FF39
...
6F69FF39: or   ecx, 0FFFFFFFFh               ; targetObj1 = 0xFFFFFFFF
6F69FF48: or   eax, 0FFFFFFFFh               ; targetObj2 = 0xFFFFFFFF
```
**这就是真人插眼抓包中「`0x12` + `(x, y)` + 目标 `FFFFFFFF FFFFFFFF`」的精确来源！**

#### (2) `flags 0x40` vs `0x44` 的位拼装来源

反汇编 `SendUnitOrder_0x11`（1.27 `0x3AE540`）与 `SendUnitOrder_0x12_XY`（1.27 `0x3AE660`），两者对 `abilityFlags` 的计算完全一致：
- 输入：`ecx = abilFlags`（`CAbility::GetOrderFlags()`），`edx = uiFlags`（来自 UI 状态）。
- 输出 16 位 `abilityFlags` 各位含义：
  - `bit 0` (`0x0001`) = `uiFlags & 1`（**Shift 队列**）
  - `bit 1` (`0x0002`) = `(uiFlags >> 1) & 1`
  - **`bit 2` (`0x0004`) = `(abilFlags >> 18) & 4`**（即 **`(abilFlags & 0x00100000) != 0`**！）
  - `bit 3` (`0x0008`) = `(uiFlags >> 3) & 1`
  - `bit 4` (`0x0010`) = `(uiFlags >> 4) & 1`
  - `bit 5` (`0x0020`) = `(abilFlags >> 16) & 0x20`（即 `abilFlags & 0x00200000`）
  - **`bit 6` (`0x0040`) = `(uiFlags >> 2) & 1 << 6`**（编队/子组常规操作标记，玩家点选单英雄时默认置 1）
  - `bit 8` (`0x0100`) = `(abilFlags >> 3) & 0x100`（即 `abilFlags & 0x00000800`）

#### (3) `CAbilityChannel`（`ANcl`）vs `CAbilityBlink`（`AEbl`）vs `CAbilityTornado`（`ANto`）

反汇编 1.27 三个基类虚表的 `vtable[+0x30C]` (`GetOrderFlags`)：
- **`AEbl` (`CAbilityBlink`, 虚表 `0x9C38D0`, `+0x30C = 0x49F1F0`)**：`mov eax, 0x00100002; ret` → 纯点地 `0x02` + `bit 20` → **`0x11` + `flags=0x44`**。
- **`ANto` (`CAbilityTornado`, 虚表 `0xA078F8`, `+0x30C`)**：返回 **`0x00100002`** → 纯点地 `0x02` + `bit 20` → **`0x11` + `flags=0x44`**。
- **`ANcl` (`CAbilityChannel`, 虚表 `0x9B7744`, `+0x30C = 0x49F230`)**：
  ```asm
  6F49F23F: call 6F3F7470         ; 读 SLK DataB1 (TargetType)
  ; DataB1 == 0 -> 0x00000001 (No Target)
  ; DataB1 == 1 -> 0x00000004 (Unit Only)
  ; DataB1 == 2 -> 0x00000002 (Point Only)
  ; DataB1 == 3 -> 0x00000006 (Point | Unit)  <-- 注意：全程不置 0x00100000！
  ; 若 DataC1 & 2 (Targeting Image) -> |= 0x01000000
  ```
  因此所有基于 `ANcl` 的物品/技能（**假眼、真眼、推推棒**）都不含 `0x00100000`，发包时 **`flags = 0x40`**（非 `0x44`）！

### 2.2 物品 / 技能点地命令格式速查规则表

> **通用判据**：查物品首技能基类（`Units_AbilityData.slk` / `war3map.w3a`）的 `GetOrderFlags()`：
> - `targetTypeMask == 0x02` → 点地发 **`0x11`**；
> - `targetTypeMask == 0x06` → 点地发 **`0x12` + 目标 `FFFFFFFF FFFFFFFF`**，点单位发 **`0x12` + 目标 `(obj1, obj2)`**；
> - `targetTypeMask == 0x04` → 只能对单位/可破坏物发 **`0x12` + 目标 `(obj1, obj2)`**；
> - `flags = 0x40 | ((GetOrderFlags() & 0x00100000) ? 0x04 : 0)`（Shift 入队再 `| 0x01`）。

| 物品 / 技能 | 物品 FourCC | 首技能 & 基类 | `GetOrderFlags()` | 目标情形 | 正确动作包 | 正确 `flags` | 目标对象 ID | 验证状态 |
| :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :--- |
| **假眼（侦察守卫）** | `I05G` | `A2WH` (`ANcl`, `B=3`) | `0x00000006` | **点地插眼** | **`0x12`** | **`0x40`** | `FFFFFFFF FFFFFFFF` | ✅ 真人抓包 + 实机 3 局通过 |
| **假眼（递给队友）** | `I05G` | `A2WH` (`ANcl`, `B=3`) | `0x00000006` | 点友方英雄 | **`0x12`** | **`0x40`** | 队友 `(obj1, obj2)` | 离线实证（实机未测） |
| **真眼（岗哨守卫）** | `I05H` | `A2WI` (`ANcl`, `B=3`) | `0x00000006` | **点地插眼** | **`0x12`** | **`0x40`** | `FFFFFFFF FFFFFFFF` | 离线实证（SLK `DataB1=3` 与假眼同源；实机未测） |
| **回城卷轴（TP）** | `tpsc` | `A1R5` (`ANto`) | `0x00100002` | **对地** | **`0x11`** | **`0x44`** | （无目标字段） | 离线实证（地图 `XKO` 全图吸附最近己方建筑；实机未测） |
| **回城卷轴（TP）** | `tpsc` | `A1R5` (`ANto`) | `0x00100002` | **对己方建筑** | **`0x11`** | **`0x44`** | （无目标字段，传建筑坐标 `(x, y)`） | 离线实证（`ANto` 为纯点地 `0x02`，点塔同样走 `0x11`；实机未测） |
| **远行鞋（飞鞋）** | 飞鞋类 | `ANto` 基类 | `0x00100002` | 对地 / 对建筑小兵 | **`0x11`** | **`0x44`** | （无目标字段） | 离线实证（实机未测） |
| **科勒的匕首（跳刀）** | `I04H` | `AIbk` (`AEbl`) | `0x00100002` | **点地闪烁** | **`0x11`** | **`0x44`** | （无目标字段） | 离线实证（`AEbl` 返回 `0x00100002`；实机未测） |
| **原力法杖（推推棒）** | `I0HI` | `A19M` (`ANcl`, `B=1`) | `0x00000004` | **对单位（含自身）** | **`0x12`** | **`0x40`** | 目标/自身 `(obj1, obj2)` | 离线实证（纠正旧文档 `0x00100004` → `0x00000004`；实机未测） |
| **纷争面纱 / 血精石** | — | `AHbz` / `ANcl(B=2)` | `0x01100002` / `0x00000002` | 点地 | **`0x11`** | `0x44` / `0x40` | （无目标字段） | 离线实证（实机未测） |

> 注：以上所有物品命令**均须携带物品网络对象 ID**（`CItem+0x0C / +0x10`）与 `orderId = 0x000D0028 + slot`（`useslot1..6`）。普通英雄技能（非物品）同理遵循 `targetTypeMask == 0x02 → 0x11`、`0x06 → 0x12(NULL)`，区别仅在于物品对象 ID 填 `FFFFFFFF FFFFFFFF`。

### 2.3 全 11 个版本 `Game.dll` RVA 对照表（G2 + G3）

数据导出自 `artifacts/llm-mcp-gaps/g2_g3_final11.json`（`Send_0x12_XY` 为带 `(x, y, targetWidget)` 参数的 `0x12` 发送入口，区别于不带坐标的 `Send_0x12_TargetOnly`）：

| 版本 | `Send_0x10` | `Send_0x11` | `Send_0x12_XY` | `Enq_0x10` | `Enq_0x11` | `Enq_0x12_XY` | `UI_PointDispatch` (`0x11` / `0x12_NULL` 分流对) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `1.0.17.5988` | `0x140855`❓ | `0x140983`❓ | `0x140A97`❓ | `0x1E6230` | `0x1E63A0` | `0x1E67C0` | ❓（早期版入口未对齐，待手动核对） |
| `1.0.20.6048` | `0x140855`❓ | `0x140983`❓ | `0x140A97`❓ | `0x1E6230` | `0x1E63A0` | `0x1E67C0` | ❓（同上） |
| `1.20.4.6074` | `0x140865`❓ | `0x140993`❓ | `0x140AA7`❓ | `0x1E62A0` | `0x1E6410` | `0x1E6830` | ❓（同上） |
| `1.21.0.6263` | `0x1408C5`❓ | `0x1409F3`❓ | `0x140B07`❓ | `0x1E9460` | `0x1E95D0` | `0x1E99F0` | ❓（同上） |
| `1.22.0.6328` | `0x3390A0` | `0x339100` | `0x339210` | `0x2CADA0` | `0x2CAE60` | `0x2CB070` | `0x3737D4/0x3737EF`、`0x374054/0x37408E`、`0x37467D/0x374695` |
| `1.23.0.6352` | `0x33A620` | `0x33A680` | `0x33A790` | `0x2CC2E0` | `0x2CC3A0` | `0x2CC5B0` | `0x374D84/0x374D9F`、`0x375604/0x37563E`、`0x375C2D/0x375C45` |
| `1.24.1.6374` | `0x33A6E0` | `0x33A740` | `0x33A850` | `0x2CC3A0` | `0x2CC460` | `0x2CC670` | `0x374E44/0x374E5F`、`0x3756C4/0x3756FE`、`0x375CED/0x375D05` |
| `1.24.4.6387` | `0x33A7A0` | `0x33A800` | `0x33A910` | `0x2CC460` | `0x2CC520` | `0x2CC730` | `0x374F04/0x374F1F`、`0x375784/0x3757BE`、`0x375DAD/0x375DC5` |
| `1.25.1.6397` | `0x339A30` | `0x339A90` | `0x339BA0` | `0x2CB710` | `0x2CB7D0` | `0x2CB9E0` | `0x374194/0x3741AF`、`0x374A14/0x374A4E`、`0x37503D/0x375055` |
| `1.26.0.6401` | `0x339C60` | `0x339CC0` | `0x339DD0` | `0x2CB940` | `0x2CBA00` | `0x2CBC10` | `0x3743C4/0x3743DF`、`0x374C44/0x374C7E`、`0x37526D/0x375285` |
| `1.27.0.52240` | `0x3AE4E0` | `0x3AE540` | `0x3AE660` | `0x69FFA0` | `0x69FCD0` | `0x69FEB0` | `0x3A4CF5/0x3A4D17`、`0x3A663E/0x3A666D`、`0x3A6F26/0x3A6F51` |

---

## 三、G4：从 JASS VM 只读全局变量（`EL0` 可靠金钱 / `XS` 禁买活）

### 3.1 完整指针链与结构体布局（1.27 汇编实证）

从 `ExecuteFunc`（1.27 `0x1E0650`）→ `LookupJassFunc`（`0x1BF830`）→ `GetVM`（`0x7E1100`）→ `CreateGlobal`（`0x7E2DD0`）→ `TSHashTable::Find`（`0x7ECE50`）→ `JassArray::Ensure`（`0x7F1470`）逐级实证：

1. **取 JASS 环境与 VM 索引**：
   - `jassEnv = *(uint32_t*)(GameBase + g_jassEnv_RVA)`（1.27 `0xBE4238`）
   - `vmIndex = *(uint32_t*)(jassEnv + 0x08)`
2. **取当前游戏主线程的 `VirtualMachine*`**：
   - 调用 `tlsBlock = GetTlsSlot(5)`（或直接调用 `GetVM(vmIndex)`，内部取 `vmArray = *(uint32_t*)(tlsBlock + 0x90)`，返回 `vm = *(uint32_t*)(vmArray + vmIndex * 4)`）。
3. **取全局变量哈希表 `globalTable`（`TSHashTable<JassGlobalSymbol>`）**：
   - `globalTable = *(uint32_t*)(vm + vm_globalTable_off)`（`1.24.1~1.27.0` 为 **`+0x285C`**，`1.0.17~1.23.0` 为 **`+0x2858`**）。
4. **纯只读查找变量符号 `JassGlobalSymbol*`（无需调用 Storm 哈希函数，开局查一次缓存即可）**：
   - `buckets = *(uint32_t*)(globalTable + 0x1C)`（桶数组指针，每桶 12 字节）
   - `mask    = *(uint32_t*)(globalTable + 0x24)`（桶数 - 1；若为 `0xFFFFFFFF` 表示空表）
   - 遍历 `b = 0 .. mask`：
     - `bucket = buckets + b * 12`
     - `node = *(uint32_t*)(bucket + 0x08)`（头节点指针）
     - `linkOff = *(int32_t*)(bucket + 0x00)`（链偏移，见 `0x7ECE8A: mov eax, [edx]; mov ecx, [eax+ecx+4]`）
     - 当 `(int32_t)node > 0` 时循环：
       - `const char* name = *(const char**)(node + 0x14)`
       - 若 `name && strcmp(name, "EL0") == 0`（或 `"XS"`），即找到目标符号 `sym = node`！
       - `node = *(uint32_t*)(node + linkOff + 4)`
5. **读取整型数组 `EL0[pid]` 与布尔数组 `XS[pid]`**：
   - `sym + 0x18`：`elemType`（`>= 9` 表示数组；见 `0x7F1477: cmp dword ptr [esi+18h], 9`）
   - `arr = *(uint32_t*)(sym + 0x20)`（`JassArray*`，若为 0 表示数组尚未写入过元素，默认值 0/false）
   - `count = *(uint32_t*)(arr + 0x08)`（有效元素上限，`<= 8192`）
   - `data  = *(uint32_t**)(arr + 0x0C)`（连续 `uint32_t` 数组，见 `0x7F148A: mov eax, [edi+0Ch]`）
   - 当 `pid < count` 且 `data != nullptr` 时：
     - **可靠金钱 `EL0[pid]`** = `*(int32_t*)(data + pid * 4)`（对应 `war3map.j` L1130 `integer array EL0`，`pid` 为 0-based `GetPlayerId(p)`）
     - **禁买活标志 `XS[pid]`** = `*(uint32_t*)(data + pid * 4) != 0`（对应 `war3map.j` `boolean array XS`）

### 3.2 全 11 个版本 JASS VM 指针链 RVA 与偏移表

| 版本 | `ExecuteFunc` | `g_jassEnv` | `LookupJassFunc` | `vmIndex` 偏移 | `GetVM` | `GetTlsSlot` | `tls->vmArray` | `vm->globalTable` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | `0x2D2F40` | `0x87125C` | `0x29B1C0` | ❓ | ❓ | ❓ | ❓ | **`+0x2858`** |
| `1.0.20.6048` | `0x2D2F40` | `0x87229C` | `0x29B1C0` | ❓ | ❓ | ❓ | ❓ | **`+0x2858`** |
| `1.20.4.6074` | `0x2D3060` | `0x8722BC` | `0x29B2E0` | ❓ | ❓ | ❓ | ❓ | **`+0x2858`** |
| `1.21.0.6263` | `0x2D6630` | `0x873334` | `0x29E5C0` | ❓ | ❓ | ❓ | ❓ | **`+0x2858`** |
| `1.22.0.6328` | `0x3CB970` | `0xAA2FFC` | `0x39E610` | `+0x08` | `0x43A640` | `0x4B3830` | `+0x90` | **`+0x2858`** |
| `1.23.0.6352` | `0x3CD690` | `0xABBE4C` | `0x39FF60` | `+0x08` | `0x43C3D0` | `0x4B55C0` | `+0x90` | **`+0x2858`** |
| `1.24.1.6374` | `0x3D49B0` | `0xACD44C` | `0x3A0030` | `+0x08` | `0x44A7C0` | `0x4C3F50` | `+0x90` | **`+0x285C`** |
| `1.24.4.6387` | `0x3D4A70` | `0xACD44C` | `0x3A00F0` | `+0x08` | `0x44A820` | `0x4C3FD0` | `+0x90` | **`+0x285C`** |
| `1.25.1.6397` | `0x3D3D00` | `0xAB65F4` | `0x39F380` | `+0x08` | `0x449AE0` | `0x4C32A0` | `+0x90` | **`+0x285C`** |
| `1.26.0.6401` | `0x3D3F30` | `0xAB65F4` | `0x39F5B0` | `+0x08` | `0x449D10` | `0x4C34D0` | `+0x90` | **`+0x285C`** |
| `1.27.0.52240` | `0x1E0650` | `0xBE4238` | `0x1BF830` | `+0x08` | `0x7E1100` | `0x04EFB0` | `+0x90` | **`+0x285C`** |

> 注：早期 4 版（`1.0.17~1.21.0`）`LookupJassFunc` 内部采用旧版对象表间接取 VM（`0x29E5DB` 读全局池），未直接展开 `tls+0x90`，故 `vmIndex / GetVM / GetTlsSlot / tls->vmArray` 如实标 ❓。`JassGlobalSymbol`（`+0x14`/`+0x18`/`+0x20`）与 `JassArray`（`+0x08`/`+0x0C`）在全 11 版 `CreateGlobal` 特征匹配中均一致。

### 3.3 线程要求与读图阶段禁止读取说明

1. **必须在游戏主线程读取**：`GetTlsSlot(5)` 依赖游戏主线程的 TLS 槽，在 IPC 线程或其他工作线程读取会拿到空指针或错误 TLS；且 `JassArray` 动态扩容（`0x7F13D0`）会释放旧 `data` 缓冲区，跨线程无锁读取存在 UAF 风险。
2. **读图阶段绝对不能读（更不能调 JASS 原生）**：
   - 反汇编 1.27 崩溃点 **`game.dll+0x2BD982`**（见 `ai-autostart.md` 常见失败）实证：
     ```asm
     6F2BD97B: call 6F0CA020            ; 取 GamePlaying 场景对象（读图阶段返回 NULL）
     6F2BD980: mov  ecx, eax
     6F2BD982: mov  edx, dword ptr [eax]; eax == 0 -> ACCESS_VIOLATION (0xC0000005)
     ```
   - 对 JASS 全局变量同样如此：读图阶段 `war3map.j` 正在执行 `InitGlobals()` 并向 `globalTable` 插入数千个全局变量，频繁触发 `TSHashTable` 扩容；因此必须在 `g_sceneState == SceneState::GamePlaying` 且首帧进入对局后再遍历 `globalTable` 缓存 `EL0`/`XS` 符号指针，并在换局（离开 `GamePlaying`）时清零缓存！

---

## 四、G1：补全 `dota-ai-llm-mcp-control.md` §A1 全 11 版内部函数与偏移表

整合 `artifacts/llm-mcp/all_versions_rva_verified.json` 与本次 `artifacts/llm-mcp-gaps/g4_g1_all11.json` 实证结果（**修正了旧文档对 `1.0.17~1.21.0` `CAbilitySpell::ResetCooldown` 标为「早期布局」的误判**——反汇编 1.21.0 `0x473B40` 证实其同样使用 `+0x20 & 0x200` + `+0xD0` `CAgentTimer` + `vtable+0x18`！）：

| 版本 | `CUnit::FindAbility` | `CUnit::ResetCooldown` | `CAbilitySpell::ResetCooldown` | `CUnit::CountBuffsEx` | `ResolveAgent` | `CUnit::IsDetected` | `CAgentTimer` 虚表 | `CAgentTimer::GetTimeout (+0x10)` | `CAgentTimer::GetRem (+0x18)` | 链表偏移 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | `0x485B40` | `0x486990` | **`0x46F1A0`** | ❓(内联) | **`0x0935A0`** | ❓(内联) | ❓(无RTTI) | ❓ | ❓ | `+0x1D8` |
| `1.0.20.6048` | `0x486040` | `0x486E90` | **`0x46F6A0`** | ❓(内联) | **`0x0935A0`** | ❓(内联) | ❓(无RTTI) | ❓ | ❓ | `+0x1D8` |
| `1.20.4.6074` | `0x4865B0` | `0x487400` | **`0x46FC10`** | ❓(内联) | **`0x0935A0`** | ❓(内联) | ❓(无RTTI) | ❓ | ❓ | `+0x1D8` |
| `1.21.0.6263` | `0x48A4E0` | `0x48B330` | **`0x473B40`** | ❓(内联) | **`0x0935A0`** | ❓(内联) | ❓(无RTTI) | ❓ | ❓ | `+0x1D8` |
| `1.22.0.6328` | `0x077D80` | `0x078230` | `0x037550` | `0x076410` | `0x468A20` | `0x2797E0` | **`0x867394`** | **`0x467A20`** | **`0x467D60`** | `+0x1DC` |
| `1.23.0.6352` | `0x079340` | `0x079770` | `0x038A90` | `0x0779D0` | `0x46A7B0` | `0x27AD20` | **`0x87B4D4`** | **`0x4697B0`** | **`0x469AF0`** | `+0x1DC` |
| `1.24.1.6374` | `0x0793F0` | `0x079820` | `0x038B40` | `0x077A80` | `0x479140` | `0x27ADE0` | **`0x88A60C`** | **`0x478140`** | **`0x478480`** | `+0x1DC` |
| `1.24.4.6387` | `0x079400` | `0x079830` | `0x038B50` | `0x077A90` | `0x4791C0` | `0x27AE40` | **`0x88A60C`** | **`0x4781C0`** | **`0x478500`** | `+0x1DC` |
| `1.25.1.6397` | `0x0787D0` | `0x078C00` | `0x037E10` | `0x076E60` | `0x478480` | `0x27A0F0` | **`0x8784AC`** | **`0x477480`** | **`0x4777C0`** | `+0x1DC` |
| `1.26.0.6401` | `0x0787D0` | `0x078C00` | `0x037E10` | `0x076E60` | `0x4786B0` | `0x27A320` | **`0x8784AC`** | **`0x4776B0`** | **`0x4779F0`** | `+0x1DC` |
| `1.27.0.52240` | `0x46F440` | `0x471690` | `0x3DA2A0` | `0x46E630` | `0x044150` | `0x66E3B0` | **`0x95254C`** | **`0x0433C0`** | **`0x0438C0`** | `+0x1DC` |

- **全版本一致偏移**（`1.22.0~1.27.0` 全 7 版逐版反汇编实证）：
  - `CAbility+0x50` = 技能等级 - 1（全 11 版一致）
  - `CAbilitySpell+0x20 & 0x200` = 冷却中标志、`+0xD0` = 嵌入式 `CAgentTimer`（全 11 版一致）
  - `CAgentTimer` 纯只读公式：`node = *(abil + 0xDC)`，`total_cd = *(float*)(node + 0x08)`，`rem_cd = *(float*)(node + 0x04) - *(float*)(*(node + 0x0C) + 0x40)`（`1.22.0~1.27.0` 全 7 版一致；1.0.17~1.21.0 无 RTTI 标 ❓）

---

## 五、G5：RemoteControl 结构化局面命令设计（供 Claude 实现）

> **重要兼容性提示**：[`AiControlManager.cpp:L308`](file:///d:/Qt/workspace/War3Launcher/managers/AiControlManager.cpp#L308) 现有代码已将 `cmd == "status" || cmd == "state"` 路由到 `statusLine()`。为避免破坏现有脚本，建议新命令命名为 **`gamestate`**（或支持 `state json`），单行返回 `OK {json}\n`（若不在 `GamePlaying` 阶段返回 `ERR not_in_game\n`）。

### 5.1 返回 JSON 契约（单行 NDJSON）

```json
{"t":185.4,"rate":0.78,"scene":8,"team":1,"hero":{"handle":"0x00100123","x":-512,"y":-390,"hp":680,"max_hp":815,"mp":240,"max_mp":390,"lvl":4,"gold":745,"laning":true},"items":[{"slot":1,"id":"I0AN","tag":2,"chg":3,"cd_est":0.0}],"units":[{"h":"0x00100201","id":"esen","owner":1,"struct":false,"hero":false,"x":-450,"y":-350,"hp":550,"mhp":550,"loss":0,"dist":74}]}
```

### 5.2 字段来源对照表（精确到 `War3Launcher` 源码文件:行号）

| JSON 字段 | 类型 | 含义 | 代码来源（文件 : 行号） | 备注 / 安全红线 |
| :--- | :---: | :--- | :--- | :--- |
| `t` | `float` | 地图游戏钟（秒，号角为 0） | `hooker/war3hook_ai.cpp:L293, L297` (`g_aiMapClock.clock()`) | 读不到 M 时退回 `-1` |
| `rate` | `float` | 游戏相对墙钟倍率 | `hooker/war3hook_ai.cpp:L286` (`g_aiMapClock.rate()`) | 慢速局自动感知 |
| `scene` | `int` | 当前场景状态机 | `hooker/war3hook_ai.cpp:L4460` (`g_sceneState`) | 仅 `GamePlaying` 时采样 |
| `team` | `int` | 本机阵营（1=近卫, 2=天灾） | `hooker/war3hook_ai.cpp:L2429` (`resolveLocalPlayerTeam()`) | — |
| `hero.handle` | `uint32` | 本机英雄句柄 | `hooker/war3hook_ai.cpp:L500, L2411` (`aiLocalHeroHandle()`) | — |
| `hero.x / y` | `float` | 英雄坐标 | `hooker/war3hook_ai.cpp:L515` (`aiQueryPosition(hero, &x, &y)`) | 游戏主线程 |
| `hero.hp / max_hp` | `float` | 英雄当前/最大血量 | `hooker/war3hook_ai.cpp:L527` (`aiQueryLife`) + `hooker/war3hook_ai_tactics.inl:L29` (`aiQueryUnitState(hero, 1)`) | — |
| `hero.mp / max_mp` | `float` | 英雄当前/最大蓝量 | `hooker/war3hook_ai_tactics.inl:L33` (`aiHeroMana`, state=2) + `aiQueryUnitState(hero, 3)` | — |
| `hero.lvl` | `int` | 英雄等级 | `hooker/war3hook_ai.cpp:L60`（已缓存 `GetHeroLevel` 原生） | 游戏主线程 |
| `hero.gold` | `int` | 总金钱 | `GetPlayerState(GetLocalPlayer(), 1)`（原生表已有） | P2 可追加 G4 `rel_gold` |
| `hero.laning` | `bool` | 对线自动流程是否激活 | `hooker/war3hook_ai_lane.inl:L505, L541` (`g_aiLane`) | — |
| `items[0..5]` | `array` | 6 格背包（FourCC/标签/充能/冷却） | `hooker/war3hook_ai_tactics.inl:L229, L237` (`AiInventory aiReadInventory(hero)`) + `L1665` (`g_aiItemReadyAt`) | 后续可换 G1 `CAgentTimer` 精确冷却 |
| `units[]` | `array` | **本地可见**单位列表（按距离升序，上限 40） | `hooker/war3hook_ai.cpp:L506` (`struct AiUnitState`) + `L609` (`aiCollectNearby`) | **⚠ 必加安全过滤**：现有 `aiDumpUnits` (`L2421`) 未调 `aiCheckUnitVisibleToLocal` (`L2698`)；`gamestate` **必须对所有敌方单位强制校验 `aiCheckUnitVisibleToLocal(s.handle)` + `(!invis \|\| IsUnitDetected)`**，绝不向 Launcher/MCP 泄露迷雾单位！ |
| 传输通道 | `SharedMemory` | 游戏主线程写快照 → Launcher 同步读 | `shared/SharedMemory.h` + `managers/AiControlManager.cpp:L308` | 建议用 SeqLock 固定结构体（约 4~8KB）每 100ms 由 `aiTick` 刷新，Launcher 收到 `gamestate` 后 `<1ms` 无锁拼装 JSON 返回，不再写 `AiUnit.log` |

---

## 六、MCP Server 原型与验证状态（离线 vs 实机）

### 6.1 原型位置与组成
- 目录：[`artifacts/llm-mcp-server/`](../artifacts/llm-mcp-server/)
- 文件：`server.py`（官方 Python `mcp` SDK `FastMCP` stdio 服务）、`rc_client.py`（`127.0.0.1:6120` 客户端 + `LogTail` 增量读 + 日志解析 + `say` 白名单）、`landmarks.json`（DotA 6.83d 中英文地标表）、`test_mcp_server.py`（6 项离线单元测试）、`README.md`（安装与 Claude Code / Gemini 配置）。

### 6.2 实机验证步骤（待用户放行、无其他测试占用 6120 时执行）
1. 确认无其他测试占用 `war3.exe` 与 `127.0.0.1:6120`。
2. 按 `War3Launcher/.agents/rules/ai-live-test.md` 开局选人后，用 Claude Code / Gemini 挂载 `artifacts/llm-mcp-server/server.py`。
3. 依次调用 `game_status` → `get_state` → `move_to(landmark="中路一塔")` → `get_state`（确认坐标移动）→ `buy("obs")` → `get_state`（确认背包）→ `start_laning` → `stop`。
4. **实机补测 G2/G3**：分别抓包或实测 TP 对地、TP 对塔、跳刀点地、推推棒对自身/队友、真眼点地，核对 ActionData2 字节与表 2.2 一致。
5. **实机补测 G4**：在 1.27 局内按 §3.1 指针链只读 `EL0[pid]` 与 `XS[pid]`，核对买物/击杀前后可靠金钱变化与买活后 `XS[pid]` 变化。
