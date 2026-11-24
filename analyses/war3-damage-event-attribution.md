# War3 伤害事件归属入口（全 11 版）与 DotA 6.83d 对线计分地图规则

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 为对线计分 v2（[`dota-ai-laning-score-v2.md`](./dota-ai-laning-score-v2.md)）提供全 11 版本 `Game.dll` 的统一伤害结算入口、`EVENT_UNIT_DAMAGED` 派发点与只读 Inline Hook 方案（精确拿到「谁、对谁、造成多少最终伤害」），并核实 6.83d 经验/反补、神符、眼与敌方等级可见性规则 |
| **命名方式** | 正文 `war3-damage-event-attribution.md`；导图 `war3-damage-event-attribution-mindmap.md`；产物目录 `artifacts/damage-event/` |
| **分析时间** | 2026-11-24 |
| **验证状态** | **全 11 版 `Game.dll` 静态反汇编交叉核验 + DotA 6.83d `war3mapMisc.txt` / `Units_UnitBalance.slk` / `Scripts_war3map.j` 源码核验**；遵循红线未开游戏、未连 6120、未改 `War3Launcher` 源码；已提供实机对比脚本留给测试机运行；无直接证据项标 `❓` |
| **配套产物** | [`artifacts/damage-event/`](../artifacts/damage-event/)（`damage_all11_rva.txt`、`verify_exact_all11.txt`、`disasm_damage_127.txt`、`verify_ondamaged_127.txt`、`dota683d_slices.txt`、`verify_live_damage_hook.py`） |
| **配套思维导图** | [`war3-damage-event-attribution-mindmap.md`](./war3-damage-event-attribution-mindmap.md) |

---

## 零、核心结论：全 11 版 RVA 总表与最佳只读挂钩点

### 0.1 一句话结论
- **所有伤害来源**（近战普攻、远程弹道、防御塔攻击、技能脚本 `UnitDamageTarget` 如影压）最终全部汇入 **`CUnit::ApplyDamage`**（`CUnit vtable + 0x120`）。
- 在护甲减伤、7×8 攻防表、虚无、魔免与减伤技能全部算完后，`CUnit::ApplyDamage` 调用 `CUnit::NotifyDamaged`，后者立即调用 **`CUnit::DispatchEventUnitDamaged`**（内部 `push 0x00080234` 派发 `EVENT_UNIT_DAMAGED`）。
- **最佳挂钩点：`CUnit::DispatchEventUnitDamaged`**（而非 `NotifyDamaged` 或 `ApplyDamage`）：
  1. **跨全部 11 个版本调用约定完全统一**：标准 `__thiscall`——`ecx = target (CUnit*)`、`[esp+4] = const float* pFinalDamage`（**护甲/魔抗结算后的最终伤害**，即 `GetEventDamage()` 返回值）、`[esp+8] = attacker (CUnit*)`（即 `GetEventDamageSource()` 返回值）。相比之下，`NotifyDamaged` 在 1.22~1.26 为非标准自定义寄存器传参（`esi/edi/ebx`），而 `ApplyDamage` 入口拿到的是护甲减伤前的原始伤害。
  2. **全部 11 版本入口前 5~7 字节均为无相对跳转的干净指令**，可直接套用 `war3hook_engine.cpp` 的 `installInlineHookEx` 跳板，游戏主线程只读记录，零副作用、不改伤害、不改流程。

### 0.2 全部 11 版本伤害核心函数与原生 RVA 对照表

来源：[`damage_all11_rva.txt`](../artifacts/damage-event/damage_all11_rva.txt)、[`verify_exact_all11.txt`](../artifacts/damage-event/verify_exact_all11.txt)。

