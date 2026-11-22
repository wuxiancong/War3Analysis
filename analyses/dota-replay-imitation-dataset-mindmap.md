# War3 1.27 录像解析与「局面 → 操作」模仿学习数据集思维导图

| 字段 | 内容 |
|---|---|
| **分析模型** | Gemini 4 Neon (Medium) |
| **分析目的** | 以思维导图呈现 War3 1.27 `.w3g` 二进制格式、解析器架构、三条局面补齐路线对比、0.5s JSONL 数据集 Schema、本地统计与真人录像来源 |
| **命名方式** | `dota-replay-imitation-dataset-mindmap` |
| **分析时间** | 2026-11-21 |
| **关联正文** | [dota-replay-imitation-dataset.md](file:///D:/Qt/workspace/War3Analysis/analyses/dota-replay-imitation-dataset.md) |

```mermaid
flowchart LR
    Root["War3 1.27 .w3g 解析与<br/>「局面 -> 操作」模仿学习数据集"]

    %% 1. w3g 格式
    Root --> Fmt["一、War3 1.27 .w3g 格式"]
    Fmt --> Hdr["1. 物理封装<br/>• 68B 头 (ver=1, patch=27, duration_ms)<br/>• 8B 块头 zlib 流 (decompressobj 逐块解压)<br/>• 坑点: 强杀进程产生 68B 全零未封口文件"]
    Fmt --> Blocks["2. 流结构<br/>• 启动元数据: 玩家表 + odd-byte 地图串 + 0x19 槽位表<br/>• 0x1F/0x1E TimeSlot (time_ms += time_inc)<br/>• 0x20 聊天块 / 0x17 退局块"]
    Fmt --> Acts["3. DotA 常用 Action ID 与 OrderId<br/>• 0x10(14B): stop(0xD0004)/hold(0xD0019)/加点FourCC/买货<br/>• 0x11(22B): 点地施法/A地板(0xD000F)/移动(0xD0012)<br/>• 0x12(30B): 右键smart(0xD0003)/指向技能/用物品(0xD0028..2D)<br/>• 0x13(38B) 丢物品 / 0x14(43B) 双目标<br/>• 0x16/17/18/19/1A: 选人/编队/切子组(识别英雄FourCC)<br/>• 0x60 触发聊天 / 0x66 加点菜单 / 0x68 Ping<br/>• 0x6B GameCache: CSK/CSD/Level/Hero/Tower/Winner"]

    %% 2. Python 解析器
    Root --> Parser["二、纯 Python 解析器<br/>(artifacts/replay-dataset/w3g_parser.py)"]
    Parser --> POut["输出内容<br/>• 玩家动作流 (t_ms, order_name, x/y, target, 当前选中单位)<br/>• 0x6B + 聊天事件流 (升级/补刀/击杀/推塔/胜负)<br/>• 自动推断玩家英雄 (0x10 选人 + 0x19 子组 + 0x6B 终局)"]

    %% 3. 局面补齐三条路线
    Root --> State["三、「局面」怎么补 (三条路线对比)"]
    State --> RouteA["路线 A: 仅动作目标点近似<br/>• 成本极低，但无血蓝/小兵/敌人坐标<br/>• 仅适合加点/出装/宏观分路冷启动"]
    State --> RouteB["路线 B: War3 8x 回放 + hook 只读采样 (强烈推荐 ✅)<br/>• 100% 引擎精确坐标/HP/MP/金钱/CD + IsUnitVisible 防透视<br/>• 10 分钟对线期 8x 回放仅需 ~1.5 分钟/局<br/>• 离线按仿真时间 t_ms 左连接 state 与 w3g action"]
    State --> RouteC["路线 C: 网页模拟器重放<br/>• 缺 32Hz 寻路与 9 万行 JASS，几秒发散，不推荐"]

    %% 4. 数据集格式与本地统计
    Root --> DS["四、0.5s 模仿学习数据集与本地实测"]
    DS --> Schema["1. Schema (imitation_dataset_schema.json)<br/>• JSONL (可无损转 Parquet)，每 0.5s 一条 state -> action<br/>• 13 类离散动作 + 坐标/目标参数 + 窗口操作数"]
    DS --> LocalStats["2. 本地 20 份录像实测 (8 场完整 1.27 有效)<br/>• 共 36,138 动作 / 1,110 条 0x6B / 3,000 条示例 JSONL<br/>• 活跃 APM 中位 153.4 (最高 771.9)<br/>• 关键清洗警示: AI 测试局 aiSelectHero() 导致<br/>  select_or_group 占 70.60%，正式训练必须过滤 AI 局"]

    %% 5. 真人录像来源与数据量
    Root --> Src["五、合法真人录像来源与数据量估算"]
    Src --> Sites["公开来源 (不下载，仅调研)<br/>• D1Map.net (RGC 活跃 DotA 1 库)<br/>• iCCup Replay Archive (1.26/1.27 历史高分局)<br/>• WC3Stats (公开 API)<br/>• KK 平台 / 本机 War3Bot 自录局 (零版本漂移)"]
    Src --> Vol["对线期 (0~10m) 所需数据量<br/>• 单英雄分层 BC: 30~50 局 (1.5万~3.5万条有效动作)<br/>• 10~20 英雄通用对线: 300~500 局 (150万~300万条)<br/>• 大模型指挥层 SFT: 50~100 局 (5千~1.5万条高层意图)"]
```
