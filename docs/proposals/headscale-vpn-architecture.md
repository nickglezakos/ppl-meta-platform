# Headscale VPN Architecture for EyeNet Platform

## Private Mesh VPN for Local Installations, Matrix Groups, and Client Auto-Discovery

**Status**: Proposal  
**Date**: June 28, 2026  
**Author**: PPL Meta Platform Team

---

## 1. Overview

This proposal defines the architecture for integrating Headscale — a self-hosted, open-source implementation of the Tailscale control plane — as the private VPN layer for EyeNet installations. The VPN provides:

- **Private WireGuard mesh** between all EyeNet installations within a Matrix group
- **Stable addressing** — every device gets a `100.64.x.x` Tailscale IP that never changes regardless of physical network topology
- **Auto-discovery** — all five EyeNet client types auto-discover the platform over VPN without manual IP configuration
- **Zero-login device onboarding** — device clients (cameras, signage players) authenticate via Tailscale identity alone; no EyeNet credentials or manual IP input required
- **Offline resilience** — the local mesh continues operating without internet once peers have exchanged keys
- **Zero external cost** — no Tailscale subscription; Headscale is fully self-hosted on the authority VPS

### 1.1 Development Principle: Local-First, Docker-Later

All implementation is done natively on the development machine first — no Docker during development. Headscale runs as a local binary. All microservices run as local Python processes (`uvicorn`). Tailscale clients run natively on each test device. Docker Compose deployment is introduced later as part of the general platform CI/CD pipeline, after everything is verified working end-to-end.

---

## 2. Architecture

### 2.1 High-Level Topology

```
                        ┌─────────────────────────────────┐
                        │     Authority VPS (Hetzner)      │
                        │                                  │
                        │  ┌────────────────────────────┐  │
                        │  │   ppl-meta-authority        │  │
                        │  │   (existing - port 8010)    │  │
                        │  └────────────────────────────┘  │
                        │                                  │
                        │  ┌────────────────────────────┐  │
                        │  │   headscale                 │  │
                        │  │   (NEW - port 50443)        │  │
                        │  │   • Key distribution        │  │
                        │  │   • Node registration       │  │
                        │  │   • ACL / policy engine     │  │
                        │  │   • DERP relay :3478        │  │
                        │  └────────────────────────────┘  │
                        │                                  │
                        │  ┌────────────────────────────┐  │
                        │  │   authority vpn api          │  │
                        │  │   (NEW - /api/v1/vpn/*)     │  │
                        │  │   • Enroll installation     │  │
                        │  │   • Issue pre-auth keys     │  │
                        │  │   • ACL sync w/ Matrix      │  │
                        │  └────────────────────────────┘  │
                        └──────────────┬──────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │   Internet / WireGuard Peer Mesh     │
                    │   (Tailscale clients form mesh)      │
                    └──────────────────┼──────────────────┘
                                       │
        ┌──────────────┬───────────────┼───────────────┬──────────────┐
        │              │               │               │              │
   ┌────▼─────┐  ┌─────▼────┐  ┌──────▼──────┐  ┌────▼─────┐  ┌────▼─────┐
   │Install A │  │Install B │  │ Install C   │  │ Remote   │  │ Mobile   │
   │  Node A  │  │  Node B  │  │   Node C    │  │ Desktop  │  │  Camera  │
   │          │  │          │  │             │  │  Client  │  │  (Flutter)│
   │ tailscale│  │ tailscale│  │  tailscale  │  │ tailscale│  │ tailscale│
   │  100.64  │  │  100.64  │  │   100.64    │  │  100.64  │  │  100.64  │
   │  .1.2    │  │  .1.3    │  │   .1.4      │  │  .5.10   │  │  .6.20   │
   │          │  │          │  │             │  │          │  │          │
   │ services │  │ services │  │  services   │  │          │  │ camera   │
   │ :8000    │  │ :8000    │  │  :8000      │  │          │  │ stream   │
   │ :8002    │  │ :8002    │  │  :8002      │  │          │  │          │
   │ :8005    │  │          │  │  :8006      │  │          │  │          │
   │ :8006    │  │          │  │             │  │          │  │          │
   └──────────┘  └──────────┘  └─────────────┘  └──────────┘  └──────────┘
        │              │               │
        └──────┬───────┴───────┬───────┘
               │               │
     Matrix Group "Downtown"   │
     (direct WireGuard mesh    │
      between A, B, C on LAN  │
      — survives internet loss)│
```

### 2.2 Why Headscale on Authority VPS

| Concern | Authority VPS | Gateway/Local-Only |
|---|---|---|
| **Coordination** | Single source of truth for all installations, Matrix groups, and remote clients | Each installation isolated — no cross-installation mesh |
| **DERP relay** | Public IP on VPS — reachable from anywhere for NAT traversal | Local gateway behind CGNAT — unreliable |
| **ACL management** | Central ACLs express Matrix group boundaries | Distributed ACLs are fragile |
| **Licence integration** | Authority already validates licences | Gateway has no licence context |
| **Existing relationship** | Every installation already calls authority for activation + health | Gateway not present on all installations |

### 2.3 Offline Resilience

WireGuard is connectionless. Once peers have exchanged keys and endpoint information (via Headscale during initial enrollment), **the data plane continues operating indefinitely without any connection to the Headscale server**. On a local LAN, WireGuard automatically detects direct peer reachability and routes traffic at wire speed without any relay.

| Capability | Without Internet | Reason |
|---|---|---|
| Installation-to-installation traffic (same LAN) | ✅ Yes | WireGuard P2P, keys already exchanged |
| Matrix cross-installation reporting | ✅ Yes | Matrix queries via Tailscale IPs — traffic stays local |
| Service-to-service calls | ✅ Yes | All local, over existing WireGuard tunnels |
| New installation joining mesh | ❌ No | Cannot reach Headscale for key exchange |
| Remote client access (outside LAN) | ❌ No | Cannot reach DERP relay |
| Authority health reporting | ❌ No | Already handled by offline grace period |

### 2.4 Trusted-Device Authentication Model

**Core principle**: After a device or user logs into Tailscale once at the OS level, the EyeNet client apps require **zero login credentials** and **zero manual IP input**. The Tailscale node identity is the cryptographic proof of platform membership.

#### 2.4.1 Device Clients vs Human-User Clients

| Client Type | Tailscale Login Required? | EyeNet Login Required? | Manual IP Required? | How It Authenticates |
|---|---|---|---|---|
| **Mobile Camera** | Yes (once, at OS) | **No** | **No** | Tailscale ACL tag proves Matrix group membership |
| **Edge Camera (RPi)** | Yes (once, at boot) | **No** | **No** | Tailscale ACL tag proves Matrix group membership |
| **Signage Player** | Yes (once, at boot) | **No** | **No** | Tailscale ACL tag proves Matrix group membership |
| **Frontend Dashboard** | Yes (once, at OS) | **Yes** (email+password) | **No** | VPN auto-discovers node → user logs in with EyeNet creds |
| **Mobile Control App** | Yes (once, at OS) | **Yes** (email+password) | **No** | VPN auto-discovers node → user logs in with EyeNet creds |
| **Remote Desktop Client** | Yes (once, at OS) | **Yes** (email+password) | **No** | VPN auto-discovers node → user logs in with EyeNet creds |

#### 2.4.2 Device Trust Chain

```
Headscale ACL Policy
────────────────────
tag:matrix-<uuid> can talk to tag:matrix-<uuid>:*
        │
        ▼
Tailscale node key (cryptographic identity)
        │
        ▼
Device has tag:matrix-<uuid> → device belongs to this Matrix group
        │
        ▼
Discovery service accepts registrations from Tailscale IPs
with matching ACL tags — no JWT required for device-type registrations
        │
        ▼
Device calls platform services via VPN IPs
Services trust Tailscale CGNAT range (100.64.0.0/10) + ACL enforcement
```

#### 2.4.3 Discovery Service: Dual Auth Modes

The discovery service distinguishes between two caller types:

| Caller | Auth Method | Endpoint Behavior |
|---|---|---|
| **Device client** (mobile camera, edge camera, signage) | Tailscale IP + ACL tag validation | `POST /api/v1/devices/register` accepted without JWT. Topology returns device-appropriate service URLs |
| **Human client** (dashboard, mobile control app) | JWT from node login | `GET /api/v1/discovery/topology` returns full topology. Admin operations require role-based JWT claims |

