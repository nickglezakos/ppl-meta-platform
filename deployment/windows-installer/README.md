# Windows Installer Bundle

This directory contains the first MVP installer bundle for Windows deployments.

Current published release:

- `2.25.40`
- registry: `ghcr.io/nickglezakos/ppl-meta-platform`
- architecture: **`linux/amd64`** (compatible with Intel/AMD Windows PCs via Docker Desktop)
- status: ready to pull pinned images for the Windows installer stack

Release verification:

```bash
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.25.40
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:2.25.40
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:2.25.40
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:2.25.40
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:2.25.40
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:2.25.40
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend:2.25.40
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision-protected:2.25.40
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta-protected:2.25.40
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

- `docker-compose.windows-installer.yml`: pinned-image compose bundle for Windows deployment
- `.env.windows.template`: environment template used as the base for first-run installer values
- `install-platform.ps1`: PowerShell installer script that creates `.env.windows` from the template when needed, prompts for missing installation values and registry credentials, logs in, pulls images, and starts the stack

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

## Recommended Flow

1. Build `ppl-meta-vision-protected` and `ppl-meta-vmeta-protected` on a build machine.
2. Push those images and the rest of the platform images to the private registry.
3. Run `install-platform.ps1` on the Windows machine.
4. If `.env.windows` does not exist, the installer creates it from `.env.windows.template`.
5. Enter `INSTALLATION_UUID`, `APPLICATION_KEY`, and `POSTGRES_PASSWORD` when prompted if they are missing.
6. Enter `REGISTRY_USERNAME` and the GHCR token when prompted if they are missing.
7. Run platform health checks after startup.

For the current published release, the generated `.env.windows` should keep `RELEASE_TAG=2.25.40` unless you are intentionally deploying a different pinned release.

For a safer operator flow, leave `REGISTRY_PASSWORD` blank and paste the token only when the installer prompts for it.
