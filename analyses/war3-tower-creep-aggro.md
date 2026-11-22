# War3 / DotA 6.83d 防御塔与兵线小兵索敌 / 仇恨规则

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 确认塔射程/索敌、小兵转火与引擎 CallForHelp；纠正 Gemini「700/650」假设；给 `-aggro draw` 与控线判定可写进代码的条件 |
| **命名方式** | `war3-tower-creep-aggro`；导图 `*-mindmap`；产物目录 `artifacts/tower-creep-aggro/` |
| **分析时间** | 2026-11-21 |
| **验证状态** | **SLK + 地图脚本已核对**；`game.dll` 全版本字符串/原生入口已列表。塔「转火英雄」为引擎行为（无 DotA 专用塔脚本），**未本局实机断点**；建议测试步骤见第八节 |
| **证据** | `artifacts/ward-deward/map/Units_Unit*.slk` / `*UnitFunc.txt` / `war3mapMisc.txt`；`war3map_3.j` CH2 族；`versions/*/game.dll` 扫描；前序 [`war3-lasthit-combat-data.md`](./war3-lasthit-combat-data.md)、[`dota-lane-speed-by-time.md`](./dota-lane-speed-by-time.md) §4 |
| **产物** | [`../artifacts/tower-creep-aggro/`](../artifacts/tower-creep-aggro/) |
| **配套思维导图** | [`war3-tower-creep-aggro-mindmap.md`](./war3-tower-creep-aggro-mindmap.md) |

---

## 一、核心结论

| 问题 | 结论 |
| :--- | :--- |
| 塔攻击射程 / 索敌 | **全部一～四塔（近卫 `e00R/e011/e00S/e019`，天灾 `u00M/u00D/u00N`）`rangeN1 = acquire = 700`**，弹速 **750**，T1 冷却 **1.0**，T2+ **0.95** |
| Gemini 的 `700` / `650` | **`700` 正确**（攻击=索敌）。**`650` 不是引擎或物编常量**；只是约 50 码安全裕度。进塔判定应用 **`dist ≤ 700`**（中心距；可再加 collision） |
| 英雄在塔下 A 敌英雄，塔会否转火 | **会，属引擎**（`CallForHelp=600` 默认 + 建筑 AI）。DotA **无**单独「塔转火」脚本 |
| 兵线拉仇恨（卡仇恨） | **地图脚本主导**：`CH2` 在攻击者周围 **500** 拉电脑小兵转火，**2.0s** 后回 `attack` 路点；攻城车不参与 |
| 引擎 CallForHelp | 库存 `MiscGame.txt`：**`CallForHelp=600`，`CreepCallForHelp=600`**。DotA `war3mapMisc.txt` **未覆盖** → 默认 600。主要用于野怪/引擎 AI；兵线电脑兵的英雄转火走脚本 500/2s |

---

## 二、防御塔数值（物编）

来源：地图提取 `Units_UnitWeapons.slk` / `UnitBalance.slk` / `*UnitFunc.txt`（与 [`dota-6.83d-web-gameplay-data-reverse.md`](./dota-6.83d-web-gameplay-data-reverse.md) §6 一致）。导出：`artifacts/tower-creep-aggro/unit_combat_slk.json`。

| 单位 | 层级（习惯） | HP | 护甲 | 攻击类型 | 伤害 | cool1 | rangeN1 | **acquire** | Missilespeed | 视野 day/night |
| :--- | :--- | ---: | ---: | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `e00R` / `u00M` | 一塔 | 1300 | 20 fort | normal | 99+1d21 | **1.00** | **700** | **700** | **750** | 1900 / 800 |
| `e011` / `u00D` | 二塔 | 1600 | 25 fort | siege | 119+1d21 | **0.95** | **700** | **700** | **750** | 1900 / 800 |
| `e00S` / `u00N` | 三塔 | 1600 | 25 fort | siege | 119+1d21 | **0.95** | **700** | **700** | **750** | 1900 / 800 |
| `e019` | 高地/基地塔 | 1600 | 30 fort | siege | 119+1d21 | **0.95** | **700** | **700** | **750** | 1900 / 800 |

`targs1`：`air,debris,ground,item,nonsapper,structure`（可打英雄与小兵）。`weapTp1=missile`。`collision=144`。

### 2.1 选目标 / 换目标（引擎）

- **索敌圈 = 攻击圈 = 700**：进入该距离即可被选为目标并开火；不存在单独的「650 仇恨圈」。
- **换目标**：当前目标死亡、离开射程/不可见/无敌，或更高优先级事件（友军受伤触发的 CallForHelp / 建筑防御逻辑）时重选。无地图层「每 N 秒强制换目标」定时器。
- **英雄在塔范围内攻击敌方英雄**：受害者受伤 → 引擎 `CallForHelp`（默认 **600**）通知附近友方单位（含塔）。塔若已能攻击攻击者（在 700 内），会转火英雄。这是 **game.dll 建筑 AI**，不是 `war3map.j` 触发器。
- DotA `war3mapMisc.txt` 另有 `AttackNotifyRange=1000`（攻击提示/地图提示类，不是射程）。

