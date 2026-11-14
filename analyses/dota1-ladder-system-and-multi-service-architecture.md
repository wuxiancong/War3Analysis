# Dota1 天梯积分系统与分布式多服务系统架构设计白皮书

本文档系统性地梳理与总结了在分布式对战平台中，针对魔兽争霸 III（DotA 6.83d）天梯积分系统、分布式服务交互、赛后战绩结算与网络 API 安全设计的全套工程架构。

思维导图与时序交互图见：[`dota1-ladder-system-and-multi-service-architecture-mindmap.md`](./dota1-ladder-system-and-multi-service-architecture-mindmap.md)

---

## 一、 系统背景与架构职责划分

当前工作区包含三大核心工程，各司其职，协同完成对战平台的整个业务闭环：

| 子系统工程 | 技术栈 | 角色定位与核心职责 |
| :--- | :--- | :--- |
| **`War3Bot`** | C++17 / Qt 5.15 / W3GS | **分布式游戏主机宿主 (Host Bot) 与匹配引擎**：<br>1. 管理房间生命周期与 W3GS 锁步同步网络帧；<br>2. `MatchManager` 实现基于动态搜索半径扩张的撮合与蛇形平衡配队；<br>3. 实时捕获并解析 DotA 底层 `0x6B` 战绩同步包；<br>4. 游戏结束时自动持久化全量动作流为 `.dat` 归档并执行结算。 |
| **`War3Launcher`** | C++ / Qt Quick (QML) | **客户端启动器与用户交互中心**：<br>1. 呈现大厅房间列表、天梯匹配 UI 与个人资料；<br>2. `RoomManager` 集中维护房间状态、天梯等级枚举与赛后 `0x31` 结算信号分发；<br>3. 通过 `FriendNotifyComponent` 单例与右下角置顶托盘消息面板（`trayNotifyHost`）展示可展开的积分结算卡片；<br>4. `NetworkManager` 与服务端进行 TCP 二进制封包通信。 |
| **`War3Angular`** | Angular 21 / Node.js Express 5 / SSR | **Web 开放平台 API 与数据中枢**：<br>1. 提供对外 RESTful API（玩家天梯档案、全服排行榜、历史战绩）；<br>2. 暴露特权安全结算接口 `POST /api/ladder/settle`；<br>3. 维护 MySQL 高性能连接池与单事务 ACID 落库；<br>4. 前端提供天梯榜单展示与 Three.js 3D 轨迹回放。 |

---

## 二、 天梯积分算法体系设计

传统 1v1 Elo 算法无法直接照搬到 5v5 MOBA 游戏中，现代对战平台（如 11对战平台、网易官方对战平台、完美世界平台）均采用 **“团队基础胜负分 + 个人表现分 + 动态置信度 K 因子”** 的混合评分模型。

### 1. 团队期望胜率与 Elo 基础分
设近卫方 5 人的天梯平均分为 $R_A$，天灾方 5 人的天梯平均分为 $R_B$。近卫方胜利期望 $E_A$ 与天灾方胜利期望 $E_B$ 为：
$$E_A = \frac{1}{1 + 10^{(R_B - R_A) / 400}}, \quad E_B = 1 - E_A$$

### 2. 分段动态 K 因子（Dynamic K-Factor）
为了让新手快速定位实力，同时防止高分段积分通胀，实施分段动态 K 值：
* **见习/青铜新手段（Score < 1200）**：$K = 36$，波动幅度较大，使高水平玩家快速脱离低分鱼塘；
* **稳定中分段（1200 $\le$ Score < 1800）**：$K = 30$；
* **高水平铂金/钻石段（1800 $\le$ Score < 2400）**：$K = 24$；
* **超凡大师/最强王者段（Score $\ge$ 2400）**：$K = 18$，严格控制加分，登顶难度倍增。

