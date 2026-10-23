# Warcraft III 全版本 D3D Release 与 OpenGL Present/Reset 偏移

## 1. 结论

`GameBeforeD3DXReleaseRef` **不是 1.27 独有**。11 个 `game.dll` 里都有同一段设备销毁尾部：`mov esi, ecx` 之后用 `SetWindowLongA` 恢复窗口过程，再对渲染器对象 `+0x584` 上的 D3D 设备调用 COM `Release`（vtable `+8`），然后把该指针写成 0。现有钩子在命中点读 `[esi+0x584]`，这三个时期都成立。

代码生成分成三个时期，特征码不能共用，但每个时期一条特征码在全部样本上**只命中一次**，而且另外两个时期的特征码命中次数为 0。因此按「1.22 以下 → 1.22–1.26 → 1.27」逐条独立搜索时，第一条命中就是目标。

| 钩子 | 语义 | 钩子落点 | 前 6 字节是否落在指令边界 |
|---|---|---|---|
| D3DX Release | 设备 COM `Release` 并清空 `+0x584` | 函数内部的 `mov r32, [esi+0x584]` | 是，恰好 6 字节 |
| OGLX DoEndScene | OpenGL 虚表槽 17，`ScenePresent` | 函数入口 | 是 |
| OGLX ReSetScene | OpenGL 虚表槽 5，显示模式/上下文重建 | 函数入口 | 是 |

地址都是 **RVA**。样本 ImageBase 均为 `0x6F000000`，VA = `0x6F000000 + RVA`。尚未在游戏进程里下断点。

## 2. 样本

`War3Launcher\versions\<版本>\game.dll`。SHA-256 与既有 OpenGL 绘制分析使用的是同一批文件；本次又核对了 1.22 副本 `5F866BD8…`。

| 版本 | 时期 | SHA-256 |
|---|---|---|
| 1.0.17.5988 | 1.22 以下 | `EA09C582A4C8B4112C1425CC954BF710FED3051E4A85BC39586647C0BD8BF4B2` |
| 1.0.20.6048 | 1.22 以下 | `F9166A59D6029E9AF132A090CFAC8E324B0A3452D43C0D30EA39F1E3A82DD982` |
| 1.20.4.6074 | 1.22 以下 | `6B5B406861A56449C604C15CF0971DF7D6D26F679EFF7AA69A34946C7D91764B` |
| 1.21.0.6263 | 1.22 以下 | `3265E78DD68B1AB6C54957409E472C077F9FE2ABCCE4CFD279E56AF66A6EF6F3` |
| 1.22.0.6328 | 1.22–1.26 | `5F866BD8A45951CD2C4B22B1C80A0329246DBED847540C85430376E8C4310C84` |
| 1.23.0.6352 | 1.22–1.26 | `EE6175947A8792CD672253B37DEB4C5D0577E4E145FFD90FED9021C64C31AE1E` |
| 1.24.1.6374 | 1.22–1.26 | `EE23DD7795EA82DDFC292FDD2A05D5A76D3ABEF801CEC01F0EFF68F521DF0441` |
| 1.24.4.6387 | 1.22–1.26 | `C7C958174BDE30961A41FA91827E78A800E473EFDD8D1DE8D6C94ABF0B0024BF` |
| 1.25.1.6397 | 1.22–1.26 | `F504ED38F43BCCF011BF55DC8339EFACD689F4DCD6AF4AFD1815F01B5D026D07` |
| 1.26.0.6401 | 1.22–1.26 | `6D21BD9A0F9FBC8446F455C9E89AC994FED68174426FE608FCB9BAEFD4DEC53C` |
| 1.27.0.52240 | 1.27 | `E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A` |

## 3. D3D Release

函数形态在三个时期一致，只是调用 `Release` 的指令不同：

```text
push esi
mov  esi, ecx                  ; this = 渲染器
mov  ecx, [esi+0x574]          ; HWND
push -4                        ; GWL_WNDPROC
push ecx
call USER32!SetWindowLongA
push 1
mov  ecx, esi
call <helper>
; ---- 钩子 RVA 在这里 ----
mov  reg, [esi+0x584]          ; D3D 设备
test reg, reg
jz   skip
mov  edx/eax, [reg]            ; vtable
push reg
call Release                   ; vtable+8，即 IUnknown::Release
mov  dword ptr [esi+0x584], 0
skip:
pop  esi
ret
```

| 时期 | `Release` 调用 | 钩子前 6 字节 |
|---|---|---|
| 1.22 以下 | `call dword ptr [edx+8]` | `8B 86 84 05 00 00`（`mov eax, [esi+0x584]`） |
| 1.22–1.26 | `mov eax, [edx+8]` / `call eax` | `8B 86 84 05 00 00` |
| 1.27 | `call dword ptr [eax+8]` | `8B 8E 84 05 00 00`（`mov ecx, [esi+0x584]`） |

D3D8 与 D3D9 的槽 2 都是 `IUnknown::Release`，所以 `+8` 在 1.27 前后含义相同。1.0.17、1.22、1.26 的 `call [IAT]` 均解析为 `USER32.dll!SetWindowLongA`。

