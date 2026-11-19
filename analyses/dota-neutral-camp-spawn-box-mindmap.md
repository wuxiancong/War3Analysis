# 野点封野 AABB — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图化封野盒 vs 仇恨圆 vs UI |
| **命名方式** | `dota-neutral-camp-spawn-box-mindmap` |
| **分析时间** | 2026-11-19 |

```mermaid
mindmap
  root((封野区域))
    结论
      轴对齐矩形
      非视野非圆
      不必挖 dll
    脚本
      P3O 每分钟
      EnumUnitsInRect r1
      空则刷 r2 中心
      首波 0:30
    区分
      封野盒 r1
      出生点 r2
      GuardDistance 600
    UI
      线框长方体
      campboxes 命令
      XY 真 Z 显示
    AI
      blockcamp 插盒内
      stack 拉出盒外
```

配套正文：[`dota-neutral-camp-spawn-box.md`](./dota-neutral-camp-spawn-box.md)
