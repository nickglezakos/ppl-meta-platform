# Upgrading The Authority Server For The Installation Lifecycle

**Date**: May 18, 2026  
**Status**: Proposal  
**Scope**: Upgrade the existing authority service into an installation-lifecycle control plane with identity-aware update policy, first-class user management, customer and reseller dashboards, frontend alignment, and CI/CD support  
**Related Documents**: [docs/proposals/installation and onboarding/real-installation-uuid-and-application-key-onboarding-flow.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/real-installation-uuid-and-application-key-onboarding-flow.md), [docs/proposals/installation and onboarding/updating-installations.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/updating-installations.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md)

---

## Purpose

This proposal describes how the existing authority service at `autonomous/ppl-meta-authority` should evolve from a minimal installation lookup registry into a central platform service for onboarding, entitlement management, installation monitoring, update eligibility, and customer-facing dashboards.

The authority service should become an integral part of the full installation and update lifecycle, not just a small activation dependency.

The target outcome is:

1. the authority service remains the source of truth for `installation_uuid` ownership and entitlement state
2. the authority service participates in both first activation and later update eligibility checks
3. the authority service owns its own user accounts, sessions, roles, and invitations
4. owners can view the status of their own installations in web dashboards
5. resellers can manage groups of owner-linked installations and see aggregated operational views
6. the authority web UX matches the visual system already established by the existing web frontend
7. the authority service fits into a CI/CD model driven by versioned files, automation tasks, and release policy

---

## Current State

The existing authority service is intentionally small.

Today it already provides:

- health endpoints
- SQLite-backed installation storage
- public installation and owner lookup endpoints
- token-protected admin endpoints
- a minimal HTML admin page

However, the current implementation is still an MVP.

Current limitations:

- admin access depends on a single bearer token instead of real user accounts
- the admin UI is a static private operations page rather than a proper product surface
- there is no authority-owned identity model for platform owners, resellers, or support staff
- there is no dashboard model for installation status, release state, or update history
- there is no release or update policy model tied to installation identity
- the service is not yet positioned as a formal participant in CI/CD and release governance

So the needed upgrade is architectural, not cosmetic.

---

## Key Recommendation

The authority service should become the platform control plane for the post-install lifecycle.

That means it should own four connected responsibilities:

1. installation identity and entitlement authority
2. user, role, invitation, and dashboard access authority
3. release eligibility and update policy authority
4. web portal and operational visibility authority

This proposal does **not** recommend turning authority into the full local runtime orchestrator.

Instead, it should become the remote policy, identity, release, and visibility service that local installations consult throughout their lifecycle.

---

## Why This Must Align With Installation UUID

The installation proposals already establish that each logical customer deployment should own a durable `installation_uuid`.

That same identity must remain the top-level anchor in authority.

The upgraded authority service should use `installation_uuid` to:

- bind first activation to a real entitlement
- record installation ownership
- decide whether updates are allowed
- track current installed release version
- display installation health and update history in dashboards
- group installations under a reseller or customer account
- support support, audit, and recovery workflows

Without this, onboarding and update lifecycle policy will stay fragmented.

---

## Recommended Product Model

The authority service should be split conceptually into five product surfaces.

### 1. Installation Authority API

This remains the core machine-facing API.

Responsibilities:

- entitlement creation
- activation binding
- installation lookup
- periodic validation
- update eligibility checks
- release manifest access or release manifest delegation
- update result reporting

### 2. Authority User And Access Service

This becomes the human identity layer for the authority product itself.

Responsibilities:

- user registration by invitation or controlled onboarding
- login, logout, password reset, session lifecycle
- role assignment
- reseller-to-owner relationship management
- account disablement and recovery

### 3. Owner Dashboard

This is the customer-facing web surface.

Responsibilities:

- show owned installations
- show activation and licence status
- show current release version and health summary
- show pending or recommended updates
- show recent update history
- show support-relevant metadata

### 4. Reseller Dashboard

This is the multi-customer operational surface.

Responsibilities:

- invite owner accounts
- create and manage groups of owner-linked installations
- filter installations by customer, reseller, release, or health state
- view aggregate rollout status
- track activation progress and support exceptions

### 5. Platform Admin Dashboard

This remains the internal operational surface.

Responsibilities:

- issue entitlements
- assign reseller scope
- manage release channels
- publish update manifests or release metadata
- review blocked installations and failed updates
- manage recovery, transfer, or rebind flows

