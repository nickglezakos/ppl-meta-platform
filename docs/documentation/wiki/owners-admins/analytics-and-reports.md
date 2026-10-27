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
title: Analytics and reports
audience: owner-admin
nav_order: 80
---

# Analytics And Reports

Review who was detected, when, and where — summary metrics, quality, time trends, demographics, and behavioural patterns — then export an Excel summary.

**Where:** Home → **Analytics** (`/analytics`) — app bar title **MVR Analytics**

Also reachable from Profile → **Analytics**, or from **Cameras** by opening the analytics view for a selected camera (pre-filtered).

This page is the **people / MVR** dashboard. Separate “Analytics” tabs exist under Presence and Automation (section E); system health is under **Monitoring**, not here.

A cyan ring in a figure is a marker for that control, not a highlight in the app. `--` stands in for a live count.

---

## Prerequisites

- Cameras producing either:
  - **Instant detection** sessions (live), or
  - **Recorded video** that has finished face-detection / MVR processing
- Collections visible in the filter list (camera collections after recordings)
- Demographics and behavioural charts need enough samples in the selected time range

See [Cameras and detection](./cameras-and-detection.md) and [Detections, individuals and persons](./detections-individuals-persons.md).

---

## A. Open the dashboard

1. Home → **Analytics** (subtitle *View statistics*).
2. Wait for *Loading analytics...* to finish (or tap **Retry** if you see *Failed to load analytics*).
3. Confirm the header **MVR People Detection Analytics** (*Real-time insights from camera collection MVR search results*).
4. Scroll the single dashboard (there are **no tabs** on this screen). Pull down to refresh, or use app-bar **Refresh**.

**Admin only:** a **People Counters** tile may appear at the top — opens the People Counters jobs screen (daily batch, pause/resume). Skip if you are not an admin.

![Full MVR Analytics screen. App bar, applied filter bar, and level cards; the cyan ring marks Filters.](./images/mvr-analytics-bar.png)

**Refresh** reloads the dashboard. **Filters** opens Filter Analytics.

![Full MVR Analytics screen with Failed to load analytics. The cyan ring marks Retry.](./images/analytics-load-failed.png)

While data is loading the screen shows *Loading analytics...*. If the load fails, **Retry** reloads the same way **Refresh** does.

![Full MVR Analytics screen with the admin People Counters tile. Counts are placeholders.](./images/people-counters-tile.png)

![Full People Counters screen while enabled. The cyan ring marks Pause. Job counts are placeholders.](./images/people-counters-run.png)

The tile is admin-only. Its status chip is **Enabled**, **Paused**, or **Disabled**, plus **Inflight**. The count line is Success, Running, Pending, Failed, and Dead-letter. Opening the tile shows **Enabled** with **Pause**, or **Paused** with **Resume**, the line `Worker: running` or `Worker: stopped`, **Job counts**, and **Run daily-batch (now)**.

### What good looks like (open)

- Header and **LEVEL 1** metrics load without error
- App bar shows **Refresh** and **Filters**
- Optional filter summary bar under the app bar after you apply filters

---

## B. Set filters

1. App bar → **Filters** (tooltip **Filters**).
2. Dialog **Filter Analytics** — set options below → **Apply** (or **Cancel**).
3. Confirm the summary bar under the app bar (for example `Time: Today`, `Collections: N selected`, demographics chips, or an **Instant Detection** chip).

![Full MVR Analytics screen with Filter Analytics open. Instant Detection and Today are selected; Front Door is an example collection.](./images/filter-analytics.png)

Pick one **Data Source**. **Video Recording** is the default; its helper is *Analytics from video recording sessions (default)*. **Instant Detection** uses *Analytics from real-time instant detection sessions*. This figure shows Instant Detection selected. **Front Door** is an example collection name. None selected reads *All collections (N)*. **Clear** resets the collection checks. Gender and Age Group chips are optional. **Auto-refresh (10 min)** (*Automatically update data*) stays off until you turn it on. **Apply** saves the filter.

