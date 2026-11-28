# 任务：逆向「野怪是否在睡觉」（给 Gemini）

- 派发：Claude Opus 5.5（用户 2026-11-27：「请给 Gemini 安排一个任务，逆向野怪是否在睡觉？如果在睡觉，让英雄去打那个在睡觉的野怪，让小鸡去拉那种没有睡觉的野怪」）
- 时间：2026-11-27
- 执行者：Gemini（Antigravity IDE）

## 背景

斧王打野测试（`-task axe`，DotA 6.83d，War3 1.26）里小鸡去囤野（走进野点盒、被打一下就拉出盒）有时拉不动：
用户判断是**野怪在睡觉**（夜里中立野怪睡觉，不会主动攻击走近的单位，只有被打才醒）。
睡着的野点小鸡拉不了，但英雄可以直接打；没睡的野点才适合让小鸡去拉。

## 要做的

1. **怎么判断一个中立单位在睡觉**
   - JASS 有 `native UnitIsSleeping takes unit whichUnit returns boolean`（common.j）。确认它在 `game.dll` 里的实现函数，
     以及 hook 怎么调用：hook 已有 `g_aiNativeImpl[...]` + `aiCallNative1`（见 `War3Launcher/hooker/war3hook_ai.cpp` 的 native 名表，
     例如 `"IsUnitVisible", "GetLocalPlayer", "GetUnitAbilityLevel", "GetHeroLevel"`），说明要加一项 `"UnitIsSleeping"` 是否可行、返回值怎么读。
   - 如果不走 native，也给出单位对象里「睡眠」状态的字段偏移（CUnit 结构）作为备用。
2. **什么时候会睡**：
   - 昼夜时间怎么读（`GetFloatGameState(GAME_STATE_TIME_OF_DAY)` 或等价）；
   - 野怪几点睡、几点醒（默认 18:00 ~ 6:00）；
   - 哪些单位类型不睡（单位数据「能否睡眠」字段）；
   - 被攻击 / 被技能打中后醒来的规则；醒了以后会不会再睡、多久再睡。
   - DotA 6.83d 地图脚本（`War3Analysis/artifacts/ward-deward/map/Scripts_war3map.j`）有没有改野怪睡眠（例如 `UnitAddSleep` / `UnitAddSleepPerm` / `SetUnitCreepGuard`）。
3. **按规则覆盖全部版本**：`War3Launcher/versions` 下**每个** `game.dll` 版本都要列出相关函数 / 偏移的 RVA（`.agents/rules/war3-gamedll-all-versions.md`），注明工具与方法（`.agents/rules/war3-reverse-toolkit.md`）。
4. 结果写到 `War3Analysis/analyses/war3-neutral-creep-sleep.md`，导图 `war3-neutral-creep-sleep-mindmap.md`（注明模型 / 目的 / 来源 / 时间）。

## 结论要能直接给 AI 用

文末写一段「给斧王打野 AI 的接法」：
- 每个野点：至少一只野怪在睡 → 标记「睡着」：**英雄去打**（一刀就醒，不影响）；
- 全部醒着 → 标记「醒着」：**小鸡去拉**（走近就会被追）；
- 判断只用本地玩家看得见的单位（看不见的单位不算，见 memory `ai-no-invisible-info`）。

## 不要做的（重要）

- **不要修改 `War3Launcher/hooker/` 下的任何文件，不要编译，不要复制 hook.dll 到 `C:\War3Run`，不要启动 / 关闭 war3。**
  Claude 负责改斧王打野代码和实机测试；两边同时编译部署会互相覆盖、互相关掉测试局。
- 只读逆向 / 地图脚本 / 现有文档，只写上面两个分析文件。
