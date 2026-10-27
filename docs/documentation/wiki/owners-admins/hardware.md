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
title: Hardware and Docker requirements
audience: owner-admin
nav_order: 10
---

# Hardware And Docker Requirements

## Why this matters

EyeNet runs several services on the host. Two of them dominate RAM use:

- **Vision** — detects people in live camera frames and recorded video (faces, bodies, presence of people in the scene). It is the computer-vision engine behind Cameras, Presence, Analytics, and related alerts.
- **Vmeta** — runs the ML steps that turn those detections into useful identity and demographics (for example age/gender cues and matching a face to a known individual). Cameras, Individual Groups, and many searches depend on it.

Vision and Vmeta are memory-heavy. Unbounded containers on an undersized host cause OOM and unstable updates. Compose files pin per-service memory limits inside the 12 GB WSL pool (or the equivalent Docker Engine budget on Linux).

## Host

Supported install paths (same GHCR images and host **EyeNet tray**):

- **Windows** — Windows 10/11 amd64 (not ARM), physical PC or **Hyper-V** VM; WSL2 distro **`eyenet`** with **Docker Engine CE** (installed by `install-eyenet-wsl.bat`); EyeNet tray in the system tray. Docker Desktop is not required.
- **Linux** — Ubuntu 24.04 amd64 (or compatible), Docker Engine, EyeNet tray in the desktop tray / AppIndicator

Common requirements:

- **≥16 GB** physical RAM
- ≥12 GB free disk

## Docker / WSL budget

On Windows, EyeNet writes:

```
[wsl2]
memory=12GB
processors=6
swap=2GB
localhostForwarding=true
```

The installer fails if host RAM is below 16 GB or WSL memory is below 12 GB.