![Full MVR Analytics screen with Filter Analytics open. Custom Range is marked; Start Date and End Date are still empty.](./images/analytics-custom-range.png)

**Custom Range** adds **Start Date** and **End Date**. The dialog shows *Please select both start and end dates* until both are set. **Apply** then shows *Please select both start and end dates for custom range*.

![Full MVR Analytics screen after Apply. Filter bar shows Time Today, one collection, and Instant Detection.](./images/analytics-filter-bar.png)

The bar shows `Time: …` and, when collections are checked, `Collections: N selected`. A demographics line appears when gender or age chips are set. The **Instant Detection** chip appears only for that source; its × switches the source back to Video Recording and reloads. When auto-refresh is on, the bar also shows an **Auto-refresh** badge.

### Data Source

| Option | Meaning |
|---|---|
| **Video Recording** | Default. Analytics from the recording / media pipeline (processed videos) |
| **Instant Detection** | Analytics from live instant-detection sessions |

Pick **one** source. There is no combined “both” toggle on this screen. The last choice can persist for later visits.

### Time Range

| Chip | Window |
|---|---|
| **Today** | Current calendar day (typical default) |
| **Last Hour** | Rolling last hour |
| **Last 3 Hours** | Rolling last three hours |
| **Last Week** | Last seven days |
| **Last Month** | Last ~30 days |
| **Custom Range** | **Start Date** and **End Date** pickers (both required; warning if one is missing) |

### Collections

- Multi-select checkboxes for camera / media collections.
- None selected = all collections (*All collections (N)*).
- Use **Clear** to reset the collection selection.

### Demographics (optional narrow)

| Group | Chips |
|---|---|
| **Gender** | **Male** · **Female** |
| **Age Group** | **Young (0-25)** · **Adult (26-65)** · **Elderly (65+)** |

Leave unset to include all demographics present in the data.

### Auto-refresh

Toggle **Auto-refresh (10 min)** (*Automatically update data*). The badge may show on the filter bar; treat this as optional UI — prefer **Refresh** or re-**Apply** filters when you need an immediate update.

### Recommended first pass

1. **Data Source** = **Video Recording** (or **Instant Detection** if you only ran live detection).  
2. **Time Range** = **Today** or **Last Week**.  
3. Optionally select the entrance / site collections you care about.  
4. **Apply** → read Levels 1–4.

---

## C. Read the dashboard (Levels 1–4)

Sections appear top-to-bottom when data is available. Empty or failed sections may be hidden or show an empty-state message.

### LEVEL 1 — Basic Metrics

| Metric | Notes |
|---|---|
| **Total People** | Unique individuals in range |
| **Active Collections** | Collections with detections |
| **Videos Analyzed** | When source is Video Recording (*In time range*) |
| **Sessions** | When source is Instant Detection (*Detection sessions*) |
| **Image Quality** (with grade) or **Last Detection** | Quality summary or most recent detection time |

![Full MVR Analytics screen showing LEVEL 1 Basic Metrics for Video Recording. Counts are placeholders.](./images/basic-metrics.png)

**Export** on this header is the control in section D. With Video Recording and no quality data, the third card is **Videos Analyzed** (*In time range*) and the fourth is **Last Detection** (*Most recent*). Instant Detection renames the third card to **Sessions** (*Detection sessions*). When quality data exists, **Image Quality** replaces **Last Detection** and its subtitle is the grade. A figure with example counts for these cards, plus Activity Over Time and a heatmap excerpt, is at the end of Level 4. Those numbers are examples, not a live report.

### LEVEL 1.5 — MVR Quality Metrics

Shown when quality data loads.

- **Tracking Sessions Overview** — **Sessions**, **Computed**, **Detected**, **Videos** / **Sessions**
- **Quality Scores** — grade badge (Excellent / Good / Fair / Poor / Very Poor), **Average Quality**, **Range**, **Std Dev**, **Data Completeness**, counts *with* / *without* quality

