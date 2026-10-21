# Warcraft III 1.27：切换分辨率时 `GameBeforeD3DXDoEndScene` Hook 崩溃分析

## 结论摘要

**最优先排查的是设备生命周期与空设备保护，而不是面板坐标计算。** 1.27 使用 D3D9；选项中切换显示分辨率会改变呈现参数，并进入设备 `Reset`/恢复流程。普通焦点切换主要是窗口状态变化，通常不会立即替换呈现参数和重建整个显示模式；但独占全屏下 Alt+Tab 也可能让设备丢失并随后 `Reset`，两者不能简单等同为“普通切屏绝不会 Reset”。

项目在 `game.dll+0xECFF0` 安装此 inline hook。其 callback 从 renderer 的 `+0x584` 读取 D3D device 指针，随后有两个高风险点：

1. **潜在无效指针 COM 调用：** `g_oldWndProc == nullptr` 时，callback 先调用 `g_fnGetCreationParameters(device, ...)`，设备检查却在之后。若窗口过程挂钩未成功，`g_oldWndProc` 会保持空值并使此逻辑逐帧重试；若 Reset/重建期间 renderer 字段确实为空或已失效，这次 COM 调用可能以无效 `this` 崩溃。是否发生这种指针状态尚待运行时验证。
2. **原始路径仍会解引用设备：** callback 的 `isReadable(device)` 失败只会从 callback 返回；naked stub 接着无条件跳到 trampoline。trampoline 重放被覆盖的 `mov eax, [ecx+0x584]` 后回到 `+6`，原代码再执行 `push eax; mov ecx, [eax]; call dword ptr [ecx+0xA8]`。样本字节确认这会解引用 device vtable 并调用 D3D9 `EndScene` 槽；因此 callback 内的空设备判断不能保护原始路径。

这两个是**代码已确认的危险控制流**，但本次没有运行游戏或取得崩溃 dump，故尚不能断言它们就是这次复现的实际故障指令。特别是，D3D9 设备丢失或调用 `Reset` 本身不代表 COM device 指针必然变空；必须确认游戏 renderer 字段在切换期间是否被置空、变成过期指针，或在重建过程中暂不可用。还需检查切换时的 renderer、device 指针与崩溃 EIP。

## 范围与证据边界

| 项目 | 记录 |
| --- | --- |
| 源码 | `War3Launcher/hooker/war3hook.cpp` |
| 代码适用版本 | 表中有明确偏移的 `1.27.0.52240`；其它版本的偏移不可套用 |
| 本地样本 | `War3Launcher/versions/1.27.0.52240/game.dll` |
| 样本 SHA-256 | `e04d1716603c075eb0c8e1e21cf1093a664adc5249efab396bfa08d7b09d0c3a` |
| REA/Ghidra | REA 已确认分析副本与上述 SHA-256 一致；本次 `analyze_function` / `procedure_info` 请求超时 |
| 可复用静态记录 | `warcraft-iii-1.27-fps-unlock.md` 和 `warcraft-iii-fps-runtime-hooks.md` 中已有的 1.27 D3D9 / Reset 路径记录 |
| 动态复现 | 未执行游戏；没有 crash dump、运行时寄存器或 Reset 前后日志 |

因此，下文把代码直接可见的事实与对实际故障的推断分开。REA 本次超时不能作为函数反编译证据；也不据此声称已完整恢复 `0xECFF0` 所在函数的全部控制流。

## 代码与地址对照

1.27 版本表将 `GameBeforeD3DXDoEndScene` hook RVA 设为 `0xECFF0`，inline hook 窃取 6 字节，恰好覆盖 `mov eax, [ecx+0x584]`。样本对应字节为：

```text
RVA +0x00: 8B 81 84 05 00 00    mov eax, [ecx+0x584]
RVA +0x06: 50                   push eax
RVA +0x07: 8B 08                mov ecx, [eax]
RVA +0x09: FF 91 A8 00 00 00    call dword ptr [ecx+0xA8]
RVA +0x0F: C3                   ret
```

这与 D3D9 `IDirect3DDevice9::EndScene` 的 vtable 槽相符。样本 ImageBase 为 `0x6F000000`，hook VA 为 `0x6F0ECFF0`；样本 SHA-256 与上表一致。这里的原始字节是对本地样本的静态读取，不是 REA 函数反编译或运行时崩溃证据。不要把 RVA 当作文件偏移。

相关代码位置：

