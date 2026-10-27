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
title: Detections, individuals and persons
audience: owner-admin
nav_order: 35
---

# Detections, Individuals And Persons

How EyeNet turns camera frames into people you can review, group, and use in Vradar.

**Where (after install):**

| Task | Home tile / route |
|---|---|
| Live cameras, record, instant detection | **Cameras** → `/cameras` |
| Open recorded videos | **My Media** → `/gallery` (also camera collections) |
| Review people from a video | Media Preview → **Details** |
| Person groups (watchlists / whitelists) | **Individual Groups** → `/individual-groups` |

---

## A. Instant detection vs face detection on a recording

Both paths use the same face-detection quality. They differ in **when** they run and **how** results are stored for review.

### Instant detection (live)

- Started from a camera card with the **instant detection** controls (eye / detection controls), **independent of recording**.
- Samples a few frames from the live stream on a short cycle (on the order of every few seconds).
- Detects faces, groups them into people in the current view, estimates age/gender, and can resolve against known identities.
- Results feed the live counters on the camera card, **Analytics** (filter **Instant Detection**), and **Vradar** triggers that listen to live events.
- Some results are also persisted as tracking sessions / people records so they can appear in analytics later.

See [Cameras and detection](./cameras-and-detection.md) for how to start it.

### Face detection on a recording (bulk / media pipeline)

- Runs after a **recording stops** (or when media is uploaded / you press **Compute** on preview).
- Processes the full video (or segments) through the vision pipeline:
  1. Detect faces across sampled frames
  2. Group faces into **person objects** (one person within that video)
  3. Materialize **individuals** / **MVR people** (stable biometric records with embeddings and demographics)
  4. Make those people available in Media Preview → **Details**, Analytics (**Video Recording**), and Individual Groups
- Richer for review: routes, face lists, and cross-video linking when the same person appears in more than one video.

**Rule of thumb:** use **instant detection** for live ops and Vradar; use **recording + preview** when you need a durable review of who appeared in a clip.

---

## B. Record a video and review individuals in preview

![Connected camera card. The red circle is Start recording.](./images/camera-card-record.png)

**Front Door** is an example name. The green camera icon and green dot mean the stream is connected. From the left, the footer is **Active**, **Delete camera**, **Archive camera**, **Disconnect** (broken link), **Start detection** (eye; blue when active, grey when off), the marked red circle **Start recording**, and **View stream** (play — opens the live stream view). **Total: 0 people** is the counter before this clip is processed. The live detection strip is not shown.

### 1. Record from a camera

1. Home → **Cameras**.
2. Connect the camera stream if it is not already connected.
3. Tap the red **Start recording** control on the camera card (fiber / record icon).
4. Confirm the card shows recording (red indicator / size or timer where shown).
5. Tap **Stop recording** when finished.
6. The platform stores the video in the camera’s media collection and starts the face-detection pipeline in the background (you do not need to start instant detection for this path).

Optional: keep instant detection running while recording — the two lifecycles are separate.

### 2. Open the recording in Media Preview

1. Home → **My Media** (`/gallery`), or open the camera’s collection from camera collections.
2. Open the new video.
3. Wait a bit after the video is stored. **Details** appears only once people records exist. Do not rush to tap **Compute** just because **Details** is not there yet.
4. If you have waited and **Details** is still missing, or people look incomplete, use **Compute** on the preview app bar to re-run the pipeline and create or update MVR people, then open **Details** again.

![Media Preview full screen. The amber ring marks Compute (bolt). The cyan ring marks Details on the video. Preview area shows the EyeNet logo at low opacity.](./images/media-preview-controls.png)

- The marked bolt is **Compute** (re-run the pipeline for this video).
- The person icon beside it opens **MVR People Body**.
- The photo icon goes to **Collections**.
- **Details** is the blue chip on the video. It appears once people records exist and opens person analysis.
- The preview area is a placeholder — recorded frames are not shown in this wiki.

**Details** opens the person-analysis screen for that video (and can open a **cross-video** view when the session spans multiple videos or a group search).

### 3. Preview / Details tabs (single video)

When you open Details for **one** video, the screen uses these tabs:

| Tab | What it shows |
|---|---|
| **Persons** | People found in this video (person groups / cards): representative faces, age/gender when available, quality and movement stats |
| **Routes** | Where each person moved in the frame over time (camera view + top view; Path or Scatter) |
| **Overview** | High-level analysis statistics for the session (counts of faces / people, summary metrics) |
| **Face Details** | Frame-level classified faces list for deeper inspection |

