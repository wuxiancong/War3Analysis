# DotA 6.83d 英雄真实路径绘制修复与全指令/瞬移/物品同步逆向分析报告

## 一、背景与样本来源

本报告基于以下工程代码、地图脚本与实测录像数据包：

- **客户端与统计分析代码**：
  - `D:\Qt\workspace\War3Bot\main.qml`
  - `D:\Qt\workspace\War3Bot\components\CustomComboBoxComponent.qml`
  - `D:\Qt\workspace\War3Bot\src\matchstatsprovider.cpp`
  - `D:\Qt\workspace\War3Bot\src\client.cpp`
- **地图脚本**：`D:\Qt\workspace\War3Script\war3map.j`（DotA v6.83d）
- **实测玩家动作归档**：`D:\Qt\workspace\War3Bot\build\Desktop_Qt_5_15_2_VSCode_MSVC_32bit_Release\data\player_actions\wuxiancong\` 下共 **32 份** `match_*.dat` 压缩动作档案（涵盖黑曜毁灭者 `U00P`、敌法师 `Edem`、月之女祭司 `N01V`、风暴之灵 `H00S`、痛苦女王 `UC01`、舰队统帅 `H06S`、神灵武士 `H00Q`、精灵守卫 `O01F`、发条地精 `H00T`、撼地神牛 `Otch`、流浪剑客 `H001`、山岭巨人 `Ucrl`、牛头人酋长 `O015`、凤凰 `E02F`、巨牙海民 `E02I`、地精撕裂者 `E032`、大地之灵 `N0MU`、骷髅王 `NC00`、半人猛犸 `UC11`、裂魂人 `O00J`、沙王 `U00K`、变体精灵 `O00P`、隐形刺客 `HC92`、灰烬之灵 `N0M0`、鱼人夜行者 `H071`、幻影刺客 `Ewar`、虚空假面 `EC45`、仙女龙 `N00B` 等 29 位英雄）。

---

## 二、四个 Bug 的根因定位与修复方案

### Bug 1：原始动作数据包流全屏滚轮失效、数据更新不保持原滚动位置、以及“点击跳转”在追随最新下的状态控制

1. **全屏滚轮无法滚动 & 刷新重置滚动条位置的根因**：
   - 在 `main.qml` 的 `PacketStreamPanel` 中，`pktListView` 的 `model:` 绑定表达式内部直接读取了 `var keepY = pktListView.contentY;`。
   - 在 QML 属性绑定机制中，在 `model:` 块内读取 `pktListView.contentY` 会使 `model` 形成对 `contentY` 的响应式依赖！
   - 当用户滚动鼠标中键滚轮时，`contentY` 发生微调 -> 立即触发 `model:` 重新求值 -> 返回一个新的 JS 数组 `pkts` -> `ListView` 重建整个列表并将 `contentY` 强制归零 -> 在 `Qt.callLater(restorePreservedScroll)` 尚未执行前又触发第二次重算，把 `preservedContentY` 覆盖为 `0`。在全屏弹窗（`pktPopup`）下可视行数更多，滚轮一滚即被瞬间拉回顶部。
2. **“点击能跳转 ▶”的含义与追随最新互斥逻辑**：
   - 点击某条数据包行的含义是：**将回放时间轴（`curSec` 与 `playSec`）跳转到该数据包发生的时间秒数 `sec`**，从而同步查看该时刻的小地图英雄位置与战绩面板。
   - 当实时直播对局开启 **“追随最新 ✓”（`liveFollow === true`）** 时，每秒定时器会自动把时间轴推到最新秒数，此时允许点击跳转会产生状态冲突。
3. **修复方案**：
   - 移除 `pktListView` 上的响应式 JS 数组 `model:` 绑定，改为独立的 `ListModel { id: pktListModel }`，并通过 `syncPacketModel()` 函数在 `curSec` / `pktFilter` / `md` 变化时**原地增量更新**（`set` / `append` / `remove`），彻底切断 `contentY -> model` 循环依赖，保持滚动条位置稳定不变。
   - 在数据包行 `MouseArea` 的 `onWheel` 中显式按滚轮方向平滑推进 `pktListView.contentY`，确保普通视图与全屏弹窗（`pktPopup`）下鼠标中键滚轮均可顺畅滚动。
   - 新增 `canJumpTimeline: !(md && md.isLive && liveFollow)`，当处于实时对局且开启“追随最新 ✓”时禁用数据包流、时间轴标记（`markStrip`）和关键事件的点击跳转，并将悬浮提示更新为 `“追随最新中 (禁用跳转)”`，关闭追随最新或处于历史回放时显示 `“点击跳至该时间轴 ▶”`。

---

### Bug 2：非瞬移动作情况下也出现真实路径绘制断裂

1. **根因分析（共 5 处叠加原因）**：
   - **原因 A（物品换格 `moveslot` 携带商店出生点坐标污染轨迹）**：
     - 在 `match_20261104_044355` 等档案中，`0x12 + 0xD0022..0xD0027`（`moveslot1..6` 整理背包换格）的数据包目标坐标固定为物品在泉水商店创建时的坐标 `(-6904, -6831)`。旧代码将所有 `x != 0 || y != 0` 的动作全部塞入 `moves`，且 `getRealMovement` 看到目标在泉水且距离 `> 2500` 就误判为 `isRespawn = true`（死亡复活回泉水），导致**每次在野区/线上换物品格子，英雄轨迹就瞬间拉断并跳回泉水**！
   - **原因 B（远程非位移技能与吃树/插眼指令污染 `moves`）**：
     - 发条照明火箭（`0x11+0xD0079`）、船长洪流（`0x11+0xD0079`）、火猫放残焰（`0x11+0xD020A`）、大牛先祖之魂（`0x11+0xD02BD`）、神牛沟壑（`0x11+0xD0278`）、仙女龙发球发射（`0x11+0xD02B6`）、骷髅王锤（`0x12+0xD007F`）、流浪锤（`0x12+0xD02B6`）、小小投掷（`0x12+0xD0278`）以及用吃树点树（`0x12+useslot`）均带有远程目标坐标 `(x, y)`，但英雄本体并未位移；旧逻辑将它们全部当作移动目标或物品瞬移（`tpType=1`），造成路径频繁断裂或折返。
   - **原因 C（线上存活时切回泉水操作信使/能量圈）**：
     - 在 `match_20261104_013957` 的 `1143.78s`，玩家英雄在中路 `(-1120, -1677)` 存活，切回泉水右键点击信使 `(-6624, -7200)`，`1.38s` 后切回中路英雄。旧代码未结合 `Data:Hero` 死亡事件校验，直接按坐标落入泉水判定为“复活”，导致轨迹在中路凭空断裂跳回泉水。
   - **原因 D（`getRealMovement` 在瞬移前漏算前序步行位移）**：
     - 旧 `getRealMovement` 在 `actT` 遇到 `isInstant`（TP、跳刀、技能闪烁、死亡回泉水）时，直接执行 `curX = targetX; curY = targetY;`，**跳过了 `[curT, actT]` 时间段内英雄朝上一目标点 `lastTarget` 的步行推进**，导致每次 TP、跳刀或阵亡前最后几秒的绿色行走轨迹被直接吞掉，表现为视觉上的路径断裂。
   - **原因 E（轨迹末尾未闭合至 `curPos`）**：
     - 循环结束后在 `[curT, maxTime]` 推进了 `curX, curY` 用于画英雄头像 `curPos`，但**没有调用 `path.push([curX, curY, false])`**，导致绿色轨迹线末端与移动中的英雄头像之间始终脱节一段距离。
2. **修复方案**：
   - 在 `matchstatsprovider.cpp` 中严格过滤 `moves`：仅向 `moves` 推入真正的地面移动（`0xD0003`/`0xD000F`/`0xD0012`）、停止指令（`instantType = -1`）、确认的物品瞬移（`instantType = 1`：TP 与跳刀）、确认的技能瞬移/位移（`instantType = 2`）以及由 `Data:Hero<被杀者>=<击杀者>` 真实死亡事件驱动的复活回泉水节点（`instantType = 3`）；彻底剔除 `moveslot` 换格、插眼/吃树、远程非位移技能以及线上存活时的泉水信使操作。
   - 重构 `TrajMap.getRealMovement`：
     1. 对每条指令 `actT`，**先**按 `dt = (actT - curT)/1000` 将英雄沿上一目标 `lastTarget` 平滑推进并 `path.push([curX, curY, false, 0])`；
     2. **再**应用 `actT` 时刻的新指令（`tpType === -1` 原地停止；`tpType >= 1` 瞬移跳变并 `path.push([curX, curY, true, tpType])`；`tpType === 0` 更新 `lastTarget` 继续行走）；
     3. 循环结束后将 `[curT, maxTime]` 的剩余步行段推入 `path`，确保绿色轨迹线与英雄头像无缝衔接。

---

### Bug 3：当有新游戏时数据统计页所有 ComboBox 下拉列表没有更新

1. **根因分析**：
   - `liveStatsTimer`（`main.qml`）原本只在 `else if (!statsPage.md)`（即未选中任何比赛）时才调用 `statsPage.refresh()`；一旦用户已经打开过任意一场历史对局或正在观看对局，后续新开局或对局结束落盘都不会触发 `scanMatches()`。
   - `refreshLiveCurrent()` 仅重载了已有的 `rosterMds` 元素，未重建 `rosterLabels`，导致直播中玩家选出英雄后，`切换玩家 (OB)` 下拉框仍一直显示 `“[未选择英雄]”`。
   - 顶部的 3 个 `CustomComboBoxComponent`（`匹配标识`、`玩家名`、`房间名`）和 `切换玩家 (OB)` 未绑定 `currentIndex: statsPage.selectedIndex` / `statsPage.selPlayer`，且 `CustomComboBoxComponent.qml` 的 `contentItem.text` 仅绑定了 `displayText`（Qt 5.15 在 JS 数组 `model` 替换但 `currentIndex` 不变时不会自动刷新 `displayText`）。
2. **修复方案**：
   - 新增 `statsPage.syncMatchList()`，在 `liveStatsTimer` 每秒触发时计算最新扫描列表签名 `buildMatchesSig(scanned)`，一旦检测到新对局开启、直播转归档或英雄信息变化，立即刷新 `allMatches` 与 `applyFilter()`，并在 `applyFilter()` 中按 `prevPath`（或同房间玩家）自动保持选中项索引。
   - 在 `refreshLiveCurrent()` 中同步重建 `rosterLabels`。
   - 为全部 4 个 `CustomComboBoxComponent` 显式绑定 `currentIndex`，并在 `CustomComboBoxComponent.qml` 中直接响应式读取 `model[currentIndex]`。

---

## 三、Bug 4：DotA 6.83d 动作指令与 0x6B 同步协议完整映射表

通过对 `wuxiancong` 下 32 份录像档案的全量解压扫描与 `war3map.j` 逆向核对，整理出完整指令语义与位移分类表：

### 1. `0x10` 无目标指令（No-Target Order）

| 动作 ID | OrderID (Hex) | Order 字符/名称 | 对应英雄 / 场景 | 运动学与轨迹处理 (`instantType`) | 实测档案验证 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x10` | `0x6830xxxx` (`0xh0**`) | `h011`/`h02E`/`h028` 等 | 商店购买物品（无目标） | 不移动（`shouldAddMove=false`），配合 `0x6B Data:PUI_` 统计购买 | `match_20261103_235723` 等 |
| `0x10` | `0x000D0004` | `stop` (S键) | 停止指令（移动中按 S 急停，或原地按 S） | **停止节点 (`instantType = -1`)**：推进前序步行至 `t` 后将 `lastTarget` 设为当前坐标 | `match_20261104_035139` (`N01V`) |
| `0x10` | `0x000D00A1` | `windwalk` / 跳跃 | **月之女祭司 (`N01V` 白虎)** 跳跃 (Leap) | **技能位移 (`instantType = 2`)**：按英雄当前朝向 `simAngle` 与等级跳跃距离 `600/700/800/900` 码计算落点 | `match_20261104_035139` (`N01V`, 5次) |
| `0x10` | `0x000D00D9` | `etherealjaunt` | **仙女龙 (`N00B` 帕克)** 幻象法球传送 (R) | **技能瞬移 (`instantType = 2`)**：按 `0x11+0xD02B6` 发球起点与飞行速度 `650码/秒` 计算法球实时坐标并瞬移 | `match_20261104_070405` (`N00B`, 2次) |
| `0x10` | `0x000D0114` | `manashield` / 子技能停止 | **仙女龙 (`N00B`)** 灵动之翼(E)中途停止 / **凤凰 (`E02F`)** 凤凰冲击停止 | **停止节点 (`instantType = -1`)**：定格在当前位置（凤凰配合 `0x11+0xD0278` 落点） | `match_20261104_070405` (`N00B`)、`match_20261104_050321` (`E02F`) |
| `0x10` | `0x000D0278` | `carrionswarm` / 突袭 | **鱼人夜行者 (`H071`)** 突袭跳跃 (Pounce)<br>发条 (`H00T`) 弹幕冲击 / 火猫 (`N0M0`) 炎阳索 | 当 `hero == H071` 时为 **技能位移 (`instantType = 2`)**（沿朝向跳跃 700 码）；`H00T`/`N0M0` 时不移动 | `match_20261104_063421` (`H071`, 7次) |

