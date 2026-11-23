# DotA 6.83d 金币神符（Bounty Rune）经验 / 金钱公式

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Composer（Cursor Agent） |
| **分析目的** | 精确给出 0:00 首枚金币符与后续金币符的 XP/Gold、刷符时点与坐标、瓶装 `I0RE` 结算时刻，并对照 1→2 级经验供中单抢 2 级 |
| **命名方式** | `dota-bounty-rune-xp-gold` |
| **分析时间** | 2026-11-23 |
| **地图** | DotA Allstars 6.83d（`War3Script/war3map_*.j`） |
| **相关** | [`dota-683d-ai-data-tables.md`](./dota-683d-ai-data-tables.md)、[`dota-ai-laning-routine.md`](./dota-ai-laning-routine.md)、[`dota-6.83d-web-gameplay-data-reverse.md`](./dota-6.83d-web-gameplay-data-reverse.md) |

---

## 一、结论（先看这个）

| 场景 | XP | Gold | 依据 |
| :--- | ---: | ---: | :--- |
| **0:00 开局双金币符（直接拾取）** | **100** | **100** | 物品 hashtable key `835` = true → `FUO` 写死 |
| **2:00 及之后常规金币符（地面 `I0RC`）** | \(50 + 5\cdot m\) | \(50 + 2\cdot m\) | \(m=\lfloor\mathrm{TimerGetElapsed}(M)/60\rfloor\) |
| **瓶装金币符 `I0RE` 使用** | 同上常规公式 | 同上 | **按使用时刻**重算；**丢失**开局 100/100 标记 |

- 1→2 级累计经验：**200 XP**（`war3mapMisc.txt` `NeedHeroXP` 首项）。
- 近战兵 / 远程兵经验：**62 / 41**（单位等级 3 / 2 + `GrantNormalXPFormulaC=6`）。
- 吃到 0:00 首符后还差 **100 XP**：中路**独占经验**时，再吃 **1 近战 + 1 远程**（62+41=103）或 **2 近战**（124）即可到 2 级。

---

## 二、发奖函数（权威）

`war3map_2.j` **`FUO`**（约 L7028–7040）——地面拾取与瓶装释放最终都进这里：

```7028:7040:War3Script/war3map_2.j
function FUO takes unit SFI,item BA1 returns nothing
local integer G0O=R2I((TimerGetElapsed(M))/60)
local integer XP=50+5*G0O
local integer ROI=50+2*G0O
local boolean GIO=(LoadBoolean(LY,(GetHandleId(BA1)),(835)))
if GIO then
set XP=100
set ROI=100
endif
call AddHeroXP(SFI,XP,true)
call AA1(GetOwningPlayer(SFI),ROI,SFI)
call PlaySoundOnUnitBJ(AG,100,SFI)
endfunction
```

调用链（地面拾取）：`X8O`（`EVENT_PLAYER_UNIT_PICKUP_ITEM`）→ `GOO` → 若 `GetItemTypeId==I0RC(1227903555)` → `FUO`：

```7056:7074:War3Script/war3map_2.j
function GOO takes unit SFI,item BA1 returns nothing
...
elseif GetItemTypeId(BA1)==1227903555 then
call FUO(SFI,BA1)
endif
endfunction
```

金钱发放：`AA1`（`war3map_1.j` L4986）直接 `PLAYER_STATE_RESOURCE_GOLD += ROI` 并飘字。

### 2.1 开局 100/100 标记

刷新函数 **`CBO`**（`war3map_2.j` L4186）在 `J40==true`（全局初值 `true`，`war3map_1.j` L1433）时：

```4230:4235:War3Script/war3map_2.j
else
set J40=false
set VK=CreateItem(1227903555,x1,y1)
call SaveBoolean(LY,(GetHandleId(VK)),(835),(true))
set VK=CreateItem(1227903555,x2,y2)
call SaveBoolean(LY,(GetHandleId(VK)),(835),(true))
endif
```

常规刷新分支对唯一的金币符写 `(835)=false`，之后走 `50+5m / 50+2m`。

### 2.2 关于 \(m\) 的计时器语义（重要）

