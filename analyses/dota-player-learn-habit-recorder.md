# DotA 玩家加点习惯记录器 — 实现方案

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 设计可落地的「玩家加点习惯」记录与聚合方案，供后续 AI `learn` 模仿/推荐；复用已有动作归档与学习识别，避免重复挖 dll |
| **命名方式** | `dota-player-learn-habit-recorder`；配套 `*-mindmap.md` |
| **分析时间** | 2026-11-16 |
| **状态** | **方案（未编码）** |
| **机制依据** | [`dota-hero-skill-point-learn-flow.md`](./dota-hero-skill-point-learn-flow.md)、[`dota-ai-skill-command-implementation.md`](./dota-ai-skill-command-implementation.md) |
| **数据源** | `War3Bot` `data/player_actions/<player>/match_*.dat`；解析逻辑对标 `matchstatsprovider.cpp` |
| **配套思维导图** | [`dota-player-learn-habit-recorder-mindmap.md`](./dota-player-learn-habit-recorder-mindmap.md) |
| **相关** | 补刀 [`dota-player-lasthit-habit-recorder.md`](./dota-player-lasthit-habit-recorder.md)；卡兵 [`dota-player-block-habit-recorder.md`](./dota-player-block-habit-recorder.md)（同级 `data/`） |

---

## 一、核心结论

| 问题 | 结论 |
| :--- | :--- |
| 要不要新逆向 `game.dll`？ | **不必。** 加点已在 Action 流中：`0x66`（开菜单）+ `0x10`+技能 FourCC；升级有 `0x6B Data:LevelN=pid`。 |
| 原始数据够不够？ | **够。** Host Bot 已把每名玩家全量动作压进 `match_*.dat`；局内 UI 已能从中还原 `skillTimeline`。 |
| 记录器缺什么？ | 缺的是 **一等公民的「学习序列」抽取 + 跨局聚合画像**，不是再抓一层网包。 |
| 推荐落点 | **War3Bot**（主机可见全员动作）；Launcher/hook 仅作本机调试旁路，不作主库。 |
| 与 AI `learn` 关系 | 画像输出「推荐槽位/FourCC 序列」→ 升级边沿调 `learn`（二期）。 |

---

## 二、要记录的「习惯」是什么

按优先级：

| 维度 | 含义 | 用途 |
| :--- | :--- | :--- |
| **学习序列** | 本局按时间顺序：学了哪些技能/属性（FourCC、槽位、学后等级） | 核心 build order |
| **相对英雄等级** | 每次学习时英雄大约几级（由最近 `Data:Level*` 推断） | 「6 级先大」等习惯 |
| **相对对局时间** | `timeOffsetMs` / 游戏钟 | 前中后期加点节奏 |
| **开菜单延迟** | `0x66` → 随后 `0x10` 学习的间隔 | 是否囤点、手速 |
| **升级后延迟** | `LevelN` → 第一次学习的间隔 | 升级立刻点 vs 囤点 |
| **属性偏好** | `Aamk`/`A0NR` 在序列中的位置与次数 | 后期属性点习惯 |
| **跨局稳定序** | 同玩家+同英雄多局序列的众数/前缀一致性 | AI 默认 build |

不记（MVP）：精确剩余技能点数、经验条百分比、失败的非法加点尝试（引擎拒绝通常无成功包）。

---

## 三、数据从哪来（已有管道）

```text
W3GS_INCOMING_ACTION
        │
        ▼
 Client::recordPlayerAction
   actionId / orderId / extra(0x6B) / timeOffsetMs
        │
        ▼
 savePlayerMatchLog → data/player_actions/<name>/match_*.dat
   format: t,a,x,y,target,ext,order
        │
        ▼
 MatchStatsProvider 离线扫描
   识别 0x10+FourCC →「学习…」
   识别 0x66 → 打开加点菜单
   识别 Data:Level* → 升级
   输出 skillTimeline（UI 已用）
        │
        ▼
 【本方案新增】LearnHabitRecorder
   单局 learnEvents[] → 落盘
   跨局聚合 → habit profile
```

关键识别规则（与现网一致，见 `matchstatsprovider.cpp`）：

