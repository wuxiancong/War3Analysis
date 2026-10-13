# DotA v6.83d：SD 三选一候选英雄链路

## 目标与结论

目标是本机样本 `D:\Maps\DotA v6.83d.w3x` 中的 SD（Single Draft，单一征召/三选一）英雄候选。要回答的是：A 玩家自己的游戏进程能否观察到 B 玩家及其他玩家能量圈里的三个候选。

**结论：可以，且脚本级链路已确认。** 该 JASS 在 SD 初始化时遍历两队玩家，为每个正在游戏的人从三个独立候选池分别随机抽取一名英雄，再把三个英雄加入该玩家自己的 `D30[playerId]` 能量圈库存。该逻辑没有 `GetLocalPlayer()` 限制，因此在同步对局模拟中，A 客户端也会执行并持有 B 及其他玩家的候选状态。配合本机 Hook 对所有玩家能量圈的 `AddUnitToStock` 捕获，A 可以取得每个玩家的三个候选 rawcode。

这指候选单位 ID/rawcode 对 A 本地游戏进程和 Hook 可见；不意味着地图 UI 会向 A 显示 B 的候选。脚本通过 `LC2` 把每个候选英雄的玩家科技上限对除当前候选所属玩家外的玩家设为 0，限制其他玩家选择该候选。候选捕获的 DLL→Launcher IPC 仍是本机进程间消息，不会自动发给对局中的其他客户端。

## 样本与限制

| 项目 | 记录 |
| --- | --- |
| 地图 | DotA v6.83d（文件名 `DotA v6.83d.w3x`） |
| 文件大小 | 8,296,502 字节 |
| SHA-256 | `C06547206849F7931AD61509E21B76D22D63AE38D05FE7F35DAB48C3DFF56DDF` |
| 地图文件时间 | 2015-06-10 |
| JASS 源文件 | `D:\Qt\workspace\War3Script\war3map.j` |
| JASS 大小 / SHA-256 | 3,026,043 字节 / `0CAE7BDE83B19B40F810B936A923112188CB1FF9B69632BDE1CB6CBDED127347` |
| 结果状态 | JASS 随机生成链和 1.27 `GetRandomInt` 状态推进实现已还原；一轮日志捕获到玩家索引 1 的三个候选及含所选候选的动作；随机种子来源、跨客户端状态对齐和多槽位实测仍未验证 |

该 JASS 文件与 `D:\Qt\workspace\War3Bot\war3files\war3map.j` 及启动器构建目录中的同名文件逐字节 SHA-256 一致。目标 W3X 的 MPQ 脚本项本身带保护/加密标记，因此当前可确认的是：本地这份可读脚本与周边工程使用的版本一致；但没有从加密 MPQ 中解密并逐字节证明它就是该 W3X 内脚本。地图文件哈希和脚本哈希应作为两个独立样本身份记录。

## JASS 随机与三候选生成链

可读 JASS 中的函数名部分经过混淆，但函数体和调用关系可直接追踪：

1. **模式分派：** 初始化代码把字符串 `"XI2"` 映射到常量 `SD`（约 33352 行）。随机模式分派函数 `X12` 的分支 `L42 == 2` 会执行 `ExecuteFunc("XI2")`（约 38580 行）。
2. **逐个处理两队玩家：** `XI2` 循环 `i = 1..5`，依次检查 `BO[i]` 与 `CO[i]`。`T3I(p)` 仅在玩家槽位处于 `PLAYING` 且控制器为 `MAP_CONTROL_USER` 时通过；所以每个实际参赛的人类玩家分别生成候选，而不是只处理本机玩家。
3. **从三类候选池独立抽取：** `LD2(type)` 使用 `GetRandomInt(1,count)` 从相应单位池取样，再以 `GetUnitPointValueByType` 转成 `DC0` 英雄表索引：
   - `type == 1`：池 `DZ0`，35 个单位。
   - `type == 2`：池 `DW0`，37 个单位。
   - `type == 3`：池 `DY0`，40 个索引（其中一项通过 `DC0[97]` 间接引用）。

   `LF2` 为三个类型各调用一次。它排除同一组三选一中已选出的索引；当 `F2` 为 false 时，还会重抽全局 `R[index]` 已标记的候选并把新索引标记为已用。`F2` 为 true 时则走直接返回分支，仅检查本组三项彼此不同。脚本没有在这些池的定义处标明“力量/敏捷/智力”属性标签，因此报告仅按 `type` 和数组名描述，不把属性对应关系当作已证实事实。候选 rawcode 清单分别初始化在约 9875–9989 行；英雄索引到单位类型的 `DC0` 映射从约 8478 行开始。
