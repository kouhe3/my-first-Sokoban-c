@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\18\Insiders\VC\Auxiliary\Build\vcvarsall.bat" x86 -vcvars_ver=14.29 >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
if not exist Debug mkdir Debug
if errorlevel 1 exit /b 1
cl /nologo /c /ZI /Od /RTC1 /GS /MDd /JMC /W3 /D WIN32 /D _DEBUG /D _CONSOLE /FoDebug\ConsoleApplication1.obj ConsoleApplication1.c
if errorlevel 1 exit /b 1
link /nologo /DEBUG /INCREMENTAL /MANIFEST:EMBED /subsystem:console /out:Debug\ConsoleApplication1.exe /pdb:Debug\ConsoleApplication1.pdb /map:Debug\ConsoleApplication1.map Debug\ConsoleApplication1.obj
if errorlevel 1 exit /b 1
echo BUILD_OK
