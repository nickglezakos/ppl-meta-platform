# EyeNet Matrix

## Proposal for Cross-Installation Grouping, Aggregated Reporting, and Unified User Access

**Status**: Proposal  
**Date**: June 27, 2026  
**Author**: PPL Meta Platform Team

---

## 1. Overview

EyeNet Matrix is a local-level microservice that groups multiple EyeNet installations running within the same network boundary into a single management and reporting unit called a **Matrix Network**. It provides:

- **Aggregated cross-installation reporting** — presence analytics, gate activity, crowd metrics, camera events, and log reports rolled up across all member installations
- **A single Matrix parent for every installation** — no EyeNet installation exists without a Matrix group. Single-installation licences get an auto-created single-member Matrix; multi-installation licences allow grouping under one Matrix Network
- **SSO-like user access across installations** — users authenticate with their existing EyeNet credentials at their home node and gain access to Matrix-scoped reports and management across all installations in the group without duplicating accounts
- **Minimal frontend modifications** — the existing frontend and mobile clients surface a lightweight "Matrix" tab when the authenticated user possesses Matrix capabilities
- **Computation proximity to camera feeds** — aggregation runs locally, querying each member installation's services directly, avoiding round-trips to the authority VPS

---

## 2. Architecture Decision: Independent Local Microservice

### 2.1 Why a New Service and Not an Authority Extension

EyeNet Matrix is deployed as a new microservice (`ppl-meta-matrix`) within the monorepo, running alongside existing local services at each node. It is **not** an extension of the authority service.

| Concern | Local Service (`ppl-meta-matrix`) | Authority Extension (Rejected) |
|---|---|---|
| **Computation proximity** | Aggregation queries local databases and services directly — low latency, no VPS round-trip | Requires all installation data to be relayed to the VPS, breaking the local-first architecture |
| **Multiple computation points** | Node already runs ppl-meta, ppl-vmeta, orchestrator, cameras — all near camera spots. Matrix aggregates across these without leaving the local network | Creates a single aggregation bottleneck at the VPS, unsuitable for multi-site deployments |
| **Frontend compatibility** | Frontend and mobile apps call Matrix APIs at the local node URL with minimal route additions | Requires frontend to route to a different host for matrix data, complicating the client architecture |
| **Installation independence** | Each node remains self-contained; Matrix failure does not block individual installations | Authority becomes a runtime dependency for local aggregation |
| **Authority scope** | Authority only validates a `matrix_enabled` licence feature during activation — nothing more | Authority scope bloat into reporting, user management, and real-time data aggregation |

### 2.2 Service Placement

```
Matrix Network "Downtown Campus"
├── ppl-meta-matrix (one per Matrix Network, deployed on the primary node)
│
├── Installation A (Main Building)                    [own hardware]
│   ├── ppl-meta-node              ← own users DB
│   ├── ppl-meta-cameras
│   ├── ppl-meta-orchestrator
│   ├── ppl-meta-presence
│   └── ppl-meta-media
│
├── Installation B (Parking Garage)                   [own hardware]
│   ├── ppl-meta-node              ← own users DB
│   ├── ppl-meta-cameras
│   └── ppl-meta-orchestrator
│
└── Installation C (Warehouse)                        [own hardware]
    ├── ppl-meta-node              ← own users DB
    ├── ppl-meta-cameras
    └── ppl-meta-presence
```

Each installation is a fully self-contained EyeNet stack with its own node. The Matrix service aggregates across all three, querying their reporting endpoints locally.

---

## 3. Core Principle: Every Installation Has a Matrix Parent

### 3.1 Single-Installation Licence
When an EyeNet installation activates with a licence that does **not** include `matrix_multi_install`, the Matrix service automatically creates a single-member Matrix group at first instantiation. The installation operates normally with a 1:1:1 relationship:

- 1 Matrix Network → 1 EyeNet Installation → 1 Node

### 3.2 Multi-Installation Licence
When the licence includes `matrix_multi_install` (or is upgraded to include it), additional EyeNet installations can be added to the existing Matrix Network:

- 1 Matrix Network → N EyeNet Installations → N Nodes (one per installation)

### 3.3 Licence Upgrade Path
A single-installation Matrix licence can be upgraded (via authority) to allow multiple installations. Upon upgrade, the Matrix group becomes open for additional installations to join.

