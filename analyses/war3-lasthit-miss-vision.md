# 补刀「丢失」机制、中路视野与假眼

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Cursor Auto / Composer |
| **分析目的** | 把影魔中路「没补到」里真正的高低地丢失与视野问题拆开；给 AI 只读 `missChance` 与站位；明确假眼插不插 |
| **命名方式** | `war3-lasthit-miss-vision`；导图 `war3-lasthit-miss-vision-mindmap.md`；产物 `artifacts/lasthit-miss-vision/` |
| **分析时间** | 2026-11-21 |
| **验证状态** | 静态全版本 `game.dll` + 地图 Misc/w3e/wpm + 三局 CSV 叠图；**未**实机挂调试器读掷点；时机预判另见 `tasks/grok-lasthit-live-verify.md`（本任务不做） |
| **证据** | `artifacts/lasthit-miss-vision/`（RVA 表、ShouldMiss 反汇编、中路悬崖叠图）；`artifacts/neutral-stack/patch_Units_MiscData.txt`；`records/lasthit/sf/sf_mid_20261121-*.csv`；前序 [`war3-lasthit-combat-data.md`](./war3-lasthit-combat-data.md)、[`warcraft-iii-fog-of-war-implementation.md`](./warcraft-iii-fog-of-war-implementation.md)、[`dota-683d-ward-and-deward.md`](./dota-683d-ward-and-deward.md)、[`dota-ai-scoring-system.md`](./dota-ai-scoring-system.md) |
| **配套思维导图** | [`war3-lasthit-miss-vision-mindmap.md`](./war3-lasthit-miss-vision-mindmap.md) |

---

## 第一段：结论

1. **丢失怎么避免**：引擎在**弹道伤害结算**时调用 `ShouldMiss`（`CMissile.cpp`）。仅当目标地形高度 **严格高于** 攻击者，且通过 `ChanceToMiss=0.25` 闸门时，才进入丢失；结果是伤害 × `MissDamageReduction=0.5`（半伤）并飘 `MISS`，不是必杀零伤。AI 避免法：**站到与目标同层或更高**（用 w3e `layerHeight` 代理），远程补刀不要站在坡下仰打；同层则丢失项为 0。三局「没补到」里，**同层占多数**，高低地候选只是一小部分——主因仍是时机/抢刀（另任务），不是 25% 丢失。
2. **假眼插不插**：**不为消除丢失而插**。丢失比的是攻击者/目标脚下高度，眼只加视野，不改 `ShouldMiss`。假眼可改善「看不见的兵被拿来预判」的问题，但那是 FoW 过滤（已有离线 `aiLhDropUnseen`），用站位/等兵下坡/卡兵把交汇放到己方高坡更便宜。若仍要中路眼：优先已有 `mid_river (-368,-656)` 或河岸 **cliff+1** 候选（见产物），150 金换视野不等于换补刀成功率。
3. **控线**：见姊妹文档 [`dota-mid-lane-control.md`](./dota-mid-lane-control.md)。
4. **尚未实机验证**：掷点顺序与 `GetRandomReal` 对照；近战是否走同一 `ShouldMiss`；目标进迷雾时前摇/弹道中途丢视野的表现；半伤是否被地图二次改写。

---

## A. 丢失机制

### A.0 地图常量出处（6.83d）

| 键 | 值 | 出处 |
| :--- | ---: | :--- |
| `ChanceToMiss` | **0.25** | 原版/补丁 `Units\MiscData.txt`（注释：*missile chance to miss if target is moving or on high ground*）。DotA `war3mapMisc.txt` **未覆盖** → 用库存值。摘录：`artifacts/neutral-stack/patch_Units_MiscData.txt` L56–57 |
| `MissDamageReduction` | **0.5** | 同文件 L90。地图 **未覆盖** |

以前文档只写「25%」：现补全为 MiscData 原文字段 + 地图未覆盖。

### A.1 命中链（1.26.0.6401 深挖，全版本 RVA 见下表）