### 2.2 与 Gemini 文档对照

[`dota-lane-speed-by-time.md`](./dota-lane-speed-by-time.md) §4：「防御塔攻击射程为 700，仇恨触发约 650」。

| 数字 | 判定 |
| :--- | :--- |
| 700 | ✅ 与 SLK `rangeN1`/`acquire` 一致 |
| 650 | ❌ 无 SLK / Misc / 脚本常量；若要「安全不进塔」，应写 `dist > 700` 或显式 `margin`（例如 50→650），并注明是裕度 |

---

## 三、兵线小兵数值与索敌

| 单位 | rangeN1 | **acquire** | cool1 | Missilespeed | sight/nsight | collision |
| :--- | ---: | ---: | ---: | ---: | :--- | ---: |
| 近战 `esen`/`ugho` | 100 | **500** | 1.0 | 0 | 850/800 | 16 |
| 远程 `edry` | 500 | **800** | 1.0 | 900 | 850/800 | 8 |
| 远程 `unec` | 500 | **600** | 1.0 | 900 | 850/800 | 8 |
| 攻城 `ebal`/`umtw` | 690 | **800** | 2.7 | 1100 | 850/850 | 16 |

近战 **acquire(500) > range(100)** → 会追击到 500 内再近身打。远程 acquire ≥ 射程。

日常行军：`attack` 到 `O2[lane]`（见 [`dota-lane-spawn-waypoints.md`](./dota-lane-spawn-waypoints.md)）；遇敌在 acquire 内自动交战，清完再朝路点（引擎 + 脚本重发）。

---

## 四、地图脚本层：英雄仇恨（卡仇恨本体）

**有。** 核心在 `War3Script/war3map_3.j` ≈ **L8477–L8613**（摘录：`artifacts/tower-creep-aggro/map_script_aggro_excerpt.txt`）。

### 4.1 流程

```text
英雄进入地图 → CJ2 → RRI(真英雄) → CY2：
  注册 EVENT_UNIT_ISSUED_TARGET_ORDER → CV2
  注册 EVENT_UNIT_ATTACKED → CX2
  每英雄一个 Timer（hashtable 141）

CV2：对敌方真英雄下 attack(851983)/smart(851971)
CX2：英雄被「非 BO[0]/CO[0]」单位攻击
  → CH2(相关英雄, 攻击者 Z4O)：
       GroupEnumUnitsInRange(攻击者, **500**, 电脑兵线过滤)
       IssueTargetOrder(小兵, "attack", 攻击者)
       TimerStart(..., **2.00**, false) → CE2：
         清 userData，IssuePointOrderLoc("attack", O2[lane])
```

| 参数 | 值 | 含义 |
| :--- | :--- | :--- |
| 拉仇恨半径 | **500** | 以**攻击者**为圆心 |
| 持续时间 | **2.0 s** | 到时强制回兵线路点 |
| 参与单位 | `BO[0]`/`CO[0]` 小兵，且非攻城 | `CC2` 排除 `ebal/e026/umtw/u00R` |
| 提前解除 | 命令变 0 且不在 `GetUnitAcquireRange` 内 | `CD2` 立刻回路点 |

`RRI`（`war3map_1.j` ≈ L3732）：真英雄且非幻象、非若干傀儡 typeId。

**没有**发现对防御塔下「A 英雄」的额外脚本；塔转火纯引擎。

---

## 五、引擎 CallForHelp / gameplay 常量

| 键 | 库存 `MiscGame.txt` | DotA `war3mapMisc.txt` | 生效值 |
| :--- | ---: | :--- | ---: |
| `CallForHelp` | 600 | **未写出** | **600** |
| `CreepCallForHelp` | 600 | **未写出** | **600** |
| `GuardDistance` / `MaxGuardDistance` | 600 / 1000 | **600 / 600** | 野怪拴绳（见中立拉野文档） |
| `AttackNotifyRange` | — | **1000** | 提示类 |

兵线单位由电脑玩家持有并被脚本 `IssuePointOrderLoc`/`IssueTargetOrder` 驱动，**英雄 A 英雄的转火以脚本 500/2s 为准**；引擎 600 仍影响野怪与未被脚本接管的单位。

### 5.1 `game.dll` 全版本 RVA

完整表：[`artifacts/tower-creep-aggro/native_rva_table.md`](../artifacts/tower-creep-aggro/native_rva_table.md)。摘要：

| 版本 | GetUnitAcquireRange | CreepCallForHelp str | CreepCallForHelp xref(s) |
| :--- | :--- | :--- | :--- |
| 1.0.17.5988 | — | `0x806338` | `0x1C6018` |
| 1.0.20.6048 | — | `0x807378` | `0x1C6018` |
| 1.20.4.6074 | — | `0x807378` | `0x1C6088` |
| 1.21.0.6263 | `0x2C4450` | `0x808490` | `0x1C9248` |
| 1.22.0.6328 | `0x3BE720` | `0x91DE7C` | `0x26C413`, `0x27B174` |
| 1.23.0.6352 | `0x3C0440` | `0x931FBC` | `0x26D953`, `0x27C6B4` |
| 1.24.1.6374 | `0x3C5F00` | `0x9410F4` | `0x26DA03`, `0x27C774` |
| 1.24.4.6387 | `0x3C5FC0` | `0x9410F4` | `0x26DA63`, `0x27C7D4` |
| 1.25.1.6397 | `0x3C5AE0` | `0x92EF94` | `0x26CD23`, `0x27BA84` |
| **1.26.0.6401** | **`0x3C5D10`** | `0x92EF94` | `0x26CF53`, `0x27BCB4` |
| **1.27.0.52240** | **`0x1E5F50`** | `0xA4AB2C` | `0x65A543`, `0x66A948` |