### 3. 个人表现分加权（Performance Score）
通过捕获玩家对局数据，综合计算战力评级（$2.0 \sim 10.0$ 分）：
$$\text{Performance} = 5.0 + 0.3 \times \left(3K + 1.5A - 2D\right) + 2.5 \times \text{KP} + \left(0.04 \times \text{CS} + 0.06 \times \text{Deny}\right)$$
* **MVP 评定**：全场胜利方综合战力最高者荣获 **MVP** 徽章，并在基础分上额外奖励 $+3 \sim +5$ 分；
* **SVP 评定**：全场落败方表现最优的“尽力局局长”评定为 **SVP**，享受免除 $35\%$ 掉分的败者保护机制；
* **逃跑/秒退惩罚（Abandon）**：中途断线超过重连保护时间或强行退出者，**强制扣除全额惩罚分（-45分），并且清空连胜纪录**。

---

## 三、 等级代码与段位称号并存体系

为了兼顾**数据库存储高效性**、**网络协议传输紧凑性**以及 **UI 视觉表现力**，系统采用了“权威代码 + 中文称号 + 组合称号”完全并存的设计架构：

| 等级索引 | 数据库存储代码 (`rank_code`) | 中文段位称号 (`rank_title`) | UI 组合显示格式 (`fullTitle`) | 对应积分下限 (`score`) |
| :---: | :---: | :---: | :---: | :---: |
| **0** | `"-"` | 见习新手 | 见习新手 (-) | 0 分 |
| **1** | `"D"` | 青铜守护 | 青铜守护 (D) | 1,000 分 |
| **2** | `"C"` | 白银先锋 | 白银先锋 (C) | 3,000 分 |
| **3** | `"B"` | 黄金勇士 | 黄金勇士 (B) | 5,000 分 |
| **4** | `"A"` | 铂金统领 | 铂金统领 (A) | 7,000 分 |
| **5** | `"S"` | 璀璨钻石 | 璀璨钻石 (S) | 9,000 分 |
| **6** | `"SS"` | 超凡大师 | 超凡大师 (SS) | 11,000 分 |
| **7** | `"SSS"` | 最强王者 | 最强王者 (SSS) | 13,000 分 |

* **底层与数据库**：`ladder_stats.rank_level` 存 TINYINT（0~7），配置与网络中用纯字符 `["-", "D", "C", "B", "A", "S", "SS", "SSS"]`，占用极小字节且建有 B-Tree 索引；
* **C++ 枚举注册**：在 `RoomManager` 中声明 `enum LadderRankLevel` 并用 `Q_ENUM` 暴露给 QML；
* **前端展示**：下拉框保留原始 `options`（保证配置与入库不破坏兼容性），通过 `displayText` 显示组合称号（`青铜守护 (D)`）。

---

## 四、 存储架构分工：冷热分离设计

在对战平台中，**数据库与 `.dat` 文件绝非二选一，而是冷热分离的黄金搭档**：

```
┌────────────────────────────────────────────────────────────────────────┐
│                          对战数据存储分层架构                          │
└────────────────────────────────────────────────────────────────────────┘
  [热/温数据层] MySQL 8.0 (InnoDB)
  ├─ ladder_stats : 玩家当前天梯分、胜率、段位、逃跑、MVP数 (匹配寻敌/排行榜直接读取)
  ├─ matches      : 比赛主流水表 (match_id, 模式, 胜利方, 时长, 时间戳)
  └─ match_results: 10名玩家单局得分变动、KDA、补刀、英雄、是否MVP
  
  [冷数据归档层] 本地/云端二进制存储 (*.dat)
  └─ data/player_actions/<player>/match_<time>_<id>.dat
     采用 Zlib-9 压缩的全量毫秒级动作流 (包含移动、施法、物品栏瞬移、视野点击)，
     单场仅 100~300 KB，专供 AI 反作弊审计、APM 复盘、Three.js 3D 轨迹还原。
```

---

## 五、 匹配寻敌与两队均分平衡机制

每当玩家在客户端点击“天梯匹配”时，`MatchManager` 执行以下精密闭环：
1. **积分实时获取**：调用 `DbManager::instance().ladderScore(userName)` 读取当前最新分数，注入排队票据 `Ticket`；
2. **动态搜索半径扩张（Dynamic Radius Expansion）**：
   * 初始搜索半径为 $\pm 50$ 分；
   * 每等待 15 秒，半径自动增加 $50$ 分；
   * 最大搜索半径上限封顶为 $\pm 400$ 分，确保高分段即使排队较长也不会永远卡死；
