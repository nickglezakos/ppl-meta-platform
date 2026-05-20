# PPL Meta Installation Lifecycle CI/CD Policy

**Date**: May 18, 2026  
**Status**: Draft  
**Scope**: Define the policy and architectural rules for onboarding, activation, deployment, update, rollback, and audit across PPL Meta installation types  
**Related Documents**: [docs/proposals/installation and onboarding/updating-installations.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/updating-installations.md), [docs/proposals/installation and onboarding/first-batch-packaging-split-docker-and-apk.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/first-batch-packaging-split-docker-and-apk.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md), [docs/proposals/CICD policy and implementation/ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md)

---

## Purpose

PPL Meta needs a single CI/CD lifecycle policy that governs how installations are onboarded, activated, deployed, updated, rolled back, and audited across all supported delivery forms.

This policy defines authority as the control-plane boundary for installation identity, entitlement-aware release eligibility, deployment approval, and update reporting, while treating Docker images, APK or app artifacts, and Windows-installer or private-registry flows as delivery mechanisms that must comply with the same lifecycle rules.

For the current platform direction, GitHub Container Registry should be treated as the default container registry for published platform images.

---

## Scope

This policy applies to:

- installation onboarding and activation
- release publication and promotion
- deployment approval
- update authorization
- rollback and recovery governance
- lifecycle reporting and audit expectations

This policy does not define the exact pipeline jobs, registry commands, manifest schemas, or task automation in operational detail. Those belong in the paired implementation document.

---

## Related Proposals And Input Constraints

This policy should be read as the governing layer above three already established proposal surfaces.

### 1. Updating Installations

[docs/proposals/installation and onboarding/updating-installations.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/updating-installations.md) defines the lifecycle model for how a real installation should move from one release state to another while preserving durable installation identity.

### 2. First Batch Packaging Split

[docs/proposals/installation and onboarding/first-batch-packaging-split-docker-and-apk.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/first-batch-packaging-split-docker-and-apk.md) defines the packaging boundary between Docker-delivered platform services and APK or app-style installation targets.

### 3. Windows Installer And Private Registry Deployment

[docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md) defines one concrete deployment and update path for Windows-hosted Dockerized installations.

Together, these documents establish:

- the lifecycle model
- the artifact classes
- at least one concrete deployment path

This policy aligns them under one release and update governance model.

---

## Authority As Installation Lifecycle Control Plane

Authority should be treated as the installation lifecycle control plane.

That means authority is responsible for:

- installation identity and installation status
- entitlement and licence-aware release eligibility
- release approval policy by installation or channel
- audit records for deployment and update transitions
- health or lifecycle reporting associated with an installation

Authority should not be treated as the system that builds artifacts or performs platform-specific installation work itself.

Its role is to decide and record:

- what installation is asking for a deployment or update
- what release target is being requested
- whether the target is allowed
- what the outcome of that transition was

In the current target model, authority runs online as the control-plane service and a separate updater runs locally on each managed installation.

That split means:

- authority decides approved target state, eligibility, and audit policy
- the local updater executes downloads, service replacement, health validation, and rollback on the installation node
- authority may notify or signal, but it should not directly perform runtime changes on the customer machine

This is the required control boundary for the lifecycle described in this policy.

---

## Installation Identity And Entitlement Model

All CI/CD lifecycle decisions should be anchored on a durable installation identity.

The minimum policy rule is:

- every customer deployment has a stable `installation_uuid`
- deployment and update decisions are evaluated against that installation identity
- entitlement, support, licence, and ownership state are attached to that installation identity through authority

This means:

- releases are not approved for anonymous machines
- updates are not approved only by local version checks
- every deployment or update must be attributable to a real installation record

---

## Release Artifact Classes

The lifecycle policy should distinguish between release classes even when they belong to the same installation.

Minimum artifact classes are:

- Docker platform release artifacts
- APK or app-style release artifacts
- release manifests and metadata
- supporting migration or rollback instructions

This matters because the same installation may consume different artifact types while still being managed under one lifecycle policy.

---

## Versioning Policy

Versioning must be treated as part of release identity, not as an informal label.

The current repository anchor is the root [VERSION](/Users/nickgklezakos/Documents/ppl-meta-code/VERSION) file, which currently defines the platform release version for this repository.

The lifecycle policy should distinguish between two related version scopes.

### 1. Platform Release Version

This is the top-level release identity for the overall platform lifecycle.

In the current model, that identity is defined by the root `VERSION` file.

### 2. Component Or Service Version

This is the release identity of an individual service or artifact that may move within the broader platform lifecycle.

This is necessary because a single service may need to be rebuilt, patched, or redeployed while still remaining traceable to the wider platform release.

At policy level, that means:

- every CI/CD release must resolve to an explicit version
- the root `VERSION` file is the current authoritative source for the platform release version
- component or service versions may exist beneath that platform version
- release manifests, Docker image tags, app artifact versions, and authority release records must map both the platform version and the relevant component versions where applicable
- packaging-specific version expressions may differ by target, but they must remain traceable to the same approved platform release identity

The policy should also require that versioning be consistent across:

- release approval
- artifact publication
- deployment eligibility checks
- update reporting
- rollback history

The policy should also require that partial service updates do not lose platform traceability.

That means:

- a service may have its own release version
- that service release must still declare which platform release it belongs to or is compatible with
- authority and release manifests must be able to reason about both scopes together

As the lifecycle matures, the platform may later introduce richer component-level versioning or channel-aware release numbering, but those should remain subordinate to the repository-level platform version identity unless intentionally redesigned.

---

## Packaging And Delivery Boundaries

