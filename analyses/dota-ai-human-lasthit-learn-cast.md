# DotA AI 真人化补刀 + 加点 learn + 施法 cast 实现

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Claude Opus 5.5（Claude Code） |
| **分析目的** | 让 AI 补刀节律更像真人；落地加点 `learn` / 自动加点 `autolearn` / 施法 `cast`；补齐施法所需的「技能 → OrderId + 目标类型」表 |
| **命名方式** | `dota-ai-human-lasthit-learn-cast`；配套 `*-mindmap.md`；数据与脚本在 `artifacts/ability-orders/` |
| **分析时间** | 2026-11-16 |
| **状态** | **已编码**（`war3hook_ai.cpp` / `AiControlManager.cpp` / `SharedMemory.h` / `shared/DotaHeroSkillAbbrev.h`）；实战验收见第七节 |
| **前序文档** | [`dota-ai-skill-command-implementation.md`](./dota-ai-skill-command-implementation.md)（learn 方案）、[`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md)（cast 机制）、[`dota-hero-skill-point-learn-flow.md`](./dota-hero-skill-point-learn-flow.md)、[`dota-player-lasthit-habit-recorder.md`](./dota-player-lasthit-habit-recorder.md)（习惯画像，二期） |
| **配套思维导图** | [`dota-ai-human-lasthit-learn-cast-mindmap.md`](./dota-ai-human-lasthit-learn-cast-mindmap.md) |

---

## 一、结论先行

| 问题 | 结论 |
| :--- | :--- |
| 旧补刀为什么像机器？ | 55ms 固定频率狂按 S（≈18 次/秒，人手做不到）、85ms 固定假动作、每 2.8s 均匀轮换三种模式、看到可补**瞬间**出手、每刀必中、点击坐标分毫不差。 |
| 真人化改了什么？ | 引入 `AiHumanProfile`：对数正态反应时间、成串 S + 停顿、APM 令牌桶、假动作概率与窗口抖动、走位周期/幅度随机、点击抖动、随机发呆、故意漏刀；预判用反应时间中位数做提前量。 |
| 施法要的 OrderId 从哪来？ | **从 `game.dll` 自身的 Order 注册表抽出**（344 条 `字符串 → 0xD0xxx`），再用地图 `Units\AbilityData.slk` / `*AbilityFunc.txt` / `*AbilityStrings.txt` 解析每个英雄技能的基础技能与 Order 串。无需人工抓包。 |
| 目标类型怎么定？ | Channel（`ANcl`）读 `DataB1`（0 无 / 1 单位 / 2 点 / 3 单位或点）；其它基础技能按 Order 串查人工表 `ORDER_TT`。 |
| 学习门槛？ | 地图 SLK：普通技能/属性 `reqLevel=1`、`levelSkip` 缺省 2（1/3/5/7…）；大招 `reqLevel=6, levelSkip=5`（6/11/16）。 |
| 剩余技能点怎么算？ | DotA 不调用 `GetHeroSkillPoints`；改用 `GetHeroLevel − Σ GetUnitAbilityLevel(四技能+属性)`（两个原生地图都会调用，按名缓存即可）。 |
| 是否新增 game.dll RVA？ | **否。** 全部走已有 `EnqueuePlayerAction` + 按名缓存的只读 JASS 原生。 |

---

## 二、OrderId 表的提取（可复现）

### 1. game.dll Order 注册模式

`game.dll`（1.27.0.52240）启动时逐条注册 Order，机器码固定为：

```text
68 <字符串VA>     push "blink"
68 <OrderId>      push 0x000D022D
8B CE             mov  ecx, esi
E8 <rel32>        call RegisterOrder
```

脚本 `artifacts/ability-orders/extract_game_orders.py` 正则扫描该模式，过滤 `0xD0000..0xD0FFF` 与小写串，得到 **344 条**，输出 `orders-1.27.json`。

校验点：`blink=0xD022D`、`thunderbolt=0xD007F`、`channel=0xD0278`、`stop=0xD0004`、`move=0xD0012`，与 [`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md) 第三节实测样本一致。（`attack` 用另一条注册路径，未被模式命中；代码里固定用 `0xD000F`。）

### 2. 地图与基础技能数据

DotA 6.83d 是**优化过的地图**：`war3map.w3a` 里自定义技能放在「原始表」且不带基础 ID，真正的基础技能在地图内 `Units\AbilityData.slk` 的 `code` 列。

