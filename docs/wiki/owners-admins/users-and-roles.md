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
title: Users and roles
audience: owner-admin
nav_order: 100
---

# Users And Roles

Manage who can sign in to this **local** EyeNet installation and what they can do. Local accounts and roles are separate from Authority invitations (distributor wiki).

**Where:** Home → avatar / profile menu → **Users** (`/users`) and **Roles** (`/roles`)

There is no Users/Roles tile on the home grid. **Roles** appears in the menu only if your account can manage roles (`auth.roles.*`).

---

## Prerequisites

- Logged in as **owner** or **admin** (or a custom role with account / role capabilities)
- Bootstrap already created the first local **owner** account
- Authority password ≠ local app password — this page is only the local install

---

## How permissions work

| Concept | Meaning |
|---|---|
| **User** | Local login (username, email, password) |
| **Role** | Named set of permissions — system: `owner`, `admin`, `user`, plus **custom** roles you create |
| **Capability** | Fine-grained key (for example `cameras.view`, `media.manage`) stored on a **role** |

Users inherit capabilities **through roles**. You do not permanently attach a free-floating capability list to a person without a role.

**Practical admin path:** create or reuse a role → set its capabilities → **Assign** that role to the user.

### System roles (defaults)

| Role | Typical use | Notable defaults |
|---|---|---|
| **owner** | Installation owner | Full accounts (incl. delete), create/update/delete roles, system/licensing/recovery, cameras/media manage |
| **admin** | Day-to-day local admin | Create/update users (not delete by default), assign/unassign roles, assign/unassign capabilities, cameras/media manage — **cannot** create roles by default |
| **user** | Standard operator | Session + profile + `cameras.view`, `media.view`, `analytics.view`, `workflows.use` — no account or role admin |

There is no separate **operator** system role on this install. Build operator-style access with a **custom role** (examples below).

### Capability namespaces (UI grouping)

On role detail / user profile, capabilities are grouped roughly as:

**Auth** · **Users** · **Cameras** · **Media** · **Analytics** · **Workflows** · **Operations** · **System** · **Vision**

Keys appear as monospace names (for example `cameras.manage`). Important defaults:

| Area | Common keys |
|---|---|
| Session / profile | `auth.session.use`, `users.profile.read`, `users.profile.update`, `users.password.change_self` |
| Accounts | `users.accounts.read` · `create` · `update` · `disable` · `delete` |
| Roles / caps | `auth.roles.read` · `create` · `update` · `delete` · `assign` · `unassign` · `auth.capabilities.*` |
| Cameras | `cameras.view`, `cameras.manage`, plus finer `cameras:view`, `cameras:detect`, `cameras:stream:*`, `cameras:record:*`, … |
| Media | `media.view`, `media.manage`, `media:view` |
| Analytics | `analytics.view` |
| Workflows / ops | `workflows.use`, `operations.execute` |
| System (owner) | `system.installation.manage`, `system.licensing.manage`, `system.recovery.manage` |

**Note:** There are **no** separate capability keys named `presence.*`, `signage.*`, `gate.*`, `network.*`, or `triggers.*`. Gate / Presence / Signage / Vradar screens are controlled mainly by **login + broader cameras / media / analytics / workflows** rights, and by **not** giving account/role/system admin keys to desk operators. Shape custom roles accordingly (section D).

---

## A. Create and manage users

1. Menu → **Users**.
2. If you lack `users.accounts.read`, you see **Access Denied** (*You need the "users.accounts.read" capability to view users.*).
3. List shows username, email, role chips, capability count, **Verified** / **Unverified**. Filter chips: **All** + each role name.

### Create a user

1. Tap the **+** / person-add FAB.
2. Dialog **Create User**: **Username**, **Email**, **Password**.
3. **Create** (or **Cancel**).
4. Snackbar **User created** (or **Error: …** / licence *Maximum users* / *Already exists*).

New users often have **no roles** until you assign one — they may not see useful home tiles until **Manage Roles**.

### Open / administer a user

