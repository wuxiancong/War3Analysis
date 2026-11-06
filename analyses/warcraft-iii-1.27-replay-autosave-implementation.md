# Warcraft III 1.27：录像自动保存如何实现

## 结论摘要

- **局末自动保存（「游戏结束」）已经能做，且不必先逆向：** War3 每局结束都会覆盖写出 `Replay\LastReplay.w3g`；Launcher 在进程退出时复制并重命名即可。当前 `ReplayManager::handleGameExit()` 已实现该路径。
- **官方「Autosave Replay」≠ 按分钟间隔保存：** 1.22 起选项菜单的自动保存对应注册表 `Gameplay\autosaveReplay`，局末把录像落到 `Replay\Autosaved\` 一类命名路径；**不是** UI 里「每 N 分钟」那种局中快照。
- **局中按分钟保存需要逆向落盘点：** `game.dll` 存在 `TempReplay.w3g` 字符串，极可能是对局过程中的临时录像缓冲；要安全做「60/50/…/10 分钟」保存，应定位其 **Flush/Finalize/Copy** 函数，而不是盲拷可能未收尾的文件。
- **推荐落地顺序：** P0 完善局末复制（已完成大半）→ P0.5 可选同步官方 `autosaveReplay` → P1 用 Ghidra/REA 钉死 `TempReplay`/`Autosaved` 写文件链 → P2 Hook 定时触发原生保存或安全快照。

| 项目 | 记录 |
| --- | --- |
| 目标版本 | Warcraft III 1.27.0.52240 |
| 目标文件 | `game.dll` |
| 大小 | 13,187,048 字节 |
| SHA-256 | `E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A` |
| 样本来源 | `War3Launcher/versions/1.27.0.52240/game.dll` |
| 对照补丁说明 | 同目录 `Patch各版本修改列表中/英文版.txt`（1.22 引入 Autosave Replay） |
| 工具链 | Ghidra **12.1.4**（`D:\Ghidra_12.1.4`）；REA **6.8.0**（`D:\REA`，与 npm 最新一致） |
| Ghidra 项目 | `War3Analysis/ghidra/projects/War3_127.gpr` |
| Launcher 现状 | `Replay/autoSaveReplay` + `Replay/saveIntervalMinutes`（UI 已加；间隔逻辑未接） |
| 分析状态 | 静态字符串 + 注册表 + 现有代码路径已对齐；**写文件函数 VA 尚未在本轮 Ghidra 定位** |
| 置信度 | 局末 `LastReplay` 机制：**高**；官方 autosave 仅局末命名落盘：**高**；`TempReplay.w3g` 为局中缓冲：**中高（待 xref 验证）**；盲拷 TempReplay 可播：**低（未验证）** |

## 工具与样本是否最新

| 组件 | 本机 | 最新性 |
| --- | --- | --- |
| REA / `rea-agents` | `D:\REA` → **6.8.0**（`package-lock` / `node_modules`） | `npm view rea-agents version` = **6.8.0**，**是当前最新** |
| War3Analysis README | 仍写「REA 6.4.0」 | **文档过期**，应以 6.8.0 为准 |
| Ghidra | `D:\Ghidra_12.1.4` | 与分析仓约定一致；项目 `War3_127` 可用 |
| 版本树 | `War3Launcher/versions/1.27.0.52240` | 与现网经典 1.27 分析基线一致 |

> REA 分析目标须在**固定本地 NTFS**（通常拷到 `C:\War3Analysis\samples\...`），不要直接对可移动盘 `D:` 上的 `game.dll` 跑 provider。

## 方法与证据边界

1. 读 1.22/1.27 Patch 说明、Battle.net Replay FAQ、社区 LastReplay 工具行为。
2. 对 `game.dll` 做 ASCII 字符串扫描（本机 PowerShell），记录文件偏移。
3. 读 HKCU `Warcraft III\Gameplay\autosaveReplay`。
4. 对照 `War3Launcher`：`ReplayManager::{onGameStateChanged,handleGameExit,findLastReplayCandidate}`、`SettingsManager` 录像项。
5. **本轮未**打开 Ghidra 解引用 `TempReplay` xref，也未实机验证局中拷贝 TempReplay 能否 `-loadfile` 播放。

## War3 原生录像落盘模型（1.27）

```text
对局中
  └─ 引擎持续记录操作流
       └─ 可能落到 TempReplay.w3g（字符串已证实存在；写路径待证）

对局结束 / 结算屏
  ├─ 总是（或在可保存条件下）写出 Replay\LastReplay.w3g（下次对局覆盖）
  ├─ 若 Gameplay\autosaveReplay=1
  │    └─ 再按时间戳落到 Replay\Autosaved\... 或 %s\%s_%s.w3g 一类路径
  └─ 结算屏「Save Replay」→ SaveReplayPanel 手动命名保存
