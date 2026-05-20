# PPL Meta Authority CI/CD And Hetzner Deployment Proposal

**Date**: May 20, 2026  
**Status**: Draft  
**Scope**: Define the development work needed to bring `autonomous/ppl-meta-authority` into a repeatable CI/CD flow, align its entitlement and activation model with the wider PPL Meta installation lifecycle, and then deploy it safely to the Hetzner-hosted production authority service  
**Related Documents**: [docs/proposals/CICD policy and implementation/ppl-meta-installation-lifecycle-cicd-policy.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-policy.md), [docs/proposals/CICD policy and implementation/ppl-meta-installation-lifecycle-cicd-implementation-plan.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/CICD%20policy%20and%20implementation/ppl-meta-installation-lifecycle-cicd-implementation-plan.md), [docs/proposals/installation and onboarding/real-installation-uuid-and-application-key-onboarding-flow.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/real-installation-uuid-and-application-key-onboarding-flow.md), [docs/proposals/installation and onboarding/updating-installations.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/updating-installations.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md), [docs/proposals/installation and onboarding/hetzner-authority-and-node-integration-status-report.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/hetzner-authority-and-node-integration-status-report.md), [autonomous/ppl-meta-authority/README.md](/Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-authority/README.md), [ppl-meta-frontend/lib/presentation/screens/settings/settings_screen.dart](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/presentation/screens/settings/settings_screen.dart)

---

## Purpose

This proposal defines the concrete path for taking the authority service from a locally validated development service to a production-operated service with a repeatable CI/CD contract and a controlled Hetzner deployment path.

It also aligns the authority-service scope with the wider installation and onboarding proposals already in the repository. In that aligned model, the owner's software licence is not a separate commercial record that sits outside the platform startup flow. It becomes the control-plane onboarding credential exposed by authority as the `application_key` used during first-user activation.

For the platform applications, the practical outcome is:

- an owner receives a software licence or entitlement from authority
- that same licence identity is represented as the authority application key used during platform setup
- the first user of the platform enters or confirms that key through the platform settings flow at `http://localhost:3000/#/settings`
- the local platform uses `application_key + owner_email + installation_uuid` to activate against authority and start the installation lifecycle

The work should happen in two ordered phases:

1. align `autonomous/ppl-meta-authority` with CI/CD
2. deploy the resulting production artifact and runtime configuration to the Hetzner authority environment

The order matters. The authority service should not be treated as production-ready just because it can be started manually on the server. First it needs a deterministic build, validation, packaging, release, and rollback path.

It also should not be treated as aligned with platform CI/CD until the entitlement, activation, installation identity, and update contracts match the surrounding installation proposals.

---

## Current State

The current authority slice already has meaningful implementation progress:

- FastAPI service with PostgreSQL runtime support
- local validation scripts for auth, dashboard, invitations, reseller scope, distributor scope, admin UI, and end-to-end onboarding
- a local-first admin bootstrap and session-based admin shell
- a documented local run path in [autonomous/ppl-meta-authority/README.md](/Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-authority/README.md)
- an existing live Hetzner authority hostname referenced in [docs/proposals/installation and onboarding/hetzner-authority-and-node-integration-status-report.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/hetzner-authority-and-node-integration-status-report.md)
- an installation onboarding model already described in [docs/proposals/installation and onboarding/real-installation-uuid-and-application-key-onboarding-flow.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/real-installation-uuid-and-application-key-onboarding-flow.md)
- a frontend settings path that already persists the authority application key and installation UUID for local onboarding in [ppl-meta-frontend/lib/presentation/screens/settings/settings_screen.dart](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-frontend/lib/presentation/screens/settings/settings_screen.dart)

At the same time, the authority service is not yet fully aligned with CI/CD:

- no authority-specific GitHub Actions workflow is defined in this slice
- no explicit production artifact publication contract is documented for authority
- no in-repo production deployment script or runbook is defined for authority
- no explicit migration gate, release promotion gate, or rollback flow is codified for authority
- no authority-specific environment matrix for local, CI, staging, and production is documented end to end
- the authority CI/CD proposal does not yet make explicit that a granted software licence becomes the same authority application key consumed by first-user onboarding
- the proposal does not yet connect authority release validation to the platform settings contract and the real installation activation flow

This proposal closes those gaps.

---

## Platform Alignment Constraint

The authority service should be aligned with the rest of the platform documents under both CI/CD policy and installation onboarding.

The controlling rule is:

- entitlement issuance, first-user onboarding, installation binding, and later updates are one continuous lifecycle

