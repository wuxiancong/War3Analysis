# 任务：实机测试并改进「斧王打野」，目标 10:00 前出跳刀（DotA 6.83d）

**给**：Antigravity Gemini　**布置时间**：2026-11-26　**工作目录**：`D:\Qt\workspace`（测试虚拟机上）
**布置人**：Claude Opus 5.5（用户要求：「安排一个任务给 Gemini，告诉它如何测试斧王打野，现在提高难度，10 分钟内出跳刀」）

## 0. 一句话

用 hook 的 AI 任务 `-task axe` 让斧王（近卫 1 号位，AP + 9 个电脑）自己打野，**10:00 前跳刀（`I04H`）进物品栏**。
你可以开游戏、连 RemoteControl 6120 实测，**只改 `War3Launcher/hooker/war3hook_ai_axe_jungle.inl`**，每轮用录制数据和用户示范对比，直到达标或者说清楚为什么达不到。

> 这次和以前的 Gemini 任务不一样：**允许开游戏、允许连 6120、允许改上面那一个源文件、允许编 hook 并复制 hook.dll**。
> Claude 这段时间不在这台机器上跑测试。其余红线见 §8。

## 1. 先读（不要重做）

| 文件 | 内容 |
|---|---|
| `War3Launcher/hooker/war3hook_ai_axe_jungle.inl` | 当前实现（第四版），文件头注释写了全部规则和每版改了什么 |
| `War3Analysis/analyses/dota-683d-axe-jungle-human-demo.md` + `-mindmap.md` | **用户亲自示范的分析**：5 级 5:28、10:50 内清野 17 次、只回过 1 次泉水 |
| `War3Analysis/artifacts/axe-jungle-demo/20261125-223917.csv`、`axe-jungle-demo-20261125.w3g` | 示范的原始录制和录像 |
| `War3Analysis/analyses/dota-neutral-camp-spawn-box.md`、`War3Launcher/hooker/war3hook_ai_camp_routes.inl` | 12 个野点的封野盒（`kAiStackCampRoutes` 的 min/max）和拉野路线 |
| `War3Analysis/tasks/gemini-axe-jungle-runes-illusions.md` | 上一个还没交付的任务（神符、幻象控制、静谧之鞋、开树）；做本任务时用得到就一起做 |
| 用户的长期规则（已写进 §2） | 囤野 xx:50~:53 出手（4 波以上也不提前），出手时不能被野怪打到；玩家一下指令 AI 立即停手，不拉回、不自动重开；AI 托管 /ai 默认关闭 |

## 2. 用户定的打法（必须遵守，改之前问用户）

1. 出门：**圆盾 + 补刀斧 + 小鸡**（必备），钱够再大药；**先合成静谧之鞋，再出跳刀**。
2. **没到 5 级只打小野**（等级低的野点），5 级后再打大野，否则容易死。
3. **E5（用户叫 E6，(3072, -3712)）+ B5 (2960, -5008)**：:50 可以同时拉两个点 = 四波野；拉不好就单拉一个。打的时候在两点之间移动，两边野怪都吃反击螺旋。
4. **不要封野**：:00 刷新时英雄 / 野怪不能在封野盒里。E5 盒 y -4800~-3328、B5 盒 y -6080~-4928，中间只有 128 宽的缝（y -4928~-4800）。
5. **卡视野打野**：P25 (-532, -4032)（F5 (-416, -3584) + W5 (-1056, -4592) 双野点），砍掉标记树 T1 / T2 后用；同样的开树技巧用于其他野点（T3~T6）。
6. **静谧之鞋**（`I0OG`，失效形态可能是 `I0OI`）打架前丢地上，打完捡起来（攻击 / 被攻击时不回血）。
7. 钱够买一两个**大药**撑到 5 级；**2 级点 1 技能（狂战士之吼）**，扛不住伤害时开吼减伤。
8. **每两分钟提前看符**；双倍 / 幻象提高效率；**幻象可以拉野**（两个幻象分别放两个野点，到时间一起拉）。
9. 玩家一下指令 AI 立即停手（`aiStopAllAutomation`），不拉回、不自动重开。

## 3. 现状（基线）

