@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run41] Check application health endpoints                & rem Print script purpose.
echo ========================================================= & rem Print title separator.

call :check_url "http://localhost:8080/launcher/health"       & rem Check Launcher health endpoint.
call :check_url "http://localhost:8080/app1/health"           & rem Check App1 health endpoint.
call :check_url "http://localhost:8080/app2/health"           & rem Check App2 health endpoint.
call :check_url "http://localhost:8080/app3/health"           & rem Check App3 health endpoint.
call :check_url "http://localhost:8080/app4/health"           & rem Check App4 health endpoint.

echo.                                                         & rem Print blank line.
echo [OK] Application health check finished.                   & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Subroutine that checks one URL.
:check_url
set "URL=%~1"                                                 & rem Read target URL from argument.
curl -fsS "%URL%" >nul 2>nul                                  & rem Request the URL and hide response body.
if errorlevel 1 goto :check_failed                            & rem Report failure when curl fails.
echo [OK] %URL%                                               & rem Print successful URL.
exit /b 0                                                     & rem Return success from subroutine.

rem ---------------------------------------------------------  & rem Error branch for failed URL check.
:check_failed
echo [ERROR] %URL%                                            & rem Print failed URL.
exit /b 1                                                     & rem Return failure from subroutine.