- 显示游戏钟：号角 `IU2` 时 `N=TimerGetElapsed(M)`，之后显示 \(M-N\)（见 `dota-ai-laning-routine.md`）。
- **`FUO` 用的是原始 `TimerGetElapsed(M)`，没有减 `N`**。`M` 在 `main`/`HA1` 就 `TimerStart(M,99999)`（`war3map_start_timer.j` L49–57），选人阶段已在走。
- **开局双符不受影响**（强制 100/100）。
- **2:00 常规符**：\(m=\lfloor(N+120)/60\rfloor\)，选人越久 \(m\) 越大。AI 快速 `--ai-autostart` 时 \(N\) 较短，接近社区常说的「游戏 2 分钟 → \(m\approx2\) → XP 60 / Gold 54」；长 `-ap` 选人会偏高。边路加速光环同样按原始 `M` 而非游戏钟（`war3hook_ai.cpp` 注释已记录同类现象）。

| 游戏钟（号角后） | 若 \(N\approx0\) | XP | Gold |
| ---: | ---: | ---: | ---: |
| 2:00（第二次刷符） | \(m=2\) | 60 | 54 |
| 4:00 | \(m=4\) | 70 | 58 |
| 10:00 | \(m=10\) | 100 | 70 |
| 一般式 | \(m=\lfloor t_M/60\rfloor\) | \(50+5m\) | \(50+2m\) |

---

## 三、刷符时点与坐标

### 3.1 时点

号角归零 `IU2`（`war3map_3.j` ~L6824）：

```6834:6840:War3Script/war3map_3.j
if P0==false then
...
call TriggerRegisterTimerEvent(J20,120,true)
call TriggerEvaluate(J20)
endif
```

| 事件 | 地图计时 | 动作 |
| :--- | :--- | :--- |
| 号角 0:00 | `N := TimerGetElapsed(M)`，随即 `TriggerEvaluate(J20)` | **第一次** `CBO`：`J40=true` → **上下河道各一枚 `I0RC`**，均标 `835=true`，再 `J40=false` |
| 之后每 120 s | `J20` 周期 | 同一 **`CBO`**：清 `G4`/`D4` 旧符 → 一处力量符 + 另一处金币符（`835=false`） |

`J20` 本体在 `war3map_9.j` L14793–14795：`TriggerAddCondition(..., CBO)`。  
**开局与 2:00 共用同一函数 `CBO`，仅靠 `J40` 区分双金币 / 常规。**

### 3.2 坐标

| ID | Rect | 中心 (x,y) | 变量 |
| :--- | :--- | :--- | :--- |
| 上路河道 | `G4` = (-2464,1536)–(-2240,1760) | **-2352, 1648** | `F1=GetRectCenter(G4)` |
| 下路河道 | `D4` = (2912,-2944)–(3104,-2720) | **3008, -2832** | `G1=GetRectCenter(D4)` |

`CBO` 内 `GetRandomInt(1,2)` 决定哪一侧先当 `x1,y1`（开局两处都是金币；常规时 `x1` 为力量符、`x2` 为金币）。

---

## 四、瓶装金币符 `I0RE`

| 码 | 整数 | 角色 |
| :--- | ---: | :--- |
| `I0RC` | 1227903555 | 地面金币符 |
| `I0RE` | 1227903557 | 瓶中金币符（`FR0[HJ0]`，`war3map_9.j` L12908–12915） |

装瓶（瓶主动点地面符，`VRO`）：只把 **`GetItemTypeId`（`I0RC`）** 存到英雄 hashtable key `104`，`EL1` 删掉地面物品——**不调用 `FUO`，也不复制 `835` 标记**。

使用瓶中符（`W0O` → `E91` 分支，约 L8910–8922）：

```8910:8922:War3Script/war3map_2.j
elseif E91(E81)then
if(LoadInteger(LY,(GetHandleId(BA1)),(GetHandleId(u))))>0 then
set M10=true
...
set VHO=CreateItem((LoadInteger(LY,(GetHandleId(BA1)),(GetHandleId(u)))),GetUnitX(u),GetUnitY(u))
...
call UnitAddItem(u,VHO)
set M10=false
```

`CreateItem(I0RC, …)` **新建**物品 → **无 `835=true`** → `UnitAddItem` 触发 `X8O`→`GOO`→`FUO` → 走 **使用时刻** 的 `50+5m / 50+2m`。

因此：

1. 瓶装与直接拾取**共用** `FUO`，公式同形。  
2. 数值按 **喝出 / 使用时刻** 的 `TimerGetElapsed(M)` 计算，**不是**装瓶时刻。  
3. 开局双符若先装瓶再喝：**拿不到 100/100**；在 \(m=0\) 时喝反而只有 **50 XP / 50 Gold**。中单要抢 2 级应 **直接吃** 0:00 金币符。

