EyeNet Platform — Windows installer (2.25.104)

Requirements
- Windows 10/11 amd64 (Intel/AMD), administrator account
- At least 16 GB physical RAM
- At least 12 GB free disk
- Internet access to pull images from ghcr.io

Install (run as Administrator)

1. Unzip this folder to a temporary location (e.g. Downloads\eyenet-windows-2.25.104).
2. Double-click install-eyenet-wsl.bat
   - Creates WSL2 distro "eyenet" with Docker Engine CE (not Docker Desktop)
   - May ask to restart WSL once; re-run this step if prompted
3. Double-click install-platform.bat
   - Default install directory: C:\ppl-meta-platform
   - Pulls pinned GHCR images, applies schema, installs EyeNet tray
4. Open http://localhost:3000 and complete /bootstrap with your approved
   owner email and lic_… application key from Authority.

EyeNet tray
- Appears in the system tray (Start / Stop / Restart / Open UI)
- Also starts at Windows logon

Support
- User guide: https://wiki.eyenet-vision.com/owners-admins/
