# Authority Policy

**Date**: May 22, 2026  
**Status**: Final Policy  
**Scope**: Define the lifecycle, authority boundaries, suspension and reinstatement rules, soft-delete policy, orphan handling, and entitlement governance for users and customer entities managed by the authority service  
**Related Documents**: [docs/proposals/installation and onboarding/real-installation-uuid-and-application-key-onboarding-flow.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/real-installation-uuid-and-application-key-onboarding-flow.md), [docs/proposals/CICD policy and implementation/ppl-meta-installation-lifecycle-cicd-policy.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md), [docs/proposals/CICD policy and implementation/ppl-meta-authority-cicd-and-hetzner-deployment-proposal.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-authority-cicd-and-hetzner-deployment-proposal.md)

---

## Purpose

The authority service now manages invitations, role-scoped users, entitlements, onboarding approvals, and installation activation. This document defines the final lifecycle and governance policy for what happens after those entities exist.

The platform needs one consistent answer to questions such as:

- who may invite which role
- who may suspend, reinstate, or soft-delete a user
- what happens to child entities when a parent role is removed or suspended
- whether distributors and resellers may change entitlement state
- how orphaned users and entitlements should behave
- which operations are reversible and which are not
- what audit record must exist for every lifecycle mutation

This policy keeps the authority service as the single source of truth for user, scope, entitlement, and activation governance.

---

## Policy Goals

The authority policy must satisfy six goals.

1. Preserve authority as the only system that decides user governance, entitlement state, and onboarding approval.
2. Prevent destructive parent-role actions from breaking already-issued owner entitlements or application keys.
3. Make suspension and reinstatement explicit state transitions instead of implicit side effects.
4. Prefer reversible operations over hard deletion.
5. Ensure every lifecycle action is attributable to an actor, timestamp, reason, and affected scope.
6. Support future automation without weakening administrative control.

---

## Core Principles

### 1. Authority Is The System Of Record

All lifecycle state for authority-managed users and entitlements must be persisted and enforced by the authority service.

Node, mobile, installers, and other local services may cache authority-approved state, but they must not become the source of truth for:

- role status
- entitlement status
- owner approval
- installation activation approval
- organizational assignment

### 2. No Hard Delete For Operational Entities

Users, invitations, and entitlements must not be physically removed during normal operations.

Normal lifecycle handling should use explicit status fields such as:

- `pending`
- `active`
- `suspended`
- `revoked`
- `removed`
- `expired`
- `orphaned`

A physical delete is limited to:

- test data cleanup
- legal erasure workflows
- migration rollback or administrative repair by top-level operators only

### 3. Parent Removal Must Not Break Child Entitlements

When a parent actor such as a distributor or reseller is suspended or removed, child owners and their issued entitlements must not lose access merely because the parent organizational record changed.

Instead:

- the child users remain intact
- the child entitlements remain intact
- the child users may become `orphaned`
- reassignment becomes an explicit later operation by an authorized role

### 4. Entitlement State And User State Are Related But Distinct

A user being suspended is not automatically the same as an entitlement being suspended.

Examples:

- a reseller may be suspended while existing owner entitlements remain active
- an owner may be suspended while the entitlement remains issued but temporarily unusable
- an entitlement may be revoked while the owner account still exists for audit and reassignment

This separation is necessary to preserve auditability and lifecycle recovery.

---

## Managed Entity Types

This policy applies to the following authority-managed entities.

### Users

Roles currently include:

- `platform_admin`
- `distributor`
- `reseller`
- `owner`
- `support`

### Invitations

Invitations are authority-issued pending access grants tied to:

- target email
- target role
- optional distributor scope
- optional reseller scope
- lifecycle state

### Entitlements

Entitlements are authority-issued licence or onboarding records tied to:

- approved owner email
- application key
- optional installation binding
- licence status
- owner enabled flag
- tenant metadata

### Installations

Installations are local identities later bound to authority approval through activation.

### Assignments

Assignments link owners to entitlements and should also follow explicit lifecycle tracking.

---

## Recommended User Lifecycle States

Every authority user should have an explicit lifecycle state.

### `pending`

The user has been invited but has not accepted the invitation.

### `active`

The user has accepted access and is allowed to authenticate subject to role and entitlement policy.

### `suspended`

The user exists but may not authenticate or perform authority actions until reinstated.

### `removed`

The user is soft-deleted from operational use. The record remains for audit, relationships, and historical reporting.

### `orphaned`

The user is still valid but no longer has a valid parent organizational assignment.

Examples:

- an owner whose reseller was removed
- a reseller whose distributor was removed

The user remains present but may have restricted lifecycle actions until reassigned.

---

## Recommended Entitlement Lifecycle States

Entitlements should carry an independent operational state.

### `pending_activation`

Created and ready for first approved onboarding, but not yet bound to a real installation.

### `active`

Valid and usable for activation or ongoing checks.

### `suspended`

Temporarily blocked from activation, update approval, or owner use.

### `revoked`

Invalidated intentionally and not usable unless explicitly reinstated according to policy.

### `expired`

Ended due to time or commercial policy rather than explicit operator revocation.

### `orphaned`

Still valid, but its managing reseller or distributor is no longer active or assigned.

This state is administrative, not customer-facing. It signals that reassignment is required.

---

## Role Authority Model

The policy distinguishes between operational authority and commercial authority.

### Platform Admin

`platform_admin` is the ultimate authority role.

May:

- invite all non-admin roles
- suspend, reinstate, or remove any non-admin user
- reassign distributors, resellers, and owners
- create, suspend, reinstate, revoke, or reassign entitlements
- resolve orphaned users and orphaned entitlements
- override scope relationships when required for recovery

Should not:

- hard-delete operational records in normal flows

### Distributor

A distributor governs reseller relationships within its distributor scope and may invite owners subject to entitlement policy.

May:

- invite reseller users within distributor scope
- invite owner users within distributor scope, subject to entitlement policy
- suspend or reinstate reseller users within distributor scope
- view distributor-scoped entitlements and owners
- propose reassignment or mark records for admin review

Should not:

- remove other distributors
- remove platform admins
- revoke entitlements globally
- suspend owners directly
- reassign owners out of scope

Required policy:

- distributors may suspend and reinstate reseller users in their scope
- distributors must not suspend owners directly
- distributors may not permanently remove reseller or owner users without platform-admin approval
- distributors may not create, suspend, reinstate, or revoke entitlements
- distributors may only request or recommend entitlement state changes

### Reseller

A reseller governs owner relationships within its reseller scope.

May:

- invite owner users within reseller scope, subject to entitlement policy
- suspend or reinstate owner users in reseller scope
- view reseller-scoped entitlements and installation assignments

Should not:

- remove owners permanently without platform-admin approval
- change distributor assignments
- create, suspend, reinstate, or revoke entitlements

Required policy:

- resellers may suspend or reinstate owner users within their scope
- resellers may not permanently remove owners without escalation
- resellers may not create, suspend, reinstate, or revoke entitlements

### Support

Support is an observational role with limited emergency recovery authority.

May:

- inspect users, entitlements, invitations, and installation lifecycle state
- perform diagnostic or read-mostly operations
- perform limited emergency reinstatement actions for users when explicitly permitted by platform-admin policy

Should not:

- invite operational roles
- suspend users
- revoke entitlements
- reassign ownership

Emergency recovery authority is limited to reinstatement only. Support must not gain suspension, removal, revocation, or reassignment authority.

### Owner

Owners are customer users, not lifecycle governors.

May:

- authenticate
- operate within their customer scope
- view their installations and entitlement-derived status where appropriate

Should not:

- invite authority-managed organizational roles
- manage entitlements
- manage authority user states

---

## Final Authority Matrix

### User Actions

| Action | Platform Admin | Distributor | Reseller | Support | Owner |
| --- | --- | --- | --- | --- | --- |
| Invite distributor | yes | no | no | no | no |
| Invite reseller | yes | yes in scope | no | no | no |
| Invite owner | yes | yes in scope and entitlement-aware | yes in scope and entitlement-aware | no | no |
| Suspend distributor | yes | no | no | no | no |
| Suspend reseller | yes | yes in scope | no | no | no |
| Suspend owner | yes | no | yes in scope | no | no |
| Reinstate distributor | yes | no | no | no | no |
| Reinstate reseller | yes | yes in scope | no | yes emergency only | no |
| Reinstate owner | yes | no | yes in scope | yes emergency only | no |
| Remove distributor | yes | no | no | no | no |
| Remove reseller | yes | recommend only | no | no | no |
| Remove owner | yes | recommend only | recommend only | no | no |
| Reassign orphaned users | yes | no | no | no | no |

### Entitlement Actions

| Action | Platform Admin | Distributor | Reseller | Support | Owner |
| --- | --- | --- | --- | --- | --- |
| Create entitlement | yes | no | no | no | no |
| Update tenant metadata | yes | no | no | no | no |
| Suspend entitlement | yes | no | no | no | no |
| Reinstate entitlement | yes | no | no | no | no |
| Revoke entitlement | yes | no | no | no | no |
| Reassign orphaned entitlement | yes | no | no | no | no |