| War3 版本 | `CUnit::ApplyDamage` (`vt+0x120`) | `CUnit::NotifyDamaged` | **`CUnit::DispatchEventUnitDamaged`（推荐挂钩点）** | 推荐挂钩字节数与前 7 字节机器码 | `GetEventDamage` | `GetEventDamageSource` | `UnitDamageTarget` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `1.0.17.5988` | `0x19F560` | `0x19FC10` | **`0x1C0290`** | **6 B** `55 8B EC 83 EC 34` (`56`) | `0x2B7C90` | `0x2B7CB0` | `0x2C9840` |
| `1.0.20.6048` | `0x19F560` | `0x19FC10` | **`0x1C0290`** | **6 B** `55 8B EC 83 EC 34` (`56`) | `0x2B7C90` | `0x2B7CB0` | `0x2C9840` |
| `1.20.4.6074` | `0x19F570` | `0x19FC20` | **`0x1C0300`** | **6 B** `55 8B EC 83 EC 34` (`56`) | `0x2B7DB0` | `0x2B7DD0` | `0x2C9960` |
| `1.21.0.6263` | `0x1A2730` | `0x1A2DE0` | **`0x1C34C0`** | **6 B** `55 8B EC 83 EC 34` (`56`) | `0x2BB380` | `0x2BB3A0` | `0x2CCF30` |
| `1.22.0.6328` | `0x2A3540` | `0x29ABE0` | **`0x2961C0`** | **7 B** `6A FF 68 E8 48 80 6F` | `0x3BCEE0` | `0x3BCF00` | `0x3C1AF0` |
| `1.23.0.6352` | `0x2A4A80` | `0x29C120` | **`0x297700`** | **7 B** `6A FF 68 48 87 81 6F` | `0x3BEC00` | `0x3BEC20` | `0x3C3810` |
| `1.24.1.6374` | `0x2A4B40` | `0x29C1E0` | **`0x2977C0`** | **7 B** `6A FF 68 78 79 82 6F` | `0x3C46C0` | `0x3C46E0` | `0x3C92D0` |
| `1.24.4.6387` | `0x2A4BF0` | `0x29C250` | **`0x297830`** | **7 B** `6A FF 68 38 7A 82 6F` | `0x3C4780` | `0x3C47A0` | `0x3C9390` |
| `1.25.1.6397` | `0x2A3EA0` | `0x29B500` | **`0x296AE0`** | **7 B** `6A FF 68 68 4F 81 6F` | `0x3C3A10` | `0x3C3A30` | `0x3C8620` |
| `1.26.0.6401` | `0x2A40D0` | `0x29B730` | **`0x296D10`** | **7 B** `6A FF 68 98 51 81 6F` | `0x3C3C40` | `0x3C3C60` | `0x3C8850` |
| `1.27.0.52240` | `0x67DC40` | `0x67F340` | **`0x65E010`** | **5 B** `55 8B EC 6A FF` (`68 50`) | `0x1E21D0` | `0x1E21F0` | `0x1FAB70` |

> 注：1.22~1.26 入口为 `push -1; push SEH_handler`（绝对地址 4 字节，无相对偏移重定位风险），`installInlineHookEx` 拷贝 7 字节到跳板后直接跳回 `rva + 7` 即可安全执行。

---

## 一、伤害结算的统一入口（`CUnit::ApplyDamage`）

### 1.1 多源汇聚证据（1.27 反汇编）
- **远程弹道 / 塔攻击**：`CMissile::OnImpact`（`0x6B2450`）→ `CMissile::ApplyDamage`（`0x6B1500`）→ 尾部 `0x6B163E` 执行 `mov ecx, ebx; mov edx, [ebx]; call [edx + 0x120]` → **`0x67DC40`**（`CUnit::ApplyDamage`）。
- **技能脚本 `UnitDamageTarget`**（`0x1FAB70`，影压、触发伤害等）：构造栈上 `CDamageData`（`0x685690`）→ 尾部 `0x1FABF7` 执行 `mov ecx, esi; mov edx, [esi]; call [edx + 0x120]` → **`0x67DC40`**。
- **近战普攻**：`CAbilityAttack` 命中结算同样经目标虚表 `+0x120` 汇入 `CUnit::ApplyDamage`（与弹道/脚本同入口；未单独展开近战 `CAbilityAttack` 调用点，标 `❓`，但经 `DispatchEventUnitDamaged` 挂钩已覆盖所有触发 `EVENT_UNIT_DAMAGED` 的近战伤害）。

