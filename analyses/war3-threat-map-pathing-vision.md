# War3 / DotA 6.83d「危险地图」运行时数据：通行 · 视野 · 威胁

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 为 LLM/MCP 托管执行层定义：实时通行、合法视野、威胁场如何取数；标明作弊红线与全版本 RVA；给出危险地图设计（不写 hook 代码） |
| **命名方式** | `war3-threat-map-pathing-vision`；导图 `*-mindmap`；产物 `artifacts/threat-map/` |
| **分析时间** | 2026-11-21 |
| **验证状态** | **静态全版本扫描 + 既有文档交叉核对完成**；本机检测时无 war3 在跑，**未实机读迷雾栅格边长 / 未跑 `Start-AiGame`**。通行合成与威胁公式为设计规格 |
| **证据** | `versions/*/game.dll` 原生注册；[`warcraft-iii-fog-of-war-implementation.md`](./warcraft-iii-fog-of-war-implementation.md)；[`dota-683d-vision-and-fog-juke.md`](./dota-683d-vision-and-fog-juke.md)；[`dota-6.83d-eat-and-cut-tree-reverse.md`](./dota-6.83d-eat-and-cut-tree-reverse.md)；[`war3-tower-creep-aggro.md`](./war3-tower-creep-aggro.md)；[`dota-ai-llm-mcp-control.md`](./dota-ai-llm-mcp-control.md)；`artifacts/threat-map/` |
| **配套思维导图** | [`war3-threat-map-pathing-vision-mindmap.md`](./war3-threat-map-pathing-vision-mindmap.md) |

---

## 一、核心结论

| 问题 | 结论 |
| :--- | :--- |
| 实时通行怎么做 | **静态 `wpm`(512×512×32) + 运行时树存活遮罩**；查询用游戏线程 `IsTerrainPathable` / 树枚举。**不要**在游戏线程外调引擎寻路折线 API |
| 树倒/重生 | `CDestructable+0x64` life；`GetDestructableLife` / `EnumWidgetsInRect`；5 分钟脚本重生。倒下则去掉 4×4 格树 footprint |
| 视野 | 迷雾管理器两张 `uint16` 栅格（已探索 / 当前可见）；单位可见走 `IsUnitVisible`（vtable+0xFC）。**只返回本机可见信息** |
| 威胁 | 塔 **700**（已核）；小兵 acquire 见 aggro 文档；技能 `Rng1` 见 `ability_cast_ranges.json`；昼夜用 `sight`/`nsight` + `TIME_OF_DAY` |
| 寻路折线 | 引擎内部 `CLrPath` 等**无稳定、无文档的对外「返回整条折线」JASS**；执行层应 **自建 A\***（合成格网），仅用原生做可达/单点校验 |

---

## 二、运行时通行

### 2.1 静态底图（已有）

见 [`dota-6.83d-web-gameplay-data-reverse.md`](./dota-6.83d-web-gameplay-data-reverse.md) §7：

- `war3map.wpm`：`MP3W`，**512×512**，格边 **32** 世界单位；`& 0x02` 不可行走（装饰物章已烘进）。
- 树**不在** wpm 里；`doo` 中 RJI 树约 3675，按 **4×4 格（128×128）** footprint 盖章。

### 2.2 运行时如何更新

| 事件 | 引擎/脚本 | 执行层做法 |
| :--- | :--- | :--- |
| 吃树/砍树 | `CAbilityEatTree` 把 `CDestructable` life→0，播倒下 | 该树 footprint **解除阻挡** |
| 5 分钟重生 | `AA2`/`AB2` 复活 life&lt;1 的树 | footprint **重新盖上** |
| 单位/建筑 | 碰撞盒 + pathing footprint（见 [`war3-unit-collision-and-repath.md`](./war3-unit-collision-and-repath.md)） | 威胁/避让用单位表；全图动态建筑遮罩成本高，可只对附近 2000 内采样 |

**树是否存活（只读）**：

| 字段 | 含义 |
| :--- | :--- |
| `CDestructable +0x64` | 当前 life（float） |
| `vtable[+0x13C]` | 是否死亡 |
| JASS | `GetDestructableLife` / `EnumDestructablesInRect` |
| 内部枚举 | `EnumWidgetsInRect` mask `0x04FB0000`（全版本表见吃树文档） |

### 2.3 单点通行查询（可游戏线程调用）

`IsTerrainPathable(x, y, pathingType)` — JASS 原生；**必须在游戏主线程**（与 MCP 文档红线一致）。

全版本 native RVA（注册点 `mov ecx, native` / 文档覆盖交叉）：

