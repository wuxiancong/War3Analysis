# DotA1 英雄使用技能整体流程与 AI 注入路径

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 理清 DotA 6.83d 中英雄**施放技能**（非加点）的端到端链路，为后续 AI 命令（如 `-cast`/`/cast`）复用 `EnqueuePlayerAction` 做准备 |
| **命名方式** | `dota-hero-ability-cast-flow`（主题短横线英文）；配套导图同名 + `-mindmap` |
| **分析时间** | 2026-11-16 |
| **关联代码** | `War3Launcher/hooker/war3hook_ai.cpp`（`aiOrderImmediate` / `aiOrderTarget`）、`war3hook_process.cpp`（move/buy 组包）、`war3hook_gfx.cpp`（技能改键）；`War3Bot/src/matchstatsprovider.cpp`、`client.cpp`；`War3Script`（`EVENT_PLAYER_UNIT_SPELL_*`） |
| **前序文档** | [`warcraft-iii-action-ids-and-dota-stats-transmission.md`](./warcraft-iii-action-ids-and-dota-stats-transmission.md)、[`dota-hero-trajectory-and-skill-orders-analysis.md`](./dota-hero-trajectory-and-skill-orders-analysis.md)、[`warcraft-iii-ai-hero-move-command.md`](./warcraft-iii-ai-hero-move-command.md)、[`dota-hero-skill-point-learn-flow.md`](./dota-hero-skill-point-learn-flow.md)（**加点/学习**，勿与本文混淆） |
| **配套思维导图** | [`dota-hero-ability-cast-flow-mindmap.md`](./dota-hero-ability-cast-flow-mindmap.md) |
| **实现（2026-11-16）** | `cast` 已落地：[`dota-ai-human-lasthit-learn-cast.md`](./dota-ai-human-lasthit-learn-cast.md)。第三节「完整业务表需从 AbilityData + 录像生成」已完成：OrderId 直接从 game.dll Order 注册表抽取（344 条），目标类型来自地图 SLK / Order 串 |
| **工具路径** | 见全局规则 `war3-reverse-toolkit`（`hooker` / `versions` / `War3Script` / 调试器 / MPQ / Ghidra / REA / 游戏目录） |

---

## 一、核心结论（先读这段）

| 问题 | 结论 |
| :--- | :--- |
| 使用技能在协议层是什么？ | 与移动/攻击同属 **单位指令 Action**：按目标类型发 **`0x10`（无目标）/ `0x11`（点地）/ `0x12`（单位目标）**。 |
| 包里的「AbilityId」填什么？ | **施法填 OrderId（常见 `0x000Dxxxx`）**，来自技能数据的 Order 字符串映射；**不是**学习技能时用的 FourCC（`A05G`/`Aamk`）。 |
| 按热键有没有单独同步包？ | **无。** 热键/点命令卡只是本地 UI；真正同步的是随后的 `0x10`/`0x11`/`0x12`。点地/点单位前的「瞄准态」通常不发网包。 |
| 被动技能呢？ | **不发施法 Action**（如剑舞）；只有主动技/开关技/物品主动等会出包。 |
| 物品技能算不算？ | 走 **`useslot1..6`（`0xD0028..0xD002D`）**，挂在同一套 `0x10`/`0x11`/`0x12` 上；与英雄技能 Order 不同通道，AI 宜分 `-cast` vs `-useitem`。 |
| AI 要不要再挖 `game.dll` 施法函数？ | **交付注入不必。** 已有 `EnqueuePlayerAction` + `war3hook_ai.cpp` 的 `aiOrderImmediate`/`aiOrderTarget`；需补的是 **技能→OrderId+目标类型表**，不是新 RVA。 |
| 与加点命令区别？ | **加点主名 `learn`**（兼容 `skill`）：`0x66` + `0x10`+**技能 FourCC**。**施法主名 `cast`**：`0x10/11/12`+**OrderId**。勿用 `skill` 表示施法。 |

---

## 二、端到端流程（人手）