```text
CMissile 伤害结算
  → ShouldMiss(attacker, target, flag=1, …)     // 1.26: 0x2BEAC0
       early: 空指针 / flag 路径 → 不丢
       precheck buff/能力（2BEA20 / 2BB960）→ 可直接判丢
       读 Misc ChanceToMiss，经 0x2853D0 + float 比较 0x01FD80 做 25% 闸门
       攻击者豁免 0x0C7DE0（flags，飞行类等）→ 不丢
       取双方位置 vtable+0xB8 → 地形高度采样 → cmp；setg → 目标更高则返回 1
  → 若返回 1：
       调 0x2BB970 飘 MISS 字
       伤害字段 × MissDamageReduction(0.5)
```

源文件串：`e:\...\unit\CMissile.cpp` / `::Missed`（字符串在 ChanceToMiss 邻域）。

**伪代码（只读判断）**：

```cpp
// 与引擎同语义的只读近似（高度用 w3e layerHeight；引擎内部是地形高度整型）
float missChance(Vec2 atkPos, Vec2 tgtPos, bool attackerIsMissile, bool attackerExempt) {
    if (!attackerIsMissile) return 0.f;          // 近战同链：未确认
    if (attackerExempt) return 0.f;
    int ha = terrainHeightProxy(atkPos);         // layerHeight 或运行时采样
    int ht = terrainHeightProxy(tgtPos);
    if (ht <= ha) return 0.f;                   // 同层或高打低：不进丢失
    return 0.25f;                               // ChanceToMiss；期望伤害乘数 0.75 = 0.75*1 + 0.25*0.5
}
```

**往哪站就不丢**：在补刀落点前，选 `layerHeight(站位) >= layerHeight(目标)` 且仍在攻击距离内的点；优先己方高台（中路 Radiant 侧多为 cliff **9**，河面 **8**）。斜坡/ramp 角点引擎用连续高度采样——代理用 layer 时若争议，等兵走到平台再打。

### A.2 逐项问答

| 问题 | 结论 | 置信度 |
| :--- | :--- | :---: |
| 高打低 / 低打高怎么算 | `ShouldMiss` 末尾 `setg`：**目标高度 > 攻击者高度** 才可能丢。高度来自单位位置 → 地形高度采样（`0x0D8DF0`/`0x0128C0` 链），**不是**单纯单位飞高 Z，也不是只读 cliff 字节；w3e `layerHeight` 作 AI 代理足够区分中路 8/9 台 | **高**（比较方向）；**中**（采样函数内部细节） |
| 斜坡 | 斜坡角点 `ramp` 标志存在；引擎比的是采样高度。斜坡上可能出现「看起来同台但高度整数仍更高」——实机未抓 | **中** |
| 近战 vs 远程 | 已确认调用点在 **CMissile** 伤害路径（flag=1）。近战是否另有等价函数：**未确认**（本任务 caller 图未见近战 flag=1） | 远程 **高**；近战 **未确认** |
| 反补 / 攻城车 / 建筑 | `ShouldMiss` 内无兵种/建筑特判；导弹打这些单位同样走高度+25%。建筑/攻城是否另有命中表：**未确认** | **中** |
| 何时掷点 | **弹道结算/出伤时**（missile 内调用），非起手。出手后双方换高低：**以结算瞬间位置为准**（函数当场读坐标） | **高** |
| 零伤还是减伤 | **减伤**：× `MissDamageReduction=0.5`，并飘 MISS。另有一条 flag=0 调用在丢时直接跳离（取消类），与半伤路径不同 | **高** |
| 弹道脱靶 / 迷雾 / 树木 | ChanceToMiss **不算**树木遮挡。迷雾影响可见与指令，不是本函数。弹道「飞歪」未见独立 RNG | 丢失函数 **高**；迷雾指令 **未确认**（见测试步骤） |
| 目标不可见 | AI 当前 `aiCollectNearby` **不查可见性**（仅敌方英雄几处查）。引擎侧：看不见时能否下攻击、前摇中/弹道中丢视野 → **未确认**，见 §实机步骤 | **未确认** |

### A.3 全版本 RVA（与扫描产物一致）

