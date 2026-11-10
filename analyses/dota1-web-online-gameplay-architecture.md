# DotA1 网页对战：架构、与 War3 执行模型的对应关系、验证记录

日期：2026-11-09 ~ 2026-11-10
范围：`War3Angular`（主工程）、数据源 `War3Bot/images/dota_data.json` 与 `D:\Maps\DotA v6.83d.w3x`
数据逆向细节见：[dota-6.83d-web-gameplay-data-reverse.md](dota-6.83d-web-gameplay-data-reverse.md)
思维导图：[dota1-web-online-gameplay-architecture-mindmap.md](dota1-web-online-gameplay-architecture-mindmap.md)

## 1. 做了什么

| 项 | 结果 |
|---|---|
| 导航 | 顶栏「观看录像」并入新的父级菜单 **在线对战**，子项 **网页对战**（`/play`）与 **观看录像**（`/replay-3d`）；桌面端与移动端都改了，25 个语言包补了 `nav.online` / `nav.play` |
| 网页对战 | 新页面 `/play`：大厅（选英雄、单机对电脑、在线房间）+ 对局（3D 地形、WC3 式控制台、商店、计分板） |
| 逻辑引擎 | 与渲染解耦的确定性模拟，数值来自地图 SLK；无头 10 电脑对战 25 分钟可跑通，同种子两次校验和一致 |
| 联机 | 锁步指令同步：服务端只定序广播，各浏览器本地模拟；用 curl 走通了建房 / 加入 / 加电脑 / 开始 / 指令广播 |
| 录像页 | 未改行为；`Wc3MdxViewer` 只新增了 `gameplay` 选项与几个公开方法，默认路径不变 |

**没做到的**（详见 §7）：绝大多数英雄技能只是「按提示文本数值的近似」，不是脚本级还原；没有战争迷雾、信使、买活、高低地丢失；两个真实浏览器同时联机对打没有实测。

## 2. 文件清单（War3Angular）

| 文件 | 职责 |
|---|---|
| `scripts/build-gameplay-data.cjs` | 从 w3x 导出 `public/assets/dota/gameplay-data.json`（约 1.15 MB） |
| `scripts/build-pathing.cjs` | 从 wpm + doo 烘焙 `public/assets/maps/dota683/pathing.json` |
| `scripts/run-game-sim.cjs` + `game-sim-smoke.ts` | 无头冒烟测试 + 确定性校验 |
| `scripts/add-nav-online-i18n.cjs` | 导航与语言包改写（幂等，可重跑） |
| `src/app/game/game-data.ts` | 数据类型、加载器、`resolveAbilityFx()` 技能效果解析 |
| `src/app/game/path-grid.ts` | 64 码栅格 A* + 视线拉直 |
| `src/app/game/game-engine.ts` | 逻辑引擎：指令、攻击循环、伤害、出兵、野怪、神符、金钱经验、物品合成、电脑 AI |
| `src/app/game/game-session.ts` | 回合泵：单机本地回合 / 联机等服务器回合；`RoomConnection`（SSE + POST） |
| `src/app/game/game-view.ts` | 表现层：模型实例同步、血条/弹道/跳字/选择圈/技能指示器（2D 叠加画布） |
| `src/app/pages/play-3d.component.ts` | 页面：大厅 + HUD + 输入 |
| `src/server/game-rooms.ts` | 房间服务（挂在 `server.ts` 的 Express 上） |
| `src/app/replay3d/wc3-mdx-viewer.ts` | 新增 `gameplay` / `onFrame` 选项，`spawnUnit` / `loadUnitModel` / `pickGroundAt` / `focusOn` / `getPlacedBuildings` |
| `src/app/app.routes.ts`、`src/app/layout/header.component.ts`、`src/app/core/i18n/locales/*.ts` | 路由（懒加载）与菜单 |

## 3. 与魔兽争霸 III 执行模型的对应

沿用 [dota1-web-local-action-and-replay3d-fix.md](dota1-web-local-action-and-replay3d-fix.md) 的结论「网络传指令，不传状态」，这次把它做成了可对战的闭环：

| War3 / W3GS | 网页端 | 说明 |
|---|---|---|
| 玩家输入 → Order | `Command`（`move/amove/attack/stop/hold/cast/learn/buy/sell/use/swap`） | `game-engine.ts` 顶部类型定义 |
| `W3GS_OUTGOING_ACTION` | `POST /api/game/rooms/:id/cmd` | 客户端每 ~33ms 合并上行 |
| 主机汇总 → `W3GS_INCOMING_ACTION`（sendInterval ≈ 100ms） | SSE 事件 `turn`：`{ n, cmds:[{slot,c}] }`，服务端每 100ms 一次 | 服务端只定序，不跑逻辑 |
| 本地模拟层按相同种子执行 | `GameEngine.step(cmds)`，逻辑帧 50ms，2 帧一回合 | mulberry32 随机数，禁用 `Math.random`/时钟 |
| `W3GS_OUTGOING_KEEPALIVE` 校验和 | `POST …/sum`，每 50 回合上报 `engine.checksum()` | 不一致时服务端广播 `desync`，HUD 显示警告 |
| `W3GS_SLOTINFOJOIN` | SSE 事件 `lobby` | 10 槽位：0-4 近卫，5-9 天灾 |
| `W3GS_COUNTDOWN_END` | SSE 事件 `start`：种子 + 最终槽位 | |
| 表现层只读状态 | `GameView.sync()` | 位置指数平滑掩盖 50ms 步进 |