| 数据 | 来源 | 用途 |
| :--- | :--- | :--- |
| `alias → code`（基础技能）、`DataA1..F1`、`reqLevel`、`levelSkip`、`Rng1` | 地图 `Units\AbilityData.slk` | 基础技能 / Channel 参数 / 学习门槛 / 距离 |
| `[技能] Order=` | 地图与 MPQ 的 `*AbilityFunc.txt`、`*AbilityStrings.txt`（War3Patch > War3x > war3；本地化串在 `War3xlocal.mpq`） | Order 串；地图里空值表示用基础默认 |
| Channel 的 Order / 目标类型 | `DataF1`（Base Order ID）/ `DataB1`（Target Type） | 大量 DotA 技能基于 Channel |
| 引擎硬编码默认 Order | 人工补表 `ENGINE_DEFAULT_ORDER`（`ANfb firebolt`、`AHdr drain`、`ANms manashieldon`、`AHca coldarrows`、`AOwd ward`） | 这些基础技能在任何数据文件里都没有 `Order=` |

注意的坑：

- SLK 记录里 **X / Y 省略时沿用上一条**（优化器大量省略 X）；第一版解析没处理，导致一半技能查不到。
- 地图可能写引擎不认识的 Order 串（如影萨大招 `serpentward`），回退到基础技能默认（`ward`）。
- 有 `Order=` 但实为被动的：`bash`、`engineeringupgrade`、`demolish`、`incinerate`、`auravampiric`、`attributemodskill`。

MPQ 读取：MPQEditor 控制台模式会卡在 GUI 对话框，改用自写只读解析器 `artifacts/ability-orders/mpqread.py`（哈希表/块表解密 + zlib/bzip2 扇区）。

### 3. 生成结果

`build_skill_table.py` → `War3Launcher/shared/DotaHeroSkillAbbrev.h`（勿手改）+ `dota_hero_skills.json`。

| 目标类型 | 数量（112 英雄 × 4 槽 = 448） |
| :--- | ---: |
| 单位 `0x12` | 140 |
| 点地 `0x11` | 95 |
| 无目标 `0x10` | 122 |
| 单位或点 | 12 |
| 被动 | 79 |
| 非被动但无 OrderId | **0** |

抽查：剑圣（剑刃风暴 none / 治疗守卫 point / 剑舞 passive / 无敌斩 unit）、敌法（闪烁 `0xD022D` point / 法力虚空 unit）、恶魔巫师（穿刺 unit_or_point、妖术、吸魔 `drain`、死亡之指）、影萨（全部主动正确）、冰女大招持续施法保护 10.6s。

已知局限：少数技能由地图用「隐藏辅助技能」实现（如影魔大招 `A29J` 基于 `AIha`），表里显示为被动；需要时用 `cast <FourCC>` 直接指定真实技能码或在表生成脚本里补映射。

---

## 三、真人化补刀

### 1. 参数（`AiHumanProfile`，可用 `lhparam` 实时调）

| 参数 | 默认 | 含义 |
| :--- | :--- | :--- |
| `reaction` | 210ms | 看到可补 → 出手的反应时间中位数 |
| `sigma` | 0.28 | 对数正态形状（右偏：偶尔明显慢） |
| `stop` / `stopjitter` | 135 / 45ms | 压刀 S 平均间隔与抖动（人手 6~9 次/秒） |
| `feint` / `feintrate` | 95ms / 30% | A→S 假动作窗口与概率 |
| `strafe` / `strafeamp` | 430ms / 90 | 走位周期与幅度 |
| `miss` | 4% | 故意放过可补兵 |
| `apm` | 270 | 动作/分钟上限（选中包不计；出手/施法可透支） |
| `jitter` | 14 | 点击坐标抖动半径 |
| `idle` | 10%/s | 发呆 0.3~0.9s 的概率（只在附近没有快死的兵时） |
| `human` | on | off = 回到旧的机械节律（便于对比） |

### 2. 行为变化

