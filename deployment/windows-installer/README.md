# Windows Installer Bundle

This directory contains the first MVP installer bundle for Windows deployments.

Current published release:

- `2.24.88`
- registry: `ghcr.io/nickglezakos/ppl-meta-platform`
- status: ready to pull pinned images for the Windows installer stack

Release verification:

```bash
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.24.88
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:2.24.88
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:2.24.88
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:2.24.88
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:2.24.88
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:2.24.88
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend:2.24.88
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision-protected:2.24.88
docker manifest inspect ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta-protected:2.24.88
```

If these commands return manifest JSON, the published release is present in GHCR and the Windows installer can pull it.

## Goals

- keep the installer small
- treat Docker Desktop as a prerequisite
- pull exact image tags from a private registry
- avoid local image builds on customer machines
- keep disk usage controlled on machines with limited free space
- avoid mandatory manual env-file editing before first install

## Files

- `docker-compose.windows-installer.yml`: pinned-image compose bundle for Windows deployment
- `.env.windows.template`: environment template used as the base for first-run installer values
- `install-platform.ps1`: PowerShell installer script that creates `.env.windows` from the template when needed, prompts for missing installation values and registry credentials, logs in, pulls images, and starts the stack

## Low-Disk Strategy

This bundle is intentionally designed to avoid building images on the Windows machine.

Use the protected-image build scripts on a build machine first, then push images to the private registry:

- `scripts/build_protected_service_images.sh`
- `scripts/push_protected_service_images.sh`

On the Windows target, only run pulls for exact tags.

## Recommended Flow

1. Build `ppl-meta-vision-protected` and `ppl-meta-vmeta-protected` on a build machine.
2. Push those images and the rest of the platform images to the private registry.
3. Run `install-platform.ps1` on the Windows machine.
4. If `.env.windows` does not exist, the installer creates it from `.env.windows.template`.
5. Enter `INSTALLATION_UUID`, `APPLICATION_KEY`, and `POSTGRES_PASSWORD` when prompted if they are missing.
6. Enter `REGISTRY_USERNAME` and the GHCR token when prompted if they are missing.
7. Run platform health checks after startup.

For the current published release, the generated `.env.windows` should keep `RELEASE_TAG=2.24.88` unless you are intentionally deploying a different pinned release.

For a safer operator flow, leave `REGISTRY_PASSWORD` blank and paste the token only when the installer prompts for it.
