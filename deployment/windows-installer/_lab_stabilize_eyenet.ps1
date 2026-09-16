$ErrorActionPreference = "Continue"

# 8GB leaves headroom on a ~16GB Windows host so the WSL VM is not OOM-killed.
$wslConfig = @"
[wsl2]
memory=8GB
processors=4
swap=4GB
networkingMode=mirrored
vmIdleTimeout=-1
"@
Set-Content -Path "$env:USERPROFILE\.wslconfig" -Value $wslConfig -Encoding ascii
Write-Host "Wrote .wslconfig (8GB / vmIdleTimeout=-1)"

# Persistent keep-alive + stack start at user logon (survives SSH disconnect).
$actionCmd = 'wsl.exe --set-default eyenet & wsl.exe -d eyenet -u root -- systemctl start docker & wsl.exe -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d" & wsl.exe -d eyenet -u root -- sleep infinity'
schtasks /Create /TN "EyeNetKeepAlive" /TR $actionCmd /SC ONLOGON /RL HIGHEST /F | Out-Host

Write-Host "Restarting WSL..."
wsl --shutdown
Start-Sleep -Seconds 4
wsl --set-default eyenet 2>$null | Out-Null

Write-Host "Starting docker + compose..."
wsl -d eyenet -u root -- systemctl enable --now docker
wsl -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d"

# Detached keepalive via schtasks run-now (independent of this SSH session)
schtasks /Run /TN "EyeNetKeepAlive" | Out-Host

Write-Host "Wait 25s..."
Start-Sleep -Seconds 25
wsl -l -v

Write-Host "Health:"
foreach ($u in @("http://127.0.0.1:3000/", "http://127.0.0.1:8080/health")) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 8
    Write-Host ("  OK {0} -> {1}" -f $u, [int]$r.StatusCode)
  } catch {
    Write-Host ("  FAIL {0} -> {1}" -f $u, $_.Exception.Message)
  }
}

Write-Host "Wait another 40s to confirm it stays up..."
Start-Sleep -Seconds 40
wsl -l -v
try {
  $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/health -TimeoutSec 8
  Write-Host ("still_gw={0}" -f [int]$r.StatusCode)
} catch {
  Write-Host "still_gw=FAIL"
}