```text
选中己方英雄（命令卡显示技能格）
        │
        ├─ 技能改键（可选，本地）: 物理键 → 规范热键 Q/W/E/R…
        │       war3hook_gfx 改 keyCode，仍走引擎命令卡命中
        │
        ▼
按技能热键 / 点击命令卡格子
        │
        ├─【被动】无网包，结束
        │
        ├─【无目标主动】立即出站
        │     Action 0x10 | Flags | OrderId | Unknown(8×FF…)
        │
        └─【点地 / 单位 / 双目标】本地进入瞄准态（一般无包）
                │  再点地面 / 点单位 / ESC(0x61) 取消
                ▼
              0x11（点地）或 0x12（单位）或 0x14（双目标，少见）
                │
                ▼
        W3GS_OUTGOING_ACTION → 主机广播 → 全端模拟
                │
                ▼
        引擎：蓝量/CD/距离/沉默/前置校验
                │  通过则施法
                ▼
        地图 Trigger：EVENT_PLAYER_UNIT_SPELL_CHANNEL / CAST / EFFECT…
                GetSpellAbilityId() = 技能 FourCC（整数）
                执行 DotA 实际效果（伤害、位移、特效等）
```

要点：

1. **权威在 Action + 引擎模拟**；地图用 Spell 事件读 **Ability FourCC**，与网包里的 **OrderId** 是不同层标识。
2. 同一 OrderId 可被多名英雄/多种技能复用（如 `0xD0278`、`0xD00FA`），解析必须结合 **英雄类型**。
3. UI 改键只影响本地按键→命令卡，**不改变**最终 Action 字节。

---

## 三、协议与包格式

载荷长度以 `War3Bot/src/client.cpp` `getActionPayloadLength` 为准（ActionID 外）：

| Action | 场景 | 载荷长 | 布局（payload） |
| :--- | :--- | :--- | :--- |
| **`0x10`** | 无目标技能、stop/hold、学技能、买货 | 14 | `Flags(2) + Id(4) + Unknown(8)` |
| **`0x11`** | 点地技能、部分地面物品 | 22 | `Flags(2) + Id(4) + Unknown(8) + X(4) + Y(4)` |
| **`0x12`** | 对单位施法、攻击、智能右键 | 30 | 同上 + `TargetObj1(4) + TargetObj2(4)` |
| **`0x14`** | 双目标（少见） | 43（含 owner 等，见审计文档） | 两套目标 |
| **`0x61`** | ESC 取消瞄准/子菜单 | 0 | — |

### 1. Id 字段语义对照（易混）

| 用途 | Id 形态 | 示例 |
| :--- | :--- | :--- |
| **施放英雄技能** | OrderId `0x000Dxxxx` | 闪烁 `0xD022D`、洪流类 `0xD0079` |
| **学习技能/属性** | Ability FourCC | `A05G`、`Aamk` |
| **基础命令** | 固定 Order | stop `0xD0004`、hold `0xD0019`、smart `0xD0003`、attack `0xD000F` |
| **使用物品栏** | useslot | `0xD0028..0xD002D` |
| **商店购买** | 单位码 `0x6830xxxx` | `h0**` |

`client.cpp` / `matchstatsprovider.cpp`：`orderId` 均取自 payload 偏移 **+2**（Flags 之后 4 字节）。

### 2. 组包模板（与现有 AI 一致）

`war3hook_ai.cpp` 已实现：

```text
aiOrderImmediate(orderId)     → 0x10，15 字节缓冲（含 ActionID），Flags=0，尾 FF
aiOrderTarget(orderId,x,y,o1,o2) → 0x12，31 字节；攻击用 0xD000F
```

点地施法应对齐 **`0x11`**（22 字节载荷 / 总长 23），布局与 move 文档中的点地模板同构，**Id 换成技能 OrderId**：

```text
[0]     0x11
[1..2]  Flags = 0x0000（以抓包为准）
[3..6]  OrderId
[7..14] FF…
[15..18] X float
[19..22] Y float
```

