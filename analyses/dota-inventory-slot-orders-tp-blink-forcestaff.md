# DotA 物品栏 Order：换格（moveslot）与瞬移道具（useslot）

> **观测日期**：2026-11-04  
> **观测者**：先聪（任意英雄实测：回城卷轴 / 科勒的匕首 / 原力法杖）  
> **数据目录**：`War3Bot/build/.../data/player_actions/wuxiancong`  
> **关联代码（暂未改判别逻辑）**：`War3Bot/src/matchstatsprovider.cpp`（`actionName` / `orderId` / `isTp`/`isBlink`）  
> **关联协议说明**：[`warcraft-iii-action-ids-and-dota-stats-transmission.md`](./warcraft-iii-action-ids-and-dota-stats-transmission.md)  
> **配套导图**：[`dota-inventory-slot-orders-tp-blink-forcestaff-mindmap.md`](./dota-inventory-slot-orders-tp-blink-forcestaff-mindmap.md)  
> **状态**：仅记录；后续还将补充蓝猫 R、敌法/女王闪烁等；**本轮不改** `matchstatsprovider` 的瞬移识别代码。

---

## 一、两层分类（回答「actionName 下面还有子分类吗？」）

**有。** 当前 UI/归档里至少有两层：

| 层级 | 字段 | 含义 | 示例 |
| :--- | :--- | :--- | :--- |
| **L1 Action ID** | `actionId` / `actionName()` | `game.dll` 动作外壳类型 | `0x11` 地点指令、`0x12` 目标指令、`0x6B` DotA 同步… |
| **L2 Order / Ability** | 归档第 7 列 `orderId` | 具体单位指令或技能 FourCC | `0xD0003` smart、`0xD0028` useslot1、`'A0TY'` 跳刀技能码 |

因此：

- `actionName(0x11)` =「地点指令」只是外壳；
- 真正区分「走路 / 用某格物品瞬移 / 闪烁技能」靠 **`orderId`**（或后续再解物品/技能 rawcode）。

现有 `isTp`/`isBlink` 走的是 **技能 FourCC** 路径（`AItp`/`A0TY`/`A116`…）。  
背包热键使用道具时，引擎更常发 **`useslotN`（0xD0028~0xD002D）**，与 FourCC 路径并行，后续识别需要合并这两条证据链。

---

## 二、实测结论（先聪 2026-11-04）

### 1. 普通移动

| Action | Order | 说明 |
| :--- | :--- | :--- |
| `0x12`（也常见 `0x11`） | `0xD0003`（851971，`smart`） | 右键智能指令 / 普通走位 |

### 2. 物品换装备格子（moveslot）

Action 外壳多为 **`0x12` 目标指令**，Order 为 **`0xD0022` ~ `0xD0027`**：

| Order hex | Decimal | 引擎名 | DotA 热键（观测） | 物品栏格 |
| :--- | ---: | :--- | :--- | :--- |
| `0xD0022` | 852002 | moveslot1 | Num7 | 第 1 格 |
| `0xD0023` | 852003 | moveslot2 | Num8 | 第 2 格 |
| `0xD0024` | 852004 | moveslot3 | Num4 | 第 3 格 |
| `0xD0025` | 852005 | moveslot4 | Num5 | 第 4 格 |
| `0xD0026` | 852006 | moveslot5 | Num1 | 第 5 格 |
| `0xD0027` | 852007 | moveslot6 | Num2 | 第 6 格 |

**语义（引擎）**：把**目标物品**挪到该英雄物品栏的对应槽位（Hive：item-targeted *moveslot*）。  
实测场景：TP / 跳刀 / 推推在背包内换格时出现。

### 3. 物品瞬间移动（useslot + 点地）

Action 外壳为 **`0x11` 地点指令**，Order 为 **`0xD0028` ~ `0xD002D`**：

| Order hex | Decimal | 引擎名 | DotA 热键（观测） | 物品栏格 |
| :--- | ---: | :--- | :--- | :--- |
| `0xD0028` | 852008 | useslot1 | Num7 | 第 1 格 |
| `0xD0029` | 852009 | useslot2 | Num8 | 第 2 格 |
| `0xD002A` | 852010 | useslot3 | Num4 | 第 3 格 |
| `0xD002B` | 852011 | useslot4 | Num5 | 第 4 格 |
| `0xD002C` | 852012 | useslot5 | Num1 | 第 5 格 |
| `0xD002D` | 852013 | useslot6 | Num2 | 第 6 格 |

