# EyeNet Node — API Reference
v2.25.38, 22 June 2026

The **EyeNet Node** (ppl-meta-node) is the User Management microservice of the PPL Meta platform. It provides authentication, user/role/capability administration, licensing, health monitoring, and service discovery.

The API is built with **FastAPI**, which auto-generates interactive documentation and machine-readable specs:

| Format | URL |
|--------|-----|
| Swagger UI | `http://<host>:8001/docs` |
| ReDoc | `http://<host>:8001/redoc` |
| OpenAPI JSON | `http://<host>:8001/openapi.json` |

> **Base URL:** `http://<host>:8001`
>
> All request/response bodies are JSON unless noted otherwise.

---

## Authentication

Most endpoints require a **JWT Bearer token** obtained via `/api/v1/users/login`. Include it as:

```
Authorization: Bearer <access_token>
```

**Inter-service endpoints** (e.g. `/api/v1/users/validate-token`, `/api/v1/users/user-info/{user_id}`) use a shared `SERVICE_SECRET` passed as a Bearer token in the `Authorization` header instead of a user JWT.

Endpoints marked **Public** below do not require any authentication.

---

## Middleware

| Middleware | Purpose |
|-----------|---------|
| `TimingMiddleware` | Adds `X-Process-Time` header to every response |
| `AuthoritySafeguardMiddleware` | Returns **423 Locked** on protected routes when the installation enters safeguard mode |
| `CORSMiddleware` | Allows all origins, methods, and headers |
| `TrustedHostMiddleware` | Restricts requests to detected local IPs, localhost, and Tailscale/Wireguard VPN ranges |

---

## Endpoints

### 1. Root & Service Discovery

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/` | Root — returns service name, version, status, and links to docs/health | Public |
| `GET` | `/api/v1/mobile/discover` | Mobile discovery — returns all detected network IPs, service ports/endpoints, and VPN status for auto-pairing | Public |
| `GET` | `/api/v1/mobile/pairing-info` | Pairing info — returns preferred connection IP, service URLs, and login instructions for mobile app setup | Public |

---

### 2. Health

**Prefix:** `/api/v1/health`

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/` | Basic health check (always returns `healthy`) | Public |
| `GET` | `/detailed` | Detailed health — includes DB connectivity, CPU%, memory%, disk% | Public |
| `GET` | `/ready` | Kubernetes readiness probe — returns 503 if DB is unreachable | Public |
| `GET` | `/live` | Kubernetes liveness probe — always returns `alive` | Public |

The legacy prefix `/health` mirrors these same routes for backward compatibility.

---

### 3. Users

**Prefix:** `/api/v1/users`

#### Authentication

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `POST` | `/register` | Register a new user (send `username`, `email`, `password`). Sends verification email | Public |
| `POST` | `/login` | Login with `username` & `password` (OAuth2 form). Returns `access_token` + `token_type` | Public |
| `POST` | `/logout` | Logout (stateless — client must discard token) | Bearer |
| `GET` | `/verify-email` | Verify email via token (`?token=...`) | Public |

#### Profile & Settings

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/profile` | Returns current user's profile with roles & capabilities | Bearer |
| `GET` | `/debug-profile` | Debug profile — manual token extraction for troubleshooting | Bearer |
| `POST` | `/update-password` | Change own password (requires `old_password` + `new_password`) | Bearer |
| `POST` | `/forgot-password` | Request password reset email (requires `email`) | Public |
| `POST` | `/reset-password` | Reset password with reset token (requires `token` + `new_password`) | Public |

#### Admin User Management

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/` | List all users (paginated: `?skip=0&limit=100`) | Bearer + `users.accounts.read` |
| `GET` | `/{user_id}` | Get user by numeric ID | Bearer + `users.accounts.read` |
| `GET` | `/guid/{guid}` | Get user by GUID | Bearer + `users.accounts.read` |
| `GET` | `/user-profile/{user_id}` | Get full profile (roles + capabilities) for any user | Bearer + `users.accounts.read` |
| `POST` | `/admin/set-password/{user_id}` | Admin sets a user's password; optionally emails it | Bearer + `users.accounts.update` |
| `POST` | `/toggle-capability/{user_id}` | Toggle a capability on/off for a user across all their roles | Bearer + `auth.capabilities.assign` |
| `GET` | `/actions/` | List user action audit log (paginated) | Bearer + `users.accounts.read` |

