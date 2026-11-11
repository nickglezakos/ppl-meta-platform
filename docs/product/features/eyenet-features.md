# EyeNet Main Features

**Type:** Product overview  
**Source:** `docs/product/marketing/eyenet-services.html`, `docs/modules`, `docs/product/marketing`  
**Deployment:** On-premises / VPN — no cloud dependency for video or data

---

EyeNet is an on-premises computer-vision platform that turns ordinary cameras into activity, attendance, and automation sensors. The product is sold as six applications on one shared platform.

## Applications

### 1. Presence

Attendance and area control.

- Schedules and members per room
- QR/NFC plus face verification (two-factor presence)
- Unauthorized-person alerts in restricted areas
- Attendance reports, including reports sent to families or sponsors
- Works with Gate for entrance-to-area monitoring

**Modes:** Area · Gate  
**Typical users:** Schools, universities, gyms, industrial facilities, offices, hospitals

### 2. Signage

Audience-aware digital signage.

- Playlists switch by age, gender, and group size
- Automatic promotions or emergency messages based on who is watching
- Web upload and assignment of targeted media
- Impression, dwell-time, and engagement measurement
- Optional people-activity insights (demographics, traffic, heatmaps)

**Modes:** Spot · Gate · Area  
**Typical users:** Retail, malls, airports, agencies, event venues

### 3. Vradar

Product view of **Automation**: triggers and actions driven by **instant detection** results.

- Instant demographic and people-match triggers on live camera detections
- Actions: in-app alerts, email, webhooks, and digital signage switches
- Whitelists / watchlists via individual groups (POI match and NOT-match)
- Works on any instant-detection camera — fixed, mobile, wearable, or aerial
- Parallel rules across cameras from one Automation dashboard (`/triggers`)

**Modes:** Gate · Area · Goggles · Drone (any camera running instant detection)  
**Typical users:** Security agencies, law enforcement, private and event security

### 4. Gate

Entrance and corridor monitoring.

- Real-time people counters, age/gender demographics, heatmaps, crowd metrics
- Instant alerts for abnormal crowd activity and POI face matches
- Live annotated video with flexible storage (instant and deep archives)
- Mobile notifications and hooks into existing security systems
- Operational presence reports with full event history

**Modes:** Gate  
**Typical users:** Commercial buildings, industrial sites, airports, hubs, events

### 5. Sentinel

Guard-post vigilance.

- Alerts when a watch-station guard is inactive or outside custom criteria
- Live video with people-activity annotations
- Continuous oversight across shifts
- Configurable detection parameters per post

**Modes:** Area  
**Typical users:** Security firms, corporate and industrial sites, government buildings

### 6. Matrix

Multi-site control over secure VPN.

- Aggregated reports across member installations: Summary, Presence, Gate Activity, Camera Events, Demographics, Logs
- Matrix groups and installation membership with multi-install licensing
- Centralised user directory and JWT-based SSO with RBAC
- Degraded mode: partial results when some sites are unreachable
- Report caching and time-range filtering for historical analysis

**Typical users:** Multi-site operators, fleets, organisations needing one dashboard across locations

---

## Shared platform capabilities

| Capability | What it does |
|---|---|
| **Cameras** | Any IP, WiFi, phone, or NVR/VMS camera; live detection and recorded video |
| **Vision** | Face and body detection, cross-camera identity, demographics, people counts, routes, and dwell time |
| **Analytics** | Occupancy, time trends, demographics, and behaviour (peak hours, visit frequency, heatmaps) |
| **Automation (Vradar)** | Product view of triggers/actions on instant detection — demographics or known people → email, webhooks, alerts, or signage |
| **Access & licensing** | Roles and permissions, invitations, and installation licences |
| **Operations** | On-site recording and archives, system health, and remote access over VPN |

Core detection runs fully offline on standard business hardware (about 16 GB RAM and a modern multi-core CPU). Internet is used only for remote access and notifications.

---

## Operating modes

| Mode | Description | Used by |
|---|---|---|
| **Spot** | Close-range fixed areas (POS, displays) | Signage |
| **Gate** | Entrances, exits, corridors | Presence, Signage, Gate |
| **Area** | Rooms and wide spaces | Presence, Signage, Sentinel |
| **Goggles** | Wearable first-person cameras | Vradar |
| **Drone** | Aerial mobile coverage | Vradar |

---

## Primary use cases

1. **Staff presence & attendance** — dual-factor check-in and attendance history  
2. **Audience-aware digital signage** — content that follows the audience  
3. **Entrance & gate monitoring** — counts, demographics, POI, and live annotated video  
4. **Restricted area protection** — virtual perimeters and unauthorised-presence alerts  
5. **VIP & personnel protection** — Vradar (Automation) POI / demographic alerts from instant detection  

6. **Remote operational control** — VPN access to cameras, triggers, and dashboards  
7. **Maritime & fleet compliance** — presence and analytics with offline-capable sites  
8. **Multi-site aggregated reporting** — Matrix dashboards across all installations
