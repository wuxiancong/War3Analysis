# 把 C:\War3Analysis 暂存区里可入库的文件收进本仓库对应目录。
# 不复制 game.dll（已由 samples/ 与 gitignore 管理）。
$ErrorActionPreference = "Stop"
$scratch = "C:\War3Analysis"
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not (Test-Path $scratch)) {
    Write-Host "no scratch: $scratch"
    exit 0
}

if (Test-Path "$scratch\scripts") {
    New-Item -ItemType Directory -Force -Path "$root\shared\scripts" | Out-Null
    Copy-Item -Force "$scratch\scripts\*.py" "$root\shared\scripts"
    Write-Host "copied scripts -> shared/scripts"
}
if (Test-Path "$scratch\ghidra-scripts") {
    New-Item -ItemType Directory -Force -Path "$root\shared\ghidra-scripts" | Out-Null
    Copy-Item -Force "$scratch\ghidra-scripts\*" "$root\shared\ghidra-scripts"
    Write-Host "copied ghidra-scripts -> shared/ghidra-scripts"
}

$art = "$root\artifacts\_scratch-$(Get-Date -Format 'yyyyMMdd')"
if (Test-Path "$scratch\rea-out") {
    New-Item -ItemType Directory -Force -Path $art | Out-Null
    Copy-Item -Force "$scratch\rea-out\*" $art
    Write-Host "copied rea-out -> $art （请改名为主题目录，例如 artifacts/warcraft-iii-1.27-fps-unlock）"
}
if (Test-Path "$scratch\snapshots") {
    New-Item -ItemType Directory -Force -Path $art | Out-Null
    Copy-Item -Force "$scratch\snapshots\*" $art
    Write-Host "copied snapshots -> $art"
}
Write-Host "done. reports still go to analyses/; patched dlls to dll_game/<version-change>/"
