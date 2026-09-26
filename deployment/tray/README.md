# EyeNet tray (host control)

System tray / AppIndicator app that shows platform **Active / Inactive / Degraded** and offers **Open UI**, **Start**, **Stop**, and **Restart**.

Pinned to the same product identity as root [`VERSION`](../../VERSION). Binaries publish to **GitHub Releases** on tag `v${VERSION}` via **manual** lab builds + `gh release` today (Actions workflow is draft/future) — not to GHCR.

## Layout

| Path | Role |
|---|---|
| `cmd/eyenet-tray/` | Systray UI (Go + getlantern/systray) |
| `internal/ctl/` | compose status / start / stop / restart / reregister |
| `internal/config/` | `tray.json` schema |
| `scripts/install-autostart-*.ps1\|sh` | Startup / autostart registration |

## Config (`tray.json`)

Written by Windows / Ubuntu installers:

```json
{
  "install_dir": "C:\\ppl-meta-platform",
  "mode": "wsl",
  "wsl_distro": "eyenet",
  "project": "pplmeta",
  "compose_file": "docker-compose.windows-installer.yml",
  "env_file": ".env.windows",
  "ui_url": "http://127.0.0.1:3000",
  "version": "2.25.84"
}
```

Ubuntu uses `"mode": "native"`, `compose_file: "docker-compose.yml"`, `env_file: ".env"`.

Default lookup:

- Windows: `%ProgramData%\EyeNet\tray.json`
- Ubuntu: `$HOME/eyenet-platform/tray/tray.json`

## Local build

```bash
cd deployment/tray
go test ./...
go build -ldflags "-X main.version=$(tr -d '[:space:]' < ../../VERSION)" \
  -o eyenet-tray ./cmd/eyenet-tray
```

Linux needs AppIndicator / GTK headers (CI installs them):

```bash
sudo apt-get install -y libgtk-3-dev libayatana-appindicator3-dev
```

## Release assets (manual today)

| Asset | Build on |
|---|---|
| `eyenet-tray-windows-amd64-${VERSION}.exe` | Windows lab |
| `eyenet-tray-linux-amd64-${VERSION}.tar.gz` | Ubuntu lab |
| `SHA256SUMS` | after both assets exist |

See [`.github/workflows/tray-release.yml`](../../.github/workflows/tray-release.yml) (**future draft**) and *Tray publish* in [`docs/deployment/platform-release-cicd.md`](../../docs/deployment/platform-release-cicd.md). Manual checklist: [`docs/deployment/tray-stage-1.5-publish.md`](../../docs/deployment/tray-stage-1.5-publish.md).

## Operator: publish for current pin (manual)

```bash
# After Stage 1 lands tray + docs on main — build on Win + Ubuntu labs, then:
VERSION="$(tr -d '[:space:]' < VERSION)"
gh release create "v${VERSION}" --title "EyeNet platform ${VERSION}" \
  eyenet-tray-windows-amd64-${VERSION}.exe \
  eyenet-tray-linux-amd64-${VERSION}.tar.gz \
  SHA256SUMS
```

Full steps: [`docs/deployment/tray-stage-1.5-publish.md`](../../docs/deployment/tray-stage-1.5-publish.md).  
Tray-only changes do **not** require Stage 2. GitHub Actions for tray is **not used** today.