正文表与 [`../artifacts/lasthit-miss-vision/should_miss_rva_all_versions.md`](../artifacts/lasthit-miss-vision/should_miss_rva_all_versions.md) / `should_miss_rva_confirmed.json` 一致。`setg` 全 11 版已确认。`E8` 调用者：1.22+ 各 4 处已列出；**1.0.17–1.21 的 E8 调用者扫描为空 → 写「未确认」**，不按邻版推算。

| Version | ShouldMiss | setg | callers (E8) | ChanceToMiss str | use | MDR str | use |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- |
| 1.0.17.5988 | `0x1f43ce` | yes | 未确认 | `0x8076c8` | `0x1f43ce` | `0x8075fc` | `0x1f5035` |
| 1.0.20.6048 | `0x1f43ce` | yes | 未确认 | `0x808708` | `0x1f43ce` | `0x80863c` | `0x1f5035` |
| 1.20.4.6074 | `0x1f44de` | yes | 未确认 | `0x808708` | `0x1f44de` | `0x80863c` | `0x1f5145` |
| 1.21.0.6263 | `0x1f769e` | yes | 未确认 | `0x809820` | `0x1f769e` | `0x809754` | `0x1f8305` |
| 1.22.0.6328 | `0x2bdf20` | yes | `0xceec9`,`0x2c348e`,`0x2c3907`,`0x2c47d8` | `0x9211ec` | `0x2bdf8a` | `0x9211fc` | `0x2c47e8` |
| 1.23.0.6352 | `0x2bf460` | yes | `0xd0409`,`0x2c49ce`,`0x2c4e47`,`0x2c5d18` | `0x93532c` | `0x2bf4ca` | `0x93533c` | `0x2c5d28` |
| 1.24.1.6374 | `0x2bf520` | yes | `0xd04b9`,`0x2c4a8e`,`0x2c4f07`,`0x2c5dd8` | `0x944464` | `0x2bf58a` | `0x944474` | `0x2c5de8` |
| 1.24.4.6387 | `0x2bf5e0` | yes | `0xd04c9`,`0x2c4b4e`,`0x2c4fc7`,`0x2c5e98` | `0x944464` | `0x2bf64a` | `0x944474` | `0x2c5ea8` |
| 1.25.1.6397 | `0x2be890` | yes | `0xcf899`,`0x2c3dfe`,`0x2c4277`,`0x2c5148` | `0x932304` | `0x2be8fa` | `0x932314` | `0x2c5158` |
| 1.26.0.6401 | `0x2beac0` | yes | `0xcf899`,`0x2c402e`,`0x2c44a7`,`0x2c5378` | `0x932304` | `0x2beb2a` | `0x932314` | `0x2c5388` |
| 1.27.0.52240 | `0x6b7160` | yes | `0x4771b0`,`0x6b5133`,`0x6b5dc9`,`0x6b63c1` | `0xa50788` | `0x6b71d3` | `0xa50798` | `0x6b70a3` |

`IsUnitVisible` 全版本见 [`dota-ai-scoring-system.md`](./dota-ai-scoring-system.md) 末节表（本任务不重复挖）。

---

## B. 中路视野与假眼

### B.1 高度分区（两塔之间）

数据：`artifacts/ward-deward/map/war3map.w3e`（129×129，`centerOffset=(-8192,-8192)`）+ `war3map.wpm`。

| 地标 | 坐标 | layerHeight |
| :--- | :--- | ---: |
| 近卫中一塔 `GV` | (-1504, -1824) | 多为 **9** |
| 河道 `mid_river` / `Y5` | (-368, -656) | **8** |
| 天灾中一塔 `MX` | (1056, -96) | 多为 **9** |

中路 AABB 采样直方图：cliff **9** 为主，河槽 **8**，局部 **10**。坡口：相邻 128 格 `Δlayer≥1` 共 233 处（样本见 `mid_cliff_meta.json`）。ASCII：`artifacts/lasthit-miss-vision/mid_cliff_ascii.txt`。

**视野（白天 / 夜晚，半径来自已有 SLK，非本轮重挖）**：

