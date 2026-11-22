# Warcraft III 单位碰撞与被挡绕行（卡兵用）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Composer / Grok 路由（Cursor Agent） |
| **分析目的** | 回答小兵被英雄挡住时引擎如何碰撞、是否绕行、往哪边走、友军是否互挤、中间路径点能否读；给下路弯道漏外侧兵的卡兵站位建议 |
| **命名方式** | `war3-unit-collision-and-repath`；导图 `*-mindmap.md`；产物 `artifacts/unit-collision/` |
| **分析时间** | 2026-11-21 |
| **验证状态** | 1.24.4 / 1.26 / 1.27 的 RTTI、`NIpse::CLrPath` 构造与字段已对上；物编 `collision` 已与 DotA 地图层合并。**未**在实机进程里单步断到绕行分支；绕行方向与「700/400」计时单位仍为中置信。未在游戏线程调 JASS |
| **证据** | `War3Launcher/versions/{1.24.4.6387,1.26.0.6401,1.27.0.52240}/game.dll`；`artifacts/scoring/base/*/Units_UnitBalance.slk` + `artifacts/ward-deward/map/Units_UnitBalance.slk`；脚本 `shared/scripts/scan_unit_collision.py`、`deep_unit_collision.py`、`find_cpo_rtti.py`；前序 [`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md)、[`dota-lane-creep-speed-profile.md`](./dota-lane-creep-speed-profile.md)、[`dota-ai-creep-block-positioning.md`](./dota-ai-creep-block-positioning.md) |
| **配套导图** | [`war3-unit-collision-and-repath-mindmap.md`](./war3-unit-collision-and-repath-mindmap.md) |

---

## 一、卡兵可直接用的结论

| # | 结论 | 置信度 |
| :--- | :--- | :--- |
| 1 | 碰撞半径来自物编 **`UnitBalance.slk` 的 `collision`（`ucol`）**，不是 `CUnit` 上某个固定 16/32/48 字段（与移动字段文档一致）。DotA 合并后：近战 `esen=16`、远程 `edry` 地图未改 → 继承补丁 **32**、攻城 `ebal=16`、冰女 `Hjai=32` | 高（SLK）；CUnit 内嵌半径仍未找到 |
| 2 | 「接触」是两套机制叠用：**(A) 移动时单位圆分离**（半径 ≈ `collision`，圆心距 &lt; r₁+r₂ 则挡/滑）；**(B) 静态寻路占 32×32 格**，碰撞值还会收成大/中/小占用盒（见 §2.3）。不是「只认格子」也不是「只认圆」 | 高（机制）；盒换算公式来自社区/HIVE，本仓未逐指令复现 |
| 3 | 被挡时不是纯原地等：每 tick **局部分离/滑步**（`NIpse::CPoSeparate` + `CPoPosCl`），堵死时再走 **单位自带路径对象** `NIpse::CLrPath` 向全局 `CLrPathingSys` / `CLrPathingAcc` 要新路。对应 (b)+(c)，不是单纯 (a) | 高（类型与调用结构）；具体「何时触发重算」中 |
| 4 | 绕行左/右：二进制本趟**未**挖到明确的「永远向右」立即数。结合分离器 + 空格子 + 朝目标点的滑步，**弯道外侧更空 → 外侧兵被挤到外侧**（近卫下路横向 ≈ −150~−175） | 中（与速度剖面实测一致） |
| 5 | **同波友军也会互碰互绕**（同一 ground 域）。出兵叠在同一点 + 弯道压缩 → 外侧兵被同伴和英雄一起挤出车道 | 高 |
| 6 | 脚本兵线目标仍在 `COrder+0x48/+0x50`（如 `O2[lane]`）。**中间折线**在 `CLrPath`：容器在 **`+0x34`**，元素步长 **`0x20`**（构造时 `push 0x20`）。卡兵若只读 Order 目标，看不到弯道局部绕行点 | 高（布局）；从 `CUnit` 挂到 `CLrPath*` 的偏移本趟未钉死 |

---

## 二、碰撞体积

### 2.1 物编 `collision`（权威输入）

合并顺序：`war3.mpq` → `War3x.mpq` → `War3Patch.mpq` → DotA 地图 `Units_UnitBalance.slk`（后写覆盖）。产物：[`artifacts/unit-collision/dota_collision_merged.json`](../artifacts/unit-collision/dota_collision_merged.json)。

| 单位 | FourCC | `collision` | 来源层 |
| :--- | :---: | ---: | :--- |
| 近卫近战 | `esen` | **16** | 地图覆盖（补丁原 32） |
| 近卫远程 | `edry` | **32** | 补丁（地图未写该列） |
| 近卫攻城 | `ebal` | **16** | 地图覆盖（补丁原 48） |
| 天灾近战 | `ugho` | **31** | 补丁 |
| 天灾远程 | `unec` | **8** | 地图覆盖 |
| 天灾攻城 | `umtw` | **48** | 补丁 |
| 冰女 | `Hjai` | **32** | 补丁 |

> [`dota-lane-creep-speed-profile.md`](./dota-lane-creep-speed-profile.md) 表内写 `edry` 碰撞为 8，与本仓 SLK 合并结果（32）不一致；卡兵计算请以本表 / JSON 为准，或再实机量一次分离距离校准。

### 2.2 `CUnit` 上读不到半径

[`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md) §六已说明：在 `CUnit` 前 `0x320` 字节内没有 16/32/48 这一档。本趟同样未找到。运行时应：`typeId (+0x30)` → 查预载的 `collision` 表（与 `war3hook_hero_stats.inl` 同类），不要扫对象内存碰运气。

