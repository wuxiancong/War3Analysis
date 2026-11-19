# DotA AI 树木命令（-tree）实测

> 模型：Claude Opus 5.5｜目的：验证 Gemini 新增的 `-tree` 系列命令（列树 / 吃树 / 砍树）｜命名：`dota-ai-tree-commands-test`｜时间：2026-11-18 23:45 ~ 2026-11-19 00:00｜环境：新虚拟机 DESKTOP-TN24EC2，游戏 1.27.0.52240，冰女，近卫中路

## 命令（RemoteControl :6120 / 游戏内 `-tree`）

| 命令 | 作用 | 实现 |
| :--- | :--- | :--- |
| `tree list [半径]` / `trees` | 列英雄周围存活树（`all` 全部可破坏物，`dead` 含已倒下） | `aiDumpTrees` → game.dll `EnumWidgetsInRect`（1.27 RVA 0x02F3F0）+ `CWidgetPos::GetWorldPos`（0x03B720） |
| `tree eat [x y [r] \| 0x<obj1> \| r]` / `eattree` / `tango` | 用吃树（I05C / I0Q6 / I0Q9）吃最近 / 指定树 | `aiUseItemOnDestructable`：0x12 + useslot(0xD0028+栏位) + 树坐标 + 树对象 ID（CDestructable +0x0C / +0x10） |
| `tree cut ... [fallback]` / `cuttree` / `quell` / `chop` | 用压制之刃砍树 | 同上 |

## 结果

| 测试 | 结果 | 证据 |
| :--- | :--- | :--- |
| 列树（半径 2000） | ✅ 能列出 | 中路门口 (-4409, -4702)：28 棵存活 `ATtr`，最近 844，每棵带坐标和对象 ID |
| 列树（小半径） | ❌ **结果不对** | 英雄在 (-4988, -4247)，树 0x3BC2 距离 110、0x4B37 距离 247：半径 600 → **0 棵**，1000 → 2，1500 → 6，2000(all) → 16。半径小时漏掉近处的树，数量随半径不单调 |
| 背包识别 | ✅ | 远处买东西失败时正确报「背包中没有吃树」；回泉水买到后识别到吃树 x4（栏位 1）、压制之刃（栏位 2） |
| 吃树 | ❌ **游戏不执行** | 4 次 `tree eat`（含站在树旁 110 处、按对象 ID 指定 0x3BC2）：日志都显示已下令，但英雄不动、树仍存活、吃树仍是 x4 |
| 砍树 | ❌ **游戏不执行** | `tree cut` 选中 0x3BC2（距 110），下令后树仍存活 |

## 修复（2026-11-19 01:00，已验证）

**根因**：真人用吃树 / 压制之刃点树（抓 `Ws2_32hook_Send_F726.log`，工具 `War3Analysis\artifacts\creep-block\f726_item_orders.py`），游戏发出的 0x12 是：

```
12 | 44 00 | 28 00 0D 00 | 3E 71 00 00  D1 85 00 00 | <x> <y> | D0 21 00 00  D0 21 00 00
   flags    useslot1      物品对象 ID1 / ID2          树坐标    树对象 ID1 / ID2
```

AI 发的是 `flags=00 00`、物品 ID 位 `FF FF FF FF FF FF FF FF`。录像（`w3g_item_orders.py` 解析 LastReplay.w3g）里 AI 的指令都在，但游戏不执行。**树的对象 ID（两个相同）是对的**，缺的是「用哪件物品」。

**改动**（`war3hook_ai_tactics.inl`）：

- `aiItemObjectIds(slot)`：`UnitItemInSlot` 取栏位物品句柄 → 句柄环（`aiFindAgentInRing`）找到物品代理 → 读 +0x0C / +0x10。
- `aiSendItemOrder(kind, order, item1, item2, x, y, obj1, obj2)`：flags 0x44 + 物品对象 ID。
- 吃树 / 砍树（`aiUseItemOnDestructable`）和其他所有用物品的地方（`aiUseItemNow`：无目标 0x10、点地 0x11、单位 0x12）都改用它。日志多打印「物品 0x…:0x…」。
- 只有「对树用物品」用真人抓包确认过；无目标 / 点地 / 对单位用物品同样改了，但还没实测。

**验证**（01:07 新开局，冰女，近卫基地树林；按时间戳区分真人 / AI 指令）：