4. **写入该玩家能量圈：** `XI2` 对每个候选执行 `AddUnitToStock(D30[GetPlayerId(p)], DC0[index], 1, 1)`，并调用 `LC2(p, heroId)`。`LC2` 遍历两队玩家，对所有 `otherPlayer != p` 调用 `SetPlayerTechMaxAllowed(otherPlayer, heroId, 0)`；候选仍加入各自圈的库存，但其他玩家的选择上限被禁用。
5. **选择候选：** 源码中的 `ModeSD_Chosen` 会把输入的 1/2/3 映射到三个候选索引，并为触发玩家创建对应英雄、扣除 250 金。该函数体在脚本中存在，但文本搜索未找到其注册/调用点，因此本报告不把其具体 UI 触发方式当作已验证链路。

## 本机 Hook 的候选捕获链

启动器 Hook 能观察到上述同步库存更新，并按圈归属恢复玩家槽位：

1. Hook 观测 JASS 全局变量标签 `D30`，把标准玩家对应的 handle 写入 `g_playerCircleHandle[index]`。其他玩家与本地玩家都记录在同一数组中；`g_localPlayerCircleHandle` 只是额外保存本地圈。
2. Native 返回处理检查 `HASH_ADD_UNIT_TO_STOCK`；`args[0]` 是目标能量圈单位 handle，`args[1]` 是候选 `unitId`。
3. Hook 遍历全部 `g_playerCircleHandle[0..MAX_SLOT-1]`。匹配后将 `unitId` 追加到 `g_sdRandomHeroUnitIds[playerIndex]`，上限为 3，并同步写入共享内存。
4. 同时发送带 `playerIndex`、候选序号和 `unitId` 的 `RandomHeroStateChangedPayload`；Launcher 接收这条本机 DLL→Launcher IPC。

相关实现位置：

- JASS：`D:\Qt\workspace\War3Script\war3map.j`，`LD2` 约 36459–36469 行，`LF2` 约 36470–36484 行，`XI2` 约 36485–36566 行，`LC2` 和 `ModeSD_Chosen` 约 36403–36457 行。
- JASS 属性池初始化：约 9875–9989 行；玩家资格检查 `T3I` 约 3118–3125 行；模式映射约 33352 行。
- `War3Launcher/hooker/war3hook.cpp`：Native 返回处理中的 `HASH_ADD_UNIT_TO_STOCK` 与按圈匹配（约 22981–23008 行）。
- `War3Launcher/hooker/war3hook.cpp`：`D30` 全局数组解析和玩家圈 handle 存储（约 43687 行）。
- `War3Launcher/shared/SharedMemory.h`：`MAX_SD_RANDOM_HEROES` 与 `sdRandomHeroUnitIds[MAX_SLOT][3]`（约 41、762–763 行）。
- `War3Launcher/shared/SharedMemory.h`：IPC 载荷 `RandomHeroStateChangedPayload`（约 203–215 行）。
- `War3Launcher/managers/NetworkManager.cpp`：接收并验证 SD 候选 IPC 消息（约 5807–5845 行）。

## 1.27 运行日志实测

以下是启动器一次本机运行记录；它验证了 Hook 对一个玩家槽位的捕获，但不能单独证明另一位真实玩家或另一客户端的状态。该日志样本与前文 v6.83d 地图/JASS 的密码学对应关系仍未确认。

