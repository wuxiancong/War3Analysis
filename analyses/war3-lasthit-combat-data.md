# Warcraft III 全版本 game.dll 补兵（正补 / 反补）战斗与伤害逆向分析

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon |
| **分析目的** | 逆向 `game.dll` 中与补兵（正补 / 反补）直接相关的 6 类核心战斗数据结构与函数（攻击属性、伤害与护甲计算、当前攻击目标与前摇/后摇阶段、飞行中弹道列表、伤害结算入口、击杀/反补与赏金结算），为 DotA 6.83d AI 提供精确、只读的内存数据，替代经验估算 |
| **命名方式** | `war3-lasthit-combat-data`；配套导图 `war3-lasthit-combat-data-mindmap.md`；只读验证脚本在 `artifacts/lasthit-combat/verify_live_combat.py` |
| **分析时间** | 2026-11-20 |
| **覆盖版本** | `D:\Qt\workspace\War3Launcher\versions\` 下全部 11 个版本（`1.0.17.5988` ~ `1.27.0.52240`）；**1.27.0.52240** 与 **1.26.0.6401** 完成全链路深度逆向，其余 9 个版本经特征码 / 字符串交叉引用定位 |
| **关联文档** | [`dota-ai-human-lasthit-learn-cast.md`](./dota-ai-human-lasthit-learn-cast.md)（现有真人化补刀逻辑）、[`warcraft-iii-ai-unit-attack-lasthit-deny.md`](./warcraft-iii-ai-unit-attack-lasthit-deny.md) |
| **配套思维导图** | [`war3-lasthit-combat-data-mindmap.md`](./war3-lasthit-combat-data-mindmap.md) |

---

## 一、结论先行

| 维度 | 核心结论（1.27.0.52240 / 1.26.0.6401） | 置信度 |
| :--- | :--- | :---: |
| **1. 攻击属性（`CAbilityAttack`）** | `CUnit + 0x1E8` 指向 `CAbilityAttack*`（1.25~1.27 偏移一致）。内含完整双武器数组：骰子数 `+0x88`、骰子面数 `+0x94`、基础伤害（含主属性）`+0xA0`、绿字加成 `+0xAC`、武器类型 `+0xDC`（`1`=近战、`≥3`=弹道）、攻击类型 `+0xF4`、BAT `+0x158`、前摇 `dmgpt` `+0x16C`、后摇 `backSw` `+0x190`、攻速倍率 `1+IAS` `+0x1B0`、射程 `+0x258`、警戒距离 `+0x244`、当前武器槽 `+0x2B8`。**注意**：弹道速度 `Missilespeed` 不在 `CAbilityAttack` 中，而保存在 `*UnitFunc.txt` 加载的 `CUnitUI + 0x5C`，发射时拷贝到 `CMissile + 0x54`。 | **高** |
| **2. 伤害计算与护甲** | `CUnit + 0xE0` = 当前总护甲（`float`），`CUnit + 0xE4` = 护甲类型（`0..7`）。`CalcArmorReduction`（1.27: `0x64FBF0` / 1.26: `0x26D270`）实现正甲 `(k·A)/(1+k·A)`（`k = Misc/DefenseArmor = 0.06`）与负甲查表（**截断上限 `-20`**，表首址 1.27: `0xBEC2F8` / 1.26: `0xAB4300`）。攻击×护甲 7×8 浮点系数表由 `GetDamageBonus`（1.27: `0x64D7F0` / 1.26: `0x26D300`）懒加载并常驻内存（1.27: `0xBEC368` / 1.26: `0xAB4358`）。 | **高** |
| **3. 正在打谁与攻击阶段** | 当前指令在 `CUnit + 0x19C/+0x1A0`（`CAgentPtr<COrder>`，`COrder + 0x24 = OrderId`）；当前攻击目标在 `CAbilityAttack + 0x6C/+0x70`（`CAgentPtr<CWidget>`）。攻击动作由 3 个 `CAgentTimer` 驱动：`+0x1EC`（前摇/伤害点 `0xD01B1`）、`+0x200`（后摇 `0xD01B2`）、`+0x1D8`（冷却 `0xD01B0`）。剩余时间可通过 `node = *(timer+0x0C); rem = *(float*)(node+4) - *(float*)(*(node+0x0C)+0x40)` **纯只读无调用**计算。 | **高** |
| **4. 飞行中弹道（`CMissile`）** | 所有存活 `CMissile`（及子类 `CMissileSplash` / `CMissileBounce` / `CMissileLine`）均注册在全局 `g_AgentManager`（1.27: `0xBE40A8` / 1.26: `0xAB7788`）的同步代理数组中，按 vtable 过滤即可 O(N) 枚举。每个弹道可读：来源 `+0x2C/+0x30`、目标 `+0xA0/+0xA4`、主伤害（已掷骰）`+0x44`、副伤害 `+0x4C`、弹速 `+0x54`、弧度 `+0x8C`、3D 位置接口 `+0x78`（`CBhPoProjectile`）。 | **高** |
| **5. 伤害结算入口** | `CUnit::OnDamage` 位于 `CUnit` 虚表 `+0x120`（1.27: `0x67DC40` / 1.26: `0x2A40D0`），参数 `(outActualDmg*, SDamageInfo*, ...)`。`SDamageInfo` 含来源 `+0x00`、标志 `+0x0C`、伤害值 `+0x10`（原地乘以护甲与攻防系数）、伤害类型掩码 `+0x14`、攻击类型 `+0x20`。结算完触发 `EVENT_UNIT_DAMAGED`（1.27: `0x67F340`）并经 `CUnit::ModifyLife`（虚表 `+0x128`）扣血。 | **高** |
| **6. 击杀归属与赏金** | `CUnit::OnDamage` 扣血前将攻击者写入 `CUnit + 0x250/+0x254`（`lastAttacker`）。血量归零后进入 `CUnit::OnDeath`（1.27: `0x67E9D0` / 1.26: `0x2A7E60`），调 `IsEnemy(killer, victim)`（1.27: `0x66E630`）：**敌军（正补）**→ 调 `CUnit::AwardBounty`（1.27: `0x64CF40`）检查 `PLAYER_STATE_GIVES_BOUNTY`（`player+0xB0`）、掷 `bountyplus + dice·d(sides)` 加钱并弹 `+%d` 漂浮文字；**友军（反补）**→ 直接跳过赏金与经验。地图层 `GetKillingUnit`（1.27: `0x1E2DC0`）驱动 DotA 正补/反补计分板。 | **高** |

---

## 二、逐项详细逆向结果

### 1. 攻击属性（`CAbilityAttack` / `'Aatk'`）

#### 1.1 获取路径与结构布局（1.26.0.6401 & 1.27.0.52240 一致）
从 `GetUnitAcquireRange` → `CUnit::GetAcquireRange`（1.27: `0x666A20` / 1.26: `0x276A00`）反汇编确认：
- `CAbilityAttack* atk = *(CAbilityAttack**)((char*)pUnit + 0x1E8);`
- 若 `atk == nullptr`，该单位无攻击能力。
- 1.27 与 1.26 的 `CAbilityAttack` 构造函数（1.27: `0x4747F0` / 1.26: `0x0CE1C0`）成员初始化偏移完全一致。

`CAbilityAttack` 双武器字段（`idx = *(uint32_t*)(atk + 0x2B8)`，取值 `0`=攻击1 / `1`=攻击2）：

| 偏移 | 类型 | 含义 | 对应 SLK / 备注 | 验证依据（1.27 RVA） |
| :--- | :--- | :--- | :--- | :--- |
| `+0x6C / +0x70` | `CAgentPtr<CWidget>` | 当前攻击目标代理指针 | 经 `ResolveAgentPtr` 解析为 `CWidget*` | `0x47DB99`（炮塔/朝向追踪） |
| `+0x88 + idx*4` | `int32_t` | 骰子数 `diceCount[idx]` | `dice1` / `dice2`（数组头 `+0x84` 存长度 `2`） | `GetMinDamage` `0x47CAD0` |
| `+0x94 + idx*4` | `int32_t` | 骰子面数 `diceSides[idx]` | `sides1` / `sides2` | `GetMaxDamage` `0x47CA70` |
| `+0xA0 + idx*4` | `int32_t` | 基础伤害 `dmgBase[idx]` | `dmgplus1` / `dmgplus2`（**英雄已自动加上主属性值**） | `GetMinDamage` `0x47CAD0` |
| `+0xAC + idx*4` | `int32_t` | 绿字加成伤害 `dmgBonus[idx]` | 装备 / 光环 / Buff 提供的附加攻击力 | `GetMinDamage` `0x47CAD0` |
| `+0xBC + idx*0x10` | `float` | 溅射全伤半径 | `Farea1`（`CFloatWithBounds` 值在 `+4`） | `0x477679` |
| `+0xDC + idx*4` | `uint32_t` | 武器类型 `weaponType[idx]` | `weapTp1`：`1`=近战(`normal`), `2`=瞬发(`instant`), `3`=炮火, `4`=炮火直线, `5`=弹道(`missile`), `6`=溅射弹道, `7`=弹射, `8`=直线弹道 | `0x47AD9B` |
| `+0xF4 + idx*4` | `uint32_t` | 攻击类型 `attackType[idx]` | `atkType1`：`0`=法术/未知, `1`=普通, `2`=穿刺, `3`=攻城, `4`=魔法, `5`=混乱, `6`=英雄 | UI 面板 `0x3B720A` |
| `+0x110 + idx*0x10` | `float` | 溅射中伤半径 | `Harea1` | `0x477688` |
| `+0x134 + idx*0x10` | `float` | 溅射小伤半径 | `Qarea1` | `0x47768E` |
| `+0x158 + idx*8` | `float` | 基础攻击间隔 `BAT[idx]` | `cool1` / `cool2`（`CFloat` 位于 `+0x154 + idx*8`） | `GetCooldown` `0x47B1A0` |
| `+0x16C + idx*0x10` | `float` | 攻击前摇 `damagePoint[idx]` | `dmgpt1` / `dmgpt2`（`CFloatWithBounds` 位于 `+0x168`） | `StartAttackTimers` `0x47FA84` |
| `+0x190 + idx*0x10` | `float` | 攻击后摇 `backswing[idx]` | `backSw1` / `backSw2`（`CFloatWithBounds` 位于 `+0x18C`） | `StartBackswing` `0x47F93F` |
| `+0x1B0` | `float` | 当前攻速倍率 `attackSpeedMult` | `1.0 + IAS`（含敏捷 `0.01/点` + 装备/光环；钳制于 `[0.20, 5.00]`） | `GetAttackSpeedMult` `0x47AF40` |
| `+0x1C0` | `float` | 攻速减速增量 `slowPenalty` | 负值减速（如冰甲/霜冻）；计算实际冷却时叠加 | `0x47AFAF` |
| `+0x1C4` | `CAgentTimer` | 重复攻击 / 自动索敌计时器 | 20 字节计时器结构 | `0x47A728` |
| `+0x1D8` | `CAgentTimer` | **攻击冷却计时器**（事件 `0xD01B0`） | 周期 = `BAT / clamp(IAS, 0.2, 5.0)` | `0x47892C`, `0x47FA5C` |
| `+0x1EC` | `CAgentTimer` | **攻击前摇计时器**（事件 `0xD01B1`） | 周期 = `dmgpt / clamp(IAS, 0.2, 5.0)` | `0x47899D`, `0x47FACB` |
| `+0x200` | `CAgentTimer` | **攻击后摇计时器**（事件 `0xD01B2`） | 周期 = `backSw / clamp(IAS, 0.2, 5.0)` | `0x47F9E0` |
| `+0x244` | `float` | 主动警戒距离 `acquireRange` | `acquire` | `CUnit::GetAcquireRange` `0x666A3C` |
| `+0x258 + idx*8` | `float` | 攻击射程 `attackRange[idx]` | `rangeN1` / `rangeN2` | `0x47ADDC` |
| `+0x2B8` | `uint32_t` | 当前激活武器索引 `activeWeaponIdx` | `0` 或 `1` | `0x47B200` |

#### 1.2 伤害范围、实际冷却与弹道速度公式
由 `0x47CAD0` / `0x47CA70` / `0x47AF40` / `0x47B1A0` 反汇编直接还原：
$$\text{MinDmg} = \text{dmgBase} + \text{dmgBonus} + \text{diceCount}$$
$$\text{MaxDmg} = \text{dmgBase} + \text{dmgBonus} + \text{diceCount} \times \text{diceSides}$$
$$\text{EffMult} = \text{clamp}(\text{attackSpeedMult} + \min(0, \text{slowPenalty}),\ 0.20,\ 5.00)$$
$$\text{EffCooldown} = \frac{\text{BAT}}{\text{EffMult}}, \qquad \text{EffWindup} = \frac{\text{dmgpt}}{\text{EffMult}}, \qquad \text{EffBackswing} = \frac{\text{backSw}}{\text{EffMult}}$$

- **近战 / 远程标志**：`weaponType == 1` 为近战（伤害在前摇结束瞬间直接调用 `CUnit::OnDamage`，无弹道）；`weaponType >= 3` 为弹道攻击。
- **弹道速度（`Missilespeed`）来源**：逆向 `"Missilespeed"` 交叉引用（1.27: `0x338583`, `0x338C43`）发现，War3 将 `Missilespeed` 与 `Missilearc` 归类在单位表现表 `CUnitUI`（从 `*UnitFunc.txt` 读取，偏移 `CUnitUI + 0x5C` = `Missilespeed`，`+0x68` = `Missilearc`），而**不存入 `CAbilityAttack`**。发射弹道时引擎从 `CUnitUI` 读出并写入 `CMissile + 0x54`（速度）与 `CMissile + 0x8C`（弧度）。因此：
  - 静态查表：可从地图 `*UnitFunc.txt` 预建 `typeId → missileSpeed` 映射；
  - 动态运行：一旦发射，直接从飞行中的 `CMissile + 0x54` 读真实弹速。

---

### 2. 伤害计算（护甲、护甲类型、攻击×护甲系数表、减伤公式）

#### 2.1 `CUnit` 护甲字段
在 `CUnit::OnDamage`（1.27: `0x67DC40` / 1.26: `0x2A40D0`）及 UI 护甲面板（1.27: `0x3B6BF1`）中证实：
- **`CUnit + 0xE0`**（`float`）：单位**当前总护甲**（已含基础护甲 + 敏捷护甲 + 绿字装备/光环/减甲 Debuff）。
- **`CUnit + 0xE4`**（`uint32_t`）：单位**护甲类型**（`defenseType`，`0..7`）：
  - `0`=Light（轻甲）、`1`=Medium（中甲）、`2`=Heavy（重甲）、`3`=Fortified（城甲/建筑/攻城车）、`4`=Normal（普通）、`5`=Hero（英雄甲）、`6`=Divine（神圣甲）、`7`=Unarmored（无甲，DotA 兵线近战/远程兵均为 `none`=`7`）。

#### 2.2 护甲减伤函数 `CalcArmorReduction`
1.27 RVA `0x64FBF0`（1.26 RVA `0x26D270`）：
- **正甲 / 零甲（`armor >= 0.0f`）**：
  读取 `Misc/DefenseArmor` 常量 $k$（DotA 6.83d 默认 `0.06`），计算：
  $$\text{reduction} = \frac{k \cdot \text{armor}}{1.0 + k \cdot \text{armor}}, \qquad \text{armorMult} = 1.0 - \text{reduction} = \frac{1.0}{1.0 + k \cdot \text{armor}}$$
- **负甲（`armor < 0.0f`）**：
  截断取整 $n = \min(20,\ -\lfloor \text{armor} \rfloor)$（`cmp eax, 0x14; cmovg eax, ecx`），直接查全局 21 项负甲表 `NegArmorTable[n]`（1.27: `0xBEC2F8` / 1.26: `0xAB4300`），其中 `NegArmorTable[n] = -(1 - (1 - k)^n)`，因此：
  $$\text{armorMult} = 1.0 - \text{NegArmorTable}[n] = 2.0 - (1 - k)^n \quad (n \le 20,\text{ 最大增伤 } 1.710\text{ 倍})$$

#### 2.3 攻击类型 × 护甲类型系数表
由 `GetDamageBonus`（1.27: `0x64D7F0` / 1.26: `0x26D300`）首次调用时从 `Misc/DamageBonus*`（地图 `war3mapMisc.txt` 覆盖）填充到全局 `float[7][8]` 表（每行 8 个 `float` = `0x20` 字节）：
- 行索引 `atkType`：`0`=Spells、`1`=Normal、`2`=Pierce、`3`=Siege、`4`=Magic、`5`=Chaos、`6`=Hero。
- 列索引 `defType`：`0`=Light、`1`=Medium、`2`=Heavy、`3`=Fortified、`4`=Normal、`5`=Hero、`6`=Divine、`7`=Unarmored。
- **1.27.0.52240 内存地址**：表首址（`Spells` 行）`0xBEC368`（`esi` 初始 `0x40` + 基址 `0xBEC328`），因此 `Normal` 行在 `0xBEC388`、`Pierce` 在 `0xBEC3A8`、`Siege` 在 `0xBEC3C8`、`Magic` 在 `0xBEC3E8`、`Chaos` 在 `0xBEC408`、`Hero` 在 `0xBEC428`；虚无系数表 `EtherealDamageBonus[7]` 位于 `0xBEC34C`。
- **1.26.0.6401 内存地址**：`Normal` 行 `0xAB4378`、`Pierce` 行 `0xAB4398`（表首址 `Spells` 行 `0xAB4358`）。

#### 2.4 最终伤害结算顺序（`CUnit::OnDamage` `0x67DC40`）
1. **无敌 / 死亡 / 魔免检查**：检查 `CUnit + 0x5C` 标志位（`0x100` 无敌/死亡）及 `MagicImmunesResistDamage`。
2. **被动技能 / Buff 修正**：遍历 `CUnit + 0x1DC` 技能链表，按优先级 `1..8` 调用各技能虚表 `vtable[0xFC]`（如格挡、暴击、重击、法球、护盾等，原地修改 `SDamageInfo.damage`）。
3. **护甲减伤**：仅当 `damageTypeMask == 0x10`（`DAMAGE_TYPE_NORMAL`，普通物理攻击）且非虚无时，调用 `CalcArmorReduction` 并将 `damage *= (1 - reduction)`。
4. **攻防类型系数**：调用 `GetDamageBonus(atkType, defType)`，若系数 $\ne 1.0$ 则 `damage *= bonus`。
5. **虚无加成**：若目标虚无（`CUnit + 0x158 > 0`），再乘以 `EtherealDamageBonus[atkType]`。
6. **触发受击事件并扣血**：调用 `CUnit::FireDamagedEvent`（1.27: `0x67F340`）→ 记录最后攻击者 `CUnit + 0x250/+0x254` → 调用 `CUnit::ModifyLife`（`vtable + 0x128`）扣除生命值。

---

### 3. 正在打谁与攻击动作阶段

#### 3.1 当前指令与当前攻击目标
- **当前指令**：`GetUnitCurrentOrder`（1.27: `0x1E5F80`）读取 `CUnit + 0x19C/+0x1A0`（`CAgentPtr<COrder>`），经 `ResolveAgentPtr`（1.27: `0x044150`）得到 `COrder*`，`*(uint32_t*)(order + 0x24)` 即 `OrderId`（`0xD000F` = `attack`、`0xD0003` = `smart`）。
- **当前攻击目标**：直接读 `CAbilityAttack + 0x6C/+0x70`（`CAgentPtr<CWidget>`），经 `ResolveAgentPtr` 得到目标 `CUnit*`（验证处：1.27 `0x47DB99`）。

#### 3.2 攻击阶段判定（纯只读 `CAgentTimer` 剩余时间）
从 `CAgentTimer::GetRemaining`（1.27: `0x0438C0`）反汇编确认，读任意 `CAgentTimer` 剩余时间**无需调用游戏函数**，只需 3 次只读解引用：
```cpp
// 纯只读计算 CAgentTimer 剩余秒数（timerAddr = pAbilityAttack + 0x1D8 / 0x1EC / 0x200）
static float readAgentTimerRemaining(uintptr_t timerAddr) {
    uintptr_t node = *(uintptr_t *)(timerAddr + 0x0C);
    if (!node) return 0.0f;                                   // 计时器未激活
    float expireTime = *(float *)(node + 0x04);
    uintptr_t clockMgr = *(uintptr_t *)(node + 0x0C);
    if (!clockMgr) return 0.0f;
    float nowTime = *(float *)(clockMgr + 0x40);
    float rem = expireTime - nowTime;
    return rem > 0.0f ? rem : 0.0f;
}
```
结合 `0x47A728..0x47A76B`（攻击取消逻辑：仅当前摇未结束时取消才会重置冷却）与 `0x47F970..0x47FACB`，可精确判定任意单位当前的攻击阶段：

| 阶段 | 判定条件 | 补刀意义 |
| :--- | :--- | :--- |
| **前摇中（Windup）** | `rem(+0x1EC) > 0` | 单位正在抬手，**再过 `rem(+0x1EC)` 秒就会造成近战伤害或发射弹道**；若此时按 S 会重置 `+0x1D8` 冷却 |
| **已出手 / 后摇中（Backswing）** | `rem(+0x1EC) == 0 && rem(+0x200) > 0` | 本次攻击已命中（近战）或弹道已飞出（远程），处于可走位取消的后摇期 |
| **冷却中（Cooldown）** | `rem(+0x1EC) == 0 && rem(+0x200) == 0 && rem(+0x1D8) > 0` | 距离下一次可抬手还剩 `rem(+0x1D8)` 秒 |
| **就绪（Ready）** | 三者均为 `0` | 随时可立即进入下一次前摇 |

---

### 4. 飞行中的弹道（`CMissile` / `CBulletBase`）

#### 4.1 枚举全部存活弹道（`g_AgentManager`）
从 `LookupAgentById`（1.27: `0x037350` / 1.26: `0x03FA30`）确认全局代理表结构：
- `uintptr_t mgr = *(uintptr_t *)(gameDll + g_AgentManager_RVA);`（1.27: `0xBE40A8` / 1.26: `0xAB7788`）
- 同步代理数组：`entries = *(uintptr_t *)(mgr + 0x0C)`，容量 `count = *(uint32_t *)(mgr + 0x1C)`，每项 8 字节 `{ int32_t tag; CAgentLink *link; }`。
- 有效条件：`tag == -2 && link != nullptr && *(uint32_t*)(link + 0x20) == 0`，对象地址 `obj = *(uintptr_t*)(link + 0x54)`。
- 按虚表 `*(uintptr_t*)obj` 过滤以下 4 个 RTTI 弹道类即可枚举全场所有飞行中弹道（含远程兵、防御塔、远程英雄、攻城车）：
  - `CMissile`（1.27: `0x9B07D0` / 1.26: `0x89147C`）
  - `CMissileSplash`（1.27: `0x9B089C` / 1.26: `0x89154C`）
  - `CMissileBounce`（1.27: `0x9EBE4C` / 1.26: `0x8B5BC4`）
  - `CMissileLine`（1.27: `0xA506BC` / 1.26: `0x9326D4`）

#### 4.2 `CMissile` 核心字段（1.26 与 1.27 完全一致）

| 偏移 | 类型 | 含义 | 验证依据（1.27 RVA） |
| :--- | :--- | :--- | :--- |
| `+0x2C / +0x30` | `CAgentPtr<CUnit>` | **来源单位 `sourceUnit`** | `CMissile::GetSource` `0x6B4A60` |
| `+0x38` | `uint32_t` | 主伤害类型掩码（普攻为 `0x10`） | `CMissile::BuildDamageInfo` `0x6B6ECD` |
| `+0x3C` | `uint32_t` | 副伤害类型掩码（法球/附加伤害） | `0x6B6EDB` |
| `+0x44` | `float` | **主预计伤害 `primaryDamage`**（发射时已掷骰，未乘护甲与攻防系数） | `CMissile::BuildDamageInfo` `0x6B6E9A`, `CMissileBounce` `0x6B2519` |
| `+0x4C` | `float` | 副预计伤害 `secondaryDamage` | `0x6B6EAA` |
| `+0x54` | `float` | **弹道速度 `speed`**（如冰女/远程兵 `900.0`，攻城车 `1100.0`） | `CMissile::Init` `0x6B5915`, `Launch` `0x6B6718` |
| `+0x58` | `uint32_t` | **攻击类型 `attackType`**（`0..6`） | `CMissile::Init` `0x6B591C` |
| `+0x78` | `CBhPoProjectile` | 3D 弹道物理组件（`vtable[0xA0/4]` = `0x3F72F0` 取当前 XYZ） | `CMissile::GetPosition` `0x3F72F0` |
| `+0x8C` | `float` | 弹道弧度 `arc` | `0x6B5831`, `0x6B670F` |
| `+0xA0 / +0xA4` | `CAgentPtr<CWidget>` | **目标单位 `targetUnit`** | `CMissile::GetTarget` `0x6B4AA0` |

> **剩余飞行时间估算**：取弹道当前坐标 `(mx, my)` 与目标坐标 `(tx, ty)`，则 $\Delta t_{\text{rem}} \approx \frac{\sqrt{(tx-mx)^2 + (ty-my)^2}}{\text{speed}}$；预计落地扣血 $= \text{primaryDamage} \times \text{ArmorMult}(\text{target.armor}) \times \text{DamageBonus}[\text{missile.attackType}][\text{target.defType}]$。

---

### 5. 伤害结算入口

- **主入口**：`CUnit::OnDamage`（`CUnit` 虚表 `+0x120`，1.27: `0x67DC40` / 1.26: `0x2A40D0`），调用约定 `__thiscall`：
  ```cpp
  // ecx = CUnit *targetUnit
  // 返回值写入 *outActualDamage
  float *__thiscall CUnit_OnDamage(CUnit *target, float *outActualDamage, SDamageInfo *dmgInfo, int a3, int a4);
  ```
- **`SDamageInfo` 结构**：
  - `+0x00`：`CUnit *sourceUnit`（伤害来源，可能为 `nullptr`）
  - `+0x0C`：`uint32_t flags`（`0x100`=攻击伤害，`0x01`=远程，`0x04`=忽略，`0x10`=零伤害，`0x20`=致死）
  - `+0x10`：`float damageAmount`（入参为原始伤害，函数执行期间被原地更新为最终实际伤害）
  - `+0x14`：`uint32_t damageTypeMask`（`1 << damageType`，`0x10` = `DAMAGE_TYPE_NORMAL`）
  - `+0x20`：`uint32_t attackType`（`0..6`）
- **JASS 路径**：`UnitDamageTarget`（1.27: `0x1FAB70` / 1.26: `0x3C8770`）构造 `SDamageInfo` 后直接调用 `target->vtable[0x120]`。
- **事件派发点**：`CUnit::FireDamagedEvent`（1.27: `0x67F340`，位于 `CUnit::OnDamage` 内部 `0x67E126` 处调用），此时 `dmgInfo->damageAmount` 已是最终折算后的真实扣血量，且 `GetEventDamage` / `GetEventDamageSource` 从该事件上下文取值。若需只读统计每只兵的真实受击，Hook `CUnit::FireDamagedEvent` 或 `CUnit::OnDamage` 返回点最干净。

---

### 6. 击杀归属、反补判定与赏金结算

1. **记录最后击杀者**：`CUnit::OnDamage` 在调用 `ModifyLife` 前（1.27: `0x67E181..0x67E1B4`），若 `CUnit + 0x250/+0x254`（`lastAttacker`）为空则写入 `dmgInfo->sourceUnit`。
2. **死亡与正/反补分流**：血量 $\le 0.405$ 触发 `CUnit::OnDeath`（1.27: `0x67E9D0`，调用点 `0x67EB4D`；1.26: `0x2A7E60`）：
   - 解析 `killer = ResolveAgentPtr(victim + 0x250)`；
   - 调用 **`IsEnemy(killer, victim)`**（1.27: `0x66E630`）：
     - **返回 0（友军击杀 = 反补）**：跳转至 `0x67EB6A`，**直接跳过赏金与经验结算**；
     - **返回非 0（敌军击杀 = 正补）**：更新玩家击杀统计（`0x249390`），检查非幻象（`!(victim->flags & 0x40000000)`），调用 **`CUnit::AwardBounty(victim, killer)`**（1.27: `0x64CF40`）。
3. **赏金结算（`CUnit::AwardBounty` `0x64CF40` → `AwardBountyCore` `0x64CFA0`）**：
   - 检查被击杀单位所属玩家的 `PLAYER_STATE_GIVES_BOUNTY`（`CPlayer + 0xB0`）；
   - 调用 `0x669D60` 按 `CUnitData` 的 `bountyplus (+0x23C) + roll(bountydice +0x224, bountysides +0x230)` 掷出金币；
   - 调用 `0x23DB10` 给击杀者玩家加金币，并在 `0x64D08D` 生成 `"+%d"` 金色漂浮文字（`BountyTextHeight` / `BountyTextColor`）。
4. **DotA 6.83d 地图层统计**：引擎触发 `EVENT_PLAYER_UNIT_DEATH` 后，DotA 脚本经 `GetKillingUnit`（1.27: `0x1E2DC0` / 1.26: `0x3C23F0`）判定敌我，分别递增补刀计数全局变量 `A`（正补）与 `B`（反补），即 `war3hook` 现有的 `g_lastLastHitsValue` / `g_lastDeniesValue`。

---

## 三、全部 11 个版本 `game.dll` RVA / 偏移总表

> ImageBase 均为 `0x6F000000`。`1.0.17.5988 ~ 1.21.0.6263` 编译时未开启 RTTI，故虚表列标为「未确认」，但核心战斗函数已通过字符串交叉引用与调用链完成定位。

### 3.1 核心战斗函数与全局表 RVA

| 版本 | `CUnit::OnDamage` | `CalcArmorReduction` | `NegArmorTable` | `GetDamageBonus` | `DmgBonusNormal` 行 | `AwardBounty_core` | `CUnit::OnDeath` | `g_AgentManager` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1.0.17.5988** | `0x19F560` | `0x19F230` | `0x86F6E8` | `0x19F2C0` | `0x86F368` | `0x1ABC30` | `0x1AC070` | 未确认 |
| **1.0.20.6048** | `0x19F560` | `0x19F230` | `0x870728` | `0x19F2C0` | `0x8703A8` | `0x1ABC30` | `0x1AC070` | 未确认 |
| **1.20.4.6074** | `0x19F570` | `0x19F240` | `0x870748` | `0x19F2D0` | `0x8703C8` | `0x1ABC40` | `0x1AC080` | 未确认 |
| **1.21.0.6263** | `0x1A2730` | `0x1A2400` | `0x8717C0` | `0x1A2490` | `0x871440` | `0x1AEE00` | `0x1AF240` | 未确认 |
| **1.22.0.6328** | `0x2A3540` | `0x26C730` | `0xAA0D08` | `0x26C7C0` | `0xAA0D80` | `0x28AF50` | `0x2A72C0` | 未确认 |
| **1.23.0.6352** | `0x2A4A80` | `0x26DC70` | `0xAB9B58` | `0x26DD00` | `0xAB9BD0` | `0x28C490` | `0x2A8800` | `0xABCFC8` |
| **1.24.1.6374** | `0x2A4B40` | `0x26DD20` | `0xACB158` | `0x26DDB0` | `0xACB1D0` | `0x28C550` | `0x2A88C0` | `0xACE5E0` |
| **1.24.4.6387** | `0x2A4BF0` | `0x26DD80` | `0xACB158` | `0x26DE10` | `0xACB1D0` | `0x28C5C0` | `0x2A8980` | `0xACE5E0` |
| **1.25.1.6397** | `0x2A3EA0` | `0x26D040` | `0xAB4300` | `0x26D0D0` | `0xAB4378` | `0x28B870` | `0x2A7C30` | `0xAB7788` |
| **1.26.0.6401** | **`0x2A40D0`** | **`0x26D270`** | **`0xAB4300`** | **`0x26D300`** | **`0xAB4378`** | **`0x28BAA0`** | **`0x2A7E60`** | **`0xAB7788`** |
| **1.27.0.52240** | **`0x67DC40`** | **`0x64FBF0`** | **`0xBEC2F8`** | **`0x64D7F0`** | **`0xBEC388`** | **`0x64CFA0`** | **`0x67E9D0`** | **`0xBE40A8`** |

### 3.2 关键类虚表、构造函数与 JASS 原生 RVA

| 版本 | `CUnit` vtable | `CAbilityAttack` vtable | `CMissile` vtable | `CMissileSplash` vtable | `UnitDamageTarget` | `GetKillingUnit` | `GetUnitAcquireRange` | `GetUnitCurrentOrder` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1.0.17.5988** | 未确认 | 未确认 | 未确认 | 未确认 | `0x2C9840` | 未确认 | 未确认 | `0x2CB980` |
| **1.0.20.6048** | 未确认 | 未确认 | 未确认 | 未确认 | 未确认 | 未确认 | 未确认 | `0x2C53F0` |
| **1.20.4.6074** | 未确认 | 未确认 | 未确认 | 未确认 | `0x2C9960` | `0x2B5E30` | 未确认 | `0x2C5510` |
| **1.21.0.6263** | 未确认 | 未确认 | 未确认 | 未确认 | `0x2CCF30` | `0x2B9400` | `0x2C4450` | `0x2C8AE0` |
| **1.22.0.6328** | `0x92081C` | `0x8A1414` | `0x880364` | `0x880434` | `0x3C1A10` | `0x3B5930` | `0x3BE720` | 未确认 |
| **1.23.0.6352** | `0x93495C` | `0x8B5554` | `0x8944A4` | `0x894574` | `0x3C3730` | `0x3BD590` | `0x3C0440` | `0x3C2740` |
| **1.24.1.6374** | `0x943A94` | `0x8C468C` | `0x8A35DC` | `0x8A36AC` | `0x3C92D0` | `0x3C2E70` | `0x3C5F00` | `0x3C8200` |
| **1.24.4.6387** | `0x943A94` | `0x8C468C` | `0x8A35DC` | `0x8A36AC` | `0x3C92B0` | `0x3C2F30` | `0x3C5FC0` | `0x3C82C0` |
| **1.25.1.6397** | `0x931934` | `0x8B252C` | `0x89147C` | `0x89154C` | `0x3C8540` | `0x3C21C0` | `0x3C5AE0` | `0x3C7550` |
| **1.26.0.6401** | **`0x931934`** | **`0x8B252C`** | **`0x89147C`** | **`0x89154C`** | **`0x3C8770`** | **`0x3C23F0`** | **`0x3C5D10`** | **`0x3C7780`** |
| **1.27.0.52240** | **`0xA4A704`** | **`0x9ADDBC`** | **`0x9B07D0`** | **`0x9B089C`** | **`0x1FAB70`** | **`0x1E2DC0`** | **`0x1E5F50`** | **`0x1E5F80`** |

### 3.3 跨版本结构体偏移差异摘要

| 字段 | 1.25.1 / 1.26.0 / 1.27.0 | 1.22 ~ 1.24 | 1.0.17 ~ 1.21 |
| :--- | :--- | :--- | :--- |
| `CUnit → CAbilityAttack*` | **`+0x1E8`**（三版本一致） | `+0x1E8`（与 1.25+ 同代架构） | 未确认（1.21 附近为 `+0x19C`） |
| `CUnit → armor / defType` | **`+0xE0` / `+0xE4`** | `+0xE0` / `+0xE4` | 未确认 |
| `CUnit::OnDamage` 虚表槽 | **`+0x120`**（槽 72） | `+0x120` | 未确认 |
| `CAbilityAttack` 伤害/计时器布局 | **1.26 与 1.27 完全一致** | 与 1.26 同源 | 早期布局不同，未确认 |
| `CMissile` 源/目标/伤害/弹速布局 | **1.26 与 1.27 完全一致** | 与 1.26 同源 | 早期布局不同，未确认 |

---

## 四、DotA 6.83d SLK 基准对照与只读实测脚本

### 4.1 地图 SLK 与 `war3mapMisc.txt` 精确对照（`DotA v6.83d.w3x`）

从 `D:\Qt\workspace\War3Bot\war3files\maps\DotA v6.83d.w3x` 直接提取 `Units\UnitBalance.slk`、`Units\UnitWeapons.slk`、`Units\*UnitFunc.txt` 与 `war3mapMisc.txt`：

| 单位 | FourCC | HP / 回血 | 护甲 / 护甲类型 | 武器 / 攻击类型 | 伤害公式（原始） | BAT / 前摇 / 后摇 | 射程 / 弹速 | 赏金 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **水晶室女 (Lv1)** | `Hjai` | `150+16×19=454` / `0.25+` | `2` / `hero(5)` | `missile(5)` / `hero(6)` | `17 + INT(16) + 2d4` = **35~41** | `1.7` / `0.55` / — | `600` / **`900`** | — |
| **近卫/天灾近战兵** | `esen` / `ugho` | `550` / `0.5` | **`2`** / `none(7)` | `normal(1)` / `normal(1)` | `18 + 1d5` = `19~23` | `1.0` / `0.467` / `0.533` | `100` / `0` | `37+1d11` (`38~48`) |
| **近卫/天灾远程兵** | `edry` / `unec` | `300` / `2.0` | **`0`** / `none(7)` | `missile(5)` / `pierce(2)` | `20 + 1d6` = `21~26` | `1.0` / `0.50`(`0.53`) / `0.67`(`0.47`) | `500` / **`900`** | `42+1d11` (`43~53`) |
| **近卫/天灾攻城车** | `ebal` / `umtw` | `550` / `0` | **`0`** / **`fort(3)`** | `missile(5)` / `siege(3)` | `34 + 1d12` = `35~46` | `2.7` / `0.30` / `1.30` | `690` / **`1100`** | `65+1d15` (`66~80`) |

**1 级冰女（`AGI=16` → `IAS = 1.16`）理论计算基准**：
- **实际前摇**：`0.55 / 1.16` = **`0.4741s`（474ms）**；**实际攻速冷却**：`1.7 / 1.16` = **`1.4655s`**。
- **弹道飞行时间**：距离 $d$ 时 $t_{\text{flight}} = d / 900.0$（如 600 距离 = `0.667s`，450 距离 = `0.500s`）。
- **每一下实际伤害理论值**（由 `CalcArmorReduction` 与 `DamageBonusHero` 算得）：
  - 打 **近战兵**（`armor=2`, `defType=7`, 系数 `1.00`, 护甲倍率 `1/1.12 = 0.89286`）：**`31.25 ~ 36.61`**（保守保底 **`31.25`**）。
  - 打 **远程兵**（`armor=0`, `defType=7`, 系数 `1.00`, 护甲倍率 `1.00`）：**`35.00 ~ 41.00`**（保守保底 **`35.00`**）。
  - 打 **攻城车**（`armor=0`, `defType=3(fort)`, `DamageBonusHero[fort] = 0.50`, 护甲倍率 `1.00`）：**`17.50 ~ 20.50`**（保守保底 **`17.50`**，仅为旧版固定假设 `40` 的不到一半！）。

### 4.2 独立只读实测验证脚本

已编写独立的纯只读外部内存验证脚本 [`artifacts/lasthit-combat/verify_live_combat.py`](../artifacts/lasthit-combat/verify_live_combat.py)（仅使用 `OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION)`，不注入、不修改任何进程内存、不触碰 `War3Launcher` / `War3Bot` 源码）。

> [!NOTE]
> 本轮检查时本地未启动 `War3Server` / `war3.exe`（`War3Launcher` 127.0.0.1:6120 未处于对局中），因此**实机对局采集样本待在本地开局后一键运行完成**。静态逆向与 SLK 公式对照已完成全链路交叉验证。

本地开局选冰女 `Hjai` 走到中路后，运行：
```powershell
python D:\Qt\workspace\War3Analysis\artifacts\lasthit-combat\verify_live_combat.py 45
```
脚本将自动输出并保存 `live_verify_results.json`，逐发对比：
1. `Hjai` 与三类小兵内存读取的 `CAbilityAttack` / `armor` / `defType` 与上表 SLK 值；
2. 每次抬手的 `+0x1EC` 计时器前摇读数 vs 实测 `t_missile_spawn - t_windup_start`；
3. 每次弹道的 `+0x54` 弹速与实测飞行时间 `t_impact - t_missile_spawn`；
4. `missile(+0x44) × ArmorMult(target+0xE0) × DamageBonus[6][target+0xE4]` 预测伤害 vs 目标实际掉血量。

---

## 五、补刀算法可以怎么改（面向 `war3hook_ai.cpp` 的升级方案）

当前 `war3hook_ai.cpp` 的核心短板有 4 个：① 用固定参数 `r.damage` 代替真实英雄攻击力且忽略护甲/城甲系数（打攻城车直接差一倍）；② 用两次采样血量差估计 `lossRate`，对远程兵集火、塔弹道、近战兵同步抬手滞后严重；③ 手动传 `windup`/`projectileSpeed` 而不随等级/攻速动态更新；④ 不知道小兵是否刚抬手或已有致命弹道在飞。

接入本次逆向的只读字段后，可将 `aiTickRoutine` 升级为**「物理精确预测模型」**：

### 1. 实时读取英雄真实出手参数（替代手动传参）
每帧从英雄 `CUnit` → `CAbilityAttack (+0x1E8)` 读：
- **保守本刀伤害（必死下限）**：
  $$\text{MyMinDmg}(target) = (\text{dmgBase} + \text{dmgBonus} + \text{diceCount}) \times \text{ArmorMult}(target.\text{armor}) \times \text{DmgBonus}[\text{heroAtkType}][target.\text{defType}]$$
  - 若要更激进（如抢正补），可用期望伤害 $\text{dmgBase} + \text{dmgBonus} + \text{diceCount} \cdot \frac{\text{diceSides}+1}{2}$ 或 25% 分位。
- **动态实际前摇**：$\text{windup} = \frac{\text{dmgpt}}{\text{clamp}(\text{IAS}+\min(0,\text{slow}),\ 0.2,\ 5.0)}$。
- **动态命中总耗时**：$T_{\text{hit}} = t_{\text{approach}} + \text{windup} + \frac{d_{\text{shot}}}{\text{missileSpeed}} + t_{\text{reaction}}$（若英雄当前冷却 `+0x1D8` 未好，需加上 `rem(+0x1D8)`）。

### 2. 确定性「落地时剩余血量」模拟（替代粗糙 `lossRate`）
对每个候选小兵 $u$，在时间窗 $[0,\ T_{\text{hit}}]$ 内做确定性事件累加：
1. **已在飞的弹道伤害 $\Delta H_{\text{missile}}$**：
   遍历 `g_AgentManager` 中所有 `targetUnit == u` 的存活 `CMissile`：
   - 算剩余飞行时间 $t_{\text{rem}} = \text{dist}(\text{missile}, u) / \text{missile.speed}$；
   - 若 $t_{\text{rem}} < T_{\text{hit}}$，累加该弹道真实折算伤害：
     $$\Delta H_{\text{missile}} \mathrel{+}= \text{missile.dmg} \times \text{ArmorMult}(u.\text{armor}) \times \text{DmgBonus}[\text{missile.atkType}][u.\text{defType}]$$
2. **正在前摇中的攻击者伤害 $\Delta H_{\text{windup}}$**：
   对周围满足 `CAbilityAttack.target (+0x6C) == u` 且前摇计时器 `rem(+0x1EC) > 0` 的单位（近战兵、远程兵、防御塔、敌方英雄）：
   - 算其预计命中时间 $t_{\text{arr}} = \text{rem}(+0x1EC) + (\text{isRanged} ? \frac{d}{\text{speed}} : 0)$；
   - 若 $t_{\text{arr}} < T_{\text{hit}}$，累加其期望折算伤害（近战兵/塔的抬手瞬间即可提前预判！）。
3. **回血补偿**：$\Delta H_{\text{regen}} = \text{regenHP} \times T_{\text{hit}}$（从 `CUnit + 0x98` 代理链接 `+0x7C` 直接可读）。
4. **精准出手判据**：
   $$H_{\text{land}} = H_{\text{now}} + \Delta H_{\text{regen}} - \Delta H_{\text{missile}} - \Delta H_{\text{windup}}$$
   - **安全防抢 / 防过早**：若 $H_{\text{land}} \le 0$，说明**不等我出手这只兵就会被在飞弹道打死** → 立即放弃或提前 1 帧抢刀；
   - **必中补刀窗口**：当 **$0 < H_{\text{land}} \le \text{MyMinDmg}(u)$** 时立即出手！
   - **反补额外收益**：同理可判断「己方小兵被敌方远程兵/塔弹道打到 `< 50%` 血的精确时刻」，提前卡好前摇做到「刚下 50% 瞬间反补」。

### 3. 事后精确归因（提升训练/统计准确度）
- 现有 `aiTickRoutine` 通过「金钱跳涨 ≥ 25」和「1.2s 内死亡」猜测是否补到，在多人同时出手或远程兵补掉时容易误判。
- 若在 `CUnit::OnDeath`（或 `CUnit::AwardBounty`）加只读观察点，可直接精确拿到 `(victimHandle, killerHandle, isEnemy, bountyGold)`，100% 区分正补成功、反补成功、被小兵/塔抢刀、被敌方英雄反补。
