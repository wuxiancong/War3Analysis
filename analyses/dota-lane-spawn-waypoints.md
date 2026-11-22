# DotA 6.83d 六路出兵点、路点链与出兵时序

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 为卡兵 AI 提供精确出兵 rect/坐标、路点折线、波次组成与时序；解释 `kAiLanes` 偏差与「号角前开 block 认不到波」 |
| **命名方式** | `dota-lane-spawn-waypoints`（短横线英文）；导图 `*-mindmap`；头文件 `DotaLaneWaypoints.h` |
| **分析时间** | 2026-11-21 |
| **验证状态** | **脚本已核对**（`War3Script/war3map_3.j` / `_9.j`）；出兵中心与用户上路实测一致；折线中间塔点来自 `CreateUnit` 建筑坐标，**未本局 RemoteControl 再采样** |
| **证据** | `war3map_9.j` Rect L10478+、O2 L11577+、进区 L16171+；`war3map_3.j` `SPO`/`IU2`/`TQO`；产物 `artifacts/lane-spawn/` |
| **前序** | [`dota-lane-creep-trajectory.md`](./dota-lane-creep-trajectory.md)；摘录 `artifacts/dota-web-gameplay/war3map.j-creep-spawn-excerpt.txt` |
| **产物** | [`../artifacts/lane-spawn/DotaLaneWaypoints.h`](../artifacts/lane-spawn/DotaLaneWaypoints.h)、`spawn-rects.json`、`wave-composition.json`、`dump_rects.py` |
| **配套思维导图** | [`dota-lane-spawn-waypoints-mindmap.md`](./dota-lane-spawn-waypoints-mindmap.md) |

---

## 一、核心结论

| 问题 | 结论 |
| :--- | :--- |
| 出兵点是什么 | 每路 **两个 rect 中心**：近战 `GetRectCenter(…)`、远程/攻城另一 rect。不是兵营建筑中点。 |
| 近卫上路偏差 | `kAiLanes` 用兵营中点 **(-6368,-4480)**；真实近战 **B4 中心 (-6160,-4064)**、远程 **R3 (-6192,-4304)** — 与实测一致。 |
| 路点链 | 脚本层几乎是 **一跳**：`attack` → `O2[lane]`（对侧标记建筑）；进己方出兵/handoff rect 只是 **重发同一目标**；靠近对侧 `BZ/ZZ/DZ`（300）时 `CL2` 改 `O2[5/1]` 打基地。卡兵投影应用 **spawn→handoff→T2→T1→O2** 几何折线。 |
| 号角 vs 第一波 | 号角：倒计时 **&lt;12s**；第一波：**倒计时 = 0（GameStart）** 立刻 `TriggerExecute(ZG)`。间隔约 **12s**。 |
| 号角前开 block | 主要因 **门口坐标错 + along&lt;150 判定** 漏认；叠加若在 GameStart 前把非兵线 `CreateUnit` 算进波次时钟会更糟。读图阶段 **无持久** `esen/ugho` 预放（仅 `RemoveUnit(CreateUnit…)` 预载模型）。 |
| 4 只 vs 5 只 | 默认 **3 近战 + 1 远程 = 4**；每第 **7** 波加 **1 攻城 = 5**。 |

---

## 二、出兵点（六路）

`SPO`（`war3map_3.j`）对 `BO[0]` / `CO[0]` 调用 `CreateNUnitsAtLoc`；Location 在 `war3map_9.j` ≈ L11588 由 `GetRectCenter` 赋值。

### 2.1 对照表

