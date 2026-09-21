@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  EyeNet Platform Manager
::  Windows Batch Installer & Management Console
::  Version: 2.25.83
::
::  Download ONLY this file to any folder on your Windows PC.
::  Double-click to run.  No PowerShell, no setup required.
:: ============================================================

set "VERSION=2.25.83"
set "ENV_FILE=.env.windows"
set "COMPOSE_FILE=docker-compose.windows-installer.yml"
set "ENV_TEMPLATE=.env.windows.template"
set "GITHUB_RAW=https://raw.githubusercontent.com/nickglezakos/ppl-meta-platform/main/deployment/windows-installer"
set "REGISTRY=ghcr.io/nickglezakos/ppl-meta-platform"
set "MIN_FREE_GB=12"
set "MIN_HOST_RAM_GB=16"
set "MIN_WSL_MEM_GB=12"
set "INSTALL_DIR="
set "FIRST_RUN=0"
set "WSL_DISTRO=eyenet"
set "USE_WSL_DOCKER=0"
set "COMPOSE_PROJECT=pplmeta"

:: Prefer WSL docker-ce when available
wsl -d %WSL_DISTRO% --user root -- docker info >nul 2>&1
if not errorlevel 1 set "USE_WSL_DOCKER=1"

:: Detect if this is first run (no .env.windows in current directory)
if not exist "%ENV_FILE%" (
    if exist "%ENV_TEMPLATE%" (
        set "INSTALL_DIR=%CD%"
    ) else (
        set "INSTALL_DIR=C:\ppl-meta-platform"
    )
    set "FIRST_RUN=1"
) else (
    set "INSTALL_DIR=%CD%"
)

:main_menu
cls
call :banner

echo.
echo   +========================================================+
echo   ^|            EyeNet Platform Manager                     ^|
echo   +========================================================+
if "%FIRST_RUN%"=="1" (
    echo   ^|  [1]  Install / Reconfigure Platform               ^|
    echo   +========================================================+
    echo   ^|  Platform not yet installed. Choose [1] to begin.  ^|
    echo   +========================================================+
) else (
    echo   ^|  [1]  Install / Reconfigure Platform               ^|
    echo   ^|  [2]  Start All Containers                         ^|
    echo   ^|  [3]  Stop All Containers                          ^|
    echo   ^|  [4]  View Container Status                        ^|
    echo   ^|  [5]  View Container Logs                          ^|
    echo   ^|  [6]  Exit                                         ^|
    echo   +========================================================+
)
echo.
set /p "choice=  Enter choice [1-6]: "

if "%FIRST_RUN%"=="1" (
    if "%choice%"=="" set "choice=1"
    if "%choice%"=="1" goto install
    if "%choice%"=="?1" goto install
    goto install
)

if "%choice%"=="1" goto install
if "%choice%"=="2" goto start_stack
if "%choice%"=="3" goto stop_stack
if "%choice%"=="4" goto show_status
if "%choice%"=="5" goto show_logs
if "%choice%"=="6" exit /b 0
goto main_menu

:: ============================================================
::  BANNER
:: ============================================================
:banner
echo.
echo   =========================================================
echo   ^|                                                       ^|
echo   ^|     EEEEEE  Y   Y  EEEEE  N   N  EEEEE  TTTTTTT      ^|
echo   ^|     E        Y Y   E      NN  N  E         T          ^|
echo   ^|     EEEE      Y    EEEE   N N N  EEEE      T          ^|
echo   ^|     E         Y    E      N  NN  E         T          ^|
echo   ^|     EEEEEE    Y    EEEEE  N   N  EEEEE     T          ^|
echo   ^|                                                       ^|
echo   ^|              Platform Manager  v%VERSION%               ^|
echo   ^|                                                       ^|
echo   =========================================================
goto :eof

:: ============================================================
::  OPTION 1: FULL INSTALL / RECONFIGURE
:: ============================================================
:install
cls
call :banner
echo.
echo   === EyeNet Platform Installation ===
echo.
echo   Progress will be shown as each step completes.
echo.

