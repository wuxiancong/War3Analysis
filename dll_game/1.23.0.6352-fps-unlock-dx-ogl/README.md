# 1.23.0.6352 FPS unlock

从官方样本复制后改字节。输出文件名保持 `game.dll`（若有 `war3.exe` 补丁则一并放本目录）。

## 文件

- 源 DLL：`D:\Qt\workspace\War3Launcher\versions\1.23.0.6352\game.dll`
- 源 SHA-256：`ee6175947a8792cd672253b37deb4c5d0577e4e145ffd90fed9021c64c31ae1e`
- 输出 DLL：`D:\Qt\workspace\War3Analysis\dll_game\1.23.0.6352-fps-unlock-dx-ogl\game.dll`
- 输出 SHA-256：`a5601f9cb52bbe0d23a8de1086605e002c7db164745ba26d97ae1ddd0b0e8874`

## 改动

| 名称 | 文件偏移 | 原始 | 替换 |
| --- | ---: | --- | --- |
| software-64fps-keep-flag-bit2 | `0x61F4FB` | `fb` | `ff` |
| d3d8-fullscreen-PresentationInterval-IMMEDIATE | `0x51EC43` | `c7 46 30 00 00 00 00` | `c7 46 30 00 00 00 80` |
| maxfps-default-200-to-10000 | `0x384058` | `c7 44 24 14 c8 00 00 00` | `c7 44 24 14 10 27 00 00` |
| opengl-wglSwapIntervalEXT-name | `0xA53E74` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `77 67 6c 53 77 61 70 49 6e 74 65 72 76 61 6c 45 58 54 00` |
| opengl-wglSwapIntervalEXT-cave | `0x86F6FA` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `e8 f1 3f cb ff 50 e8 00 00 00 00 5a 8d 82 6f 47 1e 00 50 8b 82 2f 0e 00 00 ff d0 85 c0 74 04 6a 00 ff d0 58 c3` |
| opengl-hook-after-wglMakeCurrent | `0x51C7C8` | `e8 23 6f 00 00` | `e8 2d 2f 35 00` |

## 验证

1. 备份游戏目录对应文件。
2. 把本目录文件覆盖到该版本游戏根目录。
3. Direct3D 启动后输入 `/fps`；OpenGL 加 `-opengl` 再测。
4. 启动器切版本会从 `versions\` 还原原件，测完勿提交 DLL。

