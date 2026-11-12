# Warcraft III 战争迷雾的实现位置与机制（Game.dll 1.26 + DotA 6.83d war3map.j）

日期：2026-11-11
样本：
- `C:\Program Files (x86)\iCCup Warcraft III\game.dll`（与 `War3Launcher\versions\1.26.0.6401\game.dll` MD5 相同，基址 `0x6F000000`）
- `C:\Program Files (x86)\iCCup Warcraft III\{War3Patch,War3x,war3}.mpq`
- `D:\Maps\DotA v6.83d.w3x`（`scripts\war3map.j`、`war3map.w3i`）

工具：Qt 自带 `mingw810_32\bin\objdump.exe`（只读反汇编），`mdx-m3-viewer` 的 MPQ 解析器。全程只读，没有修改任何游戏文件。

> 每条结论都标了可信度：
> **[反汇编]** 直接从 game.dll 指令读出；**[数据]** 从 MPQ / 地图文件原文读出；
> **[推断]** 由前两者推出、但没有逐条验证；**[未确认]** 需要运行时调试才能定。

## 1. 结论

**战争迷雾在 game.dll 里实现，war3map.j 只是通过 JASS 原生函数去开关和改写它。**

| 部分 | 在哪里 | 做什么 |
|---|---|---|
| 迷雾栅格、每格每玩家的可见/已探索位、视野计算、渲染 | **game.dll** | 引擎每帧按单位视野更新两张 16 位栅格，按「可见 / 迷雾 / 黑色遮罩」三态绘制与判定 |
| 迷雾开关、黑色遮罩开关 | game.dll 原生函数 `FogEnable` / `FogMaskEnable` | DotA 的 war3map.j **没有调用**这两个函数，沿用引擎默认（大厅「可见度」选项） |
| 「一开局就看得到地形」 | **war3map.j** | 开局对两个电脑玩家创建并立即销毁一个覆盖全图的「可见」修改器，把整张图标记为已探索 |
| 盟友共享视野 | war3map.j | `SetPlayerAlliance(…, ALLIANCE_SHARED_VISION, true)` |
| 临时视野（被塔打的隐身攻击者等） | war3map.j | `CreateFogModifierRadius` + 计时器销毁 |
| 迷雾中攻击暴露、死亡暴露、渐隐速度 | game.dll，参数在 `Units\MiscData.txt` | `FoggedAttackRevealRadius=200`、`DyingRevealRadius=500`、`FogFlashTime=3` |

## 2. game.dll：原生函数注册与处理函数 [反汇编]

1.26 用 fastcall 注册原生函数：`ecx = 处理函数地址`、`edx = 名字字符串`、`push 签名字符串`，然后 `call 0x6F455110`。按名字字符串的引用（`mov edx, imm32`，机器码 `BA xx xx xx xx`）找到：

| 原生函数 | 名字字符串 | 处理函数 |
|---|---|---|
| `IsUnitVisible` | `0x6F948008` | `0x6F3C7AF0` |
| `IsUnitFogged` | `0x6F947FD8` | `0x6F3C7D00` |
| `IsUnitMasked` | `0x6F947FC8` | `0x6F3C7D80` |
| `FogEnable` | `0x6F94A3F0` | `0x6F3BB1E0` |
| `IsFogEnabled` | `0x6F94A3E0` | `0x6F3BB200` |
| `CreateFogModifierRect` | `0x6F94A39C` | `0x6F3D0E70` |
| `CreateFogModifierRadius` | `0x6F94A35C` | `0x6F3D0F90` |
| `DestroyFogModifier` | `0x6F94A2E8` | `0x6F3C1BA0` |
| `FogModifierStart` | `0x6F94A2D4` | `0x6F3C1BC0` |
| `FogModifierStop` | `0x6F94A2C4` | `0x6F3C1BE0` |

两组注册代码分别在 `0x6F3D66C0`（单位相关）和 `0x6F3D4DB0`（迷雾相关）附近；各原生函数在 `0x6F71E7xx / 0x6F7200xx` 还有第二处名字引用（另一张注册表，未展开）。

## 3. game.dll：迷雾管理器与数据结构 [反汇编]

全局游戏对象指针在 `ds:0x6FAB65F4`，**迷雾管理器 = `*(*(0x6FAB65F4) + 0x34)`**（`FogEnable` 与 `IsUnitFogged` 都从这里取）。

