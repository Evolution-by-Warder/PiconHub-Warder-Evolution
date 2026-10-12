@echo off
setlocal EnableExtensions
set "WARDER_ROOT=D:\WARDER-PICON-FACTORY"
set "WARDER_EXE=%WARDER_ROOT%\11-APP\WARDER-PICON-FACTORY.exe"
set "WARDER_UPDATER=%~dp0windows_exe_startup.py"
if not exist "%WARDER_EXE%" (
 echo Factory EXE missing: "%WARDER_EXE%"
 exit /b 2
)
if exist "%~dp0SPUSTI-WARDER-EXE.cmd.pending" (
 powershell.exe -NoProfile -NonInteractive -Command "try { Move-Item -LiteralPath '%~dp0SPUSTI-WARDER-EXE.cmd.pending' -Destination '%~dp0SPUSTI-WARDER-EXE.cmd' -Force -ErrorAction Stop } catch { exit 1 }" >nul 2>nul
)
if exist "%WARDER_UPDATER%" (
 where py >nul 2>nul
 if not errorlevel 1 py -3 "%WARDER_UPDATER%"
)
start "" /D "%WARDER_ROOT%\11-APP" "%WARDER_EXE%"
exit /b 0