:: -- STEP 1: Install directory --
echo   [Step 1/9] Install directory
echo   -----------------------------------
echo   Where should EyeNet platform files be stored?
echo.
set /p "INSTALL_DIR=  Install directory [C:\ppl-meta-platform]: "
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=C:\ppl-meta-platform"

:: Create directory if needed
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
echo   [ OK ] Using: %INSTALL_DIR%

:: -- STEP 2: Check host RAM --
echo.
echo   [Step 2/9] Host RAM check (16 GB standard)
echo   -----------------------------------
call :check_host_ram
if errorlevel 1 (
    echo   [FAILED] Step 2/9 - Host RAM below %MIN_HOST_RAM_GB% GB
    goto install_done
)

:: -- STEP 3: Check free space --
echo.
echo   [Step 3/9] Disk space check
echo   -----------------------------------
call :check_freespace "%INSTALL_DIR%"
if errorlevel 1 (
    echo   [FAILED] Step 3/9 - Not enough disk space
    goto install_done
)

:: -- STEP 4: Check Docker --
echo.
echo   [Step 4/9] Docker Engine check
echo   -----------------------------------
call :check_docker
if errorlevel 1 (
    echo   [FAILED] Step 4/9 - Docker Engine not available
    goto install_done
)

:: -- STEP 5: Check WSL --
echo.
echo   [Step 5/9] WSL configuration
echo   -----------------------------------
call :check_wsl
if errorlevel 1 (
    echo   [FAILED] Step 5/9 - WSL memory below %MIN_WSL_MEM_GB% GB
    goto install_done
)

:: -- STEP 6: Download files --
echo.
echo   [Step 6/9] Download installer files
echo   -----------------------------------
call :download_files
if errorlevel 1 (
    echo   [FAILED] Step 6/9 - Could not download files from GitHub
    goto install_done
)

:: -- STEP 7: Configure credentials --
echo.
echo   [Step 7/9] Platform credentials
echo   -----------------------------------
call :create_env
if errorlevel 1 (
    echo   [FAILED] Step 7/9 - Configuration failed
    goto install_done
)

:: -- STEP 8: Pull Docker images --
echo.
echo   [Step 8/9] Downloading Docker images
echo   -----------------------------------
echo   This may take 5-10 minutes depending on your internet speed.
call :pull_images
if errorlevel 1 (
    echo   [FAILED] Step 8/9 - Image pull failed. Check internet connection.
    goto install_done
)

:: -- STEP 9: Start containers --
echo.
echo   [Step 9/9] Starting the platform
echo   -----------------------------------
call :start_containers
if errorlevel 1 (
    echo   [FAILED] Step 9/9 - Failed to start containers
    goto install_done
)

:: -- Show status --
echo.
call :display_status

echo.
echo   +========================================================+
echo   ^|  ALL STEPS COMPLETE - Platform is running!             ^|
echo   ^|  Open: http://localhost:3000                          ^|
echo   +========================================================+

cd /d "%INSTALL_DIR%"
set "FIRST_RUN=0"

:install_done
echo.
echo   Press any key to return to menu...
pause >nul
goto main_menu

:: ============================================================
::  CHECK HOST RAM (16 GB standard)
:: ============================================================
:check_host_ram
echo   [CHECK] Host physical RAM...
set "total_mem_kb="
for /f "skip=1" %%a in ('wmic computersystem get TotalPhysicalMemory 2^>nul') do (
    if not "%%a"=="" (
        set "total_mem_bytes=%%a"
        goto :got_host_ram
    )
)
:got_host_ram
if "%total_mem_bytes%"=="" (
    echo   [WARN] Could not determine host RAM. Continuing.
    goto :eof
)
set /a total_mem_gb=%total_mem_bytes% / 1073741824 2>nul
if "%total_mem_gb%"=="" goto :eof
echo   [CHECK] Host RAM...                   [%total_mem_gb% GB]
if %total_mem_gb% lss %MIN_HOST_RAM_GB% (
    echo   [FAIL] Need at least %MIN_HOST_RAM_GB% GB physical RAM. Detected %total_mem_gb% GB.
    exit /b 1
)
echo   [ OK ] Host RAM meets 16 GB platform standard
goto :eof

