# EyeNet platform CI/CD — operator guide

**Audience:** You (operator / product owner) and agents helping you ship  
**Last updated:** 2026-09-20  
**Current platform pin:** root [`VERSION`](../../VERSION) (today `2.25.82`)  
**Canonical contract (short, strict):** [`platform-release-cicd.md`](./platform-release-cicd.md)  
**Lab inventory:** [`lab-machines.md`](./lab-machines.md)  
**Release notes:** [`CHANGELOG.md`](../../CHANGELOG.md)

This guide teaches the **same** process as the canonical doc, with plain-language intros first and full commands afterward. When wording conflicts, **follow `platform-release-cicd.md`**.

---

## For dummies (start here)

### The one-sentence version

You change **code on GitHub** often (Stage 1). When you want labs to **run** container changes, you **build Docker images** on a Windows/Linux lab PC and upload them to GHCR (Stage 2). Tray binaries are built **manually** on Windows + Ubuntu labs and uploaded with `gh release` (GitHub Actions for tray/images are **not** used today). Then you **install** on each lab (Stage 3): images **and** tray.

### Kitchen analogy

| Real world | EyeNet |
|---|---|
| Recipe written in a notebook | Source code in the GitHub repo |
| Publishing the recipe online | **Stage 1** — commit + push (+ changelog) |
| Hand-building the fridge remote | **Tray publish** — manual lab build + `gh release` upload |
| Cooking the meal and putting it in the freezer aisle | **Stage 2** — build images + push to **GHCR** on a lab PC |
| Customer unpacks the labeled box at home | **Stage 3** — **install** (images + tray) |
| Label on the box: “EyeNet 2.25.82” | Root **`VERSION`** / installer **`RELEASE_TAG`** |
| Exact batch ID printed on the seal | **Digest** in the **release manifest** |

**Critical:** Publishing the recipe does **not** put food in the freezer. Stage 1 alone never changes what a running lab pulls from GHCR. Stage 2 fills the freezer. Stage 3 unpacks it (and hangs the tray remote on the wall).

### What we are *not* doing (yet)

- We are **not** using GitHub Actions to build platform **images** or the **host tray** day-to-day (manual lab builds only). Related workflow YAML is draft/future.
- We are **not** shipping two different products for Windows vs Ubuntu — **one** set of `linux/amd64` images; two **installers**; tray is two **host binaries** for the same pin.
- We are **not** (yet) making installers pull by digest — they still pull by tag `:2.25.82`. Digests are the **coherence / audit** layer.

### The three steps (memorize this)

```text
  Mac (you)                    GitHub / Releases           Lab PC (amd64)              GHCR
     │                              │                            │                      │
     │  1. Code: commit + push      │                            │                      │
     │  (+ CHANGELOG, pins) ───────►│                            │                      │
     │                              │                            │                      │
     │  Tray: manual build ─────────┼── Win + Ubuntu labs ───────►│  gh release upload    │
     │                              │                            │                      │
     │  2. Images: SSH / RDP ───────┼───────────────────────────►│  build + push ───────►│
     │                              │                            │                      │
     │  Mode D finalize ────────────┼── release-manifest.yml     │                      │
     │                              │                            │                      │
     │  3. Install / upgrade ───────┼───────────────────────────►│  images + tray       │
```

| Step | Plain English | Touches GHCR? | Touches running labs? |
|---|---|---|---|
| **1 — Code** | Save work to GitHub | No | No |
| **Tray publish** | Manual Win/Ubuntu build → GitHub Release | No | After Stage 3 |
| **2 — Images** | Cook and upload containers on a lab PC | Yes | Only after Stage 3 |
| **3 — Install** | Run installer on a named lab | Pulls | Yes |

### What to say out loud (to an agent or yourself)

- *“Stage 1 only”* → git + changelog, **no** images  
- *“Publish tray for 2.25.82”* → manual lab builds + `gh release`  
- *“Stage 2 on lab-work-dual-64g”* → build/push images there  
- *“Upgrade lab-home-win-nickg”* → Stage 3 install (images + tray)  

