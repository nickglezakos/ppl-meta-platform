@echo off
REM EyeNet WSL runtime bootstrap — Docker Engine CE in distro "eyenet" (no Docker Desktop)
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-eyenet-wsl.ps1" %*
exit /b %ERRORLEVEL%
