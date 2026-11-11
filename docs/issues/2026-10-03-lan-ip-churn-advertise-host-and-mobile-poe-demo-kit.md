# Issue: LAN IP churn (`ADVERTISE_HOST` / `platform_local_ip`) and mobile PoE demo kit (RPi / mini PC)

**Date:** 2026-10-03  
**Status:** Open (two-phase)  
**Severity:** 🟠 High for leaf reachability after DHCP change; 🟡 Medium for demo-kit productization  
**Reporter:** Product / ops discussion (Mac local + lab advertise-host education)

---

## Summary

EyeNet installations expose services to phones, signage, edge cameras, and RTSP/PoE cameras using a **LAN IP** that DHCP can change when a customer router reboots. Mesh (Headscale/Tailscale) IPs for a given licence / installation are comparatively stable, but day-to-day on-LAN clients still need a correct local address.

This issue tracks **two levels** of work:

1. **Level A (software — finish first):** Complete the designed **report + resolve `platform_local_ip`** loop (and optional discovery self-update of advertise host) so leaf devices recover after LAN IP changes without re-enrollment and without a dedicated network appliance.
2. **Level B (hardware kit — after Level A):** Define how to use an **RPi or mini PC** as a **mobile demo / site edge** that provides a **stable LAN** (static addressing) for PoE cameras such as TP-Link models in the VIGI / 113-class family, so demos are not hostage to venue DHCP.

Do **not** invent a “dedicated private LAN per `LICxxxxx` via L2 bridge” as the primary fix for DHCP churn. That is a different networking product. Stable **installation identity** is the mesh + Authority mapping; stable **demo camera addressing** is a controlled LAN on the kit.

---

## Background: two addresses, two jobs

| Address | Typical form | Stability | Used for |
|---------|--------------|-----------|----------|
| Mesh IP | `100.64.x.x` (Headscale) | Stable per enrolled node / installation | Remote reachability, VPN fallback |
| LAN IP | `192.168.x.x` / site LAN | Can change on router reboot / DHCP | Fast on-LAN path, RTSP cameras, `ADVERTISE_HOST` for phones on same Wi‑Fi |

**Installer / lab ops today:** `ADVERTISE_HOST` in `~/eyenet-platform/.env` (or Windows `.env.windows`) is the IP discovery/node advertise to LAN clients. When it goes stale, phones get wrong service URLs and node can return **HTTP 400 `Invalid host header`**. Ops fix: DHCP reservation, or `artifacts/lab-fix-advertise-host.sh`.

**Product design (already written):**  
`docs/product/modules/VPN/vpn-mesh-discovery-and-remote-access.md` — platform reports `platform_local_ip` to Authority; leaves re-resolve; prefer LAN, fall back to mesh.

**Day-to-day lab guide:**  
`docs/documentation/guides/ubuntu-lab-eyenet-day-to-day.md` §6 (LAN IP change).

---

## Level A — Finish report + resolve `platform_local_ip` (and/or discovery self-update)

### Goal

After a router reboot or DHCP renewal that changes the platform’s LAN IP:

- No re-enrollment of leaves  
- Authority holds a fresh `platform_local_ip` for the installation (`LICxxxxx` / install UUID)  
- Leaves recover via Authority and/or VPN pull from the platform  
- Optionally, discovery/`ADVERTISE_HOST` on the host updates itself so new LAN clients are not stuck on a stale advertise IP

### Current state (from VPN mesh discovery audit)

| Item | Status | Notes |
|------|--------|-------|
| Token returns `platform_tailscale_ip` / hostname | Done | Authority enroll |
| Token returns `platform_local_ip` | Done (Authority) | Field exists; value null if platform never reports |
| Authority stores `platform_local_ip` | Done | `installations.platform_local_ip` |
| Platform reports local IP (enroll / boot / periodic) | Code written, deploy/wire incomplete | `report_platform_local_ip()` in node VPN service + background task |
| Leaf auto re-resolve from Authority | Partial | `resolve-platform` + client refresh exist; not reliably auto-triggered |
| Leaf on-demand pull from platform over mesh (Variant A) | Design | Needs `GET /api/v1/vpn/local-ip` on node + leaf retry wiring |
| Discovery rewrites compose/bridge hosts to advertise IP | Exists | Needs correct advertise source when LAN IP moves |
| Discovery / node self-update of advertise host from detected LAN IP | Gap | Still often pinned by static `.env` `ADVERTISE_HOST` |

### Acceptance criteria (Level A)

