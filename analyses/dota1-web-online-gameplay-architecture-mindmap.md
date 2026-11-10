---
title: DotA1 网页对战架构思维导图
markmap:
  colorFreezeLevel: 2
  maxWidth: 420
---

# DotA1 网页对战（War3Angular）

## 一、入口与导航

### 顶栏「在线对战」
- 网页对战 `/play`（新，懒加载）
- 观看录像 `/replay-3d`（原有，行为未改）
- 25 个语言包：`nav.online` / `nav.play`

### 大厅
- 112 英雄：阵营 × 主属性分组
- 单机：5v5 / 3v3 / 1v1 中路
- 在线房间：创建 / 加入 / 加电脑 / 开始

## 二、数据源

### 地图 w3x
- SLK：单位 / 技能 / 物品
- `war3mapMisc.txt`：常量与克制表
- Profile：中文提示、热键、弹道、货架
- wpm + doo：寻路栅格

### War3Bot
- `dota_data.json`：商店码 → 物品码、合成表、技能槽位
- `heroes.json` 与图标目录

### 产物
- `gameplay-data.json`（112 英雄 / 450 技能 / 193 物品 / 92 配方 / 15 商店）
- `pathing.json`

## 三、执行模型（对齐 War3）

### 锁步
- 只传指令，不传状态
- 逻辑帧 50ms，回合 100ms
- 相同种子 + 相同指令 → 相同结果

### W3GS 对应
- OUTGOING_ACTION → `POST …/cmd`
- INCOMING_ACTION → SSE `turn`
- KEEPALIVE 校验和 → `POST …/sum`
- SLOTINFOJOIN → SSE `lobby`
- COUNTDOWN_END → SSE `start`

### 为什么是 SSE + POST
- 不加依赖
- 开发模式下 WebSocket 升级到不了 `server.ts`

### 确定性边界
- mulberry32，不用 `Math.random` / 时钟
- 同内核一致；跨内核三角函数末位可能不同
- 校验和不一致 → HUD 警告

## 四、模块

### `game-engine.ts`
- 指令 / 攻击循环 / 伤害结算
- 出兵 / 野怪 / 神符
- 金钱 / 经验 / 升级 / 学技能
- 商店分区 / 自动合成
- 建筑保护链 / 胜负
- 电脑 AI（在引擎内）

### `path-grid.ts`
- 64 码格 8 向 A*
- 视线拉直

### `game-session.ts`
- 单机本地回合
- 联机等服务器回合、积压追帧
- `RoomConnection`

### `game-view.ts`
- 模型实例同步、动画序列
- 2D 叠加：血条 / 弹道 / 跳字 / 指示器

### `play-3d.component.ts`
- 大厅 + HUD + 输入
- 商店 / 计分板 / 小地图

### `game-rooms.ts`
- 房间、槽位、指令白名单
- 100ms 回合广播

### `wc3-mdx-viewer.ts`（扩展）
- `gameplay` / `onFrame`
- `spawnUnit` / `pickGroundAt` / `focusOn`

## 五、验证

### 通过
- 构建与类型检查
- 无头 25 分钟：同种子校验和一致
- 中路 0:20 交战
- 房间 API 全流程（curl）
- 浏览器：开局 / 学技能 / 移动 / 镜头 / 交战

### 验证中修掉的问题
- `YTlb` 误当树 → 泉水被封
- 路点在塔的阻挡章里 → 小兵停住

### 局限
- 浏览器面板隐藏，帧率被限，靠 `?debug` 推进
- 双浏览器实机联机未测

## 六、已知问题

- 技能多为数值近似，脚本技能未还原
- 缺模型 / 粒子贴图（白色方块）
- 无战争迷雾、信使、买活
- 电脑不打野、不回家补装
- 退出对局靠整页刷新
- 房间状态仅在内存
- 模板无障碍 lint 报错未处理

## 七、下一步

- 选一个英雄做脚本级技能还原
- 两台机器实测联机与跨内核
- 补解包模型
- 战争迷雾与高低地