1. Tap a user row → **User Profile** (`/profile?userId=…`).
2. **Assign** → dialog **Manage Roles**: tick roles (**System role** / **Custom role**) → **Apply**.
3. If you are an **admin** (or equivalent): capability switches on the profile can refine keys; **Set Password** (**New Password**, optional **Send password via email**).
4. Delete from the users list (if you have `users.accounts.delete`): **Delete {username}?** → **Delete**.

Cannot remove the last **owner** role from the installation (*Cannot remove the last owner role*).

### What good looks like (users)

- User appears in the list; after role assign, role chips show  
- User can log in with the local password  
- Restricted screens stay hidden or blocked without matching capabilities  

---

## B. Create and manage roles

1. Menu → **Roles** (requires role-management capability).
2. App bar **Roles**; **+** (**Create Role**) if you have `auth.roles.create` (default: **owner** only).

### Create a custom role

1. Tap **+** → dialog **Create Role** → **Role name** → **Create**.
2. Open the new role → **Role: {name}** → section **Capabilities**.
3. Review keys by namespace. Remove with **Remove** if you have `auth.capabilities.unassign`.
4. To **add** capabilities in the UI, the usual path is: assign this role to a user → open that user’s profile → use capability **switches** (admin) so the keys land on the role(s) that user currently has — see caution below.

System roles show **System role (immutable)** — you cannot rename or delete `owner` / `admin` / `user`. Custom roles can be renamed / deleted (**Migrate capabilities to** / **Discard capabilities** when deleting).

### Caution — capability switches on a user profile

Toggling a capability on **User Profile** updates the **roles that user currently has** (shared role definitions), not a private per-user override.

- Prefer a **dedicated custom role** per job (gate desk, presence desk, signage).
- While shaping that role, avoid leaving the person on shared `user` / `admin` if a toggle would change those system roles for everyone.
- Safer sequence: create custom role → assign **only** that custom role to a test user → toggle capabilities on → then assign the finished role to real operators.

### What good looks like (roles)

- Custom role appears as **Custom role**  
- Capability list matches the job  
- Operators get the custom role via **Manage Roles**, not a copy of full **admin**  

---

## C. Recommended admin workflow

1. **Owner** (if needed): **Roles** → **Create Role** for each job (`gate-ops`, `presence-desk`, `signage-editor`).  
2. Shape capabilities on each custom role (profile toggles on a throwaway user that only has that role, or remove extras from role detail).  
3. **Admin** or owner: **Users** → create accounts → **Manage Roles** → assign the matching custom role (optionally also `user` only if you accept default view rights).  
4. Have the operator log in and confirm the target screens; withhold `users.accounts.*`, `auth.roles.*`, and `system.*` from desk roles.

---

## D. Example use cases (custom roles + capabilities)

These examples assume an **admin** (or owner) creates/assigns roles. Map each job to cameras / media / analytics keys — Presence, Signage, and entrances do not have their own capability names.

### Example 1 — Gate / entrance activity operator

**Job:** Watch door cameras, run instant detection awareness, review Analytics for that entrance, optionally check Automation results — without managing users or the install.

**Create role:** e.g. `gate-ops`

| Grant (typical) | Why |
|---|---|
| `auth.session.use`, `users.profile.read`, `users.profile.update`, `users.password.change_self` | Sign in and manage own profile |
| `cameras.view` (and if needed `cameras:view`, `cameras:detect`, `cameras:stream:view`, `cameras:connect`) | See entrance cameras / live view |
| `analytics.view` | [Analytics](./analytics-and-reports.md) for traffic / demographics |
| `media.view` | Review recordings / collections when needed |
| `workflows.use` | Monitoring / workflow surfaces if used on site |

| Do **not** grant | Why |
|---|---|
| `cameras.manage`, `users.accounts.*`, `auth.roles.*`, `system.*` | No camera admin, no user admin, no install control |
| Full `admin` role | Too broad for a gate desk |

**Assign:** Users → operator → **Manage Roles** → tick `gate-ops` → **Apply**.

