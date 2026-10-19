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

## [2.25.103] — 2026-10-19

### Fixed

- Instant-detection persist on existing labs: schema pack `050_individuals_instant_detection_columns.sql` adds `individuals.total_appearances`, `first_seen`, `last_seen`, and `person_objects`. `schema/verify.sh` fails if any of those columns are missing. Without them, a later sighting of a known person returns persist-batch 500 and rolls back the whole cycle.
- Instant-detection Redis batch no longer replays cycles older than 120s after persist outages (`INSTANT_DETECTION_BATCH_MAX_AGE_SECONDS`, default 120). Queues are capped at 30 items (`INSTANT_DETECTION_BATCH_MAX_LEN`). Over-age heads are dropped before flush and after failed persist instead of retrying forever.
- Persist-batch skips ghost `mvr_person_uuid` values missing from `mvr_people` (avoids FK 500 on `individual_mvr_mapping`) and ensures `tracking_sessions` exists before inserts.
- `identify-face` only returns UUIDs that exist in `mvr_people`; ghost gallery hits fall through to create/unmatched.
- DeepFace uses baked image weights: link `$DEEPFACE_HOME/.deepface/weights` → `$DEEPFACE_HOME/weights` (stops nested re-download / `.part` stalls).
- Vision compose sets `MODELS_SERVICE_URL=http://ppl-meta-models:8013` so artifact fetch is not `localhost:8013` in-container.
- Schema pack `051_media_processing_status_last_updated_trigger.sql`: `media_processing_status` UPDATE trigger writes `last_updated` (not missing `updated_at`).

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.102 → 2.25.103**.
- Stage 1 is not done while CHANGELOG Notes defer a missing column the shipped code writes. The column belongs in the schema pack and in `schema/verify.sh` in that same push.
- Stage 3 lab notes must include `schema/verify.sh` output. A compose pull whose image digests match is not a finished install.

### Notes

- Affects `ppl-meta-cameras`, `ppl-meta-vision`, `ppl-meta-vmeta` (plus installer schema pack / compose). Mode D: rebuild those three; retag-forward the other nine from `2.25.102`.
- Do not finalize `release-manifest.yml` digests until Stage 2.

## [2.25.102] — 2026-10-18

### Added

- Presence ↔ HubSpot CRM connector: Service Key in Presence Settings; HubSpot → People Profiles import (`external_ref` = contact id); real-time grant Notes + `last_presence_*` contact properties.
- Presence authenticator enroll/verify APIs for EyeNet Authenticator (gateway proxy timeout 90s for `/authenticator/` paths).

### Fixed

- Flutter web login session survives hard refresh (auth restore no longer races to `/login`).
- User-visible MVR matching scores show three decimal places in views/templates (stored scores and match logic unchanged).

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.101 → 2.25.102**.

### Notes

- Affects `ppl-meta-presence`, `ppl-meta-frontend`, `ppl-meta-media`, `ppl-meta-gateway`. Mode D: rebuild those four; retag-forward the other eight from `2.25.101`.
- Operator wiki: HubSpot Service Key setup under Presence and attendance (published to wiki.eyenet-vision.com).
- GHCR images published for **2.25.102** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): rebuilt presence `358fd9ab2ddd…`, frontend `62b45fcb4dd7…`, media `7f3debe3866c…`, gateway `0b405f9c4bd7…`; retagged the other eight from `2.25.101`. Manifest finalized 2026-10-18.
- Stage 3 on `lab-work-dual-64g` (`eyenet-demo` @ `100.101.128.40`) — 2026-10-18; compose pull/recreate to `:2.25.102`; cleared local `authenticator-hotfix` presence image pin; presence/gw/ui 200; HubSpot + authenticator routes **401** unauth.

## [2.25.101] — 2026-10-16

### Fixed

