# DotA 6.83d 囤野（stack）时机与守卫 / 回巢逻辑

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 按野点给出「最晚几秒 A 一下、往哪走」；拆清守卫距离 / 刷新区 AABB / 野怪移速；供 AI 按点出手 |
| **命名方式** | `dota-neutral-camp-stack-timing`；导图 `*-mindmap`；短名 `CampStack` / `stackSecond` |
| **分析时间** | 2026-11-21 |
| **样本** | `war3mapMisc.txt`；`Units\MiscGame.txt` / `MiscData.txt`；`UnitBalance.slk` / `UnitWeapons.slk`（1.27 War3Patch）；`versions/*/game.dll`；`war3map_3.j` `P3O`；既有 [`dota-neutral-camp-spawn-box.md`](./dota-neutral-camp-spawn-box.md) / [`dota-ai-neutral-creep-pull.md`](./dota-ai-neutral-creep-pull.md) |
| **工具** | `mpyq` 抽 SLK；`pefile` 扫字符串 / 反汇编入口；几何表见 `artifacts/neutral-stack/stack_timing_calc.json` |
| **配套思维导图** | [`dota-neutral-camp-stack-timing-mindmap.md`](./dota-neutral-camp-stack-timing-mindmap.md) |
| **验证** | Launcher 在线但对局 `running=0`；**本局未用冰女实拉**。验证步骤见第九节 |

---

## 一、核心结论（先看这里）

1. **刷不刷**看脚本封野盒 AABB（已有文档）；**追多远 / 何时回头**看引擎守卫常数。两套几何，不要混。
2. DotA 6.83d `war3mapMisc.txt`：**`GuardDistance = MaxGuardDistance = 600`，`GuardReturnTime = 3`**。软硬拴绳宽度为 0 → 离守卫点 **>600 立刻回巢**（不再等 3 秒）。
3. 回巢途中：**不主动索敌、受击也不报复**（`SetUnitCreepGuard` 开启时的中立策略）；按移速走回守卫点，**不传送**；血量按物编 `regenHP` 回，不是瞬间满血。
4. 守卫点：创建 时写入；字段证据指向 **`CUnit+0x2AC / +0x2B4`（代理 ID 对，与坐标代理同一套）**；开关位在 **`CUnit+0x60` bit `0x04`**（`SetUnitCreepGuard`）。
5. 纯几何「最近边 / 移速」算出最晚约 **:57～:58**；加上绕树、停下来打、英雄自己也要出盒，实测经验 **:50～:53（:51 最佳）**。差异约 **4～7 秒**，见第四节。
6. AI 落地：按野点用第五节表；默认远程 **:51**、近战 **:50**；出盒方向用表内 `prefer_dir`；4 波以上再提前 **2 秒**。

---

## 二、地图 / 游戏常量

### 2.1 DotA 覆盖（权威）

`War3Analysis/artifacts/ability-orders/map/war3mapMisc.txt`（与 web-gameplay 副本一致）：

| 键 | DotA 值 | 原版 MiscGame 默认 | 囤野含义 |
| :--- | ---: | ---: | :--- |
| `GuardDistance` | **600** | 600 | 软拴：离开守卫点这么远后开始「想回家」 |
| `MaxGuardDistance` | **600** | 1000 | 硬拴：超过则**无视是否在挨打**立刻回家 |
| `GuardReturnTime` | **3** | 5 | 仅在「已过软拴、未过硬拴」且 **GuardReturnTime 秒内没挨打** 时回家；DotA 软=硬 → **此路径基本用不上** |

### 2.2 原版 MiscGame / MiscData（对照）

从 `War3Patch.mpq` → `Units\MiscGame.txt`（已落 `artifacts/neutral-stack/`）：

- 注释原文（引擎意图）：过 `GuardDistance` 后开始考虑回家；再花 `GuardReturnTime` 追击且无人打 → 回家；过 `MaxGuardDistance` → 无条件回家。
- `Units\MiscData.txt`：`CreepCampPathingCellDistance=26`（×32 = **832** 世界单位）——**小地图野点图标 / AI 营地聚类半径**，不是封野盒，也不是 600 拴绳。

