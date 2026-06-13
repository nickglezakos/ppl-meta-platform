# bootstrap testing guide

## Scope

This document defines how to test the first-install bootstrap flow introduced for:

- `ppl-meta-frontend`
- `ppl-meta-node`
- `autonomous/ppl-meta-authority`

It covers three things:

1. a concrete local test procedure
2. a synthetic Authority licence or installation seeding workflow
3. an automated backend test plan for the new bootstrap endpoints

## Testing Strategy

The bootstrap flow should be tested in two layers:

1. contract and integration testing with synthetic Authority data
2. one realistic end-to-end run with a real persisted Authority installation record in a non-production environment

The default development approach should use synthetic data stored in Authority. The Authority record should be real inside the Authority service, but the owner email, tenant name, and key values can be test-only values.

## What Counts As A Valid Test Record

For bootstrap activation to succeed, Authority must expose a persisted installation or entitlement contract with at least these effective values:

- `application_key`
- `approved_owner_email`
- `installation_uuid`
- `owner_enabled=true`
- `licence_status=active` or `licence_status=grace`

Node must be configured to talk to that Authority environment, and the installation identifier presented by Node must match the Authority record.

## Local Test Procedure

### Automated Test Goal

Validate that a fresh installation:

1. routes to the bootstrap flow
2. accepts the approved owner credentials plus application key
3. activates through Authority
4. creates the local owner user in Node
5. grants local `owner`, `admin`, and `user` roles
6. returns an authenticated session and lands in the normal app

### Preconditions

Before starting the flow, confirm:

1. Authority is running.
2. Node is running.
3. Frontend is running.
4. Node is pointed at the correct Authority service URL.
5. Node has either the correct installation identifier configured or a stable persisted installation GUID that matches the Authority test record.
6. Authority contains a test installation or entitlement record for the bootstrap run.

### Happy Path Procedure

1. Seed a synthetic Authority installation record with a test `application_key` and a test `approved_owner_email`.
2. Ensure the local Node user database does not already contain that owner email.
3. Open the frontend on a fresh unauthenticated session.
4. Confirm the frontend routes to `/bootstrap` instead of generic login.
5. Enter:
   - username
   - the Authority-approved owner email
   - password
   - the seeded application key
6. Submit the bootstrap form.
7. Confirm Node calls bootstrap activation successfully.
8. Confirm the frontend transitions into authenticated state.
9. Confirm the app lands on `/home`.
10. Confirm a subsequent unauthenticated revisit no longer routes to `/bootstrap` if bootstrap is complete.

### Verification Checklist

After a successful run, verify:

1. `GET /api/v1/licensing/bootstrap/status` returns `bootstrap_complete`.
2. The returned bootstrap status includes the approved owner email.
3. The local user exists in Node.
4. The local user has the `owner` role.
5. The local user also has `admin` and `user`.
6. Authority cache fields in Node show the approved owner email and a successful result reason.
7. The frontend can access protected routes without manual re-login.

### Negative Test Cases

Run these cases with synthetic test data:

1. Wrong application key with correct owner email.
2. Wrong owner email with correct application key.
3. Correct key and email, but `owner_enabled=false`.
4. Correct key and email, but `licence_status` is not `active` or `grace`.
5. Re-run bootstrap after completion and confirm the frontend no longer treats the installation as pending bootstrap.

Expected result:

- the frontend stays out of the authenticated app
- Node does not create an owner user for rejected cases
- bootstrap status remains incomplete
- rejection reason is visible in the frontend error path

## Synthetic Authority Seeding Workflow

### Why Use Synthetic Data

Synthetic Authority data is the preferred default because it is:

- repeatable
- disposable
- isolated from production licensing
- sufficient to validate the activation contract

You do not need a production commercial licence to test the bootstrap flow. You only need a real Authority-managed record with test values.

### Recommended Test Record Values

Example test values:

- `application_key`: `lic_11111111222233334444555555555555`
- `approved_owner_email`: `bootstrap.owner@example.com`
- `installation_uuid`: the installation identifier value that matches Node
- `tenant_name`: `Bootstrap Test Tenant`
- `owner_enabled`: `true`
- `licence_status`: `active`
- `offline_grace_days`: `14`

### Preferred Seeding Method

Authority already exposes an admin installation upsert endpoint:

- `POST /api/v1/admin/installations`

That endpoint accepts the Authority installation upsert contract and can be used to create or update the synthetic bootstrap record.

### Example Synthetic Seed Payload

```json
{
  "installation_uuid": "11111111-2222-3333-4444-555555555555",
  "application_key": "lic_11111111222233334444555555555555",
  "approved_owner_email": "bootstrap.owner@example.com",
  "owner_enabled": true,
  "licence_status": "active",
  "offline_grace_days": 14,
  "tenant_name": "Bootstrap Test Tenant",
  "notes": "Synthetic bootstrap test record"
}
```

