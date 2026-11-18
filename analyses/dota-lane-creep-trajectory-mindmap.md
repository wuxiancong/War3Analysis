# 兵线轨迹与卡兵前置 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图化 30s 出兵、路点与轨迹采集 |
| **命名方式** | `dota-lane-creep-trajectory-mindmap` |
| **分析时间** | 2026-11-18 |

```mermaid
mindmap
  root((兵线轨迹))
    结论
      脚本决定路点
      MVP 不必挖 dll
      首波用 CreateUnit 校准
    出兵
      ZG 每 30 秒 SPO
      首波立刻 Execute
      第 7 波攻城车
    行军
      SSO 标记分路
      attack 到 O2 lane
      进区改下一站
      前 7 分速度修正
    采集
      g_aiFirstWaveTick
      领头兵采样 xy
      静态路点 dump
      lane_traces 可选
    卡兵后续
      波次时钟
      挡在 lead 前方
      move hold
```

配套正文：[`dota-lane-creep-trajectory.md`](./dota-lane-creep-trajectory.md)
