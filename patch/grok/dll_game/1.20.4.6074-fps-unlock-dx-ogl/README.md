# 1.20.4.6074 FPS unlock

从官方样本复制后改字节。输出文件名保持 `game.dll`（若有 `war3.exe` 补丁则一并放本目录）。

## 文件

- 源 DLL：`D:\Qt\workspace\War3Launcher\versions\1.20.4.6074\game.dll`
- 源 SHA-256：`6b5b406861a56449c604c15cf0971df7d6d26f679eff7aa69a34946c7d91764b`
- 输出 DLL：`D:\Qt\workspace\War3Analysis\dll_game\1.20.4.6074-fps-unlock-dx-ogl\game.dll`
- 输出 SHA-256：`a1dc3e75476862510c42da38668d4eab7100a3a584e6f9a2729ba85b55307a94`

## 改动

| 名称 | 文件偏移 | 原始 | 替换 |
| --- | ---: | --- | --- |
| d3d8-fullscreen-PresentationInterval-IMMEDIATE | `0xD069D` | `c7 46 30 00 00 00 00` | `c7 46 30 00 00 00 80` |
| opengl-wglSwapIntervalEXT-name | `0x7E2144` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `77 67 6c 53 77 61 70 49 6e 74 65 72 76 61 6c 45 58 54 00` |
| opengl-wglSwapIntervalEXT-cave | `0x704BB0` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `e8 9b a8 9c ff 50 e8 00 00 00 00 5a 8d 82 89 d5 0d 00 50 8b 82 59 06 00 00 ff d0 85 c0 74 04 6a 00 ff d0 58 c3` |
| opengl-hook-after-wglMakeCurrent | `0xCB998` | `e8 b3 3a 00 00` | `e8 13 92 63 00` |
| software-64fps-war3exe | `0x445FE` | `fb` | `ff` |

- 源 EXE：`D:\Qt\workspace\War3Launcher\versions\1.20.4.6074\war3.exe`
- 输出 EXE：`D:\Qt\workspace\War3Analysis\dll_game\1.20.4.6074-fps-unlock-dx-ogl\war3.exe`
- 输出 EXE SHA-256：`57a3852d9ccf173f010a8e1bb80f80b1d2a8cc56c219cf6dccf2e207b47b24ee`

| software-64fps-war3exe | `0x445FE` | `fb` | `ff` |

## 验证

1. 备份游戏目录对应文件。
2. 把本目录文件覆盖到该版本游戏根目录。
3. Direct3D 启动后输入 `/fps`；OpenGL 加 `-opengl` 再测。
4. 启动器切版本会从 `versions\` 还原原件，测完勿提交 DLL。

## 备注

- software-64 not in game.dll
- no maxfps string

