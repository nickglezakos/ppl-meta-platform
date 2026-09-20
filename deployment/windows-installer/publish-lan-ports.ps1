# Publish EyeNet HTTP ports on the Windows LAN (and Windows Tailscale) NIC.
#
# WSL2 NAT + localhostForwarding already maps Windows 127.0.0.1:<port> into
# the eyenet distro. LAN phones and cameras talk to the *physical* NIC
# (192.168.x / 10.x) which does not get that mapping. This script adds
# netsh portproxy: <Windows NIC>:<port> -> 127.0.0.1:<port> so the real
# machine IP reaches the stack without depending on the WSL eth0 address
# (which changes on every WSL restart).
#
# Requires: Administrator (IP Helper + firewall + portproxy).
# Safe to re-run. Call after compose up and at Windows logon.

param(
    [string]$DistroName = "eyenet",
    [string]$EnvFile = "C:\ppl-meta-platform\.env.windows",
    [switch]$SkipLogonTask
)

$ErrorActionPreference = "Continue"
$RuleName = "EyeNet LAN ports"
$TaskName = "EyeNetLanPublish"
$DefaultPorts = @(3000, 8080, 8006, 8001, 8005, 8000, 8002, 8003, 8008, 8009, 8011, 8013)

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-EnvPortMap {
    $map = @{}
    if (-not (Test-Path $EnvFile)) { return $map }
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^(FRONTEND_PORT|GATEWAY_PORT|DISCOVERY_PORT|NODE_PORT|CAMERAS_PORT|MEDIA_PORT|ORCHESTRATOR_PORT|VISION_PORT|VMETA_PORT|COMMUNICATIONS_PORT|PRESENCE_PORT|MODELS_PORT)=(\d+)\s*$') {
            $map[$matches[1]] = [int]$matches[2]
        }
    }
    return $map
}

function Get-EyeNetPorts {
    $e = Get-EnvPortMap
    $ports = @(
        $(if ($e.FRONTEND_PORT) { $e.FRONTEND_PORT } else { 3000 }),
        $(if ($e.GATEWAY_PORT) { $e.GATEWAY_PORT } else { 8080 }),
        $(if ($e.DISCOVERY_PORT) { $e.DISCOVERY_PORT } else { 8006 }),
        $(if ($e.NODE_PORT) { $e.NODE_PORT } else { 8001 }),
        $(if ($e.CAMERAS_PORT) { $e.CAMERAS_PORT } else { 8005 }),
        $(if ($e.MEDIA_PORT) { $e.MEDIA_PORT } else { 8000 }),
        $(if ($e.ORCHESTRATOR_PORT) { $e.ORCHESTRATOR_PORT } else { 8002 }),
        $(if ($e.VISION_PORT) { $e.VISION_PORT } else { 8003 }),
        $(if ($e.VMETA_PORT) { $e.VMETA_PORT } else { 8008 }),
        $(if ($e.COMMUNICATIONS_PORT) { $e.COMMUNICATIONS_PORT } else { 8009 }),
        $(if ($e.PRESENCE_PORT) { $e.PRESENCE_PORT } else { 8011 }),
        $(if ($e.MODELS_PORT) { $e.MODELS_PORT } else { 8013 })
    )
    return @($ports | Select-Object -Unique)
}

function Test-VirtualAdapter([string]$alias) {
    return $alias -match 'vEthernet|WSL|Hyper-V|Bluetooth|Loopback|Default Switch|Virtual'
}

function Get-EyeNetListenAddresses {
    # Physical LAN + Windows Tailscale. Skip WSL/Hyper-V virtual NICs so we
    # never publish on 172.19.x (the WSL vSwitch) or APIPA.
    $addrs = @()
    try {
        $addrs = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object {
                $_.IPAddress -notlike '127.*' -and
                $_.IPAddress -notlike '169.254.*' -and
                -not (Test-VirtualAdapter $_.InterfaceAlias)
            } |
            Select-Object -ExpandProperty IPAddress -Unique)
    } catch {
        $addrs = @()
    }
    return @($addrs)
}

