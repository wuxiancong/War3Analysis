# DotA AI `learn` / `-learn` 实现方案（英雄加点）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 在写代码前固定加点命令（主名 **`learn`**）的分层、包格式、解析与验收，对齐已有 `-buy`/`-move`；与施法主名 **`cast`** 成对 |
| **命名方式** | 文档文件名历史保留 `dota-ai-skill-command-implementation`；**对外命令主名改为 `learn`**（见下文「命令命名」） |
| **分析时间** | 2026-11-16（命名修订同日） |
| **状态** | **已实现（2026-11-16）**：见 [`dota-ai-human-lasthit-learn-cast.md`](./dota-ai-human-lasthit-learn-cast.md)。与本方案差异：未新增 `MSG_TYPE_HERO_SKILL_LEARN`，复用 `MSG_TYPE_AI_UNIT_COMMAND`（`AI_UNIT_CMD_LEARN`）；技能表为生成的 `shared/DotaHeroSkillAbbrev.h`（含 OrderId）；增加真人延迟、门槛校验与 `autolearn` |
| **机制依据** | [`dota-hero-skill-point-learn-flow.md`](./dota-hero-skill-point-learn-flow.md) |
| **施法对照** | [`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md)（主名 `cast`） |
| **对标实现** | [`warcraft-iii-ai-hero-move-command.md`](./warcraft-iii-ai-hero-move-command.md)、`war3hook_process.cpp`（buy/move） |
| **配套思维导图** | [`dota-ai-skill-command-implementation-mindmap.md`](./dota-ai-skill-command-implementation-mindmap.md) |
| **习惯数据** | [`dota-player-learn-habit-recorder.md`](./dota-player-learn-habit-recorder.md)（跨局加点画像 → 二期自动 `learn`） |

---

## 一、命令命名（推荐）

| 动作 | **推荐主名** | 兼容别名 | 勿用 |
| :--- | :--- | :--- | :--- |
| 花费技能点 / 学一级 / 属性附加 | **`learn`** | `skill`（易与「放技能」混淆，仅兼容） | 不要把 `cast` 当成加点 |
| 施放已学技能 | **`cast`**（另文） | `ability`（可选） | 不要用 `skill` 表示施法 |

选用 `learn` + `cast` 的理由：

1. 与引擎语义对齐：学习 = Learn Hero Skill；施放 = Cast / Order。  
2. 避免口语 “skill Q” 既像加点又像放技能。  
3. 与已有短动词族一致：`buy` / `move` / `attack` / **`learn`** / **`cast`**。

未采用 `skillup` / `talent`：更长，且 DotA 无独立天赋树；`learn` 已足够。  
未采用 `level`：易与英雄等级 / `Data:Level` 同步混淆。

---

## 二、目标与非目标

### 目标（MVP）

1. RemoteControl / 游戏内聊天均可触发：**为本地英雄学习一级技能或属性附加**。
2. 管道与 `-buy`/`-move` 相同：`AiControl → IPC → war3hook → EnqueuePlayerAction`。
3. 默认**不回显**聊天（复用 `ShowAiCommandChat` / `aichat`）。
4. 不新增 `game.dll` RVA；复用已有 `GameEnqueuePlayerAction_Ex`。

### 非目标（本阶段不做）

- 自动出装/完整加点规划引擎（可后接「升级边沿 → 调 `learn`」）。
- 精确读取「剩余技能点 / 经验条」内存字段。
- 用 JASS `SelectHeroSkill` 代替玩家 Action（联机不同步）。
- 卡尔 Invoker 召唤技能的特殊编排（MVP 只支持英雄固有可学技能 + 属性）。

---

## 三、命令语法

```text
# RemoteControl（推荐主路径，纯 IPC，无聊天）
learn <token> [nosubmenu]          # 主名
skill <token> [nosubmenu]          # 兼容别名（文档/日志仍打印 learn）

# 游戏内 / 大厅聊天拦截（同 buy/move）
-learn <token> [nosubmenu]
/learn <token> [nosubmenu]
-skill <token> [nosubmenu]         # 兼容
/skill <token> [nosubmenu]
```

### `<token>` 解析规则（优先级从上到下）

| Token | 含义 | 解析结果 |
| :--- | :--- | :--- |
| 4 字符 FourCC（如 `A05G`、`Aamk`、`A0NR`） | 直接技能码 | `abilityId = fourCcToU32` |
| `attr` / `stats` / `stat` / `attribute` | 属性附加 | 当前英雄 `attrCode`（缺省 `Aamk`） |
| `1` / `2` / `3` / `4` | 技能槽（1=一技能…4=大招） | 查英雄技能表 `skills[slot]` |
| `Q`/`W`/`E`/`R`（单字母，大小写不敏感） | **按槽位习惯映射** 1..4，**不是**地图真实热键 | 同槽位；日志注明「槽位别名」 |
| 其它 | 非法 | `ERR unknown learn token` |

可选后缀：

| 参数 | 默认 | 作用 |
| :--- | :--- | :--- |
| （无） | 开子菜单 | 先发 **`0x66`**，再发 **`0x10`** |
| `nosubmenu` | — | 跳过 `0x66`，只发 `0x10`（验证用） |

示例：

```text
learn 1
learn attr
learn A05G
-learn 4
/learn attr nosubmenu
skill 2                 # 兼容，等价 learn 2
```

---

## 四、总体架构（对齐 buy/move）

```text
RemoteControl / 游戏内 -learn|/learn（及兼容 -skill）
        │
        ▼
 AiControlManager::learnAbility(abilityId, flags)   // API 名避免 skill 歧义
   或 NetworkManager 聊天分支 → IPC
        │
        ▼
 SharedMemory  MSG_TYPE_HERO_SKILL_LEARN            // 枚举名可保留；语义=加点
   HeroSkillLearnPayload { abilityId, flags }
        │
        ▼
 war3hook_ipc.cpp  收包 → requestHeroSkillLearn(...)
        │
        ▼
 Action 线程 / 逻辑帧 executePendingHeroSkillLearn()
        │
        ├─ resolveLocalHeroObjectIds（同 -move）
        ├─ buildSelectionSwitchAction 保证选中英雄
        ├─ [flags 含 OpenSubmenu] enqueue 单字节 0x66
        └─ enqueue 0x10 | flags16 | abilityId | FFFFFFFF×2
              → g_originalGameEnqueuePlayerAction_Ex
```

游戏内键入路径：

```text
Enqueue 拦截 0x60 聊天
  → tryInterceptHeroLearnChatAction（擦除文本，若 ShowAiCommandChat=0）
  → handleLearnCommand("-learn ...")  // 同时识别 -skill 别名
  → requestHeroSkillLearn
Recipient 路径同 lobby 已有 handleMoveCommand 模式
```

---

## 五、IPC 与载荷设计

### 1. 新增消息类型

`War3Launcher/shared/SharedMemory.h`：

```cpp
MSG_TYPE_HERO_SKILL_LEARN,   // Launcher/AiControl → DLL：学技能/属性
```

注释约定（与 ITEM_BUY / UNIT_MOVE 同风格）：

```text
// 调试：RemoteControl `learn <token>`（兼容 skill）或游戏内 `-learn`/`/learn`；
// 组包：可选 0x66 + 0x10(Ability FourCC)；默认不回显聊天
```

### 2. Payload

```cpp
// MSG_TYPE_HERO_SKILL_LEARN
// abilityId：技能/属性 FourCC（小端 uint32，如 'Aamk'）
// flags：bit0 = 1 先发 0x66；其余保留 0
struct HeroSkillLearnPayload {
    uint32_t abilityId;
    uint32_t flags;
};

enum HeroSkillLearnFlags : uint32_t {
    HERO_SKILL_LEARN_OPEN_SUBMENU = 1u << 0,  // 默认置位
};
```

**解析放在哪一侧？**

| 路径 | Token → abilityId |
| :--- | :--- |
| RemoteControl / `AiControlManager` | **Launcher 侧解析**（可读 `dota_data.json` 或 shared 表），IPC 只传 `abilityId` |
| 游戏内 `-learn`（及 `-skill`） | **DLL 侧解析**（与 `-buy` 的 `resolveDotaItemToken` 同模式） |

两边共用同一套 C 表（推荐），避免 JSON 进 DLL。

### 3. 共享技能表（推荐落地物）

新增 `War3Launcher/shared/DotaHeroSkillAbbrev.h`（风格抄 `DotaItemShopAbbrev.h`）：

```text
struct DotaHeroSkillEntry {
    const char *heroUnitId;   // "Nbbc" 等
    const char *attrCode;     // "Aamk" / "A0NR"
    const char *skill1..4;    // FourCC 字符串
};
```

- 数据可从 `War3Bot/images/dota_data.json` **生成**（脚本一次性导出），或 MVP 先手写常用英雄 + 通用 `attr→Aamk`。
- DLL：`resolveDotaSkillToken(heroTypeId, token, &abilityId)`。
- Launcher：同一头文件或 Qt 包装函数。

MVP 最小集：

1. 任意英雄：`attr` → `Aamk`（若 `attrCode` 表有则覆盖）。
2. FourCC 直通。
3. 槽位 `1..4`：仅当 `heroTypeId` 能在表中命中；否则 `ERR need fourcc (hero skills not in table)`。

---

## 六、Action 组包（DLL）

### 1. 选中英雄

复用 `-move` 已验证路径：

- `resolveLocalHeroObjectIds`
- `buildSelectionSwitchAction(0xFFFFFFFF, 0xFFFFFFFF, hero1, hero2, heroType)`（只加选，不带取消段）
- 短 sleep ~30ms（与 buy/move 一致）

### 2. 打开加点菜单（默认）

```text
buf[0] = 0x66
len = 1
Enqueue
sleep ~20–30ms
```

### 3. 学习

对齐购买 `0x10` 布局（`war3hook_process.cpp` buyBuf），学习 Flags 默认 **`0x0000`**（与购买 `0x0044` 不同；**以实战抓包校正**）：

```text
unsigned char learnBuf[15];
memset(learnBuf, 0xFF, sizeof(learnBuf));
learnBuf[0] = 0x10;
learnBuf[1] = 0x00;   // flags lo — 抓包后可改
learnBuf[2] = 0x00;   // flags hi
// abilityId 按小端写入 [3..6]
memcpy(learnBuf + 3, &abilityId, 4);
// [7..14] 保持 FF
Enqueue(learnBuf, 15);
```

FourCC 写入注意与 buy 一致：内存小端即引擎 AbilityId；若用字符 `'A','a','m','k'` 组装，按现有 `fourCcToUnitId` / buy 倒序惯例统一，避免大小端搞反。

### 4. 线程模型

与 move 相同：

- `requestHeroSkillLearn` 只置 pending（允许覆盖未执行的 pending）。
- `executePendingHeroSkillLearn` 在 **Action 线程 / 已验证可 Enqueue 的上下文**执行。
- **禁止**在纯 WndProc/aiTick 直接 call Enqueue（move 注释已踩坑）。

---

## 七、代码改动清单（按文件）

| 层 | 文件 | 改动 |
| :--- | :--- | :--- |
| 协议 | `shared/SharedMemory.h` | `MSG_TYPE_HERO_SKILL_LEARN` + `HeroSkillLearnPayload` + flags 枚举 |
| 表 | `shared/DotaHeroSkillAbbrev.h`（新） | 英雄→技能/attr；`resolveDotaSkillToken` |
| DLL | `hooker/war3hook_process.cpp` | `request/execute/handleLearnCommand/tryIntercept…`（兼容解析 `skill`） |
| DLL | `hooker/war3hook_ipc.cpp` | case `MSG_TYPE_HERO_SKILL_LEARN` |
| DLL | `hooker/war3hook_lobby.cpp` | Enqueue 拦截 + Recipient 调 `handleLearnCommand` |
| DLL | `hooker/war3hook_internal.h` | 声明 |
| DLL | Action 调度处（与 `executePendingUnitMove` 同点） | 调 `executePendingHeroSkillLearn` |
| Launcher | `AiControlManager.h/.cpp` | `learnAbility(abilityId, flags)`；RemoteControl 解析 **`learn`**（兼容 `skill`） |
| Launcher | `NetworkManager.cpp` | `/learn` `-learn` → IPC（兼容 `/skill`；对标 `/move`） |
| 文档 | 本 md + learn-flow 交叉链接 | 实现后把「状态」改为已实现并补验收日志 |

**不改**：`versions/*/game.dll` 偏移表（无新函数）。

---

## 八、AiControl / RemoteControl 行为

```text
learn 1
→ 查本地英雄类型（若 Launcher 尚无英雄码：可 IPC 只传槽位改扩展 payload，
   或要求 DLL 侧解析；MVP 建议 RemoteControl 传 FourCC/attr，
   槽位解析优先放 DLL，因 DLL 已有 heroType）

推荐 MVP 分工：
  RemoteControl `learn <token>`（`skill` 别名同路径）
    → IPC 增加可选：token 字符串太重则仍只传 abilityId
    → 若 token 为槽位：发 MSG 时带 skillSlot + abilityId=0，DLL 用 heroType 查表
```

为减少两轮设计，**定稿 MVP payload 扩展**：

```cpp
struct HeroSkillLearnPayload {
    uint32_t abilityId;   // 非 0：直接用；为 0：用 skillSlot 查表
    uint32_t flags;       // bit0 OpenSubmenu
    uint8_t  skillSlot;   // 1..4；0=不用槽位；5=attr（可选约定）
    uint8_t  reserved[3];
};
```

- RemoteControl 已能解析 FourCC/attr → 填 `abilityId`，`skillSlot=0`。
- RemoteControl 只写 `learn 2` → `abilityId=0`，`skillSlot=2`，DLL 查表。
- `attr` → `skillSlot=5` 或直接 `abilityId='Aamk'`（DLL 再按英雄覆盖 `A0NR`）。

返回值约定：

```text
OK learn ability=A05G submenu=1
ERR usage: learn <token> [nosubmenu]
ERR learn ipc failed (is war3 hooked?)
ERR unknown learn token
ERR hero skills not in table
ERR no local hero
```

---

## 九、升级后自动加点（二期，可选）

不在 MVP 编码范围，接口预留：

1. 监听 `0x6B` `Data:LevelN=pid`（Bot）或 hook 侧 `g_lastHeroLevel` 边沿。
2. 查预设加点序（如 `1,2,1,3,1,4,…`）。
3. 调 `learnAbility` 一次。

与本方案同一 IPC，无需新协议。

---

## 十、验收计划

| # | 步骤 | 期望 |
| :--- | :--- | :--- |
| 1 | 进局选英雄，升级有技能点 | — |
| 2 | RemoteControl：`learn 1` | `OK learn…`；英雄一技能 +1；有 `0x66`+`0x10` 日志 hex |
| 3 | `learn attr` | 属性附加 +1（或该英雄 `A0NR`） |
| 4 | `learn A05G`（剑圣风暴） | 按 FourCC 学习 |
| 5 | 游戏内 `-learn 2` 且 `aichat off` | 学会；屏幕无刷屏 |
| 6 | `learn 1 nosubmenu` | 仅 `0x10`；对比是否仍能学会（定默认是否保留 0x66） |
| 7 | 无技能点时 `learn 1` | 引擎拒绝；不崩；日志仍有入队记录 |
| 8 | 兼容：`skill 1` 与 `learn 1` 等价 | 同效果；响应文案统一为 `OK learn…` |
| 9 | 未选人/无英雄 | `ERR no local hero` 或 DLL 日志失败 |

日志锚点：沿用 `g_wlogHeropickPath3` 或前缀 `[Learn] 0x66` / `[Learn] 0x10`。

抓包校正：人手 O→学一技能一条 `0x10`，核对 Flags；若非 `0000`，改 `learnBuf[1..2]` 并回写本 md。

---

## 十一、风险与对策

| 风险 | 对策 |
| :--- | :--- |
| Flags 猜错导致学不上 | 验收 #8 前先抓包；模板可配置常量 |
| 必须先 `0x66` | 默认开 submenu；`nosubmenu` A/B |
| 槽位热键≠QWER | Token `QWER` 只映射槽 1–4；文档写明；真实热键用 FourCC |
| 英雄不在表内 | FourCC/attr 仍可用；槽位报错 |
| 与购买 `0x10` 混淆 | AbilityId 落在技能码空间；买货是 `h0**`/`0x6830xxxx` |
| 幻象/非英雄选中 | 强制 `resolveLocalHeroObjectIds`，不依赖当前选中杂单位 |

---

## 十二、实现顺序（编码时按此勾）

1. `SharedMemory.h` 消息 + payload  
2. `DotaHeroSkillAbbrev.h` + resolve（先 attr + FourCC + 少量英雄槽位）  
3. DLL `request/execute` + IPC case + Action 调度挂接  
4. 聊天拦截 `handleLearnCommand` / `tryIntercept…`（兼容 `skill`）  
5. `AiControlManager::learnAbility` + RemoteControl（主解析 `learn`）  
6. `NetworkManager` `/learn` `-learn`（兼容 `/skill`）  
7. 实战验收 → 校正 Flags → 更新本 md 状态为「已实现」  
8. （可选）升级边沿自动加点  

---

## 十三、总结

对外主名 **`learn`**（兼容 `skill`）：**照搬 buy/move 管道** — IPC + 选中英雄 +（可选）`0x66` + `0x10(Ability FourCC)`。  
与施法主名 **`cast`** 成对；业务差只在 **token→FourCC 表** 与 **学习 Flags**；**不必逆向新的 game.dll 函数**。
