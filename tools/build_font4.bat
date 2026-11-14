@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars32.bat" >nul
cd /d "D:\Qt\workspace\War3Analysis\tools"
cl /nologo /EHsc /O2 /DWIN32 /I"D:\Qt\workspace\War3Launcher\3rdparty\msvc\stormLib\include" extract_war3_font.cpp /Fe:extract_war3_font.exe /link /LIBPATH:"D:\Qt\workspace\War3Launcher\3rdparty\msvc\stormLib\lib" StormLib.lib zs.lib bz2.lib Advapi32.lib User32.lib Winmm.lib
