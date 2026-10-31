# 魔兽争霸 III 动作体系与 DotA 战绩传输 — 思维导图与架构图

本文档用 Mermaid 展现魔兽争霸 III 底层网络动作（Action IDs）体系，以及 DotA 游戏战绩从 JASS 脚本通过 `game.dll` `0x6B` 封包流向 `War3Bot` 服务器的全链路结构。

详细论证与汇编证据见：[`warcraft-iii-action-ids-and-dota-stats-transmission.md`](./warcraft-iii-action-ids-and-dota-stats-transmission.md)

---

## 一、 全景思维导图

```mermaid
mindmap
  root((魔兽3 动作与DotA战绩))
    动作体系归属
      100% 在 game.dll
        CNetData 锁步网络帧
        W3GS_OUTGOING_ACTION 0x26
        Jump Table 跳转表解析
      脚本仅负责触发
        JASS Native 函数调用
        game.dll 序列化入队
    Action ID 分类
      单位与物品操作 APM
        0x10 无目标停止/技能 14B
        0x11 点目标移动/A地 22B
        0x12 单位目标施法/攻击 30B
        0x13 转移丢弃物品 38B
        0x14 双目标技能 42B
      选择与编队
        0x16 框选/加选 变长
        0x17 设置编队 变长
        0x18 双击/切编队 2B
        0x19 TAB子编队 12B
        0x1B 拾取物品 9B
      界面与控制
        0x01/0x02 暂停/恢复 0B
        0x21 按ESC键 0B
        0x29 小地图信号 12B
      同步与通信
        0x60 游戏内聊天 变长
        0x6B GameCache 同步 变长
    DotA 战绩传输机制
      触发时机
        基地爆炸
        war3map_3.j 行 7210
        裁判/主机广播
      数据通道 0x6B
        game.dll 0x6F44154A
        CacheName dr.x
        MissionKey 槽位或Global
        Key 战绩指标
        Value 4字节整数
      数据项映射
        Key 1: Kills 杀敌
        Key 2: Deaths 死亡
        Key 3: CS 正补
        Key 4: Denies 反补
        Key 5: Assists 助攻
        Key 6: Gold 剩余金钱
        Key 8_0到8_5: 六格物品ID
        Key 9: 英雄ID
        Global Winner: 1近卫 2天灾
        Global m/s: 比赛时长
    War3Bot 统计实现
      流式解析步进
        区分 ActionId
        安全跳跃已处理长度
      微秒级开销
        单包解析 < 1μs
        完全免跑魔兽3客户端
      反作弊公信力
        权威数据源
        防客户端本地伪造
```

---

## 二、 战绩数据端到端数据流转图

```mermaid
sequenceDiagram
    autonumber
    participant DotA as DotA 地图脚本 (war3map_3.j)
    participant GameDLL as 魔兽引擎 (game.dll)
    participant War3Bot as 虚拟主机 (War3Bot / client.cpp)
    participant Server as 战绩结算后台 (War3Server)

    Note over DotA: 基地生命值为 0，游戏结束
    DotA->>DotA: 执行结算函数 (StoreInteger 写入 dr.x)
    DotA->>GameDLL: SyncStoredInteger(OS, "0", "1") (Kills)
    DotA->>GameDLL: SyncStoredInteger(OS, "0", "2") (Deaths)
    DotA->>GameDLL: SyncStoredInteger(OS, "Global", "Winner")
    
    Note over GameDLL: 0x6F44154A 构建 0x6B 动作包
    GameDLL->>War3Bot: 发送 W3GS_OUTGOING_ACTION (0x26)<br/>[Action: 0x6B | "dr.x" | "0" | "1" | Value=12]
    GameDLL->>War3Bot: 发送 W3GS_OUTGOING_ACTION (0x26)<br/>[Action: 0x6B | "dr.x" | "Global" | "Winner" | Value=1]

    Note over War3Bot: client.cpp 解析 0x6B 动作流
    War3Bot->>War3Bot: 组装整场比赛比分大板 (KDA/出装/胜负)
    War3Bot->>Server: HTTP POST /api/match/settle (包含玩家战绩 JSON)
    Server-->>War3Bot: 200 OK (积分更新完成)
```

---

## 三、 APM 与动作过滤架构

```mermaid
flowchart TD
    A[收到 0x26 W3GS_OUTGOING_ACTION] --> B[剥离前 4 字节 CRC32]
    B --> C[进入 actionData 字节流]
    C --> D{读取当前字节: Action ID}

    D -->|0x10, 0x11, 0x12, 0x13| E[有效单位操作]
    D -->|0x16, 0x17, 0x18, 0x19| F[有效选择/编队操作]
    D -->|0x1B| G[有效捡神符/物品操作]
    
    E --> H[玩家有效操作计数++ (APM)]
    F --> H
    G --> H

    D -->|0x60| I[聊天与命令捕获: -ap, -stats]
    D -->|0x6B| J[DotA 结算数据捕获: 比分/出装/胜负]

    D -->|0x01, 0x21, 0x29 等| K[常规辅助操作 (不计入有效APM)]

    H --> L[根据 paramLen 步进 offset]
    I --> L
    J --> L
    K --> L

    L --> M{offset < dataSize?}
    M -->|是: 存在连包| D
    M -->|否: 本帧动作解析完毕| N[加入时隙广播队列 m_actionQueue]
```
