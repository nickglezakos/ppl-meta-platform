# Authority Hetzner Deployment Runbook

## Purpose

This runbook documents the exact files, GitHub secrets, and remote layout expected by the authority release and Hetzner deployment workflows.

## Required GitHub Secrets

The manual deployment workflow expects these repository secrets:

- `HETZNER_HOST`: public SSH hostname or IP of the Hetzner server
- `HETZNER_USER`: remote SSH user used for deployment
- `HETZNER_SSH_KEY`: private SSH key for the deployment user
- `GHCR_USERNAME`: GitHub username used for GitHub Container Registry login
- `GHCR_TOKEN`: GitHub token with package read access for GitHub Container Registry
- `AUTHORITY_ADMIN_EMAIL`: authority admin email used for authenticated post-deploy smoke checks
- `AUTHORITY_ADMIN_PASSWORD`: authority admin password used for authenticated post-deploy smoke checks
- `MAIL_SERVER`: shared platform SMTP server used by authority invitation emails
- `MAIL_PORT`: shared platform SMTP port
- `MAIL_USERNAME`: shared platform SMTP username
- `MAIL_PASSWORD`: shared platform SMTP password
- `MAIL_FROM`: shared platform sender email address
- `MAIL_FROM_NAME`: shared platform sender display name
- `MAIL_STARTTLS`: shared platform SMTP STARTTLS toggle
- `MAIL_SSL_TLS`: shared platform SMTP SSL/TLS toggle
- `USE_CREDENTIALS`: shared platform SMTP authentication toggle
- `AUTHORITY_TEST_APPLICATION_KEY`: optional entitlement/application key used for activation-contract verification
- `AUTHORITY_TEST_OWNER_EMAIL`: optional approved owner email paired with the test application key
- `AUTHORITY_TEST_INSTALLATION_UUID`: optional installation UUID used during activation-contract verification

Current validated production state:

- `AUTHORITY_ADMIN_EMAIL` and `AUTHORITY_ADMIN_PASSWORD` now point at the real production `platform_admin` account, not the bootstrap admin.
- `AUTHORITY_TEST_APPLICATION_KEY`, `AUTHORITY_TEST_OWNER_EMAIL`, and `AUTHORITY_TEST_INSTALLATION_UUID` are configured and have already been validated through a successful `run_activation_check=true` deployment workflow run.

The workflow checker may warn about unknown secret names in the editor. Those warnings do not mean the workflow syntax is invalid.

The deploy workflow performs a remote `docker login ghcr.io` before pulling the authority image, so the Hetzner host does not need pre-seeded registry credentials.

## Required Remote Layout

The workflow assumes the Hetzner host uses this directory structure:

- `/home/deploy/apps/ppl-meta-authority/cicd/compose/docker-compose.yml`
- `/home/deploy/apps/ppl-meta-authority/cicd/env/authority.env`
- `/home/deploy/apps/ppl-meta-authority/cicd/scripts/check_authority_deployment.sh`

## Required Remote Env File

Create the remote env file from [autonomous/ppl-meta-authority/.env.production.example](/Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-authority/.env.production.example).

Suggested command on Hetzner:

```sh
mkdir -p /home/deploy/apps/ppl-meta-authority/cicd/compose /home/deploy/apps/ppl-meta-authority/cicd/env /home/deploy/apps/ppl-meta-authority/cicd/scripts
cp /path/to/authority.env /home/deploy/apps/ppl-meta-authority/cicd/env/authority.env
```

Populate at minimum:

- `AUTHORITY_IMAGE`
- `AUTHORITY_POSTGRES_DB`
- `AUTHORITY_POSTGRES_USER`
- `AUTHORITY_POSTGRES_PASSWORD`
- `AUTHORITY_DATABASE_URL`
- `AUTHORITY_ADMIN_TOKEN`
- `AUTHORITY_BOOTSTRAP_ADMIN_ENABLED=false`
- `AUTHORITY_BASE_URL`

For invitation email delivery, also populate:

- `MAIL_SERVER`
- `MAIL_PORT`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_FROM`
- `MAIL_FROM_NAME`
- `MAIL_STARTTLS`
- `MAIL_SSL_TLS`
- `USE_CREDENTIALS`

The deploy workflow now also syncs `AUTHORITY_BASE_URL`, `AUTHORITY_PUBLIC_BASE_URL`, and the shared `MAIL_*` values from GitHub repository secrets into the remote `authority.env` file on each deployment.

## Required Remote Compose File

Copy [autonomous/ppl-meta-authority/docker-compose.production.yml](/Users/nickgklezakos/Documents/ppl-meta-code/autonomous/ppl-meta-authority/docker-compose.production.yml) to:

- `/home/deploy/apps/ppl-meta-authority/cicd/compose/docker-compose.yml`

This file is image-based and expects `AUTHORITY_IMAGE` to be supplied externally. It is designed for CI/CD deployment and should replace ad hoc build-based compose usage on the server.

## Deployment Flow

1. Publish a versioned authority image to GHCR using the release workflow.
2. Update `AUTHORITY_IMAGE` in `/home/deploy/apps/ppl-meta-authority/cicd/env/authority.env` to the approved image tag or digest.
3. Run the manual Hetzner deployment workflow.
4. The workflow copies the smoke-check script, updates the compose file, starts the authority container, and runs post-deploy checks.

For the first cutover from the legacy installations-only SQLite deployment, run the workflow once with `bootstrap_admin_before_login=true` and set the login smoke-check secrets to the bootstrap admin credentials.

That first-cutover mode has already been used for the current Hetzner authority host. Normal future deployments should use:

- `bootstrap_admin_before_login=false`
- `run_activation_check=true`

## Digest Pinning Recommendation

Prefer image digests in production when available.

Example:

```sh
AUTHORITY_IMAGE=ghcr.io/nickglezakos/ppl-meta-authority@sha256:replace-with-real-digest
```

Using a digest ensures the Hetzner deployment consumes an immutable image instead of a mutable tag.

## Post-Deploy Verification

The smoke-check script validates:

- `/health`
- `/admin`
- optional admin login and `/api/v1/auth/me`
- optional activation-contract check using `application_key + owner_email + installation_uuid`

When `bootstrap_admin_before_login=true`, the smoke-check first calls `POST /api/v1/auth/bootstrap-admin` before attempting login. Use that mode only for the one-time migration deployment.

The current validated steady-state deployment path is:

1. real `platform_admin` login check using `AUTHORITY_ADMIN_EMAIL` and `AUTHORITY_ADMIN_PASSWORD`
2. activation-contract check using `AUTHORITY_TEST_APPLICATION_KEY`, `AUTHORITY_TEST_OWNER_EMAIL`, and `AUTHORITY_TEST_INSTALLATION_UUID`
3. bootstrap disabled on the server with `AUTHORITY_BOOTSTRAP_ADMIN_ENABLED=false`

## Notes

- Bootstrap admin must remain disabled in production.
- The workflow does not create secrets on the server; it assumes the env file already exists.
- If PostgreSQL is externalized later, only the env file should need to change.
- The legacy SQLite-to-PostgreSQL migration for the current Hetzner host has already been completed; future deploys should treat PostgreSQL as the only runtime database.
