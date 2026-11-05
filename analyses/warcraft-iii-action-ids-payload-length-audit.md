# 魔兽争霸 III Action ID 载荷长度审计与日志“未知动作”纠错

> **分析日期**：2026-11-01  
> **目标版本**：1.26.0.6401 / 1.27（DotA Allstars）  
> **代码入口**：`War3Bot/src/client.cpp` → `Client::getActionPayloadLength` / `categorizeAction` / `getActionName`  
> **证据来源**：`D:\var\log\War3Bot`、`War3Script`、`War3Launcher\versions\*\game.dll`、公开 W3G 规范（nagger/blue）、Tinker、w3grs  
> **配套导图**：[`warcraft-iii-action-ids-payload-length-audit-mindmap.md`](./warcraft-iii-action-ids-payload-length-audit-mindmap.md)  
> **前序文档**：[`warcraft-iii-action-ids-and-dota-stats-transmission.md`](./warcraft-iii-action-ids-and-dota-stats-transmission.md)（本文对其 Gemini 逆向表做纠错）

---

## 一、核心结论

1. **日志中的“未知动作”几乎全部是解析错位，不是真实 Action ID。**  
   根因：Gemini 实现把 **`0x1A PreSubselection` 的附加长度写成了 `1`**，实际应为 **`0`**。它吃掉了紧随其后的 **`0x19 SelectSubgroup`**，再把英雄/单位 FourCC 的首字节误当成新动作 ID。
2. **`0x66` 不是“旧版 GameCache 同步”。**  
   在 1.07+ / 1.26 DotA 中，`0x66` = **进入英雄技能加点菜单**（0 字节）。GameCache `SyncStoredInteger` 固定是 **`0x6B`**（1.24b+）。
3. **ESC / 技能菜单 / 建造菜单 / 小地图信号的 ID 被整体错位到了作弊码区间。**  
   正确映射：`ESC=0x61`、`SkillMenu=0x66`、`BuildMenu=0x67`、`Ping=0x68`。  
   `0x21/0x27/0x28/0x29/0x2E` 属于单机作弊或其它用途，不可当作 UI 动作。
4. **`0x1B/0x1C/0x1D/0x1E` 名称与长度也需纠正。**  
   `0x1B`=选择单位(9B)、`0x1C`=选择地面物品(9B)、`0x1D`=取消复活(8B)、`0x1E`=取消队列(5B)。
5. **`0x14` 载荷是 43 字节，不是 42。**（含 `owner` 1 字节；与 w3grs / Tinker FogObjectOrder 一致）

---

## 二、日志未知 ID 的还原（错位指纹）

所有“未知”样本都满足同一模式：先正确解析到 `0x1A`，紧接着出现“未知”，且原始 hex 里能看到 `1A 19 xx xx xx xx ...`。

| 日志“未知 ID” | 实际来源（`0x19` 后 FourCC 首字节） | 典型 FourCC（LE 字节） | 含义 |
| :--- | :--- | :--- | :--- |
| **0x35** | `'5'` | `35 39 43 68` → `59Ch` / `hC95` | 英雄单位类型 |
| **0x38** | `'8'` | `38 30 30 6E` → `800n` | 英雄 `n008` 一类 |
| **0x49** | `'I'` | `49 4C 30 6E` → `IL0n` | 英雄 `n0LI` |
| **0x4B** | `'K'` | `4B 31 30 6E` → `K10n` | 英雄 `n01K` |
| **0x4E** | `'N'` | `4E 31 30 6E` → `N10n` | 英雄 `n01N` |
| **0x57** | `'W'` | `57 30 30 6E` → `W00n` | 英雄 `n00W` |
| **0x63** | `'c'` | `63 62 62 4E` → `cbbN` | 单位 `Nbbc` |
| **0x70** | `'p'` | `70 6F 63 6E` → `pocn` | `ncop`（中立建筑等） |

### 复现样例（`war3bot.log`）

```
数据: ...16010100E5650000696600001A1935394368E565000069660000
```

| 步进 | 正确解析 | 错误解析（0x1A 多吃 1 字节） |
| :--- | :--- | :--- |
| … | `0x16` 加选 | 同左 |
| `1A` | PreSub，载荷 0 | PreSub，**误吃 `19`** |
| `19 35 39 43 68 ...` | Subgroup，ItemID=`59Ch` | **伪动作 `0x35`**，后续全部错位 |

单独一包 `66`（1 字节）在日志里被标成“旧版 GameCache”，实际是玩家打开 **技能加点菜单**；长度碰巧为 0 才没有进一步炸流。

---

## 三、Gemini 表 vs 校正表（1.26 DotA 常用）

长度均指 **不含 ActionID 本身** 的 payload 字节数。

