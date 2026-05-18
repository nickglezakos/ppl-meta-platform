# First Batch Packaging Split: Docker Images And APK Deliverables

**Date**: May 10, 2026  
**Status**: Draft  
**Scope**: First packaging batch for installation and onboarding, defining which platform parts should ship as Docker images, which should remain APK installs, and which monorepo shared assets must remain available for interoperability  
**Related Documents**: [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md), [docs/proposals/installation and onboarding/hetzner-minimal-owner-licence-lifecycle.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/hetzner-minimal-owner-licence-lifecycle.md)

---

## Purpose

This document defines the **first packaging batch** for installation and onboarding.

The goal is to make the packaging split explicit:

1. which components should be delivered as Docker images
2. which components should remain APK-style installs for now
3. which components are out of scope for this first packaging pass
4. which shared monorepo assets must continue to exist so the packaged services still work together the way they do now in the mono-repo

This is a packaging and deployment-boundary proposal, not a runtime redesign.

---

## Packaging Principle

The first packaging batch should preserve the current runtime relationships between services as much as possible.

That means:

- package the existing backend/web services as containers
- keep the existing mobile-facing apps and signage player as installable app artifacts
- do not try to package every experimental or autonomous surface in the first pass
- keep shared contracts, configuration, and helper modules available to the packaged services

The key rule is:

- everything in the first batch should still know how to work together like it does now in the mono-repo

---

## APK Deliverables For The First Batch

For the first batch, the following should remain installable app artifacts rather than Docker services.

### 1. Mobile Camera App

Repository surface:

- `ppl_meta_mobile_camera`

Reason:

- this is a device-facing mobile application
- the current install pattern already fits APK delivery
- it is not a backend runtime service in the same sense as the platform microservices

### 2. Signage Player

Repository surface:

- `ppl-meta-signage-simple-player`

Reason:

- this is effectively a client/player installation target
- APK or app-style installation is more appropriate than turning it into a platform backend image

### 3. Frontend App Installations Already Existing

For the first batch, keep the existing APK-style installation outputs that already exist in the mobile/app delivery path.

This avoids mixing frontend device-install artifacts into the backend container packaging pass.

---

## Docker Images For The First Batch

For the first packaging batch, the following should be packaged as Docker images.

### Core Backend And Platform Images

1. `ppl-meta-cameras`
2. `ppl-meta-bootcore`
3. `ppl-meta-code`
4. `ppl-meta-communications`
5. `ppl-meta-discovery`
6. `ppl-meta-frontend` for **web delivery**
7. `ppl-meta-gateway`
8. `ppl-meta-media`
9. `ppl-meta-node`
10. `ppl-meta-orchestrator`
11. `ppl-meta-vision`
12. `ppl-meta-vmeta`

### Why These Belong In Docker

These components are the parts that make up the local platform runtime and should be installed, configured, started, and upgraded together as an interoperating service set.

For this first batch, they form the deployable backend/web platform.

---

## Out Of Scope For This First Packaging Batch

The following should **not** be packaged in this first pass.

### 1. Autonomous

Repository surface:

- `autonomous`

Reason:

- this should remain outside the first packaging batch for now
- it is better treated as a separate future packaging or productization stream

### 2. Edge Camera

Repository surface:

- `ppl-meta-edge-camera`

Reason:

- you explicitly do not want to pack it for now
- it likely has a device-specific deployment path that should stay separate until stabilized further

---

## Frontend Clarification

The frontend should be treated in two ways depending on target.

### Dockerized Frontend

- `ppl-meta-frontend` for web delivery should be packaged as a Docker image

This supports the local platform web UI and keeps the browser-based frontend aligned with the rest of the local stack.

### APK Or App-Style Frontend Installations

- keep the already existing APK/app installation outputs as they are for now

This avoids trying to force all frontend targets into the same packaging shape in the first batch.

---

## Vision And vmeta Protection Strategy

For the first packaging batch, `ppl-meta-vision` and `ppl-meta-vmeta` should still ship as Docker images, but they should not be treated like ordinary source-open Python service images.

The recommended rule for these two services is:

- keep the FastAPI shell, startup wiring, and non-sensitive integration glue as plain Python
- compile the proprietary processing and decision modules with Cython
- copy only the compiled extension artifacts for those protected modules into the final runtime image
- remove the original `.py` source for the protected modules from the final runtime image
- treat this as hardening, not as perfect secrecy

This keeps the deployment boundary intact while reducing direct source exposure for the two most sensitive services in the batch.

