# VPN Mesh Functionality in Discovery Service and in Online Remote Access

**Status:** Issue tracker (current state audit + open bugs)
**Date:** 2026-09-04
**Related docs:**
- `docs/modules/VPN/multi-platform-mesh-plan.md` (client ↔ platform assignment)
- `docs/modules/VPN/vpn-mapping-and-reachability-plan.md` (device mapping + reachability)
- `docs/modules/VPN/implementation-roadmap-headscale-vpn.md` (original VPN roadmap)
- `docs/guides/headscaleVPN/headscaleVPN guide.md` (authority + headscale production)

---

## 1. Requirement summary

A leaf device (signage player, edge camera, mobile camera) must be able to:

1. **Discover its platform at enrollment time, one internet round-trip.**
   The enrollment token response returns, together in one payload:
   - `platform_tailscale_ip` — the platform's mesh (`100.64.x.x`) IP (stable, internet-independent after enrollment),
   - `platform_local_ip` — the platform's **current** local LAN IP (fast on-LAN path),
   - `platform_hostname` — human name of the platform.

2. **Know its own VPN (mesh) IP** — so it can be reached remotely over the internet.

3. **Run locally by default, remotely on demand.**
   Normal operation uses the local LAN IP; a device working outside the local network uses the mesh IP over the internet.

4. **Recover the platform's local IP when it changes** (router restart, DHCP renewal).
   Two-layer recovery, no re-enrollment:
   - **Fast path:** re-resolve the cached `platform_local_ip` from the Authority (single internet round-trip).
   - **On-demand (Variant A):** when the cached local IP is actually unreachable, the device pulls the platform's *current* local IP directly from the platform over the VPN mesh, then reports the fresh value back to the Authority to refresh the shared cache.

5. **A process that refreshes the platform's local IP at the source.**
   The platform reports its current local LAN IP to the Authority (on enroll, on boot, and periodically), so the Authority always has an up-to-date value to hand out.

---

## 2. Current state of the codebase vs. requirements

| # | Requirement | Status | Where / notes |
|---|---|---|---|
| 1a | Token returns `platform_tailscale_ip` | ✅ Done | `EnrollInstallationResponse` in `autonomous/ppl-meta-authority/src/api/vpn.py` |
| 1b | Token returns `platform_local_ip` | ✅ Done (deployed `2.25.68`) | New field on `EnrollInstallationResponse` + `_issue_enrollment()` |
| 1c | Token returns `platform_hostname` | ✅ Done | Was already present |
| 2 | Device knows its own mesh IP | ✅ Done | Per-app `tailscale up`; player persists `tailscale_ip` |
| 3a | Platform reports its local IP to Authority | 🟡 Code written, **not deployed** | `report_platform_local_ip()` in `ppl-meta-node/src/services/vpn_service.py` |
| 3b | Platform reports on enroll + boot | 🟡 Code written, **not deployed** | `enroll_once()` calls `report_platform_local_ip()` on both paths |
| 3c | Platform reports periodically | 🟡 Code written, **not deployed** | `ppl-meta-node/src/main.py` background task |
| 4 | Authority stores `platform_local_ip` | ✅ Done (deployed) | `installations.platform_local_ip` column + `set_installation_platform_local_ip()` |
| 5 | Device re-resolves platform IP from Authority | 🟡 Code written, **not wired/auto** | `POST /api/v1/vpn/resolve-platform` + `ConfigService.refreshPlatformEndpoints()` exist, nothing calls the refresh automatically |
| 6 | Player prefers LAN, falls back to VPN | 🟡 Code written, **APK not rebuilt** | `ConfigService.platformHost` = `platform_local_ip → backendIP → vpn_platform_tailscale_ip` |
| 7 | Media advertises LAN URL first | 🟡 Code written, **not deployed** | `_resolve_media_service_url()` in `ppl-meta-media/src/services/signage_service.py` |
| 8 | Leaf pulls current local IP on demand (Variant A) | 🔵 Not implemented (design) | Needs platform endpoint `GET /api/v1/vpn/local-ip` + leaf fallback/retry wiring |
---

## 3. Reference — how the two IPs are discovered

### 3.1 Enrollment payload (Authority → device)

`POST /api/v1/vpn/enroll-installation` and `POST /api/v1/vpn/enroll-token` both funnel through `_issue_enrollment()` and return (leaf nodes only):

```jsonc
{
  "auth_key": "tskey-auth-…",
  "headscale_server": "https://vpn.eyenet-vision.com",
  "matrix_group_id": "…",
  "installation_uuid": "…",
  "primary_node_ip": "100.64.x.x",
  "api_token": "…",                    // HMAC(secret, installation_uuid) — discovery auth
  "platform_tailscale_ip": "100.64.x.x", // mesh IP (remote)
  "platform_hostname": "…",
  "platform_local_ip": "192.168.x.x"     // LAN IP (local) — NEW
}
```

### 3.2 Platform → Authority local-IP report

