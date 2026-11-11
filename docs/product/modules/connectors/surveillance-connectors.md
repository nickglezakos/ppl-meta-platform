# Surveillance & Network Connectors

## Purpose

This document describes, at a high level and with **generic technical specifications**, how the
platform connects to third-party physical hardware for video surveillance:

- **IP cameras** — fixed dome, bullet, and PTZ models from any vendor.
- **NVR / VMS systems** — centralized recording and video-management platforms.
- **Network infrastructure** — industrial and managed Ethernet switches.

The intent is to keep hardware-specific figures approximate. Any camera, NVR, or switch that exposes
the standard protocols listed below should be connectable, regardless of vendor.

---

## Connection Model Overview

The platform treats physical devices as one edge of a larger pipeline:

```
Physical layer                 Platform services
─────────────────              ─────────────────────────────
IP camera ──┐
            ├──► Ethernet/PoE ──► switch ──► network
NVR / VMS ──┘                                 │
                                              ▼
                              ┌─────────────────────────────┐
                              │ eyenet-cameras            │  device registry + config
                              │ eyenet-edge-camera        │  stream capture/ingest client
                              │ eyenet-gateway            │  API entry / routing
                              │ eyenet-media              │  recording & storage
                              │ eyenet-vision             │  analysis / detection
                              │ eyenet-orchestrator       │  workflow coordination
                              └─────────────────────────────┘
```

Devices are reached over standard IP protocols; the platform does not require vendor-specific
physical wiring beyond ordinary Ethernet.

## 1. IP Cameras

Applies to fixed dome, bullet, and PTZ IP cameras from any vendor.

### Generic connectivity requirements

| Aspect | Generic specification |
|--------|-----------------------|
| Physical interface | 10/100/1000 Mbps Ethernet (RJ45), typically powered via PoE (802.3af) or PoE+ (802.3at) |
| Addressing | Static IP or DHCP, reachable on the camera VLAN/subnet |
| Discovery / control | ONVIF Profile S (and optionally Profile T) for discovery, configuration, PTZ, and streaming setup |
| Video streaming | RTSP (primary), optionally HTTP/MJPEG or vendor SDKs |
| Video codecs | H.264 (baseline/main/high), H.265/HEVC where supported |
| Audio | Optional two-way audio over RTSP/ONVIF where supported by the camera |
| Resolution | Generic HD range (e.g. 1 MP to 4K), chosen by deployment requirements |
| Frame rate / bitrate | Configurable per stream; main and substream profiles |
| Authentication | Username/password, optionally digest; credentials stored in the camera registry |
| Security | HTTPS/RTSP over TLS where available; MAC/IP allow-listing optional |

### How the platform connects

1. The camera is added in the platform camera registry (`eyenet-cameras`) with its IP, credentials,
   model/serial, and stream URLs.
2. ONVIF discovery (or manual entry) identifies available stream profiles and capabilities.
3. `eyenet-edge-camera` (or an equivalent ingestion component) opens RTSP pull sessions for the
   main and/or substream.
4. Video frames are captured, decoded, and forwarded into `eyenet-vision` for detection/analysis.
5. Snapshots and recordings are persisted through `eyenet-media`.

> **Note:** A camera that only speaks ONVIF/RTSP works the same regardless of vendor; no vendor
> lock-in is required.

## 2. NVR / VMS Systems

Applies to centralized NVR/VMS recording platforms from any vendor.

### Generic connectivity requirements

| Aspect | Generic specification |
|--------|-----------------------|
| Discovery / control | ONVIF Profile S / Profile T when available; otherwise the VMS vendor API or SDK |
| Video access | RTSP/RTSP-over-TLS streams re-exported by the NVR for live and recorded video |
| Event ingestion | HTTP(S) push/webhooks, ONVIF event subscriptions, or vendor event/API polling |
| Time sync | NTP recommended across cameras, NVR, and platform to keep timestamps consistent |
| Authentication | Per-system API keys or service accounts with least-privilege access |
| Network | Reachable over the same management/data network; typically higher bandwidth on uplinks |

