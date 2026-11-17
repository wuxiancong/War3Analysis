# DotA1 英雄使用技能流程 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图化施法链路与 AI 注入要点 |
| **命名方式** | `dota-hero-ability-cast-flow-mindmap` |
| **分析时间** | 2026-11-16 |

```mermaid
mindmap
  root((使用技能))
    结论
      0x10 无目标
      0x11 点地
      0x12 单位目标
      Id 是 OrderId 非学习 FourCC
      不必新挖 dll 施法函数
    人手路径
      选中英雄
      热键或点命令卡
      瞄准态本地无包
      ESC 0x61 取消
    与加点区分
      加点 0x66 加 FourCC
      施法 OrderId 0xDxxxx
    引擎与地图
      Action 全端模拟
      SPELL 事件读 FourCC
      IssueOrder 仅脚本侧
    AI
      主名 cast
      加点用 learn
      复用 Enqueue
      aiOrderImmediate 已有
      aiOrderTarget 已有
      点地补 0x11 helper
      需 Order 与目标类型表
    勿混
      skill 不作施法名
      useslot 是物品
      被动不发包
```

配套正文：[`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md)
