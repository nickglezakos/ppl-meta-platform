# EyeNet VPN Mesh — Device Mapping & Reachability Plan

**Status:** Design (audit of current implementation + gap plan)
**Date:** 2026-08-29
**Related docs:**
- `docs/guides/headscaleVPN/headscaleVPN guide.md` (authority + headscale production guide)
- `docs/authority/eyenet-vpn-mesh-implementation-guide.md` (original blueprint)
- `docs/matrix/ppl-meta-matrix.md` (matrix ↔ VPN mesh)
- `docs/modules/VPN/implementation-roadmap-headscale-vpn.md`

---

## 1. Business requirement

1. A platform owner buys an EyeNet licence.
2. The licence provides **Matrix access** backed by the **Headscale VPN mesh**.
3. After a **one-time onboarding** (which requires internet), the platform must:
   - know the **VPN IPs** (`100.64.x.x`) of all enrolled devices, and
   - be able to **discover and connect** to them **over the VPN**, with **no internet** and **no LAN** dependency.

---

## 2. Target architecture

```
Onboarding (internet, once)
  Device ──POST /api/v1/vpn/enroll-installation──▶ Authority
  Authority ──{auth_key, matrix_group_id, tags, primary_node_ip}──▶ Device
  Device ──tailscale up --login-server https://vpn.eyenet-vision.com --auth-key … --accept-routes──▶ Headscale
  Headscale assigns 100.64.x.x + tags

Steady state (no internet, VPN only)
  Platform ──GET /api/v1/vpn/nodes  (or /matrix-groups/{id}/nodes)──▶ Authority
  Authority returns per-node: hostname, tailscale_ip, online, node_id, tags, installation_uuid
  Platform ──connect to device @ tailscale_ip:port over WireGuard──▶ Device
```

The **Authority + Headscale side already exists**:

| Piece | Location | Status |
|---|---|---|
| Enrollment | `autonomous/ppl-meta-authority/src/api/vpn.py` → `enroll-installation` | ✅ |
| Node list | `vpn.py` → `GET /api/v1/vpn/nodes`, `GET /api/v1/vpn/matrix-groups/{id}/nodes` | ✅ (see gap) |
| ACL sync | `autonomous/ppl-meta-authority/src/services/vpn_acl_service.py` | ✅ |
| Headscale config | `autonomous/ppl-meta-authority/headscale/config.yaml` | ✅ |
| Gateway VPN provider | `ppl-meta-gateway/src/services/headscale_provider.py` + `vpn_service.py` + `api/v1/vpn.py` | ✅ (default `none`) |
| Discovery VPN fields | `ppl-meta-discovery/src/models/service_models.py` (`tailscale_ip`/`tailscale_port`) | ✅ |

The gaps are in **device↔node mapping** and **Android reachability**.

---

## 3. Gap 1 — Identity mapping (no device ↔ VPN-node link)

### 3.1 Current state

There is no deterministic link between a signage device and its Headscale node.

| Domain | Identifier | Observed value |
|---|---|---|
| Discovery (player) | `device_id` / `name` | `android-TKQ1.221114.001` / `signage-simple-android-TKQ1.221114.001` |
| Player (config) | `installation_uuid`, `matrix_group_id` | known to player (`config_service.dart`) |
| Headscale node | `hostname`, `node_id`, `tailscale_ip`, `tags` | `eyenet-android-nick7`, numeric id, `100.64.0.2`, `tagged-devices` |
| Authority `/nodes` | `installation_uuid` | **hard-coded `""`** |

Concretely:

- `autonomous/ppl-meta-authority/src/api/vpn.py` → `list_vpn_nodes` builds `VpnNodeInfo(installation_uuid="", …)` — the field is never populated.
- The device's Tailscale hostname (`eyenet-android-nick7`) is manual and unrelated to `device_id`/`installation_uuid`.
- The player (`discovery_service.dart`) only puts `tailscale_ip` into discovery metadata when `DeviceInfoHelper.getLocalIpAddress()` returns a `100.x` address. On Android, `NetworkInterface.list()` does **not** expose the VPN `tun` interface, so this never happens — discovery shows `tailscale_ip=null`.

### 3.2 Proposed fix (two parts)

**Part A — Authority: embed installation identity in node tags.**

In `enroll-installation`, add a per-installation tag to the pre-auth key:

```
tags = ["tag:installation", "tag:matrix-<uuid>", "tag:<node|client>", "tag:install-<installation_uuid>"]
```

Then in `GET /api/v1/vpn/nodes` and `/matrix-groups/{id}/nodes`, derive `installation_uuid` from the node's tags (strip the `tag:install-` prefix). This reuses the existing tag/ACL model and needs **no new table**. (Alternative: a `vpn_nodes` table keyed `installation_uuid → node_id` populated on enrollment.)

**Part B — Player: register its own VPN IP from the Authority.**

The player already has the client to do this:
- `ppl-meta-signage-simple-player/lib/services/authority_api_client.dart` → `listMatrixGroupNodes(matrixGroupId)` returns each node's `installationUuid` + `tailscaleIp`.
- `config_service.dart` holds `authorityInstallationUuid` + `vpnMatrixGroupId`.