:: ============================================================
::  CHECK FREE SPACE
:: ============================================================
:check_freespace
set "drive=%~d1"
if "%drive%"=="" set "drive=C:"

:: Try PowerShell first (most reliable)
powershell -Command "try { $d = Get-PSDrive '%drive:~0,1%'; [math]::Floor($d.Free/1GB) } catch { }" 2>nul | findstr /r "[0-9]" > "%TEMP%\eyenet_freegb.txt"
set /p "free_gb=<%TEMP%\eyenet_freegb.txt" 2>nul
del "%TEMP%\eyenet_freegb.txt" 2>nul

if not "%free_gb%"=="" goto :check_free_result

:: Fallback: wmic (works on all Windows 10/11)
for /f "skip=1" %%a in ('wmic logicaldisk where "DeviceID='%drive%'" get FreeSpace 2^>nul') do (
    if not "%%a"=="" set "free_bytes=%%a"
    goto :got_bytes
)
:got_bytes
if "%free_bytes%"=="" (
    :: Fallback: skip the check entirely rather than block install
    echo   [WARN] Could not determine free space for %drive%. Skipping check.
    echo   [INFO] EyeNet requires ~5 GB for images, ~1 GB for data.
    goto :eof
)

:: Convert bytes to GB (WMIC returns bytes)
set /a free_gb=%free_bytes% / 1073741824 2>nul

:check_free_result
if "%free_gb%"=="" goto :eof

echo   [CHECK] Free disk space...            [%free_gb% GB]

if %free_gb% lss %MIN_FREE_GB% (
    echo   [FAIL] Need at least %MIN_FREE_GB% GB free. Only %free_gb% GB available.
    exit /b 1
)
echo   [ OK ] Sufficient disk space
goto :eof

:: ============================================================
::  CHECK DOCKER ENGINE (WSL eyenet preferred; Desktop legacy)
:: ============================================================
:check_docker
echo   [CHECK] Docker Engine (WSL eyenet preferred)...
set "USE_WSL_DOCKER=0"
wsl -d %WSL_DISTRO% --user root -- docker info >nul 2>&1
if not errorlevel 1 (
    set "USE_WSL_DOCKER=1"
    for /f "tokens=*" %%a in ('wsl -d %WSL_DISTRO% --user root -- docker version --format "{{.Server.Version}}" 2^>nul') do set "docker_ver=%%a"
    if "!docker_ver!"=="" set "docker_ver=running"
    echo   [ OK ] WSL/%WSL_DISTRO% docker-ce (v!docker_ver!)
    goto :eof
)

docker version >nul 2>&1
if not errorlevel 1 (
    for /f "tokens=*" %%a in ('docker version --format "{{.Server.Version}}" 2^>nul') do set "docker_ver=%%a"
    if "!docker_ver!"=="" set "docker_ver=running"
    echo   [WARN] Using host Docker (legacy Desktop path). Prefer install-eyenet-wsl.bat.
    echo   [ OK ] Host docker detected (v!docker_ver!)
    goto :eof
)

echo.
echo   [FAIL] No Docker Engine found.
echo.
echo   Preferred: run install-eyenet-wsl.bat first (Docker Engine CE in WSL).
echo   Legacy: start Docker Desktop, then re-run this installer.
echo   Or use install-platform.ps1 for the WSL-aware PowerShell path.
pause
exit /b 1
goto :eof

:: ============================================================
::  CHECK WSL CONFIG
:: ============================================================
:check_wsl
set "wslconfig=%USERPROFILE%\.wslconfig"
echo   [CHECK] WSL configuration...

