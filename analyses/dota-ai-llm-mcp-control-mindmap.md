# 大模型托管 DotA 6.83d（MCP Server）思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 以思维导图形式呈现大模型托管 DotA 6.83d 的分层架构、War3 全 11 个版本逆向数据层、10ms 级自适应微操、动作包缺口、MCP 工具集、安全边界与 MVP 路线 |
| **命名方式** | `dota-ai-llm-mcp-control-mindmap`（配套正文 [`dota-ai-llm-mcp-control.md`](./dota-ai-llm-mcp-control.md)） |
| **分析时间** | 2026-11-21 |

```mermaid
flowchart LR
    Root["大模型托管 DotA 6.83d<br/>(MCP Server 架构与全版本逆向)"]

    Root --> Arch["1. 分层架构原则"]
    Arch --> Arch1["指挥层: LLM + MCP stdio (2~5s 宏观意图)"]
    Arch --> Arch2["桥接层: Launcher 127.0.0.1:6120<br/>(NDJSON + 请求 id, 替代 AiUnit.log)"]
    Arch --> Arch3["执行层: hook.dll aiTick (10ms 级自适应微操)<br/>高性能机可下探 4~8ms 发挥极限 / 低配平滑退避<br/>补刀 / 卡兵 / 拉野 / 连招 / 避险"]

    Root --> Data["2. 看局面逆向 (全 11 个版本 1.0.17~1.27)"]
    Data --> D1["25 个 JASS 原生 100% 覆盖<br/>HP/MP/三维/物品/技能等级/昼夜"]
    Data --> D2["精确冷却 (1.22~1.27 全一致)<br/>CAbilitySpell+0x20 & 0x200<br/>+0xD0 CTimer vtable+0x18"]
    Data --> D3["Buff/Debuff<br/>CUnit+0x1DC 链表 / GetUnitAbilityLevel"]
    Data --> D4["可靠金钱 & 买活<br/>EL0[pid] / 能量圈 n01F / 360s 冷却"]
    Data --> D5["严格本地视野 (防作弊)<br/>IsUnitVisible + IsUnitDetected"]
    Data --> D6["态势与事件流<br/>兵线 / 塔 / 肉山仅公开FL1+视野 / 0x60 / 0x68"]

    Root --> Cmd["3. 指令缺口与 1.27 动作包"]
    Cmd --> C1["Shift 队列: 0x10~0x12 flags |= 0x01"]
    Cmd --> C2["远距买装 + 信使: 选商店入储藏处<br/>0x16 选信使 + 0x10 送货/加速"]
    Cmd --> C3["买活: 0x16 选 n01F + 0x10 英雄 FourCC"]
    Cmd --> C4["Glyph: 0x16 选 n01F + 0x10 0xD00FA"]
    Cmd --> C5["插眼排眼 & TP 到塔: 0x11 地标坐标 + 0x12 攻击显形眼"]

    Root --> Tools["4. MCP 工具集 (14 个)"]
    Tools --> T1["感知类: get_game_state (<2k token)<br/>get_units / get_events"]
    Tools --> T2["宏观决策: farm_lane / set_mode<br/>retreat / move_to / ward"]
    Tools --> T3["战斗与经济: attack_target / cast<br/>buy / use_item / learn / team_action"]
    Tools --> T4["地标表: 三路塔 / 12 野点 / 符点<br/>肉山 (4176,-2288) / 高台眼位"]

    Root --> Safe["5. 安全边界"]
    Safe --> S1["零迷雾泄露 (hook 层先过滤)"]
    Safe --> S2["只发玩家合法动作包 + APM 限速"]
    Safe --> S3["一键收回控制 (-ai off / 急停键)"]
    Safe --> S4["仅绑定 127.0.0.1 + stdio"]

    Root --> MVP["6. MVP 路线"]
    MVP --> M1["P0 (6工具首周上线): NDJSON + 视野快照<br/>get_game_state / farm_lane / set_mode / retreat / buy / learn"]
    MVP --> M2["P1: 精确冷却 + Buff + 信使 + 事件流"]
    MVP --> M3["P2: 买活 + Glyph + 可靠金钱 + 眼位 + Shift 队列"]
```