That means the authority service should not model software licensing as a side channel that is disconnected from activation.

Instead, for the PPL Meta platform:

- the owner-facing software licence number should be the authority-controlled onboarding key
- authority may store it internally as an entitlement key or `application_key`
- the local platform settings flow should persist that same value for later activation and revalidation
- first-user activation should succeed only when that value, the owner email, and the real `installation_uuid` resolve to a valid entitlement in authority
- future updates should continue to be evaluated against the bound `installation_uuid` and that licence-entitlement state

This aligns the authority proposal with the existing onboarding and update documents rather than creating a second incompatible licensing workflow.

---

## Target Outcome

After this proposal is implemented, the authority service should have the following properties:

- every change to `autonomous/ppl-meta-authority` is validated automatically in CI
- every releasable authority build produces a versioned artifact tied to the repository `VERSION`
- the production deployment target on Hetzner consumes only approved, versioned artifacts
- authority-issued software licences are represented consistently as the platform `application_key` used for first-user onboarding
- the authority deployment contract explicitly supports `application_key + owner_email + installation_uuid` activation and later installation update policy
- authority schema changes are validated before production rollout
- deployment to Hetzner follows a documented preflight, rollout, verification, and rollback sequence
- authority remains the installation lifecycle control plane, but its own service deployment becomes auditable and repeatable

---

## Guiding Principles

### 1. Authority Must Be Released Like A Product, Not Updated By Hand

Manual server edits create drift between Git, the running server, and future rollback points. The Hetzner instance should run only from versioned release artifacts.

### 2. CI Must Validate Real Authority Behavior

The existing validation scripts are already the strongest local signal. CI should use them instead of replacing them with weaker smoke checks.

That includes the activation path in which a granted software licence becomes the persisted authority application key used by platform onboarding.

### 3. Production Deployment Must Be Artifact-Based

Hetzner should pull a released authority artifact, not rebuild source code ad hoc during deployment.

### 4. Database Migration Must Be A First-Class Deployment Step

Because authority is PostgreSQL-backed and holds installation, invitation, session, and entitlement state, schema changes must be checked explicitly before service cutover.

### 5. Rollback Must Be Designed Before The First Automated Production Release

A deployment path without a rollback path is incomplete.

### 6. Licence, Application Key, And Installation Identity Must Be One Contract

The proposal should use one consistent lifecycle contract across authority, installer, local settings, first-user onboarding, and later updates.

For the current platform direction, that contract is:

- software licence or entitlement issued online
- same licence identity surfaced as authority `application_key`
- key persisted locally through the settings flow
- activation evaluated against `application_key + owner_email + installation_uuid`
- ongoing update policy evaluated against the bound installation record

---

## Phase 1: Align `autonomous/ppl-meta-authority` With CI/CD

## Workstream 0. Scope Alignment With Platform Installation Lifecycle

Before automating release and deployment, the authority proposal should be explicit about the service boundary it is automating.

Required scope alignment:

- authority remains the source of truth for entitlement and licence state
- the owner's software licence number is treated as the authority application key used in onboarding
- the application key persisted at `http://localhost:3000/#/settings` is the same authority-controlled key, not a second local-only credential
- first-user activation uses the authority contract already described in the installation proposals
- post-activation update eligibility remains keyed by the bound `installation_uuid`

Required authority capabilities under this model:

- create a pending entitlement for an owner
- generate or assign the software licence number as the authority application key
- activate an installation from `application_key + owner_email + installation_uuid`
- return bound installation state, owner approval state, and licence status
- continue evaluating update eligibility against the same installation record

Expected deliverables:

- authority proposal language aligned with the installation lifecycle proposals
- documented terminology rule that software licence number and authority application key refer to the same onboarding credential in the MVP flow
- explicit verification that the frontend settings contract persists that onboarding credential and the bound installation UUID

## Authority API Contract For Licence-Backed Onboarding

The authority proposal should name the concrete API contract that the platform onboarding flow depends on.

### 1. Admin Creates Or Updates The Entitlement Record

The current admin-managed entitlement payload is represented by the installation upsert model in the authority service.

Current request shape:

- `entitlement_uuid` optional
- `installation_uuid` optional
- `application_key` optional, minimum length 3
- `approved_owner_email` required
- `owner_enabled` default `true`
- `licence_status` default `active`
- `offline_grace_days` default `14`
- `tenant_name` optional
- `notes` optional

Current persisted record shape includes:

- `entitlement_uuid`
- `installation_uuid`
- `application_key`
- `approved_owner_email`
- `owner_enabled`
- `licence_status`
- `offline_grace_days`
- `tenant_name`
- `activation_status`
- `notes`

Under the aligned platform model, the owner-facing software licence number should be stored and surfaced through this `application_key` field.

### 2. First-User Activation Endpoint

The authority service already exposes the activation endpoint:

- `POST /api/v1/installations/activate`

Current request payload:

- `application_key`
- `installation_uuid`
- `owner_email`

Current success response fields:

- `approved = true`
- `reason = approved_owner`
- `entitlement_uuid`
- `installation_uuid`
- `application_key`
- `approved_owner_email`
- `owner_enabled`
- `licence_status`
- `offline_grace_days`
- `tenant_name`
- `activation_status`
- `notes`

Current failure reasons already supported by the implementation:

- `unknown_application_key`
- `owner_email_not_approved`
- `owner_disabled`
- `licence_inactive`
- `installation_already_bound_elsewhere`

This is the core control-plane contract that the platform settings flow and first-user onboarding must keep using.

### 3. Installation State Reporting Endpoint

The authority service currently exposes:

- `POST /api/v1/installations/report-state`

Current request payload:

- `installation_uuid`
- `current_release_version`
- `deployment_mode` optional
- `health_state` optional
- `components` object mapping component name to version

This endpoint is the first post-activation lifecycle reporting surface and should remain tied to the same bound installation record.

### 4. Update Eligibility Endpoint

The authority service currently exposes:

- `POST /api/v1/installations/check-update`

Current request payload:

- `installation_uuid`
- `target_release_version`

Current response fields:

- `allowed`
- `reason`
- `installation_uuid`
- `current_release_version`
- `target_release_version`

This is the minimum CI/CD contract for installation-aware release gating.

### 5. Update Result Endpoint

The authority service currently exposes:

- `POST /api/v1/installations/report-update-result`

Current request payload:

- `installation_uuid`
- `from_release_version` optional
- `to_release_version`
- `status` in `pending|running|succeeded|failed|rolled_back`
- `failure_reason` optional
- `components` object mapping component name to version

The authority CI/CD plan should treat these four installation endpoints as the minimum production contract that must not drift.

### 6. Platform Settings Contract

The current frontend settings screen already models the persisted onboarding values that the local installation needs:

- `Application key`
- `Installation UUID`

For CI/CD alignment, this proposal should treat that settings contract as an external dependency of the authority API rather than as a UI-only convenience.

That means:

- authority releases must not break the meaning of those two persisted values
- authority activation responses must continue to support the same onboarding pair
- deployment verification should confirm that the production authority still honors values persisted through the settings flow

## Workstream 1. Repository And Runtime Standardization

The authority service should be made releaseable as a self-contained unit inside the repository.

Required work:

- define the authority service root for CI as `autonomous/ppl-meta-authority`
- standardize the Python runtime version used locally, in CI, and in production
- standardize dependency installation from the authority requirements file
- document the production start command and runtime entrypoint in one canonical place
- define the required environment variables for each environment class: local, CI, staging, production
- separate bootstrap-only settings from normal production settings

Expected deliverables:

- authority environment matrix document or README section
- canonical runtime entrypoint definition
- `.env.example` or equivalent non-secret template for authority

## Workstream 2. Automated Validation In CI

The authority service already has useful validation scripts. CI should formalize them as the release gate.

Required CI checks:

- Python dependency install succeeds
- import and syntax validation succeeds
- authority validation scripts run successfully
- service startup against CI PostgreSQL succeeds
- bootstrap-only behavior is never enabled in production-mode validation
- entitlement issuance and first-user activation semantics remain compatible with the platform onboarding contract
- the persisted settings contract for application key and installation UUID does not drift from authority expectations

Recommended minimum CI validation sequence:

1. create Python environment
2. install authority dependencies
3. provision PostgreSQL service for CI
4. set `AUTHORITY_DATABASE_URL` for CI
5. run authority validation scripts
6. fail the workflow if any script fails

The initial CI gate should include at least:

- `validate_authority_auth_dashboard.py`
- `validate_authority_invitations_assignments.py`
- `validate_authority_reseller_scope.py`
- `validate_authority_distributor_scope.py`
- `validate_authority_admin_ui.py`
- `validate_authority_admin_e2e_workflow.py`

The authority CI plan should also add or extend coverage for the following path:

1. create pending owner entitlement
2. issue or expose the software licence as authority application key
3. persist the application key and installation UUID through the platform settings contract
4. activate first owner using `application_key + owner_email + installation_uuid`
5. reject mismatched email, invalid key, inactive licence, or double-bind attempts

Expected deliverables:

- GitHub Actions workflow for authority validation
- deterministic CI PostgreSQL configuration
- clear pass or fail release gate tied to pull requests and release branches or tags

## Workstream 3. Versioning And Release Identity

Authority releases should inherit the repository platform version while still being identifiable as authority artifacts.

Required work:

- use the root `VERSION` file as the platform release source
- define an authority artifact tag convention derived from that version
- record the authority release version in published artifact metadata
- tie release tags to immutable Git commits

Recommended tagging shape:

- platform version: `2.24.90`
- Git tag: `v2.24.90`
- authority image tag: `authority-2.24.90`
- optional immutable tag: `authority-2.24.90-<shortsha>`

Expected deliverables:

- documented authority tag naming convention
- release workflow that reads `VERSION`
- authority artifact metadata that can be traced back to the Git tag and commit

## Workstream 4. Artifact Packaging

Authority needs a production-consumable artifact. The preferred artifact should be a container image, because the existing Hetzner authority path already references containerized hosting.

Required work:

- add or finalize a production-grade Dockerfile for `autonomous/ppl-meta-authority`
- ensure the image contains only what is needed to run the service
- externalize secrets and runtime configuration through environment variables
- define health check behavior for the container
- publish the built image to GitHub Container Registry

Minimum artifact contract:

- image is version-tagged
- image is reproducible from Git
- image can run with external PostgreSQL configuration
- image exposes the expected service port
- image supports `/health` validation

Expected deliverables:

- authority Dockerfile
- authority image publication workflow
- GHCR repository naming convention for authority

Recommended registry path:

- `ghcr.io/nickglezakos/ppl-meta-authority`

If the platform later prefers a monorepo namespace convention, that can become:

- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-authority`

The important constraint is stable, documented naming.

## Workstream 5. Deployment Configuration Separation

Production deployment should not reuse local development configuration verbatim.

Required work:

- define production environment variables for authority
- remove any dependence on local bootstrap defaults in production
- define production logging behavior
- define database connection, reverse proxy, and session/security settings explicitly
- define how secrets are stored on Hetzner and how they are rotated

Minimum production configuration set:

- `AUTHORITY_DATABASE_URL`
- bootstrap gate disabled by default
- session/auth secrets if required by runtime
- production base URL
- trusted proxy or host settings if needed
- log level

Minimum platform activation contract that production must support:

- production authority base URL reachable from installations
- application key values generated and stored by authority
- installation activation endpoint enabled in production
- compatibility with the platform settings flow that stores `application_key` and `installation_uuid`

Expected deliverables:

- production `.env` template without secrets
- secret inventory for Hetzner
- documented secret rotation procedure

## Workstream 6. Migration And Backward-Compatibility Gate

Authority stores persistent operational data. Schema change safety must be enforced before production deployment.

Required work:

- define the supported migration path for PostgreSQL schema changes
- define whether startup auto-migration remains acceptable in production or whether migration becomes a separate explicit deployment step
- add a migration rehearsal to CI for schema-changing releases
- define backup requirements before applying migrations on Hetzner

Recommended rule:

- production deployment should run a dedicated migration or schema verification step before service restart
- if migration fails, deployment stops before traffic cutover

Expected deliverables:

- migration checklist or script
- production backup-before-migrate runbook step
- rollback rule for failed schema changes

Migration compatibility should also verify that entitlement records, application keys, installation bindings, and update eligibility data remain readable after deployment.

## Workstream 7. Release Promotion Policy

Not every passing commit should go straight to the Hetzner production host.

Required work:

- define which Git event creates an authority release candidate
- define which Git event approves production deployment
- define who can promote authority to production
- define the minimal verification evidence required before production promotion

Recommended flow:

1. pull request validates authority in CI
2. merge to `main` may publish a release candidate image
3. version tag publishes the production candidate image
4. production deployment is triggered only for an approved version tag or an explicit manual release action

Expected deliverables:

- authority promotion policy
- release checklist for production approval

---

## Phase 2: Deploy `autonomous/ppl-meta-authority` To Hetzner

## Deployment Architecture Recommendation

The Hetzner production path should use four layers:

1. GitHub as the source of truth for code and release tags
2. GitHub Actions as the build and validation layer
3. GitHub Container Registry as the artifact source
4. Hetzner host as the runtime node, with reverse proxy and PostgreSQL backing services

The Hetzner host should not compile authority from source during routine production deployment.

The Hetzner deployment should also be the production authority endpoint that platform applications contact when they persist a software licence as the authority application key and later activate the first owner.

---

## Hetzner Deployment Workstreams

## Workstream 8. Server Baseline Verification

Before automating deployment, verify the production host baseline.

Required checks:

- the Hetzner host is reachable through SSH using the intended operator account
- Docker and Docker Compose are installed and working
- reverse proxy configuration for `authority.eyenet-vision.com` is present and understood
- PostgreSQL is available either on-host or through a reachable managed endpoint
- production DNS and TLS are already working or can be reissued safely
- the host has enough disk space for image pull, logs, and backups

Expected deliverables:

- server baseline checklist
- verified runtime directories and ownership on the server
- documented deployment user and permissions model

## Workstream 9. Production Runtime Layout On Hetzner

The authority deployment should use a fixed directory layout on the server.

Recommended layout:

- `/opt/ppl-meta/authority/compose/`
- `/opt/ppl-meta/authority/env/`
- `/opt/ppl-meta/authority/backups/`
- `/opt/ppl-meta/authority/logs/`

Required work:

- define where compose or runtime manifests live
- define where the production `.env` file lives
- define where database backup artifacts are stored before rollout
- define log persistence expectations

Expected deliverables:

- production directory convention
- deployment user permissions for those paths

## Workstream 10. Production Compose Or Runtime Manifest

Even if the final production path stays Docker Compose-based, it must be version-aware and artifact-based.

Required work:

- create or finalize a production compose file for authority
- point the service image to GHCR rather than a local build
- parameterize the image tag or digest
- wire the container to production env files and reverse proxy expectations
- define restart behavior and health checks

The production runtime manifest should support:

- image replacement without editing application code on the host
- deterministic rollback to the previous image tag
- separate configuration from image version

Expected deliverables:

- production compose file or equivalent runtime manifest
- documented image update variable or deployment parameter

## Workstream 11. Deployment Automation

Hetzner deployment should be performed by a script or workflow, not by an operator manually remembering commands.

Recommended deployment sequence:

1. select approved authority version
2. pull the approved image from GHCR
3. create a PostgreSQL backup or snapshot checkpoint
4. run schema verification or migration step
5. update the runtime manifest to the target image
6. restart the authority service
7. wait for health endpoint success
8. run post-deploy API validation
9. record deployment outcome

The first implementation can be either:

- a GitHub Actions manual workflow that SSHs into Hetzner and runs a deployment script
- or a server-resident deployment script invoked manually with a target version

The preferred initial implementation is:

- server-resident deployment script plus a manually triggered GitHub Actions wrapper

That gives repeatability without making the first production release depend on a fully unattended SSH automation path.

Expected deliverables:

- `deploy_authority.sh` or equivalent
- optional GitHub Actions `workflow_dispatch` deployment workflow
- deployment logs and exit-code handling

## Workstream 12. Post-Deploy Verification

A deployment is not complete when the container starts. It is complete when the service behaves correctly.

Required verification after deployment:

- `GET /health` returns success through the public authority URL
- admin UI loads at `/admin`
- auth endpoints respond correctly
- at least one protected admin call succeeds with valid credentials
- database-backed reads still work
- no bootstrap-only path is available in production
- recent invitation and session flows still work on the production dataset
- entitlement issuance still produces the application key value used by platform onboarding
- first-user activation still accepts the correct `application_key + owner_email + installation_uuid` combination
- the platform settings contract remains valid for persisted `application_key` and bound `installation_uuid`

Recommended verification layers:

1. infrastructure health check
2. API health check
3. authenticated smoke check
4. targeted authority data check

Expected deliverables:

- post-deploy verification checklist
- optional production smoke script

## Workstream 13. Rollback And Recovery

Rollback should be simple enough to run under pressure.

Minimum rollback design:

- retain the previous approved image tag
- retain the pre-deploy runtime manifest or image reference
- take a database backup before any schema-affecting deployment
- define when image rollback alone is safe and when database recovery is needed

Recommended rollback rule:

- if application health fails but schema is still compatible, roll back to the previous image immediately
- if schema migration partially applied and broke compatibility, stop and execute the database recovery plan instead of guessing

Expected deliverables:

- rollback runbook
- explicit decision tree for image rollback versus database restore

---

## Proposed Delivery Sequence

The development and deployment work should be executed in this order.

### Stage 1. CI Foundation

- standardize runtime and environment contract
- implement authority CI validation workflow
- make CI PostgreSQL-backed checks green and stable
- add activation-flow validation for software licence to application-key alignment

### Stage 2. Artifact Releaseability

- add or finalize authority production Dockerfile
- publish versioned authority images to GHCR
- bind authority release output to `VERSION` and Git tags

### Stage 3. Production Deployment Contract

- create production compose manifest
- create server env template and secret inventory
- create deployment and rollback scripts

### Stage 4. Hetzner Rehearsal

- test deployment against a non-production Hetzner path or rehearsal environment if available
- validate migration step, health step, and rollback step
- capture timing, failure cases, and missing secrets

### Stage 5. Production Cutover

- back up production PostgreSQL
- deploy the approved authority image
- run post-deploy checks
- confirm public authority URL, admin shell, and authenticated admin API behavior
- confirm a platform installation can persist the authority application key in settings and use it for first-user activation

### Stage 6. Operational Hardening

- add log rotation and monitoring
- add alerting for health degradation and container restart loops
- document on-call operational steps

---

## Suggested GitHub Actions Structure

A pragmatic first pass can use three workflows.

### 1. `authority-ci.yml`

Runs on pull requests and `main` changes affecting the authority service.

Responsibilities:

- install dependencies
- provision PostgreSQL service
- run authority validation scripts
- report status back to GitHub checks

### 2. `authority-release.yml`

Runs on version tag creation or approved manual dispatch.

Responsibilities:

- read `VERSION`
- build authority image
- tag image
- publish image to GHCR
- emit release metadata

### 3. `authority-deploy-hetzner.yml`

Runs by manual approval only.

Responsibilities:

- accept target authority version
- connect to Hetzner using deployment credentials
- invoke the server deployment script
- collect deployment result

This is enough to create separation between validate, publish, and deploy.

---

## Suggested Acceptance Criteria

This proposal should be considered implemented only when all of the following are true.

### CI Alignment Complete

- authority pull requests run automated validation in CI
- CI uses PostgreSQL, not SQLite fallback assumptions
- CI fails on broken authority validation scripts
- release builds produce a versioned authority artifact
- release artifact is published to GHCR and is traceable to a Git tag
- CI proves that the software licence to application-key onboarding contract still works
- CI proves that first-user activation remains keyed by `application_key + owner_email + installation_uuid`

### Hetzner Deployment Ready

- Hetzner runtime manifest consumes published authority image tags
- production secrets are externalized from Git
- deployment script can update the running authority version deterministically
- pre-deploy backup and post-deploy verification are documented and executed
- rollback procedure has been tested at least once
- the live Hetzner authority can issue or expose the same application key later consumed by platform onboarding

### Production Service Validated

- public health endpoint passes after deployment
- admin shell loads successfully
- authenticated admin API calls succeed
- production bootstrap path remains disabled
- existing authority data remains readable and valid after deployment
- a valid owner entitlement can be turned into the application key used in the platform settings flow at `http://localhost:3000/#/settings`
- that persisted key can activate the first owner against production authority when paired with the approved owner email and real installation UUID

