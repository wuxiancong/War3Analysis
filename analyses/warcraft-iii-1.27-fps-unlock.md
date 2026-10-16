# Warcraft III 1.27：Game.dll FPS 限制与解除路径

## 结论摘要

- **1.27.0.52240 的主限帧路径是 D3D9 呈现间隔，不是 1.26 及更早常见的约 64 FPS 软件等待循环。** `CGxDeviceD3d` 在填充 `D3DPRESENT_PARAMETERS` 时把 `PresentationInterval`（结构体偏移 `+0x34`）写成 `0`（`D3DPRESENT_INTERVAL_DEFAULT`）。在窗口/无边框全屏下，这通常会跟显示器刷新率同步，表现为约 60 FPS。
- **同一填充函数还把 `Flags`（`+0x2C`）写成 `1`（`D3DPRESENTFLAG_LOCKABLE_BACKBUFFER`）。** 这与公开资料中的 `Video\lockfb` 行为同类：可锁定后台缓冲会增加呈现开销，并常被当作“关 lockfb”的对象。尚未在静态代码里把该立即数与 `lockfb` 配置槽一一绑死。
- **`maxfps` 是独立的整数配置项，默认 200，经 Storm 设置注册写入内部槽 `0x16`。** 启动器把 `fpsLimit==0` 同步成注册表 `300`。现有反编译没有找到“按 `1000/maxfps` 睡眠”的帧调度循环；因此把注册表改成 `0`/`300` 仍约 60 FPS，更符合垂直同步仍开启，而不是 `maxfps` 失效。
- **OpenGL 路径用 `wglSwapLayerBuffers(hdc, 1)` 呈现。** 是否限帧取决于像素格式/驱动交换间隔，不是上面那条 D3D9 立即数。
- **其它 10 个版本只做了字符串与字节模式普查，没有逐个 Ghidra 函数级确认。** 1.26 及更早为 D3D8（`Direct3DCreate8`），`PresentationInterval` 在 D3D8 结构中位于 `+0x38`；`maxfps` 字符串从 1.22 的 `Game.dll` 起出现。

| 项目 | 记录 |
| --- | --- |
| 目标版本 | Warcraft III 1.27.0.52240 |
| 目标文件 | `game.dll` |
| 大小 | 13,187,048 字节 |
| SHA-256 | `E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A` |
| 来源 | `War3Launcher/versions/1.27.0.52240/game.dll` |
| 分析副本 | `C:\War3Analysis\samples\1.27.0.52240\game.dll`（固定 NTFS；与来源哈希一致） |
| 工具 | REA 6.4.0 + Ghidra 12.1.4 headless；Capstone 核对汇编 |
| Ghidra 项目 | `War3Analysis/ghidra/projects/War3_127.gpr`（程序 `/game.dll`） |
| ImageBase | `0x6F000000`；`.text` 文件偏移 = RVA − `0xC00` |
| 分析状态 | 静态定位完成；**未实机改字节、未测帧率** |
| 置信度 | D3D9 `PresentationInterval` 写入：**高**；其为约 60 FPS 主因：**中高（待运行时）**；`maxfps` 软件等待循环：**未找到** |

## 方法与证据边界

1. D: 为可移动 NTFS，REA 的 Windows Ghidra provider 拒绝直接分析。将 `game.dll` 拷到 `C:\War3Analysis\samples\...` 后校验 SHA-256。
2. REA `search maxfps --provider ghidra` 成功（evidence `ev_e633218f8c60156e0a282d4ee31976f964454de8e2112036c31ad11e4ce9bf8d`）。后续 `trace` 因每次重建临时工程约 11 分钟而超时。函数级反编译改走已有 `War3_127` 工程的 `analyzeHeadless -process game.dll -noanalysis -postScript DumpFps.java`。
3. 未运行游戏，未修改磁盘上的原始 `game.dll`。
4. 旧报告 [warcraft-iii-game-dll-map-size-and-fps.md](warcraft-iii-game-dll-map-size-and-fps.md) 只追到 `maxfps` 注册；本报告补上呈现路径。

## 路径 A：D3D9 呈现间隔（1.27 主候选）

### 填充 `D3DPRESENT_PARAMETERS`

函数 `FUN_6f0ec6b0`（VA `0x6F0EC6B0`）先 `memset` 目标 `0x38` 字节（D3D9 呈现参数大小），再按窗口/适配器模式填字段。Ghidra/Capstone 一致看到：

