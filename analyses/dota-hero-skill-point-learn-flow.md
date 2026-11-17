# DotA1 英雄添加技能点（O）整体流程与 AI 注入路径

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 理清 DotA 6.83d 中按 O 打开加点菜单、学习技能/属性附加的完整链路，为后续 AI 接口（主名 **`learn`**，兼容 `skill`；施法主名 **`cast`**）复用 `EnqueuePlayerAction` 做准备 |
| **命名方式** | `dota-hero-skill-point-learn-flow`（主题短横线英文）；配套导图同名 + `-mindmap` |
| **分析时间** | 2026-11-16 |
| **关联代码** | `War3Bot/src/client.cpp`、`matchstatsprovider.cpp`、`main.qml`；`War3Launcher/hooker/war3hook_process.cpp`（`-buy`/`-move` 同管道）；`War3Script`（`EVENT_PLAYER_HERO_SKILL` / `SelectHeroSkill`） |
| **前序文档** | [`warcraft-iii-action-ids-and-dota-stats-transmission.md`](./warcraft-iii-action-ids-and-dota-stats-transmission.md)、[`warcraft-iii-action-ids-payload-length-audit.md`](./warcraft-iii-action-ids-payload-length-audit.md)、[`warcraft-iii-ai-hero-move-command.md`](./warcraft-iii-ai-hero-move-command.md)、[`dota-hero-trajectory-and-skill-orders-analysis.md`](./dota-hero-trajectory-and-skill-orders-analysis.md) |
| **配套思维导图** | [`dota-hero-skill-point-learn-flow-mindmap.md`](./dota-hero-skill-point-learn-flow-mindmap.md) |
| **相关（施法）** | [`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md)（使用技能，非加点） |
| **相关（习惯）** | [`dota-player-learn-habit-recorder.md`](./dota-player-learn-habit-recorder.md)（加点习惯记录与聚合） |

---

## 一、核心结论（先读这段）

| 问题 | 结论 |
| :--- | :--- |
| 按 **O** 在协议层发什么？ | 仅 **`0x66`**（Enter hero skill submenu），**0 字节载荷**。不消耗技能点。 |
| 真正「加点 / 学技能 / 学属性」是什么？ | **`0x10` 无目标指令**，`AbilityId` = 技能 FourCC（如 `A05G`）或属性附加（多数英雄 `Aamk`，少数 `A0NR`）。 |
| 属性点和技能点是不是两套协议？ | **同一套。** 属性附加是可学习技能；在 O 打开的子菜单里点 U（或点图标）同样发 `0x10 + Aamk/A0NR`。 |
| AI 要不要再挖 `game.dll` 的「学习技能」C++ 函数？ | **交付 AI 接口不必。** 与 `-buy` / `-move` 相同：组 Action → `GameEnqueuePlayerAction_Ex`。已有各版 `Enqueue` RVA 即可。 |
| 地图 JASS 的 `SelectHeroSkill` 能当 AI 玩家指令吗？ | **不能当联机权威路径。** 那是地图脚本改单位技能等级；玩家侧必须走 Action，主机广播后引擎扣点并触发 `EVENT_PLAYER_HERO_SKILL`。 |
| 是否必须先发 `0x66` 再发 `0x10`？ | 人手路径是 **O → 再选技能**。注入时 **建议先 `0x66` 再 `0x10`**（贴近人手、UI 一致）；引擎是否强制要求子菜单状态，需一局抓包/回放验证（见第六节）。 |
| 如何知道英雄升级了？ | **有同步。** DotA 在 `EVENT_PLAYER_HERO_LEVEL` 后发 **`0x6B` GameCache**：`Data:Level{等级}={玩家槽}`。进程内还可读已有 `GetHeroLevel` Hook → `g_lastHeroLevel`。 |
| 升级要不要再逆向 `game.dll`？ | **感知升级 / 触发加点：不必。** 无单独「升级 Action」；等级由引擎模拟抬升，地图用 `0x6B` 广播。仅当要精确读「未用技能点/当前经验条」内存字段时，才值得轻量挖单位 Hero 结构。 |

---

## 二、端到端流程

```text
升级获得技能点（引擎 Hero / AHer）
        │
        ▼
命令卡出现「英雄技能」格（快捷键 O，书本/加点图标）
        │  玩家按 O 或点击该格
        ▼
本地 UI 进入 Learn 子菜单  ──同时──►  出站 Action: 0x66（0 字节）
        │                              └─ W3GS_OUTGOING_ACTION → 主机广播
        ▼
子菜单命令卡：可学技能 Q/W/E/R… + 属性附加（热键多为 U）
        │  点击某技能 / 按热键 / 点属性
        ▼
出站 Action: 0x10
  Flags(2) + AbilityId(4 FourCC) + Unknown(8 常 FF…)
        │
        ▼
主机校验：选中单位是己方英雄、有未用技能点、等级/前置满足、未满级
        │  通过则：扣 1 技能点、技能等级 +1
        ▼
引擎触发 EVENT_PLAYER_HERO_SKILL
        │
        ▼
DotA war3map.j 各英雄 Trigger（GetLearnedSkill / GetUnitAbilityLevel）
        └─ 衍生技能、特效、幻象同步等地图逻辑
```

要点：

1. **O 只切菜单**；扣点发生在第二次的 `0x10`。
2. **权威在引擎 + 主机**；纯本地改内存不会让对家看到加点。
3. 地图脚本大量 `UMI(t, EVENT_PLAYER_HERO_SKILL)`：学完后脚本反应，不负责「玩家点选」本身。

---

## 三、协议与包格式

### 1. `0x66` — 打开技能加点菜单（O）

| 项 | 值 |
| :--- | :--- |
| ActionID | `0x66` |
| 载荷长度 | **0** |
| 工程命名 | `Hero skill submenu` /「技能菜单」 |
| 易混淆点 | 旧文档曾把 `0x66` 当成 GameCache；**DotA 战绩同步是 `0x6B`**（见 payload 审计文档） |

War3Bot：`client.cpp` `getActionPayloadLength` / `getActionName`；`matchstatsprovider.cpp` 描述为「📘 打开技能加点菜单 (O)」。

关闭子菜单：常见 **`0x61`（ESC）**，载荷 0。

### 2. `0x10` — 学习技能 / 属性附加

与停止、无目标施法、商店购买同一 Action ID，靠 **AbilityId 语义**区分：

| 场景 | AbilityId（orderId） | 识别线索 |
| :--- | :--- | :--- |
| 学技能 | 技能 rawcode，如 `A05G`、`AEbl` | `0x41xxxxxx`～`0x7Axxxxxx` 且落在英雄技能表 |
| 学属性 | `Aamk` 或（水人/德鲁伊等）`A0NR` | 同上；UI 称「属性附加」 |
| 停止 | `0x000D0004` | 引擎 order 常量 |
| 买货 | `0x6830xxxx`（`h0**` 单位码） | 商店；flags 实测常 `0x0044` |

**学习用推荐布局**（与 `client.cpp` / `-buy` 同构，总长 ActionID+14）：

```text
[0]     ActionID = 0x10
[1..2]  Flags    uint16   ← 人手学习常见 0x0000；购买为 0x0044。注入前用真实 O→学技能抓包核对
[3..6]  AbilityId uint32  ← FourCC 小端，如 'Aamk' = 0x41616D6B
[7..14] Unknown  8 bytes  ← 抓包多为 FF FF FF FF FF FF FF FF
```

`matchstatsprovider.cpp`：`orderId` 取 payload+2；若 FourCC 命中英雄技能槽或 `dotaAbilityInfo`，记为「📘 学习…」。

### 3. 命令卡语义（勿与「直接学 Aamk」混淆）

`main.qml` 英雄面板把 O 格标成「英雄技能/属性 / 加点 (O)」，并挂 `attrObj.code`（展示属性等级）。**协议上 O = `0x66`，不是 `0x10+Aamk`。**  
属性真正升级：进入子菜单后再发 `0x10 + Aamk/A0NR`（热键多为 **U**，见 `dota_data.json`）。

---

## 四、引擎 / 地图两侧职责

### 引擎（game.dll）

- 英雄单位带 Hero 能力（`AHer` 等），升级给 **unspent skill points**。
- 命令卡「学习」格在有点数时可点；O 进子菜单。
- 处理 `0x10` 学习：校验点数、英雄等级门槛（大招常见 6/11/16）、最大等级（普技 4、大招 3、属性 10 等，以地图技能数据为准）。
- 成功后改技能等级并触发 **`EVENT_PLAYER_HERO_SKILL`**。

### 地图（`War3Script` / DotA 6.83d）

| API / 事件 | 用途 |
| :--- | :--- |
| `EVENT_PLAYER_HERO_SKILL` | 玩家（或脚本）学会技能后的反应 |
| `GetLearnedSkill()` / `GetUnitAbilityLevel()` | 分支衍生效果 |
| `SelectHeroSkill(unit, abilId)` | **脚本侧**强制学一级（幻象、测试、特殊逻辑）；非玩家键盘路径 |
| `UnitModifySkillPoints` | 加减可用技能点（如特殊单位初始化） |

AI **控制真人槽位英雄**应注入 Action，不要指望在客户端单独 `SelectHeroSkill` 同步全场。

### 数据表（业务层）

- `War3Bot/images/dota_data.json`：每英雄 `skills[]` + `attrCode`（`Aamk` / `A0NR`）。
- AI 命令解析：token → FourCC（技能码 / `attr` / slot 1..4）。

---

## 五、与现有 AI 管道对齐（实现建议）

```text
RemoteControl / 游戏内聊天（主名 -learn|/learn；兼容 -skill）
        │
        ▼
 AiControlManager / NetworkManager（IPC）
        │
        ▼
 war3hook Action 线程
        │
        ├─ 若当前选中非己方英雄 → buildSelectionSwitchAction（同 -buy/-move）
        ├─ （推荐）enqueue [0x66]
        └─ enqueue [0x10 | flags | AbilityFourCC | FFFFFFFF FFFFFFFF]
              → g_originalGameEnqueuePlayerAction_Ex
```

**命令命名**：加点用 **`learn`**，施放用 **`cast`**（见 [`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md)）；`skill` 仅作加点兼容别名，避免与「放技能」口语冲突。

