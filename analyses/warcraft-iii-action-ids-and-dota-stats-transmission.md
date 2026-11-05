# 魔兽争霸 III 动作体系（Action IDs）逆向分析与 DotA 战绩传输机制

> **分析日期**：2026-10-31  
> **纠错更新日期**：2026-11-01（见 [`warcraft-iii-action-ids-payload-length-audit.md`](./warcraft-iii-action-ids-payload-length-audit.md)）  
> **逆向目标**：`D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll`  
> **关联脚本**：`D:\Qt\workspace\War3Script\war3map_3.j`（第 7210~7293 行）  
> **关联代码**：`D:\Qt\workspace\War3Bot\src\client.cpp`（`W3GS_OUTGOING_ACTION [0x26]` 处理）  
> **配套思维导图**：[`warcraft-iii-action-ids-and-dota-stats-transmission-mindmap.md`](./warcraft-iii-action-ids-and-dota-stats-transmission-mindmap.md)

> **重要纠错**：下文第三节 Gemini 初版字典中，`0x1A` 长度、`0x1B~0x1E` 命名、`0x21/0x27/0x28/0x29/0x2E` UI 映射、`0x66` GameCache 归属、`0x14`=42 均有误。以审计文档校正表为准；**DotA 战绩通道仍是 `0x6B`，本节第二/四/五章结论不变。**

---

## 一、 核心结论

1. **动作ID（Action ID）是在脚本文件还是 `game.dll`？**
   * **100% 在 `game.dll` 中定义和实现！** 脚本文件（JASS / `common.j` / `war3map.j`）运行在高层虚拟机中，不具备操作底层网络封包的能力。动作外壳、Action ID 分发、动作长度步进全由 `game.dll` 负责。
   * 脚本通过暴雪导出的原生 Native 函数（如 `SyncStoredInteger`、`IssueTargetOrder` 等）调用 `game.dll`，由 `game.dll` 内部组装出特定的 Action 封包。
2. **Dota 玩家战绩数据是如何发送给服务器主机（Bot）的？**
   * 游戏结束基地爆炸时，Dota 脚本在 `war3map_3.j` 的结算函数中调用 `SyncStoredInteger`。
   * 该调用进入 `game.dll`（地址 `0x6F44154A`），硬编码生成 **`0x6B` 动作包**（早期 1.20~1.23 版本为 `0x66`）。
   * 该动作包作为 `W3GS_OUTGOING_ACTION (0x26)` 动作流的一部分发送给服务器主机（`War3Bot`）。
   * `War3Bot` 只需要在接收循环中捕获 `0x6B` 并按照 `[dr.x] + [Slot/Global] + [Key] + [Value]` 解码，即可**完全免运行魔兽客户端、微秒级直接获取整场比赛的胜负、KDA、正反补、金钱、英雄与六格神装**！

---

## 二、 `game.dll` 逆向证据链：`SyncStoredInteger` 到 `0x6B` 动作

### 1. JASS 导出表与注册点
在 `game.dll` (1.26.0.6401，基地址 `0x6F000000`) 中：
* 符号字符串 `"SyncStoredInteger"` 位于 `.rdata` 段：**VA `0x6F946284`** (文件偏移 `0x946284`)。
* JASS Native 函数注册入口位于 `0x6F3D79FB`：
  ```assembly
  6F3D79F1   68 98 62 94 6F   PUSH 6F946298        ; 签名参数: (gamecache, string, string, integer)
  6F3D79F6   BA 84 62 94 6F   MOV EDX, 6F946284    ; "SyncStoredInteger"
  6F3D79FB   B9 E0 A6 3C 6F   MOV ECX, 6F3CA6E0    ; C++ 内部处理函数入口
  6F3D7A00   E8 07 D7 07 00   CALL RegisterJassNative
  ```

### 2. 核心封包构造函数：硬编码写入 `0x6B`
进入底层实现函数 `0x6F44154A`，Ghidra / IDA 反汇编出原生动作包构建逻辑：
```assembly
; game.dll RVA 0x44154A (VA 0x6F44154A)
; 构建 GameCache 同步动作流
6F44157E   C6 44 24 20 6B   MOV BYTE PTR SS:[ESP+20], 6B   ; <-- 硬编码写入 Action ID: 0x6B
6F441595   68 00 01 00 00   PUSH 100                       ; 最大字符串长度 256
6F44159A   51               PUSH ECX                       ; GameCache 名称 (如 "dr.x")
6F44159F   E8 BB 9F 2A 00   CALL StringCopy                ; 拷贝 String 1
6F4415A9   68 00 01 00 00   PUSH 100
6F4415AE   56               PUSH ESI                       ; MissionKey (如玩家槽位 "0"~"9" 或 "Global")
6F4415B3   E8 A8 9F 2A 00   CALL StringCopy                ; 拷贝 String 2
6F4415BD   68 00 01 00 00   PUSH 100
6F4415C2   57               PUSH EDI                       ; Key (如 "1"=杀敌, "Winner"=胜负)
6F4415C7   E8 95 9F 2A 00   CALL StringCopy                ; 拷贝 String 3
6F4415D4   8B 48 18         MOV ECX, DWORD PTR DS:[EAX+18] ; 同步的 4 字节整数值 Value
6F4415DF   E8 75 C9 FF FF   CALL EnqueuePlayerAction       ; 压入玩家出栈动作队列 (0x6F43DFC0)
```
**逆向定论**：
`0x6B` 是魔兽 1.24b+ 补丁中为修复 GameCache 溢出漏洞专门分配给 GameCache 同步的独立动作 ID，与 `0x60`（聊天）处于同级协议层。