Use **Persons** as the main review surface; open **Face Details** when you need to inspect individual detections. Use **Routes** when you need movement through the scene (see below).

### 4. Preview / Details tabs (cross-video / multi-individual)

When analysis covers **multiple videos** or a multi-individual session (for example after linking appearances or certain group searches), the tabs are:

| Tab | What it shows |
|---|---|
| **Statistics** | Aggregated metrics across the selected videos / individuals |
| **Routes** | Movement paths per camera across the analysis window (same visualization as single-video Routes) |
| **Individuals** | List of individuals with appearances; select people for actions |
| **Attendance** | Who appeared when: summary table + timeline graph per camera |

On **Individuals**, you can select people and open **Actions** → **Add to Group** (see section C). Selecting two or more may also offer **Merge** when merge rules allow it.

![Full Details screens. Top: single-video Persons. Bottom: cross-video Individuals with one person selected and Actions marked.](./images/details-tabs.png)

**Persons** is the main tab for one video. On a cross-video session, **Individuals** is where you select people. **Actions (1)** appears after a selection.

![Full cross-video Individuals screen with the Actions dialog open. Add to Group is available; Merge needs two or more selected.](./images/actions-add-to-group.png)

**Add to Group** sends the selected individual to a person group. With one person selected, Merge is not offered.

### Routes tab

**Routes** shows how people moved through the camera scene during the analysis.

- Available on **single-video** Details and on **cross-video** Details.
- **Camera View** plots route points on the video frame.
- **Top View** shows the same movement from a top-down projection.
- Switch display mode between **Path** (connected trail with start/end markers) and **Scatter** (points only).
- A legend maps colors to people / individuals and explains Start · End · Path markers.
- In cross-video mode, pick a camera when the session spans more than one; load more route pages if offered.

Use Routes to see walk paths, dwell clusters, or whether someone crossed a doorway — not for identity actions (those stay on **Individuals**).

![Full Routes tab. Camera View and Top View with Scatter mode. Legend lists individuals and start/end/path markers.](./images/details-routes.png)

### Attendance tab

**Attendance** (cross-video only) answers *who was present when* for the analysis window.

- **Individuals Summary** — table of first seen, last seen, appearance count, and total duration per person (grouped by camera when several cameras are in scope).
- **Attendance Timeline** — graph of each person’s appearances over time.
- Download control exports the summary for that camera to Excel when available.

This is analysis attendance for the selected videos / date range — related to, but not the same as, the Presence product sessions under [Presence and attendance](./presence-attendance.md).

![Full Attendance tab. Individuals Summary table and Attendance Timeline for the Front Door collection.](./images/details-attendance.png)

### What good looks like (recording → review)

- Recording stops cleanly; video appears in My Media / the camera collection
- After processing (or Compute), **Details** is available
- **Persons** (or **Individuals** in cross-video) shows people with faces
- Demographics appear when the pipeline had usable face crops

---

## C. Person groups (Individual Groups)

Person groups are named sets of **individuals** (watchlists, whitelists, staff lists). Vradar **Instant People Match** / **Vprofile match** triggers (and Presence video readiness) select these lists. Creating members here is separate from creating the group container.

**Where:** Home → **Individual Groups** (`/individual-groups`)

On a wide desktop layout the screen is **master / detail**: groups on the left, the selected group’s **Members** content pane on the right. Member face tiles use the EyeNet logo at low opacity in this wiki (placeholders — live installs show face crops when available).

![Full Individual Groups master/detail. The cyan ring marks New Group (+). Right pane shows member cards.](./images/individual-groups-toolbar.png)

The marked **+** is **New Group**. Filters are All · Private · Shared · Public.

![Full Individual Groups list with Staff – Main Door selected. The cyan ring marks the member-count circle. Right pane shows that group’s members.](./images/group-card.png)

**Staff – Main Door**, the description, the tag **staff**, and **3 members** are examples. The circle is the member count. The badge is the visibility value: **private** (lock), **shared**, or **public**. The ⋮ menu is **Group actions**.

### Member card controls

Each member tile in the content pane has:

| Control | Where | What it does |
|---|---|---|
| **Link** (chain icon) | Top-left on the tile | Opens **Member Details** → **People Profile** link / create |
| **Delete** (trash) | Top-right on the tile | Removes this member from the group (confirm first) |
| **Tap the card** | Tile body | Opens **Person Objects** analysis for that member (MVR individual) |

