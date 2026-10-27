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
title: Invite people on Authority
audience: distributor
nav_order: 30
---

# Invite People

Use **People → +** to open the invite sheet. Invitations create Authority accounts. They do **not** create the local Node user on a customer install.

Wiki figures: phone captures show below ~900px viewport width; wide captures show on larger screens. A cyan ring is a figure marker, not a highlight in the app. Example emails are not live accounts.

Shell overview (tabs, overflow, Me): [Authority admin shell](./authority-admin.md).

---

## Who can invite whom

| Actor | Can invite | Invite FAB |
|---|---|---|
| platform_admin | distributor, reseller, owner, support | Yes |
| distributor | reseller, owner | Yes |
| reseller | owner | Yes |
| support / owner | — | Hidden |

Platform admins may set **Distributor UUID** / **Reseller UUID** when inviting into the hierarchy. Distributors may set a **Reseller UUID** when inviting an **owner**. Resellers only invite **owner** (no scope UUID fields).

---

## Open the invite sheet

![Full People screen as distributor — phone. The cyan ring marks the Invite (+) FAB.](./images/mobile-admin-people.png)

![Full People screen as distributor — wide screen. The cyan ring marks the Invite (+) FAB.](./images/admin-people-wide.png)

1. Sign in at `/admin`.
2. Open **People**.
3. Tap **+** (`Invite`).

Empty list reads *No people in scope.* Search is **Search name or email**. Segments: **All**, **Pending**, **Active**, **Suspended**.

---

## Invite an owner (distributor)

![Full People screen with Invite sheet open — phone. Role owner and Send invite are shown.](./images/mobile-admin-invite-sheet.png)

![Full People screen with Invite sheet open — wide screen. Role owner and Send invite are shown.](./images/admin-invite-sheet-wide.png)

Sheet title **Invite**. Fields for a distributor inviting an owner:

| Field | Notes |
|---|---|
| **Role** | `reseller` or `owner` (distributor options) |
| **Email** | Invitee address |
| **Reseller UUID** | Optional when role is **owner** |
| **Expires (days)** | Default `7` |
| **Send invite** / **Cancel** | Submit or dismiss |

### Invite a reseller (distributor)

![Full Invite sheet for reseller role — phone. No Reseller UUID field.](./images/mobile-admin-invite-reseller.png)

![Full Invite sheet for reseller role — wide screen. No Reseller UUID field.](./images/admin-invite-reseller-wide.png)

Role **reseller** shows **Email** and **Expires (days)** only (no Reseller UUID).

### Invite as reseller (owner only)

![Full Invite sheet as reseller actor — phone. Role list is owner only.](./images/mobile-admin-invite-as-reseller.png)

![Full Invite sheet as reseller actor — wide screen. Role list is owner only.](./images/admin-invite-as-reseller-wide.png)

A **reseller** actor can invite **owner** only. No distributor/reseller UUID fields.

### Invite as platform_admin (scope UUIDs)

![Full Invite sheet as platform_admin — phone. Distributor UUID and optional Reseller UUID for owner.](./images/mobile-admin-invite-platform.png)

![Full Invite sheet as platform_admin — wide screen. Distributor UUID and optional Reseller UUID for owner.](./images/admin-invite-platform-wide.png)

**platform_admin** role options: distributor, reseller, owner, support. For **owner** (and distributor / reseller), **Distributor UUID** appears (*Required for distributor / owner*). **Reseller UUID** is optional when inviting an owner.

---

## First owner invite (end-to-end)

1. Open `/admin` and sign in as distributor, reseller, or platform_admin.
2. Go to **People** → **+**.
3. Choose role **owner**, enter the customer email, set expiry if needed, **Send invite**.
4. Confirm the row under **Pending** until they accept.
5. The invitee opens the email link (or pastes the token) on `/admin`, sets an **Authority** password, and accepts.
6. Accepting an **owner** invite auto-creates an entitlement (`lic_…` application key, pending activation, no installation UUID yet).
7. Copy the `lic_…` key from **Licences** (or person/licence detail) and give it to the customer for Windows `/bootstrap` with the **same** email.

### Pending invites

![Full People screen on Pending — phone. Pending owner row is marked.](./images/mobile-admin-invite-pending.png)

![Full People screen on Pending — wide screen. Pending owner row is marked.](./images/admin-invite-pending-wide.png)

After **Send invite**, the person shows status **pending** until accept. Use the **Pending** segment to filter.

### Accept invitation

![Full Accept invitation screen — phone. Accept is marked.](./images/mobile-admin-accept-invitation.png)

![Full Accept invitation screen — wide screen. Accept is marked.](./images/admin-accept-invitation-wide.png)

Logged-out card **Accept invitation**: **Token**, optional **Display name**, **Password** (*Set a password*), **Show password**, then **Accept** (or **Back** to Sign in). Deep link: `?invitation_token=…`.

Also shown on the owner wiki first-install page for the same form.

### Copy the application key

![Full Licence detail after owner accept — phone. Application key is marked; status pending_activation.](./images/mobile-admin-invite-licence-key.png)

![Full Licence detail after owner accept — wide screen. Application key is marked; status pending_activation.](./images/admin-invite-licence-key-wide.png)

Open **Licences** (or the person → linked licence). Status is typically **pending_activation** until the customer binds at `/bootstrap`. Copy **Application key** (`lic_…`). Installation stays empty until first activation.

---

## What accept does and does not do

| Does | Does not |
|---|---|
| Create the Authority user | Create the local EyeNet Node account |
| For owners: mint an entitlement / `lic_…` key | Bind the licence to a Windows installation |
| Set the Authority password | Set the local app password |

Local binding happens later on the customer PC at `/bootstrap` — see [First install](../owners-admins/index.md) / [Bootstrap](../owners-admins/bootstrap.md).

---

## Related pages

- [Issue and assign licences](./issue-licences.md)
- [Authority admin shell](./authority-admin.md)
- [First install](../owners-admins/index.md)