1. **Platform → Authority:** On enroll, boot, and on a periodic interval, the on-prem platform reports current non-bridge LAN IP (+ optional mesh IP / hostname) with `application_key`.
2. **Authority → leaf:** Enrollment and `resolve-platform` return the latest `platform_local_ip`.
3. **Leaf recovery:** If LAN host fails (timeout / refused), leaf automatically:
   - re-resolves via Authority, and/or  
   - pulls current LAN IP from platform over mesh (`Variant A`), updates cache, retries LAN, then falls back to mesh if still unreachable.
4. **Shared cache refresh:** When a leaf learns a newer LAN IP, it reports back so other devices benefit.
5. **Advertise / discovery (optional but recommended with A):**  
   - Either keep `ADVERTISE_HOST` as ops override, **or**  
   - discovery/node periodically detect host LAN IP and refresh advertise + discovery registrations when IP changes (still refuse Docker `172.16–31.x` bridges).  
   Recreate TrustedHost-dependent processes if allow-list is process-start frozen.
6. **Docs / Stage path:** Deploy via Stage 1 → 2 → 3; update operator guide: DHCP reservation remains best practice; software recovery is the safety net.

### Explicit non-goals (Level A)

- Replacing Headscale/mesh with a custom “per-licence LAN”  
- Requiring an RPi at every customer site just to fix DHCP churn  
- Changing lab Compose DNS (`ppl-meta-*`) defaults for Mac local Python (separate local-env loader)

### Related code / docs

- `docs/product/modules/VPN/vpn-mesh-discovery-and-remote-access.md`  
- `ppl-meta-node` — `report_platform_local_ip`, TrustedHost / `ADVERTISE_HOST` in users/platform services  
- `ppl-meta-discovery` — `get_advertise_host()`, `resolve_service_hosts()`  
- `artifacts/lab-fix-advertise-host.sh`  
- Authority VPN enroll / `platform/local-ip` / `resolve-platform` APIs  

### Suggested implementation order

1. Deploy + verify platform local-IP reporting (env: installation UUID + application key).  
2. Wire leaf auto-refresh on LAN failure (Authority resolve).  
3. Add platform `GET …/vpn/local-ip` + Variant A leaf path.  
4. Discovery/node advertise self-heal (detect LAN IP change → update advertise + reregister; recreate node if TrustedHost requires it).  
5. Rebuild / ship leaf APKs and edge agents that include the recovery path.

---

## Level B — RPi / mini PC mobile kit with stable LAN for PoE cameras (demo)

### Goal

Support a **portable EyeNet demo** (trade show, customer site visit, “platform in a bag”) where:

- PoE cameras (e.g. **TP-Link VIGI / 113-class** RTSP cameras) need **stable LAN IPs** and often PoE power  
- Venue Wi‑Fi / DHCP is untrusted or will change overnight  
- Operators should not run `lab-fix-advertise-host` every time the demo moves  

This is **not** the primary fix for Level A. It is a **kit architecture** that *uses* Level A (mesh identity per licence) while giving cameras a **controlled L2/L3 segment** with static addressing.

### Problem statement (demo / mobile)

| Need | Why |
|------|-----|
| Static camera IPs | RTSP URLs, NVR-style config, and EyeNet camera records break if cameras get new DHCP leases |
| PoE | Many TP-Link VIGI / 113-class units expect PoE; phone power banks are not enough |
| Predictable gateway / DNS for cameras | Cameras talk to the platform (or NVR path) on a known subnet |
| Portable compute | RPi 5 / mini PC runs edge agent and/or full demo stack (or bridges to a laptop/lab licence) |
| Licence identity | Demo installation still enrolls as a real `LICxxxxx` / install UUID on mesh for remote support |

### Recommended kit shape (conceptual)

Treat the RPi/mini PC as a **site edge / demo gateway**, not as a mysterious “licence LAN registry” in discovery:

```text
[PoE switch] —— static IPs —— [TP-Link PoE cameras]
      |
      +—— [RPi / mini PC]  (optional DHCP server ON THIS SEGMENT ONLY,
      |                     or all-static; hosts discovery advertise /
      |                     edge agent / optional full stack)
      |
      +—— uplink to venue Wi‑Fi / LTE router (NAT) for internet + Headscale
              |
         phones / laptop UI on venue Wi‑Fi OR on demo SSID
```

**Stable LAN for cameras:** a small dedicated subnet (e.g. `10.50.0.0/24`) where:

- Cameras: reserved static IPs (`10.50.0.11` …)  
- RPi: `.1` gateway + optional dnsmasq  
- Platform services (if on the RPi) advertise `ADVERTISE_HOST=10.50.0.1` **to clients on that segment**  
- Uplink NAT for internet / mesh; do not rely on venue DHCP for camera addresses  

