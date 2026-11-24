# 任务：补刀预测用到的引擎事实——逆向核对 + 用实测记录验证

**给**：Antigravity Gemini　**布置时间**：2026-11-24　**工作目录**：`D:\Qt\workspace\War3Analysis`
**布置人**：Claude Opus 5.5（正在调影魔中路 AI 补刀，结果直接用在这里）

## 背景

AI 补刀要预测「我的弹道落地那一刻，这只兵还剩多少血」。代码在 `War3Launcher/hooker/war3hook_ai.cpp`：

| 函数 | 作用 |
|---|---|
| `aiReadAttackInfo` | 读单位攻击结构，拿到伤害骰子、前摇、冷却、当前目标、三个计时器 |
| `aiPredictDamageByAttackers` / `aiSimulateCreepWindow` | 根据在途弹道和周围小兵 / 塔的攻击节奏，模拟未来 2.2 秒落到目标身上的每一下伤害 |
| `aiDamageTypeMult` | 攻击类型 × 护甲类型倍率表 |

实测（2026-11-24，`C:\War3Run\War3Launcher\records\lasthit\sf\*.csv`）：

- 从发令到落地约 1.0~1.1 秒：联机延迟 0.2~0.43 秒 + 前摇 0.40 秒 + 弹道约 0.27 秒。
- 基线局里，「打了没补到」的 16 刀中有 12 刀是早了：落地时兵还剩 1.5~3 倍伤害。
- 也有一批是落地和兵死亡相差不到 0.1 秒、抢输了。
- 有的兵掉血只有 3~4/s，模拟器却预计 1.2 秒内会掉 100 多血。

**模拟器的输入只要有一个是错的，补刀就会系统性偏早或偏晚。** 这次请逐项核对这些输入。

## 要做的事

每项都要列出 `War3Launcher/versions` 下**全部 11 个版本**的 RVA / 偏移（`.agents/rules/war3-gamedll-all-versions.md`），每条结论要有独立证据（反汇编指令、`war3map.j` / SLK 原文行号）。

1. **攻击结构字段**（`aiReadAttackInfo` 用的 `CAbilityAttack` 偏移）
   - `+0x6C/+0x70` 当前目标；`+0x88..+0xAC` 骰子 / 基础 / 加成；`+0x158` BAT；`+0x16C` 前摇；`+0x1B0` 攻速；`+0x1C0`；`+0x1D8` / `+0x1EC` / `+0x200` 三个计时器；`+0x2B8` 武器索引；`+0xF4` 攻击类型。
   - 逐个确认含义。特别是：
     - `+0x1D8` 在移动状态下每 0.5 秒重置（代码注释里写的实测结论）的原因；
     - 「当前目标」是已经开始攻击的目标，还是只是索敌锁定的目标。小兵锁定了、但还没开始打（在走过去、在转身），算不算？这正是「掉血 3/s 却预计掉 100 多」的嫌疑。
2. **弹道什么时候结算伤害**
   - `CMissile` 是在到达那一帧扣血，还是下一帧，或者有额外延迟。
   - 弹道的起点：发射点的 X/Y/Z 偏移（`UnitData` 的 launchX/Y/Z）、目标的命中半径 / 碰撞半径，对实际飞行距离有什么影响。
   - 给出公式：前摇结束 → 扣血，一共多少游戏秒（含小兵近战的「前摇结束即扣血」）。
   - DotA 6.83d 影魔 `Nfir`、远程兵 `edry`/`unec`、攻城车、一塔的弹道速度和弧度。
3. **伤害公式**
   - 英雄 / 小兵的伤害骰子怎么掷（最小、最大、平均）。
   - 护甲减伤公式。
   - 6.83d 小兵的护甲类型码（`+0xE4`）和攻击类型，核对 `aiDamageTypeMult` 那张 7×8 表（注释说是从 `game.dll+0xBEC368` 实机转储的；请核对来源和全版本地址）。
   - 高地丢失（`ChanceToMiss`）对补刀的影响，已有 `war3-lasthit-miss-vision.md`，引用即可。
4. **联机指令延迟**
   - 本地 War3Bot 做主机时，W3GS 锁步一个 turn 是多少毫秒，指令从发出到执行要等几个 turn。
   - 可以看 `War3Bot` 源码（`D:\Qt\workspace\War3Bot`）和 `game.dll` 的 turn 处理。
   - 回答：发令到开始执行的延迟，是固定值加抖动，还是和游戏速度有关？
5. **用实测记录验证**（只读，先复制到你自己的目录）
   - 记录格式见 `War3Launcher/hooker/war3hook_ai_score.inl` 里 `aiLhRecTrace` 上面的注释：`trace` 每 100ms 一行，记英雄前摇 / 冷却 / 目标和每只兵的血与位置；`event` 每只兵死亡一行。
   - 已有脚本：`artifacts/lasthit-combat/lh_miss_classify.py`（漏刀分类）、`flight_measure.py`（量飞行时间）。
   - 用你核对出来的模型重算：从记录里能不能看出小兵的攻击间隔、伤害和预计的一致？「早了」的那些刀，偏差主要来自哪一项输入？

## 红线

1. **不要开游戏、不要连 6120 端口**：Claude 正在这台机器上跑补刀实机测试。
2. **不要改** `War3Launcher/hooker`、`managers`、`shared` 下的源码，也不要动 `build` 目录。需要改代码的地方写进文档的「建议改法」，由 Claude 来改。
3. `C:\War3Run` 下的文件只读，分析时先复制出来。
4. 不 commit / push。拿不出证据的结论标 ❓。

## 交付

| 交付物 | 位置 |
|---|---|
| 正文（结论放最前面：哪些输入是对的、哪些错了、该怎么改；文件开头写分析模型 / 目的 / 命名 / 时间 / 验证状态） | `analyses/war3-lasthit-prediction-engine-facts.md` |
| 思维导图 | `analyses/war3-lasthit-prediction-engine-facts-mindmap.md` |
| 扫描脚本、全版本 RVA 表、验证脚本和输出 | `artifacts/lasthit-prediction/` |

最重要的是第 1、2 项，以及第 5 项里「早了的偏差来自哪一项」，请先做这几项。