```

### 关键字符串（`game.dll` 文件偏移）

| 偏移 | 字符串 / 片段 | 含义（推断） |
| ---: | --- | --- |
| `0x984753` | `Replay\LastReplay.w3g` | 固定「上一场」路径 |
| `0x984D10` | `LastReplay` / `%s%s%s%s.w3g` | 命名模板旁路 |
| `0x985C0E` 一带 | `TempReplay.w3g` | **局中临时录像文件名（关键）** |
| `0x950A38` | `autosaveReplay` | 与注册表/选项键同名 |
| `0x978994` | `AutosaveReplayCheckBox` | 选项 UI |
| `0x985014` | `Autosaved` / `%04u_%02u_%02u_%02u%02u` / `%s\%s_%s.w3g` | 官方自动保存命名 |
| `0x96B224` | `DoNotSaveReplay` | JASS/地图侧禁止存录像 |
| `0x97B79C` | `SaveReplayPanel` | 手动保存面板 |

### 注册表（本机实测）

```text
HKCU\Software\Blizzard Entertainment\Warcraft III\Gameplay
  autosaveReplay = 0   # DWORD；1=开启官方局末自动保存到 Replay 目录
```

同组邻近键与 dll 字符串表一致：`customkeys`、`schedrace`、`multiboardon` 等。

### Patch 证据（1.22）

> 选项菜单增加回放自动保存；回放自动保存到 `replay` 文件夹。  
> （另有断线自动存档到 `save`，那是 **SaveGame**，不是 `.w3g`。）

## Launcher 现状（War3Launcher）

| 能力 | 状态 | 位置 |
| --- | --- | --- |
| 局末检测 LastReplay | ✅ | `ReplayManager::findLastReplayCandidate`（`LastReplay.w3g` / `Replay/` / `Replays/`） |
| 局末复制到用户录像目录 | ✅（受 `autoSaveReplay`） | `handleGameExit` ← `onGameStateChanged(false)` |
| 命名：时间/玩家/英雄 | ✅ | `SettingsManager::replayNameTemplate` |
| 结束后打开目录 | ✅ | `openReplayFolderAfterGame` |
| 频率 ComboBox UI | ✅ | `saveIntervalMinutes`：0/60/50/40/30/20/10 |
| 按分钟局中保存 | ❌ 未接 | 仅配置项 |
| 同步官方 `autosaveReplay` 注册表 | ❌ | 可选增强 |
| 录像模式禁自定义 UI | ✅（另项） | `war3hook` `replayMode` |

局末触发条件：**War3 进程从 Running → 退出**。若只是返回主菜单但进程不退，可能**不会**走 `handleGameExit`——若实机出现「退房不存」，要改挂场景态/`MSG_TYPE_GAME_CLOSED` 或结算屏信号。

## 实现方案（按推荐优先级）

### 方案 A — 局末复制 LastReplay（P0，已基本完成）

**做法：** 保持现有 `handleGameExit`；`saveIntervalMinutes==0` 时只走这条。

**优点：** 不依赖逆向；产出标准可播 `.w3g`。  
**缺点：** 崩溃/强杀可能没有完整 LastReplay；无法满足「每 N 分钟」。

**可选加固：**

1. 结算屏出现时提前复制（Hook 场景 / ScoreScreen），不单等进程退出。
2. Launcher 打开「自动保存」时同步写 `Gameplay\autosaveReplay=1`，双保险（官方目录 + 用户目录）。
3. 复制前检查文件大小/修改时间，避免拷到空文件。

### 方案 B — 复用官方 Autosave（P0.5，低成本）

**做法：** 设置页开关映射到 `autosaveReplay`；用户目录仍由 Launcher 再拷一份（命名规则用自家模板）。

**优点：** 零逆向，局末多一份 Blizzard 路径备份。  
**缺点：** 仍无局中间隔；命名格式固定为官方 `Autosaved` 风格。

### 方案 C — 监控并快照 TempReplay / 正在写入的 w3g（P1，需验证）

**做法：**

1. Ghidra 对 `TempReplay.w3g` 做 xref，确认创建/写入/关闭点。
2. 局中定时（N 分钟）：若文件存在且 size 增长，**共享读**拷贝到用户目录（带 `_part_HHMM` 后缀）。
3. 局末再存一份完整版，并可删除不完整片段或标记。

**风险：** 未 Finalize 的文件可能头不完整、无法播放或只播到拷贝时刻；拷贝时若引擎正写可能撕文件——需 `FILE_SHARE_READ` + 最好在引擎 flush 之后。

**验证门槛：** 实机对拷出的 `_part_*.w3g` 做 `-loadfile`，确认可播长度 ≈ 拷贝时刻。

### 方案 D — Hook 原生「保存录像」函数并定时调用（P1/P2，推荐终极形态）

**做法：**

1. 从 `Autosaved` / `ScoreScreenSaveReplay` / `SaveReplaySaveButton` / `TempReplay` 字符串 xref 找到「收尾并写出 .w3g」的函数。
2. `war3hook` 在 `GamePlaying` 且 `replaySaveIntervalMinutes>0` 时用多媒体定时器调用该函数（或模拟结算保存路径的无 UI 变体）。
3. 通过 IPC 把新文件路径回传 Launcher，或约定落在 `Replay\` 后由 Launcher 监视目录。

**优点：** 产出合法完整快照的概率最高。  
**缺点：** 需稳定 VA/特征码；录像模式已禁止自定义 UI，但**允许**后台保存逻辑；错误调用可能导致卡顿/崩溃。

### 方案 E — 旁路录制 W3GS 操作流自合成 w3g（P3，不推荐优先）

Hook 里已有大量 W3GS 包解析。从零拼出可播 `.w3g` 工作量大、版本敏感，仅当 C/D 失败时考虑。

## 与 UI「保存频率」的映射建议

| `saveIntervalMinutes` | 行为 |
| ---: | --- |
| `0`（游戏结束） | 方案 A（+ 可选 B） |
| `10..60` | 进入对局后启动间隔定时器 → 方案 C 或 D；局末仍执行 A |

配置已落在 `GameConfig.ini` → `[Replay] saveIntervalMinutes`；需再经 SharedData/IPC 传到 hook（若 D 在 DLL 侧跑表），或纯 Launcher 侧对 `TempReplay`/`Replay` 目录轮询（方案 C 可全在 Launcher，进程外）。

**进程外轮询（C）** 实现快、崩溃面小；**进程内 Hook（D）** 正确性更好。可先 C 做实验，确认 TempReplay 可播后再上 D。

## 建议的 Ghidra / REA 下一步（可复现）

样本请先拷到固定盘并校验哈希：

```powershell
New-Item -ItemType Directory -Force C:\War3Analysis\samples\1.27.0.52240 | Out-Null
Copy-Item 'D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll' `
  'C:\War3Analysis\samples\1.27.0.52240\game.dll' -Force
(Get-FileHash 'C:\War3Analysis\samples\1.27.0.52240\game.dll' -Algorithm SHA256).Hash
# 期望: E04D1716603C075EB0C8E1E21CF1093A664ADC5249EFAB396BFA08D7B09D0C3A
```