### How the platform connects

1. The NVR/VMS is registered as a **source system** rather than as individual cameras when recording
   is centralized on the NVR.
2. The platform enumerates available cameras/channels through ONVIF or the vendor API.
3. Live and recorded streams are pulled over RTSP (or the vendor API) using the NVR as a proxy.
4. Events (motion, analytics, alarms) are subscribed to so the platform can trigger workflows in
   `eyenet-orchestrator`.
5. Recorded clips may remain on the NVR and be referenced by URL, or be copied into
   `eyenet-media` for long-term retention.

> **Note:** If the NVR does not expose ONVIF/RTSP, the fallback is the vendor SDK/API. The platform
> abstracts this behind a connector so the rest of the system sees a uniform camera/stream model.

## 3. Network Infrastructure

Applies to industrial and managed Ethernet switches from any vendor.

### Generic connectivity requirements

| Aspect | Generic specification |
|--------|-----------------------|
| Access ports | Gigabit Ethernet for cameras/NVR, often with PoE/PoE+ (and PoE++/UPoE for PTZ/heaters) |
| Uplink ports | SFP/SFP+ fiber or copper uplinks to the core network |
| VLANs | Separate VLANs recommended: camera/VMS VLAN, management VLAN, and platform VLAN |
| QoS | Prioritize video traffic (e.g. DSCP/CoS marking) to protect streams from congestion |
| PoE budget | Verify total switch PoE budget exceeds the sum of powered device requirements |
| Management | SNMP, SSH, HTTPS for monitoring and configuration |
| Environment | Industrial/rugged rating where deployed in non-climate-controlled areas |
| Redundancy | Optional: RSTP, link aggregation, or dual uplinks for resilience |

### How the platform connects

1. Cameras and NVR are wired to switch access ports with PoE enabled.
2. The switch trunk/uplink connects to the network segment that hosts the platform services.
3. Traffic is segmented by VLAN and shaped with QoS so video streams and control traffic are stable.
4. The switch itself is monitored through standard network tooling; the platform only requires
   IP reachability to the devices, not direct switch integration.

## Connector Module Design

The **eyenet-connectors** module is the single integration layer that manages every third-party
hardware connection described in this document. It abstracts IP cameras, NVR/VMS systems, and network switches behind one common interface, so the
rest of the platform only ever works with normalized devices and streams.

### Responsibilities

| Responsibility | Description |
|----------------|-------------|
| Device registry | Maintains the canonical list of connected hardware, its type, addressing, and capabilities |
| Credential handling | Stores and rotates device credentials in the platform secret store; secrets are never logged |
| Protocol adapters | Translates ONVIF, RTSP, HTTP/MJPEG, and vendor APIs/SDKs into a unified device model |
| Stream fan-out | Bridges live and recorded streams to `eyenet-edge-camera` and `eyenet-vision` |
| Event ingestion | Subscribes to NVR/VMS motion/analytics/alarm events and forwards them to `eyenet-orchestrator` |
| Health & retry | Monitors connection health, auto-reconnects, and publishes status to `eyenet-gateway` |

### Connector types

The module ships three adapter families, selected automatically by device type:

1. **Camera connector** — ONVIF discovery and RTSP streaming for IP cameras.
2. **NVR/VMS connector** — ONVIF/RTSP re-export, plus a vendor API/SDK fallback.
3. **Network connector** — read-only SNMP/SSH access to switches for status and PoE telemetry.

### Common connector interface

Every adapter implements the same interface:

    connect()      – establish the session using stored credentials
    discover()     – enumerate cameras, channels, or ports
    streams()      – list available live/recorded stream URLs
    subscribe()    – subscribe to motion/analytics/alarm events
    health()       – report connection and stream health
    disconnect()   – cleanly tear down the session

Because every adapter shares this interface, adding a new vendor model is usually
configuration-only: the device is registered and bound to the matching adapter, with no changes
to upstream services.

---

## Data Flow Summary

