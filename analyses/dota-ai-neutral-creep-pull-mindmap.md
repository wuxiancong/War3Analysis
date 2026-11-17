# DotA AI 自动拉野 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Claude Opus（Antigravity Agent） |
| **分析目的** | 导图化拉野方案：能力盘点、缺口、状态机、命令、验收 |
| **命名方式** | `dota-ai-neutral-creep-pull-mindmap`；对外命令 **`camp`** |
| **分析时间** | 2026-11-16 |

```mermaid
mindmap
  root((AI 自动拉野))
    结论
      不需要新逆向 game.dll
      拉野是时序策略
        0x12 attack 点一下
        0x11 move 拖向兵线
      缺数据不缺偏移
    机制
      野怪归属
        1.24-1.28 Player 12
        1.29+ Player 24
      按分钟 CreateUnit 刷新
      拴绳距离
        GuardDistance
        MaxGuardDistance
        GuardReturnTime
      出手秒 pullSecond 可配置
      囤野 约 xx:53
    已有能力
      CreateUnit 钩子 aiOnUnitCreated
      只读原生
        GetUnitX Y
        GetWidgetLife
        GetOwningPlayer
      aiCollectNearby
      aiAttackUnit
      requestUnitMove 0xD0012
      g_aiPendingAggroAction 延迟动作
      aiExecAggroDraw 参考
      游戏时间 g_allGameSeconds
      aiTick 10ms
    缺口
      G1 aiNeutralHostileOwner
      G2 野点坐标采集
        argSnapshot 2 3 可能是 float 指针
        优先原生查询
      G3 兵线拦截点预测
      G4 追击判定
        GetUnitCurrentOrder
        降级 几何判定
      G5 回营判定
      G6 仇恨目标 可选逆向
    状态机
      Idle
      GoCamp
      WaitTime hold
      Hit 等前摇
      Drag 每200ms 重算
      Release 回线
      Abort 记原因
    命令
      camp pull
      camp auto
      camp stack
      camp log
      camp list
      IPC AI_UNIT_CMD_CAMP
      勿用 pull 与 aggro 冲突
    协调
      暂停 push lasthit
      stop move 可打断
      危险检测排除野怪
    验收
      units 显示野怪 owner
      log 坐标稳定
      A 后转身不吞攻击
      野怪撞己方兵
      空营 Abort
      录像不同步检查
```

配套正文：[`dota-ai-neutral-creep-pull.md`](./dota-ai-neutral-creep-pull.md)

