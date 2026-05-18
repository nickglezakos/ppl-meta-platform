# Updating Installations

**Date**: May 18, 2026  
**Status**: Proposal  
**Scope**: Define how existing PPL Meta installations, services, and applications should be updated over time using a durable installation UUID, release metadata, and authority-aware update policy  
**Related Documents**: [docs/proposals/installation and onboarding/real-installation-uuid-and-application-key-onboarding-flow.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/real-installation-uuid-and-application-key-onboarding-flow.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md), [docs/proposals/installation and onboarding/hetzner-authority-and-node-integration-status-report.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/hetzner-authority-and-node-integration-status-report.md)

---

## Purpose

This proposal describes how deployed PPL Meta installations should be updated after the initial onboarding and activation flow is complete.

The main goal is to make updates safe, traceable, and compatible with the installation identity model introduced in the Real Installation UUID And Application Key Onboarding Flow proposal.

The core recommendation is:

1. every customer installation owns a durable `installation_uuid`
2. every service or application instance reports its current version against that installation identity
3. update policy is evaluated against the installation identity and its licence or entitlement state
4. updates are delivered as controlled release transitions, not as ad hoc manual file replacement

This lets the platform answer three critical questions for every upgrade:

- which installation is being updated
- which software components are currently installed
- whether that installation is allowed to receive the requested release

---

## Problem

The platform already has a proposal for first activation and owner onboarding, but it still needs a clear model for how already deployed installations should evolve over time.

Without a proper update model, the system risks the following problems:

- releases being applied without a durable installation identity
- no reliable link between a deployed machine and its authority-backed entitlement
- services drifting to incompatible versions across the same customer environment
- no clear policy for partial updates, blocked updates, or rollback
- no clean way to audit which installation moved from one release to another
- no stable way to decide whether an update is allowed for a given licence or support status

The missing piece is an update lifecycle that continues after onboarding instead of treating installation as a one-time event.

---

## Key Recommendation

The same `installation_uuid` used for onboarding should remain the permanent identity anchor for update operations.

That means:

- the installation UUID is created once and persisted locally
- the installation UUID is bound to authority during activation
- all later update checks and release reporting use that same installation UUID
- a reinstall that keeps the same logical customer deployment should only retain that identity through an explicit recovery or transfer policy

This is important because updates should apply to an identified installation, not just to a machine that happens to have some config files.

---

## Recommended Identity Model

The update lifecycle should distinguish between three identity scopes.

### 1. Installation Identity

This is the main durable identifier for the customer deployment.

Suggested field:

- `installation_uuid`

This UUID should represent the full deployed platform instance, not a single process.

### 2. Application Or Service Identity

Each major PPL Meta application or service should also expose a stable component identifier within the installation.

Suggested fields:

- `component_name`
- `component_type` such as `backend_service`, `frontend_app`, `edge_app`, `worker`
- `component_instance_id` if multiple instances of the same component can exist

In the simplest MVP, `component_name` is enough for the core stack:

- `ppl-meta-node`
- `ppl-meta-media`
- `ppl-meta-gateway`
- `ppl-meta-orchestrator`
- `ppl-meta-discovery`
- `ppl-meta-communications`
- `ppl-meta-frontend`
- `ppl-meta-vision`
- `ppl-meta-vmeta`

### 3. Release Identity

Every update decision should refer to an explicit release target.

Suggested fields:

- `release_version`
- `release_channel` such as `stable`, `pilot`, `internal`
- `release_published_at`
- `minimum_data_contract_version` if needed later

---

## Update Model

The recommended model is installation-scoped release management.

In that model:

1. the authority service or release service knows which releases are available
2. the local installation reports its current installed versions under one `installation_uuid`
3. the update system decides whether the installation may move to a target release
4. the update is executed in a controlled sequence
5. the installation reports the result back against the same installation UUID

This is better than allowing each service to update independently without coordination because the platform has cross-service compatibility requirements.

---

## Why Installation UUID Must Survive Into The Update Flow

The onboarding proposal already establishes that a real local installation UUID is the correct identity anchor.

The update proposal should extend that rule.

The installation UUID should be used to:

- fetch eligible releases
- validate licence or support status before update
- attach update history to a real installation record
- detect duplicated or conflicting deployments
- coordinate rollback and recovery decisions
- support future fleet management or remote support tooling

Without this, the authority service can approve onboarding but still have no durable control point for ongoing lifecycle management.

---

## Recommended Update Lifecycle

The following is the recommended lifecycle for updating an existing installation.

### Step 1. Installation Reports Current State

Before downloading or applying an update, the local installation should know and optionally report:

- `installation_uuid`
- current platform release version
- current version of each installed service or application
- health summary
- optional OS and deployment mode metadata such as `docker`, `windows_installer`, or `local_python`

This creates a clear baseline.

### Step 2. Update Eligibility Is Evaluated

The authority or release service should decide whether that installation is allowed to update.

Minimum checks:

- installation exists and is active
- licence or entitlement is valid enough for update access
- release is allowed for that installation's channel
- current version can safely move to target version
- no policy block such as revoked, suspended, or unsupported state

### Step 3. Installation Fetches A Release Manifest

The update system should resolve a release manifest that defines exactly what to install.

Suggested manifest contents:

- target `release_version`
- exact image tags, package versions, or binaries per component
- required migration steps
- restart order
- health checks
- rollback guidance

This prevents the installation from constructing a release ad hoc.

### Step 4. Installation Performs Preflight Checks

Before applying the update, the local updater should verify:

- sufficient disk space
- required network access
- writable config and data locations
- backup or rollback prerequisites
- no conflicting local process state
- database migration readiness if applicable

### Step 5. Installation Applies The Update In Order

The update should run in a controlled order.

A practical order is:

1. backup current config and critical metadata
2. download or pull target artifacts
3. stop affected services
4. apply schema or data migrations if needed
5. start updated services in dependency order
6. run health checks
7. mark release active only after successful validation

### Step 6. Installation Reports Update Result

After the update attempt, the system should record:

- `installation_uuid`
- previous release version
- target release version
- success or failure state
- failure reason if any
- timestamp
- resulting component versions

### Step 7. Rollback Or Recovery Runs If Needed

If validation fails, the updater should either:

- roll back automatically to the previous known-good release, or
- stop in a recoverable maintenance state with explicit operator guidance

---

## Recommended Data Model

The authority or release service should evolve toward installation-aware update records.

### 1. Installation Record

Suggested fields:

- `installation_uuid`
- `entitlement_uuid`
- `application_key`
- `approved_owner_email`
- `tenant_name`
- `activation_status`
- `licence_status`
- `release_channel`
- `current_release_version`
- `last_seen_at`

### 2. Installation Component State

Suggested fields:

- `installation_uuid`
- `component_name`
- `component_type`
- `component_instance_id`
- `current_version`
- `reported_at`
- `health_state`

### 3. Installation Update History

Suggested fields:

- `update_event_uuid`
- `installation_uuid`
- `from_release_version`
- `to_release_version`
- `requested_at`
- `started_at`
- `completed_at`
- `status` such as `pending`, `running`, `succeeded`, `failed`, `rolled_back`
- `failure_reason`
- optional operator metadata

### 4. Release Manifest Record

Suggested fields:

- `release_version`
- `release_channel`
- `manifest_payload`
- `minimum_supported_from_version`
- `published_at`
- `active`

---

## Update Policy Recommendations

The update system should have explicit policy instead of assuming every active installation always gets every release.

Recommended MVP policy:

- one installation UUID maps to one logical customer deployment
- updates are allowed only for active and non-revoked installations
- release access may depend on licence state or support entitlement
- upgrades should target approved release channels only
- skipping too many versions at once may be blocked if migrations are unsafe
- rollback should be supported for the immediately previous release whenever practical

---

## Service And Application Responsibilities

Each PPL Meta service or application should participate in the update model in a small but consistent way.

Minimum expectations:

- expose component name and version
- expose health status
- tolerate controlled restart during coordinated update
- read installation identity from shared local configuration or platform settings
- avoid generating its own unrelated installation identity

The platform should not allow every service to invent a separate top-level customer identity.

