@echo off
setlocal
rem --- AI 修改开始 [GHIDRA-LAUNCHER]：从项目仓库启动便携版 Ghidra ---
if not defined GHIDRA_HOME set "GHIDRA_HOME=D:\ghidra_12.1.4"
if not exist "%GHIDRA_HOME%\ghidraRun.bat" (
    echo [错误] 找不到 Ghidra：%GHIDRA_HOME%\ghidraRun.bat
    echo 请设置 GHIDRA_HOME 为 Ghidra 安装目录后重试。
    exit /b 1
)
set "JAVA_HOME=%GHIDRA_HOME%\jdk"
call "%GHIDRA_HOME%\ghidraRun.bat"
exit /b %errorlevel%
rem --- AI 修改结束 [GHIDRA-LAUNCHER]：从项目仓库启动便携版 Ghidra ---