| 偏移 | 含义 | 依据 |
|---|---|---|
| `+0x10` | 黑色遮罩开关（`FogMaskEnable`） | 状态表下标 = `[+0x10] + [+0x14]*2` [推断] |
| `+0x14` | 迷雾开关（`FogEnable` 写这里） | `0x6F407E60`：`mov [esi+0x14], edi` |
| `+0x2C` | **已探索**栅格：每格一个 `uint16`，低 12 位 = 12 个玩家 | 读出后 `and ax, 0x0FFF` [推断：哪张是可见、哪张是已探索] |
| `+0x30` | **当前可见**栅格：每格一个 `uint16` | 关闭迷雾时整张清零：`memset([+0x30], 0, (h << shift) * 2)` |
| `+0x44 / +0x48` | 栅格原点（世界坐标最小 Y / X） | 世界→格子：`(world - min) * inv` |
| `+0x60` | 列数（宽） | 格子 X 夹到 `[0, +0x60 - 1]` |
| `+0x68` | 行跨度的位移量（宽按 2 的幂对齐） | 下标 = `(cy << [+0x68]) + cx` |
| `+0x6C` | 行数（高） | 格子 Y 夹到 `[0, +0x6C - 1]` |
| `+0x70 / +0x74` | 1 / 格子边长（X / Y） | 世界→格子乘的是这个值 |

**格子边长 [未确认]**：`+0x70/+0x74` 是运行时按地图尺寸写入的，静态扫描没有找到直接的浮点常量写入，需要挂调试器读内存才能确定是 32、64 还是 128 世界单位。

### 3.1 一个点对某玩家是什么状态

`IsUnitFogged`（`0x6F3C7D00`）的调用链：

1. 句柄 → 单位（`0x6F3BDCB0`），句柄 → 玩家（`0x6F3BD4D0`），玩家编号是 `byte [player+0x30]`。
2. 取单位坐标（单位虚函数表 `+0xB8`），玩家位掩码 `1 << playerId`。
3. `0x6F276240(x, y, mask)` → `0x6F26D0C0` 把世界坐标转成格子并读出两张栅格的值 → `0x6F00E7A0` 查状态表。
4. `IsUnitFogged` 返回 `状态 == 2`；紧随其后的同类函数返回 `状态 == 1`。

`0x6F00E7A0` 在栈上建了一张 4×3 的表，按 `[遮罩开关] + [迷雾开关]*2` 选一行，再按「当前可见 / 已探索未可见 / 未探索」选一列。数值与 common.j 的常量一致：`FOG_OF_WAR_MASKED = 1`、`FOG_OF_WAR_FOGGED = 2`、`FOG_OF_WAR_VISIBLE = 4`：

| 迷雾开关 | 遮罩开关 | 当前可见 | 已探索、当前不可见 | 从未探索 |
|---|---|---|---|---|
| 关 | 关 | 4 可见 | 4 可见 | 4 可见 |
| 关 | 开 | 4 可见 | 4 可见 | 1 黑色遮罩 |
| 开 | 关 | 4 可见 | 2 迷雾 | 2 迷雾 |
| 开 | 开 | 4 可见 | 2 迷雾 | 1 黑色遮罩 |

（列的含义由「四种开关组合都得出合理结果」反推 [推断]。）

### 3.2 单位是否可见不只看格子

`IsUnitVisible`（`0x6F3C7AF0`）不查栅格，而是调用**单位自己的虚函数**（vtable `+0xFC`，参数 `playerId, 0, 4`）。这样隐身、反隐、共享单位视野（`UnitShareVision`）都在单位这一层处理，而不只是「它站的格子亮不亮」[推断]。

### 3.3 `FogEnable` 做了什么（`0x6F407E60`）

- 参数为 0（关闭）时，把 `+0x30` 栅格整张清零，然后写 `[+0x14] = 0`。
- 之后刷新（`0x6F406CC0`、`0x6F392E70` 等），并根据 `[+0x24] & 1`、`[+0x10]`、`[+0x14]` 决定是否重画迷雾层（`0x6F00FAC0`、`0x6F016CD0`）。

## 4. 引擎参数 [数据]

`War3Patch.mpq\Units\MiscData.txt`：

| 键 | 值 | 含义 |
|---|---|---|
| `FoggedAttackRevealRadius` | 200.0 | 从迷雾里发起攻击的单位，会在被攻击方那里暴露半径 200 |
| `DyingRevealRadius` | 500.0 | 单位死亡时暴露周围半径 500 |
| `FogFlashTime` | 3 | 单位在可见 / 不可见之间渐变的速度（注释：越小「隐形」越慢） |

