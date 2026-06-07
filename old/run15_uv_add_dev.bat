REM ------------------------------------------------------------------------------
REM Purpose:
REM   Add development-only dependencies to the project, either through uv's
REM   dependency metadata or, when pyproject.toml is absent, directly into .venv.
REM
REM What this script does:
REM   - Verifies that uv is available.
REM   - Requires one or more package names as arguments.
REM   - Uses uv add --group dev when pyproject.toml exists.
REM   - Falls back to pip install inside .venv when the project is in requirements-
REM     file mode instead of pyproject-managed mode.
REM
REM Typical usage:
REM   - run15_uv_add_dev.bat ruff
REM   - run15_uv_add_dev.bat mypy ruff
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN15_SCRIPT_VERSION=v0.1.0"
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "PYPROJECT=%ROOT%pyproject.toml"

cd /d %ROOT%

where uv >nul 2>nul
if errorlevel 1 (
    echo [Error] uv is not installed or not in PATH.
    exit /b 1
)

echo ========================================
echo       Add Dev Packages (--group dev)
echo ========================================
echo Script version : %RUN15_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if "%~1"=="" (
    echo Usage: run15_uv_add_dev.bat ^<package^> [package2 ...]
    echo.
    echo Examples:
    echo   run15_uv_add_dev.bat ruff
    echo   run15_uv_add_dev.bat mypy ruff
    exit /b 1
)

if exist "%PYPROJECT%" (
    echo Adding to dev group: %*
    uv add --group dev %*
) else (
    if not exist "%VENV_PY%" (
        echo [Info] .venv not found. Creating virtual environment first...
        uv venv .venv
        if errorlevel 1 exit /b %ERRORLEVEL%
    )
    "%VENV_PY%" -m pip --version >nul 2>nul
    if errorlevel 1 (
        echo [Info] pip not found in .venv. Bootstrapping pip...
        "%VENV_PY%" -m ensurepip --upgrade
        if errorlevel 1 exit /b %ERRORLEVEL%
    )
    echo [Info] pyproject.toml not found. Installing packages into .venv only.
    echo Running: "%VENV_PY%" -m pip install %*
    "%VENV_PY%" -m pip install %*
)
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
    echo [OK] Dev dependency added successfully.
) else (
    echo [Error] uv add --group dev failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
