# DotA / War3 `0x60` 聊天动作动态句柄生成机制

> 分析日期：2026-10-29  
> 证据来源：`D:\Qt\workspace\War3Script`、`War3Launcher\hooker\war3hook.cpp`、`versions\*\game.dll` 偏移矩阵、运行时 `ActionData1.log` / `War3Chat.log`  
> 关联工具：`D:\Ghidra_12.1.4`（`War3Analysis\ghidra\projects\War3_127.gpr`）、`D:\REA`（暂无现成 handle 专库）

---

## 1. 结论（一句话）

`0x60` 包里的 Trigger/Event 四个 dword **不是地图常量，也不是固定硬编码值**；它们是 `game.dll` 全局 Agent 句柄表在地图脚本调用 `CreateTrigger` / `TriggerRegisterPlayerChatEvent` 时分配出的**动态 ID**。玩家数、电脑数、单人作弊触发器套装（`BK2`）以及晚注册时序，都会整体平移这些 ID；`Event2` 甚至同配置下都会出现 ± 几个 ID 的抖动。

因此：`sendChatAction` 里 `0x7E47 / 0x7F73 / 0x7966 / 0x8068` 这类硬编码**不可靠**；可靠路径应复用真实聊天入队（`GameChatInputLogicInGame`），或在运行时解析匹配到的 Trigger/Event 句柄。

---

## 2. 运行时观测（硬编码被证伪）

### 2.1 手动输入 `-ap`（`ActionData1.log` 11:24:25）

```
60 47 7e 00 00 73 7f 00 00 2d 61 70 00
60 66 79 00 00 6b 80 00 00 2d 61 70 00
```

| 字段 | LE 字节 | 句柄 | 硬编码值 | 是否一致 |
|------|---------|------|----------|----------|
| Trigger1 | `47 7e 00 00` | `0x7E47` | `0x7E47` | 相同 |
| Event1 | `73 7f 00 00` | `0x7F73` | `0x7F73` | 相同 |
| Trigger2 | `66 79 00 00` | `0x7966` | `0x7966` | 相同 |
| Event2 | `6b 80 00 00` | **`0x806B`** | `0x8068` | **不一致** |

随后地图自发 `0x6B`：

```
6b 64 72 2e 78 00 44 61 74 61 00 4d 6f 64 65 61 70 00 01 00 00 00
= SyncStoredInteger(OS="dr.x", "Data", "Modeap", ...)
```

### 2.2 自动注入（`War3Chat.log` 同局 `sendChatAction`）

```
Trigger1=0x7E47 Event1=0x7F73 Trigger2=0x7966 Event2=0x8068
hex 结尾: ... 68 80 00 00 2d 61 70 00
```

同一局里手动包用 `0x806B`、注入包用 `0x8068` —— 说明 **Event2 不是固定常量**。

---

## 3. 包格式与双段原因（脚本侧）

每个匹配到的聊天事件都会入队一段：

```
0x60 | TriggerHandle:u32 LE | EventHandle:u32 LE | cstring\0
```

DotA 对前缀 `"-"` 注册了 **至少两个** 聊天触发器，所以 `-ap` 产生 **两段** `0x60`：

### 3.1 触发器 A：全玩家通用命令（较早创建，对应较小 Trigger ID ≈ `Trigger2=0x7966`）

`war3map_9.j`：

```jass
set t=CreateTrigger()
call TriggerRegisterPlayerChatEvent(t,BO[1],"-",false)  // ×5
call TriggerRegisterPlayerChatEvent(t,CO[1],"-",false)  // ×5
call TriggerAddAction(t,function DB2)
```

- 一次 `CreateTrigger` → 1 个 Trigger Agent  
- 立即注册 **10** 个 `TriggerRegisterPlayerChatEvent` → 10 个 Event Agent  
- Action：`DB2`（杂项命令；`-ap` 不在其业务分支里设模式）

### 3.2 触发器 B：房主模式解析 `PF0`（较晚创建，对应较大 Trigger ID ≈ `Trigger1=0x7E47`）

`war3map_9.j`：

```jass
set t=CreateTrigger()
call TriggerAddAction(t,function XX2)
call TriggerAddCondition(t,Condition(function WI2))
set PF0=t
set t=CreateTrigger()
call TriggerRegisterTimerEvent(t,0.01,false)
call TriggerAddCondition(t,Condition(function XY2))
```

`war3map_4.j`：

```jass
function XX2 takes nothing returns nothing
    call W82(GetEventPlayerChatString(),1)
endfunction

function XY2 takes nothing returns boolean
    if (MY)!="" and AL==false then
        set PE0=true
        call W82("-"+(MY),2)
    else
        call TriggerRegisterPlayerChatEvent(PF0,WO,"-",false)  // 延迟 ~0.01s
    endif
    return false
endfunction
```

