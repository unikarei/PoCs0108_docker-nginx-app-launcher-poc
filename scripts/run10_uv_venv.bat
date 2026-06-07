@echo off                                                     & rem Hide command echo for readable output.
setlocal EnableExtensions                                     & rem Enable standard Windows batch features.
chcp 65001 >nul                                               & rem Use UTF-8 output when possible.
set "ROOT=%~dp0.."                                            & rem Project root is the parent folder of scripts.
cd /d "%ROOT%"                                                & rem Move to the project root.

echo ========================================================= & rem Print title separator.
echo [run10] Create Python virtual environment with uv         & rem Print script purpose.
echo ========================================================= & rem Print title separator.
echo Root: %CD%                                                & rem Show current project root.

where uv >nul 2>nul                                           & rem Check whether uv command is installed.
if errorlevel 1 goto :uv_missing                              & rem Stop when uv is not found.

uv venv                                                       & rem Create .venv in the project root.
if errorlevel 1 goto :failed                                  & rem Stop when uv venv fails.

echo.                                                         & rem Print blank line.
echo [OK] .venv was created or already exists.                 & rem Show success message.
exit /b 0                                                     & rem Exit successfully.

rem ---------------------------------------------------------  & rem Error branch for missing uv.
:uv_missing
echo [ERROR] uv command was not found.                         & rem Explain the error.
echo Install uv first, then run this script again.             & rem Show next action.
exit /b 1                                                     & rem Exit with error.

rem ---------------------------------------------------------  & rem Error branch for uv failure.
:failed
echo [ERROR] Failed to create .venv.                           & rem Explain the error.
exit /b 1                                                     & rem Exit with error.
