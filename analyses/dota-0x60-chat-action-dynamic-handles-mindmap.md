# DotA `0x60` 聊天动作动态句柄 — 思维导图与架构图

本文档用 Mermaid 展现 Trigger/Event 动态句柄的生成链路、双段 `0x60` 成因，以及与 `0x6B Modeap` 的关系。

详细论证见：[`dota-0x60-chat-action-dynamic-handles.md`](./dota-0x60-chat-action-dynamic-handles.md)

---

## 一、全景思维导图

```mermaid
mindmap
  root((0x60 动态句柄机制))
    运行时观测
      手动 -ap 包
        T1 0x7E47
        E1 0x7F73
        T2 0x7966
        E2 0x806B 可变
      自动注入包
        前三相同
        E2 硬编码 0x8068 错误
      后续 0x6B
        dr.x Data Modeap
    脚本侧双触发器
      触发器A DB2
        CreateTrigger 较早
        10x RegisterPlayerChatEvent 立即
        对应较小 T2
      触发器B PF0
        CreateTrigger 较晚
        XY2 延迟 0.01s 注册事件
        对应较大 T1 与更晚 E1
        XX2 调 W82 解析模式
      模式落地
        WB2 ap 命中
        FL1 Mode+EL
        SyncStoredInteger 0x6B
    引擎侧句柄表
      NativeFuncEntryPoint
      CreateTrigger 分配 Agent
      TriggerRegisterPlayerChatEvent 分配 Event Agent
      Handle2AgentRegistry 登记
        1.26 RVA 0x430D88
        1.27 RVA 0x2652F4
      顺序递增加 free-list 复用
      Event2 同局可抖
    人数影响水位
      真人 +15 Agent 经验值
      电脑 +12 Agent 经验值
      单人 BK2 作弊套装抬高基线
      线性公式不能覆盖单人与抖动
    Launcher 对策
      禁用四常量硬编码
      优先 ChatInputLogic 物理路径
      或运行时缓存 GetHandleId
      不必强行 sendMapCommand 0x6B
```

---

## 二、端到端时序图

```mermaid
sequenceDiagram
    autonumber
    actor Player as 玩家
    participant UI as ChatEditBar
    participant ChatLogic as GameChatInputLogicInGame
    participant Queue as EnqueuePlayerAction
    participant Net as 网络同步
    participant Jass as war3map.j

    Note over Jass: 开局初始化
    Jass->>Jass: CreateTrigger DB2 + 10 ChatEvent
    Jass->>Jass: CreateTrigger PF0
    Jass->>Jass: 0.01s 后 XY2 注册 PF0 ChatEvent

    Player->>UI: 输入 -ap 回车
    UI->>ChatLogic: 提交聊天
    ChatLogic->>Queue: 0x60 (T1,E1,"-ap") 匹配 PF0
    ChatLogic->>Queue: 0x60 (T2,E2,"-ap") 匹配 DB2
    Queue->>Net: 广播双段动作
    Net->>Jass: 触发 XX2
    Jass->>Jass: W82("-ap") → AP=true EL=ap
    Jass->>Net: FL1 → SyncStoredInteger Modeap
    Net-->>Jass: 0x6B 到达各端，模式生效
```

---

## 三、句柄水位状态图

```mermaid
stateDiagram-v2
    [*] --> InitAgents: 地图加载 / 玩家槽位创建
    InitAgents --> ExtraHumans: 每多 1 真人 ≈ +15 Agent
    InitAgents --> ExtraComps: 每多 1 电脑 ≈ +12 Agent
    InitAgents --> SoloCheats: 单人 AR2 → BK2 大量 Chat 触发器
    ExtraHumans --> Watermark
    ExtraComps --> Watermark
    SoloCheats --> Watermark
    Watermark --> CreateDB2: CreateTrigger + 10 Events
    CreateDB2 --> CreatePF0: 稍后 CreateTrigger PF0
    CreatePF0 --> DelayRegister: 0.01s 定时器窗口内继续消耗 Agent
    DelayRegister --> PF0Event: TriggerRegisterPlayerChatEvent(PF0)
    PF0Event --> Ready: 四句柄定稿但仍可能因 free-list 微调
    Ready --> Emit60: 玩家输入 -ap
    Emit60 --> [*]: 双段 0x60 + 后续 0x6B
```

---

## 四、包结构解剖图

```mermaid
flowchart LR
    subgraph Seg1["0x60 段1 ≈ PF0"]
        A1["0x60"] --> T1["Trigger1 u32"]
        T1 --> E1["Event1 u32"]
        E1 --> S1["'-ap\\0'"]
    end
    subgraph Seg2["0x60 段2 ≈ DB2"]
        A2["0x60"] --> T2["Trigger2 u32"]
        T2 --> E2["Event2 u32"]
        E2 --> S2["'-ap\\0'"]
    end
    subgraph Mode["随后地图自发"]
        B["0x6B"] --> C["dr.x"]
        C --> D["Data"]
        D --> E["Modeap"]
    end
    Seg1 --> Seg2 --> Mode
```

---

## 五、可靠注入 vs 错误硬编码

```mermaid
flowchart TD
    Goal["注入 -ap 模式命令"]
    Goal --> Good["可靠：chatSendCommand"]
    Goal --> Bad["不可靠：sendChatAction 硬编码"]
    Good --> Engine["GameChatInputLogicInGame"]
    Engine --> Match["引擎匹配 PF0/DB2 事件表"]
    Match --> RealH["使用真实运行时句柄"]
    RealH --> OK["双段 0x60 正确 → W82 → Modeap"]
    Bad --> Guess["0x7E47/7F73/7966/8068"]
    Guess --> Miss["Event2 常错成 0x8068≠0x806B"]
    Miss --> Flaky["偶发成功 / 多数失败"]
```
