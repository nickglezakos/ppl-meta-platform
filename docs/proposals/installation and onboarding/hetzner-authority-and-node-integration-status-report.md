# Hetzner Authority And Node Integration Status Report

**Date**: May 11, 2026  
**Status**: In Progress  
**Scope**: Implementation status of the Hetzner authority service, local Node integration, security hardening completed so far, current verified behavior, open gaps, and recommended next development steps  
**Related Documents**: [docs/proposals/installation and onboarding/hetzner-minimal-owner-licence-lifecycle.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/hetzner-minimal-owner-licence-lifecycle.md), [docs/proposals/installation and onboarding/windows-installer-private-registry-deployment.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/windows-installer-private-registry-deployment.md), [docs/proposals/installation and onboarding/first-batch-packaging-split-docker-and-apk.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/first-batch-packaging-split-docker-and-apk.md)

---

## Purpose

This document records the current implementation state after the initial Hetzner authority-service build and the first `ppl-meta-node` integration pass.

It is intended as a resume point for later development.

The goal is to make the following explicit:

1. what has already been implemented and verified
2. what is only partially implemented
3. what is still missing before this becomes a complete production-ready owner and licence lifecycle
4. what the recommended next development steps are

---

## High-Level Outcome So Far

The project has moved beyond proposal-only status.

The following are now real implementation surfaces, not just design notes:

- a live Hetzner-hosted authority service is running behind HTTPS
- the authority service has persistent installation ownership records
- the authority service has a token-protected admin API
- the authority service has a minimal private admin UI
- `ppl-meta-node` now uses the authority service to influence local owner convergence
- `ppl-meta-node` now stores cached authority validation state and offline grace metadata locally

This means the platform is no longer purely local-owner-driven in the areas that have been integrated.

---

## What Has Been Implemented

## 1. Hetzner Authority Service

Implemented location:

- `autonomous/ppl-meta-authority`

Implemented capabilities:

- FastAPI-based service scaffold
- persistent SQLite-backed installation registry
- public health endpoint
- public installation lookup endpoint
- public owner lookup endpoint
- token-protected admin endpoints for installation management
- minimal admin UI page at `/admin`
- Docker packaging and compose deployment
- Caddy reverse proxy on the Hetzner server
- public HTTPS hostname at `authority.eyenet-vision.com`

Implemented data model fields in the authority service MVP:

- `installation_uuid`
- `application_key`
- `approved_owner_email`
- `owner_enabled`
- `licence_status`
- `offline_grace_days`
- optional `tenant_name`
- optional `notes`

Verified live behavior:

- public health endpoint responds over HTTPS
- admin API rejects invalid bearer tokens
- admin API accepts the configured token
- installation records can be created and retrieved through the live service
- admin UI is publicly reachable at the expected path and uses the protected admin API
- container-level OpenAPI inspection confirms admin routes are present in the running image

---

## 2. Hetzner Server Provisioning

Completed server work:

- fresh Hetzner server created
- SSH key access configured
- `deploy` user created
- Docker installed and verified
- Caddy installed and configured
- DNS subdomains pointed at the server via Cloudflare
- authority service deployed as a Docker container
- service reachable via public HTTPS

Security work completed:

- authority admin API protected by bearer token
- token now sourced from server-side `.env` instead of the compose file
- placeholder token no longer works
- real configured token works

Important note:

- one token was exposed during setup and later rotated; any token previously pasted into chat should be considered compromised and not reused
- the admin token was later exposed again in terminal output during validation and should be rotated again before further use

---

## 3. `ppl-meta-node` Authority Integration

Implemented location:

- `ppl-meta-node/src/services/authority_service.py`
- `ppl-meta-node/src/services/user_service.py`
- `ppl-meta-node/src/main.py`
- `ppl-meta-node/src/models/installation_info.py`
- `ppl-meta-node/src/api/licences.py`
- `ppl-meta-node/src/config.py`

Implemented behavior:

### First-user owner path