`POST /api/v1/vpn/installations/{installation_uuid}/platform/local-ip`
(auth: `application_key`)

```jsonc
{
  "application_key": "lic-…",
  "platform_local_ip": "192.168.x.x",
  "platform_tailscale_ip": "100.64.x.x",  // optional, self-links on re-enroll
  "platform_hostname": "…"                // optional
}
```

### 3.3 Device → Authority re-resolve

`POST /api/v1/vpn/resolve-platform`
(auth: `api_token` = HMAC of the installation UUID)

```jsonc
{ "installation_uuid": "…", "api_token": "…" }
```

Returns `InstallationPlatformResponse` (node id, mesh IP, hostname, **local IP**, assigned_at).

### 3.4 Player host resolution order (`ConfigService.platformHost`)

```
1. platform_local_ip          (auto-discovered from token — LAN)
2. backendIP                  (manually configured — LAN)
3. vpn_platform_tailscale_ip  (mesh IP — remote/off-LAN fallback)
```

`discoveryServiceUrl` (`:8006`), `mediaServiceUrl` (`:8000`), and `gatewayUrl` (`:8080`) all derive from `platformHost`.

### 3.5 Media service advertised URL

`_resolve_media_service_url()` resolves, in order:
1. discovery's LAN `host`/`port` for the media service,
2. discovery's `tailscale_ip`/`tailscale_port` (remote fallback),
3. the local Tailscale daemon,
4. `http://localhost:8000`.

### 3.6 On-demand local-IP recovery (Variant A — leaf pulls from the platform)

When the cached `platform_local_ip` is missing or unreachable, the leaf recovers it
from the platform itself over the VPN mesh, instead of trusting a possibly-stale
Authority cache:

```
1. Leaf tries the LAN path (platform_local_ip).
2. On connection failure (timeout / refused) → leaf calls the platform over the mesh:
   GET http://<platform_tailscale_ip>:<node_port>/api/v1/vpn/local-ip
   → returns { platform_local_ip, platform_tailscale_ip }
3. Returned IP differs → leaf updates its cache and retries the LAN path.
4. Returned IP unchanged → platform is LAN-unreachable from this vantage point;
   the leaf stays on the VPN mesh IP.
5. Leaf reports the fresh value back to the Authority (POST …/platform/local-ip)
   so other devices benefit from the refreshed shared cache.
```

> New platform endpoint required: `GET /api/v1/vpn/local-ip` on `ppl-meta-node`
> (the detection logic `_get_local_ip()` already exists; it only needs exposing
> over HTTP).

---

## 4. Current issues and bugs

> Severity: 🔴 Critical · 🟠 High · 🟡 Medium · 🔵 Low

### 🔴 #1 — Playlist sync still returns HTTP 400 (same symptom as before)

- **Symptom:** `SignageApiClient.syncPlaylist` POSTs `/api/v1/signage/devices/pull` and gets a `400`.
- **Root cause:** `main.dart:230` builds the client with `baseUrl = gatewayUrl`, and `gatewayUrl` resolves to `http://100.64.0.22:8080`. That host is **headscale's HTTP API on Hetzner**, not the gateway — hence the 400.
- **Why it's unchanged:** `platformHost` falls back to `vpn_platform_tailscale_ip = 100.64.0.22` because `platform_local_ip` is null and `backendIP` is empty (see #3, #4, #5).
- **Status:** Open.

### 🔴 #2 — Discovery heartbeat still goes to Hetzner `100.64.0.22:8006`

