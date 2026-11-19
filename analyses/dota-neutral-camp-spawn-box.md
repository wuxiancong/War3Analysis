# DotA 6.83d 野点封野区域（刷新区 AABB）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 逆向「站/插眼在某区域内会封野、否则不封」的几何与判定；供后续命令画带边框长方体 UI |
| **命名方式** | `dota-neutral-camp-spawn-box`；导图 `*-mindmap`；代码短名 `CampSpawnBox` / `campboxes`（勿冗长） |
| **分析时间** | 2026-11-19 |
| **样本** | `War3Script/war3map_3.j` `P3O`/`P2O`/`POO`；`war3map_9.j` `Rect(...)`；`war3mapMisc.txt` `GuardDistance` |
| **工具** | 脚本为主；`versions`/`Ghidra`/`REA` **本主题不必**（可选仅核对引擎 `GroupEnumUnitsInRect`） |
| **配套思维导图** | [`dota-neutral-camp-spawn-box-mindmap.md`](./dota-neutral-camp-spawn-box-mindmap.md) |
| **相关** | [`dota-ai-neutral-creep-pull.md`](./dota-ai-neutral-creep-pull.md)；技巧库 `blockcamp` / `stack` |

---

## 一、核心结论

| 问题 | 结论 |
| :--- | :--- |
| 封野看的是「视野」吗？ | **否。** 与守卫视野无关；是刷新时刻 **检测矩形内是否还有「算占用」的单位**。 |
| 形状是圆还是方？ | **轴对齐长方形（AABB / `rect`）**，不是圆。UI 可画成带边框的「长方体」（XY 用 rect，Z 用地形高度做显示厚度）。 |
| 要不要逆向 `game.dll`？ | **不必。** 判定全在地图脚本 `P3O`：`GroupEnumUnitsInRect` + 过滤后为空才刷。 |
| `GuardDistance=600`？ | **另一套机制**：野怪仇恨/回营距离（`war3mapMisc.txt`），**不是**封野盒。拉野 leash ≠ 封野区。 |
| 现有 AI `blockcamp`？ | 插在聚类中心点上，多数落在盒内能封；精确挡边/画 UI 应改用本文 **check rect**。 |

---

## 二、机制（脚本）

### 2.1 刷新时钟

游戏开始号角后（`IU2`）：

```text
TriggerRegisterTimerEvent(OH, 60, true)   // 之后每 60s
TriggerRegisterTimerEvent(t, 30, false) → IQ2 → TriggerEvaluate(OH)  // 首波 0:30
```

- 首批野怪：**开局后 30s**。  
- 之后：**每分钟整点**（相对该 60s 周期）。  
- `-noneutrals` 等会把 `O3I=false`，`P3O` 直接 return，整图不刷。

### 2.2 单点判定（`P3O`）

每个野点一对 rect：

| 角色 | 变量 | 用途 |
| :--- | :--- | :--- |
| **封野 / 占用检测区** `r1` | 如 `Q4`、`U4`、`I5`… | `GroupEnumUnitsInRect(g, r1, N1I)` |
| **出生点区** `r2` | 如 `H4`、`Z4`、`V4`…（较小） | 空则在 `GetRectCenter(r2)` 上 `CreateUnit(DO,…)` |

```text
GroupEnumUnitsInRect(g, r1, true)
P2O(g): 去掉「不算占用」的单位后 FirstOfGroup==null ?
  yes → 在该点刷一组野怪
  no  → 本分钟本点不刷（封野 / 未拉走 / 仍有野）
```

`N1I` 恒 `true`（全收）；真正过滤在 `POO` / `P2O`。

### 2.3 谁算「封野」、谁不算（`POO`）

从枚举组里 **剔除**（剔除后若组空 → 仍可刷）：

| 条件 | 含义（短名） |
| :--- | :--- |
| `GetUnitAbilityLevel(u,'A0P4')!=0` | 带 `A0P4` 的单位不计 |
| `typeId == 'o003'` / `'o01X'` | 特定假单位不计 |
| `IC1(u)` | 死/无效句柄不计 |
| `RYI(u)` | 一串召唤/特殊单位码不计（含部分 `n***` / `e***`） |

**侦察/岗哨守卫**不在上述剔除表里 → **落在 `r1` 内会封野**。  
英雄、小兵、未剔除的召唤物同理。

囤野（stack）：把本营野怪 **拉出 `r1`**，刷新时组空 → 再刷一波叠在外面的旧野上。

### 2.4 与「可视/仇恨」的区分

| 概念 | 形状 | 数值来源 | 用途 |
| :--- | :--- | :--- | :--- |
| **封野盒** | AABB rect | 脚本 `r1` | 刷不刷 |
| **出生点** | 小 rect 中心 | 脚本 `r2` | 刷在哪 |
| **守卫距离** | 近似圆 | `GuardDistance=MaxGuardDistance=600` | 追击/回营 |
| **拉野安全站位** | 经验圆 | 技巧库远程 ~570–700 / 近战 ~260 | 不被打到 |

用户说的「可视范围」若指封野，应对齐 **封野盒**，不要用 600 圆代替。

---

## 三、6.83d 十二野点 AABB 表

坐标系：地图世界坐标（与 hook `GetUnitX/Y` 一致）。  
`check` = 封野区；`spawn` = 出生中心（应落在 check 内）。