**Device registration authorization**:
```python
# In ppl-meta-discovery: src/services/edge_registry.py
TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")

def is_trusted_device(request: Request) -> bool:
    """A device is trusted if it connects from a Tailscale IP
    and the IP belongs to a peer tagged with the installation's ACL tags."""
    client_ip = request.client.host
    if ipaddress.ip_address(client_ip) not in TAILSCALE_CGNAT:
        return False
    # Verify the Tailscale IP is a known peer with correct ACL tags
    peer = mesh_vpn_service.get_peer_by_ip(client_ip)
    if not peer:
        return False
    # Peer must have at least one tag:matrix-* or tag:installation tag
    return any(tag.startswith("tag:matrix-") or tag == "tag:installation"
               for tag in peer.get("Tags", []))
```

#### 2.4.4 User Flow: From Tailscale Login to App Operation

**DEVICE CLIENT FLOW (zero EyeNet credentials)**:
```
1. User installs Tailscale on device (OS level, one-time)
2. User logs into Tailscale: tailscale up --authkey=<from-authority>
3. Device gets 100.64.x.x IP + tag:matrix-<uuid> ACL tag
4. User opens EyeNet app (mobile camera / signage player)
5. App detects Tailscale IP via local socket
6. App calls discovery service: GET http://<known-node-ip>:8006/api/v1/discovery/topology?vpn=true
7. Discovery returns all platform service URLs
8. App registers itself: POST /api/v1/devices/register { tailscale_ip, device_type, capabilities }
   → Registration accepted because Tailscale IP + ACL tag proves Matrix membership
9. App begins operating — streaming, content display, presence scanning
   → Services accept requests because source IP is in 100.64.0.0/10 + ACL-enforced

   ✅ NO EyeNet login screen
   ✅ NO manual IP entry
   ✅ NO configuration file editing
```

**HUMAN CLIENT FLOW (zero manual IP, requires EyeNet credentials)**:
```
1. User installs Tailscale on device (OS level, one-time)
2. User logs into Tailscale
3. User opens EyeNet dashboard or mobile control app
4. App detects VPN, discovers node: GET /api/v1/discovery/topology?vpn=true
5. App presents EyeNet login screen (email + password)
6. User logs in → node issues JWT
7. App is connected with role-based access

   ✅ NO manual IP entry
   ✅ NO "find my server" wizard
   🔐 Still requires EyeNet login for role-based authorization
```

---

## 3. Development Environment Setup

All development and testing is done **without Docker**. Each service runs as a native process.

### 3.1 Prerequisites

```bash
# macOS (development machine)
brew install headscale
brew install tailscale

# Or download Headscale binary
# https://github.com/juanfont/headscale/releases

# Python dependencies (same as existing services)
pip install fastapi uvicorn httpx psycopg sqlalchemy
```

### 3.2 Local Headscale Configuration

```yaml
# ~/.headscale/config.yaml (dev)
server_url: http://127.0.0.1:8080
listen_addr: 127.0.0.1:8080
metrics_listen_addr: 127.0.0.1:9090
grpc_listen_addr: 127.0.0.1:50443
grpc_allow_insecure: true  # dev only — TLS in production

derp:
  server:
    enabled: true
    region_id: 999
    region_code: "dev"
    region_name: "Dev DERP"
    stun_listen_addr: 0.0.0.0:3478

database:
  type: sqlite
  sqlite:
    path: /Users/nickgklezakos/.headscale/headscale.db

acl_policy_path: /Users/nickgklezakos/.headscale/acl.json
```

```bash
# Start Headscale locally
headscale serve

# In another terminal, create a user namespace
headscale users create eyenet-platform
```

### 3.3 Local Service Startup (No Docker)

Each service runs as a native Python process on a unique port:

```bash
# Terminal 1: Authority
cd autonomous/ppl-meta-authority/src
AUTHORITY_DATABASE_URL=postgresql://... python -m uvicorn main:app --port 8010 --reload

# Terminal 2: Discovery
cd ppl-meta-discovery/src
python -m uvicorn main:app --port 8006 --reload

# Terminal 3: Communications
cd ppl-meta-communications/src
python -m uvicorn main:app --port 8009 --reload

# Terminal 4: Node (Installation A)
cd ppl-meta-node/src
python -m uvicorn main:app --port 8000 --reload

# Terminal 5: Cameras
cd ppl-meta-cameras/src
python -m uvicorn main:app --port 8005 --reload

# Terminal 6: Orchestrator
cd ppl-meta-orchestrator/src
python -m uvicorn main:app --port 8002 --reload

# Terminal 7: Presence
cd ppl-meta-presence/src
python -m uvicorn main:app --port 8007 --reload

# Terminal 8: Media
cd ppl-meta-media/src
python -m uvicorn main:app --port 8001 --reload
```

---

## 4. Implementation Phases

### Phase 1: Headscale Core — Authority VPS Integration (Weeks 1-2)

**Goal**: Headscale deployed on authority VPS. Node auto-enrolls in VPN on startup and gets a stable `100.64.x.x` address.

#### 1.1 Headscale on Authority VPS

**Service**: `autonomous/ppl-meta-authority`

**No Docker approach**: Headscale runs as a systemd service or background process on the VPS.

```bash
# On Hetzner VPS
headscale serve &
```

```yaml
# /etc/headscale/config.yaml (production)
server_url: https://vpn.eyenet-vision.com
listen_addr: 127.0.0.1:8080
grpc_listen_addr: 0.0.0.0:50443
grpc_allow_insecure: false

tls:
  letsencrypt:
    hostname: vpn.eyenet-vision.com

derp:
  server:
    enabled: true
    region_id: 1
    stun_listen_addr: 0.0.0.0:3478

acl_policy_path: /etc/headscale/acl.json

database:
  type: sqlite
  sqlite:
    path: /var/lib/headscale/db.sqlite
```

**Deliverables**:
- Headscale binary installed on VPS
- Systemd unit or startup script for headscale
- Initial ACL policy (restrictive default, expanded per Matrix group)
- Health check: `curl https://vpn.eyenet-vision.com:50443`

#### 1.2 Authority VPN API Endpoints

**Service**: `autonomous/ppl-meta-authority`

**New file**: `src/api/vpn.py`

```python
# Enroll an installation — returns a pre-authorized key scoped to installation tags
POST /api/v1/vpn/enroll-installation
  Request:  { "installation_uuid": "...", "application_key": "lic_..." }
  Response: { "auth_key": "tskey-auth-...", "tailscale_ip_range": "100.64.0.0/10",
              "headscale_server": "https://vpn.eyenet-vision.com:50443",
              "tags": ["tag:installation", "tag:matrix-<uuid>"] }

# List enrolled nodes (admin only)
GET /api/v1/vpn/nodes
  Response: { "nodes": [{ "id": "...", "installation_uuid": "...", "tailscale_ip": "...",
              "online": true, "last_seen": "..." }] }

# Revoke node access
DELETE /api/v1/vpn/nodes/{node_id}

# Get VPN configuration for a Matrix group (ACL status)
GET /api/v1/vpn/matrix-groups/{matrix_id}/acl
```

**Implementation details**:
- `enroll-installation` validates the `application_key` against existing entitlements (reuses existing authority auth)
- Pre-auth keys are scoped with tags matching the installation's Matrix group membership
- Keys have a short TTL (1 hour) — node must enroll before expiry
- ACL synced when `POST /enroll-installation` is called: add new node's tag to the group ACL

**Deliverables**:
- New `src/api/vpn.py` router registered in authority's `main.py`
- `generate_preauth_key()` function calling headscale CLI or gRPC API
- `sync_acl_for_matrix_group()` function updating headscale ACL policy
- Validation tests: `python validate_authority_vpn_enrollment.py`

#### 1.3 Node MeshVPNService

**Service**: `ppl-meta-node`

**New file**: `src/services/mesh_vpn_service.py`

**No Docker approach**: Tailscale runs directly on the host. The service manages it via CLI.

