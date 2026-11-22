# 任务：落地「录像引擎回放 + hook 只读采样」（路线 B）的逆向与设计

**给**：Antigravity Gemini　**布置时间**：2026-11-21　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 背景

你上一份 `analyses/dota-replay-imitation-dataset.md` 推荐了**路线 B**：用 War3 引擎高速回放 `.w3g`，回放过程中由 hook 只读采样每个单位的坐标、血蓝、金钱、技能冷却，和录像里的动作对齐，生成「局面 → 操作」样本。它的第 223 行之后列了落地步骤。

这一步要把路线 B 涉及的引擎细节逆向清楚，并给出可以直接照着写代码的设计。**这次还是不改代码**：主会话核对后再实现。

已有相关文档，先读：

- `warcraft-iii-replay-reverse-speed-unlock-and-web-simulation.md`（录像倍速解锁）
- `warcraft-iii-1.27-replay-autosave-implementation.md`（录像自动保存）
- `dota-3d-replay-viewer-blademaster.md`
- `war3-unit-movement-fields.md`（单位字段）
- `dota-ai-llm-mcp-verify.md`（已核验的读取偏移：冷却、buff 等）

## 要回答的问题

1. **自动播放录像**
   - Launcher / hook 怎么不经人手直接打开一个指定的 `.w3g` 并开始播放：命令行参数？游戏内部的录像加载函数？
   - 怎么把倍速设到最大，以及能不能超过 8x：已有的倍速解锁文档有没有提到上限。
   - 播放结束怎么检测，以及怎么自动接下一个录像（批处理）。
   - 现有 hook 在 `replayMode` 下哪些功能被关掉了（代码里有 `g_pSharedData->replayMode` 判断），采样时要不要绕开。
2. **回放时的采样**
   - 回放中的游戏线程和 `GamePlaying` 时一样吗？`aiTick`（WndProc 定时器）还会跑吗？JASS 原生函数（`GetUnitX`、`IsUnitVisible`…）能不能在回放里安全调用？
   - 回放时**以哪个玩家的视野**为准？能不能逐个切换玩家视角，让每个玩家的样本都只包含他当时合法可见的信息？这一条是防作弊红线，模仿数据里不能有迷雾下的信息。
   - 高倍速下每秒能采多少帧，采样会不会拖慢回放、导致回放失步。
   - 回放进度时间（游戏内时间）怎么读，用来和 `.w3g` 动作时间戳精确对齐。
3. **对齐和数据**
   - 录像里的玩家编号、`0x6B` 事件和回放中的单位所属玩家怎么对应。
   - 每 0.5s 一条样本时，「下一步操作」怎么取：同一窗口里有多个动作怎么办？只有选择、没有指令的窗口怎么处理？
   - 和你定的 `imitation_dataset_schema.json` 对照：哪些字段路线 B 能拿到，哪些还要补。
4. **版本**：**凡是 `game.dll` 的函数和偏移，必须覆盖 `War3Launcher/versions` 下全部版本并列出各版 RVA**（规则 `.agents/rules/war3-gamedll-all-versions.md`）。
5. **落地方案**：给出 hook 侧和 Launcher 侧要加的模块、接口、文件格式、步骤顺序和工作量估计，以及一个最小可行版本（MVP）：先对 1 个录像跑通，输出多少条样本。

## 要求

- 实机验证只读。需要打开录像的话，先确认机器上没有正在进行的对局（主会话在跑卡兵测试时不要开 war3、也不要结束 war3）；不确定就写成「建议测试步骤」交给主会话。
- 不往游戏进程写内存，不在游戏线程以外调用 JASS 原生函数，不改 War3Launcher / hooker 代码，不下载外部文件。
- 输出：
  - 正文：`analyses/dota-replay-route-b-sampling.md`
  - 导图：`analyses/dota-replay-route-b-sampling-mindmap.md`
  - 脚本和导出：`artifacts/replay-route-b/`
- 文档开头写明：分析模型、分析目的、命名方式、分析时间、验证状态、证据（规则 `.agents/rules/war3-analysis-save.md`、`war3-reverse-toolkit.md`）。
