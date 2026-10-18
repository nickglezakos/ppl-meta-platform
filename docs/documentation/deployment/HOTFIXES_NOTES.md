# Hotfixes notes

Living tracker for **lab hotfixes** that are not yet a proper release.

A lab that “works” after `docker cp`, an in-container edit, a compose override, or a one-off `.env` change is **debug**, not a release. Other labs must not be patched that way.

**Release path:** Stage 1 (source on `main` + CHANGELOG) → Stage 2 (GHCR images) → Stage 3 (lab pull / install). See [`docs/deployment/platform-release-cicd.md`](../../../docs/deployment/platform-release-cicd.md).

| Status | Meaning |
|--------|---------|
| **Pending** | Applied on a lab (or source edited locally) but Stage 1–3 not finished |
| **Completed** | Stage 1 + Stage 2 + Stage 3 done; GHCR replaced the hotfix |

When a release finishes Stage 3, move the entry from **Pending** to **Completed** and note the VERSION / image digests / lab.

---

## Pending

### 2026-10-18 — HubSpot ↔ Presence CRM (eyenet-demo)
- **Status:** Pending (lab docker-cp hotfix only; not in GHCR release)
- **Lab:** `lab-work-dual-64g` / `eyenet-demo` @ `100.101.128.40`
- **Script:** `artifacts/lab-hotfix-hubspot-crm.sh`
- **Summary:** Presence Settings HubSpot card; contact import → PPP `external_ref`; real-time grant Notes + `last_presence_*` properties. Applied on top of `eyenet-local/ppl-meta-presence:authenticator-hotfix` + frontend `main.dart.js` overlay.
- **Files:**
  - `ppl-meta-presence`: `hubspot_crm.py`, `presence_models.py`, `presence_service.py`, `presence_routes.py`
  - `ppl-meta-frontend`: Presence Settings HubSpot UI + API client/models
- **Verify:** Hard-refresh http://100.101.128.40:3000/ → Presence → Settings → **HubSpot CRM**. Unauth `GET /api/v1/presence/installations/current/crm/hubspot` → **401** (not 404).
- **Next:** Stage 1 commit on `main` → Stage 2 rebuild presence + frontend → Stage 3 lab pull

### 2026-10-18 — Web login session survives refresh (eyenet-demo)
- **Status:** Pending (Stage 1 source on `main`; not in GHCR release)
- **Summary:** Flutter web no longer races to `/login` before persisted JWT restore finishes. Auth starts in `restoring`; router defers login redirect; profile 401 does not wipe a silently refreshed token.
- **Files:**
  - `ppl-meta-frontend`: `auth_provider.dart`, `auth_service.dart`, `app_router.dart`, `api_client.dart`
- **Verify:** Sign in on eyenet-demo web → hard refresh (same origin) → stay on app, not login.
- **Next:** Stage 2 rebuild frontend → Stage 3 lab pull / recreate ui

### 2026-10-18 — MVR matching score display: 3 decimals (views only)
- **Status:** Pending (source edited locally; not in GHCR release)
- **Summary:** Every user-visible MVR matching score shows `0.xxx` (3 decimals) instead of full floats or 1-decimal percents. Stored `similarity_score`, thresholds, and match logic unchanged.
- **Files:**
  - `ppl-meta-frontend`: `cross_video_analysis_models.dart` (`formattedSimilarity`), `person_objects_detail_screen.dart`, `triggers_tab.dart`, `duplicate_detection_dialog.dart`
  - `ppl-meta-media`: `routes/triggers.py`, `services/redis_subscriber.py` (match-reason + `{similarity_score}` template text only)
  - `ppl-meta-authenticator`: `presence_home_screen.dart` verify-error score text (tree currently untracked in this workspace)
- **Next:** Stage 1 commit on `main` → Stage 2 rebuild frontend + media → Stage 3 lab pull

### 2026-10-18 — Presence authenticator enroll/verify APIs (EyeNet Authenticator app)
- **Status:** Pending (lab docker image hotfix only; not in GHCR release)
- **Lab:** `lab-work-dual-64g` / `eyenet-demo` @ `100.101.128.40`
- **Image:** `eyenet-local/ppl-meta-presence:authenticator-hotfix` (from `:2.25.101` + authenticator routes + `python-multipart` + `VMETA_SERVICE_URL`)
- **Compose:** `~/eyenet-platform/docker-compose.override.yml` pins presence image + `VMETA_SERVICE_URL=http://ppl-meta-vmeta:8008`
- **Verify:** `curl http://100.101.128.40:8080/api/v1/presence/authenticator/enrollment` → **401** (not 404)
- **Next:** Stage 1/2/3 proper Presence (+ gateway timeout) release; remove local image pin

