# PPL Meta Installation Lifecycle CI/CD Implementation Plan

**Date**: May 18, 2026  
**Status**: Draft  
**Scope**: Define the concrete pipelines, manifests, packaging flow, authority integrations, and operational automation required to implement the installation lifecycle CI/CD policy  
**Related Documents**: [docs/proposals/CICD policy and implementation/ppl-meta-installation-lifecycle-cicd-policy.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md), [docs/proposals/CICD policy and implementation/ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-manual-windows-deployment-checklist.md), [docs/proposals/installation and onboarding/updating-installations.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/updating-installations.md), [docs/proposals/installation and onboarding/first-batch-packaging-split-docker-and-apk.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/first-batch-packaging-split-docker-and-apk.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md)

---

## Purpose

This document defines the concrete implementation path for the PPL Meta installation lifecycle CI/CD policy.

Its role is to translate lifecycle policy into repository structure, pipeline jobs, release manifests, artifact publishing, deployment behavior, and authority integration points.

---

## Target Pipeline Architecture

The implementation should separate the lifecycle into a small number of clear pipeline stages.

Recommended stages:

1. source validation
2. artifact build
3. artifact publish
4. release manifest generation
5. environment promotion
6. installation deployment or update execution
7. result reporting back to authority

This keeps policy, artifact generation, and rollout mechanics distinct.

---

## Version Source And Propagation

The implementation should explicitly define how release versioning is produced and propagated.

The current source of truth is the root [VERSION](/Users/nickgklezakos/Documents/ppl-meta-code/VERSION) file.

The implementation should treat that file as the platform release version, not as the only possible version expression in the system.

In the current model, the implementation should treat that file as the canonical platform release version input for:

- CI build metadata
- Docker image tagging
- APK or app artifact version mapping
- release manifest generation
- authority release identity and eligibility checks
- deployment and update reporting

The implementation should also support component or service version expressions beneath that platform version when needed.

That means the versioning model should become:

- one platform release version from `VERSION`
- zero or more component versions attached to releasable services or artifacts
- release manifests that bind component versions back to the platform release version

The implementation should therefore define:

- when and how `VERSION` is updated
- how pipelines read `VERSION`
- how the platform version is injected into build outputs
- how component versions are derived or declared for services that release independently
- how both platform and component versions are written into manifests and authority-facing release metadata
- how rollback references point back to previously published versions

This avoids a split where repository versioning, artifact versioning, and authority release identity drift apart.

---

## Build Jobs By Artifact Type

The first implementation pass should build artifact classes according to the already defined packaging split.

### Docker Artifact Jobs

Build versioned images for the first-batch Dockerized platform services.

Those image tags should derive from the platform version in `VERSION`, optionally combined with component-specific, channel, or build metadata where needed.

### APK Or App Artifact Jobs

Build versioned mobile or app deliverables that remain outside the Docker packaging path.

Those artifacts should also map back to the same platform version identity even if target-specific packaging requires additional formatting or component-specific version notation.

### Shared Metadata Jobs

Produce release metadata, checksums, manifest inputs, and compatibility declarations.

---

## Docker Image Publication Flow

The Docker pipeline should:

- build tagged images for approved platform services
- apply version and channel tagging rules
- publish to GitHub Container Registry by default
- record immutable references for manifest generation

The implementation should preserve compatibility with the packaging split and the Windows private registry deployment model.

---

## APK Or App Artifact Publication Flow

The APK or app publication pipeline should:

- build versioned app artifacts
- publish them to the selected delivery location
- attach release metadata needed for manifest generation
- preserve a stable link between artifact version and release identity

---

## Release Manifest Generation

The implementation should generate explicit release manifests rather than letting installations infer target versions ad hoc.

A release manifest should identify:

- release version
- release channel
- artifact class
- component versions where applicable
- component versions or image tags
- migration requirements
- restart order
- health expectations
- rollback notes

Authority should evaluate eligibility against these manifest identities.

The manifest generation step should consume the repository `VERSION` value directly or from a derived CI variable that was generated from it.

---

## Registry And Artifact Repository Layout

The implementation should define one coherent layout for published artifacts.

At minimum it should define:

- GitHub Container Registry namespace and tagging convention
- APK or app artifact storage convention
- manifest storage location
- environment or channel separation
- retention and rollback reference rules

This layout should support both normal promotion and recovery workflows.

The tagging and storage convention should make the platform version easy to resolve from published artifacts.

The current default should be:

- `ghcr.io/nickglezakos/ppl-meta-platform` for Dockerized platform images

Docker Hub should not be treated as the default publication target in this implementation plan.

---

## Authority Integration Points And APIs

The implementation should define concrete integration points between release automation, deployed installations, and authority.

