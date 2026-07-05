# EyeNet VPN Mesh — Authority VPS Upgrade & Matrix Integration Guide

**Version:** 1.0  
**Date:** 2026-02-07  
**Status:** Implementation Blueprint  

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Part 1 — VPS Infrastructure Upgrade for VPN](#2-part-1--vps-infrastructure-upgrade-for-vpn)
   - 2.1 [Install Headscale on Hetzner VPS](#21-install-headscale-on-hetzner-vps)
   - 2.2 [Headscale Production Configuration](#22-headscale-production-configuration)
   - 2.3 [Nginx Reverse Proxy (TLS + Subdomain)](#23-nginx-reverse-proxy-tls--subdomain)
   - 2.4 [DNS Record](#24-dns-record)
   - 2.5 [Headscale API Key Generation](#25-headscale-api-key-generation)
3. [Part 2 — Authority Entitlement Schema Upgrade](#3-part-2--authority-entitlement-schema-upgrade)
   - 3.1 [Add `matrix_group_id` to Entitlements Table](#31-add-matrix_group_id-to-entitlements-table)
   - 3.2 [Auto-Provision Matrix Group on Entitlement Creation](#32-auto-provision-matrix-group-on-entitlement-creation)
   - 3.3 [Entitlement → Matrix Defaults](#33-entitlement--matrix-defaults)
   - 3.4 [Update VPN Enrollment to Use Per-Matrix Users](#34-update-vpn-enrollment-to-use-per-matrix-users)
   - 3.5 [Update `enroll-installation` Endpoint](#35-update-enroll-installation-endpoint)
   - 3.6 [Add Matrix-Aware Node Listing Endpoint](#36-add-matrix-aware-node-listing-endpoint)
   - 3.7 [Register VPN Router in `main.py` (Bug Fix)](#37-register-vpn-router-in-mainpy-bug-fix)
4. [Part 3 — Matrix-VPN Integration Implementation](#4-part-3--matrix-vpn-integration-implementation)
   - 4.1 [The 1:1 Matrix ↔ VPN Mesh Relationship](#41-the-11-matrix--vpn-mesh-relationship)
   - 4.2 [Lifecycle Hooks](#42-lifecycle-hooks)
   - 4.3 [Device Enrollment Flow (End-to-End)](#43-device-enrollment-flow-end-to-end)
   - 4.4 [Gateway Discovery Integration](#44-gateway-discovery-integration)
   - 4.5 [Complete Code Changes Summary](#45-complete-code-changes-summary)
5. [Part 4 — Deployment Runbook](#5-part-4--deployment-runbook)
6. [Appendix A — Complete Headscale Production Config](#appendix-a--complete-headscale-production-config)
7. [Appendix B — Complete Nginx vhost for VPN Subdomain](#appendix-b--complete-nginx-vhost-for-vpn-subdomain)
8. [Appendix C — Updated `docker-compose.production.yml`](#appendix-c--updated-docker-composeproductionyml)
9. [Appendix D — Updated `.env.production.example`](#appendix-d--updated-envproductionexample)

---

## 1. Architecture Overview

The VPN mesh architecture ties **Matrix groups** to **Headscale users** in a 1:1 mapping, forming isolated WireGuard/Tailscale-compatible mesh networks. Every entitlement automatically receives a Matrix group and corresponding VPN namespace. All devices enrolled under installations belonging to the same entitlement share the same VPN mesh, regardless of which physical installation they reside on.

```
┌────────────────────────────────────────────────────────────┐
│  authority.eyenet-vision.com (Hetzner VPS)                 │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ppl-meta-authority (Docker, port 8000)              │  │
│  │  ┌──────────────┐  ┌─────────────────────────────┐  │  │
│  │  │ Entitlement  │  │ VPN Enrollment API          │  │  │
│  │  │ + matrix_    │  │ POST /api/v1/vpn/           │  │  │
│  │  │ group_id     │──│   enroll-installation       │  │  │
│  │  └──────┬───────┘  │ GET  /api/v1/vpn/           │  │  │
│  │         │           │   matrix-groups/{id}/nodes  │  │  │
│  │         │           │ GET  /api/v1/vpn/           │  │  │
│  │         │           │   matrix-groups/{id}/acl    │  │  │
│  │         │           └─────────────┬───────────────┘  │  │
│  └─────────┼─────────────────────────┼──────────────────┘  │
│            │                         │ headscale CLI       │
│            │                         ▼                     │
│  ┌─────────┴────────────────────────────────────────────┐  │
│  │  Headscale Server (systemd or Docker, port 8080)     │  │
│  │  ┌─────────────────┐  ┌─────────────────┐            │  │
│  │  │ User: matrix-    │  │ User: matrix-    │  ...      │  │
│  │  │ <uuid-A>        │  │ <uuid-B>        │            │  │
│  │  │ ACL: tag:        │  │ ACL: tag:        │            │  │
│  │  │ matrix-<A> →     │  │ matrix-<B> →     │            │  │
│  │  │ matrix-<A>:*     │  │ matrix-<B>:*     │            │  │
│  │  └────────┬────────┘  └────────┬────────┘            │  │
│  └───────────┼────────────────────┼─────────────────────┘  │
│              │                    │                         │
│  ┌───────────┴────────────────────┴─────────────────────┐  │
│  │  Nginx Reverse Proxy (TLS termination)               │  │
│  │  vpn.eyenet-vision.com:443 → 127.0.0.1:8080          │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬─────────────────────────┘
                                   │ Internet (TLS)
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
    ┌─────▼──────┐           ┌─────▼──────┐           ┌─────▼──────┐
    │ Site A     │           │ Site B     │           │ Site C     │
    │ Matrix-A   │           │ Matrix-A   │           │ Matrix-B   │
    │ ┌────┐┌───┐│           │ ┌────┐     │           │ ┌────┐     │
    │ │ GW ││D1 ││           │ │ GW │ ... │           │ │ GW │ ... │
    │ └────┘└───┘│           │ └────┘     │           │ └────┘     │
    │ 100.64.0.2 │           │ 100.64.0.3 │           │ 100.64.1.2 │
    └────────────┘           └────────────┘           └────────────┘
    ◄─────── Meshes A devices can all communicate ───────►
    ◄─────── Mesh B devices isolated from Mesh A ───────────────►
```

### Key Design Principles

| Principle | Implementation |
|-----------|---------------|
| **1 Matrix Group = 1 VPN Mesh** | Each entitlement's Matrix group is backed by a dedicated Headscale user `matrix-<uuid>`. |
| **Cross-Installation Visibility** | All devices enrolled under the same Matrix group (across any number of installations) share the same Tailscale mesh IP space and can communicate peer-to-peer. |
| **Mesh Isolation** | Headscale ACLs enforce that only nodes tagged `tag:matrix-<uuid>` can communicate with each other. Different Matrix groups are cryptographically isolated. |
| **Internet-Only Once** | Devices contact `vpn.eyenet-vision.com` only during enrollment. After that, all device-to-device traffic is peer-to-peer WireGuard (direct if on same LAN, DERP-relayed if behind NAT). |
| **Gateway Discovery** | Local gateways query the authority for their Matrix group's nodes, then discover services by Tailscale mesh IP. No broadcast/mDNS required. |

---

## 2. Part 1 — VPS Infrastructure Upgrade for VPN

### 2.1 Install Headscale on Hetzner VPS

The authority VPS currently runs:
- PostgreSQL 16 (Docker, for authority DB)
- ppl-meta-authority (Docker, port 8000)
- Nginx (reverse proxy for `authority.eyenet-vision.com`)

Headscale is a new service. Two deployment approaches exist:

#### Option A: Native Binary with Systemd (Recommended)

The existing `src/api/vpn.py` shells out to `headscale` CLI commands (e.g., `headscale preauthkeys create`, `headscale nodes list`). Running Headscale natively avoids Docker-in-Docker CLI complexity.

```bash
# SSH to Hetzner VPS
ssh deploy@<hetzner-ip>

# Download and install Headscale
HEADSCALE_VERSION="0.28.0"
wget https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_amd64.deb
sudo dpkg -i headscale_${HEADSCALE_VERSION}_linux_amd64.deb

# Create data directory
sudo mkdir -p /var/lib/headscale
sudo chown headscale:headscale /var/lib/headscale
```

Create systemd unit (or use the one shipped with the package):

```bash
sudo systemctl enable headscale
```

#### Option B: Docker Compose (Alternative)

If preferred for consistency with the existing Docker Compose setup, add a `headscale` service to the authority's compose file (see [Appendix C](#appendix-c--updated-docker-composeproductionyml)). In this case, wrap CLI calls with `docker exec headscale headscale ...`.

> **⚠️ Decision Required:** Choose one approach. The rest of this guide assumes **Option A (native)** since the existing `vpn.py` code calls `headscale` directly.

---

### 2.2 Headscale Production Configuration

Create `/etc/headscale/config.yaml` on the VPS.

See [Appendix A](#appendix-a--complete-headscale-production-config) for the complete file.

Key configuration decisions:

| Setting | Value | Rationale |
|---------|-------|-----------|
| `server_url` | `https://vpn.eyenet-vision.com` | Public URL that Tailscale clients connect to |
| `listen_addr` | `127.0.0.1:8080` | Bind to localhost only; nginx handles TLS |
| `grpc_listen_addr` | `127.0.0.1:50443` | gRPC via localhost; nginx proxies HTTPS |
| `prefixes.v4` | `100.64.0.0/10` | Tailscale CGNAT range (standard) |
| `prefixes.v6` | `fd7a:115c:a1e0::/48` | ULA IPv6 range |
| `dns.magic_dns` | `true` | Enable MagicDNS for device name resolution |
| `dns.base_domain` | `eyenet-vpn.local` | Internal DNS domain for mesh devices |
| `dns.nameservers.global` | `1.1.1.1`, `1.0.0.1` | Cloudflare DNS fallback |
| `database.type` | `sqlite` | Simple; upgrade to PostgreSQL later if needed |
| `database.sqlite.path` | `/var/lib/headscale/db.sqlite` | Persistent storage path |
| `log.level` | `info` | Production log level; set to `debug` for troubleshooting |
| `randomize_client_port` | `false` | Deterministic port for easier firewall rules |
| `taildrop.enabled` | `true` | Enable file transfer between mesh nodes |

---

### 2.3 Nginx Reverse Proxy (TLS + Subdomain)

The VPS already runs nginx for `authority.eyenet-vision.com`. Add a new server block for the VPN subdomain.

See [Appendix B](#appendix-b--complete-nginx-vhost-for-vpn-subdomain) for the complete nginx configuration.

```bash
# On Hetzner VPS
sudo nano /etc/nginx/sites-available/vpn.eyenet-vision.com
# Paste the server block from Appendix B

sudo ln -s /etc/nginx/sites-available/vpn.eyenet-vision.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

#### Obtain TLS Certificate

```bash
sudo certbot --nginx -d vpn.eyenet-vision.com
```

This sets up automatic renewal via certbot's systemd timer.

---

### 2.4 DNS Record

Add an A record (or CNAME) on your DNS provider:

```
Type:  A
Name:  vpn.eyenet-vision.com
Value: <Hetzner VPS public IP>
TTL:   300 (or auto)
```

Verify:

```bash
dig vpn.eyenet-vision.com +short
```

---

### 2.5 Headscale API Key Generation

After Headscale is running, generate an API key for the authority to use:

```bash
# SSH to VPS, run as root or headscale user
sudo headscale apikeys create --expiration 87600h
# Output: tskey-api-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **Note:** The current `vpn.py` uses the `headscale` CLI directly (not the API key), so the API key is primarily for the gateway's `HeadscaleProvider` HTTP client. For the authority's CLI-based approach, ensure the `headscale` user or the user running the authority container has permission to execute `headscale` commands.

Add the API key to the authority environment:

```bash
echo "HEADSCALE_API_KEY=tskey-api-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" >> /home/deploy/apps/ppl-meta-authority/cicd/env/authority.env
```

---

## 3. Part 2 — Authority Entitlement Schema Upgrade

### 3.1 Add `matrix_group_id` to Entitlements Table

The `entitlements` table currently has no matrix linkage. Add a `matrix_group_id` column.

**File:** `src/core/storage.py`

**1. Add the column to the `CREATE TABLE` statement in `_schema_statements()`:**

The entitlements table currently ends with:
```sql
notes TEXT,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
```

Add `matrix_group_id` after `notes`:
```sql
notes TEXT,
matrix_group_id TEXT,
created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
```

**2. Add `_ensure_column` call in `initialize_database()`:**

Add this line after the existing `_ensure_column` calls in `initialize_database()`:
```python
_ensure_column(connection, "entitlements", "matrix_group_id", "TEXT")
```

**3. Add an index (optional but recommended):**

```sql
CREATE INDEX IF NOT EXISTS idx_entitlements_matrix_group ON entitlements(matrix_group_id);
```

Add this as an additional statement in `_schema_statements()` or execute it in `initialize_database()`.

---

### 3.2 Auto-Provision Matrix Group on Entitlement Creation

When an entitlement is created (via `upsert_entitlement()`), if no `matrix_group_id` exists, the system must:

1. Generate a new UUID for the matrix group
2. Store it in the entitlements row
3. Call Headscale to create a corresponding user
4. Write initial ACL policy
5. Log to audit trail

**File:** `src/core/storage.py`

Add a new helper function:

```python
def _ensure_matrix_group(entitlement_uuid: str) -> str:
    """Ensure an entitlement has a matrix_group_id.

    If the entitlement already has one, return it.
    Otherwise, generate a new UUID, persist it, and provision
    the corresponding Headscale user + ACL.
    """
    import subprocess
    import logging

    logger = logging.getLogger(__name__)

    entitlement = get_entitlement_by_uuid(entitlement_uuid)
    if entitlement is None:
        raise ValueError(f"Entitlement not found: {entitlement_uuid}")

    existing = entitlement.get("matrix_group_id")
    if existing:
        return existing

    matrix_group_id = str(uuid.uuid4())

    # Persist the matrix_group_id
    with _connect() as connection:
        connection.execute(
            "UPDATE entitlements SET matrix_group_id = ?, updated_at = CURRENT_TIMESTAMP WHERE entitlement_uuid = ?",
            (matrix_group_id, entitlement_uuid),
        )
        connection.commit()

    # Provision Headscale user
    headscale_user = f"matrix-{matrix_group_id}"
    try:
        subprocess.run(
            ["headscale", "users", "create", "--name", headscale_user],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        logger.info("Headscale user created: %s", headscale_user)
    except subprocess.CalledProcessError as exc:
        logger.error("Failed to create Headscale user %s: %s", headscale_user, exc.stderr)
        # Non-fatal: enrollment will retry user creation via _ensure_user_id()

    logger.info(
        "Matrix group %s auto-provisioned for entitlement %s",
        matrix_group_id,
        entitlement_uuid,
    )

    return matrix_group_id
```

**Integration point in `upsert_entitlement()`:**

At the end of `upsert_entitlement()`, after the `stored_record` is confirmed, call:

```python
# Ensure matrix group exists (auto-creates if missing)
stored_record = get_entitlement_by_uuid(entitlement_uuid)
if stored_record is None:
    raise RuntimeError("Entitlement upsert failed")

# Auto-provision matrix group if not present
if not stored_record.get("matrix_group_id"):
    _ensure_matrix_group(stored_record["entitlement_uuid"])
    stored_record = get_entitlement_by_uuid(entitlement_uuid)  # refresh

return stored_record
```

---

### 3.3 Entitlement → Matrix Defaults

| Rule | Behavior |
|------|----------|
| **One entitlement → one Matrix group** | Each entitlement gets exactly one `matrix_group_id`. This is the default behavior. |
| **Multiple installations, same entitlement** | All installations under the same entitlement share the same `matrix_group_id`. Devices across installations automatically see each other on the mesh. |
| **Separate meshes required** | Create separate entitlements. Each gets its own Matrix group and isolated VPN mesh. |
| **Auto-creation on first enrollment** | If an entitlement somehow lacks a `matrix_group_id` at VPN enrollment time, the enrollment endpoint calls `_ensure_matrix_group()` before issuing a key. |

---

### 3.4 Update VPN Enrollment to Use Per-Matrix Users

**Current behavior (wrong):** The `enroll_installation` endpoint in `src/api/vpn.py` uses a single flat user `"eyenet-platform"` for all enrollments. This means ALL devices across ALL entitlements end up in the same Headscale user namespace — defeating mesh isolation.

**Required change:** Use `f"matrix-{matrix_group_id}"` as the Headscale user.

**File:** `src/api/vpn.py`

**Replace in `enroll_installation()`:**

```python
# OLD CODE (lines 186-195):
# Determine ACL tags
tags = ["tag:installation"]
matrix_group_id = installation.get("matrix_group_id")
if matrix_group_id:
    tags.append(f"tag:matrix-{matrix_group_id}")

headscale_user = "eyenet-platform"

# NEW CODE:
# Determine ACL tags and user namespace
matrix_group_id = installation.get("matrix_group_id")
if matrix_group_id:
    tags = [f"tag:matrix-{matrix_group_id}"]
    headscale_user = f"matrix-{matrix_group_id}"
else:
    # Legacy installations without a matrix group — auto-provision one
    from core.storage import _ensure_matrix_group
    matrix_group_id = _ensure_matrix_group(installation["entitlement_uuid"])
    tags = [f"tag:matrix-{matrix_group_id}"]
    headscale_user = f"matrix-{matrix_group_id}"

# Always include the base installation tag
if "tag:installation" not in tags:
    tags.insert(0, "tag:installation")
```

Also update `list_vpn_nodes()` and `revoke_vpn_node()` to accept a `matrix_group_id` parameter or infer it from the node's tags.

---

### 3.5 Update `enroll-installation` Endpoint

**Current return value:**

```python
return EnrollInstallationResponse(
    auth_key=auth_key,
    tags=tags,
    headscale_server="https://vpn.eyenet-vision.com:50443",
    expires_in_seconds=PREAUTH_KEY_EXPIRY_HOURS * 3600,
)
```

**Required change:** The `headscale_server` field should use port 443 (standard HTTPS via nginx), not 50443 (raw gRPC port):

```python
headscale_server="https://vpn.eyenet-vision.com"
```

Additionally, add the `matrix_group_id` to the response so the enrolling device knows which mesh it belongs to:

```python
class EnrollInstallationResponse(BaseModel):
    auth_key: str
    tailscale_ip_range: str = "100.64.0.0/10"
    headscale_server: str = ""
    matrix_group_id: str = ""          # NEW
    tags: list[str] = []
    expires_in_seconds: int = 3600
```

---

### 3.6 Add Matrix-Aware Node Listing Endpoint

Add a new endpoint that returns only the nodes belonging to a specific Matrix group.

**File:** `src/api/vpn.py`

```python
@router.get("/matrix-groups/{matrix_id}/nodes", response_model=VpnNodeListResponse)
async def list_matrix_group_nodes(matrix_id: str, _request: Request):
    """List all enrolled VPN nodes for a specific Matrix group.

    Returns only nodes tagged with tag:matrix-{matrix_id}.
    Requires admin session authentication.
    """
    # TODO: require_admin_session dependency
    headscale_user = f"matrix-{matrix_id}"

    try:
        nodes_data = _list_nodes(headscale_user)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"Failed to list nodes: {exc}")

    nodes = []
    for node in nodes_data:
        nodes.append(VpnNodeInfo(
            node_id=node.get("ID", node.get("NodeKey", "")),
            installation_uuid="",
            tailscale_ip=(
                node.get("IPAddresses", [None])[0] if node.get("IPAddresses") else None
            ),
            online=node.get("Online", False),
            last_seen=node.get("LastSeen"),
        ))

    return VpnNodeListResponse(nodes=nodes)
```

---

### 3.7 Register VPN Router in `main.py` (Bug Fix)

**Critical:** The VPN router at `src/api/vpn.py` is **not registered** in `src/main.py`. It must be added.

**File:** `src/main.py`

Add these two lines:

```python
from api.vpn import router as vpn_router          # NEW

# ... existing router registrations ...

app.include_router(vpn_router)                     # NEW
```

---

## 4. Part 3 — Matrix-VPN Integration Implementation

### 4.1 The 1:1 Matrix ↔ VPN Mesh Relationship

| Concept | Implementation |
|---------|---------------|
| **Matrix Group** | A row in the `matrix_groups` table (managed by `ppl-meta-matrix` service) + a Headscale user `matrix-<uuid>` (managed by authority) |
| **Matrix Member** | An installation's device enrolled with ACL tag `tag:matrix-<uuid>` |
| **Mesh Isolation** | Headscale ACL policy: only nodes with matching `tag:matrix-X` can communicate with each other. A `deny * → *:*` catch-all at the bottom ensures cross-group isolation. |
| **Cross-Installation Visibility** | All devices in the same matrix group (regardless of which installation they belong to) see each other via Tailscale mesh IPs (`100.64.x.x`) |

#### ACL Policy Structure

The `VpnACLService` (`src/services/vpn_acl_service.py`) already manages ACL file-based policies. The ACL for each matrix group is:

```json
{
  "hosts": {},
  "acls": [
    {
      "action": "accept",
      "src": ["tag:matrix-<uuid-A>"],
      "dst": ["tag:matrix-<uuid-A>:*"]
    },
    {
      "action": "accept",
      "src": ["tag:matrix-<uuid-B>"],
      "dst": ["tag:matrix-<uuid-B>:*"]
    },
    {
      "action": "deny",
      "src": ["*"],
      "dst": ["*:*"]
    }
  ]
}
```

> ⚠️ **Note:** The `VpnACLService` writes to file-based ACL (`/etc/headscale/acl.json`). This works when Headscale runs natively on the same host. If Headscale is containerized, the ACL path must be a shared volume.

---

### 4.2 Lifecycle Hooks

| Event | VPN Action | Where to Hook |
|-------|-----------|---------------|
| **Entitlement created** | Call `_ensure_matrix_group()` → creates Headscale user + initial ACL | `upsert_entitlement()` in `storage.py` |
| **Installation activated** (bound to entitlement) | Issue pre-auth key for user `matrix-<matrix_group_id>` via `enroll-installation` endpoint | Already handled in `enroll_installation()` in `vpn.py` |
| **Installation deactivated/suspended** | Delete node from Headscale to revoke mesh access | Add to `set_entitlement_activation_status()` or create a new hook |
| **Entitlement revoked** | Delete Headscale user `matrix-<uuid>` (evicts all nodes) | Add to `delete_entitlement()` in `storage.py` |
| **Entitlement licence expired** | Optionally suspend nodes (mark offline via ACL, don't delete — allows re-activation) | Add to licence lifecycle logic |

#### Recommended Lifecycle Hook Implementation

Add to `delete_entitlement()` in `storage.py`:

```python
def delete_entitlement(entitlement_uuid: str) -> bool:
    import subprocess
    import logging
    logger = logging.getLogger(__name__)

    entitlement = get_entitlement_by_uuid(entitlement_uuid)
    if entitlement is None:
        return False

    # Clean up VPN mesh
    matrix_group_id = entitlement.get("matrix_group_id")
    if matrix_group_id:
        headscale_user = f"matrix-{matrix_group_id}"
        try:
            subprocess.run(
                ["headscale", "users", "destroy", "--name", headscale_user, "--force"],
                capture_output=True, text=True, timeout=15, check=False,
            )
            logger.info("Headscale user %s destroyed (entitlement deleted)", headscale_user)
        except Exception as exc:
            logger.warning("Failed to destroy Headscale user %s: %s", headscale_user, exc)

    # Existing deletion logic...
    with _connect() as connection:
        if entitlement["installation_uuid"]:
            connection.execute(
                "DELETE FROM installations WHERE installation_uuid = ?",
                (entitlement["installation_uuid"],),
            )
        cursor = connection.execute(
            "DELETE FROM entitlements WHERE entitlement_uuid = ?",
            (entitlement_uuid,),
        )
        connection.commit()

    return cursor.rowcount > 0
```

---

### 4.3 Device Enrollment Flow (End-to-End)

```
STEP 1: Installation boots
  │
  ├─ Installation has: application_key, installation_uuid
  │
  ▼
STEP 2: Installation calls Authority VPN API
  │
  │  POST https://authority.eyenet-vision.com/api/v1/vpn/enroll-installation
  │  Body: {
  │    "installation_uuid": "abc-123",
  │    "application_key": "lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f"
  │  }
  │
  ▼
STEP 3: Authority validates
  │
  │  ├─ application_key found in entitlements table? ✓
  │  ├─ owner_enabled = true? ✓
  │  ├─ licence_status in {"active", "grace"}? ✓
  │  └─ installation not bound elsewhere? ✓
  │
  ▼
STEP 4: Authority reads/resolves matrix_group_id
  │
  │  ├─ entitlement.matrix_group_id exists? → Use it
  │  └─ NULL? → _ensure_matrix_group() creates:
  │       ├─ UUID → matrix_group_id
  │       ├─ Headscale user: matrix-<uuid>
  │       └─ Stored in entitlements table
  │
  ▼
STEP 5: Authority generates pre-auth key
  │
  │  $ headscale preauthkeys create \
  │      --user matrix-<matrix_group_id> \
  │      --tags tag:matrix-<matrix_group_id>
  │
  │  Output: tskey-auth-kABC123...
  │
  ▼
STEP 6: Authority returns enrollment payload
  │
  │  {
  │    "auth_key": "tskey-auth-kABC123...",
  │    "headscale_server": "https://vpn.eyenet-vision.com",
  │    "matrix_group_id": "<uuid>",
  │    "tags": ["tag:matrix-<uuid>"],
  │    "tailscale_ip_range": "100.64.0.0/10",
  │    "expires_in_seconds": 3600
  │  }
  │
  ▼
STEP 7: Installation runs Tailscale enrollment
  │
  │  $ tailscale up \
  │      --login-server https://vpn.eyenet-vision.com \
  │      --auth-key tskey-auth-kABC123... \
  │      --accept-routes
  │
  │  Result: Device gets IP 100.64.x.x
  │
  ▼
STEP 8: Device is now a mesh peer
  │
  │  ├─ Can communicate with ALL other devices tagged tag:matrix-<uuid>
  │  ├─ Regardless of which installation they belong to
  │  ├─ Peer-to-peer WireGuard (direct if same LAN, DERP if NAT'd)
  │  └─ MagicDNS: device-name.eyenet-vpn.local resolves
  │
  ▼
STEP 9: Local gateway discovers mesh peers
  │
     GET https://authority.eyenet-vision.com/api/v1/vpn/matrix-groups/<uuid>/nodes
     → Returns list of all devices in this matrix group
     → Gateway maps Tailscale IPs to local services
```

---

### 4.4 Gateway Discovery Integration

The local gateway (`ppl-meta-gateway`) at each installation needs to discover its VPN mesh peers. This is done by querying the authority for the installation's Matrix group nodes.

**Recommended integration pattern in the gateway:**

```python
# Pseudocode for gateway integration
async def discover_mesh_peers(entitlement_matrix_group_id: str) -> List[VPNDevice]:
    """Discover all VPN mesh peers for this installation's Matrix group."""
    authority_url = "https://authority.eyenet-vision.com"
    endpoint = f"{authority_url}/api/v1/vpn/matrix-groups/{entitlement_matrix_group_id}/nodes"

    async with httpx.AsyncClient() as client:
        resp = await client.get(endpoint)
        resp.raise_for_status()
        data = resp.json()

    return data["nodes"]
```

The gateway should:
1. On startup, query the matrix group's nodes to discover all peers
2. Periodically refresh (e.g., every 60 seconds) to detect new/offline devices
3. Map Tailscale IPs (`100.64.x.x`) to local service endpoints for cross-installation communication

---

### 4.5 Complete Code Changes Summary

| # | File | Change | Severity |
|---|------|--------|----------|
| 1 | `src/main.py` | Register VPN router: `from api.vpn import router as vpn_router; app.include_router(vpn_router)` | 🔴 **Critical** — VPN API is unreachable without this |
| 2 | `src/core/storage.py` | Add `matrix_group_id TEXT` to entitlements CREATE TABLE | 🔴 **Critical** |
| 3 | `src/core/storage.py` | Add `_ensure_column("entitlements", "matrix_group_id", "TEXT")` in `initialize_database()` | 🔴 **Critical** |
| 4 | `src/core/storage.py` | Add `_ensure_matrix_group()` function | 🔴 **Critical** |
| 5 | `src/core/storage.py` | Call `_ensure_matrix_group()` from `upsert_entitlement()` | 🔴 **Critical** |
| 6 | `src/core/storage.py` | Add VPN mesh cleanup to `delete_entitlement()` | 🟡 Important |
| 7 | `src/api/vpn.py` | Update `enroll_installation()`: use `matrix-{id}` user instead of `"eyenet-platform"` | 🔴 **Critical** |
| 8 | `src/api/vpn.py` | Fix `headscale_server` URL: remove `:50443` port | 🟡 Important |
| 9 | `src/api/vpn.py` | Add `matrix_group_id` to `EnrollInstallationResponse` | 🟡 Important |
| 10 | `src/api/vpn.py` | Add `GET /matrix-groups/{matrix_id}/nodes` endpoint | 🟢 Enhancement |
| 11 | `src/api/vpn.py` | Update `list_vpn_nodes()` to support matrix-scoped queries | 🟡 Important |
| 12 | `src/api/vpn.py` | Update `revoke_vpn_node()` to support matrix-scoped queries | 🟡 Important |
| 13 | `src/services/vpn_acl_service.py` | Minor update to handle per-matrix users (already designed for this) | 🟢 Minor |
| 14 | `docker-compose.production.yml` | Add docker socket mount for headscale CLI access from authority container (or use systemd) | 🟡 Important |
| 15 | `.env.production.example` | Add `HEADSCALE_API_KEY` and `VPN_SUBDOMAIN` | 🟡 Important |
| 16 | New: `/etc/headscale/config.yaml` | Production Headscale config (see Appendix A) | 🔴 **Critical** |
| 17 | New: `/etc/nginx/sites-available/vpn.eyenet-vision.com` | Nginx vhost (see Appendix B) | 🔴 **Critical** |
| 18 | DNS | Add `vpn.eyenet-vision.com` A record | 🔴 **Critical** |

---

## 5. Part 4 — Deployment Runbook

### Step 1: SSH to Hetzner VPS

```bash
ssh deploy@<hetzner-ip>
```

### Step 2: Install Headscale

```bash
HEADSCALE_VERSION="0.28.0"
cd /tmp
wget https://github.com/juanfont/headscale/releases/download/v${HEADSCALE_VERSION}/headscale_${HEADSCALE_VERSION}_linux_amd64.deb
sudo dpkg -i headscale_${HEADSCALE_VERSION}_linux_amd64.deb

# Create data directories
sudo mkdir -p /var/lib/headscale
sudo chown -R headscale:headscale /var/lib/headscale

# Verify
headscale version
```

### Step 3: Deploy Headscale Configuration

```bash
sudo nano /etc/headscale/config.yaml
# Paste content from Appendix A
```

### Step 4: Start Headscale

```bash
sudo systemctl enable headscale
sudo systemctl start headscale
sudo systemctl status headscale
```

Verify it's listening:

```bash
curl -s http://127.0.0.1:8080/version
```

### Step 5: Add Nginx Vhost

```bash
sudo nano /etc/nginx/sites-available/vpn.eyenet-vision.com
# Paste content from Appendix B

sudo ln -s /etc/nginx/sites-available/vpn.eyenet-vision.com /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Step 6: Obtain TLS Certificate

```bash
sudo certbot --nginx -d vpn.eyenet-vision.com
```

### Step 7: Add DNS Record

```
Type:  A
Name:  vpn
Value: <hetzner-ip>
TTL:   300
```

Verify:

```bash
dig vpn.eyenet-vision.com +short
```

### Step 8: Generate Headscale API Key

```bash
sudo headscale apikeys create --expiration 87600h
# Save the output
```

### Step 9: Update Authority Environment

Edit `/home/deploy/apps/ppl-meta-authority/cicd/env/authority.env` and add:

```bash
HEADSCALE_API_KEY=tskey-api-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VPN_SUBDOMAIN=vpn.eyenet-vision.com
```

### Step 10: Grant Authority Container Access to Headscale CLI

Since the authority container calls `headscale` CLI directly, it needs access. Several options:

**Option A — Bind-mount the headscale binary and socket (recommended):**

Add to `docker-compose.production.yml` under the `ppl-meta-authority` service:

```yaml
volumes:
  - /usr/bin/headscale:/usr/bin/headscale:ro
  - /var/run/headscale:/var/run/headscale
```

**Option B — Run headscale in Docker alongside authority with docker exec wrapper.**

**Option C — Expose headscale via HTTP API instead of CLI.**

Option A is simplest if headscale is installed natively.

### Step 11: Deploy Updated Authority Image

Build and push the updated authority image with all code changes from Part 2 & 3, then deploy:

```bash
# Via GitHub Actions workflow (as documented in DEPLOYMENT_HETZNER.md)
# Or manually:
docker pull ghcr.io/nickglezakos/ppl-meta-authority:<new-tag>
# Restart with updated compose file
```

### Step 12: Smoke Test

```bash
# 1. Authority health check
curl -s https://authority.eyenet-vision.com/health | jq

# 2. VPN health check
curl -s https://authority.eyenet-vision.com/api/v1/vpn/health | jq

# 3. Create a test entitlement and verify matrix_group_id is auto-generated
#    (Use admin dashboard or API)

# 4. Enroll a test device
curl -s -X POST https://authority.eyenet-vision.com/api/v1/vpn/enroll-installation \
  -H "Content-Type: application/json" \
  -d '{
    "installation_uuid": "test-installation",
    "application_key": "lic_6f3c8d1e2b4a5c7d8e9f0a1b2c3d4e5f"
  }' | jq

# Expected response:
# {
#   "auth_key": "tskey-auth-...",
#   "matrix_group_id": "<uuid>",
#   "headscale_server": "https://vpn.eyenet-vision.com",
#   "tags": ["tag:installation", "tag:matrix-<uuid>"],
#   ...
# }

# 5. List nodes for the matrix group
curl -s https://authority.eyenet-vision.com/api/v1/vpn/matrix-groups/<uuid>/nodes | jq

# 6. Test device enrollment with tailscale
tailscale up --login-server https://vpn.eyenet-vision.com --auth-key <tskey-auth-...>

# 7. Verify mesh connectivity
tailscale status
ping <other-device-ip>
```

---

## Appendix A — Complete Headscale Production Config

**File:** `/etc/headscale/config.yaml`

```yaml
# Headscale Production Configuration
# EyeNet VPN Mesh — authority.eyenet-vision.com
# Based on https://github.com/juanfont/headscale/blob/main/config-example.yaml

server_url: https://vpn.eyenet-vision.com
listen_addr: 127.0.0.1:8080
metrics_listen_addr: 127.0.0.1:9090
grpc_listen_addr: 127.0.0.1:50443
grpc_allow_insecure: false

noise:
  private_key_path: /var/lib/headscale/noise_private.key

prefixes:
  v4: 100.64.0.0/10
  v6: fd7a:115c:a1e0::/48
  allocation: sequential

derp:
  server:
    enabled: false
    region_id: 999
    region_code: headscale
    region_name: Headscale Embedded DERP
    verify_clients: true
    stun_listen_addr: 0.0.0.0:3478
    private_key_path: /var/lib/headscale/derp_server_private.key
    automatically_add_embedded_derp_region: true
  urls:
    - https://controlplane.tailscale.com/derpmap/default
  paths: []
  auto_update_enabled: true
  update_frequency: 3h

database:
  type: sqlite
  debug: false
  sqlite:
    path: /var/lib/headscale/db.sqlite
    write_ahead_log: true
    wal_autocheckpoint: 1000

log:
  level: info
  format: json

policy:
  mode: file
  path: /etc/headscale/acl.json

dns:
  magic_dns: true
  base_domain: eyenet-vpn.local
  override_local_dns: true
  nameservers:
    global:
      - 1.1.1.1
      - 1.0.0.1
  split: {}
  search_domains: []
  extra_records: []

logtail:
  enabled: false

randomize_client_port: false

taildrop:
  enabled: true
```

> **Note:** ACL policy path (`/etc/headscale/acl.json`) must be writable by the headscale user. The `VpnACLService` writes to this file. Ensure the authority container (or the user running it) also has write access to this path, or use a shared volume.

---

## Appendix B — Complete Nginx vhost for VPN Subdomain

**File:** `/etc/nginx/sites-available/vpn.eyenet-vision.com`

```nginx
# EyeNet VPN Mesh — Headscale Reverse Proxy
# vpn.eyenet-vision.com → 127.0.0.1:8080

server {
    listen 80;
    server_name vpn.eyenet-vision.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name vpn.eyenet-vision.com;

    # Managed by certbot
    ssl_certificate     /etc/letsencrypt/live/vpn.eyenet-vision.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vpn.eyenet-vision.com/privkey.pem;
    include             /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam         /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Main proxy to Headscale HTTP API
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;

        # Timeouts for long-lived connections
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;

        # Buffer settings for API responses
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # gRPC endpoint (for Tailscale client control protocol)
    location /grpc {
        grpc_pass grpc://127.0.0.1:50443;
        grpc_set_header Host $host;
        grpc_set_header X-Real-IP $remote_addr;
        grpc_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        grpc_read_timeout 86400s;
        grpc_send_timeout 86400s;
    }

    # Metrics endpoint (internal only, or add IP restriction)
    location /metrics {
        proxy_pass http://127.0.0.1:9090/metrics;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Restrict to VPS internal access only
        allow 127.0.0.1;
        allow <your-office-ip>;  # optional: monitoring IP
        deny all;
    }

    # Access log
    access_log /var/log/nginx/vpn.eyenet-vision.com.access.log;
    error_log  /var/log/nginx/vpn.eyenet-vision.com.error.log;
}
```

After creating this file, enable it and reload nginx:

```bash
sudo ln -s /etc/nginx/sites-available/vpn.eyenet-vision.com /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Then obtain the TLS certificate:

```bash
sudo certbot --nginx -d vpn.eyenet-vision.com
```

---

## Appendix C — Updated `docker-compose.production.yml`

**File:** `/home/deploy/apps/ppl-meta-authority/cicd/compose/docker-compose.yml`

```yaml
services:
  authority-postgres:
    image: postgres:16
    container_name: authority-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${AUTHORITY_POSTGRES_DB}
      POSTGRES_USER: ${AUTHORITY_POSTGRES_USER}
      POSTGRES_PASSWORD: ${AUTHORITY_POSTGRES_PASSWORD}
    volumes:
      - authority-postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${AUTHORITY_POSTGRES_USER} -d ${AUTHORITY_POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  ppl-meta-authority:
    image: ${AUTHORITY_IMAGE}
    container_name: ppl-meta-authority
    restart: unless-stopped
    depends_on:
      authority-postgres:
        condition: service_healthy
    environment:
      AUTHORITY_DATABASE_URL: ${AUTHORITY_DATABASE_URL}
      AUTHORITY_ADMIN_TOKEN: ${AUTHORITY_ADMIN_TOKEN}
      AUTHORITY_BOOTSTRAP_ADMIN_ENABLED: ${AUTHORITY_BOOTSTRAP_ADMIN_ENABLED:-false}
      AUTHORITY_BASE_URL: ${AUTHORITY_BASE_URL:-}
      AUTHORITY_PUBLIC_BASE_URL: ${AUTHORITY_PUBLIC_BASE_URL:-}
      HEADSCALE_API_KEY: ${HEADSCALE_API_KEY:-}
      MAIL_SERVER: ${MAIL_SERVER:-}
      MAIL_PORT: ${MAIL_PORT:-587}
      MAIL_USERNAME: ${MAIL_USERNAME:-}
      MAIL_PASSWORD: ${MAIL_PASSWORD:-}
      MAIL_FROM: ${MAIL_FROM:-}
      MAIL_FROM_NAME: ${MAIL_FROM_NAME:-PPL Meta Authority}
      MAIL_STARTTLS: ${MAIL_STARTTLS:-true}
      MAIL_SSL_TLS: ${MAIL_SSL_TLS:-false}
      USE_CREDENTIALS: ${USE_CREDENTIALS:-true}
    volumes:
      # Grant access to headscale CLI and socket for VPN operations
      - /usr/bin/headscale:/usr/bin/headscale:ro
      - /var/run/headscale:/var/run/headscale
      # ACL policy file (shared with headscale)
      - /etc/headscale/acl.json:/etc/headscale/acl.json
    ports:
      - "${AUTHORITY_PORT:-8000}:8000"

volumes:
  authority-postgres-data:
```

> **⚠️ Important:** The volume mounts for headscale CLI and ACL file require Headscale to be installed **natively** (not containerized). If you choose the Docker Compose approach for Headscale instead, these mounts are unnecessary and you'll need a `docker exec` wrapper.

---

## Appendix D — Updated `.env.production.example`

**File:** `autonomous/ppl-meta-authority/.env.production.example`

```bash
# Hetzner authority runtime configuration
AUTHORITY_IMAGE=ghcr.io/nickglezakos/ppl-meta-authority:authority-2.24.90
AUTHORITY_PORT=8000

# PostgreSQL container settings
AUTHORITY_POSTGRES_DB=authority_db
AUTHORITY_POSTGRES_USER=authority_user
AUTHORITY_POSTGRES_PASSWORD=change-me

# Authority runtime settings
AUTHORITY_DATABASE_URL=postgresql://authority_user:change-me@authority-postgres:5432/authority_db
AUTHORITY_ADMIN_TOKEN=change-me
AUTHORITY_BOOTSTRAP_ADMIN_ENABLED=false
AUTHORITY_BASE_URL=https://authority.eyenet-vision.com
# Optional legacy override; if unset authority falls back to AUTHORITY_BASE_URL
AUTHORITY_PUBLIC_BASE_URL=

# VPN Mesh Settings (Headscale)
HEADSCALE_API_KEY=change-me
VPN_SUBDOMAIN=vpn.eyenet-vision.com

# Shared platform SMTP settings
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=mailer@example.com
MAIL_PASSWORD=change-me
MAIL_FROM=noreply@example.com
MAIL_FROM_NAME=PPL Meta Authority
MAIL_STARTTLS=true
MAIL_SSL_TLS=false
USE_CREDENTIALS=true
```

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-07 | System | Initial implementation blueprint |