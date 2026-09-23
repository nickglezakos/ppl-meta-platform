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

### 2026-09-23 — Mobile camera APK (crash fix + Stop stream)
- **Status:** Pending (APK only — not GHCR)
- **Service(s):** `ppl_meta_mobile_camera`
- **Stage 1:** done (`dd464478`)
- **Stage 2:** N/A
- **Stage 3:** rebuild/sideload APK on TrebleDroid / devices
- **Notes:** Source on `main`; operators must `flutter build apk` / install separately.

---

## Completed

### 2026-09-23 — Gateway/Discovery CORS RFC1918 + frontend mobile lease UI
- **Status:** Completed
- **VERSION / pin:** `2.25.83`
- **Stage 1:** `dd464478`
- **Stage 2:** gateway `b01e6b22…`, discovery `7ced8041…`, frontend `f9e2aacc…` (tags `2.25.83` / `2.25.83-dd46447`)
- **Stage 3:** `lab-work-dual-64g` @ `10.171.48.228` — 2026-09-23; OPTIONS CORS 200 for `http://10.171.48.228:3000`
- **Summary:** Replaced gateway docker-cp hotfix; 10.x LAN UI no longer false-bootstraps; mobile Connect lease chip in GHCR frontend.
