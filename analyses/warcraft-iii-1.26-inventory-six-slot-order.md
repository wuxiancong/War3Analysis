# Warcraft III 1.26：本地客户端如何设定物品栏 6 格顺序

> **分析日期**：2026-11-07  
> **问题**：魔兽本地客户端如何维护英雄物品栏 6 格的物品顺序？换格（拖拽）时引擎侧发生了什么？为何录像复盘会出现「源格未决」？  
> **目标版本**：Warcraft III 1.26.0.6401  
> **目标文件**：`game.dll`（12,042,240 字节）  
> **SHA-256**：`6D21BD9A0F9FBC8446F455C9E89AC994FED68174426FE608FCB9BAEFD4DEC53C`  
> **来源**：`War3Launcher/versions/1.26.0.6401/game.dll`  
> **分析副本**：`C:\War3Analysis\samples\1.26.0.6401\game.dll`（固定 NTFS；哈希一致）  
> **工具**：Capstone 静态反汇编 + 字符串/常量扫描；既有 UI 分析见 War3Bot `details/1.26/GameDll_360CD0_*.md`  
> **产物**：`War3Analysis/artifacts/inventory-slot-order/`  
> **关联**：[`dota-inventory-slot-orders-tp-blink-forcestaff.md`](./dota-inventory-slot-orders-tp-blink-forcestaff.md)、War3Bot `matchstatsprovider.cpp` moveslot 启发式  
> **配套导图**：[`warcraft-iii-1.26-inventory-six-slot-order-mindmap.md`](./warcraft-iii-1.26-inventory-six-slot-order-mindmap.md)  
> **置信度**：槽位数组布局 / 自动入格 / moveslot 换格路径：**高**（静态反汇编直接读出）；UI `CInventoryBar` 与能力对象同步细节：**中**（有源文件路径字符串与既有按键分析，本轮未跟完整 UI 刷新链）；1.27 偏移是否逐字节相同：**未核**（机制应同构）

---

## 一、结论摘要

本地客户端**不是**用「热键 7/8/4/5/1/2」直接当数组下标，而是：

1. 单位挂载 **`CAbilityInventory`** 能力；真正的 6 格顺序是该对象上的**固定槽位数组**。  
2. 槽位索引 **0..N-1**（英雄通常 N=6），每槽 **12 字节**，基址 **`ability + 0x70`**；槽内主要存物品的 **Agent 句柄对**（空槽为 `FFFFFFFF/FFFFFFFF`）。  
3. **拾取/购买自动入包**：从槽 0 起顺序找第一个空槽放入 → 引擎顺序固定为 slot0→slot5。  
4. **玩家拖拽换格**：发出 `moveslot1..6`（`0xD0022..0xD0027`）；包内带**目标物品句柄 + 目标槽**，**不带源槽**。引擎在能力对象上**反查句柄所在源槽**，再与目标槽对调。  
5. DotA 的 Num7/8/4/5/1/2 只是 **UI/快捷键标签**（`CInventoryBar` / 物品 UI `boundKey`），映射到引擎 slot1..6；**不改变**底层数组下标语义。  
6. 录像复盘若尚未绑定句柄且多格候选歧义，就无法唯一确定源格 → War3Bot 的「源格未决，已跳过」是**正确的保守行为**，不是爪/盔「不能交换」。

---

## 二、对象与字段（1.26）

| 对象 | 关键偏移 / 地址 | 含义 |
| --- | --- | --- |
| `unit + 0x1F8` | 指针 | 指向该单位的 `CAbilityInventory`（为空则无物品栏） |
| `CAbilityInventory + 0x6C` | `uint` | 槽位容量上限之一（与物编容量取 min） |
| `CAbilityInventory + 0x70` | `Slot[N]` | 槽位数组起点 |
| 每槽步长 | `0x0C`（12） | `slot_ptr = base + index * 12` |
| 每槽句柄 | `+0x00 / +0x04` | AgentId 低/高；`and == -1` 视为空 |
| ImageBase | `0x6F000000` | `.text` 文件偏移 ≈ RVA（本样本 RAW==VA） |

类名字符串：`CAbilityInventory` @ VA `0x6F8B4D58`；UI：`UI/CInventoryBar.cpp`、`.?AVCInventoryBar@@`。

容量读取 `0x6F0E4050`（`UnitInventorySize` 最终落到此）：

```text
size = min( GetAbilityDataCapacity(this+0x50), *(this+0x6C) )
```