---

### 2. `0x11` 地点目标指令（Point-Target Order）

| 动作 ID | OrderID (Hex) | 对应英雄 (`heroCode`) | 技能 / 物品名称 | 是否位移 (`instantType`) | 轨迹与视野处理说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x11` | `0xD0028..0xD002D` | 全英雄 (`useslot1..6`) | **回城卷轴(TP) / 远行鞋 / 跳刀** / 侦查守卫 | **物品瞬移 (`instantType = 1`)**（排除 0.65s 内触发 `DRI` 消耗假眼 `I014`/真眼 `I016` 的插眼操作） | 距离 `> 1350` 或 1.2~5.8s 内触发 `DRI=1227896137(I009)` 归为 **TP传送**；其余归为 **跳刀闪烁** |
| `0x11` | `0x000D0079` | 发条 (`H00T`) / 船长 (`H06S`) / 火猫 (`N0M0`) | **照明火箭(导弹)** / **洪流** / **无影拳** | **否 (`shouldAddMove = false`)** | 远程开视野/范围技能，记录命中点事件但绝不拉扯英雄本体轨迹 |
| `0x11` | `0x000D00D9` | 灰烬之灵 (`N0M0`) | **激活火之余烬 (R实现瞬移)** | **技能瞬移 (`instantType = 2`)** | 英雄飞向指定残焰坐标 `(x, y)` |
| `0x11` | `0x000D020A` | 灰烬之灵 (`N0M0`) | **释放火之余烬 (F预放位置)** | **否 (`shouldAddMove = false`)** | 仅投射残焰镜像至 `(x, y)`，英雄本体不发生位移 |
| `0x11` | `0x000D022D` | 敌法师 (`Edem`) / 痛苦女王 (`UC01`) | **闪烁 (Blink)** | **技能瞬移 (`instantType = 2`)** | 瞬间闪烁至目标点 `(x, y)` |
| `0x11` | `0x000D0278` | 撼地神牛 (`Otch`) / 凤凰 (`E02F`) | **沟壑 (Fissure)** / **凤凰冲击 (Icarus Dive)** | `Otch`：**否**（沟壑轨迹）<br>`E02F`：若 2.5s 内按 `0x10+0xD0114` 暂停则为 **技能位移 (`instantType = 2`)** | 区分神牛沟壑与凤凰冲击中途停驻 |
| `0x11` | `0x000D02AC` | 发条地精 (`H00T`) | **发射钩爪 (Hookshot)** | **技能瞬移 (`instantType = 2`)** | 钩中后高速牵引位移至 `(x, y)` |
| `0x11` | `0x000D02B6` | 伐木机 (`E032`) / 大地之灵 (`N0MU`) / 仙女龙 (`N00B`) | **伐木锯链** / **翻滚巨石** / **幻象法球预传递** | `E032` & `N0MU`：**技能瞬移 (`instantType = 2`)**<br>`N00B`：**发射法球记录方向向量**（待 `0x10+0xD00D9` 触发真实瞬移） | 完美还原帕克“发球飞行 + R 传球”的真实落点 |
| `0x11` | `0x000D02BD` | 牛头人酋长 (`O015`) | **先祖之魂 (Astral Spirit)** | **否 (`shouldAddMove = false`)** | 魂体开视野技能，本体不移动 |

---

### 3. `0x12` 单位/物体目标指令（Unit/Object-Target Order）

| 动作 ID | OrderID (Hex) | 对应英雄 (`heroCode`) | 技能 / 指令名称 | 是否位移 (`instantType`) | 动态目标与轨迹计算说明 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `0x12` | `0x000D0003` | 全英雄 (`smart`) | **普通右键移动/智能指令** | **普通移动 (`instantType = 0`)** | 过滤线上存活时切泉水点信使的伪指令，按移速平滑插值 |
| `0x12` | `0xD0022..0xD0027` | 全英雄 (`moveslot1..6`) | **背包物品换格** | **否 (`shouldAddMove = false`)** | 数据包坐标为物品在商店创建点 `(-6904,-6831)`，严禁加入 `moves` |
| `0x12` | `0x000D007F` | 骷髅王 (`NC00`) | **冥火暴击 (锤子)** | **否 (`shouldAddMove = false`)** | 远程单体眩晕锤，本体不位移 |
| `0x12` | `0x000D0097` | 精灵守卫 (`O01F`) | **闪电之链联结队友 (Tether)** | 距离 `> 300` 时为 **技能位移 (`instantType = 2`)** | 远距离连线会将小精灵牵引至队友身边 |
| `0x12` | `0x000D00D9` | 巨牙海民 (`E02I`) | **滚动雪球 (Snowball)** | **技能位移 (`instantType = 2`)** | 滚向目标单位 `(x, y)` |
| `0x12` | `0x000D00FA` | 蓝猫 (`H00S`) / 猛犸 (`UC11`) / 水人 (`O00P`) / 虚空 (`EC45`) | **球状闪电(飞)** / **獠牙冲刺** / **波浪形态** / **时间漫游** | **技能位移 (`instantType = 2`)** | 四位英雄共用 `0xD00FA`（含 `0x11`/`0x12`），均直接位移至 `(x, y)` |
| `0x12` | `0x000D0107` | 神灵武士 (`H00Q`) | **牺牲大招冲刺 (Life Break)** | **技能位移 (`instantType = 2`)** | 冲刺跳跃至目标单位位置 `(x, y)` |
| `0x12` | `0x000D0265` | 舰队统帅 (`H06S`) | **X标记 (X Marks the Spot)** | 标记自施法后 **4 秒内（或按 `0x10+0xD0265`）触发回传 (`instantType = 2`)** | 记录标记点 `(xMarkX, xMarkY)` 并在主动二段或 4 秒到期时回传 |
| `0x12` | `0x000D0278` | 裂魂人 (`O00J`) / 沙王 (`U00K`) / 山岭巨人 (`Ucrl`) / 幻刺 (`Ewar`) / 隐刺 (`HC92`) | **暗影冲刺** / **掘地穿刺** / **投掷(Toss)** / **幻影突袭** / **闪烁突袭** | `Ewar`/`HC92`/`U00K`/`O00J`：**技能瞬移/冲刺 (`instantType = 2`)**<br>`Ucrl`（投掷）：**否** | 裂魂人暗影冲刺若目标移动，后续指令或到达后的首次移动指令会自动修正最终接触点；小小投掷自身不移动 |
| `0x12` | `0x000D02B6` | 流浪剑客 (`H001`) | **风暴之锤 (锤子)** | **否 (`shouldAddMove = false`)** | 范围眩晕投射物，本体不移动 |

---

### 4. `0x16` 与 `0x6B` 游戏缓存同步事件（死亡复活与物品获得/消耗）

1. **英雄死亡与复活 (`0x6B "Data:Hero<被杀者>=<击杀者>"` + `0x16`)**：
   - `Data:Hero1=6` 表示 **玩家 1 被阵营 6（天灾电脑/防御塔/小兵）击杀**；
   - 击杀者 ID 映射：
     - `0`：近卫军团（小兵/防御塔/泉水）
     - `6`：天灾军团（电脑小兵/防御塔/泉水）
     - `12`：中立生物（野怪/远古野/肉山）
     - `1..5`、`7..11`：对应槽位玩家英雄
   - 当检测到当前玩家阵亡时，立即在死亡时刻 `t` 插入停止节点（`instantType = -1`），并在复活选定英雄（`0x16`）或复活后首次移动时插入 **死亡复活回泉水节点（`instantType = 3`）**。
2. **物品状态更新同步 (`Data:PUI_<pid>=<itemId>` 与 `Data:DRI_<pid>=<itemId>`)**：
   - `Data:PUI_1=<十进制FourCC>`：购买、拾取地面物品或合成获得物品时由地图 JASS 触发同步（例如 `1227896137` -> `I009` 回城卷轴，`1227895375` -> `I00O` 铁树枝干）。
   - `Data:DRI_1=<十进制FourCC>`（或 `Data:DR_1=`）：出售、丢弃到地面或使用消耗完物品（如 TP 落地消耗 `I009`、插眼消耗 `I014`/`I016`、吃树消耗 `I01K`）时触发同步。
   - **为什么交换物品槽位不会触发 `PUI`/`DRI`？** 因为在魔兽争霸 III 引擎中，背包内换格（`0x12 + 0xD0022..0xD0027`）仅改变物品在 `UnitInventorySlot` 数组中的槽位索引，不会触发 `EVENT_PLAYER_UNIT_PICKUP_ITEM` 或 `EVENT_PLAYER_UNIT_DROP_ITEM`，因此 `war3map.j` 不会广播 `PUI`/`DRI`。

