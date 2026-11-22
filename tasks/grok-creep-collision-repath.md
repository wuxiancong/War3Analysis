# 任务：逆向 War3 1.27 小兵被挡时的碰撞与绕行（给卡兵 AI 用）

**给**：Cursor Grok　**布置时间**：2026-11-21　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 背景

卡兵 AI 已经能读单位坐标、移速、当前指令（见你写的 `analyses/war3-unit-movement-fields.md`）。现在的问题是**下路卡兵在拐弯处总漏外侧那只兵**：外侧兵横向偏移约 −175，走到兵线距离 3300~4300 时绕过英雄跑掉。真人也在同一个弯漏兵。要知道引擎是怎么决定「被挡住的小兵什么时候、往哪边绕」的，AI 才能提前站位。

相关文档先读：`analyses/dota-ai-creep-block-positioning.md`、`dota-lane-creep-trajectory.md`、`dota-lane-creep-speed-profile.md`、`war3-unit-movement-fields.md`。

## 要回答的问题

1. **碰撞体积**：小兵（`esen`/`edry`/`ebal` 等）和英雄的碰撞半径从哪个字段读（单位数据 `collision`，CUnit 上的偏移）？两个单位「接触」的判定是半径之和还是格子（pathing grid，32 单位一格）占用？
2. **被挡时的处理**：移动中的单位撞上另一个单位，引擎是 (a) 原地等、(b) 局部绕行、还是 (c) 重新全局寻路？找到对应函数（1.27 RVA），以及触发重算的条件和**间隔**（多少 ms / 多少游戏帧重试一次）。
3. **绕行方向**：往左还是往右绕是怎么选的？是不是跟目标点方向、被挡单位相对位置、或者格子空闲情况有关？
4. **友方单位之间**：同一波小兵彼此是否也会绕（解释为什么外侧兵会被挤出去）？
5. **单位移动中途的路径点**：小兵走兵线时的 waypoint（`COrder +0x48/+0x50` 之外）是不是一串中间点？拐弯处的路径点坐标能不能读出来？

## 要求

- 多版本：至少 1.24.4 / 1.26 / 1.27 各给 RVA（游戏 dll 在 `War3Launcher/versions/*/game.dll`）。
- 工具见规则 `.agents/rules/war3-reverse-toolkit.md`（Ghidra / hooker / MPQ）。**不要在游戏线程以外调用 JASS 原生**；实机只读内存。
- 结果保存：`analyses/war3-unit-collision-and-repath.md`（正文）+ `analyses/war3-unit-collision-and-repath-mindmap.md`（导图）；脚本和导出放 `artifacts/unit-collision/`。
- 文档开头表格写明：分析模型、分析目的、命名方式、分析时间、验证状态、证据。
- 最后一节写「对卡兵 AI 的建议」：英雄应站在兵前方多远、偏向哪一侧，才能让外侧兵不触发绕行；给出可以直接写进 `war3hook_ai_tactics.inl` 的判定条件（不用改代码）。
