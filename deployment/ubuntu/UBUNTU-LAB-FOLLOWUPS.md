# Ubuntu lab install — follow-ups

> **CI/CD truth (two stages):**  
> [`docs/deployment/platform-release-cicd.md`](../../docs/deployment/platform-release-cicd.md)  
> **Stage 1** — push code to GitHub **and update [`CHANGELOG.md`](../../CHANGELOG.md)** (frequent). **Stage 2** — build/push GHCR images from a Windows or Linux host (when ready).  
> Lab `docker cp` / compose overrides are **not** a release. GitHub Actions is not used for platform images yet.

Issues found while bringing up EyeNet `2.25.81` on native Ubuntu 24.04
(`eyenet-server`, LAN `192.168.9.14`, Sept 2026). Each item needs a durable
fix in **installer scripts**, **Dockerfiles**, **requirements**, or **product
code** so the next clean install does not need lab overrides.

Lab host paths (reference):

- Install dir: `~/eyenet-platform`
- Clone: `~/ppl-meta-platform`
- Compose: `docker-compose.windows-installer.yml` + lab `docker-compose.override.yml`
- One-shot installer: `deployment/ubuntu/install-eyenet-ubuntu.sh`
- Shared post-up: schema apply/verify + `deployment/windows-installer/reregister-discovery-services.sh`

---

## P0 — Blocks mobile / network UX

### 1. Discovery registry nearly empty after install

**Symptom:** `/network` shows only gateway. Mobile camera finds communications
(multicast) but reports **node service cannot be found**. Login still works
(gateway path).

**Cause:**

- Discovery keeps an **in-memory** registry.
- Published `ppl-meta-node` fails self-register:
  `Failed to register with discovery service: No module named 'shared'`.
- Communications logs: `Service discovery module not available, using fallback mode`.
- Other services often never register on cold start either.

**Lab workaround:**

```bash
bash ~/ppl-meta-platform/deployment/mac-lima/reregister-discovery-services.sh
```

Registers compose DNS hosts; discovery rewrites to `ADVERTISE_HOST` for phones.

**Follow-up actions:**

| Where | What |
|--------|------|
| `ppl-meta-node` image / Dockerfile | Fix missing `shared` package (or stop importing it) so discovery registration works at startup. |
| Other service images | Ensure discovery client is packaged and registration is best-effort, not silent skip. |
| `deployment/ubuntu/install-eyenet-ubuntu.sh` | Always run `reregister-discovery-services.sh` after `up -d` (and after any discovery recreate). |
| Windows installer / Lima setup | Same: call reregister after stack healthy (Windows `install-platform.ps1` + shared `deployment/windows-installer/reregister-discovery-services.sh`). |
| Ops | Optional: systemd timer / cron on lab boxes to re-run register after reboot until images are fixed. |
| Product | Consider persisting discovery registry or having gateway seed peers so a discovery restart is not catastrophic. |

---

## P0 — Published image packaging bugs

### 2. `ppl-meta-communications` — cannot create `/logs`

**Symptom:** Crash loop: `PermissionError: [Errno 13] Permission denied: '/logs'`.

**Cause:** `main.py` resolves log dir to workspace root `/logs` inside the image;
non-root user `communications` cannot create it. Image does not pre-create a
writable log path.

**Lab workaround:** Compose override: run as root and/or bind-mount writable
`/logs`; also `pip install email-validator` at start.

**Follow-up actions:**

| Where | What |
|--------|------|
| `ppl-meta-communications/src/main.py` | Log under `/app/logs` (or `LOG_DIR` env), not `/logs`. |
| Communications Dockerfile | `mkdir -p /app/logs` and chown to runtime user. |
| `requirements.txt` | Add `email-validator` (Pydantic email fields). |
| Rebuild & push | New `ppl-meta-communications` tag; drop lab override. |

### 3. `ppl-meta-orchestrator` — same `/logs` permission issue

