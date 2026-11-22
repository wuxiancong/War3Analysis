# DotA 6.83d AI 数据表：坐标库 · 卡尔切球 · 隐藏辅助技能

| 项 | 内容 |
| :--- | :--- |
| **分析模型** | Composer（Cursor Agent） |
| **分析目的** | 补齐 tactics「六、待补能力」中的坐标库 / 卡尔切球表 / 隐藏辅助技能映射，供 AI 控符、肉山、卡地形远古、卡尔连招、影魔假摇大等 |
| **命名方式** | `dota-683d-ai-data-tables`；机器可读 `artifacts/ai-data/*.json` |
| **分析时间** | 2026-11-21 |
| **约束** | 只读；未改 hook / War3Bot 源码 |
| **不重复** | 眼位见 [`dota-683d-ward-and-deward.md`](./dota-683d-ward-and-deward.md)；野点 AABB 见 [`dota-neutral-camp-spawn-box.md`](./dota-neutral-camp-spawn-box.md) |

## 机器可读产出

| 文件 | 内容 |
| :--- | :--- |
| [`artifacts/ai-data/map_landmarks_683d.json`](../artifacts/ai-data/map_landmarks_683d.json) | 符点 / 肉山 / 远古池 / 泉水 / 商店 / 河道路径 |
| [`artifacts/ai-data/invoker_orb_combos_683d.json`](../artifacts/ai-data/invoker_orb_combos_683d.json) | 卡尔 Q/W/E/R + 10 祈唤技 |
| [`artifacts/ai-data/hidden_aux_skills_683d.json`](../artifacts/ai-data/hidden_aux_skills_683d.json) | 按键码 → 真施放码 / OrderId + `build_skill_table.py` 补丁建议 |

---

## 1. 地图坐标库

坐标系：世界坐标（`GetUnitX/Y`）。来源标注 **script** = `war3map_*.j` rect / `CreateUnit`；**derived** = 由 spawn 偏移推得（置信度中）。

### 1.1 神符

| ID | 坐标 (x,y) | 来源 | 用途 |
| :--- | :--- | :--- | :--- |
| `rune_top` | **-2352, 1648** | script `G4` → `F1=GetRectCenter(G4)` | 上路河道符 |
| `rune_bot` | **3008, -2832** | script `D4` → `G1=GetRectCenter(D4)` | 下路河道符 |

**刷新规则**（`CBO` + `J20`）：

1. 开局 `GameStart` 后 `TriggerEvaluate(J20)`：`J40=true` → **两点都刷赏金 `I0RC`**，再 `J40=false`。  
2. 之后每 **120 s** 周期：清空 `G4`/`D4` 上旧符；一处随机力量符（`I007` 幻象 / `I006` 极速 / `I00K` 双倍 / `I008` 回复 / `I00J` 隐身，避开上次 `J30`），另一处 **赏金 `I0RC`**；上下路随机对调。

### 1.2 肉山

| ID | 坐标 (x,y) | 来源 | 用途 |
| :--- | :--- | :--- | :--- |
| `roshan_spawn` | **4176, -2288** | script `P4` → `NQO` `CreateUnitAtLoc(..., 'n00L', ...)` | **权威出生点**（单位 `n00L`） |
| `roshan_approach_w` | 3900, -2288 | derived | 西侧接近 / 风筝（中置信） |
| `roshan_approach_n` | 4176, -2000 | derived | 北沿站位（中置信） |
| `kb_nw_river` | -2368, 1664 | script `KB` | NW 河道控制（**不是**脚本出生点） |
| `z6_nw_high` | -2176, 2320 | script `Z6` | NW 高台（上路符侧） |

> 脚本出生在 `P4`（偏下路河道东侧）。若实机肉山战斗盒与经典 NW 坑不一致，以 `n00L` 实时坐标为准，再回填 JSON。

### 1.3 远古野点与卡地形站位

`P3O` 调度下，**仅野点 #1（`H4`）与 #2（`Z4`）** 的刷新池含 `RAO` → **远古蜥蜴 `n0LC`/`n0LD`**（1/5 概率）。其余野点无该池。