### Follow-up — Full clean rebuild of vmeta-protected (replace thin 2.25.100)
- **Status:** Pending (product OK on lab; image lineage is a thin overlay)
- **Why:** Stage 2 for **2.25.100** could not push a full `Dockerfile.protected` rebuild to GHCR (hung on large layer `db07833fef22` / ~DeepFace weights blob). Workaround: `FROM …:2.25.99` + `COPY individual_groups_manager.py` → digest `3afa092bc2af…`.
- **Next Stage 2 (vmeta):** Do a **full clean** `stage2_one.sh vmeta` (or equivalent protected build+push) on a later pin so GHCR `:VERSION` is a normal protected image, not base+patch. If full push hangs again, fix GHCR upload path first (serial uploads / network / alternate publish), then rebuild — do not keep stacking thin layers.
- **Verify after clean rebuild:** manifest digest for `ppl-meta-vmeta-protected` changes; image history is a normal multi-stage protected build; `get_group_members` still selects `gm.member_number` / `gm.added_by` in the outer query.

---

## Completed

### 2026-10-14 — Group member numbers oldest-first + API field leak
- **Status:** Completed (see Pending follow-up: replace thin vmeta with full clean rebuild)
- **VERSION / pin:** `2.25.100` (source Stage 1 `3cc18a7a`, manifest `44016433`)
- **Stage 1:** `3cc18a7a` (feature) + `44016433` (release-manifest)
- **Stage 2:** Mode D on `lab-work-dual-64g` — **thin** vmeta-protected on 2.25.99 (`3afa092bc2af…`) after full rebuild push hung; retagged eleven from `2.25.99`
- **Stage 3:** `lab-work-dual-64g` (`eyenet-demo` @ `100.101.128.40`) — 2026-10-14; compose to `:2.25.100`; schema `034_024_renumber_group_members_oldest_first.sql`
- **Summary:** Oldest join = Member 01; `get_group_members` returns stored `group_member_number`.

### 2026-10-13 — Individual group MVR membership numbers + private member manage ACL
- **Status:** Completed
- **VERSION / pin:** `2.25.99` (source Stage 1 `a3a808dc`, manifest `f08aba91`)
- **Stage 1:** `a3a808dc` (feature) + `f08aba91` (release-manifest)
- **Stage 2:** Mode D on `lab-work-dual-64g` — rebuilt vmeta-protected `5ebe506f8f0c…`, gateway `55ff36d242f9…`, presence `6250b5480e76…`, frontend `b68e70251e39…`; retagged the other eight from `2.25.98`
- **Stage 3:** `lab-work-dual-64g` (`eyenet-demo` @ `192.168.9.13` / `100.101.128.40`) — 2026-10-13; compose pull/recreate to `:2.25.99`; schema `033_023_stable_group_member_numbers.sql` applied (`member_number` + reservations)
- **Summary:** Stable membership ordinals; private-group link/delete gated on media ACL (same as face thumbnail). Replaces lab docker-cp hotfix path. Note: initial 023 backfill was newest-first; corrected on lab by pending SQL 024.

### 2026-10-07 — Users register form-urlencoded → JSON (signup 500)
- **Status:** Completed (source since 2.25.95; lab overlays cleared by Stage 3 of **2.25.99**)
- **VERSION / pin:** `2.25.99` (gateway/frontend recreate; node already carried `_json_safe` via retag)
- **Stage 1:** originally `054e0932` (2.25.95)
- **Stage 3:** `lab-work-dual-64g` @ `192.168.9.13` — 2026-10-13 with pin 2.25.99
- **Summary:** Gateway form→JSON for signup; node validation errors stay serializable; frontend registers with JSON.

### 2026-10-01 — Signage rich media message overlay
- **Status:** Completed
- **VERSION / pin:** `2.25.94` (source Stage 1 `cca8fb38`, manifest `d6f75017`)
- **Stage 1:** `cca8fb38` (feature) + `d6f75017` (release-manifest)
- **Stage 2:** Mode D on `lab-work-dual-64g` — rebuilt media `2e2d4eef…`, gateway `4086453a…`, frontend `6c84f576…`; retagged the other nine from `2.25.93`
- **Stage 3:** `lab-work-dual-64g` (`eyenet-demo` @ `192.168.9.13`) — 2026-10-01; in-place compose recreate to `:2.25.94`; schema pack through `050_add_signage_rich_message_templates.sql` verified
- **Summary:** Non-blocking rich-message overlays (Signage → Messages), `signage_rich_message` automation action, fire-time `{magic tags}`, gateway CRUD proxy. Replaces lab docker-cp hotfix.

