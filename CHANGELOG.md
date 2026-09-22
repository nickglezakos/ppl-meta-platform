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

- Cameras: Connect **reuses** an active mobile `stream_session_id`
  (`ensure_stream_lease`) instead of reminting — remint invalidated the phone’s
  lease and immediately 409’d frames on Connect.
- Cameras: Disconnect no longer segfaults (exit 139) / returns gateway **503**
  when worker status pub/sub hit Redis on the wrong event loop — sync Redis
  publish from workers; mobile Disconnect returns 200 before deferred queue
  teardown.
- Gateway: explicit `POST /streaming/mobile/{device_id}/stream-lease` proxy so
  phone lease mint is not a 404 behind the gateway catch-all gap.
- Cameras + mobile APK: **stream session lease** for mobile upload — Connect /
  `POST .../stream-lease` mint a `stream_session_id`; every `/frame` must carry
  it; Disconnect revokes the lease (and keeps hold). Stops the Connect/Disconnect
  race where the phone kept POSTing after Disconnect. USB/RTSP/edge unchanged.
- Mobile APK: acquire lease before upload; stop on 409 (revoked/held); idempotent
  stop across in-flight frames.
- Cameras: operator-disconnected mobile frame hold now returns **HTTP 409**
  (not 500) so the phone can stop uploading cleanly; Disconnect no longer looks
  broken while the APK keeps POSTing held frames.
- Mobile camera APK: on frame **409** (platform hold after Disconnect), stop
  backend upload and the camera image stream so the phone side matches the
  platform.
- Recording timer: reset from `startedAt` each session; `copyWith` can clear
  nullable fields so stop/start no longer keeps a stale timestamp.
- Media preview face overlay: scale boxes using detection `frame_width` /
  `frame_height` (with letterbox fit) so mobile portrait recordings are not
  treated as landscape. Also fall back to top-level Enhanced V2 face dims when
  `detection_result.faces_by_frame` omits them (common path — caused lingering
  off-center rects after the first overlay fix).
- VMeta MVR materialize: resolve Gateway via `GATEWAY_SERVICE_URL` (not
  in-container `localhost:8080`) so face-crop enrich succeeds and face→MVR
  people are created; compose sets `PPL_GATEWAY_URL` for VMeta.
- VMeta FaceNet: treat pre-cropped faces with `detector_backend=skip` and
  correctly parse bare 512-d embedding vectors — the multi-face guard was
  rejecting every materialize (`Multi-face crop: 512 faces`) so individuals
  stayed at 0 even after Gateway URL was fixed.
- Media: entrypoint chowns `/app/media` (uid 1001) then drops privileges so
  fresh Docker `media_data` volumes are writable — Stage 3 / empty volumes no
  longer regress with upload `Permission denied` and skipped face/MEDIA-VERIFY.
- Media entrypoint: set `HOME=/home/app` before `setpriv` so pip `--user`
  packages resolve (without this, uvicorn crashed with `No module named uvicorn`).
- Installers (Windows + Ubuntu): post-`compose up` call
  `ensure-media-volume-perms.sh` as belt-and-suspenders until labs pull the
  new Media image.
- Communications audit logs: store the real trigger UUID in `trigger_id`
  (from event payload) instead of the event type string `"alert"`, so the
  Triggers tab detail pane can list on-screen notification logs for that
  trigger (Analytics already showed them unfiltered).
- Frontend nginx: stop 1-year `immutable` caching of unfingerprinted
  `main.dart.js` / Flutter bootstrap / service worker so Stage 3 pulls are
  visible without waiting a year (labs kept serving a cached pre-fix UI after
  logout-after-`/triggers`).
- Media compose: set `REDIS_HOST` / `REDIS_URL` so the instant-detection trigger
  subscriber connects to compose Redis (was defaulting to `localhost` and never
  evaluating triggers).
- Media compose: set `COMMUNICATIONS_SERVICE_URL` so alert/email/webhook actions
  reach Communications (was defaulting to `localhost:8009`).
- Frontend: stop clearing the shared JWT when legacy AuthManager's localhost
  health probe fails (logout after leaving `/triggers`).
- Frontend: remove 60s alert content-dedupe that hid legitimate trigger
  notifications; trigger `cooldown_seconds` remains the rate limit.
- Schema pack `049_individual_video_appearances_instant_columns.sql`: add
  `quality_score` / `processing_method` / `source_session_uuid` / `created_at`
  so instant-detection persist-batch stops 500ing.
- Gateway (and Discovery) CORS: allow Tailscale CGNAT origins (`100.64.0.0/10`)
  so the UI at `http://<tailscale-ip>:3000` can call `:8080` (was only
  localhost / `192.168.*`; personal Tailscale login preflight failed).
- Cameras: operator Disconnect on mobile must **hold** frame ingest until
  Connect — phone kept POSTing frames and auto-resume reattached the stream
  within ~200ms (looked like Disconnect did nothing).
- Stage 2 tooling: `stage2_one.sh` requires `origin/main` + clean service
  trees (`stage2_preflight.sh`) and always rebuilds Flutter web for frontend
  (stops publishing lab-local / stale `build/web` as if it were GHCR truth).

### Notes

- No `VERSION` bump (still **2.25.83**). Stage 2 republished **`ppl-meta-cameras`**
  (`4a969d77…`, Connect lease reuse + Disconnect no-SIGSEGV) and
  **`ppl-meta-gateway`** (`1b95b5fd…`, explicit `stream-lease` route). Stage 3 on
  `lab-work-dual-64g` Ubuntu (`192.168.9.13`) pulled both and removed lab hotfix
  override images.
- Prior Stage 2 on this pin: stream-lease cameras (`065fc898…`); **`frontend`**
  (`3afac7f6…`); **`ppl-meta-vmeta-protected`** (`28dc8f0a…`).
- **Rebuild APK from `main` @ `f78d67a2`** (or later) — old APKs without
  `stream_session_id` get 409 on `/frame`.
- Frontend nginx cache fix already published (`635127bf…`); hard-refresh UI once
  if a lab still shows a pre-fix cached `main.dart.js`.
- Tray publish not required for this Stage 1.
- Process: do **not** copy container HTML/`docker cp` between labs — Stage 1 →
  Stage 2 GHCR → Stage 3 pull only.
- Fleet tracking: `docs/deployment/lab-machines.md` § Fleet status — update
  after each Stage 3. Compare **running container Image ID** + `main.dart.js`
  hash, not only the `:tag` RepoDigest.

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
