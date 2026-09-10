# EyeNet Online Wiki Sources

This tree is the source for EyeNet **online wiki** documentation.

It has its **own CI/CD**, decoupled from platform/Authority image publish workflows, but every published page must reference the software lifecycle via `software_ref` frontmatter.

## Sites

| Path | Audience |
|---|---|
| [`distributors/`](./distributors/) | Distributors and channel operators |
| [`owners-admins/`](./owners-admins/) | Platform owners and platform admins |

Do not merge these audiences into one undifferentiated site.

## `software_ref` contract

Every markdown page under the two site roots must include YAML frontmatter:

```yaml
---
software_ref:
  platform_version: "2.25.79"
  policy_revision: "2026-09-10"
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

Those workflows must not run as a side effect of `platform-release.yml` or `authority-release.yml`.

## Governing software policy

- [Installation lifecycle CI/CD policy](../proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md)
- [Bootstrap module](../modules/bootstrap/)