The first-user owner-registration flow in Node is no longer purely local.

It now checks the authority service before attempting owner registration.

Approval currently depends on:

- authority integration enabled in config
- matching installation UUID
- matching application key
- matching approved owner email
- `owner_enabled = true`
- `licence_status` in `active` or `grace`

### Startup role convergence

The previous local development bootstrap logic in Node has been changed.

Current behavior:

- `fresh.user@example.com` is no longer guaranteed owner just because startup seeded it that way historically
- when authority is enabled, Node asks the Hetzner authority whether `fresh.user@example.com` is approved as owner
- if not approved, Node downgrades `fresh.user@example.com` to `admin,user`
- if another seeded local user is the authority-approved owner, Node converges that user to `owner,admin,user`

This is now verified in startup logs.

### Local cached authority state

Node now stores authority validation state in `installation_info`.

Cached fields currently include:

- approved owner email
- licence status
- owner enabled flag
- offline grace days
- last checked time
- last successful check time
- last result reason

### Offline grace fallback

If authority verification fails because the remote service is temporarily unavailable, Node can preserve owner approval when:

- cached approved owner email matches the current user
- cached owner is enabled
- cached licence status is still `active` or `grace`
- cached grace window has not expired

### Status API for inspection

Node now exposes an authority status endpoint:

- `GET /licensing/authority/status`

This is intended to show:

- whether authority integration is enabled and configured
- current cached authority state
- last successful check timestamps
- cache expiry timing
- whether the cache is still within the offline grace window

---

## Current Verified Runtime Behavior

The following behavior has been verified from the live logs and live service calls.

### Authority service

- `https://authority.eyenet-vision.com/health` responds successfully
- `https://authority.eyenet-vision.com/admin` responds successfully
- invalid admin bearer token returns `403`
- valid configured bearer token returns `200`
- authority installation record for `tenant-a` exists and is retrievable
- direct in-container requests to `/api/v1/admin/installations` succeed and return the expected installation data
- direct in-container fetch of `/admin` succeeds after normal container startup completes

### Node startup

Verified startup outcome from logs:

- Node contacts the authority service successfully
- Node receives `not_approved_owner` for `fresh.user@example.com`
- Node promotes `nick.glezakos@gmail.com` as the authority-approved owner for `tenant-a`
- Node converges `fresh.user@example.com` to `admin,user`
- Node completes startup successfully after the migration and owner handoff fixes

This confirms the authority service is now influencing the local owner decision path.

---

## Important Current Role Outcome

For the current authority record:

- installation UUID: `tenant-a`
- application key: `key-a`
- approved owner email: `nick.glezakos@gmail.com`

The resulting local behavior is now:

- `nick.glezakos@gmail.com` becomes the effective owner path when authority is enabled
- `fresh.user@example.com` remains `admin,user`, not `owner`

This is a deliberate result of the current authority data.

If later development wants `fresh.user@example.com` to remain the full-power development owner, the authority record must be updated to make that email the approved owner for the relevant installation.

---

## What Was Fixed During Implementation

Several implementation defects were encountered and resolved.

### Fixed in authority-service work

- live deployment initially served stale source files after `scp -r`
- deployment flow was corrected by using `rsync --delete`
- admin token was initially hardcoded in compose and later moved to `.env`
- live token verification was confirmed after hardening
- an apparent `404` on admin routes was traced to wrong execution context or wrong listener rather than missing admin route registration
- an apparent `/admin` failure during one validation pass was traced to container startup timing and succeeded on retry after a short delay

### Fixed in Node integration work

- authority-aware startup initially used SQLite-specific schema inspection (`PRAGMA`) and failed against PostgreSQL
- schema inspection was changed to SQLAlchemy inspector-based logic
- migration initially used `DATETIME` and failed on PostgreSQL
- timestamp migration types were changed to PostgreSQL-compatible `TIMESTAMP`
- owner handoff initially failed because Node tried to remove the final owner before assigning the authority-approved owner
- owner handoff order was corrected
- bootstrap initially re-downgraded the newly assigned authority-approved owner back to `user`
- seeded-user bootstrap logic was corrected to preserve the authority-approved owner