### 2026-09-26 — Individual Groups People-link icon + PPP select-then-link UX
- **Status:** Completed
- **VERSION / pin:** `2.25.83` (source `7282168f`)
- **Stage 1:** `7282168f`
- **Stage 2:** frontend `f9b2184d…` (tags `2.25.83` / `2.25.83-7282168`) on `lab-work-dual-64g`
- **Stage 3:** `lab-work-dual-64g` @ `10.171.48.228:3000` — 2026-09-26; compose pull/recreate replaced docker-cp hotfix; running digest matches GHCR
- **Files:** `individual_groups_screen.dart`, `people_profile_picker.dart`, `individual_group_detail_screen.dart`
- **Summary:** `/individual-groups` member cards get a top-left link icon (same height as trash); People Profile picker uses select-then-Link (one choice per submission).

### 2026-09-23 — Media signage sync cannot reach discovery (`localhost:8006`)
- **Status:** Completed
- **VERSION / pin:** `2.25.83` (source `f5816b45`)
- **Stage 1:** `f5816b45`
- **Stage 2:** media `d4635f9a…` (tag `2.25.83-f5816b4`) on `lab-work-dual-64g`
- **Stage 3:** `lab-work-dual-64g` @ `10.171.48.228` — 2026-09-23; compose pull/recreate replaced docker-cp hotfix; running digest matches GHCR
- **Summary:** Media used hardcoded `localhost:8006` for device lookup inside the container. Now uses `DISCOVERY_SERVICE_URL` (`http://ppl-meta-discovery:8006`).

### 2026-09-23 — Frontend batch upload stops after the first file
- **Status:** Completed
- **VERSION / pin:** `2.25.83` (source `f5816b45`)
- **Stage 1:** `f5816b45`
- **Stage 2:** frontend `8279d972…` (tag `2.25.83-f5816b4`) on `lab-work-dual-64g`
- **Stage 3:** `lab-work-dual-64g` @ `10.171.48.228:3000` — 2026-09-23; compose pull/recreate; running digest matches GHCR
- **Summary:** Multi-file `/upload` no longer throws `ConcurrentModificationError` after the first success (walk a snapshot; clear uploading when the batch ends).

### 2026-09-23 — Signage simple player (local enroll + sync soak)
- **Status:** Completed (APK path)
- **VERSION / pin:** `2.25.83` (source `f5816b45`)
- **Stage 1:** `f5816b45`
- **Stage 2:** N/A (APK; not a GHCR service image)
- **Stage 3:** APK rebuilt and installed on SM-T510 — 2026-09-23; local discovery enroll (no enrollment token) + playlist sync verified against `lab-work-dual-64g` @ `10.171.48.228`
- **Summary:** Setup defaults to tokenless local `device-enroll`; VPN one-time token only when joining the mesh. Playlist sync to the tablet worked after media discovery URL fix.

### 2026-09-23 — Mobile camera APK (crash fix + Stop stream)
- **Status:** Completed
- **VERSION / pin:** `2.25.83` (source `dd464478`)
- **Stage 1:** `dd464478`
- **Stage 2:** N/A (APK)
- **Stage 3:** APK rebuilt and installed on device — 2026-09-23
- **Summary:** `availableCameras()` init (no TrebleDroid probe crash) + persistent Stop stream UI.

### 2026-09-23 — Gateway/Discovery CORS RFC1918 + frontend mobile lease UI
- **Status:** Completed
- **VERSION / pin:** `2.25.83`
- **Stage 1:** `dd464478`
- **Stage 2:** gateway `b01e6b22…`, discovery `7ced8041…`, frontend `f9e2aacc…` (tags `2.25.83` / `2.25.83-dd46447`)
- **Stage 3:** `lab-work-dual-64g` @ `10.171.48.228` — 2026-09-23; OPTIONS CORS 200 for `http://10.171.48.228:3000`
- **Summary:** Replaced gateway docker-cp hotfix; 10.x LAN UI no longer false-bootstraps; mobile Connect lease chip in GHCR frontend.