> 注：当前 `-move` 实现里地面移动实测改用 **`0x12` + 目标 ID 全 FF**（见 `executePendingUnitMove`）。**技能点地仍以录像中的 `0x11` 为主**；落地 AI 时对目标技能各抓 1 条人手包校正，不要假设与 move 完全同形。

### 3. 实测 Order 样本（来自轨迹分析，非全表）

| 目标类型 | OrderId | 代表技能 |
| :--- | :--- | :--- |
| 无目标 `0x10` | `0xD00A1` | 白虎跳跃 |
| 无目标 | `0xD0278` | 鱼人突袭 / 部分无目标主动 |
| 点地 `0x11` | `0xD022D` | 敌法/毒龙 闪烁 |
| 点地 | `0xD0079` | 发条火箭 / 船长洪流 / 火猫拳 |
| 点地 | `0xD02B6` | 帕克法球 / 伐木锯链 / 土猫滚 |
| 单位 `0x12` | `0xD007F` | 骷髅王锤 |
| 单位 | `0xD0107` | 神灵大招冲刺 |
| 单位/点地 | `0xD00FA` | 蓝猫球 / 猛犸冲 / 水人浪 / 虚空漫游 |

完整业务表需从 `AbilityData`/`war3map` 的 Order 字段 + 录像抽样生成；`dota_data.json` 目前有 **code/hotkey/slot**，**尚无 orderId / 目标类型**。

---

## 四、引擎 / UI / 地图职责

### 引擎（game.dll）

- 命令卡命中 → 无目标立即下单；有目标则进瞄准。
- 收到 Action 后校验：选中单位、技能等级、蓝、CD、距离、魔法免疫/自己人规则等。
- **不必**为 AI 再定位 `IssueImmediateOrder` 一类 C++ 入口；那些最终也进同一 Action 队列。

### UI / Hook

- 技能改键：`war3hook_gfx.cpp` 将物理键映射为命令卡规范键（槽位与 `skill_map` 对齐）。
- 仅影响「人手怎么按下」；AI 注入 **绕过 UI**，直接 Enqueue。

### 地图（`War3Script`）

| 事件 / API | 作用 |
| :--- | :--- |
| `EVENT_PLAYER_UNIT_SPELL_CHANNEL/CAST/EFFECT` | 施法各阶段 |
| `GetSpellAbilityId()` | **技能 FourCC**（如剑刃风暴 `A05G` 的整数） |
| `GetSpellTargetX/Y` / `GetSpellTargetUnit` | 目标 |
| `IssueImmediateOrder` / `IssuePointOrder` / `IssueTargetOrder` | **脚本强制下令**（幻象、触发器）；非玩家键盘权威路径 |

玩家侧 AI 应发 Action，不要只在本地调 Issue*Order（联机不同步）。

---

## 五、与现有 AI 管道对齐

```text
RemoteControl / 游戏内聊天（拟：-cast|/cast）
        │
        ▼
 AiControl → IPC（拟 MSG_TYPE_HERO_ABILITY_CAST）
        │
        ▼
 war3hook（主线程选目标 ID + Action 线程 Enqueue）
        │
        ├─ aiSelectHero / resolveLocalHeroObjectIds
        ├─ 无目标 → aiOrderImmediate(orderId)          // 已有
        ├─ 单位目标 → aiOrderTarget(orderId,x,y,t1,t2) // 已有
        └─ 点地 → 组 0x11（待补对称 helper）
```

| 维度 | `-move` / `attack` | **`learn` 加点（另案）** | **`cast` 施法（本文）** |
| :--- | :--- | :--- | :--- |
| 入队 API | `EnqueuePlayerAction_Ex` | 同左 | **同左** |
| 主 Action | `0x11`/`0x12` + 移动 Order | `0x66`+`0x10`+FourCC | **`0x10`/`0x11`/`0x12`+技能 OrderId** |
| 业务表 | 坐标 | 技能 FourCC / attr | **OrderId + 目标类型 +（可选）技能码** |
| 新 dll RVA | 否 | 否 | **否** |