### 2.3 圆 vs 格子

| 层 | 规则 | 对卡兵的含义 |
| :--- | :--- | :--- |
| 移动时分离 | 圆心距 &lt; `collision_a + collision_b` 则触发挡/滑（OpenWarcraft / 速度剖面所称 `CPoSeparate`） | 冰女(32)+近战(16) → **约 48** 内算「贴上」 |
| 寻路占地 | 世界坐标落到 **32×32** pathing 格；碰撞值还会收成占用盒（HIVE：按 16 对齐抬到盒半宽，16→64²、32→96²、48→128²） | 英雄盒通常比小兵大；弯道外侧空格更容易成为绕行出口 |
| 建筑/树木 | 主要靠 pathing 贴图 footprint，不是 `collision` 圆 | 卡兵一般可忽略 |

**接触判定答案**：两者都用——移动用圆（半径和），寻路/占位用 32 格 + 碰撞盒；漏兵时往往是「圆上已开始滑，格子上外侧仍空」。

---

## 三、被挡时引擎做什么

### 3.1 角色分工

| 类型 | 作用 |
| :--- | :--- |
| `NIpse::CPoPosCl` | 每 tick 转向 + 推进（含 `propWin` 门控，见速度剖面） |
| `NIpse::CPoSeparate` | 与邻近单位做分离 / 滑步（友军也参与） |
| `NIpse::CLrPath` | **每个移动者自带的路径对象**（当前/目标坐标、路点容器、参数字） |
| `NIpse::CLrPathingSys` / `CLrPathingAcc` | 全局加速寻路数据，供 `CLrPath` 取新折线 |

被挡时：**先局部分离（b）**；局部走不通再 **刷新 `CLrPath` 折线（c）**。长时间贴死时表现为走走停停（速度剖面：`forceStop` 使本 tick 速度为 0），不是 AI 意义上的「永久原地 Hold」。

### 3.2 `CLrPath` 布局（1.24.4 / 1.26 / 1.27 同构）

构造函数（装 vtable + 清零 + 建容器）：

| 版本 | `CLrPath` 构造 RVA | vtable RVA |
| :--- | :---: | :---: |
| 1.24.4.6387 | `0x49D52F` | `0x9654C4` |
| 1.26.0.6401 | `0x49CA1F` | `0x95336C` |
| 1.27.0.52240 | `0x111F10` | `0x961300` |

关键字段（相对 `CLrPath*`）：

