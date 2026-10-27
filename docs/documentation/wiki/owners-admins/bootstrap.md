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
title: Bootstrap the installation
audience: owner-admin
nav_order: 25
---

# Bootstrap The Installation

Bootstrap binds this EyeNet host to your Authority licence and creates the first local **owner** account. You do it once, right after the Windows or Linux installer finishes.

**Where:** local app route `/bootstrap` (the app opens here automatically when bootstrap is still pending)

Authority password and local app password are separate. Bootstrap sets the **local** password for this machine only.

## Before you start

- Installer has finished (GHCR images pulled; **EyeNet tray** running)
- You accepted the Authority invitation for the **approved owner email**
- You have the `lic_…` application key from Authority **Licences** (or from your distributor)
- You will use that **same email** on `/bootstrap`

See [Licence key before first install](./index.md#licence-key-before-first-install) and [First install](./index.md#first-install).

## Open bootstrap

1. Start the stack from the **EyeNet tray** if services are not already up.
2. Open the EyeNet web app (installer / tray shortcut, or the host URL your distributor gave you).
3. If bootstrap is pending, the app routes you to **`/bootstrap`** instead of login.

You should see **Activate Your Installation** (app bar title **Create Account**).

## Activate the installation

Fill the form with the approved owner details and the licence key, then create the account.

| Field | What to enter |
|---|---|
| **Username** | Local username for this host (letters, numbers, underscore) |
| **Email** | Exact **approved owner email** from Authority |
| **Licence / Application Key** | The `lic_…` key for this installation |
| **Password** / **Confirm Password** | New **local** password for this machine (not the Authority password) |

Tap **Create Account**. On success the app continues to **Home**.

![Activate Your Installation on phone / tablet. Create Account is marked.](./images/mobile-bootstrap-activate.png)

![Activate Your Installation on a wide screen. Create Account is marked.](./images/bootstrap-activate-wide.png)

Names and the `lic_…` value in these figures are examples only.

## What bootstrap does

| Does | Does not |
|---|---|
| Create the first local EyeNet owner account | Change your Authority password |
| Bind this host to the Authority entitlement / installation | Invite other people on Authority |
| Let you into local **Home** as owner | Configure cameras, media, or automation |

After bootstrap, day-to-day sign-in uses the local email/password on this host. Manage the licence record itself in Authority.

## After bootstrap

1. Confirm you land on **Home** and can open **Cameras** or **Upload Media**.
2. Later visits use local **Sign In** (`/login`) with the same owner email and the local password you set at bootstrap.
3. Optional: open **Network** later for EyeNet VPN enroll when remote access is needed — see [Remote access and multi-site](./multi-site-and-remote.md).
4. Add local users under menu **Users** when others need access — see [User management](./users-and-roles.md).

### Sign in (later visits)

After bootstrap completes, the app no longer opens `/bootstrap`. Use **Sign In** with the local owner email and password. The installation UUID on the form is this host only — the password is not your Authority password.

![Sign In on phone / tablet. Sign In is marked.](./images/mobile-login.png)

![Sign In on a wide screen. Sign In is marked.](./images/login-wide.png)

### Home

After a successful bootstrap or sign-in you land on **Home**. Open each product area from its tile (for example **Cameras**, **Upload Media**, **Network**).

![Home on phone / tablet after login.](./images/mobile-home-screen.png)

![Home on a wide screen after login.](./images/home-screen-wide.png)

## If bootstrap fails

| Symptom | What to check |
|---|---|
| App never opens `/bootstrap` | Tray / Docker stack is up; try a hard refresh; ask distributor if bootstrap already completed |
| Email rejected | Must match the Authority **approved owner email** exactly |
| Key rejected | Paste the full `lic_…` key; confirm the licence is for this owner and still pending/active |
| Status / gateway error | Node and gateway containers are healthy; wait for first start, then retry |

Contact your distributor if the form still fails after those checks.