### 2.3 野怪移速 / 攻击距离 / 索敌（patch `UnitBalance` / `UnitWeapons`）

索敌在 **UnitWeapons `acquire`**（不是 Balance）。常见 6.83d 池子（stock 四字码；自定义 `n0**` 以地图 w3u 为准，下表 spd 暂按 270 估）：

| 四字码 | spd | rangeN1 | acquire | 武器 | 常见营 |
| :--- | ---: | ---: | ---: | :--- | :--- |
| `njg1`/`njga` | 320 | 128 | 500 | 近战 | A 池丛林 |
| `nbdo`/`nbds` | 300/270 | 100 | 500 | 近战 | A 黑龙崽 |
| `nbdk`/`nbwm` | 350/300 | 500 | 500 | 溅射远程 | A |
| `ngst`/`nggr` | 270 | 100/128 | 500 | 近战 | A 石魔 |
| `nogm`/`nomg` | 270 | 100 | 500 | 近战 | D 食人魔 |
| `nfpc`/`nfpu` | 320 | 100 | 500 | 近战 | B 熊怪 |
| `nsth`/`nstl`/`nsat` | 320/270/270 | 100/100/**600** | 500/500/**600** | 萨特远程 600 | B/D |
| `nwlg` | 350 | 90 | 500 | 近战 | D 狼 |
| `nkol`/`nkob`/`nkot` | 270 | 100 | 500 | 近战 | C 狗头人 |
| `nftb`/`nfsh` | 270 | 500/**600** | 500/**600** | 熊怪萨满远程 | C |
| `ncen`/`ncnk` | 350/320 | 100 | 500 | 近战 | B/D 半人马 |
| `ngns` | 270 | 500 | 500 | 远程 | C 豺狼人 |
| `ngh1`/`npfl` | 270/350 | 400/100 | 500 | 幽灵远程 | C |
| `nowe`/`nowb` | 320/300 | 128 | 500 | 近战 | B 猫头鹰熊 |
| `ndtr`/`ndtw` | 270/320 | 500 | 600/500 | 巨魔远程 | B |

**营内最慢单位决定出盒时间**（要整营都出 AABB）。多数池子最慢 **270**；半人马/熊怪偏快 **300～350**。

远程野（`nsat`/`nfsh`/`ndtr`/`ngh1`/`ngns`/`nbwm`…）会边走边停火，**有效追击速度远低于 spd** —— 这是几何算 :58、经验却要 :51 的主因之一。

---

## 三、`game.dll` 守卫 / 回巢（多版本）

### 3.1 机制摘要（与 Misc 注释 + 反汇编一致）

```text
CreateUnit(中立敌对) → 守卫点 = 最终落点；CreepGuard 位打开
被打 / 索敌 → 追击英雄
dist(home) > MaxGuardDistance(=600 in DotA) → 立刻进入回巢 Move
（原版若 Max>Guard：在 (Guard, Max] 内且 GuardReturnTime 秒未挨打 → 回巢）
回巢中：清索敌、不报复；走到 home 附近再 idle
挨打刷新「未受伤计时」——仅软拴区间有意义；DotA 可忽略
```

置信度：**机制高**（Misc 注释 + 社区 + OpenRealm 复刻文档交叉）；**DotA 软=硬 → 3 秒路径基本死** 高。

### 3.2 `SetUnitCreepGuard` → `CUnit+0x60` bit `0x04`

反汇编（两版同逻辑）：

```text
JassHandleToUnit(handle)
if creepGuard:  or  dword [CUnit+0x60], 4
else:           and dword [CUnit+0x60], ~4   ; 0xFFFFFFFB
```

| 版本 | 原生 RVA | 置信度 |
| :--- | :---: | :---: |
| 1.26.0.6401 | `0x3C5480` | **高** |
| 1.27.0.52240 | `0x1F7450` | **高** |
| 1.25.1.6397 | `0x3C5250` | 高 |
| 1.24.4.6387 | `0x3C5FC0` | 高 |
| 1.24.1.6374 | `0x3C5F00` | 高 |
| 1.23.0.6352 | `0x3C0440` | 高 |
| 1.22.0.6328 | `0x3BE720` | 高 |
| 1.21.0.6263 | `0x2C2B80` | 中（外壳不同） |
| 1.20.4.6074 | `0x2BF5B0` | 中 |

与 `RemoveGuardPosition` / `RecycleGuardPosition` / `RemoveAllGuardPositions` **不是同一套**：后三者是电脑 AI 岗哨表，不是中立拴绳。

### 3.3 守卫点字段

| 项 | 结论 | 置信度 |
| :--- | :--- | :---: |
| 写入时机 | 中立敌对 `CreateUnit` 最终落点（`SetUnitPosition` 纠偏后） | 高（脚本行为 + OpenRealm/Warsmash 对齐） |
| 存储 | 使用点附近读 **`[CUnit+0x2AC]` / `[CUnit+0x2B4]`**（像代理 ID 对，再经 `vtable+0xB8` 位置对象比距离） | **中高**（1.26 `MaxGuardDistance` 使用点 `0xCEC1A` 所在函数 `≈0xCEA80`） |
| 开关 | `+0x60 & 4` | 高 |
| 回巢状态位 | 同函数族对 `CUnit+0x20` 置/清多类 flag（含与 `GuardReturnTime` 定时器相关） | 中（未逐 bit 命名） |

1.26 `GuardReturnTime` 使用点 `0xC8B3C`：对 `esi+0x280` 建定时相关对象，常量 `0xD01AE` —— 对应「软拴超时回家」调度；DotA 因 Max=Guard ** practically 不走到**。

### 3.4 字符串 / INI 加载锚点

| 版本 | `GuardDistance` str | 典型 code xref（getter / 使用） |
| :--- | :---: | :--- |
| 1.26 | `0x8B23D8` | getter `0xC4BA3`；use `0xD0EFD` |
| 1.27 | `0x9AE0D8`（file `0x9AD4D8`） | getter `0x47B8A3`；use `0x47F3D6` |
| 1.24.4 | `0x8C4538` | `0xC57D3` / `0xD1B2D` |
| 1.25.1 | `0x8B23D8` | 同 1.26 布局 |

`MaxGuardDistance` / `GuardReturnTime` 紧挨同表。完整扫描：`artifacts/neutral-stack/guard_string_scan.md`。

### 3.5 回巢时是否满血 / 是否无视攻击

| 问题 | 结论 | 置信度 |
| :--- | :--- | :---: |
| 回头瞬间满血？ | **否**。按 `regenHP`（野怪多为 0.5～2 /s）走回过程回血 | 高（物编 + 观察） |
| 回巢中挨打？ | 策略上**不报复、不重新追**；仍可被伤害（非无敌） | 中高 |
| 回巢速度 | 当前 `GetUnitMoveSpeed`（与追击同移速技能） | 高 |
| 回巢路程 | ≤ 约 `MaxGuardDistance`（DotA 600）；耗时 ≈ `600/spd` ≈ **1.7～2.2 s**（270～350） | 高（量级） |

---

## 四、为何经验是 :50～:53，几何却是 :57～:58

对每个野点：`exit = spawn → AABB 最近边`，多数 **80～400**，均 ≤600 拴绳。

| 模型 | 公式要点 | 典型最晚秒 |
| :--- | :--- | :--- |
| 理论乐观 | `connect(0.35) + (exit+32)/270 + 0.4` | **:57.5～:58.8** |
| 实用追击 | ×路径系数 1.5～2.0 + 停火/转向 1.2～2.7s | **:54.5～:57** |
| 真人/AI 安全 | 再留 3～4s：英雄出盒、末只野、绕树、前摇 | **:50～:53**（与经验对齐） |
| 囤 ≥4 波 | 拥堵再 −1.5～2s | **:48～:51**（经验 :49） |

**差异来源（按影响）**

1. 远程野停下来射击（有效追速 << spd）。  
2. 树挡路，折线 > 欧氏距离。  
3. **英雄自己也必须在 xx:00 前出盒**（英雄占盒同样封野）。  
4. 要整营最慢那只出去，不是第一只。  
5. 前摇 / 弹道 / 仇恨传播（`CreepCallForHelp=600`）有几十到几百毫秒。

因此：**不要把理论 :58 写进 AI**；用第五节「AI 推荐秒」。

---

## 五、十二野点出手表（6.83d）

坐标系与封野盒同 [`dota-neutral-camp-spawn-box.md`](./dota-neutral-camp-spawn-box.md)。  
`prefer_dir`：建议拉出方向（世界坐标轴：N=+Y，E=+X）。  
`AI 近战/远程`：已加安全裕度，对齐 :50～:53；`4+` 为多波拥堵。

| # | 盒/出生 | 边距 W/E/S/N | 最近 | 建议方向 | 典型最慢 spd | 理论最晚(近/远) | 实用最晚(近/远) | **AI 近战** | **AI 远程** | **AI 4+波** |
| :-: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | Q4 / H4 (4640,-976) | 736/**320**/432/336 | E320 | **E** | 270 | 57.9/57.7 | 55.9/55.7 | **:51** | **:51** | **:49** |
| 2 | U4 / Z4 (-3216,-256) | **336**/688/512/576 | W336 | **W** | 270 | 57.9/57.7 | 55.8/55.6 | **:51** | **:51** | **:49** |
| 3 | I5 / V4 (1584,-3984) | 528/784/1232/**240** | N240 | **N** | 270～300 | 58.3/58.1 | 56.0/55.8 | **:52** | **:51** | **:50** |
| 4 | O5 / W4 (-4512,3408) | 608/864/**400**/912 | S400 | **S** | 270～300 | 57.8/57.6 | 55.1/54.9 | **:50** | **:50** | **:48** |
| 5 | A5 / X4 (-3088,4256) | **368**/432/448/**608** | W368 | **W**（勿 N：608>600） | 270 | 57.8/57.6 | 55.0/54.8 | **:50** | **:50** | **:48** |
| 6 | B5 / Y4 (2960,-5008) | 688/816/928/**80** | N80 | **N** | 270 | 58.8/58.6 | 57.4/57.2 | **:53** | **:53** | **:51** |
| 7 | C5 / J4 (-1648,2352) | 240/656/**144**/688 | S144 | **S** | 270 | 58.6/58.4 | 56.6/56.4 | **:52** | **:52** | **:50** |
| 8 | E5 / K4 (3072,-3712) | 480/672/1088/**384** | N384 | **N** | 270 | 57.7/57.5 | 55.1/54.9 | **:50** | **:50** | **:48** |
| 9 | D5 / L4 (1232,3040) | 816/**400**/416/608 | E400 | **E**（勿 N：608>600） | 270～300 | 57.8/57.6 | 55.1/54.9 | **:50** | **:50** | **:48** |
| 10 | F5 / M4 (-416,-3584) | 608/608/**224**/832 | S224 | **S**（勿 N：832>600） | 270 | 58.3/58.1 | 56.1/55.9 | **:52** | **:51** | **:50** |
| 11 | Z5 / V5 (-288,3456) | 512/**352**/384/576 | E352 | **E** | 270 | 57.8/57.6 | 55.1/54.9 | **:50** | **:50** | **:48** |
| 12 | W5 / X5 (-1056,-4592) | 288/**288**/752/752 | E/W288 | **E** | 270～300 | 58.2/58.0 | 55.9/55.7 | **:51** | **:51** | **:49** |

