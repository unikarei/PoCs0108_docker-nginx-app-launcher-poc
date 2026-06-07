REM ------------------------------------------------------------------------------
REM Purpose:
REM   Create or validate the local Python virtual environment used by the uv-
REM   based workflow for this repository.
REM
REM What this script does:
REM   - Creates .venv with Python 3.11 when no usable environment exists.
REM   - Skips recreation when a compatible .venv already exists.
REM   - Recreates the environment only when RUN10_FORCE_RECREATE=1 is set.
REM
REM What this script does not do:
REM   - It does not install dependencies.
REM   - It does not start the backend or frontend.
REM
REM Typical next step after a successful run:
REM   - run11_uv_sync.bat
REM   - then run20_start_backend_W.O._docker.bat and run21_start_frontend_W.O._docker.bat
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN10_SCRIPT_VERSION=v0.1.0"
set "ROOT=%~dp0"
set "VENV_DIR=%ROOT%.venv"
set "PY_TARGET=3.11"

cd /d %ROOT%

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    echo         Install uv first: https://docs.astral.sh/uv/
    exit /b 1
)

echo ========================================
echo         uv venv - Create Virtual Env
echo ========================================
echo Script version : %RUN10_SCRIPT_VERSION%
echo Project root   : %CD%
echo Venv path      : %VENV_DIR%
echo Python target  : %PY_TARGET%
echo.

if /I not "%RUN10_FORCE_RECREATE%"=="1" (
    if exist "%VENV_DIR%\Scripts\python.exe" (
        echo [OK] Existing virtual environment found. Skipping recreate.
        echo      To force recreate, run: set RUN10_FORCE_RECREATE=1 ^&^& run10_uv_venv.bat
        echo.
        echo Done! Next step:
        echo   .venv\Scripts\Activate.ps1  ^(PowerShell^)
        echo   .venv\Scripts\activate.bat  ^(Command Prompt^)
        echo.
        echo Then run:
        echo   run11_uv_sync.bat
        echo   run20_start_backend_W.O._docker.bat
        echo   run21_start_frontend_W.O._docker.bat
        echo.
        exit /b 0
    )
)

echo Running: uv venv .venv --python %PY_TARGET% --clear
echo.
uv venv .venv --python %PY_TARGET% --clear
if errorlevel 1 (
    echo.
    echo [Error] Failed to recreate .venv.
    echo         A process may be using files under .venv ^(e.g. uvicorn/run12^).
    echo         Stop running app processes and close shells using .venv, then retry.
    exit /b %ERRORLEVEL%
)

echo.
echo Done! Next step:
echo   .venv\Scripts\Activate.ps1  (PowerShell)
echo   .venv\Scripts\activate.bat  (Command Prompt)
echo.
echo Then run:
echo   run11_uv_sync.bat
echo   run12_app_start.bat
echo.

endlocal
