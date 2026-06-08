# Licence Lifecycle Proposal

This document proposes the target licence lifecycle for the EyeNet platform across Authority, Node, and frontend.

The goal is to make Authority the single source of truth for licence state, keep the application key server-side, and define a predictable transition from normal operation to warning mode and then to safeguard mode.

## Title

Authority Licence Lifecycle Proposal

## Scope

This proposal covers:

- the authoritative licence states managed by Authority
- the Node-side validation and cache model
- the frontend warning and safeguard behavior
- the difference between online status, warning period, and offline grace
- the operational ownership of each field

This proposal does not cover:

- billing workflows
- reseller contracting details
- commercial notifications outside the platform UI

## Core Principles

### 1. Authority is the single source of truth

Authority owns the licence record and all mutable licence lifecycle controls.

Authority must be the only place where the following values can be edited:

- licence status
- owner enabled state
- warning period in days
- offline grace days
- approved owner mapping
- licence metadata such as licence name and tenant name

Node must never be the place where an operator edits post-bootstrap licence state.

### 2. The application key stays server-side

The application key is a machine credential.

It may be entered only during bootstrap binding. After bootstrap is complete:

- the application key must not be editable from the normal settings views
- the application key must not be rendered to the frontend
- Node keeps using it internally to resolve the Authority licence record

### 3. Safeguard is a backend enforcement mode

Safeguard must be enforced by Node, not by the frontend.

The frontend may display licence state and warnings, but it must not be responsible for deciding whether the installation can continue operating.

## Proposed Lifecycle Model

## Authority-Controlled Fields

Each Authority installation or entitlement record should expose at least:

- `application_key`
- `installation_uuid`
- `licence_status`
- `owner_enabled`
- `approved_owner_email`
- `licence_name`
- `tenant_name`
- `warning_period_days`
- `offline_grace_days`
- `warning_started_at` or another equivalent timestamp that defines when the warning window began
- optional `safeguard_reason`

### Meaning of the new field

`warning_period_days` is the number of days the installation may continue to operate after entering a warning-triggering licence condition before Node moves into safeguard mode.

This field must be editable in Authority only.

Node and frontend may read it, but they must not modify it.

## Licence State Categories

The platform should treat licence conditions in four runtime categories.

### 1. Valid

Installation remains fully operational.

Conditions:

- `owner_enabled = true`
- `licence_status in {active, grace}`

Expected platform behavior:

- no blocking
- no warning banner
- normal operation

### 2. Warning

Installation remains operational, but a stable warning must be shown because the licence has entered a condition that will lead to safeguard if not resolved in time.

Typical triggers:

- `licence_status = suspended`
- `licence_status = expired`
- `licence_status = inactive`
- `owner_enabled = false`
- another Authority-defined non-valid status that still allows a temporary remediation period

Expected platform behavior:

- protected operations continue to work during the warning window
- a stable warning is shown on screen across the platform
- Node computes and exposes the warning deadline and remaining days
- Authority remains the only place where the operator can clear the condition

### 3. Safeguard

Installation is no longer allowed to continue normal protected operation.

Entry condition:

- the installation is in a non-valid licence condition
- and the warning period has elapsed

Expected platform behavior:

- Node blocks protected operations
- the frontend shows a persistent safeguard state
- only a limited recovery surface remains accessible

### 4. Offline Grace

Offline grace is not a normal commercial state. It is a resilience state used only when Authority cannot be reached.

Entry condition:

- last known online state was valid
- Authority is temporarily unreachable
- `now <= last_successful_validation + offline_grace_days`

Expected platform behavior:

- platform continues operating temporarily
- frontend shows an Authority connectivity warning if desired
- once offline grace expires without successful revalidation, Node enters safeguard

## Proposed Decision Model

Node should derive a single effective runtime state.

### Allowed states

Allowed operation should continue when either of the following is true:

- online state is valid
- Authority is unreachable, but cached valid state is still within offline grace
- online state is warning, but warning deadline has not passed

### Blocked states

Safeguard should activate when any of the following is true:

- online state is non-valid and warning deadline has passed
- online state is non-valid and no warning period is available
- Authority is unreachable and offline grace has expired
- no valid Authority state has ever been obtained for a bootstrapped installation

## Runtime Timeline

## Normal lifecycle

1. Bootstrap binds Node to an Authority application key.
2. Node resolves the Authority licence record by application key.
3. Authority returns metadata and lifecycle controls.
4. Node caches the resolved state and periodically revalidates.
5. Frontend shows only the derived status and metadata.

## Warning transition

1. Authority operator changes the licence into a non-valid status or disables owner access.
2. Authority sets or retains `warning_period_days`.
3. Node periodic revalidation detects the changed status.
4. Node computes `warning_deadline`.
5. Frontend shows a stable warning banner until the issue is cleared or the deadline passes.

## Safeguard transition

