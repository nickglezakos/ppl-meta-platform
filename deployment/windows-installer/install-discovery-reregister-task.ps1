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
    Write-Error "Missing $scriptPath - copy reregister-discovery-services.sh into the install dir first."
    exit 1
}

$drive = $InstallDir.Substring(0, 1).ToLower()
$rest = ($InstallDir.Substring(2) -replace '\\', '/')
$wslCwd = "/mnt/$drive$rest"
# Prefer semicolon over double-ampersand for Windows PowerShell 5.1 safety.
$bash = "cd '$wslCwd'; bash reregister-discovery-services.sh"
$argList = "-d $DistroName -u root -- bash -lc `"$bash`""

$action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument $argList
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerLogon.Delay = "PT2M"
# TimeSpan.MaxValue is rejected by Task Scheduler XML; use a long finite window.
$triggerPeriodic = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(2) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($triggerLogon, $triggerPeriodic) -Settings $settings -Principal $principal -Force | Out-Null
Write-Host ("Scheduled task {0} installed - logon+2m, every {1}m" -f $TaskName, $IntervalMinutes)
Write-Host ("  wsl.exe {0}" -f $argList)
exit 0
