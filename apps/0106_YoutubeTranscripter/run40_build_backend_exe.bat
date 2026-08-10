@echo off
setlocal enableextensions

REM ------------------------------------------------------------------------------
REM Purpose:
REM   Build a one-file Windows executable for the FastAPI backend using
REM   PyInstaller.
REM
REM Output:
REM   dist\yt_transcripter_backend.exe
REM ------------------------------------------------------------------------------

set "RUN40_SCRIPT_VERSION=v0.1.2"
set "ROOT=%~dp0"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "ENTRY_FILE=%ROOT%backend\exe_main.py"
set "EXE_NAME=yt_transcripter_backend"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"

cd /d "%ROOT%"

echo ========================================
echo      Build Backend EXE (PyInstaller)
echo ========================================
echo Script version : %RUN40_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if not exist "%VENV_PY%" (
  echo [Error] .venv python not found: %VENV_PY%
  echo         Run run10_uv_venv.bat and run11_uv_sync.bat first.
  exit /b 1
)

if not exist "%ENTRY_FILE%" (
  echo [Error] Entry file not found: %ENTRY_FILE%
  exit /b 1
)

"%VENV_PY%" -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
  echo PyInstaller is not installed in .venv. Installing once...
  "%VENV_PY%" -m pip install pyinstaller
  if errorlevel 1 (
    echo [Error] Failed to install PyInstaller.
    exit /b 1
  )
) else (
  echo PyInstaller already installed. Skipping install step.
)

echo.
echo Running PyInstaller build...
"%VENV_PY%" -m PyInstaller --noconfirm --clean --onefile --name "%EXE_NAME%" --collect-submodules celery "%ENTRY_FILE%"
if errorlevel 1 (
  echo [Error] PyInstaller build failed.
  exit /b 1
)

if not exist "%ROOT%dist\%EXE_NAME%.exe" (
  echo [Error] Build finished but EXE not found: %ROOT%dist\%EXE_NAME%.exe
  exit /b 1
)

echo.
echo [OK] EXE build completed.
echo      %ROOT%dist\%EXE_NAME%.exe
exit /b 0
