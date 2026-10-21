# 1.21.0.6263 FPS unlock

从官方样本复制后改字节。输出文件名保持 `game.dll`（若有 `war3.exe` 补丁则一并放本目录）。

## 文件

- 源 DLL：`D:\Qt\workspace\War3Launcher\versions\1.21.0.6263\game.dll`
- 源 SHA-256：`3265e78dd68b1ab6c54957409e472c077f9fe2abcce4cfd279e56af66a6ef6f3`
- 输出 DLL：`D:\Qt\workspace\War3Analysis\dll_game\1.21.0.6263-fps-unlock-dx-ogl\game.dll`
- 输出 SHA-256：`08f7cf777f22a721c08aa64ee5c7b9aad41ade0b8ae3a546c81b99ef4d73633c`

## 改动

| 名称 | 文件偏移 | 原始 | 替换 |
| --- | ---: | --- | --- |
| d3d8-fullscreen-PresentationInterval-IMMEDIATE | `0xD069D` | `c7 46 30 00 00 00 00` | `c7 46 30 00 00 00 80` |
| opengl-wglSwapIntervalEXT-name | `0x7E3164` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `77 67 6c 53 77 61 70 49 6e 74 65 72 76 61 6c 45 58 54 00` |
| opengl-wglSwapIntervalEXT-cave | `0x705FD0` | `00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00` | `e8 7b 94 9c ff 50 e8 00 00 00 00 5a 8d 82 89 d1 0d 00 50 8b 82 39 02 00 00 ff d0 85 c0 74 04 6a 00 ff d0 58 c3` |
| opengl-hook-after-wglMakeCurrent | `0xCB998` | `e8 b3 3a 00 00` | `e8 33 a6 63 00` |
| software-64fps-war3exe | `0x445FE` | `fb` | `ff` |

- 源 EXE：`D:\Qt\workspace\War3Launcher\versions\1.21.0.6263\war3.exe`
- 输出 EXE：`D:\Qt\workspace\War3Analysis\dll_game\1.21.0.6263-fps-unlock-dx-ogl\war3.exe`
- 输出 EXE SHA-256：`663d742504d5548892a1f4ffb542d9ca0d5ec460cd2fac0b2a91d45cd0521172`

| software-64fps-war3exe | `0x445FE` | `fb` | `ff` |

## 验证

1. 备份游戏目录对应文件。
2. 把本目录文件覆盖到该版本游戏根目录。
3. Direct3D 启动后输入 `/fps`；OpenGL 加 `-opengl` 再测。
4. 启动器切版本会从 `versions\` 还原原件，测完勿提交 DLL。

## 备注

- software-64 not in game.dll
- no maxfps string

