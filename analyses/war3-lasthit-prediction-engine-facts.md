# War3 补刀预测引擎事实核对与实测验证

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 逐项核对影魔中路 AI 补刀预测（`War3Launcher/hooker/war3hook_ai.cpp`）依赖的 War3 引擎攻击结构、弹道结算、伤害公式与 W3GS 联机延迟，并用 7 份 SF 实测 CSV 量化验证「打早了」与「低掉血却高预估」的根因 |
| **命名方式** | 正文 `war3-lasthit-prediction-engine-facts.md`；导图 `war3-lasthit-prediction-engine-facts-mindmap.md`；产物目录 `artifacts/lasthit-prediction/` |
| **分析时间** | 2026-11-24 |
| **验证状态** | **静态全 11 版 `Game.dll` 反汇编 + DotA 6.83d SLK/`war3mapMisc.txt` 核验 + `War3Bot` 源码核验 + 7 份 SF 实测 CSV 只读回算**；遵循红线未启动游戏、未连 6120、未改 `War3Launcher` 源码；无直接证据项标 `❓` |
| **配套产物** | [`artifacts/lasthit-prediction/`](../artifacts/lasthit-prediction/)（`all11_summary.txt`、`dmg_table_and_cattack_all11.txt`、`sf_csv_validation.txt`、`probe_attack_127*.txt`、`parse_dota_slk.py`、`analyze_sf_csv.py`、`records/`） |
| **配套思维导图** | [`war3-lasthit-prediction-engine-facts-mindmap.md`](./war3-lasthit-prediction-engine-facts-mindmap.md) |

---

## 零、核心结论：哪些输入是对的、哪些错了、建议 Claude 怎么改

### 0.1 逐项核对总表

| 模块 | 当前 `war3hook_ai.cpp` 做法 | 核对结论 | 实测影响量级 |
| :--- | :--- | :---: | :--- |
| **`CAbilityAttack` 字段偏移与攻速钳位** | `+0x6C/+0x70`, `+0x88..+0xAC`, `+0xF4`, `+0x158`, `+0x16C`, `+0x1B0`, `+0x1C0`, `+0x1D8/+0x1EC/+0x200`, `+0x2B8`；`mult = clamp(ias + min(slow,0), 0.2, 5.0)` | **✅ 全部正确** | 与 1.27 反汇编 100% 一致 |
| **`aiDamageTypeMult` 7×8 表与护甲减伤** | 7×8 倍率表（注称转储自 `1.27 +0xBEC368`）；正护甲 `0.06*a/(1+0.06*a)` | **✅ 全部正确** | 56 项与 6.83d `war3mapMisc.txt` 逐项一致；`0xBEC368` 确为 `0xBEC328 + 0x40` |
| **`CMissile` 到达扣血时机** | 到达即扣血，无额外帧延迟 | **✅ 正确** | `vt+0xBC` (`1.27 0x6B2450`) 当帧调 `ApplyDamage` 并立即销毁 |
| **影魔弹道起点偏移 `launchY`** | 直接用 `centerDist / 1200` 算飞行时间，**未减 `launchY`** | **❌ 系统性高估** | 6.83d `Nfir` `launchY = 100` → 每次高估 `100/1200 = 0.083s`；加上目标命中半径，7 局 99 刀实测中位高估 **`0.105` 游戏秒**，直接导致 **52%（22/42）** 早刀在 `≤0.15gs` 边缘抢输 |
| **一塔弹道速度** | `war3hook_ai.cpp:L1157` 硬编码防御塔 `missileSpeed = 1200` | **❌ 严重偏快 60%** | 6.83d `UnitFunc.txt` 实值：天辉一塔 `e00R` = **`750`**（arc `0.10`），夜魇一塔 `u00M` = **`750`**（arc `0.15`）。700 码塔攻实际飞 `0.93s` 而非 `0.58s`（差 `0.35s`） |
| **近战小兵「当前目标 `+0x6C`」判定** | `L1361 / L1442` 对 `dist <= 135` 的近战兵，只要 `+0x6C` 指向目标且未进 cd，就按 `firstHit = windup + 0.08f` 注入后续周期伤害 | **❌ 假攻击者注入** | `+0x6C/+0x70` 在 **索敌 / 下令追击瞬间**（`0x480E49`）即写入，而非开始挥刀。被卡位、转身、走近中的近战兵全被当成「0.51s 后必砍一刀」，直接造成 **「实际掉血 3~4/s 却预估 1.2s 掉 >100 血」**（占早刀 **26%，11/42**） |
| **`+0x1D8` 移动中每 0.50s 重置** | 代码注释记录了现象，未区分「真攻击冷却」与「移动重试轮询」 | **⚠ 机制已查明** | `0x47E610` 在单位移动/够不着目标时调 `SetAttackCooldown(0.50f, startWindup=0)`，借用 `+0x1D8` 当 0.50s 索敌重试计时器；此时 `+0x1EC`（前摇）与 `+0x200`（后摇）均为 0 |
| **W3GS 联机延迟 vs 游戏速度** | 按固定或慢滑动墙钟延迟估算发令提前量 | **⚠ 强依赖客户端倍速** | `War3Bot` 以墙钟 `10ms` 定时广播 `0x0C` 且 **`0x27` 无同步上限背压**；实测 7 局游戏运行速度在 **`0.57x ~ 1.00x`** 波动，降速时客户端接收队列堆积空 turn，延迟放大且墙钟≠游戏秒 |

