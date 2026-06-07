@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
set "SERVICE=%~1"                                             & rem Optional service name from first argument.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run34] Show Docker logs                                  & rem Print script purpose.
echo ========================================================= & rem Print title separator.

if not exist "docker-compose.yml" goto :missing_compose       & rem Require docker-compose.yml.

if "%SERVICE%"=="" goto :all_logs                             & rem Show all logs when no service is specified.

docker compose logs -f "%SERVICE%"                            & rem Follow logs for one service.
exit /b %ERRORLEVEL%                                          & rem Return Docker Compose exit code.

rem ---------------------------------------------------------  & rem Branch for all service logs.
:all_logs
docker compose logs -f                                        & rem Follow logs for all services.
exit /b %ERRORLEVEL%                                          & rem Return Docker Compose exit code.

rem ---------------------------------------------------------  & rem Error branch for missing Compose file.
:missing_compose
echo [ERROR] docker-compose.yml was not found.                 & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
