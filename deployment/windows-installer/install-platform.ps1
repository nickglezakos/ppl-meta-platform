# EyeNet Platform Manager
# Autonomous Windows installer & management console
# Version: 2.25.82
# Repository: https://github.com/nickglezakos/ppl-meta-platform

param(
    [switch]$SkipMenu
)

$ErrorActionPreference = "Continue"
$script:EnvFile = ".env.windows"
$script:ComposeFile = "docker-compose.windows-installer.yml"
$script:EnvTemplateFile = ".env.windows.template"
$script:MinimumFreeSpaceGb = 12
$script:MinimumHostRamGb = 16
$script:MinimumWslMemoryGb = 12
$script:TargetWslMemoryGb = 12
$script:TargetWslProcessors = 6
$script:GitHubRawBase = "https://raw.githubusercontent.com/nickglezakos/ppl-meta-platform/main/deployment/windows-installer"
$script:InstallDir = $null
$script:ReleaseTag = "2.25.82"
$script:ComposeProjectName = "pplmeta"
$script:WslDistro = "eyenet"
$script:UseWslDocker = $false

# ============================================================
# COLOR / STYLE HELPERS
# ============================================================
$script:Cyan    = "Cyan"
$script:Green   = "Green"
$script:Red     = "Red"
$script:Yellow  = "Yellow"
$script:White   = "White"
$script:Gray    = "DarkGray"
$script:Blue    = "DarkBlue"

function Write-EyeNetBanner {
    Clear-Host
    Write-Host ""
    Write-Host "  ╔══════════════════════════════════════════════════════════════╗" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "                                                              " -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "    ███████╗██╗   ██╗███████╗███╗   ██╗███████╗████████╗     " -ForegroundColor $script:Cyan -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "    ██╔════╝╚██╗ ██╔╝██╔════╝████╗  ██║██╔════╝╚══██╔══╝     " -ForegroundColor $script:Cyan -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "    █████╗   ╚████╔╝ █████╗  ██╔██╗ ██║█████╗     ██║        " -ForegroundColor $script:Cyan -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "    ██╔══╝    ╚██╔╝  ██╔══╝  ██║╚██╗██║██╔══╝     ██║        " -ForegroundColor $script:Cyan -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "    ███████╗   ██║   ███████╗██║ ╚████║███████╗   ██║        " -ForegroundColor $script:Cyan -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "    ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═══╝╚══════╝   ╚═╝        " -ForegroundColor $script:Cyan -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "                                                              " -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "             Platform Manager  v$script:ReleaseTag                   " -ForegroundColor $script:White -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ║" -ForegroundColor $script:Cyan -NoNewline
    Write-Host "                                                              " -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    Write-Host "  ╚══════════════════════════════════════════════════════════════╝" -ForegroundColor $script:Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Message, [string]$Status = "", [string]$StatusColor = $script:Green)
    Write-Host "  [" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "*" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "] " -NoNewline -ForegroundColor $script:Cyan
    Write-Host $Message -NoNewline -ForegroundColor $script:White
    if ($Status) {
        Write-Host "  " -NoNewline
        Write-Host $Status -ForegroundColor $StatusColor
    } else {
        Write-Host ""
    }
}

function Write-Success {
    param([string]$Message)
    Write-Host "  " -NoNewline
    Write-Host "OK " -NoNewline -ForegroundColor $script:Green
    Write-Host $Message -ForegroundColor $script:White
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "  " -NoNewline
    Write-Host "ERROR " -NoNewline -ForegroundColor $script:Red
    Write-Host $Message -ForegroundColor $script:Red
}

function Write-WarningMsg {
    param([string]$Message)
    Write-Host "  " -NoNewline
    Write-Host "WARNING " -NoNewline -ForegroundColor $script:Yellow
    Write-Host $Message -ForegroundColor $script:Yellow
}

function Write-Divider {
    param([string]$Color = $script:Cyan)
    Write-Host "  " -NoNewline
    Write-Host ("─" * 62) -ForegroundColor $Color
}

function Draw-Box {
    param(
        [string]$Title,
        [string]$TitleColor = $script:White,
        [string]$BoxColor = $script:Cyan
    )
    Write-Host "  ╔" -NoNewline -ForegroundColor $BoxColor
    Write-Host ("═" * 60) -NoNewline -ForegroundColor $BoxColor
    Write-Host "╗" -ForegroundColor $BoxColor
    if ($Title) {
        Write-Host "  ║" -NoNewline -ForegroundColor $BoxColor
        $padding = 60 - $Title.Length
        $leftPad = [math]::Floor($padding / 2)
        $rightPad = $padding - $leftPad
        Write-Host (" " * $leftPad) -NoNewline
        Write-Host $Title -NoNewline -ForegroundColor $TitleColor
        Write-Host (" " * $rightPad) -NoNewline
        Write-Host "║" -ForegroundColor $BoxColor
    }
}

function Draw-BoxFooter {
    param([string]$BoxColor = $script:Cyan)
    Write-Host "  ╚" -NoNewline -ForegroundColor $BoxColor
    Write-Host ("═" * 60) -NoNewline -ForegroundColor $BoxColor
    Write-Host "╝" -ForegroundColor $BoxColor
}

function Draw-MenuItem {
    param(
        [string]$Key,
        [string]$Label,
        [string]$Suffix = "",
        [string]$SuffixColor = $script:White
    )
    Write-Host "  ║" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "  [" -NoNewline -ForegroundColor $script:Cyan
    Write-Host $Key -NoNewline -ForegroundColor $script:Cyan
    Write-Host "]  " -NoNewline -ForegroundColor $script:Cyan
    Write-Host $Label -NoNewline -ForegroundColor $script:White
    if ($Suffix) {
        Write-Host "  " -NoNewline
        Write-Host $Suffix -NoNewline -ForegroundColor $SuffixColor
    }
    $totalLen = 5 + $Key.Length + $Label.Length + $Suffix.Length
    $remaining = 60 - $totalLen
    if ($remaining -gt 0) {
        Write-Host (" " * $remaining) -NoNewline
    }
    Write-Host "║" -ForegroundColor $script:Cyan
}

function Draw-MenuDivider {
    Write-Host "  ╠" -NoNewline -ForegroundColor $script:Cyan
    Write-Host ("═" * 60) -NoNewline -ForegroundColor $script:Cyan
    Write-Host "╣" -ForegroundColor $script:Cyan
}