1. [NativeFunc4.log](../../War3Launcher/build/Desktop_Qt_5_15_2_VSCode_MSVC_32bit_Release/logs/NativeFunc4.log) 在 `07:34:01.235` 记录 `GetRandomInt` 范围 `[1,35]`、`[1,37]`、`[1,40]`。随后 `07:34:01.349–01.352`，Hook 对玩家索引 `1`、能量圈 `0x00100FB5` 捕获三个 `AddUnitToStock` rawcode：`Naka`、`N01I`、`N0EG`。因此实测确认了该本机进程记录到一个玩家的三候选，不是所有玩家槽位的对照结果。
2. [ActionData1.log](../../War3Launcher/build/Desktop_Qt_5_15_2_VSCode_MSVC_32bit_Release/logs/ActionData1.log) 记录 `Type=0x60` 的 `-sd` 动作，以及首字节为 `0x6B`、解析文本含 `dr.x Data Modesd` 的同步数据。
3. `07:34:05.088` 有一个长度 15、类型 `0x10` 的动作，携带候选 `Naka`；[ActionData2.log](../../War3Launcher/build/Desktop_Qt_5_15_2_VSCode_MSVC_32bit_Release/logs/ActionData2.log) 将它解析为玩家 `wuxiancong`（PID 1）请求选择赏金猎人 `Naka`。`07:34:05.601` 随后出现长度 72、类型 `0x1B` 的动作，载荷含 `kdr.x` 且末尾 FourCC 为 `Naka`。这表明所选英雄 ID 出现在游戏动作数据中，但不能据此说三候选列表被广播。
4. [war3hook.cpp](../../War3Launcher/hooker/war3hook.cpp) 的解析代码尝试把 `0x1B/72` 且含 `kdr.x` 的动作识别为最终选人锁定；但这次 `ActionData2.log` 将该包记为“其他动作”，所以这个特定运行中的 Hook 并未确认其语义。检查过的 `ActionData1.log`、`ActionData2.log` 只出现所选的 `Naka`，未出现另外两个候选 `N01I`、`N0EG`，也未见三候选作为一组发送。

因此，当前证据没有显示一个“广播 SD 三候选列表”的专属 Action ID：本次记录中的 `0x10` 是对 `Naka` 的选人请求，`0x1B/72` 虽含 `Naka`，但其具体语义尚未由这次 Hook 运行确认；`0x6B` 记录的是模式/同步数据。该结论只限于所检查的这一轮日志，不排除其他版本、其他对局或未检查动作采用不同载荷。

## 为什么本地能看到其他玩家候选

证据链由脚本和 Hook 两部分组成：

1. `XI2` 不通过 `GetLocalPlayer()` 分支筛选玩家，而是处理两队全部正在游戏的人类玩家，并对每人调用同样的随机抽取和 `AddUnitToStock` 序列。
2. `GetRandomInt` 在 Warcraft III 同步触发器中产生确定性游戏状态；候选创建和库存变更在各参与客户端的同步模拟中执行。因此，A 本机也有 B 的英雄候选数据。
3. `LC2` 对非候选所属玩家限制单位科技上限，说明“候选在本机同步状态中存在”与“其他玩家 UI 可点击/选择该候选”是两件事。
4. 本机 Hook 按所有玩家圈 handle 归属候选，不依赖本地圈字段；因此可以把 B 的三个库存更新映射到 B 的 `playerIndex`。

## 结论边界

- **A 能否本地获取 B 的三名候选：从静态链路看能。** JASS 为 B 的 `D30[playerId]` 加入 3 个分别从三个候选池抽出的英雄；Hook 按所有圈匹配库存调用。但本机日志实际只确认玩家索引 1，尚未以 B 槽位或第二客户端的日志完成实测。
- **A 能否获取所有玩家能量圈的候选：静态链路覆盖所有符合条件的槽位。** `XI2` 遍历两队的 1–5 号槽位，只跳过非正在游戏的人类槽位；共享内存结构最多容纳 `MAX_SLOT × 3` 个候选。当前运行日志并未展示所有槽位。
- **是否把三候选列表作为网络动作发送：本次日志未见。** 观察到的选人动作带已选中的 `Naka`，没有三项候选列表；`0x1B/72` 的具体语义仍需另一轮有跨客户端日志的对局确认。同步随机数初态及调用顺序的网络来源仍待确认。
- **能否在其他玩家 UI 中选用这些候选：通常不能。** `LC2` 将该候选对除所属玩家以外的玩家设置 `SetPlayerTechMaxAllowed(..., 0)`。
- **实际池范围已可确认，抽取无重复规则有条件。** 每名玩家分别从三类池取一名；`LF2` 确保同组三个索引不同。`F2` 为 false 时还避免选到已标记的全局索引；`F2` 为 true 时只在本组三项内做去重。脚本源码没有显式证明三池分别对应哪种主属性。
- **地图源文件对应关系尚未密码学确认。** JASS 源文件与两个本机工程副本哈希一致，且大小与地图 MPQ 中脚本条目的未压缩大小相同；加密 MPQ 内容无法直接与明文文件逐字节比较。
- **Hook 实机捕获已部分验证。** `NativeFunc4.log` 确认了一个玩家槽位的三候选捕获；其他玩家槽位、跨客户端候选一致性和 UI 呈现仍未实测。

