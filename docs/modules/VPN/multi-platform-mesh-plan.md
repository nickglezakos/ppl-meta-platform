# EyeNet Multi-Platform Mesh — Implementation Plan

**Status:** Design (implementation plan)
**Date:** 2026-08-30
**Related docs:**
- `docs/modules/VPN/vpn-mapping-and-reachability-plan.md` (device mapping + reachability)
- `docs/modules/VPN/implementation-roadmap-headscale-vpn.md` (original VPN roadmap)
- `docs/guides/headscaleVPN/headscaleVPN guide.md` (authority + headscale production)
- `docs/authority/eyenet-vpn-mesh-implementation-guide.md` (original blueprint)
- `docs/matrix/ppl-meta-matrix.md` (matrix ↔ VPN mesh)

---

## 1. Goals

1. Multiple **platform installations** can coexist under one licence / matrix / mesh, each as an independent **compute module** with its own DB, discovery registry and media library — **no shared DB**.
2. Devices/apps are **linked to one platform at a time**, and can be **manually flipped** to another platform later.
3. Every app (platform, device, aggregator) is its own VPN node — **one node per app** — enrolled **once over the internet**, then discovers peers by mesh IP (`100.64.0.XX`) and connects **directly over LAN when co-located** (no internet / no shared-LAN dependency afterward).
4. A separate **read-only analytics aggregator** (follow-up) gathers metrics from all platforms and presents a unified logical view.

---

## 2. Architecture

```
                      Authority (internet, shared coordination point)
                      ┌─────────────────────────────────────────────┐
                      │ licence / entitlements / matrix             │
                      │ client ↔ platform assignment (the only link)│
                      └─────────────────────────────────────────────┘
                              ▲  enroll (internet, once)
                              │  resolve platform / flip
        ┌─────────────────────┴──────────────────────────────────────┐
        │                  Headscale mesh (100.64.0.0/10)            │
        │   one node per app, tagged; WireGuard direct / DERP        │
        └───────┬──────────────────────┬──────────────────────┬───────┘
          Platform A (tag:platform)  Platform B (tag:platform)  Analytics (tag:analytics)
          own DB / registry / media  own DB / registry / media  read-only aggregator (follow-up)
                │                         │
          device (tag:client)        device (tag:client)
```

**Key principle:** the **mesh only provides connectivity**. Platform *state* is never shared; the **Authority** owns the *only* shared state (licence + the client↔platform link). Platforms are interchangeable "compute modules" that clients are pointed at.

---

## 3. Tag taxonomy

| Tag | Dimension | Meaning | Assigned by | Status |
|---|---|---|---|---|
| `tag:install-<hex(uuid)>` | identity | Immutable installation identity (hex of `installation_uuid`) | Authority enroll | ✅ done |
| `tag:installation` | role | Generic "is an installation" | Authority enroll | ✅ existing |
| `tag:platform` | role | Platform compute module (own DB/registry) | Authority enroll (`node_type=platform`) | ⬜ new |
| `tag:client` | role | Leaf device/app (signage, camera, presence, …) | Authority enroll | ✅ existing |
| `tag:analytics` | role | Read-only aggregator/observer | Authority enroll (`node_type=analytics`) | ⬜ follow-up |
| `tag:camera` | type | Edge camera (`ppl-meta-edge-camera`) | Authority enroll | ✅ existing |
| `tag:signage` | type | Signage player (Android + RPi) | Authority enroll | ⬜ new |
| `tag:node` | legacy | Generic node (superseded by `tag:platform`) | Authority enroll | ⚠️ deprecated |
| `tag:matrix-<uuid>` | matrix | Matrix group membership | Authority enroll | ✅ existing |

