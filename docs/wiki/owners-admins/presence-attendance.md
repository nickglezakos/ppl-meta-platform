---
software_ref:
  platform_version: "2.25.86"
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

Run presence check-in and attendance flows (QR, camera, or both), manage people profiles, assign a platform camera for Actions, confirm video readiness in Settings, and review session outcomes.

**Where:** Home → **Presence** (`/presence`)

## Prerequisites

- Bootstrap completed; you can log in as owner or admin
- For camera-backed flows: at least one camera online — see [Cameras and detection](./cameras-and-detection.md)
- For known-person matching: an **Individual Group** with members — see [Detections, individuals and persons](./detections-individuals-persons.md)
- For **Video Match** / **QR + Video**: an active Vradar trigger in **People match** (`ppl_match`) or **Vprofile match** (`vprofile_match`) with camera(s), group(s), and a Presence action — see [Alerts and automation](./alerts-and-automation.md)
- Instant detection on the trigger’s camera when using video paths

## Session modes (basics)

| Mode (UI / API) | Meaning |
|---|---|
| **QR Only** (`qr_only`) | Check-in via QR (station QR or owner identity QR) |
| **Camera Only** (`camera_only`) | Face / people match via a ready match trigger + Presence action (UI: **Video Match**) |
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
| **Settings** | Video readiness report (camera assignment is on **Actions**) |

Refresh the dashboard with pull-to-refresh where available, or by leaving and re-entering Presence.

---

## Settings (video readiness)

**Tab:** **Settings** → **Presence Settings**

Video-backed buttons (**Video Match**, **Scan Owner QR + Video**) stay disabled until Settings reports green.

### What “ready” means

At least one **active** trigger must satisfy all of:

1. Mode is **People match** (`ppl_match`) or **Vprofile match** (`vprofile_match`)
2. One or more cameras are bound on the trigger
3. One or more individual groups are bound on the trigger
4. An attached action that Presence accepts (action type `presence_*`, name starting with **Presence Action**, or log config with `category` / tags `presence`)

Camera reservation under **Actions** is still used for **Scan Owner QR** (platform decode). Video grants themselves come from the match trigger’s Presence action when detection fires.

### Using the report

1. Open **Settings**.
2. Under **Video readiness**, confirm **Ready** (lists qualifying trigger names) or **Not ready** (checklist of missing steps).
3. If not ready, open **Triggers**, create/fix the match trigger + Presence action, ensure instant detection is running, then pull-to-refresh Settings.

QR-only flows (**Render QR**, **Scan Owner QR**) do not require this readiness report.

---

## Actions (run a check-in)

**Tab:** **Actions**

### Assign a platform camera (do this first for owner-QR scan)

1. Under **Presence Camera**, find the USB / RTSP / edge camera to use for presence.
2. Tap **Reserve**. Reserving also auto-binds the linked media collection when the backend can resolve one.
3. Confirm the snackbar. A chip shows the assigned camera.
4. **Unreserve** to clear.

Without an assigned camera, **Scan Owner QR** (and the QR step of **QR + Video**) cannot run platform decode.

Optional fields above / beside the QR panel:

| Field | Notes |
|---|---|
| **Device Display Name** | Label stored inside the QR payload (defaults differ for console vs station) |
| Location label | Optional label in the QR location payload |

### Operator buttons

| Button | Mode | What it does |
|---|---|---|
| **Render QR** | `qr_only` | Creates/reuses a session and renders a **station** presence QR. Shows under **Current QR Payload** (copyable). Mobile users scan this QR. |
| **Video Match** | `camera_only` | Starts a camera-only session when video readiness is green. Grants arrive when the match trigger’s Presence action fires. Disabled with a Settings hint when not ready. |
| **Scan Owner QR** | `qr_only` | Decodes an **owner identity** QR from the **assigned platform camera** (cameras service). Browser/webcam scanning is not used. Shows live preview for aiming when available. |
| **Scan Owner QR + Video** | `qr_plus_camera` | Same platform-camera QR decode, then camera verification. Disabled until video readiness is green. |

### Typical flows

**A. Station QR (phone scans screen)**  
1. Actions → **Render QR** (match-group reserve in Settings is not required for QR-only).  
2. Phone scans the displayed QR with the EyeNet mobile / presence path.  
3. Watch **Overview** / **Sessions** for granted or denied.

**B. Camera-only match**  
1. Triggers: active `ppl_match` or `vprofile_match` with camera, group, and Presence action; start [instant detection](./cameras-and-detection.md).  
2. Settings: confirm **Video readiness** is green.  
3. Actions → **Video Match**.  
4. Person stands in view of the trigger camera.  
5. Session completes with a decision; snackbar may show *Presence grant awarded.* on success.

**C. Owner QR at the desk**  
1. Actions: assign a platform camera (USB webcam on the host is typical).  
2. Actions → **Scan Owner QR** (or **Scan Owner QR + Video** when Settings is green).  
3. Hold the owner QR from the mobile app in view of that **platform** camera (not the browser camera).  
4. On success the console submits the owner QR hit; for + Video, face verification continues via the ready match trigger path.

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
3. [Triggers](./alerts-and-automation.md): create an active People match or Vprofile match trigger with that camera + group and a Presence action.  
4. Presence → **Actions**: **Reserve** the platform camera for owner-QR decode.  
5. Presence → **Settings**: confirm **Video readiness** is green.  
6. Presence → **People**: create profiles if you track email/phone externally.  
7. Presence → **Actions**: run **Video Match**, **Scan Owner QR**, or **Render QR** as a dry run.  
8. Presence → **Sessions**: open the inspector and confirm granted / denied + reason.  
9. Presence → **Analytics**: confirm the session mode bucket moved.

## What good looks like

- Settings **Video readiness** is green and lists the qualifying trigger(s)  
- Actions shows the assigned platform camera for owner-QR decode  
- Video Match / QR + Video are enabled only when readiness is green  
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
