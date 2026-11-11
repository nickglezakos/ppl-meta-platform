# Authority Updates

This document captures the exact update flow used on 2026-06-08 to deploy Authority changes safely from this repository to the live Hetzner-hosted service.

Use this as the default guide for future Authority updates.

## Scope

This guide covers:

- isolating Authority-only changes from a dirty worktree
- validating the changed Authority files before push
- committing and pushing the Authority slice to GitHub
- triggering the GitHub Actions release workflow
- triggering the GitHub Actions Hetzner deployment workflow
- verifying the public Authority service after deployment

This guide does not cover:

- local-only Authority development
- database backfills beyond what the application performs on startup
- manual server-side SSH deployment outside the GitHub workflow path

## Repository Workflows

The live Authority deployment path is already implemented in this repository:

- `.github/workflows/authority-ci.yml`
- `.github/workflows/authority-release.yml`
- `.github/workflows/authority-deploy-hetzner.yml`

Behavior:

- CI validates the Authority service on pull requests and pushes affecting the Authority code.
- Release builds and pushes the Docker image to `ghcr.io/nickglezakos/ppl-meta-authority`.
- Deploy pulls that image on Hetzner, updates the remote env file, restarts the service, and runs public deployment checks.

## Preconditions

Before starting an update, confirm:

- you are in the repository root
- the local git remote points to `origin`
- GitHub CLI is authenticated with `repo` and `workflow` scope
- the Authority change set is understood and limited to the files intended for deployment
- unrelated local changes are not included in the commit

Useful checks:

```bash
git remote -v
git branch --show-current
gh auth status
git status --short
```

## Standard Update Sequence

### 1. Inspect the Authority-only slice

When the worktree is dirty, inspect only the Authority paths first:

```bash
git status --short autonomous/ppl-meta-authority VERSION .github/workflows
git diff --stat -- autonomous/ppl-meta-authority
```

On 2026-06-08, the live deployment contained only these Authority files:

- `autonomous/ppl-meta-authority/src/api/installations.py`
- `autonomous/ppl-meta-authority/src/core/storage.py`
- `autonomous/ppl-meta-authority/src/ui/assets/admin.js`
- `autonomous/ppl-meta-authority/src/validate_authority_audit_api.py`
- `autonomous/ppl-meta-authority/src/validate_authority_auth_dashboard.py`
- `autonomous/ppl-meta-authority/src/validate_authority_invitations_assignments.py`
- `autonomous/ppl-meta-authority/src/validate_authority_lifecycle.py`

### 2. Run focused validation before commit

Run narrow checks only on the touched Authority files.

Example used successfully:

```bash
source .venv/bin/activate
python -m py_compile \
  autonomous/ppl-meta-authority/src/api/installations.py \
  autonomous/ppl-meta-authority/src/core/storage.py \
  autonomous/ppl-meta-authority/src/validate_authority_audit_api.py \
  autonomous/ppl-meta-authority/src/validate_authority_auth_dashboard.py \
  autonomous/ppl-meta-authority/src/validate_authority_invitations_assignments.py \
  autonomous/ppl-meta-authority/src/validate_authority_lifecycle.py
```

Notes:

- Do not feed JavaScript assets to `py_compile`.
- If the changed set includes frontend assets such as `admin.js`, validate those with editor diagnostics or the relevant JS tooling instead.

### 3. Stage only the Authority files

Do not stage the whole worktree if unrelated changes are present.

Example:

```bash
git add \
  autonomous/ppl-meta-authority/src/api/installations.py \
  autonomous/ppl-meta-authority/src/core/storage.py \
  autonomous/ppl-meta-authority/src/ui/assets/admin.js \
  autonomous/ppl-meta-authority/src/validate_authority_audit_api.py \
  autonomous/ppl-meta-authority/src/validate_authority_auth_dashboard.py \
  autonomous/ppl-meta-authority/src/validate_authority_invitations_assignments.py \
  autonomous/ppl-meta-authority/src/validate_authority_lifecycle.py
```

### 4. Commit the isolated Authority change

Example used on 2026-06-08:

```bash
git commit -m "authority: enforce machine licence keys"
```

Resulting commit:

- `d7b06fc0`

### 5. Push to GitHub

Push the commit before attempting release or deployment.

```bash
git push origin main
```

Important:

- GitHub Actions can only build and deploy code that exists on GitHub.
- Local unpushed changes cannot be released through the existing workflow path.

### 6. Trigger the Authority release workflow

The release workflow publishes the Docker image to GHCR.

Example used on 2026-06-08:

```bash
AUTHORITY_VERSION=20260608-machine-key
gh workflow run authority-release.yml --ref main -f authority_version="$AUTHORITY_VERSION"
gh run list --workflow authority-release.yml --limit 1 --json databaseId,displayTitle,headSha,status,conclusion,url
```

Release run used:

- workflow: `authority-release.yml`
- run id: `27128591748`
- status: `success`
- head SHA: `d7b06fc0439390ab3e89f34a2583f8f68d0b3464`
- published image tag: `ghcr.io/nickglezakos/ppl-meta-authority:authority-20260608-machine-key`

Optional wait command:

```bash
gh run watch 27128591748 --exit-status
```

### 7. Trigger the Hetzner deployment workflow

After the image is published, trigger deployment using the same Authority version.

Example used on 2026-06-08:

```bash
gh workflow run authority-deploy-hetzner.yml \
  --ref main \
  -f authority_version=20260608-machine-key \
  -f authority_base_url=https://authority.eyenet-vision.com \
  -f run_activation_check=false \
  -f bootstrap_admin_before_login=false

gh run list --workflow authority-deploy-hetzner.yml --limit 1 --json databaseId,displayTitle,headSha,status,conclusion,url
```

