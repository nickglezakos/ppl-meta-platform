# Windows Installer And Private Registry Deployment Proposal

**Date**: May 11, 2026  
**Status**: Published for release 2.24.88  
**Scope**: Windows installer lifecycle, Docker Desktop prerequisite handling, private registry image pulls, installation identity provisioning, and initial platform health validation  
**Depends On**: [docs/proposals/installation and onboarding/hetzner-minimal-owner-licence-lifecycle.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/installation%20and%20onboarding/hetzner-minimal-owner-licence-lifecycle.md)

## Release Status

Release `2.24.88` has now been built and published to GitHub Container Registry for the Windows installer stack.

Published images for this release are:

- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:2.24.88`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:2.24.88`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:2.24.88`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:2.24.88`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:2.24.88`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:2.24.88`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend:2.24.88`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision-protected:2.24.88`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta-protected:2.24.88`

This means the current Windows installer bundle is ready to pull exact pinned images for release `2.24.88` without any local image builds on the Windows target machine.

### Published Release Verification

Before a Windows deployment, operators can verify that the pinned release is present in GitHub Container Registry with manifest inspection.

Example checks:

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

If these commands return manifest JSON, the release is published and ready for installer pulls.

---

## Lifecycle Alignment Status

This document must now align with the implemented Hetzner authority MVP.

The following authority-side assumptions are already true:

- the online authority service exists and is reachable at `https://authority.eyenet-vision.com`
- operators can create entitlements in the private admin UI
- local first-user onboarding uses `installation_uuid`, `application_key`, and `owner_email`
- local Node persists effective authority application key and installation UUID in app settings
- authority activation binds a real installation UUID to the entitlement on first approved use

The following installer-related ideas are still future work and should be treated as optional extensions, not current dependencies:

- the authority service issuing short-lived private-registry pull credentials
- a registry-token exchange tied directly to installation activation
- customer self-service provisioning through the authority service

---

## Purpose

This proposal describes a practical MVP installer model for deploying the platform on Windows.

The installer should not package the entire runtimeflutter  itself. Instead, it should:

1. verify that Docker Desktop is installed and usable
2. collect or prompt for installation identity and application-key data
3. authenticate to a private image registry
4. pull versioned container images
5. write local configuration
6. start the local stack and verify health

This keeps the installer small, keeps image distribution centralized, and aligns the local installation with the implemented Hetzner-based owner and licence model.

---

## MVP Recommendation

The Windows installer should treat Docker Desktop as a **prerequisite**, not as something the platform silently manages end-to-end.

That means the installer should:

- detect whether Docker Desktop is installed
- detect whether Docker is actually running and usable
- stop and guide the user if Docker Desktop is missing or unhealthy
- continue only when Docker is ready

This is the safest MVP because Docker Desktop and Windows virtualization setup are already complex enough on their own.

---

## High-Level Installer Flow

The recommended Windows installer flow is:

1. launch installer
2. check Windows prerequisites
3. check Docker Desktop presence
4. check Docker engine availability
5. create the local env file from template if needed
6. collect or prompt for local authority configuration
7. collect or prompt for registry credentials if needed
8. authenticate for private image pull
9. pull exact tagged images
10. write local config and compose assets
11. start containers
12. run health checks
13. optionally validate authority reachability
14. present success or recovery guidance

---

## Why Docker Desktop Should Be A Prerequisite

For the MVP, Docker Desktop is the simplest deployment substrate on Windows because it already solves:

- Linux container runtime on Windows
- WSL2 integration
- local image management
- volume and network handling
- service startup for containerized apps

The installer should not attempt to replace Docker Desktop.

Instead, it should depend on it and verify it.

---

## Windows Prerequisite Checks

Before doing anything else, the installer should verify the minimum local environment.

Suggested checks:

1. supported Windows version
2. sufficient disk space
3. Docker Desktop installed
4. Docker engine responsive
5. WSL2 available if required by the Docker setup
6. required virtualization features enabled if needed
7. required ports not already taken by conflicting services

### Practical Disk Rule For This MVP

Because the current operator environment may only have about 25 GB of free disk, the installer and packaging process should assume that local disk is constrained.