**Symptom:** Crash loop writing `/logs` when user/path wrong; with `user: "0:0"`
override, `uvicorn` broke (`ModuleNotFoundError: No module named 'uvicorn'`
because PATH pointed at `appuser` local bins).

**Follow-up actions:**

| Where | What |
|--------|------|
| `ppl-meta-orchestrator/src/main.py` | Use `/app/logs` or `LOG_DIR`. |
| Orchestrator Dockerfile | Pre-create writable logs for `appuser`. |
| Do not | Force `user: "0:0"` in compose as a permanent fix. |

### 4. `ppl-meta-vmeta-protected` — broken / incomplete published image

**Symptoms (stacked):**

1. `ModuleNotFoundError: No module named 'httpx'`
2. `ModuleNotFoundError: No module named 'asyncpg'`
3. `ImportError: libGL.so.1` (OpenCV) on some attempts
4. Protected build deletes `.py` sources (`mvr_service.py`, etc.) but compiled
   modules were not importable → `No module named 'services.mvr_service'`
5. After local rebuild from plain `Dockerfile`, still missing `PyJWT` (`import jwt`)

**Cause:** `requirements/base.txt` does not list deps the code imports
(`httpx`, `asyncpg`, `PyJWT`, …). Protected Dockerfile runtime stage / Cython
packaging is unreliable for this release. Lab rebuilt **non-protected**
`docker/Dockerfile` and tagged it as `…/ppl-meta-vmeta-protected:2.25.81`, plus
startup `pip install` for JWT stack.

**Follow-up actions:**

| Where | What |
|--------|------|
| `ppl-meta-vmeta/requirements/base.txt` | Add at least: `httpx`, `asyncpg`, `PyJWT`, and any other runtime imports used by `src/` (audit with import scan). |
| `docker/Dockerfile` | Prefer `libgl1` (not obsolete `libgl1-mesa-glx`) on current Debian slim. |
| `docker/Dockerfile.protected` | Verify `.so` artifacts are copied and importable; don’t delete `.py` until smoke-test passes. |
| CI / release | Smoke-test: `python -c "import src.main"` (or start `/health`) before pushing GHCR tags. |
| Compose | Stop needing lab entrypoint `pip install …` overrides. |

---

## P1 — Schema apply / verify

### 5. Schema pack apply races ORM and fails first pass

**Symptom:** First `schema/apply.sh` run floods errors (`person_objects` /
`mvr_people` missing). Verify fails. After services create base tables, re-apply
mostly works; still needed manual fixes for:

- `individuals.created_by_session`
- `person_objects` + `representative_faces` (vision created then **rolled back**)

**Cause:**

- Pack migrations assume tables that ORM/vision create at runtime.
- Vision `person_objects_migrations` expects `schema_migrations(migration_name, …)`
  while pack creates `schema_migrations(version, …)`. Mark-complete fails →
  **rollback drops** `person_objects`.
- `individuals.created_by_session` lives in archive stubs / vmeta migrations but
  is not reliably in the ordered pack path used by the installer.

**Follow-up actions:**

| Where | What |
|--------|------|
| Installer (`apply.sh` / Ubuntu / Windows) | Wait for postgres **and** key services (or run a single “bootstrap DDL” before pack). Re-apply + verify as a hard gate. |
| Vision migrations | Align `schema_migrations` shape with pack **or** detect existing table and skip rollback on mark failure. |
| Schema pack sync | Ensure `created_by_session` and full `person_objects` CREATE are in `deployment/windows-installer/schema/pack/`. |
| `verify.sh` | Keep as install gate; document required order. |

---

## P1 — Installer / ops reliability

### 6. GHCR pull DNS timeouts (`127.0.0.53`)

**Symptom:** `docker compose pull` fails mid-blob:
`lookup ghcr.io on 127.0.0.53:53: … i/o timeout`.

**Lab workaround:** Pull images one-by-one with retries; optionally set Docker
daemon `"dns": ["1.1.1.1", "8.8.8.8"]` (needs sudo).