Never assume “release” means all of the above unless you said so.

---

## Step 0 — Mental model: one product, two installers

### Plain English

Think of EyeNet as **one product in a warehouse** (GHCR). Windows and Ubuntu are two **delivery trucks** that pick up the **same** boxes and unpack them on different driveways (WSL vs native Linux). Fixing a pothole on the driveway is an installer fix (Stage 1 only). Fixing the product inside the box needs Stage 2.

### Technical details

| Layer | Count | Where |
|---|---|---|
| Service images | **One** set of tags per `VERSION` | `ghcr.io/nickglezakos/ppl-meta-platform/…` |
| Compose + schema pack | **One** shared bundle | `deployment/windows-installer/` |
| Windows/WSL installer | Host bootstrap | `deployment/windows-installer/install-*.bat\|ps1` |
| Ubuntu 24 installer | Host bootstrap | `deployment/ubuntu/install-eyenet-ubuntu.sh` |
| Host tray | **One** pin, two OS binaries | GitHub Releases `v${VERSION}` — **manual** upload today (`deployment/tray/`) |

Architecture for customer/lab images: **`linux/amd64` only**.

Do **not**:

- Publish Ubuntu-only or Windows-only service image tags  
- Treat `docker cp` / a compose override on one lab as a “release”  
- Bump only one installer’s `RELEASE_TAG`  
- Skip `CHANGELOG.md` on meaningful Stage 1 work  
- Use the Apple Silicon Mac as the default Stage 2 builder  

Pin check (any time):

```bash
./scripts/check_installer_pins.sh
```

---

## Step 1 — Stage 1: push code to GitHub (do this often)

### Plain English

This is “save your homework to the cloud.” Labs can pull **installer scripts** from git, but they keep running **old containers** until Stage 2.

### Technical details

**Does:** commit + push (source, installers, docs, pins, schema pack when needed) **and** update root [`CHANGELOG.md`](../../CHANGELOG.md).  
**Does not:** build or push Docker images.

#### CHANGELOG (mandatory on meaningful Stage 1)

1. Prefer `## [Unreleased]` while iterating without a pin bump.  
2. When cutting a pin, use `## [X.Y.Z] — YYYY-MM-DD` matching root `VERSION`.  
3. Sections: **Added** / **Changed** / **Fixed** / **Notes** (omit empty).  
4. No secrets. Do not use `docs/notes.txt` for release notes.  

#### Typical Stage 1 sequence

```bash
# from repo root on the Mac
# 1) land fixes
# 2) if new pin: set VERSION + all installer RELEASE_TAG / VERSION pins to the same value
# 3) if schema changed:
bash deployment/mac-lima/sync-schema-pack.sh   # include schema/pack.tar.gz in commit

# 4) edit CHANGELOG.md
./scripts/check_installer_pins.sh

git add -A   # review; exclude secrets / notes.txt if private
git commit -m "…"
git push origin main
```

Agent wording: *“Stage 1: push code to GitHub per platform-release-cicd.md”* (changelog implied).

---

## Tray publish — manual (not Actions)

Tray publish is **not** a separate stage and **not** driven by GitHub Actions today. After Stage 1 push, build on Windows + Ubuntu labs and upload with `gh release`. See [`platform-release-cicd.md`](./platform-release-cicd.md) and [`tray-stage-1.5-publish.md`](./tray-stage-1.5-publish.md).

Agent wording: *“Publish tray for 2.25.82”*.

---

## Step 2 — Stage 2: build and push images (when ready)

### Plain English

This is “cook the meal and put it in the freezer aisle.” You SSH/RDP into a **named lab PC**, build `linux/amd64` images from the git revision you checked out, and push them to **GHCR** under tag `:VERSION` (e.g. `:2.25.82`).

