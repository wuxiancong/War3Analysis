# DotA 合成成品落格规律 & 臂章切换是否挪位

> **分析日期**：2026-11-07  
> **触发问题**：爪 / 盔 / 手套在 Num7/8/4，合成臂章后本地在 **Num7**，War3Bot 统计却到 **Num5（或错误格）**，后续格序全乱。  
> **地图脚本**：`War3Script/war3map.j`（6.83 系混淆）  
> **对照 Bot**：`War3Bot/src/matchstatsprovider.cpp` `applyInventoryAcquire`  
> **关联**：[`warcraft-iii-1.26-inventory-six-slot-order.md`](./warcraft-iii-1.26-inventory-six-slot-order.md)

---

## 一、结论

| 问题 | 本地客户端规律 | Bot 旧逻辑 | 正确做法 |
| --- | --- | --- | --- |
| 合成落格 | 先删配件，再 `UnitAddItemById` → **最小空槽** = **被消耗配件的最小槽下标** | `matchedSlots.first()`（**配方表组件顺序**的第一件） | `min(matchedSlots)` |
| 臂章开/关 | `A11` 取原槽 + `FD1(..., 同槽)` **原位替换** | 同族 `morphSlot` 原地改 code | 保持原位；勿无依据 swap |

### 臂章物编开/关（地图权威，勿与错误 JSON 名混淆）

| 状态 | 英雄 | 信使 | 地图符号 |
| --- | --- | --- | --- |
| **开启** | `I00M`（及 `I00S`） | `I00N`（及 `I00V`） | `WS0` / `WR0`（挂主动加成技能） |
| **关闭** | `I00Q`（及 `I00T`） | `I00R`（及 `I00W`） | `WT0` / `WP0` |
| 合成默认 | `I00Q` 关闭 | — | `NJO`: `WT0↔WS0` 切换 |

臂章配方（`dota_data` / 地图 `J50..J80→JB0`）：

`I02P 加速手套 + I04E 铁意头盔 + I045 攻击之爪 + I08D 卷轴 → I00Q/WP0 系臂章`

---

## 二、地图证据链（合成）

### 2.1 购入时先尝试合成，成功则不再入包卷轴

`EDO`（约 L15979）：

```jass
if EGO==null or E8O(MDI,EGO,E71(E81))==false or KK==false then
    // 合成失败才 UnitAddItemById 放入新购物品
    set EJ1=UnitAddItemById(EGO,FR0[E81])
```

`E8O` → `DBO`：用 **尚未入包的新物品类型** 作 `DCO[0]`，与当前 6 格一起匹配配方。

### 2.2 匹配成功后的落格：`D9O`

```jass
// 按槽 0..5 删除 FB1 标记的配件
if i0>0 then call EL1(UnitItemInSlot(SWI,0)) ...
// ...
set BA1=UnitAddItemById(SWI,FR0[DAO])  // 成品 → 引擎首个空格
```

引擎 `CAbilityInventory` 自动入格从槽 **0** 扫到 **5**（见 1.26 `0x6F0FD040`）。  
配件删完后，**最小被删槽** 一定是第一个空格 ⇒ 成品落在该槽。

**例（与先聪复现一致）**

| 槽 | 热键 | 合成前 |
| ---: | --- | --- |
| 0 | Num7 | 攻击之爪 |
| 1 | Num8 | 铁意头盔 |
| 2 | Num4 | 加速手套 |
| （pending） | — | 臂章卷轴（未入包） |

→ 删 0/1/2 → `UnitAddItemById(臂章)` → **槽 0 = Num7**。

### 2.3 Bot 旧 bug 为何偏到后面格子

配方组件顺序是 `手套, 头盔, 爪, 卷轴`。  
`matchedSlots` 按该顺序 push ⇒ `[手套槽=2, 盔槽=1, 爪槽=0]`，  
`first()` = **2（Num4）**；若再叠加「合成未识别、卷轴先塞进首空格」等，表现可进一步偏到 **Num5（槽3）**。

---

## 三、臂章切换：保持原位

`NJO`（约 L22818，开关臂章）：

```jass
set FF1=A11(GetTriggerUnit(),GetManipulatedItem())  // 原槽 0..5
call RemoveItem(GetManipulatedItem())
set VK=FD1(GetTriggerUnit(),FR0[WS0或WT0],FF1)     // 强制写回同槽
```

`A11`：扫 `UnitItemInSlot` 找物品所在槽。  
`FD1`：用占位物堵住其它空槽，再 `UnitAddItem`，使新形态**只能进 FF1**。

因此：**切换状态不换格、不占新格**（信使/英雄形态互转 `F3O` 里部分路径用 `UnitAddItemById` 无槽参数，那是另一类 morph，英雄背包内主动开关走 `NJO`/`FD1`）。

Bot 侧：同族 toggle 应只改 `code`、清 `handleId`；仅当模型槽位已错且有权威 `UseSlot` 时才校准，避免盲目 `swap`。

---

## 四、Bot 修正

`matchstatsprovider.cpp`：合成 `targetSlot = min(matchedSlots)`（已改）。  
仿真脚本 `tools/_sim_inv_full.py` 同步。

---

## 五、置信度

| 项 | 等级 |
| --- | --- |
| D9O / UnitAddItemById 落最小空槽 | 高（脚本原文） |
| 臂章 NJO+FD1 原位 | 高 |
| Bot first() 导致偏格 | 高 |
| 用户截图「Num5」是否 100% 仅由 first() 引起（或叠加未合成） | 中（first()→Num4；Num5 更像未合成先入槽3） |