| 偏移 | 含义 |
| :--- | :--- |
| `+0x00` | vtable |
| `+0x1C` … `+0x30` | 若干 float：当前位置 / 目的地分量（构造时填全局 0 浮点） |
| `+0x34` | 路点容器起点；构造 `push 0x20` → **元素大小 32 字节** |
| `+0x48` / `+0x68` | 初值 `0x80`（128）— 容量/上限类参数 |
| `+0x80` | 标志类 dword（OpenWarcraft 在更早 demo 里把 update 与 flags 联系起来） |
| `+0x84` / `+0x86` | 两个 **word**：初值 **`0x2BC`（700）** 与 **`0x190`（400）**。1.27 写成一个 dword `0x019002BC` |
| `+0x8C` / `+0x90` | 在 1.27 里表现为路径对象 **链表前后指针**（插入时写 `0xFFFFFFFF` 或指向另一节点）。**不要**再当成 ROC demo 审计里的「倒计时槽」——字段复用/改版了 |

### 3.3 其它相关 RVA

| 符号 | 1.24.4 | 1.26 | 1.27 |
| :--- | :---: | :---: | :---: |
| `CLrPathingSys` vtable | `0x9656F4` | `0x95359C` | `0x95FFAC` |
| `CLrPathingAcc` vtable | `0x964894` | `0x95273C` | `0x960300` |
| `CMoveReq` vtable | `0x93C170` | `0x92A010` | `0x970788` |
| `CAbilityMove` vtable | `0x93C1B4` | `0x92A054` | `0xA34FD8` |
| `CAbilityMove` 构造 | `0x206F10` | `0x206400` | `0x5DC850` |
| `CPoSeparate` vtable | `0x96430C` | `0x9521B4` | `0x960EB0` |
| `CPoPosCl` vtable | `0x9646AC` | `0x952554` | `0x96095C` |

1.27 上 `CLrPath` 由路径系统池分配后 placement-new（例如 `0xFD503` / `0x101423` → `call 0x111F10`），不是 `CAbilityMove` 构造函数里直接 `new`。

### 3.4 重算间隔

| 来源 | 数值 | 说明 |
| :--- | :--- | :--- |
| 二进制 | `CLrPath+0x84=700`，`+0x86=400` | 与两套路点缓冲一起序列化；**单位未实机标定**（可能是 ms、也可能是内部 tick 缩放） |
| OpenWarcraft 行为复现 | 位移停滞约 **24 帧** 后可再要局部绕行；重试窗口约 **500 ms** 一次 | 与 400/700 同量级，可作工作假设 |
| 模拟步 | 速度剖面：逻辑步约 **32 Hz**（无加速时满速 `325/32`） | 分离/滑步每逻辑 tick 都可发生 |

**答案**：被挡后优先每 tick 局部滑；折线级重算有节流（候选 400~700 与 ~500 ms）。卡兵 AI 应按 **≤100 ms** 控制环假设「外侧兵随时可能改横向」，不要假设要等半秒才绕。

---

## 四、绕行方向

本趟**没有**在三版 `game.dll` 里定位到「恒定左/右偏置」的立即数分支。

可依赖的机制模型：

1. `CPoSeparate` 在接触时给出一个**不加重穿透**的滑步方向（速度剖面 / OpenWarcraft：接触擦边、慢速方常让快速方）。  
2. 滑步会偏向 **pathing 仍为空** 的一侧。  
3. 近卫下路弯道：车道内侧更挤、外侧更空 → 同波互挤后，最外侧兵横向到 **−150~−175**（已有卡兵日志），再遇到站在中线偏内的英雄时，继续从外侧格子绕过。

因此：「往哪边绕」≈ **目标点方向 + 相对挡路体质心 + 哪侧格子空**，不是随机硬币，但也不是写死的「永远向右」。

---

## 五、友方是否互绕

会。`CPoSeparate` 不区分敌我，只认同一移动碰撞域（地面 `foot` 对地面）。速度剖面 §核心结论 ③ 已用下路日志解释：同波叠出生 → 后排 `forceStop` → 侧向挤出。  
这直接解释 **为什么总是外侧那只漏**：它已经被同伴顶到英雄碰撞盒/寻路盒盖不住的横向位置。

---

## 六、路径点（waypoint）

| 层级 | 位置 | 能否读 | 用途 |
| :--- | :--- | :--- | :--- |
| 脚本兵线路点 | `O2[lane]` 等 → 发到单位的 point/attack 指令 | 是（脚本/已有轨迹文档） | 全局下一「兵线意图」 |
| 指令目标 | `COrder+0x48` = X，`+0x50` = Y | 是（移动字段文档，高置信） | 当前命令终点，**不是**绕行折线 |
| 引擎折线 | `CLrPath+0x34` 起、步长 `0x20` 的节点数组 | 布局高置信；**从 `CUnit`/`Amov` 取 `CLrPath*` 的偏移未完结** | 弯道局部绕行点 |

