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
title: Digital signage
audience: owner-admin
nav_order: 60
---

# Digital Signage

Build playlists from media collections, discover signage player devices, sync content, and control playback remotely. Audience-aware switching uses **Vradar** Automation actions of type **Digital Signage**.

**Where (platform):** Home → **Signage Management** (`/signage`)

![Full Signage Management screen on Playlists. App bar, Playlists / Devices / Messages tabs, and master/detail list are shown.](./images/signage-tabs.png)

**Playlists** is selected when you open Signage Management. The cyan underline is the selected tab. **Refresh** reloads playlists and devices. **Devices** and **Messages** are the other tabs. Players are not added from this bar.

A signage **player** is a separate app that registers with Discovery. Players are not added with a toolbar button on the platform — they appear under **Devices** after the player connects. Two common device paths:

| Player | Typical hardware | Setup on this page |
|---|---|---|
| **Android Simple Player** | Phone, tablet, TV stick | [Section B](#b-android-player-device-side-after-platform-prep) |
| **Edge / Raspberry Pi player** | Raspberry Pi with HDMI display (often same Pi as an [edge camera](./cameras-and-detection.md#add-an-edge-camera)) | [Section C](#c-raspberry-pi-linux-edge-player) |

Platform **Playlists**, **Sync**, **Devices** controls, and **Vradar** Digital Signage actions are the same for both.

---

## Prerequisites

- Bootstrap completed; you can log in as owner or admin
- Video content in **user** media collections (Home → **Collections** / **Upload Media**). Camera-linked collections are not used as playlist sources.
- Discovery healthy on Home → **Network** (`/network`)
- A player device:
  - **Android:** phone/tablet/TV stick that can install APKs, and the **EyeNet Signage Simple Player** zip (section B), **or**
  - **Edge / RPi:** Raspberry Pi with HDMI display running the Linux signage player (section C; usually installed by your distributor)
- For vision-triggered playlists: [cameras + instant detection](./cameras-and-detection.md) and [Vradar](./alerts-and-automation.md)

---

## A. Platform side (do this first)

### 1. Confirm the install is ready

1. Log in to EyeNet on the platform PC.
2. Home → **Network**: Discovery Service status should be healthy and services listed.
3. Note the platform **LAN IP** and **Discovery port** (usually **`8006`**) for player setup.
4. Optional (remote / off-LAN players): enroll the platform in the EyeNet VPN mesh; use **Generate token** on Network for a short-lived, single-use **enrollment token** (about 5 minutes) just before device setup.

### 2. Prepare media

1. Home → **Upload Media** / **Collections**.
2. Create or open a **user** collection and upload the videos you want on screens.
3. Confirm videos appear in the collection (item count &gt; 0).

### 3. Create a playlist

1. Home → **Signage Management** → **Playlists**.
2. Tap **New Playlist** when playlists already exist, or **Create Playlist** on the empty state (*No playlists yet*).
3. In **Create Video Playlist**, set:

| Field | Notes |
|---|---|
| **Playlist Name** | Required |
| **Description** | Optional |
| **Loop Mode** | Play Once · Continuous Loop · Shuffle |
| **Transition (seconds)** | Gap between items (stored as ms) |
| **Collections** | Tick one or more user collections that contain videos |

4. Optionally reorder videos in the list when the builder shows ordered items.
5. Tap **Create**.
6. Select the playlist in the sidebar. **Content** shows videos from the assigned collections. **Settings** (the gear) edits name, collections, loop, and transition. The form title is **Edit Video Playlist** and the button is **Save**.

![Full Signage Playlists screen. Search playlists and New Playlist are shown; New Playlist is marked.](./images/playlists-toolbar.png)

**Search playlists...** filters the list. The marked **New Playlist** opens **Create Video Playlist**. The cyan outline is only a marker in this figure. The empty-state button label is **Create Playlist**.

![Full Signage Playlists screen with Create Video Playlist open and example values.](./images/create-playlist.png)

Example only. **Lobby Display** is a typed name; the empty-field hint is *e.g., Morning Display*. **Loop Mode** defaults to **Continuous Loop**. The other choices are **Play Once** and **Shuffle**. **Transition (seconds)** defaults to **1**. **Lobby Signage** is an example user collection. **welcome.mp4** and **hours.mp4** are example file names, not pictures. **Auto-order** sorts the list; you can also drag rows. **Create** saves. Editing uses **Save**.

![Full Signage Playlists screen with Lobby Display selected. Content view (list icon) shows example videos.](./images/playlist-pane.png)

The pill switches views. The list icon is **Content** (selected here). The gear is **Settings**. File names are examples. The app also shows a preview frame for each video; those frames are placeholders here. **2 videos • 2m** is an example count.

### 4. Playlist actions

On a playlist row menu (⋮):

| Action | What it does |
|---|---|
| **Edit** | Open settings for that playlist |
| **Sync to Devices** | Push the playlist to selected **online** players |
| **Duplicate** | Copy the playlist |
| **Delete** | Remove the playlist (confirm) |

![Full Signage Playlists screen with a playlist row menu open (Edit, Sync to Devices, Duplicate, Delete).](./images/playlist-menu.png)

The number in the circle is the video count. **Lobby Display** and **2 videos • 2m** are examples. **⋮** opens **Edit**, **Sync to Devices**, **Duplicate**, and **Delete** (red). **Edit** opens Settings on the detail pane.

**Sync to Devices** dialog:

1. Choose one or more online devices (checkboxes).
2. Tap **Sync**.
3. Confirm success snackbar (*Sync started successfully…*).

![Full Signage Playlists screen with Sync dialog open. Lobby Screen is an example device name.](./images/sync-devices.png)

Online devices are checked by default. **Sync** starts the push. If none are online, the dialog says **No online devices available**.

If no devices appear, finish **player side** setup below and refresh **Devices**.

### 5. Devices and remote playback

1. Open the **Devices** tab.
2. Refresh if the list is empty or stale.
3. Select a device (name, host/IP, online/offline).
4. In the detail pane **Playback Controls**:

| Control | Purpose |
|---|---|
| **Play** / **Pause** / **Resume** | Start or toggle playback |
| **Stop** | Stop playback |
| **Skip previous / next** | **Previous** and **Next**. **Restart** replays the current playlist |
| **Select & Play Playlist** | Choose a synced playlist and start it on this device. The dialog title is **Select Synced Playlist** |
| Volume | Device volume slider |
| History | **Playback History** when items have already played |

![Full Signage Devices screen with Lobby Screen selected. Playback Controls show idle state (nothing playing).](./images/playback-controls.png)

**Lobby Screen** and **192.168.1.50:8080** are examples. The green dot means **online**; offline is red. **No video currently playing** is the idle state. **Play** is green and opens **Select Synced Playlist** when nothing is loaded. **Previous**, **Stop**, **Restart**, and **Next** stay grey until a playlist is active; **Stop** is red while playback is running. **Refresh Status** is the circular arrow. Volume here is the default **100%**.

Device must show **online** for controls to work. Status refreshes automatically on a short interval.

### 6. Optional — vision-adaptive signage (Vradar)

1. Aim a camera at the audience in front of the screen; start [instant detection](./cameras-and-detection.md).
2. Home → **Automation** → create a **Digital Signage** action: select player device(s), the first **Playlist**, optional **Second Playlist** + **Duration (seconds)** (play the first, then switch), and **Transition Mode** (Immediate / After Current Video / Fade).
3. Create an **Instant Demographic** (or other) trigger on that camera; link the action.
4. Walk a test audience past the camera and confirm the player switches content.

See [Vradar — alerts and automation](./alerts-and-automation.md).

### What good looks like (platform)

- Playlist lists videos from your collections
- **Devices** shows the player as online after player setup
- Sync completes; **Play** changes what the screen shows
- Optional Vradar action fires and updates the player

---

## B. Android player / device side (after platform prep)

Android signage players **register themselves** with Discovery. Do platform Network + media prep first, then set up the device. For a Raspberry Pi HDMI player, skip to [section C](#c-raspberry-pi-linux-edge-player).

### 1. Get the player app

1. Download the release zip from this wiki: **[eyenet-signage-simple-player-1.0.0-release.zip](./downloads/eyenet-signage-simple-player-1.0.0-release.zip)** (SHA-256: [checksum file](./downloads/eyenet-signage-simple-player-1.0.0-release.zip.sha256)).
2. Unzip it. Inside you will find `eyenet-signage-simple-player-1.0.0-release.apk` and a short `README.txt`.
3. Your distributor may also provide a later build — use the zip here unless they tell you otherwise.
4. **Prepare the Android device (Developer options + install permission)**
   - Turn on **Developer options** before installing the APK. Google’s steps: [Configure on-device developer options](https://developer.android.com/studio/debug/dev-options) (Settings → About phone → tap **Build number** seven times, then open **Developer options**). On a TV stick the menu names differ; use the device’s settings to allow apps from this source.
   - Allow installing apps from this source: after you open the APK, Android will ask to allow your **Files**, **Chrome**, or **Files by Google** app to install unknown apps — turn that on for this install. Overview: [Install apps from unknown sources](https://support.google.com/android/answer/9431958).
5. **Install and open** the APK on the display device.

### 2. Open Backend Setup

1. Launch the player app.
2. On first run you should see **Backend Setup** (PPL Meta Signage · Simple Player).

![EyeNet Signage Simple Player Backend Setup (portrait). LAN defaults; Join the VPN mesh off.](./images/mobile-signage-backend-setup.png)

**Backend IP Address**, **Discovery Service Port** (default **8006**), and **Connect**. Helper: *Local discovery. No enrollment token required.*

### 3. Connect to the platform

**LAN (default — same Wi‑Fi / network as the EyeNet PC):**

1. Enter **Backend IP Address** = platform LAN IP from platform Network notes.
2. Enter **Discovery Service Port** = `8006` (unless your install advertises a different port).
3. Leave **Join the VPN mesh** off unless you need remote mesh access.
4. Connect / save. Local discovery enrolls the device **without** an enrollment token.

**VPN / remote (optional):**

1. On the platform **Network** screen, mint a fresh **enrollment token** (Generate token).
2. On the player, turn on **Join the VPN mesh (enrollment token)**.
3. Paste the one-time token (and Authority URL if your distributor specifies one other than the default).
4. Connect. Token is short-lived and single-use — mint immediately before this step.

![Backend Setup with Join the VPN mesh on. One-time enrollment token and Authority URL fields are shown.](./images/mobile-signage-backend-setup-vpn.png)

### 4. Landscape player views

After connect, the Simple Player is meant to run **landscape** on the display (phone/tablet/TV stick). Top-right icons: **Allow Portrait + Landscape**, **Configuration** (gear), **Toggle Info**.

#### Idle (waiting for content)

![Landscape Signage Simple Player idle. EYENET logo, No playlist loaded, Waiting for content…](./images/mobile-signage-idle.png)

#### Playlist loaded

After platform **Sync** (or remote load), the player can show **Playlist loaded: {name}** and **Start Playback**.

![Landscape player with Playlist loaded: Lobby Display and Start Playback.](./images/mobile-signage-playlist-ready.png)

#### Playing

Full-screen video playback. Chrome is minimal; the figure uses a placeholder frame labeled with an example file name.

![Landscape player during full-screen playback (example welcome.mp4 placeholder).](./images/mobile-signage-playing.png)

#### Status overlay (Toggle Info)

Tap the info icon for playlist + system status (**Backend** Connected / Offline, **Discovery** Registered / Not registered, now playing, loop mode, …).

![Landscape player with status overlay showing Playlist and System details.](./images/mobile-signage-status.png)

#### Backend Configuration

Gear → **Backend Configuration**: **Backend IP Address**, **Discovery Port**, **Reset & Reconfigure**, **Cancel**, **Save**.

![Landscape player with Backend Configuration dialog open.](./images/mobile-signage-config.png)

### 5. Confirm on the platform

1. Home → **Signage Management** → **Devices** → refresh.
2. Confirm the new player appears and becomes **online**.
3. **Sync** a playlist to it, then use **Play** / **Select & Play Playlist**.

### What good looks like (player)

- Backend Setup completes without error
- Device listed and online under **Devices**
- Synced playlist plays full-screen on the player hardware (landscape)

### Common player issues

- **Device never appears** — wrong LAN IP, guest Wi‑Fi isolation, Discovery unhealthy, or player not finished setup
- **Enrollment token failed** — expired or already used; mint a new token on Network
- **Offline after reboot** — player must reach Discovery again (same IP/port or VPN still enrolled)
- **Sync / Play fails** — device offline; playlist empty; or no videos in the assigned collections
- **Install blocked** — Developer options off, or “install unknown apps” not allowed for the app you used to open the APK; see step 1 above
- **No zip / APK** — use the [download on this page](./downloads/eyenet-signage-simple-player-1.0.0-release.zip), or ask your **distributor** for a newer build

---

## C. Raspberry Pi / Linux edge player

Use this when the display is a **Raspberry Pi** (or Linux mini PC) with HDMI out — often the **same Pi** that runs an [edge camera](./cameras-and-detection.md#add-an-edge-camera). The player is the **EyeNet Signage Simple Player** Linux build (Docker or native), not the Android APK.

Your **distributor** normally installs and starts the player on the Pi. Owner/admin work is: prepare playlists on the platform, confirm the device is online, Sync, and Play — same as Android.

### 1. Edge device side (usually distributor)

1. Pi on the **same LAN** as the EyeNet PC, HDMI connected to the lobby / window screen, powered on.
2. Signage player container or service running (typical compose stack may also include `edge-camera`).
3. Player can reach platform **Discovery** (usually port **`8006`**) and the gateway.
4. Display is intended **landscape**. On first start the Linux player often opens **fullscreen**; keyboard shortcuts on the Pi:

| Key | Action |
|---|---|
| **F11** | Toggle fullscreen |
| **Esc** (or **Q**) | Quit the player app |
| **Space** | Pause / resume (when controls allow) |
| **C** | Show / hide on-screen controls (when offered) |

5. Note the Pi LAN IP if you need local checks. The player’s embedded control/health port is often **`8009`** (distributor notes may differ).

If the player is not installed yet, ask your **distributor** — do not treat the Android zip on this page as the Pi package.

### 2. Connect to the platform

Same idea as Android Backend Setup, configured on the edge install:

- **LAN:** platform LAN IP + Discovery port **`8006`** (unless your install advertises another port).
- **VPN / remote (optional):** enroll with a short-lived Network **enrollment token**, then Discovery over the mesh.

After connect, the player registers with Discovery and should appear under Signage **Devices**.

### 3. Confirm and play (platform)

1. Home → **Signage Management** → **Devices** → **Refresh**.
2. Confirm the Pi player is listed and **online** (green).
3. On a playlist, **Sync to Devices** and include this device.
4. Select the device → **Play** / **Select & Play Playlist**.
5. Confirm the HDMI screen shows the video full-screen (landscape).

Remote controls (**Pause**, **Stop**, **Previous** / **Next**, volume, history) work the same as for Android players when the device is online.

### 4. Optional — vision-adaptive signage on the edge kit

A common lobby kit is **one Pi** with:

- USB/CSI camera → [edge camera](./cameras-and-detection.md#add-an-edge-camera) aimed at the audience  
- HDMI → this signage player  

Then wire a [Vradar Digital Signage](./alerts-and-automation.md) action (first playlist, optional **second playlist** + duration) to that camera’s instant detection, as in section A.6.

### What good looks like (RPi / Linux player)

- Device online under **Devices** after Discovery registration
- Sync + Play fills the HDMI screen (fullscreen landscape)
- F11 / Esc behave as above when you need to leave kiosk mode on the Pi
- Optional Vradar action switches playlists when people are detected

### Common RPi / Linux player issues

- **Device never appears** — player not running, wrong Discovery IP/port, guest Wi‑Fi isolation, or Discovery unhealthy
- **Online but black / frozen screen** — HDMI cable/output, player not fullscreen (try **F11**), or playlist empty / not synced
- **Sync / Play fails** — device offline; no videos in the user collections; or player cannot reach media/gateway
- **Edge camera works but signage does not** — camera and player are separate processes on the Pi; ask distributor to check signage container/logs specifically
- **Need a new Pi image** — ask your **distributor** (Android APK zip is not the Linux/RPi package)

---

## Recommended setup order

1. Upload videos into a user collection.  
2. Create a playlist from that collection.  
3. Install and connect a player — **Android** (section B) or **Raspberry Pi / Linux** (section C).  
4. Confirm device online → Sync → Play (landscape / HDMI shows content).  
5. Optional: wire a Vradar Digital Signage action to a camera in front of the screen (edge camera + edge player is a common pair).

## Related

- [Vradar — alerts and automation](./alerts-and-automation.md)
- [Cameras and detection](./cameras-and-detection.md) (including edge camera)
- [Remote access and multi-site](./multi-site-and-remote.md) (Network / enrollment tokens)
- [Media and collections](./media-management.md) — upload and user collections for playlist sources