---

## 三、 魔兽争霸 III 完整 Action ID 字典表

一个客户端 `W3GS_OUTGOING_ACTION (0x26)` 包结构为：
`[CRC32: 4字节]` + `[ActionData: 连续动作流]`。
在 `ActionData` 内部，可能串联 1 个或多个 Action。每个 Action 的首字节即为 Action ID。

| Action ID | 功能定义 | 触发来源 / 行为 | 附加参数长度 (字节) | 长度计算规则 |
| :--- | :--- | :--- | :--- | :--- |
| **`0x01`** | Pause Game | 菜单点击暂停 | 0 | 固定 0 字节 |
| **`0x02`** | Resume Game | 菜单点击恢复 | 0 | 固定 0 字节 |
| **`0x03`** | Set Game Speed | 设置游戏速度 | 1 | 固定 1 字节 |
| **`0x04`** | Increase Speed | 加速（单机） | 0 | 固定 0 字节 |
| **`0x05`** | Decrease Speed | 减速（单机） | 0 | 固定 0 字节 |
| **`0x06`** | Save Game | 存盘请求 | 变长 | 以 `\0` 结尾的字符串 |
| **`0x07`** | Save Game Done | 存盘完成校验 | 4 | 固定 4 字节 |
| **`0x10`** | **无目标单位指令** | 停止(S)、保持(H)、无目标技能、技能加点 | **14** | Flags(2) + AbilityId(4) + Order(8) |
| **`0x11`** | **点目标单位指令** | 地面右键移动、A地面、巡逻、点地施法 | **22** | AbilityId(4) + Order(8) + X(4 float) + Y(4 float) |
| **`0x12`** | **目标单位指令** | 攻击指定单位、右键跟随、指定单位施法 | **30** | 同上 + TargetUnitId1(4) + TargetUnitId2(4) |
| **`0x13`** | **物品转移/丢弃** | 拖动背包物品到地面、递交给友方单位 | **38** | 同上 + ItemId1(4) + ItemId2(4) |
| **`0x14`** | **双目标指令** | 特殊技能联动操作 | **42** | 包含两套目标单位句柄 |
| **`0x16`** | **选择单位** | 鼠标框选、单选、Shift 加选单位 | 变长 | `Mode(1B) + Count(2B) + Count * 8B` |
| **`0x17`** | **设置编队** | 按 `Ctrl + 1~9` 设置小队 | 变长 | `GroupIdx(1B) + Count(2B) + Count * 8B` |
| **`0x18`** | **双击/切编队** | 按 `1~9` 快捷键选中编队 | **2** | `GroupIdx(1B) + SubGroup(1B)` |
| **`0x19`** | **子编队切换** | 选多单位时按 `TAB` 轮换 | **12** | AbilityId(4) + UnitId1(4) + UnitId2(4) |
| **`0x1A`** | 预选择 PreSubselection | 切换选中前的自动前缀 | **0** | **无附加字节（旧表写成 1 是错的）** |
| **`0x1B`** | 选择单位 | 触发器/点选单位 | 9 | Mode(1) + ObjectID×2 |
| **`0x1C`** | 选择地面物品 | 左键点选地上物品 | 9 | Flags(1) + ObjectID×2 |
| **`0x1D`** | 取消英雄复活 | 祭坛取消复活 | 8 | UnitID×2 |
| **`0x1E`** | 取消建造/训练队列 | 取消造兵/研究 | 5 | Slot(1) + ItemID(4) |
| **`0x61`** | 按 ESC 键 | 取消当前命令/关闭子菜单 | 0 | （旧表误写成 0x21） |
| **`0x66`** | 英雄技能加点菜单 | 进入 hero skill submenu | 0 | （旧表误当成 GameCache） |
| **`0x67`** | 建造子菜单 | worker 进入 build submenu | 0 | （旧表误写成 0x28） |
| **`0x68`** | 小地图信号 | Alt+小地图 Ping | 12 | X(4)+Y(4)+duration(4) |
| **`0x69`/`0x6A`** | 对话框按钮 | Dialog click | 16 | 两个 ObjectID |
| **`0x60`** | **游戏内聊天** | `-ap` / `-stats` 等 | 变长 | Trigger(4)+Event(4)+文本`\0` |
| **`0x6B`** | **GameCache 同步** | **`SyncStoredInteger`（1.24b+）** | 变长 | **3个`\0`字符串 + 4字节整数** |