---

## User Management Recommendation

For simplicity and delivery speed, the authority service should reuse the user-management and role-capability ideas already implemented in the Node service.

This means reuse at the pattern and code level where practical, not by making authority depend directly on Node at runtime.

### What Should Be Reused

The Node service already has a useful model for:

- users
- roles
- capabilities
- system roles such as `owner`, `admin`, and `user`
- capability-based authorization

That model should be adapted for authority so that authority has its own database tables, auth flows, and policies while keeping naming and semantics compatible.

### Why Reuse Is Better Than Starting Fresh

- faster implementation
- less risk of inventing a second incompatible auth model
- easier role reasoning across the platform
- better future interoperability between local Node and remote authority workflows

### Authority-Specific Role Model

Recommended system roles for authority:

- `platform_admin`
- `reseller`
- `owner`
- `support`
- `viewer` if needed later

Recommended MVP rule set:

- `platform_admin` can manage releases, resellers, entitlements, and recovery operations
- `reseller` can create or invite owner accounts within delegated scope and view grouped installations
- `owner` can view and manage only the installations explicitly linked to that owner identity
- `support` can read operational status without owning commercial relationships

### Ownership Model Recommendation

The upgraded service should support both direct ownership and reseller-managed ownership.

Suggested relationship model:

- a reseller owns a portfolio or scope
- an owner belongs directly to one reseller scope or is independent
- one owner may be linked to one or more `installation_uuid` records
- a reseller may manage many owners and therefore many installations

This fits the requested model where resellers can issue and own groups of owner UUIDs while owners still get their own dashboards.

A more accurate data model than "owner UUID" is likely:

- authority `user_uuid` for the human account
- `installation_uuid` for the customer deployment
- a relation table connecting user scope to installation scope

---

## Invitation And Onboarding Model

The authority service should support invitation-driven onboarding for human users.

Recommended flows:

### Reseller Invitation Flow

1. platform admin creates or invites a reseller account
2. reseller accepts invitation and sets credentials
3. reseller receives scoped access to assigned tenant groups or customer portfolios

### Owner Invitation Flow

1. reseller or platform admin creates an entitlement and approved owner email
2. reseller or platform admin invites the owner to the authority portal
3. owner accepts invitation and creates authority credentials
4. owner sees the relevant installation records and activation status in the dashboard

This is better than keeping user access separate from entitlement issuance.

---

## Dashboard Requirements

### Owner Dashboard

Minimum owner dashboard widgets:

- installation cards keyed by `installation_uuid`
- licence and activation status
- current platform release version
- available update or update eligibility state
- health summary for key services
- last successful validation timestamp
- recent update history and failure reasons

### Reseller Dashboard

Minimum reseller dashboard capabilities:

- customer list with filters
- grouped installation status by owner or tenant
- rollout status by target release version
- activation funnel such as pending, active, blocked, suspended
- failed update queue
- invitation management for owner users

### Platform Admin Dashboard

Minimum platform admin capabilities:

- release and manifest management
- installation search by UUID, email, tenant, or reseller
- policy overrides and recovery operations
- entitlement issuance and revocation
- system-wide operational summaries

---

## Frontend UX And Styling Recommendation

The authority web product should adopt the visual system of the existing `ppl-meta-frontend` web application.

It should not remain a standalone inline-HTML page with its own separate styling direction.

### Recommended Approach

The authority dashboards should either:

1. be implemented as additional routes or a companion web app built from the same Flutter web design system, or
2. reuse the same theme tokens, typography choices, navigation patterns, and component language in a dedicated authority frontend package

### Why This Matters

- users should feel that authority is part of the same product family
- reseller and owner dashboards should not look like internal prototypes
- design duplication should be avoided
- shared frontend patterns reduce maintenance and speed delivery

### Minimum UX Alignment Requirements

- reuse the existing app theme palette and typography direction
- reuse shared shell patterns such as dashboard cards, forms, dialogs, and navigation
- support responsive web layouts for desktop-first operations with tablet tolerance
- keep auth, dashboard, invitation, and release views visually consistent with the existing frontend

### Explicit Recommendation

The current `GET /admin` HTML page should be treated as temporary.

The long-term authority UI should move to a proper frontend implementation using the same visual language as `ppl-meta-frontend`.

---

## Installation And Update Lifecycle Integration