视野半径来自 `Units\UnitBalance.slk` 的 `sight`（白天）/ `nsight`（夜晚）。
树木挡视野：`Units\DestructableData.slk` 的 `occH`（遮挡高度）。DotA 用的树 `ATtr`（灰谷树）`occH = 230`，地面单位的视线会被它挡住。高地挡低地视野也由引擎处理 [推断，未逐条反汇编视线算法]。

## 5. 地图 `war3map.w3i` 的设置 [数据]

- 标志 `0x15C78`，其中 **`0x0010` 遮罩区域部分可见**：未探索区域不是纯黑，能隐约看到地形。
- 其余相关：`0x0040` 自定义队伍、`0x0020` 固定玩家设置。
- 地形雾（与战争迷雾无关，是远处的距离雾）：类型 0，起止 3000–5000，颜色黑。

## 6. DotA 6.83d 的 war3map.j 怎么用迷雾 [数据]

玩家：`BO[0] = Player(0)`（近卫电脑，红）、`BO[1] = Player(1)`（近卫 1 号玩家，蓝）、`CO[0] = Player(6)`（天灾电脑，绿）、`CO[1] = Player(7)`（天灾 1 号玩家，粉）。

| 位置 | 调用 | 作用 |
|---|---|---|
| `main` | 对 `BO[0]`、`CO[0]` 各 `DestroyFogModifier(CreateFogModifierRect(p, FOG_OF_WAR_VISIBLE, MS, true, true))`，`MS = Rect(-7040,-7680,7040,7168)`；另有 (3200,1) 半径 300、两处边路商店 (-7292,4186)/(7348,-4334) 半径 450 | 创建后立即销毁，用来把这些区域**标记为已探索**，所以开局整张图是「迷雾」而不是「黑色遮罩」[推断：效果依赖创建时立即刷新一次栅格] |
| `Z32` | 对所有互为盟友的玩家 `SetPlayerAlliance(…, ALLIANCE_SHARED_VISION, true)`（同时共享控制） | 队友共享视野 |
| `D12` | 近卫/天灾建筑被攻击，且攻击者对 `BO[1]` 或 `CO[1]` 处于迷雾中 → 给建筑所属一方开一个半径 128、持续 1 秒的可见修改器（经 `O71` 计时销毁） | 塔被迷雾中的单位攻击时短暂暴露攻击者 |
| `I41` / `O71` / `SM2` 等 | `CreateFogModifierRadius(p, FOG_OF_WAR_VISIBLE, x, y, r, true, true)` + `FogModifierStart` + 计时器 | 各种技能、物品的临时视野 |
| `QV1` / `JA2` / `KX2` | 对两个电脑玩家 `CreateFogModifierRadius(…, FOG_OF_WAR_MASKED, x, y, 700, false, false)` 后立即销毁 | 把某处半径 700 重新设为未探索 |
| `UnitShareVision`（21 处） | 单位级共享视野 | 信使、召唤物等 |
| 全脚本 | **没有** `FogEnable` / `FogMaskEnable` 调用 | 迷雾和遮罩是否开启取决于大厅的「可见度」设置 |

## 7. 网页版应如何还原

按上面的结论，网页版（`War3Angular/src/app/game/fog.ts`）采用：

1. 每格一个「当前可见」标记（按己方单位/建筑的 `sight`/`nsight` 计算），与引擎 `+0x30` 栅格对应；只影响本端显示，不进入锁步模拟。
2. 视线遮挡：树木（`occH` > 0）和更高的悬崖层挡住视线。
3. 「已探索」按 DotA 的做法视为整张图已探索，因此只有「可见」和「迷雾」两态。迷雾区域地面压暗；敌方单位隐藏；建筑保持显示，与原版一致。
4. 迷雾中攻击的单位按 `FoggedAttackRevealRadius = 200` 暴露。
5. 边缘做柔化和渐变（对应 `FogFlashTime`），不是硬边方块。

## 8. 没有确认的部分

- 迷雾格子的世界边长（`+0x70/+0x74` 的值）：需要运行时读内存。
- 视线算法的细节（光线步进方式、高地判定、`occH` 与单位高度如何比较）：本次只确认了数据来源，没有反汇编视野更新循环。
- `+0x2C` / `+0x30` 哪一张是「已探索」、哪一张是「当前可见」：由清零行为和状态表反推，仍属推断。
- `main` 里「创建即销毁」能留下已探索标记，这个效果是推断，没有在游戏里单独验证。
