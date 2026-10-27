---
software_ref:
  platform_version: "2.25.103"
  policy_revision: "2026-09-10"
  channels_documented:
    - sandbox
    - pilot
    - stable
  install_path: "windows-wsl-docker-engine-ghcr"
  host_ram_gb: 16
  wsl_memory_gb: 12
title: First install
audience: owner-admin
nav_order: 15
---

# First Install

This is the **User guide** for **platform owners** and **platform admins** on a customer installation: licence key, host install (Windows or Linux), and links into bootstrap and day-to-day ops. Product overview: [What is EyeNet](../what-is-eyenet/). Distributor Authority tools: [Distributors guide](../distributors/).

## Licence key before first install

1. Your distributor (or reseller) invites your **approved owner email** on Authority (`/admin` → People).
2. You accept the invitation and set an **Authority** password (governance account).
3. Copy the `lic_…` application key from your Authority **Licences** view (or receive it from the distributor).
4. On the host PC, use that **same email** plus the key on local **`/bootstrap`**. That creates the local EyeNet account and binds the installation — see [Bootstrap the installation](./bootstrap.md).

Authority password and local app password are separate.

![Accept invitation on Authority — phone / tablet. Set the Authority password here.](./images/mobile-authority-accept-invitation.png)

![Accept invitation on Authority — wide screen. Set the Authority password here.](./images/authority-accept-invitation-wide.png)

## First install

Choose one host path (same GHCR images, host **EyeNet tray**, and bootstrap):

**Windows**

1. Windows 10/11 amd64 PC or **Hyper-V** virtual machine with **≥16 GB RAM** and **≥12 GB** free disk (same install path on physical hosts and Hyper-V guests). Run the installers as **Administrator**.
2. Download the Windows installer zip from this wiki: **[eyenet-windows-2.25.103.zip](./downloads/eyenet-windows-2.25.103.zip?v=20261020-44cfe24f)** (SHA-256: [checksum file](./downloads/eyenet-windows-2.25.103.zip.sha256?v=20261020-44cfe24f)). Unzip it.
3. Double-click **`install-eyenet-wsl.bat`**. This creates the WSL2 distro **`eyenet`** with **Docker Engine CE** (not Docker Desktop) and configures **12 GB** WSL memory. If Windows asks to restart WSL, finish that step and re-run the same bat if prompted.
4. Double-click **`install-platform.bat`**. Accept the default install directory (`C:\ppl-meta-platform`) unless you need another path. The installer pulls pinned GHCR images, applies the database schema, and installs the **EyeNet tray** (start/stop/restart and status from the system tray; also starts at Windows logon).
5. Open **http://localhost:3000** and complete **bootstrap** with the approved owner email and licence / application key — see [Bootstrap the installation](./bootstrap.md).

**Linux**

1. **Ubuntu 24.04** (or a compatible amd64 Ubuntu) with **≥16 GB RAM**.
2. Download the Ubuntu installer zip from this wiki: **[eyenet-ubuntu-2.25.103.zip](./downloads/eyenet-ubuntu-2.25.103.zip?v=20261020-7f626037)** (SHA-256: [checksum file](./downloads/eyenet-ubuntu-2.25.103.zip.sha256?v=20261020-7f626037)). Unzip it.
3. In a terminal inside the unzipped folder, run **`bash install-eyenet-ubuntu.sh`** (optional: `ADVERTISE_HOST=<lan-ip> bash install-eyenet-ubuntu.sh`). The installer installs **Docker Engine** if needed, pulls the same pinned GHCR images, applies the schema, and installs the **EyeNet tray** (start/stop and status from the desktop tray / AppIndicator).
4. Open **http://localhost:3000** and complete **bootstrap** with the approved owner email and licence / application key — see [Bootstrap the installation](./bootstrap.md).

**Android phone or tablet**

The same EyeNet app (launcher name **EyeNet Media**, version **1.0.0**, built **13 October 2026, 13:02**) can be installed on an Android phone or tablet. This is the platform app used for bootstrap and day-to-day work. It is separate from the Mobile Camera and Signage player apps.

1. Download the release zip from this wiki: **[eyenet-media-1.0.0-release.zip](./downloads/eyenet-media-1.0.0-release.zip?v=20261013-1302)** (SHA-256: [checksum file](./downloads/eyenet-media-1.0.0-release.zip.sha256?v=20261013-1302)).
2. Unzip it. Inside you will find `eyenet-media-1.0.0-release.apk` and a short `README.txt`.
3. Turn on **Developer options** before installing the APK. Google’s steps: [Configure on-device developer options](https://developer.android.com/studio/debug/dev-options) (Settings → About phone → tap **Build number** seven times, then open **Developer options**).
4. Allow installing apps from this source: after you open the APK, Android will ask to allow your **Files**, **Chrome**, or **Files by Google** app to install unknown apps — turn that on for this install. Overview: [Install apps from unknown sources](https://support.google.com/android/answer/9431958).
5. Install and open the APK.
6. Complete **bootstrap** on this device with the approved owner email and licence / application key, or sign in if the installation is already active — see [Bootstrap the installation](./bootstrap.md). The phone or tablet must reach the EyeNet host (same LAN, or the remote path in [Remote access and multi-site](./multi-site-and-remote.md)).

See [Hardware and Docker requirements](./hardware.md). Full bootstrap steps and screenshots: [Bootstrap the installation](./bootstrap.md).

## After install — operating the platform

Work from the local EyeNet home screen after login. Suggested order:

| Topic | Page | Home tile / route |
|---|---|---|
| Hardware and Docker | [Hardware and Docker requirements](./hardware.md) | Host prep before / after install |
| First install (this page) | [First install](./index.md) | Licence key · Windows / Linux · Android app · tray |
| Bootstrap (first activation) | [Bootstrap the installation](./bootstrap.md) | `/bootstrap` (once, before login) |
| User management | [User management](./users-and-roles.md) | menu **Users** / **Roles** → `/users`, `/roles` |
| Cameras and live detection | [Cameras and detection](./cameras-and-detection.md) | **Cameras** → `/cameras` |
| Detections, individuals and persons | [Detections, individuals and persons](./detections-individuals-persons.md) | Cameras · My Media · Individual Groups |
| Media and collections | [Media and collections](./media-management.md) | **Upload Media** · **My Media** · **Collections** |
| Vradar (alerts & automation) | [Vradar — alerts and automation](./alerts-and-automation.md) | **Automation** → `/triggers` |
| Presence and attendance | [Presence and attendance](./presence-attendance.md) | **Presence** → `/presence` |
| EyeNet Authenticator | [EyeNet Authenticator](./presence-authenticator.md) | Android phone Presence (sandbox / pilot) |
| Digital signage | [Digital signage](./digital-signage.md) | **Signage Management** → `/signage` |
| Entrance and activity monitoring | [Entrances and activity](./entrances-and-activity.md) | Cameras + Analytics + Automation |
| Analytics and reports | [Analytics and reports](./analytics-and-reports.md) | **Analytics** → `/analytics` |
| Remote access and multi-site | [Remote access and multi-site](./multi-site-and-remote.md) | **Network** → `/network` |

## Updates

- Most installations receive **stable** releases only
- Some installations may be on **pilot** and see updates earlier
- After an update, verify login, Authority status, and basic media/camera paths

You do not change another customer's release channel from this wiki.
