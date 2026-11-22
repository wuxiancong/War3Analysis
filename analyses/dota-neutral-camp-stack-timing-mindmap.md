# 囤野时机 — 思维导图

```text
dota-neutral-camp-stack-timing
├─ 两套几何（勿混）
│  ├─ 封野盒 AABB …… 脚本 P3O / 已有 spawn-box 文档
│  └─ 守卫拴绳 圆 …… GuardDistance / MaxGuardDistance
├─ DotA 常数 war3mapMisc
│  ├─ GuardDistance = 600
│  ├─ MaxGuardDistance = 600  → 软硬重合，>600 立刻回巢
│  ├─ GuardReturnTime = 3    → 软区间宽度 0，基本用不上
│  └─ CreepCampPathingCellDistance=26 → 仅小地图/AI 聚类（832）
├─ 引擎 game.dll
│  ├─ SetUnitCreepGuard
│  │  ├─ 1.26 RVA 0x3C5480 / 1.27 0x1F7450
│  │  └─ CUnit+0x60 bit 0x04
│  ├─ 守卫点
│  │  ├─ CreateUnit 最终落点写入
│  │  └─ +0x2AC / +0x2B4 代理 ID 对（中高置信）
│  ├─ 追击 → dist>Max → 回巢 Move（不传送）
│  ├─ 回巢：不索敌、不报复；regenHP 回血非满血
│  └─ RemoveGuard* = 电脑 AI 岗哨 ≠ 中立拴绳
├─ 野怪属性（patch SLK）
│  ├─ 多数最慢 spd 270；半人马/熊怪 300～350
│  ├─ 远程 range 500～600 → 边走边打拖慢出盒
│  └─ acquire 多 500（UnitWeapons）
├─ 时机模型
│  ├─ 理论 (exit/spd) …… :57～:58
│  ├─ 实用 (绕树+停火) …… :54～:57
│  ├─ AI 安全 (=经验) …… :50～:53（:51 最佳）
│  └─ 4+ 波拥堵 …… 再提前 ~2s → :49
├─ 12 点表（AI）
│  ├─ 多数 :50～:51 + 方向 E/W/N/S
│  ├─ 营6 北缘80 → 可 :53
│  ├─ 营5/9/10 勿朝 >600 边拉
│  └─ JSON → stackSecond / pullDir
├─ 囤成功判定
│  ├─ xx:00 CreateUnit 中立钩子 + 旧野在盒外
│  ├─ 或 GamePlaying 下枚举 check 空再数新单位
│  └─ 禁止读图阶段调 JASS
└─ 验证
   ├─ 冰女 Hjai 实拉 1/6/8/10
   └─ 本局 Launcher idle，待开局补测
```

## 关键边

| 从 | 到 | 关系 |
| :--- | :--- | :--- |
| MaxGuardDistance=600 | 出盒方向 | 边距 >600 的方向拉不出去（会先回家） |
| 远程野 | 实用秒 | 停火 → 必须比理论更早出手 |
| 封野盒 | 囤成功 | xx:00 check 内无占用单位才刷 |
| SetUnitCreepGuard bit | AI | 只读可判断是否仍受拴绳策略约束 |
