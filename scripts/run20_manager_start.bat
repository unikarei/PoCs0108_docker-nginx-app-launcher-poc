@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
set "MANAGER_DIR=%ROOT%\manager-api"                          & rem Manager API folder.
set "VENV_PY=%ROOT%\.venv\Scripts\python.exe"                 & rem Python interpreter inside root .venv.
set "PID_DIR=%ROOT%\.run"                                     & rem Runtime folder for PID files.
set "PID_FILE=%PID_DIR%\manager-api.pid"                      & rem PID file for Manager API.
set "MANAGER_URL=http://127.0.0.1:9000/health"                & rem Health URL for Manager API.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run20] Start host-side Manager API                       & rem Print script purpose.
echo ========================================================= & rem Print title separator.

curl -fsS "%MANAGER_URL%" >nul 2>nul                          & rem Check whether Manager API is already running.
if not errorlevel 1 goto :already_running                     & rem Skip start when health check succeeds.

if not exist "%MANAGER_DIR%\src\main.py" goto :missing_main   & rem Require Manager API source file.
if not exist "%PID_DIR%" mkdir "%PID_DIR%"                    & rem Create runtime folder if missing.
if exist "%VENV_PY%" set "PYTHON_EXE=%VENV_PY%"               & rem Use .venv Python when available.
if not defined PYTHON_EXE set "PYTHON_EXE=python"             & rem Fall back to system Python.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$p=Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList '-m','uvicorn','src.main:app','--host','127.0.0.1','--port','9000' -WorkingDirectory '%MANAGER_DIR%' -PassThru; $p.Id | Out-File -Encoding ascii '%PID_FILE%'; Write-Host ('Manager API PID: ' + $p.Id)"    & rem Start Manager API and save PID.
if errorlevel 1 goto :failed                                  & rem Stop when PowerShell start fails.

echo.                                                         & rem Print blank line.
echo [OK] Manager API start command was issued.                & rem Show success message.
echo URL: http://127.0.0.1:9000/health                        & rem Show health check URL.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Branch when Manager API is already running.
:already_running
echo [OK] Manager API is already running.                      & rem Show existing status.
echo URL: %MANAGER_URL%                                       & rem Show health check URL.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for missing Manager API source.
:missing_main
echo [ERROR] Manager API source was not found.                 & rem Explain the error.
echo Missing: %MANAGER_DIR%\src\main.py                       & rem Show missing path.
exit /b 1                                                     & rem Exit with error.

rem ---------------------------------------------------------  & rem Error branch for start failure.
:failed
echo [ERROR] Failed to start Manager API.                      & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