**Phones on venue Wi‑Fi:** either join a demo SSID attached to the kit, or use **mesh** to the demo installation (Level A). Mixing “cameras on kit LAN” + “phones only on venue Wi‑Fi without routing/mesh” will fail — document the chosen client path.

### How this relates to Level A

| Concern | Level A | Level B kit |
|---------|---------|-------------|
| Platform LAN IP changes at customer site | Software recovery | Prefer static / reservation on kit subnet so it rarely changes |
| Camera RTSP IP stability | Out of scope (camera DHCP) | In scope — static IPs on kit PoE LAN |
| Licence / install identity | Mesh + Authority | Same — enroll kit (or host PC) under demo `LICxxxxx` |
| Discovery advertise | Self-heal + Authority | Pin `ADVERTISE_HOST` to kit’s stable LAN IP for on-kit clients |

### Acceptance criteria (Level B)

1. **BOM draft:** RPi 5 (or mini PC), PoE switch (802.3af/at as required by camera), TP-Link VIGI / 113-class (or equivalent) cameras, cabling, optional LTE/Wi‑Fi uplink.  
2. **Network runbook:** static IP table; how to set camera IP via TP-Link VIGI config; RPi `ADVERTISE_HOST` / discovery; uplink vs isolated mode.  
3. **EyeNet config:** cameras registered with stable RTSP URLs; demo installation enrolled; mesh works for remote assist.  
4. **Operator checklist:** power-on order, verify camera ping, verify discovery `:8006`, UI on kit IP or mesh, what to do if venue blocks outbound VPN.  
5. **Boundary:** kit does **not** replace Level A for normal customer installs that sit on customer DHCP; kit is for **mobile / controlled-LAN** demos (and optionally hardened branch sites that want the same pattern).

### Explicit non-goals (Level B)

- Shipping a custom “per-licence L2 bridge” inside `ppl-meta-discovery`  
- Requiring every production install to include an RPi  
- Using Docker bridge IPs (`172.18.x`) as advertise or camera targets  

### Open design questions

1. Does the RPi run **full platform** (compose Stage-3-like) or only **edge + RTSP forward** to a laptop/lab host?  
2. Should phones join a **kit SSID** (simplest LAN path) or stay on venue Wi‑Fi + mesh?  
3. PoE budget: how many 113-class cameras per switch / injector?  
4. Image / SD card: golden image vs installer script for the kit.  
5. Licence model: one demo `LICxxxxx` per kit vs shared lab licence (security / Authority policy).

---

## Decision guide

| Scenario | Do this |
|----------|---------|
| Customer router rebooted, platform IP moved, phones/cameras lost platform | **Level A** (plus DHCP reservation as ops hygiene) |
| Lab dual-boot / take-home IP change (`192.168.9.x` ↔ `192.168.1.x`) | Ops: `lab-fix-advertise-host.sh` until Level A self-heal exists |
| Trade-show / van demo with PoE TP-Link cameras | **Level B** kit with static camera LAN; still enroll mesh (Level A) |
| Tempted to add “RPi registers a LAN per LIC in discovery” as the only fix | Reject as primary; finish Level A; use Level B only for controlled-LAN kits |

---

## References

- `docs/product/modules/VPN/vpn-mesh-discovery-and-remote-access.md`  
- `docs/product/modules/VPN/multi-platform-mesh-plan.md`  
- `docs/documentation/guides/ubuntu-lab-eyenet-day-to-day.md` (§6 advertise host / IP change)  
- `docs/documentation/deployment/lab-machines.md`  
- `artifacts/lab-fix-advertise-host.sh`  
- Edge camera notes: `docs/documentation/guides/installation-auth-client-rollout.md` (edge camera HMAC)  

---

## Tracking checklist

### Level A

- [ ] Deploy platform `report_platform_local_ip` (enroll + boot + periodic) with install UUID / application key  
- [ ] Verify Authority returns non-null `platform_local_ip` on enroll / resolve  
- [ ] Wire leaf auto refresh on LAN failure  
- [ ] Implement `GET /api/v1/vpn/local-ip` + Variant A  
- [ ] Discovery/node advertise self-heal on detected LAN IP change  
- [ ] Ship leaf clients (APK / edge) with recovery path  
- [ ] Operator docs: reservation + software recovery  

### Level B

- [ ] Approve BOM (RPi/mini PC + PoE switch + TP-Link camera model)  
- [ ] Write kit network runbook (static IPs, advertise host, uplink)  
- [ ] Decide full-stack-on-kit vs edge-only  
- [ ] Golden image or install script  
- [ ] One successful end-to-end demo: camera RTSP → detection/recording → UI  
