REM ------------------------------------------------------------------------------
REM Purpose:
REM   Start the Docker Compose stack in development mode and keep the logs in
REM   the current terminal.
REM
REM What this script does:
REM   - Checks that docker, docker compose, and the daemon are available.
REM   - Runs docker compose up --build in the foreground.
REM   - Uses the repository's docker-compose.yml and Dockerfiles to build the
REM     backend and worker images before starting the stack.
REM
REM Notes:
REM   - Use this when you want to see live container logs in the terminal.
REM   - The companion detached launcher is run32_docker_start_prd.bat.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN31_SCRIPT_VERSION=v0.1.0"

cd /d %~dp0

echo ========================================
echo   YouTubeTranscripter Docker Compose (Dev)
echo ========================================
echo Script version : %RUN31_SCRIPT_VERSION%
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

REM Start Docker Compose (foreground)
docker compose up --build

endlocal