function Write-InputPrompt {
    param([string]$Label, [string]$Default = "")
    Write-Host "    " -NoNewline
    Write-Host $Label -NoNewline -ForegroundColor $script:Cyan
    if ($Default) {
        Write-Host " [$Default]" -NoNewline -ForegroundColor $script:Gray
    }
    Write-Host ": " -NoNewline -ForegroundColor $script:Cyan
}

# ============================================================
# CORE FUNCTIONS
# ============================================================

function Get-FreeSpaceGb {
    param([string]$Path)
    try {
        $drive = Get-PSDrive -Name (Split-Path $Path -Qualifier).TrimEnd(':') -ErrorAction Stop
        return [math]::Floor($drive.Free / 1GB)
    } catch {
        return 999
    }
}

function ConvertTo-WslPath {
    param([string]$WindowsPath)
    $full = [System.IO.Path]::GetFullPath($WindowsPath)
    if ($full -match '^([A-Za-z]):\\(.*)$') {
        $drive = $matches[1].ToLower()
        $rest = ($matches[2] -replace '\\', '/')
        return "/mnt/$drive/$rest"
    }
    return $WindowsPath.Replace('\', '/')
}

function Test-WslDockerEngine {
    try {
        $distros = @(wsl -l -q 2>$null | ForEach-Object { ($_ -replace "`0", "").Trim() } | Where-Object { $_ })
        if ($distros -notcontains $script:WslDistro) {
            return $false
        }
        wsl -d $script:WslDistro --user root -- bash -lc "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; /usr/bin/docker info >/dev/null 2>&1"
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Invoke-EyeNetDocker {
    param([Parameter(Mandatory = $true)][string[]]$DockerArgs)

    if ($script:UseWslDocker) {
        $cwd = ConvertTo-WslPath (Get-Location).Path
        $escaped = foreach ($arg in $DockerArgs) {
            $safe = $arg -replace "'", "'\''"
            "'$safe'"
        }
        $joined = $escaped -join ' '
        wsl -d $script:WslDistro --user root -- bash -lc "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; cd '$cwd' && docker $joined"
        return $LASTEXITCODE
    }

    & docker @DockerArgs
    return $LASTEXITCODE
}

function Test-DockerRunning {
    if (Test-WslDockerEngine) {
        $script:UseWslDocker = $true
        return $true
    }
    try {
        docker version *>$null 2>&1
        docker info *>$null 2>&1
        if ($LASTEXITCODE -eq 0) {
            $script:UseWslDocker = $false
            return $true
        }
        return $false
    } catch {
        return $false
    }
}

function Wait-ForDocker {
    Write-Step "Checking Docker Engine (WSL $script:WslDistro preferred)..." ""
    if (Test-WslDockerEngine) {
        $script:UseWslDocker = $true
        $version = (wsl -d $script:WslDistro --user root -- docker version --format '{{.Server.Version}}' 2>$null) -replace "`n|`r|`0", ""
        if (-not $version) { $version = "running" }
        Write-Host "  OK (WSL/$script:WslDistro docker-ce v$version)" -ForegroundColor $script:Green
        return $true
    }

    if (Test-DockerRunning -and -not $script:UseWslDocker) {
        Write-WarningMsg "Using host Docker (Docker Desktop). Preferred path is install-eyenet-wsl.ps1."
        $version = (docker version --format '{{.Server.Version}}' 2>$null) -replace "`n|`r", ""
        if (-not $version) { $version = "running" }
        Write-Host "  OK (host docker v$version)" -ForegroundColor $script:Yellow
        return $true
    }

    Write-ErrorMsg "No Docker Engine found."
    Write-Host ""
    Write-Host "    Preferred: run install-eyenet-wsl.bat first (Docker Engine CE in WSL distro '$script:WslDistro')." -ForegroundColor $script:Yellow
    Write-Host "    Legacy: start Docker Desktop, then re-run this installer." -ForegroundColor $script:Gray
    Write-Host ""
    Pause-ForUser
    return $false
}

function Test-HostMemory {
    Write-Step "Checking host RAM..." ""
    try {
        $cs = Get-CimInstance -ClassName Win32_ComputerSystem
        $totalGb = [math]::Round(($cs.TotalPhysicalMemory / 1GB), 1)
    } catch {
        Write-Host "  WARN (could not read host RAM)" -ForegroundColor $script:Yellow
        return $true
    }

    # Windows often reports ~15.x GB for a 16 GB machine (hardware reserved).
    if ($totalGb -lt ($script:MinimumHostRamGb - 1)) {
        Write-Host "  FAIL (${totalGb} GB, need $($script:MinimumHostRamGb) GB)" -ForegroundColor $script:Red
        Write-ErrorMsg "EyeNet requires at least $($script:MinimumHostRamGb) GB physical RAM on the Windows host."
        Pause-ForUser
        return $false
    }

    Write-Host "  OK (${totalGb} GB)" -ForegroundColor $script:Green
    return $true
}

function Test-WslConfig {
    Write-Step "Checking WSL configuration..." ""
    $wslConfigPath = "$env:USERPROFILE\.wslconfig"
    $needsFix = $false
    $memoryOk = $false
    $cpuOk = $false
    $mem = 0
    $cpu = 0

    if (Test-Path $wslConfigPath) {
        $content = Get-Content $wslConfigPath -Raw
        if ($content -match 'memory\s*=\s*(\d+)\s*GB') {
            $mem = [int]$matches[1]
            if ($mem -ge $script:MinimumWslMemoryGb) { $memoryOk = $true }
        }
        if ($content -match 'processors\s*=\s*(\d+)') {
            $cpu = [int]$matches[1]
            if ($cpu -ge 4) { $cpuOk = $true }
        }
    }

    if (-not (Test-Path $wslConfigPath)) {
        Write-Host "  NOT FOUND (will create)" -ForegroundColor $script:Yellow
        $needsFix = $true
    } elseif ($memoryOk -and $cpuOk) {
        Write-Host "  OK (${mem}GB / ${cpu} CPUs)" -ForegroundColor $script:Green
    } else {
        $memInfo = if ($memoryOk) { "${mem}GB" } else { "BELOW $($script:MinimumWslMemoryGb)GB" }
        $cpuInfo = if ($cpuOk) { "${cpu} CPUs" } else { "BELOW 4 CPUs" }
        Write-Host "  NEEDS FIX ($memInfo / $cpuInfo)" -ForegroundColor $script:Yellow
        $needsFix = $true
    }

    if ($needsFix) {
        Write-Host ""
        Write-WarningMsg "EyeNet needs at least $($script:MinimumWslMemoryGb) GB RAM and 4 CPUs for the WSL distro (16 GB host standard)."
        Write-Host ""
        Write-InputPrompt "Auto-configure WSL now?" "Y"
        $response = Read-Host
        if ($response -eq "" -or $response -eq "Y" -or $response -eq "y") {
            $wslContent = @"
[wsl2]
memory=$($script:TargetWslMemoryGb)GB
processors=$($script:TargetWslProcessors)
swap=2GB
networkingMode=mirrored
"@
            Set-Content -Path $wslConfigPath -Value $wslContent -Force
            Write-Success "WSL config created at $wslConfigPath"

            Write-WarningMsg "WSL must be restarted for changes to take effect."
            Write-InputPrompt "Restart WSL now?" "Y"
            $restart = Read-Host
            if ($restart -eq "" -or $restart -eq "Y" -or $restart -eq "y") {
                Write-Step "Shutting down WSL..." ""
                wsl --shutdown 2>$null
                Write-Host "  DONE" -ForegroundColor $script:Green
                Write-Host "    Re-run install-eyenet-wsl.bat if the eyenet distro needs docker-ce." -ForegroundColor $script:Yellow
                Pause-ForUser
                return (Wait-ForDocker)
            }
        } else {
            Write-ErrorMsg "WSL memory must be at least $($script:MinimumWslMemoryGb) GB before continuing."
            Pause-ForUser
            return $false
        }
    }
    return $true
}

function Test-FreeSpace {
    param([string]$Path)
    $free = Get-FreeSpaceGb -Path $Path
    Write-Step "Checking disk space..." ""
    if ($free -lt $script:MinimumFreeSpaceGb) {
        Write-Host "  FAIL ($free GB free, need $script:MinimumFreeSpaceGb GB)" -ForegroundColor $script:Red
        Write-ErrorMsg "Not enough free disk space. Required: $script:MinimumFreeSpaceGb GB. Available: $free GB."
        Pause-ForUser
        return $false
    }
    Write-Host "  OK ($free GB free)" -ForegroundColor $script:Green
    return $true
}

function Download-InstallerFiles {
    Write-Step "Downloading installer files..." ""

    if (-not (Test-Path $script:InstallDir)) {
        New-Item -ItemType Directory -Path $script:InstallDir -Force | Out-Null
    }
    Set-Location $script:InstallDir

    $files = @(
        @{Name = $script:ComposeFile; Url = "$script:GitHubRawBase/$script:ComposeFile"},
        @{Name = $script:EnvTemplateFile; Url = "$script:GitHubRawBase/$script:EnvTemplateFile"},
        @{Name = "install-eyenet-wsl.ps1"; Url = "$script:GitHubRawBase/install-eyenet-wsl.ps1"},
        @{Name = "install-eyenet-wsl.bat"; Url = "$script:GitHubRawBase/install-eyenet-wsl.bat"},
        @{Name = "schema/apply.sh"; Url = "$script:GitHubRawBase/schema/apply.sh"},
        @{Name = "schema/verify.sh"; Url = "$script:GitHubRawBase/schema/verify.sh"},
        @{Name = "schema/pack.tar.gz"; Url = "$script:GitHubRawBase/schema/pack.tar.gz"},
        @{Name = "reregister-discovery-services.sh"; Url = "$script:GitHubRawBase/reregister-discovery-services.sh"}
    )

    foreach ($file in $files) {
        try {
            $outPath = $file.Name
            $outDir = Split-Path $outPath -Parent
            if ($outDir -and -not (Test-Path $outDir)) {
                New-Item -ItemType Directory -Path $outDir -Force | Out-Null
            }
            # Prefer already-present install-dir file or copy shipped next to this script
            if (Test-Path $outPath) {
                Write-Host "`r    $($file.Name)  " -NoNewline -ForegroundColor $script:White
                Write-Host "OK (local)" -ForegroundColor $script:Green
                continue
            }
            $bundled = Join-Path $PSScriptRoot $file.Name
            if (Test-Path $bundled) {
                Copy-Item $bundled $outPath -Force
                Write-Host "`r    $($file.Name)  " -NoNewline -ForegroundColor $script:White
                Write-Host "OK (bundled)" -ForegroundColor $script:Green
                continue
            }
            Write-Host "`r    Downloading $($file.Name)..." -NoNewline -ForegroundColor $script:Gray
            Invoke-WebRequest -Uri $file.Url -OutFile $outPath -UseBasicParsing -ErrorAction Stop
            Write-Host "`r    $($file.Name)  " -NoNewline -ForegroundColor $script:White
            Write-Host "OK" -ForegroundColor $script:Green
        } catch {
            $bundled = Join-Path $PSScriptRoot $file.Name
            if (Test-Path $bundled) {
                $outPath = $file.Name
                $outDir = Split-Path $outPath -Parent
                if ($outDir -and -not (Test-Path $outDir)) {
                    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
                }
                Copy-Item $bundled $outPath -Force
                Write-Host ""
                Write-Host "    $($file.Name)  " -NoNewline -ForegroundColor $script:White
                Write-Host "OK (bundled fallback)" -ForegroundColor $script:Green
                continue
            }
            Write-Host ""
            Write-ErrorMsg "Failed to download $($file.Name) from $($file.Url)"
            Write-ErrorMsg "Error: $_"
            return $false
        }
    }

    # Expand pack.tar.gz into schema/pack if needed
    $packDir = Join-Path $script:InstallDir "schema\pack"
    $packTar = Join-Path $script:InstallDir "schema\pack.tar.gz"
    if ((Test-Path $packTar) -and -not (Test-Path (Join-Path $packDir "000_preflight_extensions_and_stub_reconcile.sql"))) {
        New-Item -ItemType Directory -Path $packDir -Force | Out-Null
        $drive = $script:InstallDir.Substring(0, 1).ToLower()
        $rest = ($script:InstallDir.Substring(2) -replace '\\', '/')
        $wslSchema = "/mnt/$drive$rest/schema"
        if ($script:UseWslDocker) {
            wsl -d $script:WslDistro --user root -- bash -lc "mkdir -p '$wslSchema/pack' && tar -xzf '$wslSchema/pack.tar.gz' -C '$wslSchema/pack'"
        } else {
            tar -xzf $packTar -C $packDir 2>$null
        }
    }

    Write-Success "All files downloaded to $script:InstallDir"
    return $true
}

function New-EnvWindows {
    Write-Step "Preparing environment configuration..." ""

    try {
        if (Test-Path $script:EnvFile) {
            Write-WarningMsg "$script:EnvFile already exists. Using existing file."
        } else {
            Copy-Item $script:EnvTemplateFile $script:EnvFile -Force
            Write-Host "  Created $script:EnvFile" -ForegroundColor $script:Green
        }
    } catch {
        Write-ErrorMsg "Failed to create $script:EnvFile from template: $_"
        return $false
    }

    # Read current values
    $currentValues = @{}
    if (Test-Path $script:EnvFile) {
        Get-Content $script:EnvFile | ForEach-Object {
            if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)') {
                $currentValues[$matches[1]] = $matches[2]
            }
        }
    }

    Write-Host ""
    Write-Divider $script:Cyan
    Write-Host "  " -NoNewline
    Write-Host "EyeNet Configuration" -ForegroundColor $script:White
    Write-Divider $script:Cyan

    # Prompt for required values (lab / first-boot only).
    # PRODUCTION TODO: do NOT ask the end-user for INSTALLATION_UUID or APPLICATION_KEY.
    # In production these must come from Authority entitlement / first-owner bootstrap
    # (pre-provisioned .env, claim token, or /bootstrap after start) — never typed by hand
    # during install. Keep POSTGRES_PASSWORD local-secret generation or secure prompt.
    $installUuid = Prompt-Value -Label "INSTALLATION_UUID" -Current $currentValues['INSTALLATION_UUID'] -Required
    $appKey = Prompt-Value -Label "APPLICATION_KEY" -Current $currentValues['APPLICATION_KEY'] -Required
    $pgPassword = Prompt-ValueSecure -Label "POSTGRES_PASSWORD" -Current $currentValues['POSTGRES_PASSWORD'] -Required
    Write-Divider $script:Cyan
    Write-Host ""

    # Write to .env.windows
    Set-EnvValue -Path $script:EnvFile -Key "INSTALLATION_UUID" -Value $installUuid
    Set-EnvValue -Path $script:EnvFile -Key "APPLICATION_KEY" -Value $appKey
    Set-EnvValue -Path $script:EnvFile -Key "POSTGRES_PASSWORD" -Value $pgPassword
    Set-EnvValue -Path $script:EnvFile -Key "RELEASE_TAG" -Value $script:ReleaseTag
    Set-EnvValue -Path $script:EnvFile -Key "REGISTRY" -Value "ghcr.io/nickglezakos/ppl-meta-platform"

    # Prefer an existing ADVERTISE_HOST; otherwise detect a non-loopback IPv4 for
    # mobile discovery (LAN phones cannot use Docker 172.x addresses).
    $advertiseHost = $currentValues['ADVERTISE_HOST']
    if ([string]::IsNullOrWhiteSpace($advertiseHost)) {
        try {
            $advertiseHost = Get-NetIPAddress -AddressFamily IPv4 |
                Where-Object {
                    $_.IPAddress -notlike '127.*' -and
                    $_.IPAddress -notlike '169.254.*' -and
                    $_.IPAddress -notlike '172.1[6-9].*' -and
                    $_.IPAddress -notlike '172.2[0-9].*' -and
                    $_.IPAddress -notlike '172.3[0-1].*' -and
                    $_.PrefixOrigin -ne 'WellKnown'
                } |
                Sort-Object -Property InterfaceMetric |
                Select-Object -ExpandProperty IPAddress -First 1
        } catch {
            $advertiseHost = $null
        }
    }
    if (-not [string]::IsNullOrWhiteSpace($advertiseHost)) {
        Set-EnvValue -Path $script:EnvFile -Key "ADVERTISE_HOST" -Value $advertiseHost
        Write-Host "  ADVERTISE_HOST=$advertiseHost (mobile discovery)" -ForegroundColor $script:Green
    } else {
        Write-WarningMsg "ADVERTISE_HOST unset — set the Windows LAN IP in .env.windows for mobile onboarding"
    }

    # Ensure COMPOSE_PROJECT_NAME is set in env for this session
    $env:COMPOSE_PROJECT_NAME = $script:ComposeProjectName

    Write-Success "Configuration saved to $script:EnvFile"
    return $true
}

function Prompt-Value {
    param([string]$Label, [string]$Current, [switch]$Required)
    Write-InputPrompt $Label
    if ($Current) {
        Write-Host "[$Current]" -NoNewline -ForegroundColor $script:Gray
        Write-Host ": " -NoNewline -ForegroundColor $script:Cyan
    } else {
        if ($Required) { Write-Host "(required): " -NoNewline -ForegroundColor $script:Red }
        else { Write-Host ": " -NoNewline -ForegroundColor $script:Cyan }
    }
    $val = Read-Host
    if ([string]::IsNullOrWhiteSpace($val)) {
        return $Current
    }
    return $val
}

function Prompt-ValueSecure {
    param([string]$Label, [string]$Current, [switch]$Required)
    $promptText = "    $Label"
    if ($Current -and $Current -ne "change-me") {
        $promptText += " [****]: "
    } elseif ($Required) {
        $promptText += " (required): "
    } else {
        $promptText += ": "
    }
    Write-Host $promptText -NoNewline -ForegroundColor $script:Cyan
    $secureVal = Read-Host -AsSecureString
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureVal)
    try {
        $plainVal = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        if ([string]::IsNullOrWhiteSpace($plainVal)) {
            return $Current
        }
        return $plainVal
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
    }
}

