# Platform release CI/CD (single source of truth)

**Status:** Active  
**Last updated:** 2026-11-18  
**Current pin:** root [`VERSION`](../../VERSION) (today `2.25.107`)  
**Registry:** `ghcr.io/nickglezakos/ppl-meta-platform`  
**Architecture:** `linux/amd64` only for customer/lab installs  

### Open for next full Stage 1 → 2 → 3

**Pin `2.25.107` Stage 1 cut (+ follow-up) / Stage 2 in progress on `lab-work-win-eynetdell`.** Routes/Motion timestamp+velocity repair, analytics merge cache, Image Quality IVA fallback, schema gates for `face_detections.timestamp` + IVA quality/movement_pattern; **follow-up:** cross-video Motion/Routes series + camera filter (Instant flush route_points, named/scoped camera chips, VMeta camera_name).

| Step | Must include |
|---|---|
| **Stage 1** | **Whole open pin** (not one chat fix): Vision/Orchestrator/VMeta/Gateway/Cameras/Frontend route+quality+analytics; Instant cameras detection-flags SQL path if still dirty; cross-video Motion/Routes series + camera filter; pack + verify gates; CHANGELOG + pin `2.25.107` — base `66157f8b`, follow-up `70f1030c`; any remaining Pending/unstaged pin paths must land before Stage 2 |
| **Stage 2** | Mode D on **`lab-work-win-eynetdell`** (WSL `eyenet`): rebuild **frontend**, **vmeta-protected**, **gateway**, **vision-protected**, **orchestrator**, **cameras**; retag-forward others from `2.25.106`; finalize release-manifest |
| **Stage 3** | Compose pull rebuilt services; **migrations:** `schema/apply.sh` then `schema/verify.sh` for pack SQL `add_face_detections_timestamp.sql` + `052_ensure_iva_quality_and_movement_pattern.sql` (gates: `face_detections.timestamp`, `iva.quality_score`, `iva.movement_pattern`); paste verify output into lab note |

Tracker: [`HOTFIXES_NOTES.md`](./HOTFIXES_NOTES.md) § Pending.

**Behavioural triggers (Media DDL) — already Completed in pin `2.25.105`**. Do not re-open unless a new Behavioural follow-up lands.

**Analytics Face | Body | Both — no new DB migration.** Already shipped with `2.25.105`.

**How we ship (memorize this):**

1. **Commit + push the whole open pin** to GitHub (Stage 1 hard gate — Open + Pending + related dirty paths; name Stage 3 migrations)  
2. **Build images** on a remote lab PC → GHCR (**only** from that pushed tip)  
3. **Install** on labs by **pulling GHCR** (images **+** tray **+** named migrations via schema apply/verify)

**Non-negotiable:** A lab that “works” after `docker cp`, a local `docker build`, or copying `main.dart.js` between hosts is **debug**, not a release. Other labs must not be patched that way. Source → GHCR → pull.

This is the **canonical** EyeNet platform release contract.  
For a plain-language walkthrough + glossary, see [`eyenet-cicd-operator-guide.md`](./eyenet-cicd-operator-guide.md).  
Runnable installers and compose live under [`deployment/`](../../deployment/).  
Background proposals under `docs/proposals/CICD policy and implementation/` must follow this document.

---

## Three steps — use this wording

Tell the agent (or yourself) which step you want. Do **not** assume they happen together.

| Step | What it updates | Say this |
|---|---|---|
| **1 — Code** | GitHub repo: **commit + push the whole open pin** (all Pending/unstaged product paths for that pin — not only the latest chat fix), plus installers, docs, pins, **CHANGELOG**, and named Stage 3 migrations | *“Stage 1: push code to GitHub per platform-release-cicd.md”* |
| **2 — Images** | GHCR container tags for the current `VERSION` (build on preferred Stage 2 lab) | *“Stage 2: build and push images for VERSION on lab-work-win-eynetdell”* |
| **3 — Install** | Running stack on a named lab (compose pull + tray + **named migrations** via `schema/apply.sh` / `schema/verify.sh`) | *“Upgrade lab-home-win-nickg”* / *“Upgrade Ubuntu on lab-work-dual-64g”* |

Optional extras (always name them explicitly):

