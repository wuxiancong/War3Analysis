# Warcraft III 原生控制台 UI 的取数路径与布局数值（用于网页对战 HUD 还原）

日期：2026-11-10
样本：`C:\Program Files (x86)\iCCup Warcraft III\{War3Patch,War3xlocal,War3x,war3}.mpq`、`D:\Maps\DotA v6.83d.w3x`
产物：`War3Angular/public/assets/wc3/native-ui/`（贴图 + `manifest.json`）、`War3Analysis/artifacts/wc3-native-ui/`（`war3skins.txt`、27 个 UI `.fdf`、地图 `war3mapSkin.txt`）
脚本：`War3Angular/scripts/extract-native-ui.cjs`
思维导图：[warcraft-iii-native-console-ui-layout-for-web-mindmap.md](warcraft-iii-native-console-ui-layout-for-web-mindmap.md)

> 范围说明：本次**没有反汇编 `Game.dll`**。布局数值有三个来源，下文每一项都标了是哪一个：
> **[FDF]** MPQ 内的帧定义文件，数值是引擎直接读取的原文；
> **[贴图]** 控制台贴图的镂空区域，用脚本量出来的像素；
> **[截图]** 按用户提供的 2000×1094 原版截图比对出来的估计值。
> 命令卡 / 物品栏 / 小地图 / 肖像这几个帧的矩形是 `Game.dll` 里硬编码的，这里用 [贴图] 镂空代替，没有从二进制取证。

## 1. 资源是怎么被引擎找到的

`Game.dll` 不直接写死贴图路径，而是按「皮肤键」去查 `UI\war3skins.txt`：先取 `[Default]` 段，再用玩家种族段（`[Human]` / `[Orc]` / `[NightElf]` / `[Undead]`）覆盖，最后被地图里的 `war3mapSkin.txt [CustomSkin]` 覆盖。`.fdf` 里出现的 `File "ConsoleTexture01"`、`DecorateFileNames` 就是在引用这些键。

对 DotA 有用的结论：

| 事实 | 证据 |
|---|---|
| 近卫玩家是暗夜精灵皮肤、天灾玩家是不死族皮肤 | 截图为藤蔓控制台；DotA 两方种族分别为 NightElf / Undead |
| 种族段**只**覆盖：四块控制台瓦片、物品栏盖板、空物品格填充、时间指示器模型、鼠标指针、顶部菜单按钮精灵图、Esc 菜单/任务对话框边框 | `war3skins.txt [NightElf]` |
| 小地图五个按钮、命令按钮高亮、经验条、提示框边框、信息面板图标，四个种族**共用人族那套** | `[Default]` 段的 `MiniMap*Button*`、`CommandButtonActiveHighlight`、`SimpleXpBar*`、`ToolTip*`、`InfoPanelIcon*` 全指向 `…\Human\…` |
| DotA 把木材图标换成时钟、人口图标换成空白 | 地图 `war3mapSkin.txt [CustomSkin]`：`LumberIcon=UI\Widgets\BattleNet\bnet-tournament-clock`、`SupplyIcon=ReplaceableTextures\WorldEditUI\LocationBrush00.blp` |
| 资源栏第二、三格显示的是「分」「秒」，第四格是版本号 | 同文件 `[FrameDef]`：`COLON_LUMBER=分：`、`COLON_FOOD=秒：`、`UPKEEP_NONE=v6.83d 中文版` |
| 左上第一个按钮在 DotA 里叫「地图信息 (F9)」 | 同文件 `KEY_QUESTS=地图信息 (|Cfffed312F9|R)` |

MPQ 读取优先级与游戏一致：`War3Patch.mpq > War3xlocal.mpq > War3x.mpq > war3.mpq`。

## 2. 坐标系