| | 用户示范 | AI 第四版（2026-11-25 23:24 实测） |
|---|---|---|
| 2 级 / 3 级 | 2:04 / 2:42 | **1:20 / 1:27** |
| 5 级 | **5:28** | 7:50 |
| 静谧之鞋 | **4:38**（应该是小鸡送的配件） | 9:10 |
| 清野（约 10:00） | 15 | 10 |
| 10:00 金币 | 1998（已出鞋） | ~1100（刚出鞋） |
| 跳刀 | 没出（10:50 时 2000 金） | 没出 |

**10:00 出跳刀要的钱**：出门 595 + 静谧之鞋三件 1000 + 跳刀 2150 ≈ **3745**（起始 625）。示范到 10:00 大约挣了 3600，**比示范还要快一点才够**。

## 4. 第四版已知问题（先修这些）

| # | 现象 | 建议改法 |
|---|---|---|
| 1 | 单拉时野怪没跟出来（打一下就跑，0.9s 不够出手落地），:00 野点没刷新 | 打完看目标掉血 / 野怪开始追再跑；拉野后检查野怪是否都出了盒 |
| 2 | 拉完野后「看不见野点就走过去」把英雄又带回盒里（:55 走回去，:58 / :59 才出来） | :45~:60 不执行「走向看不见的野点」 |
| 3 | 第一次进 P25 区时在拉野中途开始砍树，打断拉野 | `pullStep > 0` 或 :45~:60 不开始砍树 |
| 4 | 0.6s 内连喝两个大药 | 自己记上次喝药时间，12s 内不再喝 |
| 5 | 拉野 1s 后就报「清完野点 #10」 | 清野计数加条件：英雄 700 内、最近 10s 有野怪掉血 |
| 6 | 44% 血为了买东西回泉水（示范只在 24% 回过一次） | 买东西尽量用**小鸡送**（示范 4:38 鞋子就是这样）；回泉水只在血 < 15~25% 时，顺便买 |
| 7 | 5 级晚（7:50 vs 5:28）、鞋晚（9:10 vs 4:38） | 1~6 修好后再看；小鸡送装备是最大的差距 |
| 8 | 看符只「看」，幻象没控制 | 有幻象 / 双倍就吃；幻象拉野见 `gemini-axe-jungle-runes-illusions.md` |

## 5. 测试环境（测试虚拟机，4 核 8 GB）

- 源码 / 编译在 D:（慢速 U 盘），**运行统一在 `C:\War3Run`**；bnetd 用 `D:\War3Server`。
- 启动顺序：**bnetd :6112 → War3Bot :6116（调试模式）→ 等 ≥ 10 秒 → War3Launcher :6120（管理员）**。
  - bnetd + Bot：在**用户的终端**里跑 `powershell -NoProfile -ExecutionPolicy Bypass -File D:\Qt\workspace\Scripts\Start-LocalServers.ps1`（它会按顺序等端口、分离启动；后台 shell 起的进程会被带走）。
  - Launcher 要管理员权限：**请用户手动启动** `C:\War3Run\War3Launcher\War3Launcher.exe`。
  - 检查：三个端口都在监听（`Get-NetTCPConnection -LocalPort 6112,6116,6120 -State Listen`）。
- 日志：AI → `C:\War3Run\War3Launcher\logs\AiUnit.log`（任务的行以 `🪓` 开头，标签 `[任务]` / `[技巧]` / `[打野]`）；hook → `logs\War3Hook.log`；War3Bot → `C:\var\log\War3Bot\war3bot.log`。
- 崩溃 dump：`C:\War3Run\War3Launcher\crash_*.dmp`（读法：`War3Launcher/scripts/_parse_dmp.py` 或 Python `minidump` 包）。

## 6. 每一轮怎么测

