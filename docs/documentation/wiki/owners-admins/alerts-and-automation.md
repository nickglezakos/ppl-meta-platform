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
title: Vradar — alerts and automation
audience: owner-admin
nav_order: 40
---

# Vradar — Alerts And Automation

**Vradar** is the product view of Automation: **triggers** and **actions** driven by **instant detection** (and related search) results. Configure it under Home → **Automation** (`/triggers`).

Use it for person-of-interest alerts, demographic thresholds, and automated follow-ups (on-screen alert, email, webhook, log, messaging app, digital signage) on cameras running live detection.

**Where:** Home → **Automation** (`/triggers`)

## Screen layout

Three tabs:

| Tab | Purpose |
|---|---|
| **Triggers** | Rules that evaluate detections and fire linked actions |
| **Actions** | Reusable outcomes (alert, email, webhook, …) |
| **Analytics** | Charts and communication logs for firings / deliveries |

App bar:

| Control | Purpose |
|---|---|
| **+** menu | **Add Trigger** or **Add Action** |
| Refresh | Reload lists |
| Help | Short in-app explanation of the active tab |

![Full Automation screen on Triggers. The cyan ring marks + with Add Trigger / Add Action open. Left list and right detail pane are shown.](./images/automation-toolbar.png)

The marked **+** opens **Add Trigger** (bolt) and **Add Action**. **Refresh** is the circular arrow to its right. **Help** is the question mark. **Triggers** is the selected tab in this figure; **Actions** and **Analytics** are the other two tabs. The cyan outline is only a marker in this figure.

Create **actions first**, then **triggers** that link to them.

## How the create forms work

Both create dialogs share one shell and **swap the middle of the form** when you change the type dropdown:

| Dialog | Dropdown | What changes |
|---|---|---|
| **Create User Action** | **Action Type** | Type-specific fields below the common block |
| **Create Trigger** | **Trigger Mode** | Mode-specific configuration card (and which camera controls appear) |

Common fields stay the same. Only the type/mode block changes. The rest of this page documents **every field for every Action Type and every Trigger Mode**.

## Prerequisites

- At least one camera with [instant detection](./cameras-and-detection.md) running (core Vradar path)
- For Instant / Search People Match and VProfile Match: an existing **Individual Group** already populated — see [Detections, individuals and persons](./detections-individuals-persons.md)
- For **Email**: communications / SMTP configured on the installation
- For **Digital Signage** / **Signage Rich Message**: players and playlists (or rich-message templates) set up — see [Digital signage](./digital-signage.md)
- For **Messaging App**: a Slack or Teams incoming webhook URL
- Specialised trigger modes (body posture, velocity, left object, vehicle + plate) need the matching detection stages enabled on the camera

---

## Actions

### Open the create dialog

1. Home → **Automation**.
2. Open the **Actions** tab (or use **+** → **Add Action**).
3. Dialog title: **Create User Action** (or **Edit User Action** when editing).

### Common fields (every Action Type)

These appear for every type. Changing **Action Type** does not remove them.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Name** | Yes | empty | Display name on the Actions list and when linking from a trigger. Hint example: `Alert on High Traffic`. |
| **Description (Optional)** | No | empty | Free text shown on the action card / detail. Hint example: `Shows alert when threshold is met`. |
| **Action Type** | Yes | **Alert (On-Screen)** | Selects which form body appears below. Values listed in the next section. |
| **Active** | — | on | Switch. Leave on so triggers can fire this action. Off pauses the action without deleting it. |

Footer: **Cancel** · **Create** (reads **Update** when editing).

### Action Type catalogue

Exact dropdown labels:

1. [Alert (On-Screen)](#alert-on-screen)
2. [Email](#email)
3. [Webhook](#webhook)
4. [Log](#log)
5. [Digital Signage](#digital-signage)
6. [Signage Rich Message](#signage-rich-message)
7. [Messaging App (Slack / Teams)](#messaging-app-slack--teams)

---

### Alert (On-Screen)

Shows a toast / banner in the product UI when a linked trigger fires.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Alert Message \*** | Yes | empty | Text shown in the on-screen alert. Hint: `High traffic detected!`. Supports [template variables](#template-variables). |
| **Severity** | No | **Warning** | `Info` · `Warning` · `Error` · `Critical`. Controls how the alert is presented. |
| **Duration (seconds)** | Yes (positive integer) | `30` | How long the alert stays visible. Helper: “How long the alert should be displayed”. |

![Full Automation Actions screen with Create User Action open for an on-screen alert.](./images/create-action-alert.png)

Example only: name **Alert on High Traffic**, type **Alert (On-Screen)**, message **High traffic detected!**, severity **Warning**, duration **30**, **Active** on.

---

### Email

Sends mail through the installation’s communications / SMTP path.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Recipient Email \*** | Yes | empty | Primary recipient. Hint: `user@example.com`. |
| **CC (Optional)** | No | empty | Extra recipients. Helper: “Separate multiple emails with commas”. |
| **Subject \*** | Yes | empty | Email subject. Helper lists variables such as `{trigger_name}`, `{reason}`, `{match_reason}`, `{matched_member_uuid}`, `{matched_member_name}`, `{group_member_number}`, `{similarity_score}`. |
| **Email Body** | No | empty | Message body. Hint example uses `{trigger_name}` and `{timestamp}`. Prefer variables from the [template variables](#template-variables) table that the runtime substitutes. |

SMTP must already work on the install or delivery fails (check **Analytics**).

---

### Webhook

HTTP call to an external URL when the trigger fires.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Webhook URL \*** | Yes | empty | Destination URL. |
| **HTTP Method** | No | **POST** | `GET` · `POST` · `PUT` · `PATCH`. |
| **Headers (Optional JSON)** | No | empty | Optional header object. Must be valid JSON if filled. |
| **Payload (Optional JSON)** | No | empty | Optional body object. Must be valid JSON if filled. Message-body template variables are **not** interpolated into this payload the way they are for alert/email text. |

---

### Log

Writes an audit / log entry via communications.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Log Message \*** | Yes | empty | Logged text. Helper: available variables `{trigger_name}`, `{timestamp}` (prefer the runtime set in [template variables](#template-variables)). |
| **Log Level** | No | **Info** | `Debug` · `Info` · `Warning` · `Error`. |

---

### Digital Signage

Pushes a **playlist** to one or more signage players (switches what is playing).

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Target Devices \*** | Yes (≥1) | none | Checkboxes for discovered signage players. Prefer online devices. |
| **Playlist \*** | Yes | none | Playlist to start on the selected devices. |
| **Second Playlist** | No | none | Optional playlist to switch to after the first playlist has played for the duration below. |
| **Duration (seconds)** | No (only when Second Playlist is set) | **10** | How long the first playlist plays before switching to the second. Empty uses 10 seconds. Hidden unless a second playlist is selected. |
| **Transition Mode** | No | **Immediate** | `Immediate` · `After Current Video` · `Fade Transition`. |
| **Fade Duration (ms)** | Only when Fade Transition | `1000` | Fade length in milliseconds. Hidden unless transition is fade. |

If no devices appear, start players and confirm Discovery — see [Digital signage](./digital-signage.md).

---

### Signage Rich Message

Shows a **rich-message overlay** on selected players without stopping the playlist.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Target Devices \*** | Yes (≥1) | none | Signage players that should show the overlay. |
| **Rich Message Template \*** | Yes | none | Template picker (`name (layout)`). Choosing a template can set the default duration from the template. |
| **Duration override (ms)** | No | `15000` (or template default) | How long the overlay stays on screen. Helper: “How long the overlay stays on screen”. |

Title/message text inside the **template** (not this dialog) can use [template variables](#template-variables) at fire time.

---

### Messaging App (Slack / Teams)

Posts to Slack or Microsoft Teams via an incoming webhook.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Platform \*** | Yes | **Slack** | `Slack` · `Microsoft Teams`. Changes helpers and which optional fields apply. |
| **Webhook URL \*** | Yes | empty | Incoming webhook URL for the chosen platform. |
| **Message Template \*** | Yes | empty | Message body. Helper lists `{trigger_name}`, `{reason}`, `{match_reason}`, `{similarity_score}`, `{matched_member_name}`. |
| **Card Title (Optional)** / **Title (Optional)** | No | empty | Teams: Adaptive Card title (interpolated). Slack: title field is not used for Slack delivery. |
| **Mention (Optional)** | Slack only | empty | Prepended mention, e.g. `@channel` or `@here`. Hidden for Teams. |

### Manage actions after create

- Filter / search the Actions list; open a row for the detail pane
- **Active / Inactive** on the action
- **Edit** / **Delete** on the detail pane
- Keep actions **Active** before linking them from triggers

### What good looks like (actions)

- Action appears with the correct type label
- **Active** is on
- Required type-specific fields validate (recipient, URL, message, devices, template, …)

![Full Automation Actions screen with Alert on High Traffic selected in the list and shown in the detail pane.](./images/action-card.png)

**Alert on High Traffic** is an example name. The type badge is **Alert** (the on-screen type). **Active** is the status chip. Body lines are description and alert message from the action config.

---

## Triggers

### Open the create dialog

1. Home → **Automation** → **Triggers** tab.
2. App bar **+** → **Add Trigger**.
3. Dialog title: **Create Trigger**.

### Common fields (every Trigger Mode)

These stay visible for every mode. Changing **Trigger Mode** swaps only the configuration card in the middle (and whether you pick one camera or many).

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Name \*** | Yes | empty | Unique, readable name on the Triggers list. |
| **Description** | No | empty | Free text (about two lines in the dialog). |
| **Trigger Mode** | Yes | **Instant Demographic** | Selects which configuration card appears. Values listed below. |
| **Time Span \*** | Marked required; default is usable | `any` | When the rule is allowed to fire. Examples from the in-app **?**: `any`; `Mon-Fri 09:00-17:00`; `Mon,Wed,Fri 08:00-12:00`; `Sat-Sun 00:00-23:59`. |
| **User Actions (Optional)** | No | none | Multi-select of existing actions. When the trigger fires, **all** selected actions run. “None selected” is allowed while testing conditions. |
| **Tracking Duration** | No | `10` | Numeric lookback / tracking window size used with **Unit**. Stored together (for example `10 minutes`). Important for search lookback and some match paths. |
| **Unit** | No | **Minutes** | `Seconds` · `Minutes` · `Hours` · `Days`. Paired with **Tracking Duration**. |
| **Cooldown (seconds)** | No | `60` | Minimum seconds between firings of this trigger. Helper: “Minimum seconds between trigger firings”. Lower values allow more frequent firings; higher values suppress storms. |
| **Active** | — | on | Leave on for production. Toggle off from the list to pause without deleting. |

**Camera pattern**

| Pattern | Modes | Control |
|---|---|---|
| Single camera | Instant Demographic, Instant People Match | **Camera \*** → **Select Camera** (any registered camera; detection should be running for live firings) |
| Multi-camera inside the mode card | Search *, VProfile, Body Posture, Velocity, Left Object, Vehicle + Plate | **Cameras \*** / **Cameras to Search \*** checkboxes inside the mode card — the single **Select Camera** dropdown is hidden |

### Trigger Mode catalogue

Exact dropdown labels, grouped by family:

| Family | Modes |
|---|---|
| **Core Vradar (live)** | [Instant Demographic](#instant-demographic), [Instant People Match](#instant-people-match) |
| **Search (scheduler)** | [Search People Match](#search-people-match), [Search Demographic](#search-demographic) |
| **Specialised** | [VProfile Match (Multi-Group, Multi-Camera)](#vprofile-match-multi-group-multi-camera), [Body Posture (Multi-Camera)](#body-posture-multi-camera), [Velocity (Multi-Camera)](#velocity-multi-camera), [Left / Stationary Object](#left--stationary-object), [Vehicle + Plate](#vehicle--plate) |

Prefer Instant Demographic and Instant People Match for a standard Vradar setup unless your distributor has enabled a specialised path.

---

### Instant Demographic

Live evaluation of demographic conditions from instant detection on **one** camera. All conditions use **AND** logic.

**Mode card:** **Demographic Conditions (All must match)** — use **+** to add rows. At least one condition is required. New row defaults: Field **People Count**, Op **≥**, value **1**.

#### Per-condition fields

| Field | Values | Explanation |
|---|---|---|
| **Field** | `People Count` · `Male %` · `Female %` · `Age` | What is measured in the live detection. |
| **Op** | `>` `≥` `<` `≤` `=` | Comparison operator. |
| Value | Depends on Field | Label becomes **Count**, **Percent** (suffix `%`), or **Age** (suffix `yrs`). Changing Field resets a sensible default: percent → `50`, Age → `18`, count → `1`. Age input is clamped to **1–100**. |

#### Camera

| Field | Required | Explanation |
|---|---|---|
| **Camera \*** / **Select Camera** | Yes | Single live camera. Helper: all registered cameras (connected or disconnected). Instant detection should be running for live firings. |

Then complete the [common fields](#common-fields-every-trigger-mode) (Time Span, User Actions, Tracking Duration / Unit, Cooldown, Active).

![Full Automation Triggers screen with Create Trigger open for Instant Demographic.](./images/create-trigger-demographic.png)

Example only: **People Count ≥ 2** on camera **Front Door**, Time Span `any`, User Actions linked to the alert, Cooldown **60**, **Active** on.

---

### Instant People Match

Live face match against **one** Individual Group on **one** camera.

**Mode card:** **PPL Match Configuration**

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Individual Group \*** | Yes | none | Existing group whose members are matched (whitelist / watchlist). Create groups elsewhere — see [Detections, individuals and persons](./detections-individuals-persons.md). |
| **Similarity Threshold (0..1)** | Yes | `0.75` | Minimum face similarity. Higher = stricter. Must be between 0.0 and 1.0. |
| **Top K** | Yes | `1` | How many top matches to keep (≥ 1). |
| **NOT mode** | No | off | Switch. Subtitle: “Fire when NO group members are matched”. Useful for unknown-person / exclusion rules. |

| Field | Required | Explanation |
|---|---|---|
| **Camera \*** / **Select Camera** | Yes | Single live camera for matching. |

Then complete the common fields.

---

### Search People Match

Periodic search across **recordings** for group members — not live Redis instant events.

**Mode card:** **Search Configuration**

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Individual Group \*** | Yes | none | Group whose members are searched in recordings. Helper: “Group whose members will be searched against camera recordings”. |
| **Cameras to Search \*** | Yes (≥1) | none | Multi-check cameras included in each search run. |
| **Search Interval (seconds)** | Yes | `300` | How often the scheduler runs. Minimum **30** (helper: “Min 30s”). |
| **Similarity Threshold** | Yes | `0.75` | 0.0–1.0 match floor for search hits. |
| **NOT mode** | No | off | “Fire when NO group members are found in camera recordings”. |

No single **Select Camera** dropdown — cameras are chosen only in this card. **Tracking Duration** / **Unit** (common fields) set the lookback window for the search.

---

### Search Demographic

Periodic demographic aggregates across selected cameras, then the same AND condition list as Instant Demographic.

**Mode card:** **Search Demographic Configuration**

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Cameras to Search \*** | Yes (≥1) | none | Cameras queried each interval. |
| **Search Interval (seconds)** | Yes | `300` | Minimum **30**. Helper: “Min 30s. How often cameras are queried for demographics.” |
| **Demographic Conditions (All must match)** | Yes (≥1 condition) | People Count ≥ 1 | Same **Field** / **Op** / value controls as [Instant Demographic](#instant-demographic). |

Then complete the common fields (Tracking Duration sets the aggregation lookback).

---

### VProfile Match (Multi-Group, Multi-Camera)

Live multi-camera, multi-group people match. List cards may shorten the mode to **VProfile Multi-Group**.

**Mode card:** **VProfile Match Configuration**

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Cameras \*** | Yes (≥1) | none | Cameras that contribute live detections. |
| **Individual Groups \*** | Yes (≥1) | none | One or more groups to match against. |
| **Similarity Threshold (0..1)** | Yes | `0.75` | Minimum similarity 0–1. |
| **Top K** | Yes | `1` | Max top matches kept (≥ 1). |
| **NOT mode** | No | off | “Fire when NO group members are matched”. |

---

### Body Posture (Multi-Camera)

Fires when posture consensus across recent frames matches the target on selected cameras.

**Mode card:** **Body Posture Configuration**

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Cameras \*** | Yes (≥1) | none | Cameras to watch. |
| **Target posture** | Yes | **Horizontal** | `Horizontal` · `Upright` · `Either (upright or horizontal)`. Posture class that should fire the rule. |
| **Window size (3-4)** | Yes | `4` | Number of recent samples in the consensus window. Must be **3 or 4**. |
| **Min matches** | Yes | `3` | How many samples in the window must match the target (1 … window size). |
| **Min posture confidence (0..1)** | Yes | `0.5` | Minimum model confidence for a sample to count. |

Requires body / posture detection capability on those cameras.

---

### Velocity (Multi-Camera)

Fires when estimated speed meets a gait-band floor on selected cameras.

**Mode card:** **Velocity Configuration**

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Cameras \*** | Yes (≥1) | none | Cameras to watch. |
| **Scope** | Yes | **Crowd mean** | `Crowd mean` — mean speed of the crowd; `Any person` — at least one person exceeds the floor. Helper: “Crowd = mean speed; Any person = at least one exceeds”. |
| **Gait band (fires when speed ≥ floor)** | Yes | Walking band | `Walking (≥ 1.25 m/s ≈ 4.5 km/h)` · `Light running (≥ 2.2 m/s ≈ 8 km/h)` · `Running (≥ 3.3 m/s ≈ 12 km/h)` · `Fast running (≥ 5.0 m/s ≈ 18 km/h)`. The trigger fires when measured speed is at or above that floor. |

---

### Left / Stationary Object

Stable or abandoned object in an ROI. Needs object detection on the camera (`auto_object_detection`; V2 abandon also uses body detection).

**Mode card:** **Left / Stationary Object Configuration**

Helper in the card: enable **auto_object_detection** on the camera; for V2 abandon behaviour also enable **auto_body_detection**.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Cameras \*** | Yes (≥1) | none | Cameras to monitor. |
| **Object classes \*** | Yes | backpack, handbag, suitcase, bottle selected | Allowlist chips: `backpack`, `handbag`, `suitcase`, `bottle`, `cup`, `cell phone`, `laptop`, `book`, `umbrella`. |
| **T_stable (seconds)** | No | `60` | Seconds of low motion before the object is treated as STABLE. Helper: “Low motion before STABLE”. |
| **T_abandon (seconds)** | No | `30` | Wait after no body nearby (V2). Helper: “No body nearby (V2)”. |
| **Min box area (px)** | No | `400` | Reject detections smaller than this area. |
| **Proximity (px)** | No | `120` | Body–object distance for V2. Helper: “Body–object distance (V2)”. |
| **Require person left (V2)** | No | off | Switch. “Fire only after a person was near the object and left”. Off → V1 stable-only behaviour. |
| **ROI** | No | Full frame | Status shows “Full frame by default” or “Custom ROI (N points)”. Buttons: **Use center 50% ROI**, **Clear ROI (full frame)**. |

---

### Vehicle + Plate

Stable vehicle track in an ROI; optional plate OCR metadata.

**Mode card:** **Vehicle + Plate Configuration**

Helper in the card: enable **auto_vehicle_detection**; plate OCR attaches metadata when readable.

| Field | Required | Default | Explanation |
|---|---|---|---|
| **Cameras \*** | Yes (≥1) | none | Cameras to monitor. |
| **Vehicle classes \*** | Yes | all selected | Allowlist chips: `car`, `motorcycle`, `bicycle`, `truck`, `bus`. |
| **T_stable (seconds)** | No | `15` | Seconds of low motion before STABLE. Helper: “Low motion before STABLE”. |
| **Min box area (px)** | No | `800` | Minimum detection box area. |
| **Plate OCR enabled** | No | on | Switch. “Attach plate_text metadata when OCR succeeds (V2)”. |
| **OCR every N cycles** | No | `2` | How often OCR runs while tracking. |
| **ROI** | No | Full frame | Same center-50% / clear controls as Left / Stationary Object. |

### Save a trigger

1. Tap **Create** (or **Update**).
2. Fix validation snackbars (missing camera, group, threshold out of 0–1, no search cameras, empty conditions, etc.).
3. Confirm the trigger appears on the **Triggers** tab with mode badge and **Active**.

![Full Automation Triggers screen. Crowd at front door selected; content pane shows the Details (gear) view with status, mode, camera, conditions, Edit and Delete.](./images/trigger-card.png)

**Crowd at front door** is an example name. This figure is the **Details** view (gear side of the content-pane mode pill). Mode badge **Instant Demographic**. Camera line and **1 condition(s)** come from the saved rule. Chip **Alert on High Traffic** is a linked action; no actions → **None**.

### Trigger content pane — communication logs

Selecting a trigger opens the right **content pane**. By default the pane shows that trigger’s **communication logs** (firings / deliveries for its linked actions), not the settings card.

| Content-bar control | View |
|---|---|
| **List** icon (default) | Communication logs for this trigger only |
| **Gear** icon | Details: status, mode, camera / conditions summary, **Edit**, **Delete** |

The cyan outline on the mode pill in the figures below marks the pill; the filled list icon means logs are active. Each log card shows a headline (subject or “type to recipient”), a metadata line (time · recipient · attempts), and chips for **status** (`SENT` / `PENDING` / `FAILED`) and **communication type** (`alert`, `email`, `webhook`, …). Tap a card for full log details. Empty state: **No logs recorded for this item yet.**

Logs below are examples only — names, times, and delivery outcomes are illustrative.

#### Instant Demographic — logs

![Full Automation Triggers screen. Instant Demographic trigger selected; content pane shows its communication logs list (list icon active).](./images/trigger-logs-demographic.png)

#### Instant People Match — logs

![Full Automation Triggers screen. Instant People Match trigger selected; content pane shows email delivery logs for matches.](./images/trigger-logs-ppl-match.png)

#### Search People Match — logs

![Full Automation Triggers screen. Search People Match trigger selected; content pane shows webhook delivery logs.](./images/trigger-logs-search.png)

#### Search Demographic — logs

![Full Automation Triggers screen. Search Demographic trigger selected; content pane shows alert logs.](./images/trigger-logs-search-demographic.png)

#### VProfile Match — logs

![Full Automation Triggers screen. VProfile Multi-Group trigger selected; content pane shows messaging-app delivery logs.](./images/trigger-logs-vprofile.png)

#### Body Posture — logs

![Full Automation Triggers screen. Body Posture trigger selected; content pane shows alert logs.](./images/trigger-logs-body-posture.png)

#### Velocity — logs

![Full Automation Triggers screen. Velocity trigger selected; content pane shows audit log entries.](./images/trigger-logs-velocity.png)

#### Left / Stationary Object — logs

![Full Automation Triggers screen. Left / Stationary Object trigger selected; content pane shows webhook logs.](./images/trigger-logs-left-object.png)

#### Vehicle + Plate — logs

![Full Automation Triggers screen. Vehicle + Plate trigger selected; content pane shows email logs with plate examples.](./images/trigger-logs-vehicle-plate.png)

### Manage triggers after create

- Filter: All / Active / Inactive; search by name

![Full Automation Triggers screen. Status filters All / Active / Inactive are marked; All is selected.](./images/trigger-status-filters.png)

**All**, **Active**, and **Inactive**. **All** uses the dashboard icon. The cyan outline marks the filter control in this figure.

- Tap a trigger → content pane opens on **logs** (list icon); use the gear for Details / Edit / Delete
- Tap status to toggle Active / Inactive
- Cross-trigger delivery history is also on the **Analytics** tab

### What good looks like (triggers)

- Instant detection (or the specialised stage) is running on the selected camera(s)
- Trigger shows **Active** with the expected mode label
- Causing a matching scene fires linked actions and adds rows to that trigger’s logs list
- Cooldown stops duplicate storms within the configured window

---

## Template variables

Used in supported action text fields at fire time (`{variable_name}`).

| Variable | Meaning | Typically filled when |
|---|---|---|
| `{trigger_name}` | Trigger name | Always |
| `{trigger_id}` | Trigger UUID | Always |
| `{reason}` | Why the evaluation passed | Always |
| `{match_reason}` | Formatted best face match | People-match / search match |
| `{matched_member_uuid}` | Matched member UUID | People-match / search match |
| `{matched_member_name}` | Matched member display name | Named people-match |
| `{group_member_number}` | Member ordinal in the group | People-match / search match |
| `{similarity_score}` | Similarity 0–1 | People-match / search match |

**Where they apply**

| Action Type | Interpolated fields |
|---|---|
| Alert (On-Screen) | **Alert Message** |
| Email | **Subject** / **Email Body** (runtime substitution) |
| Log | **Log Message** |
| Messaging App | **Message Template**; Teams **Card Title** |
| Signage Rich Message | Template title/message (in the Signage template, not this dialog) |
| Webhook / Digital Signage | No message-body interpolation in the form path |

---

## Analytics tab (verify firings)

1. Open **Automation** → **Analytics**.
2. Filters: status (All / Sent / Pending / Failed), type (Email / Webhook / …), date range, optional trigger chips.
3. Switch **charts** / **logs**.
4. Confirm recent deliveries after a live test.

![Full Automation Analytics screen. Left filters for Status / Type / Triggers / Time Range; charts view selected in the content bar.](./images/analytics-controls.png)

The download arrow exports logs as CSV. In the pill, chart = charts view, list = logs view. **Status**: All / Sent / Pending / Failed. **Type**: All / Email / Webhook / SMS / Push / Audit. Chart pies in the figure are placeholders.

Failed rows usually mean SMTP misconfiguration, bad webhook URL, or an inactive downstream system.

---

## Recommended first Vradar setup

1. Camera + [instant detection](./cameras-and-detection.md) working.
2. Create an **Alert (On-Screen)** action — fill every Alert field above.
3. Create an **Instant Demographic** trigger (e.g. People Count ≥ 2) on that camera; link the alert; Time Span `any`; Cooldown `60`; Active on.
4. Walk in front of the camera → on-screen alert → optional check on **Analytics**.
5. Add Instant People Match only after an Individual Group exists with members — see [Detections, individuals and persons](./detections-individuals-persons.md).

## Related

- [Cameras and detection](./cameras-and-detection.md)
- [Detections, individuals and persons](./detections-individuals-persons.md)
- [Digital signage](./digital-signage.md) (Digital Signage and Signage Rich Message actions)
- [Entrances and activity](./entrances-and-activity.md)
- Product map: [`eyenet-features.md`](../../product/features/eyenet-features.md) (Vradar)
