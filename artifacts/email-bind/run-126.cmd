@echo off
set "JAVA_HOME=D:\ghidra_12.1.4\jdk"
call "D:\ghidra_12.1.4\support\analyzeHeadless.bat" D:\Qt\workspace\War3Analysis\ghidra\projects War3_126 -import "D:\Qt\workspace\War3Launcher\versions\1.26.0.6401\Game.dll" -scriptPath D:\Qt\workspace\War3Analysis\shared\ghidra-scripts -postScript DumpEmailBind.java > D:\Qt\workspace\War3Analysis\artifacts\email-bind\headless-126.log 2>&1