function Set-EnvValue {
    param([string]$Path, [string]$Key, [string]$Value)
    $lines = Get-Content $Path
    $updated = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^$Key=") {
            $lines[$i] = "$Key=$Value"
            $updated = $true
            break
        }
    }
    if (-not $updated) {
        $lines += "$Key=$Value"
    }
    Set-Content -Path $Path -Value $lines
}

function Get-ContainerHealthStatus {
    param([string]$Name)
    if ($script:UseWslDocker) {
        $status = wsl -d $script:WslDistro --user root -- docker inspect --format='{{.State.Health.Status}}' $Name 2>$null
    } else {
        $status = docker inspect --format='{{.State.Health.Status}}' $Name 2>$null
    }
    return ($status -replace "`0|`n|`r", "").Trim()
}

function Invoke-ApplyCodebaseSchema {
    Write-Step "Applying codebase database schema (must match repo)..." ""
    $schemaDir = Join-Path $script:InstallDir "schema"
    $applySh = Join-Path $schemaDir "apply.sh"
    $packDir = Join-Path $schemaDir "pack"
    $packTar = Join-Path $schemaDir "pack.tar.gz"

    # Prefer files shipped next to this script (full installer folder / Lima sync)
    $srcSchema = Join-Path $PSScriptRoot "schema"
    if (Test-Path $srcSchema) {
        if (-not (Test-Path $schemaDir)) {
            New-Item -ItemType Directory -Path $schemaDir -Force | Out-Null
        }
        Copy-Item -Path (Join-Path $srcSchema "*") -Destination $schemaDir -Recurse -Force
    }

    if ((Test-Path $packTar) -and -not (Test-Path (Join-Path $packDir "000_preflight_extensions_and_stub_reconcile.sql"))) {
        New-Item -ItemType Directory -Path $packDir -Force | Out-Null
        if ($script:UseWslDocker) {
            $wslSchema = ($schemaDir -replace '\\', '/') -replace '^([A-Za-z]):', { "/mnt/$($args[0].Groups[1].Value.ToLower())" }
            # Fallback path conversion for C:\...
            $drive = $schemaDir.Substring(0, 1).ToLower()
            $rest = ($schemaDir.Substring(2) -replace '\\', '/')
            $wslSchema = "/mnt/$drive$rest"
            wsl -d $script:WslDistro --user root -- bash -lc "mkdir -p '$wslSchema/pack' && tar -xzf '$wslSchema/pack.tar.gz' -C '$wslSchema/pack'"
        } else {
            tar -xzf $packTar -C $packDir
        }
    }

    if (-not (Test-Path $applySh)) {
        Write-ErrorMsg "schema/apply.sh missing under $script:InstallDir — re-run sync-schema-pack.sh and ship schema/ with the installer"
        return $false
    }

    Start-Sleep -Seconds 5
    $cwd = ($script:InstallDir -replace '\\', '/')
    $drive = $script:InstallDir.Substring(0, 1).ToLower()
    $rest = ($script:InstallDir.Substring(2) -replace '\\', '/')
    $wslCwd = "/mnt/$drive$rest"

    if ($script:UseWslDocker) {
        $code = wsl -d $script:WslDistro --user root -- bash -lc "cd '$wslCwd' && INSTALL_DIR='$wslCwd' SCHEMA_PACK_DIR='$wslCwd/schema/pack' bash schema/apply.sh"
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "Schema apply/verify failed (exit $LASTEXITCODE). Installer will not continue with a mismatched DB."
            return $false
        }
    } else {
        # Docker Desktop path: need bash (Git Bash / WSL)
        $bash = Get-Command bash -ErrorAction SilentlyContinue
        if (-not $bash) {
            Write-ErrorMsg "bash required to apply schema pack (install Git for Windows or use WSL eyenet path)"
            return $false
        }
        Push-Location $script:InstallDir
        try {
            & bash schema/apply.sh
            if ($LASTEXITCODE -ne 0) {
                Write-ErrorMsg "Schema apply/verify failed"
                return $false
            }
        } finally {
            Pop-Location
        }
    }
    Write-Success "Database schema matches codebase invariants"
    return $true
}

