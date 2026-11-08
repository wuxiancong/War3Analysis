# DotA1 网页端：魔兽本地动作机制对齐 + replay3d 修复说明

日期：2026-11-08  
范围：`War3Angular/src/app/replay3d`、`public/assets/maps/dota683/scene-sync.json`

## 1. 魔兽争霸 3 本地如何“收到网络数据后执行动作”

DotA1（WC3 地图）不是现代帧同步服务端权威 FPS，而是 **锁步 / 指令同步**：

1. **玩家输入 → 指令（Order）**  
   本地 UI 把右键攻击、A 键、技能热键等变成游戏指令（目标单位/点、技能 ID、物品槽等）。
2. **指令进入同步队列**  
   联机时指令经主机/对等同步；录像里则按时间轴回放同一批 action。
3. **本地模拟层执行**  
   每个客户端用相同的随机种子与指令序列跑同一套逻辑：
   - 寻路 / 转身 / 切换 MDX 序列（Walk / Attack / Spell / Death）
   - 武器系统到点后触发伤害事件
   - 生命值、buff、金钱、经验在本地状态机更新
4. **表现层只读状态**  
   掉血、血条、飘字是状态变化的渲染，而不是“网络直接传掉血包”。

要点：**网络传的是指令与定时器事件，不是“小兵 -37 HP”这种表现包。**  
网页端 `DotaSceneSim` 是简化的本地模拟器：用配置的刷兵计时器 + 兵线路点 + 近战 DPS 近似 WC3 的出兵与交战，而不解析完整 JASS/物编。

### 自动出兵（对齐真实图）

- WC3/DotA：`war3map.j` 用周期性计时器在兵营附近 `CreateUnit`，再对小兵下 **攻击-移动** 到敌方路线。
- 网页端：`creepWaveIntervalMs`（默认 30s）触发 `spawnWave()`，按 `lanes[]` 生成近卫/天灾波次，沿 `waypoints` 推进；遇敌进入攻击序列并扣 HP。

### 攻击掉血（对齐真实图）

- WC3：单位进入攻击距离 → Attack 序列 → 伤害点帧 → `UnitDamageTarget` → 生命变更 → 死亡动画/移除。
- 网页端：`tickUnits` 在 ~280 码内互选敌兵，播放 `Attack` 序列，按 `dps * dt` 扣血；归零后 detach 并飘金。

## 2. 本次发现的根因（修复前）

| 问题 | 根因 |
|---|---|
| 小兵无攻击/不掉血、血条没有 | `scene-sim.ts` / `replay-3d.component.ts` 被半截合并写坏：`tickUnits` 语法断裂；模板里头顶血条 DOM 丢失；`scene-sync.json` JSON 非法导致 lanes 空 |
| 下路兵线不对 | 旧路径 Y≈-6080，真实下路塔在 Y≈-6688~-6816（偏北约 600+） |
| 下方面板太高 | 控制台 `aspect-ratio: 1600/342` 在 16:9 下约占屏高 35%+ |
| 坡度“隆起” | 单位用最近格子高度（阶梯采样）；悬崖层差被 clamp 到 2，高差悬崖mesh与地表不匹配 |
| 野怪不对 | 同 tier 刷同一模型；缺少 composition |

损坏主要出现在 `64fe5f9` 之后的合并提交；已先回滚关键文件再做定点修复。

## 3. 修复内容

1. **恢复** `scene-sim.ts`、`replay-3d.component.ts`、`wc3-mdx-viewer.ts`、`wc3-doodad-patch.ts`、`scene-sync.json` 至可编译基线。
2. **兵线**：按 `buildings.json` 防御塔/兵营坐标重写 top/mid/bot waypoints（下路贴塔：-6816/-6688/-6752）。
3. **战斗/血条**：恢复交战逻辑与头顶血条 overlay；暂停回放时场景模拟仍以 1x 推进，便于观察兵线。
4. **面板**：控制台限制 `max-height: 26vh`，并略降相机 HUD 补偿。
5. **地形贴地**：`sampleHeight` 改为与地面四边形剖分一致的**三角插值**（对齐 mdx-m3-viewer `heightAt`/`groundNormal`），斜坡上不再用简单双线性错位。
6. **野怪**：`composition` 字段按营地点名混合 Kobold/Troll/Centaur/Furbolg/Golem（受现有 MPQ 解包模型种类限制）。
7. **命令卡状态**：停止时截断行走关键帧；站立后 `move/attack/patrol` 收敛为 `stop`，避免一直显示「移动」。
8. **地形源**：`named/war3map.w3e` 已与 `D:\Maps\DotA v6.83d.w3x` 对照（129×129，layer 差最大 2）；斜坡主要靠 `groundHeight` 连续变化而非悬崖层。

## 4. 后续可增强（逆向工具）

- 用 `MPQEditor` 从 `War3Launcher/versions` + DotA map 抽取更多中立模型（Gnoll/Satyr/Dragonspawn/Roshan 专用）。
- 用 Ghidra/`D:\REA` 对照 1.26/1.27 指令派发与 `war3map.j` 出兵函数，把网页端从“近似 DPS”升级到“攻击间隔 + 伤害点帧”。
- 悬崖：放宽/按真实 cliff 目录生成超过 2 级高差的 mesh，消除高台边缘视觉隆起。

## 5. 验收

- `scene-sync.json` 可 `JSON.parse`
- `tsc` 无 `scene-sim` / `replay-3d` 语法错误
- 下路小兵沿 T3→T2→T1（南缘）再北上天灾高地
- 对碰时有 Attack 动画、HP 下降、头顶血条
- 各营地模型组合可区分，Roshan 点仅 1 只大体型石魔
