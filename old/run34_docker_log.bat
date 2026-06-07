REM ------------------------------------------------------------------------------
REM Purpose:
REM   Stream Docker Compose logs for the repository's container stack.
REM
REM What this script does:
REM   - Checks that docker and docker compose are available.
REM   - Runs docker compose logs -f so the terminal follows container output.
REM
REM Notes:
REM   - This is useful after a detached launch from run32_docker_start_prd.bat.
REM   - Use Ctrl+C to stop following the log stream.
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "RUN34_SCRIPT_VERSION=v0.1.0"

cd /d %~dp0

echo ========================================
echo   YouTubeTranscripter Docker Compose Logs
echo ========================================
echo Script version : %RUN34_SCRIPT_VERSION%
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

REM Show logs
docker compose logs -f

endlocal