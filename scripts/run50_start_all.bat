@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "SCRIPT_DIR=%~dp0"                                        & rem Directory that contains this script.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

set "SKIP_INIT=0"                                              & rem Run Docker/project checks by default.
set "SKIP_MANAGER=0"                                           & rem Start or verify Manager API by default.
set "SKIP_DATABASE=0"                                          & rem Start external database by default.
set "NO_BUILD=0"                                               & rem Rebuild images by default for backward compatibility.
set "SKIP_STATUS=0"                                            & rem Show Compose status by default.
set "SKIP_WORKER_CHECK=0"                                      & rem Verify worker health by default.

:parse_args
if "%~1"=="" goto :args_done                                   & rem Finish option parsing.
if /I "%~1"=="--quick" (
  set "SKIP_INIT=1"
  set "SKIP_DATABASE=1"
  set "NO_BUILD=1"
  set "SKIP_STATUS=1"
  shift
  goto :parse_args
)
if /I "%~1"=="--skip-init" (set "SKIP_INIT=1" & shift & goto :parse_args)
if /I "%~1"=="--skip-manager" (set "SKIP_MANAGER=1" & shift & goto :parse_args)
if /I "%~1"=="--skip-database" (set "SKIP_DATABASE=1" & shift & goto :parse_args)
if /I "%~1"=="--no-build" (set "NO_BUILD=1" & shift & goto :parse_args)
if /I "%~1"=="--skip-status" (set "SKIP_STATUS=1" & shift & goto :parse_args)
if /I "%~1"=="--skip-worker-check" (set "SKIP_WORKER_CHECK=1" & shift & goto :parse_args)
if /I "%~1"=="--help" goto :help
echo [ERROR] Unknown option: %~1
goto :usage

:args_done

echo ========================================================= & rem Print title separator.
echo [run50] Start all services                                & rem Print script purpose.
echo ========================================================= & rem Print title separator.

if "%SKIP_INIT%"=="0" call "%SCRIPT_DIR%run30_docker_init.bat" & rem Check Docker and key files.
if "%SKIP_INIT%"=="0" if errorlevel 1 goto :failed             & rem Stop when Docker check fails.
if "%SKIP_INIT%"=="1" echo [SKIP] Docker/project check.

if "%SKIP_MANAGER%"=="0" call "%SCRIPT_DIR%run20_manager_start.bat" & rem Start host-side Manager API.
if "%SKIP_MANAGER%"=="0" if errorlevel 1 goto :failed           & rem Stop when Manager API start fails.
if "%SKIP_MANAGER%"=="1" echo [SKIP] Manager API start.

if "%SKIP_MANAGER%"=="0" timeout /t 3 /nobreak >nul         & rem Wait for Manager API startup only when it was started.

if "%SKIP_DATABASE%"=="0" call "%SCRIPT_DIR%run25_database_start.bat" & rem Start the separately managed database.
if "%SKIP_DATABASE%"=="0" if errorlevel 1 goto :failed             & rem Stop when database start fails.
if "%SKIP_DATABASE%"=="1" echo [SKIP] External database start.

set "DOCKER_OPTIONS=--skip-database"                          & rem Database was handled by this script or intentionally skipped.
if "%NO_BUILD%"=="1" set "DOCKER_OPTIONS=%DOCKER_OPTIONS% --no-build" & rem Reuse existing images when requested.
call "%SCRIPT_DIR%run32_docker_start_detached.bat" %DOCKER_OPTIONS% & rem Start Docker services in background.
if errorlevel 1 goto :failed                                  & rem Stop when Docker start fails.

if "%SKIP_STATUS%"=="0" call "%SCRIPT_DIR%run35_docker_status.bat" & rem Show Docker service status.
if "%SKIP_STATUS%"=="1" echo [SKIP] Docker service status.

if "%SKIP_WORKER_CHECK%"=="0" call "%SCRIPT_DIR%run43_youtube_worker_check.bat" & rem Verify worker health.
if "%SKIP_WORKER_CHECK%"=="0" if errorlevel 1 goto :failed       & rem Stop when worker health fails.
if "%SKIP_WORKER_CHECK%"=="1" echo [SKIP] YouTube worker health check.

echo.                                                         & rem Print blank line.
echo [OK] All start commands finished.                         & rem Show success message.
echo Launcher: http://localhost:8080/launcher/                 & rem Show Launcher URL.
echo Manager : http://127.0.0.1:9000/health                   & rem Show Manager API health URL.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for failed step.
:failed
echo [ERROR] Start-all sequence failed.                        & rem Explain the error.
exit /b 1                                                     & rem Exit with error.

:help
echo Usage: run50_start_all.bat [options]
echo   --quick              Skip init, database start, status, and image build.
echo   --skip-init          Skip Docker/project file checks.
echo   --skip-manager       Skip Manager API start/check.
echo   --skip-database      Skip external database start.
echo   --no-build           Start containers without rebuilding images.
echo   --skip-status        Skip Docker Compose status display.
echo   --skip-worker-check  Skip YouTube worker health polling.
exit /b 0

:usage
echo Use --help to list supported options.
exit /b 2
