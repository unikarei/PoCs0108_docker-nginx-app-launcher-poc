@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run32] Start Docker services in background               & rem Print script purpose.
echo ========================================================= & rem Print title separator.

if not exist "docker-compose.yml" goto :missing_compose       & rem Require docker-compose.yml.

docker compose -f docker-compose.yml -f generated\docker-compose.apps.yml up --build -d & rem Build and start services.
if errorlevel 1 goto :failed                                  & rem Stop when Docker Compose fails.
docker compose -f docker-compose.yml -f generated\docker-compose.apps.yml up -d --force-recreate nginx & rem Refresh Nginx DNS after app recreation.
if errorlevel 1 goto :failed                                  & rem Stop when Nginx recreation fails.

echo.                                                         & rem Print blank line.
echo [OK] Docker services were started.                        & rem Show success message.
echo Launcher: http://localhost:8080/launcher/                 & rem Show Launcher URL.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for missing Compose file.
:missing_compose
echo [ERROR] docker-compose.yml was not found.                 & rem Explain the error.
exit /b 1                                                     & rem Exit with error.

rem ---------------------------------------------------------  & rem Error branch for Docker Compose failure.
:failed
echo [ERROR] docker compose up -d failed.                      & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
