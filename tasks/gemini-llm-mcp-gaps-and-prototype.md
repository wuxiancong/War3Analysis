# 任务：补齐「大模型托管游戏」逆向缺口 + 做出第一个能跑的 MCP Server 原型

**给**：Antigravity Gemini　**布置时间**：2026-11-23　**工作目录**：`D:\Qt\workspace\War3Analysis`
**布置人**：Claude Opus 5.5（根据 `analyses/` 现有文档查缺补漏后整理）

## 背景

你之前写了两份文档：

- `analyses/dota-ai-llm-mcp-control.md`：接口设计，指挥层 / 执行层分开
- `analyses/dota-ai-llm-mcp-verify.md`：离线复核

到现在为止，**MCP Server 一行代码都还没有**，大模型还不能真正玩游戏。对照后来别的文档，还有下面这些缺口。

| # | 缺口 | 依据 |
|---|---|---|
| G1 | 两份文档的 RVA 大多只写了 1.27 / 1.26 / 1.24.4，**违反全版本规则**（`.agents/rules/war3-gamedll-all-versions.md`：`War3Launcher/versions` 下 11 个版本都要列） | `dota-ai-llm-mcp-control.md` §A1 表；`artifacts/llm-mcp/all_versions_rva*.txt` 只覆盖 25 个原生 |
| G2 | **插眼命令格式写错了**：verify 文档 B3+ 写「`0x11` + 物品对象 ID + flags `0x44`」，这一条已被真人抓包推翻。实际要用 **`0x12` + flags `0x40` + useslot + 物品对象 ID + X Y + 目标 `FFFFFFFF FFFFFFFF`**，`0x11/0x44` 下了不会生效 | `analyses/dota-ai-laning-routine.md`「插眼对照」一节 |
| G3 | **TP、跳刀、推推棒等其他点地物品**目前还发 `0x11 + 0x44`，**没有真人包对照**，很可能和假眼一样不生效 | 同上「同类风险」 |
| G4 | 可靠金钱 `EL0[pid]`、禁买活 `XS[pid]` 这类 **JASS 全局变量，怎么从 JASS VM 读出来**（指针链），没有给出来，各版本也没有 | verify 文档 A2 写的是「尚未给出」 |
| G5 | RemoteControl（`127.0.0.1:6120`）大多只回 `OK`，结果写进 `AiUnit.log`（比如 `units`）。**没有返回结构化局面的命令**，MCP 拿不到数据 | `.agents/rules/ai-autostart.md` §3；`War3Launcher/.agents/rules/ai-live-test.md` §8 |

## 要做的事

### 一、逆向（结果写进 `analyses/`）

1. **G2 + G3：点地物品 / 技能的命令格式规则**（最重要）
   - 在 `game.dll` 里找到真人点地使用物品时，`0x11` 和 `0x12` 分别是从哪条路径发出来的：`CNetCommandUnitOrder*` 怎么构造、flags `0x40` / `0x44` 从哪里来、为什么物品对地要用 `0x12` 加空目标。
   - 给出规则：**哪些物品 / 技能对地要用 `0x12` 格式，哪些用 `0x11`**，至少覆盖 TP（`useslot` 对建筑 / 对地两种）、跳刀、推推棒（对单位）、真眼 `I05H`、假眼 `I05G`。
   - 写出各版本的 RVA（11 个版本）。
   - 更正 `dota-ai-llm-mcp-verify.md` 里 B3+ 那一条：不要直接改原文，在原文 B3+ 这一行后面加「⚠ 2026-11-23 更正：见 …」，链接到你的新文档。
2. **G4：读 JASS 全局变量**
   - 从 `game.dll` 的 JASS VM 里，按变量名找全局变量（整数数组 / 布尔数组），用 `EL0`、`XS` 做例子，给出 11 个版本的指针链和偏移。
   - 只读。说明在哪个线程读、读图阶段能不能读（读图阶段调 JASS 原生会崩：`game.dll+0x2bd982`，见 `ai-autostart.md` 常见失败）。
3. **G1：补全版本表**
   - `dota-ai-llm-mcp-control.md` §A1 里的技能冷却（`CAgentTimer`）、Buff 链表、`FindAbility`、`CountBuffsEx` 这些内部函数 / 偏移，补齐 11 个版本的 RVA 表。
   - 原文档里没有直接证据的，标 ❓。

