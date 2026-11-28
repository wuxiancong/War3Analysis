# 任务：6.83d 近卫野点刷怪表（给 Gemini）

- 派发：Claude Opus 5.5（用户 2026-11-27 要求「安排一个任务给他，切换到他的窗口，主动输入任务并记录」）
- 时间：2026-11-27 20:1x
- 执行者：Gemini（Antigravity IDE）

## 为什么

斧王打野 AI 要决定「谁去囤哪个野点」（英雄空档囤 I5 / P25、小鸡囤近战野点）。现在只能看到当局刷出来的怪，
不知道每个野点**可能**刷哪些组合、哪些有远程、血量和金钱多少。

## 要做的

1. 从地图脚本 `War3Analysis/artifacts/ward-deward/map/Scripts_war3map.j`（6.83d 解包）找出中立野怪的刷新逻辑：
   每个野点（封野盒 r1：Q4 U4 I5 O5 A5 B5 C5 E5 D5 F5 Z5 W5）可能刷出的怪物组合。
2. 每个组合列出：单位 ID（如 ncnk / ndtw / nftb / nkob）、近战还是远程、血量、击杀金钱范围、经验。
3. 重点标出近卫这几个：E5、B5、I5、F5、W5（斧王打野用），以及哪些组合是「全近战」（小鸡可以安全囤）。
4. 结果写到 `War3Analysis/analyses/dota-683d-neutral-camp-creeps.md`，导图写到同名 `-mindmap.md`
   （按 `.agents/rules/war3-analysis-save.md`：注明模型 / 目的 / 来源 / 时间）。

## 不要做的（重要）

- **不要修改 `War3Launcher/hooker/` 下的任何文件，不要编译，不要复制 hook.dll 到 `C:\War3Run`，不要启动 / 关闭 war3。**
  Claude 正在改斧王打野代码并实机测试，两边同时编译部署会互相覆盖、互相关掉测试局。
- 只读地图脚本和现有文档，只写上面两个分析文件。

## 完成标准

- 分析文档里每个近卫野点都有组合表；E5 / B5 / I5 / F5 / W5 有明确的「近战 / 远程」结论和金钱估算。
