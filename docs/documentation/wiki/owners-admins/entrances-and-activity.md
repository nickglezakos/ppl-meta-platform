---
software_ref:
  platform_version: "2.25.82"
  policy_revision: "2026-09-10"
  channels_documented:
    - sandbox
    - pilot
    - stable
  install_path: "windows-docker-desktop-ghcr"
  host_ram_gb: 16
  wsl_memory_gb: 12
title: Entrances and activity
audience: owner-admin
nav_order: 70
---

# Entrances And Activity

Monitor people activity at doors, corridors, and busy areas by composing cameras, live detection, analytics, automation, and (when needed) presence check-in. There is no separate **Gate** or **Entrances** home tile — you assemble the workflow from the screens below.

**Where (compose these):**

| Role in entrance ops | Home tile / route | Expanded how-to |
|---|---|---|
| Aim camera, start live detection | **Cameras** → `/cameras` · **Camera Ops** → `/camera-operations` | [Cameras and detection](./cameras-and-detection.md) |
| People, groups, preview review | **My Media** · **Individual Groups** | [Detections, individuals and persons](./detections-individuals-persons.md) |
| Organise recordings / time-window people search | **Collections** → `/collections` | [Media and collections](./media-management.md) |
| Traffic, demographics, peaks | **Analytics** → `/analytics` | [Analytics and reports](./analytics-and-reports.md) |
| Alerts & automation (**Vradar**) | **Automation** → `/triggers` | [Vradar — alerts and automation](./alerts-and-automation.md) |
| Check-in / attendance grants | **Presence** → `/presence` | [Presence and attendance](./presence-attendance.md) · phone-only: [EyeNet Authenticator](./presence-authenticator.md) |
| Optional lobby screens | **Signage Management** → `/signage` | [Digital signage](./digital-signage.md) |

---

## Prerequisites

- At least one camera aimed at the door / corridor / lobby, connected, with [instant detection](./cameras-and-detection.md) when you need live counters or Vradar
- For known-person rules: an **Individual Group** with members — [Detections, individuals and persons](./detections-individuals-persons.md)
- For notifications: Vradar actions (Alert / Email / Webhook / …) — [Vradar](./alerts-and-automation.md)
- For attendance at the door: Presence video readiness (match trigger + Presence action) and Actions camera reserve for owner-QR — [Presence](./presence-attendance.md)

---

## A. Building blocks (use the expanded sections)

Use this page as the **entrance story**. The figures show the controls those screens use. A cyan ring is a figure marker, not a highlight in the app. Names such as **Front Door** are examples. `--` stands in for a live count.

1. **Cameras** — Add RTSP or mobile camera, connect stream, start **instant detection**; confirm health on **Camera Ops**. Details: [Cameras and detection](./cameras-and-detection.md).
2. **People & groups** — After recordings or live matches, review people in Media Preview / Details; create watchlists under **Individual Groups**. Details: [Detections…](./detections-individuals-persons.md). For “who was at this door between 09:00–10:00?”, use Collections date/time search → **Details** → **Analysis**: [Media and collections](./media-management.md).
3. **Analytics** — Home → **Analytics** → **Filters** → Data Source (**Instant Detection** for live door traffic, or **Video Recording** for processed clips) → select the entrance collections → **Apply**. Read LEVEL 1–4 (counts, trends, demographics, heatmap / peaks). Export Excel if needed. Details: [Analytics and reports](./analytics-and-reports.md).
4. **Vradar (triggers)** — Create **actions** first, then **triggers** (typically **Instant Demographic** or **Instant People Match**) on the entrance camera; link Alert / Email / Webhook / Digital Signage. Confirm firings on Automation → **Analytics**. Details: [Vradar — alerts and automation](./alerts-and-automation.md).
5. **Presence (optional)** — When the entrance is also a **check-in point**, ensure Settings **Video readiness** is green (active people-match / Vprofile-match trigger with camera, group, and Presence action), reserve the platform camera under Presence → **Actions** for owner-QR decode, then run **Video Match**, **Render QR**, etc. Details: [Presence and attendance](./presence-attendance.md). Presence Actions are started from the Presence screen; Vradar does not replace them — you run both when you want alerts *and* attendance.

