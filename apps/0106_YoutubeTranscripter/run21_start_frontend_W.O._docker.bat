@echo off
setlocal enableextensions enabledelayedexpansion

REM ------------------------------------------------------------------------------
REM Purpose:
REM   Start the local Next.js frontend without Docker and automatically point it
REM   at the backend port selected by run20_start_backend_W.O._docker.bat.
REM
REM What this script does:
REM   - Sets the frontend UI port to 3000 by default.
REM   - Allows RUN21_PORT (or legacy RUN20_PORT) to force a specific UI port.
REM   - Reads backend API port from .run_backend_port.
REM   - Fails fast when .run_backend_port is missing or empty.
REM   - Falls back to a free frontend port in the 3000-3010 range when the
REM     desired port is already occupied.
REM   - Installs frontend deps only when needed (first run or lockfile changed).
REM   - Exports NEXT_PUBLIC_API_URL so the frontend build/runtime can talk to
REM     the backend selected by the backend launcher.
REM
REM Environment variables:
REM   - RUN21_PORT: force the frontend UI port.
REM   - RUN20_PORT: legacy alias for the frontend UI port.
REM   - RUN21_REQUIRE_HEALTH: 1=require backend /health status=healthy (default), 0=skip.
REM
REM Notes:
REM   - Start run20 first when you want automatic API URL synchronization.
REM   - This script is the frontend half of the local no-Docker workflow.
REM ------------------------------------------------------------------------------

REM Launch this repository's frontend GUI (Next.js)
set "PORT=3000"
set "API_URL="
set "PORT_FROM_USER=0"
set "ROOT=%~dp0"
set "FRONTEND_DIR=%ROOT%frontend"
set "BACKEND_PORT_FILE=%ROOT%.run_backend_port"
set "NPM_HASH_CACHE_FILE=%FRONTEND_DIR%\.run21_npm_lock.sha256"
if "%RUN21_REQUIRE_HEALTH%"=="" set "RUN21_REQUIRE_HEALTH=1"

if not "%RUN21_PORT%"=="" (
  set "PORT=%RUN21_PORT%"
  set "PORT_FROM_USER=1"
) else if not "%RUN20_PORT%"=="" (
  set "PORT=%RUN20_PORT%"
  set "PORT_FROM_USER=1"
)

if exist "%BACKEND_PORT_FILE%" (
  set /p BACKEND_PORT=<"%BACKEND_PORT_FILE%"
  if not "!BACKEND_PORT!"=="" set "API_URL=http://127.0.0.1:!BACKEND_PORT!"
)

if "%API_URL%"=="" (
  echo [Error] Backend API URL is not resolved.
  echo         Start run20_start_backend_W.O._docker.bat first.
  exit /b 1
)

if "%RUN21_REQUIRE_HEALTH%"=="1" (
  set "HEALTH_OUTPUT="
  for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "$ErrorActionPreference='Stop'; try { $r = Invoke-RestMethod -Uri '%API_URL%/health' -TimeoutSec 5; if ($r.status -eq 'healthy') { 'healthy' } else { 'degraded: ' + ($r | ConvertTo-Json -Compress); exit 2 } } catch { 'unreachable: ' + $_.Exception.Message; exit 3 }"`) do set "HEALTH_OUTPUT=%%H"

  if errorlevel 1 (
    echo [Error] Backend health check failed: !HEALTH_OUTPUT!
    echo         Start backend dependencies ^(PostgreSQL/Redis/worker^) and retry.
    exit /b 1
  )
  echo [OK] Backend health is healthy.
)

cd /d "%ROOT%"

if not exist "%FRONTEND_DIR%\package.json" (
  echo [Error] frontend package.json not found: %FRONTEND_DIR%\package.json
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [Error] npm is not installed or not in PATH.
  echo         Install Node.js first: https://nodejs.org/
  exit /b 1
)

set "PORT_IN_USE=0"
netstat -ano | findstr /R /C:":%PORT% .*LISTENING" >nul
if not errorlevel 1 set "PORT_IN_USE=1"

if "%PORT_IN_USE%"=="1" (
  if "%PORT_FROM_USER%"=="1" (
    echo [Error] Port %PORT% is already in use.
    echo         Change RUN21_PORT/RUN20_PORT or stop the process using this port.
    exit /b 1
  )

  set "FREE_PORT="
  for /L %%P in (3000,1,3010) do (
    netstat -ano | findstr /R /C:":%%P .*LISTENING" >nul
    if errorlevel 1 (
      set "FREE_PORT=%%P"
      goto :FREE_PORT_FOUND
    )
  )

  :FREE_PORT_FOUND
  if "!FREE_PORT!"=="" (
    echo [Error] No free port found in range 3000-3010.
    echo         Stop conflicting processes or set RUN20_PORT to another free port.
    exit /b 1
  )
  echo [Warn] Port 3000 is already in use. Falling back to port !FREE_PORT!.
  set "PORT=!FREE_PORT!"
)

echo Starting Frontend GUI on http://127.0.0.1:%PORT% ...
echo API target: %API_URL%
echo Note: Start backend first with run20_start_backend_W.O._docker.bat
echo Press Ctrl+C to stop.
echo.

cd /d "%FRONTEND_DIR%"

set "CURRENT_LOCK_HASH="
set "CACHED_LOCK_HASH="
set "NEED_INSTALL=0"

if exist "package-lock.json" (
  for /f "tokens=1" %%H in ('certutil -hashfile "package-lock.json" SHA256 ^| findstr /R /I "^[0-9A-F][0-9A-F]"') do (
    set "CURRENT_LOCK_HASH=%%H"
    goto :LOCK_HASH_DONE
  )
)
:LOCK_HASH_DONE

if exist "%NPM_HASH_CACHE_FILE%" (
  set /p CACHED_LOCK_HASH=<"%NPM_HASH_CACHE_FILE%"
)

if not exist "node_modules" (
  set "NEED_INSTALL=1"
) else if not "!CURRENT_LOCK_HASH!"=="" if /I not "!CURRENT_LOCK_HASH!"=="!CACHED_LOCK_HASH!" (
  set "NEED_INSTALL=1"
)

if "!NEED_INSTALL!"=="1" (
  if exist "package-lock.json" (
    echo [Info] Installing frontend dependencies ^(npm ci^)...
    call npm ci --no-audit --fund=false
    if errorlevel 1 exit /b %ERRORLEVEL%
  ) else (
    echo [Info] package-lock.json not found. Running npm install...
    call npm install --no-audit --fund=false
    if errorlevel 1 exit /b %ERRORLEVEL%
  )

  if not "!CURRENT_LOCK_HASH!"=="" (
    > "%NPM_HASH_CACHE_FILE%" echo !CURRENT_LOCK_HASH!
  )
) else (
  echo [Info] Frontend dependencies are up-to-date. Skipping npm install.
)

set "NEXT_PUBLIC_API_URL=%API_URL%"
call npm run dev -- --hostname 127.0.0.1 --port %PORT%

endlocal
