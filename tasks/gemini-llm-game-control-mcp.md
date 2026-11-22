# 任务：逆向 + 设计「大模型托管 DotA」的游戏接口（类 MCP Server）

**给**：Antigravity Gemini　**布置时间**：2026-11-21　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 目标

让大模型（Claude / Gemini 等）通过一个 **MCP Server** 托管玩家的 DotA 6.83d（War3 1.27）对局：大模型调用工具「看局面」和「下指令」，hook.dll 在游戏线程里执行。

**分层原则（必须遵守）**：大模型一次调用要 1~5 秒，跟不上补刀、卡兵、躲技能这种 100ms 级的操作。所以：

- **大模型 = 指挥层**：决定意图，比如「去中路对线」「回家买鞋」「去下路 gank」「推塔」「撤退」。
- **hook AI = 执行层**：完成具体操作，包括补刀、卡兵、走位、放技能连招、躲塔，这些已有 `tactic` / `lasthit` / `cast` / `safe` 等命令。
- **MCP 工具粒度**：做成「意图 + 参数」，不要做成逐帧点击。

## 现有基础（先读，不要重复造）

- **Launcher RemoteControl**：`127.0.0.1:6120`，一行文本命令，回一行 `OK …` / `ERR …`。
  - 实现在 `War3Launcher/managers/AiControlManager.cpp`。
  - 已有命令：`start` / `stop` / `status` / `pick` / `random` / `shop` / `move` / `attack` / `hold` / `stop` / `lasthit` / `deny` / `cast` / `learn` / `autolearn` / `skills` / `buy` / `items` / `use` / `inv` / `tactic …` / `safe` / `unsafe` / `push` / `back` / `aggro` / `units` / `minimap` / `lock` / `say` 等。
- **命令结果写在 `logs/AiUnit.log`**，不在回包里。这一点必须改进。
- **已知缺陷**：`say -xxx` 注入的聊天命令不会被 hook 的聊天解析器处理，只有玩家亲手打字的才会。
- **相关分析文档**（`analyses/`）：
  - `dota-ai-player-live-state-10ms-reporter.md`
  - `dota-683d-ai-data-tables.md`
  - `dota-ai-tactics-library.md`
  - `dota-ai-skill-command-implementation.md`
  - `dota-ai-smart-item-buy-and-use.md`
  - `war3-unit-movement-fields.md`
  - `dota-683d-ward-and-deward.md`
  - `dota-ai-draft-and-lineup.md`
  - `dota-ai-scoring-system.md`

## 要做的事

### A. 逆向补齐「看局面」需要的数据（1.27 RVA，能做就附 1.24.4 / 1.26）

1. **我方英雄**：等级、经验、HP/MP、属性、金钱（可靠 / 不可靠）、物品栏和冷却、技能等级和冷却、buff / debuff（眩晕、沉默等），以及买活状态与冷却。
2. **视野内的单位**：敌我英雄、小兵、塔、野怪、守卫。要给出 **只读本地玩家视野** 的判定方法（`IsUnitVisible` / 迷雾位图），**不能读迷雾下的敌人**（那是作弊，大模型托管也不允许）。
3. **地图态势**：各路兵线位置、各塔血量和是否存活、肉山状态（只用视野和公开信息）、游戏时间与昼夜。
4. **事件流**：击杀、死亡、塔倒、大招释放、聊天、Ping。看能不能从已有的钩子拿，比如 `Net-Hook` 动作包和 `TriggerRegister` 回调。

每项写清：字段 / 函数、偏移、读取线程要求（哪些必须在游戏线程读）、读一次的开销。

### B. 指令覆盖检查

对照 DotA 玩家的操作，列出现有命令**还缺什么**：

- 点地 / 点单位 / 无目标技能（含 Shift 队列）；
- 买东西（远离商店时用信使）、信使操作；
- 插眼 / 排眼；
- 升级技能；
- 买活、扫描 / Glyph（6.83d 只有 Glyph）、TP 到建筑。

对缺的部分，给出可以复用的 1.27 动作包格式或游戏内部函数。

### C. MCP Server 接口设计（写成文档，不用写代码）

1. **形态**：一个独立进程（建议 Node 或 Python 的 MCP SDK，stdio 传输），内部连 `127.0.0.1:6120`，或者走新开的本地 JSON 端口。
2. **工具清单**，每个都写清名字、参数 JSON Schema、返回 JSON 示例、执行层对应的现有命令，以及缺什么。比如：
   - `get_game_state(detail)`：概览，压到 2k token 以内，给大模型看；
   - `get_units(radius, filter)`；
   - `move_to(x, y | landmark)`；
   - `farm_lane(lane)`；
   - `retreat()`；
   - `attack_target(unit_id)`；
   - `cast(ability, target)`；
   - `buy(items[])`；
   - `use_item(item, target)`；
   - `learn(ability)`；
   - `ward(spot)`；
   - `set_mode(push | farm | gank | defend)`；
   - `chat(text)`；
   - `get_events(since)`。
3. **协议改进**：RemoteControl 要从「文本 + 结果写日志」改成「请求 id + JSON 回包」，给出兼容旧命令的方案。
4. **安全边界**：
   - 只读本地视野；
   - 只做玩家本人能做的操作；
   - 每秒指令数上限；
   - 玩家随时一键收回控制（比如聊天 `-ai off`，或按键）；
   - 只监听本机 `127.0.0.1`。
5. **地标表**：把「中路一塔」「下路野区小营地」「肉山」等名字映射到坐标。坐标来源：`War3Angular/public/assets/maps/dota683/buildings.json`、`analyses/dota-neutral-camp-spawn-box.md`，以及眼位文档。

### D. 一个最小可行版本（MVP）建议

挑 5~6 个工具，说明用现有命令今天就能做到哪一步，需要先补哪几个逆向点，按优先级排。

## 输出

- 正文：`analyses/dota-ai-llm-mcp-control.md`
- 导图：`analyses/dota-ai-llm-mcp-control-mindmap.md`
- 脚本 / 导出：`artifacts/llm-mcp/`
- 文档开头写明：分析模型、分析目的、命名方式、分析时间、验证状态、证据（规则 `.agents/rules/war3-analysis-save.md`、`war3-reverse-toolkit.md`）。
- **不要改 War3Launcher / hooker 的代码**，只做逆向和设计。实机只读内存；不在游戏线程以外调用 JASS 原生函数。