```
Camera ──RTSP/ONVIF──► Switch ──► Network ──► eyenet-edge-camera ──► eyenet-vision
   │                                                                         │
   └──NVR/VMS ──► ONVIF/RTSP/API ─────────────────────────────────────────────┤
                                                                             ▼
                                                        eyenet-media (recording)
                                                        eyenet-orchestrator (workflows)
```

---

## Security & Operational Notes

- Use a dedicated, segmented VLAN for cameras/NVR; do not expose devices directly to the internet.
- Use least-privilege credentials per device; rotate passwords/API keys regularly.
- Enable NTP across cameras, NVR, and platform for consistent timestamping in analysis.
- Prefer RTSP-over-TLS / HTTPS where supported; otherwise restrict to the trusted LAN.
- Monitor PoE budget and port bandwidth to avoid stream drops on busy switch stacks.

---

## Related Components

| Component | Role |
|-----------|------|
| `eyenet-cameras` | Camera/source registry, settings, and connection configuration |
| `eyenet-edge-camera` | Stream capture and ingest client for devices |
| `eyenet-gateway` | API entry point and routing for the platform |
| `eyenet-media` | Recording, storage, and media lifecycle |
| `eyenet-vision` | Detection and analysis of ingested frames |
| `eyenet-orchestrator` | Workflow coordination and event-driven processing |

---

## Addendum: Reference Hardware Configurations

The tables below give concrete, commonly deployed reference models per device class. Exact specs
vary by model and firmware, so treat the figures as representative rather than exact.

### Cameras

| Vendor / model family | Form factor | Power | Control | Streaming | Typical resolution |
|-----------------------|-------------|-------|---------|-----------|--------------------|
| Avigilon H4A HD Dome | Fixed dome | PoE / PoE+ | ONVIF Profile S | RTSP | HD (~2–4 MP) |
| Avigilon H4A Bullet | Fixed bullet | PoE / PoE+ | ONVIF Profile S | RTSP | HD |
| TP-Link Tapo (C-series) | Fixed dome/bullet, some pan/tilt | PoE, USB, or Wi-Fi | ONVIF (select models), Tapo app | RTSP | HD / 2K |
| Axis Communications (P-series) | Fixed/PTZ dome & bullet | PoE / PoE+ | ONVIF Profile S/T, VAPIX | RTSP | HD to 4K |
| Hikvision (DS-2CD series) | Fixed dome/bullet | PoE / PoE+ | ONVIF Profile S | RTSP | HD to 4K |

### NVR / VMS

| Vendor / platform | Recording | Control / API | Streaming out | Notes |
|-------------------|-----------|---------------|---------------|-------|
| Avigilon Control Center 7 | Centralized VMS | Vendor SDK/API, ONVIF | RTSP re-export | Reference in this doc |
| Hikvision (DS-76xx NVR / iVMS) | Embedded NVR | ISAPI / ONVIF | RTSP | — |
| Dahua (NVR / SmartPSS) | Embedded NVR | HTTP API / ONVIF | RTSP | — |
| TP-Link VIGI (NVR / VIGI app) | Embedded NVR | ONVIF (select models), VIGI API | RTSP | — |

### Network / PoE

| Vendor / model family | Class | PoE | Uplink | Management |
|-----------------------|-------|-----|--------|------------|
| Cisco Catalyst IE-3300-8P2S-E | Industrial managed switch | PoE / PoE+ | SFP fiber | CLI / SNMP / HTTPS |
| TP-Link Omada (JetStream) | Managed switch | PoE / PoE+ | SFP / SFP+ | Omada SDN / web |
| Ubiquiti UniFi (Switch series) | Managed switch | PoE / PoE+ | SFP / SFP+ | UniFi controller |
| Netgear (AV / ProSAFE) | Managed switch | PoE / PoE+ | SFP | Web / SNMP |

All of the above reduce to the same vendor-neutral protocols (Ethernet/PoE, ONVIF, and RTSP)
described earlier, so the platform's single connector approach applies across vendors.

---