function Invoke-ReregisterDiscovery {
    Write-Step "Re-registering services with discovery..." ""
    $rereg = Join-Path $script:InstallDir "reregister-discovery-services.sh"
    $bundled = Join-Path $PSScriptRoot "reregister-discovery-services.sh"
    if (-not (Test-Path $rereg) -and (Test-Path $bundled)) {
        Copy-Item $bundled $rereg -Force
    }
    if (-not (Test-Path $rereg)) {
        Write-WarningMsg "reregister-discovery-services.sh missing — skip (mobile discovery may be incomplete)"
        return $true
    }

    $drive = $script:InstallDir.Substring(0, 1).ToLower()
    $rest = ($script:InstallDir.Substring(2) -replace '\\', '/')
    $wslCwd = "/mnt/$drive$rest"

    try {
        if ($script:UseWslDocker) {
            wsl -d $script:WslDistro --user root -- bash -lc "cd '$wslCwd' && bash reregister-discovery-services.sh" | Out-Host
        } else {
            $bash = Get-Command bash -ErrorAction SilentlyContinue
            if (-not $bash) {
                Write-WarningMsg "bash required for discovery reregister — skip"
                return $true
            }
            Push-Location $script:InstallDir
            try {
                & bash reregister-discovery-services.sh | Out-Host
            } finally {
                Pop-Location
            }
        }
        Write-Success "Discovery registry refreshed"
    } catch {
        Write-WarningMsg "Discovery reregister failed (non-fatal): $_"
    }
    return $true
}