| 维度 | `-buy`（已有） | `-move`（已有/同构） | **`learn`（拟加；兼容 skill）** |
| :--- | :--- | :--- | :--- |
| 入队 API | `EnqueuePlayerAction_Ex` | 同左 | **同左，无新 RVA** |
| 主 Action | `0x10` + 物品/单位码 | `0x11` + 点地 order | **`0x66`（可选）+ `0x10` + 技能 FourCC** |
| 选中前置 | 商店 | 英雄 | **英雄** |
| 业务表 | `DotaItemShopAbbrev` | 坐标 | **`dota_data` 技能/attrCode** |

**不需要**为「学习技能」单独逆向各版 `SelectHeroSkill` 原生入口才能做 AI；`versions/*/game.dll` 上继续维护的是已有 **Enqueue / NetProvider** 偏移。仅当要做「读剩余技能点 / 灰态判断」内存 UI 时，再挖命令卡/`unspentSkillPoints` 相关 RVA（增强项）。

---

## 六、如何感知「英雄升级了」？

### 1. 升级本身有没有专用玩家 Action？

**没有。** 玩家不会发「我升级了」的 `0x10`/`0x11` 之类指令。经验与升级是引擎在全端同步模拟里完成的（击杀/吃经验等权威结果到位后，英雄 XP 过阈值 → 等级 +1 → 给技能点）。