The concrete first-pass plan is documented in:

- `docs/proposals/installation and onboarding/vision-vmeta-source-protection-plan.md`

That plan also reflects an important constraint:

- if a piece of logic must remain truly secret, it should not be shipped in a customer-controlled Docker image at all and should instead move behind a private service boundary

---

## Shared Monorepo Assets That Must Continue To Travel With The Packaged Services

The first batch will only work well if the packaged services continue to share the same contracts and helper assets they use now.

The following repo-level shared surfaces are especially important.

### `shared/`

This is the most important shared runtime support area and should remain available to the Dockerized services during build and runtime where needed.

Important subareas include:

- `shared/auth`
- `shared/face_detection`
- `shared/logging`
- `shared/metrics`
- `shared/migrations`
- `shared/models`
- `shared/queue_config.py`
- `shared/redis_pubsub.py`
- `shared/service_discovery`
- `shared/storage`
- `shared/validation`

These shared modules help preserve the current mono-repo interaction model.

### `scripts/`

Not every script needs to ship into production images, but this directory contains useful operational and setup assets that should inform packaging and installer workflows.

Examples worth preserving or adapting:

- `scripts/setup-dev.sh`
- `scripts/setup-secrets.sh`
- `scripts/setup_migrations.py`
- `scripts/generate_migrations.py`
- `scripts/standardize_database_config.py`
- `scripts/optimize_docker_images.sh`
- `scripts/start-all-services.sh`
- `scripts/stop-all-services.sh`
- `scripts/test-nginx-local.sh`

These are useful for:

- image build conventions
- runtime setup
- migration handling
- local validation and troubleshooting

### `workers/`

Current surface:

- `workers/ppl_thread_worker.py`

This should be reviewed as part of the packaging process because worker behavior may need to stay aligned with the Dockerized service set even if it is not a top-level image by itself.

### Repo-Level Config And Support Assets

The packaged services may also continue to depend on repo-level support areas such as:

- `config/`
- `tools/`
- `utils/`
- `tests/` for validation and packaging checks
- root environment/config patterns such as `.env` and `.env.service-auth`

The first packaging batch should preserve the effective contracts from these assets, even if not every file is copied verbatim into each image.

---

## What “Know How To Work With Each Other Like Now” Means

For the first packaging batch, the Dockerized services should preserve the current platform interaction model.

That means they should continue to align on:

1. service-to-service URLs and ports
2. auth and service-auth configuration
3. shared models and validation expectations
4. queue and Redis conventions
5. discovery and inter-service registration behavior
6. database and migration conventions
7. frontend-to-gateway and gateway-to-backend contracts

The packaging process should not redefine these contracts yet. It should carry them forward into the first image-based deployment.

---

## Recommended First-Batch Output

The first batch should produce two packaging families.

### Family A. Dockerized Local Platform

This includes the containerized service set for local installation:

- cameras
- bootcore
- code
- communications
- discovery
- frontend web
- gateway
- media
- node
- orchestrator
- vision
- vmeta

### Family B. Installable Client Artifacts

This includes the device/app-side artifacts that remain outside the backend Docker packaging set:

- mobile camera APK
- signage player APK/app package
- any already existing frontend app installation outputs kept as-is for now

---

## Suggested Packaging Rule Per Component

The practical rule for this first batch is:

- if it is part of the always-on local backend/web platform, package it as Docker
- if it is installed onto a user/device endpoint, keep it as APK/app install for now
- if it is experimental, autonomous, or device-specialized and not yet ready, exclude it from the first packaging batch

---

## Recommended Conclusion

For the first packaging batch:

- keep `ppl_meta_mobile_camera`, `ppl-meta-signage-simple-player`, and the already-existing app-install frontend targets as installable app artifacts
- package `ppl-meta-cameras`, `ppl-meta-bootcore`, `ppl-meta-code`, `ppl-meta-communications`, `ppl-meta-discovery`, `ppl-meta-frontend` for web, `ppl-meta-gateway`, `ppl-meta-media`, `ppl-meta-node`, `ppl-meta-orchestrator`, `ppl-meta-vision`, and `ppl-meta-vmeta` as Docker images
- do not package `autonomous` or `ppl-meta-edge-camera` yet
- preserve the shared mono-repo contracts from `shared/`, useful operational assets from `scripts/`, and relevant worker/config support so the packaged services continue to interoperate exactly as they do now

That is the cleanest first packaging boundary for installation and onboarding.
