REM ------------------------------------------------------------------------------
REM Purpose:
REM   Stop and remove the Docker Compose stack for this repository.
REM
REM What this script does:
REM   - Checks that docker and docker compose are available.
REM   - Runs docker compose down to stop and remove the containers created by
REM     the compose workflow.
REM
REM Notes:
REM   - This script only targets the Docker Compose stack.
REM   - It does not manage the optional local frontend PID file used by stop_app.sh.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN33_SCRIPT_VERSION=v0.1.0"

cd /d %~dp0

echo ========================================
echo   YouTubeTranscripter Docker Compose Stop
echo ========================================
echo Script version : %RUN33_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo [Error] docker command not found in PATH.
    exit /b 1
)

docker compose version >nul 2>nul
if errorlevel 1 (
    echo [Error] docker compose is not available.
    exit /b 1
)

REM Stop and remove containers
docker compose down

endlocal