## 后续验证建议

1. 核对 `D:\Qt\workspace\War3Script\war3map.j` 的生成/提取记录，确认它确实来自上表 SHA-256 的 v6.83d 地图。
2. 在能确认地图版本的 6.83d 多人对局中检查 `XI2` 对每个正在游戏的人类槽位执行三次 `AddUnitToStock`，并确认 `D30` 标签在 Hook 开始捕获前已解析。
3. 比对两个客户端或至少两个玩家槽位的 Native/ActionData 日志，验证本地候选与最终选人动作的边界；不能仅凭单个槽位的 `Naka` 选人包推断三候选列表被广播。
4. 如需向启动器展示其他玩家候选，UI 应读取该玩家槽位对应数组；不能把本地 UI 的可选择状态误当作候选数据不可见。

## 1.27 Native dispatcher 的 REA/Ghidra 复核

为确认 `GetRandomInt` 所在的 Native 调用框架，使用 REA 6.4.0 和 Ghidra 12.1.4 对 Warcraft III 1.27.0.52240 的 `game.dll` 做了只读函数分析。目标样本 SHA-256 为 `E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A`，PE 架构为 x86。

REA 的 Windows provider 拒绝直接分析 `D:` 上的原件：虽然该卷为 NTFS，但系统将 Kingston U 盘识别为 removable，而 provider 要求固定本地 NTFS 目标。为验证 provider，将原件暂存到 `C:` 本地临时目录；临时副本 SHA-256 与原件相同，原件未修改。Ghidra 全文件自动分析超过默认 330 秒期限；将本次分析期限设为 900 秒后，REA 成功返回函数证据。

Ghidra 将入口 `0x6F7EF590` 识别为 391 字节函数 `FUN_6f7ef590`，函数体范围为 `0x6F7EF590–0x6F7EF716`。其反编译结果从 Native 节点读取函数指针，再进行间接调用；指令清单给出：

```text
0x6F7EF6E0: CALL dword ptr [EBP - 0x80]
```

该地址对应 ImageBase `0x6F000000` 下的 RVA `0x7EF6E0`，与启动器版本表记录的 Native 间接调用点相符。Ghidra 的伪代码将被调用目标表示为从节点偏移 `+0x1C` 读取的函数指针，随后执行 `(*pcVar4)()`。这复核了该位置是通用 Native 函数指针调用点；它本身不标识 `GetRandomInt`，也不是随机数算法或对局网络同步实现。REA/Ghidra 本次证据未改变前文关于随机种子初始化和网络同步仍待验证的边界。

## 1.27 `GetRandomInt` 与 RNG 状态推进

使用 REA 6.4.0 CLI / Ghidra 12.1.4 对相同 SHA-256 的 `game.dll` 继续分析。以下是静态反编译和指令观察，地址按 ImageBase `0x6F000000` 换算 RVA：

