# 内存监测 + 游戏内内存面板（-mem）与设置面板命令（-settings）

- 模型：Claude Opus 5.5
- 时间：2026-11-19
- 目的：在魔兽因内存问题崩溃之前提前提醒玩家；把内存状态画到游戏画面上（可显示 / 隐藏 / 拖动 / 命令控制），并给设置面板加命令控制。
- 代码：`War3Launcher/hooker/war3hook_memhud.cpp`（新增），改动 `war3hook_threads.cpp`（memoryMonitorThread）、`war3hook_overlay.cpp`、`war3hook_gfx.cpp`、`war3hook_ai.cpp`、`war3hook_process.cpp`、`war3hook_internal.h`、`CMakeLists.txt`。

## 1. 为什么看这些指标

`war3.exe`（iCCup 安装版和 `versions\1.27.0.52240` 都一样）PE Characteristics = `0x0102`，**没有 LARGE_ADDRESS_AWARE**，所以即使在 64 位 Windows 上进程也只有 **2 GB 用户地址空间**。魔兽的内存崩溃基本都是地址空间问题，不是物理内存问题：

| 崩溃原因 | 指标 | 紧张（黄） | 告急（红） |
| :--- | :--- | :--- | :--- |
| 地址空间用完 | 已用 = `ullTotalVirtual − ullAvailVirtual` | ≥ 65%（≈1331 MB） | ≥ 80%（≈1638 MB） |
| 碎片化：总剩余够，但没有足够大的连续块（大纹理 / 模型申请失败） | 最大空闲连续块（VirtualQuery 遍历） | < 192 MB | < 64 MB |
| 持续增长（泄漏） | 地址空间增长速度（3 分钟窗口，≥60 s 才算） | ≥ 15 MB/分 且 15 分钟内到红线 | 3 分钟内到红线 |
| 页面文件不足（任何进程都申请不到） | 系统提交余量 `ullAvailPageFile` | < 1024 MB | < 256 MB |
| GDI / USER 对象到每进程 10000 上限 | `GetGuiResources` | > 6000 | > 8500 |
| 句柄泄漏 | `GetProcessHandleCount` | > 6000 | > 10000 |
| hook 自己的文字贴图缓存无上限增长 | `g_textCache.size()` | > 3000 | > 6000 |
| 系统物理内存不足（严重卡顿） | `ullAvailPhys` | < 512 MB | < 150 MB |

总级别 = 各项最高级别；原因 = 最高级别里优先级最高的一项（顺序同上表）。

**发现的隐患：`g_textCache` 没有上限**。`drawUIText` 每个不同的（文字, 字体, 字号, 颜色）都建一张贴图，只在 D3D 设备重置时清空。Ping HUD 的毫秒数、`-mark` 坐标提示等每出现一个新字符串就多一张。内存面板本身因此**逐字符绘制数字**（每个字符一张贴图，种类有限），标签用固定字符串。

本机（ETVLFFTRPWJKTJ4）17:52 游戏中实测：地址空间可用 1201 MB（已用 ≈847 MB），最大块 464 MB。

## 2. 监控线程改进（memoryMonitorThread）

- 采样改为 `memHudSample()`：除原来的可用地址空间 / 最大块 / 工作集外，增加私有提交量、系统物理内存 / 提交余量、GDI / USER、句柄、文字缓存、增长趋势和分级；返回值与原 `MemoryStatusResult` 兼容，原有的低内存清理逻辑不变。
- 最大块遍历从 `lpMinimumApplicationAddress` 到 `lpMaximumApplicationAddress`，并防止地址不前进时死循环（原来写死 `0xFFFFFFFF`）。
- 等待结束后立即释放 `g_memoryMonitorMutex`（原来整轮采样 / 清理都占着这把锁，`stopMemoryMonitor` 要拿它）。
- 日志：原来每秒一行（`MemoryDetail.log` 一局就到 5 MB），改为每 10 秒一行 `📊 [内存]` + 级别变化时立即写；容器统计 `📺 [监控]` 也改为每 10 秒一行。
- 预警：级别升高立即在游戏屏幕提示（自定义 UI 通知，id 前缀 `MEM`，最多 8 条）；告急每 60 s 重复、紧张每 180 s 重复；恢复充足时提示一次；告急时自动弹出内存面板（`-mem auto off` 可关）。

## 3. 内存面板

