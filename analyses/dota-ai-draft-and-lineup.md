# DotA AI 选人 / 阵容评估算法设计

| 项 | 内容 |
| :--- | :--- |
| **分析模型** | Composer（Cursor Agent） |
| **分析目的** | 基于克制图与选人接口，设计可落地的阵容评分 + 选人打分 + RemoteControl/自动选人接口；实现前列出改动面 |
| **命名方式** | `dota-ai-draft-and-lineup`；导图 `dota-ai-draft-and-lineup-mindmap.md`；数据约定 `artifacts/draft-ai/`（实现时落盘） |
| **分析时间** | 2026-11-21 |
| **约束** | 只读设计；不改 hook / Launcher 源码 |

## 依赖与缺口

| 依赖 | 状态 | 本设计如何处理 |
| :--- | :--- | :--- |
| `dota-683d-hero-counter-graph.md` + `artifacts/hero-draft/*.json` | **工作区未找到** | 下文定义克制边 / 英雄画像 **契约**；用例用 **示意边权**（标 `illustrative`），实现前需补真实图 |
| `dota-683d-draft-flow-and-ai-interface.md` | **工作区未找到** | 接口落在已有逆向与代码：[`warcraft-iii-dota-tavern-shop-select.md`](./warcraft-iii-dota-tavern-shop-select.md)、[`dota-rd-and-sd-mode-execution-chain.md`](./dota-rd-and-sd-mode-execution-chain.md)、[`dota-6.83d-single-draft-candidates.md`](./dota-6.83d-single-draft-candidates.md)、`SharedMemory.h` CM/RD/SD 同步、`AiControlManager` `pick`/`heroes`/`random` |
| [`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md) | 有 | 抽出 **AI 会玩** 分层，作选人降权依据 |

英雄键统一：`index`（1..112，`DotaHeroAbbrev.h`）+ `code`（FourCC）+ `abbrev`。例：矮人火枪手 `26` / `Usyl` / `sniper`；幽鬼 `85` / `E01B` / `spec`。

---

## 1. 数据契约

### 1.1 英雄画像 `hero_profiles_683d.json`

每个英雄一条（可由 SLK + 人工标签生成；实现时放 `artifacts/draft-ai/`）：

```json
{
  "schema": "draft-ai/hero-profile/v1",
  "heroes": {
    "Usyl": {
      "index": 26, "abbrev": "sniper", "name": "矮人火枪手",
      "primaryAttr": "agi",
      "roles": ["carry", "late"],
      "lanes": ["mid", "bot"],
      "damage": { "phys": 0.95, "magic": 0.05 },
      "controlSeconds": 0.0,
      "initiators": 0.0,
      "aoeTeamfight": 0.2,
      "push": 0.3,
      "powerCurve": { "early": 0.2, "mid": 0.5, "late": 0.95 },
      "mobility": 0.15,
      "sustain": 0.2,
      "save": 0.0
    }
  }
}
```

| 字段 | 含义 | 建议量纲 |
| :--- | :--- | :--- |
| `roles` | 定位标签集合 | `carry` / `mid` / `offlane` / `support` / `hard_support` / `jungler` / `roamer` |
| `lanes` | 可分路 | `top` / `mid` / `bot` / `jungle` / `roam` |
| `damage.phys/magic` | 输出构成（和为 1） | 0..1 |
| `controlSeconds` | 单人满级对单目标有效硬控估算秒 | 秒 |
| `initiators` | 先手能力 | 0..1 |
| `aoeTeamfight` | AOE 团战 | 0..1 |
| `push` | 推进 / 拆塔 | 0..1 |
| `powerCurve` | 发力期 | early/mid/late 各 0..1 |
| `mobility` / `sustain` / `save` | 位移 / 续航 / 救援 | 0..1 |

### 1.2 克制图 `counter_graph_683d.json`

有向边 `A → B` 表示 **A 克制 B**（选 A 打已出现的 B 加分）：

```json
{
  "schema": "draft-ai/counter-graph/v1",
  "edges": [
    {
      "from": "E01B", "to": "Usyl", "weight": 0.85,
      "reasons": ["gap_close", "reflect", "haunt_global"],
      "source": "illustrative"
    }
  ]
}
```

`weight` ∈ [0,1]。同名反向边表示互克。缺边 = 0。实现时应用真实图替换示意边。

### 1.3 协同图（可选）`synergy_graph_683d.json`

`A ↔ B` 或有向 `A 配合 B`：先手+爆发、光环+物理核、全球大+拆塔等。缺省可用角色启发式（见 §2.3）。

### 1.4 AI 能力表 `ai_capability_683d.json`

由 tactics / `kAiHeroCombos` / `kAiAoeUlts` / farm 表导出：

| tier | 含义 | `playWeight` | 本仓库现状（示例） |
| :---: | :--- | ---: | :--- |
| **A** | 连招+打野/团战大+通用对线均可用 | 1.00 | `Hjai` 冰女 |
| **B** | 有编码连招或专属 farm/AOE/推线 | 0.75 | 莉娜 `H004`、莱恩 `UC18`、胖子 `U00F`、船长 `H06S`、影萨 `Orkn`、猛犸 `UC11`、小牛 `Otch`、蝙蝠 `O016`、流浪 `H001`、潮汐 `Ofar`、斧王 `Opgh`、露娜 `E005`、美杜莎 `H00V`、先知 `Emns`、剧毒 `EC57`、谜团 `Uktl`、沙王 `U00K`、虚空 `EC45`、卓尔 `Nbrn`（加点） |
| **C** | 仅通用：卡兵/补刀/逃命/burst/aoe 表外 | 0.40 | 其余可选英雄 |
| **D** | 明确缺状态机 / 极高操作 | 0.10 | 卡尔 `H00U`（切球表已有、tactic 仍 CATALOG）、地卜师等 |

`playWeight` 参与选人分，**不**直接进阵容纯理论分（可选 `aiAwareLineup=true` 时乘入）。

---

## 2. 阵容评分 `scoreLineup(team[5], weights)`

对已选（或假设选满）的 5 人算 **阵容健康度** ∈ 大致 0..100。各项先归一到 0..1，再按可调权重加权。

### 2.1 子分项

| 键 | 计算要点 | 默认权重 `W` |
| :--- | :--- | ---: |
| `roleCover` | 是否覆盖：`carry`、`support`（含 hard_support）、`initiator`（`initiators≥0.5` 或 offlane 坦克）、`control`（队内 `Σ controlSeconds ≥ 4`） | 18 |
| `dmgBalance` | `physShare = Σ phys / (Σ phys+Σ magic)`；理想带 `[0.35, 0.75]`，偏离线性扣分 | 12 |
| `controlTotal` | `min(1, Σ controlSeconds / 12)` | 12 |
| `aoeTeamfight` | `min(1, mean(aoe) * 1.2 + max(aoe) * 0.3)` | 12 |
| `push` | `min(1, Σ push / 2.5)` | 8 |
| `powerCurve` | early/mid/late 三峰是否至少有一峰 `≥0.7` 且不三峰全 `<0.35`（避免全晚期或全早期崩） | 12 |
| `laneAssign` | 贪心分配 top/mid/bot +（jungle\|roam）后，冲突数越少越好；双中无辅等重罚 | 16 |
| `synergy` | 队内协同边均值 + 角色互补启发 | 10 |

$$
S_{\text{lineup}} = \sum_k W_k \cdot s_k \Big/ \sum_k W_k \times 100
$$

### 2.2 分路贪心（`laneAssign`）

1. 中路候选：`lanes` 含 `mid` 且（`roles` 含 mid/carry 或 `powerCurve.mid` 高）优先 1 人。  
2. 优势路 / 劣势路：按 `carry` vs `offlane`/`support` 分配 bot/top（近卫约定：bot=优势；天灾镜像）。  
3. 剩余：`hard_support`→跟 carry；`jungler`/`roamer`→第四槽。  
4. 惩罚：两人抢同一硬位 −0.25/冲突；无任何 `support*` −0.4；无 carry/mid 输出核 −0.4。

### 2.3 角色互补启发（无协同图时）

- 高 `initiators` + 高爆发 carry（`phys` 或 `magic` ≥0.7 且 mid/late 高）→ +  
- 双纯物理且无 `control` → −  
- 全球大（Haunt 类：画像可加 `global=true`）+ 推进核 → +  

### 2.4 伪代码

```text
function scoreLineup(heroes, W = DEFAULT_WEIGHTS):
  P = map(heroes, loadProfile)
  s.roleCover   = coverRoles(P)           # 0..1
  s.dmgBalance  = balanceDamage(P)
  s.controlTotal= clamp(sum(p.controlSeconds)/12, 0, 1)
  s.aoeTeamfight= aoeScore(P)
  s.push        = clamp(sum(p.push)/2.5, 0, 1)
  s.powerCurve  = curveHealth(P)
  s.laneAssign  = laneGreedy(P)
  s.synergy     = synergyScore(P, SYNERGY_GRAPH)
  return 100 * weightedMean(s, W)
```

---

## 3. 选人打分 `scorePick(candidate, state)`

### 3.1 草稿状态 `DraftState`

```text
mode: AP | CM | RD | SD | NM | XL | AR | ...
phase: ban | pick | ap_open
ourPicks[], enemyPicks[], ourBans[], enemyBans[]
pool[]          # RD 共享池 / CM 全池减 ban / SD 本人 3 候选 / AP=全英雄
turnIndex       # 本方第几次行动（0-based）
isFirstPickTeam # CM/RD 是否先手方
mySlotLaneHint  # 可选：已知要打哪路
```

候选集合：

| 模式 | `candidates` |
| :--- | :--- |
| AP / NM | 全英雄 − 已 ban − 已选 −（NM：己方阵营池） |
| CM | 未 ban 未选 |
| RD | 当前仍在 `QA0` 池且 `Q90=0` |
| SD | 本机 `sdRandomHeroUnitIds[local]` 三个 |
| AR | 不可主动选（跳过建议 / 只评估随机结果） |

### 3.2 分项与默认权重

| 键 | 公式要点 | 默认 `V` | 备注 |
| :--- | :--- | ---: | :--- |
| `counterEnemy` | `Σ_e edge(cand→e).weight / max(1,|E|)` | **32** | 克制对方已选 |
| `synergyAlly` | `Σ_a synergy(cand,a) / max(1,|A|)` | 18 | 配合己方 |
| `fillGap` | `scoreLineup(A∪{cand}) − scoreLineup(A)` 再映射到 0..1（差 ÷ 25 clamp） | 18 | 补缺口 |
| `counteredByEnemy` | `Σ_e edge(e→cand).weight / max(1,|E|)` | **22** | 被克（减分） |
| `aiPlay` | `playWeight(cand)` | 16 | AI 会不会玩 |
| `flexEarly` | 先手轮：泛用度 `flex(cand)`；后手轮：抬高 `counterEnemy`（见 §3.3） | 内嵌于顺序因子 | |

综合（在纳入顺序因子前）：

$$
R = V_c C - V_x X + V_s S + V_g G + V_a A
$$

其中 \(C\)=`counterEnemy`，\(X\)=`counteredByEnemy`，\(S\`=`synergyAlly`，\(G\`=`fillGap`，\(A\`=`aiPlay`。再乘顺序因子 \(\phi\)，得 `pickScore = 100 * σ(R) * φ` 或直接线性归一（实现选线性更易解释）：

```text
raw = Vc*C + Vs*S + Vg*G + Va*A - Vx*X
pickScore = 100 * clamp(raw / (Vc+Vs+Vg+Va), 0, 1)   # 分母不含 Vx，使「被克」真扣分
pickScore *= phi(turn, mode)
```

每条推荐必须带 **`breakdown`**：各项原始值、用到的边、阵容差分、tier。

### 3.3 选人顺序因子 \(\phi\)

| 情境 | \(\phi\) 调整 |
| :--- | :--- |
| 全局先手第 1 抢（CM/RD first pick） | 抬高 `flex`：`flex = 0.4*mean_outdegree_norm + 0.3*(1-role_specificity) + 0.3*aiPlay`；\(\phi = 0.85 + 0.15*flex\)；并 **临时** 把 `Vc` 乘 0.7（少赌死克） |
| 后手 / 对方已露出核心 | \(\phi = 1.0\)；`Vc` 乘 1.15 |
| 本方末位（收阵容） | `Vg` 乘 1.25；优先补 `roleCover`/`lane` 缺口 |
| SD | 只在 3 候选内排序；\(\phi=1\)；忽略 flex |
| AP 开放抢 | 与「后手」类似，但若敌方 0 人则用 first-pick flex |

### 3.4 伪代码

```text
function suggestPicks(state, topK=5):
  cands = eligible(state)                    # 按模式过滤
  scored = []
  for h in cands:
    C, Cedges = avgCounter(h, state.enemyPicks)
    X, Xedges = avgCountered(h, state.enemyPicks)
    S, Sedges = avgSynergy(h, state.ourPicks)
    G, Gdetail = gapDelta(state.ourPicks, h)
    A, tier = aiPlay(h)
    Vc,Vx,Vs,Vg,Va = tuneWeights(state)      # 含先后手
    raw = Vc*C + Vs*S + Vg*G + Va*A - Vx*X
    score = 100 * clamp(raw / (Vc+Vs+Vg+Va), 0, 1)
    score *= phi(state)
    scored.append({ hero:h, score, breakdown:{C,X,S,G,A,tier,Cedges,Xedges,Sedges,Gdetail} })
  return topK by score desc

function autoPick(state):
  rec = suggestPicks(state, 1)[0]
  if rec.score < MIN_AUTO_SCORE: return wait_or_random_policy(state)
  emit pick(rec.hero.abbrev)                 # → 现有 pick 管道
```

`MIN_AUTO_SCORE` 建议 35（SD 可降到 25，避免三差里僵死）。

---

## 4. 用例

### 4.1 对方先选矮人火枪手 → Top 推荐须含幽鬼

**状态**：AP/CM 开局，`enemyPicks=[Usyl]`，`ourPicks=[]`，后手方第一次选。  
**示意边**（`source: illustrative`，实现前替换）：

| from | to | w | 理由标签 |
| :--- | :--- | ---: | :--- |
| `E01B` 幽鬼 | `Usyl` | 0.85 | 幽灵步接近、折射反伤、大招全球砸玻璃炮 |
| `Nbbc` 主宰 | `Usyl` | 0.70 | 跳砍贴脸 |
| `HC92` 隐刺 | `Usyl` | 0.65 | 烟幕+背刺 |
| `U00F` 胖子 | `Usyl` | 0.60 | 钩起秒玻璃 |
| `Usyl` | `E01B` | 0.25 | 远程风筝弱克（远低） |

**幽鬼 `E01B` 得分拆解**（默认权重，后手 `Vc×1.15` → 有效 Vc≈36.8；其余默认；无己方故 S=0；空阵容 G 按「补 late carry」≈0.55；AI tier C → A=0.40）：

| 项 | 值 | 来源 |
| :--- | ---: | :--- |
| C counterEnemy | **0.85** | 边 `E01B→Usyl` w=0.85 |
| X counteredBy | **0.25** | 边 `Usyl→E01B` w=0.25 |
| S synergyAlly | 0.00 | 己方空 |
| G fillGap | 0.55 | 补 carry + late 峰 |
| A aiPlay | 0.40 | tier C（无专属连招） |
| raw | \(36.8\times0.85 + 18\times0 + 18\times0.55 + 16\times0.40 - 22\times0.25\) ≈ **43.4** | |
| 归一分母 | 36.8+18+18+16=88.8 | |
| **pickScore** | **≈48.9** | \(100\times43.4/88.8\) |

同池对比（示意）：主宰 C=0.70、胖子 C=0.60 且 tier B（A=0.75）可能总分接近或略高——**推荐列表仍应包含幽鬼**；展示时按分排序，理由栏必须写出克制边。Top5 期望示例：`spec` / `bs` / `pudge` / `riki` / `pa`（具体序随真实图与 AI 权重变化）。

### 4.2 完整 5v5 选人过程示例（示意）

下列为 **CM 类轮次** 叙述；边权 illustrative；AI 侧偏向 tier A/B。

#### 例 A — 对方 sniper 一抢，我方偏辅助开局

| 序 | 方 | 选择 | 决策摘要 |
| :---: | :---: | :--- | :--- |
| 1 | 敌 | `sniper` | 玻璃远程核 |
| 2 | 我 | `spec` | 高 C vs sniper；补 late carry（§4.1） |
| 3 | 敌 | `lina` | 魔法爆发 |
| 4 | 我 | `es` | tier B 连招；先手+沟壑；抬 control |
| 5 | 敌 | `ss` | 推线+控制 |
| 6 | 我 | `cm` | **tier A**；光环配合智力；补 support + aoe |
| 7 | 敌 | `dk` | 前排 |
| 8 | 我 | `axe` | farm+发起；offlane |
| 9 | 敌 | `wd` | 辅助 |
| 10 | 我 | `luna` | 物理团战 AOE；与 axe/es 发力 mid |

阵容粗评：我方 role 齐、控制足、phys/magic 尚可；AI 可玩度高（cm/es/axe/luna 均 B+）。

#### 例 B — 我方先手，强调 flex

| 序 | 方 | 选择 | 决策摘要 |
| :---: | :---: | :--- | :--- |
| 1 | 我 | `cm` | first-pick flex + tier A，少赌死克 |
| 2 | 敌 | `am` | 反魔核 |
| 3 | 我 | `tide` | 魔法减伤团控；不完全怕 am；tier B |
| 4 | 敌 | `drow` | 物理光环 |
| 5 | 我 | `cent`/`bb` 类前排（若画像有）或 `axe` | 补 initiator；斧王 AI B |
| … | … | … | 末位用 `fillGap` 补 hard_support / 推线 |

#### 例 C — SD：本人候选 `cm` / `sniper` / `invoker`

| 候选 | C（敌已有 pudge+lina） | A | 结论 |
| :--- | :--- | ---: | :--- |
| `cm` | 中（控 lina 走位） | 1.00 | **首选** |
| `sniper` | 低且怕钩 | 0.40 | 次 |
| `invoker` | 理论高 | **0.10** | 垫底（不会玩） |

#### 例 D — RD 池 24 人，对方已选 `void`+`enigma`

建议抬高：高魔免/驱散/打断通道类（画像 `anti_channel` 标签，待补）；AI 侧优先 `ss`/`lion`/`es` 等 B 级打断，而不是只会站桩的 C 级。

#### 例 E — AP 敌方五黑假想核 `medusa`+`cm` 光环体系

`fillGap` 倾向：破光环推线（`np` B）、或静默（`silencer` C→降权）、或 `bat` 发起（B）。最终在「破法」与「AI 会玩」间折中 → `bat`/`np` 进 Top5。

---

## 5. 落地接口

### 5.1 RemoteControl（`127.0.0.1:6120`）

在现有 `pick` / `heroes` / `random` / `shop` 旁增加：

| 命令 | 行为 |
| :--- | :--- |
| `draft status` | 打印 mode/phase、双方已选/已 ban、池大小、是否我方回合 |
| `draft suggest [k]` | 默认 k=5；每行：`rank score abbrev name | C=.. X=.. S=.. G=.. A=tier | reasons...` |
| `draft explain <abbrev>` | 单英雄完整 breakdown（边列表） |
| `draft autopick [on\|off\|once]` | once=按建议发一次 `pick`；on=每到我方回合自动 |
| `draft weights` / `draft weights reset` | 调试：读写 `V_*` / `W_*`（内存或 json） |

底层选人仍走现网：`pick <abbrev>` → `AiControlManager::pickHero` → `MSG_TYPE_HERO_PICK_*` / DLL `requestHeroPickByIndex`（酒馆 + `0x10`）。SD 需先确认候选在 `sdRandomHeroUnitIds`；RD 需点池内展示单位 + `h06N` 确认（见 RD 链路文档）。

### 5.2 Hook / 共享状态（只读消费）

| 来源 | 用途 |
| :--- | :--- |
| `isHeroPicking` / `isHeroPickCompleted` | 门闩 |
| `cmDraftPhase` / round / hero lists / turn | CM |
| `MSG_TYPE_HERO_POOL_RANDOM_SYNC` / RD `Q80/Q90` | RD 池 |
| `sdRandomHeroUnitIds[slot][3]` | SD |
| `MSG_TYPE_PLAYER_PICK_COMPLETED` / 英雄同步 | 双方已选 |
| `NM` 阵营池同步 | NM 过滤 |

建议 **评分跑在 Launcher**（Qt，易读 json、打日志）；DLL 只负责状态同步与执行 `pick`。自动选人定时器放 `AiControlManager`（与 `--ai-autostart` 同级），不要在 `war3hook_ai_tactics.inl` 里塞草稿逻辑。

### 5.3 数据文件（实现时目录）

```text
War3Analysis/artifacts/draft-ai/
  hero_profiles_683d.json      # §1.1
  counter_graph_683d.json      # §1.2（可从计划中的 hero-draft 迁入）
  synergy_graph_683d.json      # §1.3 可选
  ai_capability_683d.json      # §1.4
  weights_default.json         # W_* 与 V_* 默认
  examples/sniper_first_pick.json  # §4.1 回归样例
```

Launcher 运行时可复制到 `C:\War3Run\War3Launcher\config\draft-ai\`（同步脚本需加规则；配置保留策略同 ini）。

### 5.4 实现前列出要改的文件（尚未改）

| 文件 | 改动 |
| :--- | :--- |
| `War3Launcher/managers/AiControlManager.{h,cpp}` | `draft *` 命令；加载 json；`suggest`/`autopick` |
| 新建 `War3Launcher/draft/DraftScorer.{h,cpp}`（或 `lib`） | `scoreLineup` / `scorePick` / breakdown |
| `War3Launcher/managers/NetworkManager.cpp` / Room 选人状态 | 向 DraftScorer 暴露双方 picks/bans/pool |
| `War3Launcher/shared/SharedMemory.h` | 仅当 Launcher 缺字段时补齐只读镜像（尽量不改） |
| `War3Launcher/hooker/war3hook_process.cpp` | 可选：游戏内 `-draft suggest` 转发到同一评分（非必须） |
| `scripts/ai_control.ps1` / `Scripts/Start-AiGame.ps1` | 文档化 `draft suggest`；自动选人开关 |
| `scripts/Sync-War3Run.ps1` | 同步 `config/draft-ai/*.json` |
| `War3Analysis/artifacts/draft-ai/*` | 数据生成脚本（Python）+ 样例 |
| `War3Analysis/analyses/dota-683d-hero-counter-graph.md` 等 | **补齐前置克制图**（本设计的硬依赖） |

**明确不改（首轮）：** `war3hook_ai_tactics.inl`、`war3hook_ai.cpp` 对线逻辑、War3Bot。

### 5.5 验收

1. `draft suggest` 在「仅敌方 sniper」时 Top5 **含** `spec`，且 `explain spec` 显示 `E01B→Usyl` 边。  
2. SD 三候选含 `invoker`+`cm` 时，默认排序 `cm` > 其他（`aiPlay`）。  
3. 空敌方 first-pick 时，推荐偏 flex + tier A/B，而非冷门死克。  
4. `autopick once` 实际发出与 `pick` 相同 IPC，英雄生成。  
5. 权重文件改 `Vc` 后建议序变化可复现。

---

## 6. 与 tactics「会玩」对照（能力导出）

| 能力来源 | 英雄（FourCC） | tier 建议 |
| :--- | :--- | :---: |
| 连招 `kAiHeroCombos` | `H004` 莉娜, `UC18` 莱恩, `U00F` 胖子, `H06S` 船长, `Orkn` 影萨, `UC11` 猛犸, `Otch` 小牛, `O016` 蝙蝠, `H001` 流浪, `Ofar` 潮汐, `Hjai` 冰女 | B（冰女升 A） |
| AOE 大 `kAiAoeUlts` | `Uktl` 谜团, `Hjai`, `Ofar`, `U00K` 沙王, `EC57` 剧毒, `UC11`, `EC45` 虚空, `E005` 露娜, `Otch`, `H00V` 美杜莎 | ≥B |
| 清野 farm | `Opgh` 斧王, `O016`, `H00V`, `E005`, `Hjai`, `Emns` 先知 | ≥B |
| 推线 `venomward` | `EC57` | B |
| 加点特例 | `Hjai`, `EC57`, `Nbrn` 卓尔, `Opgh`, `O016` | 计入 B |
| 通用 block/lasthit/escape/burst | 全英雄 | 保底 C |
| CATALOG 卡尔 | `H00U` | D 直至切球状态机 READY |

冰女同时具备 combo + cmfarm + aoeult + build + 通用对线 → **唯一默认 A**。

---

## 7. 风险与后续

1. **克制图缺失**：无真实边则 `counterEnemy` 退化，系统变成「AI 会玩 + 阵容缺口」选择器——仍可用，但 §4.1 验收依赖补图。  
2. 画像手标偏差：优先从技能标签半自动生成 `controlSeconds`/`aoe`，再人工修。  
3. CM 船长模式：建议分 `captain` vs `player`；非船长只 `suggest` 不 `autopick`。  
4. 与 Ban：`draft suggest` 在 ban 阶段改为 `suggestBan` = 高威胁且克我方已选 / 对方招牌（可第二期）。

---

## 8. 来源索引

- [`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md) §连招 / farm / aoe / 待补  
- [`warcraft-iii-dota-tavern-shop-select.md`](./warcraft-iii-dota-tavern-shop-select.md)  
- [`dota-rd-and-sd-mode-execution-chain.md`](./dota-rd-and-sd-mode-execution-chain.md)、[`dota-6.83d-single-draft-candidates.md`](./dota-6.83d-single-draft-candidates.md)  
- `War3Launcher/shared/DotaHeroAbbrev.h`、`SharedMemory.h`（CM/SD/选人 IPC）  
- `War3Launcher/managers/AiControlManager.h`（RemoteControl 命令面）  
- `War3Launcher/hooker/war3hook_ai_tactics.inl`（`kAiHeroCombos` / `kAiAoeUlts` / farm）  
- `War3Bot/images/dota_data.json`（`Usyl` / `E01B` / `Hjai` 等）
