# 1.27.0.52240 FPS unlock

从官方样本复制后改字节。输出文件名保持 `game.dll`（若有 `war3.exe` 补丁则一并放本目录）。

## 文件

- 源 DLL：`D:\Qt\workspace\War3Launcher\versions\1.27.0.52240\game.dll`
- 源 SHA-256：`e04d1716603c075eb0c8e1e21cf1093a664adc5249efab396bfa08d7b09d0c3a`
- 输出 DLL：`D:\Qt\workspace\War3Analysis\dll_game\1.27.0.52240-fps-unlock-dx-ogl\game.dll`
- 输出 SHA-256：`4c03df5a82efab9c7011b8f283ee427b8e2b78e96916992bfa39886dcc21d17c`

## 改动

| 名称 | 文件偏移 | 原始 | 替换 |
| --- | ---: | --- | --- |
| software-64fps-keep-flag-bit2 | `0x5F0FB` | `fb` | `ff` |
| d3d9-PresentationInterval-IMMEDIATE | `0xEBB59` | `c7 46 34 00 00 00 00` | `c7 46 34 00 00 00 80` |
| d3d9-windowed-interval-cave | `0x94D29A` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `c7 46 18 01 00 00 00 c7 46 34 00 00 00 80 89 4e 08 e9 ed e8 79 ff` |
| d3d9-windowed-hook-to-cave | `0xEBB94` | `c7 46 18 01 00 00 00 89 4e 08` | `e9 01 17 86 00 90 90 90 90 90` |
| d3d9-Flags-clear-LOCKABLE_BACKBUFFER | `0xEBBA2` | `c7 46 2c 01 00 00 00` | `c7 46 2c 00 00 00 00` |
| maxfps-default-200-to-10000 | `0x35C6ED` | `c7 45 fc c8 00 00 00` | `c7 45 fc 10 27 00 00` |
| opengl-wglSwapIntervalEXT-name | `0xB5765A` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `77 67 6c 53 77 61 70 49 6e 74 65 72 76 61 6c 45 58 54 00` |
| opengl-wglSwapIntervalEXT-cave | `0x94D2B0` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `e8 8b dc 79 ff 50 e8 00 00 00 00 5a 8d 82 9f a3 20 00 50 8b 82 31 06 00 00 ff d0 85 c0 74 04 6a 00 ff d0 58 c3` |
| opengl-hook-after-wglMakeCurrent | `0xE6CEB` | `e8 50 42 00 00` | `e8 c0 65 86 00` |

## 验证

1. 备份游戏目录对应文件。
2. 把本目录文件覆盖到该版本游戏根目录。
3. Direct3D 启动后输入 `/fps`；OpenGL 加 `-opengl` 再测。
4. 启动器切版本会从 `versions\` 还原原件，测完勿提交 DLL。