---

## 4. Authority Scope: Matrix-Enabled Software Licence

### 4.1 Licence Feature Flags
Authority's installation entitlement model gains a `licence_features` field (JSON array or dedicated column). Matrix-relevant features:

| Feature Flag | Effect |
|---|---|
| `matrix_enabled` | The installation is allowed to participate in a Matrix Network |
| `matrix_multi_install` | The Matrix Network may contain more than one installation |

### 4.2 Activation Flow
1. Node activates with authority via `POST /api/v1/installations/activate`
2. Authority returns `activation_status` and `licence_features: ["matrix_enabled", "matrix_multi_install"]` (or just `["matrix_enabled"]`)
3. Node's `AuthorityService` caches the feature flags in `InstallationInfo`
4. On startup, `ppl-meta-matrix` reads the cached flags:
   - `matrix_enabled=false` → Matrix service runs in dormant mode (no APIs exposed beyond health)
   - `matrix_enabled=true, matrix_multi_install=false` → Single-installation Matrix auto-created, no additional installations can join
   - `matrix_enabled=true, matrix_multi_install=true` → Full Matrix functionality available

### 4.3 What Authority Does NOT Handle
- No Matrix group data stored on authority
- No cross-installation reports generated on authority
- No user directory or SSO logic on authority
- No real-time data aggregation on authority

---

## 5. Functional Specification

### 5.1 Matrix Group Management

#### 5.1.1 Auto-Creation on First Boot
When `ppl-meta-matrix` starts for the first time and detects no existing Matrix group:
1. Query local node for this installation's UUID
2. Create a Matrix group named after the installation's tenant name (or "Default Matrix")
3. Assign the current installation as the sole member
4. If `matrix_multi_install=false`, lock the group to single-member mode

#### 5.1.2 Manual Group Management (Multi-Install Licences)

```
POST   /api/v1/matrix/groups                              # Create a new Matrix group
GET    /api/v1/matrix/groups                              # List all Matrix groups
GET    /api/v1/matrix/groups/{matrix_id}                  # Get group details
PUT    /api/v1/matrix/groups/{matrix_id}                  # Update group name/description
DELETE /api/v1/matrix/groups/{matrix_id}                  # Delete group (removes memberships)
```

### 5.2 Installation Membership

```
POST   /api/v1/matrix/groups/{matrix_id}/installations           # Add installation to group
GET    /api/v1/matrix/groups/{matrix_id}/installations           # List member installations
DELETE /api/v1/matrix/groups/{matrix_id}/installations/{uuid}    # Remove installation from group
```

**Constraints:**
- Adding installations only allowed when `matrix_multi_install=true`
- An installation can belong to exactly one Matrix group at a time
- Removing the last installation from a group is allowed but triggers a warning; the group becomes empty until another installation is added or the group is deleted

### 5.3 Group-Level Aggregated Reporting

Matrix queries each member installation's local reporting endpoints and aggregates results. The aggregation strategy depends on the report type:

| Report Type | Aggregation Strategy | Source Services |
|---|---|---|
| **Presence analytics** | Sum counts, merge distributions | ppl-meta-presence per installation |
| **Gate activity / crowd metrics** | Combine time-series, merge heatmap data | ppl-meta-orchestrator per installation |
| **Camera event summaries** | Aggregate event counts, merge timelines | ppl-meta-cameras per installation |
| **Log reports** | Combine log entries, sort by timestamp, deduplicate | ppl-meta-node per installation |
| **Demographic summaries** | Merge age/gender distributions | ppl-meta-orchestrator per installation |

#### 5.3.1 Reporting Endpoints

```
GET /api/v1/matrix/groups/{matrix_id}/reports/presence?from=&to=
GET /api/v1/matrix/groups/{matrix_id}/reports/gate-activity?from=&to=
GET /api/v1/matrix/groups/{matrix_id}/reports/camera-events?from=&to=
GET /api/v1/matrix/groups/{matrix_id}/reports/logs?from=&to=&level=&installation_uuid=
GET /api/v1/matrix/groups/{matrix_id}/reports/demographics?from=&to=
GET /api/v1/matrix/groups/{matrix_id}/reports/summary?from=&to=
```