| 时间 | 指令 | 谁 | 结果 |
| :--- | :--- | :--- | :--- |
| 01:08:58 / 01:09:02 | 吃树 → 0x2E30 / 0x494D | 真人 | 吃树 x4 → x2 |
| 01:09:38 | `tree eat 1500` → 0x21D0（物品 0x679C:0x95B7） | AI | ✅ 树消失，x2 → x1 |
| 01:09:47 | `tree eat 1500` → 0x45AA | AI | ✅ 吃树用完（物品栏清空） |
| 01:13:17 | `tree cut 1500` → 0x482E（压制之刃 0x73FA:0x107EF，距 472 自动靠近） | AI | ✅ 树消失 |

## 修复 2：小半径扫描漏树（2026-11-19 01:28，已验证）

`aiScanTreesAround` 原来传给 `EnumWidgetsInRect` 的矩形是 (cx±r, cy±r)，小半径会漏掉近处的树（r=600 时 110 处的树都找不到）。game.dll 的矩形约定和 {minX,minY,maxX,maxY} 不一致（或按大格子取）。改为**枚举整张地图**（±16384），半径交给回调里的精确距离判断；只在下树木命令时扫一次，开销很小。

验证（01:38，英雄 (-6155, -7114)，基地树林）：

| 半径 | 修复前（相近位置） | 修复后 | 最近的树 |
| ---: | ---: | ---: | :--- |
| 300 | 0 | 3 | 0x2E30（118） |
| 600 | 0 | 9 | 0x2E30（118） |
| 1000 | 2 | 39 | 0x2E30（118） |
| 1500 | 26 | 74 | 0x2E30（118） |

数量随半径单调增加，最近的树每次都在；1500 内实际有 74 棵，旧扫描漏了约 2/3。

不带半径的完整流程（01:39）：

| 指令 | 结果 |
| :--- | :--- |
| `tree eat` | 选最近 0x2E30（124，自动靠近，物品 0x6207:0x9ABB）→ ✅ 树消失，吃树 x4 → x3 |
| `tree cut` | 选 0x494D（251，压制之刃 0x5ECC:0x9A37）→ ✅ 树消失 |
| `tree list 600` | 9 → 7（正好少了这两棵） |

## 树木标记 -mark（2026-11-19，已验证）

用于拉双野等要砍掉特定位置树木的场合。玩家先自己用吃树 / 压制之刃吃（砍）一棵树，再在聊天输入 `-mark`（或 `/mark`）。

| 命令 | 作用 |
| :--- | :--- |
| `-mark` | 标记刚才吃 / 砍的那棵树（2 分钟内；记对象 ID + 树的实际坐标） |
| `-mark list` | 列出标记和当前是否存活 |
| `-mark cut [N]` | 依次砍 N 棵存活的标记树（离英雄最近优先；不写 N = 全部）；压制之刃，没有或冷却时用吃树 |
| `-mark clear <序号>`（或 `-mark del <序号>`） | 删除指定标记 |
| `-mark clear` | 删除全部标记 |
| `-mark hide` | 清除屏幕上的提示（标记保留） |

- 来源：`W3GS_OUTGOING_ACTION` 解析时（`war3hook_proto.cpp` → `aiNoteOutgoingActions`）记住最近一次「对树使用物品」的目标（真人和 AI 的都算）。
- 保存：`C:\War3Run\War3Launcher\tree_marks.txt`（`obj1 obj2 x y`）。预放树的对象 ID 每局相同，标记下局照样能用。
- 砍：按对象 ID 走现有砍树逻辑；砍倒确认后再砍下一棵；没倒就重下一次（射程内等 3s，远处按走路时间），再不倒跳过。

验证：02:35 玩家吃掉 0x2B5B 后 `-mark` → 标记 #1；新开局 02:48 `-mark list` 显示存活，`-mark cut` → 压制之刃砍倒（第一次下令没生效，重下后 1s 内倒）。02:53 版改为记树的实际坐标（指令里的 X/Y 是点击位置，偏 ~110）、近处重试等待 8s → 3s（未再实测）。

### -mark 第二版（2026-11-19 05:12）：阵营 + 屏幕提示 + 打野技巧