| 环节 | 旧 | 新 |
| :--- | :--- | :--- |
| 出手判定 | 预测落地血 ≤ 伤害就**立刻**出手 | 预测时间加上反应中位数做提前量；首次可补时采样反应时间，到点才出手；兵快没血时「抢着按」（等待不超过预测见底时间） |
| 漏刀 | 从不 | 以 `miss` 概率走神放过，日志 `🙈`；该兵死后清除 |
| 压刀 S | 55ms 固定 | 成串 2~5 下（×0.75 间隔）+ 停顿（×1.7）；上限 = 前摇 × 0.55，保证自动攻击伤害打不出去 |
| 假动作 | 85ms 固定，按模式轮流 | 每次按键时机以 `feintrate` 概率触发，窗口 `feint ± 25ms`，上限 = 前摇 × 0.6 |
| 模式 | 每 2.8s 均匀随机 | 混合 50% / 站桩 S 30% / 走位 20%，停留时长对数正态（中位 3.5s） |
| 走位 | 固定 ±100/85 交替 | 周期对数正态、幅度 ×0.55~1.35、角度扰动、80% 交替 20% 同向 |
| 贴近 | 每 350ms | 对数正态（中位 380ms）+ 站位 0.65~0.9 倍攻击距离 + 点击抖动 |
| 手速 | 无上限 | APM 令牌桶；非必要动作（S/走位）没令牌就跳过 |
| 与施法冲突 | — | `g_aiCastGuardUntil`：施法前摇 / 持续施法期间不按 S、不走位 |

日志新增：出手行带 `反应:Nms`；等待行带 `漏刀 / 抢刀` 计数；结束行带 `真人:开/关`。

### 3. 与习惯画像的关系

本次是「通用真人模型」。[`dota-player-lasthit-habit-recorder.md`](./dota-player-lasthit-habit-recorder.md) 的画像字段与 `AiHumanProfile` 一一对应（`stopIntervalMs`↔`stop`、`feintRate`↔`feintrate`、`noiseMissRate`↔`miss`…），二期 Loader 只需把 profile JSON 写进这些字段（可经 `lhparam` 或新 IPC 批量下发）。

---

## 四、加点 learn / autolearn

```text
learn <1..4|q|w|e|r|ult|attr|FourCC> [nosubmenu]
  → 校验：剩余点 > 0、未满级、英雄等级 ≥ reqLevel + 当前等级 × levelSkip
  → 选中英雄 → 0x66（按 O）
  → 等 300~700ms（对数正态，模拟移鼠标点图标；nosubmenu 只等一次反应）
  → 0x10 | 0000 | 技能 FourCC | FF×8
  → 1.2s 后用 GetUnitAbilityLevel 校验：✅ 等级 a→b / ⚠ 未变化（引擎拒绝）

autolearn [on|off] [优先级如 1234]
  → 每 250ms 检查剩余点；有点时先等 0.6~6s（对数正态，中位 1.3s；补刀出手中 2.2s）
  → 大招能学就学 → 4 级前把优先级技能各点一级 → 按优先级加满 → 最后点属性
  → 多个点连续加时间隔 350~1800ms
```

`q/w/e/r` 是**槽位别名**（1..4），不是地图真实热键（真实热键见 `skills` 输出）。

---

## 五、施法 cast

```text
cast <1..4|q|w|e|r|ult|FourCC> [x y | enemy | creep | ally | self | none | 0x<句柄>]

缺省目标：无目标技能直接放；单位/点地技能 → 最近可见敌方英雄，没有则最近敌方小兵
点地技能给了单位目标 → 对单位位置放
包：0x10 OrderId（无目标） / 0x11 OrderId X Y（点地，23 字节） / 0x12 OrderId X Y 对象ID×2（单位）
真人：无目标 70~500ms（中位 150）、指向 140~900ms（中位 290）反应；点地坐标 ±1.5×jitter
施法保护：从按键到 guardMs（600ms + Channel 持续时间，如冰女大招 10.6s）补刀例程不按 S
拒绝：被动技能、未学（GetUnitAbilityLevel=0）、找不到目标
```

---

## 六、命令总表（RemoteControl 与游戏内 `-` / `/` 前缀相同）

| 命令 | 示例 |
| :--- | :--- |
| `skills` | 输出英雄技能槽、等级、OrderId、目标类型、门槛、剩余点 |
| `learn` | `learn 1`、`learn ult`、`learn attr`、`learn A05G nosubmenu` |
| `autolearn` | `autolearn on`、`autolearn on 2134`、`autolearn off` |
| `cast` | `cast 1`、`cast 2 enemy`、`cast w -6000 -6000`、`cast 4 0x00101234` |
| `lhparam` | `lhparam`（只看）、`lhparam reaction 260`、`lhparam miss 6`、`lhparam human off` |
| `lasthit` / `deny` | 不变；真人化默认开启 |

`ai_control.ps1` 已加入上述命令：`.\ai_control.ps1 learn -- 1`、`.\ai_control.ps1 cast -- 2 enemy`。

---

## 七、验收记录（2026-11-17，本地 War3Server + C:\War3Run，AP83，英雄 `H001` 流浪剑客）

