# Ubuntu installer

Native Ubuntu 24.04 lab/customer install: Docker CE + GHCR images.

```bash
ADVERTISE_HOST=<lan-ip> bash deployment/ubuntu/install-eyenet-ubuntu.sh
```

**CI/CD:** [`docs/deployment/platform-release-cicd.md`](../../docs/deployment/platform-release-cicd.md)  
**Release notes:** [`CHANGELOG.md`](../../CHANGELOG.md)  
**Tray:** after stack up, downloads `eyenet-tray-linux-amd64-${VERSION}.tar.gz` from GitHub Releases `v${VERSION}` (soft-fail if missing). See [`deployment/tray/`](../tray/).

Pin: root `VERSION` / `RELEASE_TAG` (today `2.25.82`).