**结果显示在游戏屏幕上**：所有 `-mark` / `treepull` 的结果除了写 `AiUnit.log`，还通过 hook 自带的自定义 UI（`g_customUiTasks` → `renderCustomNotifications`，与 Launcher 的 `MSG_TYPE_SHOW_CUSTOM_UI_MSG` 同一渲染队列）显示在屏幕左上（约 (160,160) 起）：黄色 = 信息，绿色 = 成功，红色 = 失败 / 用法错误。**提示不会自动消失**（duration = 0），直到输入 `-mark hide`；最多同时 16 条，超出时丢最旧的并重新排版。实现：`aiScreenMsg` / `aiMarkSay` / `aiClearScreenMsgs`（`war3hook_ai_tactics.inl`）。

⚠ 05:30 版：`-mark clear <序号>` 删除指定标记，`-mark clear` 删除全部标记，`-mark hide` 清除屏幕提示（标记保留）。

**完整命令**（聊天输入，`-` 和 `/` 都行）：

| 命令 | 作用 |
| :--- | :--- |
| `-mark` | 标记刚吃 / 砍的树（2 分钟内）。阵营 = 你当前所在阵营 |
| `-mark sentinel` / `-mark scourge` | 标记并**指定阵营**（在天灾时标近卫的树就用这个）；对已标记的树再输入会改它的阵营 |
| `-mark list` | 列出所有标记：序号、阵营、存活 / 已倒 |
| `-mark cut [N]` | 砍**本方阵营**存活的标记树（N 棵，不写 = 全部），离英雄最近优先 |
| `-mark team <序号> sentinel\|scourge` | 修改已有标记的阵营 |
| `-mark clear <序号>`（或 `-mark del <序号>`） | 删除指定标记 |
| `-mark clear` | 删除全部标记 |
| `-mark hide` | 清除屏幕上的提示（标记保留） |
| `-mark help` | 屏幕上显示用法（输错子命令也会显示） |

**打野技巧 `treepull`（砍树拉双野，分类：打野）**：`tactic run treepull [N]` = `-mark cut [N]`；`tactic on treepull` = 有压制之刃或吃树、且本方有存活标记树时自动砍一轮然后关闭。RemoteControl 和游戏内 `-tactic` 都能用。

**换阵营**（RemoteControl，Launcher 04:46 版）：`start hold`（建房后停在房间）→ `swap <a> <b>`（房间里 `/swap a b`）→ `startgame`；脚本 `Start-AiGame.ps1 -Swap "1 7"` 一次完成。实测 `swap 1 7` 后英雄阵营 = 2（天灾）。

**砍树重试逻辑**（04:01~04:41 三轮修正）：英雄还在走近就一直等；远处 3s 没进展才重下；进射程（≤400）后 3s 没倒重下；每棵最多 3 次；树倒时把压制之刃冷却从这一刻重算（下令时刻记的冷却早过了，砍完立刻下一棵会被游戏因冷却忽略）。

| 测试 | 结果 |
| :--- | :--- |
| 04:01 第一版重试 | 0/4（按当前距离算等待，走到一半就判失败） |
| 04:10 | 2/4（重下后计时没重置；冷却按下令时刻算） |
| 04:38 | 3/4（冷却后第一次下令常不生效，2 次不够） |
| **05:14（3 次 + 屏幕提示版）** | **4/4，0 跳过**（含之前失败的 0x492） |

当前标记（`tree_marks.txt`）：近卫 4 个（#1~#4），#5~#11 共 7 个是在天灾时标的，全部记成了天灾；其中用户说有近卫的树，需用 `-mark team <序号> sentinel` 改正。（05:5x 查看时 `C:\War3Run\War3Launcher\tree_marks.txt` 已只剩表头，标记已被 `-mark clear` 清空。）

### -mark 第三版（2026-11-19 05:55，已编译安装，未进游戏测）：mark tree / mark position + 阵营按河道自动判断

