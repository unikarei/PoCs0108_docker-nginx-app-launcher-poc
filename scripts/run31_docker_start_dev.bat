@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run31] Start Docker services in foreground               & rem Print script purpose.
echo ========================================================= & rem Print title separator.
echo Press Ctrl+C to stop foreground logs.                     & rem Explain foreground behavior.

if not exist "docker-compose.yml" goto :missing_compose       & rem Require docker-compose.yml.

docker compose up --build                                     & rem Build and start services with foreground logs.
if errorlevel 1 goto :failed                                  & rem Stop when Docker Compose fails.

exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for missing Compose file.
:missing_compose
echo [ERROR] docker-compose.yml was not found.                 & rem Explain the error.
exit /b 1                                                     & rem Exit with error.

rem ---------------------------------------------------------  & rem Error branch for Docker Compose failure.
:failed
echo [ERROR] docker compose up failed.                         & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
