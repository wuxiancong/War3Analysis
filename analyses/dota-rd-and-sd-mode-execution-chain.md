# Warcraft III 1.27.0.52240: DotA RD 与 SD 模式执行链路逆向分析报告

## 摘要与概述

在魔兽争霸 III（以经典 DotA 地图及 1.27.0.52240 `game.dll` 为例），**RD (Random Draft / 随机征召)** 与 **SD (Single Draft / 单一征召)** 两种模式的核心玩法逻辑是由地图脚本（JASS/vJASS）通过 `game.dll` 导出的 **JASS 虚拟机全局变量体系**、**Native API 调度网关** 以及 **底层玩家动作协议（Action Packet）** 深度协同驱动的。

本报告系统化梳理了两种模式在二进制引擎与脚本层之间的执行链路、关键内存偏移、网络封包以及状态迁移机制。

---

## 一、核心机制与设计对比

| 维度 | RD 模式 (Random Draft) | SD 模式 (Single Draft) |
| :--- | :--- | :--- |
| **规则定义** | 全局共享的 20~24 个英雄池，双方玩家按顺位轮流征召 | 每位玩家独立的 3 选 1 专属英雄池（力量、敏捷、智力各一） |
| **英雄池展现形式** | 地图专属选人区域生成 24 个展示实体单位 (`QA0`) | 动态注入各玩家独占的**能量圈**（Circle of Power, `D30`）商品列表 |
| **选人交互方式** | 选中展示单位进行预览，点击**固定确认勾选按钮** (`h06N`) | 选中自身能量圈，通过原生**商店购买/雇佣单位**交互 |
| **网络动作类型** | 复合选择包 (`0x3A`/`0x0A`) + 15 字节专属确认动作 (`Flag: 0x40`) | 标准单位购买指令 (`0x10`) |
| **JASS 核心变量** | `Q80` (槽位映射), `Q90` (锁定状态), `QA0` (展示实体) | `D30` (玩家能量圈 Handle) |
| **底层引擎切入** | `GameJassVariableSetter` + 动作入队协议拦截 | `GameNativeFuncEntryPoint` (`AddUnitToStock`) |

---

## 二、RD 模式 (Random Draft) 详细执行链路

RD 模式是一套严格的**带状态机轮流选人系统（Turn-based Draft）**。

### 1. 模式启动与英雄池初始化
1. **模式判定**：解析聊天指令（如 `/host rd` 或 `-rd`），JASS 设置模式标志，触发 RD 状态机。
2. **抽取随机英雄**：JASS 从全局英雄池中随机抽取 24 个不重复的英雄索引。
3. **建立全局映射（JASS 变量写入）**：
   - **`Q80[slot]`**（槽位 -> 英雄库索引）：`slot (0..23)` 映射至对应的全局英雄索引 `heroIndex`。
   - **`QA0[slot]`**（槽位 -> 展示单位句柄）：地图在选人区为每个槽位创建展示用傀儡单位，并将单位 Handle 写入 `QA0[slot]`。
   - **`Q90[slot]`**（槽位锁定状态）：初始化为 `0`（表示可选）。
   - **底层切入**：通过 `game.dll` 的 `GameJassVariableSetter_1` (`0x7EC719`) 与 `Setter_2` (`0x7EC660`) 写入 JASS 符号表。

### 2. 玩家选人交互（预览与目标切换）
- **动作封包 `0x3A` (58 字节)**：
  当玩家在 UI 或场景中切换选中不同的候选英雄时，客户端构建复合动作包：
  - 封包结构：`[0x1B 0x02] ... [0x1B 0x01, Handle1, Handle2] ... [0x1A 0x19]`
  - 作用：向同步队列发出取消当前选择（Deselect）、选中目标英雄实体（Select）并同步本地镜头的指令。
- **动作封包 `0x0A` (10 字节)**：
  当玩家重复点击同一已选中的候选英雄时，发送 `0x1B 0x01 [Handle1] [Handle2]`，维持选择状态。

### 3. 锁定确认与英雄生成 (Pick 结算)
1. **确认勾号按钮 (`h06N`)**：
   RD 模式不直接向英雄单位发送购买指令，而是通过点击一个固定的确认勾号虚拟单位（FourCC: `h06N`）。
2. **确认动作包注入**：
   - 发送 15 字节动作载荷（Action Type `0x10`，Flag `0x40`，UnitCode `h06N`）。
