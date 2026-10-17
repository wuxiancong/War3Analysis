# Warcraft III 1.27：Game.dll FPS 限制与解除路径

## 结论摘要

- **1.27 仍保留 1.26 那条约 64 FPS 软件调度，并叠加 D3D9 垂直同步。** 只改 `PresentationInterval` 时，全屏 `/fps` 仍约 64，与 60Hz vsync 不符。软件点在 `FUN_6f05fcd0`：当 `[obj+0x2C] != 1` 且 `[obj+0x44]` bit2 置位时，`and eax, 0xFFFFFFFB` 清 bit2，再以 `edx=0x11` 调用 `FUN_6f05ae90`。1.26 对应 `Game.dll+0x62D7FB`（`83 E0 FB` / `mov edx, 0x11`）。社区 WarcraftHelper 1.27a 把 RVA `0x5FCFB` 的 `FB` 改成 `FF`（`and eax, -1`）。
- **D3D9：`FUN_6f0ec6b0` 在独占全屏分支把 `PresentationInterval`（`+0x34`）写成 `0`（`DEFAULT`）。窗口化分支不写该字段，memset 后仍是 DEFAULT。** 前一版补丁只改了独占分支，窗口/无边框全屏仍可能 vsync。
- **同一填充函数还把 `Flags`（`+0x2C`）写成 `1`（`LOCKABLE_BACKBUFFER`）。** 与公开资料中的 `Video\lockfb` 同类，尚未与配置槽一一绑死。
- **`maxfps` 槽 `0x16` 的 apply（`FUN_6f023310` case VA `0x6F023537`）计算 `1000.0 / value` 毫秒，写入定时对象 `+0x48`（`FUN_6f057b80`）。** 启动器 `fpsLimit==0` → 注册表 `300`，对应约 3.3ms 间隔，**不是** 64 FPS。游戏默认 200。
- **OpenGL 路径用 `wglSwapLayerBuffers(hdc, 1)` 呈现。** 限帧还取决于驱动交换间隔。
- **其它 10 个版本只做了字符串与字节模式普查。** 1.26 及更早为 D3D8；`maxfps` 字符串从 1.22 起出现。

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
| 分析状态 | 静态已定位软件 64 帽 + 双分支 D3D interval；已重新打补丁；**实机 `/fps` 仍待验证** |
| 补丁输出 | `dll_game/1.27.0.52240-fps-unlock-d3d9-ogl/game.dll` |
| 补丁 SHA-256 | `60b2a320d25a5304c7808b662e18c958d373e2f56fbb946f5447d2deb34ef1aa` |
| 置信度 | 软件 64 点与 1.26/WarcraftHelper 对齐：**高**；D3D interval 写入：**高**；补丁后实机帧率：**未测** |

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

`FUN_6f0e51f0`：`[device+0x9C]==0` 则返回 1，走窗口化分支 `0x6F0EC763`（`Windowed=1`，**不写** `+0x34`）。非 0 走独占全屏并写 interval。补丁在窗口化路径 `0x6F0EC794` 跳到 cave `0x6F19DFC2`，补写 `IMMEDIATE` 再回到 `0x6F0EC79E`。

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

### apply（已定位）

槽 `0x16` 经 `FUN_6f023310` 跳到 `0x6F023537`：把整数转 double，用 `1.0/value * 1000.0`（常量 `0x6F9517A8` / `0x6F9517B0`），`FUN_6f7714c1` 取整后 `FUN_6f057b80` 写入对象 `+0x48`。这是 `maxfps` 软件上限，默认 200 / 启动器 300，解释不了稳定 ~64。

`FUN_6f154c30` 的 `QueryPerformanceCounter` + `Sleep(50|500)` 是计时校准，不是逐帧限速。

## 路径 D：软件 64 FPS（1.26 同源）

| 项 | 1.27.0.52240 | 1.26.0.6401 |
| --- | --- | --- |
| 函数 | `FUN_6f05fcd0` VA `0x6F05FCD0` | 同构：`test al, 4` / `and eax, ~4` / `edx=0x11` |
| 立即数 `FB` | VA `0x6F05FCFB`，RVA `0x5FCFB`，文件 `0x5F0FB` | `Game.dll+0x62D7FB` |
| 原始 | `83 E0 FB`（`and eax, 0xFFFFFFFB`） | 相同 |
| 补丁 | `83 E0 FF` | WarcraftHelper / 社区 FPS Unlocker 同改 |
| 随后 | `lea edx, [ebx+0x11]`；`mov [edi+0x44], eax`；`call FUN_6f05ae90` | `push 0`；`mov edx, 0x11` |

条件：`[edi+0x2C] != 1` 且 flags bit2 置位。`FUN_6f05ae90` 按 `edx` 派发（`edx*2+0x17` 索引到对象内槽）。把 `FB`→`FF` 后 and 不再清 bit2，与公开 1.27a 解锁器一致。`.text` 中仅此一处 `83 E0 FB` 紧接 `edx=0x11`。

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

社区口径：1.24e/1.26a 有约 64 FPS 软件帽；1.27 叠加 V-Sync。1.27 软件帽已按字节特征对齐到 `0x5FCFB`，不再需要单独的 1.26 Ghidra 项目来打 1.27 补丁。1.26 D3D8 interval 在结构 `+0x38`，不能套用 `0xEC759`。

`C7 46 34 00 00 00 00` 在各版本中出现多次，多数是无关结构体的 `+0x34` 清零。1.27 必须结合 `push 0x38`（参数块大小）和 `CGxDeviceD3d` 附近的 `Direct3DCreate9` 才能认定。

## 建议的解除顺序（实现时）

1. 打软件 64 点（`0x5FCFB` `FB`→`FF`）。
2. 独占全屏与窗口化两条分支都把 `PresentationInterval` 写成 `IMMEDIATE`；清 lockable Flags。
3. OpenGL 调 `wglSwapIntervalEXT(0)`。
4. `maxfps` 用较大值（启动器已写 300；DLL 默认改为 10000）。`0` 不代表无限。
5. 覆盖游戏目录后核对 SHA-256；用启动器切版本会从 `versions\` 还原原版 DLL。
6. 实机 `/fps` 验证（本补丁仍未在本机测帧）。

## 未解决

- `FUN_6f05ae90(edx=0x11)` 内部如何变成 ~64Hz，尚未逐指令跟完。
- `lockfb` 加载后是否写回 `Flags`。
- 补丁 DLL 的实机帧率。
