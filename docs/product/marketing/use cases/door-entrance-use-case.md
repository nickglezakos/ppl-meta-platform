# Eyenet Products — Door Entrance & Staff Monitoring Use Case

> **Target Audience:** Companies needing intelligent door monitoring with staff identification, access analytics, and dynamic screen-based messaging for approaching visitors.

---

## 1. Use Case Overview

A company operates a secured entrance (door) and wants to:

| Need | Description |
|---|---|
| **Alerts** | Real-time notifications when people approach or enter the door (who, when, how) |
| **Staff Identification** | Determine whether the person entering is a known staff member or an unknown visitor |
| **Analytics** | Historical reporting on entry traffic, staff vs visitor breakdowns, peak hours, demographics |
| **Digital Signage** | A small screen near the door that plays targeted information messages and short videos to people as they approach, with content that can adapt based on who is approaching |

---

## 2. Eyenet Product Mapping

Each requirement maps to one or more Eyenet modules:

| Requirement | Primary Module(s) | Supporting Module(s) |
|---|---|---|
| Entry verification (who entered, when) | **Presence** | Cameras, Instant Detection |
| Staff vs visitor identification | **Individual Groups** + **Instant Detection** | Person Objects, vmeta |
| Real-time alerts & notifications | **Automation** (Triggers & Actions) | Communications |
| Entry analytics & reporting | **Presence** (analytics endpoints) + **Analytics** | Matrix (multi-site) |
| Door screen content (videos/messages) | **Digital Signage** | Automation (trigger-based content switching) |
| Camera-based person detection | **Instant Detection** + **Cameras** | Vision |

---

## 3. Product-by-Product Outline

### 3.1 Presence — Entry Verification & Check-in

Presence serves as the core door-entry workflow:

- **QR-based check-in:** Staff scan a station QR at the door via the mobile app, or the station scans their mobile QR
- **Face-detection-based check-in:** The door camera detects and verifies the person automatically
- **Two-factor mode (QR + Face):** For higher-security scenarios — QR initiates the session, camera completes verification
- **Configurable policies:** Per-installation and per-group policies determine whether entry is granted, denied, or flagged for retry
- **Session traceability:** Every entry event is recorded with decision history, grant type, policy source, and execution metadata
- **Presence analytics:** Built-in reporting by user, by device, by session mode, by grant type, and by date range — directly answers "who entered and when"

**How it fits:** Presence provides the verified entry record — the authoritative log of every person passing through the door, along with the mechanism (QR, face, or both) and the policy outcome.

---

### 3.2 Individual Groups — Staff Identification

Staff members are registered as known individuals grouped into one or more "individual groups" (e.g., "All Staff", "Engineering", "Management"):

- **Group registration:** Staff faces are enrolled via the Individual Groups module
- **Real-time matching:** When a person approaches the door, the Instant Detection system matches detected faces against registered staff groups via the vmeta service
- **Match outcome:** Each detection returns a match/no-match result with similarity scores — enabling the system to distinguish "staff" from "visitor"
- **Negate-mode matching:** Triggers can fire specifically when NO staff member is matched (i.e., an unknown person approaches)

**How it fits:** Individual Groups provides the identity layer — it answers "is this person our staff?" and enables differentiated treatment of known vs unknown individuals.

---

### 3.3 Automation — Triggers & Actions for Door Events

Automation connects detection events to concrete actions:

#### Relevant Trigger Modes

| Trigger Mode | Door Use Case |
|---|---|
| **Instant Demographic** | Fire when person count at door exceeds X, or when specific demographic patterns are detected |
| **Instant People Match** | Fire when a specific staff member (or group member) is detected at the door |
| **Instant People Match (negated)** | Fire when an **unknown** person (not in any staff group) approaches the door |
| **Search People Match** | Periodically scan door camera recordings for staff member appearances |
| **Search Demographic** | Periodically aggregate demographics at the door zone |

#### Relevant Action Types

| Action Type | Door Use Case |
|---|---|
| **`alert`** | On-screen alert to security/reception when an unknown person approaches |
| **`email`** | Email notification to facilities/security with person details and timestamp |
| **`messaging_app`** (Slack/Teams) | Instant message to a security channel when a VIP staff member enters or an unknown person is detected |
| **`webhook`** | Integrate with third-party access control systems, door controllers, CRM, or ERP |
| **`digital_signage`** | Automatically switch the door screen content based on who is approaching |
| **`log`** | Audit log entry for compliance and traceability |

#### Example Automation Rules (Triggers → Actions)

1. **Staff member detected** → `digital_signage`: show personalized welcome screen + `log`: record entry
2. **Unknown person detected** → `alert`: notify security + `email`: alert facilities + `digital_signage`: show visitor instructions
3. **Person count > 5 at door** → `messaging_app`: notify crowd management + `webhook`: trigger additional door unlock
4. **VIP staff member matched** → `messaging_app`: notify executive assistant + `digital_signage`: show premium welcome

**How it fits:** Automation is the nervous system — it evaluates conditions in real time and triggers the right response across all channels (screens, notifications, external systems).

---

### 3.4 Digital Signage — Door Screen Content

A small screen mounted near the door plays targeted content to approaching people:

