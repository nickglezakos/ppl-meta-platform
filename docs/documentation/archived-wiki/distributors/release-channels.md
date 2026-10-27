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
title: Release channels and pilot tagging
audience: distributor
archived: true
archived_on: "2026-10-04"
archived_reason: "Not published online — Authority /admin has no channel tagging UI (KI-003). Restore to docs/documentation/wiki/distributors/ when product ships controls."
---

# Release Channels And Pilot Tagging

> **Archived (2026-10-04).** This page is **not** part of the published distributor wiki. See [KI-003](../../../issues/known%20issues/known%20issues.md).

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

## UI gap (laconic admin)

The rebuilt `/admin` shell covers invite, issue/assign, and licence review. It does **not** yet expose controls to tag a licence as `sandbox` / `pilot` / `stable` or to promote a release through soak.

Those steps remain **policy and control-plane requirements**. Do not invent click-paths in People or Licences for channel tagging until the product ships them. Until then, follow the installation lifecycle CI/CD policy and operator runbooks for eligibility and promotion audit.

## Pilot soak (summary)

- At least **2** distinct pilot installations (not sandbox, not developer machines)
- **72 hours** after last healthy report; **7 days** if vision/vmeta images changed
- Any failure/rollback or ≥50% cohort failure blocks stable promotion
- Stable promotion requires an Authority audit record

Full rules live in the installation lifecycle CI/CD policy.

## Related pages

- [Issue and assign licences](./issue-licences.md)
- [Distributor wiki home](./index.md)