- 模型：Claude Opus 5.5；目的：拆分标记命令、增加拉野站位标记；hook.dll 05:52:16 安装到 `C:\War3Run\War3Launcher\hook.dll`。
- 裸 `-mark` 不再标树，改为显示帮助；标树改为 `-mark tree`。
- **阵营默认按位置自动判断**，以河道为界：`x + y < 0` = 近卫（左下半场），否则天灾（`aiTreeMarkTeam` / `aiPosMarkTeam`）。DotA 河道大致沿 `x + y ≈ 0` 的对角线，紧贴河道的点可能判错，这时用 `-mark team` 手动改。文件里 `team = 0` 表示自动，1 / 2 表示手动指定。不再用「标记者当前阵营」。
- **英雄站立位置**：`aiQueryPosition(aiLocalHeroHandle())` → JASS `GetUnitX` / `GetUnitY`，和日志里「英雄 位置(x,y)」同一来源；在 `aiTick` 游戏线程执行。
- 位置标记文件：`C:\War3Run\War3Launcher\position_marks.txt`，每行 `x y radius team`。目前只保存 / 列出 / 删除，AI 还不会自动走过去拉野。

| 命令 | 作用 |
| :--- | :--- |
| `-mark` / `-mark help` | 屏幕上显示用法 |
| `-mark tree` | 标记刚吃 / 砍的树（2 分钟内），阵营按树的位置自动判断 |
| `-mark position [半径]`（`pos`） | 标记英雄当前站立位置（拉野点）；半径默认 0 = 精确位置 |
| `-mark list` | 列出树标记 `Tn`（t = tree）和位置标记 `Pn`（p = position） |
| `-mark cut [N]` | 砍本方阵营存活的标记树 |
| `-mark team t<n>\|p<n> sentinel\|scourge\|auto` | 手动改阵营 / `auto` 恢复按位置判断 |
| `-mark clear t<n>` / `-mark clear p<n>` | 删除指定树标记 / 位置标记（`t` 可省略：只写数字 = 树） |
| `-mark clear` | 删除全部树标记和位置标记 |
| `-mark hide` | 清除屏幕提示（标记保留） |

`-mark tree sentinel|scourge`、`-mark position [半径] sentinel|scourge` 仍可强制指定阵营（不写时自动判断，帮助里不再列出）。

05:55 版：树标记序号改为 `T<n>`（t = tree），位置 `P<n>`（p = position）；`clear` / `team` 里 `t` 可省略。

### 兵线标记 -mark lane（2026-11-19 06:03，已编译安装，未进游戏测）

