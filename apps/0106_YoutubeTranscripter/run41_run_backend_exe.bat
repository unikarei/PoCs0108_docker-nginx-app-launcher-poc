@echo off
setlocal enableextensions

REM ------------------------------------------------------------------------------
REM Purpose:
REM   Launch the packaged backend EXE built by run40_build_backend_exe.bat.
REM
REM What this script does:
REM   - Verifies dist\yt_transcripter_backend.exe exists.
REM   - Launches the EXE from the repository root so relative paths and .env files
REM     resolve the same way as the other local launchers.
REM   - Fails fast with a clear message if the EXE has not been built yet.
REM ------------------------------------------------------------------------------

set "RUN41_SCRIPT_VERSION=v0.1.0"
set "ROOT=%~dp0"
set "EXE_PATH=%ROOT%dist\yt_transcripter_backend.exe"

cd /d "%ROOT%"

echo ========================================
echo      Run Backend EXE
echo ========================================
echo Script version : %RUN41_SCRIPT_VERSION%
echo Project root   : %CD%
echo.

if not exist "%EXE_PATH%" (
  echo [Error] EXE not found: %EXE_PATH%
  echo         Run run40_build_backend_exe.bat first.
  exit /b 1
)

echo Launching backend EXE...
echo EXE           : %EXE_PATH%
echo Press Ctrl+C to stop.
echo.

"%EXE_PATH%"

endlocal
exit /b %ERRORLEVEL%
