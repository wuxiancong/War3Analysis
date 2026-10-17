# 1.24.4.6387 FPS unlock

从官方样本复制后改字节。输出文件名保持 `game.dll`（若有 `war3.exe` 补丁则一并放本目录）。

## 文件

- 源 DLL：`D:\Qt\workspace\War3Launcher\versions\1.24.4.6387\game.dll`
- 源 SHA-256：`c7c958174bde30961a41fa91827e78a800e473efdd8d1de8d6c94abf0b0024bf`
- 输出 DLL：`D:\Qt\workspace\War3Analysis\dll_game\1.24.4.6387-fps-unlock-dx-ogl\game.dll`
- 输出 SHA-256：`802feb939f82de838f77fd9a5bc936f15fe798ee647849b1775d9a08b55fcb45`

## 改动

| 名称 | 文件偏移 | 原始 | 替换 |
| --- | ---: | --- | --- |
| software-64fps-keep-flag-bit2 | `0x62DF9B` | `fb` | `ff` |
| d3d8-fullscreen-PresentationInterval-IMMEDIATE | `0x52D653` | `c7 46 30 00 00 00 00` | `c7 46 30 00 00 00 80` |
| maxfps-default-200-to-10000 | `0x3841D8` | `c7 44 24 14 c8 00 00 00` | `c7 44 24 14 10 27 00 00` |
| opengl-wglSwapIntervalEXT-name | `0xA64CC4` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `77 67 6c 53 77 61 70 49 6e 74 65 72 76 61 6c 45 58 54 00` |
| opengl-wglSwapIntervalEXT-cave | `0x87EFBA` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `e8 41 31 cb ff 50 e8 00 00 00 00 5a 8d 82 ff 5c 1e 00 50 8b 82 6f 05 00 00 ff d0 85 c0 74 04 6a 00 ff d0 58 c3` |
| opengl-hook-after-wglMakeCurrent | `0x52B1D8` | `e8 23 6f 00 00` | `e8 dd 3d 35 00` |

## 验证

1. 备份游戏目录对应文件。
2. 把本目录文件覆盖到该版本游戏根目录。
3. Direct3D 启动后输入 `/fps`；OpenGL 加 `-opengl` 再测。
4. 启动器切版本会从 `versions\` 还原原件，测完勿提交 DLL。

