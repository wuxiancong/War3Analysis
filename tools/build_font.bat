@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
cd /d "D:\Qt\workspace\War3Analysis\tools"
cl /nologo /EHsc /O2 /DWIN32 /D_UNICODE /DUNICODE /I"D:\Qt\workspace\War3Launcher\3rdparty\msvc\stormLib\include" extract_war3_font.cpp /Fe:extract_war3_font.exe /link /LIBPATH:"D:\Qt\workspace\War3Launcher\3rdparty\msvc\stormLib\lib" StormLib.lib zs.lib bz2.lib Advapi32.lib User32.lib > "D:\Qt\workspace\War3Analysis\tools\build_font.log" 2>&1
echo EXIT=!ERRORLEVEL!>> "D:\Qt\workspace\War3Analysis\tools\build_font.log"
