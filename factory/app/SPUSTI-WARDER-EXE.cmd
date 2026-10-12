@echo off
setlocal EnableExtensions

set "WARDER_ROOT=D:\WARDER-PICON-FACTORY"
set "APP_DIR=%WARDER_ROOT%\11-APP\WARDER-PICON-FACTORY"
set "WARDER_EXE=%APP_DIR%\WARDER-PICON-FACTORY.exe"
set "WARDER_UPDATER=%APP_DIR%\WARDER-PICON-UPDATER.exe"
set "APP_LAUNCHER=%APP_DIR%\SPUSTI-WARDER-EXE.cmd"

if not exist "%WARDER_EXE%" (
 echo CHYBA: Factory EXE nebolo najdene:
 echo %WARDER_EXE%
 pause
 exit /b 2
)

rem Activate updater staged by the previous verified update.
if exist "%APP_DIR%\WARDER-PICON-UPDATER.exe.pending" (
 move /Y "%APP_DIR%\WARDER-PICON-UPDATER.exe.pending" "%WARDER_UPDATER%" >nul 2>nul
)

rem Keep the release launcher in the application directory current as well.
if exist "%APP_DIR%\SPUSTI-WARDER-EXE.cmd.pending" (
 powershell.exe -NoProfile -NonInteractive -Command "try { Move-Item -LiteralPath '%APP_DIR%\SPUSTI-WARDER-EXE.cmd.pending' -Destination '%APP_LAUNCHER%' -Force -ErrorAction Stop } catch { exit 1 }" >nul 2>nul
)

rem The updater must run before Factory starts so the EXE can be replaced safely.
if exist "%WARDER_UPDATER%" (
 "%WARDER_UPDATER%"
 if errorlevel 1 exit /b %errorlevel%
)

if not exist "%WARDER_EXE%" (
 echo CHYBA: Factory EXE po aktualizacii nebolo najdene:
 echo %WARDER_EXE%
 pause
 exit /b 3
)

start "" /D "%APP_DIR%" "%WARDER_EXE%"
exit /b 0