### 0.2 建议 Claude 的修改方案（只列建议，未改动源码）

1. **修正远程弹道飞行距离（最高优先，立竿见影消掉 ~105ms 系统早偏）**
   - 在 `war3hook_ai.cpp` 计算影魔（及其他远程单位）弹道飞行时间时，不能用 `centerDist / missileSpeed`，应改为：
     ```cpp
     // 影魔 Nfir: launchY = 100（单位朝向发射点前移）；远程兵 edry: launchY = 60；再扣目标碰撞半径 ~24（小兵约 16~32）
     float effDist = std::max(0.0f, centerDist - launchY - targetHitRadius);
     float flightGameSec = effDist / missileSpeed;
     ```
   - 7 局 99 刀实测：仅扣 `launchY = 100`，飞行误差中位数即从 **`-0.105s` 收敛到 `-0.022s`**（均值 `+0.008s`）；若再扣 `~24` 碰撞半径，中位数趋近 `0.000s`。
2. **修正防御塔弹道速度（`war3hook_ai.cpp:L1157`）**
   - 将硬编码 `1200.0f` 改为 DotA 6.83d 一塔真实弹道速度 **`750.0f`**（或按单位 typeId 查表：`e00R`/`u00M` → `750.0f`，攻城车 `ebal`/`umtw` → `1100.0f`，远程兵 `edry`/`unec` → `900.0f`，影魔 `Nfir` → `1200.0f`）。
3. **收紧 `aiPredictDamageByAttackers` / `aiSimulateCreepWindow` 中近战小兵的「真正在打」门槛（`L1361`、`L1442`）**
   - 不要把 `windupLeft <= 0.005f && !inAttackCd && dist <= 135.0f` 的近战兵直接按 `firstHit = windup + 0.08f` 全额计入未来 2.2s 连击：
     - 区分**已开火 / 刚打完**（`windupLeft > 0.005f` 或 `backswingLeft > 0.005f` 或 `cdLeft > 0.505f`——注意避开移动重试的 `<= 0.50f`）与**仅锁定目标**（`+0x6C` 指向目标但三个计时器都处于 idle / `<= 0.50f` 重试态）；
     - 对仅锁定目标的近战兵，要么要求更严格距离（如 `dist <= 105` 且朝向夹角小、近 0.3s 位移极小），要么把首击时间加上保守的走位/转身缓冲（`+0.35s ~ +0.50s`），或直接降权，避免出现「前 1s 实测掉血 `-0.4/s`（自然回血），模拟器却在 1.2s 内灌进 100+ 假伤害」。
4. **统一时间基准为「游戏秒」并动态跟踪 `gameSpeed`**
   - 7 局实测游戏倍速在 `0.57x ~ 1.00x` 间变化（51 兵基线局仅 `0.68x`）。用英雄 `wu`（或 `cd`）在连续 trace 帧的递减量 `Δwu / Δwall_t` 可在线估计实时 `gameSpeed`。
   - 所有引擎内时间（前摇 `windup`、冷却 `cd`、飞行时间 `effDist / speed`）都是**游戏秒**；而联机发令延迟 `netLeadWallSec` 是**墙钟秒**，二者合并时应换算为同一口径（`totalLeadGameSec = netLeadWallSec * gameSpeed + windup + flightGameSec`），防止低倍速局把墙钟延迟当游戏秒多算 30%~40%。

---

## 一、攻击结构字段核对（`CAbilityAttack`）

### 1.1 1.27 静态反汇编逐字段验证

基于 `1.27.0.52240` `CAbilityAttack` 虚表 `0x9ADDBC`、构造函数 `0x474820` 及其攻击状态机函数（反汇编完整证据见 [`probe_attack_127.txt`](../artifacts/lasthit-prediction/probe_attack_127.txt)、[`probe_attack_127_detail.txt`](../artifacts/lasthit-prediction/probe_attack_127_detail.txt)）：

