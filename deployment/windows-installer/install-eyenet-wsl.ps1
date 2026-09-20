# EyeNet WSL Runtime Bootstrap
# Creates/configures the `eyenet` WSL2 distro with Docker Engine CE + Tailscale
# (open-source client). Does NOT require Docker Desktop.
# Version: 2.25.83

param(
    [string]$DistroName = "eyenet",
    [string]$UbuntuVersion = "Ubuntu-24.04",
    [switch]$SkipTailscale
)

$ErrorActionPreference = "Stop"
$script:MinimumHostRamGb = 16
$script:TargetWslMemoryGb = 12
$script:TargetWslProcessors = 6

function Write-Info([string]$Message) {
    Write-Host "  [*] $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-Warn([string]$Message) {
    Write-Host "  [WARN] $Message" -ForegroundColor Yellow
}

function Write-Err([string]$Message) {
    Write-Host "  [FAIL] $Message" -ForegroundColor Red
}

function Test-HostMemory {
    try {
        $cs = Get-CimInstance -ClassName Win32_ComputerSystem
        $totalGb = [math]::Round(($cs.TotalPhysicalMemory / 1GB), 1)
    } catch {
        Write-Warn "Could not read host RAM; continuing."
        return $true
    }
    # Windows often reports ~15.x GB for a 16 GB machine (hardware reserved).
    if ($totalGb -lt ($script:MinimumHostRamGb - 1)) {
        Write-Err "EyeNet requires at least $($script:MinimumHostRamGb) GB physical RAM (found ${totalGb} GB)."
        return $false
    }
    Write-Ok "Host RAM ${totalGb} GB"
    return $true
}

function Ensure-WslConfig {
    $wslConfigPath = Join-Path $env:USERPROFILE ".wslconfig"
    $content = @"
[wsl2]
memory=$($script:TargetWslMemoryGb)GB
processors=$($script:TargetWslProcessors)
swap=2GB
localhostForwarding=true
networkingMode=mirrored
"@
    $needsWrite = $true
    if (Test-Path $wslConfigPath) {
        $existing = Get-Content $wslConfigPath -Raw
        if ($existing -match "memory\s*=\s*$($script:TargetWslMemoryGb)GB" -and
            $existing -match "processors\s*=\s*$($script:TargetWslProcessors)") {
            $needsWrite = $false
        }
    }
    if ($needsWrite) {
        Set-Content -Path $wslConfigPath -Value $content -Force
        Write-Ok "Wrote $wslConfigPath ($($script:TargetWslMemoryGb)GB / $($script:TargetWslProcessors) CPUs)"
        Write-Warn "Shutting down WSL so memory settings apply..."
        wsl --shutdown 2>$null
        Start-Sleep -Seconds 2
    } else {
        Write-Ok "WSL config already meets EyeNet memory policy"
    }
}

function Test-WslInstalled {
    try {
        wsl --status 2>$null | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Get-WslDistros {
    $raw = wsl -l -q 2>$null
    if (-not $raw) { return @() }
    return @($raw | ForEach-Object { ($_ -replace "`0", "").Trim() } | Where-Object { $_ })
}

function Ensure-UbuntuBase {
    $distros = Get-WslDistros
    if ($distros -contains $UbuntuVersion -or ($distros | Where-Object { $_ -like "Ubuntu*" })) {
        Write-Ok "Ubuntu base present"
        return
    }
    Write-Info "Installing $UbuntuVersion from Microsoft Store / wsl --install..."
    wsl --install -d $UbuntuVersion --no-launch
    Write-Warn "If Ubuntu setup prompts for a UNIX username, complete that once, then re-run this script."
}

function Ensure-EyeNetDistro {
    $distros = Get-WslDistros
    if ($distros -contains $DistroName) {
        Write-Ok "WSL distro '$DistroName' already exists"
        return
    }

    $base = $null
    foreach ($candidate in @($UbuntuVersion, "Ubuntu-22.04", "Ubuntu")) {
        if ($distros -contains $candidate) {
            $base = $candidate
            break
        }
    }
    if (-not $base) {
        $base = ($distros | Where-Object { $_ -like "Ubuntu*" } | Select-Object -First 1)
    }
    if (-not $base) {
        throw "No Ubuntu WSL distro found. Install Ubuntu from the Store or run: wsl --install -d Ubuntu-24.04"
    }

    Write-Info "Exporting '$base' and importing as '$DistroName'..."
    $exportDir = Join-Path $env:TEMP "eyenet-wsl-export"
    New-Item -ItemType Directory -Path $exportDir -Force | Out-Null
    $tarPath = Join-Path $exportDir "ubuntu-base.tar"
    $installPath = Join-Path $env:LOCALAPPDATA "eyenet-wsl"

    wsl --export $base $tarPath
    New-Item -ItemType Directory -Path $installPath -Force | Out-Null
    wsl --import $DistroName $installPath $tarPath --version 2
    Remove-Item $tarPath -Force -ErrorAction SilentlyContinue
    Write-Ok "Created WSL distro '$DistroName' at $installPath"
}

function Invoke-InEyeNet([string]$Bash) {
    wsl -d $DistroName --user root -- bash -lc $Bash
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed inside WSL distro '$DistroName' (exit $LASTEXITCODE)"
    }
}

function Configure-SystemdAndDocker {
    Write-Info "Enabling systemd in $DistroName..."
    Invoke-InEyeNet @"
set -euo pipefail
if [ ! -f /etc/wsl.conf ] || ! grep -q 'systemd=true' /etc/wsl.conf 2>/dev/null; then
  mkdir -p /etc
  printf '[boot]\nsystemd=true\n' > /etc/wsl.conf
fi
"@

    Write-Warn "Restarting WSL to enable systemd..."
    wsl --shutdown 2>$null
    Start-Sleep -Seconds 3
    # Touch distro so it starts
    wsl -d $DistroName --user root -- echo ready | Out-Null

    Write-Info "Installing Docker Engine CE + Compose plugin (no Docker Desktop)..."
    # Use a single-quoted here-string so PowerShell does not expand $(...), $VARS, or [brackets].
    Invoke-InEyeNet @'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
# Ignore Windows/Docker-Desktop shims on PATH (/mnt/c/...).
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
if [ -x /usr/bin/docker ] && /usr/bin/docker compose version >/dev/null 2>&1; then
  echo 'Docker Engine already installed'
  systemctl enable --now docker || true
  /usr/bin/docker version
  exit 0
fi
apt-get update -y
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.asc ]; then
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
fi
. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
/usr/bin/docker version
/usr/bin/docker compose version
'@
    Write-Ok "Docker Engine CE ready inside $DistroName"
}

