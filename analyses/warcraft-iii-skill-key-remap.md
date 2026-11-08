# Warcraft III：技能改键（Skill Hotkey Remap）逆向与实现

> **分析日期**：2026-11-07  
> **问题**：如何实现「技能栏改键」？与已有物品栏改键共用哪些引擎路径？Launcher `skill_map` 应对齐哪些规范键？  
> **目标版本**：Warcraft III **1.26.0.6401**（机制说明）；Launcher Hook 另有 **1.27.0.52240** 偏移表  
> **目标文件**：`game.dll`（12,042,240 字节）  
> **SHA-256**：`6D21BD9A0F9FBC8446F455C9E89AC994FED68174426FE608FCB9BAEFD4DEC53C`  
> **来源**：`War3Launcher/versions/1.26.0.6401/game.dll`  
> **分析副本**：`C:\War3Analysis\samples\1.26.0.6401\game.dll`  
> **工具**：Capstone（`War3Analysis/shared/scripts/dis_rva.py`）；Ghidra `D:\Ghidra_12.1.4`；REA `D:\REA`  
> **产物**：`War3Analysis/artifacts/skill-key-remap/`  
> **关联**：物品栏改键同 Hook `GameModifyInputKeyCodes_`（RVA `0x3821C6`）；物品栏槽序见 [`warcraft-iii-1.26-inventory-six-slot-order.md`](./warcraft-iii-1.26-inventory-six-slot-order.md)  
> **配套导图**：[`warcraft-iii-skill-key-remap-mindmap.md`](./warcraft-iii-skill-key-remap-mindmap.md)  
> **置信度**：按键分发顺序 / `boundKey@+0x5AC` / 4×3 命令卡网格：**高**；规范键 Q/W/E/R/S/D 与 Launcher 槽位对齐：**高**（与 `SettingsManager` 默认值一致）；自定义图改过技能热键后「规范键」方案的完备性：**中**（见局限）

---

## 一、结论摘要

1. **技能与物品共用同一输入入口**：高层输入处理 `HighLevelInputHandler` @ VA `0x6F382150`；Launcher 已在 **`0x6F3821C6`**（`mov eax,[ebx+0x10]`）Hook，把事件对象上的 **War3 键码**改写后再继续分发。  
2. **技能优先于物品**：同一键处理路径中先 `call 0x6F35E390`（技能/命令卡按热键查 UI），未命中再 `call 0x6F360CD0`（物品栏按热键查）。  
3. **匹配方式与物品同构**：都是拿按下键码与 UI 对象上的 **`boundKey`（偏移 `+0x5AC`）** 比较；技能走 **4 列 × 3 行** 命令卡网格，物品走物品栏按钮列表。  
4. **推荐实现（与物品改键同策略）**：不改 `boundKey`、不改物编；在 Hook 里把玩家设定的物理键 **翻译成该槽位的「规范热键」**（默认 `S/D/Q/W/E/R`），让引擎仍用原 `boundKey` 命中。  
5. **优先级**：技能 remap 命中后 **不要再做** 物品 remap，避免 `A→Q` 再被物品表 `Q→Num7` 二次改写。

---

## 二、调用链（1.26）

```text
按键事件对象 key @ [event+0x10]
        │
        ▼
0x6F382150  HighLevelInputHandler
        │
        ├─ 0x6F3821C6  mov eax,[ebx+0x10]   ← War3Launcher Hook 点
        │                 （改写后的键码供后续查询使用）
        │
        ├─ 0x6F38283F  call 0x6F35E390      ← 技能/命令卡 QueryByHotkey
        │         ecx = LocalPlayer… → +0x3C8 命令卡/技能 UI 根
        │         热键参数经栈传入，函数内 ebx = pressedKey
        │         命中 → 发技能/命令；未命中继续
        │
        └─ 0x6F3829AC  call 0x6F360CD0      ← 物品栏 QueryByHotkey
                  ecx = … → +0x3C4 → +0x148 物品栏 UI
                  同样 cmp boundKey(+0x5AC) == pressedKey
```

