# 塔 / 小兵索敌与仇恨 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 索引 `war3-tower-creep-aggro` |
| **命名方式** | `war3-tower-creep-aggro-mindmap` |
| **分析时间** | 2026-11-21 |
| **正文** | [`war3-tower-creep-aggro.md`](./war3-tower-creep-aggro.md) |

```mermaid
mindmap
  root((塔与小兵仇恨))
    防御塔
      range_acquire_700
      missile_750
      cool_1_or_0.95
      转火英雄_引擎CallForHelp600
      无地图塔脚本
      Gemini650_非常量
    兵线小兵
      近战_acq500_rng100
      远程_acq600到800_rng500
      攻城_acq800_rng690
      行军_attack_O2
    地图脚本CH2
      半径500绕攻击者
      持续2秒
      排除攻城车
      CV2下攻击令_CX2被打
    引擎常量
      CallForHelp600
      CreepCallForHelp600
      DotA未覆盖Misc
      全版本RVA表
    AI规格
      aggro_draw_500内出手
      后撤超acquire与塔700
      进塔判定_dist小于等于700
```

## 速查

- 塔：**700 = 射程 = 索敌**；弹速 750；**没有 650 常量**
- 卡仇恨脚本：**500 / 2s**（`war3map_3.j` CH2）
- 引擎求救：默认 **600**（野怪等）
- 进塔：`dist(敌兵, 己方T1) ≤ 700`
