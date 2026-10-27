# ppl-meta-matrix: Cross-Installation Grouping & Aggregated Reporting Service

**Purpose:** Runs alongside `ppl-meta-node` on the primary installation in a Matrix Network. Designed to operate under VPN, providing centralized management and aggregated reporting across multiple PPL Meta installations.

**Port:** `8015` (configurable via `MATRIX_PORT` env var)

---

## Phase 1 — Auto-Provisioning

- **Auto-creation of a default Matrix group** on first boot, with the local installation added as the sole member.
- Auto-discovers the local installation UUID from the node's SQLite database (`ppl_meta_node.db`) or generates one if unavailable.
- Configurable default group name via `MATRIX_GROUP_NAME` env var.

## Phase 2 — Matrix Group CRUD & Installation Membership

- **Group management (full CRUD):**
  - `POST /api/v1/matrix/groups` — Create a group (name, description, `multi_install` flag)
  - `GET /api/v1/matrix/groups` — List all groups
  - `GET /api/v1/matrix/groups/{id}` — Get a single group
  - `PUT /api/v1/matrix/groups/{id}` — Update group name/description
  - `DELETE /api/v1/matrix/groups/{id}` — Delete a group

- **Installation membership management:**
  - `POST /api/v1/matrix/groups/{id}/installations` — Add an installation (UUID, name, node URL)
  - `GET /api/v1/matrix/groups/{id}/installations` — List member installations
  - `DELETE /api/v1/matrix/groups/{id}/installations/{uuid}` — Remove an installation

- **Multi-install licensing enforcement:** The `licence_multi_install` boolean flag on groups restricts adding more than 1 installation unless explicitly enabled.

## Phase 3 — User Directory & SSO (JWT-based)

- **JWT authentication** that trusts JWTs issued by member nodes (does not issue its own tokens). Validates `Authorization: Bearer <token>` headers using a shared `SECRET_KEY`.

- **User directory CRUD per Matrix group:**
  - `GET /api/v1/matrix/groups/{id}/users` — List users in a group
  - `POST /api/v1/matrix/groups/{id}/users` — Add a user (email, home installation UUID, display name, initial capabilities)
  - `DELETE /api/v1/matrix/groups/{id}/users/{email}` — Remove a user
  - `PUT /api/v1/matrix/groups/{id}/users/{email}/capabilities` — Update user capabilities

- **`GET /api/v1/matrix/me`** — Primary endpoint for frontend integration. Returns the authenticated user's Matrix groups, capabilities, and whether the "Matrix" tab should be shown in the UI.

- **Matrix Capabilities (RBAC):**

  | Capability | Description |
  |---|---|
  | `matrix:view_reports` | View aggregated reports across all member installations |
  | `matrix:manage_group` | Create, update, delete Matrix groups; manage installation memberships |
  | `matrix:manage_users` | Add/remove users from the Matrix directory; assign capabilities |
  | `matrix:view_logs` | View aggregated log reports |
  | `matrix:admin` | Full administrative access (all of the above) |

## Phase 4 — Cross-Installation Aggregated Reporting

- **6 report types**, each querying all member installations in parallel via HTTP and aggregating results:

  | Report | Endpoint | Data Source |
  |---|---|---|
  | **Summary** | `GET /groups/{id}/reports/summary` | Aggregates presence + camera-event totals |
  | **Presence** | `GET /groups/{id}/reports/presence` | `ppl-meta-presence` analytics |
  | **Gate Activity** | `GET /groups/{id}/reports/gate-activity` | `ppl-meta-orchestrator` crowd metrics |
  | **Camera Events** | `GET /groups/{id}/reports/camera-events` | `ppl-meta-cameras` event stats |
  | **Demographics** | `GET /groups/{id}/reports/demographics` | `ppl-meta-orchestrator` age/gender data |
  | **Logs** | `GET /groups/{id}/reports/logs` | `ppl-meta-node` log entries |

- **Result caching** with a 60-second TTL (configurable), stored in the `matrix_report_cache` table.

- **Degraded mode:** If some installations are unreachable, the report still returns partial data with a `degraded: true` flag and an `unreachable` list.

- **Time-range filtering:** All reports support optional `from` / `to` ISO-8601 timestamp query parameters.

- **Log report extras:** Supports `level` filter (info/warning/error) and `installation_uuid` filtering to narrow results to a single installation.

---

## Infrastructure

- **Database:** 5 tables — `matrix_groups`, `matrix_installation_memberships`, `matrix_users`, `matrix_user_capabilities`, `matrix_report_cache`. Uses SQLite by default, PostgreSQL in production.
- **Built with:** FastAPI, SQLAlchemy 2.0, httpx (async HTTP client for cross-installation queries), PyJWT.
- **Health check:** `GET /health` returns service status.

---

## VPN Context

Since the entire platform operates under VPN, the ppl-meta-matrix service communicates with member installations via their internal VPN node URLs (stored as `node_url` on each membership). All cross-installation HTTP queries go over the VPN tunnel, meaning the service works transparently within a private network without needing public internet exposure.

---

## Source File Structure

```
ppl-meta-matrix/
├── requirements.txt
├── migrations/
└── src/
    ├── __init__.py
    ├── main.py                        # FastAPI app entry point, lifespan, router registration
    ├── ppl-meta-matrix.db             # SQLite development database
    ├── api/
    │   ├── __init__.py
    │   ├── groups.py                  # Group CRUD endpoints
    │   ├── memberships.py             # Installation membership endpoints
    │   ├── users.py                   # User directory + SSO endpoints
    │   ├── reports.py                 # Aggregated reporting endpoints (6 report types)
    │   └── health.py                  # Health check endpoint
    ├── models/
    │   ├── __init__.py
    │   └── database.py                # SQLAlchemy models (5 tables), DB init, session factory
    └── services/
        ├── __init__.py
        ├── matrix_service.py          # Core business logic (groups, memberships, users, capabilities)
        └── aggregation_service.py     # Cross-installation report aggregation + caching