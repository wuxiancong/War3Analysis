# DotA AI `learn` 加点实现方案 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 导图化加点命令落地；主名 `learn`，与施法 `cast` 成对 |
| **命名方式** | 文件名历史保留 `dota-ai-skill-command-implementation-mindmap`；对外命令 **`learn`** |
| **分析时间** | 2026-11-16 |

```mermaid
mindmap
  root((learn 加点))
    命名
      主名 learn
      兼容 skill
      施法用 cast
      勿混 skill=放技能
    语法
      learn token
      attr FourCC 1-4
      nosubmenu 可选
    管道
      AiControl IPC
      MSG_TYPE_HERO_SKILL_LEARN
      request 再 Action 线程
      同 buy move
    组包
      选中本地英雄
      默认 0x66
      0x10 + AbilityId
      Flags 抓包校正
    表
      DotaHeroSkillAbbrev
      attrCode Aamk A0NR
      槽位查英雄
    不做
      新 dll RVA
      SelectHeroSkill 当权威
      MVP 不做自动加点序
    验收
      RemoteControl learn 1
      skill 别名等价
      游戏内不刷屏
      无点数不崩
```

配套正文：[`dota-ai-skill-command-implementation.md`](./dota-ai-skill-command-implementation.md)
