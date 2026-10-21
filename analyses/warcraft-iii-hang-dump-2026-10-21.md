# Warcraft III 挂起 Dump 初步分析（2026-10-21）

## 摘要

`Z:\Temp\War3.DMP` 是 War3.exe 的完整内存用户态 dump，可用于离线查看应用内存和线程栈。当前证据**没有证明发生了崩溃**：dump 没有异常上下文，WinDbg 的 `0x80000003` 是调试器初始断点上下文，不应当作游戏异常。线程栈也没有显示任何线程正在 `d3d9.dll+0xE6500`（本次加载地址 `0x6E5D6500`）执行。

本次快照不足以确认挂起原因，也不足以统计 Reset 调用次数或确认分辨率切换是否经过某个具体调用点。若要判断阻塞，需要在真实卡住状态采集至少两份间隔数秒的 dump，并比较关键线程的指令位置、调用栈和等待对象；或者在 Reset 入口命中时记录调用栈。

## 样本与分析方式

| 项目 | 观察 |
|---|---|
| Dump | `Z:\Temp\War3.DMP` |
| 类型 | User Mini Dump File with Full Memory（应用数据可用） |
| 进程 | War3.exe；dump 中 PID 为十六进制 `0x4bb0`（十进制 19376） |
| Dump 时间 | 2026-10-21 04:11:01（UTC+8） |
| 进程运行时间 | 约 47 秒 |
| 分析方式 | x64 CDB 加载 `wow64exts` 并切换至 WOW64 Guest x86 上下文 |
| 输出记录 | `Z:\Temp\War3-hang-wow64-20261021-0420.txt` |

模块基址（仅对此次 dump 有效）：

| 模块 | 基址 | 结束地址（exclusive） |
|---|---:|---:|
| War3.exe | `0x00980000` | `0x00A0A000` |
| Game（game.dll） | `0x79D00000` | `0x7A9D8000` |
| d3d9.dll | `0x6E4F0000` | `0x6E682000` |
| hook.dll | `0x7AA80000` | `0x7ABE8000` |

模块基址和 RVA 来自该 dump，不应直接套用到其他运行或 Windows 版本。当前材料没有确认 game.dll 的文件 SHA-256、Warcraft III 精确版本或驱动版本。

## 崩溃还是挂起

- `.ecxr` 报告 `Minidump doesn't have an exception context`，所以 dump 没有可用的应用异常现场。
- `.exr -1` 出现的 `0x80000003 Break instruction exception` 对应调试器的初始断点上下文，**不能据此判定 War3 崩溃**。
- 早先 32 位 CDB 的 `!analyze -hang` 结果落在 WOW64 的线程查询路径，不能据此当作游戏根因。x64 CDB 切换至 Guest x86 后，才获得本次应用线程的 x86 栈。

结论：这是可用于观察卡住进程的内存 dump，但目前没有崩溃异常证据。是否确实是用户可见的挂起，以及 dump 是否采集于卡住后，仍依赖采集时状态。

## 关键线程观察

### War3/Game 主线程候选

线程 `0x6C98`（十进制 27800）的 x86 栈顶为：

```text
ntdll!NtQueryInformationThread
KERNELBASE!GetThreadPriority
Game!GameMain+0x12BB3D
Game!GameMain+0x34F51
War3.exe+...
```

这说明该线程快照当时位于线程信息/优先级查询路径。栈展开同时有缺少 unwind 信息的警告，因此 `GameMain` 上层帧应谨慎看待。单一时点无法证明线程在这里持续阻塞，也不能仅凭它说明分辨率切换逻辑卡在该位置。

### D3D9 与显卡驱动工作线程

- D3D9 线程 `0x524`（十进制 1316）在 `d3d9!ThreadAffinitizedWorkerThread<ProxyWindowCommands>::WorkerThread` 中等待 `MsgWaitForMultipleObjects`。这是工作线程等待消息/对象的栈形态，本身不是 Reset 卡死证据。
- 一个 NVIDIA 用户态驱动线程在 `WaitForSingleObject` 等待，另一个在 `WaitForMultipleObjects` 等待。驱动线程等待可能是正常同步；当前栈不足以判断等待是否永久或由哪个游戏线程触发。
- 本次 dump 的所列线程栈中没有看到 `d3d9.dll+0xE6500`。这只能说明采样时没有可见线程栈帧落在该地址，不能证明该地址从未执行或切屏时没有执行。

### hook.dll 自有工作线程

`hook!logWriterThread`、`gameJassVariableDataThread_1/_2`、`textureConvertThread` 等线程处于条件变量等待路径。若它们是按设计等待队列任务，这属于空闲状态；仅凭 dump 不能认定它们导致死锁。

## 对 Reset 调用点问题的结论

本 dump 没有命中时的调用栈/断点记录，因此不能回答“切屏时是否只有一个位置调用 Reset”。已知静态地址 `game.dll+0xECC1F` 是此前分析的一个版本中的调用点，`+0xECC22` 是该 `call` 的返回地址；这些静态事实不能证明本次 dump 对应相同版本，也不能证明其他路径不存在。

本次加载基址下，`d3d9.dll+0xE6500` 的进程地址为：

```text
0x6E4F0000 + 0xE6500 = 0x6E5D6500
```

要确认运行时调用者，应在目标进程实际映射该 D3D9 版本后解析模块内函数，并在入口处采集 `EIP`、线程 ID、调用栈和 `[esp]` 返回地址。不要把系统 DLL 的固定 RVA 当作跨系统版本的稳定函数身份；`[esp]` 也应与本次运行的 game.dll 映射范围和实际反汇编一起验证。

## 下一步建议

1. 确认游戏界面真正卡住后立即采集一份 dump，数秒后再采一份；比较主线程及图形相关线程的 EIP、栈和等待状态是否持续不变。
2. 若重点是 Reset 调用者，在已确认正确的 D3D9 函数入口设置**日志型断点/tracepoint**，记录命中时间、线程 ID、`[esp]`、调用栈和寄存器后自动继续，不要让每次命中都暂停游戏。
3. 每次运行同时记录 game.dll、d3d9.dll 的版本/哈希和加载基址，避免把其他版本的静态偏移用于当前进程。
4. 可将两份快照的线程状态与 hook 线程的队列/锁日志对应；只有持续稳定的相同等待关系或明确的锁所有者链，才足以进一步判断死锁。

## 证据限制

- 这是单次快照，不包含线程随时间变化的证据。
- 没有异常上下文，不能定位崩溃指令。
- 模块私有符号和 unwind 信息不完整；部分较深调用帧可能不准确。
- 没有 Reset 入口命中记录、完整运行时调用链或锁等待链。
- 因此本报告是 dump 线程栈的初步归纳，不是挂起根因结论。
