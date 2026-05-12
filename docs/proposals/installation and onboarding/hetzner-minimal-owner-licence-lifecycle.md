# Hetzner Minimal Owner And Licence Lifecycle

**Date**: May 11, 2026  
**Status**: Partially Implemented  
**Scope**: First-user onboarding, owner verification, installation identity, subscription-backed licence validation, and offline alerting for a local installation  
**Depends On**: [docs/proposals/node-user-management-target-design.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-target-design.md), [docs/proposals/node-user-management-implementation-plan.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-implementation-plan.md), [docs/COMMUNICATIONS_SERVICE_INTEGRATION.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/COMMUNICATIONS_SERVICE_INTEGRATION.md)

---

## Implementation Status

This document describes the current MVP authority flow and the gaps that still remain.

The following are currently implemented:

- Hetzner-hosted authority service with SQLite-backed entitlement storage
- private operator admin UI at `https://authority.eyenet-vision.com/admin`
- first-user owner assignment via online approval during local registration
- Node authority activation using local installation UUID, application key, and user email
- periodic Node authority refresh worker
- cached owner/licence state with offline grace timestamps
- frontend visibility for authority state in Settings and Profile
- local Settings fields for authority application key and installation UUID

The following are still incomplete or intentionally simplified:

- no customer self-service owner-claim workflow
- no dedicated banner-based frontend alerting for stale or expired authority state
- no automatic local owner-role demotion workflow after revocation
- no richer subscription-plan model beyond the MVP licence-state fields
- no fully separate heartbeat contract beyond the current activation plus installation lookup flow

So the platform is no longer operating on a purely local first-user owner model. The running system now uses a hybrid local Node plus online authority model for first-owner approval and cached ongoing validation.

---

## Purpose

This document describes the minimal online ownership and licence lifecycle for a local installation of the platform.

The platform runs primarily on local hardware, but ownership and subscription state are anchored to an online authority hosted on Hetzner.

The goal is to answer these questions in a practical way:

1. how the first user becomes the installation owner
2. how the local app knows whether that owner is still valid
3. how licensing and subscription status are checked over time
4. what happens when the installation temporarily has no internet access
5. how to do this with the smallest viable online service footprint

---

## Problem Statement

The platform is a local application, so it must continue to function during internet outages. At the same time, owner status and licence validity should not be purely local, because:

- local-only owner assignment is hard to govern safely
- ownership recovery needs an external source of truth
- subscription licence status needs an external authority
- installations need a durable identity beyond one local database state

So the platform needs a hybrid model:

- local-first operation
- online authority for ownership and licence verification
- periodic synchronization
- user-visible status for stale or failed checks

---

## Current High-Level Flow

Use the Hetzner-hosted authority service as the source of truth for:

1. entitlement registration
2. owner approval status
3. application key issuance and lookup
4. licence status
5. installation binding during first activation

The local Node service remains the authority for:

- local user records
- local login
- local role and capability enforcement
- local cached view of owner and licence state

### Local Node Service

- authenticates local users
- stores local installation identity
- stores cached authority state and timestamps
- persists effective authority application key and installation UUID in app settings
- decides whether first-user owner onboarding should grant `owner`

### Hetzner-Hosted Online Service

- stores entitlement records
- stores approved owner email per entitlement
- stores application key and licence state
- binds an entitlement to a real installation UUID on activation
- returns authoritative status for installation and owner checks

---

## Core Design Principle

The first local user does not become the final owner purely because they registered first.

Instead, the first local user becomes the owner only if the online authority confirms that this user is the approved owner for the supplied application key and installation.

So the real model is:

- operator seeds or updates entitlement centrally
- first local user registers
- Node sends activation request to the online authority
- local installation assigns `owner` only after confirmation

That avoids making first-login order the true security rule.

---

## Minimal Entities

### 1. Entitlement

Represents the centrally managed authority record.

Current MVP fields:

- `entitlement_uuid`
- `installation_uuid` optional until activation
- `application_key`
- `approved_owner_email`
- `owner_enabled`
- `licence_status`
- `offline_grace_days`
- optional `tenant_name`
- `activation_status`
- optional `notes`

### 2. Local Installation Identity

Represents one deployed local platform instance.

Current effective sources for `installation_uuid` are:

- configured env value
- persisted Node app setting
- generated local `InstallationInfo.guid`

### 3. Local Authority Cache

Represents the last known online authority state stored locally.

Current cached fields include:

- approved owner email
- licence status
- owner enabled flag
- offline grace days
- last checked timestamp
- last successful check timestamp
- last result reason

---

## Implemented First-User Onboarding Scenario

### Step 1. Operator Creates Or Updates Entitlement

In the authority admin UI, the operator creates or updates an entitlement with:

