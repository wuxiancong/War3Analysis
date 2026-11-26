# War3Launcher 退房 / 对局结束后自行消失 — 原因分析

- 模型：Claude Opus 5.5（Claude Code 子会话）
- 时间：2026-11-25 21:50 左右
- 目的：找出 War3Launcher 在退房 / 对局结束后消失的原因，并给出修复方案（未改代码、未编译、未提交）
- 范围：`C:\War3Run\War3Launcher\logs` 的日志、`crash_launcher.dmp`（19:18）、`D:\Qt\workspace\War3Launcher` 源码
- 命名：本文件 `war3launcher-exit-after-room-leave.md`

## 结论

三次"消失"的触发原因各不相同，但都不是"退房这个动作本身让程序退出"：

| 时间 | PID | 怎么退出的 | 证据 |
|---|---|---|---|
| 19:18:22 | 3168 | 正常退出流程（`aboutToQuit`）**执行到一半崩溃** → 写出 dump | `main.log` 19:18:22.399 依次清理 IPC → 监视 → 数据 → 网络线程，"网络线程已安全终止"那一行没有写出来；dump 是 AV |
| 20:53:15 | 10340 | **被硬杀**（TerminateProcess 一类），没有任何退出日志 | 没有 `aboutToQuit` 日志、没有 gracefulExit、没有 dump、没有 WER 事件；日志停在房间列表刷新中间 |
| 21:20:57 | 240 | **有人点了 QML 菜单里的「退出程序」**，干净退出 | `network_lifecycle.log` 21:20:57.519 `gracefulExit` 出现在 `aboutToQuit`（.520 起）**之前**，而 QML 里只有两个「退出程序」菜单项会先调 gracefulExit |

21:20 日志里的 `onDisconnected` / `cleanupRoomUIState` / `[页面组件销毁]` 是退出**造成的结果**（`RoomManager::onAppQuitCleanup` 在 `aboutToQuit` 里发出 `/unhost` 和复位信号），不是原因。

## 1. 19:18 崩溃：IPC 线程先解除了共享内存映射，网络线程还在写

### dump 内容（Python `minidump` 解析）

- `EXCEPTION_ACCESS_VIOLATION`，**写** `0x07100001`（参数 `[1, 0x7100001]`）
- 出错位置 `War3Launcher.exe+0x14ac5f`，线程 `0x2490`；`EAX=0x07100000`（64 KB 对齐，是 `MapViewOfFile` 返回的典型基址）
- 线程栈上有 `Qt5Network.dll` / `ws2_32.dll` / `mswsock.dll` 帧 → 是 **NetworkBackendThread**
- 当时的 exe 是 19:45 之前的旧版本，现在的 PDB 符号化不了，所以 0x14ac5f 对应哪个函数是推断出来的（推断过程见下）

### 为什么写 `0x07100001` = 写 `SharedData::sessionId`

- `shared/SharedMemory.h:837` `#pragma pack(push, 1)` … `:1043` pop，`SharedData`（`:856`）第一个字段是 `uint8_t my_pid`，第二个字段是 `uint32_t sessionId` → `sessionId` 的偏移是 **1**
- 网络线程写 `sessionId` 的地方：
  - `managers/NetworkManager.cpp:1406-1407` `resetConnectionState()`（`gracefulExit → stopListening → cleanupSockets` 会调到）
  - `managers/NetworkManager.cpp:4056-4057` 注册成功回包时
- 这两处都是"先判断非空，再写入"，判断和写入之间没有任何同步手段

### 为什么这时映射已经没了

- `main.cpp:962-965` 按 IPC → GameMonitor → DataMonitor → Network 的顺序建线程，各自的 `aboutToQuit` 槽也按这个顺序连接，所以**退出时最先跑的是 IPC 清理**
- `main.cpp:682-693` IPC 线程的槽 → `IpcManager::cleanup()`（`managers/IpcManager.cpp:53-57`）`UnmapViewOfFile(m_pSharedData); m_pSharedData = nullptr;`
- 在 IPC → 监视 → 数据这几个阻塞清理执行期间，网络线程的事件循环**还在跑**（UDP 注册重试 / 收包），19:18:16 刚自动重连成功，正处在注册阶段
- 网络线程刚判断完 `m_pSharedData` 非空，IPC 线程就把映射解除了，接着网络线程写 `->sessionId` → 写到已经释放的 `0x07100000+1` → AV
- 其他线程（GameMonitor、DataMonitor、主线程的 GameManager 等）里，`auto *sharedData = IpcManager::instance().m_pSharedData;` 这种先缓存指针再使用的写法有几十处，同样存在这个风险

### 另外两个小问题

- `managers/NetworkManager.cpp:62-67` `~NetworkManager()` 也会 `UnmapViewOfFile(IpcManager::instance().m_pSharedData)`，解除的是别的类拥有的映射；`NetworkManager::m_hSharedMemory`（`NetworkManager.h:467`）从来没有被赋值，所以这段现在不会执行，属于死代码，但留着很危险
- 崩溃处理（`main.cpp:100-120` `exceptionFilter`）
  - 用的是相对路径 `crash_launcher.dmp`，每次 `CREATE_ALWAYS` 覆盖上一次
  - 返回 `EXCEPTION_EXECUTE_HANDLER` 让进程静默结束，所以**不会产生 WER 事件**，这和"应用日志里没有崩溃事件"对得上
  - 只能捕获 SEH 异常；`__fastfail`、栈溢出、`abort` 走不到这里

