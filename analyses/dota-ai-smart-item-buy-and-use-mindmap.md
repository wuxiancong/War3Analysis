# DotA AI 智能购买与使用物品 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Hydrogen（Antigravity Agent） |
| **分析目的** | 导图化智能买装、信使、补给、控符、插排眼、TP、跳刀与切装全链路方案 |
| **命名方式** | `dota-ai-smart-item-buy-and-use-mindmap`；主命令 `use`/`items`/`autoitem`/`courier`/`rune`/`ward` |
| **分析时间** | 2026-11-17 |

```mermaid
mindmap
  root((AI 智能物品系统))
    结论
      无需新逆向 game.dll
      用 useslot1..6 0xD0028..0xD002D
      只读原生自动学地址
      决策分层 L1-L3
    命令规范
      use 兼容 item
      items 对偶 skills
      autoitem 对偶 autolearn
      courier 兼容 bird
      rune 控符
      ward 插排眼
      IPC 追加到 AiUnitCommand 末尾
    L1 底层数据与原语
      只读原生补齐
        UnitInventorySize
        UnitItemInSlot
        GetItemTypeId
        GetItemCharges
        GetItemX Y
      动作包
        0x10 无目标 useslot
        0x11 点地 useslot
        0x12 目标 useslot
        0xD0021 dropitem 给队友
        0xD0022..27 moveslot 换格
        0x10 0x0044 买假单位
      状态跟踪
        AiInventorySlot 6格缓存
        队友 g_lastHeroHandle
        信使句柄跟踪
        CreateItem 神符记录
    L2 智能购买与信使
      开局买鸡变小鸡
      3分钟升级飞行信使
      无补给买药或魔瓶
      信使自动运货与加速
      神秘/边路商店距离判断
    L2 补给与控符
      大药与小蓝
        优先给大残队友加
        脱战安全防打断
      吃树 Tango 指向树木
      魔瓶 Bottle
        2分钟前10秒准备
        优先有视野河道点
        F1 -2352,1648 与 G1 3008,-2832
        残血缺蓝自动喝
    L2 视野与战术道具
      视野
        盲区超时买假眼
        有钱或有隐身买真眼排眼
      TP 支援与逃生
        队友残血且塔下可援
        拉高 g_aiCastGuardUntil 防打断
      跳刀 Blink
        躲技能与追杀 1150码内
        3秒受英雄伤害冷却记录
      动态切装
        假腿 力敏智按需切换
        臂章 开打保命与脱战关
        圣殿天鹰 推线开控线关
        魔棒魔杖 读充能急救
    L3 协调与落地
      P1 读包与 use items
      P2 信使与补给
      P3 控符与插眼
      P4 TP 跳刀与切装
      防坑 选中不带取消段与真人延迟
```

配套正文：[`dota-ai-smart-item-buy-and-use.md`](./dota-ai-smart-item-buy-and-use.md)

