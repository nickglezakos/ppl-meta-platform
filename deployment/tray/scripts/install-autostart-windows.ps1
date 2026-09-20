#!/usr/bin/env pwsh
# Register EyeNet tray for Windows Startup (Current User).
param(
    [Parameter(Mandatory = $true)][string]$TrayExe,
    [Parameter(Mandatory = $true)][string]$ConfigPath,
    [switch]$LaunchNow
)

$ErrorActionPreference = "Stop"
if (-not (Test-Path $TrayExe)) {
    throw "Tray exe not found: $TrayExe"
}

$startup = [Environment]::GetFolderPath("Startup")
$shortcutPath = Join-Path $startup "EyeNet Tray.lnk"
$wsh = New-Object -ComObject WScript.Shell
$sc = $wsh.CreateShortcut($shortcutPath)
$sc.TargetPath = $TrayExe
$sc.Arguments = "`"$ConfigPath`""
$sc.WorkingDirectory = Split-Path -Parent $TrayExe
$sc.WindowStyle = 7
$sc.Description = "EyeNet platform tray"
$sc.Save()
Write-Host "Startup shortcut: $shortcutPath"

if ($LaunchNow) {
    Start-Process -FilePath $TrayExe -ArgumentList "`"$ConfigPath`"" -WindowStyle Hidden
    Write-Host "Launched EyeNet tray"
}