实操：卡兵预测仍以「车道前进/横向 + 0.25 s 外推」为主；若以后挂上 `CLrPath*`，优先 dump `+0x34` 容器里的坐标对，核对是否与外侧兵横向跳变同步。

---

## 七、对卡兵 AI 的建议（可写进 `war3hook_ai_tactics.inl` 的判定，本任务不改代码）

目标：让**外侧兵在弯道也不触发「有空格可绕」**——英雄身体要盖住它的前进走廊，而不是只挡中线。

### 7.1 几何常数（近卫下路 / 冰女）

```text
kCreepCollision_esen   = 16
kCreepCollision_edry   = 32   // SLK 合并；若实机分离更像 8 再改表
kHeroCollision_cm      = 32
kContactRadius         = heroCollision + creepCollision   // 近战 48，远程 64
kPathCell              = 32
kBotOuterLateralSign   = -1   // 近卫下路外侧（日志 −150~−175）
kBendProgress0         = 3300
kBendProgress1         = 4300
```

### 7.2 站位

1. **前进**：保持在目标兵（尚未越过英雄的最前兵）前方 **70~110**（现有逻辑可保留）；弯道段不要退到 &lt; 40（太近更容易被当成「可滑过去的贴面」而不是堵死格）。  
2. **横向（关键）**：在 `progress ∈ [3300, 4300]`（或本路弯道区间）时，目标横位置不要用「整波中位」，而用：

```text
outer = 本波中 lateral * kBotOuterLateralSign 最大的那只（还未越过英雄）
aimLat = lerp(前排中位, outer.lat, 0.65~0.85)
// 再向外侧多偏 0.5 * kContactRadius（约 24~32）
aimLat += kBotOuterLateralSign * (0.5 * kContactRadius)
```

3. **覆盖宽度**：若前排宽度 `w > 110` 或存在 `|lat - median| > 120` 的外侧兵，视为「必须偏外侧挡」，禁止只锁中线。  
4. **接触预警**（可选日志 / 提前横移）：

```text
if hypot(hero - creep) < kContactRadius + 25
   && creep.progress > hero.progress - 20
   && creep 在外侧:
      立即把 aimLat 拉到 creep.lat（允许更大横移步）
```

5. **不要**指望读 `COrder` 目标点预测绕行；弯道漏兵是 `CPoSeparate` 挤出 + 局部空格，不是脚本改了 `O2`。

### 7.3 成功判据（弯道段）

- 该段内外侧兵 `|hero.lat - outer.lat|` 中位 &lt; **40**；  
- 无 `🚨 漏兵` 且该兵 `lat` 不再继续向外扩超过 −200。

---

## 八、产物索引

| 文件 | 内容 |
| :--- | :--- |
| `artifacts/unit-collision/dota_collision_merged.json` | DotA 碰撞合并表 |
| `artifacts/unit-collision/rva_table.json` | 多版本 RVA 摘要 |
| `artifacts/unit-collision/cpo_rtti.json` | `CPoSeparate` / `CPoPosCl` 类型描述符 RVA |
| `artifacts/unit-collision/*-scan.md` / `*-deep.md` | 各版 vtable / 构造反汇编摘录 |
| `artifacts/unit-collision/1.27-clrpath-from-timer.md` 等 | `CLrPath` 构造与 `+0x8c` 附近代码 |

---

## 九、未完结

1. `CUnit` / `CAbilityMove` → `CLrPath*` 的确定偏移（实机跟一次分配即可）。  
2. `+0x84/+0x86` 的 700/400 是 ms 还是内部计数。  
3. `CPoSeparate` 选左右的精确代价函数（需断点或插装）。  
4. `edry` 碰撞 32 vs 速度剖面写的 8：实机量一次分离距离定稿。  
5. 路点元素 `0x20` 字节内哪些是 X/Y（dump 绕行中的容器对照 `GetUnitX/Y`）。