Final rule:

- only `platform_admin` can create, update, suspend, reinstate, revoke, or reassign entitlements
- distributor and reseller may not directly mutate entitlement state

---

## Invitation Policy

### General Rule

Every invitation should be treated as a pending lifecycle object, not merely a token.

The invitation record should preserve:

- issuer user UUID
- issuer role
- target email
- target role
- target scope
- reason or note if supplied
- lifecycle status
- acceptance timestamp
- superseded or cancelled state if replaced

### Owner Invitation Rule

Owner invitations must be entitlement-aware.

Enforced rule:

- the system must not send an owner invitation unless an entitlement already exists for that owner email

This keeps authority as the source of truth for commercial approval.

### Superseding Invitations

If a later invitation for the same email and role is sent, the earlier pending invitation must be superseded automatically.

Final rule:

- older pending invitations for the same email and target role become `superseded`
- superseded invitations must not remain valid for acceptance

---

## Parent-Child Orphan Policy

### Distributor Suspended

When a distributor is suspended:

- distributor users lose authority access
- child reseller users remain present
- child owner users remain present
- child entitlements remain unchanged unless explicitly changed
- child resellers become operationally `orphaned_from_distributor`

Operational effect:

- no immediate licence breakage for owners
- no automatic revocation of application keys
- reassignment required before new downstream governance actions continue

### Distributor Removed

When a distributor is removed:

- reseller children become orphaned
- owners that were only governed by that distributor through a reseller chain remain intact
- entitlements remain intact
- no automatic customer outage is introduced

### Reseller Suspended

When a reseller is suspended:

- reseller user loses authority access
- owner users remain present
- owner entitlements remain intact
- owners become operationally `orphaned_from_reseller`
- owner installations and application keys remain valid unless entitlement state changes separately
- orphaned owners continue logging into authority
- orphaned owners remain operational until reassigned, subject to other explicit user or entitlement states

### Reseller Removed

When a reseller is removed:

- owners remain present
- owner entitlements remain intact
- owner-to-entitlement assignments remain intact
- owners become orphaned and require reassignment by an authorized higher role

### Orphan Resolution

Only a role with reassignment authority should clear orphan state.

Final rule:

- `platform_admin` resolves orphan state
- orphaned owners continue logging into authority until reassigned
- non-admin roles must not reassign orphaned users unless a later final policy revision explicitly grants that power

---

## Entitlement Policy

### Entitlement Creation

Entitlements remain authority-issued records.

Final rule:

- `platform_admin` is the only role allowed to create entitlements

### Entitlement Suspension

Suspension should be reversible and should preserve the record.

Effects of entitlement suspension:

- new activation should be denied
- update approval may be denied depending on lifecycle policy
- local offline grace behavior continues only if explicitly permitted
- the owner record remains present

### Entitlement Revocation

Revocation is stronger than suspension.

Effects of entitlement revocation:

- activation denied
- update eligibility denied
- future local approval denied after grace logic, if any
- entitlement remains visible for audit

Final rule:

- only `platform_admin` may revoke

### Entitlement Reinstatement

A suspended or revoked entitlement may be restored only by an authorized role.

Final rule:

- `platform_admin` may reinstate suspended entitlements
- revoked entitlements are reinstatable and do not require mandatory reissuance

### Entitlement Removal

The platform should prefer `revoked` or `removed` state instead of physical deletion.

---

## Final Policy Decisions

This final policy establishes the following mandatory decisions.

1. All operational delete actions are soft deletes.
2. Distributors may suspend and reinstate resellers in scope.
3. Distributors must not suspend owners directly.
4. Resellers may suspend and reinstate owners in scope.
5. Support may perform limited emergency reinstatement only.
6. Only platform admins may permanently remove distributors, resellers, owners, or entitlements.
7. Only platform admins may create, suspend, reinstate, revoke, or reassign entitlements.
8. Parent suspension or removal never automatically revokes child entitlements.
9. Parent suspension or removal may orphan child users and child entitlements.
10. Only platform admins may resolve orphaned scope assignments.
11. Orphaned owners continue logging into authority until reassigned.
12. Owner invitations require an entitlement to exist first.
13. Invitation supersession automatically cancels earlier pending invitations for the same email and role by moving them to `superseded`.
14. Revoked entitlements are reinstatable.
15. Every lifecycle mutation requires actor, timestamp, reason, and target scope in audit storage.

