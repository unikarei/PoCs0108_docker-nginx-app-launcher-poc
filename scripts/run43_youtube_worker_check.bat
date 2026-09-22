@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run43] Check YouTube Celery worker                       & rem Print script purpose.
echo ========================================================= & rem Print title separator.

set /a ATTEMPTS=0                                             & rem Count health-check attempts.
:retry
set "RESULT=WAIT"                                            & rem Clear the previous attempt result.
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "try { $r = Invoke-RestMethod -Uri 'http://localhost:8080/youtube/api-proxy/health/' -TimeoutSec 3; if ($r.status -eq 'healthy' -and $r.redis -match 'workers=[1-9]') { 'OK' } else { 'WAIT' } } catch { 'WAIT' }"`) do set "RESULT=%%H" & rem Read routed API health.
if /I "%RESULT%"=="OK" goto :success                         & rem Finish when a worker is reported.
set /a ATTEMPTS+=1                                            & rem Increment retry count.
if %ATTEMPTS% GEQ 30 goto :failed                             & rem Fail after roughly one minute.
timeout /t 2 /nobreak >nul                                   & rem Allow containers to start.
goto :retry                                                   & rem Try health again.

:success
echo [OK] YouTube API and Celery worker are healthy.            & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

:failed
echo [ERROR] YouTube Celery worker did not become healthy.      & rem Explain the failure.
echo         Check: docker compose logs youtube-transcripter-worker & rem Show recovery command.
exit /b 1                                                     & rem Exit with error.
