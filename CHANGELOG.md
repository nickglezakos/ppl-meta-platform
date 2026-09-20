# Changelog

All notable changes to the EyeNet / PPL Meta platform are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Version identity matches root [`VERSION`](./VERSION) and GHCR image tags.

**Process:** Updating this file is a **required Stage 1** step — see  
[`docs/deployment/platform-release-cicd.md`](./docs/deployment/platform-release-cicd.md).  
You do not need to ask separately for “update the changelog.”

Do **not** put secrets, passwords, or personal scratch notes here (use a private notes file outside this changelog).

---

## [Unreleased]

### Fixed

- Node Alpine image: install `linux-headers` and allow `netifaces` to compile on GCC 14 (`-Wno-error=int-conversion`).
- Communications / orchestrator / vmeta: write file logs under `/app/logs` so non-root containers can start.
- vmeta protected image: install `httpx` required by analytics.

### Changed

- Authority admin UI rebuilt as a laconic mobile-first shell (Home / People / Licences / Me); retired the dual Workspace vs Data Console surface (`/admin/console` redirects to `/admin`).
- CI/CD contract: **three steps** (code → images → install); tray publish is **manual** lab build + `gh release` (GitHub Actions for tray/images are draft/future only).

### Added

- **EyeNet host tray** (`deployment/tray/`): Go systray for Windows (WSL) and Ubuntu — Active/Inactive/Degraded status, Open UI, Start/Stop/Restart; installers download from GitHub Releases tag `v${VERSION}` (soft-fail if missing).
- Tray publish via manual lab builds + `gh release` (`.github/workflows/tray-release.yml` is draft/future); documented in `platform-release-cicd.md`.
- Lab machines inventory: `docs/deployment/lab-machines.md` (`lab-home-win-nickg`, `lab-work-u24-mini-8g`, `lab-work-dual-64g`); linked from platform-release-cicd Stage 2.
- Stage 2 SSH-safe modes: one-by-one `scripts/stage2_one.sh` with `REPORT OK`, selective rebuild via `scripts/stage2_changed_services.sh`, optional `:VERSION-<sha>` sub-tags; documented in `platform-release-cicd.md`.
- **Release manifest (Mode D):** digest coherence for the twelve GHCR images — `scripts/write_release_manifest.sh`, `verify_release_manifest.sh`, `stage2_finalize_manifest.sh`, `stage2_retag_forward.sh`; artifact path `deployment/windows-installer/release-manifest.yml`; documented in `platform-release-cicd.md`.
- Operator CI/CD guide (for-dummies intro + full steps + terminology appendix): `docs/deployment/eyenet-cicd-operator-guide.md`.

### Notes

- GHCR images published for **2.25.82** from `lab-home-win-nickg` (git `cb066ae`); Windows tray asset on GitHub Release `v2.25.82`.
- Installers still pull by `:VERSION`; digests are the audit / future pin-by-digest contract. Run `stage2_finalize_manifest.sh` after Stage 2 completes a pin, then Stage 1-commit the manifest.
- First tray ship for pin `2.25.82`: after Stage 1 push, build tray on Windows + Ubuntu labs, `gh release create v2.25.82 …`, then Stage 3 lab soak.

## [2.25.82] — 2026-09-19

### Added

- Root `CHANGELOG.md` as the product release-notes source of truth; Stage 1 always updates it (no separate ask).
- Links from deployment CI/CD docs, installer READMEs, and Ubuntu lab follow-ups to the changelog.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG` defaults: **2.25.81 → 2.25.82**.
- `docs/deployment/platform-release-cicd.md`: changelog is mandatory on meaningful Stage 1; two-stage wording clarified.

### Notes

- Product fixes from the `2.25.81` Stage 1 push (cameras disconnect, frontend disconnect UX, communications/vmeta packaging, shared reregister) ship under this pin once **Stage 2** publishes GHCR tags for `2.25.82`.
- Until Stage 2 runs, labs still pull whatever older images are already on GHCR.

---

## [2.25.81] — 2026-09-19

### Added

- Two-stage release process documentation (`docs/deployment/platform-release-cicd.md`): Stage 1 git push, Stage 2 GHCR image build on Windows/Linux hosts.
- Native Ubuntu 24 lab installer (`deployment/ubuntu/install-eyenet-ubuntu.sh`) and lab follow-ups doc.
- Shared `reregister-discovery-services.sh` in the Windows installer bundle (mac-lima wraps it).
- Installer pin check script (`scripts/check_installer_pins.sh`).

### Changed

- Windows and Ubuntu installers both run schema apply/verify and discovery reregister after stack up.
- Platform release docs treat GitHub Actions as future Stage 2 automation only; current publish is manual on an amd64 builder.
- CI/CD policy / implementation plan aligned with two-stage local publish.

### Fixed

- Cameras disconnect during instant detection / mobile stream (per-camera stop path).
- Frontend camera card stops instant detection before disconnect.
- Communications Dockerfile packaging path for lab installs.
- vmeta protected Dockerfile packaging adjustments for published images.

### Notes

- Stage 1 code landed on `main`. Container fixes for that work are intended to publish under **2.25.82** Stage 2 (this pin was superseded for image tags before a full 2.25.81 image republish).
- Earlier in this pin: RTSP instant detection, Lima/WSL lab path, schema pack tracked for GitHub raw download (see git history).

---

## [2.25.80] and earlier

See git history and version-specific guides under `docs/guides/first-windows-release-*.md` for pre-changelog releases. New cuts start here.