| 版本 | `IsTerrainPathable` |
| :--- | :--- |
| 1.0.17.5988 | `0x2DC5C0` |
| 1.0.20.6048 | `0x2DC5C0` |
| 1.20.4.6074 | `0x2DC6E0` |
| 1.21.0.6263 | `0x2DFCB0` |
| 1.22.0.6328 | `0x3B7440` |
| 1.23.0.6352 | `0x3B0790` |
| 1.24.1.6374 | `0x3B4D50` |
| 1.24.4.6387 | `0x3B4E10` |
| 1.25.1.6397 | `0x3B40A0` |
| **1.26.0.6401** | **`0x3B42D0`**（xref `0x3D9797` 旁 `B9 3B42D0` 实证） |
| **1.27.0.52240** | **`0x1E8440`** |

`pathingType` 常用 walkability（common.j `PATHING_TYPE_WALKABILITY`）。完整原生表：[`artifacts/threat-map/native_rva_table.md`](../artifacts/threat-map/native_rva_table.md)。

### 2.4 「返回路径」的引擎函数

- **结论**：没有适合 MCP 线程调用的、稳定公开的「输入起终点 → 返回折线点列」JASS。
- 内部存在 `CLrPath` / pathing 系统（碰撞绕行文档），**跨版本布局变动大，且依赖游戏线程与单位上下文**。
- **设计裁定**：执行层用 **合成格网 A\***；可选在游戏线程对关键边做 `IsTerrainPathable` 抽检。文档层**禁止**在 IPC/MCP 线程直接 call 引擎寻路。

---

## 三、视野 / 迷雾

### 3.1 迷雾管理器（1.26 反汇编，机制跨版同构）

前序 [`warcraft-iii-fog-of-war-implementation.md`](./warcraft-iii-fog-of-war-implementation.md)：

| 项 | 内容 |
| :--- | :--- |
| 入口 | 全局游戏对象 `+0x34` → 迷雾管理器 |
| `+0x2C` | **已探索**栅格 `uint16`，低 12 位 = 玩家位 |
| `+0x30` | **当前可见**栅格 `uint16` |
| `+0x60/+0x6C` | 宽/高（格） |
| `+0x70/+0x74` | 1/格边长（**实机未读定**；与地图尺寸相关） |
| 三态 | Visible=4 / Fogged=2 / Masked=1（迷雾+遮罩都开时） |

DotA 开局 FogModifier 创建即毁 → 地图多为**已探索迷雾**，少见纯黑 Masked。

### 3.2 单位可见性

| API | 作用 | 1.26 / 1.27 |
| :--- | :--- | :--- |
| `GetLocalPlayer` | 本机玩家 | `0x3BBB60` / `0x1E3150` |
| `IsUnitVisible(u,p)` | 单位对玩家是否可见（迷雾+隐身综合，vtable+0xFC） | `0x3C7AF0` / `0x1E8E80` |
| `IsUnitDetected(u,p)` | 反隐侦测 | `0x3C7C80` / `0x1E8580` |
| `IsUnitFogged` / `IsUnitMasked` | 单位所在格迷雾态 | 见全表 |
| `IsLocationVisibleToPlayer(x,y,p)` | 点是否当前可见 | `0x3C9940` / `0x1E7DE0` |

**全 11 版 RVA** 见 `artifacts/threat-map/native_rva_table.md`（与 [`dota-ai-llm-mcp-control.md`](./dota-ai-llm-mcp-control.md) § 全版本表一致处已覆盖）。

### 3.3 单位视野半径与高地

| 来源 | 字段 |
| :--- | :--- |
| `UnitBalance.slk` | `sight`（昼）、`nsight`（夜） |
| 塔 | sight 1900 / nsight 800（aggro 文档） |
| 小兵 | 850 / 800（约） |
| 昼夜 | `GetFloatGameState(GAME_STATE_TIME_OF_DAY)`；夜晚用 `nsight` |
| 树挡视线 | `DestructableData.occH`（ATtr≈230） |
| 高地 | 引擎视线；辅助可用 `GetLocationZ`（全表已列）比较相对高度。**精确射线算法未本任务逐条反汇编** |

### 3.4 最后可见位置（合法）

```text
on tick:
  if IsUnitVisible(enemy, lp):
      last_seen[enemy] = {x,y,t_now}; visible_now=true
  else:
      visible_now=false
      # 禁止再读 enemy 的实时世界坐标写入快照
```

### 3.5 作弊红线（必须遵守）

详见 [`artifacts/threat-map/cheat_redlines.md`](../artifacts/threat-map/cheat_redlines.md)。

**读了就算作弊（不得进 MCP / SharedMemory）**：

- 迷雾中敌方单位的**实时坐标 / 血量 / 面向**
- 用迷雾栅格 + 单位表「反查」不可见敌人位置
- 肉山在迷雾中的存活与血量

**合法**：本机 Visible/Detected 单位；`last_seen`；公开 `FL1` 事件；地形/树/通行。

---

## 四、威胁参数

### 4.1 塔（引用已完成任务）

