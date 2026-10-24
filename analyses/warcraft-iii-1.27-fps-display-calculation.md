# Warcraft III 1.27：`/fps` 显示的帧率是怎么算的

## 结论

没有必要为了“哪次调用导致掉帧”去挂钩 `game.dll` 里的 FPS 计算函数。`/fps` 打出来的是 **32 帧滑动平均**，文字本身还要等 **250 毫秒** 才刷新一次。一次卡顿会被后面的帧摊平，看不到是哪一个函数造成的。

要和函数耗时对照，应在 Present 入口自己记两帧之间的时间。计算函数仍然值得读，是为了知道屏幕上的数字到底是什么，以及它和限帧不是同一个逻辑。

| 项目 | 记录 |
| --- | --- |
| 目标版本 | Warcraft III 1.27.0.52240 |
| 目标文件 | `War3Launcher/versions/1.27.0.52240/game.dll` |
| 大小 | 13,187,048 字节 |
| SHA-256 | `E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A` |
| ImageBase | `0x6F000000`。`.text` 文件偏移 = RVA − `0xC00` |
| 分析副本 | `C:\War3Analysis\samples\1.27.0.52240\game.dll` |
| 工具 | Capstone 5.0.7 逐指令追踪；时钟导入名和 `FUN_6f154c30` 来自既有 Ghidra 工程（REA 6.4.0 + Ghidra 12.1.4） |
| 验证 | 静态。本轮没有进游戏看 `/fps` |
| 置信度 | 调用链和公式：**高**。屏幕数字与公式一致：**未在本轮实机核对** |

格式串 `" FPS: %-4.1f"` 从 1.21 的 `game.dll` 起就有，1.22–1.27 都有。下面的地址只适用于 1.27.0.52240。1.20 及更早没有这条格式串。补丁说明里的 `/fps` 从 1.21 开始。

这不是 `maxfps`，也不是大约 64 FPS 的软件帽。那两条路径见 [warcraft-iii-1.27-fps-unlock.md](warcraft-iii-1.27-fps-unlock.md)。

## 屏幕上的数字

```text
显示值 = (signed)device[+0x50] / 100.0
格式   = " FPS: %-4.1f"
```

`device` 是全局 `DAT_6FBC5420`。读取函数 `FUN_6f0e5b30`（VA `0x6F0E5B30`）做 `this[index * 4 + 0x34]`。OSD 传入 index `7`，所以是 `this + 0x50`。

`+0x50` 里的整数是 `fps * 100` 四舍五入后的结果。OSD 再除以常量 `100.0`（VA `0x6F9517B8`）。

## 调用链

```text
聊天 "/fps"
  FUN_6f354700  VA 0x6F354700
    首字节必须是 '/'
    名字表 DAT_6F98B480，8 项；第 6 项（下标 5）是 "fps"，长度 3
    跳转表 DAT_6F3549A4[5] = 0x6F35491D
      call FUN_6f35e090          VA 0x6F35E090
        mov [DAT_6FB66630], 0x20
        jmp FUN_6f3b5fd0         VA 0x6F3B5FD0
          把界面对象 +0x144 在 0 和 1 之间翻转

每帧 Present
  D3D9  FUN_6f0ed080  VA 0x6F0ED080，入口 call 0x6F0E65A0
  OpenGL FUN_6f0f0cc0 VA 0x6F0F0CC0，入口 call 0x6F0E65A0
    FUN_6f0e65a0  采样、选定窗口、写入 device+0x70，再发布到 device+0x50

界面刷新（仅 +0x144 != 0）
  FUN_6f3a4980  VA 0x6F3A4980
    call FUN_6f3b0bc0  VA 0x6F3B0BC0
      GetTickCount 间隔 >= 250ms 才格式化
```

D3D 和 OpenGL 共用同一个采样函数。Present 函数一进来就采样，所以这一笔时间是“上次采样到这次 Present 入口”。

## 采样：`FUN_6f0e6da0`（VA `0x6F0E6DA0`）

每次 Present：

1. `RDTSC`（`FUN_6f0e4ee0`，VA `0x6F0E4EE0`）减去上次计数，得到本帧周期数。
2. 写入 128 槽环形缓冲 `DAT_6FB66650`，下标 `DAT_6FB66648 & 0x7F`。
3. 维护 4 个周期累加和。新样本加进去，滑出窗口的旧样本减掉。

| 窗口 | 累加和 | 结果 | 乘数 |
| --- | --- | --- | --- |
| 8 帧 | `DAT_6FB66A50` | `DAT_6FB66A58` | `8.0`（`0x6F95C5F8`） |
| 16 帧 | `DAT_6FB66A60` | `DAT_6FB66A68` | `16.0`（`0x6F95D548`） |
| 32 帧 | `DAT_6FB66A70` | `DAT_6FB66A78` | `32.0`（`0x6F95D808`） |
| 128 帧 | `DAT_6FB66A80` | `DAT_6FB66A88` | `128.0`（`0x6F95D80C`） |

累加和大于 `0x400` 个周期时：

```text
fps = TSC频率(Hz) * N / 窗口内周期和
```