选 SSE + POST 而不是 WebSocket 的原因：不新增依赖，而且 `ng serve` 开发模式下 `/api` 是经 Angular 的 SSR 中间件转到 `server.ts` 的，WebSocket 升级请求走不到那里。实测 SSE 在开发服务器下不被缓冲（3 秒内收到 18 个 `turn`）。

**确定性的边界**：引擎只用四则运算、`Math.sqrt/atan2/cos/sin/pow`。`sqrt` 与四则是 IEEE 精确的，三角函数在不同 JS 引擎间末位可能不同，所以**同内核浏览器之间可期望一致，跨内核（Chromium ↔ Firefox）不保证**——这正是保留校验和检测的原因。跨内核一致性没有测过。

## 4. 引擎规则与数据来源

| 规则 | 实现 | 来源 |
|---|---|---|
| 英雄面板 | `recalcHero()`：生命 = HP + 力×19；护甲 = def − 1 + 敏×0.14；攻击 = dmgplus + 骰子 + 主属性；攻速 = cool/(1+敏×0.01+装备) | SLK + `war3mapMisc.txt` |
| 攻击循环 | 追击 → 前摇 `dmgpt`（随攻速缩放）→ 伤害点（近战直接结算 / 远程发弹道 `Missilespeed`）→ 冷却 | `UnitWeapons.slk` + Profile |
| 伤害 | `伤害 × 克制表[攻击类型][护甲类型] × (1 − 0.06a/(1+0.06a))`；负护甲 `2 − 0.94^(−a)` | 表来自地图；公式为公开机制，未做二进制核对 |
| 出兵 | 每 30 秒；3 近战 + 1 远程；每 7 波 1 攻城；999/1999/2999 秒近战 +1，2699 秒远程 +1；兵营被毁出超级兵 | `war3map.j` `SPO()` |
| 金钱 | 初始 603；每 0.6 秒 +1；补刀赏金 = `bountyplus + dice×sides` | [dota-gold-periodic-increment-mechanism.md](dota-gold-periodic-increment-mechanism.md) + SLK |
| 经验 | 小兵按等级递推（41/62/88），1300 码内平分；升级表 `NeedHeroXP` | 引擎公式 + 地图常量 |
| 学技能 | 英雄等级 ≥ `reqLevel + levelSkip × 当前技能等级` | `AbilityData.slk` |
| 建筑保护链 | T2←T1，T3←T2，兵营←T3，T4←任一 T3，基地←全部 T4 | DotA 规则（未从脚本逐条取证） |
| 物品 | 基地 / 边路 / 神秘商店分区购买；材料齐全自动合成，成品落在材料占用的最小格；半价出售 | `Sellunits` + `dota_data.json` + [warcraft-iii-dota-item-combine-slot-placement.md](warcraft-iii-dota-item-combine-slot-placement.md) |
| 野怪 | 整分刷新、营地有单位则不刷（封野）；小/中/大/远古/Roshan 组合池 | 单位数值来自 SLK；组合为手工整理 |
| 神符 | 0:00 双赏金，之后每 2 分钟一侧强化（双倍/极速/恢复/隐身） | 简化实现 |
| 电脑 | 加点、先出鞋再出属性装、残血回泉、跟兵线、避塔、对英雄放已实现的技能 | 自写；逻辑在引擎内以保证各端一致 |

## 5. 页面与操作

- 大厅：112 个英雄按「近卫/天灾 × 力量/敏捷/智力」分组（分组来自酒馆 `Sellunits`），右侧显示属性与技能中文说明；脚本技能会标注「未还原特效」。
- 单机：选阵营、5v5 / 3v3 / 1v1 中路，其余位置由电脑随机英雄补齐。
- 在线：创建房间 → 其他人打开同一站点的 `/play` 在列表里加入 → 房主加电脑 / 开始。
- 对局操作对齐 WC3：右键移动/攻击、`A` 攻击移动、`S`/`H`/`M`、技能热键取自地图 `Hotkey`、`O` 学习或 `Ctrl+热键` 加点、物品小键盘 7/8/4/5/1/2（或 1-6）、`F2` 商店、`Tab` 计分板、空格回英雄、边缘滚屏/方向键/中键拖动、滚轮缩放。
- 地址加 `?debug` 会把组件挂到 `window.__play3d`，可在控制台手动推进逻辑帧（本次浏览器验证用的就是它）。

