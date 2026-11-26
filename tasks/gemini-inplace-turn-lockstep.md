# 任务：用玩家动作包让英雄**原地**转到指定朝向（不位移）——锁步回合 / 指令执行时序 / 可用指令（全 11 版）

**给**：Antigravity Gemini　**布置时间**：2026-11-25　**工作目录**：`D:\Qt\workspace\War3Analysis`
**布置人**：Claude Opus 5.5

## 背景

hook 新加了 `-face <度>`（给 `-mark arc` 标拉野弧度用，用户不想用右键转向）。你上一份 `analyses/war3-unit-facing.md` 的读朝向（`GetUnitFacing`，1.27 `0x1E6130`）实机验证**正确**，但「让英雄转向」的三种做法实测都不理想：

| 做法 | 实测（2026-11-25，影魔，本地自建服 1 人房） |
| :--- | :--- |
| ① 你推荐的方案 A：往反方向退 32 码再走回原位 | **朝向是乱的**：目标 45° 实际 74°、0° → 295°、120° → 288°、180° → 27°（32 码太短，像被当作已到达 / 被碰撞挤开） |
| ② 往目标方向 400 远下 move，每帧读 `GetUnitFacing`，到 ±10° 立刻 hold（`0x10 + 0xD0019`） | 朝向**对了**，但英雄**走出几十码**（hold 要再过一个网络回合才执行） |
| ③ 下 move 后不等朝向，隔 60 / 120 / 180 / 240ms 发 hold，转不够就加长再来 | 朝向对了，**仍有小位移**（用户：「没有原地转动，但是有进步，只是移动了很小距离」） |

实现在 `War3Launcher/hooker/war3hook_ai_tactics.inl` 的 `aiStartFaceTurn` / `aiTickFaceTurn`（只读参考）。动作包通过 `aiOrderTarget`（0x12）/ `aiOrderImmediate`（0x10）入队，走 `EnqueuePlayerAction` → 网络锁步。

## 要做的事

`War3Launcher/versions` 下**全部 11 个版本**都要给出 RVA（`.agents/rules/war3-gamedll-all-versions.md`），每条结论要有反汇编证据。

1. **锁步回合与指令执行时序**：
   - 本地动作包从 `EnqueuePlayerAction` 入队到在游戏里**真正执行**（单位收到指令）要经过几个回合？回合长度（ms）由什么决定（局域网 / 战网 / 自建服、`latency` 设置、主机下发的回合间隔）？给出读取当前回合间隔的方法（全局变量 / 函数，各版 RVA）。
   - 同一个回合里先后入队的两条指令（move 再 hold）是不是在同一帧按顺序执行？执行时转身有没有机会发生（move 设了目标朝向 `+0x8C`、hold 立刻清掉）？
2. **转身和移动的引擎细节**：`CPoPosCl::StepTurnAndMove`（1.27 `0x11CFF0`）里，|Δθ| ≥ `propWin` 时是不是「本帧只转身、不移动」？转到 `propWin` 以内的那一帧就开始移动吗？转身每帧的角速度（`turnRate` 弧度 / 帧，帧率 32Hz？）。由此算出：要让英雄**不位移**地转到 θ，hold 应该在 move 之后的哪个时间窗口内执行（以回合 / 帧计）。
3. **有没有不位移的转向指令**：除了 move（`0xD0012`）/ smart（`0xD0003`），玩家动作包里有没有能**只改朝向不移动**的指令或用法？请逐个核实并给证据：
   - 对**英雄自己**下 smart / move（目标对象 = 自己）？
   - 对点下 `0xD0019`（hold）带坐标（0x11 / 0x12 形式）？引擎会不会用坐标设朝向？
   - attack-ground / patrol（`0xD0016`）到很近的点？
   - 「对点施法但技能在冷却 / 没学」的指令，会不会先转身再报错、不位移？（DotA 英雄常见：施法前转身）
   - 其他：选中英雄后 `0x1E`/`0x1C` 之类的非指令动作、或物品对点使用（无物品时）。
4. **方案 A 为什么失败**：寻路「已到达」容差是多少（多近的 move 会被忽略或判到达）？碰撞半径对短距离 move 的影响？给出最小可用退后距离，以及「退 d 再走回」的总位移误差。
5. **推荐方案**：给出一个能在本地自建服 / 战网都工作的「原地转向」方案（伪代码，写清每一步发什么动作包、隔多久、怎么用 `GetUnitFacing` 校验），目标：最终朝向误差 ≤ 10°，位移 ≤ 10 码。Claude 会照着实现并实测。
6. **验证**：静态能验证的先验证；实机步骤写成脚本 / 说明留给 Claude（hook 日志 `AiUnit.log` 的 `🧭 [Face] 英雄面朝 N°…| 移动了 M（第 k 次）` 可直接对照）。

## 红线

1. **不要开游戏、不要连 6120**：Claude 正在这台机器上跑囤野实机测试。
2. **不要改** `War3Launcher/hooker`、`managers`、`shared` 源码，也不要动 `build` 目录。改法写成文档里的建议 / 伪代码，由 Claude 实现。
3. 不 commit / push。拿不出证据的标 ❓。
4. **注意机器负载**：这台虚拟机只有 4 核、8 GB，Claude 跑测试时 CPU 一满游戏就变慢、测试作废。大批量反汇编扫描尽量分批，别长时间占满 CPU。
5. **文件存到 `D:\Qt\workspace\War3Analysis`**（U 盘，见交付表）。上一份任务（`tasks/gemini-neutral-creep-leash-kite.md`）的结果在这里找不到，请确认那份正文、导图、`artifacts/neutral-leash/` 存在哪里，一并放回这个目录。

## 交付

| 交付物 | 位置 |
|---|---|
| 正文（结论放最前面：锁步回合与执行时序、不位移转向的可行指令 / 时序窗口、推荐方案伪代码；文件开头写分析模型 / 目的 / 命名 / 时间 / 验证状态） | `analyses/war3-inplace-turn-lockstep.md` |
| 思维导图 | `analyses/war3-inplace-turn-lockstep-mindmap.md` |
| 扫描脚本、全版本 RVA 表、实机验证脚本 | `artifacts/inplace-turn/` |