### 偏移（RVA）

| 版本 | Release 钩子 | 函数入口（`mov esi, ecx` 所在函数） |
|---|---:|---:|
| 1.0.17 / 1.0.20 / 1.20.4 / 1.21 | `0x0D0611` | `0x0D05F0` |
| 1.22.0.6328 | `0x51D451` | `0x51D430` |
| 1.23.0.6352 | `0x51F1E1` | 未逐条标入口，钩子字节与 1.22 相同 |
| 1.24.1.6374 | `0x52DB71` | 同上 |
| 1.24.4.6387 | `0x52DBF1` | 同上 |
| 1.25.1.6397 | `0x52CEC1` | 同上 |
| 1.26.0.6401 | `0x52D0F1` | `0x52D0D0` |
| 1.27.0.52240 | `0x0EC510` | `0x0EC4F0`（Ghidra `FUN_6f0ec4f0`） |

1.27 的 Ghidra 12.1.4 反编译（项目 `War3_127`，`DumpDrawHooks.java`，`-noanalysis`）：

```c
void __fastcall FUN_6f0ec4f0(int param_1) {
  SetWindowLongA(*(undefined4 *)(param_1 + 0x574), 0xfffffffc, DAT_6fbc5e98);
  FUN_6f0ec5a0(1);
  piVar1 = *(int **)(param_1 + 0x584);
  if (piVar1 != 0) {
    (**(code **)(*piVar1 + 8))(piVar1);
    *(undefined4 *)(param_1 + 0x584) = 0;
  }
}
```

钩子在 `0xEC510`，是函数内部，不是入口。进入钩子时 `esi` 已经等于 `this`。

### 特征码

每条都在所属时期的每个样本上命中 1 次，在其他时期命中 0 次。`??` 只盖住 `jz` 的短跳转位移。

| 时期 | 特征码 |
|---|---|
| 1.22 以下 | `8B 86 84 05 00 00 85 C0 74 ?? 8B 10 50 FF 52 08 C7 86 84 05 00 00 00 00 00 00` |
| 1.22–1.26 | `8B 86 84 05 00 00 85 C0 74 ?? 8B 10 50 8B 42 08 FF D0 C7 86 84 05 00 00 00 00 00 00` |
| 1.27 | `8B 8E 84 05 00 00 85 C9 74 ?? 8B 01 51 FF 50 08 C7 86 84 05 00 00 00 00 00 00` |

原先只收录 1.27 的那条，在 1.0.17–1.26 上命中次数为 0，所以旧表看起来像“只有 1.27”。

## 4. OpenGL ScenePresent（DoEndScene，虚表槽 17）

既有 RVA 与本次扫描一致。每个版本的函数窗口内都有 `call [opengl32!wglSwapLayerBuffers]`。1.27 Ghidra 反编译：`+0x504` 的 `0x20` 位为 0 时 `glFinish()`，否则 `wglSwapLayerBuffers(this+0x57C, 1)`。钩子在入口，`ecx` 是渲染器。

| 版本 | RVA | 入口前 6 字节 |
|---|---:|---|
| 1.0.17 / 1.0.20 / 1.20.4 / 1.21 | `0x0D5BD0` | `55 8B EC 83 EC 0C` |
| 1.22.0.6328 | `0x5235E0` | `83 EC 08 53 55 56` |
| 1.23.0.6352 | `0x525370` | 同上 |
| 1.24.1.6374 | `0x533D00` | 同上 |
| 1.24.4.6387 | `0x533D80` | 同上 |
| 1.25.1.6397 | `0x533050` | 同上 |
| 1.26.0.6401 | `0x533280` | 同上 |
| 1.27.0.52240 | `0x0F0CC0` | `55 8B EC 83 EC 08` |

| 时期 | 特征码 | 样本内命中 |
|---|---|---|
| 1.22 以下 | `55 8B EC 83 EC 0C 53 56 8B 75 08 57 8B D9 8B BB 60 05 00 00` | 1，且是首次 |
| 1.22–1.26 | `83 EC 08 53 55 56 57 8B 7C 24 1C 8B F1` | 1，且是首次 |
| 1.27 | `55 8B EC 83 EC 08 53 8B 5D 08 56 57 8B F9 53 8B 87 60 05 00 00` | 1，且是首次 |

1.22 以下读 `[ebx+0x560]`，1.27 读 `[edi+0x560]`，与 1.27 反编译里 Present 前保存的 `+0x560` 标志是同一字段。

## 5. OpenGL 显示模式重置（ReSetScene，虚表槽 5）

每个版本从该 RVA 起的函数里都能直接或经一层 `call` 找到 `USER32!ChangeDisplaySettingsExA`。1.22 以下入口把 `this+0x94` 起 6 个 dword（`mov ecx, 6` / `rep movsd`）拷进栈，这是显示模式字段。1.27 Ghidra 反编译在两次内部尝试失败后调用 `ChangeDisplaySettingsExA(0,0,0,0,0)`。钩子在入口，`ecx` 是渲染器。

