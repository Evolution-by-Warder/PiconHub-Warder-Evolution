@echo off
setlocal EnableExtensions
set "WARDER_PICON_FACTORY_ROOT=D:\WARDER-PICON-FACTORY"
rem Run the batch interpreter from a stable path OUTSIDE the replaceable APP.
if not "%WARDER_FACTORY_STABLE_BOOTSTRAP%"=="1" (
  copy /y "%~f0" "%WARDER_PICON_FACTORY_ROOT%\11-APP\FACTORY-STABLE-START.cmd" >nul
  if errorlevel 1 goto :failure
  set "WARDER_FACTORY_STABLE_BOOTSTRAP=1"
  call "%WARDER_PICON_FACTORY_ROOT%\11-APP\FACTORY-STABLE-START.cmd"
  exit /b %ERRORLEVEL%
)
cd /d "%WARDER_PICON_FACTORY_ROOT%\11-APP\WARDER-PICON-FACTORY"
if errorlevel 1 goto :failure
set "PYTHON="
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 -c "import sys; assert sys.version_info[:2] == (3,12)" >nul 2>nul
  if not errorlevel 1 set "PYTHON=py -3.12"
)
if not defined PYTHON (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys; assert sys.version_info[:2] == (3,12)" >nul 2>nul
    if not errorlevel 1 set "PYTHON=python"
  )
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
rem Keep the runtime OUTSIDE the versioned application folder so a full
rem engine/module update cannot remove the Python interpreter mid-launch.
set "WARDER_RUNTIME=%WARDER_PICON_FACTORY_ROOT%\11-APP\.factory-runtime-venv"
if not exist "%WARDER_RUNTIME%\Scripts\python.exe" (
  %PYTHON% -m venv "%WARDER_RUNTIME%"
  if errorlevel 1 goto :failure
)
if "%WARDER_FACTORY_SETUP_ONLY%"=="1" (
  "%WARDER_RUNTIME%\Scripts\python.exe" -m pip install --disable-pip-version-check -r "requirements-runtime.txt"
  if errorlevel 1 goto :failure
  exit /b 0
)
rem The updater is a short-lived process with an exclusive Factory lock.
"%WARDER_RUNTIME%\Scripts\python.exe" "factory_update_bootstrap.py"
rem The release may contain NEW engine modules and NEW runtime dependencies.
rem Install its requirements only after the update has been staged/activated.
"%WARDER_RUNTIME%\Scripts\python.exe" -m pip install --disable-pip-version-check -r "requirements-runtime.txt"
if errorlevel 1 goto :dependency_failure
"%WARDER_RUNTIME%\Scripts\python.exe" "factory_launcher.py"
set "EXITCODE=%ERRORLEVEL%"
if not "%EXITCODE%"=="0" pause
exit /b %EXITCODE%
:dependency_failure
echo Factory dependencies could not be installed; rolling back a pending update.
"%WARDER_RUNTIME%\Scripts\python.exe" -c "from factory_update_transaction import resolve; from workspace_paths import resolve_root,workspace_paths; print(resolve(workspace_paths(resolve_root())['app'],gui_ready=False))"
echo Factory runtime setup failed; no original picons or registry were changed.
pause
exit /b 1
:missing
echo Unable to install Python automatically. See README.md.
pause
exit /b 2
:failure
echo Factory setup failed. Existing source and output were not deleted.
pause
exit /b 1