[`war3-tower-creep-aggro.md`](./war3-tower-creep-aggro.md)：各级塔 **`range = acquire = 700`**，弹速 750，T1 cool 1.0 / T2+ 0.95。进塔：`dist ≤ 700`。

### 4.2 兵线

同文档：近战 acquire **500**，`edry` **800**，`unec` **600**，攻城 **800**；攻击射程近战 100 / 远程 500 / 攻城 690。

### 4.3 英雄技能施法距离

- 物编：`Units_AbilityData.slk` 的 **`Rng1`**（可逗号分级）、**`Area1`**、**`Cool1`**。
- 导出：[`artifacts/threat-map/ability_cast_ranges.json`](../artifacts/threat-map/ability_cast_ranges.json)（1135 条带射程的技能；含 `99999` 类无限距，使用时过滤）。
- 运行时精确值：技能链表 + 当前等级（见 [`dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md`](./dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md)）；威胁场可用「当前等级 Rng」或保守取 max。
- [`dota-683d-ai-data-tables.md`](./dota-683d-ai-data-tables.md) 偏坐标/卡尔/隐藏技，**不重复抄全表**；威胁用本导出补齐 `Rng1`。

### 4.4 昼夜

- 昼：`sight`；夜：`nsight`（英雄/塔常大幅缩短）。
- `FoggedAttackRevealRadius=200`（雾中 A 会暴露）— 绕雾走位勿无意义攻击。

---

## 五、执行层危险地图设计（不写代码）

### 5.1 图层

```text
Layer W  walkable   = wpm_walk AND NOT dead_tree_cleared_wrong AND NOT live_tree_block
Layer V  vision     = IsLocationVisibleToPlayer samples / fog snapshot (local only)
Layer T  threat     = max(
                       tower_ring(700),
                       visible_enemy_hero (attack_range + spell_Rng * w),
                       visible_enemy_creep (acquire),
                       last_seen_ghost * decay
                     )
Layer S  safety     = walkable ? f(threat, vision) : 0
```

### 5.2 更新频率与开销（量级）

| 任务 | 周期 | 线程 | 量级 |
| :--- | ---: | :--- | :--- |
| 树枚举（英雄周围 2000 或脏区） | 500 ms | 游戏 | `EnumWidgetsInRect` 局部，&lt;1 ms |
| Visible / last_seen | 100 ms | 游戏 | 与现有 units 枚举合并 |
| 威胁场（降采样 64 码格） | 200 ms | 游戏写快照 / MCP 读 | O(格×可见威胁源) |
| `safe_path` A* | 按需 | **MCP/Launcher**（只读快照） | 256² 级可接受 |

### 5.3 MCP 查询草图

见 [`artifacts/threat-map/mcp_threat_api_sketch.json`](../artifacts/threat-map/mcp_threat_api_sketch.json)：

- `is_safe(x,y)` → `{safe, score, reasons[]}`
- `safe_path(from,to)` → 折线 + cost（A\* on 快照）
- `last_seen(hero)` → 合法最后坐标
- `is_walkable` / `is_visible` / `threat_at`

意图层只说「去中路」；执行层：`safe_path(hero, mid_wait)` + 沿途 `is_safe` 重规划。

### 5.4 与现有能力衔接

| 已有 | 用途 |
| :--- | :--- |
| `IsUnitVisible` 过滤（MCP 文档） | 快照红线 |
| `EnumWidgetsInRect` 树扫描 | 通行叠加 |
| `buildings.json` / 塔 700 | 塔威胁环 |
| lane waypoints | 兵线走廊先验 |
| fog-juke 暴露分 | 可并入 `reasons` |

---

## 六、建议实机验证（主会话；勿杀卡兵进程）

当前无 war3 时跳过。有空窗时：

1. 只读：迷雾管理器 `+0x70` 格边长；对比 `IsLocationVisibleToPlayer` 与栅格位。
2. 砍一棵树前后：`IsTerrainPathable` 与合成格是否一致。
3. 敌英雄进雾：确认 SharedMemory/`units` **无坐标**，仅 `last_seen` 保留。

---

## 七、产物清单

| 路径 | 内容 |
| :--- | :--- |
| `analyses/war3-threat-map-pathing-vision.md` | 本文 |
| `analyses/war3-threat-map-pathing-vision-mindmap.md` | 导图 |
| `artifacts/threat-map/native_rva_table.md` | 全版本原生 RVA |
| `artifacts/threat-map/native_string_xrefs.json` / `resolved_natives.json` | 扫描原始数据 |
| `artifacts/threat-map/cheat_redlines.md` | 作弊红线 |
| `artifacts/threat-map/mcp_threat_api_sketch.json` | MCP 查询设计 |
| `artifacts/threat-map/ability_cast_ranges.json` | 技能 Rng1 导出 |
| `artifacts/threat-map/scan_*.py` / `resolve_*.py` / `export_*.py` | 脚本 |

**未改** `War3Launcher` / `hooker`。
