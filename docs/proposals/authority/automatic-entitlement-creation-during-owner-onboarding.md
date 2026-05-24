# Automatic Entitlement Creation During Owner Onboarding

**Date**: May 24, 2026  
**Status**: Proposed  
**Scope**: Define the implementation path for automatic entitlement creation during hierarchy-scoped owner onboarding in the authority service  
**Related Documents**: [docs/proposals/authority/admin-console-actions-and-hierarchy-clarification.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/authority/admin-console-actions-and-hierarchy-clarification.md), [docs/proposals/authority/authority-policy.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/authority/authority-policy.md)

---

## Purpose

The authority proposal now recommends a user-first onboarding model.

This follow-up proposal defines how to implement that recommendation without breaking the current authority governance model, activation contract, or reseller and distributor scope rules.

The specific goal is to remove the current requirement that operators manually create an entitlement before a downstream owner can be onboarded in the normal flow.

---

## Current State

Today, owner onboarding is split across separate control surfaces:

- create entitlement
- issue owner invitation
- accept invitation
- assign installation or activate installation later

In practice, reseller and distributor owner invitation flows are constrained by entitlement state tied to `approved_owner_email`.

This means the operational success of owner onboarding depends on record order:

- the owner email must be known in advance
- the entitlement may need to exist before invitation
- the invitation creates the user only later during acceptance
- assignment and activation happen in separate steps after that

This is safe, but it is not the best default user journey.

---

## Problem Statement

The current design exposes entitlement creation too early.

This creates four product and implementation problems:

1. Onboarding order is brittle.
An operator can fail the workflow simply by performing valid steps in the wrong order.

2. Distributor and reseller onboarding is too back-office oriented.
The operator has to think about licence records before the target owner exists as a fully onboarded user.

3. The UI and API expose internal licensing mechanics as the primary path.
That is appropriate for exception handling, but not for normal onboarding.

4. Invitation success is coupled to pre-existing entitlement preparation.
This prevents the system from behaving like a guided hierarchy-aware onboarding flow.

---

## Proposed Direction

Make owner onboarding the primary workflow and create the required entitlement automatically when the owner is accepted into the system.

Recommended high-level sequence:

1. A platform admin, distributor, or reseller issues an owner invitation inside allowed scope.
2. The invited owner accepts the invitation.
3. The authority service creates the owner user record as it already does today.
4. During the same onboarding transaction, the authority service creates a default entitlement for that owner email when one does not already exist.
5. The newly created entitlement is scoped and attributed to the inviter's hierarchy context.
6. Later assignment or activation can bind the installation UUID when a real device appears.

This preserves entitlements as the licensing source of truth while making user onboarding the operational entry point.

---

## Recommended Implementation Model

## 1. Trigger Automatic Entitlement Creation On Owner Invitation Acceptance

The cleanest implementation point is invitation acceptance, not invitation issuance.

Why acceptance is the correct trigger:

- the owner account is definitely being created at that point
- the accepted invitation already contains the final role and hierarchy scope
- the system can avoid creating unused entitlements for invitations that are never accepted
- the owner email, inviter identity, and scope are all available for audit and record creation

Recommended rule:

- when `accept-invitation` creates an `owner` user from a hierarchy-scoped invitation, the service should ensure there is an entitlement for that owner email
- if no entitlement exists, create one automatically
- if an entitlement already exists for that owner email, reuse it instead of creating a duplicate

---

## 2. Preserve Existing Manual Entitlement Support

Manual entitlement creation should remain supported.

It is still needed for:

- pre-provisioning and bulk commercial preparation
- migration and recovery workflows
- exception handling when onboarding data arrives out of order
- platform-admin back-office control

Automatic entitlement creation should therefore be additive, not destructive.

Recommended compatibility rule:

- automatic onboarding should create a new entitlement only when no matching entitlement already exists
- existing manually created entitlements for the accepted owner email should be treated as authoritative and should not be replaced silently

---

## 3. Define A Default Entitlement Template For Auto-Created Records

Automatic creation should not guess arbitrary commercial values.

The implementation should use an explicit default template for auto-created owner entitlements.

Recommended default fields:

- `approved_owner_email`: accepted owner email
- `application_key`: auto-generated by authority
- `installation_uuid`: null until first activation or explicit assignment
- `owner_enabled`: true
- `licence_status`: `active` or `pending_activation`, depending on final product policy
- `offline_grace_days`: system default, currently aligned with the authority default
- `tenant_name`: derived from owner display name or a neutral generated label until a tenant label is supplied
- `notes`: operator- and flow-generated note such as `Auto-created during owner onboarding`