```python
class MeshVPNService:
    """Manages Tailscale client lifecycle on the node."""

    def __init__(self):
        self.tailscale_binary = self._find_tailscale()
        self.tailscale_ip: str | None = None
        self.enrolled: bool = False

    def _find_tailscale(self) -> str:
        """Find tailscale binary on PATH."""
        import shutil
        path = shutil.which("tailscale")
        if not path:
            raise RuntimeError("tailscale not found. Install with: brew install tailscale")
        return path

    async def enroll(self, installation_uuid: str, application_key: str):
        """Enroll this node in the VPN mesh."""
        # 1. Request pre-auth key from authority
        auth_key = await self._fetch_auth_key(installation_uuid, application_key)

        # 2. Bring up tailscale with the auth key
        # tailscale up --authkey=tskey-auth-... --hostname=campus-node-a
        await self._run_tailscale_up(auth_key)

        # 3. Fetch assigned IP
        self.tailscale_ip = await self._get_tailscale_ip()
        self.enrolled = True

    async def get_peers(self, tag_filter: str | None = None) -> list[dict]:
        """List all peers in the mesh, optionally filtered by ACL tag."""
        # tailscale status --json
        result = await self._run_tailscale_status()
        peers = result.get("Peer", {})
        if tag_filter:
            peers = {k: v for k, v in peers.items()
                     if tag_filter in v.get("Tags", [])}
        return list(peers.values())

    async def get_status(self) -> dict:
        """Get VPN connection status."""
        return {
            "enrolled": self.enrolled,
            "tailscale_ip": self.tailscale_ip,
            "online": self.enrolled,
            "headscale_server": settings.AUTHORITY_VPN_SERVER,
        }
```

**Modified files**:
- `ppl-meta-node/src/main.py` — call `mesh_vpn_service.enroll()` during lifespan startup if `authority_licence_features` includes `vpn_enabled`
- `ppl-meta-node/src/models/installation_info.py` — add columns: `tailscale_ip VARCHAR(45)`, `tailscale_enrolled BOOLEAN`
- `ppl-meta-node/src/config.py` — add settings: `AUTHORITY_VPN_SERVER`, `TAILSCALE_AUTH_KEY` (optional env override for dev)

**New endpoint** (on node):
```
GET /api/v1/node/vpn/status
  Response: { "enrolled": true, "tailscale_ip": "100.64.1.2",
              "peers_count": 3, "matrix_peers": [...] }
```

**Deliverables**:
- `mesh_vpn_service.py` that manages tailscale CLI lifecycle
- Node auto-enrolls on first boot with appropriate licence
- Tailscale IP cached in installation_info
- Status endpoint returns VPN state and peers

#### 1.4 Local Dev Verification (Phase 1)

```bash
# 1. Start headscale locally
headscale serve &

# 2. Create user and pre-auth key manually for testing
headscale users create dev
headscale preauthkeys create --user dev --tags tag:installation,tag:matrix-dev

# 3. Start authority
cd autonomous/ppl-meta-authority/src
AUTHORITY_DATABASE_URL=postgresql://... AUTHORITY_VPN_ENABLED=true \
  python -m uvicorn main:app --port 8010 --reload

# 4. Enroll local machine as a test node
tailscale up --login-server http://localhost:8080 --authkey tskey-auth-...

# 5. Verify
tailscale status            # Should show 100.64.x.x IP
tailscale ping 100.64.x.x   # Should succeed
curl http://localhost:8000/api/v1/node/vpn/status  # Should show enrolled
```

---

### Phase 2: Discovery Service VPN Upgrade (Weeks 3-4)

**Goal**: `ppl-meta-discovery` stores and serves Tailscale IPs alongside LAN IPs. Implements dual auth modes for device vs human clients. Multicast continues as LAN fallback.

#### 2.1 VPN-Aware Service Registration

**Service**: `ppl-meta-discovery`

**Modified file**: `src/services/service_registry.py`

Changes:
- `register_service()` — accept optional `tailscale_ip` in `RegistrationRequest.metadata`
- Store `tailscale_ip` alongside host/port in `ServiceInfo`
- `_check_service_health()` — prefer Tailscale IP for health check when service is on a different node (detect by comparing host IPs)

**New fields in models** (`src/models/service_models.py`):
```python
class ServiceInfo:
    tailscale_ip: str | None = None  # NEW
    tailscale_port: int | None = None  # NEW (same as port, but explicit for VPN)
```

#### 2.2 VPN-Aware Edge Device Registration with Trusted-Device Auth

**Service**: `ppl-meta-discovery`

**Modified file**: `src/services/edge_registry.py`

Changes:
- `register_device()` — accept `tailscale_ip` in metadata; implement `is_trusted_device()` check based on Tailscale CGNAT range + ACL tag validation (see Section 2.4.3)
- Store Tailscale IP alongside LAN IP
- `get_mobile_cameras()`, `get_raspberry_pi_devices()` — include `tailscale_ip` in response
- **Device registration no longer requires JWT** when caller's Tailscale IP has a matching ACL tag

```python
TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")

def is_trusted_device(request: Request) -> bool:
    client_ip = request.client.host
    if ipaddress.ip_address(client_ip) not in TAILSCALE_CGNAT:
        return False
    peer = mesh_vpn_service.get_peer_by_ip(client_ip)
    if not peer:
        return False
    return any(tag.startswith("tag:matrix-") or tag == "tag:installation"
               for tag in peer.get("Tags", []))
```

#### 2.3 Host Resolution with VPN Preference

**Service**: `ppl-meta-discovery`

**Modified file**: `src/main.py`

Changes to `resolve_service_hosts()`:
```python
def resolve_service_hosts(services_list, prefer_vpn: bool = False):
    machine_ip = get_machine_ip()
    tailscale_ip = get_tailscale_ip()  # NEW: from local tailscale status

    for service in services_list.services:
        if prefer_vpn and service.tailscale_ip:
            # Use Tailscale IP for VPN-connected clients
            service.host = service.tailscale_ip
        elif service.host == "0.0.0.0":
            # Use Tailscale IP as primary, machine IP as fallback
            service.host = tailscale_ip or machine_ip
```

**New endpoint**:
```
GET /api/v1/discovery/topology?vpn=true
  Returns topology with Tailscale IPs preferred for all services/devices
  Adds "preferred_network": "tailscale" to response
```

#### 2.4 Multicast Announcement Enrichment

**Service**: `ppl-meta-discovery`

**Modified file**: `src/services/multicast_announcer.py`

Changes to `_create_announcement_message()`:
```python
message = {
    "type": "discovery_service_announcement",
    "service": "ppl-meta-discovery",
    "tailscale_ips": [self._tailscale_ip],  # NEW
    "tailscale_network": "100.64.0.0/10",   # NEW
    # ... existing fields
}
```

