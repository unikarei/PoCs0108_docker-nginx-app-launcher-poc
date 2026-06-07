REM ------------------------------------------------------------------------------
REM Purpose:
REM   Add runtime dependencies required by the application, either through uv's
REM   dependency metadata or, when pyproject.toml is absent, directly into .venv.
REM
REM What this script does:
REM   - Verifies that uv is available.
REM   - Requires one or more package names as arguments.
REM   - Uses uv add when pyproject.toml exists.
REM   - Falls back to pip install inside .venv when the project is in requirements-
REM     file mode instead of pyproject-managed mode.
REM
REM Typical usage:
REM   - run16_uv_add_prd.bat numpy
REM   - run16_uv_add_prd.bat numpy scipy
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN16_SCRIPT_VERSION=v0.1.0"
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
echo      Add Production Packages
echo ========================================
echo Script version : %RUN16_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if "%~1"=="" (
    echo Usage: run16_uv_add_prd.bat ^<package^> [package2 ...]
    echo.
    echo Examples:
    echo   run16_uv_add_prd.bat numpy
    echo   run16_uv_add_prd.bat numpy scipy
    exit /b 1
)

if exist "%PYPROJECT%" (
    echo Adding runtime dependencies: %*
    uv add %*
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
    echo [OK] Runtime dependency added successfully.
) else (
    echo [Error] uv add failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
