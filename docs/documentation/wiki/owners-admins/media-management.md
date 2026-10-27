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
title: Media and collections
audience: owner-admin
nav_order: 36
---

# Media And Collections

Upload files, organise them in collections, and use collection date/time search to aggregate **MVR people** (individuals) across videos into the same cross-video analysis screen described under detections preview.

**Where:**

| Task | Home tile / route |
|---|---|
| Upload files | **Upload Media** → `/upload` |
| Browse all media | **My Media** → `/gallery` |
| Organise by collection | **Collections** → `/collections` |
| Full-screen video review | Media item → **Full Screen Preview** → `/media-preview` |

---

## Prerequisites

- Bootstrap completed; you can log in as owner or admin
- For camera recordings: at least one camera that has recorded (camera collections are created automatically)
- For people search / aggregation: videos that have finished face-detection processing (or use **Compute** on preview)

---

## A. Manually add media (upload)

1. Home → **Upload Media** (`/upload`), or from **My Media** use the upload control / FAB.
2. On **Upload Media**:
   - Desktop: **Click to browse or drag files here** (or drop onto **Drop files here**).
   - Mobile: **Tap to select photos** → **Select Image Source** → **Camera** or **Gallery**.
3. Optional: enable **Create separate item even if file already exists** if you want a duplicate library item for the same file.
4. Confirm the list **Selected Files (N)**.
5. Tap **Upload Files**.
6. When upload finishes, open **My Media** or **Collections** to find the new items.

![Upload Media. Drop zone, one selected file, and Upload Files.](./images/upload-media.png)

The switch stays off unless you want a second library item for a file that is already stored. **Upload Files** appears after at least one file is selected. The file row is a name and type, not a preview of the picture or video.

**Supported formats** (from Upload Tips in the UI):

| Kind | Examples |
|---|---|
| Images | JPG, PNG, GIF |
| Videos | MP4, MOV |
| Audio | MP3, WAV |
| Documents | PDF, DOC |

**Limits:** about **100 MB** per file; batch upload is supported.

Uploads land in the media library. Assign them to a **user** collection afterwards (section C) if you want them grouped for signage or review.

### What good looks like (upload)

- Selected files appear in the list; **Upload Files** completes without error
- Items show in **My Media** (`/gallery`)

---

## B. Manage collections (CRUD, types, filters)

**Where:** Home → **Collections** (`/collections`)

![Collections app bar and type filters. The plus is marked.](./images/collections-toolbar.png)

The marked **+** is **Create collection**. The magnifying glass is **Search by date/time**. The checklist enters multi-select. Filters are **All** · **Camera** · **User**.

### Collection types

| Type | Badge | How it appears | Typical content |
|---|---|---|---|
| **Camera** | **Camera** (videocam) | Auto-created / linked when a camera records | Recordings from that camera |
| **User** | **User** (person) | Created manually with **Create Collection** | Uploads, signage source videos, curated sets |
| **All** | Filter only | Shows both types | — |

Use **user** collections for [digital signage](./digital-signage.md) playlists. Camera collections are for operational recordings and people search (section D).

![A camera collection and a user collection. Item counts are examples.](./images/collection-cards.png)

**Front Door** is a **Camera** collection (videocam badge). **Lobby Videos** is a **User** collection (person badge). **12 items**, **4 items**, the description, and the created dates are examples. ⋮ opens **Rename** and **Delete**.

### Create

1. Open **Collections**.
2. Tap **+** (tooltip **Create collection**) or empty-state **Create Collection**.
3. Enter **Collection Name** → **Create** (or **Cancel**).
4. Confirm snackbar *Collection "…" created successfully* and the new **User** card in the list.

![Create collection bar: name, Create, and Cancel.](./images/create-collection.png)

**Create** saves a **User** collection. **Cancel** closes the bar.

### List / open (read)

1. Left pane (wide layout) or full list: collection cards show name, **N items**, created date, and **Camera** / **User** badge.
2. Select a collection → right pane shows name, item count, **Created** / **Updated**, and the media grid for that collection.
3. Empty detail: *Select a collection from the list to view its media*.

### Rename (update)