function Get-EyeNetAdvertiseHost {
    # Phones on the same Wi-Fi must get the Windows LAN IP, not Tailscale CGNAT
    # and not a Docker/WSL 172.16/12 address.
    $candidates = @()
    try {
        $candidates = @(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
            Where-Object {
                $_.IPAddress -notlike '127.*' -and
                $_.IPAddress -notlike '169.254.*' -and
                $_.IPAddress -notlike '100.*' -and
                -not (Test-VirtualAdapter $_.InterfaceAlias)
            })
    } catch {
        $candidates = @()
    }
    $preferred = $candidates |
        Sort-Object @{
            Expression = {
                if ($_.InterfaceAlias -match 'Wi-Fi|WiFi|Ethernet|Local Area Connection') { 0 } else { 1 }
            }
        }, @{
            Expression = {
                if ($_.IPAddress -like '192.168.*') { 0 }
                elseif ($_.IPAddress -like '10.*') { 1 }
                else { 2 }
            }
        }
    $first = $preferred | Select-Object -First 1
    if ($first) { return $first.IPAddress }
    return $null
}

function Ensure-LocalhostForwarding {
    $wslConfigPath = Join-Path $env:USERPROFILE ".wslconfig"
    if (-not (Test-Path $wslConfigPath)) { return }
    $raw = Get-Content $wslConfigPath -Raw
    if ($raw -match '(?im)^\s*localhostForwarding\s*=') { return }
    if ($raw -notmatch '(?im)^\s*\[wsl2\]') { return }
    $updated = $raw -replace '(?im)(\[wsl2\][^\[]*)', "`$1localhostForwarding=true`r`n"
    Set-Content -Path $wslConfigPath -Value $updated -Encoding ascii
    Write-Host "  Added localhostForwarding=true to .wslconfig (takes effect on next wsl --shutdown)"
}

if (-not (Test-IsAdmin)) {
    Write-Host "ERROR: publish-lan-ports.ps1 must run as Administrator (portproxy + firewall)." -ForegroundColor Red
    Write-Host "  From an elevated PowerShell: powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit 1
}

$ports = Get-EyeNetPorts
if (-not $ports -or $ports.Count -eq 0) { $ports = $DefaultPorts }
$listenAddrs = Get-EyeNetListenAddresses
$advertise = Get-EyeNetAdvertiseHost

Write-Host "EyeNet LAN publish"
Write-Host ("  advertise_host={0}" -f $(if ($advertise) { $advertise } else { "(none)" }))
Write-Host ("  listen={0}" -f ($(if ($listenAddrs) { $listenAddrs -join ", " } else { "(none)" })))
Write-Host ("  ports={0}" -f ($ports -join ","))

if (-not $listenAddrs -or $listenAddrs.Count -eq 0) {
    Write-Host "ERROR: no Windows LAN/Tailscale IPv4 to publish on." -ForegroundColor Red
    exit 1
}

Ensure-LocalhostForwarding

try {
    Set-Service -Name iphlpsvc -StartupType Automatic -ErrorAction SilentlyContinue
    Start-Service -Name iphlpsvc -ErrorAction Stop
    Write-Host "  IP Helper running"
} catch {
    Write-Host ("  WARN: could not start IP Helper: {0}" -f $_.Exception.Message) -ForegroundColor Yellow
}

foreach ($listen in $listenAddrs) {
    foreach ($port in $ports) {
        netsh interface portproxy delete v4tov4 listenaddress=$listen listenport=$port 2>$null | Out-Null
        $null = netsh interface portproxy add v4tov4 listenaddress=$listen listenport=$port connectaddress=127.0.0.1 connectport=$port
    }
}
Write-Host "  portproxy -> 127.0.0.1 (localhostForwarding into WSL)"

Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $ports -Profile Any | Out-Null
Write-Host ("  firewall {0} allow TCP {1}" -f $RuleName, ($ports -join ","))

if (-not $SkipLogonTask) {
    $self = $PSCommandPath
    if ([string]::IsNullOrWhiteSpace($self)) {
        $self = Join-Path (Split-Path $EnvFile -Parent) "publish-lan-ports.ps1"
    }
    $tr = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$self`""
    schtasks /Create /TN $TaskName /TR $tr /SC ONLOGON /RL HIGHEST /F 2>$null | Out-Null
    Write-Host ("  scheduled task {0} (ONLOGON, highest)" -f $TaskName)
}

Write-Host ""
Write-Host "LAN / mesh URLs (use these, not 172.18.x):"
if ($advertise) {
    Write-Host ("  UI:        http://{0}:3000" -f $advertise)
    Write-Host ("  Gateway:   http://{0}:8080" -f $advertise)
    Write-Host ("  Discovery: http://{0}:8006" -f $advertise)
}
netsh interface portproxy show v4tov4
exit 0