Minimum integration surfaces should include:

- installation state reporting
- release eligibility check
- release manifest resolution
- update result reporting
- health or post-deploy reporting

The implementation should specify which authority APIs are called at each stage.

In the current target model, authority runs online and the updater runs locally on each installation.

That means the implementation should avoid designs where authority directly SSHs into installations or performs remote runtime mutation itself. Instead, authority should publish approved target state and the local updater should converge the installation to that state.

---

## Installation Updater Workflow

Each supported delivery mechanism should map to a concrete updater behavior.

At high level, an updater should:

1. identify the installation by `installation_uuid`
2. resolve current state
3. request release eligibility
4. fetch the approved release manifest
5. execute preflight checks
6. apply the update in the required order
7. run validation and health checks
8. report the result back to authority

The exact mechanism differs by Docker, APK, or installer path, but the lifecycle sequence should remain consistent.

The updater should run locally on the installation node, not as an online centralized executor.

The recommended first implementation is a polling model:

1. the local updater polls authority on a fixed schedule
2. authority returns the approved target manifest for that installation
3. the updater decides whether action is needed locally
4. the updater downloads and applies only the approved changes
5. the updater reports lifecycle transitions and final outcome back to authority

Optional notifications may later be added to prompt an immediate poll, but polling should remain the reliable baseline.

## Concrete Update Lifecycle And State Machine

The implementation should encode a concrete update state model shared by authority records and updater reports.

Minimum lifecycle states:

1. `available`
2. `approved`
3. `downloaded`
4. `staged`
5. `applied`
6. `healthy`
7. `rolled_back`

Associated execution or operator states:

- `blocked`
- `failed`

The implementation should treat these states as reportable transition events, not informal log messages.

At minimum, authority should be able to record:

- installation UUID
- manifest or component target
- previous known state
- current lifecycle state
- transition timestamp
- updater identity or node identity
- success, failure, or rollback reason

## Concrete Docker Service Update Flow

For Dockerized services such as `vmeta`, a service update should be implemented as a new image release plus local container replacement.

The concrete flow should be:

1. CI builds and publishes a new `vmeta` image to `ghcr.io/nickglezakos/ppl-meta-platform`
2. CI generates or updates the release manifest with the new `vmeta` component version and compatibility data
3. authority marks that component version as approved for eligible installations or cohorts
4. the local updater polls authority and resolves the approved manifest for its `installation_uuid`
5. the updater compares current versus target `vmeta` version
6. the updater pulls the new `vmeta` image locally
7. the updater runs preflight checks and enters `staged`
8. the updater stops and replaces only the local `vmeta` container unless manifest dependencies require coordinated changes
9. the updater runs health checks and dependent validation
10. the updater reports `healthy` on success or performs rollback and reports `rolled_back` or `failed`

This is the expected implementation pattern for component-only service updates. A `vmeta` patch should normally produce a new full `vmeta` image, but it should not require every other service image to be rebuilt or redeployed unless compatibility rules demand it.

---

## Windows Installer And Private Registry Execution Path

The implementation should explicitly define how the Windows-hosted Docker deployment path fits into the lifecycle.

That should include:

- how the installer authenticates to GitHub Container Registry or another approved release source
- how manifests map to Docker image tags
- how Windows-hosted deployments pull and switch releases
- how rollback works in the Windows-hosted path
- how outcomes are reported back to authority

---

## Promotion, Validation, And Rollback Execution

The implementation should define concrete mechanics for:

- environment promotion
- release verification before promotion
- pre-deploy and post-deploy checks
- automatic or manual rollback triggers
- failed deployment handling

This section should become the operational reference for rollout behavior.

---

## Repository Tasks, Scripts, And Automation

The implementation should also specify the repository surfaces that realize the pipeline and updater plan.

These should include:

- CI workflow definitions
- manifest generation utilities
- packaging scripts
- deployment or update tasks
- validation scripts
- health-check and rollback support tasks

This is the bridge between the proposal and executable repository automation.

---

## Recommended Next Implementation Steps

A practical first implementation sequence is:

1. define manifest schema for Docker and APK release classes, including lifecycle state fields and component compatibility data
2. define authority endpoints for release eligibility, manifest resolution, lifecycle reporting, and rollback reporting
3. implement a local updater service contract that polls authority by `installation_uuid`
4. implement Docker publication flow for first-batch packaged services
5. implement component-only Docker update flow for `vmeta` as the first concrete updater path
6. define app artifact publication flow for APK or app deliverables
7. define the Windows installer and private registry execution path against those manifests
8. add operational tasks and validation scripts for release testing
9. connect promotion and rollback behavior to authority reporting

This sequence keeps policy, packaging, delivery, and lifecycle control aligned from the start.
