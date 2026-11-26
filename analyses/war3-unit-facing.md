# War3 英雄朝向：读取、单位换算、转身速度与转向指令（全 11 版）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 为囤野 `-mark pos` 记录并还原英雄朝向提供完整引擎依据：核实全 11 版 `GetUnitFacing` 实现、角度约定与 `180/π` 乘数来源、`+0x8C/+0x90` 关系、6.83d 影魔/冰女转身速度、玩家动作包转向方案、攻击前转身时序及 hook 接入建议 |
| **命名方式** | 正文 `war3-unit-facing.md`；导图 `war3-unit-facing-mindmap.md`；产物目录 `artifacts/unit-facing/` |
| **分析时间** | 2026-11-25 |
| **验证状态** | **全 11 版 `Game.dll` 静态反汇编 + DotA 6.83d / `War3Patch.mpq` SLK 核验**；遵循红线未开游戏、未连 6120、未改 `War3Launcher` 源码；已提供实机测试脚本留给测试机运行；无直接静态证据项标 `❓` |
| **前序参考** | [`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md)、[`dota-lane-creep-speed-profile.md`](./dota-lane-creep-speed-profile.md)、[`dota-neutral-camp-openings.md`](./dota-neutral-camp-openings.md) |
| **配套产物** | [`artifacts/unit-facing/`](../artifacts/unit-facing/)（`probe_facing_127.txt`、`facing_all11_verify.txt`、`facing_remaining_verify.txt`、`final_micro_check.txt`、`verify_live_facing.py`） |
| **配套思维导图** | [`war3-unit-facing-mindmap.md`](./war3-unit-facing-mindmap.md) |

---

## 零、核心结论速览

1. **读朝向（推荐直接调原生 `GetUnitFacing`，无需手工解内存）**：
   - `GetUnitFacing(unitHandle)` 为标准 JASS `__cdecl` 原生，**返回值是 IEEE-754 `float` 角度（度，deg）的 32 位位模式，放在 `EAX`**（不是 `ST0`！与 `GetUnitX`/`GetUnitY` 完全同款，直接复用 `aiCallNative1` + `memcpy(&deg, &bits, 4)`）。
   - **角度约定**：标准数学极坐标——**`0°` = 正东（`+X`）、`90°` = 正北（`+Y`）、`180°` = 正西（`-X`）、`270°` = 正南（`-Y`），逆时针为正**，与 `GetUnitX/Y` 世界坐标系及 `atan2(dy, dx) * 180 / π` 完全一致。
   - **更正前序文档**：[`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md) 称 1.27 乘数 `0x6FB59460`「文件里是 0、运行期才填」系未按节表换算文件偏移所致；实际 PE `.data` 节中 `1.27 0xB59460` **静态编译为 `0x42652EE1` = `57.29578f`（即 `180/π`）**，紧邻其前的 `0xB59440..0xB5945C` 依次是 `1/2π, 1/π, π/6, π/4, π/2, π, 3π/2, 2π`；仅 1.0.17~1.26.0 因旧编译器置于 `.bss` 而在 DLL 启动初始化时填入 `180/π`。
2. **转身速度与推进窗口（6.83d SLK 核验）**：
   - **影魔 `Nfir`**：DotA 6.83d `Units_UnitData.slk:L2201` 覆写 **`turnRate = 1.0`**（原版 0.6）、**`propWin = 60°`**。32 Hz 步进下转 180° 仅需 `ceil(π / 1.0) = 4` ticks ≈ **`0.125s`**（连续值 `0.098s`）。
   - **冰女 `Hjai`**：沿用 `War3Patch.mpq` `L20091` **`turnRate = 0.5`**、**`propWin = 60°`**。转 180° 需 `ceil(π / 0.5) = 7` ticks ≈ **`0.219s`**（连续值 `0.196s`）。
   - **转身是否原地停下**：与小兵完全同套引擎逻辑（`CPoPosCl::StepTurnAndMove`），硬二值门控——只要 `|Δθ| >= 60°`，移速置 `0` 原地转身；进入 `±60°` 内即瞬间满速边走边转。
3. **玩家指令转向最优方案**：
   - 推荐 **「近点 `move`（`0x12 + 0xD0012` + 空目标 `FFFFFFFF FFFFFFFF`）朝目标方向偏移 `24~32` 码 + 到位后下 `hold`（`0x10 + 0xD0019`）」**（或先站到目标点反方向 `24` 码处，再 `move` 到精确站位点——到位瞬间自然面朝指定方向，**零额外位移、不会触发自动攻击**！）。
