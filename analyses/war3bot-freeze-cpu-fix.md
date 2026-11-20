# War3Bot 开局卡死 83 秒 + 空闲占 1.7 核：原因与修复

- 模型：Claude Opus 5.5
- 时间：2026-11-19
- 机器：ETVLFFTRPWJKTJ4（Windows Server 2022 云电脑，4 逻辑核，无 GPU）
- 目的：本地联调时游戏一直「等待主机」、开局卡在读图后退回大厅。

## 现象

1. War3Bot 空闲时占 1.4~1.8 个核（开机约 1 小时累计 CPU 6252 s），4 核机器总负载 100%，游戏中频繁「等待主机」。
2. 18:02 开局：倒计时到「4」（18:02:28）后 War3Bot **整个进程 83 秒没有任何一行日志**，到 18:03:51 才恢复；war3 在 18:03:27 等不到主机，从读图退回场景 1。最后一条日志：`C_S_REPLACE_SLOT … 开始执行物理接管流程`。没有崩溃 dump。

## 定位方法

本机没有调试器，用 Python 写了一个采样器（`scratchpad\sample32.py`）：从 64 位 Python 对 32 位 War3Bot 每个线程 `Wow64SuspendThread` → `Wow64GetThreadContext` 取 EIP / 栈，`dbghelp` 加载 War3Bot.pdb 符号化，150 次采样。

- 最忙的 6 个线程每个 21~38% 核，EIP 都在线程池（`ZwWaitForWorkViaWorkerFactory`）和不属于任何模块的 0x7F3xxxxx 代码里——这是 **WARP（Windows 软件 D3D 光栅器）JIT 出来的着色器代码**；进程加载了 `d3d10warp.dll`、`d3d11.dll`、`d3d12.dll`。即：Qt Quick 默认后端走 D3D11，没有 GPU 就落到 WARP，全帧在 CPU 上光栅化。
- 日志文件里 83 秒没有任何时间戳，而日志的时间戳是在调用 `log()` 时取的、写文件在单独的工作线程——说明这段时间**没有任何线程在调用 `log()`**，所有业务线程都被挡住了。

## 原因

1. **`Logger::handleFlush`（主线程，每 200 ms）持有 `m_bufferMutex` 期间 emit `normalLogsBatched` 等信号。** QML 的 `Connections { target: logger }` 和 Logger 同在主线程 → 直接调用，整个 `logController.appendBatch` 在锁内执行；而每个线程调用 `Logger::log()` 都要拿 `m_bufferMutex`（logger.cpp:535）。主线程处理一大批日志时，所有记日志的 Bot 线程（包括开局倒计时、游戏连接）全部卡在这把锁上。
2. **`appendBatch` 很慢**：逐行 `append`，超过 5000 行上限后每行一次 `displayLogModel.remove(0)`（while 循环），ListView 不停重排；War3Bot 每秒写 20~750 行（卡死前那一秒 480 行、恢复那一秒 752 行）。
3. **整窗 `DropShadow`**（main.qml:216，30 采样，source = 整个 mainRect）：窗口里任何变化都要把整窗重新模糊一遍，在 WARP 上非常贵。1 + 2 + 3 叠加：主线程长时间占满 → 持锁 → 全进程卡死。

## 修复

| 文件 | 改动 |
| :--- | :--- |
| `War3Bot/src/logger.cpp` `Logger::handleFlush` | 锁内只把三组缓冲区 `swap` 出来，**释放锁后再 emit**。QML 再慢也不会挡住记日志的线程。 |
| `War3Bot/main.qml` `logController.appendBatch` | 日志页不可见时只记 `allLogsArray`、不动 ListView（切回日志页时 `rebuildFilteredView` 整体重建一次）；超出上限时 `remove(0, excess)` 一次删完，不再逐行 `remove(0)`；一批超过上限只留最后 5000 行。 |
| `War3Bot/src/main.cpp` | 创建 QGuiApplication 前：未设置 `QT_QUICK_BACKEND` 时设为 `software`（Qt Quick 软件渲染，只重绘变化区域）。代价：`DropShadow` 不显示（只是窗口边缘阴影）。有独立显卡想用硬件渲染：启动前设置环境变量 `QT_QUICK_BACKEND`（空值 = Qt 默认后端）。 |

## 验证

| 场景 | War3Bot CPU |
| :--- | :--- |
| 修复前（默认后端 → WARP），空闲 | 178% 核 |
| 只修 handleFlush / appendBatch，空闲 | 178% 核（CPU 问题在渲染） |
| `QT_QUICK_BACKEND=software`（环境变量试验） | 14% 核，不再加载 WARP / D3D11 / D3D12 |
| 修复后（代码默认 software），空闲 | 13% 核 |
| 修复后，对局中 | 25% 核 |

- 18:28 开局：倒计时、读图（38 s）、进入对局（场景 8）正常；倒计时到对局期间 War3Bot 日志最长间隔 4.5 s（正常的周期日志间隔），没有再卡死。
- 仍然存在：对局中 war3 自身占约 2.5 个核（同样没有 GPU），机器总负载仍接近 100%；但 War3Bot 不再抢 CPU，主机响应不再被拖住。
