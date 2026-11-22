# DotA 6.83d 出兵点 / 路点 / 时序 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图索引 `dota-lane-spawn-waypoints` |
| **命名方式** | `dota-lane-spawn-waypoints-mindmap` |
| **分析时间** | 2026-11-21 |
| **正文** | [`dota-lane-spawn-waypoints.md`](./dota-lane-spawn-waypoints.md) |

```mermaid
mindmap
  root((六路出兵与路点))
    出兵点
      近战_GetRectCenter
        近卫 B4/C4/A4
        天灾 N3/M3/L3
      远程攻城
        近卫 R3/P3/T3
        天灾 I4/U3/Q3
      非兵营中点
        kAiLanes偏差
    路点链
      SSO_I2等级
        2顶_CI
        3中_BI
        4下_DI
      EnterRegion重发attack
        handoff_TA_SA_NA
      CL2近O2改基地
        U0_II
      卡兵折线
        spawn_handoff_T2_T1
    时序
      号角_倒计时小于12
      第一波_GameStart_0
      间隔30s_ZG
      第7波攻城
      NI_SI成长
      UG_450升级
      无持久预放兵
    卡兵建议
      折线投影
      waitSpot加350
      认波用spawn中心
```

## 速查

- 近卫上路刷点：(-6160,-4064) / (-6192,-4304)，不是 (-6368,-4480)
- 第一波 = GameStart，约号角 +12s
- 每路常态 4 兵，每 7 波 5 兵（+车）
- 头文件：`artifacts/lane-spawn/DotaLaneWaypoints.h`
