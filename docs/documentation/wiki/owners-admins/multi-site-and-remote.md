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
title: Remote access and multi-site
audience: owner-admin
nav_order: 90
---

# Remote Access And Multi-Site

Reach this installation away from the LAN, connect leaf apps (mobile camera, digital signage) when they are off-site, and understand how multi-site (**Matrix**) reporting fits. Core video and detection stay on the customer PC; remote reach uses the **EyeNet VPN** mesh when the install and devices are enrolled.

**Where (this install):** Home → **Network** (`/network`) — app bar **Network & Services**

---

## What EyeNet VPN is

The mesh VPN you see on **Network** is **EyeNet VPN** (product UI: **VPN Mesh** / **EyeNet VPN mesh**). It is the hosted mesh path for this installation — login server typically `https://vpn.eyenet-vision.com`, MagicDNS names like `*.eyenet-vpn.local`.

**It is provided with the EyeNet licence / application key for the installation** (the same bootstrap licence path that binds the PC). You do not buy a separate consumer VPN product for day-to-day EyeNet remote access. Your distributor provisions Authority / VPN for your channel; after bootstrap, the platform can enroll with that licence identity.

| Stays local (no cloud for video) | Uses EyeNet VPN when enrolled |
|---|---|
| Recording, detection, media on the PC | Off-LAN operator access to this install |
| Same-LAN phones / players (Discovery) | Off-LAN **mobile camera** and **signage player** apps |
| Instant detection / Vradar on site | Multi-site **Matrix** traffic between member installs |

Internet is needed for enrollment and remote mesh traffic. On the LAN, prefer the platform **LAN IP** and Discovery (usually port **`8006`**); use the mesh address when off site.

---

## Who joins the mesh

EyeNet VPN targets **both** the software installation and the leaf apps that talk to it:

| Participant | Role | How it joins |
|---|---|---|
| **Platform** (Windows EyeNet install) | Hub: Discovery, cameras API, media, Automation, etc. | Licence-backed enroll — often automatic after bootstrap; or **Enroll Now** on Network |
| **Mobile camera** app | Phone / tablet as a camera source | Optional **Join the VPN mesh (enrollment token)** on device setup — token from Network |
| **EyeNet Authenticator** app | Phone Presence check-in (not a camera) | Optional **Join the VPN mesh (enrollment token)** on Plan A setup — same Network token mint — [EyeNet Authenticator](./presence-authenticator.md) |
| **Digital signage** player | Screen player (Signage Simple Player) | Optional **Join the VPN mesh (enrollment token)** on Backend Setup — same Network token mint |

Same-LAN devices can skip VPN and use Backend IP + Discovery port only. Turn VPN enrollment **on** when the phone or player cannot reach the PC on the local network (remote site, different VLAN, operator off-site).

Step-by-step for each leaf app:

- Mobile camera — [Cameras and detection — Add a mobile camera](./cameras-and-detection.md)
- Authenticator — [EyeNet Authenticator](./presence-authenticator.md)
- Signage player — [Digital signage — Player / device side](./digital-signage.md)

---

## Prerequisites

- Healthy local install (login works; cameras / media paths OK on LAN)
- Bootstrap completed with the approved owner email and **licence / application key** (EyeNet VPN enroll uses that installation identity)
- Discovery healthy on **Network** (services listed)
- For remote leaf devices: internet on the platform and on the phone/player; mint a fresh enrollment token just before device setup
- Mobile camera and signage player zips on this wiki ([mobile camera](./cameras-and-detection.md), [signage player](./digital-signage.md)). Your distributor may provide a later build.

---

## A. Network screen (this installation)

1. Home → **Network** (subtitle *Network & service connections*).
2. Review top to bottom:

| Block | What it shows |
|---|---|
| **Generate signage enrollment token** | **Generate token** — short-lived token to paste into leaf device setup (used for **signage and mobile camera** VPN onboarding even though the card title says signage) |
| **VPN Mesh** status | **VPN Mesh Active** (Tailscale/mesh IP, Matrix Group when present, peers, MagicDNS) · or **VPN Not Connected to EyeNet** + **Enroll Now** · or other Tailscale / unavailable states |
| **Mesh Peers** | Other nodes on the mesh (hostname `.eyenet-vpn.local`, IP, Online/Offline) when enrolled — **Refresh** |
| **Discovery Service Status** | **Connected - N services discovered** (or discovering / failed) |
| **Discovered Services** | Table: **Service**, **Status**, **URL**, **Version**, **VPN IP** |

3. On LAN: confirm Discovery is connected and expected services appear.
4. For remote: confirm **VPN Mesh Active** before relying on off-site access or remote leaf apps.

### What good looks like (Network)

- Discovery connected; services listed  
- When remote is required: **VPN Mesh Active** with a mesh IP  
- Token mint succeeds when you need to onboard a phone or player  

---

## B. Enroll the platform (software installation)

The Windows EyeNet PC is the primary mesh member.

