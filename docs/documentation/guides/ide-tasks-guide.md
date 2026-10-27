# PPL Meta Platform — IDE Tasks Guide

**Last Updated:** June 29, 2026  
**Scope:** All VS Code tasks available for local development, including the new Headscale VPN + EyeNet Matrix services implemented in this session.

---

## Quick Start — Fire Up the Full Platform

### One-Click Startup
Open **Command Palette** (`Cmd+Shift+P`) → `Tasks: Run Task` → **`🚀 Start All Platform (With VPN + Matrix)`**

This single task runs 5 phases in sequence:

| Phase | What Happens | Duration |
|---|---|---|
| 1 | Starts PostgreSQL + Headscale VPN coordinator | ~3s |
| 2 | Creates dev user, generates pre-auth key, enrolls Tailscale | ~5s |
| 3 | Launches 11 core backend services (Discovery, Node, Media, Gateway, Orchestrator, Vision, Cameras, Bootcore, vmeta, Communications, Presence) | ~10s |
| 4 | Starts Authority (port 8010) + Matrix (port 8015) | ~4s |
| 5 | Health-check of all 13 services + VPN status display | ~3s |

**Total time:** ~25 seconds from click to fully running.

### After Startup — Verify Everything

| Task | What It Shows |
|---|---|
| `📊 Tailscale Status` | VPN connection state + assigned IP (should be in `100.64.x.x`) |
| `🏥 Matrix Service Health Check` | Matrix health + lists all Matrix groups |
| `🌐 Node VPN Status Check` | Node VPN enrollment status + peer list |
| `🏥 Local Python Health Check - All Services` | All 11 core services health |

**Key endpoints to curl:**
```bash
curl http://localhost:8015/api/v1/matrix/groups          # Matrix groups
curl http://localhost:8001/api/v1/node/vpn/status         # Node VPN status
curl http://localhost:8006/api/v1/discovery/topology?vpn=true  # VPN-aware topology
```

---

## Full Shutdown

### One-Click Shutdown
**`🛑 Stop All Platform (With VPN + Matrix)`**

Stops everything in order with port verification:
1. Matrix Service (port 8015)
2. Authority Service (port 8010)
3. All 11 backend services (ports freed)
4. Tailscale VPN logout
5. Headscale coordinator
6. PostgreSQL

### Verify Everything Is Down
**`🔍 Show Local Python Services Status`** — should report `No local Python services found running.`

---

## Complete Task Catalog

### 🚀 Platform Lifecycle Tasks

| Task Label | Type | Description |
|---|---|---|
| `🚀 Start All Platform (With VPN + Matrix)` | Background | **NEW** — Full 5-phase startup with VPN, Matrix, Authority, and 11 backends |
| `🛑 Stop All Platform (With VPN + Matrix)` | Foreground | **NEW** — Complete teardown with port verification |
| `🚀 Start All Local Python Services` | Background | Legacy — 11 core backends only (no VPN/Matrix/Authority) |
| `🛑 Stop All Local Python Services` | Foreground | Legacy — Stops 11 core backends |
| `🚀 Start Complete Platform (Services + Nginx)` | Background | Legacy — Services + Nginx proxy |
| `🛑 Stop Complete Platform (Services + Nginx)` | Foreground | Legacy — Stops services + Nginx |
| `🚀 Start Full Stack (Backend + Frontend)` | Background | Backends + Flutter web frontend on port 3000 |

### 🔐 VPN Tasks (NEW — Headscale Session)

| Task Label | Type | Description |
|---|---|---|
| `🔐 Start Headscale Server (Local Dev)` | Background | Starts Headscale VPN coordinator on `http://127.0.0.1:8080` |
| `🛑 Stop Headscale Server` | Foreground | Kills the Headscale process |
| `🏥 Headscale Health Check` | Foreground | Verifies `{"status":"pass"}` |
| `🔑 Headscale Create Dev Pre-Auth Key` | Foreground | Creates `dev` user + issues key tagged `tag:installation,tag:matrix-dev`. Saves to `/tmp/last_preauth_key.txt` |
| `🔗 Enroll Tailscale to Local Headscale` | Foreground | Starts tailscaled in userspace mode, enrolls using key from previous step |
| `📊 Tailscale Status` | Foreground | Shows connection state, peers, and assigned VPN IP |
| `🔌 Disconnect Tailscale from Local Headscale` | Foreground | `tailscale logout` |
| `🌐 Node VPN Status Check` | Foreground | Queries `GET /api/v1/node/vpn/status` on the node |
| `🧪 Test Tailscale Utils (Python)` | Foreground | Tests `shared/networking/tailscale_utils.py` — IP detection, peer discovery, tags |