**Ops follow:** [Entrances and activity](./entrances-and-activity.md), [Cameras](./cameras-and-detection.md), [Vradar](./alerts-and-automation.md), [Analytics](./analytics-and-reports.md).

---

### Example 2 — Presence / attendance desk

**Job:** Run Presence check-in (**Video Match**, QR), reserve the Actions camera and rely on Triggers for video readiness only if policy allows, without becoming a platform admin.

**Create role:** e.g. `presence-desk`

| Grant (typical) | Why |
|---|---|
| Session + profile keys (as above) | Login |
| `cameras.view` (+ stream/detect keys if Video Match needs them) | Camera-only presence against the reserved camera |
| `media.view` | Related media review if required |
| `analytics.view` | Optional Presence / people analytics review |

| Do **not** grant | Why |
|---|---|
| `users.accounts.*`, `auth.roles.create` / `delete`, `system.*` | Desk must not manage the whole install |
| `cameras.manage` / `media.manage` | Unless this person also configures cameras/collections |

**Assign:** `presence-desk` via **Manage Roles**.

**Ops follow:** [Presence and attendance](./presence-attendance.md) (Settings reserve camera/group; Actions → **Video Match** / **Render QR**). For entrance + Presence together, see [Entrances use case 2](./entrances-and-activity.md).

There is no `presence.*` capability — access is “logged-in user with camera/media rights,” so keep the role narrow by **omission** of admin keys.

---

### Example 3 — Digital signage editor

**Job:** Upload/organise playlist source media, manage Signage playlists/devices/playback — not user admin or network/VPN.

**Create role:** e.g. `signage-editor`

| Grant (typical) | Why |
|---|---|
| Session + profile keys | Login |
| `media.view`, `media.manage` | Upload, collections, playlist source videos |
| `analytics.view` | Optional; not required for playlists |
| `cameras.view` | Only if this person also wires Vradar → Digital Signage actions |

| Do **not** grant | Why |
|---|---|
| `users.accounts.*`, `auth.roles.*`, `system.*` | No account / licence / recovery control |
| `cameras.manage` | Unless they also own camera setup |

**Assign:** `signage-editor` via **Manage Roles**.

**Ops follow:** [Media and collections](./media-management.md), [Digital signage](./digital-signage.md). Player VPN onboarding stays with someone who has Network access (often admin/owner) — [Remote access](./multi-site-and-remote.md).

There is no `signage.*` capability — media manage is the main lever; withhold broader admin roles.

---

### Quick comparison

| Role name (example) | Focus screens | Key grants | Key withholds |
|---|---|---|---|
| `gate-ops` | Cameras, Analytics, Automation (use) | `cameras.view`, `analytics.view`, `media.view` | accounts, roles, system, often `*.manage` |
| `presence-desk` | Presence Actions / Sessions | `cameras.view`, session/profile | accounts, roles, system |
| `signage-editor` | Collections / Upload, Signage | `media.view`, `media.manage` | accounts, roles, system |

One person can hold **multiple** custom roles (for example `gate-ops` + `presence-desk`) via **Manage Roles**.

---

## Common issues

- **Access Denied on Users/Roles** — missing `users.accounts.read` or `auth.roles.read`; use an owner/admin account  
- **New user sees almost nothing** — no role assigned after **Create User**; open **Manage Roles**  
- **Cannot create custom role** — default **admin** lacks `auth.roles.create`; use **owner** or grant that capability carefully  
- **Toggling a cap broke other users** — the key was on a shared system role; use dedicated custom roles  
- **Licence limit** — *Maximum users* from licensing; contact distributor  
- **Expected presence/signage permission chips** — not in the catalog; use media/cameras/analytics combinations above  

---

## Related

- [Entrances and activity](./entrances-and-activity.md)
- [Presence and attendance](./presence-attendance.md)
- [Digital signage](./digital-signage.md)
- [Cameras and detection](./cameras-and-detection.md)
- [Analytics and reports](./analytics-and-reports.md)
- Distributor wiki — Authority owner invite / licences (not local `/users`)
