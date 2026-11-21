# Warcraft III 补兵（正补 / 反补）战斗与伤害逆向 — 思维导图

> 分析模型：Gemini 4 Neon ｜ 时间：2026-11-20 ｜ 正文：[`war3-lasthit-combat-data.md`](./war3-lasthit-combat-data.md)

```mermaid
mindmap
  root((War3 game.dll<br/>补兵战斗与伤害逆向))
    1. 攻击属性 CAbilityAttack
      入口 CUnit + 0x1E8 (1.25~1.27)
      伤害公式
        diceCount +0x88 / diceSides +0x94
        dmgBase +0xA0 (含英雄主属性)
        dmgBonus +0xAC (绿字加成)
        Min=Base+Bonus+Dice / Max=Base+Bonus+Dice*Sides
      节拍与攻速
        BAT +0x158 / dmgpt +0x16C / backSw +0x190
        IAS倍率 +0x1B0 / 减速 +0x1C0 (钳制 0.2~5.0)
      武器与射程
        weaponType +0xDC (1=近战, >=3=弹道)
        attackType +0xF4 (0..6)
        range +0x258 / acquire +0x244 / activeIdx +0x2B8
      弹道速度
        不在 CAbilityAttack
        在 CUnitUI +0x5C (UnitFunc.txt)
        发射时写入 CMissile +0x54
    2. 伤害计算与护甲
      CUnit 护甲
        总护甲 +0xE0 (float)
        护甲类型 +0xE4 (0..7, 小兵=7, 攻城车=3)
      CalcArmorReduction
        1.27 0x64FBF0 / 1.26 0x26D270
        正甲 (0.06*A)/(1+0.06*A)
        负甲 截断-20 查 NegArmorTable (1.27 0xBEC2F8)
      攻防系数表 7x8
        GetDamageBonus (1.27 0x64D7F0 / 1.26 0x26D300)
        表首址 1.27 0xBEC368 / 1.26 0xAB4358
        英雄打城甲(攻城车) 0.50x
    3. 攻击目标与阶段
      当前指令 CUnit +0x19C/+0x1A0 → OrderId +0x24
      当前攻击目标 CAbilityAttack +0x6C/+0x70
      三阶段 CAgentTimer 纯只读
        前摇 +0x1EC (0xD01B1) > 0 → 抬手中
        后摇 +0x200 (0xD01B2) > 0 → 已出手
        冷却 +0x1D8 (0xD01B0) > 0 → 冷却中
        rem = *(node+4) - *(clk+0x40)
    4. 飞行中弹道 CMissile
      枚举 g_AgentManager (1.27 0xBE40A8 / 1.26 0xAB7788)
        遍历同步代理表 按4个Missile虚表过滤
      弹道字段 (1.26 & 1.27 一致)
        来源 +0x2C/+0x30 / 目标 +0xA0/+0xA4
        主伤害(已掷骰) +0x44 / 副伤害 +0x4C
        弹速 +0x54 / 攻击类型 +0x58 / 弧度 +0x8C
        3D位置 CBhPoProjectile +0x78
    5. 伤害结算入口
      CUnit::OnDamage (vtable +0x120)
        1.27 0x67DC40 / 1.26 0x2A40D0
      SDamageInfo
        src +0x00 / flags +0x0C / dmg +0x10 / type +0x14 / atkType +0x20
      FireDamagedEvent 1.27 0x67F340 → ModifyLife vtable+0x128
    6. 击杀归属与赏金
      lastAttacker CUnit +0x250/+0x254
      CUnit::OnDeath (1.27 0x67E9D0 / 1.26 0x2A7E60)
        IsEnemy(killer, victim) 1.27 0x66E630
        敌军(正补) → AwardBounty 0x64CF40 (+%d跳钱)
        友军(反补) → 跳过赏金与经验
      DotA计分板 GetKillingUnit (1.27 0x1E2DC0)
    7. 补刀算法升级建议
      实时读英雄最小伤害×护甲×攻防系数 (解决攻城车半伤)
      动态前摇 dmgpt/IAS + 真实弹速
      落地血 = 当前血 + 回血 - 在飞弹道伤害 - 前摇中单位伤害
      0 < 落地血 <= 本刀保守伤害 时出手
```