Each endpoint accepts optional `from` and `to` ISO-8601 timestamps. The `logs` endpoint additionally accepts `level` (info, warning, error) and `installation_uuid` filters.

#### 5.3.2 Caching Strategy
Aggregated reports are cached with a configurable TTL (default: 60 seconds). On cache miss, the matrix queries all member installations in parallel, merges results, caches, and returns.

### 5.4 Matrix User Directory and SSO-Like Access

#### 5.4.1 Design Principle
Each node owns its local user database (as it does today). The Matrix service maintains a cross-referencing user directory that maps users to their home installation and Matrix-level capabilities. Users **do not** need accounts on every installation's node.

#### 5.4.2 User Directory Schema

```sql
CREATE TABLE matrix_users (
    id SERIAL PRIMARY KEY,
    matrix_group_id UUID NOT NULL REFERENCES matrix_groups(id) ON DELETE CASCADE,
    user_email VARCHAR(255) NOT NULL,
    home_installation_uuid VARCHAR(255) NOT NULL,
    home_node_url VARCHAR(512) NOT NULL,
    display_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (matrix_group_id, user_email)
);

CREATE TABLE matrix_user_capabilities (
    id SERIAL PRIMARY KEY,
    matrix_user_id INTEGER NOT NULL REFERENCES matrix_users(id) ON DELETE CASCADE,
    capability VARCHAR(100) NOT NULL,
    granted_by_user_id INTEGER NOT NULL,
    granted_at TIMESTAMP DEFAULT NOW(),
    UNIQUE (matrix_user_id, capability)
);
```

#### 5.4.3 Matrix Capabilities

| Capability | Description |
|---|---|
| `matrix:view_reports` | View aggregated reports across all member installations |
| `matrix:manage_group` | Create, update, delete Matrix groups; manage installation memberships |
| `matrix:manage_users` | Add/remove users from the Matrix directory; assign capabilities |
| `matrix:view_logs` | View aggregated log reports |
| `matrix:admin` | Full administrative access (all of the above) |

#### 5.4.4 Authentication Flow
1. User authenticates at their **home installation's node** (`POST /api/v1/auth/login` on node A)
2. Node A issues a JWT containing the user's email, user ID, and home installation UUID
3. Frontend calls `GET /api/v1/matrix/me` with the JWT
4. Matrix service:
   - Validates the JWT signature (using the same shared secret or public key as node)
   - Looks up `matrix_users` by email + checks which Matrix groups include the user's home installation
   - Returns the user's Matrix groups and capabilities
5. Frontend conditionally renders the "Matrix" tab based on the response

**Key property:** The user never logs into Matrix directly. The Matrix trusts the home node's JWT.

#### 5.4.5 Cross-Installation Authorization
When User X (home: Installation A) requests aggregated reports that include Installation B's data:
1. Matrix verifies User X has `matrix:view_reports` capability
2. Matrix verifies both Installation A and Installation B are in the same Matrix group as User X's membership
3. Matrix queries Installation B's reporting endpoints using a **Matrix service-to-service token** (not the user's JWT)
4. Results are aggregated and returned

This means Installation B's node never needs to know about User X's account — the Matrix mediates access.

### 5.5 Frontend and Mobile Client Integration

#### 5.5.1 Additive Changes Only
- A new "Matrix" navigation item appears when `GET /api/v1/matrix/me` returns at least one group with capabilities
- Matrix views are entirely additive — no existing installation-level views are modified or removed
- The matrix tab contains:
  - **Dashboard**: Aggregated summary across all member installations
  - **Reports**: Per-report-type views with installation filter dropdowns
  - **Logs**: Aggregated log viewer with installation and severity filters
  - **Management** (if `matrix:manage_group`): Group settings, installation membership, user directory

#### 5.5.2 Mobile App
The same JWT from the mobile app's existing login flow is sent to Matrix endpoints. The mobile app gains a "Matrix" section in its navigation drawer when the user has matrix capabilities.

---

## 6. Database Schema (ppl-meta-matrix)