### 2. DotA 会不会发同步包？——会，走 `0x6B`

地图在全英雄 `EVENT_PLAYER_HERO_LEVEL` 上挂了条件 `BQ2`（`war3map_9.j` 注册 + `war3map_3.j` 实现）：

```jass
// BQ2：非幻象真实英雄升级时
call GK1(GetOwningPlayer(GetTriggerUnit()))
call FL1("Level"+I2S(GetHeroLevel(GetTriggerUnit())), GetPlayerId(GetOwningPlayer(GetTriggerUnit())))
```

`FL1`（`war3map_1.j`）本质是：

```text
StoreInteger(OS, "Data", "Level"+等级, 玩家槽)
若本机是同步源玩家 WO：SyncStoredInteger → 生成 Action 0x6B
```

| 项 | 值 |
| :--- | :--- |
| Action | **`0x6B`**（`SyncStoredInteger`，1.24b+） |
| Cache | 通常 `dr.x`（与其它 DotA 同步一致） |
| MissionKey | `"Data"` |
| Key | **`Level` + 当前等级**，如 `Level5`、`Level12` |
| Value | **玩家槽 `GetPlayerId`**（0-based；Bot 展示侧常按业务映射） |
| 语义 | 「该槽位英雄升到了该等级」 |
| 精确经验值 | **不同步**；录像/Bot 侧通常只有等级事件 |

War3Bot 已解析：`matchstatsprovider.cpp` 将 `Data:Level…` 描述为「⬆️ [等级提升] … 升到了 N 级」，并写入 `seriesEvents["Level"]`。

收包路径：任意客户端/War3Bot 在 `W3GS_INCOMING_ACTION` 流里看到该 `0x6B` 即可知升级（含观战/统计端）。

