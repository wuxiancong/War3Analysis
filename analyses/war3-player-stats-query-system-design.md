# War3 专业级战绩查询系统设计方案

> **结论置顶**
> 1. **现状缺口**：`StatsComponent.qml` 长期为 Mock 数据；房间「查看战绩」只切 Tab 不传玩家名；`/api/ladder/*` 查询面几乎裸奔，而 PHP `player_stats.php` / `players_stats.php` 已有签名但未覆盖 Node 天梯 API、也未绑定登录会话。
> 2. **目标形态**：以 **「登录会话 + 客户端身份 + 短时签名 + 限流 + 分档脱敏」** 五层防护统一 Web（War3Angular）与 Launcher（原生 HTTP，无 CORS）的战绩读路径；写路径继续走 Bot HMAC（已有）。
> 3. **本轮已落地（Launcher）**：`RoomManager.viewPlayerStats` → 签名请求 `player_stats.php` + `user_status.php` → `StatsComponent` 数据驱动渲染；房间右键 / 战绩行单击 / 好友列表均可跳转。
> 4. **进阶必做**：会话票（JWT/Session）、查询权限（认证玩家才能查他人完整档）、CORS 白名单、排行榜鉴权、近期对局补齐个人 KDA/积分变动、反爬（nonce + 设备指纹）。

| 项 | 内容 |
| :--- | :--- |
| **分析模型** | Composer（Cursor Agent） |
| **分析目的** | 综合 War3Angular 战绩页与 War3Launcher 房间/Stats 组件，设计可落地的专业战绩查询与保密体系，并完成 Launcher 侧跳转与数据绑定 |
| **命名方式** | `war3-player-stats-query-system-design` |
| **分析时间** | 2026-11-17 |

思维导图：[`war3-player-stats-query-system-design-mindmap.md`](./war3-player-stats-query-system-design-mindmap.md)

关联文档：
- [`dota1-ladder-system-and-multi-service-architecture.md`](./dota1-ladder-system-and-multi-service-architecture.md)
- [`dota1-anti-cheat-system-design.md`](./dota1-anti-cheat-system-design.md)

---

## 一、现状对照（Angular vs Launcher）

| 能力 | War3Angular | War3Launcher（改前 → 改后） |
| :--- | :--- | :--- |
| 总览卡片（分/胜率/KDA/GPM/MVP/连胜） | `stats.component.ts` Mock + 部分 `user_status` | Mock → **绑定 `player_stats` ladder** |
| 认证 / 素质 / 举报 | `user_status.php`（手机绑、时长、作弊数） | 无 → **合并 `user_status`** |
| 英雄 / 模式 / 近场 | UI 有，数据 Mock | 同左 → **heroes / modes / recent_matches** |
| 房间内窥视 | Web 房未做 | 槽位摘要 `players_stats.php` 已有；详情跳转断裂 → **已接通** |
| 查询鉴权 | PHP 有 MD5 签名；Node `/ladder/*` 仅 rateLimit | 房间批量签名已有；详情无 → **详情签名已接** |
| CORS | `user_status` 为 `*`；战绩 PHP 为 `none` | 原生客户端 **不受 CORS 限制**（正确） |

### 认证玩家判定（与房间 UI 文案对齐）

房间 `authConditionsDesc` 与 `user_status.php` 一致口径：

1. **手机号已绑定**（`is_phone_verified = 1`）
2. **无作弊违规记录**（`cheat_records_count = 0`，进阶可再要求信誉分阈值）
3. **游戏在线时长 ≥ 168 小时**（`total_ingame_time ≥ 10080` 分钟）

```
is_fully_verified = is_phone_verified && total_ingame_time >= 10080
（进阶建议追加：cheat_records_count == 0 && trust_score >= 阈值）
```

展示档位建议：

| 档位 | 条件 | UI |
| :--- | :--- | :--- |
| 已认证 | `is_fully_verified` | 绿标「已认证」 |
| 部分认证 | 仅手机已绑 | 黄标「部分认证」 |
| 未认证 | 其他 | 红/灰「未认证」 |

---

## 二、产品信息架构（战绩页）

对齐 Angular `app-stats` 与 Launcher `StatsComponent` 双栏布局：

