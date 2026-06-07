@echo off
setlocal EnableExtensions
set "SCRIPT_DIR=%~dp0"

call "%SCRIPT_DIR%run50_start_all.bat"
exit /b %ERRORLEVEL%
