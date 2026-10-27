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
title: Matrix
audience: product
nav_order: 70
---

# Matrix

Multi-site control over secure VPN.

- Aggregated reports across member installations: Summary, Presence, Gate Activity, Camera Events, Demographics, Logs
- Matrix groups and installation membership with multi-install licensing
- Centralised user directory and JWT-based SSO with RBAC
- Degraded mode: partial results when some sites are unreachable
- Report caching and time-range filtering for historical analysis

**Typical users:** Multi-site operators, fleets, organisations needing one dashboard across locations

Remote reach uses **EyeNet VPN** (licence-backed mesh). Leaf apps such as mobile camera and signage can enroll when off-LAN.

<div class="wiki-gallery" markdown="1">

![VPN enrollment on EyeNet Mobile Camera.](../owners-admins/images/mobile-vpn-enrollment.png)

![Signage backend setup with optional VPN mesh enrollment.](../owners-admins/images/mobile-signage-backend-setup-vpn.png)

</div>

Day-to-day setup: [Remote access and multi-site](../owners-admins/multi-site-and-remote.md) · Back to [What is EyeNet](./index.md)