| 路 | 近战 rect → loc | 中心 (x,y) | 远程/攻城 rect → loc | 中心 (x,y) | SSO 等级 → O2 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 近卫上 | `B4` → `B1` | **-6160, -4064** | `R3` → `E1` | **-6192, -4304** | 2 → `CI` |
| 近卫中 | `C4` → `O1` | -4752, -5344 | `P3` → `C1` | -4832, -5648 | 3 → `BI` |
| 近卫下 | `A4` → `A1` | -3536, -6784 | `T3` → `D1` | -4096, -6720 | 4 → `DI` |
| 天灾上 | `N3` → `RI` | 2528, 5504 | `I4` → `I1` | 2896, 5520 | 2 → `CI` |
| 天灾中 | `M3` → `TI` | 3744, 3728 | `U3` → `QI` | 4240, 3904 | 3 → `BI` |
| 天灾下 | `L3` → `PI` | 6288, 3264 | `Q3` → `UI` | 6176, 3600 | 4 → `DI` |

Rect 范围见 `artifacts/lane-spawn/spawn-rects.json`（由 `Rect(minX,minY,maxX,maxY)` 字面量）。

### 2.2 单位类型

| 阵营 | 近战 | 远程 | 攻城 | 超级（对应兵营倒） |
| :--- | :--- | :--- | :--- | :--- |
| 近卫 | `esen` / `e00V` | `edry` / `e00W` | `ebal` / `e026` | 标志 `JI/KI/LI`、`WI/XI/YI` |
| 天灾 | `ugho` / `u001` | `unec` / `u002` | `umtw` / `u00R` | `HI/ZI/VI`、`EI/FI/GI` |

同一波内：先近战 `NI` 只，再远程 `SI` 只，攻城波再在 **远程同一 Location** 刷 `SI` 辆车（代码里攻城也用 `CreateNUnitsAtLoc(SI, …)`，`SI` 初始为 1）。

### 2.3 与 `kAiLanes` 的差

近卫上路兵营建筑：近战 `JV` (-6080,-4480)、远程 `KV` (-6656,-4480)，中点 ≈ **(-6368,-4480)** — 正是手写表「兵营」点。真实刷兵在门口前侧 rect，沿车道已离开该中点约 **400+**，因此「门口 900 内且 along &lt; 150」极易漏判。

---

## 三、路点链

### 3.1 脚本真实逻辑（不是密集导航网格）

```text
CreateNUnitsAtLoc → SSO(group, 2|3|4)  // 只设 I2 等级，不下令
EnterRegion(出兵 rect ∪ handoff rect) → S8O/S3O/… → IssuePointOrderLoc("attack", O2[lane])
UnitInRange(BZ|ZZ|DZ, 300) → CL2：Radiant 设 level=5 打 U0；Dire 设 level=1 打 II
同建筑 300 另有 NUO：直接 attack U0 / II
```

`O2[]`（`war3map_9.j` L11577–L11587）：

| 下标 | 变量 | 建筑 | 坐标 |
| :--- | :--- | :--- | :--- |
| 1 | `II` | `CZ` | -5467.9, -5891.1 |
| 2 | `CI` | `BZ` | -6005.1, 5458.6 |
| 3 | `BI` | `ZZ` | -561.7, -651.7 |
| 4 | `DI` | `DZ` | 5901.5, -6198.9 |
| 5 | `U0` | `OZ` | 4901.8, 4536.6 |

进区触发注册：`war3map_9.j` L16181–L16256。

| 阵营+路 | 进区 rect | 动作 |
| :--- | :--- | :--- |
| 近卫上 | `B4`,`R3`,`TA` | `S8O` → attack `CI` |
| 近卫中 | `C4`,`P3`,`SA` | `S3O` → attack `BI` |
| 近卫下 | `T3`,`A4`,`NA` | `SCO` → attack `DI` |
| 天灾上 | `I4`,`N3`,`LA` | `SAO` → attack `CI` |
| 天灾中 | `U3`,`M3`,`KA` | `S6O` → attack `BI` |
| 天灾下 | `Q3`,`L3`,`MA` | `SEO` → attack `DI` |

出兵点落在进区 rect 内：创建时触发进区 → **首道 attack 令**（1.26/1.27 上 DotA 依赖此行为）。

### 3.2 卡兵用几何折线（头文件）

引擎沿地形走廊走，弯道会横向漂；应用建筑/handoff 做折线投影：

`spawn(melee) → handoff → (T2) → T1 → O2[lane] → ancient`

