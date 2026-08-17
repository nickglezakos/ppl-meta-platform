# Signage Simple Player — Discovery & Keep-Alive Communication Analysis

**Scope:** Analysis of how the *PPL Meta Signage Simple Player* (a Flutter application
targeting Android and macOS) discovers, registers with, and keeps alive its connection
to the **PPL Meta platform** via the *ppl-meta-discovery* service.

**Two communication mechanisms are analysed:**
- **Discovery (registration / comms)** — the process by which the player announces itself
  to the platform and learns where the backend services are.
- **Keep-alive (heartbeat)** — the mechanism that maintains the player's presence and
  health in the platform registry so it is not removed as stale.

---

## 1. Overview & Actors

### 1.1 The Player (client)

| Concern | Value |
|---|---|
| Framework | Flutter / Dart |
| Target platforms | Android, macOS (native `dart:io`), web fallback |
| Primary service | `SignageDiscoveryService` (`lib/services/discovery_service.dart`) |
| Configuration | `ConfigService` (user-supplied backend IP + discovery port, persisted via `SharedPreferences`) + `AppConfig` (static defaults) |
| Embedded HTTP server | `SignageHttpServer` on **port 8009** (exposes `GET /health` etc.) |
| HTTP stack | `Dio` (timeouts + interceptors) |

### 1.2 The platform (server)

| Concern | Value |
|---|---|
| Service | `ppl-meta-discovery` (FastAPI, Python) |
| Default port | **8006** |
| Registry | `ServiceRegistry` (in-memory: `service_registry.py`) |
| Models | `RegistrationRequest`, `HeartbeatRequest`, `RegistrationResponse`, `ServiceInfo` (`models/service_models.py`) |
| HTTP stack | `aiohttp` health probes; FastAPI endpoints |

### 1.3 High-level data flow

```text
 +------------------+   HTTP/Dio   +------------------------+
 | Signage Player   | -----------> | ppl-meta-discovery     |
 | (port 8009 /health|   register  | (port 8006)            |
 +------------------+ <----------- +------------------------+
        |  heartbeat every 30s        |  health probe GET host:8009/health
        |  DELETE on dispose          |
 +-----------------------------------+   persists last_seen,
        |                            |   marks stale after 90s,
        +----------------------------+   removes stale entry
```

---

## 2. Components & Configuration

### 2.1 Player static configuration (`lib/config/app_config.dart`)

| Key | Value | Used for |
|---|---|---|
| `serviceName` | `signage-simple` | Registered service name prefix |
| `serviceType` | `edge` | Registration `service_type` |
| `version` | `1.0.0` | Registration version |
| `httpServerPort` | `8009` | Embedded HTTP server + registration `port` |
| `heartbeatInterval` | **30 s** | Heartbeat `Timer.periodic` cadence |
| `registrationRetryDelay` | 10 s | **Declared but unused** (no retry loop) |
| `discoveryServiceUrl` | `http://localhost:8006` | Static default; used by deregister |
| `discoveryRegisterEndpoint` | `http://localhost:8006/api/v1/services` | Used by `deregister()` |
| `discoveryHeartbeatEndpoint` | `http://localhost:8006/api/v1/services/heartbeat` | **Declared but unused** |

### 2.2 Player runtime configuration (`lib/services/config_service.dart`)

| Key | Default | Notes |
|---|---|---|
| `backendIP` | `localhost` | Entered in `SimpleSetupScreen` |
| `discoveryPort` | `8006` | Entered in `SimpleSetupScreen` |
| `isConfigured` | `false` | Gate for setup flow |
| `discoveryServiceUrl` | `http://{backendIP}:{discoveryPort}` | Used by **register() and heartbeat()** |
| `mediaServiceUrl` | `http://{backendIP}:8000` | Playlist/ETL sync |
| `gatewayUrl` | `http://{backendIP}:8080` | `SignageApiClient` base URL |