### 1.2 `CUnit::ApplyDamage` 调用约定与参数布局
- **调用约定**：`__thiscall`（`ret 0x10`）
  - `ecx`：`CUnit* target`（受击目标单位）
  - `[esp+0x04]`：`float* outActualDamage`（输出最终结算伤害）
  - `[esp+0x08]`：`CDamageData* dmgData`（**护甲减伤前**输入结构）：
    - `+0x00`：`CUnit* attacker`（来源单位指针，可为 `NULL` 如环境/自伤）
    - `+0x0C`：`uint32_t flags`（`0x01`=远程、`0x04`=丢失/0伤、`0x100`=攻击伤害等）
    - `+0x10`：`float rawDamage`（护甲/魔抗减伤**之前**的原始伤害）
    - `+0x14`：`uint32_t damageTypeMask`（`1 << damageType`，如物理 `0x10`）
    - `+0x20`：`uint32_t attackType`（`0..6`：`Spells/Normal/Pierce/Siege/Magic/Chaos/Hero`）
    - `+0x24`：`uint32_t weaponType`（音效/命中特效类型）
  - `[esp+0x0C]`：`uint32_t flag1`（弹道/吸血标志）
  - `[esp+0x10]`：`uint32_t flag2`（通常为 `0`）

### 1.3 内部结算顺序（1.27 `0x67DC40..0x67E130`）
1. 无敌/死亡/魔免过滤（`[edi+0x5C] & 0x100` 等）→ 若免疫则走 0 伤分支调用 `NotifyDamaged(&0.0f)`。
2. 护甲减伤（`0x67DFC2: call 0x64FBF0`，读 `[edi+0xE0]` 护甲值，调用 `DefenseArmor = 0.06` 公式）。
3. 7×8 攻防倍率表（`0x67E029: call 0x64D7F0`，按 `attackType` × `[edi+0xE4]` 护甲类型查表乘算）。
4. 虚无额外法伤倍率（`0x67E07A: [esi*4 + 0xBEC34C]`）。
5. **调用 `CUnit::NotifyDamaged`（`0x67E126: call 0x67F340`）**：此时 `[ebp+0x0C]` 已是**护甲、攻防表、虚无、魔免全部结算完毕后的最终伤害**。

---

## 二、`EVENT_UNIT_DAMAGED` 的派发点与字段写入

### 2.1 `GetEventDamage` / `GetEventDamageSource` 读哪里？（1.27 反汇编）
- `GetEventDamage`（`0x1E21D0`）：调用 `0x1E5D70` 取当前 JASS 事件对象指针 `eax`，直接返回 **`[eax + 0x30]`**（`float` 最终伤害）。
- `GetEventDamageSource`（`0x1E21F0`）：取同一事件对象 `eax`，将 **`[eax + 0x34]` / `[eax + 0x38]`**（8 字节 Agent 句柄标签）解引用为 `CUnit*` 并转为 JASS `unit` 句柄返回。

### 2.2 数据在哪里写入？（1.27 `CUnit::DispatchEventUnitDamaged` @ `0x65E010`）
- `CUnit::NotifyDamaged`（`0x67F340`）入口前 4 条指令即调用 `CUnit::DispatchEventUnitDamaged`：
  ```asm
  6F67F350: push dword ptr [edi]   ; arg2 = attacker CUnit*
  6F67F352: push ebx               ; arg1 = const float* pFinalDamage
  ; ecx = target CUnit*
  6F67F353: call 6F65E010          ; CUnit::DispatchEventUnitDamaged
  ```
- 在 `0x65E010` 内部：
  - `0x65E040`: `push 0x00080234`（事件 ID = `EVENT_UNIT_DAMAGED`）。
  - `0x65E0E4..0x65E0ED`: 将 `attacker` 的 Agent 标签写入事件对象 **`[esi + 0x34]` / `[esi + 0x38]`**。
  - 紧随其后将 `*pFinalDamage` 写入 **`[esi + 0x30]`** 并向该单位已注册的所有 `EVENT_UNIT_DAMAGED` 触发器派发。