3. **蛇形配平算法（Snake Team Balancing）**：
   撮合出 10 名玩家后，按天梯积分从高到低排序 $[P_1, P_2, \dots, P_{10}]$，采用蛇形配对模式：
   * **近卫方（Team 1）**：$P_1, P_4, P_5, P_8, P_9$
   * **天灾方（Team 2）**：$P_2, P_3, P_6, P_7, P_{10}$  
   该算法在数学上证明了两队平均分差最小，彻底避免了“强强联手”导致的虐菜对局。

---

## 六、 赛后战绩提取、自动结算与客户端通知呈现机制

在魔兽争霸 III 引擎中，DotA 6.83d 通过原生 `GameCache (0x6B SyncStoredInteger)` 实行**三层战绩同步机制**，服务端 `War3Bot` 对全量事件进行拦截与状态机汇聚：

1. **三层 `0x6B` 数据采集管道**：
   * **开局握手与选人同步**：出兵零点（`Data:GameStart=1`）时初始化赛前 10 个战斗槽位快照（锁定 `slot`、`color`、`pid`、`userName`、`clientId`），防止玩家中途秒退被移除导致结算漏算；同时捕获选人 `Key "9"`（英雄 FourCC ID）及模式信息 `Data:Mode*`。
   * **局内周期性与实时事件广播**：
     * **周期补刀快照（每 210 游戏秒 / 约 262.5 现实秒）**：由地图定时器 `SWO` 周期广播 `Data:CSK<colorId>`（正补）、`Data:CSD<colorId>`（反补）、`Data:NK<colorId>`（野怪数）；
     * **实时战斗事件**：`Data:Hero<victim>=<killer>`、`Data:Assist<assist>=<victim>`（采用 1500ms 去重窗口防 N 端重复累加）、`Data:Level<lvl>=<colorId>`（记录真实英雄等级）、`Data:Tower*`/`Data:Rax*`；
     * **强退瞬间快照**：玩家离线瞬间触发 `Data:CK<a>D<b>N<c>=<colorId>` 与 `<colorId>:8_0..8_5` 装备留档。
   * **终局 `OJ2` 权威汇总**：当世界之树或冰封王座倒塌时，地图广播终局全员权威键值 `<colorId>:1..7`（K/D/A、补刀、金钱、打野）、`<colorId>:8_0..8_5`（六格装备）、`Global:m` / `Global:s`（精确比赛时长）以及胜负信号 `Global:Winner = 1 或 2`。
2. **JASS 颜色编号与战斗槽位映射修正**：
   * DotA 6.83d 中，近卫方 5 个玩家对应的 JASS `GetPlayerId` 为 **`1..5`**（`0` 为近卫建筑/小兵 AI），天灾方 5 个玩家为 **`7..11`**（`6` 为天灾 AI），对应物理槽位 `m_gameSlots[0..9].color`。
   * `Client::updateDotaLiveSyncData` 与 `Client::settleMatchResult` 统一以 **真实颜色编号 (`1..5, 7..11`)** 作为战绩表主键索引（并对中途退出者从开局快照找回并标记 `isAbandon = true`），彻底避免槽位数组下标与颜色编号错位。
3. **闭环结算与右下角托盘消息通知展示**：
   * `Client` 收到 `Global:Winner` 信号后，优先采用 `Global:m/s` 计算比赛时长，调用 `LadderScoreEngine::calculate` 计算段位分变动、综合评分与 MVP/SVP；
   * 调用 `DbManager::instance().applyMatchSettlement` 在单数据库事务中写入 `matches`、`match_results`（含真实 `hero_level`）与 `ladder_stats`，并签名上报 `POST /api/ladder/settle`；
   * 构建 `SCMatchResultPacket (0x31)` 广播给房间内各 `War3Launcher` 客户端。
   * **客户端右下角消息通知展现**：`War3Launcher` 在全局通知单例 `FriendNotifyComponent` 中监听 `RoomManager.matchResultReceived`，无论用户当前停留在任何标签页或已最小化到系统托盘，都会立即触发系统托盘图标红闪提醒，并在桌面右下角工作区（`trayNotifyHost`，与添加好友通知共用同一置顶消息面板）弹出天梯结算卡片：
     * **摘要视图**：展示胜负图标、积分变动胶囊（`+28` / `-20` / `MVP` / `SVP` / `逃跑惩罚`）、新段位称号、个人 K/D/A、正反补与对局时长；
     * **可展开详情（“战报详情”/“收起详情”）**：内联动态扩展窗口宽度与高度，直接渲染近卫/天灾 10 人紧凑计分板；
     * **“知道了” / “稍后”机制**：点“知道了”确认并消费该条通知；点“稍后”收起面板并将未确认通知保留在闪烁托盘中，悬停或点击托盘图标即可再次呼出。

