# Run in PowerShell as Administrator on DESKTOP-VDM2JKF
# Enables OpenSSH Server so the Mac at 192.168.1.85 can build remotely.

$ErrorActionPreference = "Stop"

Write-Host "Installing OpenSSH Server capability (no-op if already present)..."
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0 | Out-Null

Write-Host "Starting sshd..."
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic

$existing = Get-NetFirewallRule -Name sshd -ErrorAction SilentlyContinue
if (-not $existing) {
    New-NetFirewallRule -Name sshd -DisplayName 'OpenSSH Server (sshd)' `
        -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
    Write-Host "Firewall rule created for TCP 22."
} else {
    Enable-NetFirewallRule -Name sshd
    Write-Host "Firewall rule for TCP 22 already existed; ensured Enabled."
}

Write-Host ""
Write-Host "sshd status:"
Get-Service sshd | Format-List Name, Status, StartType
Write-Host "Listening on:"
Get-NetTCPConnection -LocalPort 22 -State Listen -ErrorAction SilentlyContinue |
    Select-Object LocalAddress, LocalPort, State | Format-Table
Write-Host "Done. From Mac: ssh -o ConnectTimeout=8 nikg@192.168.1.71"
