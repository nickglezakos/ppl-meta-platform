# First Windows Release — 2.25.81

**Goal:** Publish platform images to GHCR and install them on a Windows amd64 machine.

**Release tag:** `2.25.81` (root `VERSION`)  
**Registry:** `ghcr.io/nickglezakos/ppl-meta-platform`  
**Host requirement:** ≥16 GB RAM, WSL memory 12 GB  
**Preferred runtime:** Docker Engine CE in WSL distro `eyenet` (no Docker Desktop) — see [windows-wsl-docker-engine-full-product.md](../deployment/windows-wsl-docker-engine-full-product.md). Docker Desktop remains a legacy bootstrap-only path.

---

## A. Publish images (Mac / CI)

### Option A1 — GitHub Actions (preferred)

1. Confirm `platform-release.yml` is on `main` (already landed).
2. Re-authenticate if needed:

```bash
gh auth login -h github.com
```

3. Dispatch the workflow:

```bash
gh workflow run platform-release.yml -f platform_version=2.25.81
gh run watch
```

4. Confirm the run finished green.

### Option A2 — Local build and push

```bash
# Login to GHCR (PAT with write:packages, or gh auth token)
echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin

# Frontend web assets required before frontend image build
cd ppl-meta-frontend && flutter pub get && flutter build web --release && cd ..

# Build all twelve linux/amd64 images (includes cameras, presence, models)
RELEASE_TAG=2.25.81 ./scripts/build_windows_installer_images.sh

# Push
RELEASE_TAG=2.25.81 ./scripts/push_protected_service_images.sh
```

### Verify manifests

```bash
./scripts/verify_platform_release.sh 2.25.81
```

Or manually:

```bash
for s in node media gateway orchestrator discovery communications frontend \
         vision-protected vmeta-protected cameras presence models; do
  docker manifest inspect "ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-$s:2.25.81" >/dev/null \
    && echo "OK ppl-meta-$s:2.25.81" \
    || echo "MISSING ppl-meta-$s:2.25.81"
done
```

---

## B. Windows machine install

### Preconditions

- Windows 10/11 **amd64** (not ARM)
- **≥16 GB** physical RAM
- WSL2 available; preferred: Docker Engine CE via `install-eyenet-wsl.bat` (distro `eyenet`)
- ≥12 GB free disk
- GHCR read token (classic PAT with `read:packages`, or fine-grained package read)
- Authority entitlement ready: approved owner email + `lic_…` application key + installation identity

### Steps

1. Copy `deployment/windows-installer/` to the PC (or clone the repo).
2. Run `install-eyenet-wsl.bat` once (docker-ce + Tailscale client in WSL `eyenet`).
3. Double-click `install-platform.bat` (or `install-platform.ps1`).
4. Confirm host RAM check passes (≥16 GB).
5. Allow installer to set `.wslconfig` to `memory=12GB`, `processors=6`, `swap=2GB`.
6. When prompted for registry login, authenticate to `ghcr.io` **inside WSL** (`wsl -d eyenet -- docker login ghcr.io`).
7. Confirm generated `.env.windows` has `RELEASE_TAG=2.25.81` and `DISCOVERY_PORT=8006`.
8. Let images pull and stack start (includes cameras, presence, models).
9. Open http://localhost:3000
10. If bootstrap pending → `/bootstrap` with approved owner email + application key.
11. Confirm Network settings enrolls VPN against `https://vpn.eyenet-vision.com` (not Tailscale.com).
12. Add an RTSP camera (no USB). Optional: mint enrollment token for mobile/signage.

### Quick health checks (PowerShell)

```powershell
docker compose -f docker-compose.windows-installer.yml --env-file .env.windows ps
curl http://localhost:8080/api/v1/licensing/bootstrap/status
```

---

## C. What this release does / does not do

**Does:** prove GHCR pin + WSL Docker Engine install path + full-product compose (cameras/presence/models) + bootstrap handoff + Headscale mesh enroll under the 16 GB policy.

**Does not yet require:** Authority `release_channel` automation, pilot soak, or live online wiki hosting. USB cameras remain out of scope.

---

## D. Blockers checklist

- [ ] `gh auth login -h github.com` if the keyring token is invalid
- [ ] Dispatch `platform-release.yml` with `platform_version=2.25.81` (or local build/push)
- [ ] All twelve manifests exist for `2.25.81` (`./scripts/verify_platform_release.sh 2.25.81`)
- [ ] Windows host meets 16 GB / 12 GB WSL; `install-eyenet-wsl.bat` completed
- [ ] Authority test entitlement exists for bootstrap

## E. Unblock publish (run locally)

```bash
gh auth login -h github.com
gh workflow run platform-release.yml -f platform_version=2.25.81
gh run watch
./scripts/verify_platform_release.sh 2.25.81
```