| 信号 | 判定 |
| :--- | :--- |
| 学习 | `actionId==0x10` 且 `orderId` 为技能/属性 FourCC（约 `0x41xxxxxx`…），且命中英雄技能表或 `dotaAbilityInfo`；排除买货 `0x6830xxxx`、排除英雄单位码选人 |
| 开菜单 | `actionId==0x66` |
| 升级 | `0x6B` extra ≈ `Data:Level{N}={pid}` 且 value 对应该玩家槽 |

**注意**：学习包 Id 是 **FourCC**；施法是 **OrderId `0xDxxxx`**。记录器只收前者。

---

## 四、推荐架构（两层）

### 层 A — 单局抽取（Match Learn Log）

每场、每名有英雄的玩家写一份轻量 JSON（可与 `.dat` 同目录或子目录）：

路径建议：

```text
data/player_actions/<player>/learn_<yyyyMMdd_hhmmss>_<matchId>.json
```

或局末写入 `.dat` 同级旁车，避免改压缩格式破坏旧工具。

**单局 schema（草案）：**

```json
{
  "schema": 1,
  "matchId": "...",
  "player": "wuxiancong",
  "pid": 1,
  "heroCode": "Nbbc",
  "mapHint": "AP83",
  "durationMs": 2340000,
  "learnEvents": [
    {
      "t": 185000,
      "heroLevel": 2,
      "slot": 1,
      "code": "A05G",
      "name": "剑刃风暴",
      "newLevel": 1,
      "kind": "ability",
      "openedMenu": true,
      "msSinceMenu": 420,
      "msSinceLevel": 3100
    },
    {
      "t": 620000,
      "heroLevel": 6,
      "slot": 4,
      "code": "A0M1",
      "kind": "ultimate",
      "newLevel": 1
    },
    {
      "t": 1800000,
      "heroLevel": 17,
      "slot": 5,
      "code": "Aamk",
      "kind": "attr",
      "newLevel": 3
    }
  ],
  "learnSequence": ["A05G", "A00K", "A05G", "A047", "A05G", "ULT", "..."],
  "slotSequence": [1, 3, 1, 2, 1, 4]
}
```

字段说明：

- `kind`：`ability` / `ultimate` / `attr` / `extra`
- `openedMenu`：该次学习前合理窗口内（如 2s）是否有 `0x66`
- `learnSequence` / `slotSequence`：便于聚合的压缩视图（属性可用 `attr`，大招可用 `ult` 或槽 4）

**生成时机**：`saveAllPlayerMatchLogs` 成功后，或 `MatchStatsProvider` 首次完整解析该 `.dat` 时惰性生成并缓存。

**推荐实现位置**：`War3Bot` 新增 `LearnHabitRecorder`（或挂在 `MatchStatsProvider` / `Client` 局末钩子），**复用**现有学习识别代码，避免两套规则漂移。

### 层 B — 跨局画像（Habit Profile）

路径建议：

```text
data/learn_habits/<player>/<heroCode>.json
```

**画像 schema（草案）：**

```json
{
  "schema": 1,
  "player": "wuxiancong",
  "heroCode": "Nbbc",
  "samples": 12,
  "updatedAt": "2026-11-16T21:30:00",
  "preferredSlotSequence": [1, 3, 1, 2, 1, 4, 2, 3, 1, 2, 4, 3, 2, 3, 5, "..."],
  "sequenceConfidence": 0.72,
  "levelAnchors": {
    "2": { "slot": 1, "freq": 0.91 },
    "6": { "slot": 4, "freq": 0.88 },
    "11": { "slot": 4, "freq": 0.85 },
    "16": { "slot": 4, "freq": 0.80 }
  },
  "attrStyle": {
    "firstAttrAtHeroLevelMedian": 15,
    "attrShareOfLearns": 0.18
  },
  "timing": {
    "medianMsAfterLevelToLearn": 2500,
    "medianMsMenuToLearn": 400,
    "bankPointsRate": 0.15
  },
  "recentMatchIds": ["...", "..."]
}
```

聚合算法（MVP）：

1. 取同 `player+heroCode` 最近 N 局（如 20）的 `slotSequence`。  
2. **前缀对齐**：按英雄等级锚点（2/3/4/5/6/7…）对齐每次「该级花的第一点」众数 → `levelAnchors`。  
3. 全序列用简单 **多数票逐位** 或最长公共前缀得 `preferredSlotSequence`。  
4. `sequenceConfidence` = 与众数序列一致的局数 / samples。  
5. `bankPointsRate`：升级后 >X 秒仍未学习的比例（囤点）。