- **跨版本一致性核验**：已在 1.0.17（`0x19FC1C..0x19FC22`）、1.22~1.26（`NotifyDamaged` 入口）与 1.27（`0x67F350..0x67F353`）全部验证 `DispatchEventUnitDamaged` 均为相同 `__thiscall(target, pFinalDamage, attacker)` 签名。

---

## 三、只读挂钩方案（适配 `war3hook_engine.cpp`）

### 3.1 挂钩设计原则
- **位置**：`Game.dll + g_offsetForGameUnitDispatchDamaged`（即上表 `CUnit::DispatchEventUnitDamaged` RVA）。
- **线程**：War3 游戏主逻辑线程（每帧同步调用，无跨线程锁竞争）。
- **只读与零副作用**：回调只读取 `target`、`attacker` 和 `*pFinalDamage`（过滤 `finalDmg <= 0.001f` 的 0 伤事件），写入内存环形队列或直接累计到对线计分器；**绝不修改任何参数或寄存器，也不在回调内调 JASS 原生**（防止破坏 JASS VM 事件栈），随后无条件跳转到 `installInlineHookEx` 生成的跳板执行原函数。

### 3.2 建议伪代码（供 Claude 接入 `war3hook_offsets.cpp` / `war3hook_ai_score.inl`）

```cpp
// 1. 原函数类型（全 11 版统一 __thiscall；用 __fastcall + dummy edx 承接 ecx）
typedef void (__fastcall *FnDispatchUnitDamaged)(
    uint32_t targetUnit, uint32_t /*edx_unused*/,
    const float *pFinalDamage, uint32_t attackerUnit);

static FnDispatchUnitDamaged g_origDispatchUnitDamaged = nullptr;

// 2. 只读过滤与累计（在游戏主线程，全程只读内存 + SEH 保护）
static void __fastcall hookDispatchUnitDamaged(
    uint32_t targetUnit, uint32_t edxUnused,
    const float *pFinalDamage, uint32_t attackerUnit)
{
    if (g_aiScoreRunning && targetUnit && pFinalDamage) {
        float dmg = 0.0f;
        __try { dmg = *pFinalDamage; } __except (EXCEPTION_EXECUTE_HANDLER) { dmg = 0.0f; }
        if (dmg > 0.01f && dmg < 50000.0f) {
            // 仅关注：目标是我方英雄（受伤扣分），或来源是我方英雄且目标是敌方英雄本体（对英雄伤害加分）
            // 注意：此处只读 CUnit 内存（typeId、owner、flags），不调 JASS 原生！
            aiScoreOnDamageEvent(targetUnit, attackerUnit, dmg);
        }
    }
    // 原样透传给跳板，不改伤害、不改流程
    g_origDispatchUnitDamaged(targetUnit, edxUnused, pFinalDamage, attackerUnit);
}
```

- **关于「0 伤 / 抵挡 / 闪避」**：`ApplyDamage` 在 0 伤分支也会调用 `NotifyDamaged(&0.0f)`，因此上面 `dmg > 0.01f` 自动滤掉闪避、魔免和 0 伤触发器（DotA 地图常用 0 伤 `UnitDamageTarget` 做技能标记）。
- **关于「超出剩余血量的溢出伤害」**：`DispatchEventUnitDamaged` 收到的 `*pFinalDamage` 是结算后的理论扣血（若目标只剩 15 HP 而塔打 80 伤，此处会报 `80.0f`）。计分器若不想把致死溢出算入受伤，可在 `aiScoreOnDamageEvent` 中与目标当前血量取 `min(dmg, targetCurHp)`（因为 `DispatchEventUnitDamaged` 在真正扣血**之前**触发！）。

---

## 四、区分来源类型（英雄 / 小兵 / 塔 / 其他）与 6.83d 类型码表