反汇编摘录见：

- `artifacts/skill-key-remap/disasm_35E390_skill_query.txt`
- `artifacts/skill-key-remap/disasm_3827E0_before_skill_call.txt`
- `artifacts/skill-key-remap/disasm_360CD0_inventory_query.txt`

---

## 三、技能查询 `0x6F35E390`（命令卡 4×3）

伪代码还原：

```c
// this = 命令卡/技能 UI 根（来自 local +0x3C8）
// pressedKey 在栈上，函数序言后装入 ebx
grid = this + 0x154;          // 再 +8 得列数组基
base = grid + 8;              // edi

for (col = 0; col < 4; ++col) {          // edx = 0,4,8,0xC
    row_ptr = base;
    for (row = 0; row < 3; ++row) {      // ecx = 0..2；row_ptr += 0x10
        btn = *(uint32_t*)(*(uint32_t*)row_ptr + col*4);
        if (!btn) continue;
        if (*(btn + 0x94) == 0) continue;     // 可见/可用类标志
        if (*(btn + 0x138) == 0) continue;
        abilityUI = *(btn + 0x190);
        if (*(abilityUI + 0x5AC) == pressedKey)  // boundKey
            return Hit(abilityUI);               // 后续下发命令
        row_ptr += 0x10;
    }
}
return nullptr;
```

**按钮下标**（与常见命令卡一致）：

|  | Col0 | Col1 | Col2 | Col3 |
|--|------|------|------|------|
| Row0 | 0 | 1 | 2 | 3 |
| Row1 | 4 | 5 | 6 | 7 |
| Row2 | 8 | 9 | 10 | 11 |

`index = row * 4 + col`。

物品查询 `0x6F360CD0` 同样：`abilityUI/itemUI + 0x5AC` 与 `ebx`（热键）比较；数据结构是线性列表而非 4×3 网格。

---

## 四、与 Launcher `skill_map` 的槽位对齐

`SettingsManager` 默认：

```text
skillDefaults = {"", "S", "D", "", "Q", "W", "E", "R"}
索引             0    1    2   3    4    5    6    7
```

游戏内设置面板 / 共享内存映射（`war3hook` Sync）：

| UI 控件 | `skill_map` 下标 | 默认规范键 | 命令卡位置 |
|---------|------------------|------------|------------|
| Skill_Key_4 | 1 | S | Row0 Col1 |
| Skill_Key_5 | 2 | D | Row0 Col2 |
| Skill_Key_0 | 4 | Q | Row1 Col0 |
| Skill_Key_1 | 5 | W | Row1 Col1 |
| Skill_Key_2 | 6 | E | Row1 Col2 |
| Skill_Key_3 | 7 | R | Row1 Col3 |

索引 **0、3** 预留为空（UI 未暴露）。字母键在 War3 键码空间即 **ASCII 大写**（`KeyboardHelper::war3BaseKeyFromText`：单字符 → `(quint32)c`）。

规范键常量（实现用）：

```c
// skill_map[i] 命中时写回的引擎键
const int WAR3_SKILL_CANONICAL[8] = {
    0, 'S', 'D', 0, 'Q', 'W', 'E', 'R'
};
```

物品侧对照（已实现）：`Num7/8/4/5/1/2` → `0x108/109/105/106/102/103`。

---

## 五、实现方案

### 5.1 方案 A（推荐，已与物品改键同构）— Hook 改写键码

**位置**：已有 `doSomeThingsBeforeMoveGameModifyInputKeyCodes_`（`war3hook.cpp`）。

**逻辑**：

```text
current = *keyCode
mods = GetAsyncKeyState(Ctrl/Alt/Shift/Win)

if enable_skill_remap:
  在 skill_map[0..7] 中找「base+mods」最佳匹配（修饰键多者优先）
  若命中且 WAR3_SKILL_CANONICAL[i] != 0:
      *keyCode = WAR3_SKILL_CANONICAL[i]
      return  （不再跑物品 remap）

if enable_inventory_remap:
  （现有 6 槽 → Num 内部键逻辑）
```

