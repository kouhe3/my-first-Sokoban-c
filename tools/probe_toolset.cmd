@echo off
rem Probe an arbitrary VS instance / v142 toolset against the reconstruct baseline.
rem usage: probe_toolset.cmd ["<vcvarsall.bat>" ["<toolset dir>" ["<extra cl flags>"]]]
rem
rem Installing only the "MSVC v142 ... (v14.29-16.10)" component drops the toolset
rem payload without VC\Auxiliary\Build\vcvarsall.bat. In that case bootstrap the
rem Windows SDK paths from the Community instance and prepend the wanted toolset
rem to PATH/INCLUDE/LIB so cl and link resolve there first.
rem Paths contain "(x86)", so avoid parenthesised if-blocks entirely.
setlocal enabledelayedexpansion
set "VCVARS=%~1"
set "FORCE_TOOLSET=%~2"
set "EXTRA_FLAGS=%~3"
if "%EXTRA_FLAGS%"=="" set "EXTRA_FLAGS=%EXTRA_CL_FLAGS%"
set "SRC=ConsoleApplication1.c"
if not "%PROBE_SRC%"=="" set "SRC=%PROBE_SRC%"
set "ENT_ROOT=C:\Program Files (x86)\Microsoft Visual Studio\2019\Enterprise"
set "COM_ROOT=C:\Program Files (x86)\Microsoft Visual Studio\2019\Community"

if not "%VCVARS%"=="" goto have_vcvars
if exist "%ENT_ROOT%\VC\Auxiliary\Build\vcvarsall.bat" goto use_ent_vcvars
set "VCVARS=%COM_ROOT%\VC\Auxiliary\Build\vcvarsall.bat"
if not "%FORCE_TOOLSET%"=="" goto have_vcvars
for /d %%D in ("%ENT_ROOT%\VC\Tools\MSVC\14.29.*") do set "FORCE_TOOLSET=%%~fD"
goto have_vcvars

:use_ent_vcvars
set "VCVARS=%ENT_ROOT%\VC\Auxiliary\Build\vcvarsall.bat"

:have_vcvars
if not exist "%VCVARS%" goto no_vcvars
cd /d "%~dp0.."
if not exist ".build\probe" mkdir ".build\probe"

call "%VCVARS%" x86 -vcvars_ver=14.29 >nul
if errorlevel 1 goto vcvars_failed

if "%FORCE_TOOLSET%"=="" goto env_ready
if not exist "%FORCE_TOOLSET%\bin\Hostx64\x86\cl.exe" goto bad_toolset
set "PATH=%FORCE_TOOLSET%\bin\Hostx64\x86;%PATH%"
set "INCLUDE=%FORCE_TOOLSET%\include;%INCLUDE%"
set "LIB=%FORCE_TOOLSET%\lib\x86;%LIB%"
echo == forced toolset "%FORCE_TOOLSET%"

:env_ready
echo == cl banner
cl /Bv 2>&1 | findstr /i /c:"c1.dll" /c:"link.exe"

if not "%EXTRA_FLAGS%"=="" echo == extra cl flags: %EXTRA_FLAGS%
echo == source: %SRC%
cl /nologo /c /ZI /Od /RTC1 /GS /MDd /JMC /W3 /D WIN32 /D _DEBUG /D _CONSOLE %EXTRA_FLAGS% /Fo".build\probe\probe.obj" "%SRC%"
if errorlevel 1 goto cl_failed

link /nologo /DEBUG /INCREMENTAL /MANIFEST:EMBED /subsystem:console /out:".build\probe\probe.exe" /pdb:".build\probe\probe.pdb" /map:".build\probe\probe.map" ".build\probe\probe.obj" >nul
if errorlevel 1 goto link_failed

echo == user function order
python tools\probe_order.py ".build\probe\probe.map"
exit /b 0

:no_vcvars
echo MISSING_VCVARS=%VCVARS%
exit /b 2

:bad_toolset
echo BAD_TOOLSET=%FORCE_TOOLSET%
exit /b 6

:vcvars_failed
echo VCVARS_FAILED
exit /b 3

:cl_failed
echo CL_FAILED
exit /b 4

:link_failed
echo LINK_FAILED
exit /b 5