| # | 操作 | 结果（`logs\AiUnit.log`） |
| :--- | :--- | :--- |
| 1 | 进图 | `GetUnitAbilityLevel` / `GetHeroLevel` 按名解析成功（地图首次调用时） |
| 2 | `skills` | 4 槽 + 属性、OrderId、目标类型、门槛（大招 `6+5×n`）、剩余点 1 全部正确 |
| 3 | `learn ult`（1 级） | ⛔ 英雄等级不够 ✅ |
| 4 | `learn 1` | 按 O → 655ms 后点击 → `A190 等级 0 → 1` ✅ |
| 5 | `cast 2`（被动） / `cast 3`（未学） | ⛔ 被动技能 / ⛔ 还没学 ✅ |
| 6 | `cast 1`（泉水，无目标） | ⛔ 找不到目标 ✅ |
| 7 | `cast 1 creep`（中路） | 风暴之锤 `0xD02B6` 单位目标，反应 245ms，已入队并开 600ms 施法保护 ✅；**技能效果未在主机侧核验** |
| 8 | `autolearn on 3124`（2 级） | 1310ms 后自动按 O → 516ms 后点 → `A2IS 等级 0 → 1` ✅（按优先级 3） |
| 9 | `lasthit 45 90 700` | 90s 内出手 8 次，确认成功 4（正补 1、反补 3）；反应时间 91~294ms 分散；故意漏刀 2 次；抢刀 2 次 ✅ |

出手样例：

```text
⚔ [正补] 出手 #2 → ugho 血:64/550 掉血:88/s 预计 0.56s 后落地，落地血:18 ≤ 伤害:45 反应:129ms
│ [正补] 🙈 走神放过 unec 血:64（真人漏刀，累计 1）
⚔ [反补] 出手 #5 → esen 血:74/550 掉血:59/s 预计 0.54s 后落地，落地血:30 ≤ 伤害:45 反应:294ms
🏁 [正补] ✅ 本轮连续补刀结束 | 成功:4 出手:8 | 真人:开 漏刀:2 抢刀:2
```

### 第二轮（2026-11-17，英雄 `Hjai` 水晶室女，远程）

| # | 操作 | 结果 |
| :--- | :--- | :--- |
| 10 | `cast 1 <x> <y>`（冰霜新星，点地 `0x11`，order `0xD0079`） | 反应 335ms，坐标抖动 18；落点 250 内两只满血敌兵：`580 → 480`（**正好 -100 = 1 级新星伤害**）与 `580 → 123`（同时被小兵攻击）✅ **施法效果已在游戏内核验** |
| 11 | `lhparam reaction 400` + `sigma 0.1` + `miss 0` | 三条参数即时生效（`🎛 [Human]` 回显） |
| 12 | 远程补刀 `lasthit 40 70 900 0.45 900 600` | 出手 11、确认 5；反应时间 371~485ms（集中在 400 附近，对比默认参数时 91~294ms）；漏刀 0 ✅ |

测试方法备注：

- 1 级英雄独自走到河道会被兵线打死，测试脚本改为「跟在己方最前排小兵身后 300」，敌兵进入 850 再施法 / 开补刀。
- 测试脚本含中文正则时必须存为 **UTF-8 BOM**，否则 Windows PowerShell 5.1 按 ANSI 读取，`英雄` / `玩家` 永远匹配不上。
- `AiUnit.log` 为异步写入，`units` 之后至少等 ~1.5s 再读。

### 第三轮（2026-11-17 02:28~02:40，冰女中路真人补兵练到 6 级 → 大招施法保护）

**先修的缺陷**：第一版施法保护只挡等待期的 S / 假动作 / 走位，**出手（0x12 攻击）和 `-back`/`-push`/`-unsafe` 的自动移动仍会发出**，都会打断持续施法。修复：保护检查前移到出手判定之前；`aiTickBackAndPush` 与自动退守在保护期内不发移动；保护期每秒记一行 `🛡 [CastGuard]`（剩余时间 + 放过的可补兵次数）。

