# Client Rollout Guide — Installation/Service-Token Auth (Issue #8)

This guide covers the **client-side updates** required before `AUTH_ENFORCE` can be
turned on. The Signage Player already authenticates; all other clients that call
`ppl-meta-discovery`'s protected endpoints must be updated too, otherwise they will get
**401** once enforcement is enabled.

> **Rule of thumb:** update **every client first**, then flip `AUTH_ENFORCE=true` on
> Discovery. See the rollout checklist (§7).

---

## 0. How each client authenticates

| Client group | Token type | Headers sent |
|---|---|---|
| **Edge apps** (signage player, mobile camera, edge camera) | HMAC installation token from Authority `enroll-installation` | `Authorization: Bearer <api_token>`<br>`X-Installation-Uuid: <installation_uuid>` |
| **Backend services** (gateway, cameras, vision, node, orchestrator, media) | Internal service token (`INTERNAL_SERVICE_TOKEN`) | `Authorization: Bearer <INTERNAL_SERVICE_TOKEN>`<br>`X-Service-Name: <service_name>` |
| **Frontend web dashboard** | Platform/session token (or exempt from GET) | TBD (see §6) |

---

## 1. Prerequisites

1. Set a **matching** `INSTALLATION_AUTH_SECRET` on both **Authority** and **Discovery**
   (see `docs/guides/installation-auth-runbook.md` §2).
2. Ensure `ppl-meta-authority` is deployed with the updated `enroll-installation` that
   returns `api_token`.
3. Keep `AUTH_ENFORCE=false` until every client in this guide is shipped.

---

## 2. Edge apps (HMAC installation token)

### 2.1 Signage Simple Player — ✅ DONE
Already attaches `Authorization: Bearer <api_token>` + `X-Installation-Uuid` via the Dio
interceptor in `lib/services/discovery_service.dart` (`_setupAuthInterceptor`), with the
token persisted in `ConfigService.installationApiToken`. No action needed.

### 2.2 Mobile Camera (`ppl_meta_mobile_camera`) — DONE
Uses **local enrolment (Option 1)**: on setup it calls
`POST {discovery}/api/v1/device-enroll` (`DiscoveryConfigService.enrollLocallyIfNeeded()`)
with `X-Enroll-Key: INSTALL_AUTH_SECRET`, persists the returned token + installation UUID
via `saveInstallationAuth`, and every discovery client (unified / simplified / hybrid /
`ppl_meta_discovery_client`) attaches `Authorization: Bearer <token>` + `X-Installation-Uuid`
through `DiscoveryConfigService.authHeaders()`. So `GET /api/v1/services` and the protected
`GET /api/v1/discovery/topology` are authenticated.

### 2.3 Edge Camera (`ppl-meta-edge-camera`)
Registers as a service in `src/platform_client/registration.py`
(`POST /api/v1/services/register`, `POST /api/v1/services/{name}/heartbeat`). Choose one:

- **Option A (edge device):** if it enrolls via the Authority and has an
  `installation_uuid`, send the HMAC token like the Signage Player.
- **Option B (service):** treat it like a backend service and send the service token
  (§3 pattern) — simplest if it doesn't enroll via Authority.

---

## 3. Backend services (internal service token)

These register as platform services. The single best leverage point is the shared client
`shared/service_discovery/ppl_discovery_client.py` if used; otherwise patch each
service's own discovery module. Each request should include:

```python
from shared.auth.service_auth import get_service_auth_headers  # or equivalent

headers = get_service_auth_headers("ppl-meta-gateway")
# => Authorization: Bearer <INTERNAL_SERVICE_TOKEN> + X-Service-Name
# add headers to the discovery request (httpx/aiohttp .request(headers=headers))
```

| Service | File(s) to patch | Headers source |
|---|---|---|
| **Gateway** | `src/shared/service_discovery.py` | `ppl-meta-gateway` |
| **Cameras** | `src/shared/service_discovery.py` | `ppl-meta-cameras` |
| **Vision** | `src/main.py`, `src/main_enhanced.py` | `ppl-meta-vision` |
| **Node** | `src/microservice_config.py`, `src/services/multicast_discovery.py` | `ppl-meta-node` |
| **Orchestrator** | `src/main.py` | `ppl-meta-orchestrator` |
| **Media** | `src/microservice_config.py`, `src/services/signage_service.py` | `ppl-meta-media` |
| **Shared client** | `shared/service_discovery/ppl_discovery_client.py` | per `service_name` |

> The service name must be a `KNOWN_SERVICES` member (mirrors `shared/auth/service_auth.py`):
> ppl-meta-media, ppl-meta-cameras, ppl-meta-orchestrator, ppl-meta-gateway,
> ppl-meta-node, ppl-meta-vision, ppl-meta-vmeta, ppl-meta-discovery, ppl-meta-bootcore.

---

## 4. Single shared change (preferred)

If most Python services use the same request path, add the auth headers in **one place**:

- `shared/service_discovery/ppl_discovery_client.py` — add
  `get_service_auth_headers(service_name)` to every `POST/DELETE/GET` it makes.
