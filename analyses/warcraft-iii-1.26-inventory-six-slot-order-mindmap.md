# Warcraft III 1.26 物品栏 6 格顺序 — 思维导图

详细论证见：[`warcraft-iii-1.26-inventory-six-slot-order.md`](./warcraft-iii-1.26-inventory-six-slot-order.md)

---

## 一、数据归属

```mermaid
mindmap
  root((物品栏顺序))
    引擎真相
      CAbilityInventory
      unit加0x1F8
      slots加0x70
      步长12字节
      句柄对空为-1
    UI显示
      CInventoryBar
      slotCount加0x12C
      boundKey热键
      DotA Num784512
    网络录像
      moveslot目标槽
      物品句柄
      无源槽字段
```

---

## 二、顺序如何改变

```mermaid
flowchart TD
  A[买/捡自动入包] --> B[0x6F0FD040 从槽0找空位]
  B --> C[写入 slots i]
  D[脚本强制槽] --> E[PlaceItemAtSlot 0x6F0F8C10]
  F[玩家拖拽] --> G["Action0x12 + moveslot dst"]
  G --> H[0x6F0F1810]
  H --> I[句柄反查源槽]
  I --> J[两槽句柄对调]
  K[useslot] --> L[用该格物品]
  L -.->|通常不改顺序| C
```

---

## 三、与「源格未决」

```mermaid
flowchart LR
  P[录像只有 dst+handle] --> Q{模型已绑 handle?}
  Q -->|是| R[唯一源格 可同步]
  Q -->|否| S{未绑定候选数}
  S -->|1| T[推导并绑定]
  S -->|大于1| U[源格未决 跳过]
```