| # | check | minX,minY → maxX,maxY | 宽×高 | 中心 | spawn 中心 |
| :-: | :--- | :--- | ---: | :--- | :--- |
| 1 | `Q4` | 3904,-1408 → 4960,-640 | 1056×768 | 4432,-1024 | `H4` 4640,-976 |
| 2 | `U4` | -3552,-768 → -2528,320 | 1024×1088 | -3040,-224 | `Z4` -3216,-256 |
| 3 | `I5` | 1056,-5216 → 2368,-3744 | 1312×1472 | 1712,-4480 | `V4` 1584,-3984 |
| 4 | `O5` | -5120,3008 → -3648,4320 | 1472×1312 | -4384,3664 | `W4` -4512,3408 |
| 5 | `A5` | -3456,3808 → -2656,4864 | 800×1056 | -3056,4336 | `X4` -3088,4256 |
| 6 | `B5` | 2272,-6080 → 3776,-4928 | 1504×1152 | 3024,-5504 | `Y4` 2960,-5008 |
| 7 | `C5` | -1888,2208 → -992,3040 | 896×832 | -1440,2624 | `J4` -1648,2352 |
| 8 | `E5` | 2592,-4800 → 3744,-3328 | 1152×1472 | 3168,-4064 | `K4` 3072,-3712 |
| 9 | `D5` | 416,2624 → 1632,3648 | 1216×1024 | 1024,3136 | `L4` 1232,3040 |
| 10 | `F5` | -1024,-3808 → 192,-2752 | 1216×1056 | -416,-3280 | `M4` -416,-3584 |
| 11 | `Z5` | -800,3072 → 64,4032 | 864×960 | -368,3552 | `V5` -288,3456 |
| 12 | `W5` | -1728,-5056 → -768,-3840 | 960×1216 | -1248,-4448 | `X5` -1056,-4592 |

尺寸量级约 **0.8k～1.5k** 边长，**各点不同**，不能用统一半径圆。

定义位置：`war3map_9.j` ≈ L10496–10526；调度：`war3map_3.j` `P3O` ≈ L2881–2987。

---

## 四、后续自定义 UI（带边框长方体）

### 4.1 建议数据

```json
{
  "schema": 1,
  "map": "DotA v6.83d",
  "camps": [
    {
      "id": 1,
      "check": {"minX": 3904, "minY": -1408, "maxX": 4960, "maxY": -640},
      "spawn": {"x": 4640, "y": -976},
      "zBottom": "terrain",
      "zTop": "terrain+256"
    }
  ]
}
```

落盘建议：`shared/DotaCampSpawnBoxes.h` 或 `config/dota_camp_spawn_boxes_683d.json`。

### 4.2 绘制

- **占用判定用 2D**：点在 `[minX,maxX]×[minY,maxY]` 即封。  
- **显示用 3D 线框**：底面四边 + 顶面四边 + 四条竖棱；`zBottom = GetLocationZ`（或地面），`zTop = zBottom + H`（建议默认 **128～256**，仅视觉；脚本不检 Z）。  
- 命令草案：`campboxes on|off` / `campboxes [id]` / `campboxes all`（短名即可）。  
- 实现可挂现有 overlay / 调试画线管道；**不必**新挖 dll。

### 4.3 与 AI

| 用途 | 用法 |
| :--- | :--- |
| `blockcamp` | 插眼目标改为 `spawn` 或 check 内偏僻角（树后） |
| `stack` | 拉出方向确保野怪在刷新瞬间 **出 check** |
| 调试 | UI 开着时对照 `📍` 英雄/守卫是否在盒内 |

运行时学习的 `g_aiCamps`（450 聚类）仍可作「最近野点」索引，**几何以本文表为准**。

---

## 五、要不要挖 `game.dll`？

| 目标 | 建议 |
| :--- | :--- |
| 封野盒坐标 / UI / AI 封野 | **否** — 脚本已完整 |
| `GroupEnumUnitsInRect` 是否含飞行/隐藏 | 一般不需要；有实测争议再短名专题 `enum-units-rect` |
| 仇恨 600 回营路径 | 可读 Misc；深挖单位 AI 另开文档 |

命名若做可选引擎符号：`camp-spawn-rect` / `camp-box-ui`（短）。

---

## 六、实现勾选

1. **文档**（本文）— 完成。  
2. **静态表** `DotaCampSpawnBoxes`（上表 12 点）。  
3. **命令** `campboxes on/off` 画线框长方体。  
4. **`blockcamp`** 改插 `spawn` / check 内点。  
5. **（可选）** 运行时用 `IsUnitInRegion` 等价逻辑自检：守卫在盒内 → 下一分钟该点不刷。

---

## 七、总结

- 封野区 = **每营独立的轴对齐矩形 `r1`**；空则刷在小矩形 `r2` 中心。  
- **不是圆、不是视野**；600 是仇恨回营。  
- **无需 `game.dll` 逆向**即可做 UI 长方体边框与精确封野。  

---

## 八、参考锚点

- 判定：`War3Script/war3map_3.j` `P3O` / `P2O` / `POO`  
- 时钟：`IU2` → `OH` 60s；`IQ2` 30s 首波  
- Rect：`war3map_9.j` `Q4`/`H4`/…  
- Misc：`GuardDistance` / `MaxGuardDistance` = 600  
- AI：`war3hook_ai_tactics.inl` `aiTryBlockCamp` / `g_aiCamps`  
