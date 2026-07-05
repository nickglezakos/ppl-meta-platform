# Door Entrance Use Case — Hardware Options & Alternatives

> **Purpose:** Companion hardware reference for the [Door Entrance & Staff Monitoring Use Case](./door-entrance-use-case.md). Lists recommended hardware per component with budget, mid-range, and premium alternatives.

---

## 1. Hardware Components at a Glance

| # | Component | Role |
|---|---|---|
| 1 | **Door Camera** | Captures video of people approaching/entering; feeds Instant Detection and Presence |
| 2 | **Door Screen + Signage Player** | Small display near the door playing targeted messages/videos via the Simple Player app |
| 3 | **Platform Device** | Runs the Eyenet platform services (node, media, cameras, presence, discovery, etc.) |
| 4 | **Staff Mobile Device** | Runs the Eyenet mobile app for QR-based Presence check-in flows |
| 5 | **Network Infrastructure** | Local LAN switch/router + optional VPN for remote management |
| 6 | **QR Station Device (optional)** | A dedicated tablet or screen at the door displaying the station QR for check-in |

---

## 2. Door Camera

The camera at the door is the primary sensor. Eyenet supports multiple camera types.

### Alternative A — USB Webcam (Budget / Entry)

| Attribute | Detail |
|---|---|
| **Camera type** | USB webcam (UVC-compliant) |
| **Example models** | Logitech C920 / C922 / Brio, Microsoft LifeCam, any 1080p UVC webcam |
| **Resolution** | 1080p recommended; 720p minimum |
| **Connection** | USB-A or USB-C to the platform device or a Raspberry Pi |
| **Mounting** | Wall/ceiling bracket or clip mount above/near door |
| **Pros** | Low cost (€40–120), plug-and-play, no network config needed, widely available |
| **Cons** | USB cable length limited (~5m without active extender); fixed focus; narrower FOV |
| **Best for** | Pilots, single-door deployments, budget-conscious setups |

### Alternative B — Raspberry Pi + USB Camera (Compact / Edge)

| Attribute | Detail |
|---|---|
| **Camera type** | USB webcam or Raspberry Pi Camera Module 3 connected to a Raspberry Pi 4 or 5 |
| **Compute** | Raspberry Pi 4 (4GB) or Raspberry Pi 5 (4GB/8GB) running `ppl-meta-edge-camera` |
| **Resolution** | 1080p via USB webcam; up to 12MP via Pi Camera Module 3 |
| **Connection** | Ethernet or WiFi to local LAN; camera via USB or ribbon cable |
| **Mounting** | Compact enclosure mounted near door; camera positioned for optimal face capture |
| **Pros** | Very compact (fits above door frame), low power (5–15W), dedicated edge processing offloads platform device, cost-effective (~€80–150 total) |
| **Cons** | Requires Linux familiarity; SD card reliability concerns (mitigated with SSD or high-endurance SD); WiFi may be less stable than Ethernet |
| **Best for** | Doors where running long USB cables is impractical; deployments wanting edge compute separation |

### Alternative C — RTSP IP Camera (Mid-Range)

| Attribute | Detail |
|---|---|
| **Camera type** | IP camera with RTSP stream output |
| **Example models** | TP-Link Tapo C110 / C210 / C310, Hikvision DS-2CD2xxx series, Dahua Lite series, Amcrest, Reolink |
| **Resolution** | 1080p to 4MP |
| **Connection** | Ethernet (PoE preferred) or WiFi to local LAN |
| **Mounting** | Wall/ceiling bracket, outdoor-rated models available for exterior doors |
| **Pros** | PoE support (single cable for power + data), longer cable runs, wider FOV options, outdoor-rated models, widely used in security deployments |
| **Cons** | Higher cost (€60–250+), needs PoE switch or injector, RTSP URL configuration required |
| **Best for** | Permanent/professional installations, exterior doors, multi-camera sites, security-conscious environments |

### Alternative D — Android Phone as Soft Camera (Portable / Zero Additional Cost)

| Attribute | Detail |
|---|---|
| **Camera type** | Existing Android smartphone running the Eyenet Android app in camera mode |
| **Example models** | Any mid-range or higher Android phone (Samsung Galaxy A series, Google Pixel, Xiaomi, etc.) |
| **Resolution** | Uses phone's built-in camera (typically 1080p to 4K) |
| **Connection** | WiFi to local LAN |
| **Mounting** | Phone tripod mount or wall bracket near door |
| **Pros** | Zero additional hardware cost if a spare phone is available; quick to deploy; good camera quality on modern phones; portable |
| **Cons** | Battery dependency (needs USB power for permanent install); WiFi-only (no Ethernet); phone may overheat in continuous operation; less professional appearance |
| **Best for** | Temporary setups, pop-up deployments, proof-of-concept, events, testing before committing to dedicated hardware |

