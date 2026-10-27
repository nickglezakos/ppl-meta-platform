# Ubuntu installer

Native Ubuntu 24.04 lab/customer install: Docker CE + GHCR images.

## Customer path (wiki zip)

```bash
# From https://wiki.eyenet-vision.com/owners-admins/ downloads
unzip eyenet-ubuntu-<VERSION>.zip
cd eyenet-ubuntu-<VERSION>
ADVERTISE_HOST=<lan-ip> bash install-eyenet-ubuntu.sh
```

Pack a zip for wiki deploy:

```bash
bash deployment/ubuntu/pack-eyenet-ubuntu.sh
# → artifacts/eyenet-ubuntu-<VERSION>.zip (+ .sha256)
```

## Lab path (git checkout)

```bash
ADVERTISE_HOST=<lan-ip> bash deployment/ubuntu/install-eyenet-ubuntu.sh
```

**CI/CD:** [`docs/deployment/platform-release-cicd.md`](../../docs/deployment/platform-release-cicd.md)  
**Release notes:** [`CHANGELOG.md`](../../CHANGELOG.md)  
**Tray:** prefers bundled `tray/eyenet-tray-linux-amd64-*.tar.gz`, else downloads from GitHub Releases `v${VERSION}` (soft-fail if missing). See [`deployment/tray/`](../tray/).

Pin: root `VERSION` / `RELEASE_TAG`.