> AI 秒 = `floor(实用最晚 − ~3.5s 安全)`，再夹到经验带；营 6 因出盒极短可偏晚。  
> 明细 JSON：`War3Analysis/artifacts/neutral-stack/stack_timing_calc.json`。

### 5.1 撤离点算法（给代码）

```text
spawn = camp.spawn
dir = camp.prefer_dir   # 单位向量
# 拉到盒外 + 余量，且不超过拴绳 600（留 40）
dist = min(edge[dir] + 120, 560)
pullTo = spawn + dir * dist
# 英雄站位：盒外、靠拉出方向、距最近野 ≈ attackRange - 50
```

近战：先走进攻击距离再 A，**出手秒再减 0.5～1**（已含在「AI 近战」列）。  
远程（冰女 range≈600）：站在建议方向盒缘外 A 一下立刻 `move` 向 `pullTo`。

### 5.2 与「统一 :51」对照

| 情况 | 统一 :51 | 按点表 |
| :--- | :--- | :--- |
| 营 6（北缘 80） | 偏早，浪费线上时间 | 可 :53 |
| 营 4/5/8/9/11 | :51 刚好或略紧 | 表给 :50 |
| 有萨特/萨满远程 | :51 可能不够 | 按远程列或再 −1 |
| 已囤 4+ 波 | 常失败 | 用 4+ 列（≈:48～:50） |

