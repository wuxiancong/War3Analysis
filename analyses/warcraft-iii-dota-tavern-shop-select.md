# DotA 选人阶段「选择商店/酒馆」触发链

## 结论

玩家在 AP/CM/XL/NM 选人阶段点击英雄酒馆（俗称商店货架），工程上已由 `sendTargetClickAction` 模拟：

1. 从 `allHeroIconSource[hero].tavernHandleId` 取酒馆 Jass 句柄（`setTavernHandleIdToHeroes` 在酒馆创建时绑定）
2. 经 `g_handleToAgentMap` 解出内存 Handle1/Handle2
3. 组玩家动作包并 `EnqueuePlayerAction`：
   - `0x1B 0x02` Deselect 当前单位
   - `0x1B 0x01` **Select 新酒馆**（核心）
   - `0x16` 选中集合更新
   - `0x1A 0x19` + 酒馆 FourCC（如 `n01B`）交互

Launcher 单击头像走 `MSG_TYPE_HERO_PICK_PREVIEW` → `g_needToExecuteHeroPreview` → 同上。

双击/确选另发 `sendHeroPickAction`（`0x10`），与「只选商店」不同。

## AI 命令约定

| 意图 | 命令 | 底层 |
| --- | --- | --- |
| 选酒馆 | `shop` / `tavern` | Preview → `0x1B Select` |
| 选英雄 | `pickhero`（兼容 `pick`） | Executed → 点击酒馆 + `0x10` |
| 随机 | `random` / `-random` | `0x60` ACTION |

缩写：`shared/DotaTavernAbbrev.h`（1–12）、`shared/DotaHeroAbbrev.h`（1–112）。

## 与物品商店的区别

本文「商店」= **选人酒馆**（`n01B` 等 12 座），不是边路/神秘物品店。物品店购买是另一套 `0x10` 单位码路径，不在此命令内。
