# EyeNet Online Wiki Sources

This tree is the source for EyeNet **online wiki** documentation.

It has its **own CI/CD**, decoupled from platform/Authority image publish workflows, but every published page must reference the software lifecycle via `software_ref` frontmatter.

## Public host

| | |
|---|---|
| Base URL | https://wiki.eyenet-vision.com |
| Distributors | https://wiki.eyenet-vision.com/distributors/ |
| Owners / admins | https://wiki.eyenet-vision.com/owners-admins/ |
| Deploy package | [`autonomous/ppl-meta-wiki/`](../../autonomous/ppl-meta-wiki/) |
| Deploy workflow | [`.github/workflows/docs-wiki-deploy.yml`](../../.github/workflows/docs-wiki-deploy.yml) |

Static HTML on the Hetzner VPS (Caddy `file_server`). Independent of Authority containers.

## Sites

| Path | Audience |
|---|---|
| [`distributors/`](./distributors/) | Distributors and channel operators |
| [`owners-admins/`](./owners-admins/) | Platform owners and platform admins |

Do not merge these audiences into one undifferentiated site.

### Distributor pages

| Page | Topic |
|---|---|
| [`distributors/index.md`](./distributors/index.md) | Home and getting-started Authority entry |
| [`distributors/authority-admin.md`](./distributors/authority-admin.md) | `/admin` shell: Home · People · Licences · Me |
| [`distributors/invite-people.md`](./distributors/invite-people.md) | Invite sheet and accept flow |
| [`distributors/issue-licences.md`](./distributors/issue-licences.md) | Issue vs assign and `lic_…` keys |
| [`distributors/release-channels.md`](./distributors/release-channels.md) | Channel policy and soak (UI gap noted) |

### Owner / platform-admin pages

| Page | Topic | Menu order |
|---|---|---|
| [`owners-admins/index.md`](./owners-admins/index.md) | Install, bootstrap, updates, after-install TOC | 10 |
| [`owners-admins/hardware.md`](./owners-admins/hardware.md) | Host and WSL memory requirements | 20 |
| [`owners-admins/cameras-and-detection.md`](./owners-admins/cameras-and-detection.md) | Add cameras and start live detection | 30 |
| [`owners-admins/detections-individuals-persons.md`](./owners-admins/detections-individuals-persons.md) | Instant vs recording detection, preview tabs, person groups | 35 |
| [`owners-admins/media-management.md`](./owners-admins/media-management.md) | Upload, collections CRUD, assign media, MVR date/time search → Analysis | 36 |
| [`owners-admins/alerts-and-automation.md`](./owners-admins/alerts-and-automation.md) | Vradar: triggers/actions on instant detection (`/triggers`) | 40 |
| [`owners-admins/presence-attendance.md`](./owners-admins/presence-attendance.md) | Presence sessions, people, settings | 50 |
| [`owners-admins/digital-signage.md`](./owners-admins/digital-signage.md) | Playlists, devices, playback | 60 |
| [`owners-admins/entrances-and-activity.md`](./owners-admins/entrances-and-activity.md) | Compose cameras + analytics + Vradar + presence; two entrance use cases | 70 |
| [`owners-admins/analytics-and-reports.md`](./owners-admins/analytics-and-reports.md) | MVR Analytics filters, Levels 1–4, Excel export | 80 |
| [`owners-admins/multi-site-and-remote.md`](./owners-admins/multi-site-and-remote.md) | EyeNet VPN (licence), Network enroll/tokens, platform + mobile/signage, Matrix | 90 |
| [`owners-admins/users-and-roles.md`](./owners-admins/users-and-roles.md) | Local users/roles UI; custom roles for gate, presence, signage | 100 |

Sidebar order is controlled by optional `nav_order` frontmatter on each page (lower first).

## `software_ref` contract

Every markdown page under the two site roots must include YAML frontmatter:

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