| 作用 | VA | RVA | Ghidra 函数范围 |
| --- | --- | --- | --- |
| `GetRandomInt` 实现 | `0x6F1E43E0` | `+0x1E43E0` | `0x6F1E43E0–0x6F1E4416` |
| RNG 状态推进 | `0x6F199400` | `+0x199400` | `0x6F199400–0x6F1994B1` |
| `SetRandomSeed` 实现 | `0x6F1F64B0` | `+0x1F64B0` | `0x6F1F64B0–0x6F1F64D3` |
| RNG 状态初始化 helper | `0x6F1AE7E0` | `+0x1AE7E0` | `0x6F1AE7E0–0x6F1AE856` |
| Seed 后处理函数（语义待确认） | `0x6F675FE0` | `+0x675FE0` | `0x6F675FE0–0x6F6760C2` |

`GetRandomInt(param1, param2)` 在参数相等时直接返回 `param1`，不推进 RNG。否则它计算两参数的绝对差 `d`，调用状态推进函数取得 32 位值 `r`，并返回 `param1 + high32(r × (d + 1))`。SD 传入 `[1,count]`，所以这里 `param1` 是区间下界；函数本身不会交换逆序参数。映射使用 32×32 位乘积的高 32 位而非 `% count`，并且函数体没有拒绝采样循环。因此即便假定 `r` 完全均匀，35、37、40 这样的非 2 次幂区间长度仍可能有微小的映射偏差。正常情况下每次非退化调用推进一次状态。

状态推进函数从 `DAT_6FBC5FB0` 指向的上下文读取两项 32 位状态：`state[0]` 是累加状态，`state[1]` 打包了四个表索引。若将 `state[1]` 的四个字节从低到高记作 `b0..b3`，函数从 `0x6F964E48`（RVA `+0x964E48`）附近的表取值并计算 `ROL32(T[b1-24],3) XOR ROL32(T[b2-12],2) XOR T[b0-28] XOR ROL32(T[b3-4],1)`；其中负索引按指令中的条件分支加回 `0xD4/0xC8/0xD8/0xB8`。异或结果加到 `state[0]` 后写回；四个更新后的索引也重新打包写回 `state[1]`。这是一个带表查找、移位异或和加法的确定性状态机，不是本次看到的操作系统随机数调用。

`SetRandomSeed` 先用传入的 32 位值调用 `0x6F1AE7E0`：helper 把 seed 写入 `state[0]`，并按下式构造 `state[1]`：

```text
(seed % 59) * 0x400
| (seed % 61) * 4
| (seed % 53) * 0x40000
| ((seed / 47) * 17 + seed) * 0x4000000
```

之后 `SetRandomSeed` 立即推进一次 RNG，再把结果放入 `ECX` 尾跳到 `0x6F675FE0`。因此这个函数不只是简单存下 seed；但 `0x6F675FE0` 的后续用途以及对局启动时是谁、何时、以什么同步数据初始化 `DAT_6FBC5FB0`，本次尚未确认。代码中的 seed 设置 Native 也不能单独证明它就是开局随机种子的网络来源。

进一步分析 `0x6F675FE0`（REA Evidence `ev_f78846817333801117351f5231375f229fb4854dac7b037480cae7474e1d7805`）发现，它把传入的 `ECX` 值用于初始化一个局部 RNG 状态，之后循环 `0x2D` 次。每轮执行与状态推进函数相同的表查找、旋转异或和加法，再调用 `0x6F1AE7E0`，以新值初始化下一个 8 字节状态槽；槽地址按 `+8` 递增。循环次数与步长是指令直接观察，`0x6F04EFB0` 返回对象中的缓冲区由该函数填充则是基于调用序列和指针使用方式的解释。该函数另有调用者 `0x6F632270`，其用途还未追踪。此处揭示了 `SetRandomSeed` 后面的 45 轮确定性状态生成，但未证明这些槽就是 SD 候选实际消费的状态，也未找到向网络发送它们的代码。

对 SD 而言，JASS `XI2 → LF2 → LD2` 逐玩家抽取三类池；`LD2` 的候选池大小为 35、37、40。池内重复或被全局标记时会重抽，所以一次 SD 初始化的随机调用次数可能多于每玩家三次。若所有客户端以相同 RNG 状态执行相同同步触发器和相同分支，就会得到相同候选；这解释了为何不需要额外发送整组三候选，但“开局状态如何在客户端间建立一致”仍需要追踪同步协议或做双客户端实测才能证实。
