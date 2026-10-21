# 魔兽争霸3 帧率限制解锁 Hook 全面审计与架构优化分析

## 1. 核心结论摘要

针对提出的 8 个 Hook 函数，结合 Ghidra / REA 逆向成果与 `war3hook.cpp` 实际源码进行全面审计，结论如下：

1. **是否有缺少？**
   - **核心机制无缺少**：魔兽争霸3解帧率限制包含四个关键层面：
     - **软件层 64 FPS 轮询上限**（`Software_FpsKeepFlag`）
     - **图形层 Direct3D 呈现间隔 / 垂直同步**（`Direct3DPresentParam`）
     - **图形层 OpenGL 交换间隔**（`OpenGLSwapInterval__`）
     - **引擎配置层 maxfps 注册默认值**（`MaxFpsDefaultTo10000`）
     - **防御层 D3D 空设备防崩溃保护**（`Direct3DNullDevice__`）
     这 5 个关键点在现行工程中均已具备，覆盖了从 1.0.17 到 1.27.0.52240 的全部版本。
2. **是否有多余？**
   - **存在明显冗余与死代码**：
     - `hookGameDirect3DPresentImmed()`：**被遗漏未安装且与 PresentParam 功能冲突**。在 `installAllHooks` 中根本没有被加入任务队列，属于死代码。
     - `hookGameDirect3DWindowedSync()`：**多余**。其目的是将 1.27 窗口化分支的呈现间隔改写为 `0x80000000`，但该工作已被更高阶的 `hookGameDirect3DPresentParam()` 在函数返回前统一拦截改写，二者重叠。
     - `hookGameDirect3DLockableFlag()`：**多余**。其目的是将 1.27 的 `Flags` 清零，同样已在 `hookGameDirect3DPresentParam()` 中以 `present[11] = 0` 统一处理，无需在内部指令点重复 hook。
3. **Hook 位置与实现逻辑是否正确？**
   - **`hookGameSoftware_FpsKeepFlag`**：**完全正确**。覆盖了 1.21 及更早（`war3.exe`）、1.22~1.26（`game.dll`）、1.27（`game.dll`）的 `83 E0 FB` 指令，跳板改写为 `83 E0 FF`，消除约 64 FPS 软件帽。
   - **`hookGameDirect3DPresentParam`**：**极度关键且设计优秀**。精准识别调用者：只在 `CreateDevice`（RVA `0xEC413`）时改写为立即呈现 `0x80000000`；在 `Reset`（RVA `0xECC12`）时保持原参数，完美避开了 Direct3D9 驱动在 `Reset` 携带 `IMMEDIATE` 时卡死挂起（Hang）的顽疾。
   - **`hookGameDirect3DNullDevice__`**：**极度关键且位置正确**。防御 1.27 选项菜单切换分辨率时设备被释放，后续每帧 `TestCooperativeLevel`（RVA `0xECB54`）解引用空指针引发的 `0xC0000005` 崩溃。
   - **`hookGameMaxFpsDefaultTo10000`**：**位置与实现正确**。成功将注册表/配置默认值由 200 字节修改为 10000。
   - **`hookGameOpenGLSwapInterval__`**：**位置正确，但汇编跳板存在风险**。裸函数中未对原始调用前后的寄存器（如 caller-saved 寄存器 eax/ecx/edx）做安全保护，直接 `call dword ptr [g_originalGameOpenGLSwapInterval__Ex]`，可能污染上层上下文。

---

## 2. 8 个 Hook 函数的逐项深度审计

| 序号 | 函数名称 | 适用版本 | 状态评估 | 核心作用与问题排查 |
|---|---|---|---|---|
| 1 | `hookGameSoftware_FpsKeepFlag` | 全版本 (1.0.17~1.27) | **正确，核心必选** | 消除渲染循环内部 bit 2 清零造成的 ~64 帧上限。位置与特征码完全匹配。 |
| 2 | `hookGameDirect3DPresentParam` | 1.27 D3D9 | **正确，核心必选** | 统一在参数填充函数返回时改写参数，精准放行 Reset，防止挂起。 |
| 3 | `hookGameDirect3DNullDevice__` | 1.27 D3D9 | **正确，核心必选** | 拦截 RVA `0xECB54` 空设备解引用，阻断分辨率切换崩溃。 |
| 4 | `hookGameMaxFpsDefaultTo10000` | 1.22~1.27 | **正确，建议保留** | 防止用户切换分辨率或重置配置时被锁死在 200 帧上限。 |
| 5 | `hookGameOpenGLSwapInterval__` | 全版本 OpenGL | **位置正确，实现需优化** | 在 `-opengl` 模式建立上下文后调用 `wglSwapIntervalEXT(0)`。跳板应规范保护上下文。 |
| 6 | `hookGameDirect3DPresentImmed` | 历史遗留 | **多余 / 实际未启用** | `installAllHooks` 中漏写了调用，且与 `PresentParam` 冲突，建议清理。 |
| 7 | `hookGameDirect3DWindowedSync` | 1.27 D3D9 | **多余 (功能重复)** | 试图修改窗口化路径呈现间隔，但功能已被 `PresentParam` 完整取代。 |
| 8 | `hookGameDirect3DLockableFlag` | 1.27 D3D9 | **多余 (功能重复)** | 试图清空 LockableBackBuffer，同样已被 `PresentParam` 完整取代。 |

---

## 3. 架构优化与精简方案

### 3.1 为什么建议移除 `WindowedSync`、`LockableFlag` 与 `PresentImmed`？
在 1.27 的 D3D9 流程中，`FUN_6f0ec6b0` 负责构建 `D3DPRESENT_PARAMETERS`。
- `WindowedSync` 和 `LockableFlag` 是侵入该函数内部，在执行局部赋值时打补丁。
- 而 `PresentParam` 是挂在该函数外层/退出点，直接统一操作最终生成的 `present[13]` 和 `present[11]`，并区分了 `CreateDevice` 与 `Reset` 调用来源。
- 内部打补丁不但多余，而且无法像 `PresentParam` 那样在 `Reset` 时进行智能回退保护。

### 3.2 精简后的核心推荐 Hook 拓扑

```
[引擎启动 / 分辨率切换]
       │
       ├─► 1. 基础逻辑层 (全版本必装)
       │     └─ hookGameSoftware_FpsKeepFlag()  ── 破除 64 FPS 软件限制
       │
       ├─► 2. 渲染呈现层 (按图形 API 分流)
       │     ├─ [D3D9 模式 / 1.27]
       │     │    ├─ hookGameDirect3DPresentParam()  ── 独占/窗口立即呈现 (安全放行 Reset)
       │     │    └─ hookGameDirect3DNullDevice__() ── 切分辨率防 0xC0000005 空指针崩溃
       │     │
       │     └─ [OpenGL 模式 / 全版本 -opengl]
       │          └─ hookGameOpenGLSwapInterval__() ── wglSwapIntervalEXT(0) 关垂直同步
       │
       └─► 3. 游戏配置层 (1.22+)
             └─ hookGameMaxFpsDefaultTo10000()    ── 破除 200 FPS 默认配置上限
```
