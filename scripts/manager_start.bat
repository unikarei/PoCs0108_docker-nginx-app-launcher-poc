@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%run20_manager_start.bat"
exit /b %ERRORLEVEL%
