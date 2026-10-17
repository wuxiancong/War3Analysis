# 全版本 Game.dll / war3.exe FPS 解锁偏移

运行时六个钩子的用途、版本门闩，以及「只留软件帽则切换分辨率会出问题」见 [warcraft-iii-fps-runtime-hooks.md](warcraft-iii-fps-runtime-hooks.md)。本文只保留静态字节对齐。

按 1.27 已实机验证的规律，对 `War3Launcher/versions` 下每个官方样本做了静态对齐。补丁由 `dll_game/patch_all_versions_fps.py` 生成，输出在 `dll_game/<版本>-fps-unlock-dx-ogl/`。**未修改** `versions/` 原件。除 1.27 外均未实机测帧。

## 规律

| 路径 | 特征 | 补丁 |
| --- | --- | --- |
| 软件 64 FPS | `test al, 4` / `and eax, 0xFFFFFFFB` / `edx=0x11` | `FB`→`FF` |
| 1.21 及更早 | 上述特征在 **war3.exe**，不在 Game.dll | 同时覆盖 `war3.exe` |
| 1.22–1.26 | 特征在 Game.dll（1.26 为 `+0x62D7FB`）；EXE 里仍有一份死代码 | **只改 Game.dll**（实机：不改 EXE 也能跑） |
| D3D8 | `89 56 2C C7 46 30 00 00 00 00`（独占 `FullScreen_PresentationInterval` at `+0x30`） | 写成 `IMMEDIATE`（`...80`） |
| D3D8 窗口化 | 独占分支才写 interval；窗口化 `CreateDevice` 依赖 `Flags=LOCKABLE_BACKBUFFER` | **不再** 写 IMMEDIATE、**不再** NOP Flags（1.26 以下窗口化曾因此无法启动） |
| D3D9（仅 1.27） | `89 46 30 C7 46 34 00 00 00 00` | 与已测 1.27 补丁同一点 `0xEBB59`；窗口化 cave + 清 Flags |
| OpenGL | `wglMakeCurrent` 后 `call` 接到 slack：PIC 取 `wglGetProcAddress("wglSwapIntervalEXT")(0)` | **禁止** `FF15 0x6Fxxxxxx`；用 `call $+5 / pop ebx / [ebx+disp]`，字符串放 `.rdata` slack |
| maxfps | 1.22 起默认 200 | 改为 10000；启动器写入的注册表仍优先 |

## 软件 64 文件偏移（`FB` 字节）

| 版本 | Game.dll | war3.exe |
| --- | ---: | ---: |
| 1.0.17.5988 / 1.0.20.6048 / 1.20.4.6074 / 1.21.0.6263 | （无） | `0x445FE` |
| 1.22.0.6328 | `0x61D87B` | `0x4BB6B` |
| 1.23.0.6352 | `0x61F4FB` | `0x4BB6B` |
| 1.24.1.6374 | `0x62DEEB` | `0x4BB6B` |
| 1.24.4.6387 | `0x62DF9B` | `0x4BB7B` |
| 1.25.1.6397 | `0x62D5CB` | `0x4BD9B` |
| 1.26.0.6401 | `0x62D7FB` | `0x4BD9B` |
| 1.27.0.52240 | `0x5F0FB` | （无） |

1.24.4 的 `0x62DF9B`、1.26 的 `0x62D7FB`、1.27 的 `0x5FCFB`（VA）与 WarcraftHelper 公开偏移一致。

## D3D 独占全屏 interval（`C7 46 30/34` 立即数 0→`80000000`）

| 版本 | 文件偏移 | 结构 |
| --- | ---: | --- |
| 1.0.17–1.21 | `0xD069D` | D3D8 `+0x30` |
| 1.22.0.6328 | `0x51CEB3` | D3D8 |
| 1.23.0.6352 | `0x51EC43` | D3D8 |
| 1.24.1.6374 | `0x52D5D3` | D3D8 |
| 1.24.4.6387 | `0x52D653` | D3D8 |
| 1.25.1.6397 | `0x52C923` | D3D8 |
| 1.26.0.6401 | `0x52CB53` | D3D8 |
| 1.27.0.52240 | `0xEBB59` | D3D9 `+0x34` |

## 实机问题（已按此改生成器）

1. **窗口化 DirectX 无法启动（1.26 及更早）**：D3D8 窗口模式 `CreateDevice` 不能把 `PresentationInterval` 设成 IMMEDIATE，也不能去掉 `LOCKABLE_BACKBUFFER`。现只改独占全屏 interval。窗口化 D3D8 仍可能被显示器 vsync 卡住，请用全屏测解锁。
2. **要不要打 war3.exe**：不必打 1.22+。软件 64 从 1.22 起只在 Game.dll 生效，EXE 里是残留。1.21 及更早软件 64 只在 `war3.exe 0x445FE`，必须 DLL+EXE 一起覆盖。
3. **`-opengl` ACCESS_VIOLATION 读 `0x6F8xxxxx`**：cave 写死 ImageBase。给 `.reloc` 追加 HIGHLOW **不够**——cave 在 `.text` VirtualSize 之外时加载器不修这些 RVA。1.27 旧目录 `...-d3d9-ogl` 的 INT3 cave（`0x6F87A98D`）同样无 PIC，崩溃 IP `…A999` 即 cave+12 的 `FF15`。现改为 PIC，并抬高 `.text`/`.rdata` VirtualSize。
4. **1.26 及更早，`-opengl` 在设置里改分辨率写崩溃**：cave 用 `call $+5; pop ebx` 取 PIC 基址。`ebx` 是 callee-saved，1.25 的崩溃指令 `0x6F629510`（`add byte ptr [ecx], 0xFF`）写入的 `0x6F86C3E5` 正好是 cave 里那条 `pop ebx`。1.26 重定位后同样差 `0x242ED5`，目标也是 `.text` 末尾 `VirtualSize+11`。DirectX 不经过这段 hook。1.27 调用约定相同，但改分辨率那条路径没有把活的 `ebx` 留过这个 call。PIC 基址已改为 caller-saved 的 `edx`。

## 测试注意

- **D3D8 窗口化**不再做 interval 解锁；1.26 及更早请测全屏 DirectX + `-opengl`。
- **1.22+ 只覆盖 `game.dll`**；**1.21 及更早覆盖 `game.dll` + `war3.exe`**。
- 用启动器进游戏会按版本从 `versions\` 拷回原件；测补丁请覆盖游戏目录后不要再切版本。
- 1.27 你已验证的 D3D 那份在 `dll_game/1.27.0.52240-fps-unlock-d3d9-ogl/`。本次 `...-fps-unlock-dx-ogl` 加了 reloc，OpenGL 必须用新 DLL 重测。
