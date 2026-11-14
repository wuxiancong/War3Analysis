# GameNetCommandAllyPingXY（原 GameMinimapCameraToWorld）与 GameCameraPositionSetter

## 结论

| Hook 名称 | game.dll 实际作用 | 1.26 RVA | 1.27 RVA | 用途 |
|---|---|---|---|---|
| `GameNetCommandAllyPingXY` | 小地图 Alt+点击「友军信号」：构造 `CNetCommandAllyPing` 并广播给盟友 | 0x33BBF0 | 0x3A76D0 | `-minimap ping` / `/minimap ping` |
| `GameCameraPositionSetter` | JASS 原生 `SetCameraPosition(real x, real y)`：移动本地镜头 | 0x3B45D0 | 0x1F4200 | 预留给 `-minimap move` / `/minimap move` |

旧名 `GameMinimapCameraToWorld` 误以为该函数是「小地图坐标 → 移动镜头」，联调截图证实它只会在小地图上发出信号，镜头不动，所以改名。新名与旧名等长（`Game` + 20 字符）。

## 1.27 反编译（Ghidra，game.dll 基址 0x6F000000）

```c
// RVA 0x3A76D0 —— GameNetCommandAllyPingXY
void FUN_6f3a76d0(undefined4 *xyz)
{
    FUN_6f33b410();                 // → FUN_6f33bc20()，调用方很多，作用未确认（推测为刷新小地图/输入状态）
    FUN_6f2522d0(xyz[0], xyz[1]);   // 发送友军信号
}

// 构造网络命令 CNetCommandAllyPing
void __fastcall FUN_6f2522d0(undefined4 *x, undefined4 *y)
{
    ... FUN_6f24d990(..., CNetCommandAllyPing::vftable, 0, 0xa0068, 0, 2, 0x68, *x, *y, DAT_6fbb81e8);
}
```

- 网络动作 ID `0x68`（标志位 `0xa0068`）对应 W3GS 动作「Minimap signal / ally ping」，由命令队列同步给盟友。
- `FUN_6f3a76d0` 的调用方：`6f3a5df0`、`6f3a6ac0`、`6f3a0fa0`、`6f377b90`、`6f3a4aa0`（小地图鼠标事件处理路径）。

## SetCameraPosition（GameCameraPositionSetter）

原生函数注册表片段：`push "(RR)V"; mov edx, "SetCameraPosition"; mov ecx, 0x6F1F4200`（1.27）。
cdecl，real 参数以 `float*` 传入：`void __cdecl f(float *x, float *y)`。

各版本 RVA：1.0.17/1.0.20 0x2DD0D0，1.20.4 0x2DD1F0，1.21 0x2E07C0，1.22 0x3AED90，1.23 0x3B0A90，
1.24.1 0x3B5050，1.24.4 0x3B5110，1.25.1 0x3B43A0，1.26 0x3B45D0，1.27 0x1F4200。

## GameNetCommandAllyPingXY 各版本 RVA

1.22 0x33B030，1.23 0x33C5B0，1.24.1 0x33C670，1.24.4 0x33C730，1.25.1 0x33B9C0，1.26 0x33BBF0，1.27 0x3A76D0。
1.0.x–1.21 没有表项，运行时靠特征码扫描兜底。

## 原始输出

- `artifacts/email-bind/1.27-minimap-ping-vs-camera.txt`
- `artifacts/email-bind/1.27-minimap-ping-callees.txt`