The upgraded authority service should operate directly within the lifecycle proposed in [docs/proposals/installation and onboarding/updating-installations.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/updating-installations.md).

That means authority should support at least these machine-facing flows:

### 1. First Activation

Inputs:

- `application_key`
- `installation_uuid`
- `owner_email`

Outputs:

- activation accepted or rejected
- bound installation identity
- approved owner metadata
- licence and policy metadata

### 2. Installation State Reporting

Inputs:

- `installation_uuid`
- current platform release version
- component versions
- health summary

Outputs:

- recorded state
- optional guidance or warnings

### 3. Update Eligibility

Inputs:

- `installation_uuid`
- current release version
- target release version

Outputs:

- allowed or blocked decision
- release channel policy
- manifest reference or release metadata
- reason codes

### 4. Update Result Reporting

Inputs:

- `installation_uuid`
- update start and completion details
- resulting component versions
- success or failure state

Outputs:

- update event recorded
- dashboard visibility updated

This is the mechanism that makes authority a real part of the installation and update lifecycle rather than just a licence check service.

---

## Recommended Data Model Upgrades

The current MVP installation table is too small for the target lifecycle.

The authority service should evolve toward these core entities.

### 1. Authority User

Suggested fields:

- `user_uuid`
- `email`
- `password_hash`
- `display_name`
- `status`
- `created_at`
- `last_login_at`

### 2. Authority Role And Capability

Suggested fields:

- `role_uuid`
- `role_name`
- `capability_name`
- join tables for user-role and role-capability assignment

### 3. Reseller Scope

Suggested fields:

- `reseller_uuid`
- `account_user_uuid`
- `display_name`
- `status`

### 4. Owner Scope

Suggested fields:

- `owner_scope_uuid`
- `account_user_uuid`
- `approved_owner_email`
- optional `reseller_uuid`

### 5. Installation Record

Suggested fields:

- `installation_uuid`
- `entitlement_uuid`
- `application_key`
- `tenant_name`
- `activation_status`
- `licence_status`
- `release_channel`
- `current_release_version`
- `last_seen_at`
- optional `reseller_uuid`
- optional `owner_scope_uuid`

### 6. Installation Component State

Suggested fields:

- `installation_uuid`
- `component_name`
- `current_version`
- `health_state`
- `reported_at`

### 7. Update Event

Suggested fields:

- `update_event_uuid`
- `installation_uuid`
- `from_release_version`
- `to_release_version`
- `status`
- `failure_reason`
- `started_at`
- `completed_at`

### 8. Invitation Record

Suggested fields:

- `invitation_uuid`
- `email`
- `role_name`
- `issued_by_user_uuid`
- `reseller_uuid` if scoped
- `expires_at`
- `accepted_at`
- `status`

### 9. Release Manifest Metadata

Suggested fields:

- `release_version`
- `release_channel`
- `manifest_payload`
- `minimum_supported_from_version`
- `published_at`
- `active`

---

## API Surface Recommendation

The authority API should separate machine endpoints from human portal endpoints.

### Machine-Facing API

Suggested groups:

- `/api/v1/installations/activate`
- `/api/v1/installations/report-state`
- `/api/v1/installations/check-update`
- `/api/v1/installations/report-update-result`
- `/api/v1/releases/{version}` or manifest lookup

### Human Auth API

Suggested groups:

- `/api/v1/auth/login`
- `/api/v1/auth/logout`
- `/api/v1/auth/refresh`
- `/api/v1/auth/invitations/accept`
- `/api/v1/auth/password/reset`

### Human Dashboard API

Suggested groups:

- `/api/v1/dashboard/owner/installations`
- `/api/v1/dashboard/reseller/summary`
- `/api/v1/dashboard/reseller/installations`
- `/api/v1/admin/releases`
- `/api/v1/admin/resellers`
- `/api/v1/admin/invitations`

---

## CI/CD Alignment Recommendation

The upgraded authority service should align with a CI/CD policy that is represented in versioned repository files and operational tasks, not just manual deployment knowledge.

At the moment, this repository already has strong task-based local operations via `.vscode/tasks.json`, but it does not currently include checked-in GitHub workflow files for this service.

So the proposal should be:

- keep operational commands and health checks versioned in repo files
- add authority-specific build, test, lint, package, and deploy automation as task definitions where helpful
- add checked-in CI workflow files when the release policy is finalized
- keep release manifests, deployment config, and policy documents under source control

