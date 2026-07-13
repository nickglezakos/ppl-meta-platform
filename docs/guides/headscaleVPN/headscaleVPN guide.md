# EyeNet Headscale VPN — Authority Integration Guide

**Last Updated:** 2026-07-08  
**Status:** Production — deployed on `authority.eyenet-vision.com`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Infrastructure](#2-infrastructure)
3. [VPN API Reference](#3-vpn-api-reference)
4. [Data Model](#4-data-model)
5. [Admin UI Features](#5-admin-ui-features)
6. [Installation Integration](#6-installation-integration)
7. [Verification & Testing](#7-verification--testing)

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Hetzner VPS (138.201.245.219)                                  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Caddy (TLS termination)                                 │   │
│  │  authority.eyenet-vision.com → :8000                     │   │
│  │  vpn.eyenet-vision.com → :8080 (headscale HTTP)          │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────┴──────────────────────────────────┐  │
│  │  Docker Compose Stack                                     │  │
│  │                                                           │  │
│  │  ┌─────────────────┐  ┌──────────────────────────────┐   │  │
│  │  │ authority-       │  │ ppl-meta-authority           │   │  │
│  │  │ postgres         │  │ (port 8000)                  │   │  │
│  │  │ (postgres:16)    │  │                              │   │  │
│  │  └─────────────────┘  │ ┌──────────────────────────┐ │   │  │
│  │                       │ │ VPN API                  │ │   │  │
│  │  ┌─────────────────┐  │ │ /api/v1/vpn/             │ │   │  │
│  │  │ authority-       │  │ │   enroll-installation    │ │   │  │
│  │  │ headscale        │◄─┤ │   nodes                 │ │   │  │
│  │  │ (headscale:0.28) │  │ │   matrix-groups/{id}/*  │ │   │  │
│  │  │ ports 8080/50443  │  │ └──────────────────────────┘ │   │  │
│  │  └─────────────────┘  └──────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                                          │
         │ Internet (TLS)                            │ Internet (TLS)
         ▼                                          ▼
   ┌──────────┐                           ┌──────────┐
   │ Site A   │                           │ Site B   │
   │ (same    │◄─── WireGuard P2P ───────►│ (same    │
   │  matrix) │    100.64.x.x              │  matrix) │
   └──────────┘                           └──────────┘
```

### Key Principles

| Principle | Implementation |
|---|---|
| **1 Entitlement = 1 VPN Mesh** | `entitlements.matrix_group_id` → headscale user `matrix-<uuid>` |
| **Cross-Installation Visibility** | All devices under the same entitlement share the same Tailscale mesh IP space |
| **Mesh Isolation** | Headscale ACL tags (`tag:matrix-<uuid>`) enforce per-entitlement isolation |
| **Peer-to-Peer** | After enrollment, device traffic is direct WireGuard (DERP-relayed if behind NAT) |
| **No Periodic Re-Enrollment** | Pre-auth key is one-time bootstrap. WireGuard keypair persists until explicitly revoked |

---

## 2. Infrastructure

### 2.1 Headscale Container

**Image:** `headscale/headscale:0.28.0`  
**Container name:** `authority-headscale`  
**Network:** `ppl-meta-authority_default` (shared bridge)  
**Ports:** `127.0.0.1:8080` (HTTP), `127.0.0.1:50443` (gRPC), `127.0.0.1:9090` (metrics)

**Config:** `headscale/config.yaml` (bind-mounted from `/home/deploy/apps/ppl-meta-authority/cicd/headscale/`)

```yaml
server_url: https://vpn.eyenet-vision.com
listen_addr: 0.0.0.0:8080
grpc_listen_addr: 0.0.0.0:50443
prefixes:
  v4: 100.64.0.0/10
  v6: fd7a:115c:a1e0::/48
dns:
  magic_dns: true
  base_domain: eyenet-vpn.local
  nameservers:
    global:
      - 1.1.1.1
      - 1.0.0.1
database:
  type: sqlite
  sqlite:
    path: /var/lib/headscale/db.sqlite
policy:
  mode: file
  path: /etc/headscale/acl.json
```

### 2.2 ACL Policy

**File:** `headscale/acl.json` (managed by `VpnACLService`)

Initial state is an empty allow-list. Per-matrix ACLs are dynamically added:
```json
{
  "hosts": {},
  "acls": [],
  "groups": {},
  "tagOwners": {}
}
```

When a device enrolls, the authority adds accept rules scoped to the matrix group tag.

### 2.3 Caddy Reverse Proxy

**File:** `/etc/caddy/Caddyfile` (applied via Caddy admin API on port 2019)

```
# Global options: also listen on port 50443 for headscale gRPC
{
    servers :50443 {
        protocols h1 h2 h2c
    }
}

# Headscale HTTP API (serve/config endpoint used during tailscale up)
vpn.eyenet-vision.com {
    reverse_proxy 127.0.0.1:8080
}

# Headscale gRPC — DNS-only (grey cloud), Cloudflare free plan blocks gRPC on :443
vpn.eyenet-vision.com:50443 {
    reverse_proxy 127.0.0.1:50443 {
        transport http {
            versions h2c
        }
    }
}
```

TLS certificates are auto-managed by Caddy via Let's Encrypt. Caddy terminates TLS on port 50443 and proxies to headscale via clear-text HTTP/2 (h2c) over localhost.

### 2.4 Authority Container

**Image:** `ghcr.io/nickglezakos/ppl-meta-authority:authority-headscale-v1`  
**Headscale CLI access:** Via `docker exec authority-headscale headscale` (Docker socket mounted)  
**Environment:** `HEADSCALE_CLI=docker exec authority-headscale headscale`

### 2.5 Docker Compose

See `autonomous/ppl-meta-authority/docker-compose.production.yml` for the full stack:
- `authority-postgres` (postgres:16)
- `authority-headscale` (headscale/headscale:0.28.0)
- `ppl-meta-authority` (with Docker socket mount for CLI access)

---

## 3. VPN API Reference

All endpoints are at `https://authority.eyenet-vision.com/api/v1/vpn/`.

### 3.1 Enroll Installation

```
POST /api/v1/vpn/enroll-installation
```

**Purpose:** Issue a headscale pre-auth key for an installation to join the VPN mesh.

**Request:**
```json
{
  "installation_uuid": "tenant-a",
  "application_key": "lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f"
}
```

**Response (200):**
```json
{
  "auth_key": "hskey-auth-5nzozvGjwKFb-...",
  "tailscale_ip_range": "100.64.0.0/10",
  "headscale_server": "https://vpn.eyenet-vision.com",
  "matrix_group_id": "366c396d-fb40-4dbc-8c2e-a10cd67323b0",
  "tags": ["tag:installation", "tag:matrix-366c396d-fb40-4dbc-8c2e-a10cd67323b0"],
  "expires_in_seconds": 3600
}
```

**Validation checks:**
- Installation exists by `application_key`
- Owner is enabled
- Licence status is `active` or `grace`
- Installation UUID matches (warning if not)

**Auto-provisioning:**
- If installation has no `matrix_group_id`, it is auto-generated
- Headscale user `matrix-<uuid>` is created if it doesn't exist
- Key expires in 1 hour (for bootstrapping; WireGuard keys are permanent)

### 3.2 List All Nodes

```
GET /api/v1/vpn/nodes
```

Returns all enrolled VPN nodes for the default platform user.

### 3.3 List Matrix Group Nodes

```
GET /api/v1/vpn/matrix-groups/{matrix_id}/nodes
```

Returns only nodes belonging to a specific Matrix group.

### 3.4 Get Matrix Group ACL

```
GET /api/v1/vpn/matrix-groups/{matrix_id}/acl
```

Returns ACL status for a Matrix group's VPN mesh.

### 3.5 Revoke Node

```
DELETE /api/v1/vpn/nodes/{node_id}
```

Removes a node from the VPN (admin only).

---

## 4. Data Model

### 4.1 New Database Columns

| Table | Column | Type | Purpose |
|---|---|---|---|
| `entitlements` | `matrix_group_id` | TEXT | UUID linking entitlement to its VPN mesh (headscale user `matrix-<uuid>`) |
| `installations` | `installation_name` | TEXT | Optional human-readable label (e.g. "Athens HQ Gateway") |
| `installations` | `installation_uuid` | TEXT PK | Now auto-generated: `{owner_email}-{index}` for new installations |

### 4.2 Systemic UUID Generation

When a new installation is created without an explicit `installation_uuid`:

```
nick.glezakos@gmail.com → first installation → nick.glezakos@gmail.com-0
nick.glezakos@gmail.com → second installation → nick.glezakos@gmail.com-1
```

Implemented in `src/core/storage.py` → `upsert_entitlement()`.

### 4.3 Entity Relationships

```
Entitlement (1) ─── (1) matrix_group_id
       │
       └── Installation (1:1, optional)
              │
              └── installation_name (optional, owner-assigned)
              └── installation_uuid (systemic, auto-generated)
```

**VPN Mesh:** All installations under the same entitlement share the same `matrix_group_id`, forming one VPN mesh.

### 4.4 API Models Updated

| Model | New Fields |
|---|---|
| `InstallationRecord` | `installation_name: str \| None` |
| `InstallationUpsertRequest` | `installation_name: str \| None` |
| `DashboardInstallation` | `matrix_group_id: str \| None`, `licence_name: str \| None` |

---

## 5. Admin UI Features

### 5.1 VPN Mesh Section (Admin View)

Located at `https://authority.eyenet-vision.com/admin?view=admin`

- **"VPN Mesh" card** between Entitlement Lifecycle and Audit History sections
- **"Load entitlements with VPN status"** button — displays each entitlement with:
  - 🔗 Matrix group ID (first 12 chars) if mesh active
  - ⏳ "Not provisioned" if no matrix group
  - VPN mesh status (active / auto-provision on enrollment)
  - Entitlement UUID, Installation UUID, Owner email

### 5.2 Data Console — VPN Filter Tab

Located at `https://authority.eyenet-vision.com/admin/console`

- **VPN tab** in the console filter bar (between Updates and Health)
- Shows per-entitlement VPN rows with:
  - **Type:** 🔗 green badge (mesh active) or ⏳ pending
  - **Record:** Licence name + entitlement UUID
  - **Scope/Status:** Matrix group ID prefix + "Mesh active" / "Not provisioned"
  - **Actions:**
    - **Enrol device** — calls `POST /api/v1/vpn/enroll-installation` with the installation's credentials
    - **Copy matrix group** — copies UUID to clipboard
    - **Audit** — jumps to audit view for the entitlement

### 5.3 Installation Name Management

- **Create:** "Installation name" input field in the Advanced Licensing → Create Entitlement form
- **View:** Name shown in the console Entitlements filter as the primary record label
- **Update:** "Update name" action in console row Actions dropdown — opens a prompt with current name, submits to `POST /api/v1/admin/installations`

---

## 6. Installation Integration

### 6.1 One-Time Enrollment Pattern

Each installation (Node, Edge Camera, Gateway) needs to call the authority once during bootstrap to join the VPN:

```python
import httpx
import subprocess

AUTHORITY_URL = "https://authority.eyenet-vision.com"
INSTALLATION_UUID = os.environ["EYENET_INSTALLATION_UUID"]
APPLICATION_KEY = os.environ["EYENET_APPLICATION_KEY"]

def enroll_vpn() -> bool:
    """One-time VPN enrollment. Returns True on success."""
    try:
        resp = httpx.post(
            f"{AUTHORITY_URL}/api/v1/vpn/enroll-installation",
            json={
                "installation_uuid": INSTALLATION_UUID,
                "application_key": APPLICATION_KEY,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        subprocess.run([
            "tailscale", "up",
            "--login-server", data["headscale_server"],
            "--auth-key", data["auth_key"],
            "--accept-routes",
        ], check=True)

        print(f"VPN enrolled: matrix_group={data['matrix_group_id']}")
        return True
    except Exception as e:
        print(f"VPN enrollment failed: {e}")
        return False
```

### 6.2 Environment Variables

| Variable | Source | Example |
|---|---|---|
| `EYENET_INSTALLATION_UUID` | Authority → installation record | `nick.glezakos@gmail.com-0` |
| `EYENET_APPLICATION_KEY` | Authority → entitlement record | `lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f` |

### 6.3 Key Lifecycle

| Phase | Action | Internet Required? |
|---|---|---|
| **Bootstrap** | Call `POST /api/v1/vpn/enroll-installation` | ✅ Yes (to reach authority) |
| **Enroll** | Run `tailscale up --auth-key ...` | ✅ Yes (to reach headscale server once) |
| **Operating** | Device-to-device WireGuard | ❌ No (peer-to-peer) |
| **Operating** (NAT) | Falls back to DERP relay | ⚠️ Yes |
| **Restart** | Tailscale auto-reconnects with cached keys | ❌ No (keys persisted in `/var/lib/tailscale/`) |

> **Important:** The pre-auth key is a one-time bootstrap mechanism. Once `tailscale up` succeeds, the WireGuard keypair is stored locally and the device remains enrolled indefinitely. **No periodic re-enrollment is needed.**

### 6.4 Dockerfile Addition

```dockerfile
# Install Tailscale client for VPN mesh
RUN curl -fsSL https://tailscale.com/install.sh | sh
```

### 6.5 Docker Compose Volume

```yaml
volumes:
  - tailscale-state:/var/lib/tailscale  # Persist WireGuard keys across restarts
```

---

## 7. Verification & Testing

### 7.1 Authority Health Check

```bash
curl -s https://authority.eyenet-vision.com/health
# {"status":"healthy","service":"ppl-meta-authority","mode":"mvp"}
```

### 7.2 Issue a VPN Key (Manual)

```bash
curl -s -X POST https://authority.eyenet-vision.com/api/v1/vpn/enroll-installation \
  -H "Content-Type: application/json" \
  -d '{"installation_uuid":"tenant-a","application_key":"lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f"}' | jq
```

### 7.3 Enroll Tailscale (Manual)

```bash
tailscale up \
  --login-server https://vpn.eyenet-vision.com \
  --auth-key <hskey-auth-from-response> \
  --accept-routes
```

### 7.4 Verify Connectivity

```bash
# Check enrolled devices
tailscale status

# Ping another device in the same matrix group
ping 100.64.x.x

# MagicDNS resolution
ping installation-name.eyenet-vpn.local
```

### 7.5 Verify Mesh Isolation

Devices in different entitlements (different `matrix_group_id`) cannot communicate with each other, even if they're on the same physical network — enforced by headscale ACL tags.

### 7.6 Check Headscale State (VPS)

```bash
ssh deploy@138.201.245.219
docker exec authority-headscale headscale users list
docker exec authority-headscale headscale nodes list
```

---

## Files Reference

| File | Purpose |
|---|---|
| `autonomous/ppl-meta-authority/docker-compose.production.yml` | Docker Compose stack (headscale + authority + postgres) |
| `autonomous/ppl-meta-authority/headscale/config.yaml` | Headscale production configuration |
| `autonomous/ppl-meta-authority/headscale/acl.json` | Initial deny-all ACL policy |
| `autonomous/ppl-meta-authority/src/api/vpn.py` | VPN enrollment + node management API |
| `autonomous/ppl-meta-authority/src/services/vpn_acl_service.py` | ACL synchronization service |
| `autonomous/ppl-meta-authority/src/core/storage.py` | Matrix group auto-provision + systemic UUIDs + installation_name |
| `autonomous/ppl-meta-authority/src/api/installations.py` | InstallationRecord + InstallationUpsertRequest models |
| `autonomous/ppl-meta-authority/src/api/dashboard.py` | DashboardInstallation model (matrix_group_id) |
| `autonomous/ppl-meta-authority/src/ui/templates/console.html` | VPN filter tab in data console |
| `autonomous/ppl-meta-authority/src/ui/templates/admin.html` | VPN Mesh section + Installation name field |
| `autonomous/ppl-meta-authority/src/ui/assets/admin.js` | VPN rows, enrolment handler, update name handler |
| `autonomous/ppl-meta-authority/Dockerfile` | Docker CLI for headscale exec wrapper |
| `docs/authority/eyenet-vpn-mesh-implementation-guide.md` | Original implementation blueprint |

---

## DNS

| Hostname | Record | Resolves To |
|---|---|---|
| `authority.eyenet-vision.com` | A | `138.201.245.219` |
| `vpn.eyenet-vision.com` | A | `138.201.245.219` |