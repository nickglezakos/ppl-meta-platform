# Platform Settings And Authority Application Key Onboarding Contract

**Date**: May 20, 2026  
**Status**: Draft  
**Scope**: Define the platform-side contract for persisting the authority application key and installation UUID in the settings flow, then using those values during first-user onboarding and later authority-aware lifecycle operations  
**Related Documents**: [docs/proposals/installation and onboarding/real-installation-uuid-and-application-key-onboarding-flow.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/real-installation-uuid-and-application-key-onboarding-flow.md), [docs/proposals/installation and onboarding/updating-installations.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/updating-installations.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md), [docs/proposals/CICD policy and implementation/ppl-meta-authority-cicd-and-hetzner-deployment-proposal.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-authority-cicd-and-hetzner-deployment-proposal.md), [ppl-meta-frontend/lib/presentation/screens/settings/settings_screen.dart](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/presentation/screens/settings/settings_screen.dart)

---

## Purpose

This proposal defines the platform-side behavior that must stay aligned with authority.

The main rule is simple:

- the software licence issued to the owner is the same authority onboarding credential stored locally as the `application_key`

That means the platform should not introduce a second local-only licence secret for first-user activation.

Instead, the settings flow, first-user onboarding flow, installer flow, and later authority revalidation flow should all use the same pair of persisted values:

- `application_key`
- `installation_uuid`

---

## Existing UI Anchor

The current settings screen already exposes the required storage surface in [ppl-meta-frontend/lib/presentation/screens/settings/settings_screen.dart](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/presentation/screens/settings/settings_screen.dart).

The UI already presents:

- `Application key`
- `Installation UUID`
- save behavior for those values

This proposal treats that screen as a real lifecycle surface, not a temporary development helper.

---

## Contract Summary

The platform-side onboarding contract should be:

1. authority issues a software licence or entitlement to the owner
2. that licence identity is surfaced by authority as the `application_key`
3. the local installation persists that `application_key`
4. the local installation creates or confirms a durable `installation_uuid`
5. the first local user submits email and password
6. the platform calls authority using `application_key + owner_email + installation_uuid`
7. only after authority approval does the platform grant the `owner` role and complete onboarding

This makes the authority service the control plane for first-owner activation without forcing the platform to hardcode fake installation IDs.

---

## Required Platform Responsibilities

## 1. Persist The Correct Values

The settings flow should persist exactly the values required by authority activation.

Required stored fields:

- `application_key`
- `installation_uuid`

Rules:

- `application_key` must be the authority-issued owner licence identity
- `installation_uuid` must be the durable local installation identity
- these values must survive restart and update flows
- updates must not silently overwrite them

## 2. Distinguish Settings Persistence From Activation

Saving the settings is not the same as activating the installation.

The settings flow should:

- store the onboarding values locally
- allow the operator to inspect or correct them
- avoid granting owner access just because values exist locally

Activation should still require a successful authority call during first-user onboarding or explicit activation flow.

## 3. Use Authority During First-User Onboarding

When the first local user tries to become owner, the platform should send:

- `owner_email`
- `application_key`
- `installation_uuid`

Required behavior:

- if authority approves, grant `owner,admin,user`
- if authority rejects, do not grant `owner`
- show a clear failure reason when available
- retain the persisted settings values so the issue can be corrected without re-entering unrelated data

## 4. Reuse The Same Identity For Updates

After activation, the platform should keep using the same `installation_uuid` for:

- state reporting
- release eligibility checks
- update result reporting
- authority cache or offline grace logic

The onboarding identity and update identity must not diverge.

---

## Required Authority Compatibility

The platform depends on the following authority endpoints remaining stable enough for this contract:

- `POST /api/v1/installations/activate`
- `POST /api/v1/installations/report-state`
- `POST /api/v1/installations/check-update`
- `POST /api/v1/installations/report-update-result`

Minimum activation request payload:

- `application_key`
- `installation_uuid`
- `owner_email`

Minimum successful activation response fields:

- `approved`
- `reason`
- `installation_uuid`
- `application_key`
- `approved_owner_email`
- `licence_status`
- `owner_enabled`
- `activation_status`

The platform should not depend on fields outside that minimum set unless they are versioned deliberately.

---

## Installer And Setup Implications

The installer or setup flow should prepare the local node for this contract rather than bypass it.

Required installer behavior:

- collect or receive the authority application key
- persist the application key locally
- create or preserve the local installation UUID
- direct the operator to complete first-user onboarding afterward

The installer should not:

- auto-grant the owner role without authority activation
- generate an unrelated local-only licence credential
- assume a fake pre-bound installation ID

---

## CI/CD Implications

This contract should be tested in automation.

Minimum coverage expected from CI:

- authority accepts a valid `application_key + owner_email + installation_uuid`
- authority rejects a mismatched owner email
- authority rejects an unknown application key
- authority rejects rebinding the same application key to a second installation UUID
- state reporting and update eligibility continue working for the bound installation

The platform-side contract should also be regression-tested whenever the settings persistence model changes.

---

## Failure Handling Rules

When activation fails, the platform should keep behavior explicit.

Recommended handling:

- show the returned authority reason when safe to expose
- keep the local user in a non-owner state
- preserve the saved settings so the operator can retry
- avoid creating silent partial-owner state

Recommended reasons to map clearly in the UI:

- `unknown_application_key`
- `owner_email_not_approved`
- `owner_disabled`
- `licence_inactive`
- `installation_already_bound_elsewhere`

---

## Acceptance Criteria

This contract should be considered implemented only when:

- the settings screen persists `application_key` and `installation_uuid`
- the first-user onboarding path actually consumes those persisted values
- owner access is granted only after authority approval
- the same bound installation identity is reused for later lifecycle operations
- the authority CI/CD proposal and platform onboarding proposal describe the same activation contract

---

## Recommendation

The platform should keep the current settings UI direction and elevate it into a formal lifecycle contract.

That means:

- treat the settings screen as the persisted authority onboarding surface
- treat the software licence number as the same value stored in `application_key`
- make first-user onboarding depend on authority activation rather than local-only assumptions
- keep later update and reporting flows tied to the same bound installation record

This is the narrowest design that stays aligned with the existing authority and installation proposals while remaining practical for the current platform implementation.
