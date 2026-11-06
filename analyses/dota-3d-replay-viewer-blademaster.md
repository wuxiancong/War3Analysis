# DotA 6.83 网页 3D 录像监视（剑圣先行）设计笔记

## 目标

在 War3Bot 数据统计页「追随最新 ✓ / 实时追随」旁增加 **观看录像**，跳转到 War3Angular 的 Three.js 3D 页面，用与服务器一致的同步动作流还原场景，支持：

- 实时追随（直播）
- 时间轴回退（录像）
- 用于对照外挂 / 异常操作轨迹

首期只验证 **剑圣（Juggernaut / 兽族 Blademaster 模型）** 网格与贴图。

## 入口

| 位置 | 行为 |
|---|---|
| `War3Bot/main.qml` 统计详情顶栏 | `CusButton`「观看录像」→ `Qt.openUrlExternally(statsPage.buildReplayViewerUrl())` |
| URL | `http://127.0.0.1:4200/replay-3d?matchId=&player=&hero=&live=&t=` |
| 可配置 | `statsPage.replayViewerBaseUrl`（默认本地 Angular dev） |

历史对局与直播对局只要选中 `md` 即显示按钮；直播时仍保留「追随最新」按钮。

## 资源

- 原始 MDX：`HeroBladeMaster.mdx`（来自 `war3.mpq`）
- **浏览器加载用**：`HeroBladeMaster.mdxbin`（同内容；避免 Vite 把 `.mdx` 当 JS/MDX 模块解析）
- 贴图：`Textures/*.blp`（mdx-m3-viewer BLP 处理器直读）+ `ReplaceableTextures/TeamColor|TeamGlow/*.png` 占位
- 备用静态 JSON：`HeroBladeMaster.json`（早期 Three.js 网格预览，已不作为主路径）

## 前端实现（War3Angular）

| 文件 | 职责 |
|---|---|
| `src/app/pages/replay-3d.component.ts` | 视口、Stand/Walk/Attack 快捷键、序列列表、查询参数 |
| `src/app/replay3d/wc3-mdx-viewer.ts` | 封装 `mdx-m3-viewer` viewer 子树；路径求解；相机轨道 |
| `src/app/replay3d/mdx-json.loader.ts` | 旧 Three.js 静态网格 loader（保留备用） |
| `src/app/app.routes.ts` | `/replay-3d` |

### 运行时要点

1. **只动态 import** `mdx-m3-viewer/dist/cjs/viewer/index.js`（不要 import 包根，否则会拖进 fengari/jass2 → Node `os`）
2. `angular.json` `define.process = globalThis.process` + `index.html` 早期 shim
3. 模型 URL 使用 `.mdxbin`
4. WC3 坐标系 Z-up；镜头 `moveToAndFace(..., up=[0,0,1])`

## 同步数据（下一步）

Bot 侧已有动作归档与直播流。网页端建议：

1. HTTP 拉取历史 timeline JSON
2. WebSocket 订阅 live action
3. 用 `instance.setSequence` + `setLocation`/`face` 驱动移动与朝向

## 验收

1. `cd War3Angular && npm start`
2. 打开 `http://127.0.0.1:4200/replay-3d`
3. 可见带 BLP 贴图的剑圣，默认 Stand；点 Walk/Attack 切换骨骼动画
4. War3Bot「观看录像」打开带 query 的同一 URL（需重编 Bot）

## DotA 地形与建筑（已实现 · 小地图方案）

完整 `War3MapViewer` 需要整包 `war3.mpq` TerrainArt + 可解析的 w3x（DotA 图常加密），首期采用：

| 资源 | 路径 |
|---|---|
| 地图配置 | `War3Angular/public/assets/maps/dota683/buildings.json`（38 座） |
| 小地图 | `public/assets/dota/dota683_minimap.png` |
| 建筑标点 | `bakeDotaMapTexture()` 画到 PNG 上（近卫绿 / 天灾粉圆点），**不再用 3D 圆柱/方块** |
| 「地图」模式 | HTML `<img>` 显示烘焙小地图（可靠可见） |
| 「英雄」模式 | WebGL 剑圣 MDX 近景；canvas 尺寸须在 `ModelViewer` 创建前设定（事后改 `canvas.width` 会清空 GL 贴图） |
| 剑圣出生 | `RADIANT_SPAWN = (-6904, -6831)` |

地图 bounds 与 Bot `mmBox` 一致。已知取舍：无真实高度图 / 原生建筑 MDX。后续可挂载 `war3.mpq` 启用 `War3MapViewer`。

## 后续

1. 动作包 WebSocket
2. 其他英雄：复制 MDX→`.mdxbin` + Textures
3. w3e 真实高度图 / 原生建筑模型
