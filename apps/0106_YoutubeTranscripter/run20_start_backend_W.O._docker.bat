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
REM   - Performs preflight checks for DB/Redis and optional Celery worker ping.
REM   - Writes the selected backend port into .run_backend_port so the frontend
REM     launcher can automatically point to the correct API URL.
REM   - Starts uvicorn with --reload for iterative development.
REM
REM Environment variables:
REM   - RUN20_BACKEND_PORT: force a specific backend port.
REM   - RUN20_PREFLIGHT_STRICT: 1=fail on DB/Redis unreachable (default), 0=warn.
REM   - RUN20_CHECK_WORKER: 1=check Celery worker ping (default), 0=skip.
REM   - RUN20_REQUIRE_WORKER: 1=fail when no worker responds, 0=warn (default).
REM   - RUN20_DB_HOST / RUN20_DB_PORT: DB preflight target (default 127.0.0.1:5432).
REM   - RUN20_REDIS_HOST / RUN20_REDIS_PORT: Redis preflight target (default 127.0.0.1:6379).
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

if "%RUN20_PREFLIGHT_STRICT%"=="" set "RUN20_PREFLIGHT_STRICT=1"
if "%RUN20_CHECK_WORKER%"=="" set "RUN20_CHECK_WORKER=1"
if "%RUN20_REQUIRE_WORKER%"=="" set "RUN20_REQUIRE_WORKER=0"

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
rem Also normalize REDIS_URL from redis://redis:6379/... to localhost.
rem -----------------------------------------------------------------------------
if exist "%ROOT%.env" (
  for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%.env") do (
    if /I "%%A"=="DATABASE_URL" set "DATABASE_URL=%%B"
    if /I "%%A"=="REDIS_URL" set "REDIS_URL=%%B"
  )
)

if not defined DATABASE_URL (
  echo [Warn] DATABASE_URL not found in .env. Using existing process environment.
)

if defined DATABASE_URL set "DATABASE_URL=%DATABASE_URL:@postgres:=@127.0.0.1:%"
if defined REDIS_URL set "REDIS_URL=%REDIS_URL:redis://redis:=redis://127.0.0.1:%"

if defined REDIS_URL (
  set "CELERY_BROKER_URL=%REDIS_URL%"
  set "CELERY_RESULT_BACKEND=%REDIS_URL%"
)

set "DB_HOST=%RUN20_DB_HOST%"
if "%DB_HOST%"=="" set "DB_HOST=127.0.0.1"

set "DB_PORT=%RUN20_DB_PORT%"
if "%DB_PORT%"=="" set "DB_PORT=5432"

set "REDIS_HOST=%RUN20_REDIS_HOST%"
if "%REDIS_HOST%"=="" set "REDIS_HOST=127.0.0.1"

set "REDIS_PORT=%RUN20_REDIS_PORT%"
if "%REDIS_PORT%"=="" set "REDIS_PORT=6379"

echo Running preflight checks...
call :check_tcp "%DB_HOST%" "%DB_PORT%"
if errorlevel 1 (
  if "%RUN20_PREFLIGHT_STRICT%"=="1" (
    echo [Error] PostgreSQL unreachable at %DB_HOST%:%DB_PORT%. Start DB and retry.
    exit /b 1
  ) else (
    echo [Warn] PostgreSQL unreachable at %DB_HOST%:%DB_PORT%. Continuing due to RUN20_PREFLIGHT_STRICT=0.
  )
) else (
  echo [OK] PostgreSQL reachable at %DB_HOST%:%DB_PORT%
)

call :check_tcp "%REDIS_HOST%" "%REDIS_PORT%"
if errorlevel 1 (
  if "%RUN20_PREFLIGHT_STRICT%"=="1" (
    echo [Error] Redis unreachable at %REDIS_HOST%:%REDIS_PORT%. Start Redis and retry.
    exit /b 1
  ) else (
    echo [Warn] Redis unreachable at %REDIS_HOST%:%REDIS_PORT%. Continuing due to RUN20_PREFLIGHT_STRICT=0.
  )
) else (
  echo [OK] Redis reachable at %REDIS_HOST%:%REDIS_PORT%
)

if "%RUN20_CHECK_WORKER%"=="1" (
  set "WORKER_COUNT=0"
  for /f "usebackq delims=" %%W in (`cd /d "%BACKEND_DIR%" ^&^& "%VENV_PY%" -c "from worker import celery_app; i=celery_app.control.inspect(timeout=1); p=i.ping() if i else None; print(len(p) if p else 0)" 2^>nul`) do set "WORKER_COUNT=%%W"

  if !WORKER_COUNT! GTR 0 (
    echo [OK] Celery worker responded ^(workers=!WORKER_COUNT!^)
  ) else (
    if "%RUN20_REQUIRE_WORKER%"=="1" (
      echo [Error] No active Celery worker responded. Start worker and retry.
      exit /b 1
    ) else (
      echo [Warn] No active Celery worker responded. Jobs may stay queued.
    )
  )
)

echo.

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

goto :eof

:check_tcp
"%VENV_PY%" -c "import socket,sys; s=socket.create_connection((sys.argv[1], int(sys.argv[2])), 2.0); s.close()" %~1 %~2 >nul 2>nul
if errorlevel 1 (
  exit /b 1
)
exit /b 0