Long builds break idle SSH — use **tmux** on the builder, or build **one service per SSH** (`stage2_one.sh`).

### Technical details

#### Build host preference

| Preference | Lab ID | Notes |
|---|---|---|
| Preferred | `lab-work-dual-64g` | 64 GB dual-boot; Windows/WSL or Ubuntu |
| Optional | `lab-home-win-nickg` | Home Windows if disk/RAM allow |
| Not for Stage 2 | `lab-work-u24-mini-8g` | 8 GB soak only |

Access: LAN or Tailscale, then SSH / Windows App (RDP). Details: [`lab-machines.md`](./lab-machines.md).

#### Tags

| Tag | Example | Who uses it |
|---|---|---|
| Product pin | `2.25.82` | Installers (`RELEASE_TAG`) |
| Trace sub-tag | `2.25.82-92ea2d5` | Optional audit (`EXTRA_SHA_TAG=1`) |

Installers **must** keep pulling `:VERSION`. Sub-tags are additive.

#### Service keys (twelve)

`node` `media` `gateway` `orchestrator` `discovery` `communications` `frontend` `vision` `vmeta` `cameras` `presence` `models`  

GHCR names use `ppl-meta-vision-protected` / `ppl-meta-vmeta-protected` for vision/vmeta.

---

### Step 2a — Mode A: full Stage 2 (all twelve)

#### Plain English

Rebuild **everything**. Use after a big cut, shared/schema changes, or when the change detector prints `ALL`.

#### Technical details

```bash
# on build host — prefer inside tmux
cd /path/to/ppl-meta-platform
git fetch origin && git checkout main && git pull --ff-only

./scripts/check_installer_pins.sh
echo "$GHCR_TOKEN" | docker login ghcr.io -u nickglezakos --password-stdin

cd ppl-meta-frontend && flutter pub get && flutter build web --release && cd ..

RELEASE_TAG="$(tr -d '[:space:]' < VERSION)"
export RELEASE_TAG

for s in node media gateway orchestrator discovery communications frontend vision vmeta cameras presence models; do
  EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh "$s" || { echo "REPORT FAIL service=$s"; break; }
done

./scripts/stage2_finalize_manifest.sh
# Then Stage 1: commit deployment/windows-installer/release-manifest.yml (+ CHANGELOG Notes)
```

Classic all-at-once (tmux only):

```bash
./scripts/build_windows_installer_images.sh
./scripts/push_protected_service_images.sh
./scripts/stage2_finalize_manifest.sh
```

---

### Step 2b — Mode B: one-by-one (SSH-safe default)

#### Plain English

Build **one** service, get a clear `REPORT OK`, then do the next. A dropped VPN only costs the current service.

#### Technical details

From the Mac (Windows/WSL builder example):

```bash
ssh lab-home-win-nickg "wsl -d eyenet -- bash -lc 'cd /mnt/c/path/to/repo && RELEASE_TAG=2.25.82 EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh cameras'"
```

Native Linux builder:

```bash
ssh lab-work-dual-64g "cd ~/ppl-meta-platform && git pull && RELEASE_TAG=2.25.82 EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh cameras"
```

Expect:

```text
REPORT OK service=cameras tag=2.25.82 sha_tag=2.25.82-<shortsha> ref=ghcr.io/.../ppl-meta-cameras:2.25.82
REPORT DONE services=cameras …
```

When the intended set for this pin is complete → Mode D finalize (`stage2_finalize_manifest.sh`).

---

### Step 2c — Mode C: selective Stage 2 (only what changed)

#### Plain English

If Stage 1 only touched cameras + frontend, rebuild **those** — not vision. The shared tag `:2.25.82` still moves for the services you push; unchanged services keep their previous digests under that tag until you rebuild or retag them.

#### Technical details

```bash
git fetch origin
./scripts/stage2_changed_services.sh HEAD~1..HEAD
# or: ./scripts/stage2_changed_services.sh <before_sha> <after_sha>
```

