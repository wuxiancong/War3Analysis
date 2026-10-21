# Warcraft III 各版本 D3D Reset 边界与分辨率切换分析

## 结论摘要

已在本机 11 个原版 `game.dll` 样本中定位到同一设备重置代码路径的两个实用边界：

- **Reset 前边界（start）**：执行 `game.dll+RVA` 处的 `mov eax, [esi+0x584]`；下方很快通过设备 vtable 调用 D3D `Reset`。
- **Reset/恢复汇合边界（end）**：Reset 返回后检查 HRESULT；成功时先调用版本对应的恢复函数，失败时跳过恢复；两条路径在下表 end RVA 汇合。

这些地址能标记**设备 Reset 与同步恢复阶段**，但不能单独证明“玩家在选项中主动修改分辨率”的 UI 操作开始/结束。设备丢失恢复（包括某些独占全屏焦点切换）也可能进入该路径；反过来，选项 UI 的前置处理可能在 Reset 前已经开始。因此，后续若将这些点用于 callback 的暂停标志，应把标志语义定义为“Reset/恢复进行中”，不要命名或解释为“分辨率菜单正在切换”。

## 各版本边界

所有地址均为相对于 `game.dll` 的 **RVA**，不是文件偏移。样本 ImageBase 均为 `0x6F000000`，故 VA = `0x6F000000 + RVA`。起始位置的 6 字节签名在 11 个版本中相同：`8B 86 84 05 00 00`。

| 版本 | API | Reset 前 start RVA | Reset 调用 RVA | Reset 返回 RVA | 成功恢复调用 RVA → 目标 RVA | HRESULT 分支汇合 end RVA | 原版 DLL SHA-256 |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| 1.0.17.5988 | D3D8 | `0xD3604` | `0xD3611` | `0xD3614` | `0xD361C` → `0xD3FE0` | `0xD3621` | `EA09C582A4C8B4112C1425CC954BF710FED3051E4A85BC39586647C0BD8BF4B2` |
| 1.0.20.6048 | D3D8 | `0xD3604` | `0xD3611` | `0xD3614` | `0xD361C` → `0xD3FE0` | `0xD3621` | `F9166A59D6029E9AF132A090CFAC8E324B0A3452D43C0D30EA39F1E3A82DD982` |
| 1.20.4.6074 | D3D8 | `0xD3604` | `0xD3611` | `0xD3614` | `0xD361C` → `0xD3FE0` | `0xD3621` | `6B5B406861A56449C604C15CF0971DF7D6D26F679EFF7AA69A34946C7D91764B` |
| 1.21.0.6263 | D3D8 | `0xD3604` | `0xD3611` | `0xD3614` | `0xD361C` → `0xD3FE0` | `0xD3621` | `3265E78DD68B1AB6C54957409E472C077F9FE2ABCCE4CFD279E56AF66A6EF6F3` |
| 1.22.0.6328 | D3D8 | `0x51F3D8` | `0x51F3E9` | `0x51F3EB` | `0x51F3F3` → `0x51EE30` | `0x51F3F8` | `5F866BD8A45951CD2C4B22B1C80A0329246DBED847540C85430376E8C4310C84` |
| 1.23.0.6352 | D3D8 | `0x521168` | `0x521179` | `0x52117B` | `0x521183` → `0x520BC0` | `0x521188` | `EE6175947A8792CD672253B37DEB4C5D0577E4E145FFD90FED9021C64C31AE1E` |
| 1.24.1.6374 | D3D8 | `0x52FAF8` | `0x52FB09` | `0x52FB0B` | `0x52FB13` → `0x52F550` | `0x52FB18` | `EE23DD7795EA82DDFC292FDD2A05D5A76D3ABEF801CEC01F0EFF68F521DF0441` |
| 1.24.4.6387 | D3D8 | `0x52FB78` | `0x52FB89` | `0x52FB8B` | `0x52FB93` → `0x52F5D0` | `0x52FB98` | `C7C958174BDE30961A41FA91827E78A800E473EFDD8D1DE8D6C94ABF0B0024BF` |
| 1.25.1.6397 | D3D8 | `0x52EE48` | `0x52EE59` | `0x52EE5B` | `0x52EE63` → `0x52E8A0` | `0x52EE68` | `F504ED38F43BCCF011BF55DC8339EFACD689F4DCD6AF4AFD1815F01B5D026D07` |
| 1.26.0.6401 | D3D8 | `0x52F078` | `0x52F089` | `0x52F08B` | `0x52F093` → `0x52EAD0` | `0x52F098` | `6D21BD9A0F9FBC8446F455C9E89AC994FED68174426FE608FCB9BAEFD4DEC53C` |
| 1.27.0.52240 | D3D9 | `0xECC12` | `0xECC1F` | `0xECC22` | `0xECC2A` → `0xEF590` | `0xECC2F` | `E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A` |