| 偏移 | 类型 / 步长 | `aiReadAttackInfo` 读法 | 引擎真实语义与反汇编证据（1.27） | 核对 |
| :--- | :--- | :--- | :--- | :---: |
| `+0x6C` / `+0x70` | `uint32[2]` | 当前目标句柄/标签 | 构造初始化为 `0xFFFFFFFF`；在 **`0x480E49`** 目标获取/攻击指令绑定函数内**立即写入**，此时单位可能尚在寻路、转身或被卡位，**不代表已挥刀** | **✅ 偏移对；⚠ 语义≠正在打** |
| `+0x84/+0x90/+0x9C` | `uint32` | — | 武器槽数组计数（默认 `2`，对应武器 0 / 武器 1） | ✅ |
| `+0x88` | `int32[2]` (`+i*4`) | `dice` 骰子数 | 武器 `i` 伤害骰子数（`dice1` / `dice2`） | ✅ |
| `+0x94` | `int32[2]` (`+i*4`) | `sides` 骰子面数 | 武器 `i` 单骰面数（`sides1` / `sides2`） | ✅ |
| `+0xA0` | `int32[2]` (`+i*4`) | `base` 基础伤害 | 武器 `i` 基础攻击力（含主属性白字加成） | ✅ |
| `+0xAC` | `int32[2]` (`+i*4`) | `bonus` 绿字加成 | 武器 `i` 附加攻击力（绿字） | ✅ |
| `+0xF4` | `int32[2]` (`+i*4`) | `attackType` 攻击类型 | 武器 `i` 攻击类型枚举（`0=Spells, 1=Normal, 2=Pierce, 3=Siege, 4=Magic, 5=Chaos, 6=Hero`） | ✅ |
| `+0x158` | `float[2]` (`+i*8`) | `bat` 基础攻击间隔 | 步长 `8` 字节，已于 `0x47B1B9` 确认按武器索引 `i*8` 读取 `cool1`/`cool2` | ✅ |
| `+0x16C` | `float[2]` (`+i*0x10`) | `dmgpt` 原始前摇 | 步长 `0x10` 字节，已于 `0x47FA81`（`shl esi, 4`）确认读取 `dmgpt1`/`dmgpt2` | ✅ |
| `+0x1B0` | `float` | `ias` 攻速倍率 | 默认 `1.0f`，受敏捷/攻速装备加成（`+100 IAS = +1.0f`） | ✅ |
| `+0x1C0` | `float` | `slow` 负攻速修正 | 减速类负面攻速修正（仅当 `< 0` 时叠入） | ✅ |
| `+0x1D8` | `CAgentTimer` | `cdLeft` 攻击冷却计时器 | 计时器结构（与 `+0x1EC`/`+0x200` 同为 `0x14` 字节 `CAgentTimer`）；**兼作移动重试轮询定时器（见 1.2）** | **✅ 偏移对；⚠ 双重用途** |
| `+0x1EC` | `CAgentTimer` | `windupLeft` 前摇计时器 | 挥刀前摇倒计时，归零瞬间触发出伤/发弹道 | ✅ |
| `+0x200` | `CAgentTimer` | `backswingLeft` 后摇计时器 | 攻击后摇倒计时，可被移动/停攻打断 | ✅ |
| `+0x2B8` | `int32` | `wIdx` 当前武器索引 | `0` 或 `1`，决定从上述各数组读哪一套武器参数 | ✅ |

**攻速倍率公式核对（1.27 `0x47AF9B..0x47B052`）**：
- 反汇编明确计算 `mult = *(float*)(atk + 0x1B0) + (slow < 0.0f ? slow : 0.0f)`，随后分别与常量 `[0x6FBE7A08]`（`0.2f`，即 `-80%` 下限）和 `[0x6FBE7A04]`（`5.0f`，即 `+400%` 上限）钳位。
- 与 `war3hook_ai.cpp:L1116-1117` 完全一致。

### 1.2 为什么 `+0x1D8` 在移动状态下每 `0.50s` 重置？

在 1.27 反汇编中查明了 `+0x1D8` 的全部写入路径（`SetAttackCooldown(float dur, int startWindup)` @ `0x47FA00`）：
1. **正常挥刀开始**（`0x47CE56`）：调用 `SetAttackCooldown(BAT / mult, startWindup = 1)`，同时启动 `+0x1D8`（总冷却 `BAT / mult`）与 `+0x1EC`（前摇 `dmgpt / mult`）。若前摇途中被打断，`0x47A75A` 会取消该计时器。
2. **移动 / 追击 / 暂不可攻击状态**（`0x47E610`）：当单位持有攻击目标但当前无法挥刀（正在走路、追击、被卡位）时，引擎调用 `SetAttackCooldown([0x6FB593EC] = 0.50f, startWindup = 0)`，将 `+0x1D8` 抬升至 `0.50s` 作为**重试轮询定时器**（事件 ID `0x000D01B0`），到期后再重新检查能否挥刀；此时 `+0x1EC`（前摇）与 `+0x200`（后摇）保持 `0`。
3. **初次索敌 / 切换目标**（`0x480F0B`）：类似地写入 `[0x6FB593BC] = 0.10f` 作为短暂启动检查间隔。

