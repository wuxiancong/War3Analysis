# 「大模型托管 DotA」接口核验结果思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 一览 `dota-ai-llm-mcp-control.md` 逐项独立核验结果（✅ 通过 / ⚠ 部分对或待实机 / ❌ 必须更正） |
| **命名方式** | `dota-ai-llm-mcp-verify-mindmap`（配套正文 [`dota-ai-llm-mcp-verify.md`](./dota-ai-llm-mcp-verify.md)） |
| **分析时间** | 2026-11-21 |

```mermaid
flowchart LR
    Root["dota-ai-llm-mcp-control.md<br/>1.27 独立复核结论"]

    Root --> OK["✅ 直接可写代码 (4 项)"]
    OK --> OK1["A4 Buff/Debuff<br/>CUnit+0x1DC / +0x34 / vt+0x1E0~1E8"]
    OK --> OK2["A5b/c Glyph 冷却 & 昼夜<br/>D30+CAgentTimer / GetFloatGameState(2)"]
    OK --> OK3["B5 Shift 队列<br/>0x3AE4E0 实证 abilityFlags |= 0x0001"]
    OK --> OK4["B4 TP 吸附 (语义微调)<br/>XKO 全图吸最近塔, MS0=575 钳制落点"]

    Root --> FIX["❌ 揪出错误必须先改 (5 项)"]
    FIX --> F1["B1 买活: 不是英雄 FourCC<br/>改为 ZS[GV1(lvl)] 60 档占位单位"]
    FIX --> F2["B2 Glyph: 不是 0xD00FA<br/>1.27 OrderId 实证 coldarrows = 0x000D0114"]
    FIX --> F3["B3 信使: 15 个真 FourCC (L3691)<br/>送货='h085', 存储藏='h0BV', 续送='h0DE'"]
    FIX --> F4["B3+ 守卫: 不是 I057/I058<br/>假眼 I05G->o004(420), 真眼 I05H->oeye(500)"]
    FIX --> F5["A6 事件 0x6B: 无 Kill/Death 键<br/>改为 Hero+pid / Assist+pid / Tower / Rax"]

    Root --> WARN["⚠ 离线已证, 待实机补测 (4 项)"]
    WARN --> W1["A1 技能冷却: 纯只读公式已证<br/>node=abil+0xDC, 总=node+8, 剩=node+4-clock<br/>待冰女放前/刚放/5s 实测"]
    WARN --> W2["A2 金钱: EL0 与 CPlayer+0x50 已证<br/>待买物前后实测"]
    WARN --> W3["A3 视野红线: IsUnitVisible+Detected<br/>上线前必补实机迷雾敌方英雄=false 证据"]
    WARN --> W4["A5a 买活冷却: XS 是 boolean 非秒数<br/>改用买活时刻 + 360s 倒计时"]
```
