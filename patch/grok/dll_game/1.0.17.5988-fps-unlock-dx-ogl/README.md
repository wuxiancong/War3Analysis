# 1.0.17.5988 FPS unlock

从官方样本复制后改字节。输出文件名保持 `game.dll`（若有 `war3.exe` 补丁则一并放本目录）。

## 文件

- 源 DLL：`D:\Qt\workspace\War3Launcher\versions\1.0.17.5988\game.dll`
- 源 SHA-256：`ea09c582a4c8b4112c1425cc954bf710fed3051e4a85bc39586647c0bd8bf4b2`
- 输出 DLL：`D:\Qt\workspace\War3Analysis\dll_game\1.0.17.5988-fps-unlock-dx-ogl\game.dll`
- 输出 SHA-256：`ee5e1d9144af32dc3543834aaf1c54a90e68ff3ec62ed757d086bddab64bea10`

## 改动

| 名称 | 文件偏移 | 原始 | 替换 |
| --- | ---: | --- | --- |
| d3d8-fullscreen-PresentationInterval-IMMEDIATE | `0xD069D` | `c7 46 30 00 00 00 00` | `c7 46 30 00 00 00 80` |
| opengl-wglSwapIntervalEXT-name | `0x7E1144` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `77 67 6c 53 77 61 70 49 6e 74 65 72 76 61 6c 45 58 54 00` |
| opengl-wglSwapIntervalEXT-cave | `0x703D70` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `e8 db b6 9c ff 50 e8 00 00 00 00 5a 8d 82 c9 d3 0d 00 50 8b 82 99 04 00 00 ff d0 85 c0 74 04 6a 00 ff d0 58 c3` |
| opengl-hook-after-wglMakeCurrent | `0xCB998` | `e8 b3 3a 00 00` | `e8 d3 83 63 00` |
| software-64fps-war3exe | `0x445FE` | `fb` | `ff` |

- 源 EXE：`D:\Qt\workspace\War3Launcher\versions\1.0.17.5988\war3.exe`
- 输出 EXE：`D:\Qt\workspace\War3Analysis\dll_game\1.0.17.5988-fps-unlock-dx-ogl\war3.exe`
- 输出 EXE SHA-256：`b2525fc0e58d87ee7fc0c5d860ae6ee1b52ee45899c5d00f2f3f022fd0b420bd`

| software-64fps-war3exe | `0x445FE` | `fb` | `ff` |

## 验证

1. 备份游戏目录对应文件。
2. 把本目录文件覆盖到该版本游戏根目录。
3. Direct3D 启动后输入 `/fps`；OpenGL 加 `-opengl` 再测。
4. 启动器切版本会从 `versions\` 还原原件，测完勿提交 DLL。

## 备注

- software-64 not in game.dll
- no maxfps string