> **工程含义**：`cdLeft > 0` 且 `cdLeft <= 0.50f` 且 `windupLeft == 0 && backswingLeft == 0` 的单位，**极可能处于移动/卡位重试态，而不是刚打完一刀在等冷却**。

### 1.3 为什么「掉血 3~4/s 却预计 1.2s 掉 >100 血」？

两条引擎事实叠加 `war3hook_ai.cpp` 的过滤逻辑直接制造了假伤害：
1. **引擎侧**：`+0x6C/+0x70` 在 `0x480E49` **索敌 / 下令攻击那一刻就写入目标**，此时近战小兵可能还在 100~135 码外绕路、卡在同伴身后或正在转身，根本还没开始挥刀。
2. **AI 代码侧**（`war3hook_ai.cpp:L1361` & `L1442`）：
   ```cpp
   if (a.windupLeft <= 0.005f && !inAttackCd && (a.missileSpeed > 1.0f || dist > 135.0f))
       continue;
   ```
   对远程兵（`missileSpeed > 1`）过滤掉了未挥刀状态，但对 **近战兵（`missileSpeed == 0`）只要 `dist <= 135.0f` 就放行**！接着 `L1379 / L1459` 直接赋值 `firstHit = a.windup + 0.08f`（约 `0.51s`），并在 2.2s 窗口内按 `cd`（`1.0s`）循环叠加伤害。只要有 2~3 只卡位/游走的近战兵锁定了该兵，模拟器就会在 1.2s 内凭空多算 3~5 刀（60~110+ 伤害）。

### 1.4 全 11 版本 `CAbilityAttack` RVA 与偏移核验表

来源：`artifacts/lasthit-prediction/all11_summary.txt`、`dmg_table_and_cattack_all11.txt`。

| War3 版本 | `CAbilityAttack` 虚表 RVA | 构造函数 RVA | 构造内成员偏移核验（`+0x6C/+0x70/+0x84..+0x200/+0x2B8`） |
| :--- | :--- | :--- | :--- |
| `1.0.17.5988` | `0x78D6B8` | `0x555020` | 构造写虚表与 `+0x2B8`；其余成员由基类/子初始化函数清零（偏移布局未改） |
| `1.0.20.6048` | `0x78E6C0` | `0x555520` | 同上 |
| `1.20.4.6074` | `0x78E6C0` | `0x555C40` | 同上 |
| `1.21.0.6263` | `0x78F6F8` | `0x559CD0` | 同上 |
| `1.22.0.6328` | `0x8A1414` | `0x0CD810` | 构造直接命中 11/13 关键偏移：`+0x6C/+0x70/+0x84/+0x90/+0x9C/+0x158/+0x1B0/+0x1C0/+0x1D8/+0x1EC/+0x200` |
| `1.23.0.6352` | `0x8B5554` | `0x0CED50` | 同上（11/13 全部一致） |
| `1.24.1.6374` | `0x8C468C` | `0x0CEE00` | 同上（11/13 全部一致） |
| `1.24.4.6387` | `0x8C468C` | `0x0CEE10` | 同上（11/13 全部一致） |
| `1.25.1.6397` | `0x8B252C` | `0x0CE1E0` | 同上（11/13 全部一致） |
| `1.26.0.6401` | `0x8B252C` | `0x0CE1E0` | 同上（11/13 全部一致） |
| `1.27.0.52240` | `0x9ADDBC` | `0x474820` | 构造及成员函数已全量核验（全部 13 项偏移 100% 一致） |

---

## 二、弹道结算时机、发射点偏移与 DotA 6.83d 实值

### 2.1 `CMissile` 何时结算伤害？

反汇编 `1.27.0.52240` `CMissile` 虚表 `0x9B07D0` 的 `vt+0xBC`（`OnImpact` @ `0x6B2450`，见 `all11_summary.txt` L333-354）：
```asm
6F6B2457: call 6F6B4AA0            ; 获取目标 CUnit*
6F6B245C: test eax, eax
6F6B245E: je   6F6B2471
6F6B2460: push 6FBB81D8h           ; 1.0f 伤害倍率
6F6B2465: push eax                 ; target
6F6B2466: lea  eax, [ebp-4]
6F6B2469: mov  ecx, esi            ; this (CMissile*)
6F6B246B: push eax
6F6B246C: call 6F6B1500            ; ApplyDamage -> 当帧立即扣血（内部含 ShouldMiss）
6F6B2471: mov  eax, [esi]
6F6B2473: mov  ecx, esi
6F6B2475: call dword ptr [eax+0A8h]; vt+0xA8 (0x6B35B0) 当帧立即销毁弹道
```
**结论**：`CMissile` 在**到达目标的同一逻辑帧内立即扣血并销毁**，不存在「下一帧再扣血」的额外帧延迟。

