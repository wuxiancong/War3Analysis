# Dota1 天梯积分系统与分布式多服务架构 — 思维导图与全景拓扑

本文档提供 Dota1 天梯积分体系、分布式结算流水与安全防护架构的 Mermaid 思维导图、网络拓扑图以及时序交互图。

详细设计原理与技术白皮书见：[`dota1-ladder-system-and-multi-service-architecture.md`](./dota1-ladder-system-and-multi-service-architecture.md)

---

## 一、 全景技术思维导图

```mermaid
mindmap
  root((Dota1 天梯积分与多服务系统))
    天梯算法模型
      Elo 基础分
        胜率期望 EA/EB
        团队均分加权
      动态 K 因子
        低分段快速收敛 K=36
        中分黄金段 K=30
        高分巅峰段 K=18~22
      表现分 Performance Bonus
        KDA 加权权重
        参团率 KP 收益
        正补/反补/经济转化
      特殊赏罚机制
        全场 MVP +3分额外奖励
        败方 SVP 35%掉分减免
        强退/逃跑秒退 -45分严惩并清空连胜
    等级与称号并存体系
      等级代码 (数据库/通信/匹配)
        ["-", "D", "C", "B", "A", "S", "SS", "SSS"]
        8阶单字符或短代码，易于SQL索引与网络封包
      段位中文称号 (UI展示/成就)
        见习新手 (-)
        青铜守护 (D)
        白银先锋 (C)
        黄金勇士 (B)
        铂金统领 (A)
        璀璨钻石 (S)
        超凡大师 (SS)
        最强王者 (SSS)
      分数线映射
        0 / 1000 / 3000 / 5000 / 7000 / 9000 / 11000 / 13000
    分布式多服务架构
      War3Bot (分布式主机/匹配服务)
        MatchManager: 搜索半径动态扩张 (±50 到 ±400)
        MatchManager: 蛇形排队配平两队均分 (1/2-2/2-2/1)
        Client: 监听 0x6B (Winner=1/2, 1..9战绩数据)
        Client: 赛后自动生成 zlib 压缩动作流 .dat 归档
      War3Launcher (客户端启动器)
        RoomManager: Q_ENUM(LadderRankLevel) 暴露 QML
        RoomComponent: 数据库代码与中文称号并存展示
        NetworkManager: 接收 S_C_MATCH_RESULT (0x31) 战报包
      War3Angular (Web API 与微服务中枢)
        Express + SSR 高并发网关
        MySQL 连接池与单事务 ACID 落库
        Angular 前端 LadderService 响应式数据流
    全链路安全防护机制
      身份特权鉴权
        HMAC-SHA256 双向数字签名
        BOT_SECRET_KEY 服务间私钥校验
        常量时间对比 crypto.timingSafeEqual
      反重放攻击 Replay Defense
        X-Bot-Timestamp ±60秒时钟漂移拦截
        X-Bot-Nonce 32位随机唯一凭证
        5分钟内存滑动黑名单容器
      战绩真实性审计
        3分钟最低时长校验 (防秒开秒退)
        人头数守恒定理 (近卫击杀 == 天灾死亡)
        极端异常值与负数注入过滤
      幂等性与事务原子性
        matchId 唯一约束防重复入库
        MySQL 开启单事务多表联动提交
```

---

## 二、 系统架构全景拓扑图

