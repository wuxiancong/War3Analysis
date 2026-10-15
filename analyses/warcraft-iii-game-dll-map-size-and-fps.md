# Warcraft III Game.dll：地图大小与 FPS 限制静态分析

## 结论摘要

- **地图大小：已在 1.27.0.52240 的 Game.dll 中由 REA/Ghidra 直接确认。** 处理网络事件的 `FUN_6f85f970` 在 `0x6f85f9b6` 比较地图数据大小与 `0x800000`（8 MiB / 8,388,608 字节）；大于该值时走拒绝路径。恰好 `0x800000` 不会被此比较拒绝。
- **地图检查调用点与项目 hook 表吻合。** 1.27.0.52240 中 `0x6f861291` 是 `FUN_6f860ff0` 内的直接调用，目标为 `FUN_6f85f970`。项目源码把它们分别记录为 RVA `0x861291` 和 `0x85f970`。
- **帧率：没有确认可用于解除限制的 Game.dll 代码补丁点。** REA 找到 `maxfps` 配置项的读取设置代码；项目的 `RegisterManager` 将 `fpsLimit` 写进 `HKCU\Software\Blizzard Entertainment\Warcraft III\Video\maxfps`。这支持“通过配置控制帧率上限”的路径，不支持声称存在已定位的 FPS 硬编码补丁。
- **版本范围：** REA/Ghidra 函数级分析针对 1.27.0.52240；下面 11 个版本的地图 hook 候选地址来自项目版本表，并逐个核验了 DLL 中的相对调用指令及其目的 RVA。除 1.27 外，未将其它版本描述为 REA 函数级反编译确认。

## 分析范围与方法

- 目标：`versions` 目录内的 11 个 `game.dll`。
- REA 提供方：Ghidra 12.1.4；1.27 文件格式为 PE x86，SHA-256：`e04d1716603c075eb0c8e1e21cf1093a664adc5249efab396bfa08d7b09d0c3a`。
- 对原始 1.27 DLL 的静态分析副本进行分析；没有执行游戏或修改任何 DLL。
- Ghidra 显示的是运行时虚拟地址（VA）。本组 DLL 的首选 ImageBase 为 `0x6f000000`，所以 `RVA = VA - 0x6f000000`。RVA 与文件偏移也不是同义词：1.27 `.text` 段的原始文件位置比 RVA 少 `0xC00`。

## 地图大小限制：1.27 直接证据

### 检查函数和阈值

REA 的 `analyze_function` 结果将函数命名为 `FUN_6f85f970`，函数体范围为 `0x6f85f970–0x6f85fb44`。其反编译逻辑为：

```c
iVar2 = FUN_6f852e60(&local_234);
if (((iVar2 == 0) || (local_12c == 0)) || (0x800000 < local_12c)) {
    FUN_6f771125();
    return;
}
```

关键汇编：

| VA | 指令 | 含义 |
|---|---|---|
| `0x6f85f9b6` | `CMP EAX, 0x800000` | 将取得的大小与 8 MiB 比较 |
| `0x6f85f9bb` | `JA 0x6f85fb2f` | 无符号大于时跳到后续路径；前面的伪代码显示该路径退出处理 |

其中 `0x6f85f9b6` 的 RVA 为 `0x85f9b6`，对应本 DLL 文件偏移 `0x85edb6`。此检查也拒绝大小为零的情况。结论仅描述这个静态分支的比较行为，不等同于证明游戏所有载入、传输或地图校验路径均由它控制。

### 网络事件分派关系与调用点

REA 在 `FUN_6f860ff0` 中观察到 `param_2 == 0x3d` 时调用 `FUN_6f85f970`。调用指令位于 VA `0x6f861291`，Ghidra 的 incoming reference 将其分类为非间接的 `UNCONDITIONAL_CALL`，目标精确解析为 `0x6f85f970`。

