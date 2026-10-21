# 1.23.0.6352 map size unlock

从 `versions\1.23.0.6352\game.dll` 复制后，把地图大小检查 `CMP EAX, imm32` + `JA` 整段改成 NOP。
做法与 [WarcraftHelper sizebypass.cpp](https://github.com/LoveBeforT/WarcraftHelper/blob/master/WarcraftHelper/plugin/sizebypass.cpp) 相同。
长度为 0、以及文件大小高 32 位非 0 的拒绝仍然保留。

## 文件

- 源 DLL：`D:\Qt\workspace\War3Launcher\versions\1.23.0.6352\game.dll`
- 源 SHA-256：`ee6175947a8792cd672253b37deb4c5d0577e4e145ffd90fed9021c64c31ae1e`
- 输出 DLL：`D:\Qt\workspace\War3Analysis\patch\grok\dll_game\1.23.0.6352-map-size-unlock\game.dll`
- 输出 SHA-256：`84326cfee532f642dde9ff54ea1301afa426ad131014928124d839ebf7697a33`

## 改动

近程 `JA`（`0F 87`）NOP 11 字节，短跳 `JA`（`77`）NOP 7 字节。1.20e / 1.27a 的 RVA 与 WarcraftHelper 一致。

| # | 指令文件偏移 | 比较指令 RVA | 跳转 | 字节 | 原始 | 替换 |
| --- | ---: | ---: | --- | ---: | --- | --- |
| 1 | `0x6494E3` | `0x6494E3` | `ja-near` | `11` | `3d000040000f87a5000000` | `9090909090909090909090` |
| 2 | `0x660A7E` | `0x660A7E` | `ja-near` | `11` | `3d000040000f87ba010000` | `9090909090909090909090` |
| 3 | `0x670960` | `0x670960` | `ja-near` | `11` | `3d000040000f877f010000` | `9090909090909090909090` |

## 验证

1. 备份该版本游戏目录里的 `game.dll`。
2. 用本目录的 `game.dll` 覆盖游戏根目录同名文件。
3. 启动器切换版本会从 `versions\` 还原官方 DLL，覆盖之后再测。
4. 1.23 及更早旧阈值是 4 MiB，1.24 起是 8 MiB。低版本仍不能运行需要更高 common.j 的地图。
