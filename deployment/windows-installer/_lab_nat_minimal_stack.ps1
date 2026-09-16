$ErrorActionPreference = "Continue"

# NAT mode is more stable than mirrored on some Windows builds.
$wslConfig = @"
[wsl2]
memory=8GB
processors=4
swap=4GB
localhostForwarding=true
vmIdleTimeout=-1
"@
Set-Content -Path "$env:USERPROFILE\.wslconfig" -Value $wslConfig -Encoding ascii
Write-Host "Using NAT + localhostForwarding (no mirrored)"

wsl --shutdown
Start-Sleep -Seconds 4

Write-Host "Boot eyenet and capture systemd state..."
wsl -d eyenet -u root -- bash -lc "systemctl is-system-running; systemctl --failed --no-pager; free -h; df -h / | tail -1"
wsl -d eyenet -u root -- systemctl enable --now docker
wsl -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d postgres redis ppl-meta-node ppl-meta-gateway ppl-meta-frontend"

# Keepalive in a separate cmd window that survives SSH better
$bat = @'
@echo off
wsl -d eyenet -u root -- sleep infinity
'@
Set-Content -Path "C:\ppl-meta-platform\_keepalive.bat" -Value $bat -Encoding ascii
Start-Process -FilePath "cmd.exe" -ArgumentList "/c C:\ppl-meta-platform\_keepalive.bat" -WindowStyle Minimized

Write-Host "Immediate health..."
Start-Sleep -Seconds 8
wsl -l -v
foreach ($u in @("http://127.0.0.1:3000/", "http://127.0.0.1:8080/health", "http://127.0.0.1:8001/health")) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 5
    Write-Host ("  OK {0} -> {1}" -f $u, [int]$r.StatusCode)
  } catch {
    Write-Host ("  FAIL {0}" -f $u)
  }
}

Write-Host "Sleep 45s..."
Start-Sleep -Seconds 45
wsl -l -v
try {
  $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/health -TimeoutSec 5
  Write-Host ("still_gw={0}" -f [int]$r.StatusCode)
} catch {
  Write-Host "still_gw=FAIL"
  Write-Host "Last journal:"
  wsl -d eyenet -u root -- bash -lc "journalctl -b -n 40 --no-pager" 2>&1 | Select-Object -Last 40
}
