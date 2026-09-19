# Windows WSL Docker Engine — Full-Product Demo

**Status:** Implementation spec  
**Date:** 2026-09-14  
**Release pin:** matches repository root `VERSION` (currently `2.25.82`)  
**Related:** [platform-release-cicd.md](./platform-release-cicd.md) (canonical CI/CD), [deployment/windows-installer/](../../deployment/windows-installer/), [first-windows-release-2.25.82.md](../guides/first-windows-release-2.25.81.md), [headscaleVPN guide](../guides/headscaleVPN/headscaleVPN%20guide.md)

---

## 1. Why this path

Docker Desktop on Windows is acceptable for licence/bootstrap demos, but it fights product features:

| Capability | Docker Desktop | WSL Docker Engine (`eyenet` distro) |
|---|---|---|
| Same `linux/amd64` GHCR images | Yes | Yes |
| Commercial Desktop licence | Often required | Not required (docker-ce) |
| `/dev/net/tun` + Tailscale for EyeNet mesh | Fragile / missing in installer compose | Native in the distro |
| USB `/dev/video0` | Broken without usbipd hacks | Still not the demo target (no USB) |
| LAN multicast discovery | Unreliable through NAT | Prefer Headscale mesh |
| Operator owns the runtime | Docker Inc. wrapper | One named WSL distro |

**Decision:** demos and near-term installs use **Docker Engine CE inside one WSL2 distro named `eyenet`**, no Docker Desktop. Images stay on GHCR. Authority + Headscale stay on Hetzner.

USB webcams are **out of scope**. Cameras are RTSP, mobile APK, and Pi edge.

---

## 2. In / out of scope

### In scope (local Docker on WSL)

| Service | Port | GHCR image |
|---|---|---|
| postgres | 5432 (host 5433) | `postgres:15-alpine` |
| redis | 6379 | `redis:7-alpine` |
| ppl-meta-node | 8001 | `…/ppl-meta-node` |
| ppl-meta-media | 8000 | `…/ppl-meta-media` |
| ppl-meta-gateway | 8080 | `…/ppl-meta-gateway` |
| ppl-meta-orchestrator | 8002 | `…/ppl-meta-orchestrator` |
| ppl-meta-vision | 8003 | `…/ppl-meta-vision-protected` |
| ppl-meta-vmeta | 8008 | `…/ppl-meta-vmeta-protected` |
| ppl-meta-discovery | **8006** | `…/ppl-meta-discovery` |
| ppl-meta-communications | 8009 | `…/ppl-meta-communications` |
| ppl-meta-frontend | 3000→80 | `…/ppl-meta-frontend` |
| ppl-meta-cameras | 8005 | `…/ppl-meta-cameras` (publish) |
| ppl-meta-presence | 8011 | `…/ppl-meta-presence` (new Dockerfile) |
| ppl-meta-models | 8013 | `…/ppl-meta-models` (new Dockerfile) |

### Remote (Hetzner — do not run locally)

- `ppl-meta-authority` at `https://authority.eyenet-vision.com`
- Headscale at `https://vpn.eyenet-vision.com`

### Clients (separate channels — runbook only)

- Mobile camera APK (`ppl_meta_mobile_camera`)
- Signage APK (`ppl-meta-signage-simple-player`)
- Edge camera on Pi (`ppl-meta-edge-camera`)
- Frontend Android APK

### Out of scope

- USB `/dev/video0` and `usbipd`
- Docker Desktop as a supported engine
- Tailscale.com SaaS accounts
- Local Headscale
- Rebuild vision/vmeta from scratch
- Bootcore (Authority replaced it)
- mini, Consul, Prometheus, Grafana, Jaeger

---

## 3. WSL runtime

| Setting | Value |
|---|---|
| Distro name | `eyenet` |
| Base | Ubuntu 22.04 or 24.04 |
| systemd | enabled (`/etc/wsl.conf`) |
| Docker | docker-ce + compose plugin inside the distro |
| Tailscale | `tailscaled` **once** in the distro (not Tailscale.com login) |
| `.wslconfig` | `memory=12GB`, `processors=6`, `swap=2GB` |
| Host RAM | ≥16 GB |
| Networking | Windows 11 mirrored mode preferred; publish ports still work for `:3000` / `:8080` |

Bootstrap script: [install-eyenet-wsl.ps1](../../deployment/windows-installer/install-eyenet-wsl.ps1).

Refuse to proceed if the only Docker is Docker Desktop’s engine and the `eyenet` distro is missing docker-ce.

---

## 4. Compose inventory and known bugs fixed

Previous Windows bundle gaps:

1. **No cameras / presence / models** — gateway defaults to them; UI expects cameras at `:8005`.
2. **Discovery port** — app listens on **8006**, Windows env mapped host/container **8004**. Fixed to `${DISCOVERY_PORT}:8006` with `DISCOVERY_PORT=8006`.
3. **Communications** — image present but missing `DATABASE_URL` / `REDIS_URL`.
4. **VPN** — Node image had no `tailscale` CLI; compose had no `EYENET_TS_SOCKET` mount.

