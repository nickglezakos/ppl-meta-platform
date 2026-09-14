# EyeNet on Windows via Tailscale — Image Publish + Install Walkthrough

**Date:** 2026-09-11  
**Audience:** Developer on Mac reaching Windows lab PC over Tailscale  
**Goal:** Get GHCR platform images available, then install EyeNet on the Windows machine  
**Related:** `docs/guides/first-windows-release-2.25.80.md`, `deployment/windows-installer/`

---

## Roles (do not mix these up)

| Role | Machine | Job |
|------|---------|-----|
| **Operator Mac** | your MacBook (Tailscale mesh) | RDP to Windows; later verify GHCR manifests |
| **Windows lab PC** | `kvalvis-pc` → Tailscale IP **`100.64.0.23`** | **This session:** native `linux/amd64` image build + GHCR push, then install by pull |
| **Image builder (product)** | GitHub Actions (`platform-release.yml`) | Preferred later; currently **billing-locked** (runs die in ~4s with no runner) |

Customer Windows boxes still **pull** pinned images. Building on this lab PC is how we seed GHCR until Actions is unlocked.

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

**Current lab path (2026-09-11):** GitHub Actions is billing-locked, so **build on `kvalvis-pc`** (Path B below). Path A stays the product path once billing is unlocked.

### Path A — GitHub Actions (from Mac) — blocked today

Registry: `ghcr.io/nickglezakos/ppl-meta-platform`  
Tag: match root `VERSION` (**`2.25.80`**) and installer `RELEASE_TAG` / `VERSION` pins.

```bash
cd /path/to/ppl-meta-code
gh auth status
# if needed: gh auth login -h github.com

# Confirm platform-release.yml is on the branch you dispatch against (usually main)
gh workflow run platform-release.yml -f platform_version=$(tr -d '[:space:]' < VERSION)
gh run watch

./scripts/verify_platform_release.sh "$(tr -d '[:space:]' < VERSION)"
```

Nine → twelve images that must exist:

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

### Path B — Lab: build on Windows (native amd64) — **do this now**

Use only if Actions/auth is broken and you need images today.

On Windows (WSL2 Ubuntu recommended; scripts are bash):

1. Install Docker Desktop (WSL2 backend), Git, and (for frontend image) Flutter for `flutter build web --release`.
2. Clone `ppl-meta-code` to a fast disk with **≥12 GB free**.
3. Login to GHCR (PAT with `write:packages`):

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin
```

4. Build frontend web assets, then images + push:

```bash
cd /path/to/ppl-meta-code
TAG=$(tr -d '[:space:]' < VERSION)   # 2.25.80

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
| Actions run fails in ~4s, empty steps | GitHub account billing lock — unlock at https://github.com/settings/billing then re-dispatch `platform-release.yml` |
| `manifest unknown` | Publish Path A or B; re-run `verify_platform_release.sh` |
| Installer pulls wrong tag | Sync bat/`VERSION`/`.env.windows` (pin is **2.25.80**) |
| Bootstrap fails | Authority approved email + valid `lic_…` key |
```