`CAbilityAttack+0x244` = acquire（1.26/1.27 同构，见补刀文档）。`CallForHelp` 各版 str/xref 见同目录 `string_xrefs_all_versions.json`。

扫描脚本：`scan_aggro_strings.py`（覆盖 `War3Launcher/versions` 下全部 11 个 `game.dll`）。

---

## 六、挡路 / 换目标与卡兵

- 小兵有显式 `attack` 点命令时，卡位造成的碰撞绕行见 [`war3-unit-collision-and-repath.md`](./war3-unit-collision-and-repath.md)；**不会**因挡路自动改打英雄。
- 英雄 A 敌英雄 → 脚本 500 内小兵改打英雄（最多约 2s）。
- 英雄站在兵线中只挡路：小兵仍朝 `O2` / 当前攻击目标走，除非 acquire 内出现合法攻击目标。

---

## 七、对 AI 的可写条件（不改代码，仅规格）

### 7.1 `-aggro draw`

| 项 | 推荐值 | 依据 |
| :--- | :--- | :--- |
| 出手 | 对敌方真英雄发 `attack`/`smart`（需可见） | `CV2` |
| 站位 | 出手时尽量让**自己**落在敌方小兵堆 **≤500** 内（脚本以攻击者为圆心） | `CH2` Enum 500 |
| 后撤 | 离开敌方小兵 acquire（近战约 **>500**，远程 **>600~800**），并离开敌塔 **>700** | SLK acquire / 塔 700 |
| 持续时间 | 假定小兵 **≈2.0s** 后回兵线；现 hook `180ms` 后撤仅保证指令发出，**转火窗口是 2s** | `TimerStart(...,2,...)` |
| 勿指望攻城车转火 | 脚本排除 | `CC2` |

现实现：`war3hook_ai.cpp` `aiExecAggroDraw` — 攻击最近可见敌英雄，**180ms** 后撤 **350**。建议决策层按上表把「有效拉仇」定义为：2s 窗口内敌方近战/远程是否进入对自己的攻击；350 后撤在远程 acquire 800 时可能不够，宜 **≥550~850** 视兵种。

### 7.2 `-aggro drop`

A 己方小兵再 stop：用于打断塔/兵对自己的集火（引擎换目标）。与脚本 500/2s 无直接耦合。

### 7.3 兵线「进塔」判定（替换 Gemini 650）

```text
// 敌方兵线是否进入己方一塔攻击圈（中心距）
bool enemyInTower = dist(enemyCreepPos, ownT1Pos) <= 700.0f;
// 若用「安全交汇」：希望交汇点在塔外
bool safeMeet = dist(meetPoint, ownT1Pos) > 700.0f;   // 严格
// 或带裕度（文档化，非引擎常量）：
bool safeMeetSoft = dist(meetPoint, ownT1Pos) > 700.0f + margin; // margin 如 50 → 旧「650」
```

控线：交汇点若 `≤700`，敌兵会被塔集火清除，兵线易被反推。卡兵导致交汇内收时，用 **700** 作硬阈值，不要写死 650 当引擎值。

---

## 八、建议实机测试（主会话执行）

只读 / RemoteControl，不写内存、不在游戏线程外调 JASS：

1. 开局冰女中路，`units` 盯己方一塔与兵线坐标；量敌兵首次掉塔血时的 `dist(creep,T1)`，应接近 **700**（±collision）。
2. 塔下 A 敌英雄：看塔目标是否立刻切到自己（引擎）；同时看 500 内敌方小兵是否转火、约 2s 后是否回兵线。
3. `-aggro draw`：记录后撤距离 350 vs 600/800 时，2s 内被几只兵打中。
4. 对比攻城车：确认不因 CH2 转火英雄。

---

## 九、产物清单

| 路径 | 内容 |
| :--- | :--- |
| `analyses/war3-tower-creep-aggro.md` | 本文 |
| `analyses/war3-tower-creep-aggro-mindmap.md` | 导图 |
| `artifacts/tower-creep-aggro/unit_combat_slk.json` | 塔/兵 SLK 战斗字段 |
| `artifacts/tower-creep-aggro/map_script_aggro_excerpt.txt` | CH2 族摘录 |
| `artifacts/tower-creep-aggro/native_rva_table.md` | 全版本 RVA 表 |
| `artifacts/tower-creep-aggro/string_xrefs_all_versions.json` | 扫描原始结果 |
| `artifacts/tower-creep-aggro/scan_aggro_strings.py` | 全版本扫描脚本 |

**未改** `War3Launcher` / `hooker`。