| 结构偏移 | 写入 | D3D9 字段 | 值的含义 |
| ---: | --- | --- | --- |
| `+0x0C` | `1` | `BackBufferCount` | 一块后台缓冲 |
| `+0x18` | `1` | `SwapEffect` | `D3DSWAPEFFECT_DISCARD` |
| `+0x1C` | `[device+0x574]` | `hDeviceWindow` | 窗口句柄 |
| `+0x30` | 来自 `GetAdapterDisplayMode` | `FullScreen_RefreshRateInHz` | 适配器刷新率 |
| `+0x34` | **立即数 `0`** | **`PresentationInterval`** | **`D3DPRESENT_INTERVAL_DEFAULT`** |
| `+0x2C` | **立即数 `1`** | **`Flags`** | **`D3DPRESENTFLAG_LOCKABLE_BACKBUFFER`** |
| `+0x28` | `0x50` | `AutoDepthStencilFormat` | `D3DFMT_D16` |

关键指令：

```text
0x6F0EC759  mov dword ptr [esi + 0x34], 0     ; PresentationInterval = DEFAULT
0x6F0EC7A2  mov dword ptr [esi + 0x2C], 1     ; Flags = LOCKABLE_BACKBUFFER
```

同函数内 `mov edx, 0x16`（`0x6F0EC6FA`）是把内部颜色模式映射成 `D3DFMT_X8R8G8B8`（枚举 22），**不是** `maxfps` 配置键。

`IDirect3D9::GetAdapterDisplayMode` 调用为 `[ecx+0x1C]`（`0x6F0EC728`）。随后该结构会进入 `CreateDevice`/`Reset`。

### Present

`FUN_6f0ed080` 在 `0x6F0ED2D0` 调用 `IDirect3DDevice9::Present`（虚表槽 17，`[edx+0x44]`），参数全 0。限帧发生在设备创建时写入的 interval，而不是 Present 调用点本身。

### 静态补丁候选（仅 1.27，未运行时验证）

| 项目 | PresentationInterval | Flags（lockable） |
| --- | --- | --- |
| VA | `0x6F0EC759` | `0x6F0EC7A2` |
| RVA | `0xEC759` | `0xEC7A2` |
| 文件偏移 | `0xEBB59` | `0xEBBA2` |
| 原始字节 | `C7 46 34 00 00 00 00` | `C7 46 2C 01 00 00 00` |
| 候选替换 | `C7 46 34 00 00 00 80`（`D3DPRESENT_INTERVAL_IMMEDIATE`） | `C7 46 2C 00 00 00 00`（清 Flags） |
| 特征 | `push 0x38` / `memset` 之后、对 `[esi+0x34]` 的立即数写 0 | 同一函数尾部对 `[esi+0x2C]` 写 1 |

优先改 interval。只改 Flags 可能减轻 lockable 开销，但 DEFAULT 仍可能 vsync。运行时也可在 `CreateDevice`/`Reset` 挂钩里改同一字段（启动器 `war3hook.h` 已有 `D3DPRESENT_PARAMETERS_9` 定义，当前未见 FPS 专用 hook）。

**不要把这些 RVA 套到 1.26 及更早。** 那些版本是 D3D8。

## 路径 B：`maxfps` 配置（软件上限，默认 200）

### 注册

| 项 | VA | RVA | 文件偏移 |
| --- | ---: | ---: | ---: |
| 字符串 `"maxfps"` | `0x6F951428` | `0x951428` | `0x950828` |
| 注册 `FUN_6f35d2d0` | `0x6F35D2D0` | `0x35D2D0` | `0x35C6D0` |
| 回调 `FUN_6f35C680` | `0x6F35C680` | `0x35C680` | `0x35BA80` |

```c
void FUN_6f35d2d0(void)
{
  undefined4 kind = 3;
  undefined4 def  = 200;
  FUN_6f179ce0(&kind, 0, FUN_6f35c680, &def, 0);  // ECX = "maxfps"
}
```

回调把读到的整数写入设置槽 `0x16` 并 apply：

