@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%run35_docker_status.bat"
exit /b %ERRORLEVEL%