3. **JASS 状态结算**：
   - 地图触发器捕获对 `h06N` 的指令，确认当前属于该玩家的选人顺位；
   - 触发更新 **`Q90[slot] = 1`**（通过 `GameJassVariableSetter` 将该英雄槽位标记为已被锁定，阻止他人选择）；
   - 调用 Native API `CreateUnit` 在泉水或指定点生成玩家的真实英雄；
   - 更新 **`K1[playerIndex]`**（保存玩家最终控制的英雄 Handle）；
   - 回合顺位推进（Turn Token 转移至下一玩家，重置倒计时）。

---

## 三、SD 模式 (Single Draft) 详细执行链路

SD 模式复用了魔兽争霸 III 原生的**建筑库存与科技售卖系统（Stock System）**。

### 1. 玩家专属选择建筑绑定
- 地图在开局为每个玩家分配一个专属建筑——**能量圈（Circle of Power）**。
- JASS 脚本通过数组 **`D30[playerIndex]`** 保存该玩家能量圈的 Handle。

### 2. 候选英雄注入 (Native API: `AddUnitToStock`)
1. 地图脚本分别为力量、敏捷、智力三个属性池随机抽取 1 个候选英雄 `unitId`。
2. 调用引擎 Native 函数：
   ```jass
   call AddUnitToStock(udg_D30[playerIndex], heroUnitId, 1, 1)
   ```
3. **底层执行**：
   - 进入 `game.dll` 的统一 Native 分发网关 `GameNativeFuncEntryPoint` (`0x7EF6E0`)；
   - 调用 C++ 内部实现 `CUnit::AddStockItem`，将该 4-char ID 挂载至该能量圈建筑的商品销售列表。
   - 由于是按玩家各自的 `D30` 能量圈分别添加，每位玩家只能在自己的能量圈里看到属于自己的 3 个候选英雄。

### 3. 玩家选择与结算
1. 玩家选中自身能量圈，点击对应的英雄图标。
2. 客户端向同步队列发送标准的**雇佣/购买单位动作**（Action Type `0x10`，携带目标英雄的 `unitId`）。
3. **JASS 结算**：
   - 地图监听到购买事件，触发英雄降生；
   - 地图调用 `RemoveUnitFromStock` 或 `SetPlayerTechMaxAllowed` 移除剩余 2 个英雄商品并锁死选择权；
   - 更新 **`K1[playerIndex]`** 记录正式英雄句柄。

---

## 四、`game.dll` 关键底层内存地址 (v1.27.0.52240)

| 模块符号 / 逻辑功能 | 1.27a 内存偏移 | 调用约定 | 职责说明 |
| :--- | :--- | :--- | :--- |
| **`GameJassVariableSetter_1`** | `0x7EC719` / `0x7EC6C0` | `__fastcall` / inline | JASS 全局变量写入主入口。用于监听 `Q80` (RD 槽位)、`Q90` (RD 选走)、`QA0` (RD 句柄)、`D30` (SD 能量圈) 和 `K1` (英雄句柄) |
| **`GameJassVariableSetter_2`** | `0x7EC660` | `__thiscall` | JASS 数组元素重置与辅助更新例程 |
| **`GameNativeFuncEntryPoint`** | `0x7EF6E0` | `__cdecl` | JASS Native 调用的统一入口网关。用于拦截 `AddUnitToStock` (SD 候选添加)、`CreateUnit` 等 |
| **`EnqueuePlayerAction`** | 网络/动作输入层 | `__thiscall` | 本地玩家动作入队函数。提交 `0x10` (购买指令)、`0x1B` (选择单位)、`0x3A` (RD 复合选择包) 及勾号确认 |

---

## 五、逆向实测与证据链汇总

在 `War3Launcher` 项目的运行时 Hook 与日志捕获中，已完整证实上述调用链路：
1. **RD 槽位与锁定追踪**：
   在 `war3hook.cpp` 的 `gameJassVariableDataThread_1` 中，捕获到 JASS 标签 `Q80`（槽位英雄库索引）与 `Q90`（锁定状态）；当 `Q90 != 0` 时，触发 IPC 广播 `MSG_TYPE_HERO_PICK_SYNCED`。
2. **RD 勾号确认动作**：
   `war3hook.cpp` 在处理 RD 选人时，固定针对 `h06N` 发送 `Flag: 0x40` 封包，成功在游戏内完成选人确认。
3. **SD 三候选捕获**：
   在 `NativeFunc4.log` 中捕获到 `HASH_ADD_UNIT_TO_STOCK` 连续执行 3 次，目标单位与 `D30[playerIndex]` 能量圈完全匹配，提取到 3 个候选 RawCode（力量、敏捷、智力）。