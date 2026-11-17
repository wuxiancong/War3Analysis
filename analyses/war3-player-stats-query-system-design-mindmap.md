# War3 战绩查询系统 — 思维导图

> 配套正文：[`war3-player-stats-query-system-design.md`](./war3-player-stats-query-system-design.md)  
> 分析模型：Composer · 目的：战绩产品 + 安全架构 · 时间：2026-11-17

```mermaid
mindmap
  root((战绩查询系统))
    产品面
      基础统计
        积分_段位_排名
        胜率_KDA_GPM
        MVP_连胜_逃跑
        时长_场次
      认证与素质
        手机绑定
        满168小时
        无作弊记录
        已认证_部分_未认证
      明细模块
        胜率趋势
        最佳英雄
        最近对局
        模式分布
        排行榜
      入口
        战绩Tab自己
        房间右键
        槽位战绩行单击
        好友列表
    数据面
      ladder_stats
      match_results
      player_hero_stats
      player_mode_stats
      users认证字段
    客户端
      War3Launcher
        RoomManager签名请求
        StatsComponent数据驱动
        原生HTTP无CORS
      War3Angular
        去Mock接真API
        路由stats_user
        Bearer拦截器
      War3Bot
        HMAC结算写入
    安全面
      登录会话票
      请求签名_HMAC
      CORS白名单
      权限矩阵
        未登录拒绝
        未认证仅自己与摘要
        已认证可查他人
      反爬
        限流
        Nonce防重放
        UA弱校验
        枚举防护
    进阶改造
      统一Node与PHP鉴权
      user_status去掉星号CORS
      matches补个人KDA
      物化全球排名
      短期ClientToken
```

## 权限矩阵（简图）

```mermaid
flowchart LR
  A[请求者] --> B{已登录?}
  B -->|否| Z[401]
  B -->|是| C{查自己?}
  C -->|是| F[完整档案]
  C -->|否| D{已认证?}
  D -->|否| E[仅摘要或403]
  D -->|是| G{限流通过?}
  G -->|是| F
  G -->|否| H[429]
```

## 跳转与拉数（简图）

```mermaid
sequenceDiagram
  participant UI as Room/Friend UI
  participant RM as RoomManager
  participant Main as mainWindow
  participant API as player_stats.php
  participant ST as StatsComponent

  UI->>RM: viewPlayerStats(name)
  RM->>Main: viewPlayerStatsRequested
  Main->>Main: switchToTab(0)
  RM->>API: GET sign(t,user)
  API-->>RM: ladder+heroes+modes
  RM->>ST: detailedPlayerStatsChanged
  ST->>ST: applyDetailedStats
```

## 分层防护（简图）

```mermaid
flowchart TB
  subgraph Edge
    TLS[TLS]
    WAF[WAF/IP限流]
  end
  subgraph Auth
    Bearer[Bearer Session]
    Sign[请求签名]
    CORS[CORS白名单]
  end
  subgraph Authz
    Self[本人完整]
    Peer[他人需认证]
    Room[房间摘要限12人]
  end
  subgraph Data
    Public[公开摘要]
    Full[完整档案]
    Secret[敏感字段永不返回]
  end
  TLS --> WAF --> Bearer --> Sign --> CORS --> Authz
  Authz --> Public
  Authz --> Full
  Full -.-> Secret
```
