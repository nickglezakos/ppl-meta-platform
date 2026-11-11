---
software_ref:
  platform_version: "2.25.82"
  policy_revision: "2026-11-01"
  channels_documented:
    - sandbox
    - pilot
    - stable
  install_path: "windows-docker-desktop-ghcr"
  host_ram_gb: 16
  wsl_memory_gb: 12
title: Primary use cases
audience: owner-admin
nav_order: 65
---

# Primary Use Cases

Featured outcomes from the [EyeNet Value — Most Valuable Cases](https://value.eyenet-vision.com/why/) — where EyeNet replaces manual presence, blind nights, and disconnected sites with automatic vision. This page is the **operator guide**: each case lists the value intro, the selling points as **functionalities**, then how to achieve them by composing EyeNet apps (Cameras, Presence, Signage, Vradar, Analytics, Network / Matrix).

Product overview of the same seven titles: [What is EyeNet — Primary use cases](../what-is-eyenet/#primary-use-cases).

**Where (compose these):**

| Role | Home tile / route | Expanded how-to |
|---|---|---|
| Aim camera, start live detection / recording | **Cameras** → `/cameras` · **Camera Ops** → `/camera-operations` | [Cameras and detection](./cameras-and-detection.md) |
| People, watchlists, groups | **My Media** · **Individual Groups** | [Detections, individuals and persons](./detections-individuals-persons.md) |
| Check-in / attendance / HubSpot | **Presence** → `/presence` | [Presence and attendance](./presence-attendance.md) · [EyeNet Authenticator](./presence-authenticator.md) |
| Playlists and players | **Signage Management** → `/signage` | [Digital signage](./digital-signage.md) |
| Alerts & automation (**Vradar**) | **Automation** → `/triggers` | [Vradar — alerts and automation](./alerts-and-automation.md) |
| Counts, paths, heatmaps, demographics | **Analytics** → `/analytics` | [Analytics and reports](./analytics-and-reports.md) |
| Door / corridor compose patterns | Cameras + Analytics + Automation (+ Presence) | [Entrances and activity](./entrances-and-activity.md) |
| Remote access, leaf VPN, multi-site (**Matrix**) | **Network** → `/network` | [Remote access and multi-site](./multi-site-and-remote.md) |

---

## Prerequisites

- Bootstrap completed; you can log in as owner or admin — [First install](./index.md) · [Bootstrap](./bootstrap.md)
- At least one camera connected with [instant detection](./cameras-and-detection.md) when you need live counters, Vradar, or video Presence
- For known-person / unknown-person rules: an **Individual Group** with members — [Detections, individuals and persons](./detections-individuals-persons.md)
- For notifications: Vradar **actions** (Alert / Email / Webhook / Messaging App / Digital Signage / Presence) before **triggers** — [Vradar](./alerts-and-automation.md)
- For fall / posture: body / posture capability on the camera, then Vradar **Body Posture** — [Body Posture](./alerts-and-automation.md#body-posture-multi-camera)
- For remote or multi-site packs: EyeNet VPN (+ Matrix when licensed) — [Remote access and multi-site](./multi-site-and-remote.md)

---

## 1. Know who is present and who is not

**Intro (from Value):** Presence is one flexible machine vision tool equally suitable for an intelligent doorbell at home, offices, warehouses, industrial floors, ships, and security posts. EyeNet shows who is in, where, and when — automatically — so teams stop chasing roll-calls and badge spreadsheets. Connectors such as HubSpot keep grants and contacts aligned as people move across sites.

### Functionalities

| Functionality | What it delivers |
|---|---|
| **Intelligent doorbell** | Who is at the door at home; presence without cloud video |
| **Entrance / exit stations** | Presence stations at doors for check-in / check-out |
| **Vprofile cameras** | Offices, warehouses, industrial floors, and watch posts |
| **Presence apps** | Staff mobile phones and desk PCs |
| **Shipping & security posts** | Same stack for crew, shifts, and perimeter stations |
| **Hands-off ops** | Purely automatic; no manual roll-call or chase |
| **HubSpot CRM** | Sync contacts; post grants to HubSpot in real time |

### How to achieve it

**Compose:** Individual Groups → Cameras + instant detection → Vradar People Match / Vprofile Match + Presence action → Presence Actions / Authenticator → optional HubSpot.

| Step | Where | What to do |
|---|---|---|
| 1 | [Detections — Person groups](./detections-individuals-persons.md#c-person-groups-individual-groups) | Create groups for the people you grant (e.g. `Staff – Main Door`, `Household`). Add members from video Details → **Add to Group**, or **Add Members**. |
| 2 | [Cameras](./cameras-and-detection.md) | Aim door / desk / post cameras; connect; start **instant detection**. |
| 3 | [Vradar — action](./alerts-and-automation.md#create-an-action) | Create a **Presence** action (and optional **Alert** / **Email** for exceptions). Keep **Active**. |
| 4 | [Vradar — Instant People Match](./alerts-and-automation.md#instant-people-match) or [VProfile Match](./alerts-and-automation.md#vprofile-match-multi-group-multi-camera) | Link camera(s) + group(s) + Presence action. Use VProfile when several cameras / groups cover a floor or post. |
| 5 | [Presence — Settings](./presence-attendance.md) | Confirm **Video readiness** is green for that trigger. |
| 6 | [Presence — Actions](./presence-attendance.md) / [Authenticator](./presence-authenticator.md) | **Reserve** a camera for owner-QR if needed. Run **Video Match**, **Render QR**, or phone Authenticator for check-in. |
| 7 | Optional — [HubSpot CRM](./presence-attendance.md) | Presence → **Settings** → **HubSpot CRM**: Service Key, sync contacts, post grants. |
| 8 | Presence → **Sessions** / **Overview** | Confirm grant/deny and digests; review exceptions with Email / Alert actions. |

**What good looks like:** Video readiness green; grants appear in **Sessions**; optional HubSpot note / `last_presence_*` updates on the contact; late / unknown flows fire the linked Alert or Email.

Entrance-focused walkthrough with screenshots: [Entrances and activity — Use case 2](./entrances-and-activity.md#use-case-2--staff--authorized-entrance-vradar-people-match-alert--presence-actions-for-attendance).

---

## 2. Screens that sell themselves

**Intro (from Value):** Static screens burn budget because nobody can prove who saw what or what converted. EyeNet reads the room — age, gender, group size — and drives playlists from live audience signals in milliseconds. Views, dwell, and engagement turn concourses and spots into a measurable marketing studio instead of guesswork.

### Functionalities

| Functionality | What it delivers |
|---|---|
| **Read the room** | Age, gender, group size drive playlist switches in milliseconds |
| **Zero surveys** | Know who sees each display: views, dwell, engagement |
| **A/B in the wild** | Swap content on live audience data; measure what converts |
| **Mall as studio** | Signage network as a measurable marketing studio across concourses, shops, and spots |
| **Prove ROI** | Impression / engagement reporting and footfall context from Analytics |

### How to achieve it

**Compose:** Media collections → Signage playlists + players → Cameras + instant detection at the screen → Vradar Instant Demographic + **Digital Signage** action → Analytics.

| Step | Where | What to do |
|---|---|---|
| 1 | [Digital signage — media & playlist](./digital-signage.md) | Upload / organise **user** media collections; create playlists (e.g. promo A / promo B); sync to online players. |
| 2 | [Digital signage — devices](./digital-signage.md) | Confirm players online; **Select & Play Playlist** for a baseline. |
| 3 | [Cameras](./cameras-and-detection.md) | Aim a camera at the audience in front of the screen; start **instant detection**. |
| 4 | [Vradar — Digital Signage action](./alerts-and-automation.md#digital-signage) | Create an action that targets the player / playlist switch you want when the audience matches. |
| 5 | [Vradar — Instant Demographic](./alerts-and-automation.md#instant-demographic) | Conditions on **People Count** / **Male %** / **Female %** / **Age**; link the Signage action; set cooldown; **Active**. |
| 6 | Test | Walk a test audience past the camera; confirm the player switches content. |
| 7 | [Analytics](./analytics-and-reports.md) | **Filters** → **Instant Detection** → modality **Face** (or **Both**) → screen / floor collection → review demographics, peaks, Level 4 behavioural blocks; **Export** Excel for campaign digests. |

**What good looks like:** Baseline playlist plays; demographic trigger fires; player switches; Analytics shows who was in front of the screen in the selected window.

Detail with screenshots: [Digital signage — Optional vision-adaptive signage](./digital-signage.md#6-optional--vision-adaptive-signage-vradar).

---

## 3. See how shoppers move

**Intro (from Value):** Shop managers need to know how customers move through the premises — not only that someone walked in. EyeNet turns existing cameras into people counts, paths, heatmaps, dwell, and occupancy, with behavioural alerts when zones get busy or quiet. Managers get digests and alerts; video never has to leave the store.

### Functionalities

| Functionality | What it delivers |
|---|---|
| **People counting** | Face / Body / Both across entrances and floor cameras |
| **Paths & heatmaps** | How customers move through aisles and zones |
| **Occupancy & peaks** | Busy hours by area, not guesswork |
| **Dwell & visit patterns** | Where shoppers linger vs pass through (Analytics Level 4 + Behavioural triggers) |
| **Behavioural alerts** | Occupancy / dwell / path / co-presence → Alert, Email, Webhook |
| **On-prem privacy** | Video stays local; managers get digests and alerts, not cloud footage |

### How to achieve it

**Compose:** Floor / entrance cameras + instant detection → Analytics (Instant Detection + modality) → Vradar Behavioural (and optional Instant Demographic) → optional Collections review.

| Step | Where | What to do |
|---|---|---|
| 1 | [Cameras](./cameras-and-detection.md) | Aim entrance and aisle cameras; enable Face and/or Body as needed; start **instant detection**. |
| 2 | [Analytics](./analytics-and-reports.md) | **Filters** → **Instant Detection** → **Detection Modality** **Face** / **Body** / **Both** → select floor collections → **Apply**. Read LEVEL 1–4 (counts, trends, demographics, heatmaps / behavioural blocks). |
| 3 | [Vradar — Behavioural](./alerts-and-automation.md#behavioural) | Create Alert / Email / Webhook actions first. Add a **Behavioural** trigger on a busy-zone camera (occupancy / peak / dwell / path / co-presence over lookback flushes). |
| 4 | Optional — [Instant Demographic](./alerts-and-automation.md#instant-demographic) | Simple People Count thresholds at the door (also covered in [Entrances](./entrances-and-activity.md#use-case-1--busy-lobby--corridor-crowd-alert--review)). |
| 5 | Optional — [Media and collections](./media-management.md) | Date/time search → **Details** → **Analysis** for a specific busy window. |
| 6 | [Analytics — Export](./analytics-and-reports.md) | **Export** Excel for shift / regional digests. |

**What good looks like:** Analytics levels populate for Instant Detection; a test Behavioural (or Demographic) trigger fires; Excel export shares the summary with store ops.

Camera intents and Behavioural mapping: [Analytics — behavioural layer](./analytics-and-reports.md#c3-behavioural-layer-instant-detection--vradar) · [Trigger metrics by analytics intent](./alerts-and-automation.md#trigger-metrics-by-analytics-intent).

---

## 4. Peace of mind at home — and away

**Intro (from Value):** Families need light protection for the home, cottage, and students living away — without a full security team or forced cloud video. EyeNet confirms presence and alerts when an unknown person enters living areas. You get a few targeted phone notifications; footage stays local.

### Functionalities

| Functionality | What it delivers |
|---|---|
| **Cottage / second-home protection** | Intrusion and unknown-person alerts when empty |
| **Remote students** | Family peace of mind without cloud video |
| **Presence check** | Confirm someone is (or should be) in the dwelling |
| **Secure zones** | Alarm if an unspecified person enters living areas |
| **On-prem privacy** | Footage stays local; phone / email alerts only when needed |

### How to achieve it

**Compose:** Household Individual Group → Cameras + instant detection (+ recording) → Vradar Instant People Match (NOT / unknown) + Alert/Email → optional Presence → optional EyeNet VPN for remote phone.

| Step | Where | What to do |
|---|---|---|
| 1 | [Detections — Person groups](./detections-individuals-persons.md#c-person-groups-individual-groups) | Create e.g. `Household` / `Residents`; add known faces. |
| 2 | [Cameras](./cameras-and-detection.md) | Aim living-area / entrance cameras; start **instant detection**; enable **Recording Pipeline** when you want local evidence. |
| 3 | [Vradar — action](./alerts-and-automation.md#create-an-action) | **Alert (On-Screen)** and/or **Email** / **Messaging App** (*Unknown in living room*). |
| 4 | [Vradar — Instant People Match](./alerts-and-automation.md#instant-people-match) | Select the camera and **Household** group; use **NOT mode** for “unknown person in zone”; link actions; cooldown; **Active**. |
| 5 | Optional — [Presence](./presence-attendance.md) | Video Match / QR when you also want “someone expected is home” grants. |
| 6 | Optional — [Remote access](./multi-site-and-remote.md) | Enroll platform on **EyeNet VPN** so family phones can reach Home / alerts off-LAN without shipping video to a public cloud. |
| 7 | Test | Unknown person in view → notification; known resident → no false unknown alert (or expected Presence grant). |

**What good looks like:** Unknown fires Alert/Email; known residents do not; recordings remain on the local install; remote login works only when VPN is enrolled.

---

## 5. Hospital-grade care at home

**Intro (from Value):** EyeNet turns the unstaffed home into a care environment that MDT teams and caregivers can trust. Falls, help-calls, presence, and zone breaches become a few targeted alerts in the clinical stack — video stays on-prem. Partners such as Talos / TMAIX fuse those events into Virtual Ward workflows without shipping footage to the cloud.

### Functionalities

| Functionality | What it delivers |
|---|---|
| **Caregiver presence** | Right staff, right home, right time (visit assurance) |
| **Secure zones** | Alarm on unspecified persons in/around the dwelling |
| **Fall detection** | Body-posture automation → care team |
| **Help-call / partner fuse** | Actionable alerts into mobile, email, or clinical webhooks (tokenized events — not cloud video) |
| **Virtual Ward readiness** | Same event path partners use for admission avoidance & early discharge |

### How to achieve it

**Compose:** Caregiver / household groups → Cameras (Area) + instant detection + body/posture → Presence for visit assurance → Vradar Body Posture (fall) + People Match (zones) → Alert / Email / **Webhook** into the partner stack.

| Step | Where | What to do |
|---|---|---|
| 1 | [Cameras](./cameras-and-detection.md) | Aim dwelling cameras; enable body / posture capability where falls must be detected; start **instant detection**. |
| 2 | [Detections — Person groups](./detections-individuals-persons.md#c-person-groups-individual-groups) | Groups for **Caregivers**, **Patient / household**, and optionally a watchlist for known visitors. |
| 3 | [Presence](./presence-attendance.md) | People Match / Vprofile Match + Presence action for caregiver visit grants; run **Video Match** or Authenticator on arrival. |
| 4 | [Vradar — Body Posture](./alerts-and-automation.md#body-posture-multi-camera) | **Target posture** `Horizontal`, window / min matches tuned for the room; link **Alert**, **Email**, and/or **Webhook** to MDT / on-call. |
| 5 | [Vradar — Instant People Match](./alerts-and-automation.md#instant-people-match) | NOT-mode (or watchlist) for unspecified persons in care zones; same notification actions. |
| 6 | [Vradar — Webhook](./alerts-and-automation.md#webhook) | Point critical actions at the partner / telemedicine endpoint so only **events** leave the home. |
| 7 | Test | Simulate caregiver visit (Presence grant); posture Horizontal → fall path fires; unknown in zone → secure-zone alert. |

**What good looks like:** Caregiver grants in **Sessions**; fall / zone events appear in Automation → **Analytics** logs and reach Email / Webhook; video remains on the dwelling install.

---

## 6. Night shifts that never blink

**Intro (from Value):** Night and perimeter coverage cannot depend on hope that every post stays awake. EyeNet watches stations and fences continuously and escalates when a post goes quiet or motion hits the ring. Continuous recording stays ready so incidents have timestamped evidence, not guesswork.

### Functionalities

| Functionality | What it delivers |
|---|---|
| **Night-shift automation** | Automated monitoring that posts stay occupied and alert |
| **Presence at posts** | Presence services on watch stations across the shift |
| **Perimeter nodes** | Presence / detection nodes at fences, gates, and outer rings |
| **Vradar** | Motion detection, POI / people-match alerts on patrol feeds |
| **Forensics** | Continuous recording with timestamped evidence for incidents |

### How to achieve it

**Compose:** Post / perimeter cameras + recording + instant detection → Presence at posts → Vradar Instant Demographic / Behavioural (quiet post) + Motion + People Match → Alert / Email / Messaging App → Analytics / Collections for review.

| Step | Where | What to do |
|---|---|---|
| 1 | [Cameras](./cameras-and-detection.md) | Aim post and perimeter cameras; start **instant detection**; turn on **Recording Pipeline** for forensics. |
| 2 | [Presence](./presence-attendance.md) | Stations at watch posts (QR / Video Match / Authenticator) so shift presence is granted, not assumed. |
| 3 | [Vradar — Instant Demographic or Behavioural](./alerts-and-automation.md) | Quiet-post rules: e.g. **People Count** ≤ 0 for a span, or Behavioural occupancy drop over lookback flushes; link supervisor Alert / Email. |
| 4 | [Vradar — Motion](./alerts-and-automation.md#motion-multi-camera) | Perimeter cameras: speed / motion class / ROI transit conditions for fence and outer-ring activity. |
| 5 | [Vradar — Instant People Match](./alerts-and-automation.md#instant-people-match) | POI / watchlist (or NOT-mode unknowns) on patrol feeds. |
| 6 | Escalate | Stack **Alert**, **Email**, **Messaging App** (Slack / Teams) for on-duty → supervisor → SOC. |
| 7 | Review | [Analytics](./analytics-and-reports.md) for the night window; [Collections](./media-management.md) date/time search for incident clips. |

**What good looks like:** Post Presence grants through the shift; quiet-post and perimeter Motion triggers fire in tests; recordings cover the incident window; Automation **Analytics** shows delivery status.

Related door / corridor patterns: [Entrances and activity](./entrances-and-activity.md).

---

## 7. Who’s onboard. Who’s on site. Who fell.

**Intro (from Value):** Ships and industrial sites cannot lean on cloud VMS when links are thin or offline. EyeNet keeps local truth about who is onboard or on site and where they should be, then packs reports for shore or HQ. The same stack covers special zones that need fall detection — decks, holds, warehouses, and industrial floors — so a fall becomes an immediate alert, not a missed radio call.

### Functionalities

| Functionality | What it delivers |
|---|---|
| **Everyone in place** | Presence (and entrance compose) so crew / site staff are where they should be |
| **Fall detection in special areas** | Decks, holds, warehouses, industrial floors → fall alerts to bridge, shore, or site ops |
| **Exact onboard / on-site count** | Live people counts from Instant Detection + Analytics |
| **Shore / HQ reports** | Attendance and headcount packs (Presence + Analytics export; Matrix when licensed) |
| **Minimal connectivity** | Full local ops; sync over thin / intermittent links |
| **Fleet Matrix** | VPN mesh; degraded mode — no data loss when offline |

### How to achieve it

**Compose:** Onboard / site cameras + Presence → Vradar Body Posture (fall) + Demographic counts → local Analytics / Presence digests → EyeNet VPN + **Matrix** for shore / HQ when licensed.

| Step | Where | What to do |
|---|---|---|
| 1 | [Cameras](./cameras-and-detection.md) | Aim muster, deck, hold, and floor cameras; enable body / posture where falls matter; start **instant detection** (recording as required). |
| 2 | [Presence](./presence-attendance.md) | Crew / site groups; Video Match / QR / Authenticator for onboard or gate check-in. |
| 3 | [Vradar — Instant Demographic](./alerts-and-automation.md#instant-demographic) | Headcount thresholds on muster / deck cameras when you need live count alerts. |
| 4 | [Vradar — Body Posture](./alerts-and-automation.md#body-posture-multi-camera) | **Horizontal** on special-area cameras; Alert / Email / Webhook to bridge, shore CSO, or site ops. |
| 5 | [Analytics](./analytics-and-reports.md) + Presence **Sessions** | Local truth packs: counts, peaks, attendance outcomes; **Export** Excel for shore / HQ when the link is up. |
| 6 | [Remote access and multi-site](./multi-site-and-remote.md) | Enroll **EyeNet VPN**; confirm local ops keep working offline. |
| 7 | Matrix (when licensed) | Ask your distributor for Matrix membership; use aggregated presence / entrance / camera reports across the fleet — [Matrix](./multi-site-and-remote.md#d-multi-site-reporting-matrix). |

**What good looks like:** Presence grants match who should be onboard / on site; fall path fires from a Horizontal posture test; Analytics / export (or Matrix) delivers the shore pack; detection continues when the uplink is down.

---

## Recommended order (any site)

1. Cameras + instant detection (and recording if you need forensics).  
2. Individual Groups for anyone you will grant or watch.  
3. Vradar **actions**, then **triggers** for the operational alerts.  
4. Presence Actions when the site needs attendance / visit assurance.  
5. Signage playlists when screens are in scope.  
6. Analytics filters + Excel (or Matrix) for digests.  
7. EyeNet VPN (and Matrix) only when remote or multi-site reporting is required.

---

## Common issues

- **No live counters / Vradar never fires** — instant detection not running; see [Cameras](./cameras-and-detection.md)
- **People Match never fires** — empty Individual Group or wrong camera; populate groups first ([Detections](./detections-individuals-persons.md))
- **Presence deny while Vradar alerted** — video readiness or session policy; inspect Presence → **Sessions** ([Presence](./presence-attendance.md))
- **Fall / posture never fires** — body / posture capability off, or Body Posture trigger mistuned; see [Body Posture](./alerts-and-automation.md#body-posture-multi-camera)
- **Signage never switches** — no Digital Signage action, player offline, or demographic conditions never met ([Signage](./digital-signage.md) · [Vradar](./alerts-and-automation.md))
- **Expected Matrix on Home** — Matrix is separate from a single-site home screen ([Multi-site](./multi-site-and-remote.md))

---

## Related

- [What is EyeNet — Primary use cases](../what-is-eyenet/#primary-use-cases)
- [Entrances and activity](./entrances-and-activity.md)
- [Cameras and detection](./cameras-and-detection.md)
- [Detections, individuals and persons](./detections-individuals-persons.md)
- [Vradar — alerts and automation](./alerts-and-automation.md)
- [Presence and attendance](./presence-attendance.md)
- [Digital signage](./digital-signage.md)
- [Analytics and reports](./analytics-and-reports.md)
- [Remote access and multi-site](./multi-site-and-remote.md)
- Value site: [Most Valuable Cases](https://value.eyenet-vision.com/why/)