```
┌──────────────────────── 玩家数据 - {name} · {认证} ────────────────────────┐
│ 左栏                                      │ 右栏                          │
│ ① 基础统计 16 格                          │ ⑤ 模式分布饼图                │
│    排名/积分/胜率/KDA/GPM/MVP/段位/逃跑   │ ⑥ 赛季排行（Solo/Team）       │
│    场次/连胜/时长/素质/违规/举报/认证     │ ⑦ 英雄纪录卡                  │
│ ② 近 15 场胜率趋势                        │                              │
│ ③ 最佳英雄 Top3                           │                              │
│ ④ 最近 5 场明细（英雄/模式/时长/KDA/Δ分） │                              │
└───────────────────────────────────────────┴──────────────────────────────┘
```

### 字段字典（对外 JSON）

**公开摘要（房间槽位 / 未认证窥视）** — `players_stats.php`

| 字段 | 含义 |
| :--- | :--- |
| `score` | 天梯积分 |
| `rank_name` | 段位码 D~SSS |
| `kda` | 生涯 (K+A)/D |
| `winRate` | 胜率字符串 |
| `escapeRate` | 逃跑率字符串 |

**完整档案（需登录 + 签名；查他人另需查询者已认证）** — `player_stats.php`

| 块 | 关键字段 |
| :--- | :--- |
| `ladder` | score, rank_level, rank_name, wins/losses/escapes, win_rate, kda, gpm, mvps, streaks, totals |
| `heroes` | name, games, wins, winRate, kda, max_kills |
| `modes` | game_mode → games/wins/winRate |
| `recent_matches` | mode, duration, hero, KDA, score_point, is_winner |
| `user_status` | is_phone_verified, is_fully_verified, cheat/report counts, total_ingame_time |

**敏感字段（默认不对第三方返回）**：邮箱、手机号、设备指纹、IP、反作弊证据链、冻结原因详情。

---

## 三、安全架构（保密 + 反爬 + 允许 Launcher）

### 3.1 威胁模型

| 威胁 | 手段 | 对策 |
| :--- | :--- | :--- |
| 匿名爬取全服战绩 | 脚本刷 `?user=` | 强制登录会话 + 签名 + 限流 + 验证码升级 |
| 重放抓包 URL | 复用 `t`/`sign` | 60s 过期 + nonce 一次有效 |
| 浏览器跨站偷读 | 恶意站点 XHR | **CORS 白名单**；Cookie `SameSite=Lax`；不靠 `*` |
| 伪造 Launcher | 伪造 UA | UA 仅弱信号；真正靠 **客户端 AppKey + 会话票** |
| 未认证批量窥探 | 枚举用户名 | 查他人完整档要求查询者 `is_fully_verified`；摘要接口房间上下文限 12 人 |
| 密钥硬编码泄露 | 逆向 exe | 短期：混淆拆分（现状）；中期：登录后下发短期 client token |

### 3.2 客户端身份分层

```
                    ┌─────────────────────────────┐
                    │     API Gateway / Nginx      │
                    │  TLS · WAF · IP 限流         │
                    └─────────────┬───────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   War3Launcher              War3Angular              War3Bot
   原生 QNetwork             浏览器 fetch             主机上报
   无 CORS 问题              需 CORS 白名单           HMAC 特权
          │                       │                       │
          └───────────┬───────────┘                       │
                      ▼                                   ▼
              读接口：会话票 + 签名                  写接口：Bot HMAC
              player_stats / ladder/*               settle / ac/verdict
```

### 3.3 推荐鉴权协议（进阶统一方案）

**A. 登录会话票（所有读接口）**

1. Launcher / Web 登录成功后，由 bnetd / API 签发 `session_token`（JWT，含 `sub=userName`、`client=launcher|web`、`exp`、`verified`）。
2. 请求头：`Authorization: Bearer <token>`。
3. 未登录：仅允许查询**自己**的公开摘要，或直接 401。

**B. 请求签名（防伪造参数）**

与现有 PHP 对齐并升级：

```
sign = HMAC-SHA256( userName + "." + t + "." + nonce + "." + session_id , APP_SECRET )
```