| 步骤 | 结果 |
| :--- | :--- |
| `pick cm` → `lock on` → `autolearn on 1234` → `back on` | 镜头锁定（偏差 0.0）；1 级 2.1s 后自动加冰霜新星 ✅ |
| 跟兵线真人补兵（脚本：无敌兵时站己方最前排兵身后 350，敌兵进 1000 开 `lasthit`） | 02:30 → 02:38 由 1 级升到 6 级，中途未死亡 ✅ |
| 6 级自动加点 | 升级 0.97s 后按 O → 559ms 点击 → `A03R 等级 0 → 1`（大招优先）✅ |
| 补刀例程运行中 `cast 4`（冰封领域，无目标 Channel `0xD0278`） | 反应 180ms 发出，保护 10600ms |
| 保护期 11 秒内 | `CastGuard` 每秒一行倒计时 10780 → 522ms；共放过可补兵 **52 次**；该窗口内 **无任何「出手 / 贴近 / Back」日志** ✅ |
| 英雄位置 T+3 / T+6 / T+9 | 均为 (-883, -917)，持续施法未被打断 ✅ |
| 周围两只敌兵 | 394 / 479 → T+3：死 / 81 → T+6：均死 ✅ |
| 对敌方英雄施法（`enemy` 目标） | 单人房间无敌方英雄 |
| `killgame` 后重新建房 | **已修复**（见下） |

### 缺陷修复：killgame 后无法重开 + Launcher 日志「开局后停止」

| 问题 | 根因 | 修复 |
| :--- | :--- | :--- |
| `killgame` 后 `start` 在 StartingGame 超时 | 正常退出靠钩子 DLL 发 `MSG_TYPE_GAME_CLOSED` / 主 Socket 关闭 IPC 触发 `NetworkManager::cleanupAfterGameExitOnce`；强杀时 DLL 来不及发，Launcher 停在对局状态 | `AiControlManager` 的 `killgame` 在结束进程后主动调用 `cleanupAfterGameExitOnce("RemoteControl killgame")`（`/leave` + RoomManager/GameManager 重置，按局去重），并停止自动化 |
| 开局后 Launcher 各日志（ai_control / room_* / game_monitor…）停在开局后 ~30s | **不是停止，是积压**：`DebugWorker` 每条日志 open→write→flush→close 且无条件 `WriteConsoleW`；开局后高频日志产生速度远大于写入速度，Qt 跨线程队列无限堆积。实测 01:42 落盘的行时间戳是 00:38（落后 64 分钟），内存同步上涨。D:（U 盘）上更严重 | `workers/DebugWorker.cpp`：文件句柄常驻（上限 192）、按文件缓冲、满 64KB 或每 250ms 落盘、仅有控制台时才写控制台；析构时全部落盘 |

注：上一轮诊断「`isInGame=TRUE`」读的是积压前的最后一行日志，只能作为线索，不能作为状态证据。

修复验收（2026-11-17 02:00~02:06，C:\War3Run）：

| 项 | 结果 |
| :--- | :--- |
| 开局 1 分钟后日志时效 | `room_ping` / `room_local_player_slot` / `data_monitor` 落盘时间与行时间戳相差 < 0.3s（修复前落后 64 分钟）✅ |
| `killgame` → `start` 第 1 次 | 清理日志「清理前游戏状态: 游戏中 / 房间状态: 在房间」→ 复位回大厅；`start` 6s 后 `Completed`，新 war3 进程 ✅ |
| `killgame` → `start` 第 2 次 | 同上，6s `Completed` ✅ |

---

## 八、文件清单

| 文件 | 作用 |
| :--- | :--- |
| `War3Launcher/shared/SharedMemory.h` | `AI_UNIT_CMD_LEARN/CAST/AUTO_LEARN/HUMAN_PARAM/SKILLS`、`AiCastTargetMode`、`AiHumanParam`、payload 新增 `aux` |
| `War3Launcher/shared/DotaHeroSkillAbbrev.h` | 生成的技能表（FourCC / OrderId / 目标 / 门槛 / 距离 / 保护时长 / 热键） |
| `War3Launcher/hooker/war3hook_ai.cpp` | 真人化模型、补刀改造、learn / autolearn / cast / skills / lhparam、聊天解析 |
| `War3Launcher/hooker/war3hook_process.cpp` | 已知指令表加入新命令 |
| `War3Launcher/managers/AiControlManager.cpp` | RemoteControl 解析 |
| `War3Launcher/scripts/ai_control.ps1` | 命令行助手 |
| `War3Analysis/artifacts/ability-orders/` | `extract_game_orders.py`、`mpqread.py`、`build_skill_table.py`、`orders-1.27.json`、`dota_hero_skills.json`、抽取的原始 txt/slk |

重新生成：

```bash
cd D:\Qt\workspace\War3Analysis\artifacts\ability-orders
python -I build_skill_table.py D:\Qt\workspace\War3Launcher\shared\DotaHeroSkillAbbrev.h dota_hero_skills.json orders-1.27.json
```
