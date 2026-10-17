# 运行时 FPS 钩子

启动器在 `hooker/war3hook.cpp` 里用六个 inline hook 解除帧率限制，不改 `versions/` 里的原版 `game.dll` / `war3.exe`。静态补丁字节表仍在 [warcraft-iii-all-versions-fps-unlock.md](warcraft-iii-all-versions-fps-unlock.md)，1.27 的函数级证据在 [warcraft-iii-1.27-fps-unlock.md](warcraft-iii-1.27-fps-unlock.md)。

## 结论

六个钩子都要安装。`hookGameSoftware_FpsKeepFlag` 单独就能去掉约 64 FPS 的软件帽，但切换分辨率会重建显卡设备并重新写入呈现参数。其余钩子被注释掉后，这次重建会出问题。

版本标志 `g_detectedWar3VersionFlag`：

| 标志 | 版本 | 软件帽所在模块 | 呈现 |
| --- | --- | --- | --- |
| 0 | 1.21 及更早 | `war3.exe` | D3D8 |
| 1 | 1.22–1.26 | `game.dll` | D3D8 |
| 2 | 1.27 及以上 | `game.dll` | D3D9 |

1.22 起 `war3.exe` 里还有一份软件帽死代码，运行时只钩 `game.dll`。

## 钩子

### `hookGameSoftware_FpsKeepFlag`

去掉软件渲染留下的约 64 FPS 上限。DirectX 和 OpenGL 启动也会走过这段。

渲染标志在 `[对象+0x44]`。bit 2 置位时，游戏执行 `and eax, 0xFB`（`and eax, ~4`）把该位清掉，再以 `edx = 0x11` 派发。清掉的这一位就是 64 帧帽。钩子从 `83 E0 FB` 的 `83` 起改写，跳板把掩码改成 `0xFF`，`and` 变成空操作，bit 2 保留。

| 标志 | 模块 | 窃取长度 | 原始字节 |
| --- | --- | ---: | --- |
| 0 | `war3.exe` | 9 | `83 E0 FB 53 BA 11 00 00 00` |
| 1 | `game.dll` | 5 | `83 E0 FB 6A 00` |
| 2 | `game.dll` | 6 | `83 E0 FB 8D 53 11` |

`FB` 的文件偏移见全版本表。1.26 为 `game.dll+0x62D7FB`，1.27 为 RVA `0x5FCFB`。

### `hookGameDirect3DPresentImmed`

去掉独占全屏的垂直同步。切换分辨率会再次填充 `D3DPRESENT_PARAMETERS` 并 `Reset` / `CreateDevice`，所以这里必须留着。

独占分支把 `PresentationInterval` 写成 `0`（`D3DPRESENT_INTERVAL_DEFAULT`，跟随刷新率）。跳板把立即数改成 `0x80000000`（`D3DPRESENT_INTERVAL_IMMEDIATE`）。

| 版本 | 指令 | 改写位置 |
| --- | --- | --- |
| 1.26 及更早，D3D8 | `C7 46 30 00 00 00 00` | 结构 `+0x30`，7 字节里的最后一字节 |
| 1.27，D3D9 | `C7 46 34 00 00 00 00` | 结构 `+0x34`，同样改最后一字节 |

1.26 及更早的窗口化 `CreateDevice` 拒绝 `IMMEDIATE`。这条指令只在独占分支上，后面是 `EB` 跳过窗口化路径，钩子不要扩到窗口化那一支。

### `hookGameDirect3DWindowedSync`

只在标志 2（1.27 及以上）安装。1.27 的窗口化分支不写 `PresentationInterval`，`memset` 之后仍是 `DEFAULT`，窗口和改分辨率都会重新 vsync。

钩子落在 `C7 46 18 01 00 00 00 89 4E 08`（10 字节）。返回游戏前改写成：

- `[esi+0x18] = 1`（原来的 `SwapEffect`）
- `[esi+0x34] = 0x80000000`
- `[esi+0x08] = ecx`

1.26 及更早不要装这个钩子。

### `hookGameDirect3DLockableFlag`

只在标志 2 安装，和窗口化间隔写在同一次设备参数填充里。

原指令 `C7 46 2C 01 00 00 00` 把 `Flags` 设成 `D3DPRESENTFLAG_LOCKABLE_BACKBUFFER`。跳板把立即数改成 `0`。可锁定后台缓冲会拖住 Present；改分辨率重建的是同一块参数。

1.26 及更早的窗口化设备依赖这个 Flags，不能清。

### `hookGameOpenGLSwapInterval__`

去掉 OpenGL 的交换间隔。启动参数 `-opengl` 时才会走到 `wglMakeCurrent` 后面的那条 `call`；改分辨率会再次建立上下文，所以不能只在第一次启动时处理。

这是 `HookType::DirectCall`。裸函数先调用原来的函数，再 `wglGetProcAddress("wglSwapIntervalEXT")`，对当前上下文调用 `wglSwapIntervalEXT(0)`。先调原函数，是因为原函数自己可能把间隔设回非 0。

运行时不往节区空隙写 cave，也不写死 `FF 15 0x6Fxxxxxx`。空隙的 VirtualSize 可能没有映射；写死的 ImageBase 在重定位后会访问违规。静态补丁用过的 `call $+5 / pop ebx` 还会在 1.26 改分辨率时打坏 `ebx`。

### `hookGameMaxFpsDefaultTo10000`

把 `maxfps` 的注册默认值从 200 改成 10000。标志 0 没有 `maxfps` 字符串，直接跳过。

视频选项在改分辨率时会重新注册。默认值仍是 200 时，这次注册把上限写回 200。

| 标志 | 指令 | 立即数位置 |
| --- | --- | --- |
| 1 | `C7 44 24 14 C8 00 00 00`（8 字节） | `+4` |
| 2 | `C7 45 FC C8 00 00 00`（7 字节） | `+3` |

写入字节 `10 27 00 00`。启动器已经写进注册表的 `Video\maxfps` 优先于这个默认值；`0` 不是无限。

## 安装范围

`installAllHooks` 里六个都注册。`MaxFpsDefaultTo10000` 仅在标志非 0 时安装，`Direct3DWindowedSync` 和 `Direct3DLockableFlag` 仅在标志为 2 时安装。卸载表与安装表对应，没有装上的钩子在修订地址为空时直接返回。

| 钩子 | 去掉的限制 | 不安装时 |
| --- | --- | --- |
| `Software_FpsKeepFlag` | 约 64 FPS 软件帽 | 全屏 `/fps` 仍约 64 |
| `Direct3DPresentImmed` | 独占全屏垂直同步 | 改分辨率后回到刷新率 |
| `Direct3DWindowedSync` | 1.27 窗口化垂直同步 | 窗口化改分辨率后仍 vsync |
| `Direct3DLockableFlag` | 1.27 可锁定后台缓冲 | 与窗口化设备重建绑在一起 |
| `OpenGLSwapInterval__` | OpenGL 交换间隔 | `-opengl` 改分辨率后间隔恢复 |
| `MaxFpsDefaultTo10000` | 默认 200 的软件上限 | 改分辨率重新注册时回到 200 |
