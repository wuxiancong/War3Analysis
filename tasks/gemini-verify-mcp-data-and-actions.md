# 任务：实机核验「大模型托管」接口的数据读取和动作包（1.27 为主）

**给**：Antigravity Gemini　**布置时间**：2026-11-21　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 背景

你上一个任务写完了 `analyses/dota-ai-llm-mcp-control.md`（大模型通过 MCP Server 托管 DotA 的接口设计）。第二节「看局面」和第三节「指令缺口」里给了很多偏移、RVA 和动作包序列，**大部分还没在实机上验证过**。

接下来要按这份文档写代码，所以要先确认这些地址和序列是对的：错一个偏移，大模型就会拿错数据做决策。这次是**复核自己的文档**，重点放在 1.27（`War3Launcher/versions/1.27.0.52240/game.dll`）。

**复核要求**：
- 不能拿原文档当证据。每一条都要有独立证据：反汇编指令、`war3map.j` 原文行，或实机读数。
- 原文档里是推断、没有直接证据的条目，就标 ❓ 或 ⚠，不要因为是自己写的就标 ✅。
- 可参考 Cursor Grok 已验证的 `analyses/war3-unit-movement-fields.md` 和 `war3-unit-collision-and-repath.md`：它们是独立的证据来源，结论有冲突时要指出来。

## 要核验的条目

把下面每一条的结果标成：

- ✅ 正确
- ⚠ 部分对（写出更正后的值）
- ❌ 错（写出正确做法）
- ❓ 没法验证（写原因）

### A. 读取（文档第二节 A1~A4）

1. **技能冷却**
   - 文档写的是 `CAbilitySpell+0xD0`：确认剩余冷却和总冷却分别在哪。
   - 用冰女（Hjai）的技能实测：放技能前、放完马上、放完 5 秒后各读一次。
2. **金钱**
   - 可靠和不可靠金钱分别从哪读。文档里提到地图变量 `EL0`，确认它在 6.83d 的 `war3map.j` 里是什么。
   - 买一件东西前后各读一次。
3. **视野过滤**
   - 方法：`IsUnitVisible(unit, localPlayer)`，对隐身单位再加 `IsUnitDetected`。
   - 确认迷雾里的敌方英雄返回 false，没有漏读迷雾下单位的情况。
   - 这条是防作弊红线，必须有实测证据。
4. **buff / debuff**
   - 怎么判断眩晕、沉默、减速。文档里如果给了偏移或原生函数，逐条确认。
5. **买活冷却、Glyph 冷却、昼夜时间**（`GetFloatGameState(GAME_STATE_TIME_OF_DAY)`，1.27 RVA `0x1E2500`）：逐条确认。
6. **事件来源**：击杀、死亡、塔倒的事件，从哪个钩子或动作包能拿到（文档写的是 `FL1` / `0x6B`）。核对 `war3map.j` 和 1.27 的处理函数。

### B. 动作包（文档第三节 B2）

1. **买活**
   - 序列：选中能量圈（`n01F`），发 `0x10` 加英雄 FourCC。
   - 核对 `war3map.j` 的 `D7O` 逻辑：是不是真的这样买活，有没有额外条件。
2. **Glyph**
   - 序列：选中能量圈，发 `0x10` 加 `0x000D00FA`（`coldarrows`）。
   - 核对技能 `A141` / `A1WI` 和 OrderId。
3. **远程购买进储藏处，以及信使**：文档给的信使类型（`n00I` / `n022` …）和 OrderId（`0xD00FA` / `0xD0081` / speedburst），逐个核对。注意：上面 Glyph 也写成 `0xD00FA`，两处冲突，查清楚哪个对。
4. **TP 到指定建筑**：用 `useslot` 加坐标时，回城卷轴吸附最近己方建筑的规则和距离（文档写的是 575）。
5. **Shift 队列**：`flags |= 0x01` 在 `0x10` / `0x11` / `0x12` 里是不是 queue 位。

### C. 验证方法

- **能离线确认的**：用 Ghidra / 反汇编 / `war3map.j` 确认，给出函数地址和关键指令。
- **需要实机的**：只读内存，用 `shared/scripts/` 里已有的读取脚本或你自己写的脚本。不要在游戏线程以外调用 JASS 原生函数，不要往游戏进程写内存。
- **动作包**：只用离线证据核对格式（`war3map.j`、反汇编、已有的 `hooker/` 发包代码），**不要自己往实机发包**。需要实机发包验证的，列成「建议测试步骤」，交给主会话执行。
- **开局**：需要开一局测试的话，按 `.agents/rules/ai-autostart.md` 从 `C:\War3Run` 启动，`Scripts\Start-AiGame.ps1 -Hero cm` 可以直接到英雄就位。

## 输出

- 正文：`analyses/dota-ai-llm-mcp-verify.md`
  - 一张总表：条目、文档原值、核验结果、更正值、证据、置信度；
  - 一节「给实现者的结论」：哪些可以直接写代码，哪些要先改，哪些要换方案。
- 导图：`analyses/dota-ai-llm-mcp-verify-mindmap.md`
- 脚本 / 导出：`artifacts/llm-mcp-verify/`
- **不要直接改原文档 `dota-ai-llm-mcp-control.md`**。在新文档里逐条引用它的节号，主会话核对后再合并更正，这样改了什么、为什么改都看得清。
- 文档开头写明：分析模型、分析目的、命名方式、分析时间、验证状态、证据（规则 `.agents/rules/war3-analysis-save.md`、`war3-reverse-toolkit.md`）。
- 不改 War3Launcher / hooker 代码。