### Cameras — Instant Detection

![Full Cameras Settings screen. Pipelines shows Instant Detection on; the cyan ring marks that switch.](./images/instant-detection.png)

On the camera **Pipelines** section, turn **Instant Detection** on for live door traffic and Vradar. The subtitle is *Real-time person detection with triggers*. **Recording Pipeline** (*Video segments with face detection*) is a separate switch. Confirm the camera on **Camera Ops**. Adding the stream is on [Cameras and detection](./cameras-and-detection.md).

### Analytics — door traffic

![Full MVR Analytics screen. App bar, applied filter bar, and level cards; the cyan ring marks Filters.](./images/mvr-analytics-bar.png)

Home → **Analytics** opens **MVR Analytics**. **Refresh** reloads the dashboard. **Filters** opens Filter Analytics.

![Full MVR Analytics screen with Filter Analytics open. Instant Detection and Today are selected; Front Door is an example collection.](./images/filter-analytics.png)

**Data Source** is **Video Recording** or **Instant Detection**. With Instant Detection selected, the helper reads *Analytics from real-time instant detection sessions*. **Time Range** is Today, Last Hour, Last 3 Hours, Last Week, Last Month, or Custom Range (Start Date and End Date; both are required). **Collections** lists the entrance collections; **Clear** removes the selection. The count under the heading is `1 selected` or `All collections (N)` when none are checked. **Demographics** has **Gender** (Male, Female) and **Age Group** (Young (0-25), Adult (26-65), Elderly (65+)). **Auto-refresh (10 min)** stays off until you turn it on (*Automatically update data*). **Apply** saves the filter. **Cancel** closes it.

![Full MVR Analytics screen after Apply. Filter bar shows Time Today, one collection, and Instant Detection.](./images/analytics-filter-bar.png)

After Apply, the bar under the app bar shows `Time: Today` and, when collections are selected, `Collections: N selected`. The **Instant Detection** chip appears only for that data source. Its × sets the source back to Video Recording and reloads.

![Full MVR Analytics dashboard with LEVEL 1–4 headers. Counts are placeholders.](./images/analytics-levels.png)

The header is **MVR People Detection Analytics**, subtitle *Real-time insights from camera collection MVR search results*. **LEVEL 1 Basic Metrics**: Total People (*Unique individuals*), Active Collections (*With detections*), and Sessions (*Detection sessions*) when the source is Instant Detection. That third card is **Videos Analyzed** when the source is Video Recording. **LEVEL 2 Time-Based Trends**: Total, Peak, Average. **Level 3** is Demographics Distribution. **Level 4** is Behavioral Insights. With no data it shows *No behavioral data available* and *Try selecting a different time period or camera*. Charts and the weekly heatmap are left off this figure. `--` is the empty-value placeholder, not a live result.

![Full MVR Analytics screen with Export Analytics open. Excel Spreadsheet is the export option.](./images/export-analytics.png)

**Export** opens **Export Analytics**. **Excel Spreadsheet** (*Open with Excel, LibreOffice, etc.*) writes the file. With nothing to export, the app shows *No analytics data to export*.

### Recommended baseline order

1. Camera + instant detection at the entrance.  
2. Analytics filter to that camera / collection (sanity-check traffic).  
3. Vradar action + trigger for the operational alert.  
4. Add Individual Groups / Presence only when you need known-person or attendance flows.

### What good looks like (baseline)

- Live counters update on the entrance camera card  
- Analytics for that camera / Instant Detection shows traffic in the selected window  
- A test Vradar trigger fires the expected notification  
- (If used) Presence session shows granted / denied in **Sessions**

---

## B. Example use cases

### Use case 1 — Busy lobby / corridor: crowd alert + review