### Minimum CI/CD Requirements

1. every authority release should be buildable from versioned files only
2. lint, test, and packaging commands should be reproducible from repository tasks
3. deployment configuration should be file-backed, reviewable, and environment-specific
4. release metadata and manifests should be versioned and traceable
5. authority migrations should run in a controlled release step, not manually ad hoc

### Recommended Repo Assets

The authority upgrade should eventually include repository-backed assets such as:

- service build and test commands
- authority-specific VS Code tasks for local development and validation
- deployment scripts or compose files
- database migration files
- release manifest files
- CI workflow definitions when introduced
- markdown documents that define release, rollback, and support policy

### Why This Matters

The authority service will become a central policy system. That means undocumented deploy steps or one-off production edits would create platform risk.

---

## Deployment Model Recommendation

The authority service should remain deployable as its own service, but its release process should become stricter than the current MVP model.

Recommended direction:

- treat authority as a versioned deployable product
- pin authority releases to tagged versions
- apply database migrations explicitly
- validate health and key machine-facing endpoints after deploy
- validate dashboard login and dashboard summary endpoints after deploy

---

## Migration Strategy

The service should not jump from bearer-token MVP to full portal in one uncontrolled step.

Recommended phased migration:

### Phase 1. Data And API Foundations

- extend installation data model
- add update-state and release metadata support
- add invitation and user tables
- keep existing admin token path temporarily for bootstrap use

### Phase 2. Authority-Owned Authentication

- add authority login and session flows
- add system roles including `platform_admin`, `reseller`, and `owner`
- migrate admin operations from shared bearer token toward real user auth

### Phase 3. Owner And Reseller Dashboards

- build dashboard APIs
- build authority web UI with frontend-aligned design
- add reseller aggregation filters and invitation flows

### Phase 4. Update Lifecycle Integration

- add update eligibility endpoint
- add installation state reporting
- add update result reporting
- expose release and rollout status in dashboards

### Phase 5. CI/CD Hardening

- add dedicated build and validation tasks
- add workflow files if the repo adopts checked-in CI automation
- document release, migration, rollback, and smoke-test policy

---

## Policy Questions That Should Be Decided Explicitly

### 1. Should Authority Users Be Separate From Local Node Users?

Recommended MVP:

- yes
- authority should own its own accounts even if it reuses Node code patterns

### 2. Can One Owner Account See More Than One Installation?

Recommended MVP:

- yes
- if those installations are explicitly assigned to that owner scope

### 3. Can A Reseller Create Owners Directly?

Recommended MVP:

- yes
- through invitation flows within delegated scope

### 4. Should Resellers Be Able To Trigger Updates?

Recommended MVP:

- they may request or approve scoped rollout actions
- final release policy should still be constrained by platform rules and installation eligibility

### 5. Should The Minimal HTML Admin Page Survive Long Term?

Recommended MVP:

- no
- retain only as a temporary bootstrap surface until the proper authority portal replaces it

---

## Recommended MVP Implementation Order

### Step 1. Formalize Authority As Installation-Lifecycle Policy Service

Update the authority data model and API contract to support release state, update eligibility, and update history.

### Step 2. Port And Adapt Node User Management Concepts

Introduce authority-owned users, roles, capabilities, invitations, and sessions using Node patterns as the starting point.

### Step 3. Build Owner And Reseller Dashboard APIs

Expose installation, entitlement, release, and update views keyed by installation and user scope.

### Step 4. Replace The Static Admin UI With Frontend-Aligned Web UX

Move from inline HTML to a proper web dashboard implementation consistent with `ppl-meta-frontend`.

### Step 5. Add File-Backed CI/CD Assets

Introduce repeatable build, validation, migration, packaging, and deployment automation backed by repository files and tasks.

---

## Bottom Line

The existing authority service should evolve from a minimal installation registry into a product-grade remote control plane for the PPL Meta lifecycle.

The recommended direction is:

- keep `installation_uuid` as the top-level lifecycle identity
- make authority part of both onboarding and ongoing update policy
- give authority its own user management using adapted Node auth patterns
- support owner and reseller dashboards with scoped visibility
- adopt the UX and styling language of `ppl-meta-frontend`
- align deployment and release practice with versioned files, tasks, and CI/CD policy

This is the cleanest path to making authority a real platform service rather than a narrow activation helper.