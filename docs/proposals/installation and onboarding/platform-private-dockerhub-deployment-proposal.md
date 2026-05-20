# Platform Private Registry Deployment Proposal

**Date**: May 11, 2026  
**Status**: Draft  
**Scope**: Container image packaging for the full local platform, GitHub Container Registry distribution, Windows installer consumption, and separation of APK and Raspberry Pi deployment channels

---

## Purpose

This document proposes how the deployable parts of the platform should be packaged and distributed.

The goal is to make the main local platform installable on Windows through Docker Desktop and a Windows installer, while keeping mobile and device-specific runtimes on their own delivery paths.

The proposal covers:

- which services should be built as Docker images
- how those images should be published to GitHub Container Registry
- how the Windows installer should consume those images
- which products should **not** be distributed through this container channel

---

## Short Answer

Yes, your approach is broadly correct.

The right packaging split is:

1. the main local platform services are distributed as Docker images through GitHub Container Registry
2. the Windows installer pulls those versioned images and installs the platform on a Windows machine via Docker Desktop
3. Android deliverables remain APK-based
4. the Raspberry Pi edge camera remains a separate device image or dedicated device-specific deployment path

That is the correct high-level direction.

The main corrections are:

- the Windows installer should install a **defined platform image set**, not an open-ended list of random images
- image tags must be version-pinned and released as one tested platform bundle
- the Android frontend should not be treated as part of the Docker platform bundle
- the Raspberry Pi edge camera should not be treated as part of the Windows installer flow
- private-registry authentication and Hetzner owner activation should be treated as related but separate lifecycle steps

---

## Proposed Distribution Split

### A. Main Local Platform Via GitHub Container Registry

These services should be built and published as private Docker images for the Windows-installed local platform:

- `bootcore`
- `cameras`
- `communications`
- `discovery`
- `frontend-web`
- `gateway`
- `media`
- `node`
- `orchestrator`
- `vision`
- `vmeta`

If `code` refers to an actual runtime service that must run locally as part of the deployed stack, then it can also be part of this image set. If it is only the repository name or a development umbrella, then it should **not** be packaged as a runtime image.

### B. Android Deliverables Via APKs

These should remain outside the Docker image deployment model:

- mobile camera Android app
- signage simple player Android app
- Android frontend app

These should be distributed as signed APKs or through the appropriate Android release channel.

### C. Edge Camera Via Separate Raspberry Pi Delivery Path

The edge camera should remain separate from the Windows installer and from the general platform image bundle.

Recommended options:

- Raspberry Pi OS image with the edge camera preconfigured
- separate Pi-focused Docker deployment bundle
- dedicated device provisioning flow

The important point is that it should stay device-specific and not be mixed into the Windows host installer story.

---

## Recommended Service Bundle For Windows Installation

The Windows installer should treat the platform as one tested bundle made of multiple private images.

Recommended MVP platform bundle:

- `ppl-meta-bootcore`
- `ppl-meta-cameras`
- `ppl-meta-communications`
- `ppl-meta-discovery`
- `ppl-meta-frontend-web`
- `ppl-meta-gateway`
- `ppl-meta-media`
- `ppl-meta-node`
- `ppl-meta-orchestrator`
- `ppl-meta-vision`
- `ppl-meta-vmeta`

If needed, define one optional profile for services that are not required in every deployment.

Example deployment profiles:

- `core`: node, gateway, frontend-web, media, orchestrator, vision, vmeta
- `extended`: core plus communications, discovery, cameras, bootcore

This avoids forcing every installation to run an unnecessarily large stack when some roles are optional.

---

## Why GitHub Container Registry Is The Right Channel

GitHub Container Registry is the better current distribution channel for the containerized local platform because it gives:

- centralized image distribution
- version-tagged release control
- simple integration with Docker Desktop on Windows
- direct alignment with the GitHub-hosted repository and release workflow
- easier updates than bundling images inside an installer

This is especially suitable if the Windows installer is only responsible for:

- prerequisite checks
- local configuration
- registry authentication
- image pull
- `docker compose up`
- local health verification

---

## Image Naming And Tagging Strategy

Each service should be published as its own image under one GitHub Container Registry namespace.

Suggested pattern:

- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-bootcore:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-cameras:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-communications:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-discovery:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-frontend-web:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-gateway:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-media:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-node:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-orchestrator:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vision:<platform-version>`
- `ghcr.io/nickglezakos/ppl-meta-platform/ppl-meta-vmeta:<platform-version>`

Recommended rules:

- never deploy using `latest`
- every installer release points to one exact tested version set
- all images for a release should normally share the same platform version tag
- if one service must be hotfixed separately, use an explicit manifest or lock file rather than silently drifting one tag

Example:

- platform release `2026.05.11-rc1`
- installer pulls all service images using that exact release tag

---

## Release Manifest Requirement

The Windows installer should not carry hardcoded image names and tags in scattered logic.

Instead, every tested platform release should produce a release manifest that defines:

- image names
- exact tags
- required services
- optional services
- ports
- health endpoints
- environment/config keys

Suggested manifest contents:

- platform version
- authority URL
- compose template version
- service-to-image mapping
- health check expectations
- optional feature flags

This allows the installer to consume one coherent platform definition rather than guessing what to install.

---

## Relationship To The Hetzner Owner And Licence Lifecycle

The Docker deployment proposal must align with the implemented Hetzner authority lifecycle.

The key separation is:

- GitHub Container Registry delivers the software
- Hetzner authority governs owner approval and licence activation

The Windows installer prepares the machine for the authority lifecycle by writing:

- authority service URL
- application key
- optionally installation UUID
- platform runtime configuration

The Windows installer does **not** grant ownership.

Owner grant still happens later when:

1. the operator has created an entitlement in the authority admin UI
2. the local platform starts successfully
3. the first local user registers
4. Node activates ownership against the authority service

So software deployment and owner activation are separate steps.

---

## Windows Installer Responsibilities

The Windows installer should be responsible for:

1. checking Docker Desktop prerequisites
2. authenticating to the private Docker Hub namespace
3. pulling the exact tested platform image set
4. writing local config and compose assets
5. starting the local stack
6. verifying local platform health
7. optionally verifying authority reachability
8. presenting next-step guidance for first-user onboarding

The installer should not be responsible for:

- assigning the local owner
- creating authority entitlements
- managing APK deployment
- provisioning Raspberry Pi edge devices

---

## Post-Install Operator Guidance

After the installer completes successfully, it should guide the operator through the next lifecycle step.

Recommended post-install guidance:

1. confirm that the authority entitlement exists in `https://authority.eyenet-vision.com/admin`
2. confirm that the local application key matches the entitlement
3. optionally confirm the installation UUID strategy:
   - installer-supplied UUID
   - or Node-generated UUID on first activation
4. open the local frontend
5. register the first local user with the approved owner email

This is the point where owner activation happens.

---

## Recommended Runtime Split By Product Type

### Windows Local Platform

Deploy via Docker Desktop and the Windows installer.

Artifacts:

- private Docker Hub images
- compose assets
- config files
- release manifest

### Android Apps

Deploy via APKs.

Artifacts:

- signed APKs for mobile camera
- signed APKs for signage simple player
- signed APKs for Android frontend

### Raspberry Pi Edge Camera

Deploy via a separate Pi-specific distribution.

Artifacts:

- Pi OS image
- or Pi-specific Docker deployment bundle
- or dedicated flashing/provisioning package

This separation is correct and should remain.

---

## Minimum Corrections To The Proposed Approach

Your proposed approach is correct with these adjustments:

1. treat the Windows-installed platform as a defined release bundle, not just a list of images
2. keep APK-based Android distribution fully separate from the Docker bundle
3. keep Raspberry Pi edge camera delivery fully separate from the Windows installer path
4. ensure the installer writes authority configuration but does not attempt to perform owner activation itself
5. publish only tested, version-pinned images to the private Docker Hub namespace
6. clarify whether `code` is a real deployable runtime service before including it as an image

That is the cleanest and safest MVP packaging model.

---

## Recommended Implementation Shape

### CI/CD Output

For each tested platform release, CI/CD should produce:

1. one private Docker Hub image per deployable service
2. one release manifest describing the full platform bundle
3. one Windows installer configured to consume that bundle
4. APK artifacts for Android deliverables
5. separate device artifact for the Raspberry Pi edge camera

### Installer Input

The Windows installer should consume:

1. release manifest
2. private Docker Hub credentials or approved pull mechanism
3. local authority configuration values
4. compose template assets

### Installer Output

The Windows installer should leave the machine with:

1. pulled platform images
2. written local configuration
3. running local stack
4. verified local health state
5. clear first-user onboarding instructions

---

## Open Decisions

The following decisions still need to be made explicitly:

1. whether all listed services belong in every Windows installation or whether profiles are needed
2. whether `bootcore` and `cameras` are required in every local deployment
3. whether `code` is a real deployable runtime image or should be excluded
4. whether private Docker Hub authentication will use operator credentials, a shared org credential, or a later authority-issued token
5. whether the installer should write an explicit installation UUID or let Node generate it on first activation

---

## Recommended Conclusion

Yes, the overall approach is correct.

The main local platform should be delivered as a set of GitHub Container Registry images and installed on Windows through Docker Desktop plus the Windows installer.

Android products should remain APK-based, and the Raspberry Pi edge camera should remain on a separate device-specific deployment path.

The important correction is that the Windows installer should install a tested, version-pinned platform bundle and prepare the node for the Hetzner authority lifecycle, while the actual owner grant still happens later during first-user onboarding.
