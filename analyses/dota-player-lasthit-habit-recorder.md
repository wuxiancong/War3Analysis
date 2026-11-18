# DotA 玩家补刀（正补/反补）习惯记录与真人模仿 — 实现方案

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 说明现有 AI 补刀为何偏机械；设计「记录真人补刀微操 → 按账号加载画像 → 模仿」的落地方案；落盘约定对齐加点习惯记录器 |
| **命名方式** | `dota-player-lasthit-habit-recorder`；配套 `*-mindmap.md` |
| **分析时间** | 2026-11-16 |
| **状态** | **方案（未编码画像层）**；2026-11-16 例程已升级为通用真人模型 `AiHumanProfile`（反应时间/漏刀/成串 S/APM/抖动），参数与第 6.2 节画像字段一一对应，见 [`dota-ai-human-lasthit-learn-cast.md`](./dota-ai-human-lasthit-learn-cast.md) |
| **机制依据** | [`warcraft-iii-ai-unit-attack-lasthit-deny.md`](./warcraft-iii-ai-unit-attack-lasthit-deny.md)、[`dota-player-learn-habit-recorder.md`](./dota-player-learn-habit-recorder.md) |
| **代码现状** | `War3Launcher/hooker/war3hook_ai.cpp`（`AiLastHitRoutine` / `humanmode` / S-Cancel·Strafe·Hybrid） |
| **数据源** | `War3Bot` `data/player_actions/<player>/match_*.dat`；可选 hook 增强采样 |
| **配套思维导图** | [`dota-player-lasthit-habit-recorder-mindmap.md`](./dota-player-lasthit-habit-recorder-mindmap.md) |
| **相关（卡兵）** | [`dota-player-block-habit-recorder.md`](./dota-player-block-habit-recorder.md)（同级 `data/block_habits/`） |

---

## 一、直接回答你的问题

| 问题 | 答案 |
| :--- | :--- |
| 现在补刀不像真人？ | **是。** 现实现是规则机：掉血预测出手 + 高频 `stop(S)` 压刀 + 三种「真人模式」**随机轮换**（`g_aiRandomHumanMode`），参数全局一套，**不是某个账号的习惯**。 |
| 能不能直接实现「真人补刀」？ | **不能一次做成像你本人。** 可先继续用现有例程当底座，再叠加 **从你对局学到的时序/节律参数** 才会像「你」。 |
| 要不要记录真人历史补刀？ | **要。** 模仿必须以真实 Action 节律为教师信号；仅靠调 `damage/windup` 无法消除机械感。 |
| 你开几局专门补刀是否有用？ | **非常有用。** Host 进房即可；`match_*.dat` 已含 stop/攻击/走位；建议再开「教师增强采样」补小兵血量等（见第五节）。 |
| 登录后是否按账号找习惯？ | **要。** 键：`账号/玩家名`（+ 可选英雄/近远程）；进局 AiControl 加载对应 profile。 |
| 是否也落到 `data` 下？ | **要。** 与加点习惯同级目录约定（见第六节）。 |

---

## 二、现状：为何机械

现有 `-lasthit` / `-deny`（`war3hook_ai.cpp`）：

1. **决策**：范围内选「预测落地血 ≤ damage」的小兵 → 发攻击 `0x12`+`0xD000F`。  
2. **等待**：未到出手窗口时，用 **55ms 级 `0x10`+stop**、短 A→S 假动作、左右挪位等伪装。  
3. **模式**：`S-Cancel` / `Strafe` / `Hybrid` 约每 2.8s **随机切换**，与玩家无关。  
4. **成功确认**：地图正补/反补计数或金钱跳涨。

机械感来源：

- 节律过齐（固定 55ms/85ms），真人停顿、漏刀、偶尔提前 A 都有噪声；  
- 无「站位偏好 / 仇恨距离 / 囤刀 vs 抢刀」的个人参数；  
- 正补优先写死，与你个人正反补比例可能不符；  
- 看不到「你」在出手瞬间的血量阈值习惯（包里没有 HP，只有动作）。

