---
software_ref:
  platform_version: "2.25.101"
  policy_revision: "2026-10-16"
  channels_documented:
    - sandbox
    - pilot
    - stable
  install_path: "windows-docker-desktop-ghcr"
  host_ram_gb: 16
  wsl_memory_gb: 12
title: Cameras and detection
audience: owner-admin
nav_order: 30
---

# Cameras And Detection

Connect cameras and run live person detection. This is the foundation for Presence, Analytics, Vradar (Automation), and Signage.

**Where:** Home → **Cameras** (`/cameras`)

## Prerequisites

- Bootstrap completed; you can log in as owner or admin
- Host meets [hardware requirements](./hardware.md)
- For RTSP: the IP camera is on the same LAN as the EyeNet PC (or otherwise reachable)
- For **edge**: a Raspberry Pi (or similar) running the EyeNet edge-camera app on the same LAN (see [Add an edge camera](#add-an-edge-camera))
- For mobile: Android phone that can install APKs (see [Add a mobile camera](#add-a-mobile-camera))

On the Cameras screen toolbar:

| Control | Purpose |
|---|---|
| Refresh | Reload the camera list |
| **+** (Add) | **Add RTSP Camera** |
| Outdoor camera icon | **Add Edge Camera** (Raspberry Pi / USB-CSI edge device) |

![Cameras app bar. The plus is marked in this figure.](./images/cameras-toolbar.png)

The marked **+** opens **Add RTSP Camera**. **Refresh** is the circular arrow immediately to its left. The cyan outdoor-camera icon on the right is **Add Edge Camera**. Back and Home sit at the left and just before the camera actions.

Filter chips: All · RTSP · Edge · Mobile.

![Camera type filters with RTSP selected](./images/camera-type-filters.png)

Use **RTSP**, **Edge**, or **Mobile** when the list is long and you only want that type.

## Desktop layout — list, analytics, settings

On a wide screen, **Cameras** is a master/detail view:

- **Left:** camera list (search, type filters, cards). Tap a card to select it.
- **Right:** content pane for the selected camera. The mode pill switches between **Analytics** (chart icon) and **Settings** (gear).

![Cameras desktop layout. Left list with Front Door selected. Right pane shows analytics. Mode pill marks Analytics.](./images/cameras-desktop-analytics.png)

![Cameras desktop layout. Left list with Front Door selected. Right pane shows pipeline settings. Mode pill marks Settings.](./images/cameras-desktop-settings.png)

Names such as **Front Door** are examples. The stream preview area in analytics uses a low-opacity EyeNet logo placeholder (no live frame in this wiki).

---

## Add an RTSP camera

### 1. Collect camera details

From the camera’s web UI or installer sheet, note:

- LAN **IP address** (example: `192.168.1.100`)
- **RTSP port** (usually `554`)
- **Username** / **password** for the stream (if required)
- **Stream path** (examples: `/stream1`, `/Streaming/Channels/101`, `/live/main` — vendor-specific)

Confirm you can reach the camera from the EyeNet PC (ping or open the camera’s web page).

### 2. Open the add dialog

1. Log in to EyeNet on the platform PC.
2. Home → **Cameras**.
3. In the app bar, tap the **+** icon (**Add RTSP Camera**).
4. The **Add RTSP Camera** dialog opens.

### 3. Fill the form

| Field | Required | Notes |
|---|---|---|
| **Camera Name** | Yes | Unique display name (example: `Front Door`) |
| **Host/IP Address** | Yes | Camera LAN IP or hostname |
| **Port** | Yes | Defaults to `554` |
| **Username** | Optional | Leave blank if the stream has no auth |
| **Password** | Optional | Leave blank if the stream has no auth |
| **Stream Path** | Yes | Must start with `/`. Defaults to `/stream1` |

The dialog shows an **RTSP URL Preview** as you type (password masked). Check it matches what the camera vendor documents.

![Add RTSP Camera dialog with example values and a masked URL preview](./images/add-rtsp-dialog.png)

In this example the preview is `rtsp://admin:****@192.168.1.100:554/stream1`. Leave **Username** and **Password** blank when the stream has no auth; the preview then omits `user:****@`. **Add Camera** saves the camera. **Cancel** or the close icon discards the dialog.

### 4. Save

1. Tap **Add Camera**.
2. Wait for the success message (`Camera added successfully`).
3. The dialog closes and the list reloads.
4. If the camera does not appear, tap **Refresh**.

![RTSP camera card just after it is added. Connect is marked.](./images/camera-card.png)

The name in this figure, **Front Door**, is an example. The grey camera icon and grey dot mean the stream is not connected yet. **Time Period** defaults to **Today**; **Total: 0 people** is the counter before any detections. The marked green link is **Connect**. The trash icon is **Delete camera** (RTSP only). The box icon is **Archive camera**. The faded play icon is **View stream**, and it stays faded until the camera is connected. The live detection strip is not shown.

### 5. Connect and detect

1. Find the new card (filter **RTSP** if the list is long).
2. **Connect** the stream on the card.
3. Tap the **blue eye** (**Start detection**) to start instant detection.
4. Confirm live person counts / overlays update. Use **play** only when you want the live stream view.

### What good looks like (RTSP)

- Card shows connected / healthy
- Instant detection updates on the card
- Camera appears in **Analytics** filters and as a target in **Vradar** (**Automation** → `/triggers`)

### Common RTSP issues

- **Name already exists** — choose a unique **Camera Name**
- **Cannot connect** — wrong IP/port/path, camera offline, or PC cannot reach that subnet
- **Auth failures** — wrong username/password; some cameras need a separate “RTSP user”
- **Wrong path** — keep `/stream1` only if that is the vendor path; otherwise paste the path from the camera docs

---

## Add an edge camera

An **edge camera** is a small on-site computer (typically a **Raspberry Pi**) with a USB or CSI camera. It runs the EyeNet **edge-camera** app, which captures locally and streams to the platform. Your distributor usually installs and starts that stack on the Pi; you add it on the Cameras screen by IP.

Unlike RTSP (IP camera URL) or mobile (phone self-registers), you **Add Edge Camera** from the toolbar after the Pi is online.

### A. Edge device side (usually done by distributor)

1. Raspberry Pi (or equivalent) on the **same LAN** as the EyeNet PC, powered on, with a working USB/CSI camera.
2. Edge-camera container (or service) running and healthy — management API on port **`9001`** by default.
3. Note the Pi’s **LAN IP** (example: `192.168.1.77`). You can open `http://<pi-ip>:9001/health` in a browser; a healthy device answers OK.
4. Optional: the same Pi may also run the [edge signage player](./digital-signage.md#c-raspberry-pi--linux-edge-player) for a lobby screen.

If the edge stack is not installed yet, ask your **distributor** — owner/admin setup on this page assumes the Pi already runs edge-camera.

### B. Platform side

1. Log in to EyeNet on the platform PC.
2. Home → **Cameras**.
3. Tap the **outdoor camera** icon (**Add Edge Camera**).
4. In **Add Edge Camera**, fill:

| Field | Required | Notes |
|---|---|---|
| **Camera Name** | Yes | Unique display name (example: `Office Edge`) |
| **IP Address** | Yes | Pi LAN IP |
| **Port** | Yes | Defaults to **`9001`** (management port) |

5. Tap **Test Connection**. The platform calls `http://<ip>:<port>/api/identify` and must report an edge-camera service. On success, device info appears and the name may auto-fill from the device id.
6. Tap **Add** / save. Wait for success (`Edge camera "…" added successfully`).
7. Filter **Edge** if the list is long. Find the new card.
8. **Connect** the stream on the card (same idea as RTSP — stream must be connected before live ops).
9. Use **instant detection** and/or **recording** as needed (see below — they are independent).

### Connect, detect, and record (edge)

Same card controls as other types, with one important rule:

| Control | What it does on edge |
|---|---|
| **Connect** | Starts the platform ↔ edge stream so the card can show live state |
| **Blue eye** | **Start detection** only — live person counts / Vradar; does **not** start recording |
| **Red circle** | **Start recording** only — archives a clip to My Media; does **not** start instant detection |
| **Play** | Live stream view (larger preview; same detect / record controls) |

You can run detection only, recording only, or both together. Starting **Record** does **not** auto-start the eye.

After you **Stop recording**, the clip is stored in the camera’s media collection. Background face / person processing runs on that video. Open the clip in **My Media** / Media Preview: face rectangles appear, then **Details** / MVR people when processing finishes (see [Detections, individuals and persons](./detections-individuals-persons.md)).

### What good looks like (edge)

- **Test Connection** succeeds before Add
- Card under filter **Edge**, connected / healthy
- Blue eye updates live counts without forcing Record
- Red circle produces a clip; later Preview shows faces and Details / MVR people
- Camera selectable in Analytics and Vradar triggers

### Common edge issues

- **Test Connection fails / timeout** — wrong IP, Pi offline, edge-camera not running, or PC cannot reach that subnet; confirm `http://<ip>:9001/health`
- **Not an edge camera service** — something else is on that port; use the edge management port (**9001**)
- **Name already exists** — choose a unique **Camera Name**
- **Connect does nothing** — edge process stopped or camera device busy on the Pi; ask distributor to check `docker compose` / edge logs on the device
- **Record works but no Details / MVR** — wait for background processing; hard-refresh Media Preview; ensure platform services are on a current pin (edge Record → people needs media + vision + cameras)

---

## Add a mobile camera

A mobile camera is an Android phone running the EyeNet Mobile Camera app. The phone **registers itself** into the platform — there is no “Add Mobile Camera” button on the Cameras toolbar.

This is **not** the **EyeNet Authenticator** app. Authenticator does Presence check-in only and never appears under Cameras → Mobile — see [EyeNet Authenticator](./presence-authenticator.md).

Do the **platform side first**, then the **phone**.

### A. Platform side (do this first)

1. **Confirm the install is healthy**
   - You can log in to EyeNet on the PC.
   - Home → **Network** (`/network`): Discovery Service status should be healthy and services listed.
2. **Note connection details for the phone**
   - Platform **LAN IP** of the EyeNet PC (Windows host IP on the same Wi‑Fi/LAN the phone will use).
   - **Discovery Service port** — usually **`8006`** (also shown in Network / installer notes).
3. **Prepare a local login for the phone**
   - Use an existing local user (owner/admin), or create one under [User management](./users-and-roles.md).
   - You will enter that **username** and **password** in the mobile app.
4. **Same network (LAN path)**
   - Phone and EyeNet PC must be on the same Wi‑Fi / LAN for the simple IP + port setup.
5. **Optional — remote / VPN path**
   - On **Network**, ensure the platform is enrolled in the EyeNet VPN mesh if you need off-LAN phones.
   - Use **Generate token** (enrollment token) on Network when you need the phone to join the mesh and discover the platform without typing a LAN IP.
   - Tokens are short-lived (about **5 minutes**) and **single-use** — mint just before the phone setup.
6. **Leave Cameras open (or ready to refresh)**
   - After the phone registers, the new device appears under filter **Mobile**. Refresh if needed.

### B. Mobile side (phone)

1. **Get the EyeNet Mobile Camera package**
   - Download the release zip from this wiki: **[eyenet-mobile-camera-1.0.0-release.zip](./downloads/eyenet-mobile-camera-1.0.0-release.zip)** (SHA-256: [checksum file](./downloads/eyenet-mobile-camera-1.0.0-release.zip.sha256)).
   - Unzip it. Inside you will find `eyenet-mobile-camera-1.0.0-release.apk` and a short `README.txt`.
   - Your distributor may also provide a later build — use the zip here unless they tell you otherwise.
2. **Prepare the Android phone (Developer options + install permission)**
   - Turn on **Developer options** on the phone before installing the APK. Google’s steps: [Configure on-device developer options](https://developer.android.com/studio/debug/dev-options) (Settings → About phone → tap **Build number** seven times, then open **Developer options**).
   - Manufacturer-specific notes (same idea — Build number / Build version): [Samsung](https://developer.samsung.com/galaxy/others/how-to-install-an-app-via-adb), [Xiaomi / MIUI](https://www.mi.com/global/support/faq/details/?id=1304) (search “Developer options” / USB debugging in the phone’s support pages if the menu names differ).
   - Allow installing apps from this source: after you open the APK, Android will ask to allow your **Files**, **Chrome**, or **Files by Google** app to install unknown apps — turn that on for this install. Overview: [Install apps from unknown sources](https://support.google.com/android/answer/9431958).
3. **Install and open** the APK on the Android phone.
4. **Grant permissions** when Android asks (camera, microphone, network as prompted).
5. **Connect to the platform** (setup / login screen):
   - **LAN:** enter **Backend IP Address** = platform LAN IP from step A.2, and **Discovery Service Port** = `8006` (unless your install uses a different advertised discovery port).
   - **VPN / remote:** paste the **enrollment token** from Network (step A.5), complete mesh join, then continue to sign-in (the app can fill the platform host from enrollment).
6. **Sign in** with the local EyeNet **username** and **password** from step A.3.

<div class="figure-row" markdown="1">

![EyeNet Mobile Camera setup. Platform Connection and User Credentials.](./images/mobile-setup-login.png)

![VPN mesh enrollment on the mobile camera app](./images/mobile-vpn-enrollment.png)

![Connect to Platform on the mobile camera app](./images/mobile-connect-platform.png)

</div>

Left to right: **setup / login** (**Platform Connection** + **User Credentials**), **Join the VPN mesh** (paste token → **Join VPN Mesh**), then **Connect to Platform** under **Direct LAN connection (legacy)**. Values in the figures are examples. For LAN-only setup you can leave the enrollment token empty.

7. **Register this phone as a camera**
   - Enter a clear **Camera Name** (example: `Lobby Phone`).
   - Optional location if the form offers it.
   - Confirm registration success on the phone.

![Register Mobile Camera. Camera Name is pre-filled.](./images/mobile-register-camera.png)

The app suggests a name from the device (example pattern `mcam-…`). Change it to something clear for the site, then **Register Camera**. **Skip Registration** continues to the camera screen without adding the device on the platform (useful only for a quick local check — the phone will not appear under Cameras until you register).

8. **Start streaming** from the mobile app when prompted (or from the camera screen controls).

<div class="figure-row" markdown="1">

![Mobile camera main screen with preview and controls](./images/mobile-camera-feed.png)

![Mobile camera overflow menu](./images/mobile-overflow-menu.png)

</div>

Left: main camera screen (preview, capture / stream controls). Right: overflow menu (**Camera Device**, **Camera Settings**, **Gallery**, **Logout**). The preview here is empty because the lens was covered.

9. **On the platform PC**
   - Home → **Cameras** → filter **Mobile**.
   - Confirm the new mobile camera card appears.
   - Connect / attach the stream (mobile cameras use a lease / attach flow on the card).
   - Start **instant detection** and confirm live counts update.

### What good looks like (mobile)

- Phone shows registered / streaming
- Platform **Cameras** list shows a **Mobile** camera with the name you chose
- Instant detection works on that card
- Camera is selectable in Analytics and Vradar triggers

### Common mobile issues

- **Cannot discover / login** — wrong LAN IP, phone on guest Wi‑Fi isolated from the PC, Discovery not healthy, or wrong port
- **Enrollment token failed** — token expired or already used; mint a new one on Network
- **Camera missing on PC** — registration did not finish; refresh Cameras; check the name was unique
- **Install blocked** — Developer options off, or “install unknown apps” not allowed for the app you used to open the APK; see step 2 above
- **No zip / APK** — use the [download on this page](./downloads/eyenet-mobile-camera-1.0.0-release.zip), or ask your **distributor** for a newer build

---

## Start live detection (any camera type)

1. On a camera card, connect / attach the stream if it is not already connected.
2. Tap the **blue eye** (**Start detection**) on the card to start instant detection (independent of recording).
3. Confirm live person count / overlays update.

![Connected camera card. The cyan ring marks Start detection (blue eye).](./images/camera-card-detect.png)

The green camera icon and green status dot mean the stream is connected. The marked **blue eye** starts **instant detection**. The red circle beside it is **Start recording** — a separate feature (next section), not required for live detection. The **play** control opens the **live stream view** (larger preview; same detection and record controls there). **Front Door** is an example name.

### Live stream view — instant detection

Open **play** on the card for the live stream view. Use **Start Detection** / **Stop Detection** there (same as the blue eye on the card). The preview area below is a placeholder — live frames are not shown in this wiki.

![Live stream view with instant detection on. Stop Detection is marked. Stream area shows the EyeNet logo at low opacity.](./images/stream-detect.png)

On stream / camera detail views you may also see pipeline switches:

![Full Cameras Settings screen. Pipelines shows Instant Detection on; the cyan ring marks that switch.](./images/instant-detection.png)

Turn **Instant Detection** on for real-time person detection with triggers. **Recording Pipeline** is a separate product path and can stay off while you only run instant detection.

## Record video (standalone)

Recording is its own feature. You use it to capture archived video for later review in **My Media** / Media Preview — you do **not** need instant detection running for recording to work. This applies to **RTSP**, **edge**, and **mobile**.

1. On a connected camera card, tap the red **Start recording** control — or open **play** for the live stream view and use **Start Recording** there.
2. Confirm recording (red indicator / timer on the card, or the **RECORDING** bar on the stream view).
3. Tap **Stop recording** when finished.
4. The clip is stored in the camera’s media collection. Background face / person processing for that video runs on the recording path (see [Detections, individuals and persons](./detections-individuals-persons.md)).

![Connected camera card. The cyan ring marks Start recording (red circle).](./images/camera-card-record.png)

The marked red circle is **Start recording**. Play opens the live stream view. The blue eye is instant detection and is independent of this path — Record does **not** turn detection on by itself.

### Live stream view — recording only

Same live stream view, with recording active and instant detection off. Instant detection is not required for this path.

![Live stream view while recording only. Stop Recording is marked. Stream area shows the EyeNet logo at low opacity.](./images/stream-record.png)

### Optional: record while detecting

You *may* run recording and instant detection together (red circle + blue eye both active, or both buttons on the stream view). That is optional. Typical uses:

| Mode | Controls | Result |
|---|---|---|
| Instant detection only | Blue eye / Start Detection on | Live counts / Vradar; no new archive clip |
| Recording only | Red circle / Start Recording | Archived video + later preview / individuals |
| Both (optional) | Eye + record | Live ops and an archive clip at the same time |

## Related

- [Detections, individuals and persons](./detections-individuals-persons.md)
- [Entrances and activity](./entrances-and-activity.md)
- [Vradar — alerts and automation](./alerts-and-automation.md)
- [Analytics and reports](./analytics-and-reports.md)
- [Remote access and multi-site](./multi-site-and-remote.md) (Network / VPN)
- Home → **Camera Ops** (`/camera-operations`) for fleet health and aggregates
