# DotA 6.83d 插眼 / 排眼逆向与 AI 落地方案

| 项 | 内容 |
| :--- | :--- |
| **分析模型** | Composer（Cursor Agent） |
| **分析目的** | 给 AI 一套可执行的插眼 / 排眼方案：眼单位数据、高地视野、眼位库、真视检测（JASS + `game.dll`）、无真视推测、打眼与 hook 接口 |
| **命名方式** | `dota-683d-ward-and-deward`；导图 `dota-683d-ward-and-deward-mindmap.md` |
| **分析时间** | 2026-11-21 |
| **配套思维导图** | [`dota-683d-ward-and-deward-mindmap.md`](./dota-683d-ward-and-deward-mindmap.md) |
| **证据目录** | `War3Analysis/artifacts/ward-deward/`（地图 SLK 摘录、`visibility_natives.md`、扫描脚本） |
| **已读不重复** | [`dota-6.83d-active-items-and-consumables-reverse.md`](./dota-6.83d-active-items-and-consumables-reverse.md)、[`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md) §5、[`dota-683d-vision-and-fog-juke.md`](./dota-683d-vision-and-fog-juke.md)、[`warcraft-iii-fog-of-war-implementation.md`](./warcraft-iii-fog-of-war-implementation.md)、[`dota-neutral-camp-spawn-box.md`](./dota-neutral-camp-spawn-box.md)、[`dota-6.83d-eat-and-cut-tree-reverse.md`](./dota-6.83d-eat-and-cut-tree-reverse.md) |

> **约束**：本文只读分析。未改 `war3hook_ai_tactics.inl` / `war3hook_memhud.cpp` / War3Bot。验证桩见 `War3Launcher/hooker/war3hook_ai_ward_verify.inl`（默认不挂入工程）。JASS 原生仅限 **GamePlaying**。

---

## 0. 结论速览

| # | 结论 | 置信度 |
| :-: | :--- | :---: |
| 1 | 假眼单位 **`o004`（侦察守卫）**，真眼单位 **`oeye`（岗哨守卫）**；物品 `I05G`/`I05H` → 技能 `A2WH`/`A2WI`（`ANcl` DataB1=3） | **高** |
| 2 | 持续：假眼 **7 min**、真眼 **4 min**（`UnitApplyTimedLife`，buff `BTLD`）；插眼脚本 `M6O` | **高** |
| 3 | 假眼 `UnitBalance`：**HP=200**，**sight/nsight=1600**；隐身由脚本 `IA1(unit,'A0XB')`（`Apiv`）永久挂上 | **高** |
| 4 | 真眼：地图无 `oeye` Balance 覆盖 → 继承 1.26 库存 **HP=200 / sight=1600**；技能表 **`Adt1`（`Adet`）Rng1=`850`** 真视；脚本同样加 `A0XB`。提示文本写「视野非常之小」与 SLK 冲突 → **须实机验 FoW** | **中**（真视半径高，视野中） |
| 5 | 粉尘 `I0GH`/`AItb`：Area **1050**、Dur **12s**、CD **60**；宝石真码 `I04D` 技能 **`A14K`（`Adet`）Rng1=`1100`** | **高** |
| 6 | 排眼可见性：优先 **`IsUnitDetected(ward, localPlayer)`**；辅以 `IsUnitInvisible` / `IsUnitVisible`。底层 `CUnit+0x130/+0x134` + 侦测块每玩家 `+0x2C`/`+0x74`（**1.0.17→1.27 全版本同布局**） | **高**（原生+全版 helper）；**中**（字段语义） |
| 7 | 打眼：`0x12` + `0xD000F` 对**已被真视**的眼有效；压制之刃 `A1FD` 对 `o004`/`oeye` 额外 **+100**（`MFO`→`MEO`）。200 HP → **单次 QB 通常不能秒**，需再普攻或第二下 | **高**（脚本）；**中**（总刀数，待实机） |
| 8 | 插眼发包：`0x11` + `useslot` + `(x,y)`，且须带 **物品对象 ID** 与 **flags `0x44`**（见活跃物品文档） | **高**（已有结论） |

---

## 一、插眼

### 1.1 眼单位与物品（原始字段）

#### 物品 → 单位创建（`war3map_3.j` `M6O`）

| 物品 | 技能 | DataB1 | 点地 `0x11` | 单位 `0x12` | 创建单位 | 持续 | 施法距离 (AbilityData `Rng1`) |
| :--- | :--- | :---: | :--- | :--- | :--- | ---: | ---: |
| `I05G` 侦察守卫（假眼） | `A2WH` (`ANcl`) | 3 | 插眼 | 递给友军 1 充能 | **`o004`** | **420 s**（7×60） | **420** |
| `I05H` 岗哨守卫（真眼） | `A2WI` (`ANcl`) | 3 | 插眼 | 递给友军 1 充能 | **`oeye`** | **240 s**（4×60） | **500** |

创建后公共步骤：

1. `UnitApplyTimedLife(u, 'BTLD', duration)`  
2. `IA1(u, 'A0XB')` → `UnitAddAbility` + `UnitMakeAbilityPermanent`（永久隐身，基类 `Apiv`）  
3. 若落在禁区 `R60` → 退回充能并 `RemoveUnit`  
4. 仅真眼：`I41(owner, 12, x, y, 150)` 开 **12 s / 半径 150** 的临时 `FogModifier`（插下闪一下，不是主视野）  
5. `GUO`：对敌方本地玩家挂 `WardMark_T2.mdx` 特效（敌方看不见模型标记用）

> 命名对照：英文 Observer = 假眼 `o004`；Sentry / oeye = 真眼。库存单位名 `oeye` 在 DotA 里是岗哨而非「观察者」。

#### `o004` 地图 `Units\UnitBalance.slk`（摘录）

| 字段 | 值 | 含义 |
| :--- | :--- | :--- |
| `type` | `Ward` | 守卫类 |
| `HP` / `realHP` | **200** / **200** | 生命 |
| `defType` | `medium` | 护甲类型 medium |
| `defUp` | 2 | （库存列） |
| `sight` / `nsight` | **1600** / **1600** | 昼夜视野半径 |
| `UnitAbilities.abilList` | `_`（空） | 真视无；隐身靠脚本 `A0XB` |
| `UnitUI` 模型 | `units\orc\SentryWard\SentryWard` | 与岗哨同模型族 |
| 中文名 | 侦察守卫 | `OrcUnitStrings` |

#### `oeye`（真眼）

| 来源 | 字段 | 值 |
| :--- | :--- | :--- |
| 地图 Balance | （无 `oeye` 行） | 走 War3Patch 库存 |
| 库存 Balance（1.26 系） | HP / sight | **200** / **1600**（与假眼同量级） |
| 地图 `UnitAbilities` | `abilList` | **`A12G,A04R,Adt1,Aeth`** |
| 其中 `Adt1` | `code=Adet`，`Rng1`（X22）= **850**，`targs=vuln,invu` | **真视半径 850** |
| 脚本 | 再加 `A0XB` | 永久隐身 |
| 中文 tip | 「视野非常之小」+ 真视 | 与 SLK sight=1600 **不一致**，实机以 FoW 采样为准 |

`A12G` / `A04R` 基类均为 `Asph`（极短 Dur）；`Aeth` 为库存 `Aeth`。对 AI：**排眼半径按 `Adt1=850`；提供队伍视野仍按假眼逻辑或实机修正。**

#### 隐身 / 真视相关技能对照

| ID | 基类 | 关键数值 | 用途 |
| :--- | :--- | :--- | :--- |
| `A0XB` | `Apiv` | 无时长字段（永久） | 假眼/真眼创建后挂上 |
| `Adt1` | `Adet` | Rng1=**850** | 真眼单位真视 |
| `A14K` | `Adet` | Rng1=**1100** | 真视宝石 `I04D` |
| `Adtg` / `Agyv` | `Atru` / `Agyv` | Rng1=**900** | 库存塔真视 / 宝石旧式；6.83d 宝石改 `A14K` |
| `AItb` | `AItb` | Area1=**1050**，Dur=**12**，CD=**60**，Cost=5，Buff=`Bdet` | 显影之尘 `I0GH` |
| `A1FD` | `Aeat` | Rng=350，CD=5，`targs=tree,ward` | 压制之刃砍树/砍眼 |

物品价格（`ItemData`）：`I05G` gold **150**（2 充能）、真眼行 gold **200**、`I0GH` **180**、`I04D` **900**。

### 1.2 高地视野规则（引擎 + 地图）

承接 [`warcraft-iii-fog-of-war-implementation.md`](./warcraft-iii-fog-of-war-implementation.md) / [`dota-683d-vision-and-fog-juke.md`](./dota-683d-vision-and-fog-juke.md)：

1. **悬崖层级**：视线从低悬崖打向更高悬崖会被挡；高台眼可「俯视」低地，低地单位/眼看不穿高台（引擎 FoW 悬崖遮挡）。  
2. **树木**：`occH`（如 `ATtr`≈230）挡视线；插在树后/树间的眼对侧向更安全，也更难被无真视摸到。  
3. **假眼价值**：1600 半径在**同层或更高**时最大化；河道符点两侧高台、野区入口高台优先于平地。  
4. **真眼价值**：几乎不贡献开阔视野（tip + 实机待证），核心是 **850 真视圈** 盖住常用假眼位 / 封野点。  
5. **可插性**：`war3map.wpm` 通行 + 非建筑碰撞；禁区 `R60` 脚本直接拒插。封野必须落在 camp **check AABB** 内（见 spawn-box 文档）。

地形整理建议（二期自动化，本文不改 hook）：

- 从已提取 `war3map.w3e` 读悬崖层，在符点 / 野区入口采样「相对河面 cliff≥1」的格子作候选高台。  
- 用 `war3map.doo` 树坐标做「树后偏移」微调。  
- 当前眼位库用 **地图 rect 中心 + 封野 spawn 点** 作为可执行种子表（下节）。

### 1.3 眼位库（6.83d 世界坐标）

坐标系与 hook `GetUnitX/Y` 一致。  
**站位**：假眼施法距 **420**，真眼 **500** —— 英雄站在目标点该半径内即可发 `0x11`（再近一点防寻路抖动）。  
**种类**：`O`=假眼 `o004`，`S`=真眼 `oeye`；封野优先 `S`（与 tactics `blockcamp` 一致），没有则 `O`。

| ID | 坐标 (x,y) | 用途 | 种类 | 站位建议 | 来源 / 备注 |
| :--- | :--- | :--- | :---: | :--- | :--- |
| `rune_top` | **-2352, 1648** | 上路河道符点视野 | O | 点 ±350 内高台侧 | `G4` 中心；`F1=GetRectCenter(G4)` |
| `rune_bot` | **2944, -2816** | 下路河道符点视野 | O | 点 ±350 内高台侧 | `LB` 中心 |
| `roshan_pit` | **-2368, 1664** | 肉山坑口 / 附近反隐 | S 主 / O 辅 | 坑外 400–500 | `KB` 中心；与上路符接近，注意别插进禁区 |
| `roshan_high` | **-2176, 2320** | 肉山上方高台窥坑 | O+S | 高台边缘内 400 | `Z6` 中心 |
| `mid_river` | **-368, -656** | 中路河道枢纽 | O | 河岸高台 | `Y5` 中心 |
| `block_1` | **4640, -976** | 封野 #1 | S>O | spawn 点 | camp `H4`；check=`Q4` |
| `block_2` | **-3216, -256** | 封野 #2 | S>O | spawn | `Z4` / `U4` |
| `block_3` | **1584, -3984** | 封野 #3 | S>O | spawn | `V4` / `I5` |
| `block_4` | **-4512, 3408** | 封野 #4 | S>O | spawn | `W4` / `O5` |
| `block_5` | **-3088, 4256** | 封野 #5 | S>O | spawn | `X4` / `A5` |
| `block_6` | **2960, -5008** | 封野 #6 | S>O | spawn | `Y4` / `B5` |
| `block_7` | **-1648, 2352** | 封野 #7（近肉山侧野） | S>O | spawn | `J4` / `C5` |
| `block_8` | **3072, -3712** | 封野 #8 | S>O | spawn | `K4` / `E5` |
| `block_9` | **1232, 3040** | 封野 #9 | S>O | spawn | `L4` / `D5` |
| `block_10` | **-416, -3584** | 封野 #10 | S>O | spawn | `M4` / `F5` |
| `block_11` | **-288, 3456** | 封野 #11 | S>O | spawn | `V5` / `Z5` |
| `block_12` | **-1056, -4592** | 封野 #12 | S>O | spawn | `X5` / `W5` |
| `ent_radiant_jg` | **-3040, -224** | 近卫侧野区入口（check 中心近似） | O | 入口高台 | `U4` 中心 |
| `ent_dire_jg` | **1712, -4480** | 天灾侧野区入口近似 | O | 入口高台 | `I5` 中心 |

> `block_*` 精确几何以 [`dota-neutral-camp-spawn-box.md`](./dota-neutral-camp-spawn-box.md) 的 check/spawn 为准；插点用 **spawn**，判定封野用 **check**。  
> 进攻方「对方野区入口 / 高台」随己方阵营镜像：近卫打天灾用正坐标簇，天灾打近卫用负坐标簇。tactics `wardspots` 落地时按 `GetPlayerTeam` 选子集。

---

## 二、排眼

### 2.1 AI 如何「看见」隐身眼

| 手段 | 半径 / 时长 | 判定链 |
| :--- | :--- | :--- |
| 己方真眼 `oeye` | 真视 **850** | 敌眼进入圈 → `IsUnitDetected(enemyWard, localPlayer)==true`，且通常 `IsUnitVisible` 亦真 |
| 显影之尘 | **1050** / 12s | 对圈内敌隐身上 `Bdet`；同上用 `IsUnitDetected` / `IsUnitVisible` |
| 真视宝石 `I04D` | **1100** 持续（持有者） | 随身 `A14K`；死亡掉落 |
| 塔真视等 | 库存 `Adtg` **900**（若未改） | 同侦测原生 |

**推荐原生组合（仅 GamePlaying）：**

```text
IsUnitInvisible(u, p)  → 单位是否处于隐身状态（对 p）
IsUnitDetected(u, p)   → p 是否侦测到该隐身单位（真视/粉尘等）
IsUnitVisible(u, p)    → p 是否可见（含迷雾+隐身综合，走单位 vtable+0xFC）
IsUnitHidden(u)        → 隐藏标志（CUnit+0x20 bit0），非排眼主路径
```

排眼循环伪码：

1. 枚举敌方 `o004`/`oeye`（`GroupEnum` + `GetUnitTypeId`，或跟踪敌方 `0x11 useslot` 插眼点）。  
2. 若 `IsUnitDetected(w, me) || (IsUnitVisible(w, me) && !IsUnitInvisible(w, me))` → 可攻击。  
3. 仅 `IsUnitInvisible && !IsUnitDetected` → 不可见，走 §2.3 推测。

### 2.2 `game.dll`：侦测标志与多版本 RVA

#### JASS 原生入口 RVA

| 版本 | `IsUnitInvisible` | `IsUnitDetected` | `IsUnitVisible` | `IsUnitHidden` |
| :--- | :---: | :---: | :---: | :---: |
| 1.0.17.5988 | `0x2C6CB0` | `0x2C6B40` | `0x2C60D0` | `0x2C6240` |
| 1.0.20.6048 | `0x2C6CB0` | `0x2C6B40` | `0x2C60D0` | `0x2C6240` |
| 1.20.4.6074 | `0x2C6DD0` | `0x2C6C60` | `0x2C61F0` | `0x2C6360` |
| 1.21.0.6263 | `0x2CA3A0` | `0x2CA230` | `0x2C97C0` | `0x2C9930` |
| 1.22.0.6328 | `0x3C0F60` | `0x3C0F20` | `0x3C0D90` | `0x3C0DD0` |
| 1.23.0.6352 | `0x3C2C80` | `0x3C2C40` | `0x3C2AB0` | `0x3C2AF0` |
| 1.24.1.6374 | `0x3C8740` | `0x3C8700` | `0x3C8570` | `0x3C85B0` |
| 1.24.4.6387 | `0x3C8800` | `0x3C87C0` | `0x3C8630` | `0x3C8670` |
| 1.25.1.6397 | `0x3C7A90` | `0x3C7A50` | `0x3C78C0` | `0x3C7900` |
| **1.26.0.6401** | **`0x3C7CC0`** | **`0x3C7C80`** | **`0x3C7AF0`** | **`0x3C7B30`** |
| **1.27.0.52240** | **`0x1E8AA0`** | **`0x1E8580`** | **`0x1E8E80`** | **`0x1E86C0`** |

（字符串 RVA 与 stub 见 `artifacts/ward-deward/visibility_natives.md`；本表由 `scan_all_vis_natives.py` 从 `BA str / B9 handler` 注册点抽出。）

#### `IsUnitDetected` 内部（全版本同构）

证据：`War3Launcher/versions/*/game.dll`（本仓 11 个版本均已逐字节核对）。产物：`artifacts/ward-deward/isunitdetected_helpers_all.json`。

**核心 helper RVA（全表）**

| 版本 | JASS stub | 核心 helper | 挂接方式 |
| :--- | :---: | :---: | :--- |
| 1.0.17.5988 | `0x2C6B40` | **`0x1BC710`** | stub 末 `push -1; push playerSlot; call`（经 agent 解引用） |
| 1.0.20.6048 | `0x2C6B40` | **`0x1BC710`** | 同 1.0.17 |
| 1.20.4.6074 | `0x2C6C60` | **`0x1BC780`** | 同族 |
| 1.21.0.6263 | `0x2CA230` | **`0x1BF940`** | 同族 |
| 1.22.0.6328 | `0x3C0F20` | **`0x2797E0`** | stub 内第 3 个 `E8` |
| 1.23.0.6352 | `0x3C2C40` | **`0x27AD20`** | 同 1.22 |
| 1.24.1.6374 | `0x3C8700` | **`0x27ADE0`** | 同 1.22 |
| 1.24.4.6387 | `0x3C87C0` | **`0x27AE40`** | 同 1.22 |
| 1.25.1.6397 | `0x3C7A50` | **`0x27A0F0`** | 同 1.22 |
| 1.26.0.6401 | `0x3C7C80` | **`0x27A320`** | 同 1.22 |
| 1.27.0.52240 | `0x1E8580` | **`0x66E3B0`** | stub 第 3 个 `E8`（prologue 多 `push ebp`） |

**字段布局（1.0.17 → 1.27 全部一致）**

| 项 | 内容 | 置信度 |
| :--- | :--- | :---: |
| 调用约定 | `this=CUnit*`，栈：`playerId`，`mask`（JASS 传 `0xFFFFFFFF`）；`ret 8` | 高 |
| 单位前置 | 读 **`CUnit+0x134` AND `CUnit+0x130`**，若 `==-1` → 未侦测 | **高** |
| 侦测块 | `[base+player*4+0x2C]`（mask bit0）与 **`+0x74`**（bit1） | **中高**（语义：两路侦测源） |
| `IsUnitVisible` | 不经该 helper；`vtable[+0xFC](playerId, 0, 4)`（1.22+ stub 形态） | 高 |
| `IsUnitHidden` | `CUnit+0x20 & 1` | 高 |

版本包装差异：1.0.17–1.21 的 JASS stub 先走 agent/句柄解引用再 `call` helper；1.22 起 stub 变短，直接 `mov esi,CUnit*` 后 `call` helper；1.27 原生/helper 整体重基。**内存字段从 1.0.17 到 1.27 未改。**

AI 实现建议：**优先调 JASS 原生**（与迷雾/buff 一致）；内存偏移仅作调试 HUD / 无 JASS 上下文的旁路。

### 2.3 无真视时的推测信号（可观测）

| 信号 | 如何观测 | 权重建议 |
| :--- | :--- | :--- |
| 敌英雄在常用眼位 **进雾前短停 / 转身** | 可见时坐标进眼位半径（如 500），随后 `IsUnitVisible` 变 false | 高 |
| 敌方发出 **`0x11` + useslot** 且物品为眼（或落点在眼位表） | 钩 `EnqueuePlayerAction` / 动作日志；落点记为 `suspectWard` | **最高** |
| 敌辅助 **买眼后** 朝野区/符点移动 | 商店购买 + 路径终点近眼位 | 中高 |
| 己方单位在无视野区 **异常被打** / 兵线视野被「挖空」 | 暴露分数突变（见 fog-juke 文档） | 中 |
| 敌方 **粉尘/宝石** 动向 | 物品使用 / 持有；反向说明对方也在排眼 | 情境 |

输出：`suspectSpots[] = {x,y,score,ttl}`；排眼时优先对该点插真眼或丢粉，而不是全图乱扫。

### 2.4 打掉眼

| 方式 | Action | 条件 | 伤害 / 刀数 |
| :--- | :--- | :--- | :--- |
| 普通攻击 | `0x12` + order `0xD000F` + 眼 `(obj1,obj2)` | 必须 **已被真视/可见** | HP=200，medium 护甲；冰女等需 **约 2–4 下**（待实机按攻击力记） |
| 压制之刃 | `0x12` + `useslot(A1FD)` 点眼 | 同上；`targs` 含 `ward` | 脚本 **+100**（`MFO`）；**单次通常不秒**（200 HP）→ QB + 至少 1 次普攻，或两下技能向砍 |
| 技能清眼 | 视英雄 | 可见 | 任意对地面单位伤害 |

攻击前：`aiSelectHero` → 确认 `IsUnitDetected/Visible` → 再 `aiAttackUnit`。不可见时发包会被引擎丢弃或走无效。

---

## 三、AI 落地方案

### 3.1 插眼时机

| 阶段 | 时机 | 动作 |
| :--- | :--- | :--- |
| 开局 | 出装买到眼后、第一波兵碰撞前后 | 本路 `rune_*` 或安全侧 `block_*`（辅助）；中单可 `mid_river` |
| 周期 | 假眼到期前 **60s** 或每 **6–7 min**（商店假眼刷新） | 续关键位；过期位优先 |
| 买到眼 | 背包出现 `I05G`/`I05H` | 立刻选最高分空位点；真眼优先盖「推测敌眼」或己方高价值 O 位 |
| 封野 | 对线优垫 / 想饿对手野 | `blockcamp`：S 优先，插 **spawn** |
| 推进/烟 | 烟后进野前 | 入口 O + 关键拐角 S |

### 3.2 选点规则（评分）

```text
score = w1*visionValue + w2*objective (rune/roshan/block) + w3*safePath
      - w4*enemyThreat - w5*duplicateOwnWard
visionValue: 高台(+)、树后(+)、覆盖兵线/符点(+)
safePath: 到站位的暴露分数（fog-juke）低则加分
```

同阵营已有眼 **800** 内不重复插假眼；真眼可与假眼叠用以防排。

### 3.3 排眼流程

```text
怀疑点(suspect) 
  → 走到粉尘半径 / 真眼施法距
  → 有 S：0x11 插真眼盖 suspect
    无 S 有粉：0x10 useslot 粉尘
    有宝石：走位让 1100 圈扫过
  → 轮询 IsUnitDetected / IsUnitVisible 于 o004|oeye
  → 可见：0x12 attack；若有 QB 先 useslot 砍再补刀
  → 更新 ward 死亡 / suspect 清除
```

### 3.4 Hook 需新增的命令 / 接口（建议，本会话不改 tactics）

| 命令 / API | 作用 |
| :--- | :--- |
| `ward place o\|s x y` | 选对应物品槽，校验距离与物品 obj，发 `0x11 useslot`（flags/`0x44` 走现有 `aiUseItem*`） |
| `ward block [campId]` | 已有 `blockcamp`；改为插 spawn + 优先 S |
| `wardspots list\|run` | 按评分表执行 `wardspots` 技巧 |
| `deward scan` | 枚举可见/已侦测敌眼，打印 typeId、HP、坐标 |
| `deward attack [handle\|x y]` | 对可见眼 `0x12` 攻击；可选 `qb` 先砍 |
| `deward dust` / `deward sentry x y` | 粉尘 / 指定点插真眼 |
| `aiIsWardDetected(u)` | 封装 `IsUnitDetected(u, GetLocalPlayer())` |
| `aiTrackEnemyWardAction` | 解析敌方眼 `0x11` 写入 suspect 表 |
| 配置 | `config/dota_ward_spots_683d.json`（本文表格机器可读版） |

验证桩（未挂接）：`War3Launcher/hooker/war3hook_ai_ward_verify.inl` —— 仅日志打印单位类型 / `IsUnit*` / 持续剩余，供实机冰女插眼对照。

### 3.5 实机验证清单（冰女 Hjai）

对局中（Scene=GamePlaying）本地：

1. 买假眼 → `ward place o` 到 `mid_river` → 记 `GetUnitTypeId`（期望 `o004`）、`GetUnitState LIFE`（期望 200）、白天视野体感、7 min 是否消失。  
2. 买真眼 → 同法 → 期望 `oeye`；用隐身单位/敌假眼测 **850** 真视边缘。  
3. 真眼照出眼 → 普攻计数打掉；再测 **QB 一下 + 普攻**。  
4. 粉尘 / 宝石半径抽样。  
5. 结果回填本文 §1.1 / §2.4「待实机」行。

---

## 四、相关代码索引

| 位置 | 内容 |
| :--- | :--- |
| `War3Script/war3map_3.j` `M6O` / `MFO` / `MEO` | 插眼创建、QB +100 |
| `War3Script/war3map_2.j` `GUO` / `H3O` / `H1O` | 标记特效、召唤回退 |
| `War3Script/war3map_1.j` `IA1` / `I41` | 永久技能、临时 FogModifier |
| `artifacts/ward-deward/map/Units_*.slk` | 地图对象数值 |
| `artifacts/ward-deward/visibility_natives.md` | 原生 stub 字节 |
| 活跃物品文档 D 类 | `0x11`/`0x12`、flags、物品 obj |

---

## 五、置信度与缺口

| 缺口 | 说明 |
| :--- | :--- |
| 真眼实际 FoW 半径 | tip 与 SLK 冲突；须内存/迷雾采样 |
| 普攻刀数 | 依赖英雄攻击力与护甲结算；冰女实测后填 |
| `CUnit+0x130/+0x134` 位含义 | 与 helper 强相关，未做完整 bit 字典 |
| 高台 cliff 全图栅格 | 未本轮扫完 w3e；眼位表用 rect/spawn 种子 |
| 直播验证 | 依赖另会话未占用的 Launcher；桩文件已备 |
