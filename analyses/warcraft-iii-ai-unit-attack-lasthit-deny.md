# AI 单位攻击 / 正补 / 反补（`-attack` / `-lasthit` / `-deny`）

> **日期**：2026-11-14  
> **代码**：`War3Launcher/hooker/war3hook_ai.cpp`、`AiControlManager.cpp`、`scripts/ai_control.ps1`  
> **关联**：[`warcraft-iii-ai-hero-move-command.md`](./warcraft-iii-ai-hero-move-command.md)  
> **真人习惯（方案）**：[`dota-player-lasthit-habit-recorder.md`](./dota-player-lasthit-habit-recorder.md)

## 结论

| 命令 | 是否单独命令 | 行为 |
| :--- | :--- | :--- |
| `-attack` / `/attack` / RemoteControl `attack` | 是 | **普通攻击**：立刻发 `0x12` + Order `0xD000F`；或 `attack <x> <y>` 走攻击移动 `0x11`+`0xD000F` |
| `-lasthit` / `lasthit` | **是（与 attack 分开）** | 只打**最后一下**正补：等待期间 `stop` 压刀，按掉血预测出手，用地图正补计数确认 |
| `-deny` / `deny` | **是（与 attack / lasthit 分开）** | 只打**最后一下**反补：目标为友方小兵且血量 &lt; 50%，同样预测出手 |

正补 / 反补**不是**另一种 Action ID，而是同一套攻击包上的**时序策略**；因此必须与普通 `attack` 分命令，避免 AI 把「A 一下」和「补刀」混用。

## AI 调取入口

- 游戏内聊天：`-attack` / `/attack` / `-lasthit` / `-deny` / `-units`（`handleAttackCommand`）
- RemoteControl（`ai_control.ps1`）：`attack` / `lasthit` / `deny` / `units`
- IPC：`MSG_TYPE_AI_UNIT_COMMAND` → `requestAiUnitCommand` → 主线程 `aiTick`

## 移动/攻击入队修复（本轮）

1. **英雄代理**：号角后 Handle2Agent 极热，8192 环会被冲掉 → `aiResolveUnitObjectIds` 失败。已加持久 `handle→agent` 表 + K1 时 `aiPinHeroHandle`。选人确认后日志可见 `type=Nfir` 对象 ID。
2. **Enqueue 线程**：`-move` 与 `-buy` 对齐——在 **Action 线程**上 `callEnqueuePlayerActionEx`，选中与点地之间 `sleep(30ms)`（连续两次 Enqueue 过快会互相覆盖）。
3. **AI 攻击包**：`aiEnqueue` 仍可走队列 + `flushQueuedPlayerActions`（flush 间隔同样 30ms），供 `-attack`/`-lasthit`/`-deny` 从 `aiTick` 投递。

## 用法摘要

```text
attack <x> <y>                 # 攻击移动
attack nearest|enemy [半径]    # 普通攻击最近敌方小兵
attack ally [半径]             # 普通攻击最近友方小兵（非补刀）
attack 0x<句柄>                # 攻击指定单位
attack stop                    # stop + 取消补刀例程
lasthit [伤害] [超时秒] [范围] [前摇] [弹速]
deny    [伤害] [超时秒] [范围] [前摇] [弹速]
units [半径]                   # 日志：logs/AiUnit.log
```