#### Platform & Inter-Service

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/platform/services` | Returns full platform service discovery info (microservice URLs, ports, streaming endpoints, mobile camera config) | Bearer + `auth.session.use` |
| `POST` | `/validate-token` | Validate a JWT (inter-service only — uses `SERVICE_SECRET`) | Service Token |
| `GET` | `/user-info/{user_id}` | Get user info by ID (inter-service) | Service Token |
| `GET` | `/user-permissions/{user_id}` | Get roles + capabilities by user ID (inter-service) | Service Token |

---

### 4. Licensing & Authority

**Prefix:** `/licensing` (also mounted at `/api/v1/licensing`)

#### Bootstrap (First-Install)

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/bootstrap/status` | Get the bootstrap state (not_started → awaiting_owner_activation → owner_approved → bootstrap_complete) | Public |
| `POST` | `/bootstrap/activate` | Activate the first installation owner with an authority `application_key` | Public |

#### Authority

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/authority/status` | Get authority integration state, cached license/owner metadata, runtime state (normal/warning/safeguard), offline grace info | Bearer |
| `POST` | `/authority/refresh` | Force a fresh Authority lookup and update the local cache | Bearer |

#### License Management

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/status` | Get current license status and info from bootcore | Bearer |
| `GET` | `/features` | Get available features based on license type (trial/professional/enterprise/developer) | Bearer |
| `GET` | `/validation/user-limit` | Check if current user count is within license limits | Bearer |
| `GET` | `/health` | Test connectivity to bootcore licensing service | Public |
| `GET` | `/platform/identity` | Get the platform identity for this node installation | Public |
| `POST` | `/owner/register` | Register platform owner with the bootcore service | Public |

---

### 5. Roles

**Prefix:** `/roles`

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `POST` | `/` | Create a new role | Bearer + `auth.roles.create` |
| `GET` | `/` | List all roles | Bearer + `auth.roles.read` |
| `GET` | `/{role_id}` | Get role by ID | Bearer + `auth.roles.read` |
| `GET` | `/by-name/{role_name}` | Get role by name | Bearer + `auth.roles.read` |
| `PUT` | `/{role_id}` | Update a role name | Bearer + `auth.roles.update` |
| `DELETE` | `/{role_id}` | Delete a role | Bearer + `auth.roles.delete` |
| `POST` | `/assign/` | Assign a role to a user (`user_id` + `role_id` as query params) | Bearer + `auth.roles.assign` |
| `POST` | `/unassign/` | Unassign a role from a user (`user_id` + `role_id` as query params) | Bearer + `auth.roles.unassign` |
| `POST` | `/add-capability/` | Add a capability to a role (body: `role_id`, `capability_id`) | Bearer + `auth.capabilities.assign` |
| `POST` | `/remove-capability/` | Remove a capability from a role (body: `role_id`, `capability_id`) | Bearer + `auth.capabilities.unassign` |

---

### 6. Capabilities

**Prefix:** `/capabilities`

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/by-role/{role_id}` | List capability names for a role | Bearer + `auth.capabilities.read` |
| `GET` | `/by-user/{user_id}` | Get roles & capabilities for a user | Bearer + `users.accounts.read` |
| `GET` | `/my-capabilities` | Get the current user's roles & capabilities | Bearer |

---

### 7. OTP

**Prefix:** `/otp`

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `POST` | `/send` | Send OTP code to user's email (`user_id` in body) | Public |
| `POST` | `/verify-otp` | Verify OTP code (`email` + `otp_code`). Returns JWT access token on success | Public |

---

### 8. Application Settings

**Prefix:** `/settings`

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/{key}` | Get a setting value by key | Public |
| `POST` | `/` | Create or update a setting (body: `key` + `value`) | Public |

---

### 9. Logs

**Prefix:** `/logs`

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/` | Query log entries with optional `start`/`end` ISO timestamps, `skip`, `limit` | Public |

---

### 10. Backup & Restore

**Prefix:** `/backup` — All endpoints require **admin** role.

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| `GET` | `/export` | Export all data as JSON | Admin |
| `GET` | `/database` | Download a database backup file | Admin |
| `POST` | `/restore` | Restore data from an uploaded JSON file | Admin |
| `POST` | `/database` | Restore database from an uploaded backup file | Admin |

---

### 11. Legacy Routes (Backward Compatibility)

These routes mirror the v1 endpoints under shorter prefixes for backward compatibility with older clients:

| Legacy Prefix | Maps To |
|---------------|---------|
| `/users/*` | `/api/v1/users/*` |
| `/health/*` | `/api/v1/health/*` |

All routes under these prefixes have the same method, path structure, parameters, and auth requirements as their v1 counterparts.

---

## OpenAPI Specification

The complete machine-readable OpenAPI specification is served by FastAPI at:

- **JSON:** `http://<host>:8001/openapi.json`
- **YAML:** Can be derived from the JSON spec

This document is based on the auto-generated OpenAPI schema. For programmatic integration, prefer consuming `openapi.json` directly.