@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run26] Stop external YouTube database                    & rem Print script purpose.
echo ========================================================= & rem Print title separator.

docker compose -f database\docker-compose.yml stop             & rem Stop the database without deleting its volume.
if errorlevel 1 goto :failed                                  & rem Stop when database stop fails.

echo [OK] External database stopped; volume was preserved.      & rem Show preservation message.
exit /b 0                                                     & rem Exit successfully.

:failed
echo [ERROR] External database stop failed.                     & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
