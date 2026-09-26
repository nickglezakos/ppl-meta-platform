@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  EyeNet Platform Manager — launcher
::  Version: 2.25.86
::
::  Canonical installer is install-platform.ps1 (schema apply,
::  discovery reregister, ADVERTISE_HOST, tray). This .bat only
::  bootstraps PowerShell so double-click still works.
:: ============================================================

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%install-platform.ps1"

if not exist "%PS1%" (
    echo [FAIL] Missing install-platform.ps1 next to this launcher.
    echo        Download the full windows-installer folder from:
    echo        https://github.com/nickglezakos/ppl-meta-platform/tree/main/deployment/windows-installer
    pause
    exit /b 1
)

:: Prefer Windows PowerShell; fall back to pwsh if present
set "PS=powershell"
where pwsh >nul 2>&1 && set "PS=pwsh"

echo.
echo   EyeNet Platform Manager — launching install-platform.ps1 ...
echo.

"%PS%" -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
    echo.
    echo   [FAIL] install-platform.ps1 exited with code %RC%
    pause
)
exit /b %RC%
