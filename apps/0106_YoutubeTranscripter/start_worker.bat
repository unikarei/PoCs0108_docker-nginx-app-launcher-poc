@echo off
REM Worker startup script for Windows local development

setlocal enableextensions enabledelayedexpansion
set "ROOT=%~dp0"

cd /d "%ROOT%"

REM Activate virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)

REM Local no-docker normalization for host-side DB/Redis access
if exist "%ROOT%.env" (
    for /f "usebackq tokens=1,* delims==" %%A in ("%ROOT%.env") do (
        if /I "%%A"=="DATABASE_URL" set "DATABASE_URL=%%B"
        if /I "%%A"=="REDIS_URL" set "REDIS_URL=%%B"
    )
)

if defined DATABASE_URL set "DATABASE_URL=%DATABASE_URL:@postgres:=@127.0.0.1:%"
if defined REDIS_URL set "REDIS_URL=%REDIS_URL:redis://redis:=redis://127.0.0.1:%"

if defined REDIS_URL (
    set "CELERY_BROKER_URL=%REDIS_URL%"
    set "CELERY_RESULT_BACKEND=%REDIS_URL%"
)

echo [start_worker] DATABASE_URL=%DATABASE_URL%
echo [start_worker] REDIS_URL=%REDIS_URL%

REM Start Celery worker
cd /d "%ROOT%backend"
celery -A worker worker --loglevel=info --concurrency=2 --pool=solo --queues=transcription,correction

endlocal
