# 全版本 FPS 解锁补丁

每个子目录一个版本，内含补丁后的 `game.dll`。
**1.22+ 只覆盖 game.dll**（64 帧限制已在 DLL 内）。**1.21 及更早必须同时覆盖 war3.exe**。
D3D8（1.26 及更早）只改全屏 PresentationInterval，不再改窗口模式 Flags，避免 CreateDevice 失败。
OpenGL cave 用 PIC（相对 edx 读 IAT/字符串），不依赖 ImageBase，且不破坏 callee-saved 的 ebx。
**1.27 请用本目录 `1.27.0.52240-fps-unlock-dx-ogl/game.dll`，不要用旧的 `...-d3d9-ogl`（INT3 cave 无 PIC）。**

重新生成：`python dll_game/patch_all_versions_fps.py`

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

