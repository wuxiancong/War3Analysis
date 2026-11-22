# game.dll RVA — 索敌 / CallForHelp（全版本）

`GetUnitAcquireRange` 原生入口以既有核对文档 [`war3-lasthit-combat-data.md`](../../analyses/war3-lasthit-combat-data.md) §3.2 为准（已反汇编到 `CAbilityAttack+0x244`）。  
`CallForHelp` / `CreepCallForHelp` 为 MiscGame 键名字符串 xref（加载进 gameplay 常量表）；DotA 未在 `war3mapMisc.txt` 覆盖 → 默认 **600**。

| 版本 | GetUnitAcquireRange native | CallForHelp str | CallForHelp xref(s) | CreepCallForHelp str | CreepCallForHelp xref(s) | 备注 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1.0.17.5988 | —（早期未在补刀文档确认） | `0x80632C` | `0x1C6043`, `0x1C60B7` | `0x806338` | `0x1C6018` | 同代加载器 |
| 1.0.20.6048 | — | `0x80736C` | `0x1C6043`, `0x1C60B7` | `0x807378` | `0x1C6018` | |
| 1.20.4.6074 | — | `0x80736C` | `0x1C60B3`, `0x1C6127` | `0x807378` | `0x1C6088` | |
| 1.21.0.6263 | `0x2C4450` | `0x808484` | `0x1C9273`, `0x1C92E7` | `0x808490` | `0x1C9248` | |
| 1.22.0.6328 | `0x3BE720` | `0x91DE70` | `0x26C3F3`, `0x27B19A`, `0x2A333A` | `0x91DE7C` | `0x26C413`, `0x27B174` | 1.22+ 双 xref（load/use） |
| 1.23.0.6352 | `0x3C0440` | `0x931FB0` | `0x26D933`, `0x27C6DA`, `0x2A487A` | `0x931FBC` | `0x26D953`, `0x27C6B4` | |
| 1.24.1.6374 | `0x3C5F00` | `0x9410E8` | `0x26D9E3`, `0x27C79A`, `0x2A493A` | `0x9410F4` | `0x26DA03`, `0x27C774` | |
| 1.24.4.6387 | `0x3C5FC0` | `0x9410E8` | `0x26DA43`, `0x27C7FA`, `0x2A49EA` | `0x9410F4` | `0x26DA63`, `0x27C7D4` | |
| 1.25.1.6397 | `0x3C5AE0` | `0x92EF88` | `0x26CD03`, `0x27BAAA`, `0x2A3C9A` | `0x92EF94` | `0x26CD23`, `0x27BA84` | |
| 1.26.0.6401 | **`0x3C5D10`** | `0x92EF88` | `0x26CF33`, `0x27BCDA`, `0x2A3ECA` | `0x92EF94` | `0x26CF53`, `0x27BCB4` | `CUnit::GetAcquireRange` ≈ `0x276A00` |
| 1.27.0.52240 | **`0x1E5F50`** | `0xA4AB20` | `0x6510F2`, `0x66A972`, `0x66A993` | `0xA4AB2C` | `0x65A543`, `0x66A948` | `CUnit::GetAcquireRange` ≈ `0x666A20`；`acquire` @ `CAbilityAttack+0x244` |

原始扫描：`string_xrefs_all_versions.json`、`rva_table.md`（脚本 `scan_aggro_strings.py`）。