在挂钩回调内（不调 JASS 原生、纯内存只读），拿到 `attackerUnit`（`CUnit*`）后可按以下三步无歧义分类：
1. **读 `typeId`**（`*(uint32_t*)(unit + 0x30)`，4CC 整数）：
   - **英雄本体**：4CC 首字节为大写字母（`A`~`Z`，即 `(typeId >> 24) >= 'A' && (typeId >> 24) <= 'Z'`），且**排除幻象**（检查 `CUnit` 标志位或已有 `aiIsIllusion`；若离线统计，也可直接与已记录的敌方英雄本体句柄比对，最稳妥）。
   - **防御塔**：按下方 6.83d 精确类型码匹配（或查 `IsUnitType(u, UNIT_TYPE_STRUCTURE)` 对应结构标志位）。
   - **兵线小兵 / 攻城车**：按下方 6.83d 精确类型码匹配（`owner == 0` 近卫电脑 / `owner == 6` 天灾电脑）。
   - **其余**（野怪、召唤物、泉水、未知 `attacker == 0`）：归为 `other`。

### 6.83d 双方防御塔、兵线小兵与攻城车类型码总表

来源：6.83d `Units_UnitBalance.slk`、`Units_UnitWeapons.slk` 及 [`war3-tower-creep-aggro.md`](./war3-tower-creep-aggro.md)。

| 类别 | 近卫（Radiant / Sentinel）TypeId | 天灾（Dire / Scourge）TypeId | 说明 |
| :--- | :--- | :--- | :--- |
| **一塔 (T1)** | `e00R` (`0x65303052`) | `u00M` (`0x7530304D`) | 1300 HP，射程 700，弹速 750，真视 |
| **二塔 (T2)** | `e011` (`0x65303131`) | `u00D` (`0x75303044`) | 1600 HP，射程 700 |
| **三塔 (T3 高地)** | `e00S` (`0x65303053`) | `u00N` (`0x7530304E`) | 1600 HP，射程 700 |
| **四塔 (T4 基地)** | `e019` (`0x65303139`) | `u00T` / `u00N` ❓ | 近卫已核 `e019`；天灾 T4 码待核 ❓ |
| **近战小兵** | `eaom` / `efon`（超级兵 `e00M` ❓） | `ugho`（超级兵 `u00H` ❓） | 近战，常规等级 Lv3（62 XP） |
| **远程小兵** | `edry` (`0x65647279`) | `unec` (`0x756E6563`) | 远程，常规等级 Lv2（41 XP） |
| **攻城车** | `ebal` (`0x6562616C`) | `umtw` (`0x756D7477`) | 攻城，常规等级 Lv4（88 XP） |
| **假眼 / 真眼** | `o004` (`0x6F303034` / `1865429044`) | `oeye` (`0x6F657965` / `1868921189`) | 双方共用单位码，按 `owner` 区分阵营 |

---

## 五、离线交叉验证与实机验证方案

### 5.1 离线已完成的验证
- **全 11 版 `0x00080234` 唯一性校验**：全部 11 个版本均经 `push 0x00080234` 唯一命中 `CUnit::DispatchEventUnitDamaged`，且均被 `CUnit::NotifyDamaged` 调用，后者在 `CUnit::ApplyDamage` 内均存在 3~4 处调用点（0 伤分支 + 最终结算尾调用），交叉引用闭合率 **11/11 (100%)**。
- **原生函数偏移对称性**：全 11 版 `GetEventDamageSource == GetEventDamage + 0x20` 严格成立。

