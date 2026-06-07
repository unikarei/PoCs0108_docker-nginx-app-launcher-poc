@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%run21_manager_stop.bat"
exit /b %ERRORLEVEL%