There should be one installation UUID for the deployment and component-level identifiers beneath it.

---

## Local Persistence Requirements

The local installation should persist enough state to survive restarts and support recovery.

Minimum persisted values:

- `installation_uuid`
- `application_key`
- current release version
- last known-good release version
- installed component versions
- last successful update timestamp
- update channel if applicable

This local state should be treated as platform metadata, not as transient installer-only data.

---

## Relationship To The Installer

The installer and the updater are related but should not be treated as the same lifecycle step.

The installer handles:

- first setup
- initial environment validation
- first artifact pull or install
- first activation prerequisites

The updater handles:

- moving an already activated installation to newer releases
- validating update eligibility against the existing installation UUID
- preserving data and service continuity across versions

The same installation UUID should bridge both phases.

---

## Relationship To Authority Service

The authority service does not need to perform the entire software update itself, but it should remain the policy source of truth for whether an installation is eligible for updates.

Recommended authority responsibilities:

- know the installation UUID and entitlement status
- determine whether updates are allowed
- optionally return release channel or release entitlement
- record last successful version reported by the installation
- optionally record update history for support and audit

A separate release service could own manifest publishing, but policy should still be keyed by `installation_uuid`.

---

## Suggested API Contract

### Installation State Report

Suggested request:

- `installation_uuid`
- `current_release_version`
- `components[]` with name and version
- `health_state`

Suggested response:

- accepted state report
- optional recommended release
- optional policy flags

### Update Eligibility Check

Suggested request:

- `installation_uuid`
- `current_release_version`
- `target_release_version`

Suggested success response:

- `allowed = true`
- `release_channel`
- `manifest_url` or embedded manifest reference
- optional upgrade notes

Suggested failure reasons:

- `unknown_installation`
- `installation_not_active`
- `licence_inactive`
- `update_not_permitted_for_channel`
- `unsupported_upgrade_path`

### Update Result Report

Suggested request:

- `installation_uuid`
- `from_release_version`
- `to_release_version`
- `status`
- `failure_reason`
- `components[]`

Suggested response:

- update event recorded
- optional remediation flags

---

## Special Cases That Need Explicit Policy

### 1. Partial Component Updates

Recommended MVP:

- avoid arbitrary partial upgrades for the core platform stack
- publish a coordinated platform release that pins compatible component versions

### 2. Offline Installations

Recommended MVP:

- allow a local update package only if it still targets a known release manifest
- require deferred reporting when connectivity returns

### 3. Failed Update Midway

Recommended MVP:

- keep the previous release metadata until health checks confirm the new release
- do not mark the installation as upgraded before validation succeeds

### 4. Reinstall On The Same Customer Site

Recommended MVP:

- treat reinstall identity reuse as a recovery flow, not as a silent new installation
- preserve or rebind the original installation UUID through explicit policy

### 5. Multi-Node Or Edge Deployments

Recommended later extension:

- keep one top-level installation UUID for the deployment
- allow subordinate component instance IDs for edge devices or secondary workers

---

## Recommended MVP Implementation Order

### Step 1. Make Installation UUID A Permanent Local Platform Setting

Ensure the installation UUID created during onboarding is stored durably and reused by updater flows.

### Step 2. Standardize Version And Health Reporting

Ensure each major service and application can report component name, version, and health under the installation identity.

### Step 3. Introduce Release Manifest Delivery

Publish explicit platform releases with pinned component versions instead of relying on manual per-service updates.

### Step 4. Add Update Eligibility Checks

Use the authority-backed installation record to decide whether an installation may move to a target release.

### Step 5. Add Update History And Rollback Metadata

Record upgrade attempts and preserve enough local state to recover safely.

---

## Bottom Line

PPL Meta should treat software updates as a continuation of the installation lifecycle, not as a separate unmanaged process.

The recommended model is:

- one durable `installation_uuid` per logical customer installation
- component-level service and application version reporting beneath that installation
- authority-aware update policy keyed by installation identity
- manifest-based coordinated release transitions
- explicit success, failure, and rollback handling

This keeps the update process compatible with the real onboarding proposal and gives the platform a clean foundation for support, audit, release control, and future fleet management.