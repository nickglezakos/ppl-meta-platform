# Platform release CI/CD (single source of truth)

**Status:** Active  
**Last updated:** 2026-09-19  
**Current pin:** root [`VERSION`](../../VERSION) (today `2.25.81`)  
**Registry:** `ghcr.io/nickglezakos/ppl-meta-platform`  
**Architecture:** `linux/amd64` only for customer/lab installs  
**How we publish today:** **two stages** — (1) git push often, (2) build/push images when ready (no GitHub Actions for platform images yet)

This is the **canonical** EyeNet platform release contract.  
Runnable installers and compose live under [`deployment/`](../../deployment/).  
Background policy proposals live under `docs/proposals/CICD policy and implementation/` and must follow this document.

---

## Two-stage release (use this wording)

Tell the agent (or yourself) which stage you want. Do **not** assume both happen together.

| Stage | What it updates | Say this |
|---|---|---|
| **1 — Code** | GitHub repo only (source, installers, docs, pins) | *“Stage 1: push code to GitHub per platform-release-cicd.md”* or *“Commit and push to GitHub (no images)”* |
| **2 — Images** | GHCR container tags for the current `VERSION` | *“Stage 2: build and push images for VERSION X.Y.Z per platform-release-cicd.md”* or *“Publish GHCR images from latest main”* |

Optional extras (always name them explicitly):

- *“Also bump VERSION to X.Y.Z”* (can be Stage 1 only, or Stage 1 then Stage 2)
- *“Also upgrade the Windows lab”* / *“Also upgrade the Ubuntu lab”* (after Stage 2)

**Important:** Stage 1 does **not** change what labs pull. Installers keep serving whatever is already on GHCR until Stage 2 runs. Stage 2 does **not** replace Stage 1 — images are built from the git revision you checked out on the build host (usually latest `main` after Stage 1).

---

## Core rule

**One product on GHCR. Two installers in the same release process.**

| Layer | Count | Location |
|---|---|---|
| Service images | **One** set of tags per `VERSION` | GHCR via Stage 2 scripts |
| Compose + schema pack | **One** shared bundle | `deployment/windows-installer/` |
| Windows/WSL installer | Host bootstrap for Windows | `deployment/windows-installer/install-*.bat|ps1` |
| Ubuntu 24 installer | Host bootstrap for native Linux | `deployment/ubuntu/install-eyenet-ubuntu.sh` |

WSL Ubuntu and native Ubuntu 24 both pull the **same** `linux/amd64` images.  
They are not two products. Host/installer bugs are fixed in the matching script; product bugs are fixed in git (Stage 1) → rebuild/push images (Stage 2) → both installers `compose pull`.

Do **not**:

- Publish Ubuntu-only or Windows-only service image tags
- Treat a lab `docker cp` / compose override as a release
- Bump only one installer’s `RELEASE_TAG`
- Wait on GitHub Actions — platform image CI is **manual Stage 2** until Actions is enabled
- Run Stage 2 on the Apple Silicon Mac alone as the default (see Stage 2 build host)

---

## Directory contract

| Path | Owns |
|---|---|
| `deployment/` | Scripts, compose, schema pack, installers (executable truth) |
| `docs/deployment/` | CI/CD and operator documentation (this file = process truth) |
| `scripts/build_windows_installer_images.sh` | Stage 2: build all twelve `linux/amd64` images |
| `scripts/push_protected_service_images.sh` | Stage 2: push those images to GHCR |
| `scripts/verify_platform_release.sh` | Stage 2: post-publish GHCR gate |
| `scripts/check_installer_pins.sh` | Pin gate for both installers (Stage 1 and before Stage 2) |
| `.github/workflows/platform-release.yml` | **Future** automation of Stage 2 only — not used yet |

---

## Stage 1 — Push code to GitHub (frequent)

**Goal:** Land fixes, docs, and installer changes on GitHub so both labs (and future builds) can pull the repo. Do this often.

**Does:** `git` commit + push (and pin bumps / schema pack sync when part of the change).  
**Does not:** rebuild or push Docker images to GHCR.

Typical steps:

1. Land service / installer / doc fixes (no lasting lab hotfixes).  
2. If cutting a new product pin: set root `VERSION` and **all** installer pins to the same value.  
3. If schema changed: `bash deployment/mac-lima/sync-schema-pack.sh` and include `schema/pack.tar.gz` in the commit.  
4. `./scripts/check_installer_pins.sh`  
5. Commit and **push to GitHub**.