- approved owner email
- application key
- owner enabled flag
- licence status
- offline grace days
- optional installation UUID binding
- optional tenant name and notes

If the installation UUID is left blank, the entitlement remains available for first activation.

### Step 2. Local Node Is Provisioned

The local node must have:

- authority base URL
- application key
- optionally installation UUID

The application key and installation UUID can come from environment configuration or from the local Settings UI, which persists them through the Node app-settings API.

### Step 3. First User Registers Locally

When the first user registers locally:

- Node creates the local user account
- Node detects that this is the first user
- Node calls the authority activation endpoint with:
  - `installation_uuid`
  - `application_key`
  - `owner_email`

### Step 4. Authority Service Verifies Owner Eligibility

The authority service approves activation only when:

- the application key exists
- the user email matches `approved_owner_email`
- `owner_enabled` is true
- `licence_status` is `active` or `grace`
- the entitlement is not already bound to a different installation
- the local installation is not already bound to a different application key

If approved:

- the entitlement is bound to the real installation UUID
- activation status becomes `active`
- Node grants local roles `owner`, `admin`, and `user`

If not approved:

- the user remains a normal local `user`
- no local owner role is granted

### Step 5. Node Persists Effective Authority Values

After activation or refresh, Node persists the effective:

- application key
- installation UUID

This makes the local Settings view consistent with the real authority flow rather than requiring env-only configuration.

### Step 6. Local Cache Supports Ongoing Operation

Node stores cached authority state locally so the installation can continue operating during temporary connectivity loss.

---

## Periodic Owner And Licence Validation

### Why Periodic Validation Is Needed

Ownership and licence status can change after setup.

Examples:

- subscription cancelled
- owner transferred
- owner revoked
- application key suspended

So the local installation periodically re-checks with the authority service.

### Current Worker Model

Node now includes a periodic background worker that refreshes cached authority state.

Current behavior:

- interval controlled by `AUTHORITY_REVALIDATION_INTERVAL_SECONDS`
- current default implementation is 300 seconds
- worker starts with the Node service lifespan
- worker refreshes installation state from the authority service
- worker optionally validates owner state using the approved owner email from the installation record

### Current Validation Inputs

The refresh path uses:

- effective installation UUID
- effective application key

The owner-specific path also uses:

- approved owner email

### Local Action On Successful Check

Node updates:

- persisted effective application key
- persisted effective installation UUID
- cached approved owner email
- cached licence status
- owner enabled flag
- offline grace days
- last checked timestamp
- last successful check timestamp

If the online response is not approved, Node updates the cached state and reason fields. The current implementation does not yet perform automatic local role demotion; that remains a later policy hardening step.

---

## Offline Behavior

### Local App Constraint

The platform is local-first, so internet loss must not immediately lock out the installation.

### Current Offline Model

Use bounded offline grace based on the last successful authority check and the cached `offline_grace_days` value.

Current practical states are:

- `online_valid`
- `offline_within_grace`
- `offline_grace_expired`
- `not_approved`

### Current Behavior By State

#### `online_valid`

- normal operation
- cached authority state is current

#### `offline_within_grace`

- cached owner approval may still be treated as valid for offline verification
- local operation continues
- authority status view shows cached timestamps and grace information

#### `offline_grace_expired`

- cached owner approval is no longer accepted for offline owner verification
- the system records the failed or stale state
- no dedicated banner system exists yet

#### `not_approved`

- activation or refresh reports that authority approval is not currently valid
- no automatic product-wide restriction layer is enforced yet beyond the owner-approval logic itself

### Important Principle

Internet outage should produce:

- cached tolerance first
- visible status
- tighter restrictions later

not immediate full lockout.

---

## User Alerts And Visibility

The current implementation exposes authority state to local users, but not yet through a full alerting framework.

### Current Delivery Channels

- authority status card in frontend Profile and Settings
- backend authority status endpoint for the authenticated user
- local cached reason and timestamp fields for operator troubleshooting

### Not Yet Implemented

- persistent warning banners
- dedicated system health dashboard for authority state
- automated email alerts for stale authority checks

---

## Minimal Hetzner Architecture

The authority service is implemented as its own independent project under:

- `/Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-authority`

It remains separate from the local Node service so the online authority stays clearly independent from the local installation runtime.

### Current MVP Deployment Shape

The current MVP is materialized as:

1. a small backend API
2. a small private admin UI
3. one public HTTPS URL reachable by local installations

Current public URL:

- `https://authority.eyenet-vision.com`

Current private operator UI:

- `https://authority.eyenet-vision.com/admin`

### Current Admin Responsibilities

The admin UI is used to manage the core entitlement fields:

- `installation_uuid`
- `application_key`
- `approved_owner_email`
- `owner_enabled`
- `licence_status`
- `offline_grace_days`
- optional `tenant_name`
- optional `notes`

