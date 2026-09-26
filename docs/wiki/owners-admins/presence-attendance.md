---
software_ref:
  platform_version: "2.25.85"
  policy_revision: "2026-09-26"
  channels_documented:
    - sandbox
    - pilot
    - stable
  install_path: "windows-docker-desktop-ghcr"
  host_ram_gb: 16
  wsl_memory_gb: 12
title: Presence and attendance
audience: owner-admin
nav_order: 50
---

# Presence And Attendance

Run presence check-in and attendance flows (QR, camera, or both), manage people profiles, assign a platform camera for Actions, reserve a match group in Settings, and review session outcomes.

**Where:** Home → **Presence** (`/presence`)

## Prerequisites

- Bootstrap completed; you can log in as owner or admin
- For camera-backed flows: at least one camera online — see [Cameras and detection](./cameras-and-detection.md)
- For known-person matching: an **Individual Group** with members — see [Detections, individuals and persons](./detections-individuals-persons.md)
- Instant detection on the assigned Actions camera when using **Video Match** or **QR + Camera** paths

## Session modes (basics)

| Mode (UI / API) | Meaning |
|---|---|
| **QR Only** (`qr_only`) | Check-in via QR (station QR or owner identity QR) |
| **Camera Only** (`camera_only`) | Face / people match on the assigned platform camera (UI: **Video Match**) |
| **QR + Camera** (`qr_plus_camera`) | Owner QR on the platform camera first, then camera verification for higher assurance |

Outcomes you will see on sessions: **granted**, **denied**, **pending**, **failed**, **retry_required**, plus grant-type and assurance labels from policy.

---

## Screen layout

Six tabs on **Presence**:

| Tab | Purpose |
|---|---|
| **Overview** | Totals and recent sessions |
| **Actions** | Assign platform camera; Render QR, Video Match, Scan Owner QR, Scan Owner QR + Video |
| **Analytics** | Session-mode and grant-type distributions; user/day awards |
| **Sessions** | Paginated session list, filters, download, detail inspector |
| **People** | Presence people profiles (name, email, phone, …) |
| **Settings** | Reserve presence match group (camera assignment is on **Actions**) |

Refresh the dashboard with pull-to-refresh where available, or by leaving and re-entering Presence.

---

## Settings (match group)

**Tab:** **Settings** → **Presence Settings**  
*Operator controls for match group selection and installation policy.*

Camera reservation is **not** on Settings anymore — assign the Presence camera under **Actions**.

### Reserve a presence match group

1. Open **Settings**.
2. Under **Presence Match Groups**, groups listed come from Individual Groups (name, id, member count).
3. Tap **Reserve** on the group that should be the active **ppl-match** group for presence.
4. Confirm (*Reserved match group …*). A chip may show **Group <name>**.
5. **Unreserve** to clear the active match group.

If the list is empty, create and populate a group first under [Individual Groups](./detections-individuals-persons.md).

---

## Actions (run a check-in)

**Tab:** **Actions**

### Assign a platform camera (do this first for scan / video)

1. Under **Presence Camera**, find the USB / RTSP / edge camera to use for presence.
2. Tap **Reserve**. Reserving also auto-binds the linked media collection when the backend can resolve one.
3. Confirm the snackbar. A chip shows the assigned camera.
4. **Unreserve** to clear.

Without an assigned camera, **Scan Owner QR**, **Scan Owner QR + Video**, and **Video Match** cannot run platform decode / detection.

Optional fields above / beside the QR panel:

| Field | Notes |
|---|---|
| **Device Display Name** | Label stored inside the QR payload (defaults differ for console vs station) |
| Location label | Optional label in the QR location payload |

### Operator buttons

| Button | Mode | What it does |
|---|---|---|
| **Render QR** | `qr_only` | Creates/reuses a session and renders a **station** presence QR. Shows under **Current QR Payload** (copyable). Mobile users scan this QR. |
| **Video Match** | `camera_only` | Starts a camera-only session against the assigned platform camera / match group (no QR required). Polls for a decision. |
| **Scan Owner QR** | `qr_only` | Decodes an **owner identity** QR from the **assigned platform camera** (cameras service). Browser/webcam scanning is not used. Shows live preview for aiming when available. |
| **Scan Owner QR + Video** | `qr_plus_camera` | Same platform-camera QR decode, then camera verification starts on that same camera. |

### Typical flows

**A. Station QR (phone scans screen)**  
1. Settings: reserve match group as needed; Actions: assign camera if camera follow-up may occur.  
2. Actions → **Render QR**.  
3. Phone scans the displayed QR with the EyeNet mobile / presence path.  
4. Watch **Overview** / **Sessions** for granted or denied.