### 5.2 留给 Claude 的实机验证步骤与脚本
1. 在 `War3Launcher/hooker` 挂上 `hookDispatchUnitDamaged`，按设计稿向 `records/lasthit/sf/*.csv` 写入 `dmg,<t>,<srcType>,<srcHandle>,<tgt>,<dmg>` 行（同时保留方案 A 的每 100ms 血量 trace）。
2. 在测试机跑一局 3~5 分钟影魔中路对线（刻意吃 1 下塔、吃几下小兵、对敌方英雄平 A + 影压各 1 次）。
3. 运行我准备好的对比校验脚本 [`artifacts/damage-event/verify_live_damage_hook.py`](../artifacts/damage-event/verify_live_damage_hook.py)：
   ```powershell
   python D:\Qt\workspace\War3Analysis\artifacts\damage-event\verify_live_damage_hook.py C:\War3Run\War3Launcher\records\lasthit\sf\<最新csv>
   ```
   脚本会自动比对每段时间内「方案 B 累计 `dmg` 行」与「方案 A 血量净降 + 自然回血」，并核对塔伤（~70~100）、小兵伤（~15~25）、影压法伤（~56/131/187/244 扣 25% 魔抗后）是否逐条吻合。

---

## 六、追加核实：DotA 6.83d 对线计分地图规则（经验 / 神符 / 眼 / 等级可见性）

### 6.1 经验规则（100% 由 `war3map.j` 脚本接管，引擎原生经验已关闭）

| 规则项 | 6.83d 精确值 | 源码依据 |
| :--- | :--- | :--- |
| **引擎默认经验范围** | **`0.0`（已禁用！）** | `war3mapMisc.txt:L27`：`HeroExpRange=0.0` |
| **6.83d 实际经验范围** | **`1300 + 25 = 1325` 码** | `Scripts_war3map.j` `ASO` `L13629`（正常击杀）& `BXO` `L14007`（反补）：`1300+25`（25 为碰撞余量） |
| **小兵基础经验** | 近战兵（Lv3）= **`62`**；远程兵（Lv2）= **`41`**；攻城车（Lv4）= **`88`** | `Scripts_war3map.j` `SQI(lvl)` `L3031-3048`：`Lv1=25, Lv2=41, Lv3=62, Lv4=88, Lv5=119, Lv6=155`；`Units_UnitBalance.slk` 核得 `edry=Lv2, ugho=Lv3, umtw=Lv4`（召唤物减半 `L13607`） |
| **多英雄平分规则** | **`总经验 / N`（整数均分）** | `ARO` `L13686`：`FH0 = AMO / NPI`，范围内所有存活敌方英雄本体均分 |
| **反补后对面拿多少经验** | **脚本处理（非引擎）**：敌方**近战英雄 `31 / N`**，敌方**远程英雄 `20 / N`**（固定值，非百分比！） | `ARO` `L13647` 过滤掉己方击杀；由 `BLO` (`L14018`) → `BXO` (`L14005-14012`, `BJO=20, BKO=31`) → `BWO` (`L13996-14000`) 按 `UNIT_TYPE_MELEE_ATTACKER` 发放 |

**1~25 级累计升级经验表**（`war3mapMisc.txt:L61` `NeedHeroXP`，用于将「经验差」折算成小数级）：

| 等级 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 累计 XP | 0 | 200 | 500 | 900 | 1400 | 2000 | 2600 | 3200 | 4400 | 5400 | 6000 | 8200 | 9000 |
| 升级所需 | — | 200 | 300 | 400 | 500 | 600 | 600 | 600 | 1200 | 1000 | 600 | 2200 | 800 |

| 等级 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 累计 XP | 10400 | 11900 | 13500 | 15200 | 17000 | 18900 | 20900 | 23000 | 25200 | 27500 | 29900 | 32400 |
| 升级所需 | 1400 | 1500 | 1600 | 1700 | 1800 | 1900 | 2000 | 2100 | 2200 | 2300 | 2400 | 2500 |

> 换算小数级公式：若当前 `xp` 落在 `[T[L], T[L+1])`，则小数等级为 $L + \frac{\text{xp} - T[L]}{T[L+1] - T[L]}$。

### 6.2 神符拾取与「被对面拿走」判定
- **6.83d 神符物品码**（`Scripts_war3map.j` `GOO` `L17162` & `FMO` `L17073-17090`）：
  - `1227894838` (`I006` 急速)、`1227894840` (`I008` 恢复)、`1227894859` (`I00K` 双倍/幻象)、`1227894839` (`I007` 双倍)、`1227894858` (`I00J` 隐身)、`1227903555` (`I023` 赏金，`FUO` `L17134-17141`：0:00 首符 100 XP / 100 金，此后 `50+5*min` XP / `50+2*min` 金)。