---

## 5. VPN sequence (no Tailscale SaaS)

```text
1. Installer writes INSTALLATION_UUID + APPLICATION_KEY into .env.windows
2. Owner completes /bootstrap (Authority activate) — does NOT enroll VPN
3. Node lifespan calls enroll_once()
4. Node POST {AUTHORITY}/api/v1/vpn/enroll-installation
     body: installation_uuid, application_key, node_type=platform
5. Authority validates licence, provisions matrix group, Headscale pre-auth key
6. Node: tailscale up --login-server https://vpn.eyenet-vision.com --auth-key …
     via CLI + EYENET_TS_SOCKET → host /var/run/tailscale/tailscaled.sock
7. Node report_platform_local_ip → Authority
8. Leaf devices: Network UI mints enrollment token → phone/signage/edge
     tailscale up --login-server https://vpn.eyenet-vision.com
```

**Placement:** Tailscale runs in the WSL distro. Node container mounts the socket and uses the CLI. No `tailscale.com` account.

Foreign Tailscale.com sessions must not be overwritten; use userspace / EyeNet login-server path documented in Network settings.

---

## 6. Service packaging

| Work | Detail |
|---|---|
| cameras | Existing Dockerfile; add to `platform-release.yml` + build/push scripts |
| presence | New Dockerfile; fix `CAMERAS_SERVICE_URL` (was hardcoded `localhost:8005`) |
| models | New Dockerfile |
| node | Install `tailscale` CLI in image for socket-based enroll |

---

## 7. Installer

1. Run `install-eyenet-wsl.ps1` once (distro + docker-ce + Tailscale client).
2. Run `install-platform.ps1` / `.bat` against **WSL docker** (`wsl -d eyenet -- docker …`), not Docker Desktop.
3. GHCR login inside the distro; compose up; print `http://localhost:3000` and Tailscale status.

---

## 8. Release

Extend:

- [scripts/build_windows_installer_images.sh](../../scripts/build_windows_installer_images.sh)
- [scripts/push_protected_service_images.sh](../../scripts/push_protected_service_images.sh)
- [.github/workflows/platform-release.yml](../../.github/workflows/platform-release.yml) (draft — local publish is current; see [platform-release-cicd.md](./platform-release-cicd.md))

New matrix keys: `cameras`, `presence`, `models`. Default service list includes them.

---

## 9. Phased implementation

| Phase | Work |
|---|---|
| 1 | WSL bootstrap script |
| 2 | Dockerfiles + GHCR publish list + Node Tailscale CLI |
| 3 | Full compose + `.env.windows.template` |
| 4 | Presence `CAMERAS_SERVICE_URL`; installer retarget |
| 5 | Demo runbook + lab verify |

---

## 10. Demo runbook (no USB)

1. Authority: invite owner with distributor scope; note unbound `lic_…` key.
2. On Windows: WSL bootstrap → platform install → open `http://localhost:3000` → `/bootstrap`.
3. Confirm Network settings: VPN enrolled against `vpn.eyenet-vision.com` (EyeNet Headscale).
4. Add RTSP camera by URL (`rtsp://…`). No `/dev/video0`.
5. Mint enrollment token → install mobile camera APK + Tailscale on phone → join mesh.
6. Optional: signage APK / Pi edge with same token path.
7. Presence: preferred types `MOBILE,RTSP,EDGE`; start a presence session on a live tile.
8. Authority admin → VPN nodes: platform + leaf peers under the same matrix.

---

## 11. Verification checklist (`windows-lab`)

- [x] Spec + installer + compose artifacts present in repo
- [x] Compose has cameras/presence/models; discovery `:8006`; no USB mounts
- [x] Presence uses `CAMERAS_SERVICE_URL` (not hardcoded Docker-hostile localhost for connect)
- [x] Current lab stack: bootstrap complete against Authority (Docker Desktop legacy path still running)
- [ ] Publish twelve GHCR images (`cameras`, `presence`, `models` new)
- [ ] Run `install-eyenet-wsl.bat` on lab (create `eyenet` distro; today only `docker-desktop` exists)
- [ ] `wsl -d eyenet -- docker compose … up` with full compose; cameras/presence health
- [ ] `wsl -d eyenet -- tailscale status` shows EyeNet login-server after Node enroll
- [ ] RTSP camera connects; gateway `/api/v1/cameras` and `/api/v1/presence` not 503

Cutover note: do not switch the live lab off Docker Desktop until the new images are in GHCR.

---

## Explicit exclusions (reminder)

USB mounts, Docker Desktop, Tailscale.com accounts, local Headscale, vision/vmeta rebuilds, bootcore, shipping APKs inside Windows compose.