Empty: *No quality data available for this time period*.

![Full MVR Analytics screen showing LEVEL 1.5 MVR Quality Metrics. Quality Scores is empty; counts are placeholders.](./images/quality-metrics.png)

**Tracking Sessions Overview** is Sessions, Computed, Detected, and Videos. That last tile is labeled **Sessions** again when the source is Instant Detection. With scores, **Quality Scores** adds a grade badge (Excellent, Good, Fair, Poor, or Very Poor) and **Average Quality**, **Range**, **Std Dev**, and **Data Completeness**, plus counts *with quality* and *without quality*.

### LEVEL 2 — Time-Based Trends

- Summary stats: **Total**, **Peak**, **Average**
- Chart **Activity Over Time** with **Hourly** / **Daily** chip
- Tooltips show time and people count

Empty: *No time-series data available for this period*.

![Full MVR Analytics screen on LEVEL 2. Activity Over Time has no series; the cyan ring marks Hourly.](./images/activity-over-time.png)

The chip reads **Hourly** or **Daily**. The chart is omitted here.

### Level 3 — Demographics Distribution

Hidden when **Total People** is 0.

- **Total People Analyzed**
- **Gender Distribution** — Male / Female / Unknown
- **Age Distribution** — Young / Adult / Middle Aged / Elderly / Unknown  

(Filter chips use Young / Adult / Elderly; charts may also show Middle Aged / Unknown from the API.)

![Full MVR Analytics screen on Level 3 Demographics Distribution. Pie charts are omitted; the total is a placeholder.](./images/demographics-labels.png)

**Gender Distribution** can list Male, Female, and Unknown. **Age Distribution** can list Young, Adult, Middle Aged, Elderly, and Unknown. A slice and its legend row appear only when that count is above zero.

### Level 4 — Behavioral Insights

Empty: *No behavioral data available* / *Try selecting a different time period or camera*.

When populated:

| Block | What it shows |
|---|---|
| **Weekly Activity Heatmap** | Mon–Sun × hours 00–23 |
| **Peak Activity Times** | **Top Hours**, **Top Days** |
| **Detection Occurence** (Video Recording) | Pass patterns such as **Single Pass**, **Double Pass**, **Frequent** |
| **Visit Frequency** (Instant Detection) | Rows may show **New** / **Returning** / **Frequent** (values can be **N/A** on some builds) |
| **Top Active Cameras** | Bars with *N people* |

![Full MVR Analytics screen on Level 4 Behavioral Insights. The heatmap has no counts; Detection Occurence and Visit Frequency do not appear together.](./images/behavioral-blocks.png)

**Weekly Activity Heatmap** is Monday–Sunday by hours 00–23. Blank cells are hours with no count. **Peak Activity Times** lists **Top Hours** and **Top Days** when those lists are returned. **Detection Occurence** is the Video Recording card (Single Pass, Double Pass, Frequent). **Visit Frequency** replaces it for Instant Detection (New, Returning, Frequent), and those rows read **N/A**. **Top Active Cameras** uses the camera name and *N people*. Zeros in this figure are the empty pattern.

![Full MVR Analytics screen with example LEVEL 1 counts, Activity Over Time bars, and a heatmap. Not a live report.](./images/analytics-example.png)

Every number here is an example. **Total People** 12, **Active Collections** 1, **Videos Analyzed** 4, and **Last Detection** *2h ago* are what LEVEL 1 looks like once data exists (Video Recording, no quality grade, so the fourth card stays **Last Detection**). **Activity Over Time** draws a bar per bucket; **Hourly** is selected, and the three bars are 09:00, 12:00, and 15:00. The heatmap excerpt is Monday–Wednesday, hours 08–13 only. A cell with a blue outline has a count; a blank grey cell is zero. The full grid is still Mon–Sun by 00–23. No video frame and no face are shown.

### Drill-down

