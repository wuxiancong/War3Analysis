# DotA 6.83d 地图视野逻辑与英雄「绕视野」操作方案

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Auto（Cursor Agent / Composer） |
| **分析目的** | 梳理 DotA 6.83d 视野（引擎 FoW + 地图脚本）的实现层次；给出英雄 **绕视野 / 躲视野 / 出雾博弈** 的可落地 AI 操作方案（不依赖开图） |
| **命名方式** | `dota-683d-vision-and-fog-juke`；配套 `*-mindmap.md` |
| **分析时间** | 2026-11-17 |
| **样本** | `War3Script`（6.83d 拆分脚本）；`War3Launcher/versions`（`IsUnitVisible` 等各版 RVA）；前序 [`warcraft-iii-fog-of-war-implementation.md`](./warcraft-iii-fog-of-war-implementation.md)、[`minimap_dots_visibility.md`](./minimap_dots_visibility.md) |
| **配套思维导图** | [`dota-683d-vision-and-fog-juke-mindmap.md`](./dota-683d-vision-and-fog-juke-mindmap.md) |

---

## 一、核心结论

| 问题 | 结论 |
| :--- | :--- |
| 视野算在哪？ | **算在 `game.dll`**：每玩家迷雾栅格 + 单位层可见性（隐身/共享视野）。地图 **只改写**（FogModifier、联盟共享、临时揭示），**不自己算射线**。 |
| DotA 脚本改了什么？ | 开局「创建即销毁」全图 Visible 修改器 → 地形多为**已探索迷雾**而非纯黑；友军 `ALLIANCE_SHARED_VISION`；大量技能/塔挨打用 `CreateFogModifierRadius`；`UnitShareVision` 给信使等。 |
| 有没有 `FogEnable`？ | 6.83d **未调用** `FogEnable`/`FogMaskEnable`，跟大厅可见度选项。 |
| AI 绕视野要不要新挖 dll？ | **操作层不必。** 用已有 `IsUnitVisible` / `GetLocalPlayer`（`versions` 已有各版 RVA + 运行时按名捕获）+ `-move` Enqueue 即可。 |
| 「绕视野」合法边界 | 只根据 **本机可见性 API** 与 **己方视野模型** 决策；**禁止**读敌方迷雾内存 / 强制全图可见（开图）。 |
| 与现有 AI 关系 | `minimap_dots` 安全分已用「敌方对我是否可见」；绕视野要补的是 **「我对敌方是否可见」** + **树/高地/兵线视野规避走位**。 |

---

## 二、视野分层（引擎 × 地图）

```text
┌─────────────────────────────────────────────────────────┐
│  game.dll 战争迷雾管理器（每帧）                           │
│  · 栅格：已探索 / 当前可见（每格 uint16，玩家位）           │
│  · 单位 sight/nsight、树木 occH、高地挡视线                 │
│  · FoggedAttackReveal / DyingReveal（MiscData）          │
│  · IsUnitVisible = 单位虚函数（格子 + 隐身/反隐/ShareVision）│
└──────────────────────────▲──────────────────────────────┘
                           │ JASS 原生改写
┌──────────────────────────┴──────────────────────────────┐
│  DotA 6.83d war3map.j                                      │
│  · 开局 FogModifierRect/Radius 创建后 Destroy → 已探索       │
│  · SetPlayerAlliance(…, SHARED_VISION)                     │
│  · 技能/物品/塔挨打：CreateFogModifierRadius + 计时销毁     │
│  · UnitShareVision（信使、部分技能）                       │
│  · 脚本里大量 IsUnitVisible(…, GetLocalPlayer/Owner) 过滤  │
└─────────────────────────────────────────────────────────┘
```

细节与 1.26 反汇编、栅格偏移见前序 **迷雾实现文档**；本文只保留与「绕视野操作」相关的要点。

### 2.1 三态（对本地画面）