Agent wording examples:

- *“Stage 1: commit these fixes and push to GitHub (no image build).”*  
- *“Bump VERSION to 2.25.82, update installer pins, commit and push — Stage 1 only.”*

After Stage 1, Ubuntu/Windows can `git pull` installer scripts, but containers stay on the previous GHCR tag until Stage 2.

---

## Stage 2 — Build and push images (when ready)

**Goal:** Refresh GHCR so both installers `compose pull` the latest product for the pinned `VERSION`.

**Does:** Flutter web build (frontend image) + Docker build/push of all twelve services + verify.  
**Does not:** replace Stage 1; does not upgrade lab hosts unless you also ask for that.

### Build host (required note)

**Step 4 of the Stage 2 loop is connecting this Mac to a Windows or Linux amd64 machine and running the build there.**

- Customer/lab images are **`linux/amd64`**.  
- The development Mac (especially Apple Silicon) is **not** the default Stage 2 builder.  
- Connect over LAN or Tailscale (RDP / SSH) to a **Windows** PC (WSL2 / Docker Engine) or a **native Linux** box with Docker, ≥12 GB free disk, and GHCR write access.  
- On that host: `git pull` (or clone) the revision from Stage 1, then run the build/push scripts below.  
- The Mac remains the operator console (edit, Stage 1 push, verify manifests, RDP/SSH into the builder).

### Commands (on the Windows or Linux build host)

```bash
# from repo root — after git pull of the Stage 1 commit
./scripts/check_installer_pins.sh

echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin
# or: gh auth token | docker login ghcr.io -u nickglezakos --password-stdin

cd ppl-meta-frontend && flutter pub get && flutter build web --release && cd ..

RELEASE_TAG="$(tr -d '[:space:]' < VERSION)"
export RELEASE_TAG

./scripts/build_windows_installer_images.sh
./scripts/push_protected_service_images.sh
./scripts/verify_platform_release.sh "$RELEASE_TAG"
```

Services published (all required):

`node`, `media`, `gateway`, `orchestrator`, `discovery`, `communications`, `frontend`, `vision-protected`, `vmeta-protected`, `cameras`, `presence`, `models`

Agent wording examples:

- *“Stage 2: build and push GHCR images for 2.25.81 from latest main (use the Windows/Linux build host).”*  
- *“Publish images only — code already on GitHub.”*

Version-specific notes: [first-windows-release-2.25.81.md](../guides/first-windows-release-2.25.81.md).

### Future: GitHub Actions

`.github/workflows/platform-release.yml` is a draft of Stage 2. **Do not depend on it** until Actions is available and this doc is updated. Until then Stage 2 is manual on a Windows/Linux builder.

---

## Shared post-install steps (both installers)

After `compose up -d`, **both** paths must:

1. Wait for Postgres healthy  
2. Run `schema/apply.sh` then `schema/verify.sh` (fail install if verify fails)  
3. Run `reregister-discovery-services.sh` (canonical copy: `deployment/windows-installer/`)  
4. Print UI / gateway / discovery / bootstrap URLs  
5. Remind operators that `ADVERTISE_HOST` must be the LAN IP phones will use  

Host-only work stays installer-specific:

- **Windows:** WSL distro `eyenet`, host RAM ≥16 GB, `.wslconfig` 12 GB / 6 CPUs / 2 GB swap, `docker login` inside WSL  
- **Ubuntu:** Docker CE, docker group, optional daemon DNS, `ADVERTISE_HOST` from `ip -4 addr`

---

## Version identity

One release identity must agree everywhere:

1. Root `VERSION`
2. GHCR tags `…/<service>:${VERSION}` (updated only by **Stage 2**)
3. Windows pins: `install-platform.bat` `VERSION=`, `install-platform.ps1` `$script:ReleaseTag`, `.env.windows.template` `RELEASE_TAG=`
4. Ubuntu pin: `install-eyenet-ubuntu.sh` default `RELEASE_TAG=`
5. After promotion: wiki `software_ref.platform_version` and Authority release eligibility

Check pins any time:

```bash
./scripts/check_installer_pins.sh
```

---

## Lab upgrade after Stage 2 (optional third ask)

### Windows / WSL

Runtime: Docker Engine CE in WSL distro `eyenet` (see [windows-wsl-docker-engine-full-product.md](./windows-wsl-docker-engine-full-product.md)).

