# PPL Meta Authority

Authority service for the installation lifecycle control plane, local-first admin onboarding, and role-based dashboards.

## Current Scope

- installation entitlement registry and activation flow
- installation health and update event tracking
- session-based authentication for authority users
- bootstrap-admin flow for first-run local setup
- invitation and assignment flows for distributors, resellers, and owners
- role-aware dashboard APIs for admin, distributor, reseller, and owner users
- file-backed admin shell at `/admin`

## Local Run

The local manual test target runs on port `8010`.

### Preferred VS Code Tasks

Use the tasks in [.vscode/tasks.json](../../.vscode/tasks.json):

- `🔐 Start Authority Service (Local Python)`
- `🔐 Start Authority Service (Local Bootstrap Admin)`
- `🏥 Authority PostgreSQL Health Check (Local macOS)`
- `🛑 Stop Authority PostgreSQL (Local macOS)`
- `🛑 Stop Authority Service (Local Python)`
- `🏥 Authority Service Health Check (Local)`
- `🧪 Validate Authority Auth And Dashboard`
- `🧪 Validate Authority Invitations And Assignments`
- `🧪 Validate Authority Bootstrap Gate`
- `🧪 Validate Authority Reseller Scope`
- `🧪 Validate Authority Distributor Scope`
- `🧪 Validate Authority Admin UI`
- `python validate_authority_admin_e2e_workflow.py`
- `python validate_authority_invitation_email_delivery.py`

The bootstrap variant exists for first-time local admin setup only. It enables the bootstrap endpoint so you can create the initial platform admin through the UI.

The authority start tasks now run the native local PostgreSQL task first, and the authority stop task shuts PostgreSQL down afterward. That keeps the normal authority workflow service-first in both directions. The standalone PostgreSQL tasks remain available for manual checks and maintenance.

### Native PostgreSQL Setup

The intended local authority workflow is:

1. Start `🔐 Start Authority Service (Local Python)` or `🔐 Start Authority Service (Local Bootstrap Admin)`.
2. Run `🏥 Authority PostgreSQL Health Check (Local macOS)` if you want to verify the database separately.

If PostgreSQL is not installed yet, install it with Homebrew first, for example:

```bash
brew install postgresql@16
```

### Direct Command

```bash
cd autonomous/ppl-meta-authority
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd src
AUTHORITY_DATABASE_URL=postgresql://authority_user:authority_password@localhost:5432/authority_db python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

For first-time admin bootstrap, add the bootstrap gate only for that run:

```bash
AUTHORITY_DATABASE_URL=postgresql://authority_user:authority_password@localhost:5432/authority_db AUTHORITY_BOOTSTRAP_ADMIN_ENABLED=true python3.11 -m uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

## Manual URLs

- health: `http://localhost:8010/health`
- admin shell: `http://localhost:8010/admin`

## Persistence

The service now runs on PostgreSQL only.

- required runtime setting: `AUTHORITY_DATABASE_URL=postgresql://user:password@host:5432/database`
- local direct-run database host: `localhost`

The authority service no longer falls back to SQLite.

### SQLite Migration

Use the one-time migration script before removing the old SQLite database file:

```bash
cd autonomous/ppl-meta-authority/src
PYTHONPATH=. python3.11 migrate_sqlite_to_postgres.py \
   --sqlite-path ../data/authority-local.db \
   --postgres-url postgresql://authority_user:authority_password@localhost:5432/authority_db
```

The script initializes the PostgreSQL schema, truncates the target tables by default, and copies authority data table-by-table from SQLite.

### Optional Docker Path

Docker is no longer the default local development path for authority. It remains optional if you later want a containerized PostgreSQL or deployment-style environment.

Current persisted authority data includes:

- entitlements and activated installations
- installation state reports
- update events
- authority users
- authority sessions
- invitations
- explicit installation assignments

## Invitation Email Delivery

Authority can send invitation emails over SMTP when mail settings are provided.

Required environment settings:

- `AUTHORITY_BASE_URL` or `AUTHORITY_PUBLIC_BASE_URL`
- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_FROM`

Optional environment settings:

- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_FROM_NAME`
- `MAIL_STARTTLS`
- `MAIL_SSL_TLS`
- `USE_CREDENTIALS`