己方一塔在链上的下标见 `kDotaLanes[i].t1Index`（边路多为 3，中路多为 2）。

| 路 | 己方 T1 |
| :--- | :--- |
| 近卫上 | (-6112, 1568) `HV`/`e00S` |
| 近卫中 | (-1504, -1824) `GV` |
| 近卫下 | (4960, -6752) `EV` |
| 天灾上 | (-4704, 5920) `GZ`/`u00M` |
| 天灾中 | (1056, -96) `MX` |
| 天灾下 | (6240, -2080) `YZ` |

完整数组：`artifacts/lane-spawn/DotaLaneWaypoints.h`。

---

## 四、出兵时序

### 4.1 号角与第一波（`IU2`，`war3map_3.j` ≈ L6815）

| 事件 | 条件 | 行为 |
| :--- | :--- | :--- |
| 号角 | `TimerGetRemaining(OL) < 12` 且首次 | `PlaySoundBJ(OE)`，`DL=true` |
| GameStart / 第一波 | `remaining == 0` | `FL1("GameStart")`；`TriggerRegisterTimerEventPeriodic(ZG,30)`；**立刻** `TriggerExecute(ZG)` → `SPO` |

→ 第一波相对号角：**约 +12 秒**（倒计时从 12→0）。

### 4.2 间隔与波内顺序

- 之后每 **30s** 一次 `SPO`。
- 同一 `SPO` 内顺序：天灾三路近战 → 天灾远程 →（攻城波）天灾车 → 近卫近战 → 近卫远程 →（攻城）近卫车。
- **无** `TriggerSleep` / 定时器隔开近战与远程；同触发器同帧连续 `CreateNUnitsAtLoc`。实测坐标差来自 pathing 散开，不是脚本毫秒表。

### 4.3 攻城车

`SQO = ModuloInteger(GetTriggerExecCount(ZG), 7) == 0`  
→ 第 **7, 14, 21…** 波（`execCount` 从 1 起，第 7 次执行时为真）。游戏时间约 **3:00, 6:30, …**（从 GameStart 起）。

### 4.4 数量成长

| 游戏内时间（`M` 计时，GameStart 起） | 效果 |
| :--- | :--- |
| 0 | `NI=3`, `SI=1` |
| 999s | `NI+=1`（`HG`→`SOO`） |
| 1999s | `NI+=1` |
| 2699s | `SI+=1`（`GG`→`SIO`） |
| 2999s | `NI+=1` |

### 4.5 血量/攻击升级

`TriggerRegisterTimerEventPeriodic(UG, 450)` → `TQO`：对 `BO[0]`/`CO[0]` `SetPlayerTechResearchedSwap` 升 `R007/R008/R00C/R00D/…`。网页近似：**每 450s** 近战 +10HP/+1 攻、远程 +10HP/+2 攻（详见 [`dota-6.83d-web-gameplay-data-reverse.md`](./dota-6.83d-web-gameplay-data-reverse.md) §6）。

### 4.6 超级兵

对应路兵营死亡把该路 flag 置 `false`；`SPO` 改刷超级 FourCC（上表）。整路兵营都倒才会全面超级（按路独立）。

### 4.7 读图 / 号角前是否预放兵线单位

| 行为 | 是否持久兵线 |
| :--- | :--- |
| 地图初始化 `CreateUnit` 塔/兵营/商店 | 建筑，不是 `esen/ugho` |
| `RemoveUnit(CreateUnitAtLoc(DO, u001, …))`（多处，含 L16136+） | **否**：立刻删，仅模型预载 |
| `SPO` 首次 | **是**：GameStart 时才刷真正兵线 |

结论：号角前 **不应** 有存活的 lane creep；卡兵不应在 GameStart 前把任意 `CreateUnit` 当第一波。

---

## 五、每波组成（评分用）

