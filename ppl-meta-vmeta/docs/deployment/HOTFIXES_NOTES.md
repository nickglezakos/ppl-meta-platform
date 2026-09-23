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

### 2026-09-23 — Media signage sync cannot reach discovery (`localhost:8006`)
- **Status:** Pending Stage 3 — Stage 1 `f5816b45` + Stage 2 on `lab-work-dual-64g` (media `d4635f9a…`, tag `2.25.83-f5816b4`). Lab still needs compose pull to replace the `docker cp` hotfix.
- **Service:** `ppl-meta-media`
- **Where:** GHCR `:2.25.83` / `:2.25.83-f5816b4`; lab container may still be hotpatched until Stage 3.
- **File:** `ppl-meta-media/src/services/signage_service.py` (`_discovery_base_url`)
- **Summary:** Playlist sync returned 202 (“started”) then failed: media looked up the device at hardcoded `http://localhost:8006` inside the container (unreachable). Now uses `DISCOVERY_SERVICE_URL` (`http://ppl-meta-discovery:8006`).

### 2026-09-23 — Frontend batch upload stops after the first file
- **Status:** Pending Stage 3 — Stage 1 `f5816b45` + Stage 2 on `lab-work-dual-64g` (frontend `8279d972…`, tag `2.25.83-f5816b4`). Lab UI still needs Stage 3 pull.
- **Service:** `ppl-meta-frontend`
- **Where:** GHCR `:2.25.83` / `:2.25.83-f5816b4`; lab `@10.171.48.228:3000` until Stage 3.
- **File:** `ppl-meta-frontend/lib/widgets/device_aware_upload_widget.dart` (`_uploadFiles`)
- **Summary:** A multi-file `/upload` removed each success from `_selectedFiles` while that list was still the loop. Dart threw `ConcurrentModificationError` after the first file, so the rest of the batch never started and the Upload button stayed busy. The loop now walks a snapshot, reports a single-file failure and continues, and clears the uploading flag when the batch ends.

---

## Completed

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
