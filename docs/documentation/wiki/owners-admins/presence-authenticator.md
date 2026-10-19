---
software_ref:
  platform_version: "2.25.101"
  policy_revision: "2026-10-18"
  channels_documented:
    - sandbox
    - pilot
    - stable
  install_path: "windows-docker-desktop-ghcr"
  host_ram_gb: 16
  wsl_memory_gb: 12
title: EyeNet Authenticator
audience: owner-admin
nav_order: 51
---

# EyeNet Authenticator

Phone app for **Presence check-in** without registering the device as a cameras-console camera. You sign in to the install, enroll a face once, then run QR and video Presence actions. The phone does **not** appear under **Cameras** → Mobile.

**Channels:** sandbox and pilot while Android packaging / distribution is finalized. Not documented as generally available on stable yet.

**Related console guide:** [Presence and attendance](./presence-attendance.md)

---

## When to use which app

| App / surface | Registers as camera? | Best for |
|---|---|---|
| **EyeNet Authenticator** | No | Staff / member check-in on a personal phone; QR + enrolled-face video grants |
| **EyeNet Mobile Camera** | Yes | Live stream into Cameras + Presence controls on that stream — [Add a mobile camera](./cameras-and-detection.md#add-a-mobile-camera) |
| **Presence → Actions** (web console) | N/A | Station QR, desk webcam owner-QR decode, trigger-backed Video Match |

Authenticator does **not** replace Mobile Camera streaming. Use Mobile Camera when you need the phone in the Cameras list.

---

## Prerequisites

- Bootstrap completed; a **local** platform user (owner, admin, or member role that can use Presence)
- Platform reachable from the phone:
  - Same LAN (Discovery usually port **`8006`**), or
  - Off-LAN via EyeNet VPN enrollment token — [Remote access and multi-site](./multi-site-and-remote.md)
- Android device that can install APKs (sideload / unknown sources)
- For video match paths: face enrollment completed once (below)
- Optional: Individual Group / People profiles already used for Presence — [Detections, individuals and persons](./detections-individuals-persons.md), Presence → **People**

Authenticator video modes do **not** require Presence Settings **Video readiness** (that gate is for console / Mobile Camera trigger paths).

---

## Download (pilot APK)

**On an Android phone, download the APK directly.** Do **not** unzip on the phone — many Android file managers fail to extract the archive or corrupt the package.

### A. Phone (recommended)

1. On the phone browser, download **[eyenet-authenticator-1.0.3-pilot.apk](./downloads/eyenet-authenticator-1.0.3-pilot.apk?v=20261020-103)** (SHA-256: [checksum file](./downloads/eyenet-authenticator-1.0.3-pilot.apk.sha256?v=20261020-103)). Uninstall any older Authenticator first if Android blocks the update.
2. Turn on **Developer options** if install is blocked. Google’s steps: [Configure on-device developer options](https://developer.android.com/studio/debug/dev-options) (Settings → About phone → tap **Build number** seven times, then open **Developer options**).
3. Open the downloaded `.apk`. When Android asks, allow **Install unknown apps** for **Chrome**, **Files**, or **Files by Google** for this install. Overview: [Install apps from unknown sources](https://support.google.com/android/answer/9431958).
4. Tap **Install**, then open **EyeNet Authenticator**. You should see a short “Starting…” splash, then the sign-in screen (not a blank white page).
5. If Play Protect warns about an unknown app, choose **Install anyway** / **More details** → install (pilot sideload builds are not on the Play Store).

### B. Computer → USB (fallback)

Use this only if the phone browser cannot download the APK.

1. On a computer, download **[eyenet-authenticator-1.0.3-pilot.zip](./downloads/eyenet-authenticator-1.0.3-pilot.zip?v=20261020-103)** (SHA-256: [checksum file](./downloads/eyenet-authenticator-1.0.3-pilot.zip.sha256?v=20261020-103)).
2. Unzip **on the computer** (not on the phone). You should see `eyenet-authenticator-1.0.3-pilot.apk` and `README.txt`.
3. Copy **only the `.apk`** to the phone (USB, Drive, AirDrop-style share, etc.).
4. On the phone, open that `.apk` and follow the same unknown-sources steps as in A.

Your distributor may also provide a later build — use the files on this page unless they tell you otherwise.

---

## Install and sign-in (Plan A)

1. Install the APK from [Download (pilot APK)](#download-pilot-apk) (**prefer the direct `.apk` link on the phone**).
2. Open the app. Choose how to find the platform:
   - **LAN Discovery** — phone and EyeNet PC on the same network; Discovery listens on port **`8006`** (see Home → **Network**).
   - **VPN enrollment** — on the console, Network → **Generate token** (short-lived, about five minutes, typically single-use). On the phone, turn on **Join VPN mesh (enrollment token)**, paste the token, tap **Join VPN Mesh**, then continue.
3. Sign in with the **local** install username and password (same credentials as the web console). The app does **not** look up users in the Authority directory (Plan A).
4. After login you are gated to **face enrollment** if this user is not enrolled yet.

![EyeNet Authenticator sign-in. EyeNet logo, Discovery IP and port 8006, username, local password, Sign in.](./images/authenticator-setup.png)

**EyeNet Authenticator** title and logo are at the top. Enter **Backend / Discovery IP** and **Discovery port** (example **8006**), then **Username / email** and **Local password**. Use **Join VPN mesh** only for off-LAN. **Sign in** continues to enrollment or Presence home.

---

## Face enrollment (once)

Enrollment binds a durable face identity (MVR) to the signed-in user’s Presence people profile (PPP).

1. Follow the enroll screen and capture a clear front face still.
2. Wait for success. First enroll on a cold install can take longer while face models load.
3. The app stores only a local reference; the platform keeps the binding on the user’s PPP.
4. If the console already linked MVRs to that person in an Individual Group, enrollment may **reuse** a matching linked MVR instead of creating a new one.
5. Enrollment status is checked on next launch; users who are already enrolled skip the gate.

The enroll gate explains that this phone is **not** registered as a camera. Capture a face still when prompted, then wait for the platform to finish binding.

Re-enroll only if the person’s appearance changed enough that live verify fails repeatedly, or if an admin cleared the authenticator binding on the profile.

---

## Check-in actions

Home actions match the Presence session modes:

| Action | Mode | What happens |
|---|---|---|
| **Owner QR** | Identity QR | Shows your owner QR for a desk console **Scan Owner QR** path |
| **Scan station QR** | `qr_only` | Scan the station QR from Presence → Actions → **Render QR**. Session is created around the scan so unused QR sessions do not pile up as expires. |
| **Video match** | `camera_only` | Live face capture → verify against enrolled / PPP-linked MVR → grant or deny |
| **QR + Video** | `qr_plus_camera` | Scan station QR, then live face verify |

![EyeNet Authenticator Presence home. Signed-in email, enrolled MVR hint, Owner QR, Scan station QR, Video match, QR + Video.](./images/authenticator-home.png)

After enrollment, **Presence** home lists the four actions. The signed-in email and a short enrolled-MVR hint appear above the list. App bar actions include re-enroll (face icon) and sign out.

### Tips

- Prefer **scan, then complete** for QR: open Scan station QR, aim at a fresh **Render QR** on the console, then wait for the result banner.
- Video paths always capture a **live** face; the app never grants from a cached face UUID alone.
- Watch Presence → **Sessions** on the console for the operator-of-record decision and reason code.

---

## What admins see on the console

| Where | What to look for |
|---|---|
| **Sessions** | Filter **Origin → authenticator**. Decision, failure reason, and policy chips on the inspector. |
| **Analytics** | **Client Origin** donut; **Policy Sources** such as `authenticator_mvr_verify`; **Failure Reasons** for expires / face mismatch. Tap through to Sessions. |
| **People** | Profile linked to the signed-in user; authenticator MVR binding is server-side on that PPP. |

Full Analytics / Sessions layout: [Presence and attendance — Analytics](./presence-attendance.md#analytics).

---

## Limits (v1 / pilot)

- Android only in this pass; iOS not documented here
- Not a live RTSP / mobile camera stream
- No Authority email → VPN directory login (Plan B)
- Does not implement every console Actions control (e.g. rendering station QR from the phone against a USB webcam)
- Distribution is the [pilot APK / zip on this page](#download-pilot-apk) until a store package is published

---

## Troubleshooting

| Symptom | What to try |
|---|---|
| Phone cannot unzip the zip / “extract failed” | **Expected on many Androids.** Use the **direct `.apk` link** in [Download A](#download-pilot-apk), or unzip on a computer and copy only the `.apk` |
| APK from a phone-unzipped zip will not install / “package invalid” / “corrupt” | Delete it. Download the **direct `.apk`** again (or copy a computer-unzipped APK). Do not re-use a phone-extracted file |
| White / blank screen after open | Install **1.0.1+** from this page (cold start no longer waits on VPN/network). Uninstall the old app first, reinstall, force-stop, reopen |
| “Future not completed” / connection timed out | Install **1.0.3+**. Means Discovery/login timed out — same Wi‑Fi as the EyeNet PC (port **8006**), or Tailscale IP of the PC (e.g. `100.x`). Off-LAN do not use a `192.168.*` Discovery IP |
| “Shared preferences unavailable” / missing preferences | Install **1.0.3+**, fully uninstall the old app, reboot the phone, reinstall the wiki `.apk` |
| Install blocked | Developer options off, or “install unknown apps” not allowed for the browser/Files app you used; see Download A steps 2–3 |
| Play Protect blocks install | **Install anyway** / open details and continue — pilot builds are sideloaded |
| Download stops early / APK smaller than ~100 MB | Incomplete download. Delete and download the `.apk` again on Wi‑Fi |
| Cannot discover platform | Same Wi‑Fi / LAN; confirm Discovery on **`8006`** under Network; or use a fresh VPN enrollment token |
| Login fails | Use local install credentials (Users), not an Authority-only identity |
| Enroll hangs or times out | Wait for first model load; retry with good lighting and a clear face; confirm Presence + vision services are healthy |
| Video match denied / face mismatch | Re-capture enroll; ensure the person is the signed-in user; check Sessions reason code; confirm PPP / group links if you expect a console-linked MVR |
| QR shows failed / expired on console | Prefer scan-then-complete; avoid creating many station QRs that nobody scans; filter Analytics **Expired** / Failure `presence_session_expired` |
| Console Video Match stays Not ready | Expected for trigger paths — fix [video readiness](./presence-attendance.md#settings-video-readiness). Authenticator video does not need that green report. |
| No zip / APK | Use the [downloads on this page](#download-pilot-apk), or ask your **distributor** for a newer build |

---

## Related

- [Presence and attendance](./presence-attendance.md)
- [Cameras and detection — Add a mobile camera](./cameras-and-detection.md#add-a-mobile-camera) — different app
- [Remote access and multi-site](./multi-site-and-remote.md) — VPN enrollment tokens
- [User management](./users-and-roles.md)
- [Entrances and activity](./entrances-and-activity.md)

For integrators (API sketch): repository proposal `docs/proposals/authenticator/ppl-meta-authenticator-plan-a-enrolled-mvr.md` (not published on this wiki).