**语义（引擎）**：使用该槽位上的物品；点地型物品（TP / 跳刀 / 原力法杖）即表现为「瞬间移动」类坐标跳变。

### 4. 一句话总结（与观测者一致）

- **换格**：`0x12` + `0xD0022`…`0xD0027`（moveslot1…6）  
- **用物品瞬移**：`0x11` + `0xD0028`…`0xD002D`（useslot1…6）  
- DotA 键盘布局 `7 8 / 4 5 / 1 2` 对应引擎槽位 `1…6`（不是数字键字面顺序）。

---

## 三、与公开 Order 表交叉验证

来源：

- [Hive — List of Order Ids](https://www.hiveworkshop.com/threads/list-of-order-ids.350361/)
- [Hive — Item Events（moveslot / useslot 说明）](https://www.hiveworkshop.com/threads/item-events.203106/)
- [WarRaft/Order `Order.lua`](https://github.com/WarRaft/Order/blob/master/src/Order.lua)

交叉结果：**完全吻合**。观测中的 Num7→`0xD0022/28` 等，只是 DotA UI 热键标签，底层仍是 slot1…slot6。

相关邻近 Order（便于后续扩展，尚未用本局数据确认）：

| Order | 名 | 备注 |
| :--- | :--- | :--- |
| `0xD0021` | dropitem | 丢弃物品 |
| `0xD000D` | getitem | 走向地面物品 |
| `0xD022D` | blink | 原版闪烁技能 order 字符串（英雄技能走技能码时也可能直接是 ability FourCC） |

---

## 四、War3Bot 识别（2026-11-04 已改）

**已删除** 一切 `AItp` / `A0TY` / `A116` 等 FourCC 猜测。

```text
isItemInstant  ← action∈[0x10,0x15] 且 order ∈ useslot1..6 (0xD0028..0xD002D)
isItemMoveSlot ← action∈[0x10,0x15] 且 order ∈ moveslot1..6 (0xD0022..0xD0027)
isTp / isBlink ← 恒 false（废弃字段，仅兼容）
instantType    ← 1=物品瞬移；2=技能瞬移（尚未启用）
```

单靠 useslot **无法**区分格内是 TP / 跳刀 / 推推；若要细分物品种类，需另绑物品 rawcode。

技能瞬移（敌法/女王/蓝猫 R…）**稍后**单独统计，不走 FourCC 旧表。

---

## 五、待补充数据清单

| 主题 | 预期 Action | 预期 Order | 状态 |
| :--- | :--- | :--- | :--- |
| 蓝猫 R 各段位移 | `0x11`/`0x10`? | 地图技能 order | 待测 → 技能瞬移表 |
| 敌法师 Blink | `0x11` | 待实包 | 待测 → 技能瞬移表 |
| 女王 Blink | `0x11` | 待实包 | 待测 → 技能瞬移表 |
| 推推棒推友/推己 | `0x12`/`0x11` + useslot | 已覆盖为物品瞬移 | 种类细分待绑物品 |

原始动作包请继续落到：  
`D:\Qt\workspace\War3Bot\build\Desktop_Qt_5_15_2_VSCode_MSVC_32bit_Release\data\player_actions\wuxiancong`

---

## 六、可选逆向入口（工具已就绪，本轮未深挖 game.dll）

| 工具 | 路径 | 用途 |
| :--- | :--- | :--- |
| MpqEditor | `D:\Mpqeditor\Win32` | 抽 DotA 地图 ability/item rawcode |
| Ghidra | `D:\Ghidra_12.1.4` | `game.dll` 动作组装 / order 分发 |
| REA | `D:\REA` | 动态跟包 |
| 脚本 | `D:\Qt\workspace\War3Script` | 地图侧 `GetIssuedOrderId` / 物品事件对照 |

公开 Order 全表已覆盖 moveslot/useslot；下一刀优先用 MpqEditor + `War3Script` 把 **DotA 技能/物品 rawcode → 中文名** 表补全，再回写 `matchstatsprovider`。