| 状态 | 含义（迷雾+遮罩都开时） |
| :--- | :--- |
| Visible | 当前有视野：看见单位、地形清晰 |
| Fogged | 已探索但当前无视野：地形暗，**看不见**敌方单位（建筑常仍显示） |
| Masked | 未探索黑色遮罩（DotA 开局处理后大部分地图已不在此态） |

### 2.2 单位可见 ≠ 格子亮

`IsUnitVisible(unit, player)`：

- 查的是**单位对某玩家是否可见**（含隐身、真视、`UnitShareVision`），不是单纯「脚下格子 FOG_OF_WAR_VISIBLE」。  
- 小地图敌方圆点与此同源（见 `minimap_dots_visibility.md`）。  
- 工程内：`callGameIsUnitVisibleToLocal` / `aiLearnNative("IsUnitVisible")`；各版 RVA 表在 `versions` + 该文档。

### 2.3 DotA 脚本侧关键用法（`War3Script`）

| 模式 | 作用 | 位置线索 |
| :--- | :--- | :--- |
| `DestroyFogModifier(CreateFogModifierRect/Radius(…, FOG_OF_WAR_VISIBLE, …))` | 开局标记已探索（含全图 `MS`、商店等） | `war3map_9.j` ≈ L16491+ |
| `FOG_OF_WAR_MASKED` 创建即毁 | 局部重新「抹黑/未探索」类效果 | `war3map_4.j` 等 |
| `CreateFogModifierRadius` + `FogModifierStart` + 计时 `Stop/Destroy` | 技能临时视野（半径常见 350–1000） | 多文件（如 `_9` 沟壑/技能附近） |
| `SetPlayerAlliance` / `SetPlayerAllianceStateBJ` 共享视野 | 队友同雾 | `_4.j` 阵营初始化等 |
| `UnitShareVision(u, p, true/false)` | 单位级共享 | 信使/技能约 20+ 处 |
| `IsUnitVisible` 在 Filter/触发器 | 技能索敌、特效是否对本地播放 | 全图大量 |

引擎参数（原版 `MiscData`，地图可覆盖时以地图为准）：

| 键 | 典型值 | 绕视野含义 |
| :--- | :--- | :--- |
| `FoggedAttackRevealRadius` | 200 | **雾中出手会暴露**周围，绕视野时慎 A |
| `DyingRevealRadius` | 500 | 死亡爆视野 |
| `FogFlashTime` | 3 | 显隐渐变 |
| 单位 `sight` / `nsight` | UnitBalance | 白天/夜晚视野半径 |
| 树 `occH`（如 ATtr≈230） | DestructableData | **树挡视线**，绕树是核心手段 |

白天夜晚：脚本有 `SetFloatGameState(GAME_STATE_TIME_OF_DAY, …)` / DayNight 模型；夜晚英雄 `nsight` 变短，绕视野窗口更大。

---

## 三、「绕视野」在玩法上指什么

本文「绕视野」= 合法信息下的 **视野博弈**，不是 MapHack：

1. **躲视野（Juke）**：让敌方 `IsUnitVisible(我, 敌方玩家)==false`（进树后、出兵线/塔圈、掉高地等），再换向或 TP。  
2. **雾中机动**：在己方仍看见地形/己方单位处移动，但尽量不进入敌方当前可见区（用**近似敌方视野模型**估计）。  
3. **信息不对等决策**：敌方小地图圆点消失 → 提高警戒（已有 unsafe）；自己即将暴露 → 停手/缩回。  
4. **利用暴露规则**：雾中 **不要无意义 A**（触发 FoggedAttackReveal）；需要时故意 A 一下骗视野则另论。

---

## 四、AI 可观测信号（合法）

| 信号 | API / 来源 | 用途 |
| :--- | :--- | :--- |
| 敌方英雄对我是否可见 | `IsUnitVisible(enemy, GetLocalPlayer())` | 更新 lastSeen、安全分（已有） |
| **我是否被某敌方看见** | `IsUnitVisible(myHero, enemyPlayer)` | **绕视野核心**（工程需补查询，原生已在表中） |
| 己方单位/建筑/眼位置 | CreateUnit 跟踪 + 静态塔表 | 近似「敌方可能看见的区域」的对偶：己方视野圆 |
| 小兵波位置 | AI 单位表 owner=0/6 | 兵线提供视野，贴线易暴露 |
| 昼夜 | 游戏时间 / DayNight | 切换 sight/nsight 参数 |
| 树木挡视线 | 树坐标 + occH 简化射线（二期） | juke 点评分 |

