# DotA 6.83d 英雄使用技能深度逆向与 AI 控制体系 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Antigravity AI Agent（Planning + Execution） |
| **分析目的** | 结构化呈现 DotA 6.83d 英雄施法的已有文档覆盖度、`game.dll` 技能对象模型、全 11 版 RVA、协议 `Flags`、现有代码 8 大缺陷及分阶段升级蓝图 |
| **命名方式** | `dota-6.83d-hero-ability-cast-deep-reverse-and-ai-design-mindmap`；命令体系 `-cast`/`-learn`/`-skills`/`-autolearn` |
| **分析时间** | 2026-11-19 |

```mermaid
mindmap
  root((DotA 6.83d 英雄施法深度逆向))
    已有文档盘点
      4 篇基础与 MVP 文档已存在
        dota-hero-ability-cast-flow 协议 0x10 0x11 0x12
        dota-ai-human-lasthit-learn-cast 344 条订单表与初版代码
        dota-hero-skill-point-learn-flow 加点 0x66 + 0x10
        warcraft-iii-skill-key-remap 本地 4x3 命令卡映射
      共同缺口
        刻意回避 game.dll 对象内部机制
        仅支持 1~4 格静态 1 级属性与基础测试
    game.dll 对象模型与全 11 版 RVA
      CUnit 核心偏移
        +0x33 单位 FourCC 首字母大写判英雄
        +0x5C 状态位 0x40000000 幻象与 0x200000 Pause
        +0x19C +0x1A0 当前 COrder 再读 +0x24 OrderId
        +0x1DC +0x1E0 动态技能链表头
        +0x1F0 CAbilityHero 再读 +0x90 真技能点
      CAbilitySpell 运行时字段与虚表
        +0x34 自定义 FourCC 与 vtable +0x1C 基类码
        +0x50 0-based 等级与 +0xB0 冷却总秒数
        +0x20 位 0x200 冷却中与 0x400 暂停与 bit31 忽略 CD
        +0xD0 嵌入 CAgentTimer +0x18 读精确剩余秒数
        +0x3C 禁用计数 0xDD 与 +0x44 沉默计数 0xB9
        vtable +0x3DC CheckCanCast 七步权威预检
      全 11 版 1.0.17~1.27 RVA
        GetUnitAbilityLevel 与 GetHeroSkillPoints 与 GetUnitCurrentOrder
        UnitResetCooldown 与 IsUnitPaused 与 IsUnitType
        1.22~1.27 JassHandleToUnit 与 CAbilitySpell Reset/GetCooldown
    协议包 Flags 位掩码实证
      三大网络包
        0x10 15B 无目标 / 开关 / 加点
        0x11 23B 点地目标
        0x12 31B 单位目标含 X Y ObjId1 ObjId2
      Flags 逐位语义 1.26 0x6F2CA800 与 0x6F2CD2E1
        0x0001 bit0 Shift 队列排队入队 0x6F2A0510
        0x0002 bit1 与 0x0100 bit8 瞬发插队分支
        0x0010 bit4 选中组上下文标志
        0x0020 bit5 持续施法抑制与清队标志
        0x0040 bit6 仅当前子组 0x6F421E00 vs 全选中单位
    现有代码 8 大缺陷审计
      1 4 个核心主动技错标 PASSIVE 水人复制 炸弹雷 夜魔大 影魔大
      2 4 个 AIdd 被动错标 defend 小猴冲锋 敌法护盾 毒龙皮 屠夫堆肉
      3 水人敏转 A0KX 错标 UNIT 实证为 NONE 0x10
      4 25 个开关法球变身只有单 order 缺 On Off Unorder
      5 16 友方技与 8 双目标技 AUTO 全打敌人 ally 错连小兵
      6 slot 大于 4 被截断 丢影魔中远炮 火猫飞 帕克飞 卡尔 10 技
      7 139 蓝耗 78 CD 15 射程随级变化 缺前检且 UNIT_OR_POINT 锁 0x12
      8 War3Server 与 NetworkManager 未注册 /cast /learn /skills
    后续分阶段实现蓝图
      Phase1 修复 build_skill_table 与表结构并补齐服务端/Launcher 注册
      Phase2 接入 CUnit +0x1DC 动态链表与 CheckCanCast 实时探针
      Phase3 完整 -cast 支持 allyhero / point / on off toggle / queue 0x0001
      Phase4 接入 10ms 快照做先手控 救队友 法球不拉仇恨 瞬发防打断
```
