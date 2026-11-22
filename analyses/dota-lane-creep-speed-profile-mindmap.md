# DotA 6.83d 兵线小兵速度剖面与非匀速成因（思维导图）

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 以思维导图汇总 DotA 6.83d 兵线小兵物编、脚本、War3 引擎机制、实测速度曲线与卡兵 AI 预测结论 |
| **命名方式** | `dota-lane-creep-speed-profile-mindmap` |
| **分析时间** | 2026-11-20 |
| **配套正文** | [`dota-lane-creep-speed-profile.md`](./dota-lane-creep-speed-profile.md) |

```mermaid
flowchart LR
    ROOT["DotA 6.83d 兵线小兵速度剖面<br/>为什么实测不是匀速 325？"]

    ROOT --> D["1. 物编与环境（SLK）"]
    ROOT --> S["2. 地图脚本（war3map.j）"]
    ROOT --> E["3. War3 引擎（game.dll 全 11 版）"]
    ROOT --> M["4. 实测速度曲线"]
    ROOT --> AI["5. 给卡兵 AI 的结论"]

    D --> D1["全兵种基础移速 = 325<br/>esen/edry/ebal/ugho/unec/umtw + 超级兵"]
    D --> D2["碰撞与推进窗口<br/>近战/车 col=16, 远程 col=8<br/>近战/远程 propWin=60°, 攻城车 30°"]
    D --> D3["前 7 分钟边路调速光环（15s）<br/>A2V1(优势路): +25% → 406.25<br/>A2V0(劣势路): -25% → 243.75<br/>中路与攻城车无 Buff"]
    D --> D4["地形/昼夜不改基础移速<br/>仅地形窄口/树林影响寻路折线"]

    S --> S1["出兵 SPO（每 30s）<br/>CreateNUnitsAtLoc(..., 270° 正南)<br/>不直接下令，靠进区触发"]
    S --> S2["逐只单令（无 GroupPointOrder）<br/>S3O/S6O/S8O/SAO/SCO/SEO<br/>IssuePointOrderLoc(u, attack, O2[lane])"]
    S --> S3["中继区重复下令<br/>SA/KA/TA/LA/NA/MA 约 550~930 处<br/>目标相同，无明显停顿"]
    S --> S4["拐点换路点（NUO）<br/>BZ/ZZ/DZ 半径 300 切 U0/II<br/>边路 90° 拐弯在一塔之后"]

    E --> E1["无渐进加速度（高置信）<br/>CPoPosCl+0xB4(acc) := maxSpeed<br/>1 tick(31.25ms) 瞬时满速<br/>AddVelocity 1.26:0x4A70D0 / 1.27:0x10CE30"]
    E --> E2["propWin 硬二值门控（高置信）<br/>StepTurnAndMove 1.26:0x493FA0 / 1.27:0x11CFD0<br/>|Δθ| >= propWin → speed=0 原地转<br/>|Δθ| < propWin → 100% 满速边走边转"]
    E --> E3["编队限速（高置信）<br/>MovementGroup min(unitSpd, grpSpd)/32<br/>1.26:0x474EF5 / 1.27:0x03E900<br/>DotA 单只下令+车速325 → 不拖慢整波"]
    E --> E4["友军碰撞避让（中高置信）<br/>局部碰撞返回非 0 → forceStop=1 整 tick 置 0<br/>+ CPoSeparate 侧向绕行（停走脉冲）"]

    M --> M1["近卫下路实测（AiUnit.log 34波 >=7m）<br/>200~500 停顿起步 36~283<br/>600~5800 准匀速 305~320<br/>5800~6100 & 7400~8000 弯道降至 229~285"]
    M --> M2["近卫下路 <7m（W12/W13）<br/>2100~5800 实测 365~405（+25%）<br/>~6000（15s）回落至 325"]
    M --> M3["近卫中路出兵段实测（5波）<br/>-200~300 从 143 渐升至 258<br/>成因：270°→48° 大转身 138° + 窄口拥挤"]
    M --> M4["VM 墙钟漂移纠偏<br/>部分波间隔 37~45s（非 30s）<br/>表观延迟 1.3~1.6s 含墙钟慢放误差"]

    AI --> AI1["弃用固定 325<br/>改读真实移速或按 <7m/15s 分档<br/>406.25 / 243.75 / 325"]
    AI --> AI2["出兵与脱困按满速预测<br/>无加速爬坡：一旦转入 propWin<br/>下一 tick 瞬间冲出"]
    AI --> AI3["弯道按切线外推 + 防外侧脱钩<br/>3300~4300 外侧兵甩至 -175<br/>用瞬时切线向量，不按直线降速"]
```
