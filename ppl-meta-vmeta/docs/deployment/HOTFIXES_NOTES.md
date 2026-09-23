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

## How to add an entry

Copy this block under **Pending**:

```markdown
### YYYY-MM-DD — short title
- **Status:** Pending
- **Lab(s):** e.g. `lab-work-dual-64g` @ `10.171.48.228`
- **Service(s):** e.g. `ppl-meta-gateway`
- **Symptom:** what broke
- **Hotfix applied:** what was changed on the lab (`docker cp`, file, restart, etc.)
- **Source change:** monorepo path(s) that must land in Stage 1
- **Stage 1:** not started | in progress | done (`commit`)
- **Stage 2:** not started | in progress | done (image digest)
- **Stage 3:** not started | in progress | done (lab + pull time)
- **Notes:** anything else
```

---

## Pending

### 2026-09-23 — Mobile camera: crash during “comprehensive camera detection”
- **Status:** Pending (Stage 1 in this release)
- **Lab(s):** TrebleDroid with GApps (device IP `10.171.48.86`) vs platform `10.171.48.228`
- **Service(s):** `ppl_meta_mobile_camera` (APK — not GHCR)
- **Symptom:** App dies mid-init after login/register during front-camera orientation probe.
- **Source change:** `ppl_meta_mobile_camera/lib/core/services/camera_service.dart` (+ provider getter rename)
- **Stage 1:** in progress (this release)
- **Stage 2:** N/A (mobile APK)
- **Stage 3:** rebuild/sideload APK after Stage 1 push
- **Notes:** Also includes persistent Stop stream UI (`camera_screen.dart`, `camera_controls.dart`).

### 2026-09-23 — Gateway/Discovery CORS: allow RFC1918 `10/8` and `172.16/12`
- **Status:** Pending (Stage 1 in this release)
- **Lab(s):** `lab-work-dual-64g` @ `10.171.48.228`
- **Service(s):** `ppl-meta-gateway`, `ppl-meta-discovery`
- **Symptom:** UI flashed login → `/bootstrap` on `10.x` LAN (CORS preflight 400).
- **Hotfix applied:** Lab gateway `config.py` docker-cp (superseded by Stage 2/3).
- **Source change:** `ppl-meta-gateway/src/config.py`, `ppl-meta-discovery/src/main.py`
- **Stage 1:** in progress (this release)
- **Stage 2:** rebuild `gateway` + `discovery`
- **Stage 3:** pull on lab; drop in-container hotfix
- **Related:** Frontend mobile Connect lease chip (`camera_card.dart`, `camera_providers.dart`) — rebuild `frontend`.

---

## Completed

_None yet for this tracker. Move Pending entries here after Stage 1–3._
