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
title: Shared platform
audience: product
nav_order: 80
---

# Shared platform

Capabilities shared across Presence, Signage, Vradar, Gate, Sentinel, and Matrix.

| Capability | What it does |
|---|---|
| **Cameras** | Any IP, WiFi, phone, or NVR/VMS camera; live detection and recorded video |
| **Vision** | Face and body detection, cross-camera identity, demographics, people counts, routes, and dwell time |
| **Analytics** | Occupancy, time trends, demographics, and behaviour (peak hours, visit frequency, heatmaps) |
| **Automation (Vradar)** | Product view of triggers/actions on instant detection — demographics or known people → email, webhooks, alerts, or signage |
| **Access & licensing** | Roles and permissions, invitations, and installation licences |
| **Operations** | On-site recording and archives, system health, and remote access over VPN |

<div class="wiki-gallery" markdown="1">

![Cameras — desktop analytics and live streams.](../owners-admins/images/cameras-desktop-analytics.png)

![MVR Analytics — filters and report levels.](../owners-admins/images/mvr-analytics-bar.png)

![Analytics example report view.](../owners-admins/images/analytics-example.png)

</div>

## Operating modes

| Mode | Description | Used by |
|---|---|---|
| **Spot** | Close-range fixed areas (POS, displays) | Signage |
| **Gate** | Entrances, exits, corridors | Presence, Signage, Gate |
| **Area** | Rooms and wide spaces | Presence, Signage, Sentinel |
| **Goggles** | Wearable first-person cameras | Vradar |
| **Drone** | Aerial mobile coverage | Vradar |

Back to [What is EyeNet](./index.md)
