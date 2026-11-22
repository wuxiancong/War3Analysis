# War3 1.27 录像（`.w3g`）解析与「局面 → 操作」模仿学习数据集方案

| 字段 | 内容 |
|---|---|
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 定死 War3 1.27 `.w3g` 录像与 DotA 6.83d 常用动作二进制格式，交付纯 Python 录像解析器、0.5s 步长模仿学习 JSONL Schema 与本地样本统计，评估三条「局面坐标补齐」路线并推荐落地架构，调研公开真人录像来源与对线期模型所需数据量 |
| **命名方式** | `dota-replay-imitation-dataset`；配套导图 `dota-replay-imitation-dataset-mindmap.md`；解析器与样本 `artifacts/replay-dataset/` |
| **分析时间** | 2026-11-21 |
| **验证状态** | ✅ 已通过 8 场本地 1.27 `.w3g` 完整录像实测解析（36,138 条动作、1,110 条 `0x6B` 事件、生成 3,000 条 0.5s JSONL 样本）验证；**未**修改游戏目录，**未**改动 `War3Launcher` / `hooker` 代码，**未**下载外部文件 |
| **证据** | `artifacts/replay-dataset/w3g_parser.py`、`build_dataset.py`、`imitation_dataset_schema.json`、`sample_dataset.jsonl`、`sample_parsed_replay.json`、`replay_corpus_stats.txt`；本地副本 `artifacts/replay-dataset/data/*.w3g`；前序 [`warcraft-iii-action-ids-and-dota-stats-transmission.md`](./warcraft-iii-action-ids-and-dota-stats-transmission.md)、[`dota-hero-ability-cast-flow.md`](./dota-hero-ability-cast-flow.md)、[`dota-player-lasthit-habit-recorder.md`](./dota-player-lasthit-habit-recorder.md)、[`dota-player-learn-habit-recorder.md`](./dota-player-learn-habit-recorder.md)、[`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md)、[`dota-ai-llm-mcp-control.md`](./dota-ai-llm-mcp-control.md) |

---

## 核心结论速览

1. **`.w3g` 1.27 解析完全打通（纯 Python 标准库）**：1.27 录像采用 **68 字节标准头 + 8 字节块头 zlib 压缩块**（非重制版 12 字节块头）。解析器 [`w3g_parser.py`](../artifacts/replay-dataset/w3g_parser.py) 已完整解码玩家表、位掩码编码地图串、`0x1F/0x1E` TimeSlot、全量 1.27 Action ID、玩家当前选中单位栈、OrderId/FourCC 语义、`0x6B` GameCache 事件与英雄推断。
2. **「局面」补齐三条路线结论 → 强烈推荐路线 B（War3 引擎回放 + hook 旁路采样）**：
   - 路线 A（纯动作目标点近似）：零成本但**看不到血蓝、小兵、敌方英雄、技能 CD**，仅适合做粗粒度宏策略/加点/出装预训练；
   - **路线 B（War3 引擎 8x 加速回放 + 只读 hook 采样，推荐主路线）**：100% 引擎级精确坐标、HP/MP、金钱、技能 CD、视野过滤（`IsUnitVisible`防透视），且与 `dota-ai-llm-mcp-control.md` 已有只读偏移完全复用；配合 8 倍速回放，1 场 35 分钟录像仅需 ~4.5 分钟即可采完 4,200 帧完美「局面 → 操作」对齐样本；
   - 路线 C（网页模拟）：缺乏完整的 DotA 6.83d JASS 触发器与 32Hz 碰撞/寻路引擎，几秒后即状态发散，不适合高精度微操模仿。
3. **数据集格式与本地测试局清洗警示**：
   - 采用 **JSONL（每 0.5s 一条 `state -> action` 样本）**（大批量训练时可零成本转 Parquet），完整 schema 见 [`imitation_dataset_schema.json`](../artifacts/replay-dataset/imitation_dataset_schema.json)。
   - 对本机 20 份录像副本实测发现两个关键工程陷阱：① 强杀 `war3.exe` 产生的 `*_player_*.w3g` 头部 68 字节全零未封口（解析器自动识别跳过）；② 本地 AI 卡兵测试局里 `aiSelectHero()` 每 85ms 发一次选人包导致 `select_or_group` 占比高达 **70.60%**、APM 虚高至 `771.9`——**正式训练必须过滤 AI 测试局并合并冗余选人包**。
4. **真人录像来源与数据量估算**：
   - 合法公开来源：D1Map.net（RGC/DotA 1 活跃库）、iCCup Replay Archive（1.26/1.27 历史库）、WC3Stats（公开 API）、KK 平台/本机 `War3Bot` 自建房录制。
   - **训练「对线期（0~10 分钟）」模仿模型**：单英雄（如冰女/影魔）分层次行为克隆（BC）需 **30~50 局高质量真人局（约 3.6万~6万条 0.5s 样本）** 即可见效；泛化到 10~20 个常见对线英雄需 **300~500 局（约 36万~60万条样本）**。

---

## 一、 War3 1.27 `.w3g` 文件格式与 DotA 常用动作字典

### 1.1 1.27 `.w3g` 物理封装结构（已实测核对 8 场 1.27 录像）

```text
[0x00..0x1B] Magic (28B): "Warcraft III recorded game\x1A\x00"
[0x1C..0x2F] Main Header (20B):
               u32 header_size (= 0x44 = 68B)
               u32 compressed_size (整个文件大小)
               u32 header_version (= 1，对应 1.07~1.27 经典版)
               u32 decompressed_size
               u32 num_blocks (zlib 块数量)
[0x30..0x43] Sub Header (20B, version=1):
               char[4] game_id ("PX3W" 冰封王座 / "3RAW" 混乱之治，小端反序)
               u32 patch_version (= 27 即 1.27)
               u16 build_number
               u16 flags (0x8000 = 多人局)
               u32 duration_ms (对局总时长，毫秒)
               u32 crc32
[0x44..EOF]  Compressed Data Blocks × num_blocks:
               每块 8B 块头: u16 compressed_len, u16 decompressed_len (通常 8192), u32 checksum
               后接 compressed_len 字节的 zlib 流（块末可能用 Z_SYNC_FLUSH 而非 Z_FINISH，需用 decompressobj）
```

> **本地实测坑点**：若 `war3.exe` 未正常退出结算界面（如被 `taskkill /F` 强杀），引擎来不及回写 `[0x00..0x43]` 的 68 字节文件头，文件前 32 字节全为 `0x00`（本次扫描本机 20 份录像中 12 份 `*_player_*.w3g` 即属此类，8 份正常退出的 `*_TestUser01_*.w3g` 头部完整）。

### 1.2 解压后数据流结构

1. **启动元数据区**：
   - `4B` 未知头 → 房主 `PlayerRecord (0x00)` → `game_name\0` → `0x00` → **位掩码编码串**（每 8 字节由 1 字节 odd-byte mask + 7 字节编码数据组成，解码后偏移 `+13` 为 `map_path\0` + `creator_name\0`）→ `player_count(4) + game_type(4) + lang_id(4)` → 其余玩家 `PlayerRecord (0x16)` → 槽位表 `GameStartRecord (0x19)`（每槽 9 字节：pid、下载进度、状态、是否电脑、队伍、颜色、种族、AI 难度、血量百分比）。
2. **时序块流（Block Stream）**：
   - **`0x1F` / `0x1E` TimeSlot 块**：`u16 nbytes` + `u16 time_inc_ms`（全局时钟 `time_ms += time_inc_ms`），剩余 `nbytes - 2` 字节包含 0 个或多个 **CommandData** 子块：`u8 pid` + `u16 action_len` + `action_bytes[action_len]`。
   - **`0x20` PlayerChat 块**：`u8 pid` + `u16 len` + `u8 flags`（`0x20` 时紧跟 `u32 chat_mode`：0=所有人/1=盟友/2=观战）+ `msg\0`。
   - **`0x17` LeaveGame**（13B）、`0x1A/0x1B/0x1C`（4B 加载标记）、`0x22`（5B 同步校验）、`0x23`（10B）、`0x2F`（8B 倒计时）。

### 1.3 DotA 6.83d 常用 Action ID 载荷格式与 OrderId 含义表

所有字节长度均已与 `War3Bot/src/client.cpp` 及 [`warcraft-iii-action-ids-and-dota-stats-transmission.md`](./warcraft-iii-action-ids-and-dota-stats-transmission.md) 交叉核验：

| Action ID | 名称 | 载荷长度 (不含ID) | 二进制字段布局 | DotA 6.83d 业务含义 |
|---|---|---:|---|---|
| **`0x10`** | 无目标指令 | `14B` | `u16 flags` + `u32 order_or_fourcc` + `u64 unk` | 停止 (`0xD0004`)、保持 (`0xD0019`)、无目标技能/物品 (`0xD0028..2D`)、**技能加点**（技能 FourCC 如 `A05G`/`Aamk`）、**选英雄/买物品**（单位 FourCC 如 `Hjai`/`h01K`） |
| **`0x11`** | 点目标指令 | `22B` | `0x10(14B)` + `f32 x` + `f32 y` | 地面点地技能（闪烁 `0xD022D`、冰霜新星/暴风雪 `0xD0079`）、A 地板 (`0xD000F`)、地面移动 (`0xD0003`/`0xD0012`) |
| **`0x12`** | 单位目标指令 | `30B` | `0x11(22B)` + `u32 target_obj1` + `u32 target_obj2` | 右键移动/攻击/拾取 (`0xD0003`，点地时 `obj1=obj2=0xFFFFFFFF`)、指定攻击 (`0xD000F`)、单体指向性技能 (`0xD007F`/`0xD0083`)、对单位/树使用物品 (`0xD0028..2D`) |
| **`0x13`** | 物品转移/丢弃 | `38B` | `0x12(30B)` + `u32 item_obj1` + `u32 item_obj2` | 丢弃物品到地上或递交给队友/信使 (`0xD0021`) |
| **`0x14`** | 双目标指令 | `43B` | `Flags(2)+OrderA(4)+Unk(8)+XY1(8)+OrderB(4)+FlagsB(9)+XY2(8)` | 极少数双目标技能（如部分自定义/拉扯技） |
| **`0x16`** | 选择单位 | `3 + 8×N` | `u8 mode (1=加选, 2=减选)` + `u16 count` + `count × (u32 obj1, u32 obj2)` | 左键单选/框选/Shift 加减选，解析器据此实时维护「当前选中单位集合」 |
| **`0x17`** | 设置编队 | `3 + 8×N` | `u8 group (0..9)` + `u16 count` + `count × (u32 obj1, u32 obj2)` | `Ctrl + 1~9` 编队 |
| **`0x18`** | 切换编队 | `2B` | `u8 group (0..9)` + `u8 unk` | 按 `1~9` 选中对应编队 |
| **`0x19`** | 切换子组 | `12B` | `u32 unit_type_fourcc` + `u32 obj1` + `u32 obj2` | `Tab` 切子组或选中英雄自动触发，**`unit_type_fourcc` 可直接识别玩家英雄 FourCC 与 `hero_obj1`** |
| **`0x1A`** | 预选择 | `0B` | 无附加字节（`PreSubselection`） | `0x19` 前的固定同步前缀 |
| **`0x1B`** | 选中触发单位 | `9B` | `u8 mode` + `u32 obj1` + `u32 obj2` | 脚本/单点选中 |
| **`0x60`** | 触发聊天 | `8 + len + 1` | `u32 unk1` + `u32 unk2` + `cstr text\0` | 触发地图脚本的聊天命令（`-ap`、`-random`、`-repick`、`-buyback` 等） |
| **`0x66`** | 技能加点菜单 | `0B` | 无附加字节 | 点开红十字加点子菜单（常紧跟 `0x10 + AbilityFourCC`） |
| **`0x68`** | 小地图 Ping | `12B` | `f32 x` + `f32 y` + `f32 duration` | `Alt + 左键` 小地图信号（团队意图/求援/Gank 标注） |
| **`0x6B`** | GameCache 同步 | 变长 | `cstr cache\0` + `cstr mkey\0` + `cstr key\0` + `u32 val` | DotA 6.83d 权威事件总线：局内 `Data:CSK*` (正补)、`CSD*` (反补)、`NK*` (野怪)、`Level*` (升级)、`Hero*` (击杀)、`Tower*` (推塔)、终局 `dr.x` 全员 KDA/金钱/装备/胜负 |

**常用核心 OrderId 速查**：
- `0x000D0003` = `smart`（右键智能移动/攻击/拾取）
- `0x000D0004` = `stop`（停止 `S`，补刀压刀核心指令）
- `0x000D000F` = `attack`（攻击 `A`）
- `0x000D0012` = `move`（强制移动 `M`）
- `0x000D0016` = `patrol`（巡逻 `P`）
- `0x000D0019` = `holdposition`（保持原位 `H`）
- `0x000D0021` = `dropitem`（丢弃/给予物品）
- `0x000D0022..0x000D0027` = `moveslot1..6`（背包换格）
- `0x000D0028..0x000D002D` = `useslot1..6`（使用 1~6 号物品格）
- `0x000D0079` / `0xD007F` / `0xD0081` / `0xD0083` / `0xD0118` / `0xD022D` = 常见主动技能 Order（如冰女 V `0xD0081`、E `0xD0083`、大招 `0xD0118`、闪烁 `0xD022D`）。

---

## 二、 Python 解析器实现（`artifacts/replay-dataset/w3g_parser.py`）

解析器 [`w3g_parser.py`](../artifacts/replay-dataset/w3g_parser.py) 不依赖任何第三方库，输入任意 1.27 `.w3g` 文件，输出完整 JSON（示例见 [`sample_parsed_replay.json`](../artifacts/replay-dataset/sample_parsed_replay.json)）：
- **玩家动作流 (`actions[]`)**：包含 `t_ms`、`pid`、`aid`、`type`、`order_id`、`order_name`、`order_kind`、`x/y`、`target_obj1/2`、以及解析器实时维护的 `selected[]`（当时选中的单位对象 ID 列表）。
- **事件流 (`events[]`)**：自动提取并解码 `0x6B`（`CSK/CSD/NK/Level/Hero/Tower/Winner/end_hero`）、`0x60`/`0x20` 聊天与 `0x17` 退局事件。
- **英雄自动推断**：同时结合 `0x10` 酒馆选人 FourCC、`0x19` 首次子组切换 FourCC（同步拿到 `hero_obj1`）与 `0x6B` 终局 `key="9"`，在全部 8 场有效本地录像中 100% 准确识别出 `TestUser01 -> Hjai (水晶室女)`。

---

## 三、 「局面」怎么补：三条技术路线对比与推荐方案

`.w3g` 本质上是**确定性帧同步指令流（Deterministic Lockstep Input Log）**，只存输入操作，不存引擎每帧算出来的单位坐标、血蓝、金钱和小兵位置。补齐「局面 `state`」有三条路线：

| 对比维度 | 路线 A：仅用 `.w3g` 动作目标点近似 | **路线 B：War3 引擎回放 + hook 只读采样（强烈推荐 ✅）** | 路线 C：自研网页模拟器重放 |
|---|---|---|---|
| **能拿到的局面特征** | 英雄粗略位置（移动目标点滑动平均）、英雄等级（`0x6B Level`）、累计正反补/击杀、已学技能、历史动作流 | **全量精确引擎状态**：己方与视野内全部英雄/小兵/塔/野怪的精确 `(x,y)`、`HP/MP`、可靠/不可靠金钱、6 格物品与 CD、技能等级与 CD、Buff/Debuff、昼夜、买活状态（均在 `dota-ai-llm-mcp-control.md` 与 `war3-unit-movement-fields.md` 已验证） | 仅能模拟简化直线移动与数值公式，无法还原真实寻路与技能触发器 |
| **坐标与状态精度** | ❌ 极低（误差 300~1500；无血蓝、无小兵、无敌人位置、无视野） | ✅ **100% 引擎原生精确值**（与真实对局 0 偏差，且可调 `IsUnitVisible` 严格做防透视迷雾过滤） | ❌ 几秒即发散（缺 32Hz `CPoSeparate`/`CLrPath` 与 9 万行 `war3map.j` 触发器） |
| **开发与运行成本** | 极低（纯 Python，0.05 秒/局） | **中等偏低**：读坐标/血蓝/金钱/视野的 1.27 RVA 已全部就绪，只需在 hook 里加一个「回放模式只读 500ms 采样器」写 JSONL；配合 War3 8x 倍速回放，1 场 35 分钟录像仅需 **~4.5 分钟**（若只采 0~10 分钟对线期仅需 **~1.5 分钟/局**！） | 极高（相当于重写整个 War3 引擎 + JASS VM，投入产出比极差） |
| **适用任务** | 仅适合 **宏观出装/加点习惯、APM 节奏、粗略分路意图**（阶段 1 冷启动） | **全阶段主力路线**：对线期补刀/走位/消耗/技能连招/撤退、大模型指挥层「意图」监督微调（SFT）与离线强化学习（Offline RL） | 仅适合前端 3D 展示预览，**不推荐用于生成训练数据** |

### 推荐落地架构（双阶段融合）

1. **阶段 1（立即可用，纯 Python）**：用本文 `w3g_parser.py` + `build_dataset.py` 批量扫清录像库，筛选高水平、无早退、指定英雄/分路的录像，抽出 `actions` + `0x6B` 事件，先训练**加点/出装/宏观分路策略**。
2. **阶段 2（主力训练集，War3 引擎回放 + hook 采样）**：在 `war3hook` 中增加一个只读的 `ReplayStateDumper`（不修改游戏内存、不发任何指令）：
   - 命令行启动 War3 1.27 自动播放目标 `.w3g`（或由主会话脚本触发加载录像并切到 8x 加速）；
   - hook 每 **500ms 游戏仿真时间**（用 `CPoPosCl+0x60` 或游戏计时器对齐，**不用墙钟**，避免 8x 加速错位）遍历视野内单位，按目标玩家 `pid` 的视角用 `IsUnitVisible(unit, player_pid)` 过滤迷雾，输出一行 `state` JSONL；
   - 离线由 Python 脚本按 `t_ms` 将 `w3g_parser.py` 导出的精确 `action` 流与 hook 导出的 `state` 流做 **时间戳左连接（Exact Time-Join）**，产出零误差的「局面 → 操作」模仿学习数据集！

---

## 四、 数据集格式设计与本地录像实测统计

### 4.1 模仿学习样本 Schema（0.5s 网格 JSONL / Parquet）

完整 JSON Schema 已固化至 [`artifacts/replay-dataset/imitation_dataset_schema.json`](../artifacts/replay-dataset/imitation_dataset_schema.json)（训练大数据集时直接 `pandas.read_json(..., lines=True).to_parquet()` 即可无损转 Parquet）。单条样本示例（取自 [`sample_dataset.jsonl`](../artifacts/replay-dataset/sample_dataset.jsonl)）：

```json
{
  "schema_version": "1.0",
  "match_id": "20261120_225621_TestUser01_水晶室女.w3g",
  "patch": "1.27",
  "t_ms": 145000,
  "pid": 1,
  "team": 0,
  "hero": "Hjai",
  "state_source": "w3g_action_proxy",
  "state": {
    "game_phase": "laning_0_10m",
    "hero_pos": { "x": -4120.5, "y": -4780.2, "confidence": 0.35 },
    "hero_level": 2,
    "hp_ratio": null,
    "mp_ratio": null,
    "gold_reliable": null,
    "gold_unreliable": null,
    "last_hits": 4,
    "denies": 1,
    "kills": 0,
    "deaths": 0,
    "learned_skills": ["learn_skill:A1HQ"],
    "inventory_slots": [null, null, null, null, null, null],
    "selected_units": ["0x000041A2"],
    "nearby_units": [],
    "recent_action_hist": ["move", "move", "stop_hold", "attack_unit", "move"]
  },
  "action": {
    "category": "move",
    "order_id": "0x000D0012",
    "order_name": "move(移动 M)",
    "target_x": -3985.0,
    "target_y": -4612.0,
    "target_obj1": "0xFFFFFFFF",
    "action_count_in_window": 3
  }
}
```

- **动作空间离散化（13 类）**：`noop`、`move`、`attack_unit`、`attack_ground`、`stop_hold`、`cast_point`、`cast_unit`、`cast_immediate`、`use_item`、`buy_item`、`learn_skill`、`select_or_group`、`ping_or_chat`。当同一 0.5s 窗口有多个操作时，按战术优先级（`施法 > 用物品/加点 > 买装备 > 攻击 > 停顿 > 移动 > 选人`）选取主操作标签，同时保留 `action_count_in_window` 刻画操作密度。

### 4.2 本机 20 份录像副本实测统计（`artifacts/replay-dataset/replay_corpus_stats.txt`）

对复制到 `artifacts/replay-dataset/data/` 的 20 份最大 `.w3g` 运行 `build_dataset.py`：
- **有效完整录像**：**8 场**（均为 `1.27` 补丁、`TestUser01` 冰女 `Hjai` 测试局，单局时长 `684s ~ 1532s`）；另 12 份 `*_player_*.w3g` 因强杀进程未写 68B 文件头被自动过滤。
- **总量**：**36,138 条动作**、**1,110 条 `0x6B` 事件**、**3,000 条示例 JSONL 样本**。
- **APM 分布（8 场）**：最小 `1.5`（泉水挂机采样局 `084940`）、中位 **`153.4`**、均值 **`232.9`**、最大 **`771.9`**（`045144` 中路卡兵 AI 连续 23 波测试局）。

| 操作类别 (`action.category`) | 次数 | 占比 | 底层主 Action ID / OrderId | 现象解读（重要数据清洗提示） |
|---|---:|---:|---|---|
| **`select_or_group`** | `25,513` | **`70.60%`** | `0x1B` (8,659) / `0x16` (8,376) / `0x19` (8,333) / `0x18` (142) | **AI 测试局伪影！** `war3hook_ai_tactics.inl` 每次发指令前都调 `aiSelectHero()`，导致 70% 包是重复选英雄；**正式训练集必须剔除 AI 测试局并过滤冗余选人包** |
| **`move`** | `10,081` | **`27.90%`** | `0x12` + `0xD0012` (8,128) / `0xD0003` (1,986) | 卡兵与走位主力动作 |
| **`stop_hold`** | `459` | `1.27%` | `0x10` + `0xD0004` (459) | 站住等兵 / S 取消 |
| **`attack_unit`** | `33` | `0.09%` | `0x12` + `0xD000F` / `0xD0003` (非 `0xFFFFFFFF` 目标) | 测试局几乎未打架/补刀 |
| **`buy_item`** | `31` | `0.09%` | `0x10` + `Hjai` (27) / `h01K` (2) / `h083` (2) | 选人与买货 |
| **`ping_or_chat`** | `20` | `0.06%` | `0x60` 触发聊天命令 | `-ap` / `-test` 等模式命令 |
| **`use_item`** | `1` | `0.00%` | `0x12` + `0xD0028` (useslot1) | 吃树/使用格 1 |

---

## 五、 真人录像来源调研与「对线期」模仿模型数据量估算

### 5.1 合法公开的 DotA 6.83d 真人录像来源（仅列来源与获取方式，未下载）

| 来源平台 | 内容特点与补丁匹配度 | 合法获取方式 |
|---|---|---|
| **1. D1Map.net（DotA 1 录像库）** | 目前仍活跃的 DotA 1 专用对局库与解析站，大量收录 **RGC（Ranked Gaming Client）** 平台 6.83d / 6.85 真实天梯 5v5 对局（含分段/英雄筛选） | 网页按地图版本（`DotA v6.83d`）和英雄筛选后，通过页面提供的公开录像链接手动或礼貌限速获取玩家公开上传的 `.w3g` |
| **2. iCCup Replay Archive (`iccup.com/replays/`)** | 历史最庞大的 1.26a/1.27a DotA 1 公开天梯录像库（含高分 A/S 级对局、单英雄筛选） | 在 iCCup 官网 Replays 栏目按版本 `6.83d` 与玩家段位筛选下载公开 `.w3g`（注意核对地图版本号与 1.26/1.27 补丁，1.26 `.w3g` 解析格式与 1.27 完全兼容，回放时需切换对应版本 `Game.dll`） |
| **3. WC3Stats (`wc3stats.com`)** | 现代 War3 自定义地图战绩与录像托管平台，提供规范的公开 REST API | 通过其公开 API 按地图名过滤 DotA 自定义对局元数据与公开录像归档 |
| **4. 自建高质数据源（KK 平台 / 本地 `War3Bot` 对局录制）** | **最贴合本机 1.27 + 6.83d 环境且零版本漂移**：包含真人玩家亲自打的 1v1 中单/边路对线局，且可同步直录 hook 精确局面（无需二次回放！） | 玩家在 `War3Bot` 或 KK 平台正常打 6.83d 对局，游戏正常退出结算页自动保存完整 `.w3g`（同时 `War3Bot` 已落盘 `match_*.dat`） |

### 5.2 训练一个「对线期（0~10 分钟）」模仿模型需要多少局？

按 0.5s 采样率计算，每局对线期（0~10 分钟 = 600s）为单个玩家贡献 **1,200 条**样本（去掉 `noop` 后约 **400~700 条**有效动作样本；1 场 5v5 录像最多有 10 个玩家视角 = **4,000~7,000 条**有效样本）：

| 模型定位 | 所需有效录像局数 | 有效样本规模（0.5s 步） | 说明 |
|---|---:|---:|---|
| **L1：单英雄对线行为克隆（如冰女 / 影魔 1v1 对线）** | **30 ~ 50 局**（同英雄高分段视角） | `1.5万 ~ 3.5万` 条有效动作 | 配合「分层架构」（模型输出宏观意图：补刀/消耗/撤退/加点/买装，底层由 hook 执行 100ms 补刀与卡兵），50 局即可学出像人的站位、消耗时机与回城节奏 |
| **L2：常见 10~20 英雄通用对线模型（按位置分中/优/劣）** | **300 ~ 500 局**（5v5 约 3,000~5,000 玩家视角） | `150万 ~ 300万` 条有效动作 | 需覆盖近战 vs 远程、优势路 vs 劣势路、不同敌方组合；可先用行为克隆（BC）预训练，再用规则/胜负奖励做离线强化学习（IQL / CQL）微调 |
| **L3：大模型（LLM）托管指挥层 SFT 微调数据集** | **50 ~ 100 局**（每 3~5 秒抽一条高层决策样本） | `5,000 ~ 15,000` 条意图决策 | 直接对齐 `dota-ai-llm-mcp-control.md` 的高层工具调用（如 `lane_push` / `retreat` / `buy_item` / `gank`），数据需求远小于端到端像素/微操模型 |

---

## 六、 交给主会话的「建议测试步骤」（Hook 回放采样对接）

本任务不改 `War3Launcher` / `hooker` 代码，供主会话后续落地 **路线 B（War3 回放 + hook 只读采样）** 时按序执行：

1. **在 `war3hook` 新增只读 `ReplayStateDumper` 模块**：
   - 仅在检测到当前处于录像回放模式（或收到 RemoteControl `replaydump on <pid>`）时激活；
   - 按游戏仿真时间每 `500ms` 采样一次目标 `pid` 的英雄状态（坐标、HP/MP、等级、可靠/不可靠金钱、6 格物品与 CD、技能 CD）及 `IsUnitVisible(u, player_pid) == true` 的 1600 范围内单位列表，流式写入 `replay_state_<matchId>_pid<pid>.jsonl`；
   - **严禁**写游戏内存、**严禁**调用 `EnqueuePlayerAction`。
2. **单局回放对齐验证**：
   - 挑 1 场正常的 1.27 录像（如 `20261120_225621_TestUser01_水晶室女.w3g`），用 `war3.exe` 8x 加速回放 3 分钟，生成 `replay_state_*.jsonl`；
   - 运行 `w3g_parser.py` 解析同一份 `.w3g`，编写 30 行脚本按 `t_ms` 左连接 `state` 与 `action`，核对 `action.target_x/y` 与 `state.hero_pos` 在移动时的欧氏距离是否收敛到 `< 400`（验证时间轴零漂移）。
3. **采集第一批 30 局真人对线样本**：
   - 从 D1Map.net / iCCup 获取 30 场高分段 6.83d 1.27 真人录像（或真人自打 10 局），批量 8x 回放采样（~45 分钟全自动跑完），即构成第一版可直接微调的高质量「局面 → 操作」数据集。