### 3. 进程内（war3hook）已有通道

`war3hook_jass.cpp` 在 JASS 原生 **`GetHeroLevel`** 返回时，若 handle 匹配 `g_lastHeroHandle[i]`，写入：

- `g_lastHeroLevel[i]`
- `g_pSharedData->gameStats[i].heroLevel`

AI 在 Launcher/hook 侧可对 `heroLevel` 做边沿检测（`old → new`）作为「刚升级」信号，与监听 `0x6B Level*` 等价用途不同：前者偏本机脚本读等级，后者偏全场同步事件。

### 4. 要不要逆向 `game.dll`？

| 目标 | 要不要挖 dll |
| :--- | :--- |
| 知道「升没升级 / 升到几级」 | **不必** — 用 `0x6B Data:LevelN=pid` 或已有 `GetHeroLevel` Hook |
| 升级后自动 `learn` | **不必** — 检测等级边沿 → 组 `0x66`+`0x10` 入队 |
| 读未花费技能点 / 经验条百分比 | **可选轻量** — 挖 Hero 单位字段或 Hook `GetHeroSkillPoints`；也可用规则推断（每级通常 +1 点，扣点靠成功学习），精度略差 |
| 找「升级发包」C++ 函数 | **不需要** — 没有这种玩家出站包；地图同步已是 `SyncStoredInteger`→`0x6B` |

---

## 七、建议验证（半日级，落地前）

1. 开一局 DotA，英雄升级后：只按 **O** → 日志应仅见 `0x66`。
2. 再学 **1 技能** → 抓一条 `0x10` hex，确认 Flags 与尾 8 字节。
3. 学 **属性附加** → `AbilityId` 为 `Aamk` 或该英雄 `attrCode`。
4. 用 hook 回放同 hex（可先不发 `0x66`、再发 `0x66+0x10`），看点数是否扣减、对家是否同步。
5. 无点数 / 大招未到等级时注入，确认引擎拒绝且不花点。

样本可落 `War3Analysis/artifacts/`，正文相对链接。

---

## 八、AI 命令实现方案（已单独立项）

完整分层、IPC、组包、文件清单与验收见：

**[`dota-ai-skill-command-implementation.md`](./dota-ai-skill-command-implementation.md)**  
导图：[`dota-ai-skill-command-implementation-mindmap.md`](./dota-ai-skill-command-implementation-mindmap.md)

摘要：

```text
learn|-learn|/learn <FourCC|1..4|attr> [nosubmenu]   # 主名
skill|-skill|/skill …                                # 兼容别名
→ MSG_TYPE_HERO_SKILL_LEARN → 选中英雄 → (0x66) → 0x10+AbilityId
```

成对命令：施法用 **`cast`**（非 `skill`）。状态：**方案已写，代码未落地**。
---

## 九、文档命名与维护约定

| 项 | 约定 |
| :--- | :--- |
| 正文 | `War3Analysis/analyses/<topic>.md` |
| 导图 | 同目录 `<topic>-mindmap.md` |
| 本主题 | `dota-hero-skill-point-learn-flow` |
| 元信息 | 文首表：模型、目的、命名、时间 |
| 多版本 RVA | 若新增引擎函数，在表中列 `versions` 下各 build；本主题交付路径不依赖新函数 |

---

## 十、参考锚点（代码）

- `0x66` / `0x10` 长度与命名：`War3Bot/src/client.cpp`（`getActionPayloadLength` ≈ L9480+，`getActionName`）
- 学习识别与 O 文案：`War3Bot/src/matchstatsprovider.cpp`（`0x10` 学习分支 ≈ L1597+；`0x66` ≈ L2177+）
- 命令卡 O 展示：`War3Bot/main.qml`（`cellHeroSkill` / HeroSkillEquipPanel）
- 注入范例：`War3Launcher/hooker/war3hook_process.cpp`（购买 `0x10` 组包 ≈ L3235+；移动队列 ≈ L3305+）
- 地图事件：`War3Script/war3map_*.j` 中 `EVENT_PLAYER_HERO_SKILL`、`SelectHeroSkill`
- 升级同步：`war3map_3.j` `BQ2` + `war3map_1.j` `FL1`；`war3map_9.j` 注册 `EVENT_PLAYER_HERO_LEVEL`
- 进程内等级：`war3hook_jass.cpp` `HASH_GET_HERO_LEVEL` → `g_lastHeroLevel`