### 2.2 发射点偏移（`launchX/Y/Z`）与目标命中半径对飞行距离的影响

- **起点**：War3 创建弹道时，起点不是攻击者中心 `(x0, y0)`，而是沿单位朝向 `facing` 偏移 `(launchX, launchY)`（其中 `launchY` 为沿面朝方向的前移距离，`launchX` 为左右偏移，`launchZ` 为发射高度）。对影魔 `Nfir`，`launchY = 100`，等价于弹道一出手就领先中心点 **100 码**。
- **弧度 `arc`**：War3 追踪弹道按 2D 水平速度 `missileSpeed` 推进，抛物线弧度 `arc` 仅抬高视觉 Z 轴高度，不延长水平飞行时间（7 局 CSV 实测飞行时间已直接印证：按 2D 直线距离 `(centerDist - 100) / 1200` 误差中位数仅 `-0.022s`）。
- **终点**：残余 `-0.022s`（`0.022 * 1200 ≈ 26 码`）与小兵碰撞半径（16~32 码）吻合；`CMissile` 步进判定到达的精确碰撞半径扣减系数未在 1.27 `vt+0xB4` 内展开到最底层几何函数，标 `❓`（实测等效扣减约 `24~26` 码）。

### 2.3 前摇结束 → 扣血公式（游戏秒）

- **近战单位**（含近战小兵 `ugho` / 树人近战兵）：
  $$T_{\text{windup\_end}\to\text{hp\_drop}} = 0\text{ 游戏秒}$$
  前摇计时器 `+0x1EC` 归零当帧即调用出伤，无飞行时间。
- **远程单位**（影魔、远程兵、攻城车、防御塔）：
  $$T_{\text{windup\_end}\to\text{hp\_drop}} = \frac{\max\big(0,\; D_{\text{center}} - \text{launchY} - R_{\text{hit}}\big)}{V_{\text{missile}}}\text{ 游戏秒}$$
  其中影魔 `launchY = 100, V = 1200, R_{\text{hit}} \approx 24`（仅扣 `launchY=100` 已可把中位误差从 `-105ms` 压到 `-22ms`）。

### 2.4 DotA 6.83d 关键单位弹道与攻防参数实值（SLK / `UnitFunc.txt` 核对）

数据源：`artifacts/ward-deward/map/` 下 6.83d 地图解包 `Units_UnitWeapons.slk`、`Units_UnitData.slk`、`UnitFunc.txt`（提取脚本 [`parse_dota_slk.py`](../artifacts/lasthit-prediction/parse_dota_slk.py)）：

| 单位 | 6.83d TypeId | 弹道速度 `spd` | 弧度 `arc` | 发射偏移 `(launchX, Y, Z)` | BAT / 前摇 `dmgpt` | 射程 | 攻击类型 | 护甲类型 (`+0xE4`) | `war3hook_ai.cpp` 现值核对 |
| :--- | :--- | ---: | ---: | :--- | :--- | ---: | :--- | :--- | :--- |
| **影魔 (SF)** | `Nfir` | **1200** | 0.08 | **(-12, 100, 130)** | 1.70 / 0.50 | 500 | Hero (`6`) | Hero (`5`) | 速度对，**漏扣 `launchY=100`** |
| **天辉远程兵** | `edry` | **900** | 0.15 | (0, 60, 60) | 1.00 / 0.40 | 500 | Pierce (`2`) | Unarmored (`7`) | 速度对，漏扣 `launchY=60` |
| **夜魇远程兵** | `unec` | **900** | 0.00 | (0, 60, 60) | 1.00 / 0.40 | 500 | Pierce (`2`)※ | Unarmored (`7`) | 速度对（注：基础 SLK 为 magic，6.83d `war3map.w3u` 改为 pierce，待实机 `+0xF4` 复核 `❓`） |
| **天辉攻城车** | `ebal` | **1100** | 0.05 | (0, 0, 90) | 2.70 / 0.70 | 690 | Siege (`3`) | Fortified (`3`) | `L1157` 未单列攻城车 |
| **夜魇攻城车** | `umtw` | **1100** | 0.30 | (0, 0, 90) | 2.70 / 0.70 | 690 | Siege (`3`) | Fortified (`3`) | 同上 |
| **天辉中路一塔** | `e00R` | **750** | 0.10 | (0, 0, 180) | 1.00 / 0.60 | 700 | Siege (`3`) | Fortified (`3`) | **❌ 硬编码 1200，偏快 60%** |
| **夜魇中路一塔** | `u00M` | **750** | 0.15 | (0, 0, 180) | 1.00 / 0.60 | 700 | Siege (`3`) | Fortified (`3`) | **❌ 硬编码 1200，偏快 60%** |
| **近战小兵** | `ugho` / `efon` | 0 (近战) | — | — | 1.00 / 0.467 | 100 | Normal (`1`) | Unarmored (`7`) | 正常 |