**Goal:** Know when the main entrance gets crowded, notify operators, and review patterns later.

**Compose:** Cameras → Instant detection → Vradar Instant Demographic + Alert/Email → Analytics (and optional Collections search).

| Step | Where | What to do |
|---|---|---|
| 1 | [Cameras](./cameras-and-detection.md) | Aim camera at lobby/door; connect; start **instant detection**. |
| 2 | [Vradar — Create an action](./alerts-and-automation.md#create-an-action) | Create e.g. **Alert (On-Screen)** and/or **Email** (*High lobby occupancy*). Keep **Active**. |
| 3 | [Vradar — Create a trigger](./alerts-and-automation.md#create-a-trigger) | **Instant Demographic** on that camera — e.g. People Count ≥ threshold, Time Span `any`, Cooldown `60`, link the action(s), **Active**. |
| 4 | Test | Walk a group past the camera; confirm on-screen alert / email and Automation → **Analytics** log. |
| 5 | [Analytics](./analytics-and-reports.md) | **Filters** → **Instant Detection** → Today / Last Week → select entrance collection → review peaks, heatmap, demographics. **Export** Excel for a shift report. |
| 6 | Optional | [Media and collections](./media-management.md) date/time search on the camera collection → **Details** → **Analysis** for who appeared in a specific window. |

![Full Automation Actions screen with Create User Action open for an on-screen crowd alert. Alert on High Traffic is an example name.](./images/create-action-alert.png)

Step 2 is **Create User Action**. **Action Type** **Alert (On-Screen)** needs **Alert Message**, **Severity**, and **Duration (seconds)**. Leave **Active** on. *Alert on High Traffic* and *High traffic detected!* are examples.

![Full Automation Triggers screen with Create Trigger open for Instant Demographic. Front Door and the count of 2 are examples.](./images/create-trigger-demographic.png)

Step 3 is **Create Trigger** with **Trigger Mode** **Instant Demographic**. **Demographic Conditions (All must match)** uses Field **People Count**, an operator, and a value. The **+** adds another AND condition. **Select Camera** is the entrance camera. Time Span `any` means always; the **?** beside it opens the format examples. **User Actions** links the alert from step 2. **Cooldown (seconds)** is the minimum gap between firings. Leave **Active** on. **Create** saves the trigger.

![Full Collections screen with Filter Collections by Date/Time open. Last 7 days is selected; dates are an example window.](./images/datetime-filter.png)

![Full Collections screen with Cross-Video Tracking Details open. Counts are an example, not a live result; Analysis opens the cross-video screen.](./images/cross-video-details.png)

Step 6 is **Filter Collections by Date/Time**. Set **Start Date & Time** and **End Date & Time**, or a quick filter (Last 24 hours, Last 7 days, Last 30 days, Last 90 days). **Apply** filters the grid. **Details** opens **Cross-Video Tracking Details**; **Analysis** continues into the cross-video screen.

**What good looks like:** Trigger fires when the crowd threshold is met; Analytics LEVEL 2/4 show the same busy hours; Excel export shares the summary with ops.

---

### Use case 2 — Staff / authorized entrance: Vradar people-match alert + Presence Actions for attendance

**Goal:** Alert when a watched person (or unknown person) appears at the door **and** run a Presence check-in so attendance can be **granted** or **denied** against the same match group.

**Compose:** Individual Group → Cameras + instant detection → Vradar Instant People Match (alert + Presence action) → Presence Settings readiness + **Actions** (Video Match / QR).

Vradar handles **detection → notification** (and can fire the Presence action that awards the grant). Presence → **Actions** starts the session; Presence → **Settings** must show video readiness green. Use the same Individual Group on the match trigger so “who we watch” and “who we check in” stay aligned.

| Step | Where | What to do |
|---|---|---|
| 1 | [Detections — Person groups](./detections-individuals-persons.md#c-person-groups-individual-groups) | Create e.g. `Staff – Main Door`; add members (from video Details → **Add to Group**, or **Add Members**). |
| 2 | [Cameras](./cameras-and-detection.md) | Entrance camera connected; **instant detection** running. |
| 3 | [Vradar — action](./alerts-and-automation.md#create-an-action) | Create **Alert** and/or **Email** (e.g. *Staff match at main door* or *Unknown at main door*), plus a **Presence** action (or log tagged `presence`) for attendance grants. |
| 4 | [Vradar — Instant People Match](./alerts-and-automation.md#create-a-trigger) | Select that camera and the **Staff** Individual Group. Use normal match for “known person alert”, or **NOT mode** for “unknown person at door”. Link actions (including Presence); set cooldown; **Active**. |
| 5 | Test Vradar | Known (or unknown) person in view → confirm notification / Automation **Analytics**. |
| 6 | [Presence — Settings](./presence-attendance.md) | Confirm **Video readiness** is green for that trigger. |
| 7 | [Presence — Actions](./presence-attendance.md) | **Reserve** the entrance camera for owner-QR decode if needed. For camera check-in: **Video Match**. For phone check-in: **Render QR** or **Scan Owner QR** / **Scan Owner QR + Video**, or use [EyeNet Authenticator](./presence-authenticator.md) for attendance-only (no mobile camera registration). |
| 8 | Presence → **Sessions** / **Overview** | Confirm grant/deny, reason codes, origin when relevant, and that Analytics outcomes / origin buckets moved. |

![Full Presence Settings screen. Video readiness reports Not ready because no match trigger exists yet.](./images/video-readiness.png)

Step 6 is Presence → **Settings** → **Video readiness**. Video Match and QR + Video need an active people-match or Vprofile-match trigger with a camera, a group, and a Presence action. Until that exists, the panel says **Not ready for video presence** and *No people-match or Vprofile-match trigger exists.* The hint is: *In Triggers, create a trigger with mode People match (ppl_match) or Vprofile match (vprofile_match). Then pull to refresh this report.*

![Full Presence Actions screen. Video Match and Scan Owner QR + Video show Not ready.](./images/presence-actions.png)

Step 7 is Presence → **Actions**. **Render QR** and **Scan Owner QR** stay available. **Video Match** and **Scan Owner QR + Video** show **Not ready** until video readiness is green. **Device Display Name** defaults to *Presence Web Console*. **Location Label** is *Optional local label stored inside the QR payload.*

**Optional extras:** Link a [Digital Signage](./digital-signage.md) action from the same Vradar trigger to change lobby content when a match fires; review door traffic later in [Analytics](./analytics-and-reports.md) with **Instant Detection**.

**What good looks like:** Vradar fires on match (or NOT-match); Presence **Video Match** / QR completes with *Presence grant awarded.* (or a clear deny reason); Sessions inspector shows member/group chips for successful matches.

---

## Common issues

- **No live counters / Vradar never fires** — instant detection not running on that camera; see [Cameras](./cameras-and-detection.md)
- **People Match never fires** — empty Individual Group or wrong camera; populate group first ([Detections](./detections-individuals-persons.md))
- **Analytics empty for the door** — wrong Data Source or collection filter ([Analytics](./analytics-and-reports.md))
- **Presence deny while Vradar alerted** — Presence Settings camera/group not reserved, or policy/reason on the session; inspect Presence → **Sessions**
- **Expecting Presence from the Automation + menu** — start Presence Actions on **Presence** → **Actions**; link Vradar only for alerts / email / webhook / signage

---

## Related

- [Cameras and detection](./cameras-and-detection.md)
- [Detections, individuals and persons](./detections-individuals-persons.md)
- [Media and collections](./media-management.md)
- [Vradar — alerts and automation](./alerts-and-automation.md)
- [Analytics and reports](./analytics-and-reports.md)
- [Presence and attendance](./presence-attendance.md)
- [EyeNet Authenticator](./presence-authenticator.md)
- [Digital signage](./digital-signage.md)
