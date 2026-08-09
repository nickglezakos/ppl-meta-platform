# EyeNet Platform Manager
# Autonomous Windows installer & management console
# Version: 2.25.48
# Repository: https://github.com/nickglezakos/ppl-meta-platform

param(
    [switch]$SkipMenu
)

$ErrorActionPreference = "Continue"
$script:EnvFile = ".env.windows"
$script:ComposeFile = "docker-compose.windows-installer.yml"
$script:EnvTemplateFile = ".env.windows.template"
$script:MinimumFreeSpaceGb = 12
$script:GitHubRawBase = "https://raw.githubusercontent.com/nickglezakos/ppl-meta-platform/main/deployment/windows-installer"
$script:InstallDir = $null
$script:ReleaseTag = "2.25.48"
$script:ComposeProjectName = "pplmeta"

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

function Test-DockerRunning {
    try {
        docker version *>$null 2>&1
        docker info *>$null 2>&1
        return $true
    } catch {
        return $false
    }
}

function Wait-ForDocker {
    Write-Step "Checking Docker Desktop..." ""
    if (Test-DockerRunning) {
        $version = (docker version --format '{{.Server.Version}}' 2>$null) -replace "`n|`r", ""
        if (-not $version) { $version = "running" }
        Write-Host "  OK (v$version)" -ForegroundColor $script:Green
        return $true
    }

    Write-WarningMsg "Docker Desktop is not running."
    Write-Host ""
    Write-Host "    Please start Docker Desktop from the Start menu." -ForegroundColor $script:Yellow
    Write-Host "    Waiting for Docker to become available..." -ForegroundColor $script:Yellow
    Write-Host ""

    $attempt = 0
    while (-not (Test-DockerRunning)) {
        $attempt++
        Write-Host "`r    Waiting... ($attempt s)" -NoNewline -ForegroundColor $script:Gray
        Start-Sleep -Seconds 3
        if ($attempt -gt 120) {
            Write-Host ""
            Write-ErrorMsg "Docker Desktop did not start within 6 minutes. Please start Docker manually and re-run this script."
            Pause-ForUser
            return $false
        }
    }
    Write-Host ""
    Write-Host "    Docker Desktop detected!" -ForegroundColor $script:Green
    return $true
}

