# EyeNet Online Wiki Sources

This tree is the source for EyeNet **online wiki** documentation.

It has its **own CI/CD**, decoupled from platform/Authority image publish workflows, but every published page must reference the software lifecycle via `software_ref` frontmatter.

## Public host

| | |
|---|---|
| Base URL | https://wiki.eyenet-vision.com |
| What is EyeNet | https://wiki.eyenet-vision.com/what-is-eyenet/ |
| User guide | https://wiki.eyenet-vision.com/owners-admins/ |
| Distributors guide | https://wiki.eyenet-vision.com/distributors/ |
| Deploy package | [`autonomous/ppl-meta-wiki/`](../../autonomous/ppl-meta-wiki/) |
| Deploy workflow | [`.github/workflows/docs-wiki-deploy.yml`](../../.github/workflows/docs-wiki-deploy.yml) |

Static HTML on the Hetzner VPS (Caddy `file_server`). Independent of Authority containers.

## Sites

| Path | Nav label | Audience |
|---|---|---|
| [`what-is-eyenet/`](./what-is-eyenet/) | What is EyeNet | Product overview (features) |
| [`owners-admins/`](./owners-admins/) | User guide | Platform owners and platform admins |
| [`distributors/`](./distributors/) | Distributors guide | Distributors and channel operators |

Keep the how-to audiences (user guide vs distributors) separate. The product overview may cross-link both.

### What is EyeNet

| Page | Topic | Menu order |
|---|---|---|
| [`what-is-eyenet/index.md`](./what-is-eyenet/index.md) | Product overview and application index | 10 |
| [`what-is-eyenet/presence.md`](./what-is-eyenet/presence.md) | Presence | 20 |
| [`what-is-eyenet/signage.md`](./what-is-eyenet/signage.md) | Signage | 30 |
| [`what-is-eyenet/vradar.md`](./what-is-eyenet/vradar.md) | Vradar (Automation) | 40 |
| [`what-is-eyenet/gate.md`](./what-is-eyenet/gate.md) | Gate | 50 |
| [`what-is-eyenet/sentinel.md`](./what-is-eyenet/sentinel.md) | Sentinel | 60 |
| [`what-is-eyenet/matrix.md`](./what-is-eyenet/matrix.md) | Matrix | 70 |
| [`what-is-eyenet/shared-platform.md`](./what-is-eyenet/shared-platform.md) | Shared platform + operating modes | 80 |

### Distributor pages

| Page | Topic |
|---|---|
| [`distributors/index.md`](./distributors/index.md) | Home and getting-started Authority entry |
| [`distributors/authority-admin.md`](./distributors/authority-admin.md) | `/admin` shell: Home · People · Licences · Me |
| [`distributors/invite-people.md`](./distributors/invite-people.md) | Invite sheet and accept flow |
| [`distributors/issue-licences.md`](./distributors/issue-licences.md) | Issue vs assign and `lic_…` keys |

Archived (not published online): [`../archived-wiki/distributors/release-channels.md`](../archived-wiki/distributors/release-channels.md) — channel / pilot policy text held offline until Authority UI exists ([KI-003](../../issues/known%20issues/known%20issues.md)).

### Owner / platform-admin pages

| Page | Topic | Menu order |
|---|---|---|
| [`owners-admins/hardware.md`](./owners-admins/hardware.md) | Host and WSL / Docker memory requirements | 10 |
| [`owners-admins/index.md`](./owners-admins/index.md) | First install: licence key, Windows/Linux install, after-install TOC | 15 |
| [`owners-admins/bootstrap.md`](./owners-admins/bootstrap.md) | First-install `/bootstrap` activation with screenshots | 25 |
| [`owners-admins/users-and-roles.md`](./owners-admins/users-and-roles.md) | User management: local users/roles UI | 27 |
| [`owners-admins/cameras-and-detection.md`](./owners-admins/cameras-and-detection.md) | Add cameras and start live detection | 30 |
| [`owners-admins/detections-individuals-persons.md`](./owners-admins/detections-individuals-persons.md) | Instant vs recording detection, preview tabs, person groups | 35 |
| [`owners-admins/media-management.md`](./owners-admins/media-management.md) | Upload, collections CRUD, assign media, MVR date/time search → Analysis | 36 |
| [`owners-admins/alerts-and-automation.md`](./owners-admins/alerts-and-automation.md) | Vradar: triggers/actions on instant detection (`/triggers`) | 40 |
| [`owners-admins/presence-attendance.md`](./owners-admins/presence-attendance.md) | Presence sessions, people, settings | 50 |
| [`owners-admins/presence-authenticator.md`](./owners-admins/presence-authenticator.md) | EyeNet Authenticator (phone Presence, sandbox/pilot) | 51 |
| [`owners-admins/digital-signage.md`](./owners-admins/digital-signage.md) | Playlists, devices, playback | 60 |
| [`owners-admins/entrances-and-activity.md`](./owners-admins/entrances-and-activity.md) | Compose cameras + analytics + Vradar + presence; two entrance use cases | 70 |
| [`owners-admins/analytics-and-reports.md`](./owners-admins/analytics-and-reports.md) | MVR Analytics filters, Levels 1–4, Excel export | 80 |
| [`owners-admins/multi-site-and-remote.md`](./owners-admins/multi-site-and-remote.md) | EyeNet VPN (licence), Network enroll/tokens, platform + mobile/signage, Matrix | 90 |

Sidebar order is controlled by optional `nav_order` frontmatter on each page (lower first).

## `software_ref` contract

Every markdown page under the site roots must include YAML frontmatter:

```yaml
---
software_ref:
  platform_version: "2.25.85"
  policy_revision: "2026-09-26"
  channels_documented:
    - sandbox
    - pilot
    - stable
  install_path: "windows-docker-desktop-ghcr"
  host_ram_gb: 16
  wsl_memory_gb: 12
---
```

Validation runs in:

- `.github/workflows/docs-distributor-wiki.yml`
- `.github/workflows/docs-owner-admin-wiki.yml`

Production publish (validate + HTML build + rsync) runs in:

- `.github/workflows/docs-wiki-deploy.yml` (pushes to `main` under `docs/wiki/**`, or `workflow_dispatch`)

Those workflows must not run as a side effect of `platform-release.yml` or `authority-release.yml`.

## Governing software policy

- [Installation lifecycle CI/CD policy](../proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md)
- [Bootstrap module](../modules/bootstrap/)
- [Wiki Hetzner deployment](../../autonomous/ppl-meta-wiki/DEPLOYMENT.md)