输出给 AI：`preferredSlotSequence` + 当前已学等级 → 下一个 `learn <slot>`。

---

## 五、与现有模块的边界

| 模块 | 职责 | 本记录器 |
| :--- | :--- | :--- |
| `Client::recordPlayerAction` | 原始动作入库 | **不改协议**；局末可回调抽取 |
| `match_*.dat` | 冷归档 | 只读源；旁车 JSON 不替换它 |
| `MatchStatsProvider.skillTimeline` | UI 时间轴技能格 | **抽取逻辑应同源或抽公共函数** |
| `dota_data.json` | 英雄技能/attrCode | 解析 token、槽位、名称 |
| AI `learn` 命令 | 执行加点 | **消费**画像，本方案不实现注入 |
| war3hook `g_lastHeroLevel` | 本机等级 | 可选旁路；主库仍以 Bot 全员动作为准 |

**不要**在 hook 里为「习惯」单独写一份不兼容格式，除非只做本机调试 dump。

---

## 六、实现步骤（编码勾选）

1. **抽公共解析**  
   - 从 `matchstatsprovider` 抽出 `extractLearnEvents(actions, heroCode, pid) → LearnEventList`（或同文件静态函数）。  
   - 单测：用一份已知 `match_*.dat` 断言序列。

2. **局末旁车**  
   - `savePlayerMatchLog` 后调用抽取 → 写 `learn_*.json`。  
   - 失败不影响 `.dat` 保存。

3. **画像聚合**  
   - 命令/按钮或局末自动：`rebuildLearnHabit(player, heroCode)`。  
   - 写 `data/learn_habits/...`。

4. **只读 API（可选）**  
   - `MatchStatsProvider` / QML：展示「该英雄常用加点」；或 IPC 给 Launcher AI。

5. **（二期）AI 挂钩**  
   - 升级边沿：`learnHabits.nextSlot(hero, currentLevels)` → `learn <slot>`。

6. **验收**  
   - 一局手动 1-3-1-2-1-4，旁车序列一致。  
   - 同英雄三局后画像前缀稳定，confidence > 0。  
   - 属性点 `Aamk` 记为 `kind=attr` / slot 5。

---

## 七、隐私与范围

- 默认只聚合 **本机 Bot 见过的对局**；路径在玩家名目录下。  
- 若上云/天梯：需单独同意与脱敏（本方案默认本地）。  
- 观战位若收不到完整 Action，则该局可不入画像（`samples` 不加）。

---

## 八、风险

| 风险 | 对策 |
| :--- | :--- |
| 学技能与选人/买货 FourCC 误判 | 复用现网白名单：`dotaAbilityInfo` + 英雄技能表；排除 `0x6830` |
| 无英雄码时序列空洞 | 等 `Data` 英雄同步或选人 `0x10` 后再回溯本局学习包 |
| 多形态英雄（变体/德鲁伊 attr `A0NR`） | 用 `attrCode` 表，勿写死 `Aamk` |
| 卡尔等特殊技能 | MVP 可标记 `heroCode=H00U` 降低置信或不入默认序列 |
| 解析规则双份漂移 | **必须**抽公共函数 |

---

## 九、非目标（本阶段）

- 出装习惯记录（可另案，数据源已是同一 `.dat`）。  
- 施法 `cast` 习惯（OrderId 序列，另案）。  
- 实时云端推荐服务。  
- 修改地图脚本强制上报加点（`0x6B` 无「学了什么」专用键；学什么只在 Action `0x10`）。

---

## 十、总结

加点习惯记录器 = **在已有 `match_*.dat` 上做学习事件抽取 + 按玩家/英雄聚合**，不是新网络探针。  
MVP：局末 `learn_*.json` + `learn_habits/<player>/<hero>.json`；逻辑与 `skillTimeline` 同源；供日后 AI **`learn`** 模仿。

---

## 十一、参考锚点

- 动作落盘：`War3Bot/src/client.cpp` `recordPlayerAction` / `savePlayerMatchLog`
- 学习识别与 `skillTimeline`：`matchstatsprovider.cpp`
- 加点协议：`dota-hero-skill-point-learn-flow.md`
- AI 加点命令：`dota-ai-skill-command-implementation.md`（主名 `learn`）
- 升级同步：`0x6B Data:Level*`（同 learn-flow 第六节）
