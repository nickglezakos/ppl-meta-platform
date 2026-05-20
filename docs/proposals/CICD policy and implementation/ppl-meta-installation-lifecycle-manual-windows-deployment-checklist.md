# PPL Meta Manual Windows Deployment Checklist

**Date**: May 18, 2026  
**Status**: Draft  
**Scope**: Developer walkthrough for manually validating a Windows deployment against the production authority service, GitHub Container Registry release images, the local installer assets, and the Windows installer path  
**Related Documents**: [docs/proposals/CICD policy and implementation/ppl-meta-installation-lifecycle-cicd-policy.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md), [docs/proposals/CICD policy and implementation/ppl-meta-installation-lifecycle-cicd-implementation-plan.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-implementation-plan.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md), [docs/proposals/installation and onboarding/real-installation-uuid-and-application-key-onboarding-flow.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/real-installation-uuid-and-application-key-onboarding-flow.md)

---

## Purpose

This document is the developer-facing manual test checklist for validating the current installation lifecycle design on a real Windows machine.

The target scenario is:

- production authority service online
- release images published to GitHub Container Registry
- local installer assets prepared from this repository
- Windows installer or Windows installer script used on the target machine
- first-user onboarding completed against the production authority service
- local updater behavior validated with at least one component update scenario

This checklist is intentionally operational. It is meant to be followed step by step and marked off during a real deployment rehearsal.

---

## Test Goal

By the end of this walkthrough, you should have proven that:

1. a release exists in GitHub Container Registry and is consumable by the Windows deployment path
2. the production authority service can hold a pending entitlement for the target owner
3. the Windows machine can install the pinned platform bundle without local image builds
4. the installed node can activate against the production authority service using a real `installation_uuid` and `application_key`
5. first-owner onboarding succeeds only for the approved owner email
6. the installation reports healthy runtime state after deployment
7. a component-only update path can be validated for a service such as `vmeta`

---

## System Under Test

This checklist assumes the following roles:

- authority runs online at the production authority URL
- GitHub Container Registry stores the pinned Docker release images
- the Windows machine runs the platform locally through Docker Desktop
- the local updater logic runs on the Windows machine, even if the first pass is manually simulated by the developer

This means authority decides approved state, but the Windows host performs the actual pull, restart, health check, and rollback work.

---

## Inputs You Must Prepare Before Starting

You should not start the test until all of the following exist.

### Release Inputs

- platform release version to test, for example the current repository [VERSION](/Users/nickgklezakos/Documents/ppl-meta-code/VERSION)
- exact image list and tags for that release
- any compose files, env templates, and installer assets required by the Windows path
- release notes or known caveats for the selected build

### Authority Inputs

- production authority base URL
- platform admin credentials for the authority admin UI
- approved owner email for the test customer
- application key or the ability to create one through the authority admin UI
- licence or entitlement settings for the test installation

### Registry Inputs

- GitHub Container Registry namespace
- registry username
- registry access token with package read access
- confirmation that the required release images are already published

### Windows Test Machine Inputs

- dedicated Windows machine or clean VM
- Docker Desktop installed
- enough free disk space for pinned image pulls and writable volumes
- network path to the production authority service
- network path to `ghcr.io`
- permission to run PowerShell installer scripts

---

## Recommended Evidence Collection

For each major step, capture evidence so the test can be reviewed later.

Recommended evidence:

- screenshots of authority records
- copied terminal output for release verification and installer steps
- saved health-check responses
- installation UUID value captured after first startup
- owner activation success evidence
- update and rollback evidence if tested

Store the evidence under a dated test folder outside the target Windows runtime directory.

---

## Phase 1: Verify Release Availability

Goal: prove the release exists and is pullable before involving the Windows machine.

Checklist:

- confirm the platform release version under test
- confirm the expected service image list for that release
- verify the required GHCR manifests exist
- confirm image naming matches the installer expectation
- confirm there is no dependency on `latest`