| ID | Gemini（错误/不完整） | 校正后 | 说明 |
| :--- | :--- | :--- | :--- |
| `0x1A` | 1，预选择 | **0** | 致命 bug 源 |
| `0x1B` | 9，拾取地面物品 | **9，选择单位** | 名称错 |
| `0x1C` | 8，取消复活 | **9，选择地面物品** | ID/长度皆错 |
| `0x1D` | 5，取消队列 | **8，取消英雄复活** | |
| `0x1E` | （缺失） | **5，取消建造/训练队列** | |
| `0x14` | 42 | **43** | 含 owner |
| `0x15` | （缺失） | **51** | 双目标+object |
| `0x21` | 0，ESC | **8，罕见/旧块**；ESC 是 **0x61** | |
| `0x27` | 0，技能菜单 | **5，作弊 KeyserSoze**；菜单是 **0x66** | |
| `0x28` | 0，建造菜单 | **5，作弊 LeafitToMe**；菜单是 **0x67** | |
| `0x29` | 12，小地图信号 | **0，作弊 ThereIsNoSpoon**；Ping 是 **0x68**/12 | |
| `0x2E` | 8，对话框 | **4，作弊设时间**；对话框是 **0x69/0x6A**/16 | |
| `0x66` | 变长 GameCache | **0，技能加点菜单** | |
| `0x6B` | 变长 GameCache | **3×CString + u32**（保持） | DotA 战绩通道 |

### 完整常用字典（payload）

| ID | 名称 | Payload |
| :--- | :--- | :--- |
| `0x01`/`0x02` | Pause / Resume | 0 |
| `0x03` | Set speed | 1 |
| `0x04`/`0x05` | Inc/Dec speed | 0 |
| `0x06` | Save game | name`\0` |
| `0x07` | Save finished | 4 |
| `0x10` | Ability no target | 14 |
| `0x11` | Ability point | 22 |
| `0x12` | Ability object | 30 |
| `0x13` | Give/drop item | 38 |
| `0x14` | Two-point / fog order | 43 |
| `0x15` | Two-target + item | 51 |
| `0x16`/`0x17` | Select / Assign group | `3 + n*8` |
| `0x18` | Select group hotkey | 2 |
| `0x19` | Select subgroup | 12 |
| `0x1A` | PreSubselection | **0** |
| `0x1B` | Select unit | 9 |
| `0x1C` | Select ground item | 9 |
| `0x1D` | Cancel hero revival | 8 |
| `0x1E`/`0x1F` | Dequeue build/train | 5 |
| `0x50` | Ally options | 5 |
| `0x51` | Transfer resources | 9 |
| `0x60` | Trigger chat | 8 + text`\0` |
| `0x61` | ESC | 0 |
| `0x62` | Scenario / sleep sync | 12 |
| `0x63` | TriggerSyncReady | 8 |
| `0x64`/`0x65` | Trackable hit/track | 8 |
| `0x66` | Hero skill submenu | 0 |
| `0x67` | Building submenu | 0 |
| `0x68` | Minimap ping | 12 |
| `0x69`/`0x6A` | Dialog button(s) | 16 |
| `0x6B`/`0x6C`/`0x6D` | GameCache sync + value | 3×str + 4 |
| `0x70`~`0x74` | GameCache sync empty | 3×str |

> APM 计数建议仍只统计：`0x10~0x13`、`0x16~0x19`、`0x1B`、`0x1C`、`0x61`、`0x66`、`0x67`（行业工具略有差异，以 nagger 标准为基准）。

---

## 四、与 DotA / `game.dll` 的关系（不变部分）

- 脚本侧 `SyncStoredInteger` → `game.dll` 硬编码组装 **`0x6B`**（见前序文档 VA `0x6F44154A`）。
- DotA `war3map_*.j` 结算键（`dr.x` / `"0".."9"` / `"Global"` / `"Winner"`）协议不变。
- `0x60` 聊天包内 Trigger/Event 句柄仍是运行时动态分配（见 `dota-0x60-chat-action-dynamic-handles.md`）。

---

## 五、代码改动摘要（War3Bot）

已修正：

1. `getActionPayloadLength`：完整 1.26 动作长度表；`0x1A→0`；`0x66` 不再走 GameCache；未知 ID 返回 `-1` 中止本包，避免吞流。
2. `categorizeAction` / `getActionName`：纠正命名；新增 `Trigger` 类别；`SyncData` 仅覆盖 `0x6B+`。
3. `processPlayerActions`：同步解析只认 `0x6B/0x6C/0x6D`。

用日志原始 hex 回放校验：上述全部“未知”样本在校正后均可 **完整吃干**，末尾对齐到 `0x19` Subgroup，不再产生伪 ID。

---

## 六、仍可继续逆向的点

| 项 | 状态 |
| :--- | :--- |
| `0x6E` SyncUnit 变长结构 | 已知名、未在 DotA 主路径使用；长度实现可后续按 Tinker inventory/skills 前缀精确化 |
| `0x69`/`0x6A` 在极早补丁是 ContinueGame | 1.26 按 Dialog 命名；载荷同为 16B，步进不受影响 |
| Reforged `0x76~0x7B` | 已部分占位；非 1.26 DotA 主路径 |
| `game.dll` Action jump table 全量地址 | 可用 Ghidra 对 `EnqueuePlayerAction` 调用点做 xref 补全稀有 ID |

---

## 七、参考

- nagger/blue《WarCraft III Replay action format》`w3g_actions.txt`
- Strilanc/Tinker `Game Action Protocol.vb`
- w3grs `action.rs`（docs.rs）
- 本仓库：`War3Bot/src/client.cpp`、`War3Analysis/analyses/warcraft-iii-action-ids-and-dota-stats-transmission.md`
