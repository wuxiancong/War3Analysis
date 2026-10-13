# DotA RD 与 SD 模式执行链路思维导图与架构图

本文档通过 Mermaid 思维导图、时序流程图与状态图，直观展现 Warcraft III `game.dll` 与 DotA 地图脚本在 **RD (Random Draft)** 与 **SD (Single Draft)** 模式下的底层执行链路。

---

## 一、全景思维导图 (Mindmap)

```mermaid
mindmap
  root(("魔兽3 DotA 选人模式执行链路"))
    RD 随机征召模式
      模式规则
        全局共享 24 个候选英雄池
        双方玩家按顺位轮流征召
        倒计时限制与顺位推进
      JASS 数据结构
        "Q80: 槽位映射 (Slot -> HeroIndex)"
        "Q90: 锁定状态 (0=可选, 1=锁定)"
        "QA0: 展示实体 Handle 映射"
        "K1: 玩家最终英雄 Handle"
      网络动作协议
        "0x3A 复合动作包 (Deselect -> Select -> 镜头同步)"
        "0x0A 保持动作包 (1B 01 H1 H2)"
        "0x0F 确认勾号包 (Flag: 0x40, UnitId: h06N)"
      game.dll 底层切入点
        "GameJassVariableSetter_1 (0x7EC719 / 0x7EC6C0)"
        "GameJassVariableSetter_2 (0x7EC660)"
        CreateUnit 生成真实英雄
    SD 单一征召模式
      模式规则
        每位玩家独立 3 选 1 候选池
        力/敏/智 主属性各随机 1 名
        各玩家选择互不干扰
      JASS 数据结构
        "D30: 玩家专属能量圈 Handle"
        "K1: 玩家最终英雄 Handle"
      Native API 链路
        "GameNativeFuncEntryPoint (0x7EF6E0)"
        "AddUnitToStock: 向 D30 能量圈挂载候选商品"
        "RemoveUnitFromStock: 选定后清空剩余商品"
      网络动作协议
        "0x10 单位购买/训练指令"
      game.dll 底层切入点
        "GameNativeFuncEntryPoint: Native 统一网关"
        "CUnit::AddStockItem: 建筑库存与商品系统"
        EnqueuePlayerAction 标准单位购买指令
```

---

## 二、RD 模式执行时序图 (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor Player as 玩家客户端
    participant UI as 游戏 UI / 场景
    participant ActionQueue as game.dll 动作队列
    participant JassVM as game.dll JASS 虚拟机
    participant JassScript as war3map.j 地图脚本

    Note over JassScript, JassVM: 1. 初始化阶段
    JassScript->>JassVM: 抽取 24 英雄，写入 Q80[0..23] 与 QA0[0..23]
    JassVM-->>JassScript: GameJassVariableSetter (0x7EC719) 写入符号表
    JassScript->>JassVM: 初始化 Q90[0..23] = 0 (全部待选)

    Note over Player, JassScript: 2. 交互与预览阶段 (轮到当前玩家)
    Player->>UI: 点击切换不同的候选英雄展示单位
    UI->>ActionQueue: 提交 0x3A 动作包 (Deselect 旧单位 -> Select 新单位)
    ActionQueue->>JassVM: 广播同步，更新玩家视角与选择焦点

    Note over Player, JassScript: 3. 锁定确认阶段 (Pick)
    Player->>UI: 点击确认勾选按钮 (UI 确认或点击 h06N)
    UI->>ActionQueue: 发送 15 字节确认包 (Action 0x10, Flag 0x40, ID h06N)
    ActionQueue->>JassScript: 触发对 h06N 的指令事件 (TriggerRegisterPlayerUnitEvent)
    JassScript->>JassVM: 更新 Q90[slot] = 1 (标记已被选走)
    JassScript->>JassVM: 调用 CreateUnit 创建真实英雄实体
    JassScript->>JassVM: 写入 K1[playerIndex] = HeroHandle
    JassScript->>JassScript: 顺位状态机步进 (Turn Token 移交给下一位玩家)
