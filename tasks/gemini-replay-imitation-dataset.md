# 任务：把 War3 录像（w3g）解析成「局面 → 操作」数据集，给 AI 模仿学习用

**给**：Antigravity Gemini　**布置时间**：2026-11-21　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 背景

用户的目标是让大模型或本地 AI 程序托管整局游戏（接口设计见 `analyses/dota-ai-llm-mcp-control.md`）。要让 AI「像人一样打」，最好的数据来源是真人录像：每个玩家在什么局面下做了什么操作。

本机已经有录像：`C:\War3Run\iCCup Warcraft III\Replay\CC对战平台\<年>\<月>\<日>\*.w3g`，目前主要是本地测试局，英雄大多是冰女。

已有相关文档：

- `analyses/dota-3d-replay-viewer-blademaster.md`
- `dota-player-lasthit-habit-recorder.md`
- `dota-player-learn-habit-recorder.md`
- `dota-hero-ability-cast-flow.md`

先读这些，看已经有哪些 w3g 解析能力，不要重复做。另外 `artifacts/creep-block/` 下有 `w3g_item_orders.py` / `w3g_tree_targets.py` 两个已有脚本。

## 要做的事

1. **w3g 格式**：确认 1.27 录像的头、压缩块、玩家表、动作块（`0x1F` / `0x1E` TimeSlot）结构。列出 DotA 常用动作的格式：
   - `0x10` / `0x11` / `0x12` / `0x13` / `0x14`：无目标、点目标、单位目标、给物品、双目标；
   - `0x16`：选择；`0x17` / `0x18`：编队；
   - `0x19`：子组；`0x1A`：预选；
   - `0x60`：聊天；`0x66`：技能菜单；`0x68`：Ping；
   - `0x6B`：游戏缓存，DotA 用它同步击杀等。
   每种都要写清 OrderId 的含义，比如 `0xD0003` 是移动、`0xD000F` 是攻击。
2. **解析器**：写一个 Python 解析器，放在 `artifacts/replay-dataset/`。输入一个 w3g，输出：
   - 每个玩家的动作流：时间（ms）、动作类型、OrderId 的人类可读名、目标坐标 / 目标对象 ID、当时选中的单位；
   - 从 `0x6B` 或聊天里能拿到的事件：击杀、死亡、买活、塔倒；
   - 每个玩家的英雄（从选人动作或 `0x6B` 推断）。
3. **「局面」怎么补**：录像里只有操作，没有坐标。写清楚三条路线各自能拿到什么、精度和成本，并推荐一条：
   - 只用动作里的目标点近似英雄位置；
   - 用 War3 引擎回放录像，在回放时用 hook 采样单位坐标（我们已经有读坐标的能力，见 `war3-unit-movement-fields.md`）；
   - 用网页模拟（`dota-6.83d-web-gameplay-data-reverse.md` / `dota1-web-online-gameplay-architecture.md`）。
4. **数据集格式**：设计给模仿学习用的样本格式，比如每 0.5s 一条：局面特征（时间、英雄等级 / 金钱 / 位置、附近单位）→ 下一步操作类别和参数。
   - 用 JSONL 或 Parquet，写好 schema；
   - 对本机现有录像跑一遍，产出示例数据和统计：动作分布、APM、每类操作的占比。
5. **真人录像来源**：本机只有测试局，没有高手局。调研能合法获取的 DotA 6.83d 公开录像来源（只写来源和获取方式，不要下载），以及需要多少局才够训练一个「对线期」的模仿模型。

## 要求

- 只读录像文件。要处理的话先复制到 `artifacts/replay-dataset/data/`，不要改游戏目录。
- 不改 War3Launcher / hooker 代码。需要 hook 配合采样的，写成设计和「建议测试步骤」交给主会话。
- 不下载外部文件。
- 输出：
  - 正文：`analyses/dota-replay-imitation-dataset.md`
  - 导图：`analyses/dota-replay-imitation-dataset-mindmap.md`
  - 解析器、schema、示例数据：`artifacts/replay-dataset/`
- 文档开头写明：分析模型、分析目的、命名方式、分析时间、验证状态、证据（规则 `.agents/rules/war3-analysis-save.md`）。