Charts on this screen do **not** open a person or media preview. To review individuals in media, use [Collections date/time search → Analysis](./media-management.md#d-search-individuals-mvr-people--media-preview--details) or open a video → **Details**.

### What good looks like (read)

- LEVEL 1 numbers move after new detections or processed recordings
- Switching **Video Recording** ↔ **Instant Detection** changes counts and labels (Videos vs Sessions)
- Demographics and behavioural sections populate when the range has enough samples

---

## D. Export a report (Excel)

1. On the Analytics header, tap **Export**.
2. Dialog **Export Analytics** → choose **Excel Spreadsheet** (*Open with Excel, LibreOffice, etc.*) → confirm (or **Cancel**).
3. Wait for *Generating Excel file...*
4. Success: *Excel file downloaded successfully* (web) or *Excel file ready to share* (native).

![Full MVR Analytics screen with Export Analytics open. Excel Spreadsheet is the export option.](./images/export-analytics.png)

![Full MVR Analytics screen with Generating Excel file progress open.](./images/export-progress.png)

**Excel Spreadsheet** (*Open with Excel, LibreOffice, etc.*) starts the file. The progress card says *Generating Excel file...*. If no summary is loaded, Export shows *No analytics data to export* and does not open the dialog.

Workbook sheet **Analytics Summary** includes title *MVR Analytics Summary Report*, summary metrics, demographics, and collection breakdown. Filename pattern: `analytics_<filter>_<timestamp>.xlsx`.

Failures: *No analytics data to export* or *Failed to generate Excel: …* — widen the time range, confirm Data Source, or **Refresh** and retry.

---

## E. Related “Analytics” elsewhere (not this page)

| Where | What it is |
|---|---|
| **Presence** → tab **Analytics** | User-day awards, outcomes / client-origin donuts, failure & policy bars, mode success, session modes — see [Presence and attendance](./presence-attendance.md) |
| **Automation** (`/triggers`) → tab **Analytics** | Comm-log status (email / webhook / SMS / push): filters, charts, CSV download — see [Vradar](./alerts-and-automation.md) |
| **Camera Ops** (`/camera-operations`) | Ops health aggregates (last hour), not people MVR analytics |
| **Monitoring** (`/workflows`) | System / workflow health charts |

![Full Presence Analytics screen. This is the Presence tab, not the MVR dashboard.](./images/analytics-awards.png)

![Full Automation Analytics screen with filters and the charts / logs switch. This is the Automation tab, not the MVR dashboard.](./images/analytics-controls.png)

Presence → **Analytics** is attendance sessions (awards, outcomes, client origin, failures, mode success). Automation → **Analytics** is delivery status for email, webhook, and the other comm types. Neither screen is this MVR dashboard.

For entrance / corridor ops, compose Cameras + this Analytics page + Automation — see [Entrances and activity](./entrances-and-activity.md).

---

## Common issues

- **Empty LEVEL 1 / Failed to load** — Discovery / services unhealthy, or no data for the filter; **Retry**, then check cameras and processing
- **Demographics / Level 4 missing** — zero people in range, or not enough samples; widen time or switch Data Source
- **Counts look “wrong”** — confirm **Video Recording** vs **Instant Detection**, collection selection, and time chips
- **Export fails** — no data under current filters; clear demographics / widen range
- **Expected person click-through** — not on this dashboard; use Collections search or media **Details** instead

---

## Recommended order

1. Run instant detection and/or record + process videos.  
2. Open **Analytics** → **Filters** → Data Source + Today/Last Week → **Apply**.  
3. Read LEVEL 1–4; adjust collections or demographics if needed.  
4. **Export** → Excel when you need a shareable summary.

## Related

- [Cameras and detection](./cameras-and-detection.md)
- [Detections, individuals and persons](./detections-individuals-persons.md)
- [Media and collections](./media-management.md)
- [Entrances and activity](./entrances-and-activity.md)
- [Presence and attendance](./presence-attendance.md)
- [Vradar — alerts and automation](./alerts-and-automation.md)
