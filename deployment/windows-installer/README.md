# Windows Installer Bundle

This directory contains the first MVP installer bundle for Windows deployments.

Current release pin (tracks repository root `VERSION`):

- `2.25.81`
- registry: `ghcr.io/nickglezakos/ppl-meta-platform`
- architecture: **`linux/amd64`** (Intel/AMD Windows PCs via Docker Desktop)
- host standard: **≥16 GB physical RAM**
- WSL / Docker Desktop memory: **12 GB** (`processors=6`, `swap=2GB`)
- compose: per-service `mem_limit` / `mem_reservation` per CI/CD policy

Release verification:

```bash
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.25.81
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:2.25.81
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:2.25.81
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:2.25.81
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:2.25.81
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:2.25.81
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend:2.25.81
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision-protected:2.25.81
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta-protected:2.25.81
```

Verify that each manifest shows `"architecture": "amd64"` and `"os": "linux"`.

## Goals

- keep the installer small
- prefer Docker Engine CE in WSL distro `eyenet` (no Docker Desktop)
- pull exact image tags from GHCR (not Docker Hub)
- target **AMD64 (Intel/AMD)** architecture for Windows PC compatibility
- avoid local image builds on customer machines
- enforce the 16 GB host / 12 GB WSL resource policy
- hand off first-owner activation to frontend `/bootstrap`
- include cameras, presence, models for full-product (no-USB) demos

## Files

- `install-eyenet-wsl.bat` / `install-eyenet-wsl.ps1`: one-time WSL runtime bootstrap
- `install-platform.bat`: Double-click installer and management console
- `install-platform.ps1`: PowerShell alternative (WSL docker-aware)
- `docker-compose.windows-installer.yml`: pinned-image compose with memory budgets (`pgvector/pgvector:pg15`)
- `.env.windows.template`: environment template (`RELEASE_TAG` must match `VERSION`)
- `schema/`: **vendored DB migrations** (synced from the monorepo) — installer always applies + verifies

## Database schema (installer always matches repo)

Before releasing or testing installs, refresh the pack from the monorepo:

```bash
bash deployment/mac-lima/sync-schema-pack.sh
```

`install-platform.ps1` runs `schema/apply.sh` after Postgres is healthy and **fails the install** if `schema/verify.sh` invariants do not pass. Do not use `deployment/mac-lima/sql/archive-stubs`.

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

For the current release pin, generated `.env.windows` should keep `RELEASE_TAG=2.25.81` unless you intentionally deploy another published tag.

## Preferred runtime (full-product demo)

Docker Desktop remains a legacy bootstrap path. The **supported full-product path** is Docker Engine CE inside one WSL2 distro (`eyenet`), with Tailscale joining Hetzner Headscale (no Tailscale.com account). See:

- [Windows WSL Docker Engine full-product spec](../../docs/deployment/windows-wsl-docker-engine-full-product.md)
- `install-eyenet-wsl.ps1` / `install-eyenet-wsl.bat` in this directory

## Public image pulls (no GHCR login)

Platform images under `ghcr.io/nickglezakos/ppl-meta-platform/` are intended to be **public** so Windows installs do not need a `read:packages` PAT.

After publishing a release, make packages public (once per package, not per tag):

```bash
./scripts/make_platform_ghcr_public.sh
```

Or GitHub → Packages → each `ppl-meta-*` → Package settings → Change visibility → Public.

Customers then only need network access:

```bash
docker pull ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.25.81
```

## Related Policy

- [Installation lifecycle CI/CD policy](../../docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md)
- [Manual Windows deployment checklist](../../docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md)
