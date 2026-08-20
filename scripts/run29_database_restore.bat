@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

if "%~1"=="" goto :usage                                    & rem Require an explicit custom-format dump path.
if not exist "%~1" goto :missing                             & rem Refuse a missing dump path.
set /p "CONFIRM=Type RESTORE to replace the external DB from %~1: " & rem Require deliberate confirmation.
if /i not "%CONFIRM%"=="RESTORE" goto :cancelled             & rem Abort unless the exact confirmation was entered.

set "REMOTE=/tmp/youtube-transcription-restore.dump"         & rem Use a container-side binary file.
docker compose -f database\docker-compose.yml cp "%~1" youtube-db:%REMOTE% & rem Copy the selected dump to the DB container.
if errorlevel 1 goto :failed                                  & rem Stop when the copy fails.
docker compose -f database\docker-compose.yml exec -T youtube-db sh -c "pg_restore -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" --clean --if-exists --no-owner %REMOTE%" & rem Restore only after explicit confirmation.
if errorlevel 1 goto :failed                                  & rem Stop when pg_restore fails.
docker compose -f database\docker-compose.yml exec -T youtube-db rm -f %REMOTE% >nul & rem Remove only the temporary container file.
echo [OK] Database restore completed.                          & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

:usage
echo Usage: run29_database_restore.bat path-to-dump             & rem Explain required input.
exit /b 1                                                     & rem Exit with usage error.

:missing
echo [ERROR] Dump file was not found: %~1                     & rem Explain the error.
exit /b 1                                                     & rem Exit with error.

:cancelled
echo [CANCELLED] Database restore was not confirmed.            & rem Explain the safe abort.
exit /b 1                                                     & rem Exit with cancellation.

:failed
echo [ERROR] Database restore failed.                           & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