Rules:
- **Role** tags (`tag:platform` / `tag:client` / `tag:analytics`) are mutually exclusive and drive ACL + hub-and-spoke.
- **Type** tags (`tag:camera` / `tag:signage`, future `tag:presence`…) are additive and drive discovery filtering ("all signage", "all cameras").
- **Hardware** (RPi vs Android) is **not** a tag — it already lives in the device's discovery metadata (`platform`, `platform_version`, `supported_codecs`).
- The **hostname** is the mutable human name (MagicDNS `<hostname>.eyenet-vpn.local`); identity is the **node key** (→ stable `100.64.0.XX`), and the mapping key is **`tag:install-<hex(uuid)>`**. Renaming never breaks discovery.
- `tag:platform` doubles as the **discovery mechanism** for the analytics aggregator: "enumerate all platforms in this matrix" = filter `/nodes` by `tag:platform`.

---

## 4. Client ↔ platform assignment mechanism

**Owner:** the Authority — it already owns `installation_uuid`/entitlements, is internet-reachable, and is the natural single coordination point.

### 4.1 Storage (Authority `src/core/storage.py`)

Add idempotent columns to `installations` (mirrors the existing `_ensure_column` + `matrix_group_id` migration):

| Column | Type | Purpose |
|---|---|---|
| `platform_node_id` | TEXT | Headscale node id of the linked platform |
| `platform_tailscale_ip` | TEXT | Mesh IP of the linked platform |
| `platform_hostname` | TEXT | Human name of the linked platform |
| `platform_assigned_at` | TIMESTAMP | When the link was (re)established |

(Optional: an `installation_platform_assignments` history table for audit — defer.)

