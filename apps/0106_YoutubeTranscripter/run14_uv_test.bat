REM ------------------------------------------------------------------------------
REM Purpose:
REM   Run the project's pytest suite through the uv-managed Python environment.
REM
REM What this script does:
REM   - Verifies that uv is available.
REM   - Uses .venv\Scripts\python.exe when the local Windows venv exists.
REM   - Falls back to plain uv run when no local interpreter is available.
REM   - Runs pytest -v by default when no arguments are provided.
REM
REM Typical usage:
REM   - run14_uv_test.bat
REM   - run14_uv_test.bat tests/test_example.py -k name
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN14_SCRIPT_VERSION=v0.1.0"
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"

cd /d %ROOT%

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    exit /b 1
)

echo ========================================
echo            Run Tests with uv
echo ========================================
echo Script version : %RUN14_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if "%~1"=="" (
    if exist "%VENV_PY%" (
        echo Running: uv run --python "%VENV_PY%" pytest -v
        uv run --python "%VENV_PY%" pytest -v
    ) else (
        echo Running: uv run pytest -v
        uv run pytest -v
    )
) else (
    if exist "%VENV_PY%" (
        echo Running: uv run --python "%VENV_PY%" pytest %*
        uv run --python "%VENV_PY%" pytest %*
    ) else (
        echo Running: uv run pytest %*
        uv run pytest %*
    )
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] Test command completed successfully.
) else (
    echo [Warn] Test command finished with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