- Hook 安装、6 字节窃取与 trampoline 设置：[`war3hook.cpp`](../../War3Launcher/hooker/war3hook.cpp#L11525)
- naked stub 与 callback：[`war3hook.cpp`](../../War3Launcher/hooker/war3hook.cpp#L11596)
- `GetCreationParameters`、空设备判断和绘制流程：[`war3hook.cpp`](../../War3Launcher/hooker/war3hook.cpp#L11636)
- Reset 前资源清理：[`war3hook.cpp`](../../War3Launcher/hooker/war3hook.cpp#L11909)
- 1.27 单独安装的空设备保护 hook：[`war3hook.cpp`](../../War3Launcher/hooker/war3hook.cpp#L13123)
- COM `GetCreationParameters` 的类型声明：[`war3hook.h`](../../War3Launcher/hooker/war3hook.h#L1844)

`GameBeforeD3DXDoEndScene` 和 `GameBeforeD3DXReSetScene` 是项目中的 hook 名称。它们说明项目作者对位置的用途判断，不单独证明每条执行路径的语义。

## 两类“切屏”为何不同

### 普通焦点切换（例如 Alt+Tab）

- 首先是窗口焦点、最小化/恢复和消息状态变化。
- 在窗口化模式下，常见情况是保留同一 D3D device；应用暂停绘制，或通过 `TestCooperativeLevel` 发现设备暂时不可用。
- 独占全屏时，Alt+Tab 也可能导致设备丢失并触发恢复/Reset。因此不能依赖“焦点切换不会改变设备状态”；只能说它通常不要求用户选择另一组显示模式参数。

### 游戏选项中更改分辨率

- 需要采用新的宽高、刷新率或窗口/全屏呈现参数。
- 项目为 Reset 前路径安装了 hook，并在其中释放自有纹理和状态块（`releaseD3DResources`）。
- D3D9 Reset 期间，设备可能处于 lost/resetting 状态；应用资源必须符合 Reset 的资源池要求，且不能把设备对象仍可调用当作前提。
- 成功恢复后，渲染尺寸、viewport、呈现参数以及资源有效性都可能不同于切换前。

这解释了为何问题可能只在“选项里真正改分辨率”时出现：该操作更直接地进入 Reset 和资源转换窗口，而一次普通焦点变化可能没有走到相同状态序列。**如果所谓普通切屏也是独占全屏 Alt+Tab，则它也可能走设备丢失/Reset 路径。**

## 候选故障链（由高到低）

### 1. `GetCreationParameters` 在空设备检查之前执行（高优先级）

执行顺序是：

```text
stub: 读取 [ecx+0x584] 得到 device
  -> callback:
       若 g_oldWndProc == nullptr 且函数指针存在
         -> g_fnGetCreationParameters(device, &params)
       ...
       之后才执行 isReadable(device)
  -> callback 返回
  -> stub 无条件跳 trampoline
```

`g_fnGetCreationParameters` 在 D3D 上下文初始化时从 device vtable 索引 9 取得。窗口过程 hook 失败时 `startupHookWindow` 不会设置 `g_oldWndProc`；callback 便会在后续帧重复尝试。**只有当** `renderer+0x584` 在 Reset/重建交界处确实被游戏清空或变成无效指针时，callback 才会在到达自己的 `isReadable` 检查前以无效 `this` 调 COM 方法。D3D9 的 lost-device 状态本身不能证明 COM 指针已为空或失效。

注意：对设备地址做 `isReadable` 也不等价于确认 COM 对象仍处于有效生命周期；它只能作为额外的内存可读性检查，不能代替生命周期/设备状态判断。

### 2. callback 的返回不阻止原始指令执行（高优先级）

callback 中 `if (!isReadable(vTablePtr)) return 0;` 只结束 C++ callback。stub 随后执行：

```asm
jmp g_originalGameBeforeD3DXDoEndScene
```

trampoline 会重放被覆盖的 6 字节，并跳回 RVA `0xECFF6`。原始字节在此处先 `push eax`，随后 `mov ecx, [eax]`，再调用 `[ecx+0xA8]`。所以如果此处设备为空，callback 即使正常返回，原始路径仍会在读取设备 vtable 时崩溃。项目在 RVA `0xECB54` 有一个针对另一处设备访问的独立保护 hook；它不能自动保护 `0xECFF0` 这个 hook site。

这也是“只在 callback 里加 `if (device == nullptr) return;`”不够的原因：它没有改变 stub 后续进入 trampoline 的行为。任何空设备分支都必须确保跳到该目标函数中经验证的安全路径，或在维持游戏预期返回/寄存器状态的前提下跳过对应原始调用；具体分支地址应先由目标版本反汇编确认。

### 3. Reset 窗口里仍从渲染 hook 执行自定义绘制（中优先级）

每次命中 hook 都会进入自定义 callback。初始化完成后，callback 仍可能调用 `initD3DContext`、`drawSettingsButton`、两个进度面板、通知和 Ping HUD。`drawSettingsButton` 会检查 `TestCooperativeLevel`，但这些调用位于多个独立绘制路径；仅有这个单点检查不足以证明其他绘制 helper 在 lost/resetting 状态时都会退出。

在 Reset 前，项目释放了自己的 D3D 资源；但渲染 hook 没有显式等待 Reset 成功，也没有统一的“设备可渲染”门闩。Lost 设备上的绘制调用可能失败、影响重建过程，或在驱动/同步路径上表现为卡住。这是需要用日志验证的次级原因；lost-device 返回错误不等于必然崩溃或卡死，也没有证据证明 D3D9 的 `Reset` 必然死锁。

### 4. 在函数中间插入复杂 C++ 调用，没有保存浮点/SIMD 上下文（中优先级）

naked stub 只用 `pushad` / `pushfd` 保存通用寄存器与 EFLAGS。它在游戏函数中间增加一次会做浮点运算、调用 STL/Win32/D3D 的 C++ 函数；这些操作可能改写 x87、MMX 或 XMM 状态。若 hook site 的后续原代码依赖当时尚存的浮点/SIMD 临时值，就可能造成延迟、状态相关的损坏。

这属于 ABI/插桩风险，不足以单独解释“只有分辨率切换才触发”；应通过反汇编确认 hook site 周围的寄存器存活情况，或用 crash dump / A-B 测试证实。不能只看到 `pushad` 就认定所有 CPU 上下文都已保存。

## 建议的最小验证步骤

1. **先留住故障现场：** 记录崩溃 EIP、异常码、ECX、`[ECX+0x584]`、EAX、线程 ID；卡住时记录线程栈。核对 EIP 是否在 callback 的 `GetCreationParameters`、trampoline 的 `mov ecx,[eax]` 或 D3D 绘制调用内。
2. **在 Reset 边界记录状态：** 在 Reset 前 hook、D3D Reset 返回点、DoEndScene hook 处记录时间戳、renderer、device、`g_oldWndProc`、`g_fnGetCreationParameters`、`TestCooperativeLevel` HRESULT。避免在渲染线程同步写大日志。
3. **做单变量 A/B：** 保留原始游戏路径，只禁用这一个 hook 的 callback 副作用；再单独禁用 `GetCreationParameters`/WndProc 初始化尝试；最后只禁用自定义绘制。每次仅改一项，并分别尝试普通焦点切换和分辨率切换。
4. **先修空值控制流，再测绘制：** 在调用 COM 前检查 `renderer` 和 device 非空；确认 device 处于可用状态后才调用。若 device 为空，不能继续跳原 trampoline，因为原始指令同样需要被保护。必须基于 1.27 对应函数的实际反汇编设计安全分支。
5. **把一次性初始化移出每帧 hook：** 将 HWND 获取和窗口过程安装与设备绘制解耦；明确记录 hook 尝试/成功状态，不用 `g_oldWndProc == nullptr` 同时代表“尚未尝试”和“尝试失败”。Reset 中只做必要资源释放，成功恢复后再重建/恢复自有 D3D 资源；普通帧路径仅在设备状态允许时绘制。
6. **确认 FP/SIMD 保存约定：** 查看 `0xECFF0` 邻近汇编及编译器生成代码。如果确有跨插桩点存活的 FP/SIMD 状态，保存/恢复该状态，或把逻辑挪到调用约定明确的边界；不建议把复杂绘制逻辑留在裸汇编 trampoline 前。

## 诊断结论

目前最具体的代码级问题是：**callback 在空设备检查前调用 D3D COM 方法，且空值检查之后仍无条件进入重放原指令的 trampoline。** 分辨率变更比普通焦点切换更容易暴露这个设备生命周期缺口，因为它明确涉及呈现参数更新和 Reset/恢复。

但实际崩溃指令仍未知。若故障 EIP 位于 callback 的 COM 调用或 `mov ecx,[eax]`，上述首要假设得到支持；若 EIP 在 Reset/绘制 helper 内，应优先检查 lost-device 状态、资源恢复和渲染线程阻塞；若故障发生在普通帧且伴随浮点结果异常，再追查未保存的 x87/SIMD 状态。

## 为什么一直卡住却没有 dump

**卡死不等于异常。** `vectoredExceptionHandler` 是 VEH（向量异常处理器），由进程中的结构化异常分发调用；它不是定时检查线程是否仍在推进的 watchdog。线程陷入死循环、等待永远不会释放的锁、卡在同步 D3D/驱动调用，或窗口线程消息泵被阻塞时，如果没有产生 Win32 异常，VEH 就没有机会运行，因此不会生成 dump。D3D 返回 `D3DERR_DEVICELOST` 等 HRESULT 也只是普通返回值，不会自动变成 SEH 异常。

代码中 VEH 的具体行为还有这些边界：

- 只对访问违例、非法指令、整数除零和栈溢出创建进程内 dump；其它异常直接继续传递。异常码未匹配时不写文件。
- `AddVectoredExceptionHandler` 的返回值保存在 `g_exceptionVectoredHandler`，但注册处没有检查空返回值，也没有记录注册失败。故“它一定已经成功注册”尚未由运行日志证明。
- dump 写到注入 DLL 所在目录，而不是启动器的 `logs/dumps` 目录。检查时应区分 `hook.dll` 同目录的 `crash_*.dmp` 与 CrashMonitor 的目录。
- VEH 只检查 `CreateFileW` 是否成功，没有检查 `MiniDumpWriteDump` 的返回值；文件已创建并不表示内容完整。相反，弹出的“已成功抓取”消息也不能证明 dump 成功。
- handler 直接解引用 `ExceptionInfo->ExceptionRecord`，未先判空；而且在异常处理线程内进行 `std::wstring` 分配、文件 IO、`MiniDumpWriteDump` 和 `FatalAppExitW`。如果进程正处于堆损坏、栈耗尽、loader/heap 锁被占用或其它严重损坏状态，这些操作本身也可能失败或再次卡住。尤其栈溢出路径不适合继续依赖普通栈和堆操作。

项目另有 `CrashMonitor`：它通过 `DebugActiveProcess` 附加目标进程，在调试事件循环里等待异常事件，并对一组同样有限的致命异常写 dump，然后终止目标。它也不会因为“进程长时间无响应”自动保存 dump；而且启动器日志中的“成功附加”需要结合 CrashWorker 实际运行状态、dump 目录以及 `MiniDumpWriteDump` 结果判断。调试器附加能捕获异常，不等于能自动捕获 hang。

## 所有版本都卡住意味着什么

版本表显示，多个 Warcraft III 版本的渲染 hook RVA 不同，但都转入同一个 `jumpWhenMoveGameBeforeD3DXDoEndScene` 和 `doSomeThingsBeforeMoveGameBeforeD3DXDoEndScene` callback。因而跨版本复现提高了“共享 callback/渲染线程副作用/共用 Reset 处理”的优先级，例如每帧的窗口初始化尝试、D3D 状态初始化、UI 绘制或同步日志；它**不能**证明各版本目标函数机器码、D3D 接口槽位或设备字段布局相同。

特别是，`0xECFF0` 的具体字节与 `call [ecx+0xA8]` 结论只针对已核对的 1.27 样本。其它版本必须分别用其实际 `game.dll`、版本识别结果和签名匹配日志核实 hook site 与原始字节。若各版本是在装入同一套 hook DLL、切换相同设置时出现相同卡死，先做如下区分：

1. **无 hook / 仅注入 DLL / 启用渲染 hook** 三组对照，确定是否由该 hook 触发，以及仅注入带来的 VEH/CrashMonitor 是否有关。
2. 对每个版本记录 hook RVA、命中签名、窃取字节、trampoline 返回地址和 callback 进入/退出计数；确认线程到底停在 callback、原始 D3D 调用还是 Reset。
3. 卡住时由进程外工具对 `War3.exe` 生成完整用户态 dump，并检查所有线程栈；若渲染线程停在 `EndScene`/驱动内、锁等待、callback 或 `Reset`，栈通常比事后异常 dump 更直接。
4. 每次只关闭一种 callback 副作用（窗口 hook 初始化、D3D 初始化、自绘、日志），重复切分辨率。多个版本共享代码路径时，这比猜某个版本的裸指令更容易定位共同触发点。

因此，当前最稳妥的判断是：**VEH 没有 dump 与“进程卡死但没有被纳入的异常”完全一致；它本身既不证明也不否定渲染 hook 有问题。** 下一步应先采集 hang dump/线程栈，并确认异常处理器注册状态和 CrashMonitor 日志，而不是等待卡死后由 VEH 自动生成 dump。

## 相关记录

- [warcraft-iii-1.27-fps-unlock.md](warcraft-iii-1.27-fps-unlock.md)：1.27 D3D9 呈现参数与设备 Reset 背景。
- [warcraft-iii-fps-runtime-hooks.md](warcraft-iii-fps-runtime-hooks.md)：项目中的 D3D9 空设备保护与 Reset 相关 hook 说明。
- 项目源代码：[`war3hook.cpp`](../../War3Launcher/hooker/war3hook.cpp)。