### Example Curl Workflow

Use an Authority platform-admin session appropriate to the running environment. The preferred development path is to obtain a session token by logging in with Authority admin credentials.

Preferred token acquisition:

```bash
AUTHORITY_BASE_URL=https://authority.eyenet-vision.com \
AUTHORITY_ADMIN_EMAIL='<admin-email>' \
AUTHORITY_ADMIN_PASSWORD='<admin-password>' \
sh autonomous/ppl-meta-authority/scripts/get_authority_session_token.sh
```

That helper calls `POST /api/v1/auth/login`, verifies the session with `GET /api/v1/auth/me`, and prints the bearer token to stdout.

Example token capture:

```bash
AUTHORITY_ADMIN_TOKEN="$({
  AUTHORITY_BASE_URL=https://authority.eyenet-vision.com \
  AUTHORITY_ADMIN_EMAIL='<admin-email>' \
  AUTHORITY_ADMIN_PASSWORD='<admin-password>' \
  sh autonomous/ppl-meta-authority/scripts/get_authority_session_token.sh
})"
```

```bash
curl -X POST https://authority.eyenet-vision.com/api/v1/admin/installations \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $AUTHORITY_ADMIN_TOKEN" \
  -d '{
    "installation_uuid": "11111111-2222-3333-4444-555555555555",
    "application_key": "lic_11111111222233334444555555555555",
    "approved_owner_email": "bootstrap.owner@example.com",
    "owner_enabled": true,
    "licence_status": "active",
    "offline_grace_days": 14,
    "tenant_name": "Bootstrap Test Tenant",
    "notes": "Synthetic bootstrap test record"
  }'
```

If you already have a valid Authority admin token from another path, you can still use it directly. The credential-based helper is simply the preferred repeatable workflow.

### Matching Node Configuration

The test record must match what Node presents during activation.

That means one of these must be true:

1. Node is configured with `AUTHORITY_INSTALLATION_UUID` equal to the seeded `installation_uuid`.
2. The seeded Authority record uses the same installation identifier that Node reports as its effective installation identifier.

If the installation identifiers do not match, activation should fail even if the email and key are otherwise correct.

## Automated Backend Test Plan

### Goal

Add automated tests around the new bootstrap-specific backend contract in Node.

The primary targets are:

- `GET /api/v1/licensing/bootstrap/status`
- `POST /api/v1/licensing/bootstrap/activate`

### Recommended Test Coverage

#### Bootstrap status tests

1. Returns `not_started` when Authority is not configured.
2. Returns `awaiting_owner_activation` when Authority is configured but no approved owner is cached locally.
3. Returns `owner_approved` when Authority has approved an owner but Node has not yet assigned the local `owner` role.
4. Returns `bootstrap_complete` when the approved owner exists locally and carries the `owner` role.

#### Bootstrap activation tests

1. Successful activation creates the local user and returns a bearer token.
2. Successful activation assigns local `owner`, `admin`, and `user` roles.
3. Rejected activation returns a structured failure and does not create the owner user.
4. Duplicate email fails with the expected error.
5. Already-complete bootstrap returns conflict.
6. Authority-not-configured returns service unavailable.

### Mocking Strategy

For automated Node backend tests, Authority should be mocked at the service layer rather than requiring a live Authority process for every test.

Recommended approach:

1. patch or stub `authority_service.activate_owner_candidate`
2. patch or stub Authority configuration responses where needed
3. use an isolated Node test database
4. assert local user creation, local roles, and bootstrap-state payloads directly

### Minimum Happy Path Assertions

For a successful automated activation test, assert all of the following:

1. response status is success
2. response bootstrap state is `bootstrap_complete`
3. response contains `access_token`
4. local user exists with the seeded email
5. local role set includes `owner`
6. local role set includes `admin`
7. local role set includes `user`

### Recommended Manual Plus Automated Split

Use this split:

1. automated tests for Node bootstrap state and activation behavior
2. manual or integration tests for frontend routing and session transition
3. manual end-to-end validation against a live Authority test record before considering the flow ready

## Recommended Execution Order

Run bootstrap validation in this order:

1. automated backend tests for Node bootstrap status and activation
2. synthetic-data local integration run against live Authority
3. one realistic non-production acceptance run using a persisted Authority record that mirrors real issuance

## Summary

The bootstrap flow should be tested primarily with synthetic Authority data stored as real Authority records. A production commercial licence is not required for normal validation. The correct development path is to seed a non-production Authority installation record, run the local frontend and Node bootstrap flow against it, and back that with automated Node tests for the new bootstrap endpoints.
