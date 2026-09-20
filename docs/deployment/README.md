# Deployment documentation

**Scripts and installers live in** [`deployment/`](../../deployment/) (runnable assets).  
**CI/CD and operator docs live here** in `docs/deployment/` (how releases work).

## Single source of truth

| Document | Role |
|---|---|
| **[eyenet-cicd-operator-guide.md](./eyenet-cicd-operator-guide.md)** | **Operator guide (for dummies + full detail):** Stage 1/2 walkthrough, Mode D manifest, terminology appendix |
| **[platform-release-cicd.md](./platform-release-cicd.md)** | **Canonical CI/CD contract:** Stage 1 = code (+ optional tray tag); Stage 2 = GHCR on a lab PC; Stage 3 = install images + tray |
| **[tray-stage-1.5-publish.md](./tray-stage-1.5-publish.md)** | Manual tray build + `gh release` upload checklist |
| **[lab-machines.md](./lab-machines.md)** | Named lab inventory (home Windows, work Ubuntu mini 8 GB, work dual-boot 64 GB) + access for Stage 2 |
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
| `deployment/tray/` | Host tray (Go systray) — Windows + Ubuntu; **manual** publish to GitHub Releases today |
| `deployment/mac-lima/` | Mac Lima helpers (thin wrappers where possible) |
| `scripts/build_windows_installer_images.sh` | **Stage 2** image build (`linux/amd64`) on Windows/Linux host |
| `scripts/push_protected_service_images.sh` | **Stage 2** push to GHCR |
| `scripts/stage2_one.sh` | **Stage 2** one-by-one build+push with report line |
| `scripts/stage2_changed_services.sh` | **Stage 2** selective list from git diff |
| `scripts/stage2_retag_forward.sh` | **Stage 2 Mode D** retag unchanged images onto a new pin |
| `scripts/write_release_manifest.sh` | Write digest `release-manifest.yml` from GHCR |
| `scripts/verify_release_manifest.sh` | Verify manifest digests match GHCR |
| `scripts/stage2_finalize_manifest.sh` | Tag verify → write manifest → digest verify |
| `scripts/verify_platform_release.sh` | Confirms all twelve GHCR tags exist |
| `scripts/check_installer_pins.sh` | Confirms both installers pin root `VERSION` |
| `deployment/windows-installer/release-manifest.yml` | Digest coherence artifact for current `VERSION` (written after Stage 2) |
| `.github/workflows/tray-release.yml` | **Future** tray automation — draft; not used today |
| `.github/workflows/platform-release.yml` | Draft Stage 2 automation — not used yet |

## Policy / proposals (background, not day-to-day)

Lifecycle policy and Authority channel design stay under:

- `docs/proposals/CICD policy and implementation/`

Those documents **must not contradict** [platform-release-cicd.md](./platform-release-cicd.md). When they diverge, update the truth doc first, then the proposal.
