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

### Notes

*(none yet for post-2.25.85)*

---

## [2.25.85] — 2026-09-26

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.84 → 2.25.85**.
- Presence Actions: assign the reserved platform camera here; Settings only keeps match-group reserve.
- Presence **Scan Owner QR** / **Scan Owner QR + Video** decode QR from the assigned platform camera via cameras `scan-qr` (no browser MobileScanner).
- Presence detection cleanup stops instant detection only and no longer disconnects shared USB/RTSP workers.

### Added

- Cameras: `POST /api/v1/cameras/{device_id}/scan-qr` (OpenCV QR on shared frame buffer).
- Presence: `POST /api/v1/presence/mobile/sessions/{session_uuid}/scan-owner-qr`.

---

## [2.25.84] — 2026-09-26

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.83 → 2.25.84**.
- Presence People Profiles associate with installation user accounts by email
  (user accounts are source of truth for display name when linked).
- Presence People tab: **Sync with user accounts** button + linked-account chip;
  name is read-only when linked to a user.

### Fixed

- Individual Groups (`/individual-groups`): member cards show a top-left **link**
  icon (same height as trash) to open Member details / People profile linking.
- People Profile picker: tap a People row to **select** it (highlighted); only
  **Link** submits the link; one profile (or create-new) per submission.
- Presence: people↔user email association sync (startup + interval + manual +
  user create/update notify); audit `people_association`.

### Notes

- Stage 2 on `lab-work-dual-64g`: rebuilt **node** `8e711f1b…`, **frontend**
  `c5303a27…`, **presence** `2b9316be…` (tags `2.25.84` / `2.25.84-bc350b1`
  after SQLAlchemy pin); Mode D retag-forward remaining from `2.25.83`.
- **Stage 3** on `lab-work-dual-64g` @ `10.171.48.228` (2026-09-26):
  `RELEASE_TAG=2.25.84`; node/presence/frontend digests match; presence healthy.
- Presence `requirements.txt`: pin `sqlalchemy>=2.0.30,<2.1` so Stage 2 does
  not pull SQLAlchemy 2.1 (defaults to `psycopg` v3 and crash-loops without it).
- Prior pin **2.25.83** GHCR republishes (frontend People-link `f9b2184d…`,
  media discovery URL, CORS/`10.x`, etc.) remain under `[2.25.83]` below.

---

## [2.25.83] — 2026-09-20

### Added

- Discovery service registry persistence in Redis (reload on restart) plus compose `REDIS_URL`.
- Required discovery re-register timers: Windows `EyeNetDiscoveryReregister` scheduled task; Ubuntu `eyenet-discovery-reregister.timer`.
- Windows LAN publish (`publish-lan-ports.ps1`) and host Tailscale enroll (`enroll-host-tailscale.sh`) wired into the installer.
- Login screen shows installation UUID and per-machine password hint (cross-lab confusion).
- Mobile camera: clear sticky UUID on host change / 404; registration failure no longer fakes `cameraId: 0`.

### Fixed

- Discovery refused to advertise Docker/WSL bridge IPs without `ADVERTISE_HOST`.
- Node VPN enrollment reads UUID/key from `app_settings` after bootstrap when `.env` keys are empty (§10).
- Node prefers `ADVERTISE_HOST` for platform local IP (not container `172.18.x`).
- `start-eyenet-platform.bat` runs discovery reregister after compose up.
- Gateway analytics / camera counters called vmeta at `localhost:8008` inside the
  container (always fail). Now use compose `VMETA_SERVICE_URL` / `MEDIA_SERVICE_URL`
  / `CAMERAS_SERVICE_URL` (same as the rest of the gateway router).
- `/analytics/mvr-quality-metrics` 500 when no quality samples (`average_quality` is
  `None` but logged with `:.3f`).
- Schema pack: add `047_orchestrator_workflow_settings.sql` so people-counters
  status stops 500ing when `workflow_settings` was never created.
- Instant detection persist: vmeta INSERT schema fallbacks use Postgres `SAVEPOINT`
  so thinner `individuals` tables no longer abort the transaction
  (`InFailedSQLTransactionError` / results 404).
- Mobile stream freeze during instant detection: cameras DB pool sized for concurrent
  frame ingest (`CAMERAS_DB_POOL_SIZE` / `CAMERAS_DB_MAX_OVERFLOW`); default
  `VMETA_AGE_GENDER_TIMEOUT` lowered to 8s so Celery does not hold the pool on
  DeepFace cold-start.
- Schema pack: `048_individuals_created_by_session.sql` adds missing
  `individuals.created_by_session` when ORM created a thinner table.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.82 → 2.25.83**.
- Lab follow-ups: §9 Authority admin UX marked resolved; §1 persist+timer required; §14 nickg bootstrap/login documented; §5 documents instant-detection persist + stream-freeze failure mode.
- Stage 1 CI contract: hard gate to commit + push source for **all services
  affected by the fixes** before Stage 2 (`platform-release-cicd.md`).

### Notes

- GHCR images republished for **2.25.83** (`7282168f`) on `lab-work-dual-64g`:
  frontend `f9b2184d…` (tags `2.25.83` / `2.25.83-7282168`) — Individual Groups
  People-link icon + PPP select-then-link UX. **Stage 3** on
  `lab-work-dual-64g` @ `10.171.48.228` (2026-09-26).

- Stage 2 must rebuild at least: `ppl-meta-discovery`, `ppl-meta-node`, `ppl-meta-frontend` (login UUID). Republish cameras/frontend if Stage 3 still shows §13 disconnect gaps.
- **Also rebuild for this Stage 1:** `ppl-meta-cameras`, `ppl-meta-vmeta` (instant detection SAVEPOINT + pool/timeout). Apply schema pack / `048` on existing labs.
- Mobile §12 needs a new APK build (not GHCR). Stage 3: re-run elevated `publish-lan-ports.ps1` on existing Windows installs; wipe volumes to test `/bootstrap`.
- Lab `docker cp` hotpatches are not a release; Stage 1 hard gate + Stage 2 required.
## [2.25.82] — 2026-09-19

### Added

- Root `CHANGELOG.md` as the product release-notes source of truth; Stage 1 always updates it (no separate ask).
- Links from deployment CI/CD docs, installer READMEs, and Ubuntu lab follow-ups to the changelog.
- **EyeNet host tray** (`deployment/tray/`): Go systray for Windows (WSL) and Ubuntu; installers download from GitHub Releases tag `v${VERSION}`.
- Lab machines inventory: `docs/deployment/lab-machines.md`; Stage 2 SSH-safe scripts; release manifest Mode D; operator CI/CD guide.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG` defaults: **2.25.81 → 2.25.82**.
- `docs/deployment/platform-release-cicd.md`: changelog is mandatory on meaningful Stage 1; three-step wording (code → images → install); tray publish manual.
- Authority admin UI rebuilt as laconic mobile-first shell (Home / People / Licences / Me).

### Fixed

- Node Alpine `netifaces` build; communications/orchestrator/vmeta `/app/logs`; vmeta protected deps (`httpx`/`asyncpg`/`PyJWT`/`libgl1`); discovery reregister via compose DNS; communications `email-validator`.

### Notes

- GHCR images published for **2.25.82**; Windows tray on Release `v2.25.82`.
- Product fixes from the `2.25.81` Stage 1 push (cameras disconnect, frontend disconnect UX, communications/vmeta packaging, shared reregister) ship under this pin once Stage 2 published GHCR tags for `2.25.82`.

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
