@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run27] External YouTube database status                   & rem Print script purpose.
echo ========================================================= & rem Print title separator.

docker compose -f database\docker-compose.yml ps              & rem Show database container status.
if errorlevel 1 exit /b 1                                    & rem Propagate Compose failure.
docker volume ls --format "table {{.Name}}\t{{.Driver}}" | findstr /i "youtube-transcripter-db-data" & rem Show matching persistent volume.
exit /b 0                                                     & rem Exit successfully.