---

## 六、「囤上了」判定

刷新在脚本 `P3O`：xx:00（及开局 +30s）对每点 `GroupEnumUnitsInRect(check)` → `P2O` 空才 `CreateUnit`。

### 6.1 推荐（AI 统计成功率）

**A. CreateUnit 钩子（已有管道）**

号角后、owner = 中立敌对（1.26/1.27 = 12）：

- 若 `dist(createXY, camp.spawn) < 400` 且游戏秒的小数部分 ∈ [0, 0.3]（整点窗口）→ 记 `spawnPulse[campId]++`。  
- 同分钟在脉冲前，该营仍有活野且多数在 **check 外** → `stackSuccess`。

**B. 只读原生（必须在 GamePlaying 主线程）**

```text
t = 当前逻辑秒
若 t % 60 ∈ [0.0, 0.25]:
  枚举 check 内单位（或遍历 g_aiUnits 做点在矩形）
  过滤同 POO（死、A0P4、o003…）
  empty = 无占用
  下一 tick 再数 spawn 附近新中立句柄
  empty && newHandles>0 → 囤成功 / 正常刷新
  !empty → 封野或未拉走（失败）
```

**C. 内存辅助（可选）**

- 营内中立 `GetWidgetLife>0` 且坐标出盒；整点后 0.5s 内 spawn 处出现**新** typeId 组。  
- 不要在读图阶段调 JASS（`game.dll+0x2bd982`）。