```c
void FUN_6f35c680(undefined4 value)
{
  FUN_6f023e00();                 // 单例，无参数
  FUN_6f025a70(0x16, value);      // 槽值存到记录 +0x18
  FUN_6f023e00();
  FUN_6f023240(0x16);             // 按 DAT_6F950DD0[key*4] 的类型 apply
}
```

`FUN_6f023e00` 只保证 `DAT_6FBB8080` 上的设置对象存在。Ghidra 把 `push 0x16` 误标成 `FUN_6f023e00` 的参数；汇编上 `0x16` 是后续 `FUN_6f025a70` / `FUN_6f023240` 的栈参数。

显示字符串 `" FPS: %-4.1f"`（VA `0x6F994009`）属于 OSD，不是限帧。

### 启动器

`RegisterManager`：`fpsLimit > 0` 写该值，否则写 `HKCU\...\Video\maxfps = 300`。`SettingsManager` 默认 `fpsLimit = 0`。这只覆盖配置通道。

### 未找到的部分

在 `.text` 中未定位到把槽 `0x16` 转成帧间隔再 `Sleep`/`Wait` 的循环。`FUN_6f154c30` 虽调用 `QueryPerformanceCounter` + `Sleep(50|500)`，反编译表明这是线程优先级/计时校准，不是逐帧限速。

## 路径 C：`lockfb` 与 OpenGL

- 字符串 `"lockfb"` VA `0x6F95139C`，落在视频设置名字表里（与 `lights`、`unitshadows` 相邻）。Ghidra 对字符串本身无代码 xref；由通用表加载。表项类型字在 `DAT_6F950DD0 + key*16`。`lockfb` 名字出现在 key `0x0C` 记录附近。
- 公开资料：`Video\lockfb = 0` 可避免前/后台锁定，作用于 1.31.1 及更早的 D3D8/D3D9。
- 静态上最接近的硬编码是 `Flags = LOCKABLE_BACKBUFFER`。未证明该立即数每次都读 `lockfb`。
- OpenGL：`FUN_6f0f0cc0` 在 `(device+0x504) & 0x20` 时调用 `wglSwapLayerBuffers(*(hdc+0x57C), 1)`，否则 `glFinish`。IAT：`wglSwapLayerBuffers` `0x6F94E4DC`。

## 跨版本普查（非 Ghidra 确认）

对 `versions\*\game.dll` 的字符串/导入扫描：

| 版本 | D3D | `maxfps` 字符串 | `lockfb` | `wglSwapLayerBuffers` |
| --- | --- | --- | --- | --- |
| 1.0.17–1.21 | Create8 | 无 | 有 | 有 |
| 1.22–1.26 | Create8 | 有 | 有 | 有 |
| 1.27.0.52240 | **Create9** | 有（`0x6F951428`） | 有 | 有 |

社区口径与本静态结果一致：1.24e/1.26a 另有约 64 FPS 软件帽；1.27 起叠加 V-Sync/呈现间隔。1.26 的 64 FPS 循环与 D3D8 `FullScreen_PresentationInterval`（`+0x38`）需单独开 Ghidra 项目，不能套用 `0xEC759`。

`C7 46 34 00 00 00 00` 在各版本中出现多次，多数是无关结构体的 `+0x34` 清零。1.27 必须结合 `push 0x38`（参数块大小）和 `CGxDeviceD3d` 附近的 `Direct3DCreate9` 才能认定。

## 建议的解除顺序（实现时）

1. 运行时或加载补丁把 1.27 的 `PresentationInterval` 改为 `IMMEDIATE`（或 hook `CreateDevice`/`Reset`）。
2. 同步 `lockfb=0`，必要时再清 `Flags` 立即数。
3. 把启动器 `maxfps` 写成目标上限（无限制时用较大值，不要假定 `0` 表示无限：注册回调按整数写入槽 `0x16`）。
4. 原生全屏（`-nativefullscr`）会改变窗口化 vsync 行为，与 DLL 补丁是不同轴。
5. 实机用 `/fps` 或 `" FPS: %-4.1f"` OSD 对比：只改注册表、只改 interval、两者都改。

## 未解决

- 槽 `0x16` 的读取点与帧循环关系。
- `lockfb` 加载后是否写回 `Flags`。
- OpenGL 交换间隔是否另有 `wglSwapInterval` 等价逻辑（本 DLL 无该字符串）。
- 1.22–1.26 的 64 FPS 软件帽地址。
- 任何候选补丁的实机帧率。