- Media frame extraction: internal service token (nil system UUID) can fetch video frames for MVR face-crop enrichment (was 403 after access-check bypass).
- Vision route contamination: infer FPS from route timestamps so low-FPS edge recordings are not dropped as sparse tracks.
- Cameras / frontend: Record no longer auto-starts instant detection; ID is only via the eye control. Edge cameras get a reliable Record path (EDGE type + worker wait).

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.100 → 2.25.101**.

### Notes

- GHCR images published for **2.25.101** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): rebuilt media `e930d882…`, vision-protected `06d7cdd3…`, cameras `e28ebabe…`, frontend `b9117a5c…`; retagged the other eight from `2.25.100`. Manifest finalized 2026-10-16.
- Stage 3 on `lab-work-dual-64g` (`eyenet-demo` @ `192.168.9.13`): compose pull/recreate to `:2.25.101`; ui/gw/media 200 (2026-10-16).
- Edge camera app on RPi is outside Stage 2 (manual ship); platform images above are required for Record → faces → Details/MVR.

## [2.25.100] — 2026-10-13

### Fixed

- Individual groups: `get_group_members` now returns stored `group_member_number` (outer SELECT had dropped the column, so the UI fell back to newest-first list index).
- Individual groups: existing membership numbers rebackfilled oldest-first (first join = Member 01) via schema `024_renumber_group_members_oldest_first.sql`.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.99 → 2.25.100**.
- Schema pack includes `024_renumber_group_members_oldest_first.sql`; greenfield `023` backfill is oldest-first.

### Notes

- GHCR images published for **2.25.100** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): thin vmeta-protected on 2.25.99 + SELECT fix `3afa092bc2af…`; retagged the other eleven from `2.25.99`. Manifest finalized 2026-10-14.
- Stage 3 on `lab-work-dual-64g` (`eyenet-demo` @ `192.168.9.13` / `100.101.128.40`): compose pull/recreate to `:2.25.100`; schema pack through `034_024_renumber_group_members_oldest_first.sql`; ui/gw 200 (2026-10-14).
- Stage 3 must apply schema pack (024) so labs that never ran the hotfix get chronological numbers.

## [2.25.99] — 2026-10-13

### Fixed

- Individual groups: membership numbers (`Group Member 01`, `02`, …) stay stable across add/remove; deleted numbers are reserved for the same MVR uuid only.
- Individual groups (private): link-to-people and remove are allowed only when the caller can access that member’s source media (same ACL as the face thumbnail).

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.98 → 2.25.99**.
- Schema pack includes `023_stable_group_member_numbers.sql` (`member_number` + reservations).

### Notes

- Affects `ppl-meta-vmeta`, `ppl-meta-gateway`, `ppl-meta-presence`, `ppl-meta-frontend`. Rebuild those four; Mode D retag-forward the other eight from `2.25.98`.
- Also clears any remaining lab docker-cp overlays for the signup form→JSON path (source already on `main` since 2.25.95).
- GHCR images published for **2.25.99** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): rebuilt vmeta-protected `5ebe506f8f0c…`, gateway `55ff36d242f9…`, presence `6250b5480e76…`, frontend `b68e70251e39…`; retagged the other eight from `2.25.98`. Manifest finalized 2026-10-13.
- Stage 3 on `lab-work-dual-64g` (`eyenet-demo` @ `192.168.9.13` / `100.101.128.40`): compose pull/recreate to `:2.25.99`; schema pack applied through `033_023_stable_group_member_numbers.sql`; ui/gw 200 (2026-10-13).

## [2.25.98] — 2026-10-13

### Added

- Digital Signage automation action: optional **second playlist** and **duration (seconds)**. Plays the first playlist for the duration (default **10s** if duration omitted), then switches to the second playlist.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.97 → 2.25.98**.

### Notes

