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

_(none)_

---

## Completed

### 2026-10-20 — Gateway audit 429 / OPTIONS + frontend alert poller
- **Status:** Completed
- **VERSION / pin:** `2.25.104` (Stage 1 `aec06964` / docs `535985ad`; Stage 2 manifest `bec2e5ed`; Stage 3a wiki `d3b94c8c`)
- **Stage 1:** Gateway rate-limit/OPTIONS + frontend alert poller in pin `2.25.104`
- **Stage 2:** Mode D on `lab-work-win-eynetdell` — gateway `bd78deff018b…`, frontend `885b9752a71a…` (+ node/media/orchestrator/discovery/communications/vmeta/cameras/presence/models); vision retagged from `2.25.103`
- **Stage 3:** Wiki First install zips → in-place upgrade on `lab-work-dual-64g` + `lab-work-win-eynetdell`; digests match manifest; discovery 11/11; UI/gw/media 200
- **Summary:** Replaces lab docker-cp gateway hotfix and local-only frontend poller fix.

### Follow-up — Full clean rebuild of vmeta-protected (replace thin 2.25.100)
- **Status:** Completed (superseded by **2.25.103** full rebuild `3a684fa0cb23…` and **2.25.104** Mode D rebuild `75e7f374d7cb…`)
- **VERSION / pin:** `2.25.104`
- **Verify:** `ppl-meta-vmeta-protected@sha256:75e7f374d7cb…` on dual + eyenetdell

### 2026-10-18 — HubSpot CRM + authenticator APIs + login/MVR view fixes
- **Status:** Completed
- **VERSION / pin:** `2.25.102` (Stage 1 `8c45cacd`, manifest `ebe6519e`)
- **Stage 1:** HubSpot connector, authenticator enroll/verify + gateway 90s proxy, login session restore, MVR 3-decimal views; pin bump; CHANGELOG
- **Stage 2:** Mode D on `lab-work-dual-64g` — rebuilt presence `358fd9ab2ddd…`, frontend `62b45fcb4dd7…`, media `7f3debe3866c…`, gateway `0b405f9c4bd7…`; retagged eight from `2.25.101`
- **Stage 3:** `lab-work-dual-64g` (`eyenet-demo` @ `100.101.128.40`) — 2026-10-18; compose to `:2.25.102`; cleared `authenticator-hotfix` image pin (kept `VMETA_SERVICE_URL`); hubspot/authenticator **401** unauth
- **Script:** `artifacts/lab-stage2-3-hubspot-2.25.102.sh`

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