The packaging split already proposed for the first batch should remain valid.

At policy level, that means:

- Dockerized backend and web components are governed as coordinated platform release units
- APK or app-style deliverables are governed as device or client release units
- out-of-scope surfaces remain outside the first CI/CD packaging pass until explicitly adopted

The lifecycle policy should not collapse these classes into a fake single packaging model.

Instead, it should require that every packaging class:

- has versioned release outputs
- is representable in a release manifest
- can be approved or blocked by authority policy
- can report deployment or update outcomes back to the installation record

---

## Release Eligibility Policy

A release should only be deployable or updatable when authority policy allows it.

Minimum policy checks should include:

- installation exists and is active
- entitlement or licence state is sufficient for deployment or update
- target release is valid for the installation's channel or policy scope
- current version can move safely to target version
- no policy block exists such as suspension, revocation, or unsupported state

This eligibility layer should apply regardless of whether the target artifact is Docker-based, APK-based, or installer-driven.

---

## Deployment Approval Policy

Deployment policy should cover first deployment and later redeployment of approved releases.

The policy should require:

- explicit release identity
- explicit installation identity
- explicit artifact class
- explicit deployment mode such as Docker stack, Windows installer, or app delivery path
- explicit version identity derived from the release versioning policy
- traceable outcome reporting

Deployments should be treated as controlled release transitions, not as manual environment drift.

---

## Update Execution Policy

The policy should require that updates be executed through an approved release manifest and a controlled order of operations.

Minimum expectations are:

- preflight validation
- ordered artifact application
- restart and health validation
- update result reporting
- rollback handling if validation fails

The policy should not require one runtime mechanism for all targets, but it should require equivalent lifecycle discipline across all targets.

For Dockerized platform services such as `vmeta`, a service update should normally be treated as a replacement with a newly published service image, not an in-place mutation of the running container filesystem.

That means a `vmeta`-only update should normally result in:

- a newly published `vmeta` image version
- manifest approval for eligible installations
- a local pull of the new `vmeta` image by the installation updater
- replacement of the running `vmeta` container
- post-update validation and reporting

This policy should allow component-only updates when compatibility rules are satisfied, without requiring a full platform rebuild for every service patch.

## Concrete Installation Update Lifecycle

Every installation update should move through a concrete lifecycle with explicit states.

The minimum lifecycle should be:

1. `available`
2. `approved`
3. `downloaded`
4. `staged`
5. `applied`
6. `healthy`
7. `rolled_back`

These states mean:

- `available`: a release or component update exists in published form
- `approved`: authority has allowed that target for a specific installation, cohort, or channel
- `downloaded`: the local updater has retrieved the required artifacts
- `staged`: the updater has completed preflight checks and is ready to switch runtime state
- `applied`: the updater has replaced the target runtime or artifact locally
- `healthy`: post-apply validation has succeeded and the installation is considered converged to target state
- `rolled_back`: the attempted transition failed validation and the updater restored the prior known-good state

The policy should also recognize terminal or blocking conditions associated with these lifecycle states, including:

- `blocked` when eligibility or local policy prevents movement
- `failed` when execution stops before health can be established

These may be recorded as outcomes or operator-visible status flags, but the required release lifecycle above must remain explicit.

## Authority And Local Updater Responsibilities

The lifecycle depends on a strict responsibility split.

Authority online is responsible for:

- installation registration and identity
- entitlement and licence enforcement
- release approval by installation, channel, or cohort
- manifest resolution and target-state policy
- recording update progress, success, failure, and rollback events

The local updater is responsible for:

- polling authority for approved target state
- downloading artifacts from approved sources such as GitHub Container Registry
- executing ordered local updates
- running health checks and local rollback
- reporting lifecycle transitions back to authority

Polling should be the required baseline mechanism because it avoids needing inbound connectivity from authority to customer installations. Push-style notifications may exist later as an acceleration path, but they should not replace the local polling contract.

---

## Rollback And Recovery Policy

Rollback should be treated as a first-class lifecycle outcome.

The policy should require:

- a defined rollback path per artifact class
- explicit recording of failed release attempts
- preservation of installation identity during recovery
- operator-visible status for blocked, failed, and rolled-back states

Rollback policy should be consistent even if the technical rollback mechanism differs across Docker, APK, and installer-based targets.

---

## Reporting, Audit, And Traceability

Every deployment or update decision should be traceable.

The policy should require records for:

- installation identity
- requested release target
- previous release state
- approval decision
- update or deployment outcome
- health summary after transition
- operator or automation actor if relevant

This is necessary for support, recovery, and future fleet management.

---

## Delivery Model Mapping

The policy should explicitly map the release-control model to the existing delivery forms.

### Dockerized Platform Delivery

Authority governs eligibility and approval for platform manifests that resolve to Docker image sets.

### APK Or App-Style Delivery

Authority governs eligibility and approval for device or app manifests that resolve to app artifacts.

### Windows Installer And Private Registry Delivery

Authority governs eligibility and approval, while the Windows installer and registry path provide one concrete execution mechanism for applying approved Dockerized releases on a Windows-hosted installation.

In the current implementation direction, that registry path should default to GitHub Container Registry rather than Docker Hub.

---

## Required CI/CD Implementation Follow-Up

This policy must be followed by a CI/CD implementation plan that defines:

- concrete build and test pipelines
- release manifest generation rules
- image and artifact publication flow
- GitHub Container Registry and repository layout
- authority integration points
- installer and updater behavior
- promotion and rollback mechanics
- operational tasks and validation checks

That implementation document should realize this policy rather than redefining it.