| Script output | Meaning |
|---|---|
| `NONE` | Docs/installer-only — skip Stage 2 |
| `ALL` | Shared/schema touched — Mode A |
| `cameras frontend` | Mode B for those keys only |

```bash
SERVICES=$(./scripts/stage2_changed_services.sh HEAD~1..HEAD)
RELEASE_TAG="$(tr -d '[:space:]' < VERSION)"
for s in $SERVICES; do
  EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh "$s"
done
./scripts/stage2_finalize_manifest.sh
```

---

### Step 2d — Mode D: release manifest + retag-forward

#### Plain English

**Problem:** Tag `:2.25.82` can mean “whatever was last pushed for each service,” so “is this install coherent?” is fuzzy.

**Fix:** A small file — the **release manifest** — lists the **digest** (fingerprint) of each of the twelve images for that platform pin. That file is the answer to “what exactly is 2.25.82?”

**Retag-forward:** When you cut `2.25.83` but only cameras changed, rebuild cameras, then **copy** the other eleven digests from `2.25.82` → `2.25.83` without rebuilding (same content, new label).

#### Technical details

**Artifact:** `deployment/windows-installer/release-manifest.yml`

```yaml
schema_version: 1
platform_version: "2.25.82"
git_sha: "92ea2d5"
created_at: "2026-09-19T…"
registry: "ghcr.io/nickglezakos/ppl-meta-platform"
images:
  ppl-meta-node:
    tag: "2.25.82"
    digest: "sha256:…"
  # …all twelve
```

| Layer | Role |
|---|---|
| `VERSION` / `RELEASE_TAG` | Customer-facing platform pin |
| `:VERSION` on GHCR | What installers pull **today** |
| `:VERSION-<sha>` | Optional human audit |
| `release-manifest.yml` | Digest source of truth for that pin |

**Finalize after Stage 2 completes a pin** (Mac or builder with GHCR access):

```bash
./scripts/stage2_finalize_manifest.sh
# = verify_platform_release + write_release_manifest + verify_release_manifest
```

Then **Stage 1 commit** `release-manifest.yml` (+ CHANGELOG Notes). Do not hand-edit digests.

**Pin bump with retag-forward** (example: only cameras changed):

```bash
RELEASE_TAG=2.25.83 EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh cameras
FROM_TAG=2.25.82 TO_TAG=2.25.83 EXCLUDE="cameras" ./scripts/stage2_retag_forward.sh
RELEASE_TAG=2.25.83 ./scripts/stage2_finalize_manifest.sh
# Stage 1: commit release-manifest.yml + Notes (cameras rebuilt; rest retagged)
```

Verify any time:

```bash
./scripts/verify_platform_release.sh          # twelve tags exist
./scripts/verify_release_manifest.sh          # digests match GHCR + VERSION
```

Agent wording:

- *“Stage 2 Mode D: finalize release manifest for 2.25.82.”*  
- *“Stage 2 pin bump 2.25.82→2.25.83: rebuild cameras, retag-forward the rest, finalize manifest.”*

---

## Step 3 — Lab upgrade (optional third ask)

### Plain English

Images sitting in GHCR do nothing until a machine **pulls** them. Say explicitly which lab to upgrade.

### Technical details

#### Windows / WSL (`lab-home-win-nickg`, or Windows boot on dual)

1. Installer files match git.  
2. First time: `install-eyenet-wsl.bat`.  
3. Install/upgrade: `install-platform.bat` (or `.ps1`) — pulls `${RELEASE_TAG}`, schema apply/verify, discovery reregister.  
4. UI: `http://localhost:3000`  

Manual pull (existing install dir):

```powershell
wsl -d eyenet -- bash -lc "cd /mnt/c/path/to/install && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml pull && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d && bash schema/apply.sh && bash reregister-discovery-services.sh"
```

#### Native Ubuntu 24

