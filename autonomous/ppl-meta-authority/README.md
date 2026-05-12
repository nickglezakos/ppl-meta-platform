# PPL Meta Authority

Minimal Hetzner-hosted authority service for the local-first installation lifecycle.

## Current MVP Scope

- health endpoint
- persistent SQLite-backed installation registry
- public installation lookup and owner status endpoints
- admin installation list, create, update, and delete endpoints
- owner status lookup backed by stored ownership records
- Dockerized local run path

## Local Run

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --app-dir src
```

## Docker Run

```bash
docker compose up --build
```

## Persistence

The service stores its MVP ownership registry in SQLite.

- default database path: `data/authority.db`
- override with: `AUTHORITY_DATABASE_PATH=/custom/path/authority.db`

Current stored fields match the simplified MVP ownership model:

- `installation_uuid`
- `application_key`
- `approved_owner_email`
- `owner_enabled`
- `licence_status`
- `offline_grace_days`
- optional `tenant_name`
- optional `notes`

## Admin Authentication

Administrative mutation endpoints require a bearer token.

- environment variable: `AUTHORITY_ADMIN_TOKEN`
- header format: `Authorization: Bearer <token>`

Admin endpoints:

- `GET /api/v1/admin/installations`
- `POST /api/v1/admin/installations`
- `GET /api/v1/admin/installations/{installation_uuid}`
- `DELETE /api/v1/admin/installations/{installation_uuid}`

## Admin UI

A minimal private admin UI is available at:

- `GET /admin`

The page expects you to paste the bearer token and then uses the protected admin API for listing and upserting installation records.