### 🔢 Matrix Service Tasks (NEW)

| Task Label | Type | Description |
|---|---|---|
| `🔢 Start Matrix Service (Local Python)` | Background | Starts EyeNet Matrix on port 8015. Auto-creates default group on first boot |
| `🛑 Stop Matrix Service (Local Python)` | Foreground | Stops Matrix, frees port 8015 |
| `🏥 Matrix Service Health Check` | Foreground | Health check + lists all Matrix groups |

### 🔐 Authority Service Tasks

| Task Label | Type | Description |
|---|---|---|
| `🐘 Start Authority PostgreSQL (Local macOS)` | Foreground | Starts PostgreSQL, creates `authority_db` and `authority_user` role |
| `🛑 Stop Authority PostgreSQL (Local macOS)` | Foreground | Stops PostgreSQL via brew services |
| `🏥 Authority PostgreSQL Health Check (Local macOS)` | Foreground | Verifies DB is responding on localhost:5432 |
| `🔐 Start Authority Service (Local Python)` | Background | Starts Authority on port 8010 (requires PostgreSQL) |
| `🔐 Start Authority Service (Local Bootstrap Admin)` | Background | Starts Authority with `AUTHORITY_BOOTSTRAP_ADMIN_ENABLED=true` for first-time admin creation |
| `🛑 Stop Authority Service (Local Python)` | Foreground | Stops Authority (also stops PostgreSQL via dependsOn) |
| `🏥 Authority Service Health Check (Local)` | Foreground | `curl http://localhost:8010/health` |
| `🔑 Bootstrap Authority Admin (Local)` | Foreground | Boots clean PostgreSQL, starts bootstrap-mode authority, creates admin account |
| `🔐 Login Bootstrap Authority Admin (Local)` | Foreground | Logs in with `admin@authority.local` / `change-this-admin-password` |

### 📋 Per-Service Tasks

#### Node Service (port 8001)
| Task Label | Type |
|---|---|
| `🐍 Start Node Service (Local Python)` | Background |
| `🏥 Node Service Health Check (Local)` | Foreground |

#### Media Service (port 8000)
| Task Label | Type |
|---|---|
| `📹 Start Media Service (Local Python)` | Background |
| `🏥 Media Service Health Check (Local)` | Foreground |

#### Gateway Service (port 8080)
| Task Label | Type |
|---|---|
| `🌐 Start Gateway Service (Local Python)` | Background |
| `🏥 Gateway Service Health Check (Local)` | Foreground |

#### Orchestrator Service (port 8002)
| Task Label | Type |
|---|---|
| `🎼 Start Orchestrator Service (Local Python)` | Background |
| `🏥 Orchestrator Service Health Check (Local)` | Foreground |

#### Vision Service (port 8003)
| Task Label | Type |
|---|---|
| `🔍 Start Vision Service (Local Python)` | Background |
| `🛑 Stop Vision Service (Local Python)` | Foreground |
| `🏥 Vision Service Health Check (Local)` | Foreground |

#### Cameras Service (port 8005)
| Task Label | Type |
|---|---|
| `🔍 Start Cameras Service (Local Python)` | Background |
| `🏥 Cameras Service Health Check (Local)` | Foreground |

#### Discovery Service (port 8006)
| Task Label | Type |
|---|---|
| `🔍 Start Discovery Service (Local Python)` | Background |
| `🛑 Stop Discovery Service (Local Python)` | Foreground |
| `🏥 Discovery Service Health Check (Local)` | Foreground |
| `🔍 List All Registered Services` | Foreground |
| `🔍 Discovery Service - Health Check All Services` | Foreground |
| `🔍 Discovery Service - Search Backend Services` | Foreground |

#### Bootcore Service (port 8007)
| Task Label | Type |
|---|---|
| `🔧 Start Bootcore Service (Local Python)` | Background |
| `🏥 Bootcore Service Health Check (Local)` | Foreground |