### Alternative E — Premium IP Camera with Analytics (High-End)

| Attribute | Detail |
|---|---|
| **Camera type** | Enterprise-grade IP camera with onboard analytics and superior low-light performance |
| **Example models** | Hikvision DeepinView series, Dahua WizMind series, Axis P-series, Bosch FLEXIDOME |
| **Resolution** | 4MP to 8MP |
| **Special features** | Built-in IR for night vision, wide dynamic range (WDR), varifocal lens, onboard people counting, vandal-resistant housings |
| **Connection** | Gigabit Ethernet (PoE+) |
| **Pros** | Best image quality in all lighting conditions, durable, long warranty/support, integrates with existing enterprise security systems |
| **Cons** | High cost (€300–1,000+), requires professional installation, may need NVR infrastructure |
| **Best for** | High-security environments, 24/7 outdoor doors, enterprise/corporate HQ deployments |

### Camera Selection Summary

| Tier | Alternative | Approx. Cost | Setup Complexity | Image Quality | Best For |
|---|---|---|---|---|---|
| Budget | USB Webcam | €40–120 | Low | Good | Pilots, single door |
| Compact | Raspberry Pi + USB/Pi Cam | €80–150 | Medium | Good | Edge deployments |
| Mid-Range | RTSP IP Camera (Tapo, etc.) | €60–250 | Medium | Very Good | Permanent installs |
| Portable | Android Phone as Soft Camera | €0 (existing) | Low | Very Good | POC, temporary |
| Premium | Enterprise IP Camera | €300–1,000+ | High | Excellent | Corporate/security |

---

## 3. Door Screen + Signage Player

The small screen at the door needs both a display and a compute device running the Eyenet Simple Player app (`ppl-meta-signage-simple-player`). These can be separate or combined.

### Alternative A — Android Tablet (All-in-One, Budget)

| Attribute | Detail |
|---|---|
| **Device** | Android tablet running the Simple Player APK |
| **Example models** | Samsung Galaxy Tab A9+ (11"), Lenovo Tab M10 Plus (10.6"), Amazon Fire HD 10 (with Google Play) |
| **Screen size** | 10–12" |
| **Resolution** | 1920×1200 minimum |
| **Connection** | WiFi to local LAN |
| **Mounting** | Wall/desk tablet mount or stand |
| **Power** | USB-C powered (permanent power recommended; battery alone not suitable for 24/7) |
| **Pros** | Single device (display + compute in one), low cost (€150–300), easy to mount, built-in speakers, touchscreen for setup |
| **Cons** | Smaller screen than dedicated displays; consumer-grade build; limited to WiFi; Android OS updates may eventually cause compatibility issues |
| **Best for** | Single-door pilots, small offices, discreet installations where a large display is unnecessary |

### Alternative B — Small Monitor + Raspberry Pi (Modular, Compact)

| Attribute | Detail |
|---|---|
| **Display** | 15–24" HDMI monitor (any brand) |
| **Example displays** | Dell/HP/Lenovo 19–22" business monitors, ViewSonic, ASUS, or small HDMI displays |
| **Compute** | Raspberry Pi 4 (4GB) or Raspberry Pi 5 (4GB) running the Simple Player (Linux or Flutter Linux build) |
| **OS** | Raspberry Pi OS (Debian-based) or Ubuntu |
| **Storage** | 32GB+ microSD (high-endurance) or USB SSD for media caching |
| **Connection** | Ethernet (recommended) or WiFi to local LAN; HDMI to display |
| **Mounting** | VESA wall mount for display; Pi in enclosure behind display or nearby |
| **Pros** | Modular (upgrade display or Pi independently), compact, very low power (~20–30W total), cost-effective (€180–350 total) |
| **Cons** | Two devices to manage; Pi requires Linux familiarity; SD card lifespan concerns for 24/7 operation; Flutter Linux build may require setup |
| **Best for** | Permanent installations wanting flexibility; deployments where screen size may change |

### Alternative C — Small Monitor + Mini PC (Modular, Higher Performance)

