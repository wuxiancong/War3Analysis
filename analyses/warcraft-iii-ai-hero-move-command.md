# AI 英雄移动命令（`-move` / `/move`）可行性与实现路径

> **分析日期**：2026-11-14  
> **关联代码**：`War3Launcher/managers/AiControlManager.cpp`、`NetworkManager.cpp`、`hooker/war3hook_process.cpp`（`-buy`）、`War3Bot/src/client.cpp` / `matchstatsprovider.cpp`  
> **前序文档**：[`warcraft-iii-action-ids-and-dota-stats-transmission.md`](./warcraft-iii-action-ids-and-dota-stats-transmission.md)、[`dota-hero-trajectory-and-skill-orders-analysis.md`](./dota-hero-trajectory-and-skill-orders-analysis.md)、[`GameNetCommandAllyPingXY.md`](./GameNetCommandAllyPingXY.md)  
> **配套思维导图**：[`warcraft-iii-ai-hero-move-command-mindmap.md`](./warcraft-iii-ai-hero-move-command-mindmap.md)

---

## 一、核心结论（先读这段）

| 问题 | 结论 |
| :--- | :--- |
| 当前 `-pick` / `-shop` / `-buy` / `-minimap *` 架构能否支撑英雄移动？ | **能。** 继续走 `AiControl → IPC → war3hook → GameEnqueuePlayerAction_Ex`。 |
| 是否必须再逆向 `versions/*/game.dll` 找到「控制单位移动」的 C++ 函数？ | **不必。** 移动不是调用 `CUnit::IssueOrder` 一类导出函数，而是往已有入队口塞 **Action `0x11`**。 |
| 单位移动逻辑和购买逻辑一样吗？ | **同管道、不同包。** 都用 `EnqueuePlayerAction`；buy 是 `选中商店 + 0x10(物品码)`，move 是 `保证英雄选中 + 0x11(点地 order)`。 |
| `-minimap move` 能当英雄移动用吗？ | **不能。** 它已实现为本地镜头 `SetCameraPosition`，与单位指令无关。新命令应用 `-move`/`/move`（或 `move`）。 |
| 还要不要对 `game.dll` 做任何分析？ | **轻量验证即可**：从一局真实右键点地抓 1～2 条 `0x11` hex，核对 flags / Order 填充；不必新开深挖「移动函数」专题。协议布局工程内已有。 |

---

## 二、现有 AI 命令各自走哪一层

```text
RemoteControl / 游戏内聊天
        │
        ▼
 AiControlManager / NetworkManager
        │  IPC (SharedMemory MSG_TYPE_*)
        ▼
 war3hook（主线程 / Action 逻辑帧）
        │
        ├─ pick/shop  → HERO_PICK_* → sendTargetClickAction（0x1B Select 等）
        ├─ buy        → MSG_TYPE_ITEM_BUY → 选商店 + 0x10 + 恢复选中
        ├─ minimap ping → GameNetCommandAllyPingXY（CNetCommandAllyPing / 0x68）
        ├─ minimap move → GameCameraPositionSetter（JASS SetCameraPosition，仅镜头）
        └─ 【待加】move → 组 0x11 点地指令 → EnqueuePlayerAction_Ex  ← 与 buy 同口
```

已落地的购买路径（`war3hook_process.cpp`）证明：

1. `g_originalGameEnqueuePlayerAction_Ex` + `g_netProviderBNET` 可在对局内注入任意玩家动作流；
2. 选中切换可用 `buildSelectionSwitchAction`（`0x1B`/`0x16`/`0x1A`/`0x19`）；
3. 动作在 Action 线程/逻辑帧执行，避免非游戏线程直接乱调引擎。

英雄移动应复用 **第 1、3 点**；若当前选中不是己方英雄，再复用 **第 2 点**（与 buy 前后切选中同模式）。

---

## 三、移动 vs 购买：同构对比

| 维度 | `-buy`（已实现） | `-move`（拟实现） |
| :--- | :--- | :--- |
| 网络/同步层 | `W3GS_OUTGOING_ACTION` 内嵌动作 | 相同 |
| 入队 API | `GameEnqueuePlayerAction_Ex` | **相同，无需新 RVA** |
| 主 Action ID | `0x10`（无目标技能/训练购买） | **`0x11`（点目标指令）** |
| Order / Ability | 物品 FourCC（倒序写入） | **`0x000D0003`（smart）** 或 `0xD000F`（A 地）/`0xD0016`（巡逻） |
| 坐标 | 无（买货架位） | **世界坐标 float X/Y** |
| 选中前置 | 必须先选中对应物品商店 | 必须选中要走的单位（通常己方英雄） |
| 事后恢复 | 买完切回原选中 | 可选；若本就选中英雄则不需要 |
| 业务表依赖 | `DotaItemShopAbbrev` + 商店实例捕获 | 坐标即可；可选「先 F1/选英雄」辅助 |

**不像购买的部分**：不必解析商店实例、阵营锚点、货架 FourCC；**像购买的部分**：组二进制 action → enqueue → 等主机广播生效。

---

## 四、`0x11` 包格式（工程内已证实，无需再找「移动函数」）

来源：`War3Bot/src/client.cpp` 解析与 Action 字典审计。

