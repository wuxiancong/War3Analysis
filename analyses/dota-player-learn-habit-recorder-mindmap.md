# 玩家加点习惯记录器 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图化学习序列抽取与跨局画像 |
| **命名方式** | `dota-player-learn-habit-recorder-mindmap` |
| **分析时间** | 2026-11-16 |

```mermaid
mindmap
  root((加点习惯记录器))
    结论
      不必挖 dll
      复用 match dat
      抽学习序列再聚合
    单局
      0x10 FourCC 学习
      0x66 开菜单
      Level 同步定等级
      learn json 旁车
    跨局
      player plus hero
      preferredSlotSequence
      levelAnchors
      confidence
    落点
      War3Bot 主库
      与 skillTimeline 同源
      供 AI learn 消费
    不做
      改地图上报
      MVP 出装施法习惯
```

配套正文：[`dota-player-learn-habit-recorder.md`](./dota-player-learn-habit-recorder.md)