---

## Risks And Constraints

The main risks are:

- schema changes applied without tested rollback
- drift between local validation behavior and CI runtime behavior
- drift between CI artifact and Hetzner runtime configuration
- accidental exposure of bootstrap or secret-bearing configuration in production
- deploying from mutable tags rather than immutable approved versions
- drift between software licence issuance, application-key persistence, and first-user activation semantics across authority, installer, and frontend settings

The implementation should treat these as release blockers, not documentation footnotes.

---

## Recommendation

The recommended immediate next step is not to deploy straight to Hetzner. It is to complete the CI foundation and artifact packaging first.

The shortest safe path is:

1. add authority CI workflow with PostgreSQL-backed validations
2. add authority production Dockerfile and GHCR publication workflow
3. add Hetzner production compose and deployment script
4. rehearse backup, deploy, verify, and rollback once
5. promote the first tagged authority release to production

That sequence keeps the first real authority production deployment controlled and reversible.

---

## Implementation Summary

In practical terms, the work required is:

- make authority consistently testable in CI
- make authority publishable as a versioned production artifact
- make Hetzner consume only released authority artifacts
- make software licence issuance, authority application key persistence, and first-user activation one continuous documented contract
- make database migration, verification, and rollback explicit
- make the production rollout operationally routine rather than manual knowledge

That is the minimum bar for saying `autonomous/ppl-meta-authority` is aligned with CI/CD and properly deployable to Hetzner.