function Invoke-PullImages {
    Write-Step "Pulling Docker images (this may take several minutes)..." ""
    Write-Host ""
    try {
        $code = Invoke-EyeNetDocker -DockerArgs @(
            "compose", "--project-name", $script:ComposeProjectName,
            "--env-file", $script:EnvFile, "-f", $script:ComposeFile, "pull"
        )
        if ($code -ne 0) {
            Write-ErrorMsg "Image pull failed. Log in with: wsl -d $($script:WslDistro) -- docker login ghcr.io"
            return $false
        }
    } catch {
        Write-ErrorMsg "Image pull failed: $_"
        return $false
    }
    Write-Host ""
    Write-Success "All images pulled successfully"
    return $true
}

function Invoke-StartStack {
    Write-Step "Starting platform containers..." ""
    Write-Host ""
    try {
        $code = Invoke-EyeNetDocker -DockerArgs @(
            "compose", "--project-name", $script:ComposeProjectName,
            "--env-file", $script:EnvFile, "-f", $script:ComposeFile, "up", "-d"
        )
        if ($code -ne 0) {
            Write-ErrorMsg "Failed to start containers"
            return $false
        }
    } catch {
        Write-ErrorMsg "Failed to start containers: $_"
        return $false
    }

    Write-Step "Waiting for PostgreSQL..." ""
    $pgHealthy = $false
    for ($i = 0; $i -lt 30; $i++) {
        if ((Get-ContainerHealthStatus -Name "ppl-postgres") -eq "healthy") {
            Write-Host "  HEALTHY" -ForegroundColor $script:Green
            $pgHealthy = $true
            break
        }
        Start-Sleep -Seconds 2
        Write-Host "`r    Waiting... ($($i*2)s)" -NoNewline -ForegroundColor $script:Gray
    }
    if (-not $pgHealthy) {
        Write-Host ""
        Write-WarningMsg "PostgreSQL is not yet healthy. Containers may restart until it is ready."
    } else {
        # Installer always matches repo: apply vendored schema pack + verify invariants.
        if (-not (Invoke-ApplyCodebaseSchema)) {
            return $false
        }
    }

    Write-Step "Waiting for Redis..." ""
    $redisHealthy = $false
    for ($i = 0; $i -lt 20; $i++) {
        if ((Get-ContainerHealthStatus -Name "ppl-redis") -eq "healthy") {
            Write-Host "  HEALTHY" -ForegroundColor $script:Green
            $redisHealthy = $true
            break
        }
        Start-Sleep -Seconds 2
        Write-Host "`r    Waiting... ($($i*2)s)" -NoNewline -ForegroundColor $script:Gray
    }
    Write-Host ""

    # Same post-up as Ubuntu installer: refresh in-memory discovery registry.
    Invoke-ReregisterDiscovery | Out-Null

    Write-Success "Platform started. Open http://localhost:3000"
    Write-Host "    Gateway:   http://localhost:8080" -ForegroundColor $script:Gray
    Write-Host "    Discovery: http://localhost:8006" -ForegroundColor $script:Gray
    Write-Host "    Bootstrap: http://localhost:3000/bootstrap" -ForegroundColor $script:Gray
    if ($script:UseWslDocker) {
        Write-Host "    VPN: Node enrolls via WSL Tailscale → https://vpn.eyenet-vision.com" -ForegroundColor $script:Gray
        Write-Host "    Check: wsl -d $($script:WslDistro) -- tailscale status" -ForegroundColor $script:Gray
    }
    return $true
}

