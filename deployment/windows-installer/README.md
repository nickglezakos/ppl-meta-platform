# Windows Installer Bundle

This directory contains the first MVP installer bundle for Windows deployments.

Current published release:

- `2.25.48`
- registry: `ghcr.io/nickglezakos/ppl-meta-platform`
- architecture: **`linux/amd64`** (compatible with Intel/AMD Windows PCs via Docker Desktop)
- status: ready to pull pinned images for the Windows installer stack

Release verification:

```bash
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.25.48
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:2.25.48
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:2.25.48
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:2.25.48
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:2.25.48
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:2.25.48
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend:2.25.48
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision-protected:2.25.48
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta-protected:2.25.48
```

Verify that each manifest shows `"architecture": "amd64"` and `"os": "linux"`.

If these commands return manifest JSON, the published release is present in GHCR and the Windows installer can pull it.

## Goals

- keep the installer small
- treat Docker Desktop as a prerequisite
- pull exact image tags from a private registry
- target **AMD64 (Intel/AMD)** architecture for Windows PC compatibility
- avoid local image builds on customer machines
- keep disk usage controlled on machines with limited free space
- avoid mandatory manual env-file editing before first install

## Files

- `install-platform.bat`: **Double-click to run — no setup required.** Single-file installer & management console. Auto-downloads the compose file and env template from GitHub raw. Works on any Windows PC.
- `install-platform.ps1`: PowerShell alternative with enhanced features (clipboard copy, color-coded logs, secure password input). Requires `Set-ExecutionPolicy RemoteSigned`.
- `docker-compose.windows-installer.yml`: pinned-image compose bundle for Windows deployment (auto-downloaded)
- `.env.windows.template`: environment template used as the base for first-run installer values (auto-downloaded)

## Low-Disk Strategy

This bundle is intentionally designed to avoid building images on the Windows machine.

Build all images for **`linux/amd64`** on a build machine (macOS or Linux), then push to the private registry:

### Build all Windows installer images (AMD64):

```bash
# From the project root, build all 9 services for linux/amd64:
./scripts/build_windows_installer_images.sh

# Or build only specific services:
./scripts/build_windows_installer_images.sh node media gateway

# To override the platform (e.g., if building on ARM Mac for testing):
PLATFORM=linux/arm64 ./scripts/build_windows_installer_images.sh
```

### Push all images to the registry:

```bash
# Push all 9 services with the current VERSION tag:
./scripts/push_protected_service_images.sh

# Or push only specific services:
./scripts/push_protected_service_images.sh vision vmeta
```

### Build and push protected services only:

```bash
./scripts/build_protected_service_images.sh
./scripts/push_protected_service_images.sh vision vmeta
```

> **Important:** When building on an Apple Silicon (ARM) Mac, Docker will cross-compile to AMD64 because `--platform linux/amd64` is set by default. This may be slower but produces images that run correctly on Windows PCs.

On the Windows target, only run pulls for exact tags.

## Deploying on Windows

### Quick Start (Recommended: `.bat` file)

1. Download **only** `install-platform.bat` to any folder on the Windows PC.
2. **Double-click** the file to run it (or run from Command Prompt).
3. The script handles everything:
   - Prompts for the install directory (default: `C:\ppl-meta-platform`)
   - Downloads `docker-compose.windows-installer.yml` and `.env.windows.template` from GitHub
   - Creates and configures `.env.windows` (prompts for `INSTALLATION_UUID`, `APPLICATION_KEY`, `POSTGRES_PASSWORD`)
   - Checks Docker Desktop is running (waits if needed)
   - Auto-configures WSL 2 memory/CPU limits (8 GB / 6 CPUs)
   - Pulls all 11 Docker images from GHCR
   - Starts the stack and waits for health checks
   - Displays container status and the frontend URL

### Alternative: PowerShell Script

If you can run PowerShell scripts, use `install-platform.ps1` for enhanced features:
- Color-coded terminal output with EyeNet branding
- Secure password input (hidden characters)
- Copy container logs to clipboard
- Modern terminal UI with box drawing

```powershell
# One-time execution policy setup (if needed):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run the script:
.\install-platform.ps1
```

### Main Menu

The script doubles as a management console:

| Option | Description |
|---|---|
| **1. Install / Reconfigure** | Full install flow or re-download files and update config |
| **2. Start All Containers** | Runs `docker compose up -d`, waits for health |
| **3. Stop All Containers** | Runs `docker compose down` (data volumes preserved) |
| **4. View Container Status** | Shows `docker compose ps` with color-coded health |
| **5. View Container Logs** | Select any container, view last 150 lines, copy to clipboard, or follow live |
| **6. Exit** | Quits the script |

### Log Viewer

When viewing container logs, you can:
- **C** — Copy all displayed logs to clipboard
- **F** — Follow logs live (Ctrl+C to stop)
- **B** — Back to container list

### Requirements

- Windows 10/11 with **Docker Desktop** (WSL 2 backend)
- Minimum 12 GB free disk space
- Internet connection (to pull images from GHCR)

### First-Time User Registration

After the platform starts:
1. Open **http://localhost:3000**
2. Register with the exact email that is set as `approved_owner_email` in the Authority entitlement
3. The platform activates automatically against `authority.eyenet-vision.com`

For the current published release, the generated `.env.windows` should keep `RELEASE_TAG=2.25.48` unless you are intentionally deploying a different pinned release.