4. **挂钩与 `-mark pos` 格式建议**：
   - 在 `war3hook_ai.cpp` 的 `AI_NATIVE_*` 名字表直接新增 **`AI_NATIVE_GET_UNIT_FACING` (`"GetUnitFacing"`)**（DotA 脚本大量调用，必然自动捕获），比手工跟内存链表更稳、全 11 版零维护。
   - `-mark pos` 文件格式建议追加可选第 5 列 `facingDeg`：`x y radius team [facingDeg]`，旧文件缺省第 5 列时默认 `-1`（不强制转向），100% 向后兼容。

---

### 0.1 全部 11 版本 `GetUnitFacing` 与 `180/π` 乘数 RVA 对照表

来源：[`facing_all11_verify.txt`](../artifacts/unit-facing/facing_all11_verify.txt)、[`final_micro_check.txt`](../artifacts/unit-facing/final_micro_check.txt)（并与 `war3-unit-movement-fields.md` L177 交叉核对 100% 一致）。

| War3 版本 | `GetUnitFacing` 原生 RVA | `180/π` 乘数全局 RVA | `CUnit::GetPosNode` (`vt+0xB8`) | `StepTurnAndMove`（引用前序） | 返回值寄存器 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `1.0.17.5988` | `0x2BFCA0` | `0x84AA2C` (`.bss` 启动填) | —※ | `0x676380` | `EAX` (float bits) |
| `1.0.20.6048` | `0x2BFCA0` | `0x84BA6C` (`.bss` 启动填) | —※ | `0x676880` | `EAX` (float bits) |
| `1.20.4.6074` | `0x2BFDC0` | `0x84BA8C` (`.bss` 启动填) | —※ | `0x6771C0` | `EAX` (float bits) |
| `1.21.0.6263` | `0x2C3390` | `0x84CAC4` (`.bss` 启动填) | —※ | `0x67B1E0` | `EAX` (float bits) |
| `1.22.0.6328` | `0x3BEA30` | `0xA9B014` (`.bss` 启动填) | `0x28A590` | `0x484310` | `EAX` (float bits) |
| `1.23.0.6352` | `0x3C0750` | `0xAB3E68` (`.bss` 启动填) | `0x28BAD0` | `0x4860A0` | `EAX` (float bits) |
| `1.24.1.6374` | `0x3C6210` | `0xAC5468` (`.bss` 启动填) | `0x28BB90` | `0x494A30` | `EAX` (float bits) |
| `1.24.4.6387` | `0x3C62D0` | `0xAC5468` (`.bss` 启动填) | `0x28BC00` | `0x494AB0` | `EAX` (float bits) |
| `1.25.1.6397` | `0x3C5560` | `0xAAE60C` (`.bss` 启动填) | `0x28AEB0` | `0x493D70` | `EAX` (float bits) |
| `1.26.0.6401` | `0x3C5790` | `0xAAE60C` (`.bss` 启动填) | `0x28B0E0` | `0x493FA0` | `EAX` (float bits) |
| `1.27.0.52240` | `0x1E6130` | `0xB59460` (`.data` 静态 `0x42652EE1`) | `0x668DA0` | `0x11CFD0` | `EAX` (float bits) |

> ※ 1.0.17~1.21.0 无 MSVC RTTI，但 `GetUnitFacing` 尾部（如 1.0.17 `0x2BFD54`）同样执行 `call dword ptr [edx + 0xB8]` 获取位置包装对象。

---

## 一、读朝向：`GetUnitFacing` 反汇编与角度约定

### 1.1 1.27 `GetUnitFacing` (`0x1E6130`) 完整指令链
```asm
6F1E6133: mov ecx, [ebp+8]             ; JASS unitHandle
6F1E613A: call 6F1D1550                ; JassHandleToUnit -> CUnit* esi
... (0x1E6145..0x1E6168 校验 Agent 存活且未销毁)
6F1E616A: mov eax, [esi]
6F1E616C: mov ecx, esi
6F1E616E: call dword ptr [eax+0B8h]    ; CUnit::GetPosNode -> 返回 CUnit+0x164 位置包装对象
6F1E6174: lea ecx, [ebp-8]             ; outRad 缓冲
6F1E6177: push ecx
6F1E6178: mov ecx, eax
6F1E617A: mov edx, [eax]
6F1E617C: call dword ptr [edx+1Ch]     ; 读节点 +0x90 当前朝向（弧度）
6F1E617F: push 6FB59460h               ; 180.0 / pi = 57.29578f (0x42652EE1)
6F1E6184: mov edx, eax                 ; radPtr
6F1E6186: lea ecx, [ebp-4]             ; outDeg 缓冲
6F1E6189: call 6F0527E0                ; 软浮点乘法：deg = rad * (180 / pi)
6F1E618E: mov eax, [ebp-4]             ; 以 32 位 IEEE-754 位模式放进 EAX 返回！
6F1E6195: ret
```

