REM ------------------------------------------------------------------------------
REM Purpose:
REM   Synchronize the local .venv with the project dependency set recorded in
REM   requirements.txt / uv-managed metadata.
REM
REM What this script does:
REM   - Ensures uv is available.
REM   - Creates .venv if it does not exist.
REM   - Boots pip inside .venv if needed.
REM   - Installs runtime dependencies, including the psycopg2-binary wheel path.
REM
REM Typical usage:
REM   - Run after run10_uv_venv.bat
REM   - Run again whenever project dependencies change
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN11_SCRIPT_VERSION=v0.1.0"
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "REQ_FILE=%ROOT%requirements.txt"
set "PY_TARGET=3.11"

cd /d %ROOT%

where uv >nul 2>nul
if errorlevel 1 (
	echo [Error] uv is not installed or not in PATH.
	echo         Install uv first: https://docs.astral.sh/uv/
	exit /b 1
)

echo ========================================
echo      Install Dependencies (.venv)
echo ========================================
echo Script version : %RUN11_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if not exist "%REQ_FILE%" (
	echo [Error] requirements.txt not found: %REQ_FILE%
	exit /b 1
)

if not exist "%VENV_PY%" (
	echo [Info] .venv not found. Creating virtual environment first...
	uv venv .venv --python %PY_TARGET%
	if errorlevel 1 exit /b %ERRORLEVEL%
)

"%VENV_PY%" -m pip --version >nul 2>nul
if errorlevel 1 (
	echo [Info] pip not found in .venv. Bootstrapping pip...
	"%VENV_PY%" -m ensurepip --upgrade
	if errorlevel 1 exit /b %ERRORLEVEL%
)

echo Running: "%VENV_PY%" -m pip install --only-binary psycopg2-binary -r requirements.txt
"%VENV_PY%" -m pip install --only-binary psycopg2-binary -r requirements.txt
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
	echo [OK] Dependency installation completed successfully.
) else (
	echo [Error] Dependency installation failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%