```powershell
$env:GHIDRA_INSTALL_DIR = 'D:\Ghidra_12.1.4'
$env:JAVA_HOME = 'D:\Ghidra_12.1.4\jdk'
$env:REA_GHIDRA_STARTUP_TIMEOUT_MS = '900000'
& 'D:\REA\rea.cmd' doctor --provider ghidra
# 打开既有工程 War3_127，搜索字符串:
#   TempReplay.w3g / autosaveReplay / Autosaved / Replay\LastReplay.w3g
# 对每个字符串 xref → 向上找 CreateFile / WriteFile / fclose / 自定义 FS 封装
```

交付物（下一轮分析应补进 `artifacts/replay-autosave/`）：

1. `TempReplay` 写函数 VA / RVA / 文件偏移  
2. 局末 Finalize → `LastReplay` 的调用栈  
3. `autosaveReplay==1` 时额外拷贝分支  
4. 是否存在可重入的「立即保存」入口（供间隔调用）

## 未验证事项

- [ ] `TempReplay.w3g` 实机路径（游戏目录根？`Replay\`？临时目录？）
- [ ] 局中拷贝的 TempReplay 能否完整播放、时长是否截断
- [ ] 断线/崩溃时 LastReplay / TempReplay 是否仍刷新
- [ ] `DoNotSaveReplay` 地图是否阻断官方 autosave 与 LastReplay
- [ ] 仅退回大厅、进程不退出时，Launcher 是否漏存

## 对 War3Launcher 的直接建议

1. **短期：** `saveIntervalMinutes==0` 继续走 `handleGameExit`；补结算屏/主菜单返回的保存触发（若实测漏存）。  
2. **短期：** 可选把 `autoSaveReplay` 同步到注册表 `autosaveReplay`。  
3. **中期：** 开一轮 Ghidra 专题钉 `TempReplay`；用方案 C 做可播性实验。  
4. **中期：** 实验通过后，再在 hook 接间隔定时 + IPC，真正兑现 ComboBox 的 N 分钟选项。