- 现网兼容期可继续接受 `md5(userName + t + APP_SECRET)`（Launcher 已实现）。
- 生产最终淘汰裸 MD5，改为 HMAC + nonce 表防重放。

**C. CORS（只约束浏览器，不挡 Launcher）**

| Origin | 策略 |
| :--- | :--- |
| `https://你的官网域` | Allow-Credentials + 明确 Allow-Origin |
| `http://localhost:42xx`（开发 Angular） | 仅 DEV 环境放行 |
| `null` / 任意第三方 | **拒绝** |
| War3Launcher QNetwork | **无 Origin 头** → 走「无 CORS 预检」分支，靠 Bearer + 签名 |

关键点：**切勿**对战绩接口设置 `Access-Control-Allow-Origin: *`（当前 `user_status.php` 需改正）。

**D. 查询权限矩阵**

| 查询者状态 | 查自己 | 房间内他人摘要 | 他人完整档 | 排行榜 |
| :--- | :---: | :---: | :---: | :---: |
| 未登录 | ❌ | ❌ | ❌ | 脱敏 Top10 或 ❌ |
| 已登录未认证 | ✅ 完整 | ✅ 摘要 | ❌ 或仅摘要 | ✅ 有限 |
| 已认证 | ✅ | ✅ | ✅（限流） | ✅ |
| Bot / 管理后台 | — | — | 特权 HMAC | ✅ |

**E. 反爬加固**

- IP + 用户双维 rate limit（已有 `rateLimit` 可复用）。
- 连续 404/403 → 临时冻结查询额度。
- 可选：首次跨用户查询触发滑块（复用注册拼图）。
- 响应不返回全表扫描字段；排行榜强制分页。

### 3.4 现有密钥与 UA

- Launcher `GlobalConfig::appSecret()` = `CC_War3_@#_Platform_2026_SecureKey`（与 PHP `APP_SECRET_KEY` 一致）。
- UA：`War3Launcher-Client/1.0`（PHP 黑名单不含此前缀）。
- **注意**：密钥在客户端可被逆向；故会话票 + 服务端权限才是真正边界，AppSecret 只是「官方客户端证明」的弱因子。

---

## 四、服务端进阶改造清单

### 4.1 API 统一

| 接口 | 现状 | 目标 |
| :--- | :--- | :--- |
| `GET /api/player_stats.php` | MD5 签名，完整档 | 加 Bearer；查他人校验认证；补 recent 个人字段 |
| `GET /api/players_stats.php` | 房间批量摘要 | 要求会话；可选绑定 `roomId` 校验同房 |
| `GET /api/user_status.php` | CORS `*`，弱防 | 改白名单；并入档案或同样签名 |
| `GET /api/ladder/profile` | 仅 rateLimit | 与 player_stats 合并或同样鉴权 |
| `GET /api/ladder/matches` | 裸奔 | Bearer + 限流；返回英雄/KDA/Δ分 |
| `GET /api/ladder/leaderboard` | 裸奔 | Bearer；分页；隐藏未认证隐私 |
| `POST /api/ladder/settle` | Bot HMAC ✅ | 保持；与读路径隔离 |

### 4.2 数据层补齐

1. `match_results` 保证每局写入 hero / KDA / score_point / is_winner（结算已有，PHP recent 查询需改用该表而非仅 `matches`）。
2. `player_hero_stats` / `player_mode_stats` 在 settle 事务内 upsert（与 ladder.service 对齐）。
3. 全球排名：`SELECT COUNT(*)+1 FROM ladder_stats WHERE score > ?` 或定时物化 `rank_no`。
4. 信誉分 / 认证状态进入 `users` 或独立 `player_trust`。

### 4.3 War3Angular 前端

1. `stats.component.ts` 去掉 Mock，改为调用鉴权后的 `player_stats` / `ladder/matches` / `leaderboard`。
2. 路由支持 `/stats/:userName`，与 Launcher 深链语义一致。
3. HttpInterceptor 注入 Bearer；错误态区分 401/403/429。

---

## 五、Launcher 侧已实现与后续

### 5.1 本轮已实现

