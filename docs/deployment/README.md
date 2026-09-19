# Deployment documentation

**Scripts and installers live in** [`deployment/`](../../deployment/) (runnable assets).  
**CI/CD and operator docs live here** in `docs/deployment/` (how releases work).

## Single source of truth

| Document | Role |
|---|---|
| **[platform-release-cicd.md](./platform-release-cicd.md)** | **Canonical CI/CD:** Stage 1 = git push + CHANGELOG (frequent); Stage 2 = build/push GHCR images on a Windows/Linux host; one product, two installers |
| **[`CHANGELOG.md`](../../CHANGELOG.md)** | Product release notes (required on every meaningful Stage 1) |
| [windows-wsl-docker-engine-full-product.md](./windows-wsl-docker-engine-full-product.md) | Windows preferred runtime (Docker Engine CE in WSL `eyenet`) |
| [windows-via-tailscale-eyenet-images.md](./windows-via-tailscale-eyenet-images.md) | GHCR pull + Tailscale/mesh notes for Windows |
| [STAGING_DEPLOYMENT.md](./STAGING_DEPLOYMENT.md) | Staging notes (legacy / environment-specific) |
| [PRODUCTION_ROLLOUT.md](./PRODUCTION_ROLLOUT.md) | Production rollout notes (legacy / environment-specific) |

## Script trees (not docs)

| Path | What it is |
|---|---|
| `deployment/windows-installer/` | Windows/WSL installer bundle + shared compose + schema pack + discovery reregister |
| `deployment/ubuntu/` | Native Ubuntu 24.04 lab installer (`install-eyenet-ubuntu.sh`) |
| `deployment/mac-lima/` | Mac Lima helpers (thin wrappers where possible) |
| `scripts/build_windows_installer_images.sh` | **Stage 2** image build (`linux/amd64`) on Windows/Linux host |
| `scripts/push_protected_service_images.sh` | **Stage 2** push to GHCR |
| `scripts/verify_platform_release.sh` | Confirms all twelve GHCR tags exist |
| `scripts/check_installer_pins.sh` | Confirms both installers pin root `VERSION` |
| `.github/workflows/platform-release.yml` | Draft Stage 2 automation — not used yet |

## Policy / proposals (background, not day-to-day)

Lifecycle policy and Authority channel design stay under:

- `docs/proposals/CICD policy and implementation/`

Those documents **must not contradict** [platform-release-cicd.md](./platform-release-cicd.md). When they diverge, update the truth doc first, then the proposal.