1. On a collection card, open ⋮ → **Rename**.
2. Dialog **Rename Collection** → edit **Collection Name** → **Rename**.

### Delete

1. Card ⋮ → **Delete**.
2. Dialog **Delete Collection** (*cannot be undone*) → **Delete** (or **Cancel**).

![Collection card menu: Rename and Delete.](./images/collection-menu.png)

The day-to-day menu is **Rename** and **Delete**.

Other menu entries such as Edit / Share / Export may appear as placeholders; rely on **Rename** and **Delete** for day-to-day admin.

### Filters on the collections list

| Control | Purpose |
|---|---|
| **Search...** | Filter collections by name / description |
| **All** | Show camera + user collections |
| **Camera** | Only camera-linked collections |
| **User** | Only manually created collections |

### Gallery filters (My Media)

On **My Media** (`/gallery`), open search / **Advanced Filters** when you need library-wide filtering:

- Media type chips
- **Date Range**, **Tags**, **Collections**
- **Sort By** — Date Created · Name · Size · Type (asc/desc)
- **Show Archived**
- **Clear** / **Search**

![My Media advanced filters: type, sort, Show Archived, Clear, and Search.](./images/gallery-filters.png)

Use Collections for per-folder organisation; use Gallery when browsing everything at once.

### What good looks like (collections)

- New user collection appears with badge **User** and 0 items
- Type toggles correctly hide/show Camera vs User
- Rename updates the card title; delete removes the collection from the list

---

## C. Add media to collections

Several paths; pick the one that matches where you already are.

### From Collections or My Media (multi-select)

1. Enter selection / checklist mode on the media grid.
2. Select one or more items.
3. Tap **Add to collection** / **Add to Collection**.
4. Dialog **Add to Collection** (or *Add N items to Collection*): pick the destination collection → confirm.
5. Open that collection and verify the item count increased.

![Add to Collection. Pick a Camera or User collection.](./images/add-to-collection.png)

Tap a row to assign the selected items. Camera collections show a videocam badge; user collections show a person badge.

### Organize (move / copy / create)

1. Select items in **Collections**.
2. Open **Organize** (FAB / organize control).
3. Panel **Organize Media** → **Choose Action**:
   - **Move to Collection** — relocate into another collection
   - **Copy to Collection** — keep original and add a copy link/assignment
   - **Create New** — create a collection then place items (**Create New Collection** / **Create Collection**)
4. Confirm **Move Items** / **Copy Items** as prompted.

![Organize Media. Move to Collection is selected.](./images/organize-media.png)

**Move to Collection** changes the button to **Move Items**. **Copy to Collection** changes it to **Copy Items**. **Create New** changes it to **Create Collection**.

With selection active you can also **drag** items onto a collection in the list when the UI allows drop targets.

### From a single media item dialog

1. Tap an item → **Media** details dialog.
2. Tab **Collections** → **Add to Collection** → choose a collection.
3. Tab **Actions** for **Full Screen Preview**, **Compute**, **Download**, **Share**, **Delete**.

![Media item dialog on the Actions tab.](./images/media-actions.png)

**Collections** on this dialog is where you add the item to a collection. **Compute** and **Full Screen Preview** are on **Actions**. No thumbnail is shown here.

### Remove / delete

- Selection → **Remove from collection** when available (removes membership; behaviour may be limited on some builds).
- Selection → **Delete** / **Delete Items** permanently removes media — confirm carefully.

### What good looks like (assign)

- User collection item count rises after **Add to Collection**
- Signage playlists can see videos from that user collection
- Camera recordings remain findable under the camera’s collection

---

## D. Search individuals (MVR people) → media preview / Details

