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

### 2026-10-13 — Individual group MVR membership numbers + private member manage ACL
- **Status:** Pending (Stage 1 in progress for pin **2.25.99**; Stage 2–3 next)
- **Lab:** `lab-work-dual-64g` / `eyenet-demo` @ Tailscale `100.101.128.40` (LAN `192.168.9.13`)
- **VERSION / pin:** **2.25.99** (rebuild vmeta, gateway, presence, frontend)
- **Files (source):**
  - `ppl-meta-vmeta/migrations/023_stable_group_member_numbers.sql` — persist `member_number` on `group_memberships` + `group_member_number_reservations`
  - `ppl-meta-vmeta/src/services/individual_groups_manager.py` — stable numbers; `can_manage_member` via media ACL for private groups
  - `ppl-meta-vmeta/src/api/routes/individual_groups.py` — real JWT `added_by` / `created_by`; gate remove; permissions endpoint
  - `ppl-meta-vmeta/src/models/individual_group.py` — `member_number`, `added_by`, `can_manage_member`
  - `ppl-meta-gateway/src/api/v1/router.py` — proxy member permissions
  - `ppl-meta-presence/src/api/presence_routes.py` — refuse PPP link/unlink when `can_manage_member` is false
  - `ppl-meta-frontend/lib/screens/individual_groups_screen.dart` / `individual_group_detail_screen.dart` / `people_profile_picker.dart` / models — hide link/delete when not manageable
  - `deployment/mac-lima/sync-schema-pack.sh` — pack includes `033_023_stable_group_member_numbers.sql`
- **Symptom (numbers):** With members 01 and 02, adding a new MVR made the newest **Group Member 01**; deletes also shifted labels.
- **Symptom (ACL):** In a private group, user A sees own member faces but not user B’s face (correct media ACL), yet could still **link people** / **delete** B’s member (incorrect).
- **Summary:** Persist membership ordinals; for private groups, link/delete only when the caller can access that member’s source media (same rule as the thumbnail).
- **Release next:** Stage 2 Mode D (`artifacts/lab-stage2-3-ig-acl-2.25.99.sh`) → Stage 3 → move to Completed

### 2026-10-07 — Users register form-urlencoded → JSON (signup 500)
- **Status:** Pending (source on `main` since **2.25.95**; lab may still have docker-cp overlay until Stage 3 of **2.25.99** recreates gateway/node/frontend)
- **Lab:** `lab-work-dual-64g` / `eyenet-demo` @ Tailscale `100.101.128.40` (LAN `192.168.9.13`)
- **Applied (debug):** 2026-10-07 via `artifacts/lab-hotfix-users-register-form-json.sh`
- **Files (source):** already in `main` — gateway form→JSON, node `_json_safe`, frontend JSON register
- **Release next:** Stage 3 of **2.25.99** clears overlays; then move to Completed

---

## Completed

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