```mermaid
flowchart TB
    subgraph ClientCluster["客户端层 (Players)"]
        WL1["War3Launcher 玩家1<br/>QML 界面 + 房间管理"]
        WL2["War3Launcher 玩家2"]
        WLN["War3Launcher 玩家 N"]
        W3G["魔兽争霸 III 游戏进程<br/>(DotA v6.83d)"]
    end

    subgraph BotHostCluster["对战主机与匹配集群 (War3Bot C++)"]
        MM["MatchManager<br/>动态半径寻敌 / 蛇形平衡配队"]
        CLIENT["Client (Game Host)<br/>W3GS 协议栈 / 锁步同步"]
        STATS_PROV["0x6B 数据流解析器<br/>(KDA / 正反补 / 胜负Winner)"]
        SCORE_ENG["LadderScoreEngine (C++)<br/>Elo胜率期望 / 动态K值 / 表现分"]
        BOT_DB["DbManager (本地QtSql)"]
        DAT_STORE[("本地动作流归档<br/>data/player_actions/*.dat")]
    end

    subgraph WebApiCluster["Web API 与数据中枢 (War3Angular Node.js / Express)"]
        SEC_GATE["安全网关 (Security Middleware)<br/>HMAC-SHA256 验签 / Nonce防重放 / 频控"]
        LADDER_SVC["LadderService (TypeScript)<br/>战绩防伪审计 / 幂等落库 / 榜单计算"]
        ANGULAR_FRONT["Angular 21 前端 SPA<br/>天梯排行榜 / 个人战报 / 3D轨迹复盘"]
    end

    subgraph StorageCluster["持久化存储层 (MySQL & Object Storage)"]
        MYSQL[("MySQL 8.0 核心业务库 (pvpgn)<br/>ladder_stats: 玩家积分/胜负/段位<br/>matches: 对局流水<br/>match_results: 10人详细战绩")]
    end

    WL1 -- CSMatchEnqueuePacket (发起匹配) --> MM
    MM -- SCMatchAssignPacket (下发进房) --> WL1
    W3G -- W3GS_OUTGOING_ACTION (0x26 / 0x6B) --> CLIENT
    CLIENT --> STATS_PROV
    STATS_PROV --> SCORE_ENG
    CLIENT --> DAT_STORE
    SCORE_ENG --> BOT_DB
    BOT_DB -. 直连同步 .-> MYSQL

    CLIENT -- "特权安全上传 (POST /api/ladder/settle)<br/>X-Bot-Timestamp / Nonce / Signature" --> SEC_GATE
    SEC_GATE --> LADDER_SVC
    LADDER_SVC -- 单事务原子写入 --> MYSQL

    WL1 -- "HTTP API 查询 (GET /api/ladder/profile)" --> SEC_GATE
    ANGULAR_FRONT -- "HTTP API 查询 (GET /api/ladder/leaderboard)" --> SEC_GATE
    SEC_GATE --> LADDER_SVC
    LADDER_SVC -- 异步查询 --> MYSQL
```

---

## 三、 游戏生命周期与天梯结算时序图

```mermaid
sequenceDiagram
    autonumber
    participant Game as DotA 游戏 (JASS)
    participant Bot as War3Bot 房间主机
    participant Launcher as War3Launcher 客户端
    participant Angular as War3Angular 安全网关
    participant DB as MySQL 数据库

    Note over Game,Launcher: 1. 游戏对局中实时数据同步
    loop 游戏进行中 (每当击杀/助攻/补刀/买装)
        Game->>Bot: 0x6B SyncStoredInteger (spid: 1..9, Key/Value)
        Bot->>Bot: Client::updateDotaLiveSyncData 聚合 10 名玩家战绩
    end

    Note over Game,Launcher: 2. 终局胜负触发与结算
    Game->>Bot: 0x6B StoreInteger("Global", "Winner", 1) (近卫胜利)
    Bot->>Bot: 1. saveAllPlayerMatchLogs() 压缩归档 match_*.dat
    Bot->>Bot: 2. 收集 10 名玩家当前分，调用 LadderScoreEngine
    Bot->>Bot: 3. 计算 ΔScore、新积分、MVP/SVP 称号

    par 路径 A：Bot 本地持久化与客户端通知
        Bot->>DB: DbManager::applyMatchSettlement (本地事务提交)
        Bot->>Launcher: S_C_MATCH_RESULT (0x31) TCP 广播战报
        Launcher->>Launcher: 弹出结算卡片、段位加分动画
    and 路径 B：通过 Web API 特权安全上传
        Bot->>Bot: 构造签名：HMAC_SHA256(ts + nonce + matchId + body, BOT_KEY)
        Bot->>Angular: POST /api/ladder/settle (携带 X-Bot-*)
        Angular->>Angular: verifyBotSignature (防重放/时钟差/签名校验)
        Angular->>Angular: validateMatchIntegrity (人头守恒/最低时长审计)
        Angular->>DB: 幂等性检测 + 开启事务写入 matches / match_results / ladder_stats
        DB-->>Angular: 事务提交成功
        Angular-->>Bot: 200 OK (settled: true)
    end

    Note over Launcher,Angular: 3. 玩家赛后或大厅查询天梯档案
    Launcher->>Angular: GET /api/ladder/profile?user=wuxiancong
    Angular->>DB: SELECT * FROM ladder_stats WHERE userName = ?
    DB-->>Angular: 返回 score, rank_level, winRate, kda...
    Angular-->>Launcher: 200 OK (展示段位称号 "黄金勇士 (B)", 积分 5240)
```

