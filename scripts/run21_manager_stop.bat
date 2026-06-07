@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
set "PID_FILE=%ROOT%\.run\manager-api.pid"                    & rem PID file for Manager API.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run21] Stop host-side Manager API                        & rem Print script purpose.
echo ========================================================= & rem Print title separator.

if not exist "%PID_FILE%" goto :missing_pid                   & rem Stop cannot use PID file when it is missing.

for /f "usebackq delims=" %%P in ("%PID_FILE%") do set "PID=%%P"    & rem Read Manager API PID.
if not defined PID goto :missing_pid                          & rem Validate that PID was read.

powershell -NoProfile -ExecutionPolicy Bypass -Command "Stop-Process -Id %PID% -ErrorAction Stop"    & rem Stop the Manager API process.
if errorlevel 1 goto :failed                                  & rem Stop when process termination fails.

del "%PID_FILE%" >nul 2>nul                                   & rem Remove stale PID file.
echo [OK] Manager API was stopped.                            & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Branch when PID file is missing.
:missing_pid
echo [WARN] PID file was not found.                            & rem Explain that process may not be tracked.
echo If Manager API is still running, close its terminal manually.    & rem Show manual fallback.
exit /b 0                                                     & rem Exit without hard error.

rem ---------------------------------------------------------  & rem Error branch for stop failure.
:failed
echo [ERROR] Failed to stop Manager API by PID: %PID%          & rem Explain the error.
echo You may need to stop it manually from Task Manager.       & rem Show manual fallback.
exit /b 1                                                     & rem Exit with error.
