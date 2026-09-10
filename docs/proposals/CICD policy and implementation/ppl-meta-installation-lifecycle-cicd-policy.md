# PPL Meta Installation Lifecycle CI/CD Policy

**Date**: September 10, 2026  
**Status**: Active (revamp)  
**Scope**: Onboarding, first Windows Docker deploy, bootstrap, staged updates, rollback, audit, and decoupled online wiki documentation  
**Related Documents**:
- [ppl-meta-installation-lifecycle-cicd-implementation-plan.md](./ppl-meta-installation-lifecycle-cicd-implementation-plan.md)
- [ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md](./ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md)
- [updating-installations.md](../installation%20and%20onboarding/updating-installations.md)
- [windows-installer-private-registry-deployment.md](../installation%20and%20onboarding/windows-installer-private-registry-deployment.md)
- [docs/modules/bootstrap/](../../modules/bootstrap/)
- [docs/wiki/](../../wiki/)

---

## Purpose

This policy is the governing layer for how EyeNet / PPL Meta installations are published, first-deployed, activated, updated, and documented.

It treats Authority as the online control plane and the local Windows Docker stack as the first delivery execution path. Docker images, Windows installer assets, and online wikis must comply with these rules.

GitHub Container Registry (`ghcr.io/nickglezakos/ppl-meta-platform`) is the default and only primary registry for platform images. Docker Hub is not a primary publication target.

---

## Decisions Locked In

1. **First delivery path:** Windows amd64 + Docker Desktop prerequisite (not ARM).
2. **Registry:** GHCR only for platform images.
3. **Pipeline model:** Extend the existing Authority Actions pattern for platform image publish; keep Authority CI/deploy as-is.
4. **First-owner handoff:** Installer brings the stack up; Node/frontend bootstrap activates the owner.
5. **Host standard:** ≥16GB physical RAM; Docker Desktop / WSL2 memory **12GB**.
6. **Update promotion:** `dev → sandbox → pilot → stable`.
7. **Online docs:** Two EyeNet wikis (distributors vs owners/admins) with decoupled CI/CD that always references the software lifecycle.

---

## Authority As Control Plane

Authority is responsible for:

- installation identity (`installation_uuid`)
- entitlement / licence state and `application_key`
- `release_channel` on entitlements (`internal` | `sandbox` | `pilot` | `stable`, default `stable`)
- release eligibility by channel / cohort
- update result and promotion audit records

Authority must not SSH into customer machines or mutate local Docker runtime directly.

The local Windows installer / updater is responsible for:

- preflight checks (host RAM, WSL memory, Docker health, disk)
- pulling approved GHCR pins
- ordered compose apply, health checks, and rollback
- reporting update lifecycle outcomes back to Authority

---

## MVP Artifact Class

For this revamp, the first CI/CD packaging class is:

- Dockerized platform services on Windows Docker Desktop
- thin Windows installer bundle (compose, env template, scripts)

APK / app-style delivery remains deferred.

Platform services published under GHCR:

- `ppl-meta-node`
- `ppl-meta-media`
- `ppl-meta-gateway`
- `ppl-meta-orchestrator`
- `ppl-meta-discovery`
- `ppl-meta-communications`
- `ppl-meta-frontend`
- `ppl-meta-vision-protected`
- `ppl-meta-vmeta-protected`

Image pattern:

`ghcr.io/nickglezakos/ppl-meta-platform/<service>:<VERSION>`

Platform release version comes from the repository root `VERSION` file.

---

## First Install Contract

1. Operator installs Docker Desktop on Windows amd64.
2. Installer enforces host ≥16GB RAM and WSL memory ≥12GB.
3. Installer authenticates to GHCR and pulls pinned images for `VERSION`.
4. Compose starts the stack with per-service memory limits.
5. Health checks pass.
6. Frontend routes to `/bootstrap` when bootstrap is incomplete.
7. Owner activates with approved email + `lic_…` application key via Authority.

Publishing images does not complete installation. Bootstrap completes first-owner activation.

---

## Hardware And Docker Resource Policy (16GB Standard)

| Layer | Requirement |
|---|---|
| Host | Windows amd64, ≥16GB physical RAM, ≥12GB free disk |
| Docker Desktop / WSL2 | `memory=12GB`, `processors=6`, `swap=2GB` |
| Installer gate | Fail if host RAM < 16GB or WSL memory < 12GB |
| Compose | Every platform service declares `mem_limit` and `mem_reservation` |

Default WSL allocation on a 16GB host leaves ~4GB for Windows and gives Docker 12GB.

Initial per-service compose budget (limits sum ≈ 11.5GB inside the 12GB WSL pool):

| Service | mem_limit | mem_reservation |
|---|---|---|
| `ppl-meta-vision` / vision-protected | 2.5G | 1.5G |
| `ppl-meta-vmeta` / vmeta-protected | 2.0G | 1.0G |
| `postgres` | 1.0G | 512M |
| `ppl-meta-media` | 1.0G | 512M |
| `ppl-meta-node` | 768M | 384M |
| `ppl-meta-orchestrator` | 768M | 384M |
| `ppl-meta-gateway` | 512M | 256M |
| `ppl-meta-communications` | 512M | 256M |
| `ppl-meta-frontend` | 512M | 256M |
| `redis` | 512M | 256M |
| `ppl-meta-discovery` | 256M | 128M |

Policy rule: limits must fit under WSL memory with ≥500MB headroom. Vision and vmeta must never be unbounded on the Windows stack.

---

## Staged Updates For Existing Installations

Publishing to GHCR does **not** mean customers update. Authority channel eligibility decides who may pull.

### Promotion gates

