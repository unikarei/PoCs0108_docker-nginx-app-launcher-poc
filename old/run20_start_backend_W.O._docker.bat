@echo off
setlocal enableextensions enabledelayedexpansion

REM ------------------------------------------------------------------------------
REM Purpose:
REM   Start the local FastAPI backend without Docker, using uvicorn with
REM   --reload for development.
REM
REM What this script does:
REM   - Verifies the backend source file and local .venv interpreter exist.
REM   - Uses the default backend port 8502 unless RUN20_BACKEND_PORT is set.
REM   - If the requested port is occupied and the port came from the default or
REM     from auto-selection, scans 8502-8515 for the first free port.
REM   - Writes the selected backend port into .run_backend_port so the frontend
REM     launcher can automatically point to the correct API URL.
REM   - Starts uvicorn with --reload for iterative development.
REM
REM Environment variables:
REM   - RUN20_BACKEND_PORT: force a specific backend port.
REM
REM Notes:
REM   - This script is the backend half of the local no-Docker workflow.
REM   - run21_start_frontend_W.O._docker.bat reads the port sync file that this
REM     script writes.
REM ------------------------------------------------------------------------------

set "RUN20_SCRIPT_VERSION=v0.2.0"
set "ROOT=%~dp0"
set "BACKEND_DIR=%ROOT%backend"
set "VENV_PY=%ROOT%.venv\Scripts\python.exe"
set "UVICORN_HOST=127.0.0.1"
set "UVICORN_PORT=8502"
set "BACKEND_PORT_FROM_USER=0"
set "PORT_SYNC_FILE=%ROOT%.run_backend_port"

if not "%RUN20_BACKEND_PORT%"=="" (
  set "UVICORN_PORT=%RUN20_BACKEND_PORT%"
  set "BACKEND_PORT_FROM_USER=1"
)

cd /d "%ROOT%"

if not exist "%BACKEND_DIR%\main.py" (
  echo [Error] backend main module not found: %BACKEND_DIR%\main.py
  exit /b 1
)

if not exist "%VENV_PY%" (
  echo [Error] .venv python not found: %VENV_PY%
  echo         Run run10_uv_venv.bat and run11_uv_sync.bat first.
  exit /b 1
)

rem -----------------------------------------------------------------------------
rem Local launcher normalization:
rem Prefer DATABASE_URL from .env. If it points to @postgres:, rewrite to
rem @127.0.0.1: so host-side run20 can access docker-published PostgreSQL.
rem -----------------------------------------------------------------------------
if exist "%ROOT%.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%.env") do (
    if /I "%%A"=="DATABASE_URL" set "DATABASE_URL=%%B"
  )
)

if not defined DATABASE_URL (
  echo [Warn] DATABASE_URL not found in .env. Using existing process environment.
)

if defined DATABASE_URL (
  echo %DATABASE_URL% | findstr /I "@postgres:" >nul
  if not errorlevel 1 (
    set "DATABASE_URL=!DATABASE_URL:@postgres:=@127.0.0.1:!"
  )
)

echo ========================================
echo      Start YouTube Transcription FastAPI
echo ========================================
echo Script version : %RUN20_SCRIPT_VERSION%
echo Root           : %ROOT%
echo Backend dir    : %BACKEND_DIR%
echo Venv python    : %VENV_PY%

set "PORT_IN_USE=0"
netstat -ano | findstr /R /C:":%UVICORN_PORT% .*LISTENING" >nul
if not errorlevel 1 set "PORT_IN_USE=1"

if "%PORT_IN_USE%"=="1" (
  if "%BACKEND_PORT_FROM_USER%"=="1" (
    echo [Error] Backend port %UVICORN_PORT% is already in use.
    echo         Change RUN20_BACKEND_PORT or stop the process using this port.
    exit /b 1
  )

  set "FREE_PORT="
  for /L %%P in (8502,1,8515) do (
    netstat -ano | findstr /R /C:":%%P .*LISTENING" >nul
    if errorlevel 1 (
      set "FREE_PORT=%%P"
      goto :BACKEND_PORT_FOUND
    )
  )

  :BACKEND_PORT_FOUND
  if "!FREE_PORT!"=="" (
    echo [Error] No free backend port found in range 8502-8515.
    echo         Stop conflicting processes or set RUN20_BACKEND_PORT.
    exit /b 1
  )
  echo [Warn] Backend port 8502 is already in use. Falling back to !FREE_PORT!.
  set "UVICORN_PORT=!FREE_PORT!"
)

echo %UVICORN_PORT%>"%PORT_SYNC_FILE%"
if not exist "%PORT_SYNC_FILE%" (
  echo [Error] Failed to write backend port sync file: %PORT_SYNC_FILE%
  exit /b 1
)

echo URL            : http://%UVICORN_HOST%:%UVICORN_PORT%/
echo Sync file      : %PORT_SYNC_FILE%
echo.
echo Running FastAPI app with auto-reload...
echo.

cd /d "%BACKEND_DIR%"
"%VENV_PY%" -m uvicorn main:app --reload --host %UVICORN_HOST% --port %UVICORN_PORT%

endlocal