```bash
bash deployment/ubuntu/install-eyenet-ubuntu.sh
# or: ADVERTISE_HOST=<lan-ip> RELEASE_TAG=<VERSION> bash deployment/ubuntu/install-eyenet-ubuntu.sh
```

Health:

```bash
curl -s http://127.0.0.1:8006/api/v1/services
# UI: http://<ADVERTISE_HOST>:3000/network
```

If only the **installer script** changed (Stage 1 only), `git pull` and re-run the installer — image pull alone does not update scripts.

---

## Step 4 — Full version cut (checklist)

### Plain English

When you want a **new** number on the box end-to-end (e.g. `2.25.82` → `2.25.83`).

### Technical details

1. **Stage 1:** bump `VERSION` + all installer pins, schema pack if needed, CHANGELOG under `[X.Y.Z]`, pin check, commit, push.  
2. **Stage 2:** on preferred builder — rebuild changed services; Mode D **retag-forward** unchanged from previous pin; `stage2_finalize_manifest.sh`.  
3. **Stage 1 (manifest):** commit `release-manifest.yml` + CHANGELOG Notes (rebuilt vs retagged).  
4. Upgrade named labs if asked.  
5. Promote wiki `software_ref.platform_version` / Authority eligibility when evidence exists.

Wording: *“Full release to X.Y.Z per platform-release-cicd.md (Stage 1 + Stage 2 + finalize manifest; then upgrade …).”*

---

## Bug triage (images vs installers)

| Kind of bug | Fix in | Stage 1? | Stage 2? | Roll out |
|---|---|---|---|---|
| Service code, Dockerfile, compose memory, schema pack | Monorepo / pack | Yes | Yes (when ready) | Both installers `compose pull` |
| WSL RAM gate, Windows download list | `deployment/windows-installer/` | Yes | No | Re-run Windows installer |
| Ubuntu Docker CE, DNS, `ADVERTISE_HOST` | `deployment/ubuntu/` | Yes | No | `git pull` + re-run Ubuntu installer |
| Shared post-up (reregister, schema verify) | Prefer `deployment/windows-installer/` | Yes | No | Both installers |

A **product** release is complete when Stage 2 (+ coherent manifest) has updated GHCR **and** labs have pulled. A **code** release is complete after Stage 1 alone.

---

## Script cheat sheet

| Script | When |
|---|---|
| `scripts/check_installer_pins.sh` | Before Stage 1 push / before Stage 2 |
| `scripts/stage2_changed_services.sh` | Decide Mode A vs C |
| `scripts/stage2_one.sh` | Build+push one (or more) services |
| `scripts/stage2_retag_forward.sh` | Pin bump: copy digests without rebuild |
| `scripts/verify_platform_release.sh` | Twelve tags exist on GHCR |
| `scripts/write_release_manifest.sh` | Write digests from GHCR |
| `scripts/verify_release_manifest.sh` | Digests match GHCR + `VERSION` |
| `scripts/stage2_finalize_manifest.sh` | Tag verify → write → digest verify |
| `scripts/build_windows_installer_images.sh` | Classic bulk build |
| `scripts/push_protected_service_images.sh` | Classic bulk push |

---

## Common mistakes

1. **Expecting Stage 1 to change running labs** — it won’t until Stage 2 + pull.  
2. **Building on the Mac by default** — wrong arch / wrong host; use a named amd64 lab.  
3. **One multi-hour SSH without tmux** — disconnect loses the session; use Mode B or tmux.  
4. **Forgetting CHANGELOG on Stage 1** — required for meaningful work.  
5. **Forgetting finalize + commit of `release-manifest.yml`** — tags exist but coherence artifact missing.  
6. **Hand-editing digests** — always regenerate with `write_release_manifest.sh`.  
7. **Pointing customers at `:VERSION-<sha>`** — audit only; installers stay on `:VERSION`.  
8. **Putting secrets in CHANGELOG or committing `docs/notes.txt`** — don’t.

