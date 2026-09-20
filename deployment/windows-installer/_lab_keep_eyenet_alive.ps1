$ErrorActionPreference = "Continue"

$wslConfig = @"
[wsl2]
memory=12GB
processors=6
swap=2GB
localhostForwarding=true
vmIdleTimeout=-1
"@
Set-Content -Path "$env:USERPROFILE\.wslconfig" -Value $wslConfig -Encoding ascii
Write-Host "Wrote .wslconfig with vmIdleTimeout=-1"

wsl --shutdown
Start-Sleep -Seconds 3
wsl --set-default eyenet 2>$null | Out-Null

Write-Host "=== systemd / docker ==="
wsl -d eyenet -u root -- cat /etc/wsl.conf
wsl -d eyenet -u root -- systemctl is-system-running
wsl -d eyenet -u root -- systemctl enable --now docker
wsl -d eyenet -u root -- systemctl is-active docker
wsl -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d"

# Keep a long-lived WSL process from Windows so the VM cannot idle-exit.
$keepAlive = Start-Process -FilePath "wsl.exe" -ArgumentList @("-d","eyenet","-u","root","--","sleep","infinity") -WindowStyle Hidden -PassThru
Write-Host ("keepalive_pid={0}" -f $keepAlive.Id)

Write-Host "Waiting 20s then recheck WSL state..."
Start-Sleep -Seconds 20
wsl -l -v

Write-Host "Windows health:"
foreach ($u in @("http://127.0.0.1:3000/", "http://127.0.0.1:8080/health")) {
  try {
    $r = Invoke-WebRequest -UseBasicParsing -Uri $u -TimeoutSec 8
    Write-Host ("  OK {0} -> {1}" -f $u, [int]$r.StatusCode)
  } catch {
    Write-Host ("  FAIL {0} -> {1}" -f $u, $_.Exception.Message)
  }
}