UI 坐标为 **0.8 × 0.6**（宽 × 高），原点左下。控制台贴图的换算是 **1 单位 = 2000 贴图像素**（0.256 ↔ 512px），所以整屏宽 0.8 ↔ 1600px。宽屏下 UI 横向拉伸铺满（截图 2000×1094 即如此），网页端同样处理：横向用宽度百分比，纵向用高度百分比。

## 3. 控制台贴图怎么拼 —— `UI\FrameDef\UI\ConsoleUI.fdf` [FDF]

四块瓦片（512、512、512、64 宽，高 512）不是整张贴上去的，而是切成 9 块：

| 块 | 贴图 | 宽 × 高 | TexCoord (u0,u1,v0,v1) | 锚点 |
|---|---|---|---|---|
| 顶 1 | Tile01 | 0.256 × 0.032 | 0, 1, 0, 0.125 | TOPLEFT 0,0 |
| 顶 2 左 | Tile02 | 0.087 × 0.032 | 0, 0.3398, 0, 0.125 | TOPLEFT 0.256,0 |
| 顶 2 右 | Tile02 | 0.053 × 0.032 | 0.7930, 1, 0, 0.125 | TOPRIGHT −0.288,0 |
| 顶 3 | Tile03 | 0.256 × 0.032 | 0, 1, 0, 0.125 | TOPRIGHT −0.032,0 |
| 顶 4 | Tile04 | 0.032 × 0.032 | 0, 1, 0, 0.125 | TOPRIGHT 0,0 |
| 底 1 | Tile01 | 0.256 × 0.176 | 0, 1, 0.3125, 1 | BOTTOMLEFT 0,0 |
| 底 2 | Tile02 | 0.256 × 0.150 | 0, 1, 0.4141, 1 | BOTTOMLEFT 0.256,0 |
| 底 3 | Tile03 | 0.256 × 0.176 | 0, 1, 0.3125, 1 | BOTTOMRIGHT −0.032,0 |
| 底 4 | Tile04 | 0.032 × 0.176 | 0, 1, 0.3125, 1 | BOTTOMRIGHT 0,0 |

要点：

- 顶栏只有 **0.032 高（屏高的 5.33%）**，取贴图最上面 64 行。
- 顶栏中间 x = 0.343 ~ 0.459 **故意留空**，那里画的是时间指示器模型（`TimeOfDayIndicator`），不是贴图。Tile02 中段那个带叶子的圆环只是给模型垫底的美术。
- 底部控制台高 **0.176（屏高的 29.33%）**；中间那块（肖像 + 信息面板）矮一截，只有 0.15。
- 全部 `AlphaMode "ALPHAKEY"`，是 alpha 测试而不是半透明混合，所以导出时做了二值化。

脚本按这张表拼出 `topbar.png`（1600×64）和 `console.png`（1600×352）。

## 4. 顶栏

### 四个菜单按钮 —— `UpperButtonBar.fdf` [FDF]

- 按钮模板：宽 0.085，高 0.022，按下时文字偏移 (0.001, −0.001)。
- 第一个按钮相对 `UpperButtonBarFrame` 左上偏移 0.002，其余依次 `LEFT → RIGHT` 紧贴。即 x = 0.002 + i × 0.085。
- 四种状态共用一张精灵图 `UpperMenuButtonTexture`（256×256），u 都是 0 ~ 0.6640625：

| 状态 | v 范围 | 混合 |
|---|---|---|
| 常态 | 0 ~ 0.171875 | |
| 按下 | 0.25 ~ 0.421875 | |
| 禁用 | 0.5 ~ 0.671875 | |
| 高亮 | 0.75 ~ 0.921875 | `ADD` 叠加 |

- 文字 `MasterFont` 0.01，常态白色，高亮 (1.0, 0.83, 0.07)，热键部分用 `|Cfffed312…|R` 着色。

`UpperButtonBarFrame` 本身放在屏幕左上角这一点是 [截图] 确认的，FDF 里没写。

### 资源栏 —— `ResourceBar.fdf` [FDF]