**Follow-up actions:**

| Where | What |
|--------|------|
| `install-eyenet-ubuntu.sh` | Retrying per-image pull; optional daemon.json DNS note. |
| README | Document flaky stub resolver on some Wi‑Fi / ISP DNS (e.g. Dyn-style `96.45.x.x`). |

### 7. Ubuntu installer should harden post-`up` steps

Current script pulls/starts/applies schema but should also:

1. Run `reregister-discovery-services.sh` (see §1).
2. Retry schema apply after a short wait if verify fails once.
3. Print `/network` + discovery URL and remind `ADVERTISE_HOST` must be LAN IP.
4. Avoid relying on unpublished lab `docker-compose.override.yml` hacks.

### 8. Wrong host IP assumption

Operator reported `192.168.9.24/24`; real address was **`192.168.9.14`**.
Installer already defaults `ADVERTISE_HOST` from `ip -4 addr`; docs should say
**always verify** with `ip -4 addr show scope global` before mobile onboarding.

---

## P2 — Authority / bootstrap

### 9. Old application key → `installation_already_bound_elsewhere`

**Symptom:** Bootstrap activation fails when reusing a `lic_…` key bound to an
erased install. Same owner email **is** allowed for a **new** key.

**Lab notes:**

- Clearing stale local Authority fields was required after failed attempts
  (`app_settings` + `installation_info.authority_*`).
- Do not paste entitlement/install UUIDs into the bootstrap key field; only
  `lic_<32 hex>`.
- Local install guid (example lab): `2489feec-fb47-40ce-b43a-e8b6014a0ccf` —
  Node sends this as `installation_uuid` on activate.

**Follow-up actions:**

| Where | What |
|--------|------|
| Authority admin UX | Make “pending / unbound” entitlement obvious; warn if `installation_uuid` pre-filled. |
| Bootstrap UI | Show Authority `reason` clearly (`installation_already_bound_elsewhere`, etc.). |
| Node | Avoid persisting application key into settings when `approved=false` (today it still persists, which confused later attempts). |
| Docs / installer README | Lab reset SQL for clearing Authority columns (already done ad hoc on Ubuntu). |

### 10. Env `INSTALLATION_UUID` / `APPLICATION_KEY` intentionally empty

By design for production-like install: values come from Authority claim /
bootstrap UI, not installer prompts. VPN enrollment stays skipped until set
(`EYENET_INSTALLATION_UUID` / `EYENET_APPLICATION_KEY`).

**Follow-up:** After successful activate, optionally write keys into `.env` and
recreate node so VPN can enroll without a second manual step.

---

## P2 — Already fixed upstream (keep regression-tested)

### 11. Windows installer schema `pack.tar.gz` 404

Root `*.tar.gz` gitignore hid `deployment/windows-installer/schema/pack.tar.gz`.
**Fixed:** allowlist exception + track pack in git + raw GitHub URL returns 200.
Installer also prefers local/bundled copies.

**Regression:** After `sync-schema-pack.sh`, always commit `schema/pack.tar.gz`.

---

## Lab-only overrides to remove after image fixes

On `eyenet-server`, `~/eyenet-platform/docker-compose.override.yml` currently
(or previously) included:

- communications: `user: "0:0"`, `/logs` mount, startup `pip install email-validator`
- orchestrator: writable `/logs` mount
- vmeta: rebuilt local image + startup `pip install PyJWT …` / apt libGL

**Goal:** Delete this override once P0 image fixes are published under a new
release tag and the Ubuntu install script only needs compose + reregister +
schema verify.

---

## P1 — Mobile camera stream without `/cameras` row

### 12. Android can stream while never registering on the new install

**Symptom (lab):** Mobile app shows a live stream; platform `/cameras` empty.
Postgres `cameras` table had **0 rows**. Cameras service logs showed list/detect
only — **no** `POST /api/v1/cameras/mobile`.