---

## What Is Still Incomplete

The current implementation is a strong MVP foundation, but it is not complete.

### 1. Authority-side gaps

- no full admin authentication system beyond bearer token
- no multi-user admin model
- no audit trail for authority admin changes
- no licence-plan model beyond current status fields
- no heartbeat worker or periodic validation API yet
- no explicit owner recovery workflow yet
- no dedicated separation between API hostname and admin hostname behavior yet
- admin token rotation procedure is still manual and should be documented or automated

### 2. Node-side gaps

- authority cache status endpoint exists in code but still needs explicit runtime verification in the user flow
- no frontend/UI warning surface yet for authority offline status or grace expiry
- no periodic background authority revalidation worker yet
- no enforcement layer yet for what should happen when offline grace expires
- no comprehensive tests yet for the new authority integration behavior

### 3. Wider platform gaps

- bootcore licensing integration still returns `404` for `platform/register` in current startup logs
- some inter-service JWT validation is still failing elsewhere in the platform
- several unrelated service startup issues remain outside the authority slice

These should not be confused with authority-service failure. They are adjacent platform issues.

---

## Recommended Next Development Steps

The recommended order for resuming work later is:

### Step 1. Verify the Node authority status endpoint at runtime

Use a valid Node JWT and confirm:

- authority is enabled
- authority is configured
- cached owner email is present
- cached licence state is present
- offline grace timing is visible

This is the quickest proof that the cache path is not only implemented but actually populated as intended.

Before doing this, rotate the currently exposed authority admin token again and verify the old token no longer works.

### Step 2. Fix the remaining stale startup log message

One startup message still reports:

- `nick=user`

even when `nick.glezakos@gmail.com` has just been converged as owner.

That message should be updated so the logs reflect the actual converged roles.

### Step 3. Add a periodic authority validation worker

Node should not only validate on first-user and startup paths.

It should also revalidate periodically and refresh:

- last checked timestamp
- last successful check timestamp
- licence status
- owner enabled state
- offline grace window

### Step 4. Add local UI-visible authority/offline warning state

The platform should surface clear warnings when:

- the authority service is unreachable
- the system is operating from cached approval
- the offline grace window is close to expiry
- the offline grace window has expired

### Step 5. Decide the final owner policy for development vs production

There is a real policy decision still open:

- should the dev environment keep `fresh.user@example.com` as owner
- or should the authority-approved record remain the only source of truth even in development

That decision should be made explicitly and reflected in the authority data model for each environment.

### Step 6. Resolve the adjacent bootcore/licensing mismatch

Current logs still show `404` on:

- `POST http://localhost:8007/api/v1/platform/register`

This is not part of the Hetzner authority flow itself, but it is still active in the Node service and should be reconciled so there are not two overlapping licence/owner authorities moving in different directions.

---

## Recommended Resume Checklist

When resuming later, start with this checklist.

1. Confirm the Hetzner authority service is still live and reachable.
2. Confirm the current approved owner email for the active installation.
3. Confirm `ppl-meta-node` local env still contains the authority settings.
4. Start `ppl-meta-node` and check startup logs for authority owner convergence.
5. Call `GET /licensing/authority/status` with a valid Node JWT.
6. Decide whether to continue with:
   - periodic revalidation worker
   - UI alerting
   - bootcore/licensing cleanup
   - additional tests

---

## Current Resume Summary

At the time this report was written:

- the Hetzner authority service is implemented and live
- the authority service has persistent installation records and protected admin management
- the authority service is influencing `ppl-meta-node` owner convergence successfully
- offline grace cache plumbing exists in Node
- Node startup has been brought to a successful authority-aware state
- the next phase is refinement, periodic validation, observability, and policy cleanup rather than first implementation

This is a suitable point to pause and resume later.