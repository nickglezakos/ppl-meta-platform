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
title: Distributor wiki home
audience: distributor
---

# EyeNet Distributor Wiki

This wiki is for **distributors** and channel operators. It is separate from the owner / platform-admin wiki.

## What you manage

- Licence / entitlement issuance for owners
- Tagging selected licences as `sandbox` or `pilot` for selective updates
- Reading soak status before promoting a release to `stable`
- Partner guidance without exposing internal channel mechanics to end customers

## Software lifecycle this wiki references

- Platform version: **2.25.79**
- Install path: Windows amd64 + Docker Desktop + GHCR
- Update channels: `sandbox` → `pilot` → `stable`
- Pilot soak: minimum 2 pilot installations, 72 hours (7 days if vision/vmeta changed), promotion audit required

Publishing images to GHCR does **not** update customer installs. Authority channel eligibility decides who may pull.

## Related pages

- [Release channels and pilot tagging](./release-channels.md)
- Owner/admin wiki is published separately under `docs/wiki/owners-admins/`