![Members content pane. Link (cyan) and Delete (red outline) are marked on Group Member 01. Face area shows the EyeNet logo placeholder.](./images/group-member-controls.png)

### Link a People Profile (connect flow)

Use this when a group member should map to a Presence **People Profile** (named person record).

1. On the member tile, tap **Link** (top-left).
2. **Member Details** opens. If none is linked yet, status shows **No profile**.
3. Tap **Link / Create**.
4. In **People Profile**: search and select an existing profile, **or** type a new profile name.
5. Tap **Link**. Status becomes **Profile: …** (and later shows **Change** instead of **Link / Create**).

![Member Details over the groups screen. Link / Create is marked under People Profile.](./images/member-details-people-profile.png)

![People Profile dialog. An existing profile is selected; Link confirms the connection.](./images/people-profile-link.png)

### Remove a member (delete from group)

1. On the member tile, tap **Delete** (trash, top-right).
2. Confirm **Remove Member**.
3. The tile leaves the Members pane; the group member count decreases.

![Remove Member confirmation over the groups screen. Trash on the tile is marked.](./images/remove-member-dialog.png)

This removes the person from **this group only** — it does not delete the underlying individual / MVR record.

### Create a group

1. Open **Individual Groups**.
2. Tap **Create Group** (empty state button or the create control).
3. Fill **Create Group**:
   - **Group Name** — required, at least 3 characters
   - **Description** — optional
   - **Visibility** — Private · Shared · Public
   - Optional **tags** if offered
4. Confirm **Create Group**.
5. The new group appears in the list (member count starts at 0).

![Full Individual Groups screen with Create Group open over the master/detail layout.](./images/create-group-dialog.png)

**Group Name** must be at least 3 characters. **Private** is the default visibility. **Create Group** saves; **Cancel** or the close icon discards the dialog.

### Manage groups

From the groups list:

- **Search** and filter by visibility
- Select a group to see members in the right pane
- On a group row menu (⋮):
  - **Camera Search**
  - **Edit Group** — name, description, visibility, tags
  - **Delete Group** — removes the group (confirm in the dialog)

![Full Individual Groups screen with the group ⋮ menu open: Camera Search, Edit Group, Delete Group.](./images/group-actions-menu.png)

![Delete Group confirmation. This cannot be undone.](./images/delete-group-dialog.png)

### Add an individual to a group

Two common paths:

#### From Individual Groups (group side)

1. Open the target group.
2. Menu → **Add Members** (or the **Add Members** control on the detail screen).
3. In **Add Members**:
   - Select available individuals when listed, and/or
   - **Add by ID** — paste an individual ID if you have it from Details / Individuals
4. Confirm **Add** / **Add N Members**.
5. If the UI reports a possible duplicate, choose **merge**, **add anyway**, or cancel as prompted.

![Full Individual Groups screen with Add Members open. The cyan ring marks Add by ID (+) in the search field.](./images/add-members-dialog.png)

The **+** in the search field is **Add by ID**. With one ID selected, the button reads **Add 1 Members**. The list row shows an ID placeholder, not a face photo.

#### From video Details / Individuals (person side)

1. Open a processed video → **Details**.
2. Prefer the **Individuals** tab (cross-video) or select the person you want from the analysis view.
3. Select **one** individual (bulk add of many at once may be limited).
4. Open **Actions** → **Add to Group**.
5. Choose the destination group → confirm.
6. Return to **Individual Groups** and open the group to verify the member count and thumbnail.

### What good looks like (groups)

- Group exists with the correct visibility
- Members pane shows tiles; Link / Delete / tap-to-Person-Objects behave as above
- Member count increases after Add to Group / Add Members
- Linked members show a People Profile name under Member Details
- The group appears in Vradar **Individual Group** dropdowns for Instant / Search People Match

### Tip for Vradar

Create and populate the group **before** building an Instant People Match trigger. See [Vradar — alerts and automation](./alerts-and-automation.md).

---

## Related

- [Media and collections](./media-management.md) (upload, collections, date/time MVR search → Analysis)
- [Cameras and detection](./cameras-and-detection.md)
- [Vradar — alerts and automation](./alerts-and-automation.md)
- [Analytics and reports](./analytics-and-reports.md)
- [Presence and attendance](./presence-attendance.md)