### 4.2 API (Authority `src/api/vpn.py`)

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /api/v1/vpn/installations/{uuid}/platform` | link/assign | Body `{platform_node_id or platform_tailscale_ip}` |
| `GET /api/v1/vpn/installations/{uuid}/platform` | resolve | Returns current `platform_tailscale_ip` / `hostname` |
| `DELETE /api/v1/vpn/installations/{uuid}/platform` | unlink | Clear the link |
| `GET /api/v1/vpn/platforms` | list | Filter `/nodes` by `tag:platform` |

### 4.3 Enroll integration

`POST /api/v1/vpn/enroll-installation` already returns `{auth_key, matrix_group_id, tags, ...}`. Add:
- `node_type: "platform" | "client" | "analytics"` — so the node is tagged `tag:platform` / `tag:client` / `tag:analytics`.
- `platform_tailscale_ip` in the response — the client's *assigned* platform (or `null` when none yet). The client connects to this platform after enrollment.

### 4.4 Licence limits (commercial gating)

Gating the number of platform nodes is a clean commercial lever ("how many compute modules can this licence run?").

- **Storage:** add `max_platform_nodes INTEGER` to `entitlements` (or a JSON `licence_limits` map that also later holds `max_devices`, `max_cameras`, …). Keep it data-driven (tier → limits) rather than a hardcoded enum.
- **Enforcement (Authority):** when `enroll-installation` receives `node_type: "platform"`, count existing `tag:platform` nodes in that matrix (deduped by `tag:install-<hex>`) and reject the enroll when the count already meets `max_platform_nodes`.
- **Edge cases:** re-enrolling the *same* platform (same `tag:install-<hex>` / node key) must not double-count; deleting a platform node frees a slot.

---

## 5. Manual flip

**Flip = re-link + fresh sync, not state migration.** The client's historical state stays on the old platform; the analytics aggregator (follow-up) provides the cross-platform *view*.

Flow:
1. Owner calls `POST /api/v1/vpn/installations/{uuid}/platform` with the new platform (via UI or API).
2. Authority updates `installations.platform_tailscale_ip`.
3. Client re-polls `GET /api/v1/vpn/installations/{uuid}/platform` (or re-enrolls) → gets the new platform IP.
4. Client re-registers with the new platform's discovery, then pulls its playlist fresh from the new platform.

Start with **manual** flip only. Automatic failover (Authority health-probes `tag:platform` nodes and reassigns) is a later layer.

---

## 6. Discoverability

Per-app mesh identity + hub-and-spoke discovery through the platform.

1. **One node per app** — each app embeds `package:tailscale` (per-process `tsnet`) and enrolls itself:
   - first launch → Authority `/enroll-installation` → `auth_key` → `Tailscale.instance.up(hostname, authKey, controlUrl)` → own `100.64.0.XX`.
   - subsequent launches → `Tailscale.instance.up()` reconnects with the persisted node key (no internet needed after first enroll).
2. **Mesh-routed HTTP** — the app uses `Tailscale.instance.http.client` for outbound calls (discovery registration, playlist pull), so they traverse the mesh.
3. **Register `tailscale_ip`** — the app writes its real `100.64.0.XX` into discovery metadata (`metadata['tailscale_ip']`), replacing the broken `NetworkInterface.list()` detection (which never sees the VPN `tun` on Android).
4. **Backend resolves VPN-first** — the media resolver already tries `tailscale_ip` first, LAN second (with a curl fallback for the OpenVPN-filtered Mac). ✅ done.
5. **Hub-and-spoke** — clients only talk to their *assigned* platform (from §4); the platform reaches clients by their `tailscale_ip`. Cross-segment app↔app (internet node ↔ LAN-only node on a different LAN) is out of scope; if needed later, a **subnet router** on the platform closes that gap.

---

## 7. Implementation phases (ordered)

### Phase 1 — Tag set + ACL
- Add `tag:platform` / `tag:analytics` / `tag:signage` to the Authority tag set (and to the ACL `tagOwners` declaration once ACLs move off allow-all); keep `tag:camera`; deprecate `tag:node` in favour of `tag:platform`.
- Files: `autonomous/ppl-meta-authority/src/api/vpn.py`, `headscale/acl.json`.

### Phase 2 — Authority client↔platform assignment + licence limits
- Add the four `installations` columns (§4.1) via idempotent migration.
- Add the four endpoints (§4.2) + `platform_tailscale_ip` / `node_type` in enroll (§4.3).
- Add `max_platform_nodes` to `entitlements` and enforce at platform enrollment (§4.4).
- Files: `autonomous/ppl-meta-authority/src/core/storage.py`, `src/api/vpn.py`.
- Accept: `GET .../platform` returns the assigned platform; `POST .../platform` flips it; a platform enroll past `max_platform_nodes` is rejected.

### Phase 3 — Platform self-registration with `tag:platform`
- Platform nodes enroll/retag as `tag:platform`; media registers its own `tailscale_ip` (already done in `ppl-meta-media/src/main.py`).
- Accept: `/api/v1/vpn/platforms` lists platform nodes with their mesh IPs.

### Phase 4 — Signage player own-node (one node per app)
- Add `tailscale: ^0.5.0` to `ppl-meta-signage-simple-player`.
- Enroll once → `Tailscale.instance.up(...)` → persist node key.
- Route pull + discovery through `Tailscale.instance.http.client`.
- Register `tailscale_ip` in discovery.
- Files: `pubspec.yaml`, `config_service.dart`, `discovery_service.dart`, `signage_api_client.dart`, new `tailscale_service.dart`.
- Accept: player has its own `100.64.0.XX`, pulls playlists over the mesh (LAN-direct when co-located).

### Phase 5 — Manual flip (UI + client re-resolve)
- Expose the assignment endpoints in the Authority admin UI + platform UI.
- Client re-resolves its platform on a schedule / on demand, then re-registers + fresh sync.
- Accept: reassign a client → it moves to the new platform without touching the old platform's DB.

### Phase 6 — (follow-up) Read-only analytics aggregator
See §8.

---

## 8. Follow-up: read-only analytics aggregator (brief)

A separate EyeNet service, its own mesh node tagged `tag:analytics`, under the same licence/matrix.

- **Discovers** all `tag:platform` nodes via `/api/v1/vpn/platforms` (or Headscale `/nodes` filtered by `tag:platform`).
- **Gathers** metrics either by pulling each platform's metrics API, or by platforms pushing events to it.
- **Namespaces** data by platform (platform A's `playlist-123` ≠ platform B's `playlist-123`), then presents a **unified logical view** (a projection, never a source of truth).
- **No writes** to operational state — it is the cross-platform *view*, which is exactly what keeps the "separate platforms / no shared DB" model clean.
- **Multi-LAN reachability:** the aggregator only ever reaches *platform* nodes (`tag:platform`), never the device nodes. Each platform collects its own LAN-only devices directly over LAN and exposes aggregated metrics over the mesh. So two platforms on *different* LANs — each with LAN-only devices — are both covered as long as the **platforms and the aggregator have internet**; the device nodes need no internet.

### 8.1 ETL design (incremental + backfill + upsert)

The aggregator runs a **read-only ETL pipeline** into its own DB (a projection, never a source of truth).

- **Extract** — pull from each `tag:platform`'s metrics API (or receive pushes), keyed by platform.
- **Transform** — namespace every fact by `platform_id`; version the event shape to tolerate schema drift.
- **Load** — upsert into the aggregator store.

| Requirement | Building block |
|---|---|
| Catch changes over time | `updated_since` watermark + incremental sync |
| Fix a bounded past window | Backfill window + idempotent upsert |
| Handle platform deletions | Deleted feed / key reconciliation |

- **Watermark** — per-platform high-watermark on `updated_at` (not `created_at`); fetch `updated_since=<ts>`.
- **Idempotent upsert** — natural key `(platform_id, entity_type, entity_id)`; re-processing a batch never duplicates.
- **Backfill** — configurable lookback (e.g. 7–30 days), triggered on schedule (reconciliation) or on demand (after a platform fix/gap).
- **Tombstones** — `updated_since` alone misses deletes; platforms must expose a `deleted_since` feed, or the aggregator reconciles keys over the window.

**Platform-side requirement:** each platform exposes change-detection endpoints, e.g.
`GET /metrics/events?updated_since=<ts>&entity_type=<…>&limit=<…>` and `GET /metrics/events/deleted?since=<ts>`.

**Caveats:** idempotency is mandatory; "update batches" = re-sync the projection to match the platform, never edit analytics rows independently.

---

## 9. Current state (done vs pending)

| Item | Status |
|---|---|
| `tag:install-<hex>` + `installation_uuid` in `/nodes` | ✅ done (deployed) |
| Matrix group persistence + `installations`↔`entitlements` link | ✅ done (deployed) |
| Media VPN-first resolver + curl fallback | ✅ done |
| Pull endpoint `/api/v1/signage/devices/pull` (media + gateway) | ✅ done |
| Gateway VPN admin surface (`provider=headscale`) | ✅ done |
| Headscale ACL fixed (broken symlink → allow-all) | ✅ done |
| `tag:platform` / `tag:analytics` / `tag:signage` (role + type tags) | ✅ Phase 1 |
| Client↔platform assignment | ✅ Phase 2 |
| Licence limits (`max_platform_nodes`) | ✅ Phase 2 |
| Platform self-registration | ✅ Phase 3 |
| Signage player own-node (per-app tailnet) | ✅ Phase 4 |
| Manual flip UI + client re-resolve | ⬜ Phase 5 |
| Analytics aggregator | ⬜ Phase 6 |

---

## 10. Open decisions / notes

- **Flip is manual first**; automatic failover is deferred.
- **One node per app** (confirmed) — multiple `100.64.0.XX` per physical device is expected and fine.
- **Hostname is mutable**; identity (`node key`) and mapping (`installation_uuid` → `tag:install-*`) are immutable.
- The **Authority is the only shared state**; platforms and the analytics aggregator never share operational DBs.
- **Licence limits** gate platform-node count (and later device/camera counts) commercially, enforced at enrollment by the Authority.


