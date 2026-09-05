# VPN Mesh Discovery + Remote Access — Mobile Camera

**Status:** Implemented (WP1–WP5, WP7). WP6 (backend payload) pending cameras API schema.
**Date:** 2026-09-05
**Reference:** `docs/modules/VPN/vpn-mesh-discovery-and-remote-access.md`

---

## 1. Goals

The mobile camera is a **leaf** on the EyeNet mesh. It must be able to:

1. **Discover its platform at enrollment** — one internet round-trip via an
   enrollment token returns the assigned platform's mesh IP, current LAN IP, and
   hostname (no LAN IP typing required).
2. **Know its own mesh IP** — so it can be reached remotely over the internet.
3. **Run locally by default, remotely on demand** — LAN first, mesh over the
   internet when off-site.
4. **Recover a changed platform LAN IP** — re-resolve from the Authority (fast)
   and, via Variant A, pull the current local IP directly over the mesh.
5. Keep working against the platform-hosted gateway/discovery for
   registration, heartbeats, and streaming.

## 2. How the player does it (reference)

`ppl-meta-signage-simple-player` implements all of this in:

- `lib/services/config_service.dart` — `platformHost` (LAN→backend→mesh),
  `preferVpnHost`, `refreshPlatformEndpoints()`, `pullPlatformLocalIpFromMesh()`,
  `ensurePlatformReachable()`, `rewriteMediaUrlForReachability()`.
- `lib/services/tailscale_service.dart` + `tailscale_http_adapter.dart` —
  embedded per-app Tailscale node.
- `lib/services/authority_api_client.dart` — `enroll-token` redemption.
- `lib/screens/simple_setup_screen.dart` — token onboarding.
- `lib/main.dart` — boot: Tailscale up + `ensurePlatformReachable`.

The camera mirrors these, adapted to `package:http` and `AppLogger`.

## 3. What was added to `ppl_meta_mobile_camera`

| File | Purpose |
|------|---------|
| `lib/services/platform_config_service.dart` | Central host resolution (LAN-first), VPN metadata, reachability (Authority refresh + Variant A pull), URL rewrite, reset. 🌟 core |
| `lib/services/authority_api_client.dart` | `enroll-token` / `enroll-installation` redemption, parses `EnrollInstallationResponse`. |
| `lib/services/tailscale_service.dart` | Embedded per-app Tailscale node (own mesh IP, tailnet HTTP). |
| `lib/services/tailscale_http_adapter.dart` | dio→tailnet adapter (for dio-based clients). |
| `lib/services/discovery_config_service.dart` | `getDiscoveryUrl()` now resolves via `PlatformConfigService` when enrolled. |
| `lib/services/auto_camera_registration_service.dart` | Gateway URL prefers the resolved platform host. |
| `lib/main.dart` | Boot: best-effort Tailscale up + `ensurePlatformReachable()`. |
| `lib/features/authentication/screens/simple_setup_screen_new.dart` | **Join VPN mesh** enrollment-token section. |
| `test/platform_config_service_test.dart` | Unit tests (host precedence, URL rewrite, onboarding). |
## 4. Behavior

### Enrollment (Setup screen → “Join the VPN mesh”)
1. Paste the one-time token → `AuthorityApiClient.redeemEnrollmentToken(token, node_type: 'mobile')`.
2. Persist full metadata via `saveVpnMetadata(...)`:
   `auth_key`, `headscale_server`, `matrix_group_id`, `primary_node_ip`,
   `api_token`, `platform_tailscale_ip`, `platform_local_ip`, `platform_hostname`.
3. `TailscaleService.initialize()` brings up the camera's own mesh node and
   persists `tailscale_ip`.
4. `ensurePlatformReachable()` resolves the platform host (LAN first).
5. Discovery + registration now use the enrolled host automatically.

### Host resolution (`platformHost`)
Precedence: `platform_local_ip` → manual `backend_ip` → `platform_tailscale_ip`.
`markLanUnreachable()` switches to the mesh IP on LAN failure;
`markLanReachable()` clears it.

### LAN-IP self-heal
- `refreshPlatformEndpoints()`: `POST /api/v1/vpn/resolve-platform` (Authority) —
  one internet round-trip at boot / before operations.
- `pullPlatformLocalIpFromMesh()` (Variant A): `GET http://<mesh>:8001/api/v1/vpn/local-ip`.
- `ensurePlatformReachable()`: probe gateway (:8080/health) → refresh → Variant A → mesh fallback.

### Remote URL rewrite
`rewriteUrlForReachability(url)` swaps LAN hosts (own `platform_local_ip`,
`backend_ip`, RFC1918 ranges) for the platform mesh IP when `preferVpnHost`.

## 5. Unit tests

`test/platform_config_service_test.dart`:
- LAN-first precedence and VPN fallback.
- `markLanReachable` / `markLanUnreachable` toggling.
- Discovery/gateway URL derivation, `vpnDiscoveryNodeIp`.
- Remote URL rewrite vs. LAN (no-rewrite) vs. public hosts.
- `skipOnboarding`.

Run: `flutter test test/platform_config_service_test.dart`

Note: `test/auto_camera_registration_test.dart` and
`test/device_identifier_service_test.dart` fail to load because they define no
`main()` — pre-existing, unrelated to this work.

## 6. WP6 — advertising the camera's own mesh IP (pending backend schema)

The camera should include `tailscale_ip` (own mesh) alongside its LAN IP when
registering / heartbeating so the platform can reach it remotely. This requires
confirming/extending the cameras API payload; leave the fields optional so the
backend ignores unknown keys. The telemetry is already available via
`PlatformConfigService.tailscaleIp`.

## 7. Deployment notes / prerequisites

- Authority already returns `platform_local_ip` / `platform_tailscale_ip`
  (deployed). The `resolve-platform` endpoint requires the device to have
  persisted the real `installation_uuid` + `api_token` (see VPN doc issue #11) —
  the token path stores both.
- Variant A (`GET /api/v1/vpn/local-ip` on `ppl-meta-node`) must be deployed.
- The embedded `tailscale` package requires Dart SDK `>=3.10.4`; current toolchain
  (Dart 3.12.2) satisfies it. Falls back gracefully if the runtime is unsupported.
- `node_type` for the camera is `mobile` (verify ACL tag with the Authority).

## 8. Success criteria

- [ ] Redeem token once → camera connects without typing a LAN IP.
- [ ] On-LAN traffic uses `platform_local_ip`; off-site uses `platform_tailscale_ip`.
- [ ] Platform DHCP change self-heals via Authority refresh and/or Variant A.
- [ ] Own `tailscale_ip` persisted and (once WP6 lands) sent to the backend.
- [ ] Reset clears VPN + discovery + credentials.
| `pubspec.yaml` | Added `tailscale: ^0.5.0`. |