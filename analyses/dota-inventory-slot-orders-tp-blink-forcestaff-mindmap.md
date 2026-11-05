# DotA 物品栏 moveslot / useslot — 思维导图

详细论证见：[`dota-inventory-slot-orders-tp-blink-forcestaff.md`](./dota-inventory-slot-orders-tp-blink-forcestaff.md)

---

## 一、分类层级

```mermaid
mindmap
  root((玩家动作包))
    L1 ActionID
      0x11 地点指令
      0x12 目标指令
      0x10 无目标
      0x6B DotA同步
    L2 OrderId
      0xD0003 smart 走路
      moveslot 换格
        D0022..D0027
        对应槽1..6
        DotA热键 7 8 4 5 1 2
      useslot 用物品
        D0028..D002D
        点地=瞬移类
        TP 跳刀 推推
      技能FourCC
        AItp A0TY A116
        A00H A002 闪烁
```

---

## 二、实测映射

```mermaid
flowchart LR
  subgraph move [普通移动]
    A12["0x12/0x11"] --> S["0xD0003 smart"]
  end
  subgraph swap [换装备格]
    B12["0x12 目标"] --> M1["D0022..D0027 moveslot"]
    M1 --> Hot["Num7/8/4/5/1/2"]
  end
  subgraph use [物品瞬移]
    C11["0x11 地点"] --> U1["D0028..D002D useslot"]
    U1 --> Items["TP / 跳刀 / 推推"]
  end
```

---

## 三、当前识别（已删 FourCC）

```mermaid
flowchart TD
  pkt[归档 orderId] --> slot{useslot/moveslot?}
  slot -->|useslot D0028..D002D| item[isItemInstant]
  slot -->|moveslot D0022..D0027| move[isItemMoveSlot]
  slot -->|其它| later[技能瞬移稍后统计]
  fourcc[AItp/A0TY 等] -.->|已删除| x[不再使用]
```