#### vmeta Service (port 8008)
| Task Label | Type |
|---|---|
| `🔧 Start vmeta Service (Local Python)` | Background |
| `🛑 Stop vmeta Service (Local Python)` | Foreground |
| `🏥 vmeta Service Health Check (Local)` | Foreground |

#### Communications Service (port 8009)
| Task Label | Type |
|---|---|
| `📧 Start Communications Service (Local Python)` | Background |
| `🛑 Stop Communications Service (Local Python)` | Foreground |
| `🏥 Communications Service Health Check (Local)` | Foreground |

#### Presence Service (port 8011)
| Task Label | Type |
|---|---|
| `🫶 Start Presence Service (Local Python 3.11)` | Background |
| `🏥 Presence Service Health Check (Local)` | Foreground |
| `🛠️ Migrate Presence Service (Alembic)` | Foreground |
| `🛠️ Repair Presence Analytics Metadata (Local)` | Foreground |
| `🛠️ Repair Presence Analytics Metadata (API)` | Foreground |
| `🧪 Validate Presence Flow (Local)` | Foreground |
| `🧪 Validate Presence Trace And Analytics (Local)` | Foreground |
| `🧪 Validate Presence Policy Modes (Local)` | Foreground |
| `♻️ Reset Presence Reservations (Local)` | Foreground |

#### Edge Camera (port 9001)
| Task Label | Type |
|---|---|
| `📷 Start Edge Camera (Local Python)` | Background |
| `🛑 Stop Edge Camera (Local Python)` | Foreground |
| `🏥 Edge Camera Health Check` | Foreground |

#### PPL Meta Mini (port 8004)
| Task Label | Type |
|---|---|
| `🔧 Start PPL Meta Mini Service` | Background |
| `🛑 Stop PPL Meta Mini Service` | Foreground |
| `🏥 PPL Meta Mini Health Check` | Foreground |
| `🌐 Start PPL Meta Mini with Apache Proxy` | Background |
| `🛑 Stop PPL Meta Mini with Apache Proxy` | Foreground |
| `🧪 Test PPL Meta Mini Complete Pipeline` | Foreground |

### 🌐 Nginx Proxy Tasks

| Task Label | Type | Description |
|---|---|---|
| `🌐 Start Nginx Proxy (Local Dev)` | Foreground | Configures and starts Nginx |
| `🌐 Stop Nginx Proxy (Local Dev)` | Foreground | Stops Nginx |
| `🌐 Reload Nginx Configuration` | Foreground | Validates and reloads config |
| `🌐 Test Nginx Configuration` | Foreground | Runs test script |
| `🏥 Health Check via Nginx Proxy` | Foreground | Checks all services through the proxy at `localhost/` |

### 📱 Flutter Frontend Tasks

| Task Label | Type | Description |
|---|---|---|
| `📱 Install Flutter Dependencies` | Foreground | `flutter pub get` |
| `📱 Start Frontend (Web)` | Background | Web version on port 3000 |
| `📱 Start Frontend (Desktop)` | Background | macOS native version |
| `📱 Build Frontend (Web)` | Foreground | Production web build |
| `📱 Build Frontend (Desktop)` | Foreground | Production macOS build |
| `📱 Generate Code (Frontend)` | Foreground | `build_runner build` |
| `📱 Watch Code Generation (Frontend)` | Background | `build_runner watch` |
| `📱 Test Frontend` | Foreground | `flutter test` |
| `📱 Clean Frontend` | Foreground | `flutter clean` + `pub get` |
| `📱 Check Flutter Doctor` | Foreground | `flutter doctor -v` |

### 🐳 Docker Tasks

| Task Label | Type | Description |
|---|---|---|
| `🏗️ Build All Docker Images` | Foreground | `docker-compose build` |
| `🚀 Start All Services (Docker)` | Foreground | `docker-compose up -d` |
| `🛑 Stop All Services (Docker)` | Foreground | `docker-compose down` |
| `🏥 Health Check - All Services (Docker)` | Foreground | Checks Gateway, Node, Media, Orchestrator |
| `📋 View Logs - All Services (Docker)` | Background | `docker-compose logs -f` |

### 🧪 Test & Validation Tasks

