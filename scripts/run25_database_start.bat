@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run25] Start external YouTube database                   & rem Print script purpose.
echo ========================================================= & rem Print title separator.

docker network inspect youtube_transcripter_net >nul 2>nul     & rem Require the stable shared network.
if errorlevel 1 docker network create youtube_transcripter_net >nul 2>nul & rem Create the network when absent.
if errorlevel 1 goto :failed                                  & rem Stop when network creation fails.

docker compose -f database\docker-compose.yml up -d           & rem Start only the database service and preserve its volume.
if errorlevel 1 goto :failed                                  & rem Stop when database start fails.

echo [OK] External database is running.                        & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

:failed
echo [ERROR] External database start failed.                    & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