- 模型：Claude Opus 5.5；目的：标记本方兵线经过的点，判断现在能不能拉野（拉野 = 把野怪引到本方小兵路上，兵线在才拉得到）。
- `-mark lane [半径]`：记下英雄当前站的位置，显示为 `L<n>`，存 `C:\War3Run\War3Launcher\lane_marks.txt`（格式同 position：`x y radius team`）。半径 0 时检查范围按 500。阵营同样按河道自动判断。
- `-mark check`：对本方每个兵线标记，统计范围内本方 / 敌方兵线小兵数量和最近的本方小兵距离。有本方小兵 → `✅ 可以拉野`；没有 → `⏳ 现在拉不到兵线（最近的离 N）`。
- 小兵阵营按单位类型：近卫 `esen/edry/ebal`，天灾 `ugho/unec/umtw`（`aiLaneCreepTeam`）。单位来自 `aiOnUnitCreated` 跟踪的全图单位（`aiCollectNearby`，以标记点为中心）。
- `-mark list` 增加兵线段；`-mark clear l<n>`、`-mark team l<n> ...`；`-mark clear` 同时清兵线标记。
- **06:21 修正**（模型 Claude Opus 5.5）：
  - 06:13 实测 `-mark lane` 记的是英雄位置（与 P1 同为 (3238, -5675)）。用户要的是**最前兵的位置**：拉野看「最前兵走到哪」决定何时 A 野怪。改为：找离英雄最近的本方兵线小兵 → 它 700 内的同一波 → 取离本方泉水（近卫 (-7000,-7000) / 天灾 (7000,7000)）最远的那只，记它的坐标；屏幕显示最前兵坐标、这波兵数、离英雄距离。场上没有本方小兵时报错。
  - 位置 / 兵线文件落到了游戏目录 `C:\War3Run\iCCup Warcraft III\`：脚本改代码时把 `find_last_of(L"\\/")` 写成了 `L"\/"`（只认 `/`），取不到目录。已改回，并把两个文件移到 `C:\War3Run\War3Launcher\`。旧 L1 仍是英雄位置，需要 `-mark clear l1` 后重标。
- 06:53 实测：`L2` = 最前兵 (1262, -6800)，这波 5 个兵，离英雄 2337（英雄在拉野点 (3471, -6037) 附近，P2 = (3128, -5672) 半径 50）。旧 `L1` (3238, -5675) 仍是英雄位置，未删除。
- 实现：`aiCheckLaneMark` / `AiLaneCheck`（`war3hook_ai_tactics.inl`），供以后的自动拉野战术用（例如出兵后兵线到达 L 点前几秒去 P 点拉野）。目前只是手动查询，AI 不会自动去拉。

### 拉野进兵线 lanepull（2026-11-19 06:58，hook 已编译安装，未进游戏测）

- 模型：Claude Opus 5.5；目的：按用户的拉野方法让 AI 拉野——「根据兵线位置决定是否开始拉野，A 一下野怪往兵线跑」。以后在此基础上教囤野。
- 命令：游戏内 `-mark pull [p<n>] [l<n>]`；RemoteControl / `-tactic`：`tactic run lanepull [P序号] [L序号]`、`tactic on lanepull`（立即拉一次）。不写序号时 P = 离英雄最近的本方位置标记，L = **最后标的**本方兵线标记。
- 流程（`AiLanePullState` / `aiStartLanePull` / `aiTickLanePull`，`war3hook_ai_tactics.inl`）：
  1. 选野点：P 附近 1200 内最近的已识别野点（`aiNearestCamp`，野怪 0:30 首次刷新后自动识别）。
  2. 走到 P（容差 = P 半径，0 按 30；被挤开每 0.8s 走回）。60s 走不到就停。
  3. 在 P 等：本方兵线小兵离 L ≤ 触发距离（L 半径，0 按 150）时出手。必须先看到 L 附近空过（> 触发距离 + 200）才开始等，防止刚到就被上一波已路过的兵触发。等 45s 没来就停。
  4. 出手：攻击该野点离英雄最近的野怪（`aiAttackUnit`），等目标掉血（仇恨上身），最多 3s。
  5. 往 L 跑（每 1s 重下一次），到 L 250 内或 7s 后结束；统计英雄 900 内该野点的野怪数和本方小兵数：都 > 0 → `✅ 拉野完成`，否则 `❌`（野怪没跟过来 / 兵线不在附近）。
  - 全程 `g_aiTacticBusyUntil` 接管英雄；`tactic stop` / `tactic off lanepull` 中止；所有步骤同时显示在屏幕上。
- `AiTactics.h`：`AI_TACTIC_LANE_PULL` 追加在枚举末尾（旧技巧 ID 不变，旧 Launcher 仍可用旧技巧）。RemoteControl 的 `tactic run lanepull` 要重编 Launcher 才认得；游戏内 `-mark pull` 只需要新 hook。

#### 07:38 实测 + 07:44 改为拉野路线

- 07:38 第一次：P2 (3128, -5672) → 野点 #0 (2928, -5072) → 时机 L2 (1262, -6800)。最前兵到 L2（离 147）时 A `nkol`（距离 622），2s 后打中；然后往 L2 跑——**方向反了**：L2 是出手时最前兵的位置，兵还在往前（东）走，英雄往西跑离兵线越来越远，7s 后「英雄附近野怪 3 只、本方小兵 0 个」。
- 用户标了终点 P3 (3897, -6775) 半径 50：近卫下路拉野点（兵线前方）。以后还会有天灾的拉野点。
- 改为**拉野路线** R：起点 P（站这里 A 野）+ 终点 P（拉到这里）+ 时机 L（最前兵到这里就出手），坐标直接复制存到 `C:\War3Run\War3Launcher\pull_routes.txt`（每行 `fromX fromY fromR toX toY toR laneX laneY laneR team`），以后删改 P / L 不影响已存路线；阵营 = 起点所在半场。
- 已按用户说明预存 **R1（近卫下路）= 起点 P2 (3128, -5672) → 终点 P3 (3897, -6775)，时机 L2 (1262, -6800)**。
- 出手后跑到终点（容差 = 终点半径，最少 80；最多 10s），到了再最多等 4s：终点 900 内既有该野点的野怪又有本方小兵 → `✅ 拉野成功`（显示出手到碰上的用时），否则 `❌`（野怪没跟过来 / 兵线没到终点）。

| 命令 | 作用 |
| :--- | :--- |
| `-mark route p<起点> p<终点> [l<n>]` | 保存拉野路线 `R<n>`（L 不写 = 本方最后标的兵线标记） |
| `-mark pull [r<n>]` | AI 按路线拉野（不写 = 本方阵营里起点离英雄最近的路线） |
| `-mark pull p<起点> p<终点> [l<n>]` | 临时路线拉野（不保存） |
| `-mark clear r<n>` | 删除路线；`-mark clear` 也会清路线 |
| `tactic run lanepull [R序号]` | 同 `-mark pull`（RemoteControl 需新 Launcher） |

#### 07:50 近卫实测 + 天灾路线 + -pull（08:16 hook 已安装，未进游戏测）

- **R1 近卫下路实测成功 2/2**：07:50 出手 A `nfsh`，1.8s 打中，6.1s 跑到终点 → 终点附近野怪 1 只、本方小兵 3 个（出手到碰上 8.5s）；07:51 A `npfl` → 野怪 3 只、本方小兵 1 个（8.2s）。
- **R2 天灾**：用户在天灾（`swap 1 7`）标 P4 (-440, 4126) 半径 50（起点）、P5 (-583, 5967) 半径 50（终点）、L3 = 最前兵 (2360, 5460)（这波 5 个兵，天灾上路兵往西走）。游戏里没有执行 `-mark route`，08:16 按用户说明直接写入 `pull_routes.txt` 第 2 行。
- **`-pull` / `/pull [r<n>]`**（模型 Claude Opus 5.5）：= `-mark pull`。不写序号时**按英雄位置选路线**：河道为界判英雄在哪个半场，取该半场里起点离英雄最近的路线（这边没有路线就取全图最近的），屏幕显示选了哪条。`-mark pull` 和 `tactic run lanepull` 的自动选择也改成这样（之前按玩家阵营选）。
- 时机判断用路线所在半场的兵：在近卫下路看近卫小兵，在天灾那边看天灾小兵。

## 修复 3：买东西选错商店实例（2026-11-19 02:31，已验证）

`executePendingItemBuy` 按句柄锚点选商店实例时会选到**没有网络对象 ID（0xFFFFFFFF）的占位商店**（武器商人 4 个实例里 2 个是这种），选中动作入队失败，站在商店旁也买不到压制之刃。改为候选和锚点都跳过 0xFFFFFFFF 实例。修后同一位置压制之刃一次买到。

另加**购买结果核对**（`aiNoteBuyRequested` / `aiTickBuyCheck`）：受理购买时拍背包快照，1.5s 后比对，`AiUnit.log` 写 `🛒 [BuyCheck] ✅ 购买成功 → 栏位 N` 或 `❌ 购买未生效（英雄坐标、背包格数、常见原因）`。RemoteControl 仍立即回「OK buy sent」（改回执要重编 Launcher）。

## 仍未修

1. ~~`buy` 不报失败~~：已加购买结果核对（见修复 3），RemoteControl 回执本身未改。
2. 无目标 / 点地 / 对单位用物品（推推棒、跳刀、守卫等）改了格式但未实测。
3. 读图崩溃 game.dll+0x2BD982（本机 4 次开局崩 2 次），与树木命令无关，另行跟踪。

## 分析（修复前，保留备查）

1. **吃树 / 砍树指令被游戏静默丢弃**。同样的 0x12 + useslot 布局对单位目标能用，对树不行。最可疑的是树的对象 ID：取的是 CDestructable +0x0C / +0x10，所有树两个 ID 都相同（如 `0x3BC2:0x3BC2`）。地图预放对象在录像里通常也是两个 ID 相同，所以不能直接断定是错的，需要和真人操作对比。
2. **小半径扫描漏树**：传给 `EnumWidgetsInRect` 的矩形可能有问题（坐标顺序 / 范围约定），或枚举按四叉树格子取、小矩形碰不到树所在格子。

## 下一步

1. 真人手动用吃树吃一棵树，抓游戏发出的 0x12 动作（`Ws2_32hook_Send` 日志 / 录像），和 AI 发出的字节逐字段对比（对象 ID、坐标、标志位）。
2. 检查 `aiScanTreesAround` 的矩形参数，用同一位置不同半径验证单调性。
3. 买东西要在商店范围内（英雄在中路时 `buy` 返回 OK 但实际没买到）——`buy` 应报告失败。