## Connecting Hardware to eyenet

This section gives high-level, step-by-step instructions for bringing any of the referenced
hardware systems online. The steps assume the `eyenet-connectors` module is running and that the
operator is signed in with the credentials described in the next section.

### Prerequisites

- Hardware is powered, addressed (static IP or DHCP reservation), and reachable from the eyenet
  network.
- The device, NVR, or switch credentials are known (see "Credentials Required at Each Level").
- The site's eyenet licence matrix includes the connector tier for the device type.

### Connect an IP camera

1. In the eyenet console, open **Connectors → Add device → Camera**.
2. Enter the camera IP/hostname and its ONVIF/RTSP credentials.
3. Run discovery to read the model, capabilities, and available stream profiles.
4. Select the main and substream profiles to ingest.
5. Save. The connector opens RTSP sessions and hands frames to `eyenet-vision`.
6. Confirm the camera shows **Healthy** in the connector status panel.

### Connect an NVR / VMS

1. Open **Connectors → Add device → NVR/VMS**.
2. Choose the connection mode: ONVIF/RTSP (recommended) or vendor API/SDK.
3. Enter the NVR address and its API/service credentials.
4. Enumerate channels and map them to eyenet cameras, or leave them as NVR-managed sources.
5. Enable event subscription (motion, analytics, alarms) so `eyenet-orchestrator` can react.
6. Save and verify both live and recorded streams are reachable.

### Connect a network switch

1. Open **Connectors → Add device → Switch**.
2. Enter the management IP and read-only SNMP/SSH credentials.
3. The connector discovers ports, PoE state, and VLAN membership for monitoring only.
4. Confirm the switch appears in the status panel; no video ingestion is performed.

### Generic flow

    Register device → select adapter → provide credentials → discover → map streams/channels → verify health

---

## Credentials Required at Each Level

The connector needs credentials at every layer of the stack. Store each in the platform secret
store and never commit them to configuration files or code.

### 1. Device-level credentials

| Level | Credential needed |
|-------|-------------------|
| IP camera | ONVIF/RTSP username and password (a least-privilege view/stream account) |
| NVR / VMS | API key or service account for the vendor API, or an ONVIF/RTSP account |
| Network switch | Read-only SNMP community/credentials or an SSH account for status polling |

### 2. eyenet platform credentials

| Level | Credential needed |
|-------|-------------------|
| System owner | A single eyenet **system owner** account (email + strong password + MFA) that owns the site and authorizes new device bindings |
| Connector service | A per-site connector API token issued by `eyenet-gateway`, used by `eyenet-connectors` to register devices and publish events |

> **Note:** The system owner credential is the root of trust for the site. It is used only to
> authorize device onboarding and licence changes; day-to-day device access uses the lower-privilege
> accounts listed above.

### 3. Premium Eyenet software licence with multiplatform enabled matrix

eyenet gates connector capabilities through a its **Premium** sofware licence which unlocks all three connector families across web, desktop, and
mobile clients:

| Tier | Camera connector | NVR/VMS connector | Network connector | Multiplatform |
|------|------------------|-------------------|-------------------|---------------|
| Basic | RTSP only | — | — | Web only |
| Standard | ONVIF + RTSP | ONVIF/RTSP | Read-only SNMP | Web + desktop |
| Premium | ONVIF + RTSP + vendor SDK | ONVIF + RTSP + vendor SDK/API | SNMP + SSH telemetry | Web + desktop + mobile |

> **Note:** The Premium, multiplatform-enabled licence is required to use the vendor API/SDK
> adapters and to manage connectors from mobile clients. Without it, ONVIF/RTSP-only camera access
> still works, but NVR vendor-API integration and mobile management are disabled.

---

## Short Conclusion

The platform connects to IP cameras, NVR/VMS systems, and the supporting network through
**standard, vendor-neutral protocols** — primarily Ethernet/PoE, ONVIF, and RTSP, with a vendor
API/SDK fallback for NVR/VMS. Specific reference hardware is listed in the Addendum.