That is sufficient for the current owner/licence lifecycle.

---

## Current Minimal Endpoints

### `POST /api/v1/installations/activate`

Input:

- installation UUID
- application key
- owner email

Output:

- whether activation is approved
- reason
- entitlement UUID
- installation UUID
- application key
- approved owner email
- owner enabled
- licence status
- offline grace days
- tenant name
- activation status
- notes

### `GET /api/v1/installations/{installation_uuid}`

Input:

- installation UUID

Output:

- installation binding record for the active installation

### `GET /api/v1/owners/{email}`

Input:

- owner email

Output:

- whether the email is approved
- licence status
- owner enabled
- installation UUID
- activation status

---

## Application Key And Subscription Model

### Minimal Model

Each installation uses one application key.

That key is tied to:

- one entitlement record
- at most one bound installation UUID at a time
- one approved owner email
- one licence state

The key does not itself grant local ownership. It only allows the local installation to ask the authority whether ownership and licence state are valid.

### Why This Matters

The application key answers:

- is this installation known?
- is this installation licensed?

The approved owner email answers:

- which local user may hold the `owner` privilege?

These remain separate decisions.

---

## Current Minimal Lifecycle

### Stage 1. Create Entitlement In Authority Admin

- create or update the approved owner email
- issue or paste the application key
- optionally bind an installation UUID immediately
- set owner enabled, licence status, and offline grace days

### Stage 2. Configure Local Node

- configure authority service URL
- save the application key in local Settings or environment
- optionally save the installation UUID in local Settings or environment

### Stage 3. First Local User Registers

- local registration creates the user
- if it is the first user, Node calls authority activation
- if approved, Node grants `owner`, `admin`, and `user`
- otherwise the user remains a normal `user`

### Stage 4. Run Local Installation Normally

- periodic authority refresh keeps cached state current
- frontend shows authority state in Settings and Profile

### Stage 5. Handle Connectivity Loss Or Authority Failure

- local cache remains usable within offline grace
- failed checks are recorded with timestamps and reason fields
- later refreshes can restore approved state when connectivity returns

---

## Minimal Data Stored Locally

The local installation stores enough state to remain stable offline.

Current local state includes:

- effective installation UUID
- effective application key
- cached approved owner email
- cached licence status
- cached owner enabled flag
- offline grace days
- last checked timestamp
- last successful check timestamp
- last result reason

This is treated as a cache of the online authority, not the final source of truth.

---

## Security And Governance Notes

### 1. Do Not Let Local First Login Alone Define Ownership

That is no longer the implemented policy. First-user owner grant now requires authority approval.

### 2. Keep Owner Validation And Licence Validation Coupled In The MVP, But Distinguishable

In the current MVP they travel together through the same entitlement record, but they still represent different governance concerns.

### 3. Never Require Continuous Internet For Basic Local Use

That remains a poor fit for a local installation product.

### 4. Delay Harsh Enforcement Until The Product Policy Is Finalized

The current system validates and surfaces state, but does not yet implement the harshest automatic demotion or lockout consequences.

---

## Current MVP Implementation Summary

### Local Node Changes

1. first-user registration activates ownership against the online authority
2. effective application key and installation UUID can come from env or persisted app settings
3. startup/lifespan includes periodic authority refresh
4. authority state is cached locally with timestamps and grace metadata
5. frontend exposes current authority state in Profile and Settings

### Hetzner Service Changes

1. entitlement registry stored in SQLite
2. activation endpoint for first binding
3. installation lookup endpoint
4. owner-status lookup endpoint
5. private operator admin UI for entitlement management

### Current Policy Choice

The current policy is:

- exactly one approved owner email per entitlement
- exactly one application key per entitlement
- bounded offline grace via `offline_grace_days`
- first-user owner assignment only after online approval

That is enough to operate the current lifecycle without overbuilding.

---

## Open Decisions

The current MVP still leaves these decisions open:

1. should owner revocation trigger automatic local role demotion or only effective owner-action blocking?
2. what frontend alerting model should exist for stale or expired authority state?
3. what minimum product features remain available when licence state is not approved?
4. should application keys be rotatable from the authority admin, and what migration flow should that use?
5. should future versions replace approved-owner email matching with a stronger central identity model?

---

## Recommended Conclusion

The implemented minimal model is not “first local user becomes owner forever.”

The implemented model is:

- local app with bounded offline tolerance
- Hetzner-hosted online authority for installation, owner, and licence status
- first-user onboarding only grants owner when the online service approves it
- periodic refresh keeps the local cached status current
- authority state is visible in the local UI and settings

That gives a practical ownership and subscription lifecycle suitable for a local installation product while keeping the central governance model small enough to operate now.