- **拾取者获取与公平性边界**：
  - 引擎/脚本侧：直接吃符触发 `EVENT_PLAYER_UNIT_PICKUP_ITEM`（`G5O` `L17253`），装瓶触发物品使用；脚本内 `GetTriggerUnit()` 知道拾取者，但通知函数 `FMO` 仅向**拾取者同阵营队友**输出聊天提示，不会暴露给迷雾中的对手。
  - **只用本机可见信息的判定**：设计稿中的「**神符从视野内消失时，敌方英雄可见且距符点 `< 200` 码（或敌方英雄随后出现对应神符 Buff）→ 计被对面拿走；否则记不明不扣分**」完全符合公平信息边界（不读迷雾内存）。

### 6.3 眼（`o004` 假眼 / `oeye` 真眼）：创建、排眼击杀者与真视来源
- **创建与死亡**（`Scripts_war3map.j` `L17660-17677`、`L21949-21985`）：
  - 假眼 `o004`（`1865429044`，持续 `420s` / 7 分钟）与真眼 `oeye`（`1868921189`，持续 `240s` / 4 分钟）均作为召唤单位创建；真眼落地时脚本额外调用 `I41(..., 12, x, y, 150)` 给 12 秒小范围视野（`L17675`/`L21983`）。
  - **怎么拿排眼击杀者**：无需额外挂钩 `EVENT_UNIT_DEATH`！接入本文第三节的 **`hookDispatchUnitDamaged`** 后，当 `targetUnit` 的 `typeId` 为 `o004` 或 `oeye` 且 `dmg >= targetCurHp`（致死一击）时，`attackerUnit` 就是精确的排眼击杀者！
- **敌方眼对我方「可见」的条件（真视来源）**：
  - 假眼与真眼自带永久隐身，必须处于我方**真视（True Sight）**范围内才会触发引擎显形（随后 `IsUnitVisible(ward, localPlayer) == true`）：
    1. 我方真眼 `oeye`（常规真视半径 `850` / `900` ❓，未从 `Units_AbilityData.slk` 展开 `oeye` 对应自定义技能码，标 ❓）；
    2. 我方防御塔（一~四塔自带真视，6.83d 常规 `900` 码 ❓）；
    3. 显影之尘（Dust）不显眼（只显单位不显守卫），真视宝石（Gem）显眼。
  - **工程实践**：计分侧无需自己重算真视圈，直接用引擎已有的 **`IsUnitVisible(enemyWard, GetLocalPlayer())`** 即可——只要该敌方眼对我方变为可见，就计入「看见的敌方眼总数」；若随后在致死伤害事件中由我方英雄击杀，即计入「排眼 +3」。

### 6.4 敌方英雄等级的可见性（与真人信息一致性确认）
- 核查 `Scripts_war3map.j` 计分板代码：
  - **局内主计分板 `SG0`**（`L24926+`）：只显示玩家名、击杀/死亡/助攻（K/D/A）和复活倒计时，**不显示敌方英雄等级**。
  - **终局统计板 `SY0`**（`L26085-26155`）：仅在游戏结束后展示双方金钱、等级（`L26121/L26133`）与补刀/反补。
  - **局内左上角头像**：War3 仅显示**己方队友**英雄头像及等级，不显示敌方英雄头像。
- **结论**：局内真人玩家**只能在敌方英雄处于视野内时点击选中它**，从底部信息栏看到其等级（且真人看不到精确 XP 数值，只能看到等级与经验条进度）。因此设计稿中「**敌方 `GetHeroXP` / `GetHeroLevel` 仅在 `IsUnitVisible(enemy, localPlayer) == true` 时采样，进迷雾沿用上次读数**」与真人可获取的时机完全一致，不构成开图信息泄露。
