# 分析产物必须收进仓库目录

每次分析结束后，把新产生的脚本、导出、报告、补丁说明复制到 `D:\Qt\workspace\War3Analysis` 对应子目录，不要只留在 `C:\War3Analysis`。

| 内容 | 目录 |
| --- | --- |
| 结论 Markdown / 思维导图 | `analyses/` |
| 可复用扫描、反汇编、补丁脚本 | `shared/scripts/` |
| Ghidra headless / postscript | `shared/ghidra-scripts/` |
| 本次 REA/Ghidra 文本与 JSON | `artifacts/<主题>/` |
| 补丁 `game.dll` | `dll_game/<版本>-<改动>/game.dll` |
| 官方样本 | `samples/<版本>/`（不提交 Git） |

游戏二进制与 Ghidra `.rep` 默认不入库。详见 `.cursor/rules/analysis-workspace.mdc`。
