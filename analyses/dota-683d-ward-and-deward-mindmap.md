# DotA 6.83d 插眼 / 排眼 — 思维导图

| 项 | 内容 |
| :--- | :--- |
| **分析模型** | Composer（Cursor Agent） |
| **分析目的** | 导图索引正文 [`dota-683d-ward-and-deward.md`](./dota-683d-ward-and-deward.md) |
| **命名方式** | `dota-683d-ward-and-deward-mindmap` |
| **分析时间** | 2026-11-21 |

```mermaid
mindmap
  root((插眼/排眼 6.83d))
    插眼
      物品
        I05G A2WH 假眼 420码 7min
        I05H A2WI 真眼 500码 4min
        0x11点地 / 0x12递队友
        物品obj + flags 0x44
      单位
        o004 假眼 HP200 sight1600 A0XB
        oeye 真眼 Adt1=850TS A0XB
        BTLD 限时生命
      高地
        悬崖挡低看高
        树 occH 挡视线
        假眼上高台
      眼位库
        符点 G4 / LB
        肉山 KB / Z6
        中路 Y5
        blockcamp spawn×12
    排眼
      真视源
        真眼 850
        粉尘 1050/12s
        宝石 A14K 1100
      原生
        IsUnitDetected
        IsUnitInvisible
        IsUnitVisible
      game.dll
        helper 1.0.17 0x1BC710
        helper 1.21 0x1BF940
        helper 1.22 0x2797E0
        helper 1.26 0x27A320
        helper 1.27 0x66E3B0
        CUnit+0x130/134 全版同
        det+0x2C/74 per player
      推测
        敌0x11插眼点
        眼位停留进雾
      打掉
        0x12 attack 需可见
        QB A1FD +100
        HP200 不秒
    AI落地
      时机 开局/刷新/买到眼
      选点 评分+高台+封野
      流程 怀疑→S/粉→看见→A
      接口 ward place/deward scan
```

## 速查边

| 从 | 到 |
| :--- | :--- |
| 假眼 | `o004` / 1600 视野 / 7 min / 隐身 `A0XB` |
| 真眼 | `oeye` / `Adt1` 850 / 4 min / 隐身 `A0XB` |
| 粉尘 | `I0GH` `AItb` 1050×12s |
| 宝石 | `I04D` `A14K` 1100 |
| 侦测 helper | 1.0.17 `0x1BC710` · 1.21 `0x1BF940` · 1.22 `0x2797E0` · 1.24.4 `0x27AE40` · 1.26 `0x27A320` · 1.27 `0x66E3B0`（全表见正文） |
| 字段 | `CUnit+0x130/134` + det `+0x2C/+0x74`（1.0.17→1.27 同） |
| 封野 | spawn-box check 内 / tactics `blockcamp` |
| 打眼 | 可见后 `0xD000F`；QB +100 |