### 2.5 全 11 版本 `CMissile` 虚表及 `OnImpact` / `Destroy` RVA 表

来源：`artifacts/lasthit-prediction/all11_summary.txt`（与 `war3hook_ai.cpp:L1180-1191` `kAiMissileVerTable` 交叉验证）：

| War3 版本 | `CMissile` 虚表 RVA | `vt+0xA8` (`Destroy`) RVA | `vt+0xBC` (`OnImpact`) RVA |
| :--- | :--- | :--- | :--- |
| `1.0.17.5988` | `0x7A57E4` | `0x46FDB0` | `0x4726F0` |
| `1.0.20.6048` | `0x7A67FC` | `0x470340` | `0x470390` |
| `1.20.4.6074` | `0x7A67FC` | `0x4708B0` | `0x470900` |
| `1.21.0.6263` | `0x7A785C` | `0x474880` | `0x4748D0` |
| `1.22.0.6328` | `0x8AA6B8` | `0x001AD0` | `0x0DDA20` |
| `1.23.0.6352` | `0x8BE7E0` | `0x052EE0` | `0x001E10` |
| `1.24.1.6374` | `0x8CD8E8` | `0x4726C0` | `0x02F210` |
| `1.24.4.6387` | `0x8CD8E8` | `0x472740` | `0x02F1F0` |
| `1.25.1.6397` | `0x8BB738` | `0x02F6B0` | `0x0D32A0` |
| `1.26.0.6401` | `0x8BB738` | `0x02F6B0` | `0x0D32A0` |
| `1.27.0.52240` | `0x9B07D0` | `0x6B35B0` | `0x6B2450` |

---

## 三、伤害公式、护甲减伤与 7×8 倍率表核对

### 3.1 伤害骰子公式

War3 攻击掷骰遵循标准 `base + bonus + sum_{k=1}^{dice} rand(1, sides)`：
- **最小伤害**：$D_{\min} = \text{base} + \text{bonus} + \text{dice}$
- **最大伤害**：$D_{\max} = \text{base} + \text{bonus} + \text{dice} \times \text{sides}$
- **期望平均伤害**：$D_{\text{avg}} = \text{base} + \text{bonus} + \text{dice} \times \frac{\text{sides} + 1}{2}$

与 `war3hook_ai.cpp:L1135` 一致。补刀保守斩杀线应使用 $D_{\min}$（确保不会因摇出低骰残血 1~5 HP 漏刀），而模拟小兵集火掉血使用 $D_{\text{avg}}$ 合理。

### 3.2 护甲减伤公式（1.27 `0x64FBFC..0x64FC58` 反汇编验证）

在 `1.27.0.52240` `DefenseArmor` 引用函数（`0x64FBFC`）中反汇编确认：
- **正护甲（$A \ge 0$）**：读取 `DefenseArmor`（DotA 6.83d = `0.06`），计算
  $$R(A) = \frac{0.06 A}{1 + 0.06 A},\qquad \text{伤害倍率} = 1 - R(A) = \frac{1}{1 + 0.06 A}$$
- **负护甲（$A < 0$）**：分支 `0x64FC4F` 计算增伤 $1 - 0.94^{-A}$（在 `war3hook_ai.cpp` 护甲换算中同样覆盖）。

### 3.3 `aiDamageTypeMult` 7×8 攻防倍率表与 6.83d `war3mapMisc.txt` 逐项核对

逐项比对 `war3hook_ai.cpp:L1287-1295` 与 6.83d 解包 `war3mapMisc.txt` 的 7 行 × 8 列（共 56 个浮点数）：
- **56 / 56 项 100% 完全一致**（含小兵 Unarmored `col 7`：Normal `1.00`、Pierce `1.50`、Siege `1.50`、Hero `1.00`；以及塔 Fortified `col 3`：Normal `0.70`、Pierce `0.35`、Siege `1.50`、Hero `0.50`）。
- **1.27 表基址 `0xBEC368` 来源证实**：在 1.27 加载函数 `0x64D810..0x64D83B` 中，`lea esi, [edi+40h]` 后执行 `mov [esi+6FBEC328h], eax`，因此 `Row 0 (DamageBonusSpells)` 实际落在 `0xBEC328 + 0x40 = 0xBEC368`，每行步长 `0x20`（8 个 float），`war3hook_ai.cpp` 注释完全准确。

### 3.4 全 11 版本 `DamageBonus` 7×8 表与 `DefenseArmor` 函数 RVA 表

来源：`artifacts/lasthit-prediction/dmg_table_and_cattack_all11.txt`、`find_dmg_table_exact.py`：