- *“Also bump VERSION to X.Y.Z”* (Stage 1; then Stage 2 when you want new containers)
- *“Also publish tray for X.Y.Z”* (manual build + GitHub Release — see [Tray publish](#tray-publish-part-of-stage-1))

**Critical separations:**

- Stage 1 **hard gate:** every lasting fix for the **open pin** must be **committed and pushed** before Stage 2 — including related unstaged work and HOTFIXES **Pending** paths, not only the latest chat fix. A lab `docker cp` / `.env` edit / DB ALTER that works on one host is **not** Stage 1.  
- Stage 1 does **not** change what labs pull from GHCR.  
- Stage 2 does **not** upgrade lab hosts unless you also ask for Stage 3.  
- Stage 3 installs **both** container images and the host tray (when Release assets exist, or when you copy a locally built tray onto the lab) **and** applies/verifies every migration named in Open / HOTFIXES / CHANGELOG for that pin.  
- Images are built from the git revision checked out on the build host (usually latest `main` after Stage 1). Stage 2 without that push rebuilds **old** source.

**Release notes:** Root [`CHANGELOG.md`](../../CHANGELOG.md) is required on meaningful Stage 1. Saying *“Stage 1 … per platform-release-cicd.md”* already means: land the **whole open pin**, update the changelog (including Stage 3 migration names or an explicit “no new migration”), then commit and push. Do not use `docs/notes.txt` for release notes.

```text
  Mac (you)                 GitHub / Releases              Lab PC (amd64)               GHCR
     │                            │                              │                        │
     │  1. Code: commit+push      │                              │                        │
     │  (+ CHANGELOG, pins) ─────►│                              │                        │
     │                            │                              │                        │
     │  Tray (manual today) ──────┼── build on Win + Ubuntu ─────►│  upload Release assets │
     │                            │                              │                        │
     │  2. Images: SSH/RDP ───────┼─────────────────────────────►│  build + push ─────────►│
     │                            │                              │                        │
     │  Mode D finalize ──────────┼── release-manifest.yml ─────►│  (commit in Stage 1)    │
     │                            │                              │                        │
     │  3. Install / upgrade ─────┼─────────────────────────────►│  installer (images+tray)│
```

**GitHub Actions:** Stage 2 (GHCR images) remains manual lab builds today — `platform-release.yml` is still draft. Tray publish may use `.github/workflows/tray-release.yml` (`workflow_dispatch` or tag `v*`); manual lab build + `gh release` remains valid.
---

## Core rule

**One product on GHCR. Two installers. One tray pin on GitHub Releases.**

| Layer | Count | Location |
|---|---|---|
| Service images | **One** set of tags per `VERSION` | GHCR via Stage 2 |
| Compose + schema pack | **One** shared bundle | `deployment/windows-installer/` |
| Windows/WSL installer | Host bootstrap | `deployment/windows-installer/install-*.bat\|ps1` |
| Ubuntu 24 installer | Host bootstrap | `deployment/ubuntu/install-eyenet-ubuntu.sh` |
| Host tray binaries | **One** pin, two OS assets | GitHub Releases `v${VERSION}` (`tray-release.yml` or manual) |

WSL Ubuntu and native Ubuntu 24 pull the **same** `linux/amd64` images. They are not two products.

| Kind of change | Fix in | Then |
|---|---|---|
| Product / service bug | Monorepo service | Stage 1 → Stage 2 → Stage 3 |
| Installer / host path | Matching installer script | Stage 1 → Stage 3 (no Stage 2) |
| Tray UI / start-stop | `deployment/tray/` | Stage 1 → [manual tray publish](#tray-publish-part-of-stage-1) → Stage 3 |

Do **not**:

- Publish Ubuntu-only or Windows-only service image tags  
- Treat a lab `docker cp` / compose override / live DB patch as a release (bring the same change into monorepo source first)  
- Start Stage 2 while affected service source is still only on a lab or only in an uncommitted working tree  
- **Promote a lab-local image** (untagged digest, HTML copy, `docker commit`) to another lab or call that Stage 3  
- **Reuse stale `ppl-meta-frontend/build/web`** when publishing frontend (Stage 2 always rebuilds Flutter web unless `SKIP_FLUTTER_REBUILD=1`)  
- Bump only one installer’s `RELEASE_TAG`  
- Skip [`CHANGELOG.md`](../../CHANGELOG.md) on a meaningful Stage 1  
- Wait on GitHub Actions for images or tray — both are **manual** until this doc says otherwise  
- Use the Apple Silicon Mac as the default Stage 2 builder  
- Put tray binaries into GHCR or the twelve-image verify gate  

### Pipeline failure mode (2026-09-21) — read this

What went wrong: nickg ran a **local** frontend image that fixed logout-after-triggers; GHCR `:2.25.83` was a **different** digest; Ubuntu Stage 3 correctly pulled GHCR and “regressed.” Copying HTML between labs papered over it and **broke the CI/CD contract**.

Root causes (process + tooling):

1. Stage 1 incomplete or bypassed while a lab hotfix was treated as done.  
2. Stage 2 could run on a dirty / divergent checkout, or skip Flutter rebuild when `build/web` already existed.  
3. Operators/agents used lab-to-lab asset copy instead of GHCR.

**Prevention (enforced in scripts):**

| Gate | Script | Behavior |
|---|---|---|
| Source on GitHub | `scripts/stage2_preflight.sh` (via `stage2_one.sh`) | `HEAD == origin/main`; no dirty files under each service being built |
| Fresh frontend assets | `scripts/stage2_one.sh` | Always `flutter build web --release` unless `SKIP_FLUTTER_REBUILD=1` |
| Escape hatch | `STAGE2_ALLOW_DIRTY=1` | Emergency only — **not** a release path; still Stage-1 the code afterward |

Stage 3 stays: **compose pull from GHCR only**. If two labs disagree, compare digests (`docker image inspect … RepoDigests`) — never copy container files between them as the fix.

---

## Directory contract

| Path | Owns |
|---|---|
| `deployment/` | Scripts, compose, schema pack, installers (executable truth) |
| `docs/deployment/` | CI/CD and operator documentation (this file = process truth) |
| [`lab-machines.md`](./lab-machines.md) | Named lab inventory, Stage 2/3 access, **fleet status vs GHCR** |
| [`eyenet-cicd-operator-guide.md`](./eyenet-cicd-operator-guide.md) | Operator guide; follows this contract |
| [`CHANGELOG.md`](../../CHANGELOG.md) | Product release notes (required in Stage 1) |
| `deployment/tray/` | Host tray source (Go systray) |
| [`tray-stage-1.5-publish.md`](./tray-stage-1.5-publish.md) | Checklist: Actions `tray-release.yml` or manual tray build + upload |
| `.github/workflows/tray-release.yml` | Tray build/upload (`workflow_dispatch` or tag `v*`) |
| `scripts/build_windows_installer_images.sh` | Stage 2: build `linux/amd64` images |
| `scripts/push_protected_service_images.sh` | Stage 2: push to GHCR |
| `scripts/stage2_one.sh` | Stage 2: one-service build+push + `REPORT OK` (runs source gate) |
| `scripts/stage2_preflight.sh` | Stage 2: require `origin/main` + clean service trees |
| `scripts/stage2_changed_services.sh` | Stage 2: map git range → services (`ALL` / `NONE` / list) |
| `scripts/stage2_retag_forward.sh` | Stage 2 Mode D: retag unchanged images to a new pin |
| `scripts/write_release_manifest.sh` | Stage 2: write digest manifest from GHCR |
| `scripts/verify_release_manifest.sh` | Stage 2: verify manifest digests match GHCR |
| `scripts/stage2_finalize_manifest.sh` | Stage 2: tag verify → write manifest → digest verify |
| `scripts/platform_release_images.sh` | Shared twelve-image names / digest helper |
| `deployment/windows-installer/release-manifest.yml` | Digest coherence for current `VERSION` |
| `scripts/verify_platform_release.sh` | Stage 2: post-publish GHCR tag gate |
| `scripts/check_installer_pins.sh` | Pin gate (Stage 1 and before Stage 2) |
| `.github/workflows/platform-release.yml` | **Future** Stage 2 automation — draft; **not used today** |

---

## Stage 1 — Push code to GitHub (frequent)

**Goal:** Land fixes, docs, and installer changes on GitHub. Do this often.

**Does:** `git` commit + push of the **whole open pin** — all affected service source, related Pending/unstaged product paths, pin bumps / schema pack when needed — **and** update [`CHANGELOG.md`](../../CHANGELOG.md) with Stage 3 migration notes.  
**Does not:** rebuild or push Docker images to GHCR; does not upgrade labs; does not auto-publish tray (tray is manual — see below).

### Hard gate — whole open pin, not only the current chat fix (do this first)

Stage 1 is **not complete** until the monorepo on GitHub contains the lasting code for **every** service or path that belongs to the **open pin** (Open table + HOTFIXES **Pending**), not only the files from the latest operator message. This is the first gate of CI; Stage 2 and Stage 3 assume it.

When the operator says *“Stage 1”* / *“proper Stage 1”* / *“Stage 1 for this”*:

1. **Sweep the open pin** — read this doc’s **Open** table and [`HOTFIXES_NOTES.md`](./HOTFIXES_NOTES.md) § Pending for the current `VERSION`. Treat that list as the Stage 1 scope.  
2. **Sweep `git status`** — include **all** uncommitted product/source/schema/installer/operator-doc changes that belong to that pin (e.g. leftover `ppl-meta-cameras` fixes, dual CI/CD doc copies, pack SQL). Do **not** Stage-1 only the latest chat’s files while related pin work stays dirty.  
3. **Exclude only explicit non-product leftovers** — private `docs/notes.txt`, secrets, one-off lab-data scripts, and local artifacts the operator says to leave out (e.g. personal `artifacts/*.sh` scratch). Ask once if unclear; default is **include**.  
4. **List affected paths** — e.g. `ppl-meta-cameras`, `ppl-meta-vmeta`, schema pack, compose/env templates, installers, docs. If you hotfixed more than one container, each matching monorepo tree must be updated.  
5. **Port lab hotfixes into source** — copy lasting logic from `docker cp` / one-off scripts into the repo files. Lab-only DB row edits stay lab data; durable DDL belongs in `deployment/windows-installer/schema/pack/`.  
6. **Name Stage 3 migrations in the same push** — every new/changed pack SQL file and `schema/verify.sh` gate must appear in: CHANGELOG (Added/Notes), Open **Stage 3** row, and HOTFIXES **Schema** line. If the pin has **no** new migration, say so explicitly (`No new migration` / `schema apply still required for prior pack`).  
7. **Commit and push those sources to GitHub** (same Stage 1 push as CHANGELOG below, or an earlier push — either way they must be on the remote before Stage 2 starts).  
8. **Refuse Stage 2** if `git status` still shows uncommitted **product** fixes for the open pin, or if the only working copy of a fix is on a lab container.  
9. **Every column the shipped code writes is in the schema pack and in `schema/verify.sh` in this same push.** A CHANGELOG **Notes** line that a column is missing, or that persist can 500 until a later schema follow-up, means Stage 1 is not done. Do not cut that pin.

Example (instant detection / stream freeze): cameras + vmeta source **and** schema `048_…` must be pushed before rebuilding those GHCR images. A nickg `docker cp` that “works” is not a release.

**Anti-pattern:** “Stage 1 for this Motion fix” that leaves a related dirty `ppl-meta-cameras` change uncommitted while Open/Stage 2 still lists **cameras**. That is an incomplete Stage 1; Stage 2 would rebuild old cameras source.

### CHANGELOG is mandatory (do not wait to be asked)

Every Stage 1 with product, installer, schema, tray, or operator-facing doc changes must update root `CHANGELOG.md` in the same push:

1. Prefer `## [Unreleased]` while iterating on `main` without a pin bump.  
2. When cutting or reinforcing a pin, use `## [X.Y.Z] — YYYY-MM-DD` matching root `VERSION`.  
3. Sections: **Added** / **Changed** / **Fixed** / **Notes** (omit empty ones).  
4. No secrets. Keep bullets short.  
5. Docs-only with no user/installer impact: one-line **Notes** is enough (skip only pure typo/chore).

### Typical steps

1. **Hard gate:** sweep Open + HOTFIXES Pending + `git status`; land and **commit + push** the **whole open pin** (see above). No lasting lab-only hotfixes; no “current fix only” while related pin paths stay dirty.  
2. If cutting a new product pin: set root `VERSION` and **all** installer pins to the same value.  
3. If schema changed: `bash deployment/mac-lima/sync-schema-pack.sh` and include `schema/pack.tar.gz`.  
4. Update [`CHANGELOG.md`](../../CHANGELOG.md) — include **Stage 3 migration names** (or explicit “no new migration”).  
5. Update Open **Stage 3** row + HOTFIXES **Schema** with the same migration list.  
6. `./scripts/check_installer_pins.sh`  
7. Commit and **push to GitHub** (includes any remaining Stage 1 files from steps 2–6).  
8. **If tray binaries should refresh for this pin:** [publish tray manually](#tray-publish-part-of-stage-1) (lab builds + GitHub Release).

Agent wording:

- *“Stage 1: push code to GitHub per platform-release-cicd.md”* ← whole open pin + changelog + Stage 3 migration notes  
- *“Bump VERSION to 2.25.83 and Stage 1 push”*  
- *“Publish tray for 2.25.83”* ← `gh workflow run tray-release.yml` (or manual build/upload)

After Stage 1 alone: labs can `git pull` installer scripts; containers stay on the previous GHCR tag until Stage 2; tray binaries update only after Release assets exist (Actions or manual upload).

### Tray publish (part of Stage 1)

Tray is a **host binary**, not a container. Prefer `.github/workflows/tray-release.yml` (`workflow_dispatch` with version, or tag push `v*`). Manual lab builds + `gh release` remain valid when Actions is unavailable.

| Asset | Build on |
|---|---|
| `eyenet-tray-windows-amd64-${VERSION}.exe` | Actions `windows-latest` or Windows lab |
| `eyenet-tray-linux-amd64-${VERSION}.tar.gz` | Actions `ubuntu-latest` or Ubuntu lab (GTK/AppIndicator) |
| `SHA256SUMS` | Actions job or either host after both assets exist |

```bash
# Preferred:
gh workflow run tray-release.yml -f version="$(tr -d '[:space:]' < VERSION)"

# Manual fallback — after Stage 1 push lands tray source on main — on each OS lab:
git fetch origin && git checkout main && git pull --ff-only
VERSION="$(tr -d '[:space:]' < VERSION)"
cd deployment/tray

# Windows (PowerShell / Git Bash):
go build -ldflags "-X main.version=${VERSION}" -o "eyenet-tray-windows-amd64-${VERSION}.exe" ./cmd/eyenet-tray

# Ubuntu:
sudo apt-get install -y libgtk-3-dev libayatana-appindicator3-dev   # once
go build -ldflags "-X main.version=${VERSION}" -o eyenet-tray ./cmd/eyenet-tray
tar -czf "eyenet-tray-linux-amd64-${VERSION}.tar.gz" eyenet-tray

# From Mac or any host with gh + both artifacts:
gh release create "v${VERSION}" \
  --title "EyeNet platform ${VERSION}" \
  --notes "Host tray binaries for EyeNet ${VERSION}. Service images remain on GHCR via Stage 2." \
  eyenet-tray-windows-amd64-${VERSION}.exe \
  eyenet-tray-linux-amd64-${VERSION}.tar.gz \
  SHA256SUMS
# If the release already exists: gh release upload "v${VERSION}" … --clobber
```

You may create git tag `v${VERSION}` when cutting the Release; that is for labeling assets, **not** to trigger Actions.

Checklist: [`tray-stage-1.5-publish.md`](./tray-stage-1.5-publish.md).  
Source: [`deployment/tray/`](../../deployment/tray/).

Installers **soft-fail** if the asset is missing (compose install still succeeds). For lab soak before a Release exists, copy the binary onto the host and write `tray.json` locally (see tray README / SMOKE).

Tray-only path changes make `scripts/stage2_changed_services.sh` print **`NONE`** (skip Stage 2).

---

## Stage 2 — Build and push images (when ready)

**Goal:** Refresh GHCR so both installers `compose pull` the latest product for the pinned `VERSION`.

**Precondition:** Stage 1 hard gate is done — affected service source is on GitHub (`origin/main`). Do not build from a lab hotpatch alone.

**Does:** Flutter web build (frontend: always, unless explicitly skipped) + Docker build/push of changed or all services + verify (+ Mode D manifest).  
**Does not:** replace Stage 1; does not upgrade lab hosts (that is Stage 3).

`stage2_one.sh` **refuses** to run unless the build host checkout matches `origin/main` and the service trees being built are clean (`scripts/stage2_preflight.sh`). Override only with `STAGE2_ALLOW_DIRTY=1`.

After a successful Stage 2, on the next Stage 1 (manifest commit), add under the matching CHANGELOG version:

- **Notes:** `GHCR images published for X.Y.Z` (optional hygiene; do not block Stage 2 on it).

### Build host

**Preferred Stage 2 builder is `lab-work-win-eynetdell` (hostname `EYNETDELL`, 32 GB, WSL distro `eyenet`).**  
Inventory: **[lab-machines.md](./lab-machines.md)**.

| Preference | Lab ID | When |
|---|---|---|
| **Preferred (default)** | `lab-work-win-eynetdell` | Always first choice for Stage 2 / Mode D (WSL `eyenet` + Docker; give WSL ≥24 GB via `.wslconfig`) |
| Fallback (ask first) | `lab-work-dual-64g` (`eyenet-demo`) | **Only** if eyenetdell is unavailable **and** the operator explicitly approves using eyenet-demo |
| Optional | `lab-home-win-nickg` | Home Windows if disk and RAM allow (still ask before using) |
| Not for Stage 2 | `lab-work-u24-mini-8g` | 8 GB soak only |

**Hard rule for agents:** do **not** start Stage 2 on `lab-work-dual-64g` / `eyenet-demo` (or any non-preferred host) without asking the operator first. If eyenetdell is unreachable, stop and ask — do not silently fall back.

- Customer/lab images are **`linux/amd64`**.  
- The development Mac (especially Apple Silicon) is **not** the default builder.  
- Connect over **LAN** (`ssh Administrator@192.168.9.11`) or reverse tunnel when off-LAN; then `wsl -d eyenet`.  
- On the host: `git pull` the Stage 1 revision in the WSL clone, then run the scripts below.  
- Mac = operator console (edit, Stage 1, manifests, remote into builder). On-prem Cursor on EYNETDELL may run Stage 2 locally in WSL.

Agent wording must name the lab: *“Stage 2 on lab-work-win-eynetdell (WSL eyenet).”*

### SSH timeouts (required practice)

Long builds drop idle SSH (especially Tailscale DERP). Do **not** rely on one interactive SSH for hours.

1. **`tmux` / `screen` on the builder**, or  
2. **One image per short SSH** (`stage2_one.sh` → `REPORT OK`) — a timeout only loses the current service.

```bash
mkdir -p /tmp/eyenet-stage2
# inside tmux:
RELEASE_TAG=2.25.83 ./scripts/stage2_one.sh cameras 2>&1 | tee /tmp/eyenet-stage2/cameras.log
```

### Tags: product pin vs trace

| Tag | Example | Who uses it |
|---|---|---|
| **Product pin** | `2.25.83` | Installers (`RELEASE_TAG` / `VERSION`) |
| **Trace sub-tag** | `2.25.83-92ea2d5` | Optional audit (`EXTRA_SHA_TAG=1`) |

- Installers **must** keep pulling `:VERSION`.  
- Selective Stage 2 may leave some services on an older digest under the same `:VERSION` until rebuilt — intentional.  
- **Release manifest** records digests for the pin (coherence / audit; installers still pull by tag today).

### Mode A — Full Stage 2 (all twelve)

Use after a version cut, shared/schema changes, or when `stage2_changed_services.sh` prints `ALL`.

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

Classic all-at-once (only inside **tmux**):

```bash
./scripts/build_windows_installer_images.sh
./scripts/push_protected_service_images.sh
./scripts/stage2_finalize_manifest.sh
```

### Mode B — One-by-one with report-back (SSH-safe default)

```bash
# Windows/WSL builder example
ssh lab-home-win-nickg "wsl -d eyenet -- bash -lc 'cd /mnt/c/path/to/repo && RELEASE_TAG=2.25.83 EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh cameras'"

# Preferred: eyenetdell WSL (on the box or via SSH then wsl)
wsl -d eyenet -- bash -lc 'cd ~/ppl-meta-platform && git pull && RELEASE_TAG=2.25.83 EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh cameras'

# Fallback only after operator approval: eyenet-demo
# ssh eyenet@192.168.9.13 "cd ~/ppl-meta-platform && git pull && RELEASE_TAG=2.25.83 EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh cameras"
```

Expect:

```text
REPORT OK service=cameras tag=2.25.83 sha_tag=2.25.83-<shortsha> ref=ghcr.io/.../ppl-meta-cameras:2.25.83
```

Loop: next service only after `REPORT OK`; on fail or SSH drop, retry **that** service. When the intended set is done:

```bash
./scripts/stage2_finalize_manifest.sh
```

Service keys:  
`node` `media` `gateway` `orchestrator` `discovery` `communications` `frontend` `vision` `vmeta` `cameras` `presence` `models`  
(GHCR: `ppl-meta-vision-protected` / `ppl-meta-vmeta-protected` for vision/vmeta.)

### Mode C — Selective Stage 2 from latest Stage 1

**When:** Stage 1 fixed a few services; skip a full twelve-image rebuild.

```bash
git fetch origin
./scripts/stage2_changed_services.sh HEAD~1..HEAD
# or: ./scripts/stage2_changed_services.sh <before_sha> <after_sha>
```

| Output | Action |
|---|---|
| `NONE` | Docs/installer/tray-only — **skip Stage 2** |
| `ALL` | Mode A full Stage 2 |
| `cameras frontend` | Mode B only those keys |

```bash
SERVICES=$(./scripts/stage2_changed_services.sh HEAD~1..HEAD)
RELEASE_TAG="$(tr -d '[:space:]' < VERSION)"
for s in $SERVICES; do
  EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh "$s"
done
./scripts/stage2_finalize_manifest.sh
```

Then Stage 1: commit `release-manifest.yml` + CHANGELOG Notes (which services, git SHA).

**Agent wording:**

- *“Stage 2 full on lab-work-win-eynetdell for 2.25.83 (tmux / one-by-one).”*
- *“eyenetdell unavailable — may I use eyenet-demo as Stage 2 fallback?”*  
- *“Stage 2 selective on lab-home-win-nickg from latest Stage 1.”*  
- *“Stage 2 one: cameras then frontend on lab-home-win-nickg.”*

### Mode D — Release manifest + retag-forward (coherence)

**Goal:** Every pin has a complete twelve-image digest identity without rebuilding unchanged heavy services.

| Layer | Role |
|---|---|
| Root `VERSION` / `RELEASE_TAG` | Customer-facing platform pin |
| `:VERSION` on GHCR | What installers pull **today** |
| `:VERSION-<sha>` | Optional audit sub-tag |
| `release-manifest.yml` | Digest source of truth for the pin |

**Artifact:** [`deployment/windows-installer/release-manifest.yml`](../../deployment/windows-installer/release-manifest.yml)

```yaml
schema_version: 1
platform_version: "2.25.83"
git_sha: "92ea2d5"
created_at: "2026-09-19T…"
registry: "ghcr.io/nickglezakos/ppl-meta-platform"
images:
  ppl-meta-node:
    tag: "2.25.83"
    digest: "sha256:…"
  # …all twelve
```

**Rules**

1. After every Stage 2 that completes a pin, run `./scripts/stage2_finalize_manifest.sh`.  
2. **Stage 1 commit** the updated manifest (+ CHANGELOG Notes). Do not hand-edit digests.  
3. Selective rebuild on an existing pin: rebuild changed → finalize.  
4. **New pin** with only some services changed:

```bash
RELEASE_TAG=2.25.83 EXTRA_SHA_TAG=1 ./scripts/stage2_one.sh cameras
FROM_TAG=2.25.83 TO_TAG=2.25.83 EXCLUDE="cameras" ./scripts/stage2_retag_forward.sh
RELEASE_TAG=2.25.83 ./scripts/stage2_finalize_manifest.sh
# Stage 1: commit release-manifest.yml + Notes
```

5. `./scripts/verify_release_manifest.sh` must pass before treating the pin as coherent.  
6. Installers still pull by `:VERSION` in v1.

**Agent wording:**

- *“Stage 2 Mode D: finalize release manifest for 2.25.83.”*  
- *“Stage 2 pin bump 2.25.83→2.25.83: rebuild cameras, retag-forward the rest, finalize manifest.”*

Version-specific notes: [first-windows-release-2.25.83.md](../guides/first-windows-release-2.25.83.md).

### Future automation (not used today)

Do **not** depend on GitHub Actions for platform shipping:

| Workflow | Intent | Status today |
|---|---|---|
| `.github/workflows/platform-release.yml` | Automate Stage 2 image matrix | **Draft** — Stage 2 stays manual (Modes A–D) |
| `.github/workflows/tray-release.yml` | Automate tray build/upload on tag `v*` / dispatch | **Active** — preferred; manual `gh release` still OK |

Stage 2 stays manual on a lab PC. Tray: prefer Actions; keep real OS smoke on lab hardware either way.

---

## Stage 3 — Install on labs (images + tray)

**Goal:** Put the published product onto a named lab host. Always say which lab ([lab-machines.md](./lab-machines.md)).

**Does:** Installer (or manual compose pull) + **named migrations** via schema apply/verify + discovery reregister + **tray download/autostart** when Release assets exist.  
**Does not:** publish GHCR or rebuild tray binaries.

**Migrations (required checklist item):** Before calling Stage 3 done, confirm the Open **Stage 3** row / HOTFIXES **Schema** / CHANGELOG list for this pin. Run `schema/apply.sh` then `schema/verify.sh` so every named pack SQL and gate is applied. If Open says **no new migration**, still run apply/verify (idempotent) and note that in the lab entry. A compose pull that skips schema is **not** Stage 3.

**Tracking:** After every Stage 3, update the **Fleet status** table in [lab-machines.md](./lab-machines.md) (pin, match vs `release-manifest.yml`, date, notes, **migrations verified**). A matching tag is not enough — digests must match. Stage 3 is not finished on a compose pull alone. The lab note must include the `schema/verify.sh` output (every `OK` line, or the `FAIL` that stopped the install), including the gates named for this pin.

### Shared post-install (both installers)

After `compose up -d`:

1. Wait for Postgres healthy  
2. `schema/apply.sh` then `schema/verify.sh` (fail install if verify fails) — covers **all migrations named for this pin** in Open / HOTFIXES / CHANGELOG  
3. `reregister-discovery-services.sh` (canonical: `deployment/windows-installer/`)  
4. Print UI / gateway / discovery / bootstrap URLs  
5. Remind: `ADVERTISE_HOST` must be the LAN IP phones use  
6. Install/launch host tray from GitHub Releases `v${VERSION}` (soft-fail if missing)  
7. Update [lab-machines.md](./lab-machines.md) § Fleet status for that lab (pin + digests + migration verify)

Host-only:

- **Windows:** WSL `eyenet`, host RAM ≥16 GB, `.wslconfig` 14 GB / 6 CPUs / 2 GB swap  
- **Ubuntu:** Docker CE, docker group, optional DNS, `ADVERTISE_HOST` from `ip -4 addr`

### Windows / WSL

Runtime: [windows-wsl-docker-engine-full-product.md](./windows-wsl-docker-engine-full-product.md).

1. Ensure installer files match git.  
2. First time: `install-eyenet-wsl.bat`.  
3. `install-platform.ps1` (or double-click `install-platform.bat` launcher) — pulls `${RELEASE_TAG}`, starts stack, schema, reregister, tray.  
4. Open `http://localhost:3000`. Confirm tray icon (Active/Inactive).  
5. Health:

```powershell
curl http://localhost:8006/api/v1/services
curl http://localhost:8080/api/v1/licensing/bootstrap/status
```

Manual pull (existing install):

```powershell
wsl -d eyenet -- bash -lc "cd /mnt/c/path/to/install && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml pull && docker compose --project-name pplmeta --env-file .env.windows -f docker-compose.windows-installer.yml up -d && bash schema/apply.sh && bash reregister-discovery-services.sh"
```

### Native Ubuntu 24

```bash
bash deployment/ubuntu/install-eyenet-ubuntu.sh
# or: ADVERTISE_HOST=<lan-ip> RELEASE_TAG=<VERSION> bash deployment/ubuntu/install-eyenet-ubuntu.sh
```

Confirm `ADVERTISE_HOST` with `ip -4 addr show scope global`. Confirm tray / AppIndicator. Health:

```bash
curl -s http://127.0.0.1:8006/api/v1/services
# UI: http://<ADVERTISE_HOST>:3000/network
```

Manual upgrade of existing `~/eyenet-platform`:

```bash
cd ~/eyenet-platform
# Omit `-f docker-compose.yml` alone so Compose also merges `docker-compose.override.yml`
# (required on Ubuntu labs for USB `/dev/video*` device mounts).
docker compose --project-name pplmeta --env-file .env pull
docker compose --project-name pplmeta --env-file .env up -d
bash ~/ppl-meta-platform/deployment/windows-installer/schema/apply.sh
bash ~/ppl-meta-platform/deployment/windows-installer/schema/verify.sh
bash ~/ppl-meta-platform/deployment/windows-installer/reregister-discovery-services.sh
```

If only installer/tray scripts changed (Stage 1 only), `git pull` and re-run the installer — image pull alone does not update scripts or tray.

Tray smoke: [`deployment/tray/SMOKE.md`](../../deployment/tray/SMOKE.md).

---

## Version identity

One release identity must agree everywhere:

1. Root `VERSION`  
2. GHCR tags `…/<service>:${VERSION}` (**Stage 2 only**)  
3. Release manifest digests for that `platform_version`  
4. Windows pins: `install-platform.ps1` / `.bat` launcher / `.env.windows.template`  
5. Ubuntu pin: `install-eyenet-ubuntu.sh` default `RELEASE_TAG=`  
6. GitHub Release tag `v${VERSION}` (tray assets)  
7. After promotion: wiki `software_ref.platform_version` and Authority eligibility  

```bash
./scripts/check_installer_pins.sh
./scripts/verify_platform_release.sh          # tags exist
./scripts/verify_release_manifest.sh          # digests match GHCR + VERSION
```

---

## Full version cut (all three steps)

When you want a new pin end-to-end (e.g. `2.25.83`):

1. **Stage 1:** bump `VERSION` + all pins, schema pack if needed, CHANGELOG under `[2.25.83]`, pin check, commit, push. If tray should ship: [publish tray manually](#tray-publish-part-of-stage-1) and confirm Release assets.  
2. **Stage 2:** on preferred builder (`lab-work-win-eynetdell` / WSL `eyenet`; ask before any eyenet-demo fallback), build/push changed images; Mode D retag-forward unchanged services on a pin bump; `stage2_finalize_manifest.sh`.  
3. **Stage 1 (manifest):** commit `release-manifest.yml` + CHANGELOG Notes.  
4. **Stage 3:** upgrade named labs — installers pull images **and** download tray (or use a locally copied tray binary).  
5. Update wiki `software_ref` after promotion evidence.

Wording:

- *“Full release to 2.25.83 per platform-release-cicd.md (Stage 1 + publish tray + Stage 2 + upgrade both labs).”*

---

## Bug triage

| Kind of bug | Fix in | Stage 1? | Stage 2? | Stage 3? |
|---|---|---|---|---|
| Service code, Dockerfile, compose memory, schema pack | Monorepo / pack | **Yes** | **Yes** (when ready) | Pull on labs |
| WSL / Windows installer | `deployment/windows-installer/` | **Yes** | No | Re-run Windows installer |
| Ubuntu host path | `deployment/ubuntu/` | **Yes** | No | Re-run Ubuntu installer |
| Shared post-up (reregister, schema verify) | Prefer `deployment/windows-installer/` | **Yes** | No | Both installers |
| Tray UI / start-stop / status | `deployment/tray/` | **Yes** + manual tray publish | No | Re-run installer / replace binary |

A **code** release is complete after Stage 1.  
A **tray** release is complete after GitHub Release assets for `v${VERSION}` exist (or labs have a locally installed binary).  
A **product** release is complete when Stage 2 has updated GHCR **and** Stage 3 has pulled that pin.

---

## Today vs later

| Step | Where | Frequency |
|---|---|---|
| 1 — Code | Mac → GitHub | Often |
| Tray publish | `tray-release.yml` or labs → `gh release` | When tray changes or a pin needs tray assets |
| 2 — Images | Named lab → GHCR (manual) | When you want new containers |
| 2b — Manifest | Mac or builder → `release-manifest.yml` → Stage 1 commit | After Stage 2 completes a pin |
| 3 — Install | Each lab host | When asked |

**Later (optional):** enable `platform-release.yml` for Stage 2 only after this doc is updated to say it is active. Tray Actions (`tray-release.yml`) is already preferred. Keep real OS smoke on lab hardware either way.

---

## Related

- Operator guide: [eyenet-cicd-operator-guide.md](./eyenet-cicd-operator-guide.md)  
- Lab machines: [lab-machines.md](./lab-machines.md)  
- Tray tag checklist: [tray-stage-1.5-publish.md](./tray-stage-1.5-publish.md)  
- Release notes: [`CHANGELOG.md`](../../CHANGELOG.md)  
- Index: [README.md](./README.md)  
- Ubuntu follow-ups: [`deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md`](../../deployment/ubuntu/UBUNTU-LAB-FOLLOWUPS.md)  
- Windows installer README: [`deployment/windows-installer/README.md`](../../deployment/windows-installer/README.md)  
- Tray README: [`deployment/tray/README.md`](../../deployment/tray/README.md)  
- Lifecycle proposals: [`docs/proposals/CICD policy and implementation/`](../proposals/CICD%20policy%20and%20implementation/)