**不能做**：读敌方客户端迷雾位图、对不可见敌方发选中/`0x12` 精确点人（反作弊亦盯这个）。

---

## 五、绕视野操作实现方案

### 5.1 状态机（建议挂在 `war3hook_ai`）

```text
        ┌─────────────┐
        │  OBSERVE    │  刷新：我是否对每个敌人 Visible；敌方圆点；安全分
        └──────┬──────┘
               │
     ┌─────────┼─────────────────────────┐
     ▼         ▼                         ▼
 Exposed    SoftExposed              Hidden
 (被≥1敌人看见) (在近似敌方视野边缘)   (对所有敌人 IsUnitVisible=false)
     │         │                         │
     │    微移出圈 / 进树                 │ 可绕后、Gank、回线
     ▼         ▼
  JUKE：选附近高分掩体点 → -move
  若 unsafe 且 Exposed → 优先塔后（复用现有 -unsafe 退守）
```

命令草案（未编码）：

```text
vision status              # 日志：我对 P1.. 是否可见、敌方圆点数
juke [radius]              # 主动找掩体点并 move
fog hold                   # 保持 Hidden：禁止攻击直至安全或超时
-unsafe                    # 已有：安全分低则退守（与 juke 互补）
```

### 5.2 「我对敌人是否可见」

```text
for each enemyPlayer in 敌方人类槽:
  vis = IsUnitVisible(localHeroHandle, enemyPlayer)
  if vis: exposed = true
```

- 原生签名与 `IsUnitVisible(unit, localPlayer)` 相同，只换 player 参数。  
- `versions` 中 RVA 已覆盖；运行时 `aiLearnNative` 已学名字则无需新偏移表。  
- 盟友共享视野：对「敌方任意一人可见」≈ 对敌方队伍暴露（SHARED_VISION）。

### 5.3 近似「敌方视野区」（无开图时的对偶法）

无法读敌方栅格时，用 **已知威胁源** 估计「我可能被看见」：

| 威胁源 | 半径来源 | 备注 |
| :--- | :--- | :--- |
| 可见敌方英雄 | 该英雄 sight/nsight 表 | 不可见时用 lastSeen + 时间衰减扩大不确定圆 |
| 敌方小兵（可见） | 小兵 sight | 贴脸兵线易暴露 |
| 敌方塔（建筑常可见） | 塔攻击/视野半径表 | 高地塔特别危险 |
| 已知真眼/假眼 | 插眼 Action / 习惯数据（二期） | 无则保守少进野区暗处 |

**暴露分数**（示意）：

```text
exposeScore = Σ weight_i * max(0, 1 - dist_i / sight_i)
Hidden  ≈ exposeScore < ε 且 IsUnitVisible(me, anyEnemy)==false
```

树后修正（二期）：若我与威胁源之间有 `occH>0` 的树且同层高地关系挡住，则将该源权重×0 或×衰减。

### 5.4 JUKE 选点

在英雄周围采样点（或预置 juke 点表：各路树林坐标）：

1. 过滤不可行走；  
2. 对每个候选算 `exposeScore`（越低越好）；  
3. 偏好：短距、靠近己方塔/己方视野、不穿过敌方英雄；  
4. 最高分点 → 已有 `requestUnitMove`（`-move`）。  

进树后短暂停顿再换向，避免直线穿出雾被追。

### 5.5 雾中行为约束