| War3 版本 | `DamageBonusSpells` 加载器 / 辅助函数 RVA | 7×8 浮点表基址 RVA（Row 0 Spells） | `DefenseArmor` 减伤函数字符串引用 RVA |
| :--- | :--- | :--- | :--- |
| `1.0.17.5988` | `0x19F2F3`（内联加载循环） | `0x86F348` | `0x19F24D` |
| `1.0.20.6048` | `0x19F2F3`（内联加载循环） | `0x870388` | `0x19F24D` |
| `1.20.4.6074` | `0x19F303`（内联加载循环） | `0x8703A8` | `0x19F25D` |
| `1.21.0.6263` | `0x1A24C3`（内联加载循环） | `0x871420` | `0x1A241D` |
| `1.22.0.6328` | `0x26C4D0`（`GetDamageBonusSpells` 辅助函数） | —※ | `0x26C432` |
| `1.23.0.6352` | `0x26DA10`（`GetDamageBonusSpells` 辅助函数） | —※ | `0x26D972` |
| `1.24.1.6374` | `0x26DAC0`（`GetDamageBonusSpells` 辅助函数） | —※ | `0x26DA22` |
| `1.24.4.6387` | `0x26DB20`（`GetDamageBonusSpells` 辅助函数） | —※ | `0x26DA82` |
| `1.25.1.6397` | `0x26CDE0`（`GetDamageBonusSpells` 辅助函数） | —※ | `0x26CD42` |
| `1.26.0.6401` | `0x26D010`（`GetDamageBonusSpells` 辅助函数） | —※ | `0x26CF72` |
| `1.27.0.52240` | `0x64D826`（内联加载循环） | `0xBEC368`（`0xBEC328 + 0x40`） | `0x64FC0B` |

> ※ 1.22~1.26 编译形态为 7 个独立小辅助函数（每行一个，按需通过 `0x009EE0` 查询全局常量表），静态未展开成 1.20/1.27 式单循环直写固定 `.bss` 数组，故表基址栏标注 `—` 并给出辅助函数入口 RVA。

### 3.5 高地丢失（`ChanceToMiss`）

直接引用已完成的专项分析 [`war3-lasthit-miss-vision.md`](./war3-lasthit-miss-vision.md)：
- 仅在 **弹道伤害结算**（`CMissile` → `ShouldMiss`）瞬间判定，且仅当目标地形采样高度**严格高于**攻击者时，进入 `ChanceToMiss = 0.25` 掷点；触发后为半伤（`× MissDamageReduction = 0.5`）并飘 `MISS`，并非 0 伤害。
- 中路同层（均为河道 cliff 8 或均为高台 cliff 9）丢失率为 `0`；AI 应尽量站同层或高打低，而非在坡下仰打。

---

## 四、联机指令延迟（`War3Bot` W3GS 锁步机制分析）

核查 `D:\Qt\workspace\War3Bot` 源码（`include/client.h`、`src/bot.cpp`、`src/client.cpp`）：

1. **Turn 步长固定为 `10 ms`（100 Hz）**：
   - `client.h:L1044` 默认 `m_gameTickInterval = 10`；
   - `bot.cpp:L864` 与 `L1709` 建房时显式调用 `client->setGameTickInterval(10)`；
   - `client.cpp:L126` 驱动 `m_gameTickTimer->setInterval(10)`，每次触发 `onGameTick()`（`L2896`）打包 `m_actionQueue` 并广播 `W3GS_INCOMING_ACTION (0x0C)`（`sendInterval = 10 ms`）。
2. **指令发出到主机广播的耗时**：
   - 客户端发 `W3GS_OUTGOING_ACTION (0x26)` → `client.cpp:L1972` 入队 `m_actionQueue` → 等待下一次 `onGameTick()`（`0 ~ 10 ms`，受 Windows 默认 `QTimer` 精度影响通常 `0 ~ 15.6 ms`）立即随下个 `0x0C` 广播回客户端。
   - 也就是说，**主机侧转发延迟只有 1 个 turn（约 10~16 ms）**。
3. **关键发现：延迟为什么会达到 `0.20s ~ 0.43s` 且强依赖游戏速度？**
   - 核查 `W3GS_OUTGOING_KEEPALIVE (0x27)` 处理函数（`client.cpp:L2007-2048`）：**`War3Bot` 只更新 `lastResponseTime` 和反作弊校验和，完全没有实现经典 Ghost++ 的 `SyncLimit` 背压暂停机制！**
   - `onGameTick()` 严格按 **墙钟时间** 每 `10~15.6 ms` 发出一个 `sendInterval = 10 ms` 的 turn 包，不管客户端有没有消费完。
   - 在 7 份 SF 实测 CSV 中，从前摇 `wu` 递减率测得客户端实际运行速度仅为 **`0.57x ~ 1.00x`**（51 兵基线局为 `0.68x`）。当客户端以 `0.68x` 跑游戏时，主机每墙钟 1 秒塞进来 `~1000 ms` 游戏时间的 turn，客户端只能消化 `680 ms`，多出的空 turn 全部堆积在 War3 客户端的 W3GS 接收队列里（直到客户端内置缓冲上限）。
   - 此时 AI 发出的攻击指令被主机打包后排在客户端 turn 队列的**最尾部**，必须等前面积压的几十个空 turn 全部跑完才会被引擎执行！
   - **结论**：发令到执行的延迟 **不是纯固定值加抖动，而是与客户端实际游戏倍速强相关**（主机 1 turn 约 10~16ms + 客户端积压 turn 队列深度 × 10ms；客户端跑满 1.0x 时延迟最小，降速至 0.6x~0.7x 时延迟明显拉长且波动加剧）。`Game.dll` 客户端侧 W3GS 队列上限具体字段未单独反汇编，标 `❓`。

---

## 五、用 7 份 SF 实测 CSV 量化验证模型

从 `C:\War3Run\War3Launcher\records\lasthit\sf\*.csv` 只读复制到 [`artifacts/lasthit-prediction/records/`](../artifacts/lasthit-prediction/records/)（共 7 局），使用 [`analyze_sf_csv.py`](../artifacts/lasthit-prediction/analyze_sf_csv.py) 回算（完整输出见 [`sf_csv_validation.txt`](../artifacts/lasthit-prediction/sf_csv_validation.txt)）：

### 5.1 飞行时间误差验证（7 局合计 `n = 99` 次有效命中补刀）

为消除不同对局游戏降速的影响，先按每局英雄前摇 `wu` 连续递减斜率估算该局 `est_game_speed`，再将实测飞行时间换算为**游戏秒**与公式对比：

| 对局 CSV | 估算游戏倍速 | 命中样本 `n` | 旧公式 `dist/1200` 中位误差 | 新公式 `(dist-100)/1200` 中位误差 |
| :--- | ---: | ---: | ---: | ---: |
| `005331_lh35of51`（基线局） | `0.68x` | 37 | `-0.107s` | **`-0.023s`** |
| `010824_lh4of8` | `0.91x` | 7 | `-0.138s` | **`-0.055s`** |
| `011354_lh10of19` | `0.91x` | 17 | `-0.114s` | **`-0.031s`** |
| `012158_lh9of12` | `0.83x` | 14 | `-0.097s` | **`-0.014s`** |
| `013015_lh4of9` | `0.91x` | 8 | `-0.109s` | **`-0.026s`** |
| `013614_lh4of12` | `0.57x` | 6 | `-0.114s` | **`-0.030s`** |
| `014247_lh8of12` | `1.00x` | 10 | `-0.088s` | **`-0.005s`** |
| **全 7 局汇总** | **`0.57x~1.00x`** | **99** | **median `-0.105s` / mean `-0.075s`** | **median `-0.022s` / mean `+0.008s`** |

- **结论极其干净**：在 **全部 7 局、所有倍速下**，旧公式稳定高估飞行时间 `~0.105` 游戏秒；扣除 6.83d SLK 核出的影魔 `launchY = 100` 后，误差中位数直接归敛到 `-0.022s`（残余 22ms ≈ 26 码目标碰撞半径）。

### 5.2 「早了」漏刀的归因拆解（全 7 局共 `42` 次 `early` 漏刀）

| 归因类别 | 样本数 / 占比 | 实测特征 | 对应引擎/代码根因 |
| :--- | ---: | :--- | :--- |
| **1. 擦边早到 / 抢输**（落地比死亡早 `≤ 0.15gs`） | **22 / 42 (52%)** | 落地剩 4~50 血（0.04x~0.96x 英雄伤害），差 0.02~0.15 游戏秒被小兵抢走 | **影魔漏扣 `launchY=100` + 碰撞半径** 导致系统性早出手 ~0.105gs，叠加 `gameSpeed` 波动 |
| **2. 低掉血高预估**（落地前 1s 实测掉血 `< 25 HP/s`） | **11 / 42 (26%)** | 典型样本：落地血 90（`1.71x` 伤，前 1s 实测 `-0.4/s`）、落地血 135（`2.15x` 伤，前 1s `-0.4/s`）、落地血 107（`1.15x` 伤，前 1s `-0.2/s`） | **`+0x6C` 索敌即写入 + `L1361/L1442` 放行 `dist<=135` 未挥刀近战兵**，向窗口注入假连击 |
| **3. 大幅早到且高 DPS**（`> 0.15gs` 且前 1s 掉血 `>= 25/s`） | **9 / 42 (21%)** | 落地剩 10~185 血，小兵集火中途转火或塔攻弹道速度高估（1200 vs 750） | **一塔弹道硬编码 1200** + 集火小兵中途死亡/转火（模拟器假设目标不变） |

> 两组最主要的误差来源（飞行距离漏扣 `launchY=100` 占 52%，假近战攻击者注入占 26%）合计直接解释了 **78%** 的早刀样本。