After enrollment, the player should:
1. `listMatrixGroupNodes(vpnMatrixGroupId)`,
2. find its own node by `installationUuid`,
3. read that node's `tailscaleIp`,
4. register in discovery:
   - `host` = LAN IP (`192.168.20.56`)
   - `metadata['tailscale_ip']` = `100.64.0.2` (and `tailscale_port` = 8009)

This makes discovery surface a real `tailscale_ip`, which the media resolver (already VPN-first) consumes unchanged.

---

## 4. Gap 2 — Android reachability (separate from mapping)

### 4.1 Current state (measured)

| Test | Result |
|---|---|
| `tailscale ping eyenet-android-nick7` | ✅ pong (tunnel + tailscaled work) |
| `curl http://100.64.0.2:8009/health` | ❌ **Connection refused** |
| `curl http://192.168.20.56:8009/health` | ✅ healthy (LAN) |

So even with a correct mapping and a real `tailscale_ip`, a **push** to the Android player over the VPN fails.

**Cause:** the signage player is a normal Android app; its Flutter HTTP server is bound to the device's **default network (Wi-Fi)**. The Tailscale VPN `tun` is a separate routing domain owned by the Tailscale app, so inbound VPN connections to a third-party app's port are not delivered (Android `VpnService` limitation).

### 4.2 Options

- **A. Pull model (recommended for Android players).** The player already performs outbound discovery + heartbeat over VPN successfully. Make playlist sync/control *pulled* by the player (it polls the platform over VPN) instead of the platform pushing to the player. Partial pull path already exists (`SyncService.syncPlaylists()` / `signage_api_client.syncPlaylist()`).
- **B. Subnet router.** A Linux/Mac node advertises `192.168.20.0/24` into the mesh; the platform reaches the player's LAN IP *through* the VPN. Works, but adds infra and still depends on LAN IPs.
- **C. Tailscale serve / SSH on the device.** Expose the player's port via `tailscaled` (SSH port-forward / `serve`). Device-side setup; non-trivial on Android.

**Recommendation:** A (pull) for Android signage players; keep push-over-VPN for Linux-capable nodes (gateways/cameras), which do serve over the VPN correctly.

---

## 5. Concrete change list (ordered)

1. **Authority** — `autonomous/ppl-meta-authority/src/api/vpn.py`:
   - Add `tag:install-<installation_uuid>` to enrollment pre-auth-key tags.
   - Derive and return `installation_uuid` in `/nodes` and `/matrix-groups/{id}/nodes`.

2. **Player** — `ppl-meta-signage-simple-player/lib/`:
   - `discovery_service.dart`: after enrollment, resolve own `tailscale_ip` via `AuthorityApiClient.listMatrixGroupNodes` and register `host=LAN, tailscale_ip=<100.x>` (service + edge-device + heartbeat metadata).
   - (The `authority_api_client.dart` + `config_service.dart` pieces already exist.)

3. **Discovery** — no code: verify it now surfaces `tailscale_ip` per device (it already reads `metadata['tailscale_ip']`).

4. **Media** — already done this session: `signage_service.py` resolver is VPN-first, with a `curl` fallback for LAN; it will now prefer the real `100.x`.

5. **Player sync path** — implement the VPN **pull** path for playlists/control (or keep the LAN-via-curl stopgap until then).

6. **Gateway** — set `VPN_PROVIDER=headscale` + `HEADSCALE_URL`/`HEADSCALE_API_KEY` to enable the `/api/v1/vpn/*` admin surface.

---

## 6. Files referenced

| Repo / file | Role |
|---|---|
| `autonomous/ppl-meta-authority/src/api/vpn.py` | enrollment + node list + online status (mapping gap) |
| `autonomous/ppl-meta-authority/src/services/vpn_acl_service.py` | per-matrix ACL tagging |
| `autonomous/ppl-meta-authority/headscale/config.yaml` | `100.64.0.0/10`, MagicDNS, ACL path |
| `ppl-meta-gateway/src/services/headscale_provider.py` | Headscale REST provider |
| `ppl-meta-gateway/src/services/vpn_service.py` | provider factory (`none` default) |
| `ppl-meta-gateway/src/api/v1/vpn.py` | `/api/v1/vpn/*` admin API |
| `ppl-meta-discovery/src/models/service_models.py` | `tailscale_ip`/`tailscale_port` fields |
| `ppl-meta-media/src/services/signage_service.py` | VPN-first endpoint resolver (implemented) |
| `ppl-meta-signage-simple-player/lib/services/authority_api_client.dart` | `listMatrixGroupNodes` (used by plan step 2) |
| `ppl-meta-signage-simple-player/lib/services/config_service.dart` | stored `installation_uuid` / `matrix_group_id` |
| `ppl-meta-signage-simple-player/lib/services/discovery_service.dart` | discovery registration (needs own-tailscale-IP registration) |
| `ppl-meta-signage-simple-player/lib/utils/device_info_helper.dart` | `getLocalIpAddress()` (Android can't see VPN tun) |


