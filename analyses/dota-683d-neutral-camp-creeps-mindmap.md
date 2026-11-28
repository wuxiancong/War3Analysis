# DotA 6.83d 全野点刷怪表与近卫野区分析（思维导图）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini（Antigravity IDE） |
| **分析目的** | 可视化 6.83d 12 野点刷新池、不重复随机逻辑、近战/远程分布及斧王打野/小鸡囤野策略 |
| **命名方式** | `dota-683d-neutral-camp-creeps-mindmap.md` |
| **分析时间** | 2026-11-27 20:15 |
| **配套正文** | [`dota-683d-neutral-camp-creeps.md`](./dota-683d-neutral-camp-creeps.md) |

```mermaid
flowchart LR
    ROOT["DotA 6.83d 中立野点刷怪表 (Scripts_war3map.j + SLK)"]

    ROOT --> MECH["刷新机制 (P3O / R1O)"]
    MECH --> M1["每分钟整点检测封野盒 r1，空则在 r2 中心刷怪"]
    MECH --> M2["R1O 不重复随机：同一野点绝不连刷同一组"]
    MECH --> M3["经验公式 (FormulaC=6.0)：Lv1~6 = 25/41/62/88/119/155"]

    ROOT --> SMALL["小野池 (6 组) — 近卫 B5 / 天灾 A5"]
    SMALL --> S1["仅 1/6 (16.7%) 全近战：RHO 狗头人x5 (1445HP / 68g)"]
    SMALL --> S2["5/6 含远程 (300~600 射程)：ngh1/nftb/nfsh/ngns/n0HW/n0HX"]
    SMALL --> S3["均值 1342HP / 75.4g / 133XP — 极不适合小鸡囤野"]

    ROOT --> MED["中野池 (5 组) — 近卫 E5, F5 / 天灾 C5, Z5"]
    MED --> D1["4/5 (80%) 全近战：泥土傀儡 / 食人魔 / 巨狼 / 半人马"]
    MED --> D2["仅 1/5 含远程：REO 小萨特 nsat (300 射程 7~10 攻)"]
    MED --> D3["均值 1790HP / 102.6g / 202.4XP — F5/E5 最适合小鸡安全囤野"]

    ROOT --> LARGE["大野池 (5 组) — 近卫 I5, W5 / 天灾 O5, D5"]
    LARGE --> L1["3/5 (60%) 全近战：熊怪 RCO / 枭兽 RJO / 半人马 RVO"]
    LARGE --> L2["2/5 含远程：RDO(nsat 300) / RKO(黑暗巨魔 500 秒鸡)"]
    LARGE --> L3["均值 1860HP / 124.0g / 219.8XP — 英雄空档囤 I5 收益最高"]

    ROOT --> ANC["远古池 (5 组) — 近卫 U4 / 天灾 Q4"]
    ANC --> A1["3/5 (60%) 全近战：捕猎者 / 蓝龙人 / 傀儡"]
    ANC --> A2["2/5 含 500 射程高危远程：黑龙 R8O / 雷霆蜥蜴 RAO"]
    ANC --> A3["均值 3635HP / 266.6g / 351.6XP"]

    ROOT --> AI["斧王打野 AI 落地建议"]
    AI --> AI1["小鸡优先囤 F5 (80% 纯近战)"]
    AI --> AI2["英雄空档优先囤 I5 (+124g/波)"]
    AI --> AI3["远程黑名单仅 13 个 ID (纠正 ngst/nkol/nstl 实为近战)"]
    AI --> AI4["静谧鞋 >600 码捡 / <450 码放，覆盖全部远程射程"]
```