if not exist "%wslconfig%" (
    echo   [WARN] No .wslconfig found.
    echo.
    echo   EyeNet needs at least %MIN_WSL_MEM_GB% GB RAM and 4 CPUs for the WSL distro.
    echo   A .wslconfig file will be created with 12 GB RAM and 6 CPUs (16 GB host standard).
    echo.
    set /p "fix_wsl=  Create .wslconfig now? [Y/n]: "
    if /i not "%fix_wsl%"=="n" (
        (
            echo [wsl2]
            echo memory=12GB
            echo processors=6
            echo swap=2GB
        ) > "%wslconfig%"
        echo   [ OK ] Created %wslconfig%
        echo.
        echo   [WARN] WSL must restart. Re-run install-eyenet-wsl.bat if needed.
        echo   Press any key to continue...
        pause >nul
    ) else (
        echo   [FAIL] WSL memory must be at least %MIN_WSL_MEM_GB% GB before continuing.
        pause
        exit /b 1
    )
    goto :eof
)

:: parse existing config
set "mem_ok=0"
set "cpu_ok=0"
for /f "usebackq tokens=1,2 delims==" %%a in ("%wslconfig%") do (
    call :trim "%%a" key
    call :trim "%%b" val
    if /i "!key!"=="memory" (
        set "val_numeric=!val:GB=!"
        set "val_numeric=!val_numeric:gb=!"
        if !val_numeric! geq %MIN_WSL_MEM_GB% set "mem_ok=1"
        set "mem_val=!val!"
    )
    if /i "!key!"=="processors" (
        if !val! geq 4 set "cpu_ok=1"
        set "cpu_val=!val!"
    )
)
if "%mem_ok%"=="1" if "%cpu_ok%"=="1" (
    echo   [ OK ] WSL configured: %mem_val% RAM / %cpu_val% CPUs
    goto :eof
)

echo   [WARN] WSL needs at least %MIN_WSL_MEM_GB% GB / 4 CPUs. Current: %mem_val% RAM / %cpu_val% CPUs
echo.
echo   This will update your .wslconfig to 12 GB / 6 CPUs.
set /p "fix_wsl=  Update .wslconfig now? [Y/n]: "
if /i "%fix_wsl%"=="n" (
    echo   [FAIL] WSL memory must be at least %MIN_WSL_MEM_GB% GB before continuing.
    pause
    exit /b 1
)
(
    echo [wsl2]
    echo memory=12GB
    echo processors=6
    echo swap=2GB
) > "%wslconfig%"
echo   [ OK ] Updated %wslconfig%
echo   Please restart WSL for changes to take effect (wsl --shutdown).
echo   Press any key to continue...
pause >nul
goto :eof

:: ============================================================
::  DOWNLOAD FILES FROM GITHUB RAW
:: ============================================================
:download_files
echo   --- Downloading Files ---
cd /d "%INSTALL_DIR%"

:: download compose file
echo   Downloading %COMPOSE_FILE%...
curl -sS -L -o "%COMPOSE_FILE%" "%GITHUB_RAW%/%COMPOSE_FILE%" 2>nul
if errorlevel 1 (
    :: fallback to bitsadmin
    bitsadmin /transfer "eyeNetCompose" "%GITHUB_RAW%/%COMPOSE_FILE%" "%CD%\%COMPOSE_FILE%" >nul 2>&1
)
if not exist "%COMPOSE_FILE%" (
    echo   [FAIL] Could not download %COMPOSE_FILE%
    exit /b 1
)
echo   [ OK ] %COMPOSE_FILE%

:: download env template
echo   Downloading %ENV_TEMPLATE%...
curl -sS -L -o "%ENV_TEMPLATE%" "%GITHUB_RAW%/%ENV_TEMPLATE%" 2>nul
if errorlevel 1 (
    bitsadmin /transfer "eyeNetEnv" "%GITHUB_RAW%/%ENV_TEMPLATE%" "%CD%\%ENV_TEMPLATE%" >nul 2>&1
)
if not exist "%ENV_TEMPLATE%" (
    echo   [FAIL] Could not download %ENV_TEMPLATE%
    exit /b 1
)
echo   [ OK ] %ENV_TEMPLATE%

echo   [ OK ] All files downloaded to %INSTALL_DIR%
goto :eof

:: ============================================================
::  CREATE .env.windows
:: ============================================================
:create_env
echo   --- Configuration ---