### Automatic (typical after bootstrap)

After a successful licence bootstrap, the node may enroll once against EyeNet VPN using the installation’s application key / installation UUID (`tag:platform`). Open **Network** later to confirm **VPN Mesh Active**.

### Manual — Enroll Now

1. Home → **Network**.
2. If status is not Active, read any on-screen OS guide (Windows may mention installing Tailscale via winget). Prefer joining **EyeNet** (`vpn.eyenet-vision.com`) — do not replace an unrelated mesh blindly; follow **Join EyeNet without logging out** if another Tailscale network is already present.
3. Tap **Enroll Now**.
4. Wait for success (**Enrolled!** / status moves to **VPN Mesh Active**).
5. Confirm **Mesh Peers** / MagicDNS as shown.

If automatic key generation fails, the UI may show **⚠ Automatic key generation failed** and point you to Authority admin enrollment — contact your distributor.

### What good looks like (platform)

- **VPN Mesh Active** with a mesh IP  
- Discovery still healthy; services may also show a **VPN IP** column when applicable  

---

## C. Enrollment tokens (mobile camera & digital signage)

Leaf apps join the **same EyeNet VPN** by redeeming a token minted on this installation’s Network screen.

1. Confirm the **platform** is on the mesh (**VPN Mesh Active**) when the device will be off-LAN.
2. On **Network**, open **Generate signage enrollment token** → **Generate token**.
3. Copy the token immediately. UI copy: valid about **5 minutes**, treat as one-time — mint again if setup is delayed or fails.
4. On the **device**:
   - **Mobile camera:** enable **Join the VPN mesh (enrollment token)** → paste token → **Join VPN Mesh** / continue setup (see [Cameras](./cameras-and-detection.md)).
   - **Signage player:** enable **Join the VPN mesh (enrollment token)** → paste token (Authority URL usually defaults to the EyeNet Authority) → **Connect** (see [Digital signage](./digital-signage.md)).

![Mobile camera Join the VPN mesh (enrollment token) screen](./images/mobile-vpn-enrollment.png)

Mobile camera: paste the token, then **Join VPN Mesh**. The same Network token flow is used for signage; the player UI labels differ slightly (see Digital signage).

5. Confirm the device appears where expected (**Cameras** or Signage → **Devices**) and can reach Discovery over the mesh.

**LAN reminder:** leave the VPN switch **off** on the device and use Backend IP + port `8006` when phone/player and PC share a working local network — no token required.

### What good looks like (leaf VPN)

- Token mints without *Mint failed*  
- Device reports joined / connected to the platform  
- Camera or signage device shows online on the platform UI  

---

## D. Multi-site reporting (Matrix)

**EyeNet Matrix** aggregates reports across member installations over **EyeNet VPN** (summary, presence, gate/entrance activity, camera events, demographics, logs). It is a multi-installation product layer — **not** a tile on every single-site home screen.

If your organisation runs Matrix:

- Member installs remain independent (own cameras, users, media)
- Aggregated dashboards and central directory live on the Matrix side
- Unreachable members can still return partial results (degraded mode)
- Network may show a **Matrix Group** id when this install is enrolled in a group

Ask your distributor whether your **licence** includes Matrix membership and how to open the Matrix dashboard for your group. Single-site remote access (platform + mobile camera + signage on EyeNet VPN) does not require Matrix.

---

## Recommended order

1. Finish local install and confirm Discovery on **Network**.  
2. Enroll the **platform** in EyeNet VPN (**Enroll Now** / auto after licence bootstrap) when remote access is needed.  
3. On LAN, connect phones/players with IP + `8006`.  
4. Off-LAN, **Generate token** → paste into mobile camera or signage **Join the VPN mesh** setup.  
5. If multi-site reporting is licensed, confirm Matrix membership with your distributor.

---

## Common issues

- **VPN Not Connected / Unavailable** — Tailscale/EyeNet client missing or enroll failed; use **Enroll Now** or distributor support  
- **Tailscale is on another network** — follow **Join EyeNet without logging out** (userspace path) rather than logging out of an existing mesh without guidance  
- **Mint failed** — Authority / admin token not configured on the gateway for this install; contact distributor  
- **Enrollment token failed on phone/player** — expired or delayed paste; mint a new token and retry immediately  
- **Device never appears** — platform not on mesh, wrong LAN IP, guest Wi‑Fi isolation, or Discovery unhealthy  
- **Expected Matrix dashboards on Home** — Matrix is separate; this Network page manages **this** install’s mesh and Discovery  

---

## Related

- [Cameras and detection](./cameras-and-detection.md) — mobile camera LAN + VPN setup  
- [Digital signage](./digital-signage.md) — player Backend Setup LAN + VPN  
- [Hardware and Docker requirements](./hardware.md)  
- [Entrances and activity](./entrances-and-activity.md)  
- Product overview: [`eyenet-features.md`](../../product/features/eyenet-features.md) (Matrix, remote VPN)
