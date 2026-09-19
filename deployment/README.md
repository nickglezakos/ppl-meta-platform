# Deployment scripts (executable)

This tree holds **installers, compose, schema pack, and helpers**.

**CI/CD documentation (single source of truth):**  
[`docs/deployment/platform-release-cicd.md`](../docs/deployment/platform-release-cicd.md)

Index of deployment docs: [`docs/deployment/README.md`](../docs/deployment/README.md)

| Path | Role |
|---|---|
| `windows-installer/` | Windows/WSL installer + **shared** compose, schema pack, discovery reregister |
| `ubuntu/` | Native Ubuntu 24.04 lab installer |
| `mac-lima/` | Mac Lima helpers (reregister wraps `windows-installer/`) |

Pin check: `./scripts/check_installer_pins.sh`  
**Stage 1:** commit + push to GitHub (frequent)  
**Stage 2:** on Windows/Linux host — `./scripts/build_windows_installer_images.sh` then `./scripts/push_protected_service_images.sh`  
GHCR verify: `./scripts/verify_platform_release.sh`
