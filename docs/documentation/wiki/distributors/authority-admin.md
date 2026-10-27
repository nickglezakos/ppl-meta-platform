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
title: Authority admin shell
audience: distributor
nav_order: 20
---

# Authority Admin Shell

Authority operators use a single mobile-first app at `/admin`. On a wide browser the shell centres at up to **880px** with the same bottom tabs (not a separate desktop chrome). A cyan ring in a figure is a marker for that control, not a highlight in the app. Emails and names such as `distributor@example.com` are examples.

Wiki figures: phone captures show below ~900px viewport width; wide captures show on larger screens.

## Entry

| URL | Result |
|---|---|
| `https://authority.eyenet-vision.com/admin` | Sign-in and workspace |
| `https://authority.eyenet-vision.com/admin/console` | **307** redirect to `/admin` |
| `https://authority.eyenet-vision.com/` | JSON service descriptor (not the UI) |

![Full Sign in screen on Authority — phone. Sign in is marked.](./images/mobile-admin-sign-in.png)

![Full Sign in screen on Authority — wide screen. Sign in is marked.](./images/admin-sign-in-wide.png)

**Email** and **Password** are required. **Show password** reveals the field. **Sign in** opens the workspace. **Bootstrap admin** is only for first-time platform setup — distributors do not use it day to day.

Accept-invitation (from an email link or `?invitation_token=`) is covered under [Invite people](./invite-people.md) and in the [owner wiki](../owners-admins/index.md).

---

## Bottom tabs

| Tab | Who sees it | Purpose |
|---|---|---|
| **Home** | All roles | Pulse metrics, recent activity, primary CTA |
| **People** | platform_admin, distributor, reseller, support | Search and invite users in scope |
| **Licences** | platform_admin, distributor, reseller, owner | Issue/assign (operators) or review installations (owners) |
| **Me** | All roles | Account, logout; Tools for platform_admin / support |

Owners do not see **People**. Support does not see **Licences**.

![Full Home screen as distributor — phone. Pulse cards, Invite or assign, Recent, and four bottom tabs.](./images/mobile-admin-home.png)

![Full Home screen as distributor — wide screen. Pulse cards in one row; Invite or assign and Recent.](./images/admin-home-wide.png)

As a **distributor**, Home shows **Resellers**, **Owners**, **Licences**, and **Pending invites**. The primary CTA is **Invite or assign** (opens People and the Invite sheet). **Recent** lists recent assignments in scope.

![Full Home screen as owner — phone. Bottom tabs are Home · Licences · Me only (no People).](./images/mobile-admin-tabs-owner.png)

![Full Home screen as owner — wide screen. Bottom tabs are Home · Licences · Me only (no People).](./images/admin-tabs-owner-wide.png)

An **owner** sees three tabs. Their CTA is **My installations**. Pulse cards are Installations / Active / Grace / Suspended.

---

## People

![Full People screen as distributor — phone. The cyan ring marks the Invite (+) FAB.](./images/mobile-admin-people.png)

![Full People screen as distributor — wide screen. The cyan ring marks the Invite (+) FAB.](./images/admin-people-wide.png)

**People** subtitle is *Invite and manage users in scope*. Search placeholder is **Search name or email**. Segments are **All**, **Pending**, **Active**, **Suspended**. Rows show name/email with status and role pills. Empty state: *No people in scope.*

### Invite sheet

![Full People screen with Invite sheet open — phone. Role owner and Send invite are shown.](./images/mobile-admin-invite-sheet.png)

![Full People screen with Invite sheet open — wide screen. Role owner and Send invite are shown.](./images/admin-invite-sheet-wide.png)

FAB **+** (`Invite`) opens the **Invite** sheet. For a distributor inviting an owner: **Role**, **Email**, optional **Reseller UUID**, **Expires (days)** (default 7), then **Send invite**. Platform admins also see Distributor UUID fields. Full invite matrix: [Invite people](./invite-people.md).

### Person detail

![Full Person detail screen — phone. Back link is ← People; linked licences are listed below.](./images/mobile-admin-person-detail.png)

![Full Person detail screen — wide screen. Back link is ← People; linked licences are listed below.](./images/admin-person-detail-wide.png)

