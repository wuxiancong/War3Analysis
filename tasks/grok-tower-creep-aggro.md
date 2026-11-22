# 任务：逆向防御塔和兵线小兵的索敌 / 仇恨规则（给 AI 控线、反补、卡兵决策用）

**给**：Cursor Grok　**布置时间**：2026-11-21　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 背景

`analyses/dota-lane-speed-by-time.md`（Gemini）第四节用「兵线交汇点离己方一塔多远」来判断该不该卡兵。它假设塔射程 `700`、仇恨触发约 `650`，交汇点离塔 `< 650` 时敌兵进塔，兵线被反推。**这两个数字没有逆向证据。** 另外，AI 已有的「卡仇恨」（`-aggro draw` / `drop`，见 `dota-ai-tactics-library.md`）和补刀、反补也都依赖小兵怎么选目标、什么时候换目标。现在都是凭经验写的。

要把这些规则从引擎和地图里确认下来，AI 才能算准：

- 兵线会在哪相遇、相遇后往哪边推；
- 打敌方英雄会不会把小兵和塔的仇恨引到自己身上，以及要退多远、多久才脱离。

## 要回答的问题

1. **防御塔**
   - DotA 6.83d 各级塔（一 / 二 / 三塔、高地塔、基地）的攻击射程、索敌范围（acquire range）、攻击间隔、弹道速度。来源：物编 SLK、`war3map.j`。
   - 塔选目标的优先级：最近？先打先进范围的？小兵优先于英雄？
   - **英雄在塔范围内攻击敌方英雄时，塔会不会立刻转火英雄**，是引擎行为还是地图脚本？
   - 塔换目标的条件和间隔。
2. **兵线小兵**
   - 近战 / 远程 / 攻城车的索敌范围、射程。
   - 选目标的优先级，以及「英雄攻击英雄」时，附近小兵转火攻击者的判定：半径多大、持续多久、怎么解除（退出多远，或多久没再攻击）。
   - 引擎里对应的仇恨 / 求救（call for help）机制和参数，比如 War3 的 `CallForHelp` 半径、gameplay constants。
   - 小兵正在攻击时，被英雄挡路或换目标的行为（和卡兵、拉兵有关）。
3. **地图脚本层**：6.83d 有没有额外的仇恨脚本（比如英雄攻击英雄时给附近小兵下令），如有，给出 `war3map.j` 行号。
4. **对 AI 的结论**
   - 用于 `-aggro draw`（拉仇恨：A 一下敌方英雄再后退）：多远出手、退多远、几秒内小兵转回原目标。
   - 用于判断兵线推进：在什么条件下敌兵会「进塔」并被清掉，给出可以直接写进代码的判定条件，不用改代码。
   - 核对 Gemini 文档里的 `700` / `650`：对或不对，正确值是多少。

## 要求

- **`game.dll` 逆向必须覆盖 `War3Launcher/versions` 下全部版本，并在文档里列出各版 RVA**（规则 `.agents/rules/war3-gamedll-all-versions.md`），不能只做 1.24.4 / 1.26 / 1.27。
- 工具见 `.agents/rules/war3-reverse-toolkit.md`。
- 需要实机看的：只读内存，或按 `.agents/rules/ai-autostart.md` 开局，用 RemoteControl `units` 看单位位置和血量。
  - 不要往游戏进程写内存；
  - 不要在游戏线程以外调用 JASS 原生函数；
  - 需要发攻击指令验证的，写成「建议测试步骤」交给主会话。
- 输出：
  - 正文：`analyses/war3-tower-creep-aggro.md`
  - 导图：`analyses/war3-tower-creep-aggro-mindmap.md`
  - 脚本和导出：`artifacts/tower-creep-aggro/`
- 文档开头写明：分析模型、分析目的、命名方式、分析时间、验证状态、证据（规则 `.agents/rules/war3-analysis-save.md`）。
- 不改 War3Launcher / hooker 代码。