if exist "%ENV_FILE%" (
    echo   [INFO] %ENV_FILE% already exists.  Editing with Notepad...
    echo   Press any key to open Notepad.  Fill in your values and save.
    pause >nul
    start /wait notepad "%ENV_FILE%"
    echo   [ OK ] Configuration saved.
    ver >nul
    goto :eof
)

:: copy template
copy /y "%ENV_TEMPLATE%" "%ENV_FILE%" >nul

echo.
echo   Enter your EyeNet platform credentials.
echo   (These come from the Authority admin dashboard.)
echo.

set /p "install_uuid=  INSTALLATION_UUID: "
set /p "app_key=  APPLICATION_KEY  : "
echo   POSTGRES_PASSWORD:  (type carefully - input is hidden)
echo.

:: Use a small PowerShell one-liner for secure password input if available
set "pg_pass="
powershell -Command "$p=Read-Host -AsSecureString '  POSTGRES_PASSWORD'; $BSTR=[System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($p); Write-Host '  [ OK ] Password set'" 2>nul
if errorlevel 1 (
    :: PowerShell not available — plain text fallback
    set /p "pg_pass=  POSTGRES_PASSWORD (visible): "
    if not "!pg_pass!"=="" (
        echo.
        echo   [WARN] Password was visible.  Edit %ENV_FILE% later to secure it.
    )
)

:: Write values into .env.windows using PowerShell for reliability
powershell -Command ^
    "$lines = Get-Content '%ENV_FILE%'; " ^
    "for($i=0;$i -lt $lines.Count; $i++) { " ^
    "  if($lines[$i] -match '^INSTALLATION_UUID=') { $lines[$i] = 'INSTALLATION_UUID=%install_uuid%' } " ^
    "  elseif($lines[$i] -match '^APPLICATION_KEY=') { $lines[$i] = 'APPLICATION_KEY=%app_key%' } " ^
    "  elseif($lines[$i] -match '^POSTGRES_PASSWORD=') { $lines[$i] = 'POSTGRES_PASSWORD=%pg_pass%' } " ^
    "  elseif($lines[$i] -match '^RELEASE_TAG=') { $lines[$i] = 'RELEASE_TAG=%VERSION%' } " ^
    "  elseif($lines[$i] -match '^REGISTRY=') { $lines[$i] = 'REGISTRY=%REGISTRY%' } " ^
    "}; Set-Content -Path '%ENV_FILE%' -Value $lines" 2>nul

if errorlevel 1 (
    :: Manual fallback — tell user to edit with Notepad
    echo   [WARN] Auto-config failed.  Opening Notepad for manual editing.
    echo   Fill in INSTALLATION_UUID, APPLICATION_KEY, POSTGRES_PASSWORD.
    pause
    start /wait notepad "%ENV_FILE%"
    ver >nul
) else (
    echo   [ OK ] Configuration saved to %ENV_FILE%
)

:: verify required values are filled
findstr /r "^INSTALLATION_UUID=$" "%ENV_FILE%" >nul 2>&1 && (
    echo   [WARN] INSTALLATION_UUID is empty!
    echo   Opening Notepad so you can fill in the values.
    pause
    start /wait notepad "%ENV_FILE%"
    ver >nul
)
findstr /r "^APPLICATION_KEY=$" "%ENV_FILE%" >nul 2>&1 && (
    echo   [WARN] APPLICATION_KEY is empty!
    echo   Opening Notepad so you can fill in the values.
    pause
    start /wait notepad "%ENV_FILE%"
    ver >nul
)
goto :eof

goto :eof

:: ============================================================
::  RUN DOCKER COMPOSE (WSL eyenet when USE_WSL_DOCKER=1)
::  Usage: call :run_compose pull
::         call :run_compose up -d
:: ============================================================
:run_compose
cd /d "%INSTALL_DIR%"
if "%USE_WSL_DOCKER%"=="1" (
    for /f "delims=" %%P in ('powershell -NoProfile -Command "$p=(Resolve-Path '%CD%').Path; if($p -match '^([A-Za-z]):\\(.*)$'){ '/mnt/'+$matches[1].ToLower()+'/'+($matches[2] -replace '\\','/') }"') do set "WSL_CWD=%%P"
    wsl -d %WSL_DISTRO% --user root -- bash -lc "cd '!WSL_CWD!' && docker compose --project-name %COMPOSE_PROJECT% --env-file %ENV_FILE% -f %COMPOSE_FILE% %*"
) else (
    docker compose --project-name %COMPOSE_PROJECT% --env-file "%ENV_FILE%" -f "%COMPOSE_FILE%" %*
)
goto :eof

