# DotA 6.83d 兵线运动轨迹与卡兵前置方案

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 说明 30s 出兵下如何得到兵线（含首波、攻城车）运动轨迹；判断是否需逆向 `game.dll`；为后续 **卡兵** 提供可执行数据与采集步骤 |
| **命名方式** | `dota-lane-creep-trajectory`（短横线英文）；导图 `*-mindmap`；若后续有可选引擎符号，用短名如 `lane-creep-path`，勿冗长 |
| **分析时间** | 2026-11-18 |
| **样本** | `War3Script`（`SPO`/`SSO`/`O2`）；`War3Launcher/versions`（仅作可选原生偏移，非本方案必选）；hook：`war3hook_ai.cpp` 已有首波时钟 |
| **前序** | [`dota-6.83d-web-gameplay-data-reverse.md`](./dota-6.83d-web-gameplay-data-reverse.md) §6；[`dota-ai-neutral-creep-pull.md`](./dota-ai-neutral-creep-pull.md)；卡兵实测 [`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md) §`block`；真人采集 [`dota-player-block-habit-recorder.md`](./dota-player-block-habit-recorder.md) |
| **产物目录** | `War3Analysis/analyses`；原始摘录 `artifacts/dota-web-gameplay/war3map.j-creep-spawn-excerpt.txt` |
| **配套思维导图** | [`dota-lane-creep-trajectory-mindmap.md`](./dota-lane-creep-trajectory-mindmap.md) |

---

## 一、核心结论

| 问题 | 结论 |
| :--- | :--- |
| 兵线轨迹谁决定？ | **地图脚本**：出兵点 → `attack` 到路点 `O2[lane]`；进区触发器再改下一目标。引擎只做寻路/交战，**不另存「兵线曲线」**。 |
| 要不要逆向 `game.dll`？ | **卡兵 / 轨迹 MVP：不必。** 用脚本路点 + `CreateUnit` 钩子 + 周期 `GetUnitX/Y` 采样即可。 |
| 何时才挖 dll？ | 仅当要读引擎内部「当前攻击移动目标坐标 / 寻路折线」且脚本路点不够用时（可选，短名 `unit-order-target`）；**非卡兵前置**。 |
| 第一波怎么认？ | `ZG` 注册时 `TriggerExecute` 立刻出第一波；hook 侧 `g_aiFirstWaveTick` 已用首个兵线单位 `CreateUnit` 校准。 |
| 后续卡兵要什么？ | **波次时钟** + **分路折线路点** + **当波领头兵实时坐标/朝向**（再加英雄站位挡路）。 |

---

## 二、出兵与行军机制（脚本）

### 2.1 周期

```text
TriggerRegisterTimerEventPeriodic(ZG, 30.00)
TriggerExecute(ZG)          // 立刻第一波
TriggerAddAction(ZG, SPO)
```

- 每 **30 秒** 执行 `SPO`（`war3map_3.j`）。  
- `GetTriggerExecCount(ZG)==1`：第一波额外逻辑（重置能量圈等）。  
- `ModuloInteger(execCount, 7)==0`：该波额外出 **攻城车**（并顺带 `SWO` 同步 CSK/CSD）。

数量：初始近战 `NI=3`、远程 `SI=1`；999/1999/2999s 近战 +1；2699s 远程 +1；兵营倒则超级兵。

### 2.2 出生点（按路）

`SPO` 对 `BO[0]`（近卫电脑）/ `CO[0]`（天灾电脑）在各路 `Location` 上 `CreateNUnitsAtLoc`：

| 阵营 | 上路近战/远程等 | 中路 | 下路 |
| :--- | :--- | :--- | :--- |
| 天灾 `CO[0]` | `RI`/`I1` 等 | `TI`/`QI` | `PI`/`UI` |
| 近卫 `BO[0]` | `B1`/`E1` 等 | `O1`/`C1` | `A1`/`D1` |

这些 Location 在初始化里来自 **`GetRectCenter(…)`**（出兵矩形）或建筑 `GetUnitLoc`（见 `war3map_start_timer.j` / `war3map_9.j` ≈ L11577+）。

### 2.3 分路标记与路点表

```text
I2 = 1093678663          // 隐藏技能，用等级标记分路
SSO(group, laneLevel)    // SetUnitAbilityLevel(u, I2, laneLevel)
O2[1]=II  O2[2]=CI  O2[3]=BI  O2[4]=DI  O2[5]=U0
```

| `AbilityLevel(I2)` | 路点 `O2[n]` | 来源（初始化） |
| :--- | :--- | :--- |
| 2 / 3 / 4 | 分路上的攻击目标点 | `SSO(..., 2/3/4)` 在 `SPO` 里按路调用 |
| — | `II,CI,BI,DI,U0` | `GetUnitLoc` 关键建筑（基地/关键点） |

出兵后与进区后反复：

```jass
IssuePointOrderLoc(unit, "attack", O2[GetUnitAbilityLevel(unit, I2)])
```

即 **攻击移动到分路目标点**；遇敌交战，清完再朝路点。进 `Region` 的触发器（`war3map_9.j` 大量 `TriggerRegisterEnterRegion`）会在关键节点 **改下令到下一站**（与网页复现「路点链」同思路）。

### 2.4 前 7 分钟相遇修正

`SZO`/`SVO`：`TimerGetElapsed(M) < 7*60` 时给该波加加速/减速类技能，使 **中路相遇点** 更靠某一侧——轨迹会略变，卡兵时间表前 7 分钟要单独校准。

### 2.5 轨迹概念模型

```text
静态折线（每路 × 每阵营）:
  SpawnRectCenter → (中间塔区路点…) → 对方基地相关 O2[lane]

动态轨迹（某一波）:
  单位沿折线 attack-move；遇敌偏离；清完回到折线
  「领头兵」= 沿折线进度最大（或距己方泉水最远）的存活小兵
```

**没有**单独的「第一个兵专用路径」；同波同路近战出生点相同，领头由站位/交战自然产生。卡兵盯 **领头近战** 即可。

---

## 三、要不要逆向 `game.dll`？

| 目标 | 建议 |
| :--- | :--- |
| 知何时出兵 | **否** — 30s 触发器 + 已有 `g_aiFirstWaveTick` |
| 知出生点 / 路点 | **否** — 脚本 Location；运行时 `GetUnitX/Y` 或一次 dump |
| 知当前小兵坐标 | **否** — 已有只读 `GetUnitX/Y`（`war3hook_ai`） |
| 知引擎寻路折线缓冲 | **可选** — 仅优化；命名建议短：`lane-creep-path` / `unit-move-goal`，文档注明模型/时间；**卡兵可不做** |
| 改小兵 AI 原生 | **否** — 卡兵是英雄站位挡路，不改兵 AI |

`versions/*/game.dll`：继续用已有 JASS 原生表即可；本主题 **不强制新增 RVA**。

---

## 四、如何获取每次出兵 / 车子的运动轨迹

### 4.1 推荐管道（已有能力延伸）

```text
CreateUnit(小兵 type) 
  → aiOnUnitCreated（已识别 esen/edry/ebal/ugho/unec/umtw）
  → 波次: g_aiFirstWaveTick / g_aiWaveCount
  → 登记 handle 入 g_aiUnits
        │
        ▼
aiTick 每 N ms:
  过滤 owner∈{0,6}、兵线 type、存活
  读 x,y；按出生点/坐标聚类 → lane ∈ {top,mid,bot}
  按阵营+路 选 lead = 进度最大者
  追加采样: (t, waveId, lane, side, handle, x, y, isSiege)
        │
        ▼
可选落盘: data/lane_traces/<match>/wave_*.jsonl
静态表:   shared/DotaLaneWaypoints.h（一次校准写入）
```

### 4.2 第一波 /「第一个兵」

1. **时间**：`g_aiFirstWaveTick`（首个兵线 `CreateUnit`）；可用 0:30 野怪创建二次校正（代码已写）。  
2. **第一个兵**：该波、该路、该阵营中，**创建时刻最早** 或 **沿路点进度最大** 的近战 handle（攻城车 type 单独标 `isSiege`，卡兵通常不挡车或另策略）。  
3. **录轨迹**：从创建起每 100–200ms 记 `(x,y)` 直到死亡或进入对方高地；多波平均得「标称折线」。

### 4.3 静态路点一次校准（不必每局反编译）

进一局（或 AI 模式）在初始化后：

```text
读 GetRectCenter → B1/O1/A1/… 与 GetUnitLoc(基地建筑) → II/CI/…
写死到 DotaLaneWaypoints（世界坐标）
```

或从网页端已验证的中路交战点（约 0:20 在 `(-200,-700)` 附近）作中路参考。

### 4.4 攻城车

- 每第 7 波：`SQO` 为真时额外 `CreateNUnitsAtLoc` 攻城类型。  
- type：近卫/天灾攻城 FourCC（见 web-gameplay 表 `ebal`/`umtw` 及超级变体）。  
- 轨迹：同路 `O2[lane]`，移速更慢、射程更远；采样时 `isSiege=true` 分开统计。

### 4.5 单波落盘 schema（草案）

```json
{
  "schema": 1,
  "waveIndex": 1,
  "tSpawnMs": 0,
  "lane": "mid",
  "side": "sentinel",
  "leadHandle": "0x...",
  "samples": [{"t": 0, "x": -5200, "y": -4800}, {"t": 200, "x": -5100, "y": -4700}],
  "siege": false
}
```

目录建议：`data/lane_traces/`（与 `learn_habits` / `lasthit_habits` 同级，按需）。

---

## 五、卡兵（后续）怎么用这些数据

卡兵目标：用英雄 **挡在己方小兵前方**，拖慢兵线，使相遇点靠近己塔。

| 输入 | 用法 |
| :--- | :--- |
| `waveIndex` / 距下一波秒数 | `(g_aiFirstWaveTick + wave*30000 - now)` → 提前去卡点 |
| 分路折线 | 在领头兵前方 `blockOffset`（如 150–250）取站位点 |
| 领头兵 `(x,y)` + 切线方向 | `stand = lead + normalize(waypoint - lead) * offset`（挡在前进方向上） |
| 己方/敌方波距离 | 决定卡多久、何时放行补刀 |

已有入口：`tactic on block` / `tactic run block`（见技巧库 §`block` 与成功率判定）。实现走现有 `-move` / hold；**不改小兵 Action**。

本文轨迹方案用于 **校准路点、统一 lead 定义、可选落盘**，支撑后续把「一直跟在兵前」改成「贴住 + 短停让兵绕路」（技巧库第四轮结论）。

---

## 六、实现步骤（编码勾选）

1. **文档**（本文 + mindmap）— 完成。  
2. **静态路点 dump**：一局内打印各 spawn Location / `O2[]` 坐标 → `DotaLaneWaypoints.h`。  
3. **领头兵跟踪**：在 `aiTick` 按路维护 `leadHandle` + 可选 `data/lane_traces/` jsonl。  
4. **波次 API**：暴露 / 复用 `secondsToNextWave()` / `currentWaveIndex()`（基于已有 `g_aiFirstWaveTick`）。  
5. **（卡兵改进）** 在现有 `block` 上改：贴住 lead 前方短距 → **hold/停顿** → 兵绕行再补位；对照技巧库基线延迟。  
6. **（可选）** 仅当路点不准时，再短名专题挖 `unit-move-goal`；写入 `analyses/` 并带模型/时间元信息。

---

## 七、风险

| 风险 | 对策 |
| :--- | :--- |
| 前 7 分钟速度修正 | 分段标定；或只信实时 lead 坐标 |
| 超级兵/升科技移速变化 | 以实时采样为准，静态折线只作方向 |
| CreateUnit 路径禁调 JASS | 已有约束：归属判断放 `aiTick` |
| 暂停导致 30s 漂移 | 现有 expected 对齐逻辑；野怪 0:30 再校 |
| 把野怪当兵线 | `aiIsLaneCreepType` + owner 0/6 |

---

## 八、总结

- 兵线轨迹 = **脚本出兵点 + 分路 `attack` 路点链 + 引擎交战偏离**；30s 一波，第 7 波有车。  
- **不必为卡兵逆向 `game.dll`**；扩展现有 `CreateUnit` 波次时钟与坐标采样即可拿到 **每波/首兵/攻城车** 轨迹。  
- 下一步：dump 路点表 → 领头兵跟踪 → 再做 `block` 站位。

---

## 九、参考锚点

- 出兵：`War3Script/war3map_3.j` `SPO` / `SSO` / `SZO` / `SVO`  
- 路点：`war3map_start_timer.j` / `war3map_9.j` `O2[]`、`I2`  
- 行军重下：`IssuePointOrderLoc(...,"attack",O2[...])`（`CA2`/`CD2` 等）  
- 波次时钟：`war3hook_ai.cpp` `g_aiFirstWaveTick` / `aiOnUnitCreated` / `aiIsLaneCreepType`  
- 数值表：`dota-6.83d-web-gameplay-data-reverse.md` §6  