That means:

- do not build platform images on the Windows target machine
- build and push images on a separate build machine or CI runner
- pull only exact release-tagged images during Windows installation
- keep the Windows installer bundle limited to compose, env, and startup assets
- fail early if the target machine does not have the minimum free space needed for image pulls and writable volumes

For the first pass, a practical minimum free-space guardrail is:

- 12 GB free before pull and startup for the Windows target machine

This does not guarantee success for every release, but it is a safer first threshold than assuming the installer can consume the full remaining disk.

### Failure Strategy

The installer should fail clearly and early.

It should not proceed into partial deployment if Docker is unavailable.

---

## Docker Desktop Check

### Minimal MVP Behavior

The installer should perform two separate checks.

#### 1. Installed?

Examples of acceptable checks:

- detect known Docker Desktop install path
- detect Docker CLI availability
- detect Docker Desktop registry entry or executable

#### 2. Running And Usable?

Examples:

- run `docker version`
- run `docker info`
- optionally run a minimal container check if needed

If Docker Desktop is missing, the installer should:

- stop
- explain that Docker Desktop is required
- offer a link or guided step to install it

If Docker Desktop is installed but not running, the installer should:

- prompt the user to launch Docker Desktop
- wait or allow retry

---

## Private Registry Strategy

Yes, the installer should pull the platform images from a private registry.

That is the right MVP distribution model.

The registry could be:

- GitHub Container Registry
- self-hosted registry later if needed

For the current platform direction, GitHub Container Registry should be treated as the default and Docker Hub should not be treated as the primary target.

The important thing is that the images are:

- private
- versioned
- pinned by exact tag

The installer should not rely on `latest`.

---

## Recommended Image Pull Model

The installer should authenticate before pulling images.

For the current MVP bundle, the Windows installer may prompt the operator at runtime for required install values and registry credentials when they are not already present in the local env file. This keeps the default installer bundle free of hardcoded secrets while still allowing a simple GHCR pull workflow.

There are three plausible options:

### Option 1. Shared Static Registry Credentials

This is the simplest technically, but weakest operationally.

Use only if absolutely necessary for a very early prototype.

### Option 2. Operator Enters Registry Credentials

Better than hardcoding credentials, but still not ideal for scale.

This is the currently implemented MVP behavior for the Windows bundle:

- the installer creates `.env.windows` from the template if it does not already exist
- the operator can leave required values unset and enter them when prompted
- the operator can provide `REGISTRY_USERNAME` and `REGISTRY_PASSWORD` in `.env.windows`
- or leave them unset and enter them when prompted by `install-platform.ps1`
- for GitHub Container Registry, the password value is a GitHub personal access token with package access

### Option 3. Installer Receives Pull Authorization Via Hetzner Service

This is the preferred future direction, but it is not part of the current implemented Hetzner MVP.

The installer validates:

- installation UUID
- application key

Then the Hetzner authority returns either:

- short-lived registry credentials
- a pull token
- or a signed instruction set for which images and versions are allowed

This is the cleanest later path because it ties deployment to installation and licence state, but the current authority service does not yet provide this registry-authorization contract.

---

## Installation Identity Provisioning

The installer should collect or generate the core authority values for the local installation.

Suggested values:

- `installation_uuid`
- `application_key`
- Hetzner service URL
- target image version set

The installer should store these in the local config that the containers and local Node service will consume.

This is also the point where the local installation becomes ready for the implemented first-user authority lifecycle.

### Current Practical Rule

The installer does not need to create the entitlement itself.

The current practical model is:

- operator creates or updates entitlement in the authority admin UI
- installer writes the local `application_key`
- installer may write the local `installation_uuid`, or allow Node to generate one if the deployment model prefers first activation binding
- first local user onboarding performs the actual authority activation

---

## Local Files The Installer Should Write

At minimum, the installer should write:

1. environment/config file
2. docker compose file or generated compose override
3. local data directory structure
4. installation identity record
5. registry or image-version metadata if needed

Suggested content includes:

- installation UUID
- application key
- service ports
- image tags
- local storage paths
- Hetzner authority URL