This lets VPN-connected clients discover the discovery service without multicast (which doesn't propagate over WireGuard).

#### 2.5 All Backend Services Register with Tailscale IP

Each service's startup (`main.py` lifespan) updates its discovery registration:

| Service | Port | Modification |
|---|---|---|
| `ppl-meta-node` | 8000 | Already handled by MeshVPNService. Registers tailscale_ip |
| `ppl-meta-media` | 8001 | New: detect tailscale IP, include in registration metadata |
| `ppl-meta-orchestrator` | 8002 | New: detect tailscale IP, include in registration metadata |
| `ppl-meta-cameras` | 8005 | New: detect tailscale IP, include in registration metadata |
| `ppl-meta-presence` | 8007 | New: detect tailscale IP, include in registration metadata |
| `ppl-meta-communications` | 8009 | See Phase 3 |
| `ppl-meta-vision` | 8003 | New: detect tailscale IP, include in registration metadata |

**Common helper** — create `shared/networking/tailscale_utils.py`:
```python
import subprocess, json

def get_tailscale_ip() -> str | None:
    """Get the local machine's Tailscale IP."""
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5
        )
        data = json.loads(result.stdout)
        return data.get("Self", {}).get("TailscaleIPs", [None])[0]
    except Exception:
        return None

def get_tailscale_peer_ips(tag: str | None = None) -> list[str]:
    """Get Tailscale IPs of peers, optionally filtered by tag."""
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True, text=True, timeout=5
        )
        data = json.loads(result.stdout)
        peers = data.get("Peer", {})
        ips = []
        for peer_id, peer_data in peers.items():
            if tag and tag not in peer_data.get("Tags", []):
                continue
            for ip in peer_data.get("TailscaleIPs", []):
                ips.append(ip)
        return ips
    except Exception:
        return []
```

**Deliverables**:
- All backend services register with both LAN IP and Tailscale IP
- Discovery topology endpoint supports `?vpn=true`
- Device registration accepts Tailscale-identified callers without JWT (trusted-device model)
- Multicast announcements include Tailscale IP
- `shared/networking/tailscale_utils.py` for reuse across all services

---

### Phase 3: Communications Service VPN Upgrade (Weeks 5-6)

**Goal**: `ppl-meta-communications` is reachable over VPN. Audit logs show VPN source addresses. Notifications route over VPN.

#### 3.1 Tailscale IP Registration

**Service**: `ppl-meta-communications`

**Modified file**: `src/main.py` (lifespan)

Changes:
- Detect Tailscale IP using `shared/networking/tailscale_utils.py`
- Include `tailscale_ip` in discovery service registration metadata
- Log the detected IP on startup

#### 3.2 VPN-Aware Notification Routing

**Service**: `ppl-meta-communications`

**Modified file**: `src/routes/notification.py`

Changes:
- Add `device_tailscale_ip` to notification request schema
- When sending push notifications to a device only reachable via VPN, prefer Tailscale IP
- New field in `NotificationRequest`:
```python
class NotificationRequest(BaseModel):
    recipient: str
    message: str
    device_tailscale_ip: str | None = None  # NEW
    prefer_vpn: bool = False                 # NEW
```

#### 3.3 VPN-Aware Webhook Targets

**Service**: `ppl-meta-communications`

**Modified file**: `src/routes/webhook.py`

Changes:
- Accept webhook URLs with Tailscale IPs (e.g., `http://100.64.1.5:8000/api/v1/callback`)
- Health check for webhook targets validates reachability over VPN when URL uses `100.64.x.x`

#### 3.4 Audit Log Enrichment

**Service**: `ppl-meta-communications`

**Modified file**: `src/routes/audit.py`

Changes:
- Detect if request source IP is in `100.64.0.0/10` range
- Add `source_network: "tailscale_vpn"` to audit entries
- Store `source_tailscale_ip` alongside `source_ip`

```python
TAILSCALE_CGNAT = ipaddress.ip_network("100.64.0.0/10")

def classify_request_network(request: Request) -> str:
    client_ip = request.client.host if request.client else ""
    try:
        if ipaddress.ip_address(client_ip) in TAILSCALE_CGNAT:
            return "tailscale_vpn"
    except ValueError:
        pass
    return "local"
```

#### 3.5 VPN Status Endpoint

**Service**: `ppl-meta-communications`

**New endpoint**:
```
GET /api/v1/vpn/status
  Response: {
    "tailscale_ip": "100.64.1.5",
    "connected_peers": 3,
    "derp_relay": "connected",
    "mesh_online": true
  }
```

**Deliverables**:
- Communications registers with Tailscale IP
- Notifications route to VPN-only devices
- Webhooks accept VPN URLs
- Audit logs differentiate VPN vs LAN traffic
- VPN status endpoint

---

### Phase 4: Edge Camera + WiFi/IP Camera Zero-Login Auto-Enrollment (Weeks 7-8)

**Goal**: `ppl-meta-edge-camera` (Raspberry Pi) and `ppl-meta-cameras` (WiFi/IP camera manager) auto-enroll in VPN and auto-discover the platform **with zero EyeNet credentials and zero manual IP configuration**. The Tailscale identity is the sole authentication.

#### 4.1 Edge Camera Zero-Login VPN Enrollment

**Service**: `ppl-meta-edge-camera`

**Prerequisite on RPi**: Install Tailscale
```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

**New file**: `src/services/vpn_service.py`

```python
class EdgeCameraVPNService:
    """VPN enrollment for edge cameras — Tailscale identity only, no EyeNet creds."""

    def __init__(self, config):
        self.config = config
        self.tailscale_ip = None

    async def enroll(self, authority_url: str, application_key: str):
        """Enroll in VPN mesh. The auth key from authority cryptographically
        binds this device to its Matrix group — no EyeNet login needed."""
        # 1. Fetch pre-auth key from authority (validated by application_key)
        auth_key = await self._fetch_auth_key(authority_url, application_key)
        # 2. tailscale up --authkey=<key> --hostname=edge-<location>
        await self._run_tailscale_up(auth_key)
        # 3. Store tailscale_ip for streaming and registration
        self.tailscale_ip = self._get_tailscale_ip()
```

**Modified file**: `config/default.yaml`

```yaml
# BEFORE (hardcoded LAN IPs)
platform:
  cameras_url: http://192.168.1.75/cameras
  discovery_url: http://192.168.1.75/discovery

# AFTER (zero-config — auto-discovered via VPN)
platform:
  discovery_url: auto           # Discovered from topology
  cameras_url: auto             # Discovered from topology
  vpn:
    enabled: true
    authority_url: https://vpn.eyenet-vision.com
    application_key: "${EYENET_APPLICATION_KEY}"  # from env — single provisioning step
    # No EyeNet email, no EyeNet password, no manual IPs
```

**Zero-login startup flow**:
1. Boot → read `application_key` from env (the **only** provisioning input)
2. Enroll in VPN via authority: `POST /api/v1/vpn/enroll-installation` with application_key
3. Device gets `100.64.x.x` IP + `tag:matrix-<uuid>` ACL tag
4. Call discovery service via VPN: `GET http://<primary-node-ip>:8006/api/v1/discovery/topology?vpn=true`
5. Extract `cameras_url`, `media_url`, `discovery_url` from topology response
6. Register self with discovery: `POST /api/v1/devices/register`
   → **Accepted without JWT** — Tailscale IP + ACL tag proves Matrix membership
7. Begin streaming to the discovered cameras service

```
User provisioning: 1 step (set EYENET_APPLICATION_KEY env var)
After that: ZERO login screens, ZERO manual IPs, ZERO config files
```

#### 4.2 WiFi/IP Camera Manager VPN Integration

**Service**: `ppl-meta-cameras`

**Modified files**:
- `src/main.py` — detect Tailscale IP, include in discovery registration (trusted-device auth)
- `src/api/cameras.py` — new field `tailscale_reachable: bool` in camera registration

**Camera registration flow**:
```python
# When registering a new WiFi/IP camera
POST /api/v1/cameras/register
{
    "name": "Lobby Camera 1",
    "ip": "192.168.1.100",         # LAN IP
    "tailscale_reachable": false,   # Camera itself has no tailscale
    "proxy_via": "manager"          # Manager proxies the stream
}
```

For cameras that can't run Tailscale directly:
- Camera manager advertises them under its own Tailscale IP
- Stream URL: `http://<manager-tailscale-ip>:8005/cameras/<id>/stream`
- Manager proxies MJPEG/RTSP internally
- Client apps receive the manager's Tailscale IP via discovery — they never need the camera's LAN IP

**New endpoint**:
```
GET /api/v1/discovery/cameras
  Returns all cameras (edge, WiFi, IP) with VPN-preferred URLs:
  [
    { "id": "edge-001", "type": "edge", "tailscale_ip": "100.64.1.20",
      "stream_url": "http://100.64.1.20:9001/stream",
      "auth_mode": "tailscale_trusted" },
    { "id": "wifi-001", "type": "wifi", "lan_ip": "192.168.1.100",
      "tailscale_ip": "100.64.1.5", "stream_url": "http://100.64.1.5:8005/cameras/wifi-001/stream",
      "proxied": true, "auth_mode": "tailscale_trusted" }
  ]
```

**Deliverables**:
- Edge camera auto-enrolls in VPN and auto-discovers platform with zero EyeNet credentials
- WiFi/IP camera manager enrolls in VPN, proxies non-VPN cameras
- No hardcoded IPs in edge camera config
- Discovery endpoint exposes all cameras with VPN-preferred URLs
- Trusted-device auth allows cameras to register without JWT

---

### Phase 5: Mobile Camera + Signage Player Zero-Login Auto-Discovery (Weeks 9-10)

**Goal**: `ppl_meta_mobile_camera` (Flutter) and `ppl-meta-signage-simple-player` (Flutter) auto-discover the platform over VPN with multicast/LAN fallback. **Device clients require zero EyeNet credentials** — Tailscale identity is the sole auth. Human-user clients auto-discover the node URL but still require EyeNet login for role-based access.

#### 5.1 Mobile Camera Zero-Login VPN Integration

**Service**: `ppl_meta_mobile_camera`

**Tailscale on Flutter**: Use platform channel to invoke native Tailscale client.
- **iOS/macOS**: Tailscale app exposes a VPN configuration that can be enrolled programmatically
- **Android**: Tailscale Android app or manual WireGuard configuration
- **Development shortcut**: For dev testing, run `tailscale up --authkey=...` on the host machine; the Flutter app reads the local Tailscale IP via a platform channel or the device's network interface

**Modified files**:

`lib/services/unified_discovery_service.dart`:
```dart
class UnifiedDiscoveryService {
  // Discovery priority:
  // 1. VPN-direct: call known node Tailscale IP (auto-discovered, zero config)
  // 2. Multicast: existing mDNS/multicast discovery (LAN fallback)
  // 3. Manual entry: last resort

  Future<DiscoveryResult> discover() async {
    // Try VPN first — this is the primary path for all clients
    if (await _isVpnConnected()) {
      String vpnNodeIp = await _getMatrixNodeIp();
      try {
        var result = await http.get(
          Uri.parse('http://$vpnNodeIp:8006/api/v1/discovery/topology?vpn=true'),
        );
        if (result.statusCode == 200) {
          return DiscoveryResult.fromVpn(result.body);
        }
      } catch (_) { /* fall through to multicast */ }
    }

    // Try multicast (LAN fallback)
    try {
      return await multicastDiscovery.discover();
    } catch (_) { /* fall through to manual */ }

    // Manual entry (last resort)
    return await manualDiscovery.discover();
  }
}
```

`lib/services/auto_camera_registration_service.dart`:
- Include `tailscale_ip` in device registration metadata
- Register as `device_type: mobile_camera`
- **Registration uses trusted-device auth** — Tailscale IP + ACL tag, no JWT needed
- No EyeNet login screen presented to the user for device-mode operation

`lib/services/mobile_streaming_service.dart`:
- Stream URL uses Tailscale IP when VPN is connected (stable, routable)
- Falls back to LAN IP when on local network (multicast-discovered)
- Service accepts the stream because source IP is in `100.64.0.0/10` (trusted)

#### 5.2 Signage Player Zero-Login VPN Integration

**Service**: `ppl-meta-signage-simple-player`

**Tailscale on Flutter (desktop/embedded)**:
- Linux (RPi): Install `tailscale` via apt, enroll during provisioning
- Windows/macOS: Install Tailscale via package manager, enroll on first boot
- Android: Use platform channel or manual WireGuard config

**Modified files**:

`lib/services/discovery_service.dart` (or equivalent):
```dart
// Same VPN-first, multicast-second, manual-third pattern
class SignageDiscoveryService {
  Future<PlatformServices> discover() async {
    // 1. Check for VPN — primary path, zero config
    String? vpnIp = await VpnService.getTailscaleIp();
    if (vpnIp != null) {
      var topology = await _fetchTopology('http://$vpnIp:8006');
      if (topology != null) return topology;
    }
    // 2. Multicast fallback (same LAN)
    // 3. Manual entry fallback (last resort)
  }
}
```

**Content fetching**:
- When on VPN, content URLs use Tailscale IP of media service: `http://100.64.x.x:8001/media/...`
- When on LAN, use multicast-discovered LAN IP
- Signage player registers with discovery: `POST /api/v1/devices/register` as `device_type: signage_player`
- **Registration uses trusted-device auth** — no EyeNet login

#### 5.3 Shared Discovery Pattern Across All Clients

Both Flutter apps and all device clients share the same discovery pattern:

```
Discovery Priority:
  1. VPN-direct HTTP to primary node's Tailscale IP :8006  ← zero config, auto-discovered
  2. Multicast DNS-SD / UDP multicast                       ← LAN fallback
  3. Manual base URL entry                                  ← last resort (legacy/debug)
```

Client type determines auth mode:

| Client | Discovery | Auth Mode |
|---|---|---|
| Mobile Camera | VPN → topology → register as device | Tailscale identity only |
| Edge Camera | VPN → topology → register as device | Tailscale identity only |
| Signage Player | VPN → topology → register as device | Tailscale identity only |
| Dashboard | VPN → topology → present login | EyeNet JWT |
| Mobile Control App | VPN → topology → present login | EyeNet JWT |

**Deliverables**:
- Mobile camera auto-discovers platform via VPN with **zero EyeNet credentials** — streams over stable Tailscale IP
- Signage player auto-discovers platform via VPN with **zero EyeNet credentials** — fetches content over VPN
- Both register with discovery service as trusted devices (Tailscale auth, no JWT)
- Human-user clients (dashboard, control app) auto-discover node URL but still require EyeNet login
- Multicast fallback works for same-LAN scenarios
- Manual entry remains as last resort for debugging

---

### Phase 6: Cross-Installation (Matrix) Readiness + Hardening (Weeks 11-12)

**Goal**: VPN mesh supports Matrix groups across installations. ACLs enforce group boundaries. Trusted-device model extends across installations. Production readiness.

#### 6.1 Headscale ACL Sync with Matrix Groups

**Service**: `autonomous/ppl-meta-authority`

**New file**: `src/services/vpn_acl_service.py`

```python
class VpnACLService:
    """Syncs Headscale ACLs with Matrix group membership."""

    def sync_matrix_group_acls(self, matrix_group_id: str, member_tags: list[str]):
        """Update ACL to allow mesh between all members of a Matrix group."""
        # Generate ACL: members with tag:matrix-<uuid> can talk to each other
        acl_entry = {
            "action": "accept",
            "src": [f"tag:matrix-{matrix_group_id}"],
            "dst": [f"tag:matrix-{matrix_group_id}:*"],
        }
        # Update headscale ACL policy file or gRPC call
        self._update_headscale_acl(matrix_group_id, acl_entry)

    def add_installation_to_matrix_acls(self, matrix_group_id: str, installation_node_id: str):
        """Add a new installation to existing Matrix group ACL."""
        # Tag the node: headscale nodes tag --tags=tag:matrix-<uuid> <node-id>
        ...

    def remove_installation_from_matrix_acls(self, matrix_group_id: str, installation_node_id: str):
        """Remove an installation from Matrix group ACL."""
        ...
```

**Trigger points**:
- `POST /api/v1/vpn/enroll-installation` → if installation belongs to a Matrix group, sync ACL
- Matrix group membership change (future `ppl-meta-matrix` service) → call `POST /api/v1/vpn/matrix-groups/{id}/sync-acl`
- **ACL tags are the foundation of trusted-device auth** — a device enrolled with `tag:matrix-<uuid>` can communicate with all peer devices in the same Matrix group without any additional credentials

#### 6.2 Node Peer Discovery for Matrix

**Service**: `ppl-meta-node`

**Modified file**: `src/services/mesh_vpn_service.py`

```python
async def get_matrix_peers(self, matrix_group_id: str) -> list[dict]:
    """Get all VPN peers in the same Matrix group."""
    tag = f"tag:matrix-{matrix_group_id}"
    return await self.get_peers(tag_filter=tag)

async def get_matrix_peer_service_urls(self, matrix_group_id: str, service_port: int) -> list[str]:
    """Get service URLs for all peers in the Matrix group."""
    peers = await self.get_matrix_peers(matrix_group_id)
    return [f"http://{p['TailscaleIPs'][0]}:{service_port}" for p in peers]
```

This will be consumed by `ppl-meta-matrix` (when built later) to discover all member installations' service endpoints via their VPN IPs.

#### 6.3 Production Hardening

**All services**:

```bash
# Firewall: restrict inter-service traffic to Tailscale IP range only
# On each node:
sudo ufw allow from 100.64.0.0/10 to any port 8000:8010 proto tcp
sudo ufw deny 8000:8010/tcp  # Block non-VPN access to service ports

# Or on macOS dev:
sudo pfctl -f /etc/pf.conf  # Configure packet filter
```

**Headscale hardening**:
```yaml
# /etc/headscale/config.yaml (production)
grpc_allow_insecure: false
tls_letsencrypt_hostname: vpn.eyenet-vision.com
tls_letsencrypt_cache_dir: /var/lib/headscale/cache

# Restrict ACL to deny all by default
acl_policy:
  hosts:
    "tag:installation": []
  acls:
    # Only Matrix group members can communicate (this IS the trusted-device boundary)
    - action: accept
      src: ["tag:matrix-*"]
      dst: ["tag:matrix-*:*"]
    # Explicit denies for everything else
    - action: deny
      src: ["*"]
      dst: ["*:*"]
```

**DERP relay monitoring**:
```bash
# Health check script
tailscale status --json | jq '.Peer | to_entries | map(select(.value.Relay == "derp")) | length'
# Alert if DERP relay latency > 200ms
```

**Backup**:
```bash
# Daily backup of headscale database
cp /var/lib/headscale/db.sqlite /backups/headscale_$(date +%Y%m%d).db
```

#### 6.4 Integration Validation Checklist

| Test | Expected Result |
|---|---|
| Two installations on same LAN, internet up | Direct WireGuard P2P, <1ms latency |
| Two installations on same LAN, internet down | Mesh still works (pre-shared keys) |
| Mobile camera on cellular, connecting to installation | Routes through DERP relay, then to installation. Zero EyeNet credentials needed |
| Edge camera booted with only EYENET_APPLICATION_KEY | Auto-enrolls in VPN, auto-discovers platform, begins streaming — no login screen |
| Signage player booted with only EYENET_APPLICATION_KEY | Auto-enrolls in VPN, auto-discovers platform, begins content display — no login screen |
| New installation joins existing Matrix group | ACL updated, new node visible in peer list. Existing devices can reach new installation |
| Installation revoked from Matrix group | ACL updated, node removed from peer list. Trusted-device auth denies access |
| Headscale server restarts | Existing peers stay connected (data plane unaffected). Trusted devices continue operating |
| Node restarts | Re-enrolls automatically, gets same IP (deterministic from node key). Trusted devices re-establish connectivity |

**Deliverables**:
- ACLs synced with Matrix group membership — ACL tags form the trusted-device boundary
- Node exposes peer discovery API for Matrix service consumption
- Firewall rules restrict service access to VPN range
- Production Headscale config with TLS
- Backup and monitoring scripts
- Full integration validation including zero-login device flows

---

## 5. Service Upgrade Summary

| Service | Key Changes | New Files |
|---|---|---|
| **ppl-meta-authority** | Headscale binary, VPN API (`api/vpn.py`), ACL sync service | `src/api/vpn.py`, `src/services/vpn_acl_service.py` |
| **ppl-meta-node** | MeshVPNService, Tailscale lifecycle, peer discovery | `src/services/mesh_vpn_service.py` |
| **ppl-meta-discovery** | Tailscale IP in registry, `?vpn=true` topology, trusted-device auth, enriched multicast | Modified: `service_registry.py`, `edge_registry.py`, `multicast_announcer.py`, `main.py` |
| **ppl-meta-communications** | Tailscale IP registration, VPN audit enrichment, VPN status endpoint | Modified: `main.py`, `audit.py`, `notification.py` |
| **ppl-meta-edge-camera** | Zero-login VPN enrollment, auto-discovery, dynamic config | `src/services/vpn_service.py`, Modified: `config/default.yaml` |
| **ppl-meta-cameras** | Tailscale IP registration, camera proxy, VPN-preferring URLs | Modified: `main.py`, `cameras.py` |
| **ppl_meta_mobile_camera** | VPN-first discovery, zero-login Tailscale streaming, trusted-device auto-registration | Modified: `unified_discovery_service.dart`, `auto_camera_registration_service.dart`, `mobile_streaming_service.dart` |
| **ppl-meta-signage-simple-player** | Zero-login VPN enrollment, auto-discovery, VPN content fetching | New: `vpn_service.dart`, Modified: discovery + content services |
| **ppl-meta-media** | Tailscale IP in discovery registration | Modified: `main.py` (lifespan) |
| **ppl-meta-orchestrator** | Tailscale IP in discovery registration | Modified: `main.py` (lifespan) |
| **ppl-meta-presence** | Tailscale IP in discovery registration | Modified: `main.py` (lifespan) |
| **ppl-meta-vision** | Tailscale IP in discovery registration | Modified: `main.py` (lifespan) |
| **shared** | `tailscale_utils.py` — reusable IP detection + peer lookup | `shared/networking/tailscale_utils.py` |

---

## 6. Development vs Production

| Aspect | Development (Phase 1-6) | Production (CI/CD) |
|---|---|---|
| **Headscale** | Local binary: `headscale serve` | Systemd service or Docker container on VPS |
| **Tailscale clients** | Native OS install: `brew install tailscale` / `apt install tailscale` | Docker sidecar or host-level install via provisioning script |
| **Microservices** | Direct Python: `python -m uvicorn main:app --port XXXX --reload` | Docker Compose with per-service containers |
| **Discovery** | Multicast works on dev LAN | Multicast + VPN-direct hybrid |
| **TLS** | Not required (localhost dev) | Let's Encrypt via Headscale config |
| **Firewall** | Not applied in dev | UFW / iptables restricting to `100.64.0.0/10` |
| **Auth keys** | Manual: `headscale preauthkeys create` for testing | Authority API: `POST /api/v1/vpn/enroll-installation` |
| **Device auth** | Tailscale CGNAT check + peer tag validation | Tailscale CGNAT check + ACL-enforced peer tags |

---

## 7. Key Design Decisions

1. **Headscale on authority VPS, not gateway**: Authority is already the single coordination point every installation talks to. Headscale's control plane belongs there. The data plane (WireGuard) operates peer-to-peer and does not depend on the VPS after enrollment.

2. **Every installation runs Tailscale, even single-installation**: Uniform architecture. A "local-only" installation still has a Tailscale IP — it just has no peers. This avoids code branches and ensures Matrix multi-installation upgrade is seamless.

3. **VPN-first discovery, multicast second**: VPN-direct HTTP call to the discovery service's Tailscale IP is the primary discovery mechanism. Multicast is a same-LAN fallback. This ensures remote and mobile clients can discover the platform.

4. **Dev without Docker first**: All services run as native Python processes during development. Tailscale runs natively on the host. Docker is introduced in CI/CD after everything works. This keeps the dev loop fast (hot reload, no rebuilds) and avoids debugging container networking alongside VPN networking.

5. **Offline resilience is inherent**: WireGuard is connectionless. Peers that have exchanged keys (during enrollment) continue communicating indefinitely without internet. Headscale is only needed for new peer introduction, key rotation, and DERP relay (for non-LAN peers).

6. **Headscale first, Matrix second**: Building Headscale first provides stable `100.64.x.x` addressing for all services. When Matrix is built, it stores Tailscale IPs as `node_url` from day one — no migration from LAN IPs needed.

7. **Tailscale identity = trusted-device auth**: Device clients (cameras, signage) authenticate via their Tailscale node key and ACL tags — not EyeNet credentials. This enables zero-login onboarding: the single provisioning step is the Tailscale auth key. The discovery service validates Tailscale IP + ACL tags to accept device registrations without JWT. Human-user clients still require EyeNet login for role-based authorization.

---

## 8. Prerequisite: Headscale Setup on Dev Machine

Before Phase 1 development begins:

```bash
# 1. Install Headscale
brew install headscale

# 2. Configure
mkdir -p ~/.headscale
cat > ~/.headscale/config.yaml << 'EOF'
server_url: http://127.0.0.1:8080
listen_addr: 127.0.0.1:8080
grpc_listen_addr: 127.0.0.1:50443
grpc_allow_insecure: true
derp:
  server:
    enabled: true
    region_id: 999
    stun_listen_addr: 0.0.0.0:3478
database:
  type: sqlite
  sqlite:
    path: ~/.headscale/headscale.db
acl_policy_path: ~/.headscale/acl.json
EOF

echo '{"hosts":{},"acls":[{"action":"accept","src":["*"],"dst":["*:*"]}]}' > ~/.headscale/acl.json

# 3. Start
headscale serve &
headscale users create dev

# 4. Install Tailscale client
# macOS: already installed via Homebrew (tailscale package)
# Or: brew install tailscale

# 5. Create test pre-auth key
headscale preauthkeys create --user dev --tags tag:installation,tag:matrix-dev

# 6. Enroll local machine
tailscale up --login-server http://localhost:8080 --authkey <key-from-step-5>

# 7. Verify
tailscale status
tailscale ping <tailscale-ip>
```

---

## 10. Cybersecurity Hardening Plan

This section identifies cybersecurity gaps discovered in the existing codebase audit and defines concrete remediation steps integrated into the implementation phases. Each gap must be resolved before its associated phase is considered complete.

### 10.1 Audit Findings Summary

#### 🔴 CRITICAL — Hardcoded Secrets in Source Code

| # | Service | File | Issue |
|---|---|---|---|
| C1 | `ppl-meta-node` | `src/main.py:545-565` | Hardcoded test passwords `"Kodikos@23"` in `create_user()` calls — allows default-credential access |
| C2 | `ppl-meta-orchestrator` | `workflows_registry_endpoints.py:15`, `face_detection_endpoints.py:13` | `INTERNAL_SERVICE_TOKEN` hardcoded to `"ppl-meta-internal-service-secret-key-change-in-production"` — same value across multiple files |
| C3 | `ppl-meta-communications` | `src/config.py` | `SECRET_KEY` defaults to `"change-this-secret-key"` |
| C4 | `ppl-meta-node` | `src/config.py` | `SECRET_KEY` defaults to `"default-secret-key-change-in-production"` with a warning log that is easily ignored |
| C5 | `ppl-meta-edge-camera` | `management_api.py:47-49` | Token validation bypassed — logs `"Token validation not fully implemented - accepting token"` and returns ANY Bearer token as valid |

#### 🔴 CRITICAL — Inter-Service Authentication Weaknesses

| # | Service | Issue |
|---|---|---|
| C6 | `ppl-meta-node` → all | Inter-service calls use `X-Service-Secret` header matched with `if token != settings.SERVICE_SECRET` — plain string comparison, no expiration, no rotation, no cryptographic signature |
| C7 | `ppl-meta-orchestrator` → all | `INTERNAL_SERVICE_TOKEN` validated with `if token == INTERNAL_SERVICE_TOKEN` — identical to C6 |
| C8 | All services | JWT uses HS256 (symmetric HMAC). A single compromised `SECRET_KEY` allows an attacker to forge valid JWTs for ANY user on ANY service across the entire platform |

#### 🟠 HIGH — Sensitive Data Exposure

| # | Service | Issue |
|---|---|---|
| H1 | `ppl-meta-node` | `api/v1/users.py` — password reset flow sends new password in **plain text** via email: `"Your new password is: <strong>{body.new_password}</strong>"` |
| H2 | `ppl-meta-communications` | `mail_password` stored as plain text in `email_settings` table despite code comment `# Encrypted in production` |
| H3 | `ppl-meta-communications` | Webhook `auth_token` and `auth_password` stored as plain text in `webhook_config` table |
| H4 | `ppl_meta_mobile_camera` | JWT tokens stored in unencrypted `SharedPreferences` (`token_manager.dart`, `enhanced_authentication_service.dart`) — accessible to any Flutter plugin or debugging tool with app sandbox access |

#### 🟠 HIGH — Token Handling

| # | Service | Issue |
|---|---|---|
| H5 | All services | No JWT expiration enforcement in inter-service calls — tokens checked for presence, not expiry |
| H6 | `ppl_meta_mobile_camera` | No token refresh flow — token stored indefinitely in `SharedPreferences`, no refresh token, no revocation endpoint called on logout |
| H7 | `ppl_meta_mobile_camera` | Five parallel auth implementations (`EnhancedAuthenticationService`, `AutoAuthenticationService`, `DiscoveryBasedAuthenticationService`, `EnhancedAutoAuthenticationService`, `HybridServiceDiscovery`) — confusing security surface, multiple token storage locations |

#### 🟡 MEDIUM — Input Validation & API Exposure

| # | Service | Issue |
|---|---|---|
| M1 | `ppl-meta-edge-camera` | Management API accepts all requests when `api_key` is not configured — dev mode present in production code path |
| M2 | `ppl-meta-orchestrator` | `get_auth_token()` dependency returns any token without verification when it doesn't match internal token — line `return token` with no validation |
| M3 | `ppl-meta-communications` | No rate limiting on email/webhook endpoints — potential for abuse (email flooding, webhook spam) |

#### 🟡 MEDIUM — Headscale/VPN-Specific Gaps (New Architecture)

| # | Service | Issue |
|---|---|---|
| M4 | `ppl-meta-discovery` | `is_trusted_device()` proposed with CGNAT IP range check only — MUST also validate ACL tags, or any Tailscale node on the network (even unauthorized) could register as a trusted device |
| M5 | `autonomous/ppl-meta-authority` | Headscale admin API — dev config uses `grpc_allow_insecure: true` and no API key. Production MUST enforce API key authentication |
| M6 | All Flutter clients | No certificate/TLS pinning — susceptible to MITM attacks on the Headscale server or node API endpoints |
| M7 | `autonomous/ppl-meta-authority` | Pre-auth key exposure risk — if a key leaks, attacker joins mesh with `100.64.x.x` IP + system ACL tags. Keys need scope restriction + short TTL |

---

### 10.2 Remediation Plan — Integrated Into Implementation Phases

#### Phase 1 Hardening (Headscale Core + Authority)

| ID | Remediation | Service | Validation |
|---|---|---|---|
| **M5** | Headscale production config MUST set `grpc_allow_insecure: false` and require API key. Headscale API key stored as environment variable `HEADSCALE_API_KEY`, never in source | `ppl-meta-authority` | `curl https://vpn.eyenet-vision.com:50443` without API key returns 401 |
| **M7** | Pre-auth keys issued with 1-hour TTL maximum. Keys scoped to specific user + tags only. `POST /api/v1/vpn/enroll-installation` logs every key issuance to audit trail | `ppl-meta-authority` | Test: expired key rejected. Test: key with wrong tags rejected |
| **C3/C4** | Remove all default `SECRET_KEY` values. Enforce startup failure if `SECRET_KEY` env var is not set or is a known default. Add startup check: `if SECRET_KEY in KNOWN_DEFAULTS: raise SystemExit("Production SECRET_KEY required")` | `ppl-meta-node`, `ppl-meta-communications` | Service refuses to start without unique `SECRET_KEY` |
| **C8** | Plan RS256/ES256 migration path. Symmetric HS256 acceptable for initial phases IF `SECRET_KEY` is unique per deployment AND rotated. Add `JWT_ALGORITHM` to config with `HS256` default, documented migration path to `RS256` | All services | Documented and configurable algorithm |

#### Phase 2 Hardening (Discovery Service)

| ID | Remediation | Service | Validation |
|---|---|---|---|
| **M4** | `is_trusted_device()` MUST validate BOTH: (1) source IP in `100.64.0.0/10` range AND (2) peer has `tag:matrix-*` or `tag:installation` ACL tag. CGNAT range alone is NOT sufficient | `ppl-meta-discovery` | Test: device with Tailscale IP but no ACL tag → registration rejected 403 |
| **C6** | Replace `X-Service-Secret` plain text header with short-lived JWT (15-minute TTL) signed with service-specific key. Each service pair gets a unique shared secret | `ppl-meta-node`, `ppl-meta-discovery` | Test: expired JWT rejected. Test: wrong audience JWT rejected |
| **C2** | Remove all hardcoded `INTERNAL_SERVICE_TOKEN` values. Replace with env-var `INTERNAL_SERVICE_TOKEN` that must be set per deployment. Add startup validation: refuse to start if value equals known default | `ppl-meta-orchestrator` | Service refuses to start with default token value |

#### Phase 3 Hardening (Communications Service)

| ID | Remediation | Service | Validation |
|---|---|---|---|
| **H2** | Encrypt `mail_password` at rest using AES-256-GCM with a key derived from `SECRET_KEY`. Store encrypted value + nonce in database. Decrypt only at send time | `ppl-meta-communications` | Direct DB query shows ciphertext, not plaintext |
| **H3** | Encrypt `auth_token` and `auth_password` in `webhook_config` table using same mechanism as H2 | `ppl-meta-communications` | Direct DB query shows ciphertext |
| **M3** | Add rate limiting: 10 emails/minute per sender, 100 webhooks/minute per endpoint. Use in-memory sliding window (dev) / Redis (production) | `ppl-meta-communications` | 11th email within 1 minute → 429 Too Many Requests |
| **C3** | Same as Phase 1 C3/C4 remediation — remove default SECRET_KEY | `ppl-meta-communications` | Service refuses to start without unique key |

#### Phase 4 Hardening (Edge Camera + Camera Manager)

| ID | Remediation | Service | Validation |
|---|---|---|---|
| **C5** | Complete JWT validation in `management_api.py::verify_token()`. Validate JWT signature using node's public key or shared secret. Reject tokens with `exp` in the past. Remove the `"accepting token"` fallback code path entirely | `ppl-meta-edge-camera` | Invalid JWT → 401. Expired JWT → 401. No token → 401 |
| **M1** | Remove dev-mode fallback in management API. If no `api_key` is configured in production, management endpoints MUST return 401 for all unauthenticated requests. Dev mode allowed ONLY when `ENVIRONMENT=development` env var is set | `ppl-meta-edge-camera` | Production + no API key → 401 for all management endpoints |
| **H1** | Replace plain-text password email with time-limited password reset link. Email body becomes: `"Click here to set your password: {reset_link}"` (link expires in 1 hour). Password never transmitted in email | `ppl-meta-node` | Password reset email contains link, not password text |
| **C1** | Remove ALL hardcoded test passwords from source code. Test user creation restricted to `ENVIRONMENT=development` only. Production bootstrap user must be created via authority admin console or secure provisioning script | `ppl-meta-node` | Grep for `"Kodikos@23"` returns zero results in src/ |

#### Phase 5 Hardening (Mobile Camera + Signage Player)

| ID | Remediation | Service | Validation |
|---|---|---|---|
| **H4** | Replace `SharedPreferences` token storage with `flutter_secure_storage` (Keychain on iOS, EncryptedSharedPreferences on Android). Migrate all token storage calls: `TokenManager.saveToken()`, `EnhancedAuthenticationService._storeAuthData()`, `MobileCameraHeartbeatService` | `ppl_meta_mobile_camera` | Tokens stored in OS-level secure enclave, not plain SharedPreferences |
| **H6** | Implement token refresh flow: `POST /api/v1/auth/refresh` endpoint on node. Mobile app stores refresh token (longer TTL) in secure storage, access token (short TTL) in memory. Auto-refresh on 401 response | `ppl_meta_mobile_camera`, `ppl-meta-node` | Expired access token → automatic silent refresh → retry succeeds |
| **H7** | Consolidate to ONE authentication implementation. Deprecate `AutoAuthenticationService`, `DiscoveryBasedAuthenticationService`, `HybridServiceDiscovery`. All auth flows use `EnhancedAuthenticationService` with VPN-first discovery path | `ppl_meta_mobile_camera` | Only one auth class handles login; others removed or marked `@deprecated` |
| **M6** | Implement certificate pinning for authority Headscale server (`vpn.eyenet-vision.com`) and primary node API. Use `flutter_ssl_pinning` or platform-channel approach. Pin the Let's Encrypt intermediate CA certificate | `ppl_meta_mobile_camera`, `ppl-meta-signage-simple-player` | MITM proxy → connection refused. Legitimate cert change → requires app update |
| **H4** | Apply same secure storage migration to signage player's token/credential storage | `ppl-meta-signage-simple-player` | Tokens in OS-level secure enclave |

#### Phase 6 Hardening (Production Readiness)

| ID | Remediation | Service | Validation |
|---|---|---|---|
| **M2** | `get_auth_token()` must validate JWT signature and expiry for user tokens. Only skip validation for internal service tokens (which must be validated separately). Add: `if token != INTERNAL_SERVICE_TOKEN: payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])` | `ppl-meta-orchestrator` | Invalid JWT → 401. Unsigned token → 401 |
| **C7** | Replace `INTERNAL_SERVICE_TOKEN` string comparison with JWT-based service auth (matching Phase 2 C6 remediation). All orchestrator service clients use short-lived JWTs | `ppl-meta-orchestrator` | Same validation as Phase 2 C6 |
| **C8** | If not already migrated in earlier phases: switch `JWT_ALGORITHM` to `RS256`. Generate RSA key pair per deployment. Private key on node, public key distributed to all services for verification | All services | HS256 tokens rejected when `RS256` configured |
| **M6** | Extend certificate pinning to Python services: `httpx` / `aiohttp` clients verify against pinned CA certificate for authority and cross-installation calls | `ppl-meta-node`, `ppl-meta-communications`, `ppl-meta-discovery`, `ppl-meta-cameras` | MITM between services → connection rejected |
| **All** | Penetration testing checklist: (1) Attempt device registration with Tailscale IP but no ACL tag → must fail. (2) Attempt cross-Matrix-group API call → must fail. (3) Replay captured JWT after logout → must fail. (4) Access management API without token in production mode → must fail. (5) Enroll with expired pre-auth key → must fail | All services | All 5 pen tests pass |

---

### 10.3 Security Principles for All New Code

Every new file introduced in this proposal MUST follow these principles:

1. **No secrets in source**: All credentials, keys, and tokens come from environment variables or secure vault. Default values that allow bypass are forbidden.
2. **Fail-secure, not fail-open**: If authentication/authorization cannot be verified, the request is DENIED. No `"accepting token"` fallback paths.
3. **Least privilege**: Service-to-service tokens are scoped to a single operation. A token that can read presence analytics cannot also enroll VPN devices.
4. **Encryption at rest**: Any stored credential (SMTP password, API key, webhook token) is encrypted before database write. Decrypted only at use time.
5. **Auditability**: All authentication events (login, logout, token refresh, device enrollment, device revocation) produce audit log entries with source IP, timestamp, and actor identity.
6. **Defense in depth**: VPN (Headscale ACL) is layer 1. JWT validation is layer 2. Capability check is layer 3. All three must pass for any protected operation.

### 10.4 Security Validation Checklist Per Phase

Before marking any phase as "complete," run this checklist:

| Phase | Must-Pass Security Tests |
|---|---|
| **Phase 1** | Default SECRET_KEY → service refuses to start. Headscale rejects unauthenticated API calls. Pre-auth key with wrong tags → enrollment rejected |
| **Phase 2** | Device with Tailscale IP but no ACL tag → registration rejected (403). `X-Service-Secret` replaced by JWT. No hardcoded `INTERNAL_SERVICE_TOKEN` in orchestrator |
| **Phase 3** | DB query shows encrypted `mail_password`. 11th email in 1 minute → 429. No default SECRET_KEY in communications service |
| **Phase 4** | Invalid JWT → edge camera returns 401. Production mode + no API key → 401. Password reset email contains link, never plain text. `grep "Kodikos@23"` returns zero results |
| **Phase 5** | Tokens stored in Keychain/EncryptedSharedPreferences, not SharedPreferences. Single auth implementation. MITM proxy with wrong cert → connection refused. Expired access token → auto-refresh succeeds |
| **Phase 6** | All 5 penetration tests pass. RS256 migration complete. Python services enforce TLS pinning |

---

## 9. References

- [Headscale GitHub](https://github.com/juanfont/headscale)
- [Headscale Documentation](https://headscale.net/)
- [Tailscale Client Download](https://tailscale.com/download)
- [WireGuard Protocol](https://www.wireguard.com/)
- [Existing Headscale Roadmap](docs/modules/VPN/implementation-roadmap-headscale-vpn.md)
- [EyeNet Matrix Proposal](docs/proposals/eyenet-matrix.md)
- [Authority Service README](autonomous/ppl-meta-authority/README.md)
- [Discovery Service](ppl-meta-discovery/)
- [Communications Service](ppl-meta-communications/)

---

*Document prepared for architectural review and implementation planning*  
*Confidential - Internal Use Only*
