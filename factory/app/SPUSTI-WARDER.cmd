@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "WARDER_PICON_FACTORY_ROOT=D:\WARDER-PICON-FACTORY"
set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12)" >nul 2>nul
  if not errorlevel 1 set "PYTHON=py -3.12"
)
if not defined PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 set "PYTHON=python"
)
if not defined PYTHON (
  echo Python 3.12 is required. Installing via winget...
  where winget >nul 2>nul
  if errorlevel 1 goto :missing
  winget install --id Python.Python.3.12 --exact --source winget --accept-package-agreements --accept-source-agreements
  if errorlevel 1 goto :missing
  set "PYTHON=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
  if not exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" goto :missing
)
if not exist ".venv\Scripts\python.exe" (
  %PYTHON% -m venv ".venv"
  if errorlevel 1 goto :failure
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "requirements-runtime.txt"
if errorlevel 1 goto :failure
if "%WARDER_FACTORY_SETUP_ONLY%"=="1" exit /b 0
rem Run the updater in a separate short-lived process BEFORE starting the GUI.
rem This process exits before launcher starts, so no loaded app module is
rem replaced in-place while Windows is executing it.
".venv\Scripts\python.exe" -c "from factory_auto_update import attempt_update; from pathlib import Path; print('FACTORY UPDATE:', attempt_update(Path.cwd(), reporter=print))"
rem A failed/offline update must not prevent launching the installed Factory.
rem The launcher validates GUI readiness and rolls back a pending update.
".venv\Scripts\python.exe" "factory_launcher.py"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" pause
exit /b %EXITCODE%
:missing
echo Unable to install Python automatically. See README.md.
pause
exit /b 2
:failure
echo Factory setup failed. Existing source and output were not deleted.
pause
exit /b 1