- Affects `ppl-meta-media` (delayed second `START`) and `ppl-meta-frontend` (action form). Existing actions without a second playlist keep prior permanent first-playlist behavior.
- GHCR images published for **2.25.98** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): rebuilt media `03da47c3b9b0…`, frontend `e5cfadcca42e…`; retagged the other ten from `2.25.97`. Manifest finalized 2026-10-13.
- Stage 3 on `lab-work-dual-64g` (`eyenet-demo` @ `192.168.9.13` / `100.101.128.40`): compose pull/recreate to `:2.25.98`; digests match manifest (2026-10-13).


## [2.25.97] — 2026-10-13

### Added

- Route-based face contamination filter: hard-drop scattered / blink false-positive person tracks before MVR creation (longest consecutive run + occupancy on route data).
- Temporal max-gap when linking face detections to tracks (Vision) and IoU+time grouping on Orchestrator video regroup path.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.96 → 2.25.97**.

### Notes

- Affects bulk / recording person-objects path (`ppl-meta-vision`, `ppl-meta-orchestrator`). Instant detection keeps temporal gap but does not hard-drop short cycles.
- GHCR images published for **2.25.97** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): rebuilt orchestrator `09279411…`, vision-protected `fa842c74…`; retagged the other ten from `2.25.96`. Manifest finalized 2026-10-13.
- Stage 3 on `lab-work-dual-64g` (`eyenet-demo` @ `192.168.9.13` / `100.101.128.40`): compose pull/recreate to `:2.25.97`; digests match manifest (2026-10-13).

## [2.25.96] — 2026-10-12

### Added

- RTSP cameras: optional **substream path** (e.g. `/stream2`) for live view and instant detection; main path stays the recording stream. Single worker reconnects to main on record start and back to substream on stop.
- VMeta image bake-in of DeepFace weights (`facenet512`, age, gender) so first face does not download from GitHub after install.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.95 → 2.25.96**.
- VMeta compose budget: `mem_limit` **5g** / `mem_reservation` **3g** (was 3g / 2g); Windows WSL guidance **14 GB** to fit Facenet + age/gender.

### Fixed

- Authority invitation accept: clear any prior admin session, auto-login the invitee after password set, and surface API validation errors as readable messages (no more opaque admin-plane toasts).

### Notes

- GHCR images published for **2.25.96** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): rebuilt cameras `9e4fd04f…`, frontend `9db3d148…`, vmeta-protected `6b2e9727…` (Facenet bake; size-gate fix `222bcd4`); retagged the other nine from `2.25.95`. Manifest finalized 2026-10-13.
- Stage 3 on `lab-work-dual-64g` (`eyenet-demo` @ `192.168.9.13` / `100.101.128.40`): compose pull/recreate to `:2.25.96`; VMeta mem 5g/3g; digests match manifest (2026-10-13).
- Known lab gap (not in this pin): VMeta persist can still 500 if DB `individuals` lacks `total_appearances` / `last_seen` vs code — separate schema follow-up.

---

## [2.25.95] — 2026-10-12

### Notes

- GHCR images published for **2.25.95** (Mode D on `lab-work-dual-64g` / `eyenet-demo`): rebuilt node `0e253bf9…`, gateway `37811045…`, frontend `0ce6a469…` from `054e0932`; retagged the other nine from `2.25.94`. Stage 3 on `eyenet-demo` @ `192.168.9.13` / `100.101.128.40` + Mac IDE local Python/Flutter (2026-10-12).

### Fixed

- Mobile camera login over Tailscale: authenticate via gateway `:8080` (avoids node `TrustedHost` `Invalid host header` on `:8001`).
- Gateway converts Flutter signup `application/x-www-form-urlencoded` → JSON for Node `/users/register`.
- Frontend register posts JSON `UserCreate` (not form-urlencoded).
- Node validation error handler JSON-serializes `bytes` bodies (no 500 on bad form posts).
- Gateway / node / MVR worker resolve `127.0.0.1` service URLs when not running in Docker (Mac “Start All Local Python Services”).
- Cameras UI: narrow-screen master/detail navigation + deep-link `/cameras/:id` back to list.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.94 → 2.25.95**.
- Ubuntu installer tray autostart: use install-dir reregister script and quoted Exec paths.
- Ops: `artifacts/lab-allow-tailscale-hosts.sh` keeps LAN `ADVERTISE_HOST` and adds Tailscale IP to `ALLOWED_HOSTS`.