`war3hook_ai.cpp` 文件头已写明：「下达指令一律走 Enqueue…与真人操作等价」——施法是同一原则的自然延伸。

---

## 六、AI 接口草案与命令命名（未实现）

### 命令命名（与加点成对）

| 动作 | **推荐主名** | 可选别名 | 说明 |
| :--- | :--- | :--- | :--- |
| 施放技能 | **`cast`** | `ability`（可选，稍长） | 国际习惯清晰 |
| 加点 / 学一级 | **`learn`** | `skill`（仅兼容） | 见加点实现方案 |

未采用用 `skill` 表示施法：与加点别名冲突，且口语歧义大。  
未采用 `use`：与物品 `-useitem` / useslot 易混。

```text
# RemoteControl / 游戏内
cast <token>                         # 无目标
cast <token> <x> <y>                 # 点地
cast <token> <unitHandle|nearest|…>  # 单位目标（句柄解析同 attack）
-cast / /cast 同上
```

`<token>`：`1..4` / FourCC / 表内简称；内部查：

```text
{ abilityCode, orderId, targetType: none|point|unit|unit_or_point, … }
```

前置：选中英雄；可选校验「已习得等级>0」（读内存或本局学习时间线，二期）。

实现方案可另文 `dota-ai-cast-command-implementation.md`（结构对齐 [`dota-ai-skill-command-implementation.md`](./dota-ai-skill-command-implementation.md)，对外命令写 **`cast`**）。

---

## 七、要不要逆向 `game.dll`？

| 目标 | 要不要挖 dll |
| :--- | :--- |
| AI 发出「用某个技能」 | **不必** — Enqueue `0x10/11/12` |
| 知 OrderId / 目标类型 | **不必挖函数** — 从表 / 录像 / `AbilityData` Order 字段建表；`versions` 仅在改引擎数据读取器时才涉及 |
| 读 CD/蓝量做决策 | **可选轻量** — Hook 已有只读 JASS 或单位字段；非施法管道前置 |
| 模拟完整瞄准 UI | **不需要** — AI 直接发带坐标/目标的终态包 |

多版本：继续维护已有 **Enqueue / NetProvider** 各版 RVA；本主题不新增函数偏移表。

---

## 八、建议验证（半日级）

1. 选无目标技（如剑圣风暴）：抓 `0x10` hex → 记 OrderId。  
2. 选点地技（敌法闪烁）：抓 `0x11` → 核对 Flags/坐标。  
3. 选单位技（骷髅王锤）：抓 `0x12` → 核对目标对象 ID。  
4. 用 `aiOrderImmediate` / 新建 `0x11` helper 回放同 Id，确认全端生效。  
5. 对同一 OrderId 两名英雄各放一次，确认表需带 `heroCode` 消歧。  

样本放入 `War3Analysis/artifacts/`，正文相对链接。

---

## 九、文档命名与维护

| 项 | 约定 |
| :--- | :--- |
| 正文 | `War3Analysis/analyses/dota-hero-ability-cast-flow.md` |
| 导图 | `dota-hero-ability-cast-flow-mindmap.md` |
| 元信息 | 文首：模型、目的、命名、时间 |
| 与加点文档 | `dota-hero-skill-point-learn-flow` = 学习；本文 = 施放 |

---

## 十、参考锚点

- Action 字典：`client.cpp` `getActionPayloadLength` / `getActionName`
- 技能 Order 实测：`dota-hero-trajectory-and-skill-orders-analysis.md`；`matchstatsprovider.cpp` `0x10/11/12` 分支
- AI 组包：`war3hook_ai.cpp` `aiOrderImmediate` / `aiOrderTarget` / `aiSelectHero`
- 移动组包对照：`war3hook_process.cpp` `executePendingUnitMove`
- 技能改键：`war3hook_gfx.cpp` skill remap
- 地图施法事件：`War3Script/war3map_*.j` 中 `EVENT_PLAYER_UNIT_SPELL_*`、`GetSpellAbilityId`
- 加点对照：`dota-hero-skill-point-learn-flow.md`、`dota-ai-skill-command-implementation.md`
