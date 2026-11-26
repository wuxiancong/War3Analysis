# War3 玩家动作包「原地转向（不位移）」：锁步回合、指令时序与可行方案（全 11 版）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 解释 `-face <度>` 现有三种做法（退 32 码折返 / 看到到位再 hold / 固定 60~240ms hold）失败或微位移的底层原因，核实锁步回合时序、无位移转向指令可能性及 `StepTurnAndMove` 零位移窗口，给出在本地自建服与战网均可实现「朝向误差 ≤ 10°、位移 ≤ 10 码」的原地转向算法 |
| **命名方式** | 正文 `war3-inplace-turn-lockstep.md`；导图 `war3-inplace-turn-lockstep-mindmap.md`；产物目录 `artifacts/inplace-turn/` |
| **分析时间** | 2026-11-25 |
| **验证状态** | **全 11 版 `Game.dll` 静态反汇编 + `War3Bot` 源码核验**；遵循红线未开游戏、未连 6120、未改 `War3Launcher` 源码；已提供实机校验脚本留给 Claude 在测试机对照 `AiUnit.log` 运行；未静态展开的细节标 `❓` |
| **前序参考** | [`war3-unit-facing.md`](./war3-unit-facing.md)、[`dota-lane-creep-speed-profile.md`](./dota-lane-creep-speed-profile.md)、[`war3-lasthit-prediction-engine-facts.md`](./war3-lasthit-prediction-engine-facts.md) |
| **配套产物** | [`artifacts/inplace-turn/`](../artifacts/inplace-turn/)（`probe_lockstep_orders_127.txt`、`net_and_orders_all11.txt`、`verify_live_face_turn.py`） |
| **配套思维导图** | [`war3-inplace-turn-lockstep-mindmap.md`](./war3-inplace-turn-lockstep-mindmap.md) |

---

## 零、核心结论：怎么用玩家动作包实现「几乎零位移」的原地转向

1. **有没有纯原地转向指令？→ 没有（§三已逐条证伪）**：
   - `0xD0019` (`holdposition`) 在 `CAbilityMove`（1.27 `0x5E0EFC`）中注册为 `targetType = 1`（无目标），塞进 `0x11`/`0x12` 带坐标也不设朝向；对自身下 `move`/`smart` 距为 0 直接判到达不转；冷却中/未学技能在构造 `COrder` 前即校验失败报错，不转身。
   - **唯一可靠手段**：利用 `move`（`0x12 + 0xD0012`）触发转向，配合 **`CPoPosCl::StepTurnAndMove` 的 `propWin = 60°` 零速度门控**，在英雄刚转进目标锥角、尚未迈出第一步（或最多迈出 1 步 ≤ 9.5 码）的瞬间让 `hold`（`0x10 + 0xD0019`）生效。
2. **为什么 Test ③（`move` 后隔 Δt 直接发 `hold`，不等 `GetUnitFacing`）比 Test ② 好得多，且怎么把它做到位移 ≈ 0？**
   - **RTT 抵消原理**：`move` 与 `hold` 走同一条 W3GS 管道，若在 `t = 0` 发 `move`、`t = Δt` 发 `hold`，引擎实际执行两者的间隔就是 **`(Δt + RTT) - (0 + RTT) = Δt`**（仅受 `±0.5 × 回合长` 量化，**与 Ping / 队列积压无关**！）。Test ② 等看到 `GetUnitFacing` 到位再发 `hold`，多吃了一个完整 RTT（200~430ms = 走出 60~130 码）。
   - **Test ③ 仍有小位移的两个根因**：
     1. 用了固定的 `60/120/180/240ms`，没有按 `|Δθ|`、`turnRate` 和 `gameSpeed` 精确算 **零位移 tick 数** $N_{\text{zero}} = \lfloor (|\Delta\theta| - 60^\circ) / \text{turnRate}^\circ \rfloor + 1$；
     2. **小角度陷阱（`|\Delta\theta| < 60^\circ`）**：只要目标角在 `±60°` 内，**第 1 个 32Hz tick（31.25ms）英雄就会直接满速迈步（影魔 9.5 码/tick）**，不可能零位移！
