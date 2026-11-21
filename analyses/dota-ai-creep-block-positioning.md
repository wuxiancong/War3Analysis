# 卡兵时 AI 如何知道每个小兵 / 攻城车 / 英雄的位置

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Claude Opus 5.5 |
| **分析目的** | 汇总卡兵（`tactic run block`）用到的单位定位链路：单位从哪来、坐标怎么读、怎么分波、怎么换算成「沿车道前进 / 横向」，以及日志里每个数字的含义 |
| **命名方式** | `dota-ai-creep-block-positioning`（短横线英文） |
| **分析时间** | 2026-11-20 |
| **代码** | `War3Launcher/hooker/war3hook_ai.cpp`（单位登记、原生查询）、`war3hook_ai_tactics.inl`（车道、卡兵、评分） |
| **前序文档** | [`dota-lane-creep-trajectory.md`](./dota-lane-creep-trajectory.md)（脚本出兵 / 路点，结论：不必逆向 game.dll）、[`dota-ai-neutral-creep-pull.md`](./dota-ai-neutral-creep-pull.md)（单位查询接口表）、[`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md)（卡兵各版本实测） |

## 一、一句话

**没有读游戏内存里的坐标表，全部走 JASS 原生函数**：hook 截获地图脚本的 `CreateUnit` 拿到每个单位的句柄 → 每个控制周期对句柄调用 `GetUnitX / GetUnitY`（以及血量、归属）→ 按「兵营 → 一塔」车道轴换算成（前进, 横向）。攻城车和普通小兵走同一条链路。

## 二、单位从哪来（登记）

| 步骤 | 做法 | 代码 |
| :--- | :--- | :--- |
| 截获创建 | 地图脚本出兵用 `CreateUnit` / `CreateUnitAtLoc`；hook 在原生返回后拿到 `(handle, typeId)` | `aiOnUnitCreated`（war3hook_ai.cpp） |
| 登记 | 存进 `g_aiUnits[handle]`（句柄、类型、agent 指针 `aiFindAgentInRing`）；超过 6000 个整体重建 | `aiOnUnitCreated` |
| 兵线单位类型 | 近卫 `esen` 近战 / `edry` 远程 / `ebal` **攻城车**；天灾 `ugho` / `unec` / `umtw` **攻城车** | `aiIsLaneCreepType`、`aiLaneCreepTeam` |
| 波次时钟 | 见到兵线单位创建（距上一波 > 10 s）记为新一波，按 30 s 整倍数校准 | `g_aiWaveCount` / `g_aiLastWaveTick` |
| 归属 | **不在创建回调里查**：读图阶段在回调里调 `GetOwningPlayer` 会破坏 VM 状态（`game.dll+0x2bd982` 崩溃）；放到 `aiTick` 定时器里补查 | `aiProcessCreatedUnits` |

## 三、坐标 / 血量怎么读

- **只在游戏线程读**：所有原生调用都在 `aiTick`（WndProc 定时器）里，且 `g_sceneState == GamePlaying` 才执行。
- **坐标**：`aiQueryPosition(handle)` = 原生 `GetUnitX` + `GetUnitY`（按名字解析一次、缓存地址，`aiNativeReal1`）。英雄同理：`aiLocalHeroHandle()`（本地玩家槽位的英雄句柄）。
- **血量 / 存活**：`aiRefreshUnit` 读 `GetWidgetLife`（> 0.405 算活着），死亡 3 s 后移出跟踪（句柄会被回收给别的对象）。
- **周边单位**：`aiCollectNearby(x, y, 半径)` 遍历 `g_aiUnits`，逐个读坐标算距离；`aiBuildCtx` 再按归属分成 `allyCreeps / enemyCreeps / neutrals（玩家 12）/ 英雄 / 建筑`。
- **频率**：卡兵闭环约 **85 ms 一次**（11~12 Hz，对数正态抖动 60~120 ms），日志轨迹 `📍` 约 0.3 s 一行。

## 四、怎么分「这一波」

新一波出兵 0.45 s 后：在门口附近 900 内、沿车道还没走出门口 150 的己方兵里取离门口最近的当**领头兵**；领头兵 900 内的己方兵（最多 12 只，含攻城车）记为本波成员（`AiBlockMeasure.creeps` / `AiWaveScore.creeps`）。之后卡兵和评分**只看本波成员**（`aiBlockCreepInWave`），上一波、下一波的兵不会混进来。

## 五、车道坐标（前进 / 横向）

- **各路几何**：`kAiLanes[6]`（近卫上 / 中 / 下、天灾上 / 中 / 下）= 兵营中点 + 己方一塔坐标，来自 `War3Angular/public/assets/maps/dota683/buildings.json`。
- **门口**：第一波领头兵位置沿车道前推 180（离「兵营 + 80」超过 400 就用默认值）。
- **换算**：`aiLaneProj(单位坐标)` → `前进`（沿车道离门口多远）+ `横向`（垂直车道，左负右正）；`aiLanePoint` 反算回世界坐标给英雄下移动指令。
- **学到的兵线折线**：基线波（不卡）记录整波兵中心每 100 一点，存 `lane_paths.txt`。**2026-11-20 起只给真正弯的路用**（偏离直线 ≥ 250，即近卫上路）；近卫下路偏离只有 173，用折线反而更差（平均 76 → 56），照旧用直线。
- **边路起手位置**：用户 `-mark position` 标的点（离车道 500 内、在兵营和一塔之间、离兵营最近的那个），本机 `position_marks.txt`：P1 近卫下路 (-1016, -6942)、P2 近卫上路 (-6186, -1939)。

## 六、卡兵时怎么用这些坐标

1. 每只本波兵：本次和上次采样的（前进, 横向）差 / 时间 = 速度；预测 **0.25 s 后**的位置。
2. 「目标兵」= 还没超过英雄（前进 ≤ 英雄 + 20）的兵里预测最靠前的那只；离它 70 内的算「前排」。
3. 横向对准：中路对准前排中点 / 挡兵多的那撮；边路用整波中位，**前排优先**（前排 ≥ 2 只且宽 ≤ 110 → 前排中点；前排 1 只离中位 > 40 且离英雄 < 150 → 直接对准它）。
4. 前进：保持在目标兵前方一定距离，不够就往前走，太远就站住；一直卡到最前兵到一塔前 250。

## 七、日志字段

| 日志 | 含义 |
| :--- | :--- |
| `📍 AI轨迹 第 N 波 t=… 前沿进度 X | 英雄比前沿 前 A 横 B` | 最前兵沿车道走了 X；英雄在它前方 A（负 = 已被超过）、横向差 B |
| `🎯 卡兵 第 N 波 车道 X | 前距 G | 英雄横 a → 目标横 b（最前兵 c，一排 k 只 lo~hi 宽 w）` | 每次控制的决策：英雄横向 a 要去 b |
| `🚨 漏兵 第 N 波 t=…：兵 H 车道 X 横 L | 英雄 车道 X' 横 L'` | 某只兵超过英雄的那一刻 |
| `🏁 AI 卡兵评分 第 N 波：… 漏兵 k/n → 得分 S` | 卡到一塔时：100 × 没漏的兵 / 本波兵数 |
