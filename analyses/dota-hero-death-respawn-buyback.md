# DotA 6.83d 英雄死亡 / 复活倒计时 / 买活就绪（在线 LLM + 离线微操）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Cursor Composer |
| **分析目的** | 补齐 AI「死后停手 / 算复活 / 要不要买活」的只读数据与发包规格；同时服务离线 10ms 微操与在线大模型指挥层 |
| **命名方式** | `dota-hero-death-respawn-buyback`；导图 `*-mindmap.md`；产物 `artifacts/hero-death-buyback/` |
| **分析时间** | 2026-11-23 |
| **验证状态** | 地图脚本全文审计 + `game.dll` 全 11 版 `UnitAlive` / `TimerGetRemaining` / `TimerGetElapsed` / `ReviveHero` / `GetWidgetLife` 原生 handler 均已按注册点解出（与 `artifacts/hero-death-buyback/native_rva_table.md` 一致）。**未实机**读 `F0` 计时器 / 买活前后金币 |
| **证据** | `War3Script/war3map_start_timer.j`（`OPO`/`WD1`）、`war3map_1.j`（`GV1`/`GN1`/`GM1`/`IC1`）、`war3map_2.j`（`D7O`）、`war3map_9.j`（`ZS`/`WS`/`F0` 初始化）；[`dota-ai-llm-mcp-verify.md`](./dota-ai-llm-mcp-verify.md) 买活纠错；`artifacts/hero-death-buyback/` |
| **任务单** | [`../tasks/composer-hero-death-respawn-buyback.md`](../tasks/composer-hero-death-respawn-buyback.md) |
| **配套思维导图** | [`dota-hero-death-respawn-buyback-mindmap.md`](./dota-hero-death-respawn-buyback-mindmap.md) |

---

## 第一段：结论

1. **复活倒计时**：地图用每玩家计时器 `F0[pid]`；死亡函数 `OPO` 里  
   `ABO = R2I((level·3.8+5)·A5·A6·A7·A8) + A9`（再乘 AAO，可加 YS 买活打断罚时）→ `TimerStart(F0[pid], ABO, false, null)`。UI 用 `TimerGetRemaining(F0[pid])`（`HX2`）。AI **首选**：死亡边沿按同公式缓存 `deathAt + ABO`；有 JASS 句柄时再读 `TimerGetRemaining`。
2. **死亡判定**：脚本 `IC1(u) = GetUnitTypeId(u)<1 || IsUnitType(DEAD)`；引擎侧只读用 **`UnitAlive` 原生**（全 11 版 handler 已表）或 `GetWidgetLife<=0`。死亡时 `HJ[pid]=true`，复活 `WD1` 置 `false`。
3. **买活**：费用 `WS[GV1(level)]`（50…3000，档 `GV1`）；发包选能量圈 `D30[pid]` + **`0x10` + `ZS[GV1(level)]`**（不是英雄 FourCC）。`XS[pid]` 是**禁买活布尔**，不是剩余秒；360s 冷却靠 `GN1` 定时器 + 库存 `'h0D4'`。
4. **分层用法**：离线 AI 死后清补刀状态机、倒计时到 0 再出门；LLM 看 `respawn_s / buybackCost / buybackReady` 决定是否买活。

---

## 1. 地图侧：死亡 → 复活

### 1.1 计时器与标志

| 符号 | 类型 | 含义 |
| :--- | :--- | :--- |
| `F0[pid]` | `timer` | 本玩家复活倒计时（`war3map_9.j` 创建） |
| `W[pid]` | int | 累计/本次复活秒（`WL` 模式特殊） |
| `YS[pid]` | int | 买活打断时：剩余复活时间 ×0.25，加到**下次**死亡 `ABO` |
| `JS[pid]` | real | 买活时：`TimerGetElapsed(M)+TimerGetRemaining(F0)`（绝对时刻戳） |
| `HJ[pid]` | bool | 英雄「死透」标记：`OPO` 置 true，`WD1` 复活清 false |
| `XS[pid]` | bool | 禁买活（如某些死亡类型 `AHO`）；**不是**冷却秒数 |
| `M` / `N` | timer / real | 全局钟；`N` = 号角时 `TimerGetElapsed(M)`（买活费用用 `M-N`） |