function Test-WslConfig {
    Write-Step "Checking WSL configuration..." ""
    $wslConfigPath = "$env:USERPROFILE\.wslconfig"
    $needsFix = $false
    $memoryOk = $false
    $cpuOk = $false

    if (Test-Path $wslConfigPath) {
        $content = Get-Content $wslConfigPath -Raw
        if ($content -match 'memory\s*=\s*(\d+)\s*GB') {
            $mem = [int]$matches[1]
            if ($mem -ge 6) { $memoryOk = $true }
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
        $memInfo = if ($memoryOk) { "${mem}GB" } else { "BELOW 6GB" }
        $cpuInfo = if ($cpuOk) { "${cpu} CPUs" } else { "BELOW 4 CPUs" }
        Write-Host "  NEEDS FIX ($memInfo / $cpuInfo)" -ForegroundColor $script:Yellow
        $needsFix = $true
    }

    if ($needsFix) {
        Write-Host ""
        Write-WarningMsg "Docker Desktop requires at least 6 GB RAM and 4 CPUs for EyeNet."
        Write-Host ""
        Write-InputPrompt "Auto-configure WSL now?" "Y"
        $response = Read-Host
        if ($response -eq "" -or $response -eq "Y" -or $response -eq "y") {
            $wslContent = @"
[wsl2]
memory=8GB
processors=6
swap=2GB
"@
            Set-Content -Path $wslConfigPath -Value $wslContent -Force
            Write-Success "WSL config created at $wslConfigPath"

            Write-WarningMsg "WSL must be restarted for changes to take effect."
            Write-InputPrompt "Restart WSL now? (Docker Desktop will need to restart)" "Y"
            $restart = Read-Host
            if ($restart -eq "" -or $restart -eq "Y" -or $restart -eq "y") {
                Write-Step "Shutting down WSL..." ""
                wsl --shutdown 2>$null
                Write-Host "  DONE" -ForegroundColor $script:Green
                Write-Host "    Please restart Docker Desktop now." -ForegroundColor $script:Yellow
                Pause-ForUser
                return (Wait-ForDocker)
            }
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
        @{Name = $script:EnvTemplateFile; Url = "$script:GitHubRawBase/$script:EnvTemplateFile"}
    )

    foreach ($file in $files) {
        try {
            Write-Host "`r    Downloading $($file.Name)..." -NoNewline -ForegroundColor $script:Gray
            Invoke-WebRequest -Uri $file.Url -OutFile $file.Name -UseBasicParsing -ErrorAction Stop
            Write-Host "`r    $($file.Name)  " -NoNewline -ForegroundColor $script:White
            Write-Host "OK" -ForegroundColor $script:Green
        } catch {
            Write-Host ""
            Write-ErrorMsg "Failed to download $($file.Name) from $($file.Url)"
            Write-ErrorMsg "Error: $_"
            return $false
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

    # Prompt for required values
    $installUuid = Prompt-Value -Label "INSTALLATION_UUID" -Current $currentValues['INSTALLATION_UUID'] -Required
    $appKey = Prompt-Value -Label "APPLICATION_KEY" -Current $currentValues['APPLICATION_KEY'] -Required
    $pgPassword = Prompt-ValueSecure -Label "POSTGRES_PASSWORD" -Current $currentValues['POSTGRES_PASSWORD'] -Required
    Write-Divider $script:Cyan
    Write-Host ""

    # Write to .env.windows
    Set-EnvValue -Path $script:EnvFile -Key "INSTALLATION_UUID" -Value $installUuid
    Set-EnvValue -Path $script:EnvFile -Key "APPLICATION_KEY" -Value $appKey
    Set-EnvValue -Path $script:EnvFile -Key "POSTGRES_PASSWORD" -Value $pgPassword

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

function Invoke-PullImages {
    Write-Step "Pulling Docker images (this may take several minutes)..." ""
    Write-Host ""
    try {
        docker compose --env-file "$script:EnvFile" -f "$script:ComposeFile" pull 2>&1 | ForEach-Object {
            $line = $_.ToString()
            if ($line -match "Pulling|Downloading|Extracting|Pulled|Already") {
                Write-Host "    $line" -ForegroundColor $script:Gray
            } else {
                Write-Host "    $line" -ForegroundColor $script:White
            }
        }
        if ($LASTEXITCODE -ne 0) {
            Write-ErrorMsg "Image pull failed. Check your internet connection and try again."
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
        docker compose --env-file "$script:EnvFile" -f "$script:ComposeFile" up -d 2>&1 | ForEach-Object {
            Write-Host "    $_" -ForegroundColor $script:Gray
        }
    } catch {
        Write-ErrorMsg "Failed to start containers: $_"
        return $false
    }

    # Wait for postgres health
    Write-Step "Waiting for PostgreSQL..." ""
    $pgHealthy = $false
    for ($i = 0; $i -lt 30; $i++) {
        $status = docker inspect --format='{{.State.Health.Status}}' ppl-postgres 2>$null
        if ($status -eq "healthy") {
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
    }

    # Wait for redis health
    Write-Step "Waiting for Redis..." ""
    $redisHealthy = $false
    for ($i = 0; $i -lt 20; $i++) {
        $status = docker inspect --format='{{.State.Health.Status}}' ppl-redis 2>$null
        if ($status -eq "healthy") {
            Write-Host "  HEALTHY" -ForegroundColor $script:Green
            $redisHealthy = $true
            break
        }
        Start-Sleep -Seconds 2
        Write-Host "`r    Waiting... ($($i*2)s)" -NoNewline -ForegroundColor $script:Gray
    }
    Write-Host ""
    return $true
}

function Invoke-StopStack {
    Write-Step "Stopping all containers..." ""
    try {
        docker compose --env-file "$script:EnvFile" -f "$script:ComposeFile" down 2>&1 | ForEach-Object {
            Write-Host "    $_" -ForegroundColor $script:Gray
        }
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
        $output = docker compose --env-file "$script:EnvFile" -f "$script:ComposeFile" ps 2>&1
        foreach ($line in $output) {
            $trimmed = $line.ToString().TrimEnd()
            if ($trimmed.Length -gt 60) { $trimmed = $trimmed.Substring(0, 57) + "..." }
            $padLen = 60 - $trimmed.Length
            if ($padLen -lt 0) { $padLen = 0 }
            Write-Host "  ║ " -NoNewline -ForegroundColor $script:Cyan
            # Colorize based on status
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
        $output = docker compose --env-file "$script:EnvFile" -f "$script:ComposeFile" ps --format "{{.Name}}|{{.Status}}" 2>$null
        foreach ($line in $output) {
            $parts = $line -split '\|', 2
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
        $output = docker compose --env-file "$script:EnvFile" -f "$script:ComposeFile" logs --tail 150 $ContainerName 2>&1
        foreach ($line in $output) {
            $logLines += $line.ToString()
            $trimmed = $line.ToString().TrimEnd()
            # Colorize based on content
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
                docker compose --env-file "$script:EnvFile" -f "$script:ComposeFile" logs -f --tail 20 $ContainerName 2>&1
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

    # Step 2: Check free space
    if (-not (Test-FreeSpace -Path $script:InstallDir)) { return $false }

    # Step 3: Check Docker
    if (-not (Wait-ForDocker)) { return $false }

    # Step 4: Check WSL config
    if (-not (Test-WslConfig)) { return $false }

    # Step 5: Download files
    if (-not (Download-InstallerFiles)) { return $false }

    # Step 6: Create .env.windows
    if (-not (New-EnvWindows)) { return $false }

    # Step 7: Pull images
    if (-not (Invoke-PullImages)) { return $false }

    # Step 8: Start stack
    if (-not (Invoke-StartStack)) { return $false }

    # Step 9: Show status
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