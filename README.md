# War3Analysis

魔兽争霸 III 逆向分析工作区，用于整理不同版本的二进制样本、Ghidra 项目、分析结论和可复现的验证步骤。

## 目标

- 保留每次逆向分析的过程、证据、结论和未验证事项。
- 通过 Ghidra 项目继续已有分析，或为新版本/新目标创建独立项目。
- 避免将游戏原始二进制、Ghidra 大型数据库或个人路径误提交到 Git。

## 目录约定

```text
War3Analysis/
├─ analyses/                 # 每个目标/问题一份 Markdown 分析报告
├─ ghidra/
│  └─ projects/              # 本机 Ghidra 项目数据库（已加入 .gitignore）
├─ samples/                  # 本机原始样本及其版本信息（不提交二进制）
├─ run-ghidra.cmd            # 启动本机 Ghidra
├─ README.md
└─ .github/copilot-instructions.md
```

## 运行现有 Ghidra 项目

1. 安装或解压 Ghidra 12.1.4，并确保它的目录中包含 `ghidraRun.bat` 和兼容的 JDK 21。
2. 默认启动脚本使用 `D:\ghidra_12.1.4`。如果 Ghidra 位于其他位置，在启动前设置 `GHIDRA_HOME`，例如：

   ```powershell
   $env:GHIDRA_HOME = 'E:\Tools\ghidra_12.1.4'
   .\run-ghidra.cmd
   ```

3. 在 Ghidra 项目管理器中打开 `ghidra\projects\War3_127.gpr`。
4. 本机已有的 `War3_127` 项目数据位于 `ghidra\projects\War3_127.rep`；项目数据库被 Git 忽略，不会随仓库克隆或提交自动分发。

## 开始新的分析

1. 在 `samples\` 下按版本存放本机样本，并记录来源、版本、SHA-256 和获取日期；不要提交未经授权或不适合公开分发的游戏文件。
2. 在 `ghidra\projects\` 下为版本/目标新建独立 Ghidra 项目。
3. 将过程和结论写入 `analyses\`，文件名采用 `产品-版本-主题.md`，例如 `warcraft-iii-1.27-battlenet-button.md`。
4. 对每个重要结论标明证据、地址类型（文件偏移/RVA/虚拟地址）、版本适用范围、置信度和验证状态；区分静态分析推断与运行时验证。
5. 报告应足以让下次分析者从二进制标识、Ghidra 项目和已知地址继续工作，不要只记录最终结论。

## 使用 REA 辅助分析

- REA 6.4.0 CLI 安装在 `D:\REA`，当前 Copilot runtime 的 MCP 注册在 `D:\VSCode\data\copilot\mcp-config.json`。更新注册后需完全重启 VS Code，才能在新会话中加载 MCP 工具。
- MCP 注册指向 `D:\ghidra_12.1.4` 和其内置 JDK 21，并将 Ghidra 分析期限设为 900 秒。Windows 上的 Ghidra provider 仍属实验性支持。
- 单独运行 CLI 时，先设置 Ghidra 与 JDK 路径；分析较大的 `game.dll` 时，REA 默认 330 秒期限可能不足，可显式延长：

  ```powershell
  $env:GHIDRA_INSTALL_DIR = 'D:\ghidra_12.1.4'
  $env:JAVA_HOME = 'D:\ghidra_12.1.4\jdk'
  $env:REA_GHIDRA_STARTUP_TIMEOUT_MS = '900000'
  & 'D:\REA\rea.cmd' doctor --provider ghidra
  & 'D:\REA\rea.cmd' function 'C:\path\to\game.dll' '0x6F7EF590' --provider ghidra
  ```

- Windows provider 要求目标位于固定本地 NTFS 卷。即使 U 盘 `D:` 使用 NTFS，它仍是可移动卷，不能直接作为分析目标；需暂存到固定本地卷，并在分析前确认副本 SHA-256 与原件一致。原始样本应保持不变。

## 当前分析

- [Warcraft III 1.27 Battle.net 按钮状态分析](analyses/warcraft-iii-1.27-battlenet-button.md)
- [DotA v6.83d SD 三选一英雄候选链路分析](analyses/dota-6.83d-single-draft-candidates.md)

## 注意事项

- Git 中仅保存文档、脚本和可公开分发的辅助材料；Ghidra `.rep` 数据库、游戏二进制和生成文件保持在本机。
- 重要分析结果提交前，确认报告中的地址和签名确实对应报告所列版本。
- 对运行时补丁，记录补丁位置、原始/替换字节、补丁机制及尚未完成的实机验证。