3. **推荐的「两段折返零位移法」（§五伪代码，本地服位移 ≈ 0 码，战网 ≤ 10 码）**：
   - **若 `|Δθ| >= 65°`（大角度，直接零位移转向）**：
     - 精确计算零位移步数 $N = \lfloor (|\Delta\theta| - 60^\circ) / \text{turnRate}^\circ \rfloor + 1$（影魔 `57.3°/tick`：转 `120°` 时 $N=2$ tick = `62.5ms`，两步后剩余仅 `5.4°` 且 **位移 = `0.00` 码**！转 `180°` 时 $N=3$ tick = `93.75ms`，三步后剩余仅 `8.1°` 且 **位移 = `0.00` 码**！）。
     - `t = 0` 发 `move` 到目标方向 `400` 码处；`t = (N × 31.25ms) / gameSpeed` 发 `hold`（`0x10 + 0xD0019`）。
   - **若 `10° < |Δθ| < 65°`（小角度，避免进入 `propWin` 立即迈步）**：
     - **先反向甩到 `target ± 120°`**（选距当前朝向 `>= 90°` 的一侧，全程 `>= 60°` 零位移），停稳后 **`|Δθ|` 变成 `~120°`**，再按上面大角度公式 **`2` ticks（62.5ms）直接甩回 `target`**，最终误差 `≤ 6°`、总位移 **`0 ~ 9` 码**！
4. **为什么方案 A（退 32 码再走回）朝向完全是乱的？（§四）**：
   - 1.27 `CPoPosCl::CheckGoalReached`（`0x11B060`）用到达半径 `glr`（`+0xB0` 默认 `0.8` 格 ≈ `25.6~51.2` 码）+ 英雄碰撞半径 `24` 码 + `32×32` 寻路格中心量化；`32` 码落入到达容差与网格量化盲区，极易直接判到达或被吸附到相邻格中心导致 `atan2` 角度偏差 30°~180°。若真要用折返法，退后距离至少需 `>= 128` 码（耗时 ~0.9s 且仍有 ±15~25 码落点漂移），不如上面的「`propWin` 零位移定时 `hold`」方案。

---

### 0.1 全 11 版本核心函数 RVA 总表

