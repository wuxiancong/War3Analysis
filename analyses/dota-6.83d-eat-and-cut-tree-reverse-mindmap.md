# DotA 6.83d 吃树与砍树逆向及 AI 接口 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Antigravity AI Agent |
| **分析目的** | 结构化呈现 DotA 6.83d 吃树/砍树地图脚本、`game.dll` 底层实现及 `War3Launcher` AI 接口链路 |
| **命名方式** | `dota-6.83d-eat-and-cut-tree-reverse-mindmap`；对外主指令 `-tree / -tree cut|eat|list` 与 `/tree cut|eat|list` |
| **分析时间** | 2026-11-19 |

```mermaid
mindmap
  root((DotA 6.83d 吃树与砍树))
    地图与脚本层
      吃树 Tango
        商店假单位 h02A 缩写 tango 125g
        背包可用码 I05C → Aeat 4层 0CD
        分享码 I0Q6 I0Q9 → A2VG 1层 60CD
        脚本 XGO→XFO→XEO 挂 A0PV B07L 16秒回115血
      砍树 Quelling Blade
        商店假单位 h07W h08F 缩写 qb 225g
        近战 I0HR / 远程 I0HP → 共用 A1FD Tree Chop
        Rng1 350 / Cool1 5s / 目标 tree ward
        MFO 仅对敌方守卫 o004 oeye 补100伤
      狂战斧 I099
        6.83d 无砍树能力
      树木集合与预放
        RJI 6种树 ATtr NTtw NTtc B002 B003 B005
        war3map.doo 预放 3675 棵树
        不走 JASS CreateDestructable
    War3 引擎层 game.dll
      CAbilityEatTree Aeat
        orderId 0xD00B2 eattree
        vtable +0x420 6F08B0E0 触发 SPELL_EFFECT
        调 CDestructable +0x124 杀树并播倒地动画
      网络动作包 0x12 31B
        CNetCommandUnitOrderTargetImage
        orderId useslot1..6 0xD0028+slot
        x y 为树世界坐标
        targetObj 为 CDestructable +0x0C / +0x10
        超距由 COrderTarget 自动寻路接近
      CDestructable 结构
        +0x30 typeId FourCC
        +0x64 life / +0x6C maxLife
        vtable +0x1C 类ID 0x2B773364
        vtable +0xB8 CWidgetPos + GetWidgetWorldPos
        vtable +0x12C 生命 / +0x13C 死亡标记
      只读树木扫描 全11版本
        EnumWidgetsInRect mask 0x04FB0000 ret 10h
        1.26 0x4693D0 / 1.27 0x02F3F0
        GetWidgetWorldPos ret 4
        1.26 0x4743A0 / 1.27 0x03B720
    War3Launcher AI 接口
      偏移表与 IPC
        war3hook_offsets.cpp 全11版 RVA
        SharedMemory.h DUMP_TREES EAT_TREE CUT_TREE
        AiTreeSelectMode NEAREST NEAR_POINT BY_OBJID
      Hook 实现 war3hook_ai
        aiScanTreesAround 主线程只读空间扫描
        aiReadInventory 补 GetItemCharges 读层数
        aiUseItemOnDestructable 发 0x12 useslot
        AI_ITEM_TANGO 0.3s / SHARED 60.2s / QUELLING 5.2s
      对外控制入口
        C++ Q_INVOKABLE dumpTrees eatTree cutTree
        War3Server command.cpp 与 command_groups.conf
        RemoteControl 与 PowerShell tree cut eat list
        游戏内与大厅聊天 -tree /tree cut eat list
        兼容别名 eattree tango cuttree quell chop
        裸 -trees 放行给 DotA -test 原生重生树木
```