Suggested verification commands from a machine with Docker access:

```bash
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:<release>
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:<release>
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:<release>
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:<release>
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:<release>
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:<release>
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend:<release>
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision-protected:<release>
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta-protected:<release>
```

Pass criteria:

- every required image tag returns manifest JSON
- the selected release can be described as one pinned platform bundle

---

## Phase 2: Prepare Production Authority State

Goal: create the online state needed for real first activation.

Checklist:

- log in to the production authority admin UI
- create a pending entitlement for the test customer
- set the approved owner email
- assign or confirm the application key
- set licence or entitlement status so activation is allowed
- record the entitlement identifier if available
- confirm the entitlement is still unbound to a real installation UUID before Windows activation

Record these values:

- authority base URL
- approved owner email
- application key
- entitlement status
- any plan or support metadata relevant to eligibility

Pass criteria:

- the production authority service contains a pending activation record for the test owner
- the test owner email is clearly the approved first owner

---

## Phase 3: Prepare Local Installer Assets

Goal: make sure the Windows deployment bundle is complete before moving to the target machine.

Checklist:

- identify the exact local installer assets required from this repository
- confirm the correct env template is available
- confirm the expected compose or startup assets reference pinned release tags
- confirm the assets point to the production authority URL, not a local authority instance
- confirm the assets do not embed development-only identifiers such as fake installation UUIDs
- confirm the assets support registry login for GHCR

Expected outputs of this phase:

- installer bundle or script package ready to transfer to Windows
- env template prepared for the selected production-authority test
- documented list of values the Windows operator must enter during installation

Pass criteria:

- the deployment bundle is self-consistent and points at production authority plus GHCR

---

## Phase 4: Prepare The Windows Machine

Goal: prove the target machine is a valid installation host before pulling any images.

Checklist:

- start from a clean or known testable Windows environment
- verify Docker Desktop is installed
- verify Docker Desktop is running
- verify `docker version` succeeds
- verify `docker info` succeeds
- verify enough disk space exists before any image pulls
- verify required ports are not already occupied by conflicting services
- verify outbound connectivity to the production authority URL
- verify outbound connectivity to GHCR
- verify PowerShell execution policy permits the installer path you intend to use

Suggested checks:

```powershell
docker version
docker info
Test-NetConnection authority.eyenet-vision.com -Port 443
Test-NetConnection ghcr.io -Port 443
```

Pass criteria:

- Docker Desktop is healthy
- the Windows host can reach both authority and GHCR
- the machine is ready for installer execution

---

## Phase 5: Install The Platform On Windows

Goal: perform the real Windows deployment without building images locally.

Checklist:

- copy the installer bundle or scripts to the Windows machine
- create the local env file from the template if required
- provide production authority URL
- provide the application key prepared in authority
- provide GHCR credentials or token when prompted
- run the Windows installer or installer PowerShell path
- confirm the installer pulls pinned images instead of building them locally
- confirm local config is written successfully
- confirm containers are started
- confirm initial health checks run

Capture evidence for:

- successful GHCR authentication
- exact pulled image tags
- resulting local env/config values except secrets
- installer success output

Pass criteria:

- the platform is installed from pinned remote images
- no local image build is needed on Windows
- the local stack starts successfully

---

## Phase 6: Validate Local Runtime Before Owner Activation

Goal: verify the machine is alive locally before first-user onboarding.

Checklist:

- inspect running containers
- inspect logs for obvious startup failures
- verify local service health endpoints if available
- confirm the local node generated or persisted a real `installation_uuid`
- capture that `installation_uuid` value for later cross-checking with authority
- verify the machine is still using the intended production authority URL

Pass criteria:

- the local runtime is healthy enough to attempt activation
- a real `installation_uuid` exists locally

---

## Phase 7: Complete First-Owner Activation Against Production Authority

Goal: prove the new installation can bind to the pending online entitlement.

Checklist:

- open the local first-user onboarding flow
- register using the same approved owner email configured in the production authority service
- complete local account creation
- verify the local node sends activation using `email`, `application_key`, and `installation_uuid`
- verify activation succeeds
- verify the user receives owner-capable access only after authority approval
- verify the production authority record now shows the real bound `installation_uuid`

Negative-path check:

- attempt the same onboarding with a different non-approved email on a reset test machine or controlled test path
- verify authority rejects owner activation for the unapproved email

Pass criteria:

- approved owner email can activate successfully
- non-approved email cannot silently become owner
- the authority record is now bound to the real installation UUID from the Windows machine

---

## Phase 8: Validate Healthy Steady State

Goal: verify the deployed installation reaches the expected post-activation state.

Checklist:

- verify the local user can log in as the activated owner
- verify the local platform is operational enough for smoke testing
- verify the authority-linked configuration is persisted locally
- verify the authority service shows the installation as active
- verify local and authority-visible status is consistent
- capture the currently running service versions or image tags

Pass criteria:

- the installation is healthy and attributable to a real authority-backed installation record

---

## Phase 9: Validate Component-Only Update Flow

Goal: prove the lifecycle can handle a service-level update such as `vmeta` without implying a full-stack reinstall.

This phase may be executed manually before the dedicated local updater service exists, as long as the manual procedure follows the same lifecycle discipline.

Checklist:

- publish or identify a newer approved `vmeta` image version in GHCR
- update the authority-side target manifest or release policy for the test installation
- confirm the installation is eligible for that `vmeta` update
- from the Windows machine, resolve the approved target state
- pull the new `vmeta` image only
- stage the update with preflight checks
- replace only the local `vmeta` container unless dependencies require more
- run health validation
- record whether the installation reaches `healthy`
- report or record the lifecycle transitions `approved`, `downloaded`, `staged`, `applied`, and `healthy`

Pass criteria:

- the Windows machine can move only `vmeta` to the new approved image version
- the rest of the stack remains unchanged unless compatibility rules say otherwise
- the resulting installation remains healthy

---

## Phase 10: Validate Failure Handling And Rollback

Goal: prove the deployment path does not leave the machine in silent drift when an update fails.

Checklist:

- identify a safe rollback candidate such as the previous known-good `vmeta` image
- simulate or trigger a controlled failed update condition if safe to do so
- verify the update path records failure
- verify the machine can revert to the prior known-good image
- verify post-rollback health
- verify authority or test records show a `rolled_back` or `failed` outcome

Pass criteria:

- rollback is possible and leaves the installation healthy again
- failure is visible, not silent

---

## Final Sign-Off Checklist

Mark the rehearsal complete only if all of the following are true.

- release images were verified in GHCR before installation
- production authority entitlement was prepared before first activation
- Windows installation used pinned remote images and not local builds
- a real `installation_uuid` was created or persisted locally
- approved owner activation succeeded against production authority
- non-approved owner path was rejected or blocked
- the installation reached healthy steady state
- at least one component-only update path was exercised or explicitly deferred with reason
- rollback behavior was exercised or explicitly deferred with reason
- evidence was captured for each major phase

---

## Known Failure Points To Watch Closely

These are the failure points most likely to invalidate the test.

- GHCR credentials do not permit package pulls
- installer assets still point to a local or development authority URL
- env files still contain development-only installation identifiers
- Docker Desktop is installed but not actually healthy
- first-user onboarding does not bind the real installation UUID back to authority
- local runtime succeeds but authority state remains unbound or inconsistent
- `vmeta` update path accidentally forces broader stack drift

---

## Developer Notes After Each Rehearsal

After completing the walkthrough, record:

- release version tested
- Windows environment details
- authority environment used
- exact installer assets used
- exact failure points encountered
- whether the checklist was missing any real prerequisite or verification step
- what must change before the next rehearsal

This document should be updated after each real deployment rehearsal until the Windows deployment path is routine and the local updater behavior is fully automated.