| 单位 | day / night | 能照到的相对中路 |
| :--- | :--- | :--- |
| 英雄（影魔等） | 常见 1800 / 800 | 白天可盖过河看坡口；夜晚缩到近身 |
| 小兵 | ~800 / 800 | 兵线本身是主要「移动视野」 |
| 一塔 | **1900 / 800**（[`war3-tower-creep-aggro.md`](./war3-tower-creep-aggro.md)） | 白天塔照到河面前沿；夜视差 |
| 假眼 `o004` | **1600 / 1600** | 同层/更高台俯视价值大；**不改丢失** |

高台挡视线：低崖看不穿更高崖（FoW 文档）。假眼插在 cliff≥9 才能稳定看河对面低台兵。

### B.2 三局「没补到」叠图归因

脚本：`build_mid_cliff_and_overlay.py` → `mid_overlay_misses.json`。规则：死亡瞬间英雄与目标坐标 → 比 `layerHeight`；目标更高记「可能高低地丢失」（期望再 ×0.25 才是真 MISS）；同层/高打低记非丢失；缺坐标记**未知**（不凑数）。

| 局 | 没补到 | 可能高低地 | 同层 | 高打低 | 未知 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 23:11 `…231144…`（主证据） | 55 | **13** | 20 | 5 | 17 |
| 22:54 `…225436…` | 25 | 2 | 11 | 4 | 8 |
| 17:28 `…172855…` | 18 | 1 | 11 | 3 | 3 |
| **合计** | **98** | **16** | **42** | **12** | **28** |

主局 55 次里最多约 13×0.25≈**3.3 次**期望真 MISS；其余是时机/抢刀/半血残刀等（classify 口径），与「41 次出手没补到 ≠ 41 次丢失」一致。后撤相关仅 3 次（评分文档）——与丢失正交。

### B.3 假眼结论

| 问题 | 回答 |
| :--- | :--- |
| 眼能否消除丢失？ | **不能**。由 A：丢失只看相对高度 + 25% 闸门，与 FoW 无关 |
| 还要不要插？ | **不为补刀丢失插**。若为看见河对面兵/防 gank：可插；优先已有库位 |
| 近卫推荐 | 站在己方 cliff9 补刀；眼可选 `mid_river (-368,-656)` 或河岸高台候选如 **(-65,-481)** / **(-30,-565)**（cliff9，`wpm` 未置 unbuildable 位；施法距 420 内需英雄先站到河沿） |
| 天灾推荐 | 对称河东高台，如 **(432,-656)** / **(260,-488)**（cliff9） |
| 时机 / 持续 / 金 | 出装有眼后第一波前后；**7 min / 150 金**（2 充能物品价，见 ward 文档）。三局高低地候选仅 16/98 → **换不到可观的「补刀次数」**；ROI 低 |
| 与 `mid_river` | `mid_river` 在 cliff**8**；俯视略弱于 cliff9 岸边，但已在眼位库、路径熟——要视野优先用它，要俯视再偏岸上 200–400 |
| 不插时替代 | ① 同层/高台站位 ② 等兵下坡再补 ③ 卡兵把交汇拉到己方高坡（控线文档）④ 上线 `aiLhDropUnseen` |

---

## 建议改动（只写文档，主会话实现）

1. 补刀候选：已有 `aiLhDropUnseen` → 实机对比。  
2. 出手前：`missChance>0` 则平移到同层格或放弃该刀。  
3. 不要为丢失单独加「中路必插假眼」战术。

### 用户一分钟实机步骤（未做）

1. 影魔站河下（cliff8）打河上（cliff9）远程兵，看是否飘 MISS、伤害是否约半。  
2. 同层重复，应无高低地 MISS。  
3. 对迷雾中的兵下攻击：记指令是否接受、弹道中走进雾是否仍结算。日志：`ActionData2` / 伤害漂字。

---

## 产物索引

| 文件 | 内容 |
| :--- | :--- |
| `artifacts/lasthit-miss-vision/should_miss_rva_all_versions.md` | 全版本表 |
| `artifacts/lasthit-miss-vision/should_miss_helpers.json` | 1.26/1.27 反汇编 |
| `artifacts/lasthit-miss-vision/mid_cliff_*.json/txt/md` | 中路高度与叠图 |
| `artifacts/lasthit-miss-vision/mid_overlay_misses.json` | 逐次没补到归因 |
