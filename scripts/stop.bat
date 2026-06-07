@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%run51_stop_all.bat"
exit /b %ERRORLEVEL%
