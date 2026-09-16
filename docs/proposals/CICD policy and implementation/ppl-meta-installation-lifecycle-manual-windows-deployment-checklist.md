# PPL Meta Manual Windows Deployment Checklist

**Date**: September 10, 2026  
**Status**: Active (revamp)  
**Scope**: Developer walkthrough for manually validating a Windows deployment against the production authority service, GitHub Container Registry release images, the local installer assets, staged update promotion, and the Windows installer path  
**Related Documents**: [ppl-meta-installation-lifecycle-cicd-policy.md](./ppl-meta-installation-lifecycle-cicd-policy.md), [ppl-meta-installation-lifecycle-cicd-implementation-plan.md](./ppl-meta-installation-lifecycle-cicd-implementation-plan.md), [windows-installer-private-registry-deployment.md](../installation%20and%20onboarding/windows-installer-private-registry-deployment.md)

---

## Purpose

This document is the developer-facing manual test checklist for validating the current installation lifecycle design on a real Windows machine.

The target scenario is:

- production authority service online
- release images published to GitHub Container Registry
- local installer assets prepared from this repository
- Windows installer used on the target machine
- host meets **16 GB RAM** and WSL **12 GB** policy
- first-owner bootstrap completed against Authority
- staged update rehearsal: sandbox → pilot (stable entitlement does not update) → promote → stable becomes eligible
- wiki `software_ref` refreshed for the promoted `VERSION` via docs CI (decoupled from image CI)

---

## Test Goal

By the end of this walkthrough, you should have proven that:

1. a release exists in GHCR and is consumable by the Windows deployment path
2. the Windows machine meets 16 GB host / 12 GB WSL gates and compose memory limits are present
3. the production authority service can hold a pending entitlement for the target owner
4. the Windows machine can install the pinned platform bundle without local image builds
5. the installed node can activate via `/bootstrap` using approved owner email + `application_key`
6. the installation reports healthy runtime state after deployment
7. a sandbox update of an existing install to a new GHCR tag works
8. a pilot-tagged entitlement receives an update while a stable entitlement does **not**
9. after soak evidence / promotion record, stable entitlement becomes eligible
10. distributor and owner/admin wiki pages cite the promoted `VERSION` via `software_ref`

---

## System Under Test

This checklist assumes the following roles:

- authority runs online at the production authority URL
- GitHub Container Registry stores the pinned Docker release images
- the Windows machine runs the platform locally through Docker Desktop
- update eligibility is channel-based (`sandbox` / `pilot` / `stable`)
- the local updater logic runs on the Windows machine, even if the first pass is manually simulated by the developer

This means authority decides approved state, but the Windows host performs the actual pull, restart, health check, and rollback work.

---

## Inputs You Must Prepare Before Starting

### Release Inputs

- platform release version from repository root `VERSION` (current pin `2.25.80` unless intentionally overridden)
- exact image list and tags under `ghcr.io/nickglezakos/ppl-meta-platform`
- compose / env / installer assets from `deployment/windows-installer/`

### Authority Inputs

- production authority base URL
- platform admin credentials
- approved owner email and application key
- at least one **sandbox** entitlement and one **pilot** entitlement
- one **stable** entitlement that must remain pinned until promotion

### Registry Inputs

- GHCR credentials with package read access
- confirmation required images are published

### Windows Test Machine Inputs

- Windows 10/11 amd64
- **≥16 GB** physical RAM
- Docker Desktop with WSL2
- ≥12 GB free disk

---

## Phase A — Resource And First Install Gates

- [ ] Host RAM ≥ 16 GB (installer fails below this)
- [ ] `.wslconfig` memory ≥ 12 GB after installer configuration
- [ ] `docker-compose.windows-installer.yml` includes `mem_limit` / `mem_reservation` on all services
- [ ] `RELEASE_TAG` matches the intended published `VERSION`
- [ ] GHCR login succeeds and image pull completes without local builds
- [ ] Stack becomes healthy
- [ ] Frontend routes to `/bootstrap` when bootstrap incomplete
- [ ] Owner activation succeeds only for approved owner email + valid `lic_…` key
- [ ] Post-bootstrap login reaches `/home`

## Phase B — Staged Update Rehearsal

- [ ] Publish or select a newer GHCR `VERSION` than the running install
- [ ] Sandbox entitlement can update to the new tag; record health evidence
- [ ] Pilot entitlement is approved for the release; stable entitlement is **not** eligible
- [ ] Pilot install updates successfully and reports healthy
- [ ] Stable install remains on previous tag during pilot eligibility
- [ ] Soak evidence captured (cohort size, start/end, statuses) per policy
- [ ] Promote release to `stable` only with audit record
- [ ] Stable entitlement becomes eligible and updates successfully after promotion

## Phase C — Docs Reference Gate

- [ ] Docs CI workflows validate `docs/wiki/distributors` and `docs/wiki/owners-admins`
- [ ] Wiki `software_ref.platform_version` matches the promoted software `VERSION`
- [ ] Docs publish did **not** require re-running `platform-release.yml`

## Sign-Off

Record:

- tested `VERSION`
- Windows host RAM / WSL memory observed
- sandbox / pilot / stable installation UUIDs
- soak timestamps and promotion approver
- wiki artifact run IDs

This document should be updated after each real deployment rehearsal until the Windows deployment path is routine and channel-based updates are fully automated.
