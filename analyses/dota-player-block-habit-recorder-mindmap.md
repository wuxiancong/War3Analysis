# 真人卡兵习惯采集 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图化真人卡兵教师数据流 |
| **命名方式** | `dota-player-block-habit-recorder-mindmap` |
| **分析时间** | 2026-11-18 |

```mermaid
mindmap
  root((卡兵习惯))
    今日可做
      run block 1 基线
      run block 3 人卡
      日志 📍 50ms 与打分
    缺口
      JSONL 落盘
      跨局画像
      注入 AI 参数
    记什么
      heroAhead
      heroLateral
      stopMs
      delay success
    落盘
      block_habits player
      sessions jsonl
      global json
    AI用
      stickGap
      stop 分布
      斜前方站位
```

配套正文：[`dota-player-block-habit-recorder.md`](./dota-player-block-habit-recorder.md)
