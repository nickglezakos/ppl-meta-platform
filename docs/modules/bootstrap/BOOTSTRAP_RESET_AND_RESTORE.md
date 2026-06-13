# bootstrap reset and restore

## Purpose

This document explains:

1. why the current installation is reported as bootstrap-complete
2. how to force the platform back into bootstrap-pending state for testing
3. how to restore the current development state afterward

## Current Status Reason

The current platform is reported as bootstrap-complete because all of the following are true:

1. Node bootstrap status currently returns `bootstrap_complete`.
2. Authority is enabled and configured.
3. Node cache currently reports the approved owner email as `nick.glezakos@gmail.com`.
4. That same user exists locally in Node.
5. That local user has the `owner` role.

The live status that was returned through the gateway was:

- `state: bootstrap_complete`
- `approved_owner_email: nick.glezakos@gmail.com`
- `local_owner_role_present: true`
- `installation_uuid: tenant-a` as the current installation identifier value

## Why This Reappears After Restart

Node startup contains a bootstrap reconciliation path in [ppl-meta-node/src/main.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/main.py#L330).

That startup logic:

1. asks Authority which owner email is currently approved for the installation
2. checks whether the approved owner exists locally
3. converges local system roles toward that Authority-approved owner

For the current setup, the startup logic uses:

- installation identifier: `tenant-a`
- Authority-approved owner email: `nick.glezakos@gmail.com`

So if you only log out, the platform does not become bootstrap-pending again. Logout affects session state only. It does not remove the approved owner relationship that marks bootstrap as complete.

## Best Reset Strategy For Testing

The safest way to force bootstrap-pending state without destroying local development data is:

1. keep Authority enabled
2. keep the installation identifier the same
3. change the Authority-approved owner email for that installation to a test email that does not exist locally in Node

That causes bootstrap status to stop being complete while preserving the rest of the environment.

## Reset To Bootstrap-Pending

### Recommended Test Values

Use a test owner that does not already exist in the local Node database, for example:

- `approved_owner_email`: `bootstrap.owner@example.com`
- `application_key`: keep the current one or use a dedicated test key
- `installation_uuid`: `tenant-a` as the installation identifier value

### Method A: Use Authority Admin UI

1. Open the Authority admin UI.
2. Find the installation record for `tenant-a`.
3. Change `approved_owner_email` from `nick.glezakos@gmail.com` to a new test email such as `bootstrap.owner@example.com`.
4. Keep `owner_enabled=true` and `licence_status=active`.
5. Save the installation record.
6. Restart Node.
7. Log out of the frontend if needed and reopen the auth flow.

Expected result:

1. bootstrap status is no longer `bootstrap_complete`
2. the frontend should route to `/bootstrap`
3. the login and register screens should show the bootstrap-state badge and bootstrap guidance

### Method B: Use Authority Admin API

You can also update the installation using the Authority admin installation upsert endpoint.

Example payload:

```json
{
  "installation_uuid": "tenant-a",
  "application_key": "lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f",
  "approved_owner_email": "bootstrap.owner@example.com",
  "owner_enabled": true,
  "licence_status": "active",
  "offline_grace_days": 14,
  "tenant_name": "Tenant A",
  "notes": "Temporary bootstrap reset for local testing"
}
```

After updating Authority, restart Node so startup reconciliation refreshes against the new approved owner email.

## What To Expect After Reset

After the reset, Node may still preserve an existing local owner role on another user if it cannot safely remove the final owner assignment.

That is acceptable for bootstrap testing because the bootstrap-status endpoint only marks the installation complete when the Authority-approved owner email:

1. exists locally
2. and that same approved owner has the `owner` role

If the approved owner email points to a non-local test email, bootstrap should remain incomplete even if another local user still carries `owner` temporarily.

## Reinstate Current Development State

When you are done testing, restore the current development setup like this.

### Restore Authority Record

Set the Authority installation record back to:

- `installation_uuid`: `tenant-a` as the installation identifier value
- `approved_owner_email`: `nick.glezakos@gmail.com`
- `application_key`: the current active key used by your Node environment
- `owner_enabled=true`
- `licence_status=active`

### Restart Node

After restoring the Authority record:

1. restart Node
2. let startup reconciliation run again
3. open the frontend auth flow or query bootstrap status through the gateway

Expected result:

1. bootstrap status returns `bootstrap_complete`
2. the approved owner email is again `nick.glezakos@gmail.com`
3. the login screen returns to normal non-bootstrap behavior

## Quick Verification Commands

### Check bootstrap status through gateway

```bash
curl -s http://localhost:8080/api/v1/licensing/bootstrap/status
```

### Check current Authority installation record

```bash
curl -s https://authority.eyenet-vision.com/api/v1/installations/tenant-a
```

### Check current Authority owner record

```bash
curl -s https://authority.eyenet-vision.com/api/v1/owners/nick.glezakos@gmail.com
```

## Recommended Development Pattern

Use this cycle during bootstrap work:

1. restore current development state when you need stable normal login behavior
2. switch Authority approved owner email to a non-local test email when you need bootstrap-pending behavior
3. restart Node after each Authority-side change
4. confirm state using `GET /api/v1/licensing/bootstrap/status`

## Helper Script

The repository now includes a helper script for this workflow:

- [scripts/bootstrap-state.sh](/Users/nickgklezakos/Documents/ppl-meta-code/scripts/bootstrap-state.sh)

Supported modes:

1. `scripts/bootstrap-state.sh status`
2. `AUTHORITY_ADMIN_EMAIL=... AUTHORITY_ADMIN_PASSWORD=... scripts/bootstrap-state.sh pending`
3. `AUTHORITY_ADMIN_EMAIL=... AUTHORITY_ADMIN_PASSWORD=... scripts/bootstrap-state.sh restore`

Optional token override:

1. `AUTHORITY_ADMIN_TOKEN=... scripts/bootstrap-state.sh pending`
2. `AUTHORITY_ADMIN_TOKEN=... scripts/bootstrap-state.sh restore`

The helper now defaults `AUTHORITY_BASE_URL` to `https://authority.eyenet-vision.com` and automatically obtains a session token from Authority login credentials when `AUTHORITY_ADMIN_TOKEN` is not provided.

Preferred examples:

```bash
AUTHORITY_ADMIN_EMAIL='<admin-email>' \
AUTHORITY_ADMIN_PASSWORD='<admin-password>' \
scripts/bootstrap-state.sh pending
```

```bash
AUTHORITY_ADMIN_EMAIL='<admin-email>' \
AUTHORITY_ADMIN_PASSWORD='<admin-password>' \
scripts/bootstrap-state.sh restore
```

The VS Code tasks `🧪 Bootstrap State Pending` and `♻️ Bootstrap State Restore` now use the same rule: export either `AUTHORITY_ADMIN_TOKEN` or `AUTHORITY_ADMIN_EMAIL` and `AUTHORITY_ADMIN_PASSWORD` in the terminal before running the task.

Defaults used by the helper:

1. `INSTALLATION_UUID=tenant-a` for the current installation identifier value
2. `APPLICATION_KEY=lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f`
3. `CURRENT_DEV_OWNER_EMAIL=nick.glezakos@gmail.com`
4. `PENDING_OWNER_EMAIL=bootstrap.owner@example.com`

After running `pending` or `restore`, restart Node so startup reconciliation applies the new approved owner mapping locally.

## Summary

The platform is not showing bootstrap UI after logout because the installation is already marked bootstrap-complete at the data-contract level, not just at the session level. The correct way to test bootstrap again is to change the Authority-approved owner mapping to a non-local test owner, then restart Node. When testing is finished, restore the approved owner email to `nick.glezakos@gmail.com` and restart Node to reinstate the current development state.
