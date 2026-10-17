# 1.26.0.6401 FPS unlock

从官方样本复制后改字节。输出文件名保持 `game.dll`（若有 `war3.exe` 补丁则一并放本目录）。

## 文件

- 源 DLL：`D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\game.dll`
- 源 SHA-256：`6d21bd9a0f9fbc8446f455c9e89ac994fed68174426fe608fcb9baefd4dec53c`
- 输出 DLL：`D:\Qt\workspace\War3Analysis\dll_game\1.26.0.6401-fps-unlock-dx-ogl\game.dll`
- 输出 SHA-256：`d4787840e4f3f1b14c2a8047b4c51fa964e730de0b499f10f2a8e3485586c5ec`

## 改动

| 名称 | 文件偏移 | 原始 | 替换 |
| --- | ---: | --- | --- |
| software-64fps-keep-flag-bit2 | `0x62D7FB` | `fb` | `ff` |
| d3d8-fullscreen-PresentationInterval-IMMEDIATE | `0x52CB53` | `c7 46 30 00 00 00 00` | `c7 46 30 00 00 00 80` |
| maxfps-default-200-to-10000 | `0x383698` | `c7 44 24 14 c8 00 00 00` | `c7 44 24 14 10 27 00 00` |
| opengl-wglSwapIntervalEXT-name | `0xA4E1C4` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `77 67 6c 53 77 61 70 49 6e 74 65 72 76 61 6c 45 58 54 00` |
| opengl-wglSwapIntervalEXT-cave | `0x86C60A` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `e8 f1 4f cc ff 50 e8 00 00 00 00 5a 8d 82 af 1b 1e 00 50 8b 82 ff 0d 00 00 ff d0 85 c0 74 04 6a 00 ff d0 58 c3` |
| opengl-hook-after-wglMakeCurrent | `0x52A6D8` | `e8 23 6f 00 00` | `e8 2d 1f 34 00` |

## 验证

1. 备份游戏目录对应文件。
2. 把本目录文件覆盖到该版本游戏根目录。
3. Direct3D 启动后输入 `/fps`；OpenGL 加 `-opengl` 再测。
4. 启动器切版本会从 `versions\` 还原原件，测完勿提交 DLL。