**Not primarily caused by** reusing the same username/password on a new install
(JWT is issued by the new Node). Sticky **on-device state** matters more:

- SharedPreferences keeps `ppl_camera_uuid` / platform service URLs from the old
  install.
- `autoRegisterCamera` → `checkExistingCamera` may skip or confuse re-register.
- `camera_screen.dart` **swallows registration failure** and continues with a
  fake success (`cameraId: 0`), so streaming can start without a DB camera.

**Lab workaround:** Clear app storage (or uninstall/reinstall the APK), log in
again to this platform (`192.168.9.14`), confirm discovery lists cameras/node,
then open camera. Expect a `POST …/cameras/mobile` and a row on `/cameras`.

**Follow-up actions:**

| Where | What |
|--------|------|
| Mobile app | On login to a **different** installation/host, clear stored camera UUID and force re-register. |
| `camera_screen.dart` | Do not treat registration failure as success; surface error / block stream until registered. |
| Cameras API | Ensure `GET /cameras/{uuid}` 404 always triggers clean re-register (already intended). |
| QA | After fresh platform install, verify `/cameras` gains a row when Android streams. |

---

## P1 — Disconnect while instant detection looks broken

### 13. Disconnect button during instant detection / mobile stream

**Symptom:** On `/cameras` (or stream with ID active), Disconnect appears to do
nothing — preview/ID keeps running.

**Cause:**

- `camera_detection.disconnect_camera` blocked disconnect when **any** sampler
  had `is_sampling` (global), not per-camera.
- Disconnect API did not stop instant detection for that device first.
- Mobile connect has a special path; mobile disconnect only hit the queue worker
  and set status to `AVAILABLE`, without stopping the mobile stream/worker.

**Lab status (Sept 2026 Ubuntu box):**

- Source fixed in monorepo:
  - `ppl-meta-cameras/src/api/v1/endpoints/cameras.py`
  - `ppl-meta-cameras/src/services/camera_detection.py`
  - `ppl-meta-frontend/lib/presentation/widgets/camera/camera_card.dart`
- **Only the running lab container** was hotfixed (`docker cp` + restart
  `ppl-meta-cameras`). That change is **lost** on `compose pull` / recreate /
  new host install until images are republished.

**CI/CD / release follow-up (required):**

1. Commit the three source files above (plus this doc).
2. Rebuild and push GHCR images for at least:
   - `ppl-meta-cameras` (backend disconnect/ID stop)
   - `ppl-meta-frontend` (stop ID before disconnect in UI)
3. Bump `RELEASE_TAG` / installer pin and redeploy lab from registry (no more
   `docker cp` overrides).

Until step 2–3, other installs and a fresh Ubuntu pull still have the old bug.

---

## Suggested work order

1. Fix discovery registration in **node** (+ reregister in all installers).
2. Fix **communications** / **orchestrator** log paths + `email-validator`.
3. Fix **vmeta** requirements + protected image smoke test; republish.
4. Harden schema apply order + `schema_migrations` clash with vision.
5. Authority activate persistence / admin UX for rebound keys.
6. Mobile camera: clear UUID on new host + stop fake registration success (§12).
7. Disconnect + instant detection (§13) — source fixed; **must rebuild/push**
   cameras + frontend via CI/CD (lab hotfix is ephemeral).
8. Ubuntu installer polish (DNS retries, post-up verify checklist).

---

## Quick health checklist (lab)

```bash
# Discovery must list node, cameras, communications, …
curl -s http://127.0.0.1:8006/api/v1/services | python3 -c \
  'import json,sys; d=json.load(sys.stdin); print(len(d.get("services",[])), "services")'

# If only gateway (or empty): 
bash ~/ppl-meta-platform/deployment/windows-installer/reregister-discovery-services.sh

# Schema
bash ~/ppl-meta-platform/deployment/windows-installer/schema/verify.sh

# UI
# http://<ADVERTISE_HOST>:3000/network
```