按槽取物 `0x6F0F0F00`（`UnitItemInSlot` → `unit+0x1F8` → 本函数）：

```c
// VA 0x6F0F0F00  CAbilityInventory::GetItemInSlot(slotIndex)
uint n = GetInventorySize(this);          // 0x6F0E4050
if (slotIndex >= n) return nullptr;
AgentHandle* p = &this->slots[slotIndex]; // this+0x70 + slot*12
if ((p->a & p->b) == 0xFFFFFFFF) return nullptr;
return ResolveAgent(p);                   // 0x6F4786B0
```

JASS 入口对照：

| Native | 注册 VA（impl） |
| --- | --- |
| `UnitItemInSlot` | `0x6F3C7730` → `0x6F26EC20` → `0x6F0F0F00` |
| `UnitInventorySize` | `0x6F3C8F00` → `0x6F26EC60` → `0x6F0E4050` |
| `UnitAddItem` | `0x6F3C73F0` |
| `UnitAddItemToSlotById` | `0x6F3C75B0`（强制槽） |
| `UnitDropItemSlot` | `0x6F3C9010`（发 `0xD0021` dropitem 一类指令） |

---

## 三、顺序是如何被「设定」的

### 3.1 自动入格（买/捡，未指定槽）

`0x6F0FD040`（由 `Unit` 加物品路径 `0x6F282D30` 在非特殊分支调用）：

```c
n = GetInventorySize(inv);
for (i = 0; i < n; ++i) {
    Slot* s = &inv->slots[i];           // +0x70, 步长 0x0C
    if (empty_or_dangling(s)) {
        if (PlaceItemAtSlot(inv, item, i)) return true;  // 0x6F0F8C10
    }
}
return false; // Inventoryfull
```

**结论**：默认顺序 = **第一个空的引擎槽**（0 优先于 1…5）。  
玩家看到的「左上 / 右上 / …」由 UI 把 slot0..5 画到 2×3 格子；DotA 再给格子贴 Num 热键，**不改数组次序**。

### 3.2 强制入格（脚本 `UnitAddItemToSlotById` 等）

走 `0x6F282D90` → `0x6F0F8C10(PlaceItemAtSlot)`：校验 `slot < size` 且目标槽当前为空，再写入句柄并做附着/事件。

### 3.3 玩家拖拽换格（设定「顺序」的主路径）

#### 指令形态（与既有录像分析一致）

| Order | 名 | 槽 |
| --- | --- | ---: |
| `0xD0022`..`0xD0027` | moveslot1..6 | 目标槽 0..5 |
| `0xD0028`..`0xD002D` | useslot1..6 | 使用槽 0..5 |
| `0xD0021` | dropitem | 丢弃/交接 |

常见外壳：`Action 0x12` + moveslot + **target = 被拖物品句柄**。

#### 分发

`0x6F1026D0`：若 `order ∈ [0xD0022, 0xD0027]` → `call 0x6F0F1810`。

#### 换格核心 `0x6F0F1810`

伪代码还原：

```c
// this = CAbilityInventory* (ebp)
Order* o = ...;
int dst = o->orderId - 0xD0022;          // 目标槽 0..5
Item* target = ResolveFromOrderTarget(o);
int n = GetInventorySize(this);
if (!target || dst >= n) return;

// 1) 在 0..n-1 中反查：哪个槽的句柄 == target
int src = FindSlotOfItem(this, target);  // 倒序扫 slots[]
if (src >= n || src == dst) return;

// 2) 读出原 dst 槽物品（可为空）
Item* displaced = GetItemInSlot(this, dst); // 经 SlotRead 0x6F021A00

// 3) 对调句柄
WriteSlotHandle(&slots[dst], target);     // 0x6F0419C0
NotifyItemMoved(target, /*slot*/ dst);   // 0x6F2B61D0
WriteSlotHandle(&slots[src], displaced);
if (displaced) NotifyItemMoved(displaced, src);

// 4) 刷新拥有者相关状态（0x6F3329B0 / 0x6F021270 等）
```

要点：

- **顺序变更 = 两个槽位上的 Agent 句柄互换**（或移到空槽）。  
- **源槽不在网络包里**，只靠「句柄 ∈ 哪一格」本地推出。  
- 若 dst 原有物品，则是真正的 **swap**；若为空，则是 **move**。

句柄写入 `0x6F0419C0`：从物品对象取 `(+0x14,+0x18)` 写入槽的两 dword；失败则写 `FFFFFFFF`。

### 3.4 使用某格（useslot）——不改顺序，但声明「该格是谁」

