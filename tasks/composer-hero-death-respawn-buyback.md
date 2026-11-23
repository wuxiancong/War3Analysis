# 任务：英雄死亡 / 复活倒计时 / 买活就绪（在线 LLM + 离线微操）

**给**：本会话 Composer　**布置时间**：2026-11-23　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 为什么做

- **离线 AI**：死后仍可能瞎补刀/乱走；需要精确 `respawn_s` 与「已复活」边沿。
- **在线大模型**：`should I buyback?` 需要费用、是否可买、还要等多久自然复活；MCP 文档里买活包已纠错，但**复活倒计时与死亡态只读链未交付**。
- 已有线索：`war3map_start_timer.j` 里 `F0[pid]` 计时器、`JS[pid]`、`XS[pid]` 禁买活布尔；`dota-ai-llm-mcp-verify.md` 更正了买活 FourCC / `XS` 语义。

## 要交付

1. DotA 6.83d 地图侧：死亡触发、复活时长公式、`F0`/`JS`/`XS`/`ZS`/`D7O` 关系；完整 `ZS[0..59]` 费用表导出。
2. `game.dll`：`IsUnitDead` / `UnitAlive` / `TimerGetRemaining` / `TimerGetElapsed` 全 11 版 RVA；单位死亡标志偏移（若有）。
3. AI 只读 API：`heroDeathState(pid)` → `{dead, respawnRem, buybackCost, buybackReady, buybackBlocked}`。
4. 改法只写文档（不改 hooker）；实机步骤一分钟可做。

## 限制

只读；不注入、不开局、不改 Launcher/hooker；全版本 RVA 表。
