REM ------------------------------------------------------------------------------
REM Purpose:
REM   Start the Docker Compose stack in detached mode.
REM
REM What this script does:
REM   - Checks that docker, docker compose, and the daemon are available.
REM   - Runs docker compose up --build -d so the stack continues in the
REM     background after the terminal returns.
REM   - Uses the repository's docker-compose.yml and Dockerfiles to build the
REM     backend and worker images before starting the stack.
REM
REM Notes:
REM   - Use this when you want the containers to keep running after launch.
REM   - This script does not switch compose to a separate production profile;
REM     it uses the repository's current docker-compose.yml as-is.
REM   - Follow with run34_docker_log.bat if you want to tail logs later.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN32_SCRIPT_VERSION=v0.1.0"

cd /d %~dp0

echo ========================================
echo   YouTubeTranscripter Docker Compose (Detached)
echo ========================================
echo Script version : %RUN32_SCRIPT_VERSION%
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

docker info >nul 2>nul
if errorlevel 1 (
	echo [Error] Docker daemon is not reachable.
	echo         Start Docker Desktop and retry.
	exit /b 1
)

REM Start Docker Compose (detached)
docker compose up --build -d

endlocal