工具：`D:\Qt\workspace\War3Launcher\versions`（11 个 `game.dll`）、`D:\Qt\workspace\War3Script`（`war3map.j`）、`D:\Mpqeditor\Win32`、`D:\Ghidra_12.1.4`、`D:\REA`，规则见 `.agents/rules/war3-reverse-toolkit.md`。

### 二、MCP Server 原型（G5）

做一个**最小但能跑**的 MCP Server，让大模型（Claude / Gemini）通过 stdio 连上来。

- 位置：`D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-server\`（Python，`mcp` 官方 SDK；写 `README.md` 说明怎么装、怎么在 Claude Code / Gemini 里配置）。
- 后端：**只用现有的 RemoteControl 命令**（见 `War3Launcher/.agents/rules/ai-live-test.md` §8 和 `ai-autostart.md` §3），不改 `War3Launcher` / `hooker` 源码。
- 第一版工具（够大模型做「指挥层」决策就行）：

| MCP 工具 | 映射到 | 说明 |
|---|---|---|
| `game_status` | `status` | 状态机 + war3 进程在不在 |
| `get_state` | `units` + 读 `AiUnit.log` 新增部分 + `game_stats.log` | 解析成 JSON：英雄位置 / 血 / 蓝 / 等级 / 金钱 / 背包，视野内单位（只能是**可见的**），游戏钟。日志很大，只读新增部分（参考 `War3Launcher/scripts/ai_lane_test.py` 里的 `Tail`） |
| `move_to` | `move x y` | 支持地标名（中路一塔、上路符点……坐标从现有文档里取，表放在 `landmarks.json`） |
| `start_laning` / `stop` | `say -score start laning` / `say -score end` | 交给 hook AI 执行补刀、装符、插眼 |
| `buy` | `say -buy <名字>` | |
| `say` | `say <文本>` | 只允许白名单里的命令前缀 |

- 每个工具都要写清楚：返回 `OK` 只说明命令发出去了，到底有没有生效要靠 `get_state` 确认。
- 再写一份 **G5 的设计**（不写 hook 代码）：一个 `state` RemoteControl 命令直接回一行 JSON，字段对应 hook 里已经有的数据（`AiUnitState`、`g_aiMapClock`、背包……），给出字段表和每个字段在代码里的来源（文件 : 行号）。以后由 Claude 来实现。
- 写离线单元测试：用假的 6120 服务器和日志片段测解析和命令映射。

## 红线（必须遵守）

1. **现在不要开游戏、不要连 6120 发命令。** Claude 正在这台机器上跑影魔补刀实机测试，6120 端口和 war3 同一时间只能有一个测试用（`ai-live-test.md` 红线 7）。实机验证留到用户说可以的时候，先把步骤和脚本准备好。
2. **不要改** `War3Launcher/hooker`、`War3Launcher/managers`、`shared` 下的源码，也不要动 `build` 目录：Claude 正在改补刀代码、在编译，改了会冲突。
3. 不关任何进程，不改 `DebugConfig.ini` / `AutoStart`，只连本机。
4. 不 commit / push。输出里不要出现 ini 里的密码。
5. 每一条结论都要有独立证据（反汇编指令、`war3map.j` 行号、真人抓包）。拿不出证据的标 ❓，不要当成 ✅。

## 交付

| 交付物 | 位置 |
|---|---|
| 逆向正文（结论放最前面；文件开头写分析模型 / 分析目的 / 命名方式 / 分析时间 / 验证状态） | `analyses/dota-ai-llm-mcp-gaps.md` |
| 思维导图 | `analyses/dota-ai-llm-mcp-gaps-mindmap.md` |
| 扫描脚本、导出表 | `artifacts/llm-mcp-gaps/` |
| MCP Server 原型 + README + 测试 | `artifacts/llm-mcp-server/` |
| 对旧文档的更正标注 | `dota-ai-llm-mcp-verify.md` B3+ 行后追加，不删原文 |

报告时，**离线通过 / 实机通过 / 没测**三种情况分开写。
