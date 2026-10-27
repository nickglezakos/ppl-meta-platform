# First Windows Release — 2.25.82

**Canonical CI/CD (one GHCR product, two installers):**  
[`docs/deployment/platform-release-cicd.md`](../deployment/platform-release-cicd.md)  
**Release notes:** [`CHANGELOG.md`](../../CHANGELOG.md) (updated as part of every Stage 1)

This page is a **version-specific walkthrough** for `2.25.82`. Prefer the truth doc for ongoing process; keep this file for the exact commands used for this pin.

**Publish method today (two stages):**  
1. Push code to GitHub often.  
2. When ready, connect this Mac to a **Windows or Linux** amd64 host and build/push GHCR images there.  
See [`docs/deployment/platform-release-cicd.md`](../deployment/platform-release-cicd.md). GitHub Actions is not used for platform images yet.

**Goal:** Publish platform images to GHCR and install them on Windows/WSL **and** native Ubuntu 24.

**Release tag:** `2.25.82` (root `VERSION`)  
**Registry:** `ghcr.io/nickglezakos/ppl-meta-platform`  
**Host requirement:** ≥16 GB RAM, WSL memory 12 GB (Windows path)  
**Preferred Windows runtime:** Docker Engine CE in WSL distro `eyenet` (no Docker Desktop) — see [windows-wsl-docker-engine-full-product.md](../deployment/windows-wsl-docker-engine-full-product.md). Docker Desktop remains a legacy bootstrap-only path.

---

## A. Stage 2 — Publish images (on Windows or Linux build host)

Run these on the connected **Windows/WSL or Linux** amd64 machine after Stage 1 code is on GitHub. Do not treat the Apple Silicon Mac as the default builder.

1. Pin check:

```bash
./scripts/check_installer_pins.sh
```

2. Login to GHCR (PAT with `write:packages`, or `gh auth token`):

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin
```

3. Frontend web assets (required before frontend image build):

```bash
cd ppl-meta-frontend && flutter pub get && flutter build web --release && cd ..
```

4. Build and push all twelve `linux/amd64` images:

```bash
RELEASE_TAG=2.25.82 ./scripts/build_windows_installer_images.sh
RELEASE_TAG=2.25.82 ./scripts/push_protected_service_images.sh
```

5. Verify manifests:

```bash
./scripts/verify_platform_release.sh 2.25.82
```

Or manually:

```bash
for s in node media gateway orchestrator discovery communications frontend \
         vision-protected vmeta-protected cameras presence models; do
  docker manifest inspect "ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-$s:2.25.82" >/dev/null \
    && echo "OK ppl-meta-$s:2.25.82" \
    || echo "MISSING ppl-meta-$s:2.25.82"
done
```

### Future — GitHub Actions

`.github/workflows/platform-release.yml` is a draft of the same steps. Do not use it for releases until Actions is enabled and [platform-release-cicd.md](../deployment/platform-release-cicd.md) says so.

---

## B. Windows machine install

### Preconditions

- Windows 10/11 **amd64** (not ARM)
- **≥16 GB** physical RAM
- WSL2 available; preferred: Docker Engine CE via `install-eyenet-wsl.bat` (distro `eyenet`)
- ≥12 GB free disk
- GHCR read token if packages are private (classic PAT with `read:packages`, or fine-grained package read)
- Authority entitlement ready: approved owner email + `lic_…` application key + installation identity

### Steps

1. Copy `deployment/windows-installer/` to the PC (or clone the repo).
2. Run `install-eyenet-wsl.bat` once (docker-ce + Tailscale client in WSL `eyenet`).
3. Double-click `install-platform.bat` (or `install-platform.ps1`).
4. Confirm host RAM check passes (≥16 GB).
5. Allow installer to set `.wslconfig` to `memory=12GB`, `processors=6`, `swap=2GB`.
6. When prompted for registry login, authenticate to `ghcr.io` **inside WSL** (`wsl -d eyenet -- docker login ghcr.io`).
7. Confirm generated `.env.windows` has `RELEASE_TAG=2.25.82` and `DISCOVERY_PORT=8006`.
8. Let images pull and stack start (includes cameras, presence, models). Schema apply/verify + discovery reregister run automatically.
9. Open http://localhost:3000
10. If bootstrap pending → `/bootstrap` with approved owner email + application key.
11. Confirm Network settings enrolls VPN against `https://vpn.eyenet-vision.com` (not Tailscale.com).
12. Add an RTSP camera (no USB). Optional: mint enrollment token for mobile/signage.

### Quick health checks (PowerShell)

```powershell
docker compose -f docker-compose.windows-installer.yml --env-file .env.windows ps
curl http://localhost:8080/api/v1/licensing/bootstrap/status
curl http://localhost:8006/api/v1/services
```

---

## C. Native Ubuntu 24 install (same GHCR tag)

Uses the **same** compose file and images as Windows. Script: `deployment/ubuntu/install-eyenet-ubuntu.sh`.

```bash
# on Ubuntu 24 host
git clone --depth 1 https://github.com/nickglezakos/ppl-meta-platform.git ~/ppl-meta-platform
cd ~/ppl-meta-platform
ADVERTISE_HOST=<lan-ip> RELEASE_TAG=2.25.82 bash deployment/ubuntu/install-eyenet-ubuntu.sh
# verify LAN IP: ip -4 addr show scope global
```

Health:

```bash
curl -s http://127.0.0.1:8006/api/v1/services
# UI http://<ADVERTISE_HOST>:3000/network
```

Full process: [platform-release-cicd.md §C](../deployment/platform-release-cicd.md).

---

## D. What this release does / does not do

**Does:** prove GHCR pin + WSL Docker Engine install path + Ubuntu 24 install path + full-product compose (cameras/presence/models) + bootstrap handoff + Headscale mesh enroll under the 16 GB policy.

**Does not yet require:** GitHub Actions for image publish, Authority `release_channel` automation, pilot soak, or live online wiki hosting. USB cameras remain out of scope.

---

## E. Blockers checklist

- [ ] `./scripts/check_installer_pins.sh` passes
- [ ] Local build + push of all twelve images for `2.25.82`
- [ ] All twelve manifests exist (`./scripts/verify_platform_release.sh 2.25.82`)
- [ ] Windows host meets 16 GB / 12 GB WSL; `install-eyenet-wsl.bat` completed
- [ ] Ubuntu 24 lab can pull the same tag via `install-eyenet-ubuntu.sh`
- [ ] Authority test entitlement exists for bootstrap

## F. Unblock publish

**Stage 1 (Mac → GitHub):** commit + push; pins if bumping.

**Stage 2 (Windows or Linux build host):**

```bash
./scripts/check_installer_pins.sh
echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin
cd ppl-meta-frontend && flutter pub get && flutter build web --release && cd ..
RELEASE_TAG=2.25.82 ./scripts/build_windows_installer_images.sh
RELEASE_TAG=2.25.82 ./scripts/push_protected_service_images.sh
./scripts/verify_platform_release.sh 2.25.82
```