**开关**：`SharedMemory.enable_skill_remap`（UI「启用技能改键」）。  
**组合键**：与物品相同，`WAR3_KEY_MOD_*` 打包在 `DWORD` 高位；匹配时用 `GetAsyncKeyState` 校验修饰键。

**为何有效**：物编/技能 UI 的 `boundKey` 仍是 Q/W/E/R/…；玩家按 A 时 Hook 先改成 Q，`0x35E390` 照常命中。

### 5.2 方案 B（更强，侵入更大）— 改比较逻辑

Hook / 补丁 `0x35E390` 内 `cmp [ebp+0x5AC], ebx`：按 **网格下标** 查 `skill_map[index]`，而不是只比 `boundKey`。  
优点：自定义图把技能热键改成非常规字母时仍可按「格子」改键。  
缺点：需稳定拿到「当前比较的是第几格」、版本偏移更多、测试面更大。  
**本轮不采用**；文档保留作后续演进。

### 5.3 明确不采用

| 做法 | 原因 |
|------|------|
| 运行时写回每个 ability 的 `+0x5AC` | 选人/学满/变身/换英雄会刷新 UI，难维护且易不同步 |
| 只改 Launcher 配置不 Hook | 引擎仍只认 `boundKey`，配置不会生效 |
| 技能与物品同时对同一物理键 remap | UI 虽去重，仍须 Hook 侧技能优先，防二次翻译 |

---

## 六、版本与偏移

| 版本 | `ModifyInputKeyCodes` Hook RVA | 技能 Query | 物品 Query |
|------|-------------------------------|------------|------------|
| 1.26.0.6401 | `0x3821C6` | `0x35E390` | `0x360CD0` |
| 1.27.0.52240 | `0x3763DB`（Launcher 表） | 本轮未逐字节复核 | 未逐字节复核 |

Launcher：`g_offsetsForGameModifyInputKeyCodes_`。签名扫描可在偏移漂移时兜底。  
**机制同构假设**：1.27 仍是「先技能 UI 再物品 UI + `boundKey@+0x5AC`」；若某版本命令卡布局或偏移变化，只需重定位 Query，不必改 remap 策略。

---

## 七、局限与验收

**局限**

- 规范键方案假设：**该格子上技能的 `boundKey` 仍等于默认 S/D/Q/W/E/R**。若地图把「Q 格」技能热键改成 `T`，则 `A→Q` 无法点到该技能（需方案 B 或同步改 `boundKey`）。  
- 命令卡底行（格 8–11：攻击/移动/巡逻等）Launcher 未暴露改键。  
- `enable_skillPanel_remap` / `unit_map` 是另一套 UI 语义，不在本文范围。

**验收建议**

1. 开「技能改键」，把 Q 槽改成 `A`，进游戏对英雄按 `A` → 应释放原 Q 技能。  
2. 同时开物品改键：确保 `A` 不会落到物品栏（技能优先）。  
3. 组合键：`Ctrl+A` 绑定技能槽时，仅在 Ctrl 按下时触发。  
4. 日志：`logs` / `war3keys` 中 Hook 打印改写前后键码。

---

## 八、产物清单

| 路径 | 内容 |
|------|------|
| `analyses/warcraft-iii-skill-key-remap.md` | 本文 |
| `analyses/warcraft-iii-skill-key-remap-mindmap.md` | 导图 |
| `artifacts/skill-key-remap/disasm_35E390_skill_query.txt` | 技能查询反汇编 |
| `artifacts/skill-key-remap/disasm_360CD0_inventory_query.txt` | 物品查询对照 |
| `artifacts/skill-key-remap/disasm_382150_input_handler_head.txt` | 输入处理头部 |
| `artifacts/skill-key-remap/disasm_3827E0_before_skill_call.txt` | 调用点上下文 |