| 规则 | 原因 |
| :--- | :--- |
| `Hidden`/`SoftExposed` 时默认禁止攻击小兵/英雄 | 防 `FoggedAttackRevealRadius` 把自己打亮 |
| 需要补刀时：先确认 `IsUnitVisible(me, enemy)==false` 仍可能被兵/塔看见 → 用暴露分数 | 兵线视野 |
| 技能点地：点雾中空地一般不暴露单位本身；**单位目标技能**需目标对我可见 | 与引擎一致 |
| 出雾瞬间（Hidden→Exposed）提高走位优先级 | 被抓窗口 |

### 5.6 与现有 unsafe / 补刀关系

| 模块 | 关注点 | 协同 |
| :--- | :--- | :--- |
| `minimap_dots` 安全分 | **敌来不来得见我侧的信息** | score 低 → 退塔 |
| 本方案 expose | **我亮不亮给对面** | expose 高 → juke / 停手 |
| `-lasthit` | 贴兵线 | expose 高或 unsafe 时暂停（已有 unsafe 挂钩） |

---

## 六、要不要继续挖 `versions/game.dll`？

| 目标 | 要否 |
| :--- | :--- |
| `IsUnitVisible` / `GetLocalPlayer` | **已有**各版 RVA + 动态学名 |
| 发移动/停手 | **已有** Enqueue，无新函数 |
| 读迷雾栅格做精确敌方 FoW | **可选深挖**（反作弊也敏感）；绕视野 MVP **不需要** |
| 视线射线与 occH 精确算法 | 前序已标未完整反汇编；MVP 用采样点+树表近似 |

结论：**绕视野交付以脚本可见性 API + 走位注入为主，不必为 MVP 再扫栅格结构。**

---

## 七、实现步骤（编码勾选）

1. **文档**（本文）— 完成。  
2. **查询封装**：`aiIsVisibleToPlayer(unit, player)`；日志 `vision status`。  
3. **暴露分数**：可见敌英/兵/塔 + sight 表；挂钩 `aiTick`。  
4. **`juke`**：采样/点表 → `requestUnitMove`；`fog hold` 禁 A。  
5. **与 `-unsafe` / lasthit**：expose 或 unsafe 时暂停激进补刀。  
6. **（二期）** 树挡视线、眼位表、分路 juke 点录制（可进 `data/` 习惯目录）。  
7. **验收**：树后 `IsUnitVisible(me, enemy)` 变 false；雾中 A 后短暂变 true（暴露）；无对雾中敌方错误选中。

---

## 八、风险与合规

| 风险 | 对策 |
| :--- | :--- |
| 被当成开图 | 只用 `IsUnitVisible`；不可见敌方不读坐标、不下目标指令 |
| 近似视野不准 | 保守增大敌方 uncertain 半径；优先信 `IsUnitVisible(me, enemy)` |
| 假动作暴露 | fog hold 默认禁攻击 |
| 与地图 FogModifier 不同步 | 技能临时视野靠「被看见」边沿感知，不强行解析每个修改器 |

---

## 九、总结

- DotA 6.83d 视野 = **引擎 FoW + 单位可见性**，地图用 FogModifier/共享视野/脚本判定 **改写与消费**，不算另一套迷雾。  
- **绕视野** = 监测「我是否被敌看见」+ 近似敌方视野威胁 + **进树/出路/停手** 的 `-move` 策略。  
- 复用 `versions` 已有可见性原生与现有移动管道；**MVP 不读迷雾内存、不新挖必选 RVA**。

---

## 十、参考

- [`warcraft-iii-fog-of-war-implementation.md`](./warcraft-iii-fog-of-war-implementation.md) — 引擎栅格与 DotA 开局 FogModifier  
- [`minimap_dots_visibility.md`](./minimap_dots_visibility.md) — 圆点 / 安全分 / 各版 `IsUnitVisible` RVA  
- `War3Script/war3map_9.j` 开局 DestroyFogModifier；多文件 CreateFogModifierRadius / UnitShareVision  
- `war3hook_jass.cpp` `callGameIsUnitVisibleToLocal`；`war3hook_ai.cpp` unsafe 退守  
- `War3Launcher/versions/**/game.dll` — 原生偏移表来源  
