# Issue: Frontend Hardcoded Endpoints (VPN/Matrix Incompatibility) + Backend Service Outage

**Date:** 2026-07-01
**Reporter:** Investigation triggered by user report of broken frontend endpoint calls after VPN + Matrix migration.

---

## Summary

Two distinct but related problems were found:

1. **Frontend hardcoding**: Several frontend files call backend services directly on hardcoded `localhost:PORT` addresses instead of routing through the Gateway (`:8080`). This works fine when the browser and all services run on the same machine, but **breaks as soon as the app is accessed remotely over Tailscale/VPN**, because those hardcoded ports are not reachable/routed the same way the Gateway is.
2. **Backend service outage**: 4 of 13 backend services (Cameras :8005, Discovery :8006, vmeta :8008, Communications :8009) were found not running during this investigation. Root cause analysis below explains why, and why the "VPN + Matrix" task is very unlikely to be the actual cause despite the timing coincidence.

---

## Part 1: Frontend Hardcoded Endpoint Findings

### Files that bypass the Gateway and call backend services directly

| File | Hardcoded URL(s) | Issue |
|---|---|---|
| `lib/services/person_objects_api_client.dart` | Builds `:8002` (orchestrator) and `:8003` (vision) directly from the gateway host, bypassing `:8080` | Cross-video/individual analysis (used by media-preview "details") breaks remotely |
| `lib/providers/monitoring_providers.dart` | `http://localhost:8002` — comment literally says *"Direct to orchestrator, not gateway"* | Monitoring dashboard breaks remotely |
| `lib/services/recording_session_service.dart` | `http://localhost:8002/api/v1` and `http://localhost:8005/api/v1` hardcoded as class constants | Recording session management breaks remotely |
| `lib/providers/settings_providers.dart` | `http://localhost:8002/api/v1/settings/workflow...` (two occurrences) | Workflow velocity-sensitivity settings break remotely |
| `lib/presentation/screens/cameras/edge_camera_management_screen.dart` | `http://localhost:8005` (marked `// TODO: Get from config`) | Edge camera management screen breaks remotely |
| `lib/presentation/widgets/camera/edge_camera_config_dialog.dart` | Same `:8005` TODO | Edge camera config dialog breaks remotely |
| `lib/presentation/widgets/camera/edit_camera_name_dialog.dart` | Same `:8005` TODO | Camera rename breaks remotely |
| `lib/presentation/widgets/camera/add_edge_camera_dialog.dart` | Same `:8005` TODO | Adding edge camera breaks remotely |

All of the above should instead resolve their base URL from `AppConfig.instance.apiBaseUrl` (or an injected `ApiClient.baseUrl`), which already correctly resolves to the Gateway's origin for both local dev and VPN/remote access (see `lib/core/config/app_config.dart`, `_webRuntimeDefaults()`).

### Missing Gateway route: Discovery service

`ppl-meta-gateway/src/api/v1/router.py` defines a `SERVICES` dict used for proxying: it includes `node, media, orchestrator, vision, cameras, vmeta, communications` (and presence), **but has no `discovery` entry and no `/api/v1/services` proxy route**. The frontend's `DiscoveryServiceClient` correctly targets the Gateway per the existing endpoint-fix effort, but there is nothing on the Gateway side to receive `/api/v1/services` and forward it to the Discovery service (`:8006`). This produces a 404 regardless of VPN/local mode.

### Files with hardcoded ports confirmed to be dead code (not wired into the app)
These still contain old hardcoded ports but were not traced into any active route/import at time of writing — recommend confirming via `flutter analyze`/import search before deleting, but they are **not currently part of the fix**:
- `lib/widgets/triggers_tab_old_backup.dart`
- `lib/services/workflow_api_client_backup.dart`
- `lib/widgets/face_detection_test_page.dart`
- `lib/ARCHIVE_CAMERA_OLD_20241222/*`
- `lib/core/api/dynamic_api_client.dart.backup`
- `lib/core/config/dynamic_app_config.dart.backup`

---

## Part 2: Why Are 4 Backend Services Down? (Root Cause Analysis)

### User's working theory
"I started all local python services, ran the health check via nginx proxy — it reported all OK. Then I ran the new 'Start VPN + Matrix Only (Layered)' task, which obviously caused the issue."

### Investigation findings

**1. The VPN+Matrix task cannot structurally cause this.**
Reading the full command for `🔐 Start VPN + Matrix Only (Layered)` in `.vscode/tasks.json` line 934: it only touches PostgreSQL, Headscale (:8081), Tailscale enrollment, Authority (:8010), and Matrix (:8015). It contains **zero** references to ports 8005, 8006, 8008, or 8009 — no `pkill`, `lsof -ti`, or restart logic targeting Cameras/Discovery/vmeta/Communications. It cannot have killed them directly.

