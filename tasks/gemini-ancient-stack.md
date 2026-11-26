# 任务：远古野点（Q4 / U4）怎样稳定囤 3 波以上（DotA 6.83d，全 11 版）

**给**：Antigravity Gemini　**布置时间**：2026-11-25　**工作目录**：`D:\Qt\workspace\War3Analysis`
**布置人**：Claude Opus 5.5

## 背景

AI 囤野（hook `war3hook_ai_tactics.inl` 的 `aiTickStack` / `aiTickDomStack`）在 :50~:53 打一下野怪、往用户标的弧度方向带走，:00 时封野盒空了就会刷新。普通野点能囤 3~4 波，但**远古野点（天灾 Q4、近卫 U4）实测很难超过 3 波**：

- 上一把支配怪（`ncnk` 半人马可汗，1100 血）囤 U4，打远古（`nbwm` 等）多次「没打中（超时）」，囤上 3 波后基本就囤不动了。
- 用户原话：「你上一把总是在远古野点，那里很难囤积三波以上（可能需要特殊办法）」。

已有资料（先读，不要重做）：
- `analyses/dota-neutral-camp-openings.md`（12 个野点开口、站位 A / 出口 B）、`analyses/dota-neutral-camp-spawn-box.md`（封野盒）、`artifacts/neutral-stack/camp_routes.json`
- `analyses/dota-683d-helm-dominate-stack.md`（支配头盔、控制支配怪）
- `tasks/gemini-neutral-creep-leash-kite.md`（拴绳 / 回巢，结果在本目录没找到；有的话请一并放回）

## 要做的事

`War3Launcher/versions` 下**全部 11 个版本**都要给出 RVA（`.agents/rules/war3-gamedll-all-versions.md`），每条结论要有反汇编 / 地图数据证据（`war3map.j` 行号）。

1. **为什么远古难囤**：远古野怪（黑龙 `nbdk`/蜉蝣 `nbwm`/雷霆蜥蜴 `n0LC`/`n0LD` 等）的攻击射程、移速、获取目标范围（acquire range）、拴绳距离、回巢速度；和普通野怪比哪里不一样。囤 N 波后野怪变多、回巢时间变长，:00 时封野盒里还有野怪 → 不刷新，给出每多一波需要多拉多远 / 多早出手的估算。
2. **Q4 / U4 的封野盒和开口**：两个远古点的封野盒（脚本 r1 rect）、出生点，哪些方向能把野带得最远、最快出盒；`camp_routes.json` 里 Q4、U4 各只有 2 条路线，是不是还有更好的路线。
3. **真人玩家囤远古 3 波以上的办法**（6.83d 时代常见打法），逐个评估可行性：
   - 提前出手（:49 或更早）？——注意用户规则：普通囤野只能 :50~:53 出手，如果远古必须例外请给出理由和数据，由用户决定。
   - 远程英雄 / 远程支配怪在最大射程打、带更远；或者用技能 / 范围伤害一次拉动全部远古。
   - 两个单位配合（英雄 + 支配怪：一个打、一个接着带；或者分两批拉）。
   - 选哪种支配怪最适合囤远古（射程、移速、血量），能不能扛住远古的伤害。
4. **给 hook 的实现方案**（伪代码 / 状态机，不改源码）：远古点专用的出手时机、站位、带野距离 / 方向、几只单位怎么配合；以及「什么情况下放弃远古、换普通野点」的判断条件。
5. **验证**：静态能验证的先验证；实机步骤写成说明留给 Claude。

## 红线

1. **不要开游戏、不要连 6120**：Claude 正在这台机器上跑天灾囤野实机测试。
2. **不要改** `War3Launcher/hooker`、`managers`、`shared` 源码，也不要动 `build` 目录。改法写成文档里的建议 / 伪代码，由 Claude 实现。
3. 不 commit / push。拿不出证据的标 ❓。
4. **注意机器负载**：这台虚拟机只有 4 核、8 GB，测试时 CPU 一满游戏就变慢、测试作废。大批量反汇编扫描分批做，别长时间占满 CPU。
5. **文件存到 `D:\Qt\workspace\War3Analysis`**（见交付表）。

## 交付

| 交付物 | 位置 |
|---|---|
| 正文（结论放最前面：远古难囤的原因与数据、Q4 / U4 最佳路线、可行的 3 波以上办法、hook 状态机；文件开头写分析模型 / 目的 / 命名 / 时间 / 验证状态） | `analyses/dota-683d-ancient-stack.md` |
| 思维导图 | `analyses/dota-683d-ancient-stack-mindmap.md` |
| 扫描脚本、全版本 RVA 表、路线计算 | `artifacts/ancient-stack/` |