---

## [2.25.94] — 2026-10-01

### Notes

- GHCR images published for **2.25.94** (Mode D on `lab-work-dual-64g`): rebuilt media `2e2d4eef…`, gateway `4086453a…`, frontend `6c84f576…` from `cca8fb38`; retagged the other nine from `2.25.93`. Stage 3 on `lab-work-dual-64g` @ `192.168.9.13` (2026-10-01).

### Added

- Signage **rich media message** overlays: HTML templates (Signage → Messages) with optional media/sound, non-blocking player overlay (`show_rich_message` / `dismiss_rich_message`), and automation action type `signage_rich_message`.
- Rich-message template title/message support fire-time magic tags (`{trigger_name}`, `{reason}`, `{match_reason}`, `{similarity_score}`, `{matched_member_name}`, …) like other actions.
- Schema pack `050_add_signage_rich_message_templates.sql` for `signage_rich_message_templates`.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.93 → 2.25.94**.
- Gateway proxies `/api/v1/signage/rich-messages` CRUD to media.

---

## [2.25.93] — 2026-09-28

### Notes

- GHCR images published for **2.25.93** (Mode D on `lab-work-dual-64g`): rebuilt
  communications `4fec9dbe…` and frontend `dd546e4c…` from `b7b06437`; retagged
  the other ten from `2.25.92`. Stage 3 on `lab-work-dual-64g` @ `192.168.1.90` /
  `100.101.128.40` (2026-09-28).

### Added

- Triggers Analytics: filter communication logs by one or more People Profile
  names (search widget, then chips; OR match on payload/content/subject).

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.92 → 2.25.93**.

---

## [2.25.92] — 2026-09-28

### Notes

- GHCR images published for **2.25.92** (Mode D on `lab-work-dual-64g`): rebuilt presence
  `d481e52e…` and media `1b400a35…` from `9d8d80d8`; retagged the other ten from `2.25.91`.
  Stage 3 on `lab-work-dual-64g` @ `192.168.1.90` / `100.101.128.40` (2026-09-28).

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.91 → 2.25.92**.

### Fixed

- Presence: add internal `GET /api/v1/presence/internal/people-profiles/lookup` for the media match pipeline (no end-user JWT).
- Media: call that internal PPP lookup so trigger/action logs can include People names such as **Nick** (previously 401 on the authenticated lookup left only "Group Member 02").

---

## [2.25.91] — 2026-09-28

### Notes

- GHCR images published for **2.25.91** (Mode D on `lab-work-dual-64g`): rebuilt media
  `c8e7cc7f…` and frontend `b0709dd2…` from `054dea62`; retagged the other ten from `2.25.90`.
  Stage 3 on `lab-work-dual-64g` @ `192.168.1.90` / `100.101.128.40` (2026-09-28).

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.90 → 2.25.91**.

### Fixed

- Media trigger/action logs: after a `ppl_match` / `vprofile_match`, look up the Presence People Profile linked to the matched member and prefer `ppp.name` for `{matched_member_name}`, match reason, and audit payloads (falls back to MVR plain name). Also append match reason for `vprofile_match` when the action message has no template vars.
- Frontend Triggers tab: show People / `existing_member_name` on latest match instead of only legacy `member_name` / `member_uuid` keys.

---

## [2.25.90] — 2026-09-27

### Notes

- GHCR images published for **2.25.90** (Mode D on `lab-work-dual-64g`): rebuilt frontend
  `d55e6440…` from `8c0c203d`; retagged the other eleven services from `2.25.89`.
  Stage 3 on `lab-work-dual-64g` @ `192.168.1.90` / `100.101.128.40` (2026-09-27).

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.89 → 2.25.90**.