| ID | spawn (x,y) | check | 来源 | 卡地形站位 (x,y) | 用途 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ancient_pool_camp1` | **4640, -976** (`H4`) | `Q4` | script `PIO`/`RAO` | **4900, -1200**（derived SE 树/崖） | 先知 `Emns` / 美杜莎 `H00V` 卡位打远古 |
| `ancient_pool_camp2` | **-3216, -256** (`Z4`) | `U4` | script `P1O`/`RAO` | **-3450, -500**（derived SW） | 同上（西野） |

站位原则：站在 **刷新区外、树木/`wpm` 不可达** 一侧，使远古寻路失败；精确点需对照 `war3map.wpm` / 实机微调（置信度中）。完整 12 野 AABB 仍用 spawn-box 文档。

### 1.4 泉水

| ID | 坐标 | 单位 | 来源 | 用途 |
| :--- | :--- | :--- | :--- | :--- |
| `fountain_radiant` | **-7296, -7200** | `nfoh` 生命之泉 | script | 近卫回城 / 出生 |
| `fountain_dire` | **6784, 6368** | `ndfl` 被污染的生命之泉 | script | 天灾回城 / 出生 |

### 1.5 商店 / 秘密商店（摘录）

| ID | 坐标 | 单位 / 名 | 来源 | 用途 |
| :--- | :--- | :--- | :--- | :--- |
| `secret_radiant_side` | -7296, 4224 | `u00Z` 地精实验室 | script | 秘密商店（近卫侧） |
| `secret_radiant_side_vendor` | -7296, 4416 | `u010` 地精商人 | script | 秘密商店配套 |
| `secret_dire_side` | 7360, -4416 | `u00Z` | script | 秘密商店（天灾侧） |
| `secret_dire_side_vendor` | 7360, -4224 | `u010` | script | 秘密商店配套 |
| `radiant_home_*` | 见 JSON（约 -72xx,-65xx） | `n002`/`n00V`/`n00W`/`n00X`/`n009`/`n01K`/`nC38` 等 | script | 近卫家商店区 |
| `dire_home_*` | 见 JSON（约 60xx,60xx） | 同上镜像 | script `Player(6)` | 天灾家商店区 |
| `radiant_fountain_tree` | -6624, -7200 | `e025` 奇迹古树 | script | 泉边店 |
| `radiant_fountain_vault` | -6944, -7200 | `hC95` 奎尔瑟兰的密室 | script | 泉边店 |

完整列表以 JSON 为准。

### 1.6 河道路径点

| ID | 坐标 | 来源 | 用途 |
| :--- | :--- | :--- | :--- |
| `river_top_rune` | -2352, 1648 | `G4` | NW 节点 |
| `river_mid_west` | -4544, 1152 | script `uC74` | 中河西 |
| `river_mid_y5` | -368, -656 | `Y5` | 中河枢纽 |
| `river_mid_east` | 3200, -64 | script `uC74` | 中河东 |
| `river_bot_rune` | 3008, -2832 | `D4` | SE 节点 |
| `river_bot_oc` | 2656, -3136 | `OC` | 下路河接近 |

---

## 2. 卡尔（Invoker `H00U`）切球表

### 2.1 三个球 + 祈唤

| 槽 | 键 | 元素 | 技能码 | OrderStr | OrderId | Action |
| :-: | :-: | :--- | :--- | :--- | :---: | :---: |
| 1 | Q | 冰 Quas | `A21W` | `roar` | `0xD00C4` (852164) | `0x10` |
| 2 | W | 雷 Wex | `A21X` | `fanofknives` | `0xD022E` (852526) | `0x10` |
| 3 | E | 火 Exort | `A21V` | `battleroar` | `0xD0277` (852599) | `0x10` |
| 4 | R | 祈唤 | `A21Y` | `howlofterror` | `0xD026C` (852588) | `0x10` |

规则：只认**最近三次**球；`R` 把组合写进祈唤栏（通常保持 2 个已祈唤技）；再对该技发自己的 OrderId。

### 2.2 十技能映射

| 组合 | 技能 | 主码（备码） | OrderStr | OrderId | Action |
| :---: | :--- | :--- | :--- | :---: | :---: |
| QQQ | 急速冷却 | `A0VZ` (`A0YA`) | `autoentangle` | `0xD0219` | `0x12` |
| QQW | 幽灵漫步 | `A0XL` (`A0YD`) | `windwalk` | `0xD00A1` | `0x10` |
| QQE | 寒冰之墙 | `A0VP` (`A0YH`) | `autodispeloff` | `0xD00A6` | `0x10` |
| WWW | 电磁脉冲 | `A0VS` (`A0YC`) | `animatedead` | `0xD00F9` | `0x11` |
| WWQ | 强袭飓风 | `A0VK` | `ancestralspirittarget` | `0xD020B` | `0x11` |
| WWE | 灵动迅捷 | `A0VQ` (`A0Y9`) | `ancestralspirit` | `0xD020A` | `0x12` |
| EEE | 阳炎冲击 | `A0VG` (`A0YI`) | `blizzard` | `0xD0079` | `0x11` |
| EEQ | 熔炉精灵 | `A0VO` (`A0YG`) | `autodispel` | `0xD00A4` | `0x10` |
| EEW | 混沌陨石 | `A0VN` | `auravampiric` | `0xD00F8` | `0x11` |
| QWE | 超震声波 | `A0VM` (`A0YE`) | `auraunholy` | `0xD00F7` | `0x11` |

**切球指令序列示例（吹风→陨石→声波）**：

```text
W W Q R     # Tornado
E E W R     # Chaos Meteor
cast Tornado @ point
cast Meteor  @ same vector (+延迟)
Q W E R     # Deafening Blast
cast Blast   @ point
```

对应 tactics 目录键 `invoker`。

---

## 3. 隐藏辅助技能映射

问题：`build_skill_table.py` 丢弃 `slot>4`，且部分主槽被标成 `PASSIVE`（如影魔大 `A29J`），导致假摇大 / 三连压 / 二段技不可用。

### 3.1 影魔 `Nfir`（优先）

| 按键 / UI | UI 码 | 真施放码 | OrderId | Action | 说明 |
| :--- | :--- | :--- | :---: | :---: | :--- |
| Z 近炮 | `A0EY` | `A0EY` | `0xD00C4` `roar` | `0x10` | 可学主槽 |
| X 中炮 | （parent `A0EY`） | **`A0FH`** | `0xD026C` `howlofterror` | `0x10` | `isExtra` slot5 |
| C 远炮 | （parent `A0EY`） | **`A0F0`** | `0xD0277` `battleroar` | `0x10` | `isExtra` slot6 |
| R 挽歌 | `A29J` | `A29J` | **`0xD0131`** | `0x10` | 表内假被动；`fakecast` 用此 Order |

### 3.2 其他高价值 extras

| 英雄 | UI / parent | 真施放 | OrderId | 用途 |
| :--- | :--- | :--- | :---: | :--- |
| 仙女龙 `N00B` | `A0S9` | `A0SA` | `0xD0278` | 灵动之翼（飞向法球） |
| 船长 `H06S` | `A11N` | `A13D` | `0xD02B7` | X 标记返回 |
| 火猫 `N0M0` | `A2JK` | `A2JL` | `0xD00D9`* | 余烬激活 |
| 凤凰 `E02F` | `A1RJ` / `A1YY` | `A1Z2` / `A1YX` | `0xD00D9` / `0xD020A` | 指定精灵 / 精灵技 |
| 水人 `O00P` | `A0KX` | `A0KW` | `0xD0241` | 属性转换辅槽 |

\*火猫 Order 取自地图 `Order=acolyteharvest`；若实机不符以 `vtable[+0x308]` 为准。

### 3.3 建议补进 `build_skill_table.py`

在 `resolve()` 之后增加 **`ORDER_OVERRIDE`** / **`EXTRA_CAST_SLOTS`**（完整片段见 `hidden_aux_skills_683d.json` → `buildSkillTablePatch`）：

1. 不要丢弃 `dota_data.json` 里 `isExtra && code` 的槽。  
2. `ORDER_OVERRIDE['A29J'] = (None, 0xD0131, 'none')` 等覆盖假被动。  
3. 影魔输出三行：`A0EY` / `A0FH` / `A0F0` 均可 `cast`。  
4. 卡尔 10 技走运行时技能链表或加载 `invoker_orb_combos_683d.json`，不必静态塞满头文件。

---

## 4. 与 tactics 待补项对照

| 待补 | 本表交付 |
| :--- | :--- |
| 坐标库（符点 / 肉山 / 远古卡位） | §1 + `map_landmarks_683d.json`（眼位仍用 ward 文档） |
| 卡尔切球状态机 | §2 + `invoker_orb_combos_683d.json` |
| 隐藏辅助技能映射 | §3 + `hidden_aux_skills_683d.json` + 脚本补丁说明 |

---

## 5. 来源索引

- `War3Script/war3map_2.j` `CBO`；`war3map_3.j` `J20`/`NQO`/`P3O`/`RAO`  
- `War3Script/war3map_9.j` rects / `CreateUnit` 商店泉水  
- `War3Bot/images/dota_data.json`；`artifacts/ability-orders/dota_hero_skills.json`；`orders-1.27.json`  
- [`dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md`](./dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design.md)  
- 地图 SLK / `*AbilityFunc.txt`（`artifacts/ward-deward/map/`）
