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
title: Issue and assign licences
audience: distributor
nav_order: 40
---

# Issue And Assign Licences

Use **Licences → +** (`Issue licence`) to open the **Issue / assign** wizard. Owners see Licences read-only (their installations); they do not get the FAB.

Wiki figures: phone captures show below ~900px viewport width; wide captures show on larger screens. A cyan ring is a figure marker, not a highlight in the app. Example emails and keys are not live credentials.

Shell overview: [Authority admin shell](./authority-admin.md). Owner invite path that auto-mints a licence: [Invite people](./invite-people.md).

---

## Open Licences

![Full Licences screen as distributor — phone. The cyan ring marks the Issue licence (+) FAB.](./images/mobile-admin-licences.png)

![Full Licences screen as distributor — wide screen. The cyan ring marks the Issue licence (+) FAB.](./images/admin-licences-wide.png)

Operators see subtitle *Issue, assign, and review*. Search is **Search licence or owner**. Segments: **All**, **Active**, **Pending**, **Suspended**. Empty: *No licences in scope.*

### Owner view (no FAB)

![Full Licences screen as owner — phone. Subtitle Your installations; no Issue FAB.](./images/mobile-admin-licence-owner-list.png)

![Full Licences screen as owner — wide screen. Subtitle Your installations; no Issue FAB.](./images/admin-licence-owner-list-wide.png)

Owners see *Your installations*, three bottom tabs (no People), and no **+**. They open a row to copy their `lic_…` key for `/bootstrap`.

### Pending filter

![Full Licences screen on Pending — phone. pending_activation row is marked.](./images/mobile-admin-licence-pending.png)

![Full Licences screen on Pending — wide screen. pending_activation row is marked.](./images/admin-licence-pending-wide.png)

Use **Pending** after an owner invite accept (or a new issue) to find entitlements still waiting for first activation.

---

## Issue vs assign

| Mode | Who can complete it | What it does |
|---|---|---|
| **Issue new** | platform_admin only | Creates a new entitlement, then best-effort assignment to the owner email |
| **Assign existing** | platform_admin, distributor, reseller | Links an existing entitlement UUID to an owner email |

The Mode dropdown shows both options to channel roles. Confirming **Issue new** as distributor/reseller fails with: *Only platform admin can issue new licences. Use Assign for channel roles.*

![Full Issue / assign sheet after Confirm as distributor — phone. Error toast is marked.](./images/mobile-admin-licence-issue-blocked.png)

![Full Issue / assign sheet after Confirm as distributor — wide screen. Error toast is marked.](./images/admin-licence-issue-blocked-wide.png)

---

## Assign existing (channel roles)

![Full Licences screen with Issue / assign open — phone. Mode Assign existing.](./images/mobile-admin-issue-sheet.png)

![Full Licences screen with Issue / assign open — wide screen. Mode Assign existing.](./images/admin-issue-sheet-wide.png)

Wizard title **Issue / assign**:

1. **Person** — **Owner email**
2. **Licence** — Mode **Assign existing** → **Entitlement UUID** (*Search entitlement*)
3. **Confirm** — summary *Assign existing entitlement to {email}.* → **Confirm** / **Cancel**

### Search entitlement

![Full Search record picker for entitlement — phone.](./images/mobile-admin-licence-picker.png)

![Full Search record picker for entitlement — wide screen.](./images/admin-licence-picker-wide.png)

Tap the Entitlement UUID field to open **Search record** (*Tap a result to fill the field.*). Choose a row or **Close**.

---

## Issue new (platform_admin)

![Full Issue / assign sheet in Issue new mode — phone. Tenant, installation, More, Confirm.](./images/mobile-admin-licence-issue.png)

![Full Issue / assign sheet in Issue new mode — wide screen. Tenant, installation, More, Confirm.](./images/admin-licence-issue-wide.png)

Mode **Issue new** fields:

| Field | Notes |
|---|---|
| **Tenant / licence name** | Display name for the entitlement |
| **Installation name** | Optional host label |
| **More** | **Application key** (*Auto if empty*), **Warning days**, **Offline grace days**, **Notes** |

Confirm summary: *Issue a new licence for {email}.* Prefer the [owner invite auto-entitlement](./invite-people.md) path for new customers; use **Issue** when a platform admin must mint outside that flow.

---

## Owner auto-entitlement (preferred)

When an **owner** accepts an invitation, Authority usually already created an entitlement:

1. Invite owner on **People** — [Invite people](./invite-people.md)
2. Owner accepts
3. Find the new licence on **Licences** (often **Pending**) and copy `application_key` (`lic_…`)

![Full Licence detail after owner accept — phone. Application key marked; pending_activation.](./images/mobile-admin-invite-licence-key.png)

![Full Licence detail after owner accept — wide screen. Application key marked; pending_activation.](./images/admin-invite-licence-key-wide.png)

---

## Licence detail

![Full Licence detail screen — phone. Application key marked; status pending_activation.](./images/mobile-admin-licence-detail.png)

![Full Licence detail screen — wide screen. Application key marked; status pending_activation.](./images/admin-licence-detail-wide.png)

Opened from a Licences row. Shows **Status**, **Entitlement**, **Installation**, **Application key**, **Matrix**. Installation stays empty until first Windows activation.

### platform_admin actions

![Full Licence detail as platform_admin — phone. Suspend marked; More edit open.](./images/mobile-admin-licence-detail-admin.png)

![Full Licence detail as platform_admin — wide screen. Suspend marked; More edit open.](./images/admin-licence-detail-admin-wide.png)

**platform_admin** gets **Suspend** / **Activate** and **More** (approved owner email, status, owner enabled, warning/grace days, tenant name, notes → **Update licence details**). Channel roles see read-only meta without those actions.

---

## Customer package

Give the owner:

- Approved owner email (exact match required at bootstrap)
- `application_key` starting with `lic_`

The key binds later on the Windows install; do not expect an installation UUID from Authority before first activation. Owner bootstrap: [First install](../owners-admins/index.md) / [Bootstrap](../owners-admins/bootstrap.md).

---

## Related pages

- [Invite people](./invite-people.md)
- [Authority admin shell](./authority-admin.md)