- If a service uses a local copy (`ppl-meta-gateway/src/shared/service_discovery.py`,
  `ppl-meta-cameras/src/shared/service_discovery.py`), port the same headers into those
  local modules.

Track which services use the shared module vs. a local copy before starting.

## 5. Frontend web dashboard (`ppl-meta-frontend`)

`lib/services/discovery_service_client.dart` does `GET /api/v1/services` for dashboards.
It is a **platform UI**, not an edge installation, so the HMAC token does not apply.

**Approach (implemented): (a) Exempt read-only GET.** Discovery now **exempts** the
read-only `GET /api/v1/services` directory listing from auth (`_is_exempt_readonly`), so
the browser dashboard can query it without exposing a token. The mutating/identity
endpoints (`register`/`heartbeat`/`deregister`, devices, topology) remain protected.
No frontend code change is required.

---

## 6. Verification

For each client, after updating (with `AUTH_ENFORCE=true`):

```bash
# HMAC (edge app) — expect 200:
curl -i -X POST http://<discovery>:8006/api/v1/services/heartbeat \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'X-Installation-Uuid: my-installation' \
  -d '{"service_id":"x","status":"healthy"}'

# Service token (backend service) — expect 200:
curl -i http://<discovery>:8006/api/v1/services \
  -H "Authorization: Bearer $INTERNAL_SERVICE_TOKEN" \
  -H 'X-Service-Name: ppl-meta-gateway'

# Unauthenticated — expect 401:
curl -i http://<discovery>:8006/api/v1/services
```

Checklist per client: register works, heartbeat works, subsequent reads/endpoints work,
and the service shows up healthy in `GET /api/v1/services` / topology.

---

## 7. Rollout checklist & sequencing

1. [x] Set matching `INSTALLATION_AUTH_SECRET` on Authority + Discovery.
2. [x] Deploy Authority that returns `api_token`.
3. [x] Update **Signage Player** — DONE (minimal setup, local Option 1 enrolment).
4. [x] Update **Mobile Camera** (Option 1 local enrolment + HMAC headers).
5. [x] Update **Edge Camera** (HMAC token).
6. [ ] Update **backend services** to send the service token (gateway, cameras, vision,
   node, orchestrator, media) — prefer the shared client.
7. [x] **Frontend** uses the exempt read-only `GET /api/v1/services` (no token needed).
8. [x] Smoke-test each client — headers are accepted (client + frontend verified).
9. [x] Flip `AUTH_ENFORCE=true` on Discovery.
10. [ ] Monitor for 401 spikes; roll back with `AUTH_ENFORCE=false` if needed.
11. [x] Add local `POST /api/v1/device-enroll` (Option 1) so devices onboard locally
    without the remote Authority.

---

## 8. Rollback

- **Immediate:** set `AUTH_ENFORCE=false` on Discovery and reload — auth is bypassed and
  all clients work again. No code change needed.
- After confirming a regression, fix the client and re-enable.

---

## 9. Owners / status

| Client | Service | Token type | Status |
|---|---|---|---|
| Signage Simple Player | `ppl-meta-signage-simple-player` | HMAC | ✅ Done — minimal setup, local `device-enroll` |
| Mobile Camera | `ppl_meta_mobile_camera` | HMAC | ✅ Done — Option 1 local enrolment + headers |
| Edge Camera | `ppl-meta-edge-camera` | HMAC | ✅ HMAC patched (self-computed token) |
| Gateway | `ppl-meta-gateway` | Service | 🟡 Partial — `shared/service_discovery.py` done |
| Cameras | `ppl-meta-cameras` | Service | 🟡 Partial — `shared/service_discovery.py` done |
| Shared python client | `shared/service_discovery/ppl_discovery_client.py` | Service | ✅ Headers added |
| Vision | `ppl-meta-vision` | Service | 🟡 Covered via shared client (`register_service` sets `service_name`) |
| Node | `ppl-meta-node` | Service | N/A — not a direct `ppl-meta-discovery` client |
| Orchestrator | `ppl-meta-orchestrator` | Service | N/A — not a direct `ppl-meta-discovery` client |
| Media | `ppl-meta-media` | Service | ✅ Discovery GETs patched (`signage_service.py`) |
| Frontend dashboard | `ppl-meta-frontend` | Exempt read-only GET | ✅ Resolved — `GET /api/v1/services` exempted from auth |

---

## 10. Addendum — local onboarding (`device-enroll`, Option 1)

To keep onboarding fully **local** (remote Authority used only for licence validity), Discovery
exposes `POST /api/v1/device-enroll`:

- Guarded by `X-Enroll-Key` = the service's `INSTALLATION_AUTH_SECRET`.
- Returns `{ "installation_uuid", "api_token" }` where
  `api_token = HMAC_SHA256(INSTALLATION_AUTH_SECRET, installation_uuid)`.
- Device setup (signage player, mobile camera) reads the secret from
  `--dart-define=INSTALL_AUTH_SECRET` (default `ppl-meta-installation-auth-secret-dev` for the
  IDE/dev build) and calls this endpoint instead of the remote `enroll-installation`.
- The remote Authority remains solely responsible for **licence activation/validation**.