function Install-TailscaleClient {
    if ($SkipTailscale) {
        Write-Warn "Skipping Tailscale install (--SkipTailscale)"
        return
    }
    Write-Info "Installing Tailscale open-source client (do NOT log into Tailscale.com)..."
    Invoke-InEyeNet @"
set -euo pipefail
if command -v tailscale >/dev/null 2>&1; then
  echo 'Tailscale already installed'
  systemctl enable --now tailscaled || true
  exit 0
fi
curl -fsSL https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled
echo 'Tailscale installed. Wait for Node enroll_once (EyeNet Headscale) - do not run tailscale login to Tailscale.com.'
"@
    Write-Ok "Tailscale client installed; enrollment is via Authority Headscale"
}

function Assert-NotDesktopOnly {
    Write-Info "Verifying Docker Engine is available in $DistroName (not Desktop-only)..."
    $out = wsl -d $DistroName --user root -- bash -lc "export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin; /usr/bin/docker info --format '{{.Name}}' 2>/dev/null || true"
    $out = (($out | Out-String) -replace "`0", "").Trim()
    if (-not $out -or $out -match "could not be found|Docker Desktop") {
        throw "docker-ce is not usable inside '$DistroName'. Re-run this script or install docker-ce manually."
    }
    $desktop = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
    if ($desktop) {
        Write-Warn "Docker Desktop is running on Windows. EyeNet uses docker-ce inside '$DistroName' - prefer quitting Desktop to avoid confusion."
    }
    Write-Ok "Docker engine name: $out"
}

function Show-NextSteps {
    Write-Host ""
    Write-Host "  Next steps:" -ForegroundColor Cyan
    Write-Host "    1. cd to deployment/windows-installer"
    Write-Host "    2. Run install-platform.bat (or install-platform.ps1)"
    Write-Host "    3. When prompted, authenticate to ghcr.io inside WSL"
    Write-Host "    4. Open http://localhost:3000 and complete /bootstrap if needed"
    Write-Host "    5. Confirm VPN enrolls against https://vpn.eyenet-vision.com (not Tailscale.com)"
    Write-Host ""
    Write-Host "  Useful checks:" -ForegroundColor Cyan
    Write-Host "    wsl -d $DistroName -- docker version"
    Write-Host "    wsl -d $DistroName -- tailscale status"
    Write-Host ""
}

# --- main ---
Write-Host ""
Write-Host "  EyeNet WSL Runtime Bootstrap ($DistroName)" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-HostMemory)) { exit 1 }
if (-not (Test-WslInstalled)) {
    Write-Err "WSL is not installed. Run: wsl --install"
    exit 1
}

Ensure-WslConfig
Ensure-UbuntuBase
Ensure-EyeNetDistro
Configure-SystemdAndDocker
Install-TailscaleClient
Assert-NotDesktopOnly
Show-NextSteps
Write-Ok "WSL full-product runtime is ready"
