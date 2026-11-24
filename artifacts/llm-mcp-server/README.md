# DotA 6.83d 大模型战略指挥层 MCP Server 原型

最小可运行的 Python MCP Server（`stdio` 传输），通过现有 `War3Launcher` RemoteControl（`127.0.0.1:6120`）与日志增量解析，让 Claude Code / Gemini CLI / Antigravity 以「战略指挥层」参与对局，微操仍由 `hook.dll` 执行。

> **重要提示**：RemoteControl 返回 `OK` 只表示命令已发出，**不代表已在游戏内生效**；每次执行写工具后，大模型应调用 `get_state` 核对英雄坐标、背包或状态变化。

## 1. 环境安装

需要 Python 3.10+ 与官方 `mcp` SDK：

```powershell
pip install mcp
```

## 2. 在 Claude Code / Gemini 中配置

### Claude Code (`~/.claude.json` 或项目 `.mcp.json`)

```json
{
  "mcpServers": {
    "dota-war3": {
      "command": "python",
      "args": [
        "D:/Qt/workspace/War3Analysis/artifacts/llm-mcp-server/server.py",
        "--port", "6120",
        "--logs", "C:/War3Run/War3Launcher/logs"
      ]
    }
  }
}
```

### Gemini CLI / Antigravity (`settings.json` / MCP 配置)

```json
{
  "mcpServers": {
    "dota-war3": {
      "command": "python",
      "args": [
        "D:/Qt/workspace/War3Analysis/artifacts/llm-mcp-server/server.py",
        "--port", "6120",
        "--logs", "C:/War3Run/War3Launcher/logs"
      ]
    }
  }
}
```

> 若 Launcher 运行在 `D:\Qt\workspace\War3Launcher\build\Desktop_Qt_5_15_1_MSVC_32bit_Release_AI`，请将 `--logs` 改为对应目录下的 `logs`。

## 3. 暴露的工具清单

| MCP 工具 | 映射的 RemoteControl 命令 | 说明 |
| :--- | :--- | :--- |
| `game_status` | `status` + `war3.exe` 进程检测 | 查看 Launcher 状态机与游戏进程状态 |
| `get_state` | `units`（可选 `say -items`）+ 增量读 `AiUnit.log` / `game_stats.log` | 返回英雄位置/血/蓝/等级/金钱/背包、视野内单位、游戏钟 |
| `move_to` | `move x y` | 支持坐标或中英文地标名（见 `landmarks.json`，如 `中路一塔`、`上路符点`、`roshan`） |
| `start_laning` | `say -score start laning` | 交由 hook AI 执行补刀、装符、插眼 |
| `stop` | `say -score end` | 结束自动对线流程 |
| `buy` | `say -buy <item_name>` | 购买指定缩写/名称物品 |
| `say` | `say <text>` | 仅允许白名单命令前缀（`-score`、`-items`、`-buy`、`-use` 等）或普通聊天文本 |

## 4. 离线单元测试

不连接真实 `6120` 端口，也不启动 `war3.exe`；使用随机本地端口的假服务器和日志片段测试：

```powershell
python -m unittest discover -s D:\Qt\workspace\War3Analysis\artifacts\llm-mcp-server -p "test_*.py" -v
```