**不必新挖 game.dll**：补刀仍是 Action 时序策略；缺的是 **习惯画像**，不是新 Order。

---

## 三、真人补刀习惯记什么

补刀 ≠ 加点（稀疏 FourCC 序列）。要记的是 **微操时序特征** + **结果标签**。

### 3.1 可从 `match_*.dat` 直接抽（MVP，全员可用）

| 特征 | 信号 | 习惯含义 |
| :--- | :--- | :--- |
| Stop 密度 | `0x10` + `0xD0004` 的间隔分布 | S 卡刀频率 |
| 攻击脉冲 | `0x12`/`0x11` + `0xD000F`（及 smart `0xD0003`）相对 stop 的前后关系 | A→S 假动作、出手节奏 |
| 走位抖动 | 短距 `move`/`0x12` 点地在攻击间隙的幅度与周期 | 是否喜欢左右晃 |
| 成功正/反补时刻 | `0x6B`：`CSK*` / `CSD*` 跳变；终局 `OJ2` | 标签：这次微操是否打出刀 |
| 刀间间隔 | 相邻 CSK/CSD +1 的时间差 | 对线节奏、漏刀率代理 |
| 正反补比 | 局内 CSK vs CSD | 反补意愿 |
| 相对开局分钟 | `t` / 游戏钟 | 前期 vs 中期风格 |

### 3.2 建议教师局增强（你主动开几局时打开）

仅 Bot 动作流 **看不到出手时小兵当前血量**。教师增强在 **war3hook 本机** 旁路采样（不替代 `.dat`）：

| 增强字段 | 来源 | 用途 |
| :--- | :--- | :--- |
| 目标 `life/maxLife` 在攻击发出时 | 只读 JASS（已有 AI 查询） | 个人「出手血量阈值」 |
| 目标距离 / 是否在攻击距离内 | 同上 | 站位习惯 |
| 英雄攻击间隔/弹道（可配置表） | 英雄静态表 | 校准 windup |
| 本地是否正补成功 | `g_lastLastHitsValue` 边沿 | 与动作对齐 |

教师局产出「富事件」；普通排位局仍可用 MVP 特征更新节律统计。

### 3.3 不记（MVP）

- 像素级鼠标轨迹（无、且 Action 层已够驱动 AI）；  
- 完整每一帧所有小兵血量录像（体积大）；  
- 野怪补刀（可二期，`NK` 另案）。

---

## 四、总体架构

```text
【教师 / 正常对局】
  玩家补刀微操
        │
        ├─ W3GS Action → War3Bot recordPlayerAction → match_*.dat
        │
        └─（可选）hook LastHitTeacherSampler → 富事件缓冲
        │
        ▼
 LastHitHabitExtractor
   单局 farmEvents / 节律统计 → 旁车 JSON
        │
        ▼
 LastHitHabitAggregator
   按 账号(+英雄/近远程) 聚合 → profile
        │
        ▼
 data/lasthit_habits/<player>/...
        │
【之后 AI 进局】
  登录账号已知 → 加载 profile
        │
        ▼
 AiLastHitRoutine 参数化
   stopInterval / feintMs / strafe / commitHpRatio /
   denyBias / noise / modeWeights
   （不再纯随机三种模式）
```

登录键：

- 主键：`playerName`（与 `data/player_actions/<name>/`、记住密码账号一致）。  
- 次键（推荐）：`heroCode` 或 `attackType=melee|ranged`（近远程节律差大）。  
- 若无专属画像：回退到「全局默认真人模式」或「同攻击类型的公共均值」。

---

## 五、你需要开几局时怎么做（采集规程）

