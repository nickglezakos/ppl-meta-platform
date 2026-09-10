# First Windows Release — 2.25.79

**Goal:** Publish platform images to GHCR and install them on a Windows amd64 machine with Docker Desktop.

**Release tag:** `2.25.79` (root `VERSION`)  
**Registry:** `ghcr.io/nickglezakos/ppl-meta-platform`  
**Host requirement:** ≥16 GB RAM, WSL memory 12 GB

---

## A. Publish images (Mac / CI)

### Option A1 — GitHub Actions (preferred)

1. Commit and push the CI/CD revamp (including `.github/workflows/platform-release.yml`) to `main`.
2. Re-authenticate if needed:

```bash
gh auth login -h github.com
```

3. Dispatch the workflow:

```bash
gh workflow run platform-release.yml -f platform_version=2.25.79
gh run watch
```

4. Confirm the run finished green.

### Option A2 — Local build and push

```bash
# Login to GHCR (PAT with write:packages, or gh auth token)
echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin

# Frontend web assets required before frontend image build
cd ppl-meta-frontend && flutter pub get && flutter build web --release && cd ..

# Build all nine linux/amd64 images
RELEASE_TAG=2.25.79 ./scripts/build_windows_installer_images.sh

# Push
RELEASE_TAG=2.25.79 ./scripts/push_protected_service_images.sh
```

### Verify manifests

```bash
./scripts/verify_platform_release.sh 2.25.79
```

Or manually:

```bash
for s in node media gateway orchestrator discovery communications frontend vision-protected vmeta-protected; do
  docker manifest inspect "ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-$s:2.25.79" >/dev/null \
    && echo "OK ppl-meta-$s:2.25.79" \
    || echo "MISSING ppl-meta-$s:2.25.79"
done
```

(vision/vmeta image names are `ppl-meta-vision-protected` and `ppl-meta-vmeta-protected`.)

---

## B. Windows machine install

### Preconditions

- Windows 10/11 **amd64** (not ARM)
- **≥16 GB** physical RAM
- Docker Desktop installed (WSL2 backend)
- ≥12 GB free disk
- GHCR read token (classic PAT with `read:packages`, or fine-grained package read)
- Authority entitlement ready: approved owner email + `lic_…` application key + installation identity

### Steps

1. Copy `install-platform.bat` to the PC (or clone `deployment/windows-installer/`).
2. Double-click `install-platform.bat`.
3. Confirm host RAM check passes (≥16 GB).
4. Allow installer to set `.wslconfig` to `memory=12GB`, `processors=6`, `swap=2GB`; restart Docker Desktop if prompted.
5. When prompted for registry login, authenticate to `ghcr.io`.
6. Confirm generated `.env.windows` has `RELEASE_TAG=2.25.79` (installer forces this from the script version pin).
7. Let images pull and stack start.
8. Open http://localhost:3000
9. If bootstrap pending → `/bootstrap` with approved owner email + application key.
10. Confirm land on `/home` and Authority status looks healthy.

### Quick health checks (PowerShell)

```powershell
docker compose -f docker-compose.windows-installer.yml --env-file .env.windows ps
curl http://localhost:8080/api/v1/licensing/bootstrap/status
```

---

## C. What this release does / does not do

**Does:** prove GHCR pin + Windows Docker Desktop install + bootstrap handoff under the 16 GB policy.

**Does not yet require:** Authority `release_channel` automation, pilot soak, or live online wiki hosting.

---

## D. Blockers checklist

- [ ] `gh auth login -h github.com` (current token in keyring is invalid)
- [ ] Commit + push installer + `platform-release.yml` (+ track `.env.windows.template`)
- [ ] Dispatch `platform-release.yml` with `platform_version=2.25.79` (or local build/push)
- [ ] All nine manifests exist for `2.25.79` (`./scripts/verify_platform_release.sh 2.25.79`)
- [ ] Windows host meets 16 GB / 12 GB WSL
- [ ] Authority test entitlement exists for bootstrap

## E. Unblock publish (run locally)

```bash
gh auth login -h github.com
# then ask the agent to commit/push release files, or:
git add deployment/windows-installer .github/workflows/platform-release.yml \
  deployment/windows-installer/.env.windows.template \
  docs/guides/first-windows-release-2.25.79.md scripts/verify_platform_release.sh
# commit and push, then:
gh workflow run platform-release.yml -f platform_version=2.25.79
gh run watch
./scripts/verify_platform_release.sh 2.25.79
```