---

## 五、升级经验与抢 2 级

### 5.1 英雄升级表

`artifacts/ability-orders/map/war3mapMisc.txt` L61：

```text
NeedHeroXP=200,500,900,1400,2000,...（累计到 2..25 级）
```

| 目标等级 | 累计 XP | 本级所需 |
| ---: | ---: | ---: |
| 2 | **200** | 200 |
| 3 | 500 | 300 |
| 4 | 900 | 400 |

### 5.2 小兵经验

`GrantNormalXPFormulaC=6` + 默认递推 → 单位等级经验：

| 兵种 | 单位码（例） | 等级 | XP |
| :--- | :--- | ---: | ---: |
| 远程 | `edry` / `unec` | 2 | **41** |
| 近战 | `esen` / `ugho` | 3 | **62** |
| 攻城 | `ebal` / `umtw` | 4 | **88** |

（与 [`dota-6.83d-web-gameplay-data-reverse.md`](./dota-6.83d-web-gameplay-data-reverse.md) §5 一致；引擎分配，`GlobalExperience=0` 由脚本范围平分。）

### 5.3 0:00 吃符后到 2 级

| 步骤 | XP | 累计 |
| :--- | ---: | ---: |
| 直接拾取开局 `I0RC` | +100 | 100 |
| 还差 | 100 | → 需满 200 |

**中路独占经验**（敌方英雄不在分经验范围内）：

| 组合 | XP | 结果 |
| :--- | ---: | :--- |
| 1 近战 + 1 远程 | 62+41=**103** | **升 2**（余 3） |
| 2 近战 | 124 | 升 2 |
| 仅 1 近战 | 62 | 累计 162，还差 38 |
| 仅 3 远程 | 123 | 升 2 |

首波标准 3 近战 + 1 远程；独占时吃掉「1 近 + 1 远」即可，不必清完一整波。

若与敌方中单平分经验，首波单兵有效 XP 减半，需更多补刀/吃经验；抢符仍把缺口从 200 压到 100，优势不变。

影魔：到 2 级后可学 **1 级影压** 或 **2 级支配死灵**（加点序列见对线文档）。

---

## 六、流程图

```text
号角 IU2 (游戏钟 0:00)
  ├─ N = TimerGetElapsed(M)
  ├─ TriggerEvaluate(J20) → CBO (J40=true)
  │     └─ CreateItem I0RC @ F1 与 G1，SaveBoolean(835)=true ×2
  └─ TriggerRegisterTimerEvent(J20, 120, true)  // 之后每 2 分钟同一 CBO

英雄拾取 I0RC
  └─ X8O → GOO → FUO
        ├─ 835==true  → XP=100, Gold=100
        └─ else       → XP=50+5*⌊M/60⌋, Gold=50+2*⌊M/60⌋

瓶装
  └─ VRO 存 type=I0RC，删地面（不发奖）
喝出
  └─ CreateItem(I0RC) 无 835 → FUO 按使用时刻常规公式
```

---

## 七、源码索引

| 符号 | 文件 | 行号（约） | 作用 |
| :--- | :--- | ---: | :--- |
| `J40` | `war3map_1.j` | 1433 | 开局双金币开关，初值 true |
| `M` / `N` | `war3map_start_timer.j` / `war3map_3.j` | 49–57 / 6829 | 地图钟 / 号角锚点 |
| `IU2` | `war3map_3.j` | 6815+ | 号角；注册并立即 `J20` |
| `CBO` | `war3map_2.j` | 4186–4237 | 刷符 |
| `CAO` / `C8O` / `C9O` | `war3map_2.j` | 4169–4185 | 力量符随机、清旧符 |
| `FUO` / `GOO` / `X8O` | `war3map_2.j` | 7028 / 7056 / 9605 | 发奖 / 拾取分发 |
| `AA1` | `war3map_1.j` | 4986 | 加金 |
| `VTO` / `VRO` / `W0O` | `war3map_2.j` | 8777 / 8793 / 8847 | 瓶映射 / 装瓶 / 喝瓶 |
| `HJ0` / `FR0[HJ0]` | `war3map_9.j` | 12908–12915 | `I0RE` |
| `J20=CBO` | `war3map_9.j` | 14793–14795 | 刷符触发器 |
| `G4`/`D4` | `war3map_9.j` | 10492–10495 | 符点矩形 |
| `NeedHeroXP` | `war3mapMisc.txt` | 61 | 升级表 |