1. Warning deadline passes while the licence remains unresolved.
2. Node enters safeguard mode.
3. Node blocks protected routes and protected features.
4. Frontend renders a persistent safeguard state and recovery messaging.
5. Resolution can only happen by updating the licence state in Authority.

## Offline transition

1. Authority becomes unreachable.
2. Node checks the cached last successful valid state.
3. If within `offline_grace_days`, Node keeps operating temporarily.
4. If offline grace expires before a successful revalidation, Node enters safeguard.

## Warning Period Proposal

This section adds the new lifecycle behavior requested for the platform.

### Definition

The warning period is a configurable number of days during which a non-valid licence condition does not immediately move the installation into safeguard.

During this period:

- the platform remains operational
- a stable warning is always visible in the platform UI
- the operator is expected to resolve the issue in Authority

### Ownership

`warning_period_days` must be editable in Authority only.

Node must treat it as read-only input.

Frontend must display its effect, not edit it.

### Why it is separate from offline grace

`warning_period_days` and `offline_grace_days` solve different problems.

- `warning_period_days` handles known online commercial or administrative problems
- `offline_grace_days` handles temporary loss of connectivity to Authority

They must remain separate.

## Stable Warning UI Proposal

While the warning period is active, the platform should show a stable warning that is visible beyond the settings screen.

### Warning content

The warning should communicate:

- the installation is in a warning state
- the licence needs attention in Authority
- the deadline date or days remaining
- the reason if available, such as suspended, expired, owner disabled, or validation overdue

### Warning placement

The warning should be shown in a stable platform-level surface, not only in settings.

Recommended locations:

- global app shell banner
- dashboard header warning area
- settings Authority status card

The warning must persist across navigation until the condition is cleared or safeguard takes over.

## Safeguard Enforcement Proposal

Node should implement a central enforcement dependency or middleware for protected routes.

### Allowed during safeguard

These should remain accessible:

- login
- bootstrap status
- authority status
- health endpoints
- limited recovery or support endpoints

### Blocked during safeguard

These should be blocked:

- normal business workflows
- protected data mutation endpoints
- feature execution endpoints that require a valid licence

### Response shape

Blocked responses should include a machine-readable reason such as:

- `licence_warning_elapsed`
- `licence_expired`
- `licence_suspended`
- `licence_inactive`
- `authority_offline_grace_expired`

## Data Node Should Cache And Expose

Node should cache and expose these lifecycle-derived values from Authority:

- `licence_status`
- `owner_enabled`
- `licence_name`
- `tenant_name`
- `warning_period_days`
- `warning_started_at`
- `warning_deadline`
- `warning_days_remaining`
- `offline_grace_days`
- `last_successful_check_at`
- `cache_expires_at`
- `effective_runtime_state`
- `effective_runtime_reason`

Node should not expose the raw application key to the frontend.

## Recommended Effective Runtime States

Node should normalize raw Authority inputs into a smaller set of UI and enforcement states:

- `valid`
- `warning`
- `offline_grace`
- `safeguard`
- `not_configured`

This reduces frontend branching and keeps enforcement decisions centralized.

## Suggested Authority Rules

Authority should define which raw states enter warning first and which move directly to safeguard.

Recommended initial rule set:

- `active` -> valid
- `grace` -> valid
- `suspended` -> warning, then safeguard after warning period
- `expired` -> warning, then safeguard after warning period
- `inactive` -> warning, then safeguard after warning period
- `revoked` -> immediate safeguard
- `owner_enabled = false` -> warning, then safeguard after warning period

This rule set can be tuned later, but the distinction should live in Authority policy, not in frontend heuristics.

## Recommended Implementation Order

### Phase 1. Authority schema and API

Add Authority-side support for:

- `warning_period_days`
- warning start timestamp semantics
- optional normalized lifecycle reason

### Phase 2. Node runtime derivation

Add Node support for:

- fetching and caching warning-period fields
- deriving `valid`, `warning`, `offline_grace`, or `safeguard`
- central route enforcement for safeguard mode

### Phase 3. Frontend warning UX

Add frontend support for:

- global stable warning banner
- safeguard screen or blocked-state messaging
- Authority status rendering for warning deadline and remaining days

## Operational Recommendation

The platform should adopt this rule:

After bootstrap, Authority is the only place where licence lifecycle state may be changed.

Node is the enforcement and cache layer.

Frontend is the visibility layer.

That separation gives:

- one operational source of truth
- no application key exposure in the browser
- predictable warning behavior before safeguard
- explicit recovery flow for expired, suspended, or offline installations

## Summary

This proposal keeps the current design direction and extends it with a warning period that is editable only in Authority.

Recommended model:

- bootstrap binds the node once
- Authority remains the sole editor of lifecycle state
- Node revalidates and enforces
- frontend displays stable warnings and safeguard state
- safeguard activates when the licence is non-valid and the warning period has elapsed, or when offline grace has expired