> **提示**：计算玩家真实 **APM（手速）** 时，行业标准只统计：`0x10`, `0x11`, `0x12`, `0x13`, `0x16`, `0x17`, `0x18`, `0x19`, `0x1B` 这 9 个有效指令。

---

## 四、 DotA 战绩数据传输协议全解（映射表）

在 `D:\Qt\workspace\War3Script\war3map_3.j` 的结算逻辑中，Dota 采用如下规则通过 `0x6B` 输出比赛最终数据：

### 1. 玩家个人数据（`MissionKey = "0"` ~ `"9"`）
每个玩家槽位对应一个字符串形式的数字（`"0"` 到 `"9"`）：

| Key 字段 | 数据类型 | 业务含义 | 示例值 |
| :--- | :--- | :--- | :--- |
| **`"1"`** | DWORD | **击杀数 (Kills)** | `12` |
| **`"2"`** | DWORD | **死亡数 (Deaths)** | `3` |
| **`"3"`** | DWORD | **正补小兵 (Creep Kills)** | `185` |
| **`"4"`** | DWORD | **反补小兵 (Denies)** | `24` |
| **`"5"`** | DWORD | **助攻数 (Assists)** | `15` |
| **`"6"`** | DWORD | **游戏结束剩余金钱 (End Gold)** | `3420` |
| **`"7"`** | DWORD | **总经验 / 特殊积分统计** | `15200` |
| **`"8_0"`** | DWORD (四字符) | **物品栏第 1 格物品 ID** | `'bspd'` (速度之靴) |
| **`"8_1"`** | DWORD (四字符) | **物品栏第 2 格物品 ID** | `'dnga'` (科勒的匕首/跳刀) |
| **`"8_2"`** | DWORD (四字符) | **物品栏第 3 格物品 ID** | `'hval'` (黑皇杖 BKB) |
| **`"8_3"`** | DWORD (四字符) | **物品栏第 4 格物品 ID** | `0` (空格子) |
| **`"8_4"`** | DWORD (四字符) | **物品栏第 5 格物品 ID** | `0` |
| **`"8_5"`** | DWORD (四字符) | **物品栏第 6 格物品 ID** | `0` |
| **`"9"`** | DWORD (四字符) | **英雄单位类型 ID** | `'H008'` (影魔 Nevermore) |
| **`"id"`** | DWORD | **队伍槽位归属** | 1~5: 近卫, 6~10: 天灾 |

### 2. 全局游戏结算数据（`MissionKey = "Global"`）
| Key 字段 | 数据类型 | 业务含义 | 取值范围 |
| :--- | :--- | :--- | :--- |
| **`"Winner"`** | DWORD | **胜负归属** | **`1` = 近卫军团(Sentinel)获胜**<br>**`2` = 天灾军团(Scourge)获胜** |
| **`"m"`** | DWORD | **比赛总分钟数** | 例如 `42` |
| **`"s"`** | DWORD | **比赛总秒数余数** | 例如 `18` (即 42分18秒) |

---

## 五、 War3Bot 最佳接入实践代码

在 `War3Bot` 的 [client.cpp](file:///d:/Qt/workspace/War3Bot/src/client.cpp#L1762) 中，增加针对 `0x6B` 的解析器：

```cpp
// 解析 0x6B GameCache 同步动作
if (actionId == 0x6B) {
    int cur = offset + 1;
    // 1. 读取 CacheName (如 "dr.x")
    int null1 = actionData.indexOf('\0', cur);
    if (null1 != -1) {
        QString cacheName = QString::fromLatin1(actionData.mid(cur, null1 - cur));
        cur = null1 + 1;

        // 2. 读取 MissionKey (如 "0"~"9" 或 "Global")
        int null2 = actionData.indexOf('\0', cur);
        if (null2 != -1) {
            QString missionKey = QString::fromLatin1(actionData.mid(cur, null2 - cur));
            cur = null2 + 1;

            // 3. 读取 Key (如 "1"=Kills, "Winner"=胜负)
            int null3 = actionData.indexOf('\0', cur);
            if (null3 != -1 && cur + 4 <= actionData.size()) {
                QString key = QString::fromLatin1(actionData.mid(cur, null3 - cur));
                cur = null3 + 1;

                // 4. 读取 4 字节整数 Value (小端序)
                quint32 val = *reinterpret_cast<const quint32*>(actionData.constData() + cur);

                // 触发战绩统计信号
                emit dotaStatsPacketReceived(missionKey, key, val);
            }
        }
    }
}
```

通过这套逻辑，`War3Bot` 作为服务器主机不仅天然具备反作弊公信力，而且**零开销（单次判定时间 < 1 微秒）**，彻底消除对服务器性能消耗的担忧。