要点：

1. `PF0` 的 **CreateTrigger 与 ChatEvent 注册分离**（中间隔 0.01s 定时器 + 其间大量其它对象创建）。  
2. 因此 **Event1 ≫ Trigger1**（观测约 `+0x12C`：`0x7F73 - 0x7E47 = 0x12C`）。  
3. `XX2 → W82` 才是真正解析 `ap` / `ar` / … 并最终 `FL1("Mode"+EL)` 的路径。

### 3.3 `-ap` → `Modeap`（0x6B，不是第二段 0x60）

`war3map_4.j` 模式表：

```jass
set WA2[1]="allpick"
set WB2[1]="ap"
```

`W82` 解析成功后：

```jass
set EL=W62(W92)          // 字母串 → "ap"
call FL1("Mode"+EL, ...) // → "Modeap"
```

`war3map_1.j`：

```jass
function FL1 takes string FM1,integer U0I returns nothing
    call StoreInteger(OS,"Data",FM1,U0I)
    if GetLocalPlayer()==WO then
        call SyncStoredInteger(OS,"Data",FM1)
    endif
endfunction
```

`OS = InitGameCache("dr.x")` → 网络层表现为 `0x6B "dr.x" "Data" "Modeap"`。

---

## 4. 句柄在引擎侧如何生成（game.dll）

### 4.1 机制模型

```
JASS Native: CreateTrigger / TriggerRegisterPlayerChatEvent / TriggerAddAction / ...
    ↓
NativeFuncEntryPoint（统一入口）
    ↓
分配 Agent 对象 + 写入全局 Handle↔Agent 表
    ↓
返回 handleId（即 0x60 里那 4 字节）
```

句柄 ID 特征：

1. **大体顺序递增**（创建顺序 ≈ 相对大小：`Trigger2 < Trigger1`）。  
2. **存在回收/复用（free-list）**：同配置下 `Event2` 可在 `0x8068`/`0x806B` 间抖动。  
3. **与玩家槽位占位强相关**：更多真人/电脑 → 初始化阶段更早消耗更多 Agent → 后续聊天触发器 ID 整体上移。

脚本侧 **从不** 写死 `0x7E47`；`GetHandleId(t)` 读到的就是同一套 ID。

### 4.2 Launcher 已挂钩的引擎证据点

| 符号（Launcher 命名） | 1.26 RVA | 1.27 RVA | 作用 |
|----------------------|----------|----------|------|
| `GameHandle2AgentRegistry` | `0x430D88` | `0x2652F4` | Handle↔Agent 登记（特征含 `push 0x80267`） |
| `GameNativeFuncEntryPoint` | `0x45D1B5` | `0x7EF6E0` | JASS Native 网关（CreateTrigger 等由此进） |
| `GameStringToHandleRegEnd` | `0x45D2F0` | `0x7F162C` | 字符串句柄登记 |
| `GameEnqueuePlayerAction_` | `0x6504E2` / `0x657340` | `0x840BBB` / `0x851E10` | 动作入队（可见原始 `0x60`） |
| `GameChatInputLogicInGame` | PrimaryGameUI vtable `+0x0C` | 同左 | 真实聊天提交 → 匹配触发器 → 构造 `0x60` |

`Handle2AgentRegistry` 观测到的 Agent 布局（Launcher 注释/日志）：

| 偏移 | 字段 |
|------|------|
| `+0x00` | vtable |
| `+0x04` | refCount |
| `+0x0C` | handle1 |
| `+0x10` | handle2 |
| `+0x20` | flags |
| `+0x28` | type |
| `+0x30` | unitId（单位类） |

> 缺口：`D:\REA` 现为 `rea-agents` CLI，无现成 free-list 专库；Ghidra 工程 `War3_127.gpr` 尚无导出 CreateTrigger 分配器的文字分析。下一步应反编译 `game.dll+0x2652F4`（1.27）附近，追到分配器头结点/槽位数组。

### 4.3 真实聊天 → `0x60` 调用链

```
ChatEditBar
  → GameChatInputLogicInGame
  → 遍历 TriggerRegisterPlayerChatEvent 匹配表
  → 每个命中：EnqueuePlayerAction(
        0x60 | TriggerHandle | EventHandle | text\0 )
  → 网络同步 / NetEventInGameAction
  → JASS 触发 XX2 / DB2
```

Launcher 两条路径对比：

| 路径 | 实现 | 句柄来源 | 可靠性 |
|------|------|----------|--------|
| 物理注入 `chatSendCommand` | 填编辑框 → 调 `GameChatInputLogicInGame` | 引擎现场匹配 | 高（与手动一致） |
| 合成 `sendChatAction` | 自拼 `0x60` → `EnqueuePlayerAction_Ex` | 经验公式/硬编码 | **低**（Event2 已证伪） |

