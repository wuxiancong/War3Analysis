# 任务：逆向六路兵线的精确出兵点、路点链和出兵时序（给卡兵 AI 用）

**给**：Cursor Grok　**布置时间**：2026-11-21　**工作目录**：`D:\Qt\workspace\War3Analysis`

## 背景

卡兵 AI 在 `War3Launcher/hooker/war3hook_ai_tactics.inl` 里用一张手写的车道表 `kAiLanes[6]`，每一路是「兵营坐标 → 一塔坐标」的一条直线。今天实测发现几个问题：

1. **近卫上路实际出兵点和表里的「兵营」点差得远。** 表里是 (-6368, -4480)，实测兵刷在 (-6192, -4304) ~ (-6128, -4064)，而且沿车道已经在门口前 100~300。找新一波兵的条件（门口 900 内、沿车道没走出 150）因此很容易漏判。
2. **车道是直线，实际兵线在弯道处会横向漂。** 上路第 29 波，9 秒内整波中位横向从 -16 漂到 +139。AI 已改成「预判漂移」（2026-11-21），但根本做法应该用地图里真实的路点链做车道坐标。
3. **在号角之前开 `-block start`，这一局整整 4 分钟一波都没认到**；号角后再开就正常。怀疑和第一波出兵时机，或读图时预放的单位有关。

已有分析：`analyses/dota-lane-creep-trajectory.md`（出兵点 → `attack` 到路点 `O2[lane]`，进区触发器再改下一个目标）。它第 193 行的「静态路点 dump」还没做，摘录在 `artifacts/dota-web-gameplay/war3map.j-creep-spawn-excerpt.txt`。

## 要做的事

1. **出兵点**：近卫、天灾各 3 路，每路的出兵 rect 或 location。
   - 给出精确坐标和 rect 范围，以及近战、远程、攻城车各自刷在哪。
   - 来源：`war3map.j` 和 `war3map.w3r`（地图在 `maps/` 或游戏目录，用 MPQ 工具解包）。
2. **路点链**：每一路兵从出兵点到对方基地，依次 `attack`（或 `move`）到的每个路点。
   - 每个路点给出坐标、对应的 rect 名或变量名（`O2[]` 等），以及「进区换下一个目标」的触发器。
   - 标出每一路**己方一塔**在路点链上的位置。
3. **出兵时序**：
   - 第一波相对号角（「号角已吹响」）的时间；
   - 出兵间隔，以及每波兵出现的先后顺序（同一波里近战、远程间隔多少毫秒）；
   - 第几波有攻城车；兵的升级时间点（血量和攻击随时间增长）；
   - 超级兵的条件；
   - **读图或号角前，地图会不会预先 `CreateUnit` 兵线类型的单位**（esen / edry / ebal / ugho / unec / umtw）。这关系到第 3 个问题。
4. **每波兵的数量和组成**：随时间变化的表，比如 0:00 是 3 近战 + 1 远程，第 7 波加攻城车。卡兵评分要用它判断漏兵比例，现在实测有时 4 只、有时 5 只。
5. **产出一个头文件**：`artifacts/lane-spawn/DotaLaneWaypoints.h`，给 hooker 直接 include。
   - 每路包含：出兵点、路点数组、一塔下标；
   - 坐标用 float，注释写来源（rect 名或 `war3map.j` 行号）；
   - 只写数据，不改 hooker 代码。
6. **对卡兵 AI 的建议**：
   - 用路点链替换直线车道后，`aiLaneProj`（沿车道距离 + 横向）应该怎么算，比如分段折线投影；
   - 每路兵营门口的等兵位推荐坐标；
   - 第 3 个问题的原因判断和修法。

## 要求

- 多版本：这次主要是地图脚本，跟 War3 版本无关。如果涉及引擎（比如单位创建事件），给 1.27 的 RVA。
- 工具见 `.agents/rules/war3-reverse-toolkit.md`。
- 需要实机看的：只读内存，或按 `.agents/rules/ai-autostart.md` 开局，用 RemoteControl `units`（`127.0.0.1:6120`，结果在 `logs/AiUnit.log`）读兵的坐标。**不要往游戏进程写内存，也不要在游戏线程以外调用 JASS 原生函数。**
- 输出：
  - 正文：`analyses/dota-lane-spawn-waypoints.md`
  - 导图：`analyses/dota-lane-spawn-waypoints-mindmap.md`
  - 数据和脚本：`artifacts/lane-spawn/`
- 文档开头写明：分析模型、分析目的、命名方式、分析时间、验证状态、证据（规则 `.agents/rules/war3-analysis-save.md`）。
- 不改 War3Launcher / hooker 代码。
