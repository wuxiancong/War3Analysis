# DotA 6.83d 全英雄控制/大招威胁先验表

- 英雄数: 112
- 生成脚本: `artifacts/teamfight-key-target/build_control_threat_table.py`
- 结构化数据: `hero_control_threat_683d.json`

| 英雄 | FourCC | controlPrior | 关键技能（tier/weight） |
| :--- | :---: | :---: | :--- |
| 半人猛犸 | `UC11` | 1.00 | 震荡波(`A02S` SOFT_CC 0.35); 两极反转(`A29L` TEAM_ULT 1.0) |
| 娜迦海妖 | `HC49` | 1.00 | 诱捕(`A24D` HARD_CC 0.7); 海妖之歌(`A07U` TEAM_ULT 1.0) |
| 撼地神牛 | `Otch` | 1.00 | 沟壑(`A0SK` HARD_CC 0.85); 回音击(`A0DH` TEAM_ULT 1.0) |
| 水晶室女 | `Hjai` | 1.00 | 冰封禁制(`A04C` HARD_CC 0.75); 极寒领域(`A03R` TEAM_ULT 1.0) |
| 潮汐猎人 | `Ofar` | 1.00 | 毁灭(`A29I` TEAM_ULT 1.0) |
| 虚空假面 | `EC45` | 1.00 | 时间结界(`A0J1` TEAM_ULT 1.0) |
| 谜团 | `Uktl` | 1.00 | 黑洞(`A1BX` TEAM_ULT 1.0) |
| 仙女龙 | `N00B` | 0.95 | 新月之痕(`A0SC` HARD_CC 0.75); 梦境缠绕(`A0S8` TEAM_ULT 0.95) |
| 兽王 | `H00D` | 0.95 | 原始咆哮(`A0O2` TEAM_ULT 0.95) |
| 军团指挥官 | `E02K` | 0.95 | 决斗(`A2CI` TEAM_ULT 0.95) |
| 凤凰 | `E02F` | 0.95 | 超新星(`A1RK` TEAM_ULT 0.95) |
| 发条地精 | `H00T` | 0.95 | 弹幕冲击(`A0Z4` HARD_CC 0.7); 能量齿轮(`A0Z5` HARD_CC 0.7); 发射钩爪(`A0Z8` TEAM_ULT 0.95) |
| 寒冬飞龙 | `N0M7` | 0.95 | 寒冬诅咒(`A0Z0` TEAM_ULT 0.95) |
| 干扰者 | `E02J` | 0.95 | 动能力场(`A1SU` HARD_CC 0.7); 静态风暴(`A1U6` TEAM_ULT 0.95) |
| 末日使者 | `UC42` | 0.95 | 末日(`A0MU` TEAM_ULT 0.95) |
| 沉默术士 | `N01A` | 0.95 | 全领域静默(`A0L3` TEAM_ULT 0.95) |
| 祸乱之源 | `Oshd` | 0.95 | 恶魔的掌握(`A02Q` TEAM_ULT 0.95) |
| 巨牙海民 | `E02I` | 0.90 | 雪球(`A1S7` HARD_CC 0.8); 海象神拳(`A1YQ` TEAM_ULT 0.9) |
| 恶魔巫师 | `UC18` | 0.90 | 穿刺(`A0X5` HARD_CC 0.8); 妖术(`A0MN` HARD_CC 0.9); 死亡一指(`A095` NUKE_ULT 0.45) |
| 暗影萨满 | `Orkn` | 0.90 | 苍穹震击(`A010` HARD_CC 0.7); 妖术(`A0RX` HARD_CC 0.9); 枷锁(`A00P` HARD_CC 0.85); 群蛇守卫(`A00H` TEAM_ULT 0.75) |
| 月之女祭司 | `N01V` | 0.90 | 月神之箭(`A0L8` HARD_CC 0.9); 月之暗面(`A0KU` NUKE_ULT 0.45) |
| 胖子 | `U00F` | 0.90 | 肉钩(`A06I` HARD_CC 0.9); 肢解(`A0FL` HARD_CC 0.85) |
| 舰队统帅 | `H06S` | 0.90 | 洪流(`A136` HARD_CC 0.8); 幽灵船(`A11K` TEAM_ULT 0.9) |
| 大地之灵 | `N0MU` | 0.85 | 磁化(`A2TI` TEAM_ULT 0.85) |
| 山岭巨人 | `Ucrl` | 0.85 | 山崩(`A0LL` HARD_CC 0.85); 投掷(`A0BZ` HARD_CC 0.75); 长大！(`A0CY` NUKE_ULT 0.45) |
| 灵魂守卫 | `Eevi` | 0.85 | 灵魂隔断(`A07Q` HARD_CC 0.85) |
| 熊猫酒仙 | `Npbm` | 0.85 | 雷霆一击(`A06M` HARD_CC 0.8); 元素分离(`A0MQ` TEAM_ULT 0.85) |
| 蝙蝠骑士 | `O016` | 0.85 | 燃烧枷锁(`A19O` HARD_CC 0.85) |
| 风行者 | `N0EG` | 0.85 | 束缚击(`A12J` HARD_CC 0.85); 集中火力(`A12P` NUKE_ULT 0.7) |
| 半人马酋长 | `H000` | 0.80 | 马蹄践踏(`A00S` HARD_CC 0.8); 奔袭冲撞(`A2O6` TEAM_ULT 0.8) |
| 双头龙 | `E00P` | 0.80 | 冰封路径(`A0O6` HARD_CC 0.8); 烈焰焚身(`A0O5` NUKE_ULT 0.45) |
| 地穴刺客 | `U000` | 0.80 | 穿刺(`A0X7` HARD_CC 0.8); 仇杀(`A09U` NUKE_ULT 0.45) |
| 沙王 | `U00K` | 0.80 | 掘地穿刺(`A06O` HARD_CC 0.8); 地震(`A06R` NUKE_ULT 0.45) |
| 牛头人酋长 | `O015` | 0.80 | 回音重踏(`A1AA` HARD_CC 0.8); 裂地者(`A1A1` TEAM_ULT 0.8) |
| 祈求者 | `H00U` | 0.80 | 元素祈唤(`A21Y` NUKE_ULT 0.45); 急速冷却(`A0VZ` HARD_CC 0.7); 幽灵漫步(`A0XL` INIT 0.4); 寒冰之墙(`A0VP` SOFT_CC 0.5); 电磁脉冲(`A0VS` SOFT_CC 0.55); 强袭飓风(`A0VK` HARD_CC 0.8) |
| 秀逗魔导士 | `H004` | 0.80 | 光击阵(`A027` HARD_CC 0.8); 神灭斩(`A01P` NUKE_ULT 0.75) |
| 黑暗聆者 | `H00N` | 0.80 | 真空(`A0QE` HARD_CC 0.8); 复制之墙(`A0QK` NUKE_ULT 0.45) |
| 大魔导师 | `E02X` | 0.75 | 隔空取物(`A27F` HARD_CC 0.75); 技能窃取(`A27H` NUKE_ULT 0.45) |
| 食人魔魔法师 | `Hmkg` | 0.75 | 火焰爆轰(`A04W` HARD_CC 0.75); 多重施法(`A088` NUKE_ULT 0.45) |
| 黑曜毁灭者 | `U00P` | 0.75 | 星体禁锢(`A0OJ` HARD_CC 0.75); 神智之蚀(`A0OK` NUKE_ULT 0.45) |
| 龙骑士 | `Hlgr` | 0.75 | 神龙摆尾(`A2AI` HARD_CC 0.75); 真龙形态(`A03G` NUKE_ULT 0.45) |
| 全能骑士 | `Harf` | 0.70 | 守护天使(`A0ER` TEAM_ULT 0.7) |
| 地卜师 | `H00I` | 0.70 | 地之束缚(`A0NB` HARD_CC 0.7); 分则能成(`A0MW` NUKE_ULT 0.45) |
| 复仇之魂 | `Hvwd` | 0.70 | 魔法箭(`A02A` HARD_CC 0.7); 恐怖波动(`A17O` SOFT_CC 0.35); 移形换位(`A0IN` NUKE_ULT 0.45) |
| 幻影长矛手 | `Ogrh` | 0.70 | 幻影冲锋(`A0YK` HARD_CC 0.7); 并列(`A0DB` NUKE_ULT 0.45) |
| 流浪剑客 | `H001` | 0.70 | 风暴之锤(`A190` HARD_CC 0.7); 神之力量(`A1WH` NUKE_ULT 0.45) |
| 炼金术士 | `N01I` | 0.70 | 不稳定化合物(`A1NI` HARD_CC 0.7); 化学狂暴(`ANcr` NUKE_ULT 0.45) |
| 修补匠 | `Ntin` | 0.60 | 再装填(`A065` SOFT_CC 0.6) |
| 卓尔游侠 | `Nbrn` | 0.60 | 阵风(`A2WF` SOFT_CC 0.6); 射手天赋(`A0VC` NUKE_ULT 0.45) |
| 暗夜魔王 | `Udre` | 0.60 | 伤残恐惧(`A08E` SOFT_CC 0.6); 夜幕降临(`A03K` NUKE_ULT 0.45) |
| 死亡先知 | `UC76` | 0.60 | 沉默魔法(`A0P6` SOFT_CC 0.6); 驱使恶灵(`A073` NUKE_ULT 0.45) |
| 先知 | `Emns` | 0.55 | 发芽(`A21E` HARD_CC 0.55); 自然之怒(`A1W8` NUKE_ULT 0.7) |
| 圣骑士 | `H00A` | 0.55 | 上帝之手(`A0LT` SOFT_CC 0.55) |
| 主宰 | `Nbbc` | 0.50 | 剑刃风暴(`A05G` SOFT_CC 0.5); 无敌斩(`A0M1` NUKE_ULT 0.8) |
| 钢背兽 | `H008` | 0.45 | 粘稠鼻液(`A0FW` SOFT_CC 0.3); 刺针扫射(`A0GP` NUKE 0.4); 战意(`A0FV` SOFT_CC 0.45) |
| 巫妖 | `Ulic` | 0.35 | 霜冻新星(`A07F` SOFT_CC 0.35); 连环霜冻(`A05T` NUKE_ULT 0.45) |
| 赏金猎人 | `Naka` | 0.35 | 投掷飞镖(`A004` SOFT_CC 0.35); 追踪术(`A0B4` NUKE_ULT 0.45) |
| 不朽尸王 | `H00R` | 0.00 | 血肉傀儡(`A15J` NUKE_ULT 0.45) |
| 光之守卫 | `Hblm` | 0.00 | 灵魂形态(`A2XQ` NUKE_ULT 0.45) |
| 剧毒术士 | `EC57` | 0.00 | 剧毒新星(`A013` NUKE_ULT 0.45) |
| 受折磨的灵魂 | `Ekee` | 0.00 | 脉冲新星(`A21F` NUKE_ULT 0.45) |
| 变体精灵 | `O00P` | 0.00 | 波浪形态(`A0FN` INIT 0.45); 复制(`A0G8` NUKE_ULT 0.45) |
| 嗜血狂魔 | `Hvsh` | 0.00 | 割裂(`A0LH` NUKE_ULT 0.45) |
| 噬魂鬼 | `U00C` | 0.00 | 感染(`A0SW` NUKE_ULT 0.45) |
| 圣堂刺客 | `E01Y` | 0.00 | 灵能陷阱(`A0RP` NUKE_ULT 0.45) |
| 地狱领主 | `Udea` | 0.00 | 回光返照(`A0NS` NUKE_ULT 0.45) |
| 地穴编织者 | `Ubal` | 0.00 | 时光倒流(`A0CT` NUKE_ULT 0.45) |
| 地精工程师 | `H00K` | 0.00 | 遥控炸弹(`A0AK` NUKE_ULT 0.45) |
| 地精撕裂者 | `E032` | 0.00 | 锯齿飞轮(`A2E5` NUKE_ULT 0.45) |
| 天怒法师 | `H0DO` | 0.00 | 神秘之耀(`A2BG` NUKE_ULT 0.45) |
| 奥林匹斯之王 | `Hmbr` | 0.00 | 雷神之怒(`A29G` NUKE_ULT 0.55) |
| 守护精灵 | `O01F` | 0.00 | 重定位(`A1TB` NUKE_ULT 0.45) |
| 巨魔战将 | `N016` | 0.00 | 战斗专注(`A1EJ` NUKE_ULT 0.45) |
| 巫医 | `E01A` | 0.00 | 死亡守卫(`A0NT` NUKE_ULT 0.45) |
| 幻影刺客 | `Ewar` | 0.00 | 恩赐解脱(`A03Q` NUKE_ULT 0.45) |
| 幽鬼 | `E01B` | 0.00 | 鬼影重重(`A0H9` NUKE_ULT 0.45) |
| 弧光守卫者 | `N0MK` | 0.00 | 风暴双雄(`A2M0` NUKE_ULT 0.45) |
| 影魔 | `Nfir` | 0.00 | 毁灭阴影(`A0EY` NUKE 0.35); 魂之挽歌(`A29J` NUKE_ULT 0.9) |
| 德鲁伊 | `N01O` | 0.00 | 真实形态(`A0AG` NUKE_ULT 0.45) |
| 敌法师 | `Edem` | 0.00 | 闪烁(`AEbl` INIT 0.45); 法力虚空(`A2WE` NUKE_ULT 0.8) |
| 斧王 | `Opgh` | 0.00 | 淘汰之刃(`A0E2` NUKE_ULT 0.45) |
| 暗影恶魔 | `E02H` | 0.00 | 邪恶净化(`A2XI` NUKE_ULT 0.45) |
| 暗影牧师 | `N01W` | 0.00 | 编织(`A10Q` NUKE_ULT 0.45) |
| 月之骑士 | `E005` | 0.00 | 月蚀(`A054` NUKE_ULT 0.75) |
| 术士 | `E01C` | 0.00 | 混乱之雨(`S008` NUKE_ULT 0.45) |
| 树精卫士 | `Hamg` | 0.00 | 疯狂生长(`A07Z` NUKE_ULT 0.45) |
| 死灵法师 | `U00E` | 0.00 | 死神镰刀(`A067` NUKE_ULT 0.45) |
| 死灵飞龙 | `UC60` | 0.00 | 召唤佣兽(`A1NE` NUKE_ULT 0.45) |
| 深渊领主 | `N00R` | 0.00 | 黑暗之门(`A0R0` NUKE_ULT 0.45) |
| 混沌骑士 | `U00A` | 0.00 | 幻象(`A03O` NUKE_ULT 0.45) |
| 湮灭法师 | `H00H` | 0.00 | 生命汲取(`A0CC` NUKE_ULT 0.45) |
| 灰烬之灵 | `N0M0` | 0.00 | 火之余烬(`A2JK` NUKE_ULT 0.45) |
| 熊战士 | `Huth` | 0.00 | 激怒(`A0LC` NUKE_ULT 0.65) |
| 狼人 | `U008` | 0.00 | 变狼(`A093` NUKE_ULT 0.45) |
| 痛苦女王 | `UC01` | 0.00 | 闪烁(`A0ME` INIT 0.45); 超声冲击波(`A306` NUKE_ULT 0.75) |
| 矮人狙击手 | `Usyl` | 0.00 | 暗杀(`A04P` NUKE_ULT 0.7) |
| 矮人直升机 | `E02N` | 0.00 | 召唤飞弹(`A1T5` NUKE_ULT 0.75) |
| 神灵武士 | `H00Q` | 0.00 | 牺牲(`A0QR` NUKE_ULT 0.45) |
| 神谕者 | `N0MD` | 0.00 | 虚妄诺言(`A2TF` NUKE_ULT 0.45) |
| 育母蜘蛛 | `U006` | 0.00 | 极度饥渴(`A0WQ` NUKE_ULT 0.45) |
| 蛇发女妖 | `H00V` | 0.00 | 石化凝视(`A1AT` NUKE_ULT 0.45) |
| 蝮蛇 | `EC77` | 0.00 | 蝮蛇突袭(`A080` NUKE_ULT 0.45) |
| 裂魂人 | `O00J` | 0.00 | 幽冥一击(`A0G4` NUKE_ULT 0.45) |
| 远古冰魂 | `N0HP` | 0.00 | 冰晶爆轰(`A1MI` NUKE_ULT 0.45) |
| 闪电幽魂 | `E002` | 0.00 | 风暴之眼(`A1AO` NUKE_ULT 0.45) |
| 隐形刺客 | `HC92` | 0.00 | 闪烁突袭(`A0K9` INIT 0.45) |
| 风暴之灵 | `H00S` | 0.00 | 残影(`A14P` INIT 0.45); 球状闪电(`A14O` INIT 0.45) |
| 骷髅射手 | `E004` | 0.00 | 死亡契约(`A04Q` NUKE_ULT 0.45) |
| 骷髅王 | `NC00` | 0.00 | 重生(`A01Y` NUKE_ULT 0.45) |
| 魅惑魔女 | `Emoo` | 0.00 | 推进(`A0DY` NUKE_ULT 0.45) |
| 鱼人夜行者 | `H071` | 0.00 | 暗影之舞(`A1IN` NUKE_ULT 0.45) |
| 鱼人守卫 | `UC91` | 0.00 | 伤害加深(`A034` NUKE_ULT 0.45) |

未匹配到任何控制/大招关键词的英雄数: 0