Deployment run used:

- workflow: `authority-deploy-hetzner.yml`
- run id: `27128654567`
- status: `success`
- head SHA: `d7b06fc0439390ab3e89f34a2583f8f68d0b3464`

Optional wait command:

```bash
gh run watch 27128654567 --exit-status
```

### 8. Verify the public service

Do not stop at workflow success. Verify the live public endpoints directly.

Health check:

```bash
curl -sS -D - https://authority.eyenet-vision.com/health -o /tmp/authority-health.out
cat /tmp/authority-health.out
```

Application-key lookup check:

```bash
curl -sS -D - https://authority.eyenet-vision.com/api/v1/application-keys/lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f -o /tmp/authority-key.out
cat /tmp/authority-key.out
```

Expected result:

- `200` from `/health`
- `200` from `/api/v1/application-keys/{application_key}` if the new contract is live and the specific key exists in Authority data

## What Changed In The 2026-06-08 Update

This update deployed the Authority side of the machine-shaped licence key contract.

Key changes:

- `application_key` is now constrained to machine-shaped values in the form `lic_<32 hex>`
- `licence_name` is stored separately as the human-readable label
- the API now exposes installation lookup by application key
- admin and validation paths were updated to use the new contract

## Post-Deploy Data Check

Code deployment and data migration are separate concerns.

After the 2026-06-08 deployment, the public lookup route was live, but the queried key still resolved to the seeded demo record rather than the intended local development installation.

Observed public response:

- `installation_uuid: test-installation`
- `application_key: lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f`
- `licence_name: MVP Demo Licence`
- `approved_owner_email: owner@example.com`

This means:

- the deployed code was correct
- the application-key route was live
- the live Authority data still needed an admin-level installation update

## Live Record Migration Pattern

Once a valid Authority admin bearer token is available, the live installation record can be updated with the admin API.

### Scriptable token acquisition

Authority login is scriptable. The service exposes `POST /api/v1/auth/login`, which returns a JSON payload containing `session_token`, and protected endpoints accept it as `Authorization: Bearer <session_token>`.

Direct login call:

```bash
curl -X POST 'https://authority.eyenet-vision.com/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{
    "email": "<admin-email>",
    "password": "<admin-password>"
  }'
```

Expected response shape:

```json
{
  "session_token": "<bearer-token>",
  "expires_at": "<timestamp>",
  "user": {
    "user_uuid": "<uuid>",
    "email": "<admin-email>",
    "display_name": "<name>",
    "role_name": "platform_admin",
    "status": "active"
  }
}
```

Verification call:

```bash
curl -X GET 'https://authority.eyenet-vision.com/api/v1/auth/me' \
  -H "Authorization: Bearer $AUTHORITY_ADMIN_TOKEN"
```

Reusable helper:

```bash
AUTHORITY_BASE_URL=https://authority.eyenet-vision.com \
AUTHORITY_ADMIN_EMAIL='<admin-email>' \
AUTHORITY_ADMIN_PASSWORD='<admin-password>' \
sh autonomous/ppl-meta-authority/scripts/get_authority_session_token.sh
```

Behavior:

- optionally calls `POST /api/v1/auth/bootstrap-admin` first when `AUTHORITY_BOOTSTRAP_ADMIN_BEFORE_LOGIN=true`
- calls `POST /api/v1/auth/login`
- extracts `session_token`
- verifies the token with `GET /api/v1/auth/me` by default
- prints the session token to stdout on success

Example for shell reuse:

```bash
AUTHORITY_ADMIN_TOKEN="$({
  AUTHORITY_BASE_URL=https://authority.eyenet-vision.com \
  AUTHORITY_ADMIN_EMAIL='<admin-email>' \
  AUTHORITY_ADMIN_PASSWORD='<admin-password>' \
  sh autonomous/ppl-meta-authority/scripts/get_authority_session_token.sh
})"
```

Example payload used for the target development installation:

```bash
curl -X POST 'https://authority.eyenet-vision.com/api/v1/admin/installations' \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $AUTHORITY_ADMIN_TOKEN" \
  -d '{
    "installation_uuid": "tenant-a",
    "application_key": "lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f",
    "licence_name": "Tenant A Development Licence",
    "approved_owner_email": "nick.glezakos@gmail.com",
    "owner_enabled": true,
    "licence_status": "active",
    "offline_grace_days": 14,
    "tenant_name": "Tenant A",
    "notes": "Migrated current development installation to machine-shaped licence key"
  }'
```

Then verify:

```bash
curl -s 'https://authority.eyenet-vision.com/api/v1/application-keys/lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f'
```

## Operational Rules

- Always isolate the Authority slice before commit when the worktree contains unrelated changes.
- Always validate before push.
- Always deploy the exact image version that was just released.
- Always verify the public endpoints after deployment.
- Treat code deployment and data migration as separate steps.
- Do not assume a successful GitHub Actions deploy means the correct Authority data is already in place.

## Recommended Future Checklist

```bash
git status --short autonomous/ppl-meta-authority VERSION .github/workflows
git diff --stat -- autonomous/ppl-meta-authority
source .venv/bin/activate
python -m py_compile <changed-authority-python-files>
git add <authority-files-only>
git commit -m "authority: <short change summary>"
git push origin main
gh workflow run authority-release.yml --ref main -f authority_version="<version-tag>"
gh workflow run authority-deploy-hetzner.yml --ref main -f authority_version="<version-tag>" -f authority_base_url=https://authority.eyenet-vision.com -f run_activation_check=false -f bootstrap_admin_before_login=false
curl -sS https://authority.eyenet-vision.com/health
curl -sS https://authority.eyenet-vision.com/api/v1/application-keys/<application_key>
```