| 模块 | 改动 |
| :--- | :--- |
| `RoomManager` | `viewPlayerStats` / `fetchDetailedPlayerStats`；签名拉 `player_stats.php`；合并 `user_status.php`；属性 `detailedPlayerStats` / `statsLoading` / `statsError` / `statsQueryUser` |
| `StatsComponent.qml` | 数据驱动；标题显示认证；可见时缓存 60s 内不重复打 |
| `RoomComponent.qml` | 右键「查看战绩」；槽位战绩行单击跳转 |
| `MatchComponent.qml` / `main.qml` | 好友战绩与 `viewPlayerStatsRequested` → Tab0 |

### 5.1.2 本地联调适配（War3Angular + War3Bot，2026-11-17）

| 项 | 说明 |
| :--- | :--- |
| Angular `.env` | `APP_MODE=local`，`DATABASE_URL=127.0.0.1`，`PUBLIC_API_BASE=http://127.0.0.1:4000/api` |
| `runtime-config.ts` | 统一 local/test/production；`isEligibleLadderMode` 仅放行 5v5 / SOLO |
| 结算门禁 | **非正规模式永不落库**；debug/local 允许人数不足但仍须双方各≥1 |
| War3Bot | `ladder.api_base`→本机 Angular；上报真实 `mode` + `debugMode`/`localMode` |
| 注意 | `users.db`（bnetd 账号）≠ 天梯 MySQL；`lib/sqlite3/x86` 只是 SQLite 源码 |

### 5.1.1 UI 迭代（致敬 [iCCup Gaming Profile](https://iccup.com/dota/gamingprofile/HanzoSolomon)）

| 项 | 说明 |
| :--- | :--- |
| 身份头图 | 段位徽章 + 玩家名 + 认证徽标 + 积分/胜率一行摘要 |
| KDA 悬停 | 主题色气泡（非纯白）+ 爱因斯坦吐舌图 `images/einstein_tongue.jpg` + 加权公式 |
| 公式 | `K = (击杀×2 + 助攻) / (死亡×2)`（与 iCCup 一致）；文案 `qsTr("KDA — 衡量你技术水平的参数")` |
| 操作 | 「查看自己」「重试」；假排行榜无数据时隐藏；趋势空态 |

### 5.2 建议后续迭代

1. Node 中间件 `verifyClientSession` 统一 PHP/Express。
2. 排行榜真实数据 + 当前玩家插队显示。
3. 近期对局改走 `/api/ladder/matches` 并渲染英雄头像（`image://war3/heroIcons/`）。
4. 房间摘要失败时 UI 占位「—」而非空白，避免误读。
5. 配置项：战绩 API 基址与 Bot API 是否同域的文档化（现均用 `bnetApiAddress`）。

---

## 六、房间跳转时序

```
玩家右键槽位「查看战绩」 / 单击战绩行 / 好友「查看战绩」
        │
        ▼
RoomManager.viewPlayerStats(name)
        ├─ statsQueryUser = name
        ├─ emit viewPlayerStatsRequested ──► mainWindow.switchToTab(0)
        └─ fetchDetailedPlayerStats
                ├─ GET .../player_stats.php?userName&t&sign   (UA=War3Launcher-Client/1.0)
                └─ GET .../user_status.php?userName
                        │
                        ▼
                detailedPlayerStatsChanged
                        │
                        ▼
                StatsComponent.applyDetailedStats(...)
```

---

## 七、验收清单

- [ ] 登录 Launcher 后打开战绩 Tab，显示**自己的**真实积分/KDA/认证态（非 Mock）。
- [ ] 房间内右键他人 → 战绩 Tab 标题为对方名字且数据对应。
- [ ] 单击槽位战绩行可跳转。
- [ ] 篡改 `sign` 或过期 `t` → 403，UI 显示错误文案。
- [ ] 浏览器控制台从第三方 Origin 请求战绩 → CORS 失败（进阶改完后）。
- [ ] 未认证账号查他人完整档 → 403（进阶权限矩阵落地后）。
- [ ] Bot 结算 HMAC 路径不受读接口改动影响。

---

## 八、风险与合规

- 战绩属用户画像数据：需隐私政策披露「对局数据用于排行与房间展示」。
- 完整档仅对认证用户开放，降低人肉/开盒风险。
- 日志禁止落手机号明文；API 错误勿回显 SQL。
