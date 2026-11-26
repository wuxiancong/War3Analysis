# 任务：英雄朝向——读取、单位换算、转身速度、让英雄转向（全 11 版）

**给**：Antigravity Gemini　**布置时间**：2026-11-25　**工作目录**：`D:\Qt\workspace\War3Analysis`
**布置人**：Claude Opus 5.5

## 背景

用户在做 AI 囤野：用 `-mark pos` 在游戏里标「拉野站位」，AI 按标记站位、xx:50~:53 打一下野怪再往开口方向走（见 `analyses/dota-neutral-camp-openings.md`）。
用户接下来要让 `-mark pos` **不光记位置，还要记英雄朝向**（站在那里面朝哪边），AI 到位后也要转到同样的朝向再出手。

现有资料只有一半，**没有核实过**：

- `analyses/war3-unit-movement-fields.md`：朝向在位置对象节点 `+0x90`（弧度），`+0x8C` 是目标朝向；朝向函数读 `+0x90` 后乘一个**运行期才填的常数**换成角度（1.26 乘数地址 `0x6FAAE60C`、1.27 `0x6FB59460`，文件里是 0）；第 177 行表里有各版 `GetUnitFacing` 的地址。文档自己写明「没有和 `GetUnitFacing` 的返回值对过」。
- `analyses/dota-lane-creep-speed-profile.md`：小兵 `propWin`（推进窗口 60°）硬门控、出生朝向 270°。
- hook 里 JASS 原生是按名字表解析后在游戏线程调用的（`War3Launcher/hooker/war3hook_ai.cpp` 的 `AI_NATIVE_*` 枚举和名字表，如 `"GetUnitX"`、`"IsUnitVisible"`），**只读参考**。

## 要做的事

`War3Launcher/versions` 下**全部 11 个版本**都要给出 RVA（`.agents/rules/war3-gamedll-all-versions.md`），每条结论要有反汇编证据。

1. **读朝向**：`GetUnitFacing` 原生在各版的实现 RVA、调用方式（参数 / 返回值是 float 角度还是弧度、在 EAX 还是 ST0）、返回值范围（0~360？可以为负？）、角度约定（0° = 正东 +X、逆时针为正？与 `GetUnitX/Y` 世界坐标系一致吗）。核实它读的就是节点 `+0x90`，给出那个乘数常数的值（应是 180/π）和它在启动时被谁写入。
2. **当前朝向 vs 目标朝向**：`+0x8C`（目标朝向）和 `+0x90`（当前朝向）的关系；英雄转身时两者怎么变化；能否只读内存拿到（给出从单位句柄到节点的指针链，各版偏移）。
3. **转身速度**：英雄的转身速率（物编 `UnitBalance` / `UnitData` 的 `turnRate` / `propWin` 等字段，单位和含义）；6.83d 影魔 `Nfir`、冰女 `Hjai` 的数值；转 180° 要多少时间；转身时是否原地停下（英雄的 `propWin` 是多少）。
4. **让英雄转到指定朝向（玩家指令层面）**：玩家没有「设置朝向」指令，`SetUnitFacing` 只能脚本用。请确认用玩家动作包让英雄面向某方向的可行办法，并说明副作用：
   - 对身边很近的点下 move（0x12 + `0xD0012` + 空目标对象），能转向且几乎不位移吗？最小距离多少不会被引擎忽略？
   - 对远处点下 move 后立即 stop（`0xD0004`）/ hold（`0xD0019`）：转身是否在 stop 时被中断、朝向停在哪？
   - 哪种方式不会打断待机、不会触发自动攻击？
   给出动作包格式（参考 `War3Launcher/hooker/war3hook_ai.cpp` 的 `aiOrderTarget` / `aiOrderImmediate`，只读）。
5. **朝向与攻击 / 施法**：英雄出手攻击（`0xD000F`）前是否必须先转身对准目标？转身时间是否计入攻击前摇之前？这关系到囤野「出手到打中」的时间预算（现在实测 1.5~1.8s）。
6. **挂钩建议**：给出 Claude 在 hook 里实现「读英雄朝向」的推荐方式（加进 `AI_NATIVE_*` 名字表调用 `GetUnitFacing`，还是直接读内存），以及 `-mark pos` 记录朝向需要的数据格式建议（例如 `x y radius team facingDeg`，兼容旧文件）。
7. **验证**：不开游戏能做的验证（反汇编交叉引用）。能实机验证的写成步骤 / 脚本留给 Claude（例如：英雄面朝东站定，调 `GetUnitFacing` 应得 0；右键正北近点后应得 90；记录转 180° 用时）。

## 红线

1. **不要开游戏、不要连 6120**：Claude 在这台机器上跑实机测试。
2. **不要改** `War3Launcher/hooker`、`managers`、`shared` 源码，也不要动 `build` 目录。挂钩代码写成文档里的建议 / 伪代码，由 Claude 实现。
3. 不 commit / push。拿不出证据的标 ❓。
4. **注意机器负载**：这台虚拟机只有 4 核、8 GB，Claude 跑测试时 CPU 一满游戏就变慢、测试作废。大批量反汇编扫描尽量分批，别长时间占满 CPU。

## 交付

| 交付物 | 位置 |
|---|---|
| 正文（结论放最前面：各版 `GetUnitFacing` RVA 与读法、角度约定、转身速度、转向指令方案；文件开头写分析模型 / 目的 / 命名 / 时间 / 验证状态） | `analyses/war3-unit-facing.md` |
| 思维导图 | `analyses/war3-unit-facing-mindmap.md` |
| 扫描脚本、全版本 RVA 表、实机验证脚本 | `artifacts/unit-facing/` |
