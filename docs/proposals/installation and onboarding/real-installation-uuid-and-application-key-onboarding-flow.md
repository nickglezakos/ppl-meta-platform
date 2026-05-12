# Real Installation UUID And Application Key Onboarding Flow

**Date**: May 11, 2026  
**Status**: Proposal  
**Scope**: Replace the current hardcoded `tenant-a` and `key-a` development contract with a real installation identity and authority-backed onboarding flow for first-user owner activation and licence issuance  
**Related Documents**: [docs/proposals/installation and onboarding/hetzner-minimal-owner-licence-lifecycle.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/hetzner-minimal-owner-licence-lifecycle.md), [docs/proposals/installation and onboarding/hetzner-authority-and-node-integration-status-report.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/hetzner-authority-and-node-integration-status-report.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md)

---

## Purpose

This proposal replaces the current MVP development assumption that the Node service can be configured against a manually created authority record such as:

- `installation_uuid = tenant-a`
- `application_key = key-a`

That is sufficient for development, but it is not a real onboarding lifecycle.

The production goal should be:

1. an operator or sales/admin user registers a customer email in the online authority service
2. the authority service issues a real application key and tenant context for that customer
3. a fresh local installation generates or receives a real installation UUID
4. when the first user account is created locally, Node verifies that the user email is already approved online
5. if approved, Node activates the installation, stores the real authority-issued identity locally, grants first-owner registration, and allows login

This document proposes a better end-to-end process for that lifecycle.

---

## Problem With The Current Development Contract

The current authority integration proves the architecture, but it still relies on manually prepared values and does not yet model real customer onboarding.

Current limitations:

- the authority record is keyed against hardcoded development values such as `tenant-a` and `key-a`
- there is no proper issuance flow for a new customer or tenant
- there is no distinction between a customer pre-registered online and an installation that appears for the first time locally
- local first-user registration still depends on local config already containing authority identifiers
- the system does not yet describe how a real installation gets its application key and tenant metadata

So the missing piece is not only validation. It is identity issuance and activation.

---

## Recommended Model

The better model is to separate the lifecycle into two phases:

### Phase 1. Online Pre-Provisioning

Before a local installation is activated, the authority service should hold a pending customer or installation entitlement.

Minimum fields:

- approved owner email
- application key
- tenant name or tenant identifier
- licence plan or licence status
- owner enabled flag
- installation status such as `pending_activation`, `active`, `revoked`

At this stage, the authority service knows:

- who is allowed to become the first owner
- what licence or entitlement exists
- which application key belongs to that customer

At this stage, the authority service does **not** need to know the final local installation UUID yet.

### Phase 2. First Local Activation

When the local software runs for the first time:

1. Node generates a real installation UUID locally if one does not already exist.
2. The first user creates an account locally.
3. Node sends an activation request to the authority service containing:
   - first user email
   - local installation UUID
   - application key supplied by installer, config, or activation link
4. The authority service verifies that:
   - the application key is valid
   - the email is the approved owner email for that pending entitlement
   - the licence is eligible for activation
5. If valid, the authority service binds that real installation UUID to the entitlement and returns approval.
6. Node stores the returned installation identity and licence data locally, grants the `owner` role to the first local user, and completes login.

This is the missing step that upgrades the design from a test harness to real onboarding.

---

## Key Recommendation

The authority service should **not** require the final installation UUID to be manually known in advance for every sale.

Instead, it should allow a two-stage contract:

1. a customer entitlement exists online before installation
2. the real installation UUID is bound during first activation

This is better than pre-filling a fake UUID because:

- it matches real deployment reality
- it avoids inventing placeholder installation IDs
- it lets a real local machine create its own durable installation UUID
- it keeps the authority service as the source of truth for whether activation is allowed

---

## Suggested Data Model Change

The current MVP installation record is too activation-specific and assumes the installation UUID is already known.

The authority service should evolve toward two related entities.