| Task Label | Type | Description |
|---|---|---|
| `🧪 Complete Testing Workflow` | Foreground | Stop → Start → Nginx → Health checks |
| `🏥 Health Check - Direct Services Only` | Foreground | Direct health checks on all ports |
| `🔍 Show Local Python Services Status` | Foreground | `ps aux` filtered to active services |
| `🧪 Validate Authority Lifecycle Endpoints` | Foreground | Runs authority validation script |
| `🧪 Validate Authority Auth And Dashboard` | Foreground | Runs authority auth validation |
| `🧪 Validate Authority Invitations And Assignments` | Foreground | Runs invitation validation |
| `🧪 Validate Authority Bootstrap Gate` | Foreground | Runs bootstrap gate validation |
| `🧪 Validate Authority Reseller Scope` | Foreground | Runs reseller scope validation |
| `🧪 Validate Authority Admin End-To-End Workflow` | Foreground | Runs admin e2e validation |
| `🔍 Bootstrap State Status` | Foreground | Reports platform bootstrap state |
| `🧪 Bootstrap State Pending` | Foreground | Lists pending bootstrap items |
| `♻️ Bootstrap State Restore` | Foreground | Restores bootstrap state |

---

## Service Port Map

| Service | Port | VPN Endpoints? | New in Session? |
|---|---|---|---|
| Node | 8001 | Yes — `/api/v1/node/vpn/*` | Modified |
| Matrix | 8015 | No — `/api/v1/matrix/*` (23 new endpoints) | **NEW** |
| Authority | 8010 | Yes — `/api/v1/vpn/*` (4 new endpoints) | Modified |
| Discovery | 8006 | Yes — `?vpn=true` on topology | Modified |
| Communications | 8009 | Yes — `/api/v1/vpn/*` | Modified |
| Orchestrator | 8002 | No — token hardening only | Modified |
| Media | 8000 | No | — |
| Gateway | 8080 | No | — |
| Vision | 8003 | No | — |
| Cameras | 8005 | Modified — VPN IP detection | Modified |
| Bootcore | 8007 | No | — |
| vmeta | 8008 | No | — |
| Presence | 8011 | No | — |
| Edge Camera | 9001 | Auto-enrollment via `EdgeCameraVPNService` | Modified |
| Headscale | 8080 (HTTP), 50443 (gRPC) | VPN coordinator | **NEW** |

---

## Environment Variables Required

Per the cybersecurity hardening applied in this session, set these before starting any services:

```bash
export ENVIRONMENT=development
export DEV_BOOTSTRAP_PASSWORD=some-secure-dev-password
export INTERNAL_SERVICE_TOKEN=some-internal-token
export SECRET_KEY=some-shared-jwt-secret
```

**What happens if they're missing:**
- **Node:** Won't bootstrap (hardcoded passwords were removed)
- **Orchestrator:** `RuntimeError` on startup (`INTERNAL_SERVICE_TOKEN` is mandatory)
- **Node + Communications:** Console warnings about default secrets in `model_post_init()`

---

## Quick Sanity Check Commands

Once the platform is up via `🚀 Start All Platform (With VPN + Matrix)`:

```bash
# Headscale health
curl http://127.0.0.1:8080/health

# Tailscale status
tailscale status && tailscale ip -4

# Node VPN peers
curl http://localhost:8001/api/v1/node/vpn/status | python3 -m json.tool

# Matrix groups
curl http://localhost:8015/api/v1/matrix/groups | python3 -m json.tool

# VPN-aware topology
curl 'http://localhost:8006/api/v1/discovery/topology?vpn=true' | python3 -m json.tool

# Communications VPN status
curl http://localhost:8009/api/v1/vpn/status
```

---

## Tips

- **Background tasks** run in the VS Code terminal and don't block the UI. Stop them by closing their terminal tab or using the corresponding Stop task.
- **Foreground tasks** run inline and show output directly — useful for health checks and tests.
- The `🚀 Start All Platform (With VPN + Matrix)` task uses `wait` at the end to keep the background processes alive — closing its terminal will terminate all services.
- Headscale's config must match v0.29.x schema (see `docs/proposals/session-implementation-log.md` Section 9 for breaking changes from earlier versions).
- The Matrix service auto-creates a default single-member group on first boot by reading the local installation UUID from the node's SQLite database — the node must have been initialized at least once before the Matrix service starts.