Recommended initial activation state:

- create the entitlement as valid for onboarding but not yet bound to a real installation
- keep installation binding as a later step during assignment or activation

---

## 4. Record The Flow In Audit History

Automatic entitlement creation must be auditable.

Recommended audit behavior:

- record invitation acceptance as it already exists
- record entitlement creation as a distinct event
- include a machine-readable reason code such as `auto_entitlement_on_owner_onboarding`
- associate the audit actor with the inviting hierarchy operator when available
- preserve the final accepted owner email and resulting hierarchy scope in the audit state

This is necessary because automatic creation is still a commercial and governance action even if the operator did not click `Create Entitlement` manually.

---

## 5. Respect Hierarchy Scope Rules

Automatic entitlement creation should not bypass hierarchy governance.

Recommended scope rule:

- the entitlement should inherit the owner email and be considered part of the inviter's downstream scope
- a reseller-triggered owner onboarding should create an entitlement that is valid for that reseller-owned branch
- a distributor-triggered owner onboarding should create an entitlement in that distributor scope, even if no reseller branch exists yet
- a platform admin may still create owners and entitlements without downstream scope restrictions

This keeps onboarding aligned with the same hierarchy model used elsewhere in authority.

---

## API Recommendation

Recommended first implementation:

- keep the existing `POST /api/v1/auth/accept-invitation` endpoint as the public contract
- extend the server-side acceptance flow so owner acceptance performs `ensure owner entitlement exists`

This is preferable to adding a new onboarding endpoint first because:

- it minimizes surface-area change
- it preserves existing UI and invitation links
- it allows staged rollout behind internal logic rather than a public API split

Potential internal service abstraction:

- `ensure_owner_entitlement_for_user(...)`

Recommended behavior of that helper:

- look up entitlements by accepted owner email
- if one exists, return it unchanged
- if none exists, create one using the onboarding default template
- return whether the record was reused or newly created so the caller can audit and message appropriately

---

## UI Recommendation

The first implementation does not need a new complex UI.

Recommended near-term UI changes after backend support exists:

- update invitation copy in reseller and distributor views to explain that the required owner entitlement will be created automatically on successful onboarding
- reposition `Create Entitlement` as an advanced licensing tool for exceptional workflows
- surface onboarding success messaging such as `Owner onboarded and entitlement created`

Longer-term UI direction:

- add an explicit `Onboard Owner` flow that combines invitation, scope preview, and post-acceptance entitlement summary in a single operator journey

---

## Migration And Compatibility

This change should be backward compatible.

Recommended rollout behavior:

- existing manual entitlement workflows continue to work unchanged
- existing invitations continue to be accepted using the same endpoint
- automatic creation applies only when an owner invitation is accepted and no entitlement already exists for that owner email
- existing owner accounts and entitlements remain unchanged

This avoids forced migration while still improving the default onboarding path for all new owner users.

---

## Risks

### 1. Duplicate Entitlements

If the lookup rule is too loose or too strict, the system may create duplicate records.

Mitigation:

- define a single canonical reuse rule based on normalized owner email and current commercial policy
- validate the no-duplicate path in automated tests

### 2. Wrong Default Commercial State

If auto-created entitlements default to the wrong licence state, onboarding may unintentionally grant too much or too little access.

Mitigation:

- explicitly define the default entitlement template
- do not infer commercial state from UI convenience alone

### 3. Hidden Operator Side Effects

Operators may not realize that accepting an owner into the system also creates a licensing record.

Mitigation:

- show explicit success messaging
- write clear audit records
- document the behavior in the admin console and onboarding docs

---

## Acceptance Criteria

The proposal is satisfied when all of the following are true:

1. Accepting a valid owner invitation can complete successfully without manual entitlement pre-creation.
2. Owner invitation acceptance automatically creates an entitlement when none exists for the accepted owner email.
3. If a matching entitlement already exists, acceptance reuses it instead of creating a duplicate.
4. The automatic creation path records a distinct audit event with a machine-readable reason code.
5. Existing manual `Create Entitlement` workflows continue to operate without regression.
6. Distributor and reseller onboarding flows remain constrained by existing hierarchy scope rules.
7. Operator-facing UI copy can explain that owner onboarding may automatically create the required entitlement.

---

## Final Recommendation

Implement automatic entitlement creation at owner invitation acceptance time.

Keep entitlements as the authority-controlled licensing source of truth, but stop requiring operators to create them manually before normal owner onboarding can succeed.

This is the smallest implementation change that meaningfully shifts the product from entitlement-first onboarding to user-first onboarding while preserving the current domain model, activation contract, and hierarchy governance.