When these settings are present, admin, distributor, and reseller invitation actions send an email that includes:

- an invitation acceptance link to `/admin?view=session&invitation_token=...`
- the raw invitation token as a fallback

If mail settings are not configured, authority still creates invitation records and tokens, but email delivery is skipped.

## Authentication Model

The current implementation uses session-based authority authentication.

- login endpoint: `POST /api/v1/auth/login`
- current-session endpoint: `GET /api/v1/auth/me`
- logout endpoint: `POST /api/v1/auth/logout`
- admin bootstrap endpoint: `POST /api/v1/auth/bootstrap-admin`

The bootstrap endpoint is disabled by default and only works when `AUTHORITY_BOOTSTRAP_ADMIN_ENABLED=true` is set for the running server.

## First-Time Platform Admin Process

Use this flow before any Hetzner deployment work.

1. Start `🔐 Start Authority Service (Local Bootstrap Admin)` from VS Code.
2. Open `http://localhost:8010/health` and confirm the service responds.
3. Open `http://localhost:8010/admin`.
4. In the session card, trigger the bootstrap-admin action, or run `🔑 Bootstrap Authority Admin (Local)`.
5. Log in with the bootstrap credentials:
   - email: `admin@authority.local`
   - password: `change-this-admin-password`
6. Verify the admin dashboard loads and the console filters show data when records exist.
7. Create the first real authority users for your environment.
8. Stop the bootstrap-enabled task.
9. Restart the service with `🔐 Start Authority Service (Local Python)` so bootstrap is no longer available.
10. Continue testing with normal session login only.

If the helper task returns `Bootstrap admin flow is disabled`, the wrong service variant is running. Stop the authority service and restart `🔐 Start Authority Service (Local Bootstrap Admin)`.

The bootstrap credentials are intentionally transitional. After first login, create the real operational admin path you want to keep using and stop relying on the bootstrap gate.

## Suggested Manual QA Before Hetzner

1. Bootstrap the initial admin user locally.
2. Create at least one distributor user, one reseller invitation, and one owner invitation.
3. Accept the invitations through the UI.
4. Create or assign an entitlement to the invited owner.
5. Verify owner installations and owner summary views.
6. Verify reseller summary visibility is limited to reseller-scoped records.
7. Verify distributor summary visibility is limited to distributor-scoped resellers, owners, and installations.
8. Exercise the console filters for entitlements, invitations, assignments, updates, and health.
9. Run the authority validation tasks before treating the local flow as deployment-ready.

## Admin Shell

The authority shell is available at `GET /admin`.

It now supports:

- login and logout with authority sessions
- bootstrap-admin trigger when enabled
- invitation acceptance
- role-aware admin, distributor, reseller, and owner views
- dashboard summaries with recent activity lanes
- distributor-scoped reseller and owner directory views
- distributor-scoped entitlement assignment to owner users
- hierarchy-aware console rows for distributor, reseller, and owner scopes
- filtered data console views for entitlements, invitations, assignments, updates, and health

## Hierarchy

The current authority onboarding chain is:

1. platform admin can invite distributors, resellers, owners, and support users
2. distributor can invite reseller users within a distributor scope
3. reseller can invite owner users within a reseller scope

When a reseller is invited by a distributor, both `distributor_uuid` and `reseller_uuid` are carried into the accepted account. When an owner is invited by that reseller, the owner inherits the same distributor and reseller scopes.

Distributor management endpoints now include:

- `POST /api/v1/distributor/invitations`
- `GET /api/v1/distributor/resellers`
- `GET /api/v1/distributor/owners`
- `POST /api/v1/distributor/installation-assignments`

For CI-safe end-to-end coverage, `validate_authority_admin_e2e_workflow.py` exercises the admin-to-distributor-to-reseller-to-owner onboarding chain, distributor user listings, and distributor entitlement assignment without needing a live browser runtime.

For CI-safe invitation mail coverage, `validate_authority_invitation_email_delivery.py` stubs the SMTP transport and verifies that authority marks invitation email delivery as attempted and delivered, persists that result, and includes the invitation acceptance link in the outgoing message.

## Deployment Note

This session's implementation and validation have been local. No Hetzner deployment changes have been applied yet.
