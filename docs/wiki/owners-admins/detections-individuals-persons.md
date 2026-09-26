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

### 1. Record from a camera

1. Home → **Cameras**.
2. Connect the camera stream if it is not already connected.
3. Tap the red **Start recording** control on the camera card (fiber / record icon).
4. Confirm the card shows recording (red indicator / size or timer where shown).
5. Tap **Stop recording** when finished.
6. The platform stores the video in the camera’s media collection and starts the face-detection pipeline in the background (you do not need to start instant detection for this path).

Optional: keep instant detection running while recording — the two lifecycles are separate.

### 2. Open the recording in Media Preview

1. Home → **My Media** (`/gallery`), or open the camera’s collection from **Collections**.
2. Open the new video.
3. Wait until processing finishes. When people records are ready, use **Details** on the preview.
4. If **Details** is missing or people look incomplete, use **Compute** on the preview app bar to re-run the pipeline and create/update MVR people, then open **Details** again.

**Details** opens the person-analysis screen for that video (and can open a **cross-video** view when the session spans multiple videos or a group search).

### 3. Preview / Details tabs (single video)

When you open Details for **one** video, the screen uses these tabs:

| Tab | What it shows |
|---|---|
| **Persons** | People found in this video (person groups / cards): representative faces, age/gender when available, quality and movement stats |
| **Routes** | Path / movement of selected people through the scene over time (per camera scope of the clip) |
| **Overview** | High-level analysis statistics for the session (counts of faces / people, summary metrics) |
| **Face Details** | Frame-level classified faces list for deeper inspection |

Use **Persons** as the main review surface; open **Face Details** when you need to inspect individual detections.

### 4. Preview / Details tabs (cross-video / multi-individual)

When analysis covers **multiple videos** or a multi-individual session (for example after linking appearances or certain group searches), the tabs are:

| Tab | What it shows |
|---|---|
| **Statistics** | Aggregated metrics across the selected videos / individuals |
| **Routes** | Cross-video routes (movement across cameras and time) |
| **Individuals** | List of individuals with appearances; select people for actions |
| **Attendance** | Presence-style attendance view for the analysis window |

On **Individuals**, you can select people and open **Actions** → **Add to Group** (see section C). Selecting two or more may also offer **Merge** when merge rules allow it.

### What good looks like (recording → review)

- Recording stops cleanly; video appears in My Media / the camera collection
- After processing (or Compute), **Details** is available
- **Persons** (or **Individuals** in cross-video) shows people with faces
- Demographics appear when the pipeline had usable face crops

---

## C. Person groups (Individual Groups)

Person groups are named sets of **individuals** (watchlists, whitelists, staff lists). Vradar **Instant People Match** / **Vprofile match** triggers (and Presence video readiness) select these lists. Creating members here is separate from creating the group container.

**Where:** Home → **Individual Groups** (`/individual-groups`)

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

### Manage groups

From the groups list:

- **Search** and filter by visibility
- Open a group to see members
- On a group row or detail menu:
  - **Edit Group** — name, description, visibility, tags
  - **Set Cover Image** — optional cover
  - **Delete Group** — removes the group (confirm in the dialog)

### Add an individual to a group

Two common paths:

#### From Individual Groups (group side)

1. Open the target group.
2. Menu → **Add Members** (or the **Add Members** control).
3. In **Add Members**:
   - Select available individuals when listed, and/or
   - **Add by ID** — paste an individual ID if you have it from Details / Individuals
4. Confirm **Add** / **Add N Members**.
5. If the UI reports a possible duplicate, choose **merge**, **add anyway**, or cancel as prompted.

You can also select members in the group and **Remove** them when in selection mode.

#### From video Details / Individuals (person side)

1. Open a processed video → **Details**.
2. Prefer the **Individuals** tab (cross-video) or select the person you want from the analysis view.
3. Select **one** individual (bulk add of many at once may be limited).
4. Open **Actions** → **Add to Group**.
5. Choose the destination group → confirm.
6. Return to **Individual Groups** and open the group to verify the member count and thumbnail.

### What good looks like (groups)

- Group exists with the correct visibility
- Member count increases after Add to Group / Add Members
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
