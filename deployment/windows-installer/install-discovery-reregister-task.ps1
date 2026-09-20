# Install / refresh required EyeNet discovery re-register scheduled task.
# Runs reregister-discovery-services.sh via WSL after logon and every 10 minutes.
# Requires: install dir with reregister-discovery-services.sh; WSL distro eyenet.
# Prefer Administrator so the task runs whether or not the user is elevated later.

param(
    [string]$InstallDir = "C:\ppl-meta-platform",
    [string]$DistroName = "eyenet",
    [string]$TaskName = "EyeNetDiscoveryReregister",
    [int]$IntervalMinutes = 10
)

$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $InstallDir "reregister-discovery-services.sh"
if (-not (Test-Path $scriptPath)) {
    Write-Error "Missing $scriptPath — copy reregister-discovery-services.sh into the install dir first."
    exit 1
}

$drive = $InstallDir.Substring(0, 1).ToLower()
$rest = ($InstallDir.Substring(2) -replace '\\', '/')
$wslCwd = "/mnt/$drive$rest"
$bash = "cd '$wslCwd' && bash reregister-discovery-services.sh"
$tr = "wsl.exe -d $DistroName -u root -- bash -lc `"$bash`""

# ONLOGON with delay, plus periodic trigger
$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d $DistroName -u root -- bash -lc `"$bash`""
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerLogon.Delay = "PT2M"
$triggerPeriodic = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration ([TimeSpan]::MaxValue)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerLogon, $triggerPeriodic) -Settings $settings -Principal $principal -Force | Out-Null
Write-Host "Scheduled task $TaskName installed (logon+2m, every ${IntervalMinutes}m)"
Write-Host "  $tr"
exit 0