---

## 5. 为何句柄随人数变化

### 5.1 初始化占位

地图开局会为各玩家槽位创建大量单位/触发器/事件。真人与电脑占槽改变“水位线”，聊天触发器创建时拿到的 ID 跟着变。

Launcher 逆向经验公式（`sendChatAction`，多人）：

```
playerOffset   = (effectivePlayers - 2) * 15
computerOffset = computerCount * 12
totalOffset    = playerOffset + computerOffset

Trigger1 = 0x7D32 + totalOffset   // 2 真人 0 电脑基准
Event1   = 0x7E5E + totalOffset
Trigger2 = 0x7975 + totalOffset
Event2   = 0x7F53 + totalOffset
```

脚本里 **没有** `+15`/`+12` 常量；这是对「每多一个真人/电脑，初始化多消耗约 15/12 个 Agent」的经验拟合。

### 5.2 单人特例：`BK2` 作弊触发器套装

`war3map_9.j`：

```jass
if (bj_isSinglePlayer and AR2()) then
    call BK2()
endif
```

`BK2` 在聊天触发器定稿前注册大量 `-lvlup`/`-gold` 等作弊监听（约数十 `CreateTrigger` + 上百 `TriggerRegisterPlayerChatEvent`），把单人水位线抬到与多人线性公式不同的基线 —— 这正是 Launcher 对单人改用另一组“实测硬编码”的原因，但即便同是单人，`Event2` 仍会抖。

---

## 6. 端到端时序

```
玩家输入 "-ap" / 或物理注入 chatSendCommand
        │
        ▼
GameChatInputLogicInGame
        │
        ├─► 匹配 PF0 的 "-" 事件  ──► 0x60 #1 (T1,E1,"-ap")
        │         └─ XX2 → W82("-ap")
        │               ├─ WB2 命中 "ap" → AP=true
        │               ├─ EL="ap"
        │               └─ FL1("Modeap") → 0x6B SyncStoredInteger
        │
        └─► 匹配 DB2 的 "-" 事件  ──► 0x60 #2 (T2,E2,"-ap")
                  └─ DB2（不负责设 AP）
```

模式真正生效依赖：**正确的 PF0 (T1,E1)** 触发 `W82`，再由地图发 `0x6B Modeap`。  
仅拼错误 `Event2` 的双段 `0x60`，可能偶发“看起来像生效”（前三个碰巧对上 + 某条路径仍触发），但不可复现。

---

## 7. 对 Launcher 的工程建议

1. **停止**把 `0x7E47/0x7F73/0x7966/0x8068` 当常量；至少 `Event2` 已实测失败。  
2. 优先走 **`chatSendCommand` / `GameChatInputLogicInGame`**，让引擎自己填句柄。  
3. 若必须合成 `0x60`：在初始化后用 `GetHandleId(PF0)` + 遍历聊天事件表（或 Hook `Handle2AgentRegistry`/`TriggerRegisterPlayerChatEvent`）**缓存运行时句柄**，而不是人数公式。  
4. `0x6B Modeap` 是地图逻辑产物，**不必**由 `sendMapCommand` 强行补发（手动路径已证明引擎/地图会自发）。  
5. Ghidra 后续任务：打开 `War3_127.gpr`，从 `0x2652F4`（Handle2AgentRegistry）与 `0x7EF6E0`（NativeFuncEntryPoint）向下追 CreateTrigger 分配器。

---

## 8. 关键文件索引

| 路径 | 内容 |
|------|------|
| `D:\Qt\workspace\War3Script\war3map_9.j` | DB2 `-` 触发器、`PF0`/`XY2` 延迟注册、`BK2` 单人入口 |
| `D:\Qt\workspace\War3Script\war3map_4.j` | `XX2`/`W82`/`WA2`/`WB2`/`FL1("Mode"+EL)` |
| `D:\Qt\workspace\War3Script\war3map_1.j` | `FL1`/`FN1` GameCache `dr.x` |
| `D:\Qt\workspace\War3Launcher\hooker\war3hook.cpp` | `sendChatAction`、`chatSendCommand`、Handle2AgentRegistry / Enqueue hooks |
| `D:\Qt\workspace\War3Launcher\versions\*` | 各版本 `game.dll` |
| `D:\Qt\workspace\War3Analysis\ghidra\projects\War3_127.gpr` | 1.27 Ghidra 工程（待深挖分配器） |
| `...\logs\ActionData1.log` / `War3Chat.log` | 手动 vs 注入句柄对照 |

---

## 9. 参考思维导图

见同目录：[`dota-0x60-chat-action-dynamic-handles-mindmap.md`](./dota-0x60-chat-action-dynamic-handles-mindmap.md)