### Fixed

- Frontend mobile Connect button: do not treat a stale WebSocket `connected` event as still connected after Disconnect (list status from live frame activity is authoritative).
- Frontend mobile Connect toggle: when the phone is already sending frames, tap Disconnect instead of re-ensure Connect (re-ensure was clearing the disconnect hold and looked like “won’t disconnect”). LEASE OPEN without frames still uses short-tap re-ensure / long-press cancel.
- Mobile camera Stop stream: notify platform `/disconnect` so the camera card flips off immediately; stop teardown no longer clears lease flags before the stop path runs.

---

## [2.25.89] — 2026-09-27

### Notes

- GHCR images republished for **2.25.89** (`b50e0ffa` / follow-up `e3e54e88`) Mode D on `lab-work-dual-64g`:
  rebuilt node/cameras/media/orchestrator/communications/presence/models/vision/vmeta;
  retagged gateway/discovery/frontend from `2.25.88`. Models `00e33bb1…`,
  orchestrator `e0fd8418…` after sqlalchemy `<2.1` pin. Manifest finalized.
  Stage 3 on `lab-work-dual-64g` @ `192.168.1.90` / `100.101.128.40` (2026-09-27):
  discovery registry self-populates after recreate. Node `ADVERTISE_HOST`
  registration follow-up keeps node healthy for mobile setup.

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.88 → 2.25.89**.

### Fixed

- Service discovery self-registration after restart: vendor gateway-style `shared.service_discovery` into node, cameras, media, orchestrator, communications, vision, presence, vmeta, and models (plus `PYTHONPATH`), so `/network` no longer shows only gateway when discovery’s in-memory registry is wiped on recreate.
- Models + orchestrator: pin `sqlalchemy` to `>=2.0.x,<2.1` so rebuilds keep `psycopg2` (SQLAlchemy 2.1 defaults to `psycopg` v3 and crashed startup).
- Orchestrator lifespan: remove nested `import os` that unbound the module-level `os` when DB init failed early.
- Node discovery registration: prefer `ADVERTISE_HOST` over Docker bridge IP so discovery health checks no longer get TrustedHost `400 Invalid host header` and prune node (mobile setup “Node service not found”).
- Node safeguard exempt paths: include trailing-slash `/health/` and `/api/v1/health/`.

---

## [2.25.88] — 2026-09-27

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.87 → 2.25.88**.
- Mobile camera app: named **Stream Profile** in Camera Settings (`lowBandwidth` / `balanced` / `highQuality`) with real upload pacing + JPEG quality (APK rebuild required; not a GHCR image).

### Fixed

- Cameras mobile FPS calibration: floor lowered so slow phones (~2–4 fps JPEG upload) lock the **measured** rate instead of falling back to declared 30.
- Cameras session recording: if worker `measured_fps` is not ready yet, prefer arrival-**calibrated** FPS for mobile before the hard 30 fallback.

---

## [2.25.87] — 2026-09-27

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.86 → 2.25.87**.

### Fixed

- Vmeta hierarchical MVR merge preview: Cython runtime `TypeError` (`Expected dict, got collections.defaultdict`) that aborted auto-merge during media preview search and could leave Details/MVR people inconsistent after idle refresh.

---

## [2.25.86] — 2026-09-26

### Changed

- Platform pin `VERSION` / installer `RELEASE_TAG`: **2.25.85 → 2.25.86**.
- Presence Settings: replace match-group reserve UI with a **Video readiness** report (active `ppl_match` / `vprofile_match` + camera + group + Presence action).
- Presence Actions: **Video Match** and **Scan Owner QR + Video** stay disabled until readiness is green; QR-only paths unchanged.
- Presence video sessions no longer require the Settings group reserve / private auto-provision path when a qualifying platform trigger is ready.

### Added

- Presence: `GET /api/v1/presence/video-readiness` readiness scoring endpoint.

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