**B. Camera-only match**  
1. Actions: assign camera; Settings: reserve match group; start [instant detection](./cameras-and-detection.md) on that camera if needed.  
2. Actions → **Video Match**.  
3. Person stands in view of the camera.  
4. Session completes with a decision; snackbar may show *Presence grant awarded.* on success.

**C. Owner QR at the desk**  
1. Actions: assign a platform camera (USB webcam on the host is typical).  
2. Actions → **Scan Owner QR** (or **Scan Owner QR + Video** for dual-factor).  
3. Hold the owner QR from the mobile app in view of that **platform** camera (not the browser camera).  
4. On success the console submits the owner QR hit; for + Video, face verification continues on the same camera.

### Current QR / live result

- **Current QR Payload** — copy token; regenerate with **Render QR** if stale.
- When a session is active, chips may show decision, grant type, policy source, and related status.

---

## Overview

**Tab:** **Overview**

Metric cards (when summary data is loaded):

- **Total Sessions** · **Completed** · **Pending** · **Granted** · **Denied**

**Recent Sessions** — latest operator-readable session cards. Tap a card to open the **session inspector**.

---

## Analytics

**Tab:** **Analytics**

1. **Session Modes** — bar breakdown of `qr_only` / `camera_only` / `qr_plus_camera` usage.  
2. **Grant Types** — distribution of grant outcomes from the presence service.  
3. **User / day awards** (when available) — filter by user and date; expand a row to load granted sessions for that day; chips such as **QR**, **Cam**, **Cam & QR** / QR-to-cam transition filters.

Use this tab after a pilot day to confirm which modes and grants you are actually getting.

---

## Sessions

**Tab:** **Sessions**

Paginated list: *All presence sessions with server-side pagination and filtering.*

### Filters

| Control | Purpose |
|---|---|
| **User** | Free-text user filter |
| Date range | From / to pickers |
| Filter sheet | Multi-select chips by category |

Filter categories include:

- **Grant** (grant types from analytics)
- **Mode** — QR Only · Camera Only · QR + Camera
- **Decision** — Granted · Denied · Pending · Failed · Retry Required
- **Camera** · **Group** · **Member** · **Profile**

Apply filters, clear chips, and page through results. **Download** exports the filtered sessions to a workbook (columns include session UUID, times, mode, decision, grant type, QR status, and related identity fields).

### Session inspector

Tap a session card. Detail panels typically include:

| Section | Contents |
|---|---|
| **Session** | Mode, assurance, grant type, status, decision, QR status, detection status, camera, matched member / group / demographics when present |
| **Action Plan** | Planned steps and policy source |
| **Decision History** | Decision + reason code trail |
| **Audit Log** | Operator-readable audit entries |

Use **reason code** on denied / failed rows when troubleshooting policy or match failures.

---

## People (presence profiles)

**Tab:** **People**

Presence **people profiles** represent a person across presence activity (separate from Individual Group membership, though they can be linked by matching).

1. Tap **New** / create control → **New People Profile**.
2. Fill:

| Field | Required |
|---|---|
| **Name** | Yes |
| **Email** | Optional |
| **Phone** | Optional |
| **External Ref** | Optional |
| **Notes** | Optional |

3. **Save**. Search profiles from the search box.  
4. Edit or **Delete** from the profile card (delete asks for confirmation).

Empty state: *No people profiles yet. Create one to represent a person across groups.*

---

## Recommended setup order

1. [Cameras](./cameras-and-detection.md): add camera, connect, start instant detection.  
2. [Individual Groups](./detections-individuals-persons.md): create group, add members.  
3. Presence → **Actions**: **Reserve** the platform camera for Presence.  
4. Presence → **Settings**: **Reserve** the presence match group.  
5. Presence → **People**: create profiles if you track email/phone externally.  
6. Presence → **Actions**: run **Video Match**, **Scan Owner QR**, or **Render QR** as a dry run.  
7. Presence → **Sessions**: open the inspector and confirm granted / denied + reason.  
8. Presence → **Analytics**: confirm the session mode bucket moved.

## What good looks like

- Actions shows the assigned platform camera; Settings shows the match group  
- Actions produce a QR payload or a live session without errors  
- Overview granted/completed counts increase after a successful test  
- Session inspector shows decision, grant type, and (for matches) member/group chips  
- Denied sessions carry a readable reason code  

## Related

- [Cameras and detection](./cameras-and-detection.md)
- [Detections, individuals and persons](./detections-individuals-persons.md)
- [Vradar — alerts and automation](./alerts-and-automation.md)
- [Users and roles](./users-and-roles.md)
- [Entrances and activity](./entrances-and-activity.md) — traffic analytics, not presence sessions