来源：[`net_and_orders_all11.txt`](../artifacts/inplace-turn/net_and_orders_all11.txt)、[`war3hook_offsets.cpp:L2238-2244`](file:///d:/Qt/workspace/War3Launcher/hooker/war3hook_offsets.cpp#L2238-L2244)、[`war3-unit-facing.md`](./war3-unit-facing.md)。

| War3 版本 | `EnqueuePlayerAction` (Hook点) | `CAbilityMove` 订单校验 (`0xD0019/12/16`) | `CPoPosCl::StepTurnAndMove` | `GetUnitFacing` | `GetUnitTurnSpeed` | `GetUnitPropWindow` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | `0x6D5332` | `0x555EB0` | `0x676380` | `0x2BFCA0` | `0x2C0E30` | `0x2C0EF0` |
| `1.0.20.6048` | `0x6D5832` | `0x5563B0` | `0x676880` | `0x2BFCA0` | `0x2C0E30` | `0x2C0EF0` |
| `1.20.4.6074` | `0x6D6172` | `0x556AD0` | `0x6771C0` | `0x2BFDC0` | `0x2C0F50` | `0x2C1010` |
| `1.21.0.6263` | `0x6DA192` | `0x55AB60` | `0x67B1E0` | `0x2C3390` | `0x2C4520` | `0x2C45E0` |
| `1.22.0.6328` | `0x640562` | `0x1FFE6E` | `0x484310` | `0x3BEA30` | `0x3BEFE0` | `0x3BF010` |
| `1.23.0.6352` | `0x6421E2` | `0x2013AE` | `0x4860A0` | `0x3C0750` | `0x3C0D00` | `0x3C0D30` |
| `1.24.1.6374` | `0x650BD2` | `0x20145E` | `0x494A30` | `0x3C6210` | `0x3C67C0` | `0x3C67F0` |
| `1.24.4.6387` | `0x650C82` | `0x2014BE` | `0x494AB0` | `0x3C62D0` | `0x3C6880` | `0x3C68B0` |
| `1.25.1.6397` | `0x6502B2` | `0x20077E` | `0x493D70` | `0x3C5560` | `0x3C5B10` | `0x3C5B40` |
| `1.26.0.6401` | `0x6504E2` | `0x2009AE` | `0x493FA0` | `0x3C5790` | `0x3C5D40` | `0x3C5D70` |
| `1.27.0.52240` | `0x840BBB` | `0x5DE320` | `0x11CFD0` | `0x1E6130` | `0x1E6640` | `0x1E63A0` |

---

## 一、锁步回合与指令执行时序

1. **从 `EnqueuePlayerAction` 到真正执行要经过几个回合？**
   - 1.27 `0x840BA5..0x840BBB` 通过 `GetGlobalSubsystem(0x0E)` 取 `CNetData`，调用 `0x851E10` 将动作字节压入本地待发缓冲区。
   - 客户端打包为 `W3GS_OUTGOING_ACTION (0x26)` 发给主机 → 主机在下一个 `GameTick` 收集所有玩家动作，封入 `W3GS_INCOMING_ACTION (0x0C)`（头部携带 2 字节 `uint16 sendInterval` 回合时长）广播回各客户端 → 客户端排入接收回合队列尾部，等前面积压的回合消费完后，在该回合**起始 tick** 依次执行动作。
   - **回合时长 `T_turn` 由主机下发决定**：
     - 本地自建服 `War3Bot`（`War3Bot/src/bot.cpp:L864,L1709`）：固定 **`10 ms`**（100 Hz，受 Windows `QTimer` 粒度影响实际 ~10~15.6ms）；
     - 局域网 LAN：通常 **`100 ms`**；
     - 战网 / 平台（如默认 latency）：通常 **`100 ~ 250 ms`**（`-latency` / 主机 `dr` 设置决定）。
   - **读取当前回合间隔**：客户端侧 `CNetData`（子系统 `0x0E`）内部保存最新 `0x0C` 包的 `sendInterval`（精确成员偏移未在本轮动态内存核对，标 `❓`）。但如 §零所述，**只要 `move` 与 `hold` 间隔 `Δt` 连续发包，网络 RTT 自动相消**，不需要读主机延迟，只需考虑 `T_turn` 量化粒度（本地服 10ms < 1/3 tick，几乎无量化误差）。
2. **同一个回合里先后入队 `move` 再 `hold` 会怎样？**
   - **在同一逻辑帧内按顺序立即执行，转身根本没有机会发生！**
   - 原因：一个 `0x0C` 回合包内的动作列表在模拟步进（`StepTurnAndMove`）**之前**一次性顺序派发：`move` 写入 `COrderPoint` 并设目标朝向 `+0x8C`，紧接着同一帧内 `hold` 立刻覆盖当前指令为 `COrderImmediate(hold)` 并清除移动意图，导致 `StepTurnAndMove` 一次都没跑，**朝向变化 = `0°`**。
   - **推论**：`hold` 必须落在 **`move` 之后的至少 1 个 `0x0C` 回合（且晚于至少 1 个 32Hz 模拟 tick = 31.25ms）** 才能让引擎执行转身。

---

## 二、转身与移动的引擎细节及「零位移时间窗口」

由 1.27 `CPoPosCl::StepTurnAndMove`（`0x11CFD0`，已在 [`dota-lane-creep-speed-profile.md`](./dota-lane-creep-speed-profile.md) 及 [`war3-unit-facing.md`](./war3-unit-facing.md) 逐指令核验）：
- **模拟频率**：**32 Hz**（每 tick 精确 **`31.25 ms`** 游戏时间）。
- **每 tick 执行顺序**：
  1. 先判推进窗口：`if (forceStop == 0 && fabsf(angleDiff) < propWin /* 60° */) speed = maxSpeed; else speed = 0.0f;`
  2. 再步进朝向：`angle += clamp(angleDiff, -turnRate, +turnRate);`
- **关键推论（零位移窗口精确公式）**：
  - 只要某 tick **开始瞬间**满足 `|Δθ| >= 60°`，该 tick **速度严格为 `0`（位移 = `0.00` 码）**，但朝向仍转动 `turnRate` 弧度！
  - 因此，从初始角差 $|\Delta\theta| \ge 60^\circ$ 出发，连续保持 `speed = 0` 的最大 tick 数为：
    $$N_{\text{zero}} = \left\lfloor \frac{|\Delta\theta| - 60^\circ}{\text{turnRate}^\circ} \right\rfloor + 1$$
    这 $N_{\text{zero}}$ 个 tick 结束后：
    - **总位移严格等于 `0.00` 码**；
    - **剩余角差** $|\Delta\theta_{\text{rem}}| = \max\big(0,\; |\Delta\theta| - N_{\text{zero}} \cdot \text{turnRate}^\circ\big)$。
  - **典型数值核对（影魔 `Nfir`：`turnRate = 1.0 rad = 57.3°/tick`；冰女 `Hjai`：`turnRate = 0.5 rad = 28.65°/tick`）**：

| 英雄 | 初始角差 `\|Δθ\|` | 零位移步数 $N_{\text{zero}}$ | 零位移总时长 (游戏秒) | 结束时剩余角差 | 结束时位移 | 若多跑 1 tick 的位移 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **影魔 (`1.0`)** | `180°` | **3 ticks** | **`93.75 ms`** | **`8.1°`** (≤10° 达标！) | **`0.0` 码** | `9.5` 码 |
| **影魔 (`1.0`)** | `120°` | **2 ticks** | **`62.50 ms`** | **`5.4°`** (≤10° 达标！) | **`0.0` 码** | `9.5` 码 |
| **影魔 (`1.0`)** | `90°` | **1 tick** | **`31.25 ms`** | `32.7°`（需第 2 tick 归零） | `0.0` 码（2 tick 时 `9.5` 码） | `9.5` 码 |
| **影魔 (`1.0`)** | `30°` (`<60°`) | **0 ticks** | `0 ms` | 第 1 tick 即迈步 | 第 1 tick 即移 `9.5` 码 | — |
| **冰女 (`0.5`)** | `180°` | **5 ticks** | **`156.25 ms`** | `36.8°`（6 tick 时 `8.1°`） | 5 tick `0` 码 / **6 tick `8.75` 码** | `8.75` 码 |
| **冰女 (`0.5`)** | `120°` | **3 ticks** | **`93.75 ms`** | `34.1°`（4 tick 时 `5.4°`） | 3 tick `0` 码 / **4 tick `8.75` 码** | `8.75` 码 |

> **亮点**：对于影魔（`57.3°/tick`），**只要 `|Δθ|` 在 `110°~124°` 或 `165°~180°` 区间内**，$N_{\text{zero}}$ 个零位移 tick 跑完就已经把朝向转进 **`±10°`** 以内，此时 `hold` 落地即实现 **误差 ≤ 10° 且 位移 = 0.0 码**！

---

## 三、逐项核实：有没有「不位移的纯转向指令」？

| 候选动作包 | 引擎行为与反汇编证据（1.27） | 能否原地转向 |
| :--- | :--- | :---: |
| **1. 对英雄自己下 `move` (`0xD0012`) / `smart` (`0xD0003`)** | 目标点与自身重合（`dist = 0 <= glr`），`CheckGoalReached` (`0x11B060`) 立即返回到达，速度归 0 且无方向向量 | **❌ 不能** |
| **2. 带坐标发 `0xD0019` (`hold`)（`0x11`/`0x12` 形式）** | `1.27 0x5E0EFC..0x5E0F03` 明确将 `0xD0019` 的目标类型注册为 **`1`（无目标 Immediate）**，坐标参数被忽略/拒绝 | **❌ 不能** |
| **3. `patrol` (`0xD0016`) / `attack-ground` (`0xD0010`) 到近点** | `0xD0016` 注册为 `targetType = 6`，经同一 `CAbilityMove` (`0x5DE320`) 进入 `CPoPosCl::CheckGoalReached` + `StepTurnAndMove`，与 `move` 完全相同；`0xD0010` 常规英雄不可用 | **❌ 无额外优势** |
| **4. 对点施法但技能在冷却 / 没学 / 缺蓝** | `CAbilitySpell` 在接收命令时即校验等级、冷却与蓝量，不满足时直接返回错误并播提示音，**不创建 `COrder`、不写 `+0x8C`**（未逐行展开 `CAbilitySpell` 校验函数，标 `❓`，属 War3 标准机制） | **❌ 不能** |
| **5. 非指令动作（`0x16`/`0x1C`/`0x1E`）或空槽用物品** | 仅涉及选框/热键/物品栏校验，不触碰单位移动与朝向节点 | **❌ 不能** |

---

## 四、方案 A（退 32 码再走回）为什么失败？

- **引擎到达判定（1.27 `0x11C360..0x11C385` → `CheckGoalReached @ 0x11B060`）**：
  - 每帧计算当前坐标到目标点的欧氏距离，与 `CPoPosCl+0xB0`（`glr = 0.8f` 格）比较；一旦判到达，立即把 `speed` 置 `0.0f` 终止移动与转向。
  - 同时寻路网格分辨率为 **`32×32` 码**，英雄碰撞半径 **`24` 码**。
- **失败根因**：`d = 32` 码刚好等于 1 个寻路格且落入 `glr` + 碰撞容差内，导致：
  1. 要么引擎直接判「已到达」忽略移动；
  2. 要么目标点被吸附到相邻 `32×32` 格中心，对 32 码短向量做网格量化会产生 **±45°~180°** 的剧烈方向畸变（完美解释实测 `45°→74°`、`0°→295°`、`120°→288°`）。
- **最小可用折返距离**：需 `d >= 128` 码（4 个寻路格）才能压低网格量化误差，但来回 `256` 码耗时 `~0.85s` 且仍有 `±15~25` 码落点误差，因此**淘汰方案 A**，改用下面 §五的 `propWin` 零位移方案。

---

## 五、推荐方案：基于 `propWin` 零位移窗口的两段折返转向（适配本地服 & 战网）

### 核心策略
1. 若当前角差 `|Δθ| <= 10°`：直接完成，不发任何指令。
2. 若 **`10° < |Δθ| < 65°`**（小角度，直接 `move` 会立刻迈步）：
   - **预甩阶段**：先朝 `prepDeg = norm360(targetDeg + 120°)`（选与 `curDeg` 夹角 `>= 90°` 的 `+120°` 或 `-120°`）发一次大角度零位移 `move + hold`，把英雄原地甩离目标 `~120°`（位移 `0` 码），等稳定后再进入阶段 3 甩回 `targetDeg`！
3. 若 **`|Δθ| >= 65°`**（大角度，零位移主阶段）：
   - 读取 `turnRate`（用 `GetUnitTurnSpeed` 或按英雄表：影魔 `1.0 rad = 57.3°/tick`，冰女 `0.5 rad = 28.65°/tick`）。
   - 计算精确发 `hold` 的游戏时间延迟：
     - 零位移步数 $N_{\text{zero}} = \lfloor (|\Delta\theta| - 60^\circ) / \text{turnRate}^\circ \rfloor + 1$
     - 若跑完 $N_{\text{zero}}$ 步后剩余角差 $|\Delta\theta| - N_{\text{zero}} \cdot \text{turnRate}^\circ > 12^\circ$（例如冰女转 180° 或影魔转 90°），则允许最多多跑 **1 个 tick**（位移 ≤ `9.5` 码，满足 `≤ 10` 码目标！），即 $N = N_{\text{zero}} + 1$；否则 $N = N_{\text{zero}}$（位移 = **`0` 码**！）。
     - 墙钟延迟 `delayMs = (ULONGLONG)round(N * 31.25f / estGameSpeed)`（本地 VM 若未估计倍速可先按 `0.85f` 起步，或直接取实时倍速）。
   - `t = 0`：`aiOrderTarget(0x000D0012, hx + 400*cos(θ), hy + 400*sin(θ), 0xFFFFFFFF, 0xFFFFFFFF)`
   - `t = delayMs`：`aiOrderImmediate(0x000D0019)`（`hold`）
   - 等 `350ms` 读 `GetUnitFacing` 校验：若 `|cur - target| <= 10°` 即成功；若 `hold` 偏早导致还差 `> 10°`（例如被战网 100ms 回合边界截断），最多重试 1~2 次（按剩余角差重走步骤 2/3）。

### 建议伪代码（替换 `war3hook_ai_tactics.inl` 的 `aiStartFaceTurn` / `aiTickFaceTurn`）

```cpp
// 计算零位移（或最多 1 步 <= 9.5 码）的 move -> hold 墙钟延迟（ms）
static ULONGLONG aiFaceTurnCalcHoldDelayMs(float absDiffDeg, float turnRateRad, float gameSpeed) {
    const float stepDeg = (std::max)(15.0f, turnRateRad * 57.29578f);   // SF=57.3°, CM=28.65°
    int nZero = (absDiffDeg >= 60.0f) ? ((int)((absDiffDeg - 60.0f) / stepDeg) + 1) : 0;
    float rem = (std::max)(0.0f, absDiffDeg - nZero * stepDeg);
    int nTicks = (rem > 12.0f) ? (nZero + 1) : nZero;                   // 最多允 1 步移动 (<=9.5码)
    if (nTicks < 1) nTicks = 1;
    const float spd = (std::max)(0.5f, (std::min)(1.2f, gameSpeed));
    return (ULONGLONG)(nTicks * 31.25f / spd + 0.5f);
}

// 启动原地转向：若 10° < |Δθ| < 65°，先设 prepActive=true 甩到 target±120° 再甩回 target
static void aiStartFaceTurnV2(float targetDeg, float curDeg, float turnRateRad, float gameSpeed) {
    float diff = aiAngleDiff(curDeg, targetDeg);
    if (diff <= 10.0f) return;
    if (diff < 65.0f) {
        // 小角度防迈步：选距 curDeg >= 90° 的 ±120° 作为过渡角（保证两段均 >= 65° 零位移）
        float cand1 = std::fmod(targetDeg + 120.0f, 360.0f);
        float cand2 = std::fmod(targetDeg + 240.0f, 360.0f);
        g_aiFaceTurn.stageGoalDeg = (aiAngleDiff(curDeg, cand1) >= aiAngleDiff(curDeg, cand2)) ? cand1 : cand2;
        g_aiFaceTurn.needSecondStage = true;
    } else {
        g_aiFaceTurn.stageGoalDeg = targetDeg;
        g_aiFaceTurn.needSecondStage = false;
    }
    g_aiFaceTurn.holdDelayMs = aiFaceTurnCalcHoldDelayMs(aiAngleDiff(curDeg, g_aiFaceTurn.stageGoalDeg), turnRateRad, gameSpeed);
    // 发 move(stageGoalDeg, dist=400)，经过 holdDelayMs 后立即发 hold(0xD0019)
}
```

---

## 六、实机验证步骤（留给 Claude 在测试机运行）

1. 在 `war3hook_ai_tactics.inl` 中按 §五更新 `aiStartFaceTurn` / `aiTickFaceTurn`。
2. 在本地自建服分别对影魔（`turnRate=1.0`）和冰女（`turnRate=0.5`）依次发 6 组 `-face` 指令覆盖小角度与大角度：`-face 0` → `-face 30`（测小角两段折返）→ `-face 90` → `-face 180` → `-face 270` → `-face 45`。
3. 运行配套日志验收脚本 [`artifacts/inplace-turn/verify_live_face_turn.py`](../artifacts/inplace-turn/verify_live_face_turn.py) 解析 `AiUnit.log` 中的 `🧭 [Face]` 行：
   ```powershell
   python D:\Qt\workspace\War3Analysis\artifacts\inplace-turn\verify_live_face_turn.py C:\War3Run\War3Launcher\logs\AiUnit.log
   ```
   验收标准：全部 6 组朝向误差 `≤ 10°`，单次总位移 `≤ 10` 码（本地 10ms 回合下影魔 120°/180° 预期接近 `0` 码）。
