@echo off
setlocal enableextensions enabledelayedexpansion
rem ========================================================================
rem Git Tag Script (run04_tag.bat)
rem - Create and push annotated tag (no commit)
rem - Create an annotated tag on the current HEAD and push only the tag
rem - Does not create a commit (use run03_commit.bat for commits)
rem ========================================================================

rem [1] Change directory to the script location (project root)
cd /d %~dp0

rem [2] Verify Git command is available
where git >nul 2>nul
if errorlevel 1 (
    echo [Error] Git is not installed or not in PATH.
    pause
    exit /b 1
)

rem [3] Ensure we are inside a Git repository
git rev-parse --is-inside-work-tree >nul 2>nul
if errorlevel 1 (
    echo [Error] This directory is not a Git repository.
    pause
    exit /b 1
)

rem [4] Get current branch and latest tag (for display/reference)
for /f "delims=" %%b in ('git rev-parse --abbrev-ref HEAD 2^>nul') do set CUR_BRANCH=%%b
if "%CUR_BRANCH%"=="" set CUR_BRANCH=main

set "LATEST_TAG="
for /f "tokens=1" %%i in ('git tag --sort^=-version:refname 2^>nul') do (
    set LATEST_TAG=%%i
    goto :found_tag
)
:found_tag
if "%LATEST_TAG%"=="" set LATEST_TAG=v0.0.0

echo ========================================
echo               Git Tag Script
echo ========================================
echo Current branch : %CUR_BRANCH%
echo Latest tag     : %LATEST_TAG%
echo.

rem [5] Prompt for a new tag version (e.g., v1.2.3)
set /p VERSION="Please enter NEW tag version (ex: v1.2.3): "
if "%VERSION%"=="" (
    echo [Error] Version cannot be empty.
    pause
    exit /b 1
)

rem [6] Validate the tag does not already exist (abort if duplicate)
git rev-parse -q --verify refs/tags/%VERSION% >nul 2>nul
if not errorlevel 1 (
    echo [Error] Tag %VERSION% already exists.
    pause
    exit /b 1
)

rem [7] Prompt for the tag annotation message (concise release notes)
set /p TAG_MSG="Enter tag message (annotation): "
if "%TAG_MSG%"=="" (
    echo [Error] Tag message cannot be empty.
    pause
    exit /b 1
)
rem Replace double quotes (") with single quotes (') to avoid breaking command arguments
set "TAG_MSG=%TAG_MSG:"='%"

rem [8] Create the annotated tag on current HEAD
echo Creating annotated tag %VERSION% ...
git tag -a %VERSION% -m "%TAG_MSG%"
if errorlevel 1 (
    echo [Error] Tag creation failed.
    pause
    exit /b 1
)

rem [9] Push only the created tag to the remote (do not push branches)
echo Pushing tag %VERSION% to origin ...
git push origin %VERSION%
if errorlevel 1 (
    echo [Error] Tag push failed.
    pause
    exit /b 1
)

rem [10] Completion message
echo.
echo [Success] Tag %VERSION% created and pushed.
echo.
pause
exit /b 0