### 6.2 不要用的

- 只看英雄是否出盒（野可能还在）。  
- 用 600 圆代替 AABB。  
- 用视野 / 战争迷雾（见既有 fog 文档）。

---

## 七、AI 落地建议

1. 配置每点：`stackSecondMelee` / `stackSecondRanged` / `stackSecondStacked` / `pullDir` / `pullTo`（第五节表）。  
2. 状态机沿用 [`dota-ai-neutral-creep-pull.md`](./dota-ai-neutral-creep-pull.md)：`WaitTime → Hit → Drag`；Drag 目标 = `pullTo`。  
3. Hit 后 **150～250ms** 再 move（远程等弹道）。  
4. 成功判定用第六节 A/B，写入 `AiUnit.log`：`🏕 stack camp=# ok=1 t=xx:00`。  
5. 默认值可先全图 :51，再按点覆盖；营 6 特判 :53。  
6. **勿改**本任务约束中的 `war3hook_ai_tactics.inl` / `war3hook_memhud.cpp` / War3Bot；验证代码单独新文件。

### 7.1 默认表（可直接贴 JSON）

```json
{
  "map": "DotA v6.83d",
  "leash": 600,
  "guardReturnTime": 3,
  "camps": [
    {"id":1,"stackMelee":51,"stackRanged":51,"stack4":49,"dir":"E","spawn":[4640,-976]},
    {"id":2,"stackMelee":51,"stackRanged":51,"stack4":49,"dir":"W","spawn":[-3216,-256]},
    {"id":3,"stackMelee":52,"stackRanged":51,"stack4":50,"dir":"N","spawn":[1584,-3984]},
    {"id":4,"stackMelee":50,"stackRanged":50,"stack4":48,"dir":"S","spawn":[-4512,3408]},
    {"id":5,"stackMelee":50,"stackRanged":50,"stack4":48,"dir":"W","spawn":[-3088,4256]},
    {"id":6,"stackMelee":53,"stackRanged":53,"stack4":51,"dir":"N","spawn":[2960,-5008]},
    {"id":7,"stackMelee":52,"stackRanged":52,"stack4":50,"dir":"S","spawn":[-1648,2352]},
    {"id":8,"stackMelee":50,"stackRanged":50,"stack4":48,"dir":"N","spawn":[3072,-3712]},
    {"id":9,"stackMelee":50,"stackRanged":50,"stack4":48,"dir":"E","spawn":[1232,3040]},
    {"id":10,"stackMelee":52,"stackRanged":51,"stack4":50,"dir":"S","spawn":[-416,-3584]},
    {"id":11,"stackMelee":50,"stackRanged":50,"stack4":48,"dir":"E","spawn":[-288,3456]},
    {"id":12,"stackMelee":51,"stackRanged":51,"stack4":49,"dir":"E","spawn":[-1056,-4592]}
  ]
}
```