1. Ensure installer files match git (clone or copy `deployment/windows-installer/`).  
2. First time only: `install-eyenet-wsl.bat`.  
3. Install/upgrade: `install-platform.bat` (or `.ps1`) — pulls `${RELEASE_TAG}`, starts stack, schema apply/verify, discovery reregister.  
4. Open `http://localhost:3000` (bootstrap if needed).  
5. Health:

```powershell
curl http://localhost:8006/api/v1/services
curl http://localhost:8080/api/v1/licensing/bootstrap/status
```

Manual pull (existing install dir):

```powershell
wsl -d eyenet -- bash -lc "cd /mnt/c/path/to/install && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml pull && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d && bash schema/apply.sh && bash reregister-discovery-services.sh"
```

### Native Ubuntu 24

1. Clone/update monorepo on the Ubuntu host (`~/ppl-meta-platform` by default).  
2. Run:

```bash
bash deployment/ubuntu/install-eyenet-ubuntu.sh
# or: ADVERTISE_HOST=<lan-ip> RELEASE_TAG=<VERSION> bash deployment/ubuntu/install-eyenet-ubuntu.sh
```

3. Confirm `ADVERTISE_HOST` with `ip -4 addr show scope global`.  
4. Health:

```bash
curl -s http://127.0.0.1:8006/api/v1/services
# UI: http://<ADVERTISE_HOST>:3000/network
```

Manual upgrade of an existing `~/eyenet-platform`:

```bash
cd ~/eyenet-platform
# ensure RELEASE_TAG in .env matches published VERSION
docker compose --project-name pplmeta --env-file .env -f docker-compose.yml pull
docker compose --project-name pplmeta --env-file .env -f docker-compose.yml up -d
bash ~/ppl-meta-platform/deployment/windows-installer/schema/apply.sh
bash ~/ppl-meta-platform/deployment/windows-installer/schema/verify.sh
bash ~/ppl-meta-platform/deployment/windows-installer/reregister-discovery-services.sh
```

If only the **installer script** changed (Stage 1 only), `git pull` and re-run the installer — image pull alone does not update scripts.

---

## Full version cut (Stage 1 + Stage 2 + labs)

When you want a new pin end-to-end (e.g. `2.25.82`):

1. **Stage 1:** bump `VERSION` + all pins, schema pack if needed, pin check, commit, push.  
2. **Stage 2:** on the **Windows or Linux** build host, build/push/verify that tag.  
3. Upgrade Windows/WSL lab and/or Ubuntu 24 lab (say so explicitly).  
4. Only then treat the tag as the current product; update wiki `software_ref` after promotion evidence.

Wording:

- *“Full release to 2.25.82 per platform-release-cicd.md (Stage 1 + Stage 2; then upgrade both labs).”*

---

## Bug triage: images vs installers

| Kind of bug | Fix in | Stage 1? | Stage 2? | Roll out |
|---|---|---|---|---|
| Service code, Dockerfile, compose memory, schema pack | Monorepo service / pack | **Yes** | **Yes** (when ready) | Both installers `compose pull` |
| WSL RAM gate, Windows download list | `deployment/windows-installer/` | **Yes** | No | Re-run Windows installer |
| Ubuntu Docker CE, DNS, `ADVERTISE_HOST` | `deployment/ubuntu/` | **Yes** | No | `git pull` + re-run Ubuntu installer |
| Shared post-up (reregister, schema verify) | Prefer `deployment/windows-installer/` | **Yes** | No | Both installers |

A **product** release is complete only when Stage 2 has updated GHCR **and** labs have pulled that tag. A **code** release is complete after Stage 1 alone.

---

## CI/CD today vs later

**Today**

| Stage | Where | Frequency |
|---|---|---|
| 1 — git push | Mac (or any clone) → GitHub | Often |
| 2 — build/push images | Connected **Windows or Linux** amd64 host → GHCR | When you want labs/customers on new containers |
| Lab upgrade | Each lab host | After Stage 2, when asked |

**Later (optional)**

- Automate Stage 2 with GitHub Actions (`platform-release.yml`)  
- Keep real OS smoke on lab hardware  

---

## Related

- Index: [README.md](./README.md)  
- Ubuntu lab bug list: [`deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md`](../../deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md)  
- Windows installer scripts README: [`deployment/windows-installer/README.md`](../../deployment/windows-installer/README.md)  
- Lifecycle policy (proposals): [`docs/proposals/CICD policy and implementation/`](../proposals/CICD%20policy%20and%20implementation/)
