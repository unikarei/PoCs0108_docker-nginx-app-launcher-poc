@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "SCRIPT_DIR=%~dp0"                                        & rem Directory that contains this script.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run51] Stop all services                                 & rem Print script purpose.
echo ========================================================= & rem Print title separator.

call "%SCRIPT_DIR%run33_docker_stop.bat"                      & rem Stop Docker Compose services.
if errorlevel 1 goto :failed                                  & rem Stop when Docker stop fails.

call "%SCRIPT_DIR%run26_database_stop.bat"                    & rem Stop the separately managed database without removing its volume.
if errorlevel 1 goto :failed                                  & rem Stop when database stop fails.

call "%SCRIPT_DIR%run21_manager_stop.bat"                     & rem Stop host-side Manager API.
if errorlevel 1 goto :failed                                  & rem Stop when Manager API stop fails.

echo.                                                         & rem Print blank line.
echo [OK] All stop commands finished.                          & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for failed step.
:failed
echo [ERROR] Stop-all sequence failed.                         & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