否则写成占位值 `99.99`（立即数 `0x42C7FAE1`）。`0x400` 个周期远小于一帧，只在刚开始采样时出现。

`/fps` 把 `DAT_6FB66630` 设成 `0x20`。返回值按这个数选择窗口：

| `DAT_6FB66630` | 使用的窗口 |
| --- | --- |
| `<= 8` | 8 帧。进程启动时该全局是 0，所以第一次 `/fps` 之前内部用这个 |
| `<= 16` | 16 帧 |
| `<= 32` | 32 帧。`/fps` 写入的就是 32，屏幕用这个 |
| 更大 | 128 帧 |

`/fps` 每次都会把选择器写成 32，不管是打开还是关掉显示。关掉 OSD 之后，发布出去的数仍然是 32 帧平均。

## 频率：`FUN_6f154c30`（VA `0x6F154C30`）

第一次需要频率时：

1. 记下 `RDTSC` 和 `QueryPerformanceCounter`。
2. `GetThreadPriority` 成功则 `Sleep(50)`，失败则 `Sleep(500)`。
3. 再记一次 `RDTSC` 和 `QueryPerformanceCounter`，并读 `QueryPerformanceFrequency`。
4. `(TSC差值 * QPF) / QPC差值`，64 位结果缓存在 `DAT_6FBDABD8`。

这就是 TSC 的每秒周期数。`FUN_6f0e4ec0` 把它放进 x87。窗口函数再用 `FUN_6f77167f` 把周期和转成 XMM 浮点后做除法，不弹出已经放好的频率。

Ghidra 对 `FUN_6f154c30` 的反编译见 `artifacts/warcraft-iii-1.27-fps-unlock/ghidra-fps-dump.txt`。导入槽：`GetTickCount` = `0x6F94E1D8`，`Sleep` = `0x6F94E188`，`QueryPerformanceCounter` = `0x6F94E1DC`，`QueryPerformanceFrequency` = `0x6F94E1E0`。

## 发布和显示

`FUN_6f0e65a0`（VA `0x6F0E65A0`）在 Present 里调用上面的窗口函数，然后：

```text
device[+0x58] += 1                         ; 帧计数，随后被发布逻辑覆盖
fps100 = round(窗口fps * 100.0 + 0.005)    ; 写入 device[+0x70]
```

`FUN_6f0e5b40`（VA `0x6F0E5B40`）把 `device+0x54` 起的 8 个整数复制到 `device+0x34`，再把源清零。复制之后：

| 下标 | 发布后的地址 | 内容 |
| --- | --- | --- |
| 0 | `+0x34` | 另一路整数帧率（`fps + 0.5` 后截成整数），OSD 不用 |
| 7 | `+0x50` | `fps * 100`，`/fps` 用这个 |

`FUN_6f3b0bc0` 用 `GetTickCount`：

- 距上次刷新超过 `10000` ms，或还没有上次时间：把文字清掉。
- 距上次刷新达到 `250` ms：把 `+0x50 / 100.0` 格式化成 `" FPS: %-4.1f"`。
- 不到 250 ms：数值已经在 `+0x50` 里更新了，文字不动。

所以屏幕最多每秒改 4 次，而数值本身每帧都在变。

## 和函数耗时怎么对

Present 入口（`0x6F0ED080` 与 `0x6F0F0CC0`）用 `QueryPerformanceCounter` 记下与上一帧的间隔。这一帧里 `PERF_FUNCTION` 最慢的那几项，就是这次掉帧时主线程上最贵的钩子工作。

直接读 `device+0x50 / 100` 只能得到和 `/fps` 相同的 32 帧平均，不能指出是哪一个函数。计算函数本身只有一次 `RDTSC`、环形缓冲加减和一次除法，不是卡顿来源。

## 地址

| 角色 | VA | RVA |
| --- | ---: | ---: |
| 聊天分发，识别前导 `/` | `0x6F354700` | `0x354700` |
| 命令名表，`"fps"` 在第 6 项 | `0x6F98B480` | `0x98B480` |
| `"fps"` 字符串 | `0x6F98B840` | `0x98B840` |
| `/fps` 分支 | `0x6F35491D` | `0x35491D` |
| 设置 32 帧窗口并跳到开关 | `0x6F35E090` | `0x35E090` |
| 翻转 OSD 开关 `+0x144` | `0x6F3B5FD0` | `0x3B5FD0` |
| 窗口选择器 `DAT_6FB66630` 的写入 | `0x6F0E73F0` | `0xE73F0` |
| D3D9 Present | `0x6F0ED080` | `0xED080` |
| OpenGL Present | `0x6F0F0CC0` | `0xF0CC0` |
| 发布 `fps*100` | `0x6F0E65A0` | `0xE65A0` |
| 四个滑动窗口 | `0x6F0E6DA0` | `0xE6DA0` |
| 读已发布统计，index 7 = `+0x50` | `0x6F0E5B30` | `0xE5B30` |
| OSD 格式化 | `0x6F3B0BC0` | `0x3B0BC0` |
| 格式串 `" FPS: %-4.1f"` | `0x6F994008` | `0x994008` |
| TSC 频率校准 | `0x6F154C30` | `0x154C30` |
