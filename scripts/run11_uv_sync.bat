@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
set "VENV_PY=%ROOT%\.venv\Scripts\python.exe"                 & rem Python interpreter inside root .venv.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run11] Sync Python dependencies with uv                  & rem Print script purpose.
echo ========================================================= & rem Print title separator.

where uv >nul 2>nul                                           & rem Check whether uv command is installed.
if errorlevel 1 goto :uv_missing                              & rem Stop when uv is not found.

if not exist "%VENV_PY%" goto :venv_missing                   & rem Require .venv before installing dependencies.

if exist "pyproject.toml" goto :sync_pyproject                & rem Prefer root pyproject when it exists.
goto :sync_requirements                                       & rem Otherwise install from requirements files.

rem ---------------------------------------------------------  & rem Install dependencies from pyproject.toml.
:sync_pyproject
uv sync                                                       & rem Synchronize root project dependencies.
if errorlevel 1 goto :failed                                  & rem Stop when uv sync fails.
goto :done                                                    & rem Finish after successful sync.

rem ---------------------------------------------------------  & rem Install dependencies from requirements files.
:sync_requirements
if exist "manager-api\requirements.txt" uv pip install -r "manager-api\requirements.txt"    & rem Install Manager API dependencies.
if exist "launcher\requirements.txt"    uv pip install -r "launcher\requirements.txt"       & rem Install Launcher dependencies.
if exist "apps\app1\requirements.txt"   uv pip install -r "apps\app1\requirements.txt"      & rem Install App1 dependencies.
if exist "apps\app2\requirements.txt"   uv pip install -r "apps\app2\requirements.txt"      & rem Install App2 dependencies.
if exist "apps\app3\requirements.txt"   uv pip install -r "apps\app3\requirements.txt"      & rem Install App3 dependencies.
if errorlevel 1 goto :failed                                  & rem Stop when any install command fails.
goto :done                                                    & rem Finish after requirements installation.

rem ---------------------------------------------------------  & rem Success branch.
:done
echo.                                                         & rem Print blank line.
echo [OK] Dependency sync finished.                            & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for missing uv.
:uv_missing
echo [ERROR] uv command was not found.                         & rem Explain the error.
exit /b 1                                                     & rem Exit with error.

rem ---------------------------------------------------------  & rem Error branch for missing .venv.
:venv_missing
echo [ERROR] .venv was not found.                              & rem Explain the error.
echo Run scripts\run10_uv_venv.bat first.                      & rem Show next action.
exit /b 1                                                     & rem Exit with error.

rem ---------------------------------------------------------  & rem Error branch for dependency failure.
:failed
echo [ERROR] Dependency sync failed.                            & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