function Invoke-StopStack {
    Write-Step "Stopping all containers..." ""
    try {
        $code = Invoke-EyeNetDocker -DockerArgs @(
            "compose", "--project-name", $script:ComposeProjectName,
            "--env-file", $script:EnvFile, "-f", $script:ComposeFile, "down"
        )
        if ($code -ne 0) { throw "docker compose down exited $code" }
        Write-Success "All containers stopped. Data volumes are preserved."
    } catch {
        Write-ErrorMsg "Failed to stop containers: $_"
    }
}

function Show-Status {
    Write-Host ""
    Draw-Box -Title "Container Status"
    Write-Host "  ║" -NoNewline -ForegroundColor $script:Cyan
    Write-Host (" " * 60) -NoNewline
    Write-Host "║" -ForegroundColor $script:Cyan
    try {
        $cwd = ConvertTo-WslPath (Get-Location).Path
        if ($script:UseWslDocker) {
            $output = wsl -d $script:WslDistro --user root -- bash -lc "cd '$cwd' && docker compose --project-name $($script:ComposeProjectName) --env-file $($script:EnvFile) -f $($script:ComposeFile) ps" 2>&1
        } else {
            $output = docker compose --project-name $script:ComposeProjectName --env-file "$script:EnvFile" -f "$script:ComposeFile" ps 2>&1
        }
        foreach ($line in $output) {
            $trimmed = $line.ToString().TrimEnd() -replace "`0", ""
            if ($trimmed.Length -gt 60) { $trimmed = $trimmed.Substring(0, 57) + "..." }
            $padLen = 60 - $trimmed.Length
            if ($padLen -lt 0) { $padLen = 0 }
            Write-Host "  ║ " -NoNewline -ForegroundColor $script:Cyan
            if ($trimmed -match "healthy|Up") {
                Write-Host $trimmed -NoNewline -ForegroundColor $script:Green
            } elseif ($trimmed -match "Restarting|unhealthy") {
                Write-Host $trimmed -NoNewline -ForegroundColor $script:Red
            } elseif ($trimmed -match "starting") {
                Write-Host $trimmed -NoNewline -ForegroundColor $script:Yellow
            } elseif ($trimmed -match "exited|Exit") {
                Write-Host $trimmed -NoNewline -ForegroundColor $script:Red
            } else {
                Write-Host $trimmed -NoNewline -ForegroundColor $script:White
            }
            Write-Host (" " * $padLen) -NoNewline
            Write-Host " ║" -ForegroundColor $script:Cyan
        }
    } catch {
        Write-Host "  ║ Could not retrieve container status" -ForegroundColor $script:Red
    }
    Draw-BoxFooter
}

function Get-ContainerList {
    $containers = @()
    try {
        $cwd = ConvertTo-WslPath (Get-Location).Path
        if ($script:UseWslDocker) {
            $output = wsl -d $script:WslDistro --user root -- bash -lc "cd '$cwd' && docker compose --project-name $($script:ComposeProjectName) --env-file $($script:EnvFile) -f $($script:ComposeFile) ps --format '{{.Name}}|{{.Status}}'" 2>$null
        } else {
            $output = docker compose --project-name $script:ComposeProjectName --env-file "$script:EnvFile" -f "$script:ComposeFile" ps --format "{{.Name}}|{{.Status}}" 2>$null
        }
        foreach ($line in $output) {
            $clean = ($line -replace "`0", "").Trim()
            if (-not $clean) { continue }
            $parts = $clean -split '\|', 2
            $containers += @{ Name = $parts[0]; Status = $parts[1] }
        }
    } catch {
        # return empty
    }
    return $containers
}