### 1.2 返回值范围与坐标系约定
- **角度约定**：War3 世界坐标 `+X` 为东、`+Y` 为北，`atan2(dy, dx)` 为标准逆时针极角：`0° = 东`，`90° = 北`，`180° = 西`，`270° = 南`（与 `war3map.j` 中 `bj_UNIT_FACING = 270.0` 正南出兵完全一致）。
- **返回值范围**：War3 内部位置节点 `+0x90` 维持在 **`[0, 2π)`**（对应 `GetUnitFacing` 返回 **`[0.0, 360.0)`**）；但在极少数跨 0° 边界的浮点舍入瞬间可能出现极小负值或 `360.0`（引擎底层未在 `GetUnitFacing` 出口再做一次 `fmod`），建议业务层统一做一次 `fmodf(fmodf(deg, 360.0f) + 360.0f, 360.0f)` 归一化到 `[0, 360)`，并按最短角差 `diff = remainderf(target - cur, 360.0f)`（范围 `[-180, +180]`）比较。

---

## 二、当前朝向 (`+0x90`) vs 目标朝向 (`+0x8C`) 与内存指针链

- **语义关系**：
  - `node + 0x8C`（`float` 弧度）：**目标朝向**（由移动指令、攻击索敌或 `SetUnitFacing` 写入）。
  - `node + 0x90`（`float` 弧度）：**当前实际朝向**（每 32 Hz 模拟 tick 在 `CPoPosCl::StepTurnAndMove` 中向 `+0x8C` 逼近最多 `turnRate` 弧度：`*outAngle += clamp(angleDiff, -turnRate, +turnRate)`，见 1.27 `0x11D033..0x11D070`）。
  - 静止且转身完毕时，`+0x90 == +0x8C`；正在转身时，`+0x8C` 已切到新目标方向，`+0x90` 逐 tick 追赶。
- **只读内存指针链**（引自 `war3-unit-movement-fields.md` 并核对全 11 版 `CUnit vt+0xB8`）：
  ```text
  CUnit* unit = JassHandleToUnit(handle)
  void*  posWrap = (char*)unit + 0x164   // CUnit::vtable+0xB8 返回值（全 11 版均为 +0x164）
  // posWrap 内部挂接位置节点指针（1.26/1.27 已核，节点 +0x8C 目标弧度 / +0x90 当前弧度 / +0xB8 turnRate / +0xBC propWin_rad）
  ```
  > 注：`posWrap` 到 `CPoPosCl*` 内部节点偏移未在本轮逐 11 版重扫（标 `❓`），**工程上完全不需要直接解该内存链**——直接调 `GetUnitFacing` 原生即可安全拿到跨全 11 版的当前角度。

---

## 三、英雄转身速度与 `propWin`（6.83d SLK 核验）

| 单位 | 6.83d TypeId | `turnRate` (rad/tick) | `propWin` | 180° 理论连续用时 (`π / turnRate / 32`) | 180° 32Hz 离散用时 (`ceil(π/turnRate)/32`) | 90° 离散用时 | 数据来源 |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **影魔 (SF)** | `Nfir` | **`1.0`** | **`60°`** | `0.098s` | **`0.125s`** (4 ticks) | `0.063s` (2 ticks) | 6.83d `Units_UnitData.slk:L2201`（覆写原版 0.6→1.0） |
| **冰女 (CM)** | `Hjai` | **`0.5`** | **`60°`** | `0.196s` | **`0.219s`** (7 ticks) | `0.125s` (4 ticks) | `War3Patch.mpq` `Units_UnitData.slk:L20091`（地图未覆写） |
| **多数常规英雄** | `Hamg`/`Edem`/`Ulic` 等 | `0.5` ~ `0.6` | **`60°`** | `0.164~0.196s` | `0.188~0.219s` | `0.094~0.125s` | 同上 |