## 6. 验证记录

| 验证 | 方法 | 结果 |
|---|---|---|
| 构建 | `npx ng build`、`npx tsc -p tsconfig.app.json --noEmit` | 通过 |
| 引擎确定性 | `node scripts/run-game-sim.cjs 25`（同种子跑两次比校验和） | 一致；25 分钟模拟约 20 秒 |
| 引擎行为 | 同上输出 | 双方电脑升到 9~13 级、有击杀/助攻/补刀、外塔与二塔陆续被拆、`动力鞋` 自动合成成功 |
| 兵线时序 | 追踪中路小兵坐标 | 0:20 左右在 (−200,−700) 附近交战，与原图一致 |
| 房间服务 | curl：建房 / 加入 / 加电脑 / 非房主开始被拒 / 开始 / 上行指令 / 错误凭证被拒 | 全部符合预期；多余字段被剥离、非法指令被丢弃 |
| 浏览器 | 内置浏览器开 `/play`：大厅、选英雄、1v1 开局、学技能、右键移动、镜头跟随、与敌方英雄交战 | 画面与 HUD 正常，控制台无报错 |

过程中由验证暴露并修掉的两个真实问题：

1. `YTlb` 视线阻断器被当成树盖了通行章，近卫泉水出口被封（表现：近卫电脑全程 1 级）。
2. 兵线路点取的是塔/兵营坐标，而这些位置已盖阻挡章，小兵走到边缘就永远「没到达」而停住（表现：1 分钟时最近的敌兵还在 5800 码外）。把到达半径放大到 300 后解决。

**验证的局限**：内置浏览器面板处于隐藏状态，`requestAnimationFrame` 被限到约 1 帧/秒，所以浏览器里的对战是用 `?debug` 钩子手动推进逻辑后截图确认的，没有以 60 帧实时玩过；两个浏览器真实联机对打没有测。

## 7. 已知问题与取舍

| 问题 | 说明 |
|---|---|
| 技能还原度 | 只有「伤害 / 眩晕 / 减速 / 治疗 / 闪烁」能从数据解析的技能生效；其余主动技能只扣蓝进冷却并提示。被动只映射了暴击、闪避、重击、吸血和几种光环（且光环目前只加给自己） |
| 模型缺失 | `public/assets/wc3` 只解包了部分单位模型；缺的会回退到替代模型（英雄 → 圣骑士/深渊领主，野怪 → 狗头人）。截图里有个敌方英雄身边出现白色方块，是该模型的粒子贴图缺失 |
| 路径大小写 | SLK 里模型路径是小写（`units\nightelf\…`），Windows 上没问题；部署到大小写敏感的文件系统需要规范化 |
| 没有战争迷雾 | 全图可见（隐身神符只对敌方隐藏模型与血条） |
| 没有信使 / 买活 / 圣坛储物 | 阵亡时只能买基地商店物品 |
| 电脑 | 不会打野、不会回家补装备（钱会越攒越多）、不会配合 |
| 退出对局 | 用整页刷新回大厅（WebGL 上下文复用会残留旧场景） |
| 后台标签页 | 单机在后台会变慢（等同暂停）；联机回到前台后一次追完积压回合 |
| 房间服务 | 状态在内存里，重启即丢；凭证是随机 UUID，放在 SSE 的查询串里；没有接站点登录 |
| ESLint | `play-3d.component.ts` 有 18 条模板无障碍规则报错（`div` 上的 `click`）；功能不受影响，未处理 |
| 既有数据 | `buildings.json` 个别塔 `unitId` 与层级不符、`dota-heroes-archive.ts` 护甲少减 1，均未改 |

另：仓库里 `.env.example` 提交了一串看起来是真实的 Gemini API Key，建议作废并换成占位符（与本次改动无关，未动它）。

## 8. 运行

```powershell
cd D:\Qt\workspace\War3Angular
node scripts\build-gameplay-data.cjs   # 地图或 dota_data.json 变了才需要重跑
node scripts\build-pathing.cjs
npm run dev                            # http://localhost:4200/play
node scripts\run-game-sim.cjs 20       # 无头冒烟
```

依赖本机路径：`D:\Maps\DotA v6.83d.w3x`、`D:\Qt\workspace\War3Bot\images\dota_data.json`（构建脚本）；图标由 `server.ts` 从 War3Bot 目录静态挂载（沿用录像页的做法）。

## 9. 建议的下一步

1. 找一个英雄（建议技能全是单体/范围伤害的，如 宙斯、莉娜）把四个技能按 `war3map.j` 触发器逐个实现，建立「脚本技能 → TS 实现」的模板。
2. 两台机器实测联机，重点看跨浏览器内核是否失步。
3. 补解包缺失的英雄/野怪模型与粒子贴图。
4. 战争迷雾与高低地视野（需要 w3e 悬崖层 + 视线阻断器 `YTlb`，后者这次已经定位到）。
