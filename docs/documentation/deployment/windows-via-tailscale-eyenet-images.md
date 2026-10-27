# EyeNet on Windows via Tailscale — Image Publish + Install Walkthrough

**Date:** 2026-09-11 (notes); publish process updated 2026-09-19  
**Audience:** Developer on Mac reaching Windows lab PC over Tailscale  
**Goal:** Get GHCR platform images available, then install EyeNet on the Windows machine  
**Canonical CI/CD:** [platform-release-cicd.md](./platform-release-cicd.md) — **local build/push** (GitHub Actions not used for platform images yet)  
**Related:** `docs/guides/first-windows-release-2.25.82.md`, `deployment/windows-installer/`

---

## Roles (do not mix these up)

| Role | Machine | Job |
|------|---------|-----|
| **Operator Mac** | your MacBook (Tailscale mesh) | RDP to Windows; verify GHCR manifests; or build/push from any amd64-capable Docker host |
| **Windows lab PC** | e.g. Tailscale IP for RDP | Install by **pull**; may also build/push if that host has Docker + disk |
| **Image builder (current)** | Local Docker (`scripts/build_*.sh` + `scripts/push_*.sh`) | Seed GHCR with `linux/amd64` tags matching `VERSION` |
| **Image builder (future)** | GitHub Actions (`platform-release.yml`) | Optional later — same images, not a second product |

Customer Windows boxes still **pull** pinned images.

---

## 0. Mesh precondition (Mac)

```bash
open -a Tailscale
tailscale status
# Expect: kvalvis-pc  100.64.0.23  ... online (not offline)
tailscale ping 100.64.0.23
```

If Mac UI Network settings still shows “not connected” while CLI works: that screen hits **`http://localhost:8001/node/vpn/status`** (local Node), not the CLI. Ignore for remote Windows work; fix Node/UI later.

**Access Windows:** RDP / remote desktop to `100.64.0.23`, or whatever you already use on that PC. SSH only if you’ve enabled OpenSSH Server.

---

## 1. Get images into GHCR

**Current path:** local Docker build/push (see [platform-release-cicd.md §A](./platform-release-cicd.md)). Do not wait on GitHub Actions.

### Path A — Local build/push (from Mac or any Docker host) — use this

Registry: `ghcr.io/nickglezakos/ppl-meta-platform`  
Tag: match root `VERSION` and installer `RELEASE_TAG` / `VERSION` pins.

```bash
cd /path/to/ppl-meta-code
./scripts/check_installer_pins.sh
echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin
cd ppl-meta-frontend && flutter pub get && flutter build web --release && cd ..
RELEASE_TAG="$(tr -d '[:space:]' < VERSION)"
./scripts/build_windows_installer_images.sh
./scripts/push_protected_service_images.sh
./scripts/verify_platform_release.sh "$RELEASE_TAG"
```

### Path B — GitHub Actions — not used yet

`.github/workflows/platform-release.yml` is draft-only until Actions is enabled.

Twelve images that must exist after a local publish:

- `ppl-meta-node`
- `ppl-meta-media`
- `ppl-meta-gateway`
- `ppl-meta-orchestrator`
- `ppl-meta-discovery`
- `ppl-meta-communications`
- `ppl-meta-frontend`
- `ppl-meta-vision-protected`
- `ppl-meta-vmeta-protected`
- `ppl-meta-cameras`
- `ppl-meta-presence`
- `ppl-meta-models`

### Path C — Alternate: build on Windows lab (native amd64)

Same local scripts as Path A; useful if the Mac cannot build `linux/amd64` comfortably. On Windows (WSL2 Ubuntu recommended; scripts are bash):

1. Install Docker (WSL Engine preferred), Git, and Flutter for `flutter build web --release`.
2. Clone `ppl-meta-code` to a fast disk with **≥12 GB free**.
3. Login to GHCR (PAT with `write:packages`):

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin
```

4. Build frontend web assets, then images + push:

```bash
cd /path/to/ppl-meta-code
TAG=$(tr -d '[:space:]' < VERSION)

cd ppl-meta-frontend && flutter pub get && flutter build web --release && cd ..

RELEASE_TAG=$TAG ./scripts/build_windows_installer_images.sh
RELEASE_TAG=$TAG ./scripts/push_protected_service_images.sh
./scripts/verify_platform_release.sh $TAG
```

Builds default `PLATFORM=linux/amd64` — correct for the Windows installer compose.

---

## 2. Install EyeNet on the Windows PC (pull path)

After manifests verify OK:

### Preconditions

- Windows 10/11 **amd64**, **≥16 GB** RAM  
- Docker Desktop (WSL2); installer will push `.wslconfig` toward `memory=12GB`, `processors=6`, `swap=2GB`  
- ≥12 GB free disk  
- GHCR **read** token (`read:packages`)  
- Authority entitlement: approved owner email + `lic_…` application key  

### Steps

1. On Windows, use folder `deployment/windows-installer/` (clone repo or copy installer assets).
2. Confirm `install-platform.bat` `VERSION` / generated `RELEASE_TAG` **matches the published GHCR tag**.
3. Double-click `install-platform.bat` (or run elevated if needed).
4. Pass RAM check → allow WSL config → login to `ghcr.io` when prompted.
5. Wait for pull + compose up.
6. Open http://localhost:3000 → bootstrap if prompted → land on `/home`.

Health (PowerShell, from installer directory):

```powershell
docker compose -f docker-compose.windows-installer.yml --env-file .env.windows ps
curl http://localhost:8080/api/v1/licensing/bootstrap/status
```

From Mac over Tailscale (only if Windows ports are reachable on mesh / published):

```bash
curl -s http://100.64.0.23:3000/   # may be blocked by Windows firewall — RDP first if unsure
```

---

## 3. What success looks like

- [ ] `tailscale status` shows `kvalvis-pc` online at `100.64.0.23`
- [ ] All nine GHCR manifests OK for chosen tag
- [ ] Installer `RELEASE_TAG` == that tag
- [ ] Stack healthy on Windows; bootstrap complete; `/home` works

## 4. Out of scope for this walkthrough

- Authority `release_channel` automation  
- Pilot soak / stable promotion  
- Online wiki hosting  
- Fixing Flutter Network VPN stale UI (localhost:8001 Node probe)

## 5. Quick recovery

| Symptom | Check |
|---------|--------|
| Can’t see Windows on mesh | Mac Tailscale app + `tailscaled`; `tailscale up`; ping `.23` |
| Actions run fails / no runner | Expected today — do **not** use Actions; publish with local `build`/`push` scripts ([platform-release-cicd.md](./platform-release-cicd.md)) |
| `manifest unknown` | Publish Path A or B; re-run `verify_platform_release.sh` |
| Installer pulls wrong tag | Sync bat/`VERSION`/`.env.windows` (pin is **2.25.80**) |
| Bootstrap fails | Authority approved email + valid `lic_…` key |
```
