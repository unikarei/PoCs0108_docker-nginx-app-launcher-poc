@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "(Get-Date).ToString('yyyyMMdd-HHmmss')"`) do set "STAMP=%%T" & rem Create a sortable backup timestamp.
if not exist "backups" mkdir "backups"                      & rem Create the local backup directory.
set "REMOTE=/tmp/youtube-transcription-backup.dump"          & rem Use a container-side binary file to avoid text encoding.
set "LOCAL=backups\youtube-transcription-%STAMP%.dump"      & rem Choose the local backup path.

docker compose -f database\docker-compose.yml exec -T youtube-db sh -c "pg_dump -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" --format=custom -f %REMOTE%" & rem Create a custom-format dump inside the DB container.
if errorlevel 1 goto :failed                                  & rem Stop when pg_dump fails.
docker compose -f database\docker-compose.yml cp youtube-db:%REMOTE% "%LOCAL%" & rem Copy the binary dump to the host.
if errorlevel 1 goto :failed                                  & rem Stop when the copy fails.
docker compose -f database\docker-compose.yml exec -T youtube-db rm -f %REMOTE% >nul & rem Remove only the temporary container file.

echo [OK] Database backup created: %LOCAL%                     & rem Show the backup path.
exit /b 0                                                     & rem Exit successfully.

:failed
echo [ERROR] Database backup failed.                            & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
