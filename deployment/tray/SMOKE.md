# Lab smoke checklist (Windows WSL + Ubuntu)

Prerequisites: tray binary available (GitHub Release `vVERSION` **or** local copy), stack installable.

## Windows (`lab-home-win-nickg` or Windows boot on `lab-work-dual-64g`)

1. Re-run installer or place `eyenet-tray-windows-amd64-*.exe` in `InstallDir\tray\eyenet-tray.exe` with `%ProgramData%\EyeNet\tray.json`.
2. Confirm Startup: `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\EyeNet Tray.lnk`.
3. Tray tooltip shows pin + Inactive/Active.
4. **Start** → containers up; tooltip **Active**; Open UI → `:3000`.
5. **Stop** → Inactive; **Restart** → Active + discovery still works (phone / Network page).

## Ubuntu (Ubuntu boot on `lab-work-dual-64g` or `lab-work-u24-mini-8g`)

1. Re-run `install-eyenet-ubuntu.sh` or extract tarball under `~/eyenet-platform/tray/`.
2. Confirm `~/.config/autostart/eyenet-tray.desktop`.
3. Same Start / Stop / Restart / Open UI checks as Windows.

## Local (Mac) pre-lab gate

```bash
cd deployment/tray && go test ./... && go build -o /tmp/eyenet-tray ./cmd/eyenet-tray
```
