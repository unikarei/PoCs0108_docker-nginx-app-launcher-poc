REM ------------------------------------------------------------------------------
REM Purpose:
REM   Execute an arbitrary command through the repository's uv-managed Python
REM   environment without requiring manual activation of .venv.
REM
REM What this script does:
REM   - Verifies that uv is available.
REM   - Uses .venv\Scripts\python.exe when a Windows venv exists.
REM   - Falls back to plain uv run when no local interpreter is available.
REM
REM Typical usage:
REM   - run13_uv_run.bat python -m pip list
REM   - run13_uv_run.bat pytest -v
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN13_SCRIPT_VERSION=v0.1.0"
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"

cd /d %ROOT%

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    exit /b 1
)

if "%~1"=="" (
    echo Usage: run13_uv_run.bat ^<command^> [args ...]
    echo.
    echo Examples:
    echo   run13_uv_run.bat python -m pip list
    echo   run13_uv_run.bat pytest tests/test_phase1_api.py -v
    exit /b 1
)

echo ========================================
echo             uv run passthrough
echo ========================================
echo Script version : %RUN13_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if exist "%VENV_PY%" (
    echo Running: uv run --python "%VENV_PY%" %*
    uv run --python "%VENV_PY%" %*
) else (
    echo Running: uv run %*
    uv run %*
)
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] uv run command completed successfully.
) else (
    echo [Error] uv run command failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