### 6.1 Matrix Groups
```sql
CREATE TABLE matrix_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    licence_multi_install BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### 6.2 Installation Memberships
```sql
CREATE TABLE matrix_installation_memberships (
    id SERIAL PRIMARY KEY,
    matrix_group_id UUID NOT NULL REFERENCES matrix_groups(id) ON DELETE CASCADE,
    installation_uuid VARCHAR(255) NOT NULL,
    installation_name VARCHAR(255),
    node_url VARCHAR(512) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (matrix_group_id, installation_uuid)
);
```

### 6.3 Matrix Users
```sql
CREATE TABLE matrix_users (
    id SERIAL PRIMARY KEY,
    matrix_group_id UUID NOT NULL REFERENCES matrix_groups(id) ON DELETE CASCADE,
    user_email VARCHAR(255) NOT NULL,
    home_installation_uuid VARCHAR(255) NOT NULL,
    home_node_url VARCHAR(512) NOT NULL,
    display_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (matrix_group_id, user_email)
);

CREATE TABLE matrix_user_capabilities (
    id SERIAL PRIMARY KEY,
    matrix_user_id INTEGER NOT NULL REFERENCES matrix_users(id) ON DELETE CASCADE,
    capability VARCHAR(100) NOT NULL,
    granted_by_user_id INTEGER NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (matrix_user_id, capability)
);
```

### 6.4 Report Cache
```sql
CREATE TABLE matrix_report_cache (
    id SERIAL PRIMARY KEY,
    matrix_group_id UUID NOT NULL REFERENCES matrix_groups(id) ON DELETE CASCADE,
    report_type VARCHAR(100) NOT NULL,
    query_params JSONB NOT NULL,
    result_data JSONB NOT NULL,
    cached_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE (matrix_group_id, report_type, query_params)
);
```

---

## 7. API Contract

### 7.1 Base Path
All Matrix endpoints are served at `/api/v1/matrix/` on the Matrix service's host, or proxied through the primary node.

### 7.2 Authentication
All endpoints require a valid JWT issued by any member installation's node. The Matrix service validates the JWT using a shared secret or public key configured identically across all nodes in the Matrix Network.

### 7.3 Endpoints Summary

#### Groups
| Method | Path | Capability Required | Description |
|---|---|---|---|
| `POST` | `/api/v1/matrix/groups` | `matrix:manage_group` | Create a new Matrix group |
| `GET` | `/api/v1/matrix/groups` | `matrix:view_reports` | List groups the authenticated user belongs to |
| `GET` | `/api/v1/matrix/groups/{id}` | `matrix:view_reports` | Get group details |
| `PUT` | `/api/v1/matrix/groups/{id}` | `matrix:manage_group` | Update group |
| `DELETE` | `/api/v1/matrix/groups/{id}` | `matrix:manage_group` | Delete group |

#### Memberships
| Method | Path | Capability Required | Description |
|---|---|---|---|
| `POST` | `/api/v1/matrix/groups/{id}/installations` | `matrix:manage_group` | Add installation to group |
| `GET` | `/api/v1/matrix/groups/{id}/installations` | `matrix:view_reports` | List member installations |
| `DELETE` | `/api/v1/matrix/groups/{id}/installations/{uuid}` | `matrix:manage_group` | Remove installation from group |

#### Reports
| Method | Path | Capability Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/matrix/groups/{id}/reports/summary` | `matrix:view_reports` | Aggregated summary dashboard |
| `GET` | `/api/v1/matrix/groups/{id}/reports/presence` | `matrix:view_reports` | Aggregated presence analytics |
| `GET` | `/api/v1/matrix/groups/{id}/reports/gate-activity` | `matrix:view_reports` | Aggregated gate/crowd metrics |
| `GET` | `/api/v1/matrix/groups/{id}/reports/camera-events` | `matrix:view_reports` | Aggregated camera events |
| `GET` | `/api/v1/matrix/groups/{id}/reports/demographics` | `matrix:view_reports` | Aggregated demographic data |
| `GET` | `/api/v1/matrix/groups/{id}/reports/logs` | `matrix:view_logs` | Aggregated log reports |

#### Users
| Method | Path | Capability Required | Description |
|---|---|---|---|
| `GET` | `/api/v1/matrix/me` | (authenticated) | Get current user's Matrix groups and capabilities |
| `GET` | `/api/v1/matrix/groups/{id}/users` | `matrix:manage_users` | List users in the Matrix directory |
| `POST` | `/api/v1/matrix/groups/{id}/users` | `matrix:manage_users` | Add a user to the Matrix directory |
| `DELETE` | `/api/v1/matrix/groups/{id}/users/{email}` | `matrix:manage_users` | Remove a user from the directory |
| `PUT` | `/api/v1/matrix/groups/{id}/users/{email}/capabilities` | `matrix:manage_users` | Update user capabilities |