---

## Audit Policy

Every lifecycle mutation should create an immutable audit event.

Minimum audit fields:

- event UUID
- actor user UUID
- actor role
- target entity type
- target entity UUID
- target email if applicable
- previous state
- new state
- scope before
- scope after
- reason code
- optional operator note
- timestamp

Audited events should include at least:

- invitation issued
- invitation cancelled or superseded
- user suspended
- user reinstated
- user removed
- entity orphaned
- entity reassigned
- entitlement created
- entitlement suspended
- entitlement reinstated
- entitlement revoked
- installation assignment changed

---

## UI And UX Policy Implications

The authority UI should expose lifecycle operations only when the current role is allowed to perform them.

Examples:

- a distributor viewing a reseller should see `Suspend` and `Reinstate` if allowed, not `Delete`
- a reseller viewing an owner should see `Suspend` and `Reinstate` if allowed
- an orphaned owner should display an explicit orphan badge and reassignment-needed state
- entitlement actions should clearly distinguish `Suspend` from `Revoke`

Destructive actions should always:

- require confirmation
- show impact summary
- capture a reason
- record the audit event

Parent suspension and removal confirmations should explicitly say:

- child users will remain intact
- child entitlements will remain intact
- child records will become orphaned until reassigned

---

## Data Model Changes Recommended By This Policy

The authority service should eventually persist explicit lifecycle state fields rather than relying on implicit interpretation.

Recommended additions:

### Users

- `status` expanded to include `active`, `suspended`, `removed`, `orphaned`
- `orphaned_reason`
- `suspended_at`
- `suspended_by_user_uuid`
- `removed_at`
- `removed_by_user_uuid`
- `reinstated_at`
- `reinstated_by_user_uuid`

### Entitlements

- `entitlement_status` or expanded `activation_status` policy field
- `orphaned_reason`
- `suspended_at`
- `suspended_by_user_uuid`
- `revoked_at`
- `revoked_by_user_uuid`
- `reinstated_at`
- `reinstated_by_user_uuid`

### Invitations

- `status` should include `pending`, `accepted`, `expired`, `cancelled`, `superseded`
- `cancelled_at`
- `cancelled_by_user_uuid`
- `superseded_by_invitation_uuid`

### Audit

- dedicated `authority_audit_events` table

---

## Operational Examples

### Example 1. Distributor Suspends Reseller

1. distributor suspends reseller `R1`
2. reseller account can no longer authenticate
3. owners previously invited or managed under `R1` remain intact
4. owner entitlements remain active
5. owners become `orphaned_from_reseller`
6. platform admin later reassigns those owners to reseller `R2`

### Example 2. Reseller Suspends Owner

1. reseller suspends owner `O1`
2. owner authority login is blocked
3. entitlement remains active unless separately suspended
4. installation activation or continued use follows entitlement policy, not only user policy
5. reseller or admin may later reinstate `O1`

### Example 3. Platform Admin Revokes Entitlement

1. entitlement for owner `O2` is revoked
2. application key is no longer valid for activation or update authorization
3. owner user record remains present
4. audit shows who revoked it and why
5. later reinstatement may occur through explicit admin action

---

## Recommended Implementation Order

### Phase 1. Policy Enforcement Without Full UI Expansion

1. enforce owner-invitation entitlement prerequisite
2. add backend status transitions for suspend and reinstate on users
3. add backend status transitions for suspend and revoke on entitlements
4. add audit event persistence

### Phase 2. Orphan Modeling

1. add orphan status and orphan reason fields
2. prevent parent removal from deleting child records
3. add reassignment endpoints and admin UI

### Phase 3. Finalized Entitlement Governance And Recovery

1. keep entitlement lifecycle control admin-only
2. implement support emergency reinstatement controls with explicit audit requirements
3. add scoped entitlement visibility only after audit and orphan logic is stable

---

## Policy Summary

The final authority policy is:

- authority remains the single source of truth for user state, entitlement state, and onboarding approval
- every lifecycle mutation is explicit, reversible where practical, and audited
- no parent-role action should silently break child owner entitlements or application keys
- parent removal should orphan children, not destroy them
- only higher-authority roles should resolve orphan reassignment
- orphaned owners continue logging into authority until reassigned
- owner invitations must remain entitlement-aware
- entitlement lifecycle mutation remains platform-admin-only
- support may perform limited emergency reinstatement but remains non-destructive and non-commercial

This gives the platform a lifecycle model that is operationally safe, commercially controlled, and compatible with the existing authority-onboarding contract.