function Show-Logs {
    Write-Host ""
    Draw-Box -Title "EyeNet Platform Manager - Log Viewer"
    $containers = Get-ContainerList

    if ($containers.Count -eq 0) {
        Draw-MenuItem -Key "!" -Label "No containers found. Is the platform running?" -SuffixColor $script:Yellow
        Draw-BoxFooter
        Pause-ForUser
        return
    }

    $containers | ForEach-Object { $i = 0 } {
        $i++
        $idx = "[$i]".PadRight(5)
        $name = $_.Name.PadRight(24)
        $status = $_.Status
        if ($status -match "Up|healthy") {
            $color = $script:Green
            $suffix = "(Up)"
        } elseif ($status -match "Restarting") {
            $color = $script:Red
            $suffix = "(Restarting) `u26A0"
        } elseif ($status -match "exited|Exit") {
            $color = $script:Red
            $suffix = "(Exited)"
        } elseif ($status -match "starting") {
            $color = $script:Yellow
            $suffix = "(Starting)"
        } else {
            $color = $script:White
            $suffix = ""
        }
        Draw-MenuItem -Key $idx -Label "$name" -Suffix $suffix -SuffixColor $color
    }
    Draw-MenuDivider
    Draw-MenuItem -Key "[B]" -Label "Back to Main Menu"
    Draw-BoxFooter

    Write-InputPrompt "Select container number (or B)"
    $choice = Read-Host
    if ($choice -eq "B" -or $choice -eq "b") { return }

    $num = 0
    if (-not [int]::TryParse($choice, [ref]$num)) {
        Write-ErrorMsg "Invalid selection."
        Pause-ForUser
        return
    }
    if ($num -lt 1 -or $num -gt $containers.Count) {
        Write-ErrorMsg "Invalid container number."
        Pause-ForUser
        return
    }

    $selected = $containers[$num - 1]
    Show-ContainerLogs -ContainerName $selected.Name
}

function Show-ContainerLogs {
    param([string]$ContainerName)

    Write-Host ""
    Write-Divider $script:Cyan
    Write-Host "  Logs: " -NoNewline -ForegroundColor $script:Cyan
    Write-Host $ContainerName -NoNewline -ForegroundColor $script:White
    Write-Host " (last 150 lines)" -ForegroundColor $script:Gray
    Write-Divider $script:Cyan

    $logLines = @()
    try {
        $code = Invoke-EyeNetDocker -DockerArgs @(
            "compose", "--project-name", $script:ComposeProjectName,
            "--env-file", $script:EnvFile, "-f", $script:ComposeFile,
            "logs", "--tail", "150", $ContainerName
        )
        # Capture via wsl/docker stdout already printed by Invoke; re-run for capture
        $cwd = ConvertTo-WslPath (Get-Location).Path
        if ($script:UseWslDocker) {
            $output = wsl -d $script:WslDistro --user root -- bash -lc "cd '$cwd' && docker compose --project-name $($script:ComposeProjectName) --env-file $($script:EnvFile) -f $($script:ComposeFile) logs --tail 150 $ContainerName" 2>&1
        } else {
            $output = docker compose --project-name $script:ComposeProjectName --env-file "$script:EnvFile" -f "$script:ComposeFile" logs --tail 150 $ContainerName 2>&1
        }
        foreach ($line in $output) {
            $logLines += $line.ToString()
            $trimmed = ($line.ToString() -replace "`0", "").TrimEnd()
            if ($trimmed -match "ERROR|error|Error|FATAL|fatal|CRITICAL|critical") {
                Write-Host "  $trimmed" -ForegroundColor $script:Red
            } elseif ($trimmed -match "WARN|warn|WARNING|warning") {
                Write-Host "  $trimmed" -ForegroundColor $script:Yellow
            } elseif ($trimmed -match "INFO|info") {
                Write-Host "  $trimmed" -ForegroundColor $script:Gray
            } else {
                Write-Host "  $trimmed" -ForegroundColor $script:White
            }
        }
    } catch {
        Write-ErrorMsg "Failed to read logs: $_"
    }
    Write-Divider $script:Cyan
    Write-Host ""

    # Action menu
    Write-Host "  [" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "C" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "] Copy to clipboard   " -NoNewline -ForegroundColor $script:White
    Write-Host "[" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "F" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "] Follow (live)   " -NoNewline -ForegroundColor $script:White
    Write-Host "[" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "B" -NoNewline -ForegroundColor $script:Cyan
    Write-Host "] Back" -ForegroundColor $script:White

    Write-InputPrompt "Choice"
    $action = Read-Host

    switch ($action.ToLower()) {
        "c" {
            $allLogs = $logLines -join "`r`n"
            try {
                Set-Clipboard -Value $allLogs
                Write-Success "Logs copied to clipboard ($($logLines.Count) lines)"
            } catch {
                Write-ErrorMsg "Clipboard copy failed. The log content is available above."
            }
            Pause-ForUser
        }
        "f" {
            Write-Host ""
            Write-Host "  Following logs (Ctrl+C to stop)..." -ForegroundColor $script:Yellow
            Write-Divider $script:Cyan
            try {
                $cwd = ConvertTo-WslPath (Get-Location).Path
                if ($script:UseWslDocker) {
                    wsl -d $script:WslDistro --user root -- bash -lc "cd '$cwd' && docker compose --project-name $($script:ComposeProjectName) --env-file $($script:EnvFile) -f $($script:ComposeFile) logs -f --tail 20 $ContainerName"
                } else {
                    docker compose --project-name $script:ComposeProjectName --env-file "$script:EnvFile" -f "$script:ComposeFile" logs -f --tail 20 $ContainerName 2>&1
                }
            } catch {
                # User pressed Ctrl+C
            }
            Write-Host ""
            Write-Divider $script:Cyan
            Pause-ForUser
        }
        "b" {
            # Go back
        }
        default {
            Pause-ForUser
        }
    }
}

function Pause-ForUser {
    Write-Host ""
    Write-Host "  Press Enter to continue..." -NoNewline -ForegroundColor $script:Gray
    Read-Host | Out-Null
}