| Attribute | Detail |
|---|---|
| **Display** | 15–24" HDMI monitor (any brand) |
| **Compute** | Mini PC running Windows or Linux + Simple Player |
| **Example Mini PCs** | Intel NUC (N100/N150), Beelink Mini S, Dell OptiPlex Micro, Lenovo ThinkCentre Tiny, HP EliteDesk Mini |
| **Specs** | Intel N100 or better, 8GB RAM, 128GB SSD minimum |
| **OS** | Windows 10/11 or Ubuntu Linux |
| **Connection** | Ethernet (recommended) or WiFi; HDMI/DisplayPort to screen |
| **Mounting** | VESA mount for both display and mini PC (many mini PCs have VESA brackets) |
| **Pros** | x86 compatibility (runs any Eyenet component), more reliable storage (SSD), more powerful than Pi for media decoding, runs Windows if required, easier remote management |
| **Cons** | Higher cost (€250–500+ total), larger than Pi, higher power draw (~30–50W) |
| **Best for** | Permanent enterprise deployments; sites already using mini PCs; where Windows is required |

### Alternative D — Android TV Box + Monitor (Cost-Effective Android Player)

| Attribute | Detail |
|---|---|
| **Display** | 15–24" HDMI monitor |
| **Compute** | Android TV box or stick running the Simple Player APK |
| **Example devices** | NVIDIA Shield TV, Xiaomi Mi Box S, Amazon Fire TV Stick 4K, Chromecast with Google TV |
| **Connection** | WiFi or Ethernet (if model supports); HDMI to display |
| **Pros** | Very low cost compute (€40–100), Android-based (matches Simple Player's primary target), good video decoding hardware, compact |
| **Cons** | Consumer devices not designed for 24/7 operation; limited enterprise management; some models may not allow sideloading APKs; no guarantee of long-term OS support |
| **Best for** | Budget-conscious permanent installs; pilot deployments; Android-first strategy |

### Alternative E — All-in-One Signage Display (Premium / Purpose-Built)

| Attribute | Detail |
|---|---|
| **Device** | Commercial-grade all-in-one digital signage display with built-in Android SoC |
| **Example models** | Samsung SMART Signage (QMC/QBC series), LG Digital Signage (UH5F/UL3G series), Philips Professional Display (D-Line) |
| **Screen size** | 21.5" to 32" (small form factor for door areas) |
| **Built-in OS** | Android (Tizen for Samsung — may require Android external player) |
| **Connection** | Ethernet + WiFi built-in |
| **Pros** | Designed for 24/7 operation, slim integrated design, built-in speakers, commercial warranty, remote management (some models), brighter panel for well-lit areas |
| **Cons** | High cost (€400–1,200+), larger screen may be excessive for door area, built-in Android may be locked down (check APK sideload compatibility), overkill for simple messaging |
| **Best for** | Corporate lobbies, premium retail entrances, high-traffic public doors where aesthetics and reliability are critical |

### Door Screen + Player Selection Summary

| Tier | Display | Compute | Approx. Cost | Complexity | Best For |
|---|---|---|---|---|---|
| Budget | Android Tablet (all-in-one) | Built-in | €150–300 | Low | Pilots, small offices |
| Compact | Monitor + Raspberry Pi | Pi 4/5 | €180–350 | Medium | Permanent, flexible |
| Mid-Range | Monitor + Mini PC | Intel NUC/Mini | €250–500 | Medium | Enterprise, Windows |
| Android Box | Monitor + Android TV Box | TV Box/Stick | €150–300 | Low-Medium | Budget Android |
| Premium | Commercial Signage Display | Built-in Android SoC | €400–1,200+ | Medium-High | Corporate lobby |

---

## 4. Platform Device

The platform device runs the Eyenet backend services (node, gateway, media, cameras, orchestration, presence, discovery, vmeta, communications, matrix). One device can serve multiple doors at a single site.

### Alternative A — Existing Business PC/Laptop (Budget / Reuse)

| Attribute | Detail |
|---|---|
| **Hardware** | Existing business desktop or laptop repurposed as the platform server |
| **Minimum specs** | Intel i5/i7 (8th gen or newer) or AMD Ryzen 5/7, 16GB RAM, 500GB SSD |
| **OS** | Ubuntu Server 22.04/24.04 LTS (recommended), Debian, or Windows |
| **Pros** | Zero additional hardware cost if repurposing existing equipment; familiar enterprise hardware |
| **Cons** | May compete with other workloads if not dedicated; laptop not ideal for 24/7 (battery degradation); older hardware may struggle with multiple camera streams |
| **Best for** | Pilots, single-door deployments, customers wanting to start with existing IT assets |

### Alternative B — Small Form Factor PC / Mini PC (Mid-Range)

| Attribute | Detail |
|---|---|
| **Example models** | Intel NUC (i5/i7), Beelink SER5/SER6 (Ryzen 5/7), Dell OptiPlex Micro, Lenovo ThinkCentre Tiny, HP EliteDesk Mini |
| **Recommended specs** | Intel i5-12xxx / i7-12xxx or AMD Ryzen 5 6600H / Ryzen 7 6800H, 16–32GB RAM, 512GB–1TB NVMe SSD |
| **OS** | Ubuntu Server 22.04/24.04 LTS |
| **Connection** | Gigabit Ethernet to local LAN |
| **Pros** | Compact, energy-efficient (15–45W idle), quiet (or fanless options available), industrial-grade reliability, good price/performance |
| **Cons** | Higher cost than repurposing (€350–700); limited internal expansion (e.g., no GPU slot for heavy vision workloads) |
| **Best for** | Small to medium deployments (1–10 cameras), permanent installations, office environments |

### Alternative C — Dedicated Server / Workstation (Mid-High Range)

| Attribute | Detail |
|---|---|
| **Example models** | Dell PowerEdge T150/T350, HPE ProLiant ML30/ML110, custom-built tower server, high-end workstation (Dell Precision, Lenovo ThinkStation) |
| **Recommended specs** | Intel Xeon E-2300 / i7-13xxx+ or AMD Ryzen 9, 32–64GB RAM, 2×1TB NVMe SSD (RAID1), dedicated GPU optional for heavy vision workloads |
| **OS** | Ubuntu Server 22.04/24.04 LTS |
| **Connection** | Dual Gigabit Ethernet |
| **Pros** | High reliability (ECC RAM, redundant storage), designed for 24/7, handles many cameras (10–30+), expandable, enterprise support/warranty |
| **Cons** | Higher cost (€1,200–3,000+), larger footprint, louder, professional IT management needed |
| **Best for** | Medium to large deployments, multi-door sites, high-availability requirements |

### Alternative D — Multiple Raspberry Pi Devices (Distributed Edge)

| Attribute | Detail |
|---|---|
| **Architecture** | One Raspberry Pi 5 (8GB) per service or per small group of services, distributed across the local network |
| **Example setup** | Pi 5 #1: node + gateway + discovery, Pi 5 #2: media + cameras, Pi 5 #3: presence + communications |
| **Pros** | Very low cost per unit (€60–100 each), distributed resilience (one Pi failure doesn't take everything down), extreme energy efficiency, silent |
| **Cons** | Complex to manage multiple devices, SD card reliability, limited per-device compute for demanding workloads (vmeta, heavy camera streams), not recommended for >5 cameras total |
| **Best for** | Experimental/development setups, very small deployments (1–3 cameras), edge-only demos |

### Platform Device Selection Summary

| Tier | Type | Approx. Cost | Cameras Supported | Best For |
|---|---|---|---|---|
| Budget | Repurposed PC/Laptop | €0 (existing) | 1–5 | Pilots, single door |
| Mid-Range | Mini PC (NUC, Beelink) | €350–700 | 1–10 | Small-medium sites |
| Mid-High | Tower Server/Workstation | €1,200–3,000 | 10–30+ | Multi-door, enterprise |
| Edge | Multiple Raspberry Pi 5 | €200–400 total | 1–3 | Dev/demo only |

---

## 5. Staff Mobile Device

Staff members use their own or company-provided mobile devices with the Eyenet mobile app for QR-based Presence check-in flows.

### Alternative A — Staff Personal Device (BYOD)

| Attribute | Detail |
|---|---|
| **Device** | Staff member's own Android or iOS smartphone |
| **Requirements** | Android 10+ or iOS 15+, camera functional, WiFi connected to local network (or VPN for remote) |
| **App** | Eyenet Android APK or iOS app (sideloaded or via enterprise distribution) |
| **Pros** | Zero hardware cost; staff already carry phones; no device management overhead |
| **Cons** | Varied device quality; older phones may have poor camera performance; personal data separation concerns; staff may not want work apps on personal device |
| **Best for** | Most deployments; BYOD-friendly organizations; standard office environments |

### Alternative B — Company-Provided Smartphone

| Attribute | Detail |
|---|---|
| **Device** | Entry-level to mid-range Android smartphone issued by the company |
| **Example models** | Samsung Galaxy A15/A25, Google Pixel 7a/8a, Xiaomi Redmi Note, Nokia G-series |
| **Specs** | Any modern Android smartphone with a functional front/rear camera |
| **Cost** | €120–350 per device |
| **Pros** | Uniform hardware, controlled OS version, dedicated work device, easier MDM enrollment, no personal data concerns |
| **Cons** | Procurement and management cost per staff member; device lifecycle management |
| **Best for** | Organizations that do not permit BYOD; high-security environments; shift workers who don't carry personal phones |

### Alternative C — Dedicated QR Badge / NFC Tag (No App Needed)

| Attribute | Detail |
|---|---|
| **Approach** | Staff carry a printed QR badge or NFC card/fob; the station-side camera/scanner reads it |
| **QR option** | Printed QR code on staff ID badge (laminated) — station camera or dedicated QR scanner reads it |
| **NFC option** | NFC card/fob — station NFC reader reads it (requires NFC-capable station device) |
| **Pros** | No mobile app required for staff; low cost (€1–5 per badge); no battery, no updates; works for non-tech-savvy users; durable |
| **Cons** | Cannot support face-detection verification on the mobile side (must rely on station-side camera); badges can be lost/stolen; no two-factor from the user's device |
| **Best for** | Environments where staff cannot/don't want to use phones; industrial settings; high-turnover shift work |

### Staff Mobile Selection Summary

| Tier | Device | Approx. Cost per Staff | Setup | Best For |
|---|---|---|---|---|
| BYOD | Staff personal phone | €0 | Low (install app) | Standard offices |
| Company Phone | Entry/mid Android | €120–350 | Medium (MDM) | No-BYOD orgs, security |
| QR Badge/NFC | Printed badge or card | €1–5 | Low-Medium | Industrial, shift work |

---

## 6. Network Infrastructure

All devices must be on the same local network for discovery, media streaming, and service communication.

### Alternative A — Existing Office Network (Budget)

| Attribute | Detail |
|---|---|
| **Equipment** | Customer's existing office LAN switch and router |
| **Requirements** | Gigabit Ethernet switch with enough ports; standard WiFi access point for mobile devices and WiFi cameras |
| **Pros** | Zero additional cost; no new hardware to manage |
| **Cons** | Shared bandwidth with office traffic; no isolation from other network activity; security depends on existing network posture |
| **Best for** | Pilots, small offices, low-camera-count deployments |

### Alternative B — Dedicated VLAN / Segmented Network (Mid-Range)

| Attribute | Detail |
|---|---|
| **Equipment** | Managed Gigabit switch + existing router with VLAN support |
| **Example switches** | Ubiquiti UniFi Switch Lite 8/16, TP-Link JetStream, Netgear ProSAFE, Cisco CBS series |
| **Setup** | Eyenet devices on a dedicated VLAN; inter-VLAN routing as needed; QoS for camera streams |
| **Pros** | Traffic isolation improves reliability and security; camera streams don't compete with office traffic; better for compliance |
| **Cons** | Requires networking knowledge; managed switch cost (€100–300); some configuration needed |
| **Best for** | Permanent deployments; sites with significant office network traffic; multi-camera setups |

### Alternative C — Dedicated Physical Network + PoE (Premium)

| Attribute | Detail |
|---|---|
| **Equipment** | Dedicated PoE switch for cameras + separate switch for platform/screens |
| **Example switches** | Ubiquiti UniFi Switch PoE 8/16, Cisco CBS350 PoE, Aruba Instant On 1930 PoE |
| **Setup** | Cameras on dedicated PoE switch (power + data over single cable); platform and signage devices on separate switch; all on isolated Eyenet network segment |
| **Pros** | Maximum reliability, zero competition with office traffic, PoE eliminates power cables for cameras, clean installation, easier troubleshooting |
| **Cons** | Highest cost (€200–600+ for switches); requires cabling; professional installation recommended |
| **Best for** | Multi-door enterprise deployments, high-availability requirements, security-sensitive environments |

### VPN for Remote Management

| Option | Description |
|---|---|
| **Eyenet VPN Mesh (Tailscale/Headscale)** | Built-in VPN capability via the Eyenet authority service; devices auto-join a secure mesh; recommended approach |
| **Third-party VPN** | Customer's existing VPN solution (OpenVPN, WireGuard, corporate VPN) |
| **No VPN** | All management done locally on-site; no remote access (simplest, zero configuration) |

### Network Selection Summary

| Tier | Approach | Approx. Cost | Complexity | Best For |
|---|---|---|---|---|
| Budget | Existing office LAN | €0 | Low | Pilots, single door |
| Mid-Range | Dedicated VLAN | €100–300 | Medium | Permanent installs |
| Premium | Dedicated LAN + PoE | €200–600+ | Medium-High | Multi-door enterprise |

---

## 7. QR Station Device (Optional)

If using station-side QR scanning (where the mobile app scans a station QR, or the station scans a mobile QR/badge), a dedicated device at the door displays or reads the QR code.

### Alternative A — Tablet at Door (All-in-One Station)

| Attribute | Detail |
|---|---|
| **Device** | Android tablet mounted at the door |
| **Example models** | Samsung Galaxy Tab A9+ (11"), Lenovo Tab M10 Plus (10.6") |
| **Function** | Displays station QR code for staff to scan with mobile app; can also run camera for face detection |
| **Connection** | WiFi to local LAN |
| **Mounting** | Wall mount or kiosk stand |
| **Cost** | €150–300 |
| **Pros** | Multi-function (QR display + optional camera); visible, easy to interact with; familiar tablet UX |
| **Cons** | Additional device cost; needs power; WiFi dependency |
| **Best for** | QR-based check-in flows where a visible station is desired |

### Alternative B — Small Monitor + Raspberry Pi (Dedicated Station)

| Attribute | Detail |
|---|---|
| **Display** | 7–10" HDMI touchscreen connected to a Raspberry Pi |
| **Compute** | Raspberry Pi 4/5 running a web browser in kiosk mode displaying the station QR |
| **Camera** | USB webcam connected to the Pi for face detection |
| **Cost** | €120–200 total |
| **Pros** | Lower cost than a tablet; more configurable; can run camera + display from same device |
| **Cons** | More DIY setup; touchscreen adds cost; Linux configuration needed |
| **Best for** | Custom installations; environments needing integrated QR + camera in one station |

### Alternative C — Printed QR Code (No Electronics)

| Attribute | Detail |
|---|---|
| **Format** | Laminated printed QR code affixed to the wall or door frame |
| **Cost** | €1–5 |
| **Pros** | Zero electronics, zero maintenance, zero power, always available, trivial to replace |
| **Cons** | Static — cannot rotate QR challenge data for security; staff scan printed QR with mobile app |
| **Best for** | Low-security doors; budget deployments; backup station when electronic station is down |

### Alternative D — No Station (Mobile-Only or Camera-Only)

| Attribute | Detail |
|---|---|
| **Approach** | Skip the station entirely; use camera-only or mobile-initiated presence flows |
| **Flows** | Face-detection-only check-in (camera detects and verifies); or mobile-initiated session without a station QR |
| **Cost** | €0 |
| **Best for** | Camera-only deployments; minimal-hardware setups; fully automated doors |

### QR Station Selection Summary

| Tier | Approach | Approx. Cost | Best For |
|---|---|---|---|
| All-in-One | Android Tablet | €150–300 | QR + optional camera |
| DIY | Pi + Touchscreen | €120–200 | Custom, integrated |
| Zero-Electronics | Printed QR code | €1–5 | Budget, low security |
| None | Camera-only flow | €0 | Fully automated |

---

## 8. Recommended Configurations by Deployment Size

### Pilot / Single Door (Minimal Budget)

| Component | Recommendation | Est. Cost |
|---|---|---|
| Door Camera | USB Webcam (Logitech C920) | €80 |
| Door Screen | Android Tablet (Galaxy Tab A9+) | €180 |
| Platform Device | Existing office PC (repurposed) | €0 |
| Staff Mobile | BYOD (staff personal phones) | €0 |
| Network | Existing office LAN | €0 |
| QR Station | Printed QR code | €2 |
| **Total** | | **~€262** |

### Single Door (Professional)

| Component | Recommendation | Est. Cost |
|---|---|---|
| Door Camera | RTSP IP Camera (TP-Link Tapo C310) | €60 |
| Door Screen | 19" Monitor + Raspberry Pi 5 | €300 |
| Platform Device | Mini PC (Beelink SER5, Ryzen 5) | €400 |
| Staff Mobile | BYOD (staff personal phones) | €0 |
| Network | Existing LAN (dedicated port) | €0 |
| QR Station | Android Tablet at door | €180 |
| **Total** | | **~€940** |

### Single Door — Edge Door Unit + Separate Platform PC (Recommended)

This is the recommended architecture for a single door: a compact, fanless Raspberry Pi-based edge unit at the door handles camera input, signage display, and optional QR station duties, while an industrial fanless mini PC elsewhere on the same local network runs the full Eyenet backend platform. This cleanly separates the door-edge responsibilities from the backend compute, keeping the door hardware minimal, silent, and tamper-resistant while the platform PC can be secured in a server room or IT closet.

#### Architecture Overview

```
                      ┌─────────────────────────────────┐
                      │     LOCAL NETWORK (GigE LAN)    │
                      └────────┬───────────────┬────────┘
                               │               │
              ┌────────────────▼───┐   ┌───────▼──────────────────┐
              │  DOOR EDGE UNIT    │   │  PLATFORM DEVICE          │
              │  (at the door)     │   │  (secure location)        │
              │                    │   │                           │
              │  ┌──────────────┐  │   │  Industrial Fanless       │
              │  │ RPi Compute  │  │   │  Mini PC (32GB RAM)       │
              │  │ Module       │  │   │                           │
              │  │ 16–32GB RAM  │  │   │  Runs Docker + all       │
              │  │ NVMe SSD     │  │   │  Eyenet services:         │
              │  │              │  │   │  • ppl-meta-node          │
              │  │ Services:    │  │   │  • ppl-meta-gateway       │
              │  │ • edge-      │  │   │  • ppl-meta-media         │
              │  │   camera     │◄─┼───┼──│  • ppl-meta-cameras      │
              │  │ • signage    │  │   │  • ppl-meta-orchestrator  │
              │  │   simple     │  │   │  • ppl-meta-presence      │
              │  │   player     │  │   │  • ppl-meta-discovery     │
              │  └──────┬───────┘  │   │  • ppl-meta-vmeta         │
              │         │          │   │  • ppl-meta-communications│
              │  ┌──────▼───────┐  │   │  • ppl-meta-matrix (opt.) │
              │  │ Camera       │  │   │  • PostgreSQL + Redis     │
              │  │ Module V3    │  │   │                           │
              │  │ Wide Lens    │  │   │  Ubuntu Server 24.04 LTS │
              │  └──────────────┘  │   │                           │
              │                    │   └───────────────────────────┘
              │  ┌──────────────┐  │
              │  │ Touch Screen │  │
              │  │ 7–10" HDMI   │  │
              │  │ (signage +   │  │
              │  │  optional QR │  │
              │  │  station)    │  │
              │  └──────────────┘  │
              │                    │
              └────────────────────┘
```

#### Door Edge Unit Bill of Materials

| Component | Specification | Est. Cost |
|---|---|---|
| **Compute Module** | Raspberry Pi Compute Module 5 (CM5) with 16GB or 32GB RAM on a carrier board (e.g., Compute Blade, official IO board, or third-party carrier with M.2 slot) | €110–180 |
| **Storage** | NVMe SSD (256GB–512GB) via M.2 slot on carrier board — caches signage media locally for smooth playback; far more reliable than microSD for 24/7 operation | €30–60 |
| **Camera** | Raspberry Pi Camera Module 3 Wide (12MP, 102° diagonal FOV) — wide lens is ideal for door entrances where people approach from various angles; connects via ribbon cable | €30–35 |
| **Display** | 7–10" HDMI touch screen (e.g., official Raspberry Pi Touch Display 2, Waveshare, or similar IPS panel) — serves as signage display and can optionally double as a QR station screen | €60–100 |
| **Enclosure** | Compact fanless enclosure or 3D-printed housing integrating the carrier board, camera, and screen — mountable above or beside the door | €15–40 |
| **Power** | USB-C PD power supply (27W+ recommended for CM5 + SSD + display) | €15–25 |
| **Networking** | Gigabit Ethernet via carrier board (recommended) or WiFi if Ethernet cabling is impractical | €0 (built-in) |
| **Door Edge Unit Total** | | **~€260–440** |

#### Platform Device Bill of Materials

| Component | Specification | Est. Cost |
|---|---|---|
| **Compute** | Industrial fanless mini PC, 32GB DDR4/DDR5 RAM, x86 CPU (Intel N150/N97/i3-N305 or AMD equivalent) | €350–600 |
| **Storage** | 1TB NVMe SSD (OS + Docker services + media retention) | €60–100 |
| **OS** | Ubuntu Server 24.04 LTS | €0 |
| **Networking** | Dual Gigabit Ethernet (one for LAN, one optional for separate management VLAN) | €0 (built-in) |
| **Platform Device Total** | | **~€410–700** |

#### Full Deployment Cost Summary

| Component | Recommendation | Est. Cost |
|---|---|---|
| Door Edge Unit | RPi CM5 (16–32GB) + Camera Module 3 Wide + NVMe SSD + Touch Screen | €260–440 |
| Platform Device | Industrial fanless mini PC, 32GB RAM, 1TB SSD | €410–700 |
| Staff Mobile | BYOD (staff personal phones) | €0 |
| Network | Existing office Gigabit LAN (both devices wired via Ethernet) | €0 |
| VPN | Eyenet VPN Mesh (included in platform) | €0 |
| **Total** | | **~€670–1,140** |

#### What Runs Where

| Service | Runs On | Notes |
|---|---|---|
| `ppl-meta-edge-camera` | Door Edge Unit (RPi) | Publishes camera frames to the platform; Camera Module 3 Wide provides wide-angle face capture at door distance |
| `ppl-meta-signage-simple-player` | Door Edge Unit (RPi) | Full-screen playback on the touch display; media synced from platform, cached on local SSD |
| QR Station (optional) | Door Edge Unit (RPi) | Same touch screen can display station QR for mobile-based Presence check-in flows |
| All backend services (node, gateway, media, cameras, orchestrator, presence, discovery, vmeta, communications, PostgreSQL, Redis) | Platform Device (Mini PC) | Docker Compose stack on the industrial mini PC; 32GB RAM comfortably handles all services for a single door plus headroom |
| `ppl-meta-matrix` (optional) | Platform Device (Mini PC) | Only needed for multi-site aggregation; negligible overhead if enabled |

#### Why This Architecture Works Well

- **Silent door operation** — The RPi edge unit is completely fanless; no noise at the door area
- **Clean separation** — If the signage player or camera service needs a restart, the backend platform is unaffected (and vice versa)
- **Security** — The backend platform can be physically secured in an IT room; only the edge unit (camera + display) is exposed at the door
- **Wide lens advantage** — The Camera Module 3 Wide's 102° FOV captures people approaching from the side, not just straight-on; critical for real-world door geometries
- **SSD reliability** — NVMe SSD on the edge unit eliminates the SD card failure risk for 24/7 signage operation
- **Single cable to the door** — If using PoE via a PoE HAT on the carrier board, the entire door unit can run on one Ethernet cable (power + data + camera + display)
- **Scalable** — Additional doors simply add more edge units; the same platform device can serve 1–3 doors before needing an upgrade

### Multi-Door / Enterprise (Single Site)

| Component | Recommendation | Est. Cost |
|---|---|---|
| Door Cameras (×4) | RTSP IP Cameras (Hikvision/Dahua PoE) | €800 (€200 ×4) |
| Door Screens (×4) | 22" Monitors + Raspberry Pi 5 (×4) | €1,200 (€300 ×4) |
| Platform Device | Tower Server (Dell PowerEdge T150) | €1,800 |
| Staff Mobile | Company phones or BYOD | €0–1,400 |
| Network | PoE Switch + Dedicated VLAN (Ubiquiti) | €400 |
| QR Stations (×4) | Android Tablets | €720 (€180 ×4) |
| VPN | Eyenet VPN Mesh (included in platform) | €0 |
| **Total** | | **~€4,920–6,320** |

### Multi-Site (Matrix-Aggregated)

Same as enterprise per site, plus the Matrix service running on the primary installation's platform device (included — no additional hardware needed). VPN mesh connects all sites.

---

## 9. General Hardware Notes

- **Minimum platform RAM:** 16GB for small deployments; 32GB+ for 10+ cameras or heavy analytics workloads.
- **Storage:** SSD required for platform device. 500GB minimum for OS + services + media; 1TB+ for video retention.
- **Camera placement:** Position door camera at face height (~1.5–1.7m) and within 1–3m of where people pause at the door for best face detection results.
- **Screen placement:** Door screen should be visible at eye level from 1–3m approach distance. Avoid direct sunlight washing out the display.
- **Power:** All door-area devices (camera, screen, station) need permanent power. Plan cable routing through walls/ceilings or use PoE where possible to reduce cable count.
- **WiFi vs Ethernet:** Ethernet is strongly recommended for platform devices, cameras, and signage players. WiFi is acceptable only for mobile devices and tablets when Ethernet is impractical.
- **Environmental:** For exterior doors, ensure cameras and displays are rated for outdoor use or protected by weather housing.