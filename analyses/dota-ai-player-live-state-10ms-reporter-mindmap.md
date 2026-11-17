# DotA AI 10ms 动态玩家状态上报系统 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Hydrogen（Antigravity Agent） |
| **分析目的** | 导图化 10ms 玩家状态采集、无锁共享内存上报与跨版本免逆向方案 |
| **命名方式** | `dota-ai-player-live-state-10ms-reporter-mindmap`；主命令 `state` |
| **分析时间** | 2026-11-17 |

```mermaid
mindmap
  root((10ms 玩家状态上报))
    是否需要逐版本逆向
      绝大多数不需要 11/14项
        aiLearnNative 按名自动学地址
        天然兼容 1.24 至 1.27
      3项仅精确值需特征码
        护甲
        实时攻击力
        实时视野
      路线A 零逆向
        离线SLK基础表 + 原生实时估算
      路线B 跨版本特征码
        findVersionOffset 读 CUnit 或 CInfoPanel
    状态字段来源
      T1 高频 10ms
        死亡 GetWidgetLife <= 0.405
        血量蓝量 GetUnitState 0..3
        Order GetUnitCurrentOrder
        攻击中 Order + 攻击前摇
        被攻击 掉血速率 + GetAttacker旁路
        施法攻击前后摇阶段
      T2 中频 50ms
        移速 GetUnitMoveSpeed
        三围 GetHeroStr Agi Int false/true
        经验等级 GetHeroXP GetHeroLevel
        护甲 攻击力 视野 离线表+装备估算
    传输架构 零拷贝
      不走 MessageSlot 防队列阻塞
      SharedData::AiPlayerLiveState
      SeqLock seq奇写偶读防撕裂
      WndProc TIMER_AI_TICK 10ms写入
      外部 AI / Launcher 内存映射直读
    离线物编表
      复用 mpqread.py
      生成 DotaHeroUnitStats.h
      提取 castpt castbsw sight def dmg
    命令与验收
      state on / off / dump
      IPC AI_UNIT_CMD_STATE
      对比游戏面板数值
      压测 10ms 帧率与 seq 一致性
```

配套正文：[`dota-ai-player-live-state-10ms-reporter.md`](./dota-ai-player-live-state-10ms-reporter.md)