| 波次（exec） | 游戏秒 | 近战 | 远程 | 攻城 | 合计/路 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 1–6 | 0–150 | 3 | 1 | 0 | **4** |
| 7 | 180 | 3 | 1 | 1 | **5** |
| 8–13 | … | 3 | 1 | 0 | 4 |
| 14 | 390 | 3 | 1 | 1 | 5 |
| ≥34（过 999s） | ≥990 | 4 | 1 | 0/1 | 5–6 |
| 过 2699s | ≥2699 | 5* | 2 | 0/1 | 7–8 |

\*1999s 后再 +1 近战。漏兵比例分母用上表；实测 4/5 交替与攻城波一致。

前 **7 分钟** `SZO`/`SVO` 给部分路加加速/减速，相遇点偏移，不影响出兵数量。

---

## 六、对卡兵 AI 的建议（不改 hooker，仅设计）

### 6.1 `aiLaneProj` 改折线投影

对 `kDotaLanes[lane].waypoints[0..t1Index]`（卡兵通常只关心到己方一塔）：

1. 预计算折线累计弧长 `s[i]`。
2. 点 `P` 投影到每段线段，取距离最小的段；`along = s[i] + t*segLen`，`side = 有符号横向`。
3. 弯道处横向不再相对「兵营→一塔」直线虚高（上路 9s 内 -16→+139 的问题会收敛到走廊坐标）。

门口原点用 **melee spawn**（或 `waitSpot`），不要用兵营建筑中点。

### 6.2 推荐等兵位

头文件 `waitSpot`：自 melee 中心沿折线向 T1 约 **+350**（与现边路 `spawnProj+350` 经验一致）。

| 路 | 推荐等兵 (x,y) 约 |
| :--- | :--- |
| 近卫上 | -6140, -3710（近 `TA`） |
| 近卫中 | -4550, -5080 |
| 近卫下 | -3180, -6775（近 `NA`） |
| 天灾上 | 2400, 5750 |
| 天灾中 | 3850, 3480 |
| 天灾下 | 6320, 2910 |

边路仍可用用户 `-mark position` 覆盖。

### 6.3 问题 3（号角前开 block 认不到波）

**主因（高置信）**：认波条件「默认门口 = `kAiLanes.rax + 80*dir`，且 `along < 150`」。近卫上路真实刷点相对该 rax 的 along ≈ **420** → 永远不满足；号角后再开若换了路/或偶然学到 home，会「看起来正常」。

**次因**：第一波在 **GameStart** 而非号角；若波次时钟在读图阶段被预载 `CreateUnit` 污染，`g_aiLastWaveTick` 与真实 30s 错位，450ms 窗口也对不齐。

**修法（建议，未改代码）**：

1. 门口/找兵原点改为 `DotaLaneWaypoints` 的 **melee spawn**（或 ranged 与 melee 的中点）。
2. `along < 150` 放宽到 **&lt; 500**，或改为「在 spawn rect 扩张 200 内」。
3. 仅当 `type ∈ {esen,edry,ebal,ugho,unec,umtw,…}` 且 **GameStart 之后** 才推进 `g_aiFirstWaveTick`。
4. `-block start` 若在 GameStart 前调用：排队到第一波 CreateUnit 再 `handledWave` 复位。

---

## 七、引擎 / RVA

本主题纯地图脚本，**不依赖** `game.dll` 新偏移。若以后要钩「单位创建」核对预载：沿用现有 1.27 CreateUnit 钩即可；不必为路点再挖 RVA。

---

## 八、产物清单

| 路径 | 内容 |
| :--- | :--- |
| `analyses/dota-lane-spawn-waypoints.md` | 本文 |
| `analyses/dota-lane-spawn-waypoints-mindmap.md` | 导图 |
| `artifacts/lane-spawn/DotaLaneWaypoints.h` | 六路数据头文件 |
| `artifacts/lane-spawn/spawn-rects.json` | rect / O2 / T1 |
| `artifacts/lane-spawn/wave-composition.json` | 波次组成与时序 |
| `artifacts/lane-spawn/dump_rects.py` | 从 `war3map_9.j` 重算 rect 中心 |

**未改** `War3Launcher` / `hooker`。
