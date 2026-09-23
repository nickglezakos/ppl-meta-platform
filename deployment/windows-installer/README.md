# Windows Installer Bundle

This directory contains the first MVP installer bundle for Windows deployments
and the **shared** compose + schema pack + discovery reregister used by the
native Ubuntu installer as well.

**CI/CD truth (one GHCR product, two installers):**  
[`docs/deployment/platform-release-cicd.md`](../../docs/deployment/platform-release-cicd.md)  
**Release notes:** [`CHANGELOG.md`](../../CHANGELOG.md)

Current release pin (tracks repository root `VERSION`):

- `2.25.83`
- registry: `ghcr.io/nickglezakos/ppl-meta-platform`
- architecture: **`linux/amd64`** (Intel/AMD Windows PCs via WSL Docker Engine)
- host standard: **≥16 GB physical RAM**
- WSL / Docker Desktop memory: **12 GB** (`processors=6`, `swap=2GB`)
- compose: per-service `mem_limit` / `mem_reservation` per CI/CD policy

Release verification:

```bash
./scripts/check_installer_pins.sh
./scripts/verify_platform_release.sh 2.25.83
```

Or inspect manifests:

```bash
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.25.83
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:2.25.83
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:2.25.83
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:2.25.83
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:2.25.83
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:2.25.83
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend:2.25.83
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision-protected:2.25.83
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta-protected:2.25.83
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
- `install-platform.ps1`: **canonical** Windows installer (WSL docker-aware: schema, reregister, tray, `ADVERTISE_HOST`)
- `install-platform.bat`: thin double-click launcher that runs `install-platform.ps1` (do not maintain a second install path)
- `docker-compose.windows-installer.yml`: pinned-image compose with memory budgets (`pgvector/pgvector:pg15`)
- `.env.windows.template`: environment template (`RELEASE_TAG` must match `VERSION`)
- `schema/`: **vendored DB migrations** (synced from the monorepo) — installer always applies + verifies
- `reregister-discovery-services.sh`: post-up discovery refresh (also used by Ubuntu installer)
- `publish-lan-ports.ps1`: WSL NAT portproxy so the Windows LAN IP (not `172.18.x`) reaches published ports
- `enroll-host-tailscale.sh`: root `tailscale up` on the WSL distro (Node container is non-root `appuser`)
- `install-discovery-reregister-task.ps1`: required scheduled task (logon + every 10m) for discovery re-register

## Fresh install / bootstrap soak

When testing **first-owner `/bootstrap`**, wipe compose volumes (or remove the
install dir data) before Stage 3. Reusing Postgres from a prior activate skips
bootstrap and opens **login** instead. Local EyeNet passwords are per-machine;
they are not shared with another lab PC or with Authority.
- Host tray (separate Stage 1.5): after install, downloads `eyenet-tray-windows-amd64-${VERSION}.exe` from GitHub Releases tag `v${VERSION}`, writes `%ProgramData%\EyeNet\tray.json`, registers Startup — see [`deployment/tray/`](../tray/)

## Database schema (installer always matches repo)

Before releasing or testing installs, refresh the pack from the monorepo:

```bash
bash deployment/mac-lima/sync-schema-pack.sh
```

`install-platform.ps1` runs `schema/apply.sh` after Postgres is healthy and **fails the install** if `schema/verify.sh` invariants do not pass, then runs `reregister-discovery-services.sh`. Do not use `deployment/mac-lima/sql/archive-stubs`.

## Build And Push (Stage 2 — Windows/Linux host)

Stage 1 is git push only. Stage 2 refreshes GHCR (run on an amd64 Windows or Linux builder, not the Mac by default):

```bash
./scripts/check_installer_pins.sh
# flutter build web --release in ppl-meta-frontend first
./scripts/build_windows_installer_images.sh
./scripts/push_protected_service_images.sh
./scripts/stage2_finalize_manifest.sh   # tags + write/verify release-manifest.yml
# Stage 1: commit deployment/windows-installer/release-manifest.yml
```

Prefer one-by-one / selective / retag-forward (Modes B–D) per [`docs/deployment/platform-release-cicd.md`](../../docs/deployment/platform-release-cicd.md). GitHub Actions is future Stage 2 automation only.

**Release manifest:** `release-manifest.yml` in this directory records digests for the twelve images at the current `VERSION`. Installers still pull by tag; the manifest is the coherence artifact.

## First-Time Owner Activation

After the platform starts:

1. Open **http://localhost:3000**
2. When bootstrap is pending, the app routes to `/bootstrap`
3. Activate with the Authority-approved owner email and `lic_…` application key

For the current release pin, generated `.env.windows` should keep `RELEASE_TAG=2.25.83` unless you intentionally deploy another published tag.

### Production note (INSTALLATION_UUID / APPLICATION_KEY)

`install-platform.ps1` does **not** prompt for `INSTALLATION_UUID` or `APPLICATION_KEY`. Fresh installs leave them empty so first-owner activation happens in the product UI at `/bootstrap` (Authority entitlement / `lic_…` key). Pre-seeded values in an existing `.env.windows` are preserved. Local `POSTGRES_PASSWORD` / `JWT_SECRET_KEY` are auto-generated when missing or still at template defaults.

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
docker pull ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.25.83
```

## Related Policy

- [Installation lifecycle CI/CD policy](../../docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md)
- [Manual Windows deployment checklist](../../docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md)
