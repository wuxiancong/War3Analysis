# Warcraft III 全版本 OpenGL 绘制相关函数与偏移分析

## 1. 分析目标与样本

- 目标：为 `war3hook.cpp` 在 OpenGL 渲染模式下实现覆盖绘制，逆向 `game.dll` 的 OpenGL 渲染路径，给出全部 11 个版本的偏移。
- 样本：`War3Launcher\versions\<版本>\game.dll`（1.27.0.52240 另存于 `samples\`），镜像基址均为 `0x6F000000`，下文偏移均为 **RVA**（运行时地址 = `game.dll` 基址 + RVA）。

| 版本 | SHA-256 |
|---|---|
| 1.0.17.5988 | EA09C582A4C8B4112C1425CC954BF710FED3051E4A85BC39586647C0BD8BF4B2 |
| 1.0.20.6048 | F9166A59D6029E9AF132A090CFAC8E324B0A3452D43C0D30EA39F1E3A82DD982 |
| 1.20.4.6074 | 6B5B406861A56449C604C15CF0971DF7D6D26F679EFF7AA69A34946C7D91764B |
| 1.21.0.6263 | 3265E78DD68B1AB6C54957409E472C077F9FE2ABCCE4CFD279E56AF66A6EF6F3 |
| 1.22.0.6328 | 5F866BD8A45951CD2C4B22B1C80A0329246DBED847540C85430376E8C4310C84 |
| 1.23.0.6352 | EE6175947A8792CD672253B37DEB4C5D0577E4E145FFD90FED9021C64C31AE1E |
| 1.24.1.6374 | EE23DD7795EA82DDFC292FDD2A05D5A76D3ABEF801CEC01F0EFF68F521DF0441 |
| 1.24.4.6387 | C7C958174BDE30961A41FA91827E78A800E473EFDD8D1DE8D6C94ABF0B0024BF |
| 1.25.1.6397 | F504ED38F43BCCF011BF55DC8339EFACD689F4DCD6AF4AFD1815F01B5D026D07 |
| 1.26.0.6401 | 6D21BD9A0F9FBC8446F455C9E89AC994FED68174426FE608FCB9BAEFD4DEC53C |
| 1.27.0.52240 | E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A |

- 工具：本次使用 Python（`pefile` + `capstone`）对 PE 导入表、虚表与反汇编做静态扫描，脚本位于 `shared\scripts\`；**未使用 Ghidra / REA 的反编译结果**，结论均为静态分析，**尚未在游戏运行时验证**。

## 2. 关键结论（静态事实）

1. **全部版本的 `game.dll` 都静态导入 `opengl32.dll`**（50 个 gl/wgl 函数）与 `gdi32` 的 `ChoosePixelFormat/DescribePixelFormat/SetPixelFormat`。游戏没有导入 `SwapBuffers`，缓冲交换使用 **`wglSwapLayerBuffers(hdc, 1)`**。
2. 渲染层是 C++ 虚类：`CGxDevice` 基类、`CGxDeviceD3d`、`CGxDeviceOpenGl`（字符串 `CGxDeviceOpenGL/OpenGl` 存在于所有版本）。**GL 设备与 D3D 设备虚表同为 45 个槽位，槽位语义一一对应**：
   - 槽 `[16]` = SceneClear（GL：`glClear`；D3D：`Clear`），`ret 8`，thiscall，2 个栈参数。
   - 槽 `[17]` = **ScenePresent**（GL：`wglSwapLayerBuffers`；D3D9 1.27：`EndScene` + `Present`），`ret 4`，thiscall，1 个栈参数。
3. **GL 设备对象成员**（所有版本一致，静态）：`+0x578` = HWND，`+0x57C` = **HDC**，`+0x580` = **HGLRC**，`+0x560` = Present 参数相关标志（真值时 Present 里会 `glReadPixels` 抓屏），`+0x504` 的 `0x20` 位决定 Present 是 `wglSwapLayerBuffers` 还是 `glFinish`。D3D9 对应对象 `+0x584` = `IDirect3DDevice9*`。
4. **GL 路径的“EndScene 等价点”就是 `ScenePresent`（槽 17）入口**：此时本帧所有 `glDrawElements` 已提交，尚未交换缓冲。在此处先绘制覆盖层再调用原函数即可，与 D3D 下 `BeforeD3DXDoEndScene` 的位置语义一致。
5. 所有版本 `ScenePresent` 入口前 6 字节都落在指令边界上（见表 C），可直接复用现有 6 字节内联 Hook 框架（`g_original/currentBytesFor...[6]`）。

## 3. 偏移表
### 表 A：GL 设备虚表与关键槽位（RVA）

| 版本 | GL 虚表 | [17] ScenePresent | [16] SceneClear | swap 调用点 | [9] 开窗+建上下文 | [43] GL 初始化 | [18] 视口/裁剪 | [21] 顶点数组 | [28] DrawElements | [32] DrawElements(多重纹理) |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.0.17.5988 | `0x70A3F8` | **`0x0D5BD0`** | `0x0D5B10` | `0x0D5C04` | `0x0CC090` | `0x0CFA20` | `0x0D57D0` | `0x0D58E0` | `0x0D4F90` | `0x0D51A0` |
| 1.0.20.6048 | `0x70B3F8` | **`0x0D5BD0`** | `0x0D5B10` | `0x0D5C04` | `0x0CC090` | `0x0CFA20` | `0x0D57D0` | `0x0D58E0` | `0x0D4F90` | `0x0D51A0` |
| 1.20.4.6074 | `0x70B3F8` | **`0x0D5BD0`** | `0x0D5B10` | `0x0D5C04` | `0x0CC090` | `0x0CFA20` | `0x0D57D0` | `0x0D58E0` | `0x0D4F90` | `0x0D51A0` |
| 1.21.0.6263 | `0x70C3F8` | **`0x0D5BD0`** | `0x0D5B10` | `0x0D5C04` | `0x0CC090` | `0x0CFA20` | `0x0D57D0` | `0x0D58E0` | `0x0D4F90` | `0x0D51A0` |
| 1.22.0.6328 | `0x9434B4` | **`0x5235E0`** | `0x523500` | `0x523615` | `0x51A9A0` | `0x521C20` | `0x523880` | `0x5239D0` | `0x523D20` | `0x524190` |
| 1.23.0.6352 | `0x957614` | **`0x525370`** | `0x525290` | `0x5253A5` | `0x51C730` | `0x5239B0` | `0x525610` | `0x525760` | `0x525AB0` | `0x525F20` |
| 1.24.1.6374 | `0x967B7C` | **`0x533D00`** | `0x533C20` | `0x533D35` | `0x52B0C0` | `0x532340` | `0x533FA0` | `0x5340F0` | `0x534440` | `0x5348B0` |
| 1.24.4.6387 | `0x967B94` | **`0x533D80`** | `0x533CA0` | `0x533DB5` | `0x52B140` | `0x5323C0` | `0x534020` | `0x534170` | `0x5344C0` | `0x534930` |
| 1.25.1.6397 | `0x955A3C` | **`0x533050`** | `0x532F70` | `0x533085` | `0x52A410` | `0x531690` | `0x5332F0` | `0x533440` | `0x533790` | `0x533C00` |
| 1.26.0.6401 | `0x955A3C` | **`0x533280`** | `0x5331A0` | `0x5332B5` | `0x52A640` | `0x5318C0` | `0x533520` | `0x533670` | `0x5339C0` | `0x533E30` |
| 1.27.0.52240 | `0x95D960` | **`0x0F0CC0`** | `0x0F0BF0` | `0x0F0CF8` | `0x0E78A0` | `0x0EBB00` | `0x0F11D0` | `0x0F12C0` | `0x0F1750` | `0x0F1A40` |

### 表 B：game.dll 中 opengl32 的 IAT 槽位（RVA，可直接 hook IAT）

| 版本 | wglSwapLayerBuffers | wglMakeCurrent | wglCreateContext | wglDeleteContext | wglGetProcAddress | glDrawElements | glClear | glViewport | glFinish | glReadPixels |
|---|---|---|---|---|---|---|---|---|---|---|
| 1.0.17.5988 | `0x70427C` | `0x7041BC` | `0x70421C` | `0x704220` | `0x704214` | `0x704254` | `0x70426C` | `0x704268` | `0x704250` | `0x704274` |
| 1.0.20.6048 | `0x70527C` | `0x7051BC` | `0x70521C` | `0x705220` | `0x705214` | `0x705254` | `0x70526C` | `0x705268` | `0x705250` | `0x705274` |
| 1.20.4.6074 | `0x70527C` | `0x7051BC` | `0x70521C` | `0x705220` | `0x705214` | `0x705254` | `0x70526C` | `0x705268` | `0x705250` | `0x705274` |
| 1.21.0.6263 | `0x70627C` | `0x7061BC` | `0x70621C` | `0x706220` | `0x706214` | `0x706254` | `0x70626C` | `0x706268` | `0x706250` | `0x706274` |
| 1.22.0.6328 | `0x85C44C` | `0x85C470` | `0x85C404` | `0x85C408` | `0x85C414` | `0x85C42C` | `0x85C45C` | `0x85C434` | `0x85C448` | `0x85C454` |
| 1.23.0.6352 | `0x8704B4` | `0x870548` | `0x870544` | `0x870540` | `0x870534` | `0x870494` | `0x8704C4` | `0x87049C` | `0x8704B0` | `0x8704BC` |
| 1.24.1.6374 | `0x87F4B4` | `0x87F548` | `0x87F544` | `0x87F540` | `0x87F534` | `0x87F494` | `0x87F4C4` | `0x87F49C` | `0x87F4B0` | `0x87F4BC` |
| 1.24.4.6387 | `0x87F4B4` | `0x87F548` | `0x87F544` | `0x87F540` | `0x87F534` | `0x87F494` | `0x87F4C4` | `0x87F49C` | `0x87F4B0` | `0x87F4BC` |
| 1.25.1.6397 | `0x86D44C` | `0x86D470` | `0x86D404` | `0x86D408` | `0x86D414` | `0x86D42C` | `0x86D45C` | `0x86D434` | `0x86D448` | `0x86D454` |
| 1.26.0.6401 | `0x86D44C` | `0x86D470` | `0x86D404` | `0x86D408` | `0x86D414` | `0x86D42C` | `0x86D45C` | `0x86D434` | `0x86D448` | `0x86D454` |
| 1.27.0.52240 | `0x94E4DC` | `0x94E52C` | `0x94E4E4` | `0x94E4E0` | `0x94E4EC` | `0x94E4AC` | `0x94E4D8` | `0x94E4B4` | `0x94E4D0` | `0x94E4C8` |

### 表 C：ScenePresent 入口特征（前 6 字节，可用于 6 字节内联 Hook）

| 版本 | RVA | 前 6 字节 |
|---|---|---|
| 1.0.17.5988 | `0x0D5BD0` | `55 8B EC 83 EC 0C` |
| 1.0.20.6048 | `0x0D5BD0` | `55 8B EC 83 EC 0C` |
| 1.20.4.6074 | `0x0D5BD0` | `55 8B EC 83 EC 0C` |
| 1.21.0.6263 | `0x0D5BD0` | `55 8B EC 83 EC 0C` |
| 1.22.0.6328 | `0x5235E0` | `83 EC 08 53 55 56` |
| 1.23.0.6352 | `0x525370` | `83 EC 08 53 55 56` |
| 1.24.1.6374 | `0x533D00` | `83 EC 08 53 55 56` |
| 1.24.4.6387 | `0x533D80` | `83 EC 08 53 55 56` |
| 1.25.1.6397 | `0x533050` | `83 EC 08 53 55 56` |
| 1.26.0.6401 | `0x533280` | `83 EC 08 53 55 56` |
| 1.27.0.52240 | `0x0F0CC0` | `55 8B EC 83 EC 08` |

> 表 A 中 [9]/[43]/[18]/[21]/[28]/[32] 的语义由其内部引用的 gl/Win32 API 推断（见 §4），为**推断**，Hook 前请再确认。

## 4. 1.27.0.52240 GL 虚表槽位语义（按槽内引用 API 推断）

虚表 RVA `0x95D960`，完整导出见 `artifacts\opengl-draw\1.27.0.52240-glslots.txt`。

| 槽 | 函数 RVA | 引用的 API | 推断语义 |
|---|---|---|---|
| 0 | `0xEB600` | glGenTextures/glTexImage2D/glTexSubImage2D… | 纹理创建/上传 |
| 1 | `0xEA310` | glEnable/glDisable/glFog*/glLight*/glMaterialfv | 渲染状态/光照/雾 |
| 3 | `0xE74E0` | ShowWindow/SetFocus/GetDeviceGammaRamp | 窗口显示 |
| 5 / 7 | `0xE7670` / `0xE7750` | ChangeDisplaySettingsExA / SetDeviceGammaRamp | 切换显示模式 / 伽马 |
| 9 | `0xE78A0` | CreateWindowExA/GetDC/wglMakeCurrent… | 创建窗口并建立 GL 上下文（先 `GetDC`→`+0x57C`，`0xEBE20` 内 `wglCreateContext`→`+0x580`，再 `wglMakeCurrent`） |
| 12 / 16 | `0xF0A70` / `0xF0BF0` | glClear/glClearColor | 清屏（16=SceneClear） |
| **17** | **`0xF0CC0`** | wglSwapLayerBuffers/glReadPixels/glLoadMatrixf | **ScenePresent，覆盖绘制 Hook 点** |
| 18 | `0xF11D0` | glViewport/glScissor/glDepthRange | 视口/裁剪 |
| 21 | `0xF12C0` | gl*Pointer/gl*ClientState | 绑定顶点流 |
| 23 | `0xF1150` | glMatrixMode/glLoadMatrixf | 设置矩阵 |
| 28 / 32 | `0xF1750` / `0xF1A40` | glDrawElements/glFinish | 绘制图元（32 带多重纹理指针） |
| 43 | `0xEBB00` | ChoosePixelFormat/glGetString/wglCreateContext… | 像素格式与 GL 初始化、扩展探测 |
| 44 | `0xE8970` | TextOutW/EnumDisplaySettingsA | 文本/显示模式枚举 |

扩展探测字符串（1.27）：`GL_ARB_multitexture`@`0x95FAC0`、`GL_EXT_compiled_vertex_array`@`0x95FA7C`、`GL_EXT_bgra`@`0x95FE04`、`GL_EXT_texture_edge_clamp`@`0x95FE10`，引用点均在 `0xEBB00` 附近。

## 5. 接入 war3hook 的建议（未实现）

- **方案 A（推荐，按版本表）**：表 A 的 `[17] ScenePresent` RVA 做内联 Hook（6 字节，见表 C）。thiscall：`ecx=this`，栈上 1 个参数，`ret 4`。从 `this+0x57C` 取 HDC、`this+0x580` 取 HGLRC，钩子运行时当前线程已是 GL 渲染线程，且上下文已 `wglMakeCurrent`。
- **方案 B（不依赖版本）**：对 `game.dll` 的 IAT `wglSwapLayerBuffers`（表 B）改写，或直接 inline hook `opengl32!wglSwapLayerBuffers`。每帧交换前调用，适用所有版本且不需要特征码。
- 覆盖绘制时用 `hook.dll` 自行链接 `opengl32` 的固定管线函数（`glPushAttrib/glPushMatrix` 等 `game.dll` 未导入，但 opengl32 已在进程内），先保存并在绘制后还原：绑定纹理、`GL_BLEND/GL_DEPTH_TEST/GL_ALPHA_TEST/GL_TEXTURE_2D`、矩阵、`glVertexPointer` 等客户端数组、`glActiveTextureARB`（`game.dll` 用多重纹理）。
- 渲染方式判定：与 `GxDeviceCreate` 的 API 参数（0=OpenGL，1=D3D）联动，GL 时安装 GL 的 Present Hook，D3D 时沿用现有 DoEndScene Hook。

## 6. 推理过程

1. `gl_survey.py` 枚举 11 个版本的导入表与字符串：确认均导入 `opengl32`，没有 `SwapBuffers`，存在 `CGxDeviceOpenGL`。
2. `gl_offsets.py` 以 `FF 15/FF 25 <IAT>` 查找 `wglSwapLayerBuffers` 调用点；取其之前最近的“被虚表引用”的函数作为 ScenePresent，并反查虚表（45 槽）。
3. 1.27 上对照 D3D9 设备虚表（`0x95D87C`）：槽 16/17 = `Clear`/`Present`（槽 17 调用 `0xECFF0` 即现有 `DoEndScene` Hook 位置），与 GL 虚表槽位一致，据此确认槽位语义对应。
4. `gl_fields.py` 在 11 个版本的 swap/makecurrent 调用点前提取指令，确认 HDC 偏移恒为 `+0x57C`。
5. 1.27 对 `0xF0CC0`/`0xF0BF0` 反汇编验证调用约定：Present `ret 4`，Clear 前置读取 `[ebp+8],[ebp+0xC]`，结尾 `ret 8`。

## 7. 置信度、验证状态与未解决事项

| 项目 | 置信度 | 状态 |
|---|---|---|
| IAT RVA（表 B） | 高 | 静态解析导入表，机械得出 |
| ScenePresent RVA / 虚表（表 A、C） | 高（1.27 已手工反汇编；其余版本由同一脚本得出，6 字节前缀一致） | 静态，**未运行验证** |
| 对象成员 `+0x57C/+0x580` | 高 | 11 个版本调用点前指令一致；`+0x580` 仅在 1.27 手工确认 |
| 其余槽位语义（表 A 的 [9][18][21][28][32][43]） | 中 | 仅依据槽内引用 API 推断 |
| 1.22~1.26 的 thiscall 栈参数个数 | 中 | 序言 `mov edi,[esp+0x1C]` 与 1.27 的单参数一致，未逐版本看 `ret` |

未解决：
- 尚未在游戏内用 `-opengl` 实测 Hook 触发与绘制。
- 未与 D3D8（1.22 以前/1.22~1.26）设备虚表逐槽比对（仅在 1.27 的 D3D9 上确认）。
- `+0x504` 位 `0x20`、`+0x560` 的确切含义未确定。
- GL 上下文创建/切换前后（全屏切换、分辨率重置）是否重建 HGLRC，需要后续看槽 5/9/43 的调用时序。

## 8. 产物

- 脚本：`shared\scripts\gl_survey.py`、`gl_offsets.py`、`find_vtable.py`、`list_vtables.py`、`gl_slots.py`、`gl_fields.py`、`gl_make_tables.py`、`dis_rva.py`
- 数据：`artifacts\opengl-draw\<版本>-offsets.json`、`1.27.0.52240-glslots.txt`、`1.27.0.52240-glvtable.txt`、`1.27.0.52240-d3dvtable.txt`、`fields.txt`、`tables.md`
- 思维导图：[warcraft-iii-all-versions-opengl-draw-offsets-mindmap.md](warcraft-iii-all-versions-opengl-draw-offsets-mindmap.md)

## 9. 已接入 war3hook 的 Hook 点（OGLX，未实机验证）

| 版本 | DoEndScene（vtable[17]） | ReSetScene（vtable[5]） |
|---|---|---|
| 1.0.17 / 1.0.20 / 1.20.4 / 1.21 | 0xD5BD0 | 0xCBED0 |
| 1.22.0.6328 | 0x5235E0 | 0x51AC70 |
| 1.23.0.6352 | 0x525370 | 0x51CA00 |
| 1.24.1.6374 | 0x533D00 | 0x52B390 |
| 1.24.4.6387 | 0x533D80 | 0x52B410 |
| 1.25.1.6397 | 0x533050 | 0x52A6E0 |
| 1.26.0.6401 | 0x533280 | 0x52A910 |
| 1.27.0.52240 | 0xF0CC0 | 0xE7670 |

- vtable[5] 会调用 ChangeDisplaySettingsExA 并重建 HGLRC，作为 GL 的 "Reset"，用于释放覆盖层纹理。
- 两处入口均为 thiscall，this(ecx) 即渲染器对象，对象 +0x578 为 HWND。
