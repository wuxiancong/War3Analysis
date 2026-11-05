# War3 注入钩子后窗口标题变为 "W" / "w"

**日期**: 2026-11-03  
**现象**: 注入 `war3hook` 后，魔兽争霸 3 主窗口标题变成单个字母 `W`（或被描述为 `w`）；不注入时标题正常。  
**结论**: **不需要逆向 Game.dll / war3.exe 找“谁改了标题”**。根因在本仓库的窗口子类化 API 字符集用错。

## 根因

War3 1.2x 主窗口通过 ANSI API 创建：

- 窗口类名：`Warcraft III`（`FindWindowA("Warcraft III", NULL)` 可找到）
- `RegisterClassA` / `CreateWindowExA` → `IsWindowUnicode(hwnd) == FALSE`

`hooker/war3hook.cpp` 的 `startupHookWindow` 原先使用：

```cpp
g_oldWndProc = (WNDPROC)SetWindowLongPtrW(hWnd, GWLP_WNDPROC, (LONG_PTR)newWndProc);
// ...
return CallWindowProc(g_oldWndProc, hWnd, msg, wParam, lParam); // 常展开为 CallWindowProcW
```

按 MSDN《Subclassing and Automatic Message Translation》：

- `SetWindowLongPtrW` 会让子类窗口过程按 **Unicode** 接收带字符串的消息（含 `WM_SETTEXT`）
- 与 War3 原有的 **ANSI** 窗口/WndProc 混用后，标题字符串编码路径错乱

典型内存表现：宽字符串 `L"Warcraft III"` 为 `57 00 61 00 72 00 ...`；若被 ANSI 的 `SetWindowTextA` / ANSI `WM_SETTEXT` 路径按 `char*` 解读，会在第一个 `00` 处截断，标题只剩 **`W`**。

这与“未注入时正常、注入后才坏”完全吻合：只有 `startupHookWindow` 子类化之后才会踩中该路径。

## 为何不是游戏主动改标题？

全仓检索：

- `war3hook` **没有**调用 `SetWindowText*` / 发送 `WM_SETTEXT` 去改主窗口标题
- Launcher 侧对 War3 窗口只改 `GWL_STYLE`（去最小化框）等，不改 caption
- 面板“标题”均指自绘 UI 面板文案，与 Win32 窗口标题栏无关

因此 Ghidra/REA 去翻 Game.dll 里谁 `SetWindowText` **优先级低**；先修子类化字符集即可验证。

## 修复（已在 War3Launcher 工作区落地）

`hooker/war3hook.cpp` 的 `startupHookWindow` / `newWndProc` 已与 ANSI 窗口对齐：

1. `SetWindowLongPtrA(..., GWLP_WNDPROC, newWndProc)`（原为 `SetWindowLongPtrW`）
2. 全部转发改为 `CallWindowProcA(g_oldWndProc, ...)`（原为 `CallWindowProc` / 常展开为 W）
3. 挂钩前后打 `IsWindowUnicode` 日志，便于确认保持为 `0`

销毁路径里的 `SetWindowLongPtrW(..., DefWindowProcW)` 可保留（退出时切断原 WndProc，与标题无关）。

## 验证

1. 注入钩子启动游戏，任务栏/标题栏应为完整 `Warcraft III`（或原版标题），不再是单字母 `W`
2. 日志 `[WndProc 挂钩启动]` 中 `IsWindowUnicode=0`（保持 ANSI）
3. 进度面板防最小化、鼠标锁定、热键等 WndProc 功能仍正常

## 可选后续（仅当修复后仍复现）

再用 REA/Ghidra 或 API Monitor 钩 `user32!SetWindowText*` / `NtUserSetWindowText`，对比注入前后调用栈。当前证据表明 **不必先做这一步**。
