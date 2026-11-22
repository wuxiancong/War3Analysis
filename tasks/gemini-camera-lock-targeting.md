# 任务：锁定英雄镜头的同时，能用 A 键补刀、能定向施法

**给**：Antigravity Gemini　**布置时间**：2026-11-21　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 问题

用户实测：**只要锁定英雄镜头（`-lock on`），就无法用 A 键补刀。**

要的结果：镜头一直锁着英雄，同时下面这些都和不锁时一样可用：

- A + 左键点单位（正补、反补）、A + 左键点地面；
- 单位目标、点目标、范围目标技能，以及需要选目标的物品；
- 选目标时的光标、悬停高亮、右键 / Esc 取消；
- 选目标时左键点小地图（攻击移动、对小地图施法）。

主会话已把「默认锁定」改成默认关闭，这只是临时规避，**不是本任务的答案**。「按 A 时临时解锁」也只能作为查不出根因时的兜底方案。

## 现在的实现（`D:\Qt\workspace\War3Launcher\hooker`，按函数名找，行号会变）

1. `war3hook_ai.cpp` → `aiSetCameraLockState`：开 = `SetCameraPosition` + `SetCameraTargetController(hero, 0, 0, false)`；关 = `ResetToGameCamera(0)`。
2. `war3hook_ai.cpp` → `aiTickCameraLock`：从 `aiTick` 调，在游戏窗口线程，定时器加上任意窗口消息触发（间隔可短到 15ms，鼠标一动就会很密）。每次：
   - 镜头离英雄 > 16：**再调** `SetCameraPosition` + `SetCameraTargetController`；
   - 1 < 距离 ≤ 16：**再调** `SetCameraTargetController`；
   - 距离 ≤ 1：不调。
3. `war3hook.cpp` → WndProc：左键按下 / 按住拖动落在「客户区左 22% × 下 28%」就当成点小地图，在游戏处理之前 `ResetToGameCamera` 临时解锁（`aiTryCameraLockMinimapLeftClickAt`）；右键处理完再恢复锁定。
4. `war3hook_jass.cpp`：各原生函数的调用封装和全版本 RVA。已有分析 `analyses/camera_lock_target_controller.md`（其中流程图写的 40ms / >100 已过时，以代码为准）。

## 待验证的假设（都只是猜测，没有证据，逐条证实或排除）

| # | 假设 | 怎么区分 |
|---|---|---|
| H1 | 目标控制器本身让 UI 进入受限状态，选目标模式起不来或不接受点击 | 只绑一次、不重调也复现 |
| H2 | 重复调 `SetCameraTargetController` 会取消或重置选目标模式 | 英雄完全静止（距离 ≤ 1、不重调）时正常，移动时失败 |
| H3 | `SetCameraPosition` 有副作用（取消选目标、清悬停单位、重置输入） | 只在距离 > 16 的分支触发时失败 |
| H4 | 镜头每帧移动，点击射线或悬停单位用的是过期坐标，点击落空 | 选目标模式还在，也有点击，但命令是点地面或目标不对 |
| H5 | 第 3 条的小地图近似矩形误判，点击途中解锁导致镜头跳变 | 只有点屏幕左下区域时失败，日志同时有「临时解除锁定」 |
| H6 | 其它 Hook（改键、智能施法、鼠标锁定）和锁定叠加 | 关掉这些功能后不复现 |

## 要做的事

1. **静态逆向**，画出两条链并标出交叉点：
   - 按 A / 技能键 → 进入选目标模式（对象、字段、进入 / 取消函数）→ 左键 → 射线取目标 → 发出命令；
   - `SetCameraTargetController`、`SetCameraPosition`、`ResetToGameCamera` 往下实际改了哪些对象和字段，有没有调用取消选目标、清悬停或关闭用户输入。
2. **定根因**：H1~H6 每条给「证实 / 排除 / 未定」和证据（版本、RVA、反编译片段）。需要实机才能定的，给用户能照着做的最短测试步骤和要看的日志：
   - `C:\War3Run\War3Launcher\logs\AiUnit.log`：`[Lock]` 行；
   - `C:\War3Run\War3Launcher\logs\ActionData2.log`：Type 0x12 的 Hex 第 3~6 字节是命令号（攻击 0xD000F、右键智能 0xD0003），用来分清「没发出命令」和「发了但目标不对」。
3. **给方案**，按优先级：
   1. 锁定和选目标真正共存（例如只绑一次不重调、换更底层且无副作用的跟随方式、只屏蔽边缘 / 键盘滚屏而不动目标控制器）；
   2. 选目标期间只暂停有副作用的那一个调用，画面仍跟随英雄；
   3. 兜底：选目标期间临时解锁，完成 / 取消后恢复。要给出可靠读「正在选目标」的方法，不能只监听 A 键（改键、技能、物品、点命令卡都会进入）。

   每个方案写明：改哪个函数、伪代码、线程、对不同步的影响、小地图点击和右键恢复怎么处理。
4. **全版本**：所有用到的 `game.dll` 函数和字段偏移，按 `.agents/rules/war3-gamedll-all-versions.md` 列出 `War3Launcher/versions` 下全部版本：
   1.0.17.5988、1.0.20.6048、1.20.4.6074、1.21.0.6263、1.22.0.6328、1.23.0.6352、1.24.1.6374、1.24.4.6387、1.25.1.6397、1.26.0.6401、1.27.0.52240。
   逐版核对，没确认的明确标「未确认」，不要按相邻版本推算后当成已验证。
5. **验收表**：锁定下，英雄静止 / 移动 × A 点单位、A 点地、单位技能、点技能、物品、小地图目标、取消，每格写预期日志。

## 限制

- 工具和路径见 `.agents/rules/war3-reverse-toolkit.md`。
- 只读：不注入、不写内存、不发游戏指令或网络包、不在游戏线程外调 JASS 原生。
- 不改 War3Launcher / hooker / Scripts，不编译、不安装、不提交。代码改动只写在分析文档里，由主会话实现。
- 不开局、不结束 war3 / Launcher、不动鼠标键盘：用户会在游戏里操作。

## 输出

- 正文：`analyses/war3-camera-lock-targeting.md`；导图：`analyses/war3-camera-lock-targeting-mindmap.md`
- 脚本和反编译片段：`artifacts/camera-lock-targeting/`
- 文档开头按 `.agents/rules/war3-analysis-save.md` 写明分析模型、分析目的、命名方式、分析时间、验证状态。
- **第一段先写结论**：根因是什么、推荐哪个方案、哪些还没实机验证。