- 用现有 `processAndDrawPanel`（标题栏 / 边缘拖动、右键关闭、停靠，与设置面板同一套），面板名 `MemoryPanel`，默认 270×350，默认位置左侧 (12, 屏高×20%)。
- 圆形仪表两个半环（上下留缝）：
  - **左半 = 地址空间已用**，自下而上填充，越满越危险；左侧红色刻度 = 80% 红线。
  - **右半 = 最大可申请连续块**，自下而上填充，512 MB 为满格，越满越安全。
  - 各半环按自己那项的级别着色；中心是总体状态（充足 / 紧张 / 告急）+ 已用百分比；标题下装饰线 = 总体级别颜色。
- 下方明细：系统可用内存、系统提交余量、GDI / USER、句柄 / 文字缓存、增长趋势（各自按级别着色），有问题时最后一行显示原因类别。
- 显示状态和位置存 `hook.dll` 同目录 `mem_hud.ini`（拖动结束、右键关闭、命令修改时保存）。
- 半环用 `DrawPrimitiveUP(D3DPT_TRIANGLESTRIP)` 画（`memDrawArc`），渲染状态设置与 `drawMultiLayerRoundedRect` 相同；OpenGL 模式走 `oglDrawPrimitiveUP`（支持 TRIANGLESTRIP）。

## 4. 命令（聊天输入，`-` 和 `/` 都行）

| 命令 | 作用 |
| :--- | :--- |
| `-mem` / `-mem toggle` | 显示 / 隐藏内存面板 |
| `-mem show` / `-mem hide` | 显示 / 隐藏 |
| `-mem pos <x> <y>` | 移到指定位置（客户区像素） |
| `-mem reset` | 回到默认位置并显示 |
| `-mem auto on\|off` | 告急时自动弹出面板 开 / 关（默认开） |
| `-mem status` | 在屏幕上打出当前所有指标和原因 |
| `-settings` / `-settings toggle` | 显示 / 隐藏设置面板 |
| `-settings show` / `-settings hide` | 显示 / 隐藏（设置面板只在设置按钮可见时绘制，所以 show 会顺带强制显示按钮） |
| `-settings pos <x> <y>` / `-settings reset` | 移动 / 回到初始位置（绑定的设置按钮一起移动） |
| `-settings button show\|hide\|auto` | 强制显示 / 强制隐藏 / 跟随配置（`alwaysShowSettingsButton`） |

`-memory` = `-mem`，`-setting` = `-settings`。界面操作排队到渲染线程执行（`memApplyOps`），不在聊天线程直接改 `g_panelMap` / `g_btnMap`。

## 5. 测试

- 17:5x 编译通过（`[8/9] Linking CXX shared library hook.dll`，无错误 / 警告）。
- 18:02 开局（`mem_hud.ini` 预置 `visible=1`）：采样正常，每 10 s 一行 `📊 [内存]`，例如 18:04:23 `地址空间 516/2047 MB 最大块 730 MB | 提交 156 MB | 系统可用 2177 MB 提交余量 1682 MB | GDI 20 USER 25 句柄 4699 文字缓存 11`。没有新的崩溃 dump。
- **误报已修**：读图期间级别为「紧张」，原因是趋势 +125 MB/分（读图时内存正常上涨）。18:10 改为只在 GamePlaying 满 2 分钟后才算趋势，场景切换时清空样本。
- 这一局没能进到对局，不是内存面板的问题：**War3Bot 在开局倒计时中卡死 83 秒**（18:02:28 倒计时「4」之后到 18:03:51 没有任何一行日志，最后一条是 `C_S_REPLACE_SLOT … 开始执行物理接管流程`），war3 在 18:03:27 等不到主机退回场景 1。本机 War3Bot 平时也占约 1.4~1.7 个核（4 核机器总负载 100%），游戏中「等待主机」也是这个原因。
- 游戏内面板显示 / 拖动 / 命令：还没有看到画面，待进入对局后确认。
- 18:31 对局中：`📊 [内存] 充足 | 地址空间 916/2047 MB 最大块 468 MB … 趋势 +0.0 MB/分`（读图误报已消失）。

## 6. 2026-11-19 用户要求的调整

- 面板宽度 270 → **340**。
- **默认隐藏**：每局开始都隐藏，只记住位置（`mem_hud.ini` 里的 `visible` 不再读取）；用 `-mem` 打开。
- **地图加载完后才允许显示**：只在场景 GameLoaded / GamePlaying 时绘制；在此之前 `-mem` / `-mem show` / `-mem reset` 只提示「地图加载完后才能显示内存面板」；离开对局自动收起；读图期间的告急只做屏幕提示，不会在进图后补弹面板。
- 采样和屏幕预警不受影响（读图期间照常采样 / 记日志 / 告急提示）。
