# 共享工具

跨主题复用的脚本放这里。某个版本/问题专用的一次性导出放 `artifacts/<主题>/`。

| 子目录 | 用途 |
| --- | --- |
| `scripts/` | PE 扫描、字符串/导入 xref、Capstone 反汇编、跨版本字节普查 |
| `ghidra-scripts/` | `analyzeHeadless` 的 Java/Jython postscript |

从 `C:\War3Analysis` 收回暂存文件：

```powershell
powershell -File D:\Qt\workspace\War3Analysis\shared\scripts\collect_scratch.ps1
```
