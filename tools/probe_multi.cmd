@echo off
rem Multi-TU probe: one file per function, linked in source order.
rem usage: probe_multi.cmd ["<vcvarsall.bat>" ["<toolset dir>"]]
rem Same env bootstrap as probe_toolset.cmd: the individual toolset component
rem ships no vcvarsall, so borrow the SDK paths from Community.
setlocal enabledelayedexpansion
set "VCVARS=%~1"
set "FORCE_TOOLSET=%~2"
set "ENT_ROOT=C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise"
set "COM_ROOT=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community"

if not "%VCVARS%"=="" goto have_vcvars
if exist "%ENT_ROOT%\VC\Auxiliary\Build\vcvarsall.bat" goto use_ent
set "VCVARS=%COM_ROOT%\VC\Auxiliary\Build\vcvarsall.bat"
if not "%FORCE_TOOLSET%"=="" goto have_vcvars
for /d %%D in ("%ENT_ROOT%\VC\Tools\MSVC\14.29.*") do set "FORCE_TOOLSET=%%~fD"
goto have_vcvars

:use_ent
set "VCVARS=%ENT_ROOT%\VC\Auxiliary\Build\vcvarsall.bat"

:have_vcvars
if not exist "%VCVARS%" goto no_vcvars
cd /d "%~dp0.."
if not exist ".build\multi_probe" mkdir ".build\multi_probe"
python tools\split_multi_tu.py --src ConsoleApplication1.c --out .build\multi_probe >nul
if errorlevel 1 goto tu_failed

call "%VCVARS%" x86 -vcvars_ver=14.29 >nul
if errorlevel 1 goto vcvars_failed
if "%FORCE_TOOLSET%"=="" goto env_ready
if not exist "%FORCE_TOOLSET%\bin\Hostx64\x86\cl.exe" goto bad_toolset
set "PATH=%FORCE_TOOLSET%\bin\Hostx64\x86;%PATH%"
set "INCLUDE=%FORCE_TOOLSET%\include;%INCLUDE%"
set "LIB=%FORCE_TOOLSET%\lib\x86;%LIB%"
echo == forced toolset "%FORCE_TOOLSET%"

:env_ready
cl /Bv 2>&1 | findstr /i /c:"c1.dll"

cd /d ".build\multi_probe"
cl /nologo /c /ZI /Od /RTC1 /GS /MDd /JMC /W3 /D WIN32 /D _DEBUG /D _CONSOLE init_level1.c init_level2.c init_level0.c handle_input.c move_and_push.c move_player.c draw_map.c count_remaining_boxes.c main.c >nul
if errorlevel 1 goto cl_failed

link /nologo /DEBUG /INCREMENTAL /MANIFEST:EMBED /subsystem:console /out:m.exe /pdb:m.pdb /map:m.map init_level1.obj init_level2.obj init_level0.obj handle_input.obj move_and_push.obj move_player.obj draw_map.obj count_remaining_boxes.obj main.obj >nul
if errorlevel 1 goto link_failed

cd /d "%~dp0.."
echo == user function order
python tools\probe_order.py ".build\multi_probe\m.map"
exit /b 0

:no_vcvars
echo MISSING_VCVARS=%VCVARS%
exit /b 2

:bad_toolset
echo BAD_TOOLSET=%FORCE_TOOLSET%
exit /b 6

:tu_failed
echo TU_SPLIT_FAILED
exit /b 7

:vcvars_failed
echo VCVARS_FAILED
exit /b 3

:cl_failed
echo CL_FAILED
exit /b 4

:link_failed
echo LINK_FAILED
exit /b 5