复活回调：`TriggerAddAction(..., WD1)` → 回泉水坐标、`TimerStart(F0, 0, ...)` 清倒计时、处理血精石等。

### 1.2 复活时长公式（`OPO`）

```text
A5O=1; A6O=1; A7O=1; A8O=1; A9O=0; AAO=1
若 I4O（转生类）: A5O=0.4
若 Techies 自杀一类: A8O=0.5
A9O = -4 * 血精石充能   （有血精石时）
ABO = R2I((GetHeroLevel*3.8 + 5) * A5O*A6O*A7O*A8O) + R2I(A9O)
若 OCI: ABO = R2I(ABO*0.5)
ABO = ABO + YS[pid]          // 上次买活打断罚时
若 hashtable 4333: ABO += 30
若某些技能等级: AAO=0.8; ABO = R2I(ABO*AAO)
若 WL（特殊模式）: TimerStart(F0, 1.0) 否则 TimerStart(F0, ABO)
```

**常规对线（无转生/无血精石/无罚时）**：

| 等级 | ABO（秒） |
| ---: | ---: |
| 1 | 8 |
| 5 | 24 |
| 10 | 43 |
| 15 | 62 |
| 25 | 100 |

`A6O`/`A7O` 在 `OPO` 正文中默认保持 1（本轮未见赋值）；若他处改写标 **未确认**。

### 1.3 买活费用与占位单位

```text
GV1(level):
  GW1 = TimerGetElapsed(M) - N          // 真实对局秒
  BX1 = R2I(GW1)/60 - (1/2)             // JASS 中 1/2==0 → 即游戏分钟
  GX1 = 100 + level²*1.5 + BX1*15
  return clamp(R2I(GX1/50), 0, 59)

cost = WS[GV1(level)]                   // 50,100,...,3000
stock_unit = ZS[GV1(level)]             // h09G,h09T,... 
```

完整 60 档：[`artifacts/hero-death-buyback/zs_buyback_table.json`](../artifacts/hero-death-buyback/zs_buyback_table.json)（FourCC + `WS_gold`）。

`D7O` 条件（买活成功）：英雄 `IC1==true`（死）、卖方=己方能量圈、非死神镰刀 `LY[hid][4304]!=1`、`XS[pid]==false` → `ReviveHero` + 扣 `EL0` 可靠金 `WS[...]` + `GN1`（360s 冷却：清 `ZS` 库存、挂 `'h0D4'` 0 库存、360s 后 `GM1` 恢复）。

---

## 2. game.dll 原生（全 11 版）

与扫描产物一致：[`artifacts/hero-death-buyback/native_rva_table.md`](../artifacts/hero-death-buyback/native_rva_table.md)。

| Version | UnitAlive | TimerGetRemaining | TimerGetElapsed | ReviveHero | GetWidgetLife |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1.0.17.5988 | `0x26eac0` | `0x2afb60` | `0x2af9a0` | `0x2c33a0` | `0x2bbcf0` |
| 1.0.20.6048 | `0x26eac0` | `0x2afb60` | `0x2af9a0` | `0x2c33a0` | `0x2bbcf0` |
| 1.20.4.6074 | `0x26ebe0` | `0x2afc80` | `0x2afac0` | `0x2c34c0` | `0x2bbe10` |
| 1.21.0.6263 | `0x271da0` | `0x2b3250` | `0x2b3090` | `0x2c6a90` | `0x2bf3e0` |
| 1.22.0.6328 | `0x2dfc20` | `0x3ba8a0` | `0x3ba860` | `0x3bfd90` | `0x3bd930` |
| 1.23.0.6352 | `0x2e1160` | `0x3bc5c0` | `0x3bc580` | `0x3c1ab0` | `0x3bf650` |
| 1.24.1.6374 | `0x2e1220` | `0x3c1e80` | `0x3c1e40` | `0x3c7570` | `0x3c5110` |
| 1.24.4.6387 | `0x2e12e0` | `0x3c1f40` | `0x3c1f00` | `0x3c7630` | `0x3c51d0` |
| 1.25.1.6397 | `0x2e0590` | `0x3c11d0` | `0x3c1190` | `0x3c68c0` | `0x3c4460` |
| 1.26.0.6401 | `0x2e07c0` | `0x3c1400` | `0x3c13c0` | `0x3c6af0` | `0x3c4690` |
| 1.27.0.52240 | `0x70a0c0` | `0x1f1b00` | `0x1f8f80` | `0x1f3300` | `0x1f7db0` |

