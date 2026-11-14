@echo off
rem 用法: dis_range.cmd <pe> <startVA hex 0x...> <endVA hex 0x...>
rem 使用 MSVC dumpbin 做定点反汇编（无需 capstone）
set "DUMPBIN=C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.52.37025\bin\Hostx86\x86\dumpbin.exe"
"%DUMPBIN%" /nologo /DISASM /RANGE:%2,%3 "%~1"