---

## 8. Service Integration Details

### 8.1 Service Discovery
`ppl-meta-matrix` discovers member installations via the `matrix_installation_memberships` table, which stores each installation's `node_url`. For each reporting request, Matrix makes HTTP calls to the member node's API gateway or directly to the relevant service:

```
Matrix → http://<installation-node>:8000/api/v1/presence/analytics/summary
Matrix → http://<installation-node>:8002/api/v1/workflows/analytics
Matrix → http://<installation-node>:8005/api/v1/cameras/events/stats
Matrix → http://<installation-node>:8000/api/v1/logs
```

### 8.2 Service-to-Service Authentication
Matrix uses a pre-shared `SERVICE_SECRET` (already used by node's `ServiceDiscovery.make_internal_request`) when querying member installations. Headers:
```
X-Service-Auth: internal
X-Service-Secret: <shared-secret>
X-Requesting-Service: ppl-meta-matrix
X-Matrix-Group-ID: <group-uuid>
```

### 8.3 Health and Resilience
- If a member installation is unreachable, Matrix returns partial results with a `degraded: true` flag and lists the unreachable installations
- Matrix reports its own health at `GET /api/v1/matrix/health`
- Matrix does **not** block individual installations from operating if the Matrix service itself is down

---

## 9. Authority Changes Required

### 9.1 Entitlement Model Extension
Add `licence_features` (JSONB or text array) to the entitlement/installation records in the authority database.

### 9.2 Activation Response Extension
`POST /api/v1/installations/activate` response gains:
```json
{
  "approved": true,
  "installation_uuid": "...",
  "application_key": "lic_...",
  "licence_features": ["matrix_enabled", "matrix_multi_install"],
  ...
}
```

### 9.3 Installation Record Extension
`GET /api/v1/installations/{uuid}` response gains `licence_features`.

### 9.4 Node AuthorityService Cache Extension
`InstallationInfo` model gains:
```python
authority_licence_features = Column(JSONB, nullable=True)
```
Cached during `_cache_authority_state` from the activation/installation payload.

---

## 10. Implementation Phases

### Phase 1: Scaffolding and Core Model
- Create `/ppl-meta-matrix` service with FastAPI scaffold
- Database schema (matrix_groups, matrix_installation_memberships, matrix_users, matrix_user_capabilities)
- Auto-creation of single-member Matrix on first boot
- Health endpoint

### Phase 2: Group and Membership APIs
- CRUD for Matrix groups
- Installation membership management
- `matrix_multi_install` gating logic

### Phase 3: User Directory and SSO
- Matrix user directory CRUD
- JWT validation against member nodes
- `GET /api/v1/matrix/me` endpoint
- Capability management

### Phase 4: Aggregated Reporting
- Service-to-service queries to member installations
- Report aggregation logic per report type
- Report caching layer
- All report endpoints

### Phase 5: Authority Licence Integration
- `licence_features` column in authority schema
- Activation response extension
- Node `AuthorityService` cache update
- Node `InstallationInfo` schema migration

### Phase 6: Frontend and Mobile Integration
- Matrix tab in admin dashboard
- Matrix report views
- Matrix user management UI
- Mobile app Matrix navigation item

---

## 11. Open Questions

1. **Matrix service deployment**: Should `ppl-meta-matrix` run as a sidecar on the primary node, or as a standalone container in the docker-compose stack?
2. **Report caching TTL**: Is 60 seconds appropriate, or should it be configurable per report type?
3. **Matrix group naming convention**: Auto-generated from tenant name, or require manual naming on creation?
4. **Installation discovery for joining a Matrix**: Should new installations auto-discover existing Matrix groups on the local network (mDNS/DNS-SD), or require manual entry of the primary node's URL?
5. **Cross-node user synchronization**: Should the matrix proactively sync user records from member nodes, or resolve them lazily on first access?

---

*Document prepared for architectural review and implementation planning*
*Confidential - Internal Use Only*