If the installer writes no explicit installation UUID, the deployment must rely on Node generating the local installation UUID and binding it during first-user activation.

---

## Starting The Stack

Once prerequisites and image pulls succeed, the installer should:

1. create required directories
2. write config
3. run `docker compose pull` if needed
4. run `docker compose up -d`
5. wait for startup
6. run platform health checks

The installer should not report success until the health checks pass.

---

## Post-Install Health Validation

The installer should verify that the core stack is actually usable.

Minimal validation should include:

1. Node service reachable
2. Gateway reachable
3. frontend reachable if applicable
4. required backend containers healthy
5. local config written correctly

Optional but recommended:

1. successful contact with the Hetzner licensing authority
2. confirmation that the configured authority URL is the intended environment

---

## Suggested Recovery Paths

If installation fails, the installer should give a clear next action.

Examples:

### Docker Missing

- show Docker Desktop requirement
- provide install instructions
- allow retry after installation

### Docker Not Running

- prompt user to open Docker Desktop
- allow retry

### Registry Authentication Failed

- indicate whether the issue is credential-related, network-related, or still using a future unsupported authority-token flow
- allow retry

### Image Pull Failed

- show which image and tag failed
- suggest registry/network check

### Services Failed Health Check

- show which service failed
- point to logs
- allow retry or rollback guidance

---

## Minimum Security Expectations

For the MVP, the installer should still follow a few hard rules.

1. no hardcoded shared secrets in plain installer scripts if avoidable
2. use HTTPS for any Hetzner provisioning or token retrieval
3. pull only version-pinned images
4. do not expose a public registry token in long-lived local config unless necessary
5. tie installation identity to application-key validation where possible
6. do not assume the installer itself grants owner rights; owner grant still occurs during first-user onboarding

---

## Recommended MVP Architecture

The clean MVP architecture is:

### Windows Installer

- handles local prerequisite checks
- provisions config
- triggers image pulls
- starts the local platform

### Docker Desktop

- runs the platform containers locally

### Private Registry

- serves the versioned private images

### Hetzner Licensing Authority

- stores entitlement records
- validates application key and owner eligibility during later onboarding
- binds installation UUID during first approved activation
- may later return pull authorization or installer configuration

---

## What To Avoid In MVP

The installer should avoid these traps in the first version.

1. bundling all images into a giant installer
2. relying on floating `latest` tags
3. silently attempting to fix Docker Desktop installation in too many ways
4. declaring success before services are healthy
5. mixing local installer logic with the Hetzner service implementation itself
6. assuming registry authorization and owner activation are the same step

---

## Minimal Recommended Sequence

The best short-form MVP sequence is:

1. user launches Windows installer
2. installer checks Docker Desktop
3. installer validates Docker engine readiness
4. installer collects or receives installation UUID and application key
5. installer writes the Hetzner authority URL and local authority config
6. installer authenticates for private image pull
7. installer pulls exact tagged images
8. installer writes config
9. installer starts stack
10. installer runs health checks
11. installer optionally verifies authority reachability
12. installer reports success

After installer success, the owner lifecycle continues separately:

1. operator ensures the entitlement exists in the authority admin UI
2. first local user registers on the node
3. Node activates ownership against the authority service
4. approved first user receives local `owner`, `admin`, and `user` roles

---

## Recommended Conclusion

Yes, the platform should use a Windows installer that first checks for Docker Desktop and then pulls private images from a private registry.

But the installer should treat Docker Desktop as a prerequisite, not as an invisible subsystem it tries to fully own.

That gives the cleanest MVP:

- simple Windows setup
- centralized private image distribution
- clean alignment with the implemented Hetzner-based owner and licence lifecycle
- repeatable, versioned deployments without embedding the whole runtime into the installer itself

The key clarification is that the installer prepares the local authority configuration, but the actual owner grant still happens later during first-user onboarding against the Hetzner authority service.

For constrained-disk environments, the packaging rule should also be explicit:

- protected images such as `ppl-meta-vision-protected` and `ppl-meta-vmeta-protected` should be built on a separate build machine or CI runner
- the Windows target should only pull pinned images from the private registry and should not perform local image compilation
