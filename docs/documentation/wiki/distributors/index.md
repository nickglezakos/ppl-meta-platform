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
title: Distributor wiki home
audience: distributor
---

# EyeNet Distributor Wiki

This is the **Distributors guide** for channel operators. It is separate from the [User guide](../owners-admins/) (install owners / platform admins). Product overview: [What is EyeNet](../what-is-eyenet/).

Live site: [https://wiki.eyenet-vision.com/distributors/](https://wiki.eyenet-vision.com/distributors/)

## Where you work

Getting started happens in Authority at **https://authority.eyenet-vision.com/admin**.

- Use `/admin` only. The site root returns a JSON service descriptor, not the UI.
- `/admin/console` redirects to `/admin` (old dual console is gone).
- One mobile-first shell with bottom tabs: **Home · People · Licences · Me** (role-filtered).

## What you manage

- Invite resellers and owners on **People**
- Assign (and, as platform admin, issue) licences on **Licences**
- Hand the owner their `lic_…` application key for Windows bootstrap
- Follow release-channel and pilot-soak policy before `stable` promotion
- Partner guidance without exposing internal channel mechanics to end customers

## Software lifecycle this wiki references

- Platform version: **2.25.82**
- Install path: Windows amd64 + WSL Docker Engine CE + GHCR (wiki zip)
- Update channels: `sandbox` → `pilot` → `stable`
- Pilot soak: minimum 2 pilot installations, 72 hours (7 days if vision/vmeta changed), promotion audit required

Publishing images to GHCR does **not** update customer installs. Authority channel eligibility decides who may pull.

## Related pages

- [Authority admin shell](./authority-admin.md)
- [Invite people](./invite-people.md)
- [Issue and assign licences](./issue-licences.md)
- [User guide](../owners-admins/) (owners / platform admins)
- [What is EyeNet](../what-is-eyenet/)