This is the **collection date/time search** that aggregates **MVR people** (individuals) across videos in a collection, then opens the same **cross-video / multi-individual** analysis UI described in [Detections — Preview / Details tabs (cross-video)](./detections-individuals-persons.md#4-preview--details-tabs-cross-video--multi-individual).

It is **not** free-text name search. It filters by time window, finds videos in that range, loads people linked to those videos, and offers **Details** → **Analysis**.

### When to use it

- Review who appeared in a camera collection over a shift / day / week
- Open aggregated **Individuals** / **Routes** / **Attendance** across several recordings
- Jump from a people count into the full analysis screen without opening each video first

Prefer a **Camera** collection with processed recordings. Empty ranges or unprocessed videos yield few or no individuals.

### Steps

1. Home → **Collections** → open a collection (usually a **Camera** collection).
2. App bar → **Search by date/time** (search icon).
3. Dialog **Filter Collections by Date/Time**:
   - Set **Start Date & Time** and **End Date & Time** (date picker, then time; start defaults toward start-of-day, end toward end-of-day when picking a day), **or**
   - Use **Quick Filters**: **Last 24 hours** · **Last 7 days** · **Last 30 days** · **Last 90 days**
   - **Clear** resets; **Cancel** closes; **Apply** runs the search.

![Full Collections screen with Filter Collections by Date/Time open. Last 7 days is selected.](./images/datetime-filter.png)

4. The media grid filters to videos in range. An active filter bar shows:
   - **From** / **To**
   - **Individuals: N → M unique** (appearances vs unique MVR people)
   - **Details**

![Active date filter bar: From, To, Individuals count, and Details.](./images/mvr-filter-bar.png)

The **×** clears the filter. **12 → 4 unique** is an example of appearances versus unique people. It is not a live camera count.

5. Tap **Details** → dialog **Cross-Video Tracking Details** (session / merge stats, time range, collection, video count when available).
6. Tap **Analysis** → opens the person-analysis screen in **cross-video** mode.

![Full Collections screen with Cross-Video Tracking Details open. Analysis opens the cross-video screen.](./images/cross-video-details.png)

### What you get on Analysis (cross-video tabs)

Same tabs as detections section 4:

| Tab | What it shows |
|---|---|
| **Statistics** | Aggregated metrics across the selected videos / individuals |
| **Routes** | Movement paths (Camera View + Top View; Path or Scatter) — see [Detections — Routes](./detections-individuals-persons.md#routes-tab) |
| **Individuals** | List of individuals with appearances; select for actions |
| **Attendance** | Who appeared when (summary + timeline) — see [Detections — Attendance](./detections-individuals-persons.md#attendance-tab) |

On **Individuals**: select people → **Actions** → **Add to Group** (and **Merge** when two or more are selected and merge is allowed). See [Detections — person groups](./detections-individuals-persons.md#c-person-groups-individual-groups).

Clear the date filter on the collection bar when you want the full unfiltered media grid again.

### Single-video path (related)

For one clip only:

1. Open the video from Collections / Gallery → **Actions** → **Full Screen Preview**.
2. Optional: app-bar **Compute** (run pipeline & create/update MVR people).
3. Overlay **Details** → single-video tabs (**Persons** · **Routes** · **Overview** · **Face Details**).

Use collection date/time search when you need **many videos / many people** in one Analysis view; use single-video Details when reviewing one recording.

### What good looks like (MVR search)

- After **Apply**, the filter bar shows a non-zero **Individuals** count when people exist in range
- **Details** → **Analysis** opens with **Statistics** / **Individuals** populated
- Clearing the filter restores the full collection grid

### Common issues

- **Individuals: 0** — no videos in range, or pipeline not finished (open a video → **Compute**, wait, retry search)
- **Details disabled / empty Analysis** — search not applied, or aggregation still loading; wait and tap **Details** again
- **Wrong people set** — wrong collection or time window; adjust **From** / **To** or use a quick filter
- **Need a named watchlist** — finish in Analysis → **Add to Group**, or manage groups under **Individual Groups**

---

## Recommended order

1. Upload or record media.  
2. Create **user** collections for curated / signage content; rely on **camera** collections for recordings.  
3. Add uploads into the right user collection.  
4. For “who was here when?”, open a camera collection → **Search by date/time** → **Details** → **Analysis**.

## Related

- [Detections, individuals and persons](./detections-individuals-persons.md)
- [Digital signage](./digital-signage.md) (playlists use user-collection videos)
- [Cameras and detection](./cameras-and-detection.md)
- [Presence and attendance](./presence-attendance.md)
- [Analytics and reports](./analytics-and-reports.md)