`ResourceBarFrame` 宽 0.33828125、高 0.0218，贴屏幕右上（[截图]）。帧内：

| 元素 | 锚点 | 尺寸 |
|---|---|---|
| 金币图标 | TOPLEFT 0, −0.003125 | 0.01640625 见方 |
| 金币数值 | TOPRIGHT −0.26484375, −0.003125，右对齐 | 字体 0.01 |
| 木材图标 | TOPLEFT 0.0859375, −0.003125 | 同上 |
| 木材数值 | TOPRIGHT −0.178125 | |
| 人口图标 | TOPLEFT 0.17265625 | |
| 人口数值 | TOPRIGHT −0.09140625 | |
| 维护费文字 | TOPRIGHT −0.003125，宽 0.07578125，居中 | |

### 时间指示器

模型 `UI\Console\NightElf\NightElfUI-TimeIndicator.mdx` 内引用的贴图（脚本扫描 MDX 里的 `.blp` 字符串得到）：

- `ui\Console\NightElf\NightElfUITile-TimeIndicatorFrame.blp`（256×128 外框，圆环中心约在 (128, 40)，内径约 56px）
- `Textures\HumanUITile-TimeIndicator.blp`（256×128 的昼夜长条：两端是太阳，中间是月亮）
- 以及几张辉光贴图（`GenericGlowFaded`、`star3`、`GenericGlow2_32`、`MagicGlow`）

网页端**没有渲染这个模型**，而是「外框贴图 + 圆形窗口里横向滚动的昼夜长条」做的静态近似，辉光与星星闪烁没有还原。昼夜周期按 480 秒、开局清晨 6 点推算，这个周期**没有从 `war3map.j` 取证**。

### 多面板 —— `Multiboard.fdf` [FDF] + [截图]

最小化按钮 0.024 见方，标题底板在其左侧重叠 0.0057；边框 `BackdropEdgeFile "MultiboardBorder"`，角尺寸 0.0125，背景内缩 0.005。按钮在屏幕上的位置（右上、顶栏下方）是 [截图] 估的。

## 5. 底部控制台各帧 [贴图]

用脚本对 `console.png` 做透明连通域，得到镂空矩形（单位：贴图像素，原点为控制台带左上；暗夜精灵）：

| 帧 | x, y, w, h | 备注 |
|---|---|---|
| 小地图 | 20, 58, 276, 279 | 贴图里上面 58 行是不透明黑条，小地图画在贴图**上面** |
| 小地图按钮 ×4 | x≈310，y≈66 / 110 / 154 / 198，约 44×40 | 贴图上是四个黑方块 |
| 阵型按钮 | 约 309, 248, 46×46 | 圆形 |
| 肖像 | 435, 122, 144, 168 | 真透明，模型画在贴图**下面** |
| 生命文字 | 437, 298, 140, 22 | |
| 魔法文字 | 437, 325, 141, 20 | |
| 信息面板 | 609, 103, 395, 249 | 顶边被藤蔓压住，不规则 |
| 命令卡 4×3 | 列 x = 1233 / 1321 / 1408 / 1495，行 y = 86 / 173 / 260，格 79×79 | 换算为按钮 ≈0.039、间距 ≈0.0435 |
| 物品栏 2×3 | 列 x≈1032 / 1110，行 y≈126 / 204 / 282，约 66×66 | 格子有填充图，不是镂空，按 [截图] 与贴图目测 |

不死族控制台的镂空位置基本相同（肖像 434,130,144,159；信息面板 609,117,389,235），网页端两套皮肤共用暗夜精灵这组数值。

## 6. 信息面板 —— `SimpleInfoPanel.fdf` [FDF]