---

## 七、 War3Angular Web API 与全方位安全性防线

游戏结算接口是平台特权写接口，若未做强防护，攻击者只需发送仿冒 HTTP 请求即可任意刷分。为此 `War3Angular` 构筑了金融级的多层安全防线：

### 1. 服务间特权数字签名（HMAC-SHA256）
* War3Bot 与 War3Angular 预共享强私钥 `BOT_SECRET_KEY`；
* 请求附带三个特权安全头：
  * `X-Bot-Timestamp`：请求发起的时间戳（秒）；
  * `X-Bot-Nonce`：32 位全局唯一随机字符串；
  * `X-Bot-Signature`：基于 `HMAC_SHA256(timestamp + "." + nonce + "." + matchId + "." + bodyRaw, BOT_KEY)` 计算的数字签名；
* 服务端使用 `crypto.timingSafeEqual` 校验签名，防时序旁路攻击。

### 2. 防重放攻击防御体系（Anti-Replay Attack）
* **时钟漂移检查**：`Math.abs(now - reqTimestamp) <= 60` 秒，截获的历史请求在 1 分钟后强制失效；
* **Nonce 内存去重黑名单**：记录过去 5 分钟内所有消耗过的 Nonce，同一请求被多次重发时直接拒绝并告警。

### 3. 游戏逻辑守恒与防伪审计（Logic Integrity Audit）
* **有效对局时长门槛**：时长 $< 180$ 秒（3分钟）直接视为无效局，拒绝发放天梯积分（杜绝刷分互退）；
* **人头守恒定律**：近卫总击杀数与天灾总死亡数必须大致守恒，若发生巨大偏差（如外挂注入修改击杀），直接判定数据篡改并驳回；
* **数值越界防御**：严格校验负数、单场超大异常补刀/击杀，防止 SQL 注入与脏数据污染。

### 4. 幂等性与事务原子性（Idempotency & ACID）
* 结算前先以 `matchId` 为主键查验，已入库对局直接返回 `Idempotent OK`，彻底杜绝弱网环境下重传导致玩家多次加分；
* 使用 MySQL 单一事务同时完成 `matches`、`match_results` 插入和 `ladder_stats` 更新，失败则全量回滚。

### 5. 查询接口频率控制（Rate Limiting）
* 对公网开放的只读接口（`/api/ladder/profile`、`/api/ladder/leaderboard`）实施滑动窗口频控（每 IP 每分钟 60~120 次），防止爬虫拖库与连接池耗尽。

---

## 八、 总结与落地点

1. **War3Bot**：实现了三层 `0x6B` 战绩提取（周期性 `CSK/CSD/NK`、实时 `Hero/Assist/Level`、终局 `OJ2` 全量汇总）、开局名单快照保底强退扣分、动态 Elo 评级算法、本地数据库落库以及 `S_C_MATCH_RESULT (0x31)` 广播；
2. **War3Launcher**：实现了 `LadderRankLevel` 枚举及中文称号并存体系，并将赛后积分结算面板统一接入 `FriendNotifyComponent` + `trayNotifyHost` 右下角托盘消息通知中心，支持未确认红闪角标、内联展开十人战报与“稍后”保留；
3. **War3Angular**：完成了 Express 后端安全网关、特权验签中间件、防刷防伪审计、MySQL 事务落库接口与前端 `LadderService` 数据访问层。

整套系统形成了从**游戏内锁步同步** $\to$ **主机战绩提取** $\to$ **天梯动态结算** $\to$ **数据库原子落库** $\to$ **Web API 安全鉴权与全端呈现**的完整闭环。