**2. The "Health Check via Nginx Proxy" task has a blind spot.**
Reading its command (`.vscode/tasks.json` line 7): it only checks Gateway, Nginx itself, and `/health/node`, `/health/media`, `/health/orchestrator`, `/health/cameras`. **It never checks Discovery (8006), vmeta (8008), or Communications (8009) at all.** So "all OK" only vouches for Cameras among the 4 services later found down — Discovery/vmeta/Communications could have already been silently unhealthy (or never started) without this check ever detecting it.

**3. Live process inspection shows something more specific than "the VPN task killed them."**
At time of investigation:
```
port 8000 (Media):          200 OK
port 8001 (Node):           307 (OK, redirect)
port 8002 (Orchestrator):   200 OK
port 8003 (Vision):         200 OK
port 8005 (Cameras):        DOWN (no listener)
port 8006 (Discovery):      DOWN (no listener)
port 8008 (vmeta):          DOWN (no listener)
port 8009 (Communications): DOWN (no listener)
port 8010 (Authority):      200 OK
port 8011 (Presence):       200 OK
port 8015 (Matrix):         200 OK
port 8080 (Gateway):        200 OK
```
`ps aux` confirms the **parent shell process for the original "Start All Local Python Services" task (PID 89481) is still alive**, along with most of its child service processes (Node, Media, Gateway, Orchestrator, Bootcore, Presence). But there are **no processes at all** — not even zombies — for Cameras, Discovery, vmeta, or Communications. They didn't crash-and-linger; they are simply gone, while their sibling processes (backgrounded in the exact same shell, via the exact same task) are fine.

**4. Ruled out: broken code / shared-module import errors.**
All 4 services' entrypoint modules (`main.py` / `src.main`) were re-imported manually in their correct virtualenvs during this investigation and **all imported successfully with no exceptions** — including `ppl-meta-communications` and `ppl-meta-cameras`, which both import `shared/security/encryption.py` (a file that had open, potentially mid-edit tabs at the time). This rules out "a broken shared module crashed them on `--reload`" as the cause, at least for the current state of that file.

**5. Root cause: unrecoverable — logs were never captured.**
The "Start All Local Python Services" task backgrounds each service with plain `&` (no `nohup`, no `> logfile 2>&1` redirection) inside one shared shell. This is different from the VPN+Matrix task, which *does* redirect Authority/Matrix output to `/tmp/authority.log` / `/tmp/matrix.log`. Because Cameras/Discovery/vmeta/Communications output was never redirected to a file, whatever error caused them to exit was only ever printed to the (now-detached) integrated terminal buffer for that task and **cannot be retrieved retroactively**.

### Most likely explanations (unprovable post-hoc, but consistent with evidence)
- **Resource/memory pressure**: Cameras loads Dlib/OpenCV face-detection models and vmeta loads its own ML inference stack; running 11 services simultaneously (plus Vision, which also does CV work) is memory/CPU intensive on a single dev machine, and macOS or Python could have OOM-killed or crashed these specific heavier processes without leaving a trace once the process exits (no core dump enabled).
- **Port-bind race at startup**: if any of these 4 ports had a stale process holding them from a previous run when "Start All" executed, uvicorn would immediately exit with an "address already in use" error — again, unrecoverable since it wasn't logged.
- **Coincidental timing, not causation**: the user noticed the outage right after running the VPN+Matrix task simply because that's when they next checked — not because that task caused it.

### Recommended fix (implemented as part of this work)
1. **Fix the health check task** so it also checks Discovery/vmeta/Communications, closing the blind spot that let this go unnoticed.
2. **Add log redirection** (`> /tmp/<service>.log 2>&1`) to every service in "Start All Local Python Services", matching what the VPN+Matrix task already does for Authority/Matrix, so future crashes are diagnosable instead of lost.
3. **Restart the 4 down services** to restore a working baseline.

---

## Action Items

- [ ] Restart Cameras, Discovery, vmeta, Communications services (with log redirection this time)
- [ ] Update `🏥 Health Check via Nginx Proxy` task to include Discovery/vmeta/Communications
- [ ] Update `🚀 Start All Local Python Services` task to redirect each service's output to a log file for future diagnosability
- [ ] Add `discovery` entry + `/api/v1/services` proxy route to `ppl-meta-gateway/src/api/v1/router.py`
- [ ] Fix the 7 identified frontend files to route through the Gateway (`AppConfig.instance.apiBaseUrl`) instead of hardcoded direct ports
- [ ] Re-test end-to-end: `/cameras`, media-preview details button, vmeta cross-video search, audit logs, edge camera management