:: ============================================================
::  PULL IMAGES
:: ============================================================
:pull_images
echo   --- Pulling Images (this may take several minutes) ---
call :run_compose pull
if errorlevel 1 (
    echo   [FAIL] Image pull failed.  Check GHCR login: wsl -d %WSL_DISTRO% -- docker login ghcr.io
    exit /b 1
)
echo.
echo   [ OK ] All images pulled successfully
goto :eof

:: ============================================================
::  START CONTAINERS
:: ============================================================
:start_containers
echo   --- Starting Stack ---
call :run_compose up -d
if errorlevel 1 (
    echo   [FAIL] Failed to start containers.
    exit /b 1
)

:: Media uid 1001 vs fresh root-owned volume (upload Permission denied)
echo   --- Ensuring Media volume permissions ---
if "%USE_WSL_DOCKER%"=="1" (
    wsl -d %WSL_DISTRO% --user root -- bash -lc "cd '!WSL_CWD!' && if [ -f ensure-media-volume-perms.sh ]; then COMPOSE_PROJECT_NAME=%COMPOSE_PROJECT% bash ensure-media-volume-perms.sh; fi"
) else (
    if exist ensure-media-volume-perms.sh (
        set COMPOSE_PROJECT_NAME=%COMPOSE_PROJECT%
        bash ensure-media-volume-perms.sh
    )
)

:: Wait for postgres
echo   Waiting for PostgreSQL...
set "count=0"
:wait_pg
set /a count+=1
if %count% gtr 30 (
    echo   [WARN] PostgreSQL is taking longer than expected.
    goto :wait_redis
)
if "%USE_WSL_DOCKER%"=="1" (
    wsl -d %WSL_DISTRO% --user root -- docker inspect --format="{{.State.Health.Status}}" ppl-postgres 2>nul | findstr "healthy" >nul
) else (
    docker inspect --format="{{.State.Health.Status}}" ppl-postgres 2>nul | findstr "healthy" >nul
)
if errorlevel 1 (
    ping -n 3 127.0.0.1 >nul
    goto wait_pg
)
echo   [ OK ] PostgreSQL healthy

:wait_redis
echo   Waiting for Redis...
set "count=0"
:wait_rd
set /a count+=1
if %count% gtr 20 (
    echo   [WARN] Redis is taking longer than expected.
    goto :start_containers_done
)
if "%USE_WSL_DOCKER%"=="1" (
    wsl -d %WSL_DISTRO% --user root -- docker inspect --format="{{.State.Health.Status}}" ppl-redis 2>nul | findstr "healthy" >nul
) else (
    docker inspect --format="{{.State.Health.Status}}" ppl-redis 2>nul | findstr "healthy" >nul
)
if errorlevel 1 (
    ping -n 3 127.0.0.1 >nul
    goto wait_rd
)
echo   [ OK ] Redis healthy
:start_containers_done
if "%USE_WSL_DOCKER%"=="1" echo   VPN check: wsl -d %WSL_DISTRO% -- tailscale status
goto :eof

:: ============================================================
::  OPTION 2: START STACK (from menu)
:: ============================================================
:start_stack
cls
call :banner
echo.
echo   === Starting EyeNet Platform ===
echo.
call :check_docker
if errorlevel 1 goto start_done

cd /d "%INSTALL_DIR%"
if not exist "%ENV_FILE%" (
    echo   [FAIL] %ENV_FILE% not found.  Run Install first.
    goto start_done
)
call :start_containers
echo.
call :display_status

:start_done
echo.
echo   Press any key to return to menu...
pause >nul
goto main_menu

