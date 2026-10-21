# 全版本 FPS 解锁补丁

每个子目录一个版本，内含补丁后的 `game.dll`。
**1.22+ 只覆盖 game.dll**（64 帧限制已在 DLL 内）。**1.21 及更早必须同时覆盖 war3.exe**。
D3D8（1.26 及更早）只改全屏 PresentationInterval，不再改窗口模式 Flags，避免 CreateDevice 失败。
OpenGL cave 用 PIC（相对 edx 读 IAT/字符串），不依赖 ImageBase，且不破坏 callee-saved 的 ebx。
**1.27 请用本目录 `1.27.0.52240-fps-unlock-dx-ogl/game.dll`，不要用旧的 `...-d3d9-ogl`（INT3 cave 无 PIC）。**

重新生成 FPS：`python dll_game/patch_all_versions_fps.py`

地图大小补丁是另一套目录，见文末。重新生成：`python dll_game/patch_all_versions_map_size.py`

| 版本 | 输出 | 补丁项 | 备注 |
| --- | --- | --- | --- |
| 1.0.17.5988 | `1.0.17.5988-fps-unlock-dx-ogl/` | d3d8-fullscreen-PresentationInterval-IMMEDIATE, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent, software-64fps-war3exe | software-64 not in game.dll; no maxfps string |
| 1.0.20.6048 | `1.0.20.6048-fps-unlock-dx-ogl/` | d3d8-fullscreen-PresentationInterval-IMMEDIATE, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent, software-64fps-war3exe | software-64 not in game.dll; no maxfps string |
| 1.20.4.6074 | `1.20.4.6074-fps-unlock-dx-ogl/` | d3d8-fullscreen-PresentationInterval-IMMEDIATE, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent, software-64fps-war3exe | software-64 not in game.dll; no maxfps string |
| 1.21.0.6263 | `1.21.0.6263-fps-unlock-dx-ogl/` | d3d8-fullscreen-PresentationInterval-IMMEDIATE, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent, software-64fps-war3exe | software-64 not in game.dll; no maxfps string |
| 1.22.0.6328 | `1.22.0.6328-fps-unlock-dx-ogl/` | software-64fps-keep-flag-bit2, d3d8-fullscreen-PresentationInterval-IMMEDIATE, maxfps-default-200-to-10000, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent | 42b61b230122 |
| 1.23.0.6352 | `1.23.0.6352-fps-unlock-dx-ogl/` | software-64fps-keep-flag-bit2, d3d8-fullscreen-PresentationInterval-IMMEDIATE, maxfps-default-200-to-10000, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent | a5601f9cb52b |
| 1.24.1.6374 | `1.24.1.6374-fps-unlock-dx-ogl/` | software-64fps-keep-flag-bit2, d3d8-fullscreen-PresentationInterval-IMMEDIATE, maxfps-default-200-to-10000, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent | 2ca0e1d5e175 |
| 1.24.4.6387 | `1.24.4.6387-fps-unlock-dx-ogl/` | software-64fps-keep-flag-bit2, d3d8-fullscreen-PresentationInterval-IMMEDIATE, maxfps-default-200-to-10000, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent | 802feb939f82 |
| 1.25.1.6397 | `1.25.1.6397-fps-unlock-dx-ogl/` | software-64fps-keep-flag-bit2, d3d8-fullscreen-PresentationInterval-IMMEDIATE, maxfps-default-200-to-10000, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent | 717279b52685 |
| 1.26.0.6401 | `1.26.0.6401-fps-unlock-dx-ogl/` | software-64fps-keep-flag-bit2, d3d8-fullscreen-PresentationInterval-IMMEDIATE, maxfps-default-200-to-10000, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent | d4787840e4f3 |
| 1.27.0.52240 | `1.27.0.52240-fps-unlock-dx-ogl/` | software-64fps-keep-flag-bit2, d3d9-PresentationInterval-IMMEDIATE, d3d9-windowed-interval-cave, d3d9-windowed-hook-to-cave, d3d9-Flags-clear-LOCKABLE_BACKBUFFER, maxfps-default-200-to-10000, opengl-wglSwapIntervalEXT-name, opengl-wglSwapIntervalEXT-cave, opengl-hook-after-wglMakeCurrent | 4c03df5a82ef |

## 地图大小解锁

每个 `<版本>-map-size-unlock/` 里只有补丁后的 `game.dll`。做法与 [WarcraftHelper sizebypass.cpp](https://github.com/LoveBeforT/WarcraftHelper/blob/master/WarcraftHelper/plugin/sizebypass.cpp) 相同：把 `CMP EAX, imm32` 和后面的 `JA` 整段改成 NOP（近程 11 字节，短跳 7 字节）。长度为 0、以及文件大小高 32 位非 0 的拒绝仍保留。1.0.17–1.22 有 3 处，其中一处是 NetProvider 的短跳 `JA`。1.23 起这处变成近程 `JA`。1.20.4 / 1.27a 的三处 RVA 与 WarcraftHelper 的 1.20e / 1.27a 一致。1.23 及更早原阈值是 4 MiB；1.24 起是 8 MiB。

| 版本 | 输出 | 处数 | 补丁后 SHA-256 前 12 位 |
| --- | --- | ---: | --- |
| 1.0.17.5988 | `1.0.17.5988-map-size-unlock/` | 3 | `094629b3e20c` |
| 1.0.20.6048 | `1.0.20.6048-map-size-unlock/` | 3 | `8b71d78812f3` |
| 1.20.4.6074 | `1.20.4.6074-map-size-unlock/` | 3 | `90748f728e1a` |
| 1.21.0.6263 | `1.21.0.6263-map-size-unlock/` | 3 | `20f4607811a3` |
| 1.22.0.6328 | `1.22.0.6328-map-size-unlock/` | 3 | `27ceeeaf562d` |
| 1.23.0.6352 | `1.23.0.6352-map-size-unlock/` | 3 | `84326cfee532` |
| 1.24.1.6374 | `1.24.1.6374-map-size-unlock/` | 3 | `accd3eede578` |
| 1.24.4.6387 | `1.24.4.6387-map-size-unlock/` | 3 | `f54a28be6160` |
| 1.25.1.6397 | `1.25.1.6397-map-size-unlock/` | 3 | `baccfa0e55a9` |
| 1.26.0.6401 | `1.26.0.6401-map-size-unlock/` | 3 | `24cb496cac85` |
| 1.27.0.52240 | `1.27.0.52240-map-size-unlock/` | 3 | `45467ccc83fb` |

