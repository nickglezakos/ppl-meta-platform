---
software_ref:
  platform_version: "2.25.79"
  policy_revision: "2026-09-10"
  channels_documented:
    - sandbox
    - pilot
    - stable
  install_path: "windows-docker-desktop-ghcr"
  host_ram_gb: 16
  wsl_memory_gb: 12
title: Hardware and Docker Desktop requirements
audience: owner-admin
---

# Hardware And Docker Desktop Requirements

## Host

- Windows 10/11 amd64 (not ARM)
- **≥16 GB** physical RAM
- ≥12 GB free disk
- Docker Desktop with WSL2 backend

## Docker / WSL budget

EyeNet expects:

```
[wsl2]
memory=12GB
processors=6
swap=2GB
```

The installer fails if host RAM is below 16 GB or WSL memory is below 12 GB.

## Why this matters

Vision and vmeta services are memory-heavy. Unbounded containers on an undersized host cause OOM and unstable updates. Compose files pin per-service memory limits inside the 12 GB WSL pool.