- **转身时是否原地停下？**
  - **是（硬二值门控，非比例减速）**：`CPoPosCl::StepTurnAndMove`（1.27 `0x11CFF0: comiss xmm0, [edi+0xBC]`）检查 `fabs(Δθ) < propWin`（`60° = 1.0472 rad`）：
    - `|Δθ| >= 60°`：速度强制置 **`0`**，英雄**原地停下转身**；
    - `|Δθ| < 60°`：速度瞬间恢复满速，**边走边完成剩余 ≤60° 的转身**。
  - 这也意味着：冰女（`turnRate=0.5`）若背对开口（180°）才下移动指令，原地停顿转身到 `60°` 以内（转 `120° = 2.094 rad`）需 `5` ticks = **`0.156s`** 才迈出第一步；若提前面朝开口，起步延迟为 **`0s`**！

---

## 四、用玩家指令让英雄转到指定朝向（可行方案与副作用）

玩家动作包没有 `SetUnitFacing`，只能通过移动类网络动作包改变 `+0x8C` 目标朝向：

| 方案 | 动作包格式（参考 `war3hook_ai.cpp`） | 能否转向 | 实际位移与副作用 | 推荐度 |
| :--- | :--- | :---: | :--- | :---: |
| **方案 A（最推荐）：退后小步 → 走回精确站位** | 先 `aiOrderTarget(0x000D0012, x - 32*cosθ, y - 32*sinθ, 0xFFFFFFFF, 0xFFFFFFFF)`，到位后再 `aiOrderTarget(0x000D0012, x, y, 0xFFFFFFFF, 0xFFFFFFFF)`，到达后下 `hold`（`aiOrderImmediate(0x000D0019)`） | **✅ 精确面朝 `θ`** | **最终停在精确 `(x, y)` 零误差！** `hold` 既锁定朝向又不触发自动追击，不会像 `stop` 那样让英雄自动跑去 A 射程内野怪 | **★★★ 首选（囤野到位流程）** |
| **方案 B：就地对身边近点下 `move`** | `aiOrderTarget(0x000D0012, x + d*cosθ, y + d*sinθ, 0xFFFFFFFF, 0xFFFFFFFF)`（`d = 24 ~ 40` 码），到位后下 `hold`（`0x000D0019`） | **✅ 可转向** | 会产生 `24~40` 码位移；若 `d` 过小（`< 16` 码，处于寻路到达容差内），引擎可能直接判「已到达」而**忽略该移动指令不转身**（精确最小忽略阈值未反汇编寻路到达判定，标 `❓`，建议实机以 `24~32` 码验证） | **★★ 备选（允许 ~30 码微移时）** |
| **方案 C：对远点下 `move` 后立即 `stop` (`0xD0004`) / `hold` (`0xD0019`)** | 先发 `0x12 + 0xD0012` 到远处，隔 `T` 毫秒再发 `0x10 + 0xD0004` 或 `0xD0019` | **⚠ 中断转身** | 收到 `stop`/`hold` 瞬间取消移动指令，转身**立即中断**，朝向停在中断那一 tick 的 `+0x90`；若 `T` 太短转不够，太长又已经走出几十码；且 `stop` 会立刻让英雄恢复自动攻击（可能提前 A 野怪破坏囤野时机！） | **❌ 不推荐** |

- **动作包字节格式确认**（与 `war3hook_ai.cpp` `aiOrderTarget` / `aiOrderImmediate` 完全一致）：
  - 点地移动：`0x12`（`flags = 0x0000`，`orderId = 0x000D0012`，`x, y`，`targetObj1 = 0xFFFFFFFF`, `targetObj2 = 0xFFFFFFFF`）。
  - 原地保持（不追怪、不自动走动）：`0x10`（`orderId = 0x000D0019`）。注：若目标野怪本身就在射程内，`hold` 仍可能原地自动攻击射程内敌人，囤野等待期仍需配合「站位离野怪 > 射程」或现有防自动平 A 保护。

---

## 五、朝向与攻击 / 施法（对囤野时间预算的影响）

- **攻击前必须先转身吗？**
  - **是**：在 1.27 `CAbilityAttack` 攻击执行链（`0x47CDC0..0x47CE56`）中，单位收到攻击指令（`0x000D000F`）并进入射程后，先调用 `0x671450` 令单位朝向目标；只有当朝向转入攻击允许锥角后，才在 `0x47CE56` 调用 `SetAttackCooldown(..., startWindup=1)` 启动攻击前摇 `+0x1EC`（攻击启动的精确角度容差值未单独反汇编，标 `❓`，通常远小于 `propWin`，在 DotA 实感中接近正对目标）。