1. **用要模仿的账号**登录，走 Host/Bot 正常开局（保证 `match_*.dat` 写入该玩家目录）。  
2. 尽量对线补刀 8–15 分钟以上；正补、反补都做一些。  
3. （推荐）开启教师采样：如 RemoteControl `farmrec on` 或 ini `[AiControl] RecordLastHitTeacher=true`，本机 hook 写增强日志。  
4. 打 3～5 局同英雄或同攻击类型即可做出第一版 profile；后续局增量更新。  
5. 验收：旁车里能看到 stop 间隔直方图、CSK 边沿对齐的出手簇；画像 `samples≥3`。

不必为采集改地图；**不要**用 AI `-lasthit` 打教师局（会污染成「自己学自己」）。

---

## 六、落盘约定（与加点习惯对齐）

统一放在 Bot/`data` 树下（工作目录或程序目录，与 `player_actions` 相同解析规则）：

```text
data/
  player_actions/<player>/match_*.dat          # 已有：原始动作
  player_actions/<player>/learn_*.json         # 加点单局（另案）
  player_actions/<player>/farm_*.json          # 本方案：单局补刀抽取
  learn_habits/<player>/<heroCode>.json        # 加点跨局画像（另案）
  lasthit_habits/<player>/_global.json         # 本方案：账号级补刀画像
  lasthit_habits/<player>/<heroCode>.json      # 可选：分英雄
  lasthit_habits/<player>/melee.json           # 可选：近战聚合
  lasthit_habits/<player>/ranged.json          # 可选：远程聚合
  lasthit_habits/<player>/teacher_*.jsonl      # 可选：教师富事件
```

原则：

- **原始真相**仍是 `match_*.dat`；`farm_*.json` / profile 可重建。  
- 不把习惯写进 `game.dll` 或地图。  
- 账号目录名与 `player_actions` 安全用户名规则一致（非法字符替换）。

### 6.1 单局 `farm_*.json`（草案）

```json
{
  "schema": 1,
  "matchId": "...",
  "player": "wuxiancong",
  "heroCode": "Nbbc",
  "attackType": "melee",
  "durationMs": 1200000,
  "lastHits": 42,
  "denies": 5,
  "rhythm": {
    "medianStopIntervalMs": 62,
    "p90StopIntervalMs": 180,
    "medianAttackToStopMs": 90,
    "shortMoveAmp": 95,
    "medianGapBetweenLhMs": 14000
  },
  "commitClusters": [
    {
      "t": 185000,
      "kind": "lasthit",
      "preStops": 8,
      "hadFeint": true,
      "preMoveJitter": true
    }
  ]
}
```

`commitClusters`：在 CSK/CSD +1 前 0.3–1.2s 窗口内的 stop/攻击/短移簇，用于学「出手前微操形态」。

### 6.2 跨局 profile（草案）

```json
{
  "schema": 1,
  "player": "wuxiancong",
  "scope": "melee",
  "samples": 5,
  "updatedAt": "...",
  "params": {
    "stopIntervalMs": 60,
    "stopJitterMs": 25,
    "feintWindupMs": 85,
    "feintRate": 0.35,
    "strafePeriodMs": 400,
    "strafeAmp": 100,
    "modeWeights": { "sCancel": 0.4, "strafe": 0.25, "hybrid": 0.35 },
    "denyBias": 0.2,
    "commitHpRatioMean": 0.22,
    "commitHpRatioStd": 0.05,
    "noiseMissRate": 0.03
  },
  "confidence": 0.65,
  "recentMatchIds": []
}
```

无教师 HP 时：`commitHpRatio*` 用默认或留空，例程仍用 `damage` 预测；有教师数据后再收紧。

---

## 七、模仿时怎么用画像（改造现有例程）

不重写整套补刀状态机，只 **参数化** `AiLastHitRoutine` / `aiTickRoutine`：

