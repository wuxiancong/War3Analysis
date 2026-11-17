# DotA 6.83d 视野与绕视野 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图化视野分层与英雄绕视野 AI |
| **命名方式** | `dota-683d-vision-and-fog-juke-mindmap` |
| **分析时间** | 2026-11-17 |

```mermaid
mindmap
  root((视野与绕视野))
    引擎 game.dll
      迷雾栅格
      sight nsight
      树 occH 挡视线
      IsUnitVisible
      雾中攻击暴露
    地图 6.83d
      开局已探索
      友军共享视野
      FogModifier 临时视
      UnitShareVision
      不用 FogEnable
    绕视野操作
      我是否被敌看见
      暴露分数近似
      juke 进树出路
      fog hold 禁攻击
      复用 move unsafe
    合规
      禁止开图读栅格
      不可见不点人
      MVP 不必新挖 dll
```

配套正文：[`dota-683d-vision-and-fog-juke.md`](./dota-683d-vision-and-fog-juke.md)
