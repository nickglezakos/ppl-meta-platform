# PPL Meta Platform + Apps Deployment & Update Pipeline Proposal

## 1) Executive Summary

This proposal defines a single deployment model for the **PPL Meta Platform** and **PPL Meta Apps**, with a practical path to:

1. Validate deployment end-to-end first.
2. Then deliver product updates (including the upcoming user-permissions dashboard and admin permission assignment).
3. Keep release risk low across cloud, on-prem, Windows, Android, and Raspberry Pi targets.

The operating principle is **one release governance model**, with **two distribution tracks**:
- **Platform track**: backend services + web frontend via Docker bundles.
- **Apps track**: Android APKs and Raspberry Pi signage variant.

---

## 2) Product Segmentation (Business View)

### A. Apps Portfolio
- `ppl-meta-edge-camera`
- `ppl-meta-frontend` (mobile/desktop app distributions)
- `ppl-meta-signage-simple-player` (Android + Raspberry Pi variant)

### B. Platform Portfolio
- All remaining backend services (node/media/gateway/orchestrator/cameras/vision/discovery/communications/bootcore/vmeta/etc.)
- Web deployment of `ppl-meta-frontend`

This split supports clearer packaging, support ownership, and customer communication while preserving one platform roadmap.

---

## 3) Target Deployment Architecture

## Core approach
- Package each service as versioned Docker images.
- Deliver a **deployment bundle** per release (Compose files, env templates, health checks, startup scripts, rollback scripts).
- Include operational automations directly in deployment artifacts (no ad-hoc manual runbooks as the primary path).

## Environment model
- **Dev** -> **Staging** -> **Production** with promotion gates.
- Immutable release tags across all artifacts (platform images, web assets, app packages).

## Runtime model
- Primary deployment: Docker Compose for local/on-prem and customer environments.
- Optional evolution: Kubernetes/Swarm later if scale or multi-tenant operations demand it.

---

## 4) Windows Installation Variant (Docker Bundle)

The Windows option is a **packaged installer experience** built around Docker Desktop (or enterprise-approved container runtime), not a custom container engine.

## Expected user flow
1. Launch installer/launcher dashboard.
2. Prerequisite checks run automatically.
3. If Docker is missing, user is prompted to install it.
4. If Docker is installed but not running, launcher starts Docker and waits for health.
5. One-click actions become available:
   - Start platform
   - Stop platform
   - Open health/status dashboard
   - View logs

## Enterprise-friendly options
- Offline bundle variant for restricted networks.
- Proxy-aware configuration.
- Controlled update channel (stable/beta).

---

## 5) Deployment-First Validation Strategy (Immediate Priority)

Before implementing major feature updates (permissions dashboard/admin user permission assignment), run a deployment certification cycle first.

## Objective
Prove that packaging, install, startup, health checks, rollback, and environment config are reliable end-to-end.

## Scope
- Platform Docker deployment (all core services + web frontend).
- Windows installation flow with Docker prerequisite handling.
- App install/launch smoke checks:
  - Android APK flows.
  - Raspberry Pi signage variant flow.

## Exit criteria
- Deterministic install/start sequence.
- Health checks green for all critical services.
- Known-good rollback proven in staging.
- Release notes + operator runbook validated by non-developer operator.

---

## 6) Unified Update Pipeline Proposal

## Pipeline goal
Ship updates safely and repeatably across platform and apps using one release governance model.

## Stage 1: Source & Build
- Tag-driven builds for all components.
- Build and version:
  - Docker images (platform services + web frontend container).
  - Android APKs for app targets.
  - Raspberry Pi package/image for signage variant.

## Stage 2: Validation & Security Gates
- Automated checks:
  - Unit/integration/smoke tests.
  - Container/image scanning.
  - Configuration validation (env schema, required secrets).
  - API compatibility checks for platform-app interactions.

## Stage 3: Release Assembly
- Produce one release manifest containing:
  - Component versions.
  - Compatibility matrix.
  - Migration requirements.
  - Rollback references.
- Publish deployment bundle + app artifacts together under same release ID.

## Stage 4: Progressive Promotion
- Deploy to Dev -> Staging -> Production with approval gates.
- Require staging sign-off on:
  - Service health.
  - Core workflow smoke tests.
  - Upgrade + rollback verification.

## Stage 5: Post-Release Controls
- Monitor health/SLA and error budget windows.
- Keep rapid rollback trigger if thresholds breach.
- Publish release telemetry summary and known issues.

---

## 7) How This Supports the Permissions Dashboard Update

With deployment reliability verified first, the permissions feature rollout can follow a controlled update path:

1. Introduce permission model changes in staged releases.
2. Validate admin assignment workflows in staging against real deployment artifacts.
3. Promote only after upgrade + rollback + workflow checks pass.

This avoids mixing feature risk with unproven deployment mechanics.

---

## 8) Recommended Release Cadence

- **Monthly stable release** for production customers.
- **Bi-weekly integration release** for internal/staging validation.
- Emergency patch lane with reduced scope and accelerated approval.

---

## 9) Operating Model & Ownership

- **Platform/DevOps**: Docker bundles, deployment automation, infra checks, rollback readiness.
- **App teams**: APK/RPi packaging, compatibility with platform APIs, app-specific smoke tests.
- **QA/Release management**: stage gates, release certification, sign-off governance.

---

## 10) Business Outcomes

- Faster and safer deployments with lower operational variance.
- Better enterprise readiness via Windows on-prem install path.
- Cleaner release communication by separating app/platform packaging while preserving one release ID.
- Higher confidence for shipping upcoming permissions/admin features through a proven update pipeline.

---

## 11) Next-Step Implementation Plan (High Level)

1. Finalize release manifest format and compatibility matrix template.
2. Standardize Docker deployment bundle structure for all services.
3. Build Windows launcher/installer workflow with Docker prerequisite orchestration.
4. Run deployment-first certification cycle in staging.
5. Start permissions feature delivery on top of certified pipeline.

---

## 12) Decision Request

Approve this model as the standard go-forward release framework:
- **One governance model**
- **Two distribution tracks** (Platform and Apps)
- **Deployment-first validation** before major feature updates
- **Unified update pipeline** with strict promotion and rollback controls