```text
总长：1 + 22 = 23 字节（ActionID + payload）

[0]     ActionID = 0x11
[1..2]  Flags     uint16   （常见 0x0000；队列等标志需用真实右键包核对）
[3..6]  OrderId   uint32   ← AbilityId；地面移动 = 0x000D0003
[7..14] Unknown   8 bytes  ← 抓包多为 0xFFFFFFFF 0xFFFFFFFF（与 0x10 购买尾部同形）
[15..18] X        float32  世界坐标
[19..22] Y        float32  世界坐标
```

`client.cpp` 约定：`orderId` 取自 payload 偏移 +2；`X/Y` 取自 payload +14 / +18。

常用 Order（`matchstatsprovider.cpp` / 轨迹分析）：

| OrderId | 语义 | 建议 AI 默认 |
| :--- | :--- | :--- |
| `0x000D0003` | smart（右键点地移动） | **默认 `-move x y`** |
| `0x000D000F` | attack-move（A 地面） | 可选 `-amove` / `-move attack x y` |
| `0x000D0012` | move（显式移动） | 备选 |
| `0x000D0016` | patrol | 可选 |
| `0x12` + `0xD0003` | 右键点单位（跟随/攻击智能） | 另做 `-attack`/`-follow`，非纯坐标移动 |

> 说明：空地右键多为 **`0x11` + `0xD0003`**；点到单位则为 **`0x12`**。AI「走到坐标」应发 **`0x11`**，不要误走 minimap/镜头接口。

---

## 五、要不要逆向 `game.dll`？

### 不需要（对 `-move` 交付）

- 不必定位 `IssuePointOrder` / `CUnit::Order` / UI 右键处理函数再直接 call。  
- 那些函数最终也会组出同一套 Action，再进你已 Hook 的 `EnqueuePlayerAction`。  
- 绕过 UI 直接 enqueue 正是 `-buy` 的成功模式，移动同理。

### 可选的轻量工作（推荐，半天级）

1. 进一局，右键空地一次，从 `War3Bot` `player_actions` 或 hook 日志抄一条 `0x11` hex；  
2. 核对 Flags 与 8 字节 Unknown 是否与上表一致；  
3. 用同 hex 模板改 X/Y，经 `EnqueuePlayerAction_Ex` 回放验证。  

若 Flags 与公开 W3G/`0x0000` 不一致，以本机 1.26/1.27 DotA 抓包为准改模板即可——仍不需要新函数 RVA 表。

### 何时才值得再挖 `game.dll`

- 想支持「不依赖当前选中、按 unit handle 下指令」且不想先发选中包；  
- 或要模拟完整 UI（命令卡高亮、本地预表现）而不只同步权威指令。  
那是增强项，不是 AI 可控移动的前置条件。

---

## 六、建议的控制接口设计

### 命令语法

```text
move <x> <y>                 # RemoteControl
-move <x> <y>  /  /move <x> <y>   # 游戏内聊天（与 -buy 对称）
可选：
-move attack <x> <y>         # 0x11 + 0xD000F
-move patrol <x> <y>         # 0x11 + 0xD0016
-stop                        # 0x10 + 0xD0004（急停，后续可做）
```

注意与现有 **`minimap move`** 命名空间隔离，避免歧义。

### 实现分层（对齐 buy）

1. **`SharedMemory.h`**：`MSG_TYPE_UNIT_MOVE` + `UnitMovePayload { float x,y; uint32_t orderId; }`  
2. **`AiControlManager`**：解析 `move`/`-move`/`/move`，发 IPC（与 `buy` 同级）  
3. **`NetworkManager`**：聊天路径识别 `-move`/`/move`（对标 `/buy`）  
4. **`war3hook_process.cpp`**：  
   - `requestUnitMove(x,y,orderId)` 标记 pending  
   - Action 帧：`若未选中己方英雄 → buildSelectionSwitchAction` → 组 `0x11` → `enqueue*RawAction`  
5. **聊天 Hook**：`handleMoveCommand` 与 `handleBuyCommand` 并列  

### 选中策略

- 优先：当前全局选中已是本地英雄 → 直接 `0x11`。  
- 否则：用已有本地英雄 handle / 选人后缓存的 agent，切选中后再移动（复用 buy 的切选模式）。  
- 不要用屏幕 `rclick` 做权威移动（分辨率/镜头/迷雾不可靠）；`rclick` 仅适合人工调试。

### 验收

- Launcher RemoteControl：`move -1500 1200` → `OK`  
- hook 日志出现 `[UnitMove] 0x11 ... order=0xD0003 x=... y=...`  
- `War3Bot` `player_actions` 出现对应 `actionId=0x11`、同坐标  
- 英雄实际走向该点（主机权威同步后）

---

## 七、与「镜头移动 / 小地图」的边界

| 命令 | 效果 | 引擎入口 |
| :--- | :--- | :--- |
| `-minimap ping x y` | 盟友信号 | `CNetCommandAllyPing` / action `0x68` |
| `-minimap move x y` | **仅本地镜头** | JASS `SetCameraPosition` |
| `-move x y`（新） | **单位移动指令** | Action `0x11` + Order `0xD0003` |

三者都接收世界坐标，但语义完全不同；文档与帮助字符串务必分开。

---

## 八、总结

当前代码路径**可行**，且与购买同属「组 Action → EnqueuePlayerAction」范式。  
**不需要**为移动再逆向出专用「控制单位移动函数」；需要的是按已证实的 **`0x11` 布局组包**，并保证目标单位被选中。  
可选抓一条真实右键包做 flags 校准后即可开工实现 AI 接口。
