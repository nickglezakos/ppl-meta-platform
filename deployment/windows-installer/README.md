# Windows Installer Bundle

This directory contains the first MVP installer bundle for Windows deployments.

Current release pin (tracks repository root `VERSION`):

- `2.25.79`
- registry: `ghcr.io/nickglezakos/ppl-meta-platform`
- architecture: **`linux/amd64`** (Intel/AMD Windows PCs via Docker Desktop)
- host standard: **≥16 GB physical RAM**
- WSL / Docker Desktop memory: **12 GB** (`processors=6`, `swap=2GB`)
- compose: per-service `mem_limit` / `mem_reservation` per CI/CD policy

Release verification:

```bash
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.25.79
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:2.25.79
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:2.25.79
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:2.25.79
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:2.25.79
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:2.25.79
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend:2.25.79
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision-protected:2.25.79
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta-protected:2.25.79
```

Verify that each manifest shows `"architecture": "amd64"` and `"os": "linux"`.

## Goals

- keep the installer small
- treat Docker Desktop as a prerequisite
- pull exact image tags from GHCR (not Docker Hub)
- target **AMD64 (Intel/AMD)** architecture for Windows PC compatibility
- avoid local image builds on customer machines
- enforce the 16 GB host / 12 GB WSL resource policy
- hand off first-owner activation to frontend `/bootstrap`

## Files

- `install-platform.bat`: Double-click installer and management console
- `install-platform.ps1`: PowerShell alternative
- `docker-compose.windows-installer.yml`: pinned-image compose with memory budgets
- `.env.windows.template`: environment template (`RELEASE_TAG` must match `VERSION`)

## Build And Push

```bash
./scripts/build_windows_installer_images.sh
./scripts/push_protected_service_images.sh
```

Or use `.github/workflows/platform-release.yml` (`workflow_dispatch`).

## First-Time Owner Activation

After the platform starts:

1. Open **http://localhost:3000**
2. When bootstrap is pending, the app routes to `/bootstrap`
3. Activate with the Authority-approved owner email and `lic_…` application key

For the current release pin, generated `.env.windows` should keep `RELEASE_TAG=2.25.79` unless you intentionally deploy another published tag.

## Related Policy

- [Installation lifecycle CI/CD policy](../../docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md)
- [Manual Windows deployment checklist](../../docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md)
