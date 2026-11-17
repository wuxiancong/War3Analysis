# DotA1 英雄加点（O）流程 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图化 O → 学技能/属性 与 AI 注入路径 |
| **命名方式** | `dota-hero-skill-point-learn-flow-mindmap` |
| **分析时间** | 2026-11-16 |

```mermaid
mindmap
  root((英雄加点 O))
    结论
      O 只发 0x66
      真正加点是 0x10 + FourCC
      属性 Aamk/A0NR 同管道
      AI 复用 Enqueue 无需新 RVA
    人手路径
      升级得技能点
      按 O 或点书本
      子菜单选技能或属性U
      ESC 0x61 退出
    协议
      0x66 零载荷
      0x10 Flags+AbilityId+8B
      勿与 0x6B GameCache 混淆
    引擎与地图
      引擎扣点校验等级
      EVENT_PLAYER_HERO_SKILL
      SelectHeroSkill 仅脚本侧
    AI 拟实现
      主名 learn 兼容 skill
      施法主名 cast
      先选中英雄
      可选 0x66 再 0x10
      表驱动 dota_data
    感知升级
      无专用升级 Action
      0x6B Data:LevelN=pid
      GetHeroLevel → g_lastHeroLevel
      不必为升级再挖 dll
    验证
      抓 O 与学习 hex
      核对 flags
      无点数拒绝
```

配套正文：[`dota-hero-skill-point-learn-flow.md`](./dota-hero-skill-point-learn-flow.md)
