REM ------------------------------------------------------------------------------
REM Purpose:
REM   Validate that the Docker-based workflow is ready before starting or
REM   stopping the container stack.
REM
REM What this script does:
REM   - Checks that the docker command is present.
REM   - Checks that docker compose is available.
REM   - Verifies that the Docker daemon is reachable.
REM   - Confirms the repository contains the Dockerfiles and compose file used
REM     by the local container workflow.
REM
REM Notes:
REM   - This is a readiness check only; it does not start containers.
REM   - The next steps are run31_docker_start_dev.bat or run32_docker_start_prd.bat.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN30_SCRIPT_VERSION=v0.1.0"

cd /d %~dp0

echo ========================================
echo   YouTubeTranscripter Docker Init
echo ========================================
echo Script version : %RUN30_SCRIPT_VERSION%
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

if not exist Dockerfile.api (
	echo [Error] Dockerfile.api not found.
	exit /b 1
)

if not exist Dockerfile.worker (
	echo [Error] Dockerfile.worker not found.
	exit /b 1
)

if not exist docker-compose.yml (
	echo [Error] docker-compose.yml not found.
	exit /b 1
)

echo [OK] Docker daemon and compose files are ready.
echo Next: run31_docker_start_dev.bat or run32_docker_start_prd.bat
echo.
endlocal
