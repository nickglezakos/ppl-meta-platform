# PPL Meta Installation Lifecycle CI/CD Implementation Plan

**Date**: September 10, 2026  
**Status**: Active (revamp)  
**Scope**: Concrete pipelines, manifests, Windows installer alignment, staged promotion, and docs wiki publish  
**Related Documents**:
- [ppl-meta-installation-lifecycle-cicd-policy.md](./ppl-meta-installation-lifecycle-cicd-policy.md)
- [ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md](./ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md)
- [updating-installations.md](../installation%20and%20onboarding/updating-installations.md)
- [windows-installer-private-registry-deployment.md](../installation%20and%20onboarding/windows-installer-private-registry-deployment.md)

---

## Purpose

Translate the installation lifecycle CI/CD policy into repository structure, workflows, installer behavior, Authority channel fields, and wiki publish automation.

---

## Pipeline Stages

1. Source validation
2. Artifact build
3. Artifact publish to GHCR
4. Dev machine validation
5. Sandbox installation validation
6. Pilot cohort soak
7. Stable promotion + docs `software_ref` refresh
8. Fleet update eligibility for `stable`

Authority CI/release/deploy workflows remain unchanged for the control-plane service.

---

## Phase 1 — Publish + First Install

### Platform release workflow

Add `.github/workflows/platform-release.yml` modeled on `.github/workflows/authority-release.yml`:

- Trigger: `workflow_dispatch` and optional `v*` tags
- Read version from root `VERSION` (or dispatch input override)
- Build/push `linux/amd64` images to `ghcr.io/nickglezakos/ppl-meta-platform/<service>:<VERSION>`
- Services: node, media, gateway, orchestrator, discovery, communications, frontend, vision-protected, vmeta-protected
- Reuse existing Dockerfiles and the mapping in `scripts/build_windows_installer_images.sh`

### Installer alignment

- `deployment/windows-installer/` `RELEASE_TAG` / version pins track root `VERSION`
- WSL defaults: `memory=12GB`, `processors=6`, `swap=2GB`
- Host RAM gate: ≥16GB
- Compose declares per-service `mem_limit` / `mem_reservation` per policy budget

### First-install handoff

After healthy stack: frontend bootstrap (`/bootstrap`) activates owner via Authority.

---

## Phase 2 — Staged Updates For Existing Installs

### Authority channel model

1. Add `release_channel` on entitlements (`internal` | `sandbox` | `pilot` | `stable`, default `stable`).
2. Expose in admin UI/API upsert.
3. Release records store which channels may receive a given `VERSION`.
4. Promote channel eligibility without republishing images.
5. `check-update` / update-result reporting honor channel membership and pilot soak audit gates.

### Local Windows update path

1. Preflight: disk, Docker Desktop, WSL ≥12GB, current vs target manifest.
2. Pull only changed GHCR images for approved `VERSION`.
3. Ordered compose recreate; health checks; report `healthy` / `rolled_back` / `failed`.
4. MVP may be operator-driven via installer scripts under the same eligibility rules.

### Mandatory promotion order

`dev machine → sandbox entitlement(s) → pilot cohort (soak rules) → stable`

Pilot soak rules are defined in the governing policy and are non-optional.

---

## Phase 3 — Online Wiki CI/CD

### Layout

```
docs/wiki/
  distributors/     # distributor audience
  owners-admins/    # platform owner + platform admin audience
  SOFTWARE_REF.md   # shared reference contract explanation
```

### Workflows

- `.github/workflows/docs-distributor-wiki.yml`
- `.github/workflows/docs-owner-admin-wiki.yml`

Rules:

- Trigger on docs wiki path changes and `workflow_dispatch`
- Do **not** trigger from platform/authority image publish jobs
- Validate each page / site `software_ref` frontmatter (`platform_version`, `policy_revision`, `channels_documented`)
- Publish artifact or deploy step is independent of GHCR image jobs

### Stable promotion checklist item

When a software release is promoted to `stable`, require:

- wiki `software_ref.platform_version` updated to that `VERSION`
- distributor and owner/admin pages not marked stale for that release

---

## Registry Layout

Default:

- Platform: `ghcr.io/nickglezakos/ppl-meta-platform/<service>:<VERSION>`
- Authority: `ghcr.io/nickglezakos/ppl-meta-authority` (existing)

Docker Hub is not the default publication target.

---

## Version Propagation

1. Update root `VERSION`
2. Platform release workflow tags images with that value
3. Windows installer pins the same value
4. Authority release eligibility records reference that value
5. Wiki `software_ref.platform_version` references that value after promotion evidence is ready

---

## Implementation Order

1. Revamp policy + this plan + checklist (docs)
2. Windows installer resource gates + compose limits + VERSION pin sync
3. `platform-release.yml`
4. Wiki source tree + docs CI validate workflows
5. Authority `release_channel` storage/API/UI (follow-up engineering)
6. Automated local updater polling (follow-up; operator-driven updates acceptable under same rules until then)

---

## Success Criteria

- Platform images publish via Actions to GHCR for `linux/amd64`
- Installer enforces 16GB host / 12GB WSL and bounded compose memory
- Policy and checklist encode pilot soak and channel promotion
- Docs CI validates two separate wikis with `software_ref`
- Software image CI and docs CI remain decoupled
