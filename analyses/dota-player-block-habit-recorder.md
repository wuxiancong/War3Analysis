# DotA 玩家卡兵习惯采集与 AI 模仿 — 方案

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 说明如何采集**真人卡兵**数据供 AI 参考；对齐现有 `block` 测量口径与 `learn`/`lasthit` 习惯目录 |
| **命名方式** | `dota-player-block-habit-recorder`；导图 `*-mindmap`；代码短名 `BlockHabit` / `block_habits` |
| **分析时间** | 2026-11-18 |
| **状态** | **半成品**：`tactic run block 3` 已能按波打分并打 `📍` 轨迹日志；**尚未**落盘 `data/block_habits/` 与跨局画像 |
| **机制依据** | [`dota-lane-creep-trajectory.md`](./dota-lane-creep-trajectory.md)、[`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md) §`block`、[`dota-player-lasthit-habit-recorder.md`](./dota-player-lasthit-habit-recorder.md) |
| **代码现状** | `War3Launcher/hooker/war3hook_ai_tactics.inl`（`AiBlockMeasure.human` / `run block 3`） |
| **配套思维导图** | [`dota-player-block-habit-recorder-mindmap.md`](./dota-player-block-habit-recorder-mindmap.md) |

---

## 一、直接回答

| 问题 | 答案 |
| :--- | :--- |
| 怎么采真人卡兵？ | 开局后执行 **`tactic run block 3`**：AI **不控英雄**，你在中路兵营门口自己卡；每波自动用与 AI 相同的延迟口径打分，并每 **50ms** 记「英雄相对兵线前沿」的前后/横向（原 200ms 会漏掉 150~250ms 停顿窗）。 |
| 要不要逆向 `game.dll`？ | **否。** 波次时钟 + 单位坐标 + Action（move/stop）足够。 |
| 日志够不够给 AI 用？ | **够做对照，不够做稳定画像。** 现状只写 AI 日志；要供后续加载，需落盘 `data/block_habits/<player>/`（与 `learn_habits` / `lasthit_habits` 同级）。 |
| AI 要学什么？ | 不是整段录像复放，而是 **相对兵线前沿的站位分布 + 停顿节律 + 成功波参数**（贴距、横摆、stop 时长、提前量）。 |
| 和兵线轨迹文档关系？ | 轨迹文档定 **lead / 车道坐标系**；本文定 **真人在该坐标系下的微操教师信号**。 |

---

## 二、现状（已有）

### 2.1 入口

```text
tactic run block 3     # 真人录制：AI 不动，只测量 + 📍轨迹
tactic run block 1     # 建议先采 ≥3 波基线（不卡），成功率才用「基线+1.5s」
tactic run block 2     # 清空统计（保留已学门口）
tactic status          # 可看汇总（若已接真人计数）
```

实现要点（`war3hook_ai_tactics.inl`）：

- `g_aiBlockStats.human = true` → 出兵后 **不进入** AI `aiTickCreepBlock` 走位，只开 `AiBlockMeasure`。
- 仅 **中路**（`|x-y| < 1200`）计入测量。
- 兵线前沿：本波 900 内己方兵沿车道进度最大者。
- 成功：前沿相对门口走满约 **1500** 后，`delay = actual - dist/325`；有 ≥3 波基线则阈值 = 基线均值 + **1.5s**，否则绝对 **≥2.0s**。

### 2.2 已记什么（日志）

| 信号 | 日志形态 | 含义 |
| :--- | :--- | :--- |
| 相对位置 | `📍 真人轨迹 第 N 波 t=… 前沿进度 … \| 英雄比前沿 前 … 横 …` | 每 **50ms**：沿车道 **前为正**、横向偏置（与测量同拍） |
| 波结果 | `📏 真人卡兵结果 … 延迟 … ✅/❌` | 与 AI 同口径标签 |
| 波开始 | `📏 真人卡兵：第 N 波开始测量` | 对齐 `g_aiWaveCount` |

**缺口**：无结构化 JSON/JSONL；无按账号聚合；无与 `match_*.dat` 的 Action 对齐键；非中路不采。

---

## 三、教师局怎么开（操作清单）

1. **环境**：`C:\War3Run` 联调；中路英雄（建议移速 ≥300，便于对比；冰女也可专门采「慢英雄」画像）。  
2. **（推荐）先基线**：`tactic run block 1`，站门口**侧面**，让 ≥3 波自然延迟入库。  
3. **`tactic run block 2`** 若只要清 AI 卡兵统计、保留门口；真人模式可不清基线（当前清空会一并清基线——实现时宜拆 `clear human` / `clear all`）。  
4. **开录**：`tactic run block 3`。站到中路兵营门口，**自己操作**卡前几波（建议连续 **8～15 波**，含前 7 分钟速度修正段与之后各若干波）。  
5. **收工**：看日志 `真人卡兵结果` 成功率；局后再把日志/未来 JSONL 归入账号目录。  
6. **可选并行**：Bot 侧照常记 `data/player_actions/<player>/match_*.dat`，用于抽 move/stop 节律（见 §4.2）。

注意：

- 真人模式 **`repeat=false`**：AI 不会帮你跑回门口，需自己每波到位。  
- 对面有英雄压线 / 领头兵半路死亡 → 本波 **invalid**，不计入成功率（与 AI 相同）。  
- 攻城车波可标 `isSiegeWave`，默认画像仍以近战前沿为准。

---

## 四、应采集的字段（给 AI）

### 4.1 主通道：hook 相对坐标系（推荐，已有采样）

相对 **门口原点 + 朝中心车道**（与测量同一套）：

| 字段 | 说明 | AI 用法 |
| :--- | :--- | :--- |
| `tMs` | 相对本波测量起点 | 时序 |
| `frontProgress` | 前沿沿车道进度 | 对齐「走到哪一段」 |
| `heroAhead` | 英雄进度 − 前沿进度（+ = 在兵前） | **贴距分布**（目标 ~25–45） |
| `heroLateral` | 相对前沿的横向 | **横摆 / 堵侧面** |
| `action`（增强） | 近窗 move / stop(0xD0004) | 停顿 vs 领跑 |
| `pauseMs`（增强） | 连续 stop 或位移≈0 的时长 | stop 150–250ms 标定 |

波级标签：

| 字段 | 说明 |
| :--- | :--- |
| `waveIndex` / `gameMinute` | 波次与分钟（前 7 分单独桶） |
| `delayS` / `success` | 同口径结果 |
| `heroCode` / `ms` | 英雄与移速（静态表或运行时） |
| `lane` | MVP 固定 `mid`；二期 top/bot |

### 4.2 辅通道：`match_*.dat` Action

在波窗 `[waveTick, waveTick+14s]` 内统计：

- 短距 `move` 间隔分布、幅度；  
- `stop` 次数与间隔；  
- 与 hook 轨迹时间对齐后，可验证「贴住时是否真的发了 stop」。

**不必**像素鼠标；**不必**新挖 dll。

### 4.3 不采（MVP）

- 敌方英雄全量轨迹；  
- 非中路（未标定门口前）；  
- 完整每帧所有小兵血量。

---

## 五、落盘约定

与加点 / 补刀同级：

```text
data/block_habits/<player>/
  _global.json                 # 跨局聚合画像（AI 加载）
  <heroCode>.json              # 可选：分英雄（移速差异大时优先）
  sessions/<matchId>.jsonl     # 单局：每行一波或一条采样
  teacher_wave_*.jsonl         # 可选：富采样（含 action）
```

运行时路径：优先 `C:\War3Run\War3Bot\data\...`（或 Launcher 侧同源 `data`，与现有 player_actions 约定一致即可）。

### 5.1 单波 JSONL 行（草案）

```json
{
  "schema": 1,
  "player": "wuxiancong",
  "hero": "Hjai",
  "waveIndex": 3,
  "tSpawnMs": 90000,
  "lane": "mid",
  "delayS": 2.4,
  "success": true,
  "baselineRefS": 1.1,
  "samples": [
    {"t": 0, "front": 80, "ahead": 120, "lat": -30},
    {"t": 50, "front": 100, "ahead": 40, "lat": 10},
    {"t": 100, "front": 140, "ahead": 35, "lat": 8}
  ],
  "stats": {
    "medianAhead": 38,
    "p90Ahead": 70,
    "medianAbsLat": 22,
    "stopCount": 6,
    "medianStopMs": 190,
    "moveIntervalMs": 180
  }
}
```

### 5.2 聚合画像 `_global.json`（草案）

```json
{
  "schema": 1,
  "player": "wuxiancong",
  "waves": 42,
  "successRate": 0.45,
  "meanDelayS": 2.8,
  "aheadMean": 35,
  "aheadStd": 12,
  "stickGapMin": 25,
  "stickGapMax": 45,
  "stopMsMean": 200,
  "stopMsStd": 40,
  "lateralBias": 0,
  "preWaveStand": {"ahead": 100, "lat": 130},
  "byMinuteBucket": {
    "0_7": {"aheadMean": 40, "stopMsMean": 220},
    "7_plus": {"aheadMean": 32, "stopMsMean": 180}
  }
}
```

AI `block` 读取后覆盖/软偏置现有硬编码：`ahead 25~45`、`stop 150~250`、门口斜前方 `(100,130)` 等。

---

## 六、架构

```text
【教师局】
  玩家中路卡兵
        │
        ├─ tactic run block 3
        │     → AiBlockMeasure.human
        │     → 每 50ms 相对坐标 + 波末 delay/success
        │
        └─（并行）match_*.dat  Action 窗
        │
        ▼
  BlockHabitWriter → data/block_habits/<player>/sessions/...
        │
        ▼
  BlockHabitAggregator → _global.json / <hero>.json
        │
【AI 局】
  加载账号画像 → 参数化 aiTickCreepBlock
    stickGap / stopMs / lateral / preWaveStand / 是否敢 intercept
```

登录键：与 `player_actions` / `learn_habits` 同一 `playerName`。

---

## 七、AI 如何用这些数据

| 画像字段 | 写入 `aiTickCreepBlock` |
| :--- | :--- |
| `stickGapMin/Max` | 贴住判定 `gap` 窗（现 15–90 触发 stop 可收窄到真人分位） |
| `stopMsMean±Std` | `aiRandRange` 停顿时长 |
| `aheadMean` | 走位 `ahead` 目标（现 25–45） |
| `lateralBias` / 横摆分位 | 堵侧面幅度 |
| `preWaveStand` | `aiTickBlockReturnHome` 斜前方偏移 |
| `byMinuteBucket` | 前 7 分 vs 之后两套参数 |
| 成功波子集 | 只聚合 `success=true` 的样本，避免学失败站位 |

原则：**模仿分布，不逐帧回放**；成功标签与现网测量一致，避免「看起来像真人但延迟不涨」。

---

## 八、实现步骤（编码勾选）

1. **文档**（本文）— 完成。  
2. **教师落盘**：`run block 3` 的 `📍`/`结果` 同时写 JSONL（路径见 §5）；波结束 flush。  
3. **Action 对齐（可选）**：同波窗统计 stop/move → 填 `stats`。  
4. **Aggregator**：局末或工具脚本合并 → `_global.json`。  
5. **加载**：`AiControl` / 进局读账号画像 → 注入 `AiBlockState` 默认参数。  
6. **验收**：同英雄 `run block` vs `run block 3` 教师成功率对比；目标：AI 延迟分布靠近教师成功波。  
7. **（二期）** top/bot 门口学习；分英雄画像；与 `lane_traces` 同 matchId 联表。

**不必**为采集新挖 `game.dll` RVA。

---

## 九、风险

| 风险 | 对策 |
| :--- | :--- |
| 只写日志难聚合 | MVP 就落 JSONL，日志仅调试 |
| 基线被 `run block 2` 清掉 | 拆 clear 命令；或基线写入 `sessions` 持久化 |
| 慢英雄学不会快英雄参数 | 分 `heroCode` / 按 `ms` 桶 |
| 失败波污染 | 聚合默认 `success=true`；另存失败对照 |
| 非中路 | MVP 跳过；门口未标定不写样本 |
| 前 7 分移速修正 | `byMinuteBucket` 分开 |

---

## 十、总结

- **今天就能采**：`tactic run block 3` +（建议）先 `run block 1` 基线；人在中路自己卡，看 `📍`/`真人卡兵结果`。  
- **给 AI 用**：把相对兵线前沿的轨迹与成功标签落到 **`data/block_habits/<player>/`**，聚合成贴距/停顿/站位画像，再参数化现有 `block`。  
- **与轨迹方案分工**：轨迹解决「兵往哪走」；本方案解决「人怎么挡」。

---

## 十一、参考锚点

- 真人模式：`war3hook_ai_tactics.inl` `p.p1 == 3` / `m.human` / `📍 真人轨迹`  
- 测量与成功：同文件 `aiTickBlockMeasure`、`kAiBlockCheckpoint` / `kAiBlockOverBaselineS`  
- 兵线坐标系：[`dota-lane-creep-trajectory.md`](./dota-lane-creep-trajectory.md)  
- 卡兵实测史：[`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md) §五点五  
- 习惯目录对标：`dota-player-learn-habit-recorder.md` / `dota-player-lasthit-habit-recorder.md`