---

## Related documents

- Canonical process: [`platform-release-cicd.md`](./platform-release-cicd.md)  
- Labs: [`lab-machines.md`](./lab-machines.md)  
- Index: [`README.md`](./README.md)  
- Proposals (background): `docs/proposals/CICD policy and implementation/`

---

## Appendix A — Terminology (for your education)

Terms are grouped loosely. Skim once; use as a dictionary later.

### Versioning and identity

| Term | Meaning |
|---|---|
| **VERSION** | Single file at repo root (`2.25.82`). The **platform pin** — customer-facing product identity. |
| **Pin / platform pin** | “We are shipping EyeNet as version X.Y.Z.” Installers and docs should agree on this number. |
| **RELEASE_TAG** | Installer env var that must equal `VERSION`. What compose uses when pulling images. |
| **Tag (image tag)** | Human label on a container image, e.g. `:2.25.82` or `:2.25.82-92ea2d5`. Tags can be **moved** to a new digest when you push again. |
| **Digest** | Immutable fingerprint of an image content, e.g. `sha256:abc…`. Content-addressed; does not move when you retag. |
| **Sub-tag / trace tag** | Optional `:VERSION-<gitsha>` for humans (“which commit built this?”). Not what customers pin. |
| **Release manifest** | YAML listing each service’s digest for a `platform_version`. Coherence layer for selective Stage 2. |
| **Retag-forward** | Point a **new** tag at the **same** digest as an old tag (no rebuild). Used on pin bumps for unchanged services. |
| **SemVer (X.Y.Z)** | Version numbering style. Here the whole **platform** shares one X.Y.Z; we do not give each microservice its own customer-facing version (yet). |

### Git and Stage 1

| Term | Meaning |
|---|---|
| **Git** | Version control for source files. |
| **Commit** | A saved snapshot of changes with a message. |
| **Push** | Upload commits to GitHub (`origin`). |
| **main** | Primary branch you ship from. |
| **SHA / git SHA** | Unique ID of a commit (`92ea2d5` = short form). |
| **Stage 1** | Our name for “commit + push code (+ CHANGELOG); no image publish.” |
| **CHANGELOG** | Human release notes (`CHANGELOG.md`). Required on meaningful Stage 1. |
| **Unreleased** | CHANGELOG section for work not yet tied to a cut pin. |
| **Schema pack** | Bundled DB/schema assets installers apply (`schema/pack.tar.gz`). |
| **Stage 1.5 / tray Release** | *(Deprecated name.)* Manual tray publish after Stage 1 — not Actions. |
| **Host binary / tray** | Desktop Start/Stop/Restart app (`deployment/tray/`); Windows + Ubuntu builds. |
| **Git tag `vVERSION`** | Optional label for GitHub Release tray assets (does **not** trigger platform Actions today). |

### Containers and Stage 2

| Term | Meaning |
|---|---|
| **Container image** | Packaged runnable service (filesystem + metadata). Built from a Dockerfile. |
| **Docker** | Tool that builds/runs containers. |
| **Dockerfile** | Recipe to build one image. |
| **Compose / docker compose** | File that defines the multi-service stack and how to start it. |
| **Build** | Produce a local image from source + Dockerfile. |
| **Push** | Upload an image (tag) to a registry. |
| **Pull** | Download an image from a registry to a host. |
| **Registry** | Server that stores images. Ours: **GHCR**. |
| **GHCR** | GitHub Container Registry (`ghcr.io/…`). |
| **linux/amd64** | CPU/OS architecture of customer/lab images. Lab builders must be amd64 (or cross-build carefully); Apple Silicon Mac is not the default builder. |
| **Stage 2** | Our name for “build + push images to GHCR for `VERSION`.” |
| **Mode A / B / C / D** | Full twelve / one-by-one / selective / manifest+retag (see above). |
| **Selective Stage 2** | Rebuild only services whose paths changed in git. |
| **REPORT OK** | Success line from `stage2_one.sh` for agent/operator loops. |
| **tmux / screen** | Terminal multiplexers — keep Stage 2 running if SSH drops. |
| **Flutter web build** | Frontend compile step needed before building the `frontend` image. |

