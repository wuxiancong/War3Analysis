# Warcraft III 单位移动字段 — 思维导图

| 字段 | 内容 |
| :--- | :--- |
| **分析模型** | Grok 4.7 |
| **分析目的** | 把单位坐标、朝向、移速、指令目标点的读取路径收成一张图，并标出碰撞和寻路折线还没找到 |
| **命名方式** | `war3-unit-movement-fields-mindmap`；正文 [`war3-unit-movement-fields.md`](./war3-unit-movement-fields.md) |
| **分析时间** | 2026-11-20 |

```mermaid
mindmap
  root((单位移动字段))
    句柄到 CUnit
      aiFindAgentInRing 是 8192 缓存
        冲掉后不能当唯一来源
        存的是 CUnit 不是代理表节点
      JassHandleToUnit 才是权威入口
        1.26 0x3BDCB0
        1.27 0x1D1550
        只在游戏线程且 GamePlaying
      代理表
        1.26 查找 0x3FA30 全局 RVA 0xAB7788
        1.27 查找 0x37350 全局 RVA 0xBE40A8
        节点加 0x0C 必须是 0x2B61676C
        节点加 0x20 为 0 才活着
        ResolveAgent 取节点加 0x54
    CUnit 直接字段
      加 0x0C 和 0x10 网络 ID
      加 0x30 四字码
      加 0x164 内嵌位置对象
        vtable 加 0xB8 是 lea ecx 加 164h
        11 个版本都有这 7 字节
        ID 对在单位加 0x16C 和 0x170
      加 0x19C 和 0x1A0 当前指令 ID 对
      加 0x1EC CAbilityMove
      加 0x1F0 英雄能力 默认移速走这里
      加 0x208 飞行高度 地面实测 0
      加 0x2CC 按类型固定 不是碰撞
    坐标和朝向
      GetUnitX Y 调 GetWidgetWorldPos
        1.26 0x4743A0
        1.27 0x03B720
      地图原点加 0x6C 和加 0x70 实测都是 -8192
      每人不同的原始分量在节点加 0x78 和 0x7C
      朝向弧度在节点加 0x90
      合成公式没用走动样本对过
    移速
      Amov 加 0x70 未减速时的速度
        esen edry ebal 实测 325
        Hjai 实测 280
      Amov 加 0x78 乘数 样本为 1
      Amov 加 0x7C 非 0 则原生返回 0
      非英雄基础移速是单位数据加 0x1D4
    指令
      COrder 加 0x24 是指令 ID
        实机攻击 0xD000F
      COrder 加 0x48 和 0x50 是目标点
        有过 -6005 和 5458 这种地图坐标
      目标单位槽未确认
      寻路折线和下一路径点未找到
    实机边界
      iCCup Game.dll 基址 0x6D8B0000
      虚表槽与 1.27 一致
      只读进程 没有调 JASS 原生
      1.0.17 到 1.21 只有特征字节 外壳没跟完
```
