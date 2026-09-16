@echo off
REM Start EyeNet (WSL eyenet / docker-ce). Use this after reboot/sleep.
wsl --set-default eyenet >nul 2>&1
wsl -d eyenet -u root -- systemctl start docker
wsl -d eyenet -u root -- bash -lc "cd /mnt/c/ppl-meta-platform && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d"
start "" cmd /c "wsl -d eyenet -u root -- sleep infinity"
echo Waiting for UI...
ping -n 15 127.0.0.1 >nul
start http://127.0.0.1:3000/
echo Opened http://127.0.0.1:3000/
echo Keep the minimized keepalive window running.
pause
