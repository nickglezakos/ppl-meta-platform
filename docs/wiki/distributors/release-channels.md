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
title: Release channels and pilot tagging
audience: distributor
---

# Release Channels And Pilot Tagging

## Channels

| Channel | Purpose |
|---|---|
| `sandbox` | Non-production test installations |
| `pilot` | Selected real licences for early updates |
| `stable` | Default for remaining eligible installations |

Default for new entitlements is `stable`.

## Selective updates

1. Publish platform images for a `VERSION` to GHCR.
2. Mark the release eligible for `sandbox` / `pilot` only in Authority.
3. After sandbox evidence, approve pilot cohort.
4. Enforce pilot soak rules before promoting to `stable`.
5. Do not auto-promote when the soak clock expires.

## Pilot soak (summary)

- At least **2** distinct pilot installations (not sandbox, not developer machines)
- **72 hours** after last healthy report; **7 days** if vision/vmeta images changed
- Any failure/rollback or ≥50% cohort failure blocks stable promotion
- Stable promotion requires an Authority audit record

Full rules live in the installation lifecycle CI/CD policy.
