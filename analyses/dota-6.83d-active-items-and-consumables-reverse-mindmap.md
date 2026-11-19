# DotA 6.83d 吃大药、净化药水与全部主动物品逆向 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Antigravity AI Agent |
| **分析目的** | 结构化呈现 DotA 6.83d 吃大药、吃净化药水及全量主动物品的地图机制、引擎协议分类与 AI 命令设计 |
| **命名方式** | `dota-6.83d-active-items-and-consumables-reverse-mindmap`；主命令 `-use` / `-items` |
| **分析时间** | 2026-11-19 |

```mermaid
mindmap
  root((DotA 6.83d 主动物品逆向))
    核心统一原理
      协议统一入口
        GetItemSlotOrderId 读取 +0xAC + 0xD0028
        useslot1..6 0xD0028..0xD002D
      行为分支 GetOrderFlags +0x30C
        低位 0x1 无目标 15B Action 0x10
        低位 0x2 点地 23B Action 0x11
        低位 0x4 对象目标 31B Action 0x12
        低位 0x6 点地与目标双模式 真假眼
        高位 0x02000000 瞬发不打断动作
    吃大药与净化药水
      SLK 与引擎机制
        治疗药膏 I05F 技能 AIpr 基类 AIrg
        净化药水 I05D 技能 AIpl 基类 AIrg
        DotA 把 DataD1 改为 0 → 返回 0x00300004
        受击驱散 DataE1=1 满血满蓝可用 DataC1=3
        对比有水魔瓶 A0FO DataD1=1 → 0x00200001
      双击自施路径 N2O
        targs1 含 item 发 0x12 目标为空单位
        JASS 建马甲 e00E 加 A1WA 或 AIpr
        对自身发 order 852609 即 0xD0281
      AI 直接发包方式
        0x12 + useslot + 己方或队友 obj1 obj2
    重点装备对比实证
      跳刀 vs 隐刀 vs 推推
        跳刀 AEbl → 0x11 点地
        隐刀 AOwk → 0x10 瞬发 0x02000001
        推推 ANcl DataB1=1 → 0x12 单位
      切换假腿 vs 切换臂章
        同走 0x10 + JASS RemoveItem + FD1 原位换 FourCC
        假腿 NZO AEfk 0x00200001 三态敏力智轮转
        臂章 NJO AIam 0x02000001 瞬发不打断开关
      笛子 vs 梅肯
        AI 发包均是 0x10 + 0x00200001
        笛子 AEfk YTO 925码 50s防叠
        梅肯 AIda YYO 775码回250血 25s防叠
      赤红甲 vs 希瓦 vs BKB
        三者均走 0x10 无目标
        赤红甲 AEfk 0x00200001 YMO 775码
        希瓦 AIam 0x02000001 瞬发不打断
        BKB AHwe 0x00300001 YVO魔免 + NYO降级
    全量物品五分类
      A类 0x10 无目标
        瞬发不打断 相位 隐刀 护符 疯脸 希瓦 臂章
        常规增益回复 魔瓶 魔棒 魂戒 奶酪 粉 雾 梅肯 笛子 赤红 BKB 幻影斧 秘法 战鼓
        原位切换 假腿 臂章 王者 天鹰 辉耀 金箍棒
      B类 0x11 点地
        跳刀 纷争面纱 TP 飞鞋 血精石
      C类 0x12 对象目标
        英雄与单位 大药 小蓝 推推 骨灰 林肯 电锤 勋章 吹风 虚灵 散失 羊刀 紫怨 达贡 点金 支配
        树木可破坏物 吃树 分享吃树 补刀斧 → -tree
      D类 0x11+0x12 双模式
        侦察守卫假眼 A2WH / 岗哨守卫真眼 A2WI
      E类 非 useslot 操作
        moveslot 0x12 换格 / dropitem 0x11 0x12 丢递 / smart 拾取装瓶 / 0x10 0044 买装
    AI 命令区分设计
      职责正交四动词
        -buy 买装备
        -tree cut eat list 交互树木
        -items 查询 6 格 FourCC 充能 CD
        -use 槽位或简称 可选目标模式 参数
```