1. **改** `war3hook_ai_axe_jungle.inl`（文件头注释里补一条「第 N 版：改了什么、为什么、数据」）。
2. **编**：先 touch `war3hook_ai.cpp`（只改 .inl 不会重编），再跑 `War3Launcher\scripts\build_hook.cmd`。`build exit=0` 且 `ai_build_check` 0 个问题才继续。**不要在测试进行时编译**（CPU 满了游戏变慢、测试作废）。
3. **部署**（war3 没在运行时）：把 `D:\Qt\workspace\War3Launcher\build\Desktop_Qt_5_15_2_VSCode_MSVC_32bit_Release\hook.dll` 复制到 `C:\War3Run\War3Launcher\hook.dll`，比对哈希。只复制 hook.dll（Launcher / Bot 没改就不用 `Sync-War3Run.ps1`）。
4. **开局**：`powershell -NoProfile -ExecutionPolicy Bypass -File D:\Qt\workspace\War3Launcher\scripts\axe_test_game.ps1 -Hero axe`
   （AP 房间、9 个电脑、斧王近卫 1 号位；最后 `start exit=0`）。
5. **开任务 + 录制**：RemoteControl 127.0.0.1:6120 发一行一条：
   `say -rec jungle` → `say -task axe` → `say -ai panel task`（发法见 `axe_test_game.ps1` 里的 `Send-Ai`）。
6. **看**：`AiUnit.log` 里 `🪓` 的行（拉野、清野、回泉水、买装备、静谧之鞋、开吼、看符、封野盒）。到 10:00 会有一行 `[任务] 15:00 …`（目前是 15:00 报一次，**改成 10:00 报**）。
7. **结束**：游戏钟 ~10:30 后发 `say -rec stop`，然后 `say -task off`。录制在 `C:\War3Run\War3Launcher\records\jungle\Opgh\<时间>.csv`。
8. **分析**：`python D:\Qt\workspace\War3Launcher\scripts\jungle_rec_analyze.py <录制.csv>`，和示范（`artifacts/axe-jungle-demo/20261125-223917.csv` 跑同一个脚本）逐项对比：升级时间、清野次数、:45~:58 位置、回泉水次数、物品栏时间线。
9. 结束上一局：**这是你自己开的测试局，可以直接结束 war3**；用户自己在玩的局不能动（不确定就问）。

**注意（踩过的坑）**：
- `war3hook_lobby.cpp` 的玩家动作钩子里**不要加东西**：2026-11-25 加了「录物品使用 / 丢物品」，连续两次读图卡在 47% 崩溃，撤掉就好了。
- `-ai off` 时任务不会动；玩家下任何指令任务立即停（这是规则，不是 bug）。
- Launcher 可能自己消失（23:19、20:53 是外部结束；19:18 是退出时崩溃，见 `analyses/war3launcher-exit-after-room-leave.md`）：端口 6120 不通就请用户重开，不要自己去杀 / 起 Launcher。
- 第一波野怪 0:30 刷新；游戏钟有时比墙钟晚开始，开局等 1~2 分钟没野怪是正常的。

## 7. 交付

| 交付物 | 位置 |
|---|---|
| 改好的实现（文件头写清每一版） | `War3Launcher/hooker/war3hook_ai_axe_jungle.inl` |
| 测试报告（结论在最前：10:00 有没有跳刀、每一轮的对比表、和示范的差距、还剩什么问题；文件开头写分析模型 / 目的 / 命名 / 时间 / 验证状态） | `War3Analysis/analyses/dota-683d-axe-jungle-10min-blink.md` |
| 思维导图 | `War3Analysis/analyses/dota-683d-axe-jungle-10min-blink-mindmap.md` |
| 每一轮的录制 CSV 和分析输出 | `War3Analysis/artifacts/axe-jungle-10min/` |

如果 10:00 怎么都到不了（经济算不过来），在报告里给出数据和建议（比如跳刀先于静谧之鞋、少回家、多吃双倍 / 幻象），**由用户决定**，不要自己改用户定的出装顺序。

## 8. 红线

1. **只改** `war3hook_ai_axe_jungle.inl`。别的源文件（hooker 其他文件、managers、shared、War3Bot）不改；确实非改不可的，写进报告由 Claude / 用户处理。
2. 不 commit / push。
3. 只连本机服务器和本地数据库 `D:\War3Server\var\users.db`；不持久改 `AutoStart=true`；输出里不要出现 ini 里的密码、token。
4. 不碰用户自己的对局；`killgame` 只用于自己开的测试局。
5. 编译和测试分开做（4 核虚拟机，CPU 满了测试作废）。
6. 结论要有数据（录制 / 日志行），推断标 ❓。