- **Playlist creation:** Operators build playlists from uploaded video content and media collections via the Signage Management Screen
- **Device discovery:** The signage player (running on the door screen hardware) is auto-discovered and registered
- **Remote playback control:** Content can be started, paused, resumed, stopped, or skipped centrally
- **Automation-driven content switching:** The `digital_signage` action type in Automation triggers causes the door screen to switch playlists instantly based on who is detected. For example:
  - Default playlist: company branding, general information
  - Staff detected → switch to internal announcements playlist
  - Visitor detected → switch to visitor orientation/welcome playlist
  - Unknown person → switch to instructions/security notice playlist
- **Loop modes:** `continuous`, `once`, `shuffle`, `repeat_one` — configure how content cycles on the door screen
- **Multiple playlists per deployment:** Different playlists for different times of day, audience types, or trigger conditions

**How it fits:** Digital Signage is the communication surface at the door — it delivers the right visual message to the right person at the right moment, driven by real-time detection.

---

### 3.5 Analytics — Door Traffic Intelligence

Built-in analytics across Presence and the Analytics module provide:

| Insight | Source |
|---|---|
| Total entries per day/hour | Presence analytics endpoints |
| Staff vs visitor ratio | Individual groups matching logs + Presence |
| Peak entry times | Presence session timestamps |
| Demographics of people at the door | Camera analytics (age, gender) |
| Trigger & action performance | Automation execution logs |
| Entry method breakdown (QR vs face vs both) | Presence session mode analytics |
| Per-user presence awards / daily summaries | Presence analytics |

All analytics are exportable (xls) and filterable by date range, user, device, installation, session mode, grant type, and policy source.

For multi-site deployments, the **Matrix** service aggregates Presence, camera events, demographics, and gate activity data across all installations.

---

## 4. End-to-End Flow: Person Approaches the Door

```
Person approaches door
        │
        ▼
┌──────────────────────────────┐
│ Camera detects person        │  ← Instant Detection + Cameras
│ (people count, demographics) │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ Match against Staff Groups   │  ← Individual Groups + vmeta
│ Known staff? Unknown visitor?│
└──────────────┬───────────────┘
               │
       ┌───────┴───────┐
       │               │
   [Staff]         [Unknown]
       │               │
       ▼               ▼
┌────────────┐  ┌────────────────┐
│ Automation │  │ Automation     │
│ Trigger:   │  │ Trigger:       │
│ Staff Match│  │ No Staff Match │
└──┬──┬──┬───┘  └──┬──┬──┬───────┘
   │  │  │         │  │  │
   ▼  ▼  ▼         ▼  ▼  ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌─────────┐ ┌──────┐ ┌────────────┐
│Signage│ │Pres- │ │Alert/│ │Signage  │ │Pres- │ │Alert/      │
│Switch │ │ence  │ │Notif │ │Switch   │ │ence  │ │Notif       │
│to     │ │Check-│ │to    │ │to Visit-│ │Log   │ │to Security │
│Staff  │ │in    │ │Team  │ │or Screen│ │Entry │ │+ Facilities│
│Screen │ │Grant │ │      │ │         │ │      │ │            │
└──────┘ └──────┘ └──────┘ └─────────┘ └──────┘ └────────────┘
   │                               │
   ▼                               ▼
┌──────────────────────────────────────┐
│ Door Screen shows targeted content   │  ← Digital Signage Player
└──────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ All events logged for analytics      │  ← Presence + Automation logs
│ Queryable via dashboards & reports   │
└──────────────────────────────────────┘
```

---

## 5. Hardware & Deployment

| Component | Hardware Options |
|---|---|
| **Door camera** | USB camera, RTSP IP camera, TP-Link Tapo, Android phone as soft camera |
| **Door screen** | Any display driven by a signage player device (Android, Linux, Windows) running the Simple Player app |
| **Platform device** | PC, laptop, or server on the same local network |
| **Staff mobile** | Android/iOS device running the Eyenet mobile app (for QR-based Presence flows) |
| **Network** | All devices on same local network; VPN for remote management |

---

## 6. Privacy & Compliance

- Face data remains on local devices — not exposed through APIs
- Staff members maintain full control of their face detection data (update, delete)
- Admins access presence grands and analytics, not raw biometric data
- Full GDPR-compliant architecture even with face detection enabled
- All data stays on-premises; no cloud dependency required

---

## 7. Scalability

| Stage | Description |
|---|---|
| **Single door** | One camera + one screen + one platform device |
| **Multiple doors, single site** | Multiple cameras + screens, one platform device or node, cross-door analytics |
| **Multiple sites** | Matrix service aggregates Presence, camera, and demographics data across all installations over VPN |

---

## 8. Key Selling Points

1. **Unified platform** — A single system covers entry verification, staff identification, alerts, analytics, and door-screen content
2. **Real-time intelligence** — Content and notifications adapt instantly based on who is at the door
3. **Hardware flexibility** — Works with standard cameras and screens; no proprietary kiosk lock-in
4. **Privacy-first** — GDPR-compliant face detection; biometric data stays local
5. **Start small, expand** — Begin with one door, grow to multi-site with aggregated reporting via Matrix
6. **Integration-ready** — Webhooks connect to existing access control, CRM, ERP, and door controller systems
7. **Offline-capable** — Core operation runs locally without internet; internet needed only for remote notifications