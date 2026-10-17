# 产物：1.27 FPS 解除静态分析

对应报告：`analyses/warcraft-iii-1.27-fps-unlock.md`。

| 文件 | 来源 |
| --- | --- |
| `ghidra-fps-dump.txt` | Ghidra headless `DumpFps.java` 反编译 |
| `game127.json` | REA `--snapshot` |
| `trace-maxfps.md` | REA `trace maxfps`（超时失败记录） |

补丁 DLL：`dll_game/1.27.0.52240-fps-unlock-d3d9-ogl/game.dll`。