| 项目 | 地址 |
|---|---|
| 分派函数 | VA `0x6f860ff0` |
| 调用点 | VA `0x6f861291` / RVA `0x861291` / 文件偏移 `0x860691` |
| 大小检查函数 | VA `0x6f85f970` / RVA `0x85f970` / 文件偏移 `0x85ed70` |
| 调用点原始字节 | `E8 DA E6 FF FF` |

对 `E8 rel32` 按 x86 规则解码：`0x861291 + 5 + sign_extend(0xffffe6da) = 0x85f970`。因此，项目表中 1.27 的两个地址分别与该调用点和函数入口相符。

REA 还找到字符串 `NETERROR_MAPFILEBADSIZE`，其引用位于 `FUN_6f2b0650` 的错误类别分派中；该处是错误文本选择/派发证据，不是上面的大小比较指令，不能把它当作阈值所在位置。

### 项目 hook 的用途与边界

`war3hook.cpp` 将表中第一个地址用作 5 字节 `HookType::DirectCall` hook 的修改点，第二个地址传给安装流程作为函数地址；hook 包装器会执行项目回调后跳转到原始函数 trampoline。回调会读取并记录 `dataSize`，在解析到 room 时将 `room + 0x244` 处标记设为 `1`，最后返回 `1`。

这段 hook 实现**没有直接改写** `0x800000` 比较，也仍会跳转到原始函数。因此，表项及回调可作为项目针对地图大小网络事件的 hook 入口证据，但仅凭该静态实现不能证明它在每种模式下都成功移除了全部 8 MiB 限制。需要运行时测试才能确认实际效果；本分析没有进行该测试。

### 11 个版本的 hook 候选位置

以下 RVA 对应 `g_offsetsForGameNetEventCheckMapSize[0]` 的调用点和 `[1]` 的函数入口。每个 DLL 均检查了调用点首字节为 `E8`，并将其 `rel32` 解码后确认目的 RVA 与表中函数 RVA 一致。此验证是 PE 字节级静态核验，不是 11 个版本逐一由 REA/Ghidra 反编译确认。

| Warcraft III 版本 | 调用点 RVA | 函数 RVA | 调用点文件偏移 | 函数文件偏移 |
|---|---:|---:|---:|---:|
| 1.0.17.5988 | `0x6F462F` | `0x6F7B00` | `0x6F462F` | `0x6F7B00` |
| 1.0.20.6048 | `0x6F4B2F` | `0x6F8000` | `0x6F4B2F` | `0x6F8000` |
| 1.20.4.6074 | `0x6F546F` | `0x6F8940` | `0x6F546F` | `0x6F8940` |
| 1.21.0.6263 | `0x6F949F` | `0x6FC970` | `0x6F949F` | `0x6FC970` |
| 1.22.0.6328 | `0x671EAA` | `0x66E4D0` | `0x671EAA` | `0x66E4D0` |
| 1.23.0.6352 | `0x6742FA` | `0x670910` | `0x6742FA` | `0x670910` |
| 1.24.1.6374 | `0x682CEA` | `0x67F300` | `0x682CEA` | `0x67F300` |
| 1.24.4.6387 | `0x682D9A` | `0x67F3B0` | `0x682D9A` | `0x67F3B0` |
| 1.25.1.6397 | `0x6823CA` | `0x67E9E0` | `0x6823CA` | `0x67E9E0` |
| 1.26.0.6401 | `0x6825FA` | `0x67EC10` | `0x6825FA` | `0x67EC10` |
| 1.27.0.52240 | `0x861291` | `0x85F970` | `0x860691` | `0x85ED70` |

前 10 个 DLL 的 `.text` 段 raw offset 与 RVA 相同，因此两列数值恰好一致；1.27 `.text` raw offset 为 `0x400`、RVA 为 `0x1000`，因此两个文件偏移均比对应 RVA 小 `0xC00`。不要将此表中的 RVA 直接当成文件偏移或 VA 使用。

## FPS 限制：观察结果

### Game.dll 中的 `maxfps` 引用

REA 找到 `maxfps` 字符串 VA `0x6f951428`。引用点位于 `FUN_6f35d2d0`：