> **Note:** The configured `discoveryServiceUrl` is the *authoritative* host for
> registration and heartbeat. Only `deregister()` unexpectedly falls back to the static
> `AppConfig.discoveryRegisterEndpoint` (see Issue #4).

### 2.3 Platform discovery configuration (`ppl-meta-discovery/src/config.py`)

| Key | Default | Notes |
|---|---|---|
| `PORT` | `8006` | HTTP server |
| `HEALTH_CHECK_INTERVAL` | 30 s | General health-check cadence |
| `SERVICE_TIMEOUT` | 10 s | Some health check timeouts |
| `MAX_MISSED_HEARTBEATS` | 3 | **Not used by `ServiceRegistry`** (used for edge devices) |
| `REGISTRY_CLEANUP_INTERVAL` | 60 s | **Not used**; cleanup loop hardcodes 30 s |
| `SERVICE_REGISTRY_SIZE` | 100 | In-memory cap |
| `HEARTBEAT_TIMEOUT` (registry ctor default) | **90 s** | Stale threshold in `ServiceRegistry.__init__` |

---

## 3. Discovery (Registration / Comms) Flow

### 3.1 Startup sequence (player, `lib/main.dart`)

1. `main()` → immersive UI, orientation lock, `runApp(SignageSimplePlayerApp)`.
2. `StartupScreen` reads `ConfigService.isConfigured`.
   - **Not configured** → `SimpleSetupScreen`: operator enters **backend IP** and
     **discovery port (default 8006)**; saved via `saveBackendUrl()`. No connectivity
     probe is performed here (only serialization).
   - **Configured** → proceeds straight to `InitializationScreen`.
3. `InitializationScreen._initializeServices()` builds, in order:
   `ConfigService` → `PlaylistDatabase` → `DeviceInfoHelper.getDeviceId()` →
   `SignageApiClient` (base = `gatewayUrl`) → `SignagePlayerEngine` →
   `SignageHttpServer.start()` (port 8009) → `HistoryTrackingService` →
   `SyncService` → **`SignageDiscoveryService.initialize()`**.
4. `initialize()`:
   - Gathers full `DeviceInfoModel` via `DeviceInfoHelper.getDeviceInfo()`.
   - Calls `register()`.
   - **On success:** starts the heartbeat timer (`_startHeartbeat()`).
   - **On failure:** logs a warning and returns `false`; the player proceeds in
     "**offline mode**" (still navigates to the player screen).

### 3.2 Registration call (player → platform)

**Method:** `SignageDiscoveryService.register()` → `POST {discoveryServiceUrl}/api/v1/services/register`

The player builds a `ServiceRegistration`:

| Field (JSON) | Source in player | Example |
|---|---|---|
| `name` | `'signage-simple-{deviceId}'` | `signage-simple-android-1234` |
| `service_type` | `AppConfig.serviceType` | `edge` |
| `host` | `DeviceInfoHelper.getLocalIpAddress()` (prefers Tailscale `100.x`) | `192.168.1.50` |
| `port` | `AppConfig.httpServerPort` | `8009` |
| `health_check_endpoint` | `'/health'` | `/health` |
| `version` | `AppConfig.version` | `1.0.0` |
| `metadata` | `DeviceInfoModel.toJson()` (device_id, platform, capabilities, codecs, …) | `{ "device_id": …, "capabilities": […] }` |

> **Player request example**
> ```json
> {
>   "name": "signage-simple-android-7f3a…",
>   "service_type": "edge",
>   "host": "192.168.1.50",
>   "port": 8009,
>   "health_check_endpoint": "/health",
>   "version": "1.0.0",
>   "metadata": {
>     "device_id": "android-7f3a…",
>     "device_name": "Samsung Galaxy …",
>     "platform": "android",
>     "capabilities": ["video_playback", "remote_control", "playlist_sync", "history_tracking"]
>   }
> }
> ```

**Server-side handling** (`ServiceRegistry.register_service`):

1. Computes a **deterministic** `service_id = uuid5(NAMESPACE_DNS, name)`. Because the
   player's name embeds a stable `deviceId`, a restart yields the **same** `service_id`.
2. If a service with the same name already exists, its existing `service_id` is reused
   (idempotent re-registration / host:-port update).
3. Extracts `tailscale_ip` from `metadata` if present (Phase 2 VPN-aware).
4. Builds `ServiceInfo` with `status = REGISTERING`, sets `registered_at`/`last_seen = now`.
5. Performs an **initial health probe**: `GET http://{host}:{port}/health_endpoint`
   (5 s `aiohttp` timeout). Returns `HEALTHY` on 200, else `UNHEALTHY`.
6. Responds with `RegistrationResponse`.

> **Server response example**
> ```json
> {
>   "success": true,
>   "service_id": "3f0f2ef7-…-uuid5…",
>   "message": "Service signage-simple-android-7f3a… registered successfully",
>   "heartbeat_interval": 30
> }
> ```

**Player success handling:**

- Accepts `200` or `201`.
- Stores `_serviceId = response["service_id"]`, falling back to `registration.name`
  if the server omitted it.
- Stores the `device_id` (from device info) for the embedded HTTP server.

**Player failure handling (`DioException`):**

| Condition | Result |
|---|---|
| `connectTimeout` / `receiveTimeout` | `_lastError` set to timeout message; **no retry** |
| `connectionError` | `_lastError` "Cannot connect…"; continues offline |
| **401 / 403** | `_lastError` "Authentication failed" |
| other `DioException` | `_lastError` "Registration failed: {message}" |
| non-2xx status (not 401/403) | `_lastError` with HTTP status |

In every failure case `register()` returns `false`. The heartbeat timer is **not** started
(see Issue #5).

### 3.3 Discovery endpoints used (player ↔ platform)

| Player method | Endpoint (player builds) | HTTP |
|---|---|---|
| `register()` | `POST {configService.discoveryServiceUrl}/api/v1/services/register` | POST |
| `sendHeartbeat()` | `POST {configService.discoveryServiceUrl}/api/v1/services/heartbeat` | POST |
| `deregister()` | `DELETE {AppConfig.discoveryRegisterEndpoint}/{serviceId}` | DELETE |
| `discoverTopology()` (VPN-direct) | `GET http://{vpnNodeIp}:8006/api/v1/discovery/topology?vpn=true` | GET |

Server equivalents implemented in `ppl-meta-discovery/src/main.py`:
`POST /api/v1/services/register`, `POST /api/v1/services/heartbeat`,
`DELETE /api/v1/services/{service_id}`, `GET /api/v1/services`,
`GET /api/v1/discovery/topology`.

### 3.4 VPN-direct discovery (via the Authority)

When the player is enrolled for VPN access, it can discover backend services directly
over the mesh instead of relying only on a manually configured backend address. The VPN
metadata (primary node Tailscale IP, matrix group, headscale server, pre-auth key) is
sourced from the **PPL Meta Authority** during licensing/enrollment:

1. `SimpleSetupScreen` collects an optional Application Key + Installation UUID and calls
   `POST {authority}/api/v1/vpn/enroll-installation`. The Authority validates the licence,
   creates a pre-auth key, and returns `primary_node_ip`, `matrix_group_id`,
   `headscale_server`, `tags`.
2. The player persists this metadata (`ConfigService`) and uses `primary_node_ip` for
   VPN-direct discovery.
3. On startup, `SignageDiscoveryService.initialize()` reads `vpnPrimaryNodeIp`, calls
   `setVpnNodeIp(...)`, then `await discoverTopology()`:
   `GET http://{primaryNodeIp}:8006/api/v1/discovery/topology?vpn=true`.
4. The result is cached/exposed as `discoveredTopology`. `register()` also sends
   `metadata.tailscale_ip` (when the local IP is a `100.x` Tailscale address), so
   `ppl-meta-discovery` marks the player VPN-reachable and returns it in `?vpn=true`
   topology.

This is a **best-effort, metadata-only** bootstrap — no native Tailscale client is run by
the player; mesh connectivity is assumed to be provided by the platform.

---
---

## 4. Keep-Alive (Heartbeat) Flow

### 4.1 Player heartbeat timer

- Started **only after a successful registration** in `initialize()`.
- `Timer.periodic(AppConfig.heartbeatInterval /* 30 s */, (_) => sendHeartbeat())`.
- Cancelled in `dispose()` (which also deregisters).

### 4.2 Heartbeat request (player → platform)

**Method:** `SignageDiscoveryService.sendHeartbeat()` →
`POST {configService.discoveryServiceUrl}/api/v1/services/heartbeat`

**Payload:**
```json
{
  "service_id": "3f0f2ef7-…-uuid5…",
  "status": "healthy",
  "metadata": {}
}
```

**Behavior:**
- If the player is **not registered** or `_serviceId` is null, it tries `register()`
  again before/without sending the heartbeat (self-healing guard).
- Otherwise it posts the heartbeat with 5 s send / 5 s receive timeouts.
- Non-200 responses are logged as warnings; `DioException`s (timeout, connection error,
  other) are logged and **never thrown** — the periodic timer retries on the next tick.

### 4.3 Heartbeat handling (platform)

`ServiceRegistry.update_heartbeat(request)`:

1. **400** if `service_id` is missing; **404** if the service is not in the registry.
2. Updates `last_seen = now`, increments `heartbeat_count`, sets `status = request.status`
   (e.g. `healthy`).
3. If `metadata` is provided, merges it and extracts `tailscale_ip` if present
   (the player currently sends an empty `metadata`, so this is a no-op in practice).
4. Returns `{ "status": "heartbeat updated" }`.

### 4.4 Stale detection & cleanup (platform)

- Background task `_cleanup_stale_services()` runs a loop, sleeping **30 s** each cycle.
- A service is considered **stale** when `now - last_seen > heartbeat_timeout`
  (constructing the registry defaults to **90 s**).
- For each stale service:
  1. Marks it `UNHEALTHY`.
  2. Performs a final health check `GET host:8009/health` (5 s timeout).
  3. If the health check returns 200 → treated as **recovered**; `last_seen` and status
     are refreshed.
  4. Otherwise → the service is **removed** from the in-memory registry.
- `batch_health_check()` additionally hard-removes any service idle for
  `heartbeat_timeout * 2` (180 s).

> **Impact of timing:** The player beats every 30 s, which is well within the 90 s
> stale window. Under normal operation the registration stays healthy indefinitely.
> If the player loses network connectivity (and thus stops beating), it is marked stale
> at ~90 s and removed after a failed probe. Note the platform does **not** actively
> re-register the player — recovery depends on *another* register/heartbeat from the
> player itself.

### 4.5 Contract mapping (player ↔ server heartbeat)

| Concept | Player (`discovery_service.dart`) | Server (`HeartbeatRequest`) |
|---|---|---|
| Identity | `service_id` | `service_id` (required; else 400) |
| Status | `"healthy"` (hard-coded) | `status` (`ServiceStatus` enum) |
| Extra data | `metadata: {}` (empty) | `metadata` (merged if present) |
| Cadence | 30 s (`AppConfig`) | 90 s stale + 30 s cleanup loop |

---

## 5. Lifecycle & Resilience

```mermaid
sequenceDiagram
    participant App as Player (Dart)
    participant Disc as ppl-meta-discovery (:8006)
    participant Health as Player HTTP :8009

    App->>App: ConfigService.isConfigured?
    App->>App: SimpleSetupScreen (enter IP + port 8006) [if not configured]
    App->>Health: start HTTP server :8009
    App->>App: DeviceInfoHelper.getDeviceInfo()

    App->>Disc: POST /api/v1/services/register
    Disc->>Health: GET :8009/health (initial probe, 5s)
    Health-->>Disc: 200
    Disc-->>App: 200 {service_id, heartbeat_interval:30}

    alt registration success
        App-->>App: start heartbeat Timer.periodic(30s)
        loop every 30s
            App->>Disc: POST /api/v1/services/heartbeat {service_id, status:healthy}
            Disc-->>App: 200 "heartbeat updated"
        end
    else registration failure
        App-->>App: offline mode (no timer; no retry)  [Issue #5]
    end

    Note over Disc: cleanup loop every 30s : 90s idle -> mark unhealthy -> probe -> remove

    opt on dispose
        App->>Disc: DELETE /api/v1/services/{service_id}
    end
```
---

## 6. Identified Issues & Observations

Numbered findings from the source with location references (severity in parentheses).
Items marked **Resolved** have been fixed in code in this revision; items marked
**Documented** are intentional, require platform/architecture changes, or are noted
for future tuning. `flutter analyze` reports no issues in `lib/` after the resolved fixes.

| # | Severity | Status | Finding | Evidence |
|---|---|---|---|---|
| 1 | High (contract) | **Resolved** | Registration payload field mismatch: the player sent `health_check_endpoint` while the server model expects `health_endpoint`. Pydantic previously ignored the unknown key and fell back to `/health` — which coincidentally matched. When the player's real `/health` endpoint changes, the server would probe the wrong path. **Fix:** renamed the JSON key to `health_endpoint` in the model and its generated serializer so the payload now matches the server contract. Server side unchanged. | `lib/models/device_info_model.dart` (`@JsonKey('health_endpoint')`); `lib/models/device_info_model.g.dart` |
| 2 | Medium (bug) | **Resolved** | `deregister()` targeted the **static** `AppConfig.discoveryRegisterEndpoint` (`http://localhost:8006`) instead of the configured backend, so on non-local deployments deregistration hit the wrong host. **Fix:** deregister now builds the URL from `_configService.discoveryServiceUrl`, matching register/heartbeat. | `lib/services/discovery_service.dart` (`deregister`) |
| 3 | Medium (reliability) | **Resolved** | **No registration retry.** If the initial `register()` failed, `initialize()` returned `false`, no heartbeat timer was started, and the player stayed offline indefinitely — despite the misleading "will retry with heartbeat" log. `AppConfig.registrationRetryDelay` was unused. **Fix:** added `_startRegistrationRetry()` — on initial failure a `Timer.periodic` on `AppConfig.registrationRetryDelay` re-runs `register()` and starts the heartbeat once it succeeds; the timer is guarded against duplicates and cancelled in `dispose()`. | `lib/services/discovery_service.dart` (`initialize`, `_startRegistrationRetry`, `dispose`); `lib/config/app_config.dart` |
| 4 | Low (dead code) | **Resolved** | `AppConfig.discoveryRegisterEndpoint` and `AppConfig.discoveryHeartbeatEndpoint` were defined but unused (heartbeat builds its URL from `_configService.discoveryServiceUrl` directly; deregister also now uses the configured URL). **Fix:** removed both getters. | `lib/config/app_config.dart` |
| 5 | Low (latent feature) | **Resolved** | Phase-5 VPN-direct discovery was implemented (`setVpnNodeIp()`, `isVpnConnected`, `discoverTopology()`) but never invoked from the initialization flow. **Fix (metadata-only, VPN info sourced from the Authority):** the player now obtains VPN metadata through the Authority's licensing/enrollment flow and uses it for VPN-direct discovery. Changes: (1) **Authority** — `EnrollInstallationResponse` now returns `primary_node_ip` (resolved from the matrix group's `tag:node`), and `GET /matrix-groups/{id}/nodes` populates node `tags` (`autonomous/ppl-meta-authority/src/api/vpn.py`); (2) **Player** — new `authority_api_client.dart` (activate/enroll/list nodes), `ConfigService` stores VPN metadata (`primaryNodeIp`, `matrixGroupId`, `headscaleServer`, `authKey`), `SimpleSetupScreen` collects an optional Application Key + Installation UUID and calls `/api/v1/vpn/enroll-installation`, `register()` sends `tailscale_ip` in metadata, and `initialize()` invokes `setVpnNodeIp()` + `discoverTopology()` when a primary node IP is configured (exposing `discoveredTopology`); (3) **Discovery** — no code change required (already consumes `tailscale_ip` metadata and serves `?vpn=true` topology). | `lib/services/authority_api_client.dart`; `lib/services/discovery_service.dart`; `lib/services/config_service.dart`; `lib/screens/simple_setup_screen.dart`; `autonomous/ppl-meta-authority/src/api/vpn.py` |
| 6 | Info (design) | **Resolved** | The player registered only as a **service** (`service_type: edge`) via `/api/v1/services/*`, **not** as an edge device via `/api/v1/devices/*` — so device-registry settings did not govern it. **Fix (dual registration):** the player now registers as **both** a service (control/health plane) **and** an edge device (`device_type: signage_player`), so the device registry tracks it (type, capabilities, `tailscale_ip`, VPN reachability). Platform changes: added `signage_player`/`digital_signage` to `EdgeDeviceType`, fixed `register_device`'s `supported_types` validation to derive from the enum, and wired the dead `EDGE_DEVICE_TIMEOUT` (300 s) into `EdgeRegistry` instantiation. Player changes: added edge-device registration (`POST /api/v1/devices/register`), edge-device heartbeat (`POST /api/v1/devices/heartbeat`), and deregistration (`DELETE /api/v1/devices/{id}`) in `SignageDiscoveryService`, plus `isDeviceRegistered`/`deviceRegistrationId` getters. | `ppl-meta-discovery/src/models/service_models.py`; `ppl-meta-discovery/src/services/edge_registry.py`; `ppl-meta-discovery/src/main.py`; `lib/services/discovery_service.dart` |
| 7 | Info (ignored contract) | **Resolved** | The server's recommended `heartbeat_interval` from the registration response was ignored; the player hard-coded `AppConfig.heartbeatInterval`. **Fix:** the player now stores the suggested interval (`_serverHeartbeatInterval`) from `heartbeat_interval` in the response and uses it for the timer, falling back to `AppConfig.heartbeatInterval` when the server omits it. | `lib/services/discovery_service.dart` (`register`, `_startHeartbeat`) |
| 8 | Info (auth) | **Resolved** | Registration and heartbeat carried no credentials and discovery endpoints were open. **Fix (HMAC installation token):** the **Authority** now mints `api_token = HMAC_SHA256(INSTALLATION_AUTH_SECRET, installation_uuid)` and returns it in the `enroll-installation` response (`autonomous/ppl-meta-authority/src/api/vpn.py`). **Discovery** now enforces it via `InstallationAuthMiddleware` (`ppl-meta-discovery/src/auth.py`): it recomputes the token from `X-Installation-Uuid` and rejects mismatches with 401 on `/api/v1/services/*`, `/api/v1/devices/*`, and `/api/v1/discovery/topology` — gated behind `AUTH_ENFORCE` (default off) for safe rollout. **Player** attaches `Authorization: Bearer <token>` + `X-Installation-Uuid` on every discovery request via a Dio interceptor (`SignageDiscoveryService._setupAuthInterceptor`), with the token persisted in `ConfigService` (`installationApiToken`) and supplied through `AuthorityVpnEnrollment.apiToken`. The existing 401/403 defensive handling in `register()` now becomes active once `AUTH_ENFORCE=true`. Shared secret: `INSTALLATION_AUTH_SECRET` env (default `ppl-meta-installation-auth-secret-dev`). | `autonomous/ppl-meta-authority/src/api/vpn.py`; `ppl-meta-discovery/src/auth.py`; `ppl-meta-discovery/src/config.py`; `ppl-meta-discovery/src/main.py`; `lib/services/discovery_service.dart`; `lib/services/config_service.dart`; `lib/services/authority_api_client.dart`; `lib/screens/simple_setup_screen.dart` |
| 9 | Info (timeouts) | **Resolved** | Heartbeat/registration/deregister/topology timeouts were hard-coded magic values in `discovery_service.dart` (heartbeat 5 s, registration 4 s/6 s, deregister 5 s, topology 5 s/8 s). **Fix:** centralized all discovery-service timeouts into named `AppConfig` constants (`discoveryConnectTimeout`, `discoverySendTimeout`, `discoveryReceiveTimeout`, `heartbeatSendTimeout`, `heartbeatReceiveTimeout`, `deregisterSendTimeout`, `deregisterReceiveTimeout`, `topologySendTimeout`, `topologyReceiveTimeout`) and referenced them from `discovery_service.dart`. Behavior is unchanged (same effective values), but they are now a single source of truth to tune. The platform-side 5 s `aiohttp` health-probe timeout remains a server-settings concern. | `lib/config/app_config.dart`; `lib/services/discovery_service.dart` |

---

## 7. Appendix — Code Reference Index

| Symbol | Location |
|---|---|
| `SignageDiscoveryService` | `lib/services/discovery_service.dart` |
| `initialize()` | `discovery_service.dart` (register + start heartbeat) |
| `register()` | `discovery_service.dart:111` |
| `sendHeartbeat()` | `discovery_service.dart:201` |
| `_startHeartbeat()` | `discovery_service.dart:264` |
| `deregister()` | `discovery_service.dart:274` |
| `dispose()` | `discovery_service.dart:307` |
| `discoverTopology()` (latent) | `discovery_service.dart:54` |
| `SignageHttpServer` (`/health`) | `lib/services/http_server.dart` |
| `ConfigService` (backend IP / port) | `lib/services/config_service.dart` |
| `AppConfig` (intervals/endpoints) | `lib/config/app_config.dart` |
| `DeviceInfoHelper` (id + local IP) | `lib/utils/device_info_helper.dart` |
| Startup + init wiring | `lib/main.dart` (`StartupScreen`, `InitializationScreen`) |
| `SimpleSetupScreen` (IP + port entry) | `lib/screens/simple_setup_screen.dart` |
| `register_service` (platform) | `ppl-meta-discovery/src/services/service_registry.py:52` |
| `update_heartbeat` (platform) | `service_registry.py:113` |
| `_check_service_health` | `service_registry.py:323` |
| `_cleanup_stale_services` | `service_registry.py:364` |
| `deregister_service` (platform) | `service_registry.py:158` |
| `HeartbeatRequest` / `RegistrationRequest` / `ServiceInfo` | `ppl-meta-discovery/src/models/service_models.py` |
| Discovery settings (`PORT`, timeouts) | `ppl-meta-discovery/src/config.py` |
| Service endpoints | `ppl-meta-discovery/src/main.py` |