## 控制流解释

共同结构如下（具体寄存器、参数栈位置和恢复函数随版本变化）：

```text
start
  -> 读取 renderer + 0x584 的设备指针并准备 Reset 参数
  -> 调用设备 vtable 的 Reset 槽
  -> 保存 HRESULT；HRESULT == 0 时同步调用恢复函数
  -> 成功恢复路径与失败/跳过恢复路径在 end 汇合
```

- 1.0.17–1.21 的 Reset 调用为 `[edx+0x38]`，符合 D3D8 `IDirect3DDevice8::Reset` 槽偏移。
- 1.22–1.26 先读取 vtable `[ecx+0x38]`，再 `call eax`，仍是 D3D8 Reset。
- 1.27 调用 `[edx+0x40]`，符合 D3D9 `IDirect3DDevice9::Reset` 槽偏移。
- 每个版本的 Reset 调用后都保存 `eax` 的 HRESULT、执行 `test edi, edi`，并由 `jne` 跳过成功恢复调用；失败路径和成功恢复返回路径都到达表中 end RVA。
- 对 1.0.17–1.26，汇合点第一条指令是 `xor eax, eax`；1.27 的汇合点第一条指令是 `mov ecx, [ebp-4]`。不要跨版本复用 end-site 指令签名。

例如 1.27 的局部指令序列：

```asm
game.dll+0xECC12  mov eax, [esi+0x584]
game.dll+0xECC1F  call dword ptr [edx+0x40] ; IDirect3DDevice9::Reset
game.dll+0xECC22  mov edi, eax              ; HRESULT
game.dll+0xECC24  test edi, edi
game.dll+0xECC26  jne  game.dll+0xECC2F     ; 失败：跳过恢复调用
game.dll+0xECC28  mov ecx, esi
game.dll+0xECC2A  call game.dll+0xEF590     ; 成功：同步恢复
game.dll+0xECC2F  mov ecx, [ebp-4]          ; 两条路径汇合
```

## 对后续 Hook 设计的意义

如果后续目标是在设备重置期间避免 `GameBeforeD3DXDoEndScene` callback 做 UI 初始化、D3D 资源创建/绘制或其他设备调用，这组边界可作为**逐版本静态候选点**：在 start 标记 Reset/恢复窗口，在 end 清除标记。它们不等于成品 Hook 已可直接安装；写入代码前仍应验证：

1. 对目标 DLL 的版本识别结果和 SHA-256 与偏移表对应版本一致。
2. 运行时命中 Reset 调用点，确认触发源分别覆盖选项改分辨率与设备丢失恢复；不要只以“发生过 Reset”推断 UI 来源。
3. Reset 失败路径也会到达 end；Reset 本身若卡住或不返回，end 自然不会执行。
4. 线程并发、重入、异常退出和进程关闭时的标志生命周期。单一全局 bool 是否足够，需要运行时确认。
5. end 是函数内的汇合指令地址；实际插桩须保留该版本指令边界、寄存器/栈状态及原始控制流。

特别地，如果需求是“仅在玩家从选项发起的分辨率切换时跳过 callback”，目前这些 Reset 边界还不够：需要继续沿 Reset 调用者向上追踪，并在运行时对照选项操作、Alt+Tab 和设备丢失恢复，寻找可靠的调用来源/状态判据。此处没有找到或声称一个跨版本唯一的分辨率 UI 起点。

## 证据与限制

- **样本范围**：本机 `War3Launcher/versions/<版本>/game.dll` 的 11 个原版样本；表中列出各文件 SHA-256，便于核验目标身份。
- **跨版本核对**：用 Capstone 5.0.9 对 PE32 指令解码，并根据 PE 节区映射把 RVA 转换为文件位置；逐样本校验 start 的 6 字节签名、D3D Reset vtable 槽、HRESULT 测试/条件分支、成功恢复调用及分支目标 end。
- **Ghidra 核对范围**：Ghidra 12.1.4 headless 对 1.27 的现有 `War3_127` 项目进行了只读指令窗口核对；这不是 11 个版本都经过 Ghidra 函数级分析的声明。
- **REA 限制**：Windows REA/Ghidra provider 不接受 D: 可移动卷作为分析目标；1.27 固定卷副本的 SHA-256 与原样本一致，但当时 REA 函数分析请求超时。因此不把 REA 超时包装成函数级反编译结论。
- **没有动态验证**：没有在游戏运行中设置断点或采集这些偏移的命中记录；调用者到底是菜单分辨率变更还是设备丢失恢复，需要动态确认。

既有背景分析：[1.27 分辨率切换与 EndScene Hook 风险](warcraft-iii-1.27-resolution-switch-crash.md)、[FPS 运行时 Hook 与 Reset 路径](warcraft-iii-fps-runtime-hooks.md)。