`useslot` 把 `orderId - 0xD0028` 当作槽下标去用该格物品。  
moveslot 路径里甚至有防护：若某物品正在以 useslot 指向 dst/src，则中止换格（`cmp eax,0xD0028..D002D` 一段，VA `0x6F0F1951`），避免使用中途槽位错乱。

---

## 四、UI 层（显示顺序 / 热键）≠ 引擎数组

既有分析（War3Bot `GameDll_360CD0_GameUI_Inventory_Slot_Inventory_Bar.md`）：

- `CInventoryBar`：`slotCount @ +0x12C`，槽数组 `@ +0x130`（每项 8 字节指针结构）。  
- 按键：遍历槽上物品的 UI 数据，`boundKey @ UI+0x5AC` 与虚拟键比较——**按键跟物品 UI 绑定，不是写死「第 1 格=小键盘 7」**。

因此：

| 层级 | 「第 1 格」含义 |
| --- | --- |
| 引擎 / JASS `UnitItemInSlot(u,0)` | `CAbilityInventory.slots[0]` |
| DotA 热键 Num7 | 通常绑定到引擎 slot1（索引 0）的**显示与快捷键** |
| 录像 `moveslot1 (0xD0022)` | 目标为引擎槽 0 |

改键改的是 UI `boundKey` 或模拟按键，**不会**重排 `slots[]`；只有 moveslot / 脚本强制入格 / 自动入格会改数组顺序。

---

## 五、与 War3Bot「源格未决」的对应关系

| 引擎真实行为 | 录像里能看见的 | 复盘难点 |
| --- | --- | --- |
| 用物品句柄在 `slots[]` 里找源格 | 只有 dst=`order-0xD0022` + targetHandle | 若统计模型从未把 handle 绑到某格，且多格都「可能」，则无法唯一还原 |
| 首次拖某件被动装（爪/盔） | handle 第一次出现 | 与「刚买入的未绑定格」冲突 → 多候选 |
| 主动 UseSlot | 明确声明某格有某类物品 | 被动装几乎不发 useslot，缺少校准信号 |

故：**客户端本地始终知道顺序**（内存数组）；**旁路复盘**在缺句柄绑定时会 squawk「源格未决」——这是信息不足，不是引擎禁止爪↔盔交换。

---

## 六、方法与证据边界

1. 样本拷到 `C:\War3Analysis\samples\1.26.0.6401\`，SHA-256 与 `War3Launcher/versions/1.26.0.6401/game.dll` 一致。  
2. 用常量 `0xD0022/27/28/2D` 定位分发与 handler；用 `UnitItemInSlot` / `CAbilityInventory` 字符串锚定 JASS→能力路径。  
3. Capstone 反汇编产出见 `artifacts/inventory-slot-order/disasm_*.txt` 与辅助脚本 `_disasm_*.py`。  
4. **本轮未做**：Ghidra 工程入库标注、1.27 同函数偏移对照、运行时 CE 读英雄 `+0x1F8` 槽数组实机验证、完整 `CInventoryBar` 刷新调用链。  
5. REA CLI 本轮因启动超时未深入；结论不依赖 REA。

---

## 七、对后续工程的直接启示

1. **复盘换格**：优先建立 `handleId → slot`（首次成功 moveslot 绑定后保留）；被动装可在**购买后唯一空位**时预绑。  
2. **不要**用 DotA 热键数字当数组下标；统一 `engineSlot = order - 0xD0022`（0-based）。  
3. 若要「权威快照」，局末 `0x6B` 的 `8_0..8_5` 是脚本读 `UnitItemInSlot` 的结果，与引擎数组一致（见 action-ids 分析文）。

---

## 八、关键地址速查（1.26.0.6401）

| 符号（自拟） | VA |
| --- | --- |
| Order 分发（含 moveslot 范围） | `0x6F1026D0` |
| moveslot handler | `0x6F0F1810` |
| GetInventorySize | `0x6F0E4050` |
| GetItemInSlot | `0x6F0F0F00` |
| FindSlotOfItem（自高向低） | `0x6F0F0F40` |
| AutoPlace first-empty | `0x6F0FD040` |
| PlaceItemAtSlot | `0x6F0F8C10` |
| WriteSlotHandle | `0x6F0419C0` |
| ResolveAgentHandle | `0x6F4786B0` |
| unit → inventory ability | `unit+0x1F8` |
| slots base / stride / cap field | `+0x70` / `0x0C` / `+0x6C` |