Opened from a People row. Shows **Role**, **User UUID**, **Distributor**, **Reseller**, lifecycle actions (e.g. **Suspend**), and linked **Licences**.

---

## Licences

![Full Licences screen as distributor — phone. The cyan ring marks the Issue licence (+) FAB.](./images/mobile-admin-licences.png)

![Full Licences screen as distributor — wide screen. The cyan ring marks the Issue licence (+) FAB.](./images/admin-licences-wide.png)

Operators see subtitle *Issue, assign, and review*. Search is **Search licence or owner**. Segments: **All**, **Active**, **Pending**, **Suspended**. Empty: *No licences in scope.* Owners see *Your installations* and no FAB.

### Issue / assign wizard

![Full Licences screen with Issue / assign sheet open — phone. Mode is Assign existing.](./images/mobile-admin-issue-sheet.png)

![Full Licences screen with Issue / assign sheet open — wide screen. Mode is Assign existing.](./images/admin-issue-sheet-wide.png)

FAB **+** (`Issue licence`) opens **Issue / assign**. Steps: **1 — Person** (Owner email), **2 — Licence** (Mode **Issue new** or **Assign existing**), **3 — Confirm**. Channel roles (distributor / reseller) use **Assign existing**; only **platform_admin** can complete **Issue new**. Details: [Issue and assign licences](./issue-licences.md).

### Licence detail

![Full Licence detail screen — phone. Application key is marked; status is pending_activation.](./images/mobile-admin-licence-detail.png)

![Full Licence detail screen — wide screen. Application key is marked; status is pending_activation.](./images/admin-licence-detail-wide.png)

Opened from a Licences row. Shows **Status**, **Entitlement**, **Installation**, **Application key** (`lic_…`), and **Matrix**. Copy the key for the customer’s Windows `/bootstrap` with the **same** email. Advanced **More** edit and Suspend/Activate are **platform_admin** only.

---

## Sheets and chrome

- **Invite** sheet — FAB on People
- **Issue / assign** wizard — FAB on Licences
- Overflow menu (hamburger) — refresh session, change password, logout

![Full Authority shell with overflow Menu open — phone. Refresh session, Change password, and Logout.](./images/mobile-admin-overflow.png)

![Full Authority shell with overflow Menu open — wide screen. Refresh session, Change password, and Logout.](./images/admin-overflow-wide.png)

The top-bar hamburger opens **Menu**: **Refresh session**, **Change password**, **Logout**. The same account actions also appear on **Me**.

---

## Me

![Full Me screen as distributor — phone. Email, Role, Change password, Refresh session, Logout.](./images/mobile-admin-me.png)

![Full Me screen as distributor — wide screen. Email, Role, Change password, Refresh session, Logout.](./images/admin-me-wide.png)

**Me** subtitle is *Account and tools*. Distributors and resellers see the account card only (no Tools section).

### Me → Tools (advanced)

Visible to **platform_admin** and **support** only. VPN mesh and audit are platform_admin. Emergency reinstate is available to support as well. These are not first-step distributor tasks.

![Full Me screen as platform_admin with Tools open — phone. VPN mesh, Audit, and Emergency reinstate.](./images/mobile-admin-me-tools.png)

![Full Me screen as platform_admin with Tools open — wide screen. VPN mesh, Audit, and Emergency reinstate.](./images/admin-me-tools-wide.png)

**Tools** includes **VPN mesh** (Enroll installation), **Audit** (Load audit), and **Emergency reinstate**.

---

## Deep links

Prefer `tab=` (legacy `view=` aliases still remap to Home or Licences):

| Query | Opens |
|---|---|
| `?tab=home` | Home |
| `?tab=people` | People |
| `?tab=licences` | Licences |
| `?tab=me` | Me |
| `?tab=person&person=<user_uuid>` | Person detail |
| `?tab=licence&licence=<entitlement_uuid>` | Licence detail |
| `?invitation_token=…` | Accept-invitation card (logged out) |

---

## Related pages

- [Invite people](./invite-people.md)
- [Issue and assign licences](./issue-licences.md)
- [Distributor wiki home](./index.md)