function Invoke-FullInstall {
    Write-EyeNetBanner
    Write-Host "  EyeNet Platform Installation" -ForegroundColor $script:White
    Write-Host ""

    # Step 1: Choose directory
    Write-Host "  Where should EyeNet platform files be stored?" -ForegroundColor $script:White
    Write-Host ""
    Write-InputPrompt "Install directory" "C:\ppl-meta-platform"
    $script:InstallDir = Read-Host
    if ([string]::IsNullOrWhiteSpace($script:InstallDir)) {
        $script:InstallDir = "C:\ppl-meta-platform"
    }
    Write-Host ""

    # Step 2: Check host RAM (16 GB platform standard)
    if (-not (Test-HostMemory)) { return $false }

    # Step 3: Check free space
    if (-not (Test-FreeSpace -Path $script:InstallDir)) { return $false }

    # Step 4: Check Docker
    if (-not (Wait-ForDocker)) { return $false }

    # Step 5: Check WSL config
    if (-not (Test-WslConfig)) { return $false }

    # Step 6: Download files
    if (-not (Download-InstallerFiles)) { return $false }

    # Step 7: Create .env.windows
    if (-not (New-EnvWindows)) { return $false }

    # Step 8: Pull images
    if (-not (Invoke-PullImages)) { return $false }

    # Step 9: Start stack
    if (-not (Invoke-StartStack)) { return $false }

    # Step 10: Show status
    Write-Host ""
    Show-Status
    Write-Host ""

    Draw-Box -Title "" -BoxColor $script:Green
    Write-Host "  ║" -NoNewline -ForegroundColor $script:Green
    Write-Host "    Platform is running!" -NoNewline -ForegroundColor $script:Green
    Write-Host (" " * 35) -NoNewline
    Write-Host "║" -ForegroundColor $script:Green
    Write-Host "  ║" -NoNewline -ForegroundColor $script:Green
    Write-Host "    Open: http://localhost:3000" -NoNewline -ForegroundColor $script:White
    Write-Host (" " * 30) -NoNewline
    Write-Host "║" -ForegroundColor $script:Green
    Draw-BoxFooter -BoxColor $script:Green

    return $true
}

function Show-MainMenu {
    $installed = Test-Path (Join-Path $script:InstallDir $script:EnvFile)

    while ($true) {
        if ($script:InstallDir) {
            Set-Location $script:InstallDir -ErrorAction SilentlyContinue
        }

        Write-EyeNetBanner

        if ($installed) {
            Draw-Box -Title "EyeNet Platform Manager"
        } else {
            Draw-Box -Title "EyeNet Platform Manager" -TitleColor $script:Yellow
        }
        Draw-MenuItem -Key "[1]" -Label "Install / Reconfigure Platform"
        Draw-MenuDivider
        Draw-MenuItem -Key "[2]" -Label "Start All Containers"
        Draw-MenuItem -Key "[3]" -Label "Stop All Containers"
        Draw-MenuItem -Key "[4]" -Label "View Container Status"
        Draw-MenuItem -Key "[5]" -Label "View Container Logs"
        Draw-MenuDivider
        Draw-MenuItem -Key "[6]" -Label "Exit"
        Draw-BoxFooter

        if (-not $installed) {
            Write-Host ""
            Write-WarningMsg "Platform not yet installed. Run option 1 first."
            Write-Host ""
        }

        Write-Host ""
        Write-InputPrompt "Enter choice" "1"
        $choice = Read-Host

        switch ($choice) {
            "1" {
                Clear-Host
                $result = Invoke-FullInstall
                if ($result) {
                    $installed = $true
                    $script:InstallDir = $script:InstallDir
                }
                Pause-ForUser
            }
            "2" {
                Clear-Host
                Write-EyeNetBanner
                Write-Host "  Starting EyeNet Platform..." -ForegroundColor $script:White
                Write-Host ""
                if (Wait-ForDocker) {
                    Set-Location $script:InstallDir -ErrorAction SilentlyContinue
                    if (-not (Test-Path $script:EnvFile)) {
                        Write-ErrorMsg "$script:EnvFile not found. Run Install first."
                    } else {
                        Invoke-StartStack
                        Write-Host ""
                        Show-Status
                    }
                }
                Pause-ForUser
            }
            "3" {
                Clear-Host
                Write-EyeNetBanner
                Write-Host "  Stopping EyeNet Platform..." -ForegroundColor $script:White
                Write-Host ""
                Set-Location $script:InstallDir -ErrorAction SilentlyContinue
                if (Test-Path $script:EnvFile) {
                    Invoke-StopStack
                } else {
                    Write-ErrorMsg "$script:EnvFile not found. Run Install first."
                }
                Pause-ForUser
            }
            "4" {
                Clear-Host
                Write-EyeNetBanner
                Set-Location $script:InstallDir -ErrorAction SilentlyContinue
                if (Test-Path $script:EnvFile) {
                    Show-Status
                } else {
                    Write-ErrorMsg "Platform not installed. Run Install first."
                }
                Pause-ForUser
            }
            "5" {
                Clear-Host
                Write-EyeNetBanner
                Set-Location $script:InstallDir -ErrorAction SilentlyContinue
                if (Test-Path $script:EnvFile) {
                    Show-Logs
                } else {
                    Write-ErrorMsg "Platform not installed. Run Install first."
                    Pause-ForUser
                }
            }
            "6" {
                Clear-Host
                Write-EyeNetBanner
                Write-Host "  Thank you for using EyeNet Platform Manager!" -ForegroundColor $script:Cyan
                Write-Host ""
                exit 0
            }
            default {
                if (-not $installed) {
                    Clear-Host
                    $result = Invoke-FullInstall
                    if ($result) {
                        $installed = $true
                    }
                    Pause-ForUser
                } else {
                    Write-ErrorMsg "Invalid choice. Please enter 1-6."
                    Pause-ForUser
                }
            }
        }
    }
}

# ============================================================
# ENTRY POINT
# ============================================================

# Determine install directory
if (Test-Path $script:EnvFile) {
    $script:InstallDir = (Get-Location).Path
    if ($SkipMenu) {
        Write-EyeNetBanner
        Write-Host "  Platform already configured at $script:InstallDir" -ForegroundColor $script:White
        Write-Host "  Launching management menu..." -ForegroundColor $script:Gray
        Start-Sleep -Seconds 1
    }
} elseif (Test-Path $script:EnvTemplateFile) {
    $script:InstallDir = (Get-Location).Path
} else {
    $script:InstallDir = "C:\ppl-meta-platform"
}

# If .env.windows doesn't exist and we're in skip mode, just go to install
if (-not (Test-Path (Join-Path $script:InstallDir $script:EnvFile)) -and $SkipMenu) {
    Clear-Host
    $result = Invoke-FullInstall
    if (-not $result) {
        Write-ErrorMsg "Installation did not complete successfully."
        Pause-ForUser
    }
    exit
}

Show-MainMenu