> `IsUnitAliveBJ` / `IsUnitDeadBJ` 字符串在 `game.dll` 中**未找到**（多为 common.j 包装）；AI 用 `UnitAlive` 即可。

**线程**：原生必须在游戏主线程（`aiTick` / GamePlaying）。

---

## 3. AI 只读 API（建议）

```cpp
struct HeroDeathState {
  bool dead;           // !UnitAlive(hero) 或 IC1 等价
  float respawnRem;    // 秒；活着为 0
  int buybackCost;     // WS[GV1(level)]
  int buybackIdx;      // GV1
  uint32_t buybackUnit;// ZS[idx] FourCC
  bool buybackReady;   // dead && !xsBlocked && !cd360 && gold>=cost && !reaper
  bool buybackBlocked; // XS 或 LY[4304] 或 h0D4 冷却中
};

// 离线推荐路径（不依赖 F0 句柄）：
onDeathEdge:
  abo = computeAbo(level, modifiers);
  deathAt = gameTime();
  cachedRem = abo;
onTick:
  rem = max(0, deathAt + abo - gameTime());
  // 可选校验：若能拿到 F0 → rem = TimerGetRemaining(F0[pid])

buybackCost:
  idx = clamp(int((100 + level*level*1.5 + gameMin*15) / 50), 0, 59);
  return WS[idx];  // == 50*(idx+1)
```

### 发包（买活）

1. 选中己方能量圈单位 `D30[pid]`（`n01F` 类）。  
2. `0x10` + `abilityFlags`（单英雄常用 `0x0040`/`0x0044`）+ **`ZS[GV1(level)]`**。  
3. 成功则记 `buybackAt`，360s 内 `buybackReady=false`（勿读 `XS` 当秒数）。

与 [`war3-order-packet-flags-and-ability-item-cooldown.md`](./war3-order-packet-flags-and-ability-item-cooldown.md) 的 `0x10` 规则一致。

### 分层

| 层 | 用法 |
| :--- | :--- |
| **离线微操** | `dead`→停 lasthit/卡兵/对线；`respawnRem` 显示；复活边沿再启动出门；买活仅当 LLM/规则显式请求 |
| **在线 LLM** | 快照字段 `alive/respawn_s/buyback_cost/buyback_ready`；意图 `buyback` → 执行层按上表发包 |

---

## 4. 建议改动（只写文档）

1. `SharedMemory` / MCP `get_status` 增加 `HeroDeathState`。  
2. `aiTickRoutine`：`dead` 时强制 `state=DEAD_WAIT`，打断补刀。  
3. 修正任何仍用「英雄 FourCC 买活」或「`XS`=冷却秒」的注释/设计（以本文 + mcp-verify 为准）。  
4. `-score start laning`：死后统计勿记「没补到」直到复活（可选）。

### 一分钟实机

1. 自杀/送死，看左上倒计时是否 ≈ `R2I(level*3.8+5)`。  
2. 记 `UnitAlive` 翻转时刻与 UI 到 0 是否同秒。  
3. 买活：能量圈点对应价位单位，确认复活且 360s 内不能再买。

---

## 5. 与旧文档关系

| 文档 | 关系 |
| :--- | :--- |
| `dota-ai-llm-mcp-control.md` | 买活/复活字段原述不完整；以本文 + verify 为准 |
| `dota-ai-llm-mcp-verify.md` | `ZS`/`XS`/`D7O` 纠错已吸收；本文补 **ABO 公式与 F0 / UnitAlive RVA** |
| `dota-ai-laning-routine.md` | 对线流程可挂 `DEAD_WAIT`；本文不改其出门装逻辑 |