### 1. Customer Entitlement Or Pending Activation Record

Suggested fields:

- `entitlement_uuid`
- `approved_owner_email`
- `application_key`
- `tenant_name`
- `licence_status`
- `owner_enabled`
- `offline_grace_days`
- `activation_status` such as `pending_activation`, `active`, `revoked`, `expired`
- optional `notes`
- optional plan metadata

### 2. Bound Installation Record

Suggested fields:

- `installation_uuid`
- `entitlement_uuid`
- `application_key`
- `approved_owner_email`
- `tenant_name`
- `licence_status`
- `owner_enabled`
- `offline_grace_days`
- `activated_at`
- `last_validated_at`
- optional device metadata

This lets the authority service support:

- pre-issued entitlements before install
- later binding of a real machine installation UUID
- future reinstallation or recovery rules if needed

---

## Recommended First-User Activation Flow

The following is the recommended onboarding flow.

### Step 1. Admin Or Sales Registers The Customer Online

An operator uses the authority admin UI to create a new pending entitlement.

Input:

- customer or owner email
- tenant name
- licence plan or licence status
- owner enabled setting

Output generated by authority:

- application key
- entitlement UUID
- pending activation record

The application key is then sent to the customer through a secure onboarding channel.

### Step 2. Local Installation Is Prepared

The installer or setup flow stores:

- authority base URL
- application key
- optional tenant hint if useful for UI only

It does **not** need to hardcode a fake installation UUID.

### Step 3. Node Creates A Real Local Installation UUID

On first startup, Node creates and persists a real installation UUID locally if one does not already exist.

This UUID becomes the permanent local identity anchor.

### Step 4. First User Registers Locally

The first local user enters:

- email
- password

Node creates the local account in a pending non-owner state or in a staged transaction.

### Step 5. Node Calls Authority Activation Endpoint

Node sends an activation request such as:

- `email`
- `application_key`
- `installation_uuid`
- optional local version/build metadata

The authority service checks whether the email and application key correspond to a pending entitlement.

### Step 6. Authority Binds The Installation

If valid:

- the authority service records the real installation UUID
- the entitlement becomes active
- the response includes current approved owner email, licence status, owner enabled state, and offline grace policy

If invalid:

- authority rejects activation
- Node must not assign the local `owner` role

### Step 7. Node Grants First Owner And Completes Login

If authority activation succeeds:

- Node grants `owner,admin,user`
- Node stores authority cache and activation metadata locally
- Node completes login for that first user

If authority activation fails:

- Node may still create a normal local user only if explicitly allowed by policy
- Node should not silently make that user owner
- UI should show a clear activation failure message

---

## Why This Is Better Than The Original Idea

The original idea was directionally right:

- someone gives you their email
- you issue a licence online
- first local registration should check whether that email is already registered in the authority service

That part should remain.

The improvement is that the system should not treat the authority record as already bound to a fake installation identity.

Instead, the cleaner design is:

- online issue entitlement first
- local app produces its real installation UUID later
- first activation binds the real installation UUID to the issued entitlement

That is the correct production-friendly model.

---

## Node Changes Required

To support this lifecycle, Node should change in the following ways.

### 1. Stop Depending On Pre-Filled Fake Installation IDs

Node should no longer assume that `AUTHORITY_INSTALLATION_UUID` must already point at a manually created authority installation record during the very first onboarding.

Instead, Node should support an activation mode where:

- local installation UUID exists locally
- application key exists locally
- authority binding may not yet exist remotely

### 2. Add A First-Activation Endpoint In Authority Contract

Current owner validation is lookup-oriented.

For real onboarding, Node needs an activation-oriented authority endpoint such as:

- `POST /api/v1/installations/activate`

Suggested request:

- `application_key`
- `installation_uuid`
- `owner_email`

Suggested response:

- activation accepted or rejected
- approved owner email
- tenant name
- licence status
- owner enabled
- offline grace days

### 3. Stage First User Creation More Carefully