| 元素 | 数值 |
|---|---|
| 名称 `SimpleNameValue` | 锚 TOP 0,0；字体 `InfoPanelTextFont` 0.013 |
| 英雄等级条 `SimpleHeroLevelBar` | 名称下方 −0.0015；高 0.015625 |
| 职业文字 `SimpleClassValue` | 名称下方 −0.0055；字体 0.0085 |
| 图标模板 `InfoPanelIconTemplate` | 0.032 见方，TOPLEFT 0.004, −0.001 |
| 攻击 / 护甲行 | 行高 0.03125；标签在图标右侧 −0.003；数值在标签下方缩进 0.005 |
| 英雄三围 `SimpleInfoPanelIconHero` | 高 0.0625；图标 LEFT 0.004；三组「标签 / 数值」间隔 −0.004 |
| 标签 / 数值字体 | 0.0085；属性角标 0.009 |

面板自身在屏幕上的矩形、攻击行与护甲行的起始 y、三围列的 x 是 `Game.dll` 硬编码的；这里用 [截图] 里「护甲」图标的位置（贴图像素约 628, 188）反推，攻击行在其上方一个行高。

图标键：`InfoPanelIconDamage{Normal,Pierce,Siege,Magic,Chaos,Hero}`、`InfoPanelIconArmor{Small,Medium,Large,Fort,Hero,Divine,None}`、`InfoPanelIconHeroIcon{STR,AGI,INT}`。

## 7. 边框贴图的格式

`BackdropEdgeFile`（提示框、多面板、Esc 菜单的边框）是一张 8 个等宽方块横排的图：左、右、上、下、左上、右上、左下、右下，其中「上」「下」两块是旋转 90° 存的。脚本把它和背景贴图拼成 3×3 九宫格 PNG，前端用 `border-image` 使用。暗夜精灵 Esc 菜单的拼装结果上边是藤蔓、下边是石条，方向与原版一致；提示框和多面板的边框太细，方向是否正确**没有逐像素核对**。

## 8. 网页端对应关系与未还原项

实现在 `War3Angular/src/app/pages/play-3d.component.ts`（模板里 `.w3` 一段与同文件 `U()` / `B()` / `L`）。

已按上面数值还原：顶栏贴图与四个按钮（含三态）、资源栏四格（金钱 / 分 / 秒 / 版本）、时间指示器外框、多面板标题、底部控制台贴图、小地图与五个按钮、肖像、生命 / 魔法文字、信息面板（名称、等级条、攻击、护甲、三围、状态）、物品栏 6 格、命令卡 12 格（基础命令 / 学习技能子菜单 / 商店货架 / 选目标时只剩取消）、提示框、F9~F12 对话框。

未还原或只是近似：

| 项 | 现状 |
|---|---|
| 字体 | 原版 `Fonts\FRIZQT__.TTF` 及中文客户端字体没有导出，用系统字体代替，字形与字宽不同 |
| 时间指示器 | 静态近似，见 §4 |
| 3D 肖像 | 只有带 `*_Portrait` 模型且已解包的单位才有；其余退回头像图标或空白 |
| 冷却指示 | 原版是模型（DotA 还换成了 `Interface\CoolDown UI.mdx`），这里用 CSS 扇形 |
| 鼠标指针 | 原版是模型 `NightElfCursor.mdl`，这里沿用录像页已有的人族指针 PNG |
| 物品栏盖板 | 选中非英雄单位时显示，位置是估的 |
| 命令卡按钮位置 | 技能固定放第三行前四格，没有读每个技能的 `Buttonpos` |
| 状态图标 | 原版在面板底部画 Buff 图标，这里是文字 |
| 聊天 (F12) | 只是消息记录，没有聊天输入 |
| 出售物品 | 原版是右键拿起再点商店，这里是右键直接卖 |

## 9. 复现

```powershell
cd D:\Qt\workspace\War3Angular
node scripts\extract-native-ui.cjs dump     # war3skins.txt + fdf → War3Analysis\artifacts\wc3-native-ui
node scripts\extract-native-ui.cjs assets   # 贴图 → public\assets\wc3\native-ui（含 manifest.json 的镂空矩形）
```
