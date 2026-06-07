@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
if not defined LAUNCHER_BASIC_AUTH_USER set "LAUNCHER_BASIC_AUTH_USER=launcher"             & rem Default Launcher username.
if not defined LAUNCHER_BASIC_AUTH_PASSWORD set "LAUNCHER_BASIC_AUTH_PASSWORD=launcher-pass" & rem Default Launcher password.
set "LAUNCHER_AUTH=%LAUNCHER_BASIC_AUTH_USER%:%LAUNCHER_BASIC_AUTH_PASSWORD%"              & rem Build user:password pair for curl.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run40] Check Nginx reverse proxy routes                  & rem Print script purpose.
echo ========================================================= & rem Print title separator.

call :check_url_basic "http://localhost:8080/launcher/"       & rem Check Launcher route through Nginx with Basic auth.
call :check_url "http://localhost:8080/app1/"                 & rem Check App1 route through Nginx.
call :check_url "http://localhost:8080/app2/"                 & rem Check App2 route through Nginx.
call :check_url "http://localhost:8080/app3/"                 & rem Check App3 route through Nginx.
call :check_url "http://localhost:8080/app4/"                 & rem Check App4 route through Nginx.

echo.                                                         & rem Print blank line.
echo [OK] Nginx route check finished.                          & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Subroutine that checks one URL.
:check_url
set "URL=%~1"                                                 & rem Read target URL from argument.
curl -fsS "%URL%" >nul 2>nul                                  & rem Request the URL and hide response body.
if errorlevel 1 goto :check_failed                            & rem Report failure when curl fails.
echo [OK] %URL%                                               & rem Print successful URL.
exit /b 0                                                     & rem Return success from subroutine.

rem ---------------------------------------------------------  & rem Subroutine that checks one URL with Basic auth.
:check_url_basic
set "URL=%~1"                                                 & rem Read target URL from argument.
curl -fsS -u "%LAUNCHER_AUTH%" "%URL%" >nul 2>nul          & rem Request the URL with Basic auth and hide response body.
if errorlevel 1 goto :check_failed                            & rem Report failure when curl fails.
echo [OK] %URL%                                               & rem Print successful URL.
exit /b 0                                                     & rem Return success from subroutine.

rem ---------------------------------------------------------  & rem Error branch for failed URL check.
:check_failed
echo [ERROR] %URL%                                            & rem Print failed URL.
exit /b 1                                                     & rem Return failure from subroutine.

