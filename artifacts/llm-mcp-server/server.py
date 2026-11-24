# -*- coding: utf-8 -*-
"""
DotA 6.83d 大模型战略指挥层 MCP Server 原型（stdio 传输）。
使用官方 Python `mcp` SDK (FastMCP)，底层仅复用现有 War3Launcher RemoteControl (127.0.0.1:6120) 命令。
"""
import argparse
import json
import os
from typing import Optional

try:
    # 兼容官方 mcp SDK 2.x（MCPServer）
    from mcp.server.mcpserver import MCPServer
except ImportError:
    # 兼容官方 mcp SDK 1.x（FastMCP）
    from mcp.server.fastmcp import FastMCP as MCPServer

from rc_client import DEFAULT_LOG_DIR, DEFAULT_RC_PORT, DotaController, RemoteControlClient

mcp = MCPServer("dota-war3-commander")
_controller: Optional[DotaController] = None


def get_controller() -> DotaController:
    global _controller
    if _controller is None:
        port = int(os.environ.get("WAR3_RC_PORT", str(DEFAULT_RC_PORT)))
        log_dir = os.environ.get("WAR3_LOG_DIR", DEFAULT_LOG_DIR)
        _controller = DotaController(
            rc_client=RemoteControlClient(host="127.0.0.1", port=port),
            log_dir=log_dir,
        )
    return _controller


@mcp.tool()
def game_status() -> str:
    """查询 War3Launcher 状态机与 war3.exe 进程是否运行中。
    映射到 RemoteControl `status`。
    """
    return json.dumps(get_controller().game_status(), ensure_ascii=False, indent=2)


@mcp.tool()
def get_state(include_items: bool = True, max_visible_dist: float = 1800.0) -> str:
    """获取当前对局结构化摘要（英雄位置/血/蓝/等级/金钱/背包、视野内单位、游戏钟）。
    映射到 `units`（可选 `say -items`）并增量读取 `AiUnit.log` 与 `game_stats.log` 新增部分。
    所有写命令返回 OK 后，必须调用本工具确认是否真正生效。
    """
    return json.dumps(
        get_controller().get_state(include_items=include_items, max_visible_dist=max_visible_dist),
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def move_to(landmark: Optional[str] = None, x: Optional[float] = None, y: Optional[float] = None) -> str:
    """控制英雄移动到指定地标名（如 '中路一塔'、'radiant_mid_t1'、'上路符点'、'roshan'）或坐标 (x, y)。
    映射到 RemoteControl `move x y`。返回 OK 只表示命令已发出，需调用 get_state 确认英雄位置变化。
    """
    return json.dumps(get_controller().move_to(landmark=landmark, x=x, y=y), ensure_ascii=False, indent=2)


@mcp.tool()
def start_laning() -> str:
    """启动 hook AI 自动中单对线流程（出门装、插河道眼、补刀、买瓶、装符、用符、加点）。
    映射到 `say -score start laning`。返回 OK 只表示命令已发出，需调用 get_state 确认已接管。
    """
    return json.dumps(get_controller().start_laning(), ensure_ascii=False, indent=2)


@mcp.tool()
def stop() -> str:
    """停止 hook AI 自动对线流程。
    映射到 `say -score end`。返回 OK 只表示命令已发出，需调用 get_state 确认已停止。
    """
    return json.dumps(get_controller().stop(), ensure_ascii=False, indent=2)


@mcp.tool()
def buy(item_name: str) -> str:
    """购买指定名称/缩写的物品（如 'obs'、'tango'、'bottle'、'tp'、'boots'）。
    映射到 `say -buy <item_name>`。返回 OK 只表示命令已发出，需调用 get_state 确认背包变化。
    """
    return json.dumps(get_controller().buy(item_name), ensure_ascii=False, indent=2)


@mcp.tool()
def say(text: str) -> str:
    """发送队内聊天或白名单内的 hook 控制命令（以 '-' 开头时仅放行白名单前缀）。
    映射到 `say <text>`。返回 OK 只表示命令已发出，需调用 get_state 确认效果。
    """
    return json.dumps(get_controller().say(text), ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(description="DotA 6.83d War3 MCP Server (stdio)")
    parser.add_argument("--port", type=int, default=DEFAULT_RC_PORT, help="War3Launcher RemoteControl 端口（默认 6120）")
    parser.add_argument("--logs", type=str, default=DEFAULT_LOG_DIR, help="War3Launcher logs 目录")
    args = parser.parse_args()

    global _controller
    _controller = DotaController(
        rc_client=RemoteControlClient(host="127.0.0.1", port=args.port),
        log_dir=args.logs,
    )
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