| 现常量/行为 | 改为来自 profile |
| :--- | :--- |
| `lastStopTick` 间隔 55ms | `stopIntervalMs ± stopJitterMs` |
| 假动作 85ms | `feintWindupMs`；以 `feintRate` 概率触发 |
| 2.8s 随机切模式 | 按 `modeWeights` 采样，或锁定主模式 |
| 走位 100/85 | `strafeAmp` / `strafePeriodMs` |
| `bothSides` 正补优先 | 用 `denyBias` 调节反补候选权重 |
| 预测 `damage` | 可保留；有 `commitHpRatio` 时改为「预测血量/最大血 ≤ ratio」辅助 |
| 完美每刀必打 | `noiseMissRate` 故意偶尔放过（更像人） |

加载时机：AiControl 确认本局账号 / 英雄就绪后 `loadLastHitHabit(player, hero)` → 写入例程；无文件则保持当前默认真人模式。

---

## 八、实现步骤（编码勾选）

1. **文档与目录**（本文）— 已完成方案。  
2. **Extractor**：从 `match_*.dat` 抽 `farm_*.json`（局末或首次解析时）。  
3. **Aggregator**：生成/更新 `data/lasthit_habits/<player>/...`。  
4. **Loader**：Launcher/DLL 读 profile → 填例程参数；日志打印 `loaded habit samples=N confidence=`。  
5. **Teacher sampler（可选）**：`farmrec on` + `teacher_*.jsonl`（含 life）。  
6. **验收**：你打 3 局教师局 → 画像非空 → 开 AI lasthit，对比 stop 间隔直方图与教师局接近；体感不再「节拍器」。  
7. **与加点习惯并列**：同一 `data/` 树；API 命名 `LearnHabit*` / `LastHitHabit*` 分开。

---

## 九、与加点习惯方案对照

| 项 | 加点 `learn` | 补刀 lasthit |
| :--- | :--- | :--- |
| 事件密度 | 稀疏 | 极密 |
| 包特征 | FourCC | stop / attack / 短移 + CSK/CSD |
| 是否要英雄映射 | 槽位需要 | 近远程/攻速更重要 |
| 单局旁车 | `learn_*.json` | `farm_*.json` |
| 跨局画像 | `learn_habits/` | `lasthit_habits/` |
| AI 消费 | `learn <slot>` | 参数化现有 lasthit 例程 |
| 教师增强 | 一般不需要 | **强烈建议**（血量） |

---

## 十、风险

| 风险 | 对策 |
| :--- | :--- |
| 把 AI 自己的 lasthit 局写进画像 | 教师采集禁止开 AI 补刀；或标记 `source=human\|ai` 过滤 |
| 仅 stop 密度像人但出手时机仍机械 | 上教师 HP；或加 `noiseMissRate` / 延迟噪声 |
| 账号改名对不上目录 | 以登录名/clientId 稳定键；改名时拷贝 profile |
| `.dat` 无 HP | MVP 先节律；教师局补齐 commit 血量分布 |
| 体积 | 旁车只存统计+簇摘要，不存每帧单位快照 |

---

## 十一、总结

- **现在**：有「像人一点」的规则补刀，但不是「像某个账号」。  
- **要真人模仿**：必须 **记录历史补刀微操**（你开几局最有效），按 **登录账号** 加载，**落在 `data/lasthit_habits/`**（单局旁车 `farm_*.json`），与加点习惯同级。  
- **实现路径**：复用 `match_*.dat` + 可选 hook 教师采样 → 聚合参数 → 注入现有 `AiLastHitRoutine`；**不必新逆向 game.dll**。

---

## 十二、参考锚点

- 现例程：`war3hook_ai.cpp` `AiLastHitRoutine` / `aiTickRoutine` / `humanmode`  
- 命令说明：`warcraft-iii-ai-unit-attack-lasthit-deny.md`  
- 动作归档：`Client::recordPlayerAction` / `savePlayerMatchLog`  
- 正反补同步：`Data:CSK*` / `Data:CSD*`（`client.cpp` / `matchstatsprovider.cpp`）  
- 加点对照：`dota-player-learn-habit-recorder.md`