:: ============================================================
::  OPTION 3: STOP STACK
:: ============================================================
:stop_stack
cls
call :banner
echo.
echo   === Stopping EyeNet Platform ===
echo.
cd /d "%INSTALL_DIR%"
if not exist "%ENV_FILE%" (
    echo   [FAIL] %ENV_FILE% not found.
    goto stop_done
)
call :run_compose down
echo.
echo   [ OK ] All containers stopped.  Data volumes are preserved.

:stop_done
echo.
echo   Press any key to return to menu...
pause >nul
goto main_menu

:: ============================================================
::  OPTION 4: VIEW STATUS
:: ============================================================
:show_status
cls
call :banner
cd /d "%INSTALL_DIR%"
if not exist "%ENV_FILE%" (
    echo.
    echo   [FAIL] Platform not installed.  Run Install first.
    echo.
    echo   Press any key to return to menu...
    pause >nul
    goto main_menu
)
call :display_status
echo.
echo   Press any key to return to menu...
pause >nul
goto main_menu

:display_status
echo.
echo   === Container Status ===
call :run_compose ps
if errorlevel 1 (
    echo   [WARN] Could not retrieve container status.
)
goto :eof

:: ============================================================
::  OPTION 5: VIEW LOGS
:: ============================================================
:show_logs
cls
call :banner
cd /d "%INSTALL_DIR%"
if not exist "%ENV_FILE%" (
    echo.
    echo   [FAIL] Platform not installed.  Run Install first.
    echo   Press any key to return to menu...
    pause >nul
    goto main_menu
)

echo.
echo   === Select Container for Logs ===
echo.
echo   [1]  postgres
echo   [2]  redis
echo   [3]  ppl-meta-node
echo   [4]  ppl-meta-media
echo   [5]  ppl-meta-gateway
echo   [6]  ppl-meta-orchestrator
echo   [7]  ppl-meta-discovery
echo   [8]  ppl-meta-communications
echo   [9]  ppl-meta-vision
echo   [10] ppl-meta-vmeta
echo   [11] ppl-meta-frontend
echo   [B]  Back to Main Menu
echo.

set /p "log_choice=  Container number: "

set "container="
if "%log_choice%"=="1"  set "container=postgres"
if "%log_choice%"=="2"  set "container=redis"
if "%log_choice%"=="3"  set "container=ppl-meta-node"
if "%log_choice%"=="4"  set "container=ppl-meta-media"
if "%log_choice%"=="5"  set "container=ppl-meta-gateway"
if "%log_choice%"=="6"  set "container=ppl-meta-orchestrator"
if "%log_choice%"=="7"  set "container=ppl-meta-discovery"
if "%log_choice%"=="8"  set "container=ppl-meta-communications"
if "%log_choice%"=="9"  set "container=ppl-meta-vision"
if "%log_choice%"=="10" set "container=ppl-meta-vmeta"
if "%log_choice%"=="11" set "container=ppl-meta-frontend"
if /i "%log_choice%"=="b"  goto main_menu

if "%container%"=="" (
    echo   Invalid choice.
    echo   Press any key...
    pause >nul
    goto show_logs
)

:: Show logs
cls
echo.
echo   === %container% (last 100 lines) ===
echo.
call :run_compose logs --tail 100 "%container%"
echo.
echo   === End of logs ===
echo.
echo   [F] Follow live (Ctrl+C to stop)
echo   [B] Back to container list
echo   [M] Main menu
echo.
set /p "log_action=  Choice: "

if /i "%log_action%"=="f" (
    echo.
    echo   === Following %container% logs (Ctrl+C to stop) ===
    echo.
    call :run_compose logs -f --tail 20 "%container%"
    echo.
    echo   === Stopped following ===
    echo   Press any key...
    pause >nul
    goto show_logs
)
if /i "%log_action%"=="b" goto show_logs
if /i "%log_action%"=="m" goto main_menu
goto main_menu

:: ============================================================
::  HELPER: TRIM STRING
:: ============================================================
:trim
set "%~2=%~1"
set "%~2=!%~2:"=!"
goto :eof

:: ============================================================
::  CLEANUP
:: ============================================================
endlocal