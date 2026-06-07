@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "SCRIPT_DIR=%~dp0"                                        & rem Directory that contains this script.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run50] Start all services                                & rem Print script purpose.
echo ========================================================= & rem Print title separator.

call "%SCRIPT_DIR%run30_docker_init.bat"                      & rem Check Docker and key files.
if errorlevel 1 goto :failed                                  & rem Stop when Docker check fails.

call "%SCRIPT_DIR%run20_manager_start.bat"                    & rem Start host-side Manager API.
if errorlevel 1 goto :failed                                  & rem Stop when Manager API start fails.

timeout /t 3 /nobreak >nul                                    & rem Wait a short time for Manager API startup.

call "%SCRIPT_DIR%run32_docker_start_detached.bat"            & rem Start Docker services in background.
if errorlevel 1 goto :failed                                  & rem Stop when Docker start fails.

call "%SCRIPT_DIR%run35_docker_status.bat"                    & rem Show Docker service status.

echo.                                                         & rem Print blank line.
echo [OK] All start commands finished.                         & rem Show success message.
echo Launcher: http://localhost:8080/launcher/                 & rem Show Launcher URL.
echo Manager : http://127.0.0.1:9000/health                   & rem Show Manager API health URL.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for failed step.
:failed
echo [ERROR] Start-all sequence failed.                        & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