## 2. 20:53 硬杀

- `main.log` 在 20:49:24 之后、21:01 重启之前**没有任何"收到退出信号"日志**；`network_lifecycle.log` 在 20:5x 没有 gracefulExit；没有新的 dump
- `War3launcher.log` 停在 20:53:15.155 的房间列表刷新日志中间
- 能这样无声结束一个管理员进程的，只有 TerminateProcess 一类：
  - `Scripts\Restart-War3Launcher*.ps1` / `Stop-War3Elevated.ps1`（`taskkill /F`，需要点 UAC）
  - `Sync-War3Run.ps1 -StopRunning`（需要在管理员 shell 里跑）
  - 任务管理器
- 本机 UAC 是 `ConsentPromptBehaviorAdmin=5`，Agent 的 shell 不是管理员，所以 Agent 的 shell 不点 UAC 就杀不掉 Launcher
- 在会话记录里搜 `Restart-War3Launcher` / `Stop-War3Elevated` / `taskkill`，没有搜到结果（搜索可能不完整）
- **凶手确定不了**。也不能完全排除 SEH 以外的进程终止（`__fastfail` / 栈溢出），但这类终止一般会留下 WER 1000 / 1001 事件

## 3. 21:20 点了「退出程序」

- 21:18:31 的建房没有对应的 `ai_control` 日志 → 是通过 UI 手动建的房（有人在操作界面）
- 21:20:57.519 `NetworkManager::gracefulExit` 被调用，紧接着 `aboutToQuit`（RoomManager ExitHandler 在 .520、main.log 线程清理在 .561）
- `gracefulExit` 只有三个调用点：`main.qml:88`（onClosing，前提是 `isReallyQuitting` 已经被置为 true）、`main.qml:317`（**托盘菜单「退出程序」**）、`main.qml:2118`（**头像下拉菜单「退出程序」**，就在「切换账号」下面），另外还有 `main.cpp:656`（aboutToQuit 里那一次，就是 .566 的第二条）
- 这段时间 `ai_control.log` 没有 RemoteControl 命令，所以不是 `quit` / `exit` 命令（`AiControlManager.cpp:525-529`）
- 关闭按钮已经被禁用（`main.cpp` 里的 `disableCloseButton`），onClosing 也只会把窗口隐藏到托盘
- `CustomMenuComponent` 只响应鼠标点击（`components/CustomMenuComponent.qml:19-24`）；RemoteControl 的 `click` / `key` 都是 `PostMessage` 给 War3 窗口的（`AiControlManager.cpp:61-157`），点不到 Launcher 菜单
- 所以是一次真实的鼠标点击：人点的，或者某个会话用 computer-use 点的。**需要确认当时是谁在操作界面**

## 修复方案（未实施）

### A. 退出时最后才解除共享内存映射（修 19:18 的崩溃，优先做）

1. `main.cpp`：把四个分散的 `aboutToQuit` 槽合成一个，按 **Network → DataMonitor → GameMonitor → IPC** 的顺序停线程（先停使用者，再停拥有者）。最小改法：在 `main.cpp:962-965` 把 `setupNetworkManagerThread()` 挪到第一个调用（槽按连接顺序执行）
2. `IpcManager::cleanup()`（`IpcManager.cpp:53-57`）：只置空、关闭事件句柄，**不 `UnmapViewOfFile`**（进程退出时系统会回收），这样即使还有线程缓存着旧指针，写入也不会 AV。比第 1 条更稳，建议两条一起做
3. 删掉 `~NetworkManager()` 里的 `UnmapViewOfFile(IpcManager::instance().m_pSharedData)`（`NetworkManager.cpp:64-67`），以及没人用的 `m_hSharedMemory`

### B. 让以后的崩溃 / 退出都能查清楚

1. `exceptionFilter`（`main.cpp:100`）：dump 写到 `applicationDirPath()/crash/crash_launcher_yyyyMMdd_HHmmss_PID.dmp`，不覆盖；dump 类型加上 `MiniDumpWithThreadInfo | MiniDumpWithIndirectlyReferencedMemory`；同时直接用 `WriteFile`（不经过 Qt）往 restart 日志追加异常码和地址
2. `Sync-War3Run.ps1`：把 `War3Launcher.pdb` 一起同步，并按 exe 时间戳另存一份 `pdb\War3Launcher_<时间>.pdb`，这样旧 dump 也能符号化
3. 记录每一个退出入口（立即落盘）：两个「退出程序」菜单项（区分是托盘菜单还是头像菜单）、`AiControl quit`、`lastWindowClosed`、`WM_QUERYENDSESSION`
4. `Restart-War3Launcher*.ps1` / `Stop-War3Elevated.ps1` / `Sync-War3Run -StopRunning`：杀进程前往 `logs\launcher_kill.log` 写一行（时间、脚本名、调用者），以后再出现 20:53 这种硬杀就能对上

### C. 「退出程序」二次确认（防 21:20 这种误点）

- 托盘菜单和头像菜单的「退出程序」加确认对话框；或者在 AI 测试期间（`AiControlManager` 正在运行 / RemoteControl 有连接时）提示"测试进行中，确定退出？"
