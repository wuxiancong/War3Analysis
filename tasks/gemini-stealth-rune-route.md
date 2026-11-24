# 任务：隐蔽看符路线——路点可走性 + 敌方视野核验（中路 ↔ 上 / 下神符）

**给**：Antigravity Gemini　**布置时间**：2026-11-24　**工作目录**：`D:\Qt\workspace\War3Analysis`
**布置人**：Claude Opus 5.5
**顺序**：先把手上的 `tasks/gemini-lasthit-prediction-engine-facts.md` 写完正文（你的「飞行距离 −100」结论已经被我用进代码了，谢谢），再做这个。`tasks/gemini-llm-mcp-gaps-and-prototype.md` 的第二部分（`artifacts/llm-mcp-server/` 原型）还没交，排在这个之后。

## 背景

用户要求：AI 中单去看 / 装神符时，要**走敌方看不到的路线**，不能从敌方塔下面过去，要悄悄地去。

我已经在 `War3Launcher/hooker/war3hook_ai_lane.inl` 加了 `aiStealthNext`：当直线路径离敌方中路一塔不到 1950 码（塔白天视野 1900）时，改走下面这些路点。路点取自同文件里已有的眼位 / 站位表（`kAiTopRiverWardPool` 等），**没有实机走过**。

| 阵营 → 符点 | 路点（按顺序） |
|---|---|
| 近卫 → 下路符 (3008,-2832) | (-412,-1482) → (1468,-3060) |
| 近卫 → 上路符 (-2352,1648) | (-1596,-330) → (-2232,80) |
| 天灾 → 上路符 | (-520,-76) → (-1224,704) |
| 天灾 → 下路符 | (3160,-2232) |

敌方中路一塔：天灾 (1056,-96)，近卫 (-1504,-1824)（`kAiLanes`）。

## 要做的事

1. **可走性**：用地图的 `war3map.wpm`（通行网格）和 `war3map.w3e`（地形 / 悬崖层），确认每个路点和相邻两段之间都能直接走通。War3 寻路会不会绕路？绕的话实际会经过哪里？
2. **视野**：沿每条路线，按每 50 码采样，算出会被哪些敌方视野源看到：
   - 塔：白天 1900 / 夜晚 800（`war3-tower-creep-aggro.md`）；
   - 中路敌方小兵：按 6.83d `UnitBalance.slk` 的 sight / nsight，交战点取中路河道附近；
   - 树木挡视线（`war3map.doo` 树 + DestructableData 的遮挡高度），高地挡低地视线。
   - 要有依据，参考 `dota-683d-vision-and-fog-juke.md`、`warcraft-iii-fog-of-war-implementation.md`。
3. **给出更好的路线**：四条路线各给一条「白天也不进敌方塔视野、尽量贴树走、离中路交战点尽量远」的路点序列，同时给出比直线多走多少时间（影魔移速 305）。如果某条路线怎么走都会被看到，写明最短的暴露段在哪里、有多长。
4. **全版本规则**：这次主要是地图数据，不涉及 `game.dll`。如果用到了 `game.dll` 的地形 / 视野函数，要列出 11 个版本的 RVA。

## 红线

1. **不要开游戏、不要连 6120**：Claude 正在跑补刀实机测试。
2. **不要改** `War3Launcher/hooker` 等源码，也不要动 `build` 目录：路点写进文档，由 Claude 来改代码。
3. 地图文件只读（MPQ 解压到你自己的目录：`D:\Mpqeditor\Win32`）。
4. 不 commit / push。拿不出证据的结论标 ❓。

## 交付

| 交付物 | 位置 |
|---|---|
| 正文（结论放最前面：四条路线的路点表 + 暴露段；文件开头写分析模型 / 目的 / 命名 / 时间 / 验证状态） | `analyses/dota-ai-stealth-rune-route.md` |
| 思维导图 | `analyses/dota-ai-stealth-rune-route-mindmap.md` |
| 脚本、通行 / 视野叠图 | `artifacts/stealth-rune-route/` |