### Hosts, labs, access

| Term | Meaning |
|---|---|
| **Lab ID** | Stable name for a machine (`lab-home-win-nickg`, …). Use in chat and notes. |
| **Operator console** | Your Mac — Stage 1, docs, remote into labs; not default Stage 2 builder. |
| **Builder** | The amd64 machine that runs Docker build/push for Stage 2. |
| **WSL** | Windows Subsystem for Linux — EyeNet Windows path runs Docker Engine inside distro `eyenet`. |
| **RDP / Windows App** | Remote desktop into Windows labs. |
| **SSH** | Secure shell into Linux (or WSL via `wsl …`). |
| **Tailscale / mesh / Headscale** | VPN-style overlay so labs are reachable off-LAN (`100.x` addresses). |
| **LAN** | Local office/home network. |
| **ADVERTISE_HOST** | IP/hostname phones and browsers should use to reach the stack on Ubuntu installs. |

### Installers and runtime

| Term | Meaning |
|---|---|
| **Installer** | Script that prepares the host and starts the stack (Windows vs Ubuntu). |
| **Bootstrap** | First-time owner activation in the UI after install. |
| **Schema apply / verify** | Load DB schema then check invariants; install fails if verify fails. |
| **Discovery reregister** | Re-register services with the discovery component after up. |
| **Authority** | Cloud/licensing control plane (eligibility, activation). Separate from platform GHCR publish. |
| **Release channel** (sandbox / pilot / stable) | Policy idea: who may receive which pin. Documented; entitlement field wiring is follow-up engineering — not required to use Stage 1/2 today. |

### CI/CD vocabulary (general)

| Term | Meaning |
|---|---|
| **CI (Continuous Integration)** | Automatically build/test when code changes. |
| **CD (Continuous Delivery/Deployment)** | Automatically (or repeatedly) ship build artifacts toward users. |
| **Pipeline / workflow** | Automated sequence (e.g. GitHub Actions YAML). Platform image + tray workflows are **draft / not used** day-to-day. |
| **Artifact** | Output of a build (image, manifest file, tray `.exe` / `.tar.gz`, installer bundle). |
| **Source of truth** | Document or file everyone must follow (`platform-release-cicd.md` for process; `VERSION` for the pin; manifest for digests). |
| **Coherence** | “All twelve services in this pin belong together” — what the release manifest proves. |
| **Promotion** | Declaring a pin ready for a wider audience (e.g. pilot → stable) after evidence. |
| **Soak** | Run a release on pilot installs for a required time before wider promotion. |

### Image name examples (concrete)

| Service key | GHCR image name (under the platform registry) |
|---|---|
| `node` | `ppl-meta-node` |
| `cameras` | `ppl-meta-cameras` |
| `frontend` | `ppl-meta-frontend` |
| `vision` | `ppl-meta-vision-protected` |
| `vmeta` | `ppl-meta-vmeta-protected` |
| … | `ppl-meta-<key>` for the other keys |

Full ref example:

`ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-cameras:2.25.82`

Digest-pinned form (future installer use):

`ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-cameras@sha256:…`

---

## Appendix B — One-page cheat card

```text
Stage 1  →  git + CHANGELOG (+ pins/schema) → GitHub
Tray     →  manual Win+Ubuntu build + gh release → GitHub Release assets
Stage 2  →  build/push on lab-work-dual-64g (amd64) → GHCR :VERSION
Mode D   →  stage2_finalize_manifest.sh → release-manifest.yml → Stage 1 commit
Stage 3  →  installer on named lab → running stack (images + tray)
```

Say the stage. Name the lab. Don’t skip the changelog. Don’t skip the manifest after a complete pin.
