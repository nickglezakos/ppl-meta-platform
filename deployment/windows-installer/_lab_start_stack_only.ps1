$ErrorActionPreference = "Continue"
wsl --set-default eyenet 2>$null | Out-Null

Write-Host "Starting eyenet docker..."
wsl -d eyenet -u root -- systemctl start docker
Start-Sleep -Seconds 4

Write-Host "Compose up..."
wsl -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d"

Write-Host "Waiting for gateway/frontend..."
$gatewayOk = $false
$frontendOk = $false
for ($i=1; $i -le 40; $i++) {
  if (-not $gatewayOk) {
    try {
      $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8080/health -TimeoutSec 3
      if ([int]$r.StatusCode -eq 200) { $gatewayOk = $true; Write-Host "Gateway up" }
    } catch {}
  }
  if (-not $frontendOk) {
    try {
      $r = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:3000/ -TimeoutSec 3
      if ([int]$r.StatusCode -eq 200) { $frontendOk = $true; Write-Host "Frontend up" }
    } catch {}
  }
  if ($gatewayOk -and $frontendOk) { break }
  Start-Sleep -Seconds 2
}

Write-Host ("gateway_ok={0} frontend_ok={1}" -f $gatewayOk, $frontendOk)
wsl -l -v