| 版本 | RVA | 入口前 6 字节 |
|---|---:|---|
| 1.0.17 / 1.0.20 / 1.20.4 / 1.21 | `0x0CBED0` | `55 8B EC 83 EC 18` |
| 1.22.0.6328 | `0x51AC70` | `83 EC 18 56 8B F1` |
| 1.23.0.6352 | `0x51CA00` | 同上 |
| 1.24.1.6374 | `0x52B390` | 同上 |
| 1.24.4.6387 | `0x52B410` | 同上 |
| 1.25.1.6397 | `0x52A6E0` | 同上 |
| 1.26.0.6401 | `0x52A910` | 同上 |
| 1.27.0.52240 | `0x0E7670` | `55 8B EC 83 EC 1C` |

| 时期 | 特征码 | 样本内命中 |
|---|---|---|
| 1.22 以下 | `55 8B EC 83 EC 18 53 56 8B D9 57 8D B3 94 00 00 00 B9 06 00 00 00 8D 7D E8 F3 A5 8B CB E8 ?? ?? ?? ?? 8B 75 08` | 1，且是首次 |
| 1.22–1.26 | `83 EC 18 56 8B F1 8B 8E 98 00 00 00 8B 86 94 00 00 00 8B 96 9C 00 00 00 89 4C 24 08 8B 8E A4 00 00 00 89 44 24 04 8B 86 A0 00 00 00 89 54 24 0C 8B 96 A8 00 00 00 89 4C 24 14 57 8B CE 89 44 24 14 89 54 24 1C E8 ?? ?? ?? ?? 8B 7C 24 24` | 1，且是首次 |
| 1.27 | `55 8B EC 83 EC 1C A1 ?? ?? ?? ?? 33 C5 89 45 FC 53 56 8B 75 08 57` | 1，且是首次 |

1.27 的 `A1 ?? ?? ?? ??` 是 `/GS` cookie，不能写成绝对地址。

## 6. 接到 war3hook 时要注意的搜索方式

`findOffsetBySigns(vector)` 把多条特征码当成 **128 字节内的链**，返回最后一条的地址。上面每个向量里的三条是**互斥的整段特征**，不能走那条链。

`findVersionOffsetOrAlternative` 先查版本表；版本未知时按向量顺序把每一条当作独立特征码搜索，命中即返回。11 个样本上，第一个有命中的特征码，其全模块首次出现就是上表 RVA。

`jumpWhenMoveGameBeforeD3DXReleaseRef` 继续读 `[esi+0x584]` 即可，不必按时期改寄存器。OpenGL 两个钩子继续在入口 `push ecx`。

## 7. 证据与限制

| 项目 | 证据 | 置信度 |
|---|---|---|
| Release 全版本 RVA 与三条特征码 | 11 个镜像按字节搜索；1.0.17 / 1.22 / 1.26 反汇编与 1.27 同构；`SetWindowLongA` 导入名已核对 | 高 |
| 1.27 三个函数的语义 | Ghidra 12.1.4 headless，既有项目 `ghidra/projects/War3_127`，脚本 `shared/ghidra-scripts/DumpDrawHooks.java`，输出 `artifacts/draw-hooks/ghidra-127-draw-hooks.txt` | 高（反编译，未运行） |
| 1.22 Release 语义 | REA 6.4.0 + Ghidra 12.1.4，`function 0x6F51D451`。函数入口 `FUN_6f51d430`。evidence `ev_6cf9bc8ccc0404e18202c63a231cdfd47471e3f9ca51a046c58b358454795fbd`。摘录 `artifacts/draw-hooks/rea-122-release.txt` | 高（反编译，未运行） |
| OpenGL 两个 RVA | 与既有虚表槽一致；Present 含 `wglSwapLayerBuffers`；Reset 含 `ChangeDisplaySettingsExA` | 高 |
| 三条时期特征码“首次即目标” | `verify_draw_sigs.py` 对 11×3×3 做全镜像首次命中 | 高 |
| 运行时是否在改分辨率、退出、丢设备时走到 Release | 无 | 未验证 |

REA 的 Ghidra provider 不接受可移动卷上的 `D:` 样本。1.22 复制到 `C:\War3Analysis\samples\1.22.0.6328\game.dll` 后再分析，SHA-256 与原件一致。反编译与 1.27 的 `FUN_6f0ec4f0` 同构：`in_ECX` 为 this，`SetWindowLongA(this+0x574, -4, ...)`，然后 `Release(*(this+0x584))` 并清零。查询地址 `0x6F51D451` 落在函数内部，入口是 `0x6F51D430`。

1.0.17 与 1.26 没有再跑一遍完整自动分析。它们的指令序列、`SetWindowLongA` 导入和 `+0x574` / `+0x584` 布局与已经反编译的 1.22、1.27 相同。

未验证：

- 没有在游戏里对这三个 RVA 下断。
- `FUN_6f0ec5a0(1)` / 1.22 的 `call 0x51CF00` 只知道发生在 `Release` 之前，没有单独命名。
- 1.23–1.25 的 Release 函数入口没有逐条标出，钩子 RVA 由唯一特征码确定，入口形态在 1.22 与 1.26 上相同。