- **Symptom:** `Heartbeat URL: http://100.64.0.22:8006/api/v1/services/heartbeat`.
- **Root cause:** `discovery_service.dart:518` uses `discoveryServiceUrl`, which resolves to the same wrong `platformHost` (`100.64.0.22`).
- **Status:** Open (same root as #1).

### 🔴 #3 — `platform_tailscale_ip` points at Hetzner, not the local platform

- **Symptom:** The installation's assigned platform is `100.64.0.22` = `eyenet-node-hetzner` (authority + headscale), which is **not** the on-prem compute module.
- **Root cause:** The local box was never enrolled as the `tag:platform` node. In the dev topology the platform role was (incorrectly) assigned to the Hetzner node.
- **Impact:** Even the "VPN fallback" in `platformHost` points at the wrong host.
- **Status:** Open. Fix = enroll the local platform as `tag:platform` so `platform_tailscale_ip` becomes the local box's mesh IP.

### 🟠 #4 — Platform never reports its local LAN IP

- **Symptom:** `installations.platform_local_ip` stays NULL → the token returns `platform_local_ip: null`.
- **Root cause:** The report logic (`report_platform_local_ip()`) is written but the updated `ppl-meta-node` has **not been deployed/restarted** on the local box, and its `EYENET_INSTALLATION_UUID` / `EYENET_APPLICATION_KEY` env vars are not confirmed set.
- **Status:** Open (code complete, deployment pending).

### 🟠 #5 — Player `backendIP` is empty (no manual LAN fallback)

- **Symptom:** `platformHost` has no `backendIP` to fall back to, so it lands on the VPN IP.
- **Root cause:** Onboarding via token does not populate `backendIP`; the operator was expected to type the local platform LAN IP manually.
- **Status:** Open. Once #4 is fixed, `platform_local_ip` supersedes this; a manual fallback is still useful.

### 🟡 #6 — Player APK not rebuilt with the new `platformHost` / `platform_local_ip` code

- **Symptom:** The running binary may predate `ConfigService.platformHost`, `platformLocalIp`, and the `platform_local_ip` token parsing.
- **Status:** Open (rebuild + install required). Only the Authority (`2.25.68`) was deployed this session.

### 🟡 #7 — No automatic reachability switch between LAN and VPN

- **Symptom:** `platformHost` always picks LAN first. A device that is actually remote (LAN IP unreachable) will not automatically retry over the mesh IP.
- **Gap:** There is no reachability probe / per-request fallback from `platform_local_ip` → `platform_tailscale_ip`.
- **Status:** Implemented in player — `ConfigService.ensurePlatformReachable()` + `preferVpnHost`, and `SignageApiClient` LAN→VPN baseUrl switch on connection failure. Rebuild APK to pick up.

### 🟡 #8 — Media LAN-first advertisement has no remote rewrite path

- **Symptom:** `_resolve_media_service_url()` now advertises the LAN IP first. LAN devices benefit, but a **remote** device receiving a playlist with LAN stream URLs can no longer reach them.
- **Gap:** No client-side host rewrite (replace `platform_local_ip` with `platform_tailscale_ip`) when the device is remote.
- **Status:** Implemented in player — `ConfigService.rewriteMediaUrlForReachability()` used by `SignagePlayerEngine` when `preferVpnHost` is set. Rebuild APK to pick up.

### 🟡 #9 — Device refresh (`refreshPlatformEndpoints`) is not wired into any lifecycle

- **Symptom:** `POST /resolve-platform` (server) and `ConfigService.refreshPlatformEndpoints()` (player) exist, but nothing calls the refresh automatically (not on boot, not before sync).
- **Impact:** A router/DHCP-driven LAN IP change will not self-heal on the device without manual action.
- **Status:** Implemented — called from startup (`main.dart` → `ensurePlatformReachable`) and pre-sync (`SyncService.syncPlaylists`). Rebuild APK to pick up.

### 🔵 #10 — `vpnPrimaryNodeIp` also points at Hetzner in the dev topology

- **Symptom:** `discovery_service.dart` Phase-5 topology discovery uses `_vpnNodeIp = vpnPrimaryNodeIp`, which resolves to the Hetzner primary node (`100.64.0.22`) in the current dev setup.
- **Impact:** `GET http://100.64.0.22:8006/api/v1/discovery/topology?vpn=true` hits the wrong host.
- **Status:** Mitigated in player — `vpnDiscoveryNodeIp` prefers `vpn_platform_tailscale_ip` over legacy `vpnPrimaryNodeIp`. Full fix still needs correct `tag:platform` enrollment (#3).

### 🔵 #11 — `resolve-platform` depends on the device having stored the real `installation_uuid` + `api_token`

- **Symptom:** The HMAC check `_issue_installation_token(installation_uuid)` requires the device to have persisted the real installation UUID (not the matrix group id) and the matching `api_token`.
- **Status:** Working for the token-redemption path (player stores both); verify the app-key path also persists both, otherwise re-resolve returns 403.

### 🔵 #12 — No on-demand local-IP pull from the platform (Variant A not implemented)

- **Symptom:** A leaf whose cached `platform_local_ip` is stale/unreachable can only fall back to the VPN mesh IP; it cannot fetch the platform's *current* local IP on demand.
- **Gap:** No `GET /api/v1/vpn/local-ip` endpoint on the platform, and no leaf-side "try local → on failure pull → retry" wiring.
- **Status:** Implemented — platform `GET /api/v1/vpn/local-ip` on `ppl-meta-node` (`leaf_router`); player `pullPlatformLocalIpFromMesh()` + `ensurePlatformReachable()`. Deploy node + rebuild APK.

---

## 5. Deployment / fix sequencing (to close the critical issues)

1. Deploy updated `ppl-meta-node` on the **local platform**, with `EYENET_INSTALLATION_UUID` + `EYENET_APPLICATION_KEY` set → it enrolls as `tag:platform`, gets its own mesh IP, and reports its LAN IP (#4, and fixes #3).
2. Verify the Authority now holds `platform_local_ip` (and the correct `platform_tailscale_ip`) for that installation.
3. Rebuild + install the player APK (#6).
4. Re-onboard / re-redeem the token so the player receives and persists `platform_local_ip` (#1, #2, #5).
5. Follow-ups: wire `refreshPlatformEndpoints()` into startup/pre-sync (#9), add LAN↔VPN reachability fallback (#7), remote stream-URL rewrite (#8), and implement Variant A on-demand pull (#12: platform `GET /api/v1/vpn/local-ip` + leaf fallback/retry).


