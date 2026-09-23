# Tray publish checklist (manual today)

Canonical wording: [`platform-release-cicd.md`](./platform-release-cicd.md) (*Tray publish (part of Stage 1)*).

**GitHub Actions for tray are not used today.** Build on Windows + Ubuntu labs, then upload with `gh release`. The workflow `.github/workflows/tray-release.yml` is a future draft only.

Use this after Stage 1 has landed `deployment/tray/` and installer hooks on `main`.

Current pin example: **`2.25.83`** (always read root `VERSION`).

## Preferred: GitHub Actions

```bash
gh workflow run tray-release.yml -f version="$(tr -d '[:space:]' < VERSION)"
# or after tagging: git tag "v${VERSION}" && git push origin "v${VERSION}"
```

Confirm assets on the GitHub **Releases** page for `v${VERSION}`.

Manual lab builds (below) remain valid when Actions is unavailable.

## 1. Confirm Stage 1 is on GitHub

```bash
git fetch origin
git checkout main
git pull --ff-only
./scripts/check_installer_pins.sh
test -f deployment/tray/go.mod
VERSION="$(tr -d '[:space:]' < VERSION)"
```

## 2. Build on Windows (amd64)

```powershell
cd deployment\tray
$VERSION = (Get-Content ..\..\VERSION).Trim()
go build -ldflags "-X main.version=$VERSION" -o "eyenet-tray-windows-amd64-$VERSION.exe" .\cmd\eyenet-tray
```

## 3. Build on Ubuntu (amd64)

```bash
cd deployment/tray
VERSION="$(tr -d '[:space:]' < ../../VERSION)"
sudo apt-get install -y libgtk-3-dev libayatana-appindicator3-dev   # once
go build -ldflags "-X main.version=${VERSION}" -o eyenet-tray ./cmd/eyenet-tray
tar -czf "eyenet-tray-linux-amd64-${VERSION}.tar.gz" eyenet-tray
```

## 4. Upload GitHub Release (from Mac or any host with both assets)

```bash
VERSION="$(tr -d '[:space:]' < VERSION)"
# gather both artifacts into one directory, then:
sha256sum eyenet-tray-windows-amd64-${VERSION}.exe \
  eyenet-tray-linux-amd64-${VERSION}.tar.gz > SHA256SUMS

gh release create "v${VERSION}" \
  --title "EyeNet platform ${VERSION}" \
  --notes "Host tray binaries for EyeNet ${VERSION}." \
  eyenet-tray-windows-amd64-${VERSION}.exe \
  eyenet-tray-linux-amd64-${VERSION}.tar.gz \
  SHA256SUMS
# If release exists: gh release upload "v${VERSION}" … --clobber
```

Confirm assets on the GitHub **Releases** page for `v${VERSION}`.

## 5. Lab install / soak (Stage 3)

| Lab | Action |
|---|---|
| Windows / WSL | Re-run installer **or** copy `.exe` + write `tray.json`; smoke Start/Stop/Restart/Open UI |
| Ubuntu | Re-run installer **or** extract tarball + autostart; same smoke |

Tray-only publish does **not** require Stage 2 (GHCR). See [`deployment/tray/SMOKE.md`](../../deployment/tray/SMOKE.md).
