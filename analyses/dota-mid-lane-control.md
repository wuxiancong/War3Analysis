# DotA 6.83d 中路控线模型与 AI 状态机

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Cursor Auto / Composer |
| **分析目的** | 给中路 AI 可执行的控线：交汇点预测、手段量化、状态机（与补刀/后撤优先级） |
| **命名方式** | `dota-mid-lane-control`；导图 `dota-mid-lane-control-mindmap.md`；回测 `artifacts/lasthit-miss-vision/lane_equilibrium_backtest.json` |
| **分析时间** | 2026-11-21 |
| **验证状态** | 引用既有移速/仇恨/战术文档 + 三局 SF 中路 CSV 质心交汇回测；**精细 HP/护甲逐步仿真未做**（误差偏大，见下） |
| **证据** | [`dota-lane-speed-by-time.md`](./dota-lane-speed-by-time.md)、[`war3-tower-creep-aggro.md`](./war3-tower-creep-aggro.md)、[`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md)、[`war3-lasthit-miss-vision.md`](./war3-lasthit-miss-vision.md)；CSV `records/lasthit/sf/sf_mid_20261121-{172855,225436,231144}_*.csv` |
| **配套思维导图** | [`dota-mid-lane-control-mindmap.md`](./dota-mid-lane-control-mindmap.md) |

---

## 第一段：结论

1. **控线怎么做**：目标把**交汇点**维持在**己方高坡**（中路 cliff≥9）且敌兵距己方一塔 **>700**。手段优先级：只正补最后一下 → 反补残血己方兵 → 必要时拉仇恨（脚本 500/2s）→ 卡兵拖慢己方波 → 推空重置 → 拉野。中路全程移速 325、无边路 ±25% 光环。
2. **模型**：用轴参数 `t∈[0,1]`（近卫中塔 → 天灾中塔）；自然交汇约河 `t≈river`；一侧有效 DPS 更高则 `t` 移向弱势侧基地。三局质心回测 mean `|err|≈0.28–0.33`（轴长度比例）——**只可作方向信号，不能当像素级预瞄**；收紧需读真实兵 HP/护甲。
3. **未实机**：状态机阈值、拉仇恨窗口与卡兵秒数的联调；玩家指令打断已约定接口，未改 hooker。

---

## C.1 兵线平衡模型

### 地标与轴

| 点 | 坐标 | 来源 |
| :--- | :--- | :--- |
| 近卫中一塔 | (-1504, -1824) | [`dota-lane-spawn-waypoints.md`](./dota-lane-spawn-waypoints.md) `GV` |
| 河道 | (-368, -656) | `mid_river` / `Y5` |
| 天灾中一塔 | (1056, -96) | 同文档 `MX` |

```text
t = project(pos, RadiantT1 → DireT1)   // 0=己塔(近卫视角), 1=敌塔
meet ≈ 0.5～river 附近（无干扰）
```

### 输入 → 输出

**输入（每波或 0.5s）**：

- 己方/敌方：存活近战数、远程数、攻城；可加总当前 HP（有内存则用真 HP）
- 英雄是否在补刀窗口 / 是否在推线
- 己方一塔位置（进塔判定 **dist≤700**，见 aggro 文档；勿用 650 当引擎值）

**输出**：

- 下一拍交汇 `t_meet`
- 相对河的偏移：`Δ = t_meet - t_river`（`Δ>0` 表示推向天灾侧）
- 安全标志：`dist(enemy_front, own_T1) > 700` 且 `layerHeight(meet) >= own_plateau`

**简化公式**（`lane_equilibrium.py`）：

```text
t_own_die   = ΣEHP_own  / DPS_enemy
t_enemy_die = ΣEHP_enemy / DPS_own
t_meet      = clamp(t0 + k*(t_own_die - t_enemy_die), 0.05, 0.95)
```

中路无移速光环：两波相向速度同为 325 → `t0` 取河投影即可。英雄多打敌兵 ≈ 提高 `DPS_own` → `t_meet` 增大（近卫视角下 defer 到敌塔，易进己方危险？**注意符号**：近卫为己时，推线过猛 → 交汇靠近敌塔，回线变长、易被 gank；控线要的是交汇偏**己塔一侧高坡**，即近卫要 **略拉慢己方或反补/少推**，使 `t_meet` 略小于河）。

### 仇恨规则（引用）

| 项 | 值 | 文档 |
| :--- | :--- | :--- |
| 兵线转火英雄 | 脚本 CH2：**500** 范围 / **2s** | `war3-tower-creep-aggro.md` |
| 塔射程=索敌 | **700** | 同上 |
| CallForHelp | 600（地图未覆盖） | 同上；兵线电脑兵转火以脚本为准 |

### 回测误差

| 局 | 帧数 | 观测 mean `t_meet` | 计数模型 mean AbsErr |
| :--- | ---: | ---: | ---: |
| 17:28 | （见 json） | ~0.59 | ~0.33 |
| 22:54 | | ~0.63 | ~0.30 |
| 23:11 | | ~0.64 | ~0.28 |

产物：`artifacts/lasthit-miss-vision/lane_equilibrium_backtest.json`。误差大因只用了「可见兵数量」代理 EHP、未建模补刀消耗与走位。**方向**：三局交汇均偏河东（`t>0.5`）→ 影魔局偏推，控线应多反补/少无意义 A 兵。

---

## C.2 手段量化

| 手段 | 效果（量级） | 何时用 | 依据 |
| :--- | :--- | :--- | :--- |
| **只正补最后一下** | 对交汇影响最小；保持平衡 | 默认 | 战术常识 + 评分「补到」 |
| **反补** | 减少己方 DPS/EHP → 交汇回撤向己塔 | 己方兵残且交汇过河/近敌 | 评分反补分；丢失文档：同层反补无高低地惩罚 |
| **拉仇恨** | 兵转火英雄 2s；可把敌兵拉离/拉近 | 敌兵贴身或要拉开交汇 | CH2 500/2s |
| **卡兵** | 中路 325：拖慢己方 `τ` 秒 ≈ 交汇向己塔移 `325·τ/2` 世界单位（两波相对） | 交汇过河或敌兵将进 700 | [`dota-lane-speed-by-time.md`](./dota-lane-speed-by-time.md)（中路无光环）；卡兵细节 [`dota-ai-tactics-library.md`](./dota-ai-tactics-library.md) |
| **推线重置** | 清空波后下一波在河再汇 | 已失控进塔、要回城 | 塔清兵会反推 |
| **拉野** | 推迟回线、减少线上 DPS | 有空窗且线上安全 | 战术库野点 |

卡兵经验量：要让交汇从河东回到近卫高坡，往往只需 **3–5 s** 级微卡（移速文档结论），不是边路那种 15s+。

---

## C.3 AI 状态机

```text
优先级（高→低）：
  0. 玩家指令 / RemoteControl  → 立即停手，清空控线子目标
  1. 低血后撤（aiRetreatDecide）→ 见评分文档阈值
  2. 补刀窗口（正补/反补预计能拿到）→ 允许攻击；受 missChance 站位约束
  3. 控线状态机
  4. 待机 / 对线威胁观察
```

### 状态

| 状态 | 目标区 | 进入 | 退出 | 允许动作 |
| :--- | :--- | :--- | :--- | :--- |
| **HOLD_HIGH** | 己方 cliff≥9 平台，英雄在兵线后排 | 默认；或从危险恢复 | `t_meet` 过大或敌前排距己塔 ≤750 | 只 LH/Deny；禁止无脑 A 兵 |
| **SLOW_WAVE** | 己方兵前方卡位 | `t_meet > t_river + 0.05` 或敌前排逼近 | 交汇回到河己侧 | 卡兵 3–5s；仍可 LH |
| **AGGRO_KITE** | 拉一波走 | 敌近战贴身且非 LH 窗口 | 2s 结束或脱离 500 | 打一下撤出 500+ |
| **RESET_PUSH** | 协助清波进河 | 己塔正在打敌兵或兵线已崩 | 波清空 / 下一波刷出 | 推线；注意进塔 700 |
| **RETREAT** | 塔后 / 兵营向 | 后撤条件 | 血回阈值 | 只走位，不补刀（除已出手） |

### 与丢失/视野

- 控线站位优先己方高坡 → 顺带降低仰打丢失（见 miss 文档）。
- 假眼**不是**控线状态机的必选边；视野靠兵线+塔+可选 `mid_river`。

### 实现提示（不改代码，仅规格）

```text
onTick:
  if playerOverride: stop; return
  if retreat.needed: state=RETREAT; return
  if lasthit.opportunityReady: do LH/Deny (with missChance stand); return
  update t_meet from creeps
  transition HOLD_HIGH / SLOW_WAVE / ...
  execute state action
```

---

## 改动清单（主会话）

1. 读兵 HP 总和进 `predict_meet`，重跑回测目标 AbsErr&lt;0.1。  
2. 状态机挂到 `aiTickRoutine` 补刀之后、逛线之前。  
3. 日志：`t_meet`、state、是否因 missChance 改站位。