| Stage | Where | Who | Gate |
|---|---|---|---|
| **1. Dev** | Developer Windows machine | Local only | Stack health + bootstrap smoke + critical path |
| **2. Sandbox** | Non-production test installations | `release_channel=sandbox` | Same checks + component update + rollback rehearsal |
| **3. Pilot** | Field installations on pilot-tagged licences | `release_channel=pilot` | Must pass pilot soak rules |
| **4. Stable** | Remaining eligible installations | `release_channel=stable` | Explicit promotion only after soak **passed** |

### Pilot licence tagging

- Entitlements carry explicit `release_channel`. Notes alone are not eligibility logic.
- Operators tag selected licences as `pilot` or `sandbox` in Authority admin UI/API.
- New releases start eligible for `sandbox` / `pilot` only.
- Non-pilot licences must not see or apply pilot-only targets.
- Suspended / revoked / inactive licences remain blocked regardless of channel.
- Auto-promotion is forbidden. Soak expiry alone does not promote.

### Pilot soak rules (required before stable)

**Cohort**

- Minimum **2** distinct pilot installations (different `installation_uuid`s) on real pilot-tagged entitlements — not sandbox, not the developer machine.
- Prefer at least two sites/operators; same-lab duplicates do not count as two pilots.
- Every pilot in the cohort for that release must be included; cherry-picking healthy ones is forbidden.

**Duration**

- Minimum **72 continuous hours** after the last pilot reports `healthy` for the target `VERSION`.
- Clock resets if any pilot rolls back, re-applies, or reports `failed` / `rolled_back`.
- Releases that touch vision or vmeta image tags require **7 calendar days**, unless a written waiver is attached (waiver cannot drop below 72 hours).

**Success signals (all required)**

- Every pilot reports `healthy` for the target `VERSION`.
- Zero open P0/P1 defects attributed to the release.
- End-of-soak smoke green on each pilot: Node+gateway health, login, Authority status refresh, and one camera/media path where cameras exist.
- No out-of-band hotfix on a different tag during soak (new tag = new soak).

**Hold signals (any one blocks stable promotion)**

- Any pilot `failed` or `rolled_back`.
- Emergency manual compose/image override required to stay operational.
- Recurring OOM / restarts on vision or vmeta under the 12GB WSL budget.
- Channel misconfiguration that would expose the release to non-pilot channels.
- Missing sandbox gate evidence for this `VERSION`.

**Abort and remediation**

- On hold: keep eligibility `pilot`-only or withdraw; do not promote.
- If ≥50% of the pilot cohort fails or rolls back: mark release **blocked**, keep `stable` on previous known-good version, require a **new VERSION** (not an in-place retag).
- Hotfixes follow the same ladder; there is no pilot-skip path into stable.

**Promotion audit record**

Stable promotion requires an Authority-side record with:

- target `VERSION`
- pilot `installation_uuid` list
- soak start / end timestamps
- per-install final status
- approving operator identity
- confirmation hold signals were absent

Without that record, promotion is policy-invalid even if images exist on GHCR.

### Update lifecycle states

`available` → `approved` → `downloaded` → `staged` → `applied` → `healthy` | `rolled_back` | `failed` | `blocked`

---

## Documentation CI/CD Path (Decoupled Online Wiki)

EyeNet online documentation has its own CI/CD, decoupled from software image pipelines, but always version-linked to the software lifecycle.

### Two separate wikis

| Wiki | Audience | Content focus |
|---|---|---|
| Distributor wiki | Distributors / channel ops | Licence issuance, pilot tagging, promotion rules, partner guidance |
| Owner / platform-admin wiki | Platform owners and admins | Install, 16GB resources, bootstrap, day-2 updates, health after update |

These must remain separate sites or authenticated sections. Distributor channel mechanics must not appear in owner install docs.

Sources live under [`docs/wiki/`](../../wiki/).

### Decoupling rules

- Docs may publish without rebuilding platform images.
- Software may publish GHCR images without rewriting wiki content.
- Docs pipelines must never be a side effect of platform/authority image jobs.
- Software promotion must not depend on wiki deploy success.

### Mandatory `software_ref` contract

Every wiki release must declare:

- referenced platform `VERSION`
- referenced channels and a plain-language soak summary
- referenced install path (Windows amd64 + Docker Desktop + GHCR)
- referenced hardware budget (16GB host / 12GB WSL)
- referenced bootstrap handoff
- policy revision stamp linking to this CI/CD policy

If software policy changes, docs CI must publish an update citing the new `VERSION` / policy revision, or mark pages stale/superseded. Docs must not silently describe an older model while a newer release is live on `stable`.

Stable software promotion includes a checklist item: wiki references updated to the promoted `VERSION`, executed by docs CI, not image CI.

---

## Versioning

- Root `VERSION` is the platform release identity.
- Docker tags, installer pins, Authority release records, and wiki `software_ref.platform_version` must resolve to that identity.
- Component-only updates remain allowed when compatibility rules are satisfied, but must still declare the platform `VERSION` they belong to.

---

## Superseded Paths

- Docker Hub as primary registry is superseded for this lifecycle.
- See [platform-private-dockerhub-deployment-proposal.md](../installation%20and%20onboarding/platform-private-dockerhub-deployment-proposal.md) for historical context only.

---

## Out Of Scope For This Revamp

- Docker Hub publishing
- ARM / non-Windows first targets
- Authority-issued registry pull tokens
- Fully automated fleet updater daemon on every install (may start operator-driven under the same channel rules)
- Auto-promoting pilot → stable without operator action
- Skipping pilot soak for schedule pressure
- Counting developer or sandbox machines as pilot cohort members
- Merging distributor and owner/admin wikis
- Coupling docs deploy into software image build/push workflows