```c
local_c = 3;
local_8 = 200;
FUN_6f179ce0(&local_c, 0, FUN_6f35c680, &local_8, 0);
```

对应调用参数中，`ECX` 指向 `maxfps` 字符串。Ghidra 对此代码的识别足以确认它将 `maxfps` 传入一段配置读取/注册逻辑，但匿名函数名及反编译结果不足以单独证明 `200` 是 FPS 上限、默认值还是内部参数。REA 还找到格式字符串 `" FPS: %-4.1f"`，其引用属于 FPS 显示路径；显示字符串不是限制逻辑本身。

### 启动器写入路径

本项目的 `RegisterManager` 使用 `QSettings` 指向 `HKCU\Software\Blizzard Entertainment\Warcraft III\Video`。`fpsLimit > 0` 时写入该数值，否则写入 `300`。`SettingsManager` 将配置文件中的 `Display/fpsLimit` 默认读为 `0`。这是启动器对游戏注册表设置的静态代码证据。

**结论：** 对本项目，配置 `fpsLimit` 并同步到 `Video\maxfps` 是有源码支持的调控路径；目前没有 REA 证据证明应修改某个 Game.dll FPS 比较常量/函数来解除帧率限制。若要确认游戏是否实际遵循该配置及数值效果，需要在对应游戏版本上做受控运行时观测。

## 证据索引

### REA/Ghidra（目标：1.27.0.52240）

| 证据 | Evidence ID | 观察 |
|---|---|---|
| `trace_feature("MaximumMapSize")` | `ev_17005fc23a66e700dc1dc5d2de987ef49e51eae6c61837b6e8c1a8f5b8238b42` | 字符串及引用点，非阈值本身 |
| `trace_feature("NETERROR_MAPFILEBADSIZE")` | `ev_9b30a12868e5924822c6013f008965d6ddc1ecb50f93c711cb693289b21ddd28` | 错误字符串引用到 `FUN_6f2b0650` |
| `analyze_function(0x6f85f970)` | `ev_42a57c871ab099d58abc34babc18d190b14601c5dd4af178b8336e49b48d0300` | `0x800000` 比较函数及调用点引用 |
| `analyze_function(0x6f861291)` | `ev_5fa0a569f3974316f58a797d1b6c780da067199eb125bbe0e7cb9a8737513362` | 所在分派函数 `FUN_6f860ff0`；0x3d 分支调用大小检查函数 |
| `trace_feature("maxfps")` | `ev_ef7b91a2488895eb033bf6d34701249f776161cd59189090242fd6c78276768b` | `maxfps` 字符串引用到读取/注册辅助函数 |
| `analyze_function(0x6f35d2d0)` | `ev_ea04842b6531d722dae30e4750bdb62801bf0a65e997befb45940b2a6165a1f6` | `maxfps` 调用点及其参数 |

### 仓库源码交叉佐证

- [war3hook.cpp](D:/Qt/workspace/War3Launcher/hooker/war3hook.cpp)：版本 RVA 表约第 3859 行；hook 安装与回调约第 27524 行起。
- [RegisterManager.cpp](D:/Qt/workspace/War3Launcher/managers/RegisterManager.cpp)：单项同步写入 `maxfps` 约第 53 行；批量注册表同步约第 176–177 行。
- [SettingsManager.cpp](D:/Qt/workspace/War3Launcher/managers/SettingsManager.cpp)：`fpsLimit` 默认读取约第 470 行，初始化为 `0` 约第 698 行。

## 限制与复核建议

1. 1.27 分析中的函数由 Ghidra 自动命名（`FUN_...`），不是原始符号名称；语义来自其伪代码、汇编和交叉引用。
2. 地图 hook 的其它 10 个版本仅做了表项与 PE 直接调用字节核验；未对它们逐一运行 Ghidra 函数级分析。
3. 静态代码不能证明特定魔兽客户端、网络模式或启动器配置下的运行时结果。
4. 如果后续要实验性修改，应先备份目标 DLL，只对副本操作，并单独验证所有受影响版本；本报告不把候选 RVA 作为通用的可直接写入补丁。
