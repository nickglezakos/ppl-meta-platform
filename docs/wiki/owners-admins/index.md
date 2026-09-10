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
title: Owner and platform admin wiki home
audience: owner-admin
---

# EyeNet Owner And Platform Admin Wiki

This wiki is for **platform owners** and **platform admins** on a customer installation. It does not cover distributor channel administration.

## First install

1. Windows amd64 PC with **≥16 GB RAM**
2. Install Docker Desktop (WSL2); EyeNet configures **12 GB** WSL memory
3. Run the Windows installer and pull pinned GHCR images
4. Open the app and complete **bootstrap** with the approved owner email and licence / application key

## Updates

- Most installations receive **stable** releases only
- Some installations may be on **pilot** and see updates earlier
- After an update, verify login, Authority status, and basic media/camera paths

You do not change another customer's release channel from this wiki.