---

## 八、引擎 RVA 速查

| 符号 / 点 | 1.26.0.6401 | 1.27.0.52240 | 备注 |
| :--- | :---: | :---: | :--- |
| `SetUnitCreepGuard` | `0x3C5480` | `0x1F7450` | `+0x60 |= 4` |
| `RemoveGuardPosition` | `0x3CB820` | `0x1F2CE0` | AI 岗哨，非中立拴绳 |
| `RecycleGuardPosition` | `0x3CB800` | `0x1F2980` | 同上 |
| `RemoveAllGuardPositions` | `0x3CB840` | `0x1F2C80` | 同上 |
| GuardDistance 使用 | `≈0xD0EA0` | `≈0x47F3xx` | INI 键加载后比距离 |
| MaxGuardDistance 使用 | `≈0xCEA80` | `≈0x4760xx` | 读 `+0x2AC/+0x2B4` |
| GuardReturnTime 使用 | `≈0xC8B20` | `≈0x479Cxx` | 软拴定时；DotA 少用 |
| CreepGuard 标志 | `CUnit+0x60 & 4` | 同 | 高置信 |
| 守卫点代理对 | `CUnit+0x2AC/+0x2B4` | 同布局（待实机读确认） | 中高 |

更老版本字符串 RVA 见 `artifacts/neutral-stack/guard_string_scan.md`。

---

## 九、验证计划（冰女 Hjai）

当前：`War3Launcher` RemoteControl `running=0`，**未开局**。开局后建议：

1. `Start-AiGame.ps1 -Hero cm`（或自选冰女），工作目录 `C:\War3Run`。  
2. 对营 1 / 6 / 8 / 10 各囤一次：记录出手秒、野怪全部出盒时刻、xx:00 是否刷出。  
3. 对照第五节；偏差 >1s 则改该点 `path_factor` / 安全裕度。  
4. 验证代码放**新文件**（例如 `hooker/war3hook_ai_stack_probe.inl`），勿动约束中的 tactics/memhud/Bot。  
5. JASS 只在 `GamePlaying` 线程调。

---

## 十、参考锚点

- 封野盒：`dota-neutral-camp-spawn-box.md`；脚本 `P3O`/`POO`  
- 拉野方案：`dota-ai-neutral-creep-pull.md`  
- 常量：`war3mapMisc.txt`；`Units\MiscGame.txt`；`MiscData.txt` `CreepCampPathingCellDistance`  
- 物编：`artifacts/neutral-stack/patch_Units_UnitBalance.slk` / `patch_Units_UnitWeapons.slk`  
- 扫描：`artifacts/neutral-stack/guard_*.md`、`stack_timing_calc.json`  
- 移动字段：`war3-unit-movement-fields.md`（`+0x1EC` 移速等）  
