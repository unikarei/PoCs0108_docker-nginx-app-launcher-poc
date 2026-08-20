@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run30] Check Docker and project files                    & rem Print script purpose.
echo ========================================================= & rem Print title separator.

where docker >nul 2>nul                                       & rem Check whether Docker command exists.
if errorlevel 1 goto :docker_missing                         & rem Stop when Docker command is missing.

docker --version                                              & rem Print Docker version.
docker compose version                                        & rem Print Docker Compose version.
docker info >nul 2>nul                                        & rem Check whether Docker Engine is running.
if errorlevel 1 goto :docker_not_running                      & rem Stop when Docker Engine is not running.

docker network inspect youtube_transcripter_net >nul 2>nul     & rem Check the shared internal network.
if errorlevel 1 docker network create youtube_transcripter_net >nul 2>nul & rem Create it once when absent.
if errorlevel 1 goto :network_create_failed                   & rem Stop when network creation fails.

if exist "docker-compose.yml" echo [OK] docker-compose.yml exists.          & rem Check Compose file.
if not exist "docker-compose.yml" echo [WARN] docker-compose.yml is missing. & rem Warn when Compose file is missing.
if exist "nginx\nginx.conf" echo [OK] nginx\nginx.conf exists.              & rem Check Nginx config.
if not exist "nginx\nginx.conf" echo [WARN] nginx\nginx.conf is missing.    & rem Warn when Nginx config is missing.
if exist "launcher\Dockerfile" echo [OK] launcher Dockerfile exists.        & rem Check Launcher Dockerfile.
if not exist "launcher\Dockerfile" echo [WARN] launcher Dockerfile is missing.    & rem Warn when Launcher Dockerfile is missing.
if exist "apps\app1\Dockerfile" echo [OK] app1 Dockerfile exists.          & rem Check App1 Dockerfile.
if not exist "apps\app1\Dockerfile" echo [WARN] app1 Dockerfile is missing. & rem Warn when App1 Dockerfile is missing.
if exist "apps\app2\Dockerfile" echo [OK] app2 Dockerfile exists.          & rem Check App2 Dockerfile.
if not exist "apps\app2\Dockerfile" echo [WARN] app2 Dockerfile is missing. & rem Warn when App2 Dockerfile is missing.
if exist "apps\app3\Dockerfile" echo [OK] app3 Dockerfile exists.          & rem Check App3 Dockerfile.
if not exist "apps\app3\Dockerfile" echo [WARN] app3 Dockerfile is missing. & rem Warn when App3 Dockerfile is missing.
if exist "apps\app4\Dockerfile" echo [OK] app4 Dockerfile exists.          & rem Check App4 Dockerfile.
if not exist "apps\app4\Dockerfile" echo [WARN] app4 Dockerfile is missing. & rem Warn when App4 Dockerfile is missing.
if exist "manager-api\src\main.py" echo [OK] manager-api source exists.      & rem Check Manager API source.
if not exist "manager-api\src\main.py" echo [WARN] manager-api source is missing. & rem Warn when Manager API source is missing.

echo.                                                         & rem Print blank line.
echo [OK] Docker basic check finished.                         & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for missing Docker command.
:docker_missing
echo [ERROR] docker command was not found.                     & rem Explain the error.
echo Install or start Docker Desktop first.                    & rem Show next action.
exit /b 1                                                     & rem Exit with error.

rem ---------------------------------------------------------  & rem Error branch for shared network creation.
:network_create_failed
echo [ERROR] Could not create youtube_transcripter_net.         & rem Explain the error.
exit /b 1                                                     & rem Exit with error.

rem ---------------------------------------------------------  & rem Error branch for stopped Docker Engine.
:docker_not_running
echo [ERROR] Docker Engine is not running.                     & rem Explain the error.
echo Start Docker Desktop, then run this script again.         & rem Show next action.
exit /b 1                                                     & rem Exit with error.

