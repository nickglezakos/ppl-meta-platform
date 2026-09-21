@echo off
REM Start EyeNet (WSL eyenet / docker-ce). Use this after reboot/sleep.
wsl --set-default eyenet >nul 2>&1
wsl -d eyenet -u root -- systemctl start docker
wsl -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d"
REM Media uid 1001 vs fresh root-owned volume (upload Permission denied). Prefer image entrypoint after Stage 2; this covers older images.
wsl -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && if [ -f ensure-media-volume-perms.sh ]; then bash ensure-media-volume-perms.sh; elif [ -f /mnt/c/ppl-meta-platform/deployment/windows-installer/ensure-media-volume-perms.sh ]; then bash /mnt/c/ppl-meta-platform/deployment/windows-installer/ensure-media-volume-perms.sh; fi"
wsl -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && bash reregister-discovery-services.sh"
start "" cmd /c "wsl -d eyenet -u root -- sleep infinity"
echo Waiting for UI...
ping -n 15 127.0.0.1 >nul
start http://127.0.0.1:3000/
echo Opened http://127.0.0.1:3000/
echo Keep the minimized keepalive window running.
pause