For the very first local user, Node should avoid treating the local DB commit as final owner registration before authority activation completes.

Recommended behavior:

- create local user
- do not grant `owner`
- perform activation
- grant `owner` only after success
- then login succeeds as owner

### 4. Persist Real Bound Identity Locally

After successful activation, Node should persist:

- installation UUID
- application key
- entitlement or tenant metadata if needed
- approved owner email
- activation timestamp

---

## Authority Service Changes Required

The authority service should evolve from a pure installation lookup service into a small activation and licensing authority.

Recommended additions:

### Admin Capabilities

- create pending entitlement by email
- issue application key
- attach tenant name and licence data
- view activation status
- revoke or suspend entitlement

### Public Or Node-Scoped API Capabilities

- activate installation from application key + email + installation UUID
- validate bound installation state after activation
- return current owner/licence/offline grace state

### Optional Later Additions

- resend activation invitation
- rotate application key
- allow controlled rebind or transfer flow for reinstallations

---

## Installer Or Setup Flow Implications

The installer or setup flow should collect or receive the application key.

Possible onboarding inputs:

- activation link
- emailed application key
- QR code or one-time activation token

Recommended MVP input:

- customer receives application key manually from operator or admin
- installer asks for application key during setup
- installer writes it into local Node config

That is enough for an MVP.

Later, a richer installer can exchange a short-lived activation token for the application key automatically.

---

## Proposed API Contract

### Admin Upsert Pending Entitlement

Suggested admin payload:

- `approved_owner_email`
- `tenant_name`
- `licence_status`
- `owner_enabled`
- `offline_grace_days`

Suggested authority-generated outputs:

- `entitlement_uuid`
- `application_key`
- `activation_status = pending_activation`

### First Activation

Suggested request:

- `application_key`
- `installation_uuid`
- `owner_email`

Suggested success response:

- `approved = true`
- `installation_uuid`
- `application_key`
- `approved_owner_email`
- `tenant_name`
- `licence_status`
- `owner_enabled`
- `offline_grace_days`
- `activation_status = active`

Suggested failure response reasons:

- `unknown_application_key`
- `owner_email_not_approved`
- `licence_inactive`
- `owner_disabled`
- `installation_already_bound_elsewhere`

---

## Policy Questions That Should Be Decided Explicitly

This onboarding flow still needs explicit policy decisions.

### 1. Should A Failed First Activation Still Create A Local Non-Owner User?

Recommended MVP:

- yes, if desired for support visibility
- but never grant owner automatically

### 2. Can One Entitlement Be Bound To More Than One Installation?

Recommended MVP:

- no
- one application key activates one installation

### 3. What Happens On Reinstall?

Recommended MVP:

- allow reactivation only through admin reset or transfer
- do not silently bind a second installation UUID

### 4. Should The First Activation Immediately Log The User In?

Recommended MVP:

- yes
- if activation succeeds, grant owner and complete login in the same flow

---

## Recommended MVP Implementation Order

### Step 1. Add Entitlement-Oriented Data Model To Authority Service

Implement pending entitlement creation with generated application key.

### Step 2. Add Activation Endpoint

Implement `application_key + owner_email + installation_uuid -> activation decision`.

### Step 3. Update Node First-User Registration Flow

Replace the current simple lookup logic with first-activation binding logic when no remote installation binding exists yet.

### Step 4. Preserve Existing Periodic Validation Flow

After activation, keep using the existing authority cache and revalidation model.

### Step 5. Update Installer Or Setup UX

Collect the application key during first setup and store it locally.

---

## Bottom Line

The system should move from:

- manually configured fake installation IDs
- manually prepared authority records bound in advance

to:

- online pre-issued entitlement by owner email
- authority-generated application key
- locally generated real installation UUID
- first-user activation that binds the real installation to the entitlement
- owner role granted only after authority approval

This is the correct model for a real onboarding lifecycle and is the recommended direction for the next authority-service phase.