- **转身时间计入前摇之前**：
  - 完整「发令 → 弹道命中野怪」时间 = `联机 W3GS 延迟 (0.20~0.43s)` + **`转身时间 (0 ~ 0.22s)`** + `攻击前摇 (冰女 0.55s / 影魔 0.50s)` + `弹道飞行 (距离 / 弹速)`。
  - 这解释了囤野拉野为什么要记录朝向：如果提前面朝野怪（而非背对野怪），冰女每次拉野可稳定省下 **`~0.20s`** 的不可控转身抖动，让 xx:52/53 出手时机更准；打完后立刻往开口拉走时，若开口在身后，又会吃一次 `~0.16s` 的原地转身（转过 120° 进 `propWin`），这两段都应计入时间预算。

---

## 六、挂钩实现与 `-mark pos` 格式建议（供 Claude 参考）

### 6.1 读朝向：直接接入 `AI_NATIVE_*` 名字表（强烈推荐）
在 `War3Launcher/hooker/war3hook_ai.cpp` 现有框架中，只需加 3 行即可跨全 11 版本零偏移读取英雄朝向：
```cpp
// 1. enum AiNativeIndex 新增：
AI_NATIVE_GET_UNIT_FACING,

// 2. kAiNativeNames[] 新增：
"GetUnitFacing",   // DotA 6.83d 脚本大量调用，进图必解析

// 3. 封装只读读取函数（游戏主线程调用，与 GetUnitX 同构）：
static bool aiGetUnitFacingDeg(uint32_t unitHandle, float *outDeg) {
    uint32_t bits = 0;
    if (!g_aiNativeImpl[AI_NATIVE_GET_UNIT_FACING] ||
        !aiCallNative1(g_aiNativeImpl[AI_NATIVE_GET_UNIT_FACING], unitHandle, &bits))
        return false;
    float deg = 0.0f;
    memcpy(&deg, &bits, 4);
    if (!std::isfinite(deg)) return false;
    deg = std::fmod(std::fmod(deg, 360.0f) + 360.0f, 360.0f);
    *outDeg = deg;
    return true;
}
```
> 兜底方案：若在极早期时刻尚未捕获 `GetUnitFacing`，也可用本文 §0.1 的全 11 版静态 RVA 表直接 `base + rva` 填入 `g_aiNativeImpl[AI_NATIVE_GET_UNIT_FACING]`。

### 6.2 `-mark pos` 数据格式建议（兼容旧文件）
- 现有格式：`x y radius team`
- 新格式：`x y radius team facingDeg`（例如 `-1420.5 2310.0 80 1 45.0`）
- 解析兼容：`sscanf` 读到 4 列时设 `hasFacing = false`（兼容所有历史标记文件）；读到 5 列且 `0 <= facingDeg < 360` 时启用到位转向（采用 §四方案 A：先走至 `(x - 32*cos, y - 32*sin)`，再走到 `(x, y)` 并下 `hold`）。

---

## 七、离线验证与留给 Claude 的实机验证步骤

- **离线已验证**：全 11 版 `GetUnitFacing` 与 `180/π` 乘数全局 RVA 均经 `dumpbin` 逐版交叉核对；1.27 `0xB59460` 静态字节 `0x42652EE1` = `57.29578f` 已直接核出；`Nfir` (`1.0 / 60°`) 与 `Hjai` (`0.5 / 60°`) 已从 6.83d / `War3Patch` SLK 原文核出。
- **实机验证步骤（留给 Claude 在测试机上执行）**：
  1. 在 hook 中按 §6.1 接入 `GetUnitFacing`，并在日志或 RemoteControl `facing` 命令中输出 `t, hx, hy, facingDeg`。
  2. 运行配套测试脚本 [`artifacts/unit-facing/verify_live_facing.py`](../artifacts/unit-facing/verify_live_facing.py) 的检查项：
     - **坐标系校验**：让英雄向右（正东 `+X` 偏移 +300）走一步停稳 → `GetUnitFacing` 应为 **`0° ± 3°`**；向正北（`+Y` 偏移 +300）走一步停稳 → 应为 **`90° ± 3°`**；向正西 → **`180° ± 3°`**；向正南 → **`270° ± 3°`**。
     - **近点 `move` 最小有效距离校验**：分别向当前朝向反方向（+180°）下 `d = 8, 16, 24, 32, 48` 码的 `0xD0012` move 指令，确认哪个最小 `d` 开始触发稳定 180° 转身，并记录实际位移。
     - **180° 转身耗时校验**：100ms 采样记录 `facingDeg` 从 `0°` 转到 `180°` 的用时（影魔预期 ~0.13s，冰女预期 ~0.22s，乘以实际游戏倍速）。
     - **`stop` 中断校验**：对远处下 `move` 后 50ms 立即发 `0xD0004` (`stop`)，确认朝向停在半途而非继续转完。