```

---

## 三、SD 模式执行时序图 (Sequence Diagram)

```mermaid
sequenceDiagram
    autonumber
    actor Player as 玩家客户端
    participant ActionQueue as game.dll 动作队列
    participant NativeGateway as GameNativeFuncEntryPoint (0x7EF6E0)
    participant EngineUnit as game.dll CUnit/库存系统
    participant JassScript as war3map.j 地图脚本

    Note over JassScript, EngineUnit: 1. 能量圈分配与候选注入
    JassScript->>JassScript: 分配各玩家能量圈，记录至 D30[playerIndex]
    JassScript->>NativeGateway: AddUnitToStock(D30, 力量英雄ID, 1, 1)
    NativeGateway->>EngineUnit: CUnit::AddStockItem (挂载商品 1)
    JassScript->>NativeGateway: AddUnitToStock(D30, 敏捷英雄ID, 1, 1)
    NativeGateway->>EngineUnit: CUnit::AddStockItem (挂载商品 2)
    JassScript->>NativeGateway: AddUnitToStock(D30, 智力英雄ID, 1, 1)
    NativeGateway->>EngineUnit: CUnit::AddStockItem (挂载商品 3)

    Note over Player, JassScript: 2. 玩家购买/选定阶段
    Player->>ActionQueue: 选中自身能量圈，发送 0x10 购买指令 (包含目标英雄 ID)
    ActionQueue->>NativeGateway: 触发建筑商品购买事件
    NativeGateway->>JassScript: JASS 单位创建与训练回调
    JassScript->>NativeGateway: RemoveUnitFromStock (移除剩余 2 个候选商品)
    JassScript->>JassScript: 写入 K1[playerIndex] = HeroHandle
```

---

## 四、RD 模式状态机模型 (State Diagram)

```mermaid
stateDiagram-v2
    [*] --> ModeInit: 模式判定 /host rd
    ModeInit --> HeroPoolGenerated: JASS 随机抽取 24 英雄\n写入 Q80/QA0
    HeroPoolGenerated --> TurnWaiting: 轮选开始，分配第一个玩家顺位

    state TurnWaiting {
        [*] --> Selecting: 倒计时开始
        Selecting --> Selecting: 切换选中目标 (0x3A 封包)\n重复点击保持 (0x0A 封包)
        Selecting --> Confirmed: 点击勾号 h06N (Flag 0x40)
        Selecting --> TimeoutForced: 倒计时耗尽 (随机/弃选)
    }

    Confirmed --> HeroSpawned: 更新 Q90[slot]=1\nCreateUnit 生成英雄\n更新 K1[pid]
    TimeoutForced --> HeroSpawned: 系统强制指定英雄\n更新 Q90[slot]=1

    HeroSpawned --> NextTurn: 检查是否仍有未选玩家
    NextTurn --> TurnWaiting: 顺位转移给下一位玩家\n重置倒计时
    NextTurn --> GameStarted: 全部 10 名玩家选人完毕
    GameStarted --> [*]
```

---

## 五、关键底层符号与内存地址速查

| 符号 / 功能 | 1.27.0.52240 地址 | 调用约定 | 关联模式 | 核心作用 |
| :--- | :--- | :--- | :--- | :--- |
| `GameJassVariableSetter_1` | `0x7EC719` / `0x7EC6C0` | `__fastcall` | RD / SD | 监控 `Q80`、`Q90`、`QA0`、`D30`、`K1` 变量变更 |
| `GameJassVariableSetter_2` | `0x7EC660` | `__thiscall` | RD | 数组变量清理与重置 |
| `GameNativeFuncEntryPoint` | `0x7EF6E0` | `__cdecl` | SD / RD | 拦截 `AddUnitToStock`、`CreateUnit` 等 Native API |
| `EnqueuePlayerAction` | 导出网络层 | `__thiscall` | RD / SD | 动作包入队：RD 确认 (`0x40`, `h06N`) 与 SD 购买 (`0x10`) |