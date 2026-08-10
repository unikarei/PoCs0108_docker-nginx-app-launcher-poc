REM ------------------------------------------------------------------------------
REM Purpose:
REM   Compatibility wrapper for dependency synchronization.
REM
REM What this script does:
REM   - Locates run11_uv_sync.bat in the same directory.
REM   - Delegates all arguments to that script unchanged.
REM   - Provides a stable alternate entry point for older runbooks or team docs
REM     that reference run17 instead of run11.
REM
REM Typical usage:
REM   - run17_uv_sync.bat
REM   - run17_uv_sync.bat (same args as run11_uv_sync.bat)
REM ------------------------------------------------------------------------------
@echo off
setlocal enableextensions
set "ROOT=%~dp0"
set "TARGET=%ROOT%run11_uv_sync.bat"
set "RUN17_SCRIPT_VERSION=v0.1.0"

cd /d %ROOT%

if not exist "%TARGET%" (
	echo [Error] Target script not found: %TARGET%
	exit /b 1
)

echo ========================================
echo        run17 wrapper - uv sync
echo ========================================
echo Script version : %RUN17_SCRIPT_VERSION%
echo Delegating to: run11_uv_sync.bat
echo.

call "%TARGET%" %*
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if "%EXIT_CODE%"=="0" (
	echo [OK] run17 wrapper completed successfully.
) else (
	echo [Error] run17 wrapper failed with exit code %EXIT_CODE%.
)
exit /b %EXIT_CODE%