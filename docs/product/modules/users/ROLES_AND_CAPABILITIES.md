# EyeNet Node — Roles & Capabilities

> **Service**: `ppl-meta-node` (EyeNet Node)  
> **Role in Platform**: User Management microservice — authentication, RBAC, licensing, health, and service discovery  
> **Primary API Base**: `http://<host>:8001`  
> **Primary Audience**: platform administrators, developers integrating with EyeNet auth

---

## 1. Overview

The EyeNet Node implements a **Role-Based Access Control (RBAC)** system. The core principle is:

- **Capabilities** are fine-grained, named permissions (e.g., `users.accounts.create`, `cameras:view`).
- **Roles** are named collections of capabilities.
- **Users** are assigned one or more roles.
- Users **inherit** all capabilities from their assigned roles.

Capabilities are never assigned directly to users. Every permission check walks the chain: `User → UserRole → Role → RoleCapability → Capability`.

The system ships with three **system roles** (`owner`, `admin`, `user`) that cannot be renamed. Custom roles (e.g., `camera_user`, `vision_user`) can be created for domain-specific permission sets.

---

## 2. Data Model

The RBAC system uses five database tables:

```
┌──────────┐       ┌──────────────┐       ┌──────────┐
│  users   │       │  user_roles  │       │  roles   │
│──────────│ 1──N  │──────────────│ N──1  │──────────│
│ id (PK)  │───────│ id (PK)      │───────│ id (PK)  │
│ username │       │ user_id (FK) │       │ name     │
│ email    │       │ role_id (FK) │       └──────────┘
│ ...      │       └──────────────┘            │
└──────────┘                                   │ N
                                               │
                                      ┌────────────────────┐
                                      │ role_capabilities  │
                                      │────────────────────│
                                      │ id (PK)            │
                                      │ role_id (FK)       │
                                      │ capability_id (FK) │
                                      └────────────────────┘
                                               │ N
                                               │
                                      ┌──────────────┐
                                      │ capabilities │
                                      │──────────────│
                                      │ id (PK)      │
                                      │ name (UNIQUE)│
                                      └──────────────┘
```

### Tables

| Table | Purpose | Constraints |
|-------|---------|-------------|
| `users` | User identity records (username, email, password hash, profile fields) | `username` UNIQUE, `email` UNIQUE |
| `roles` | Role definitions | `name` UNIQUE |
| `capabilities` | Named permission strings (e.g., `cameras:view`, `auth.roles.read`) | `name` UNIQUE |
| `user_roles` | Junction: links users to roles | UNIQUE(`user_id`, `role_id`), FK cascades on delete |
| `role_capabilities` | Junction: links roles to capabilities | UNIQUE(`role_id`, `capability_id`), FK cascades on delete |

### TypeScript Interfaces (Conceptual)

```typescript
interface Role {
  id: number;
  name: string;             // "owner" | "admin" | "user" | "camera_user" | custom...
  capabilities: RoleCapability[];
  users: UserRole[];
}

interface Capability {
  id: number;
  name: string;             // e.g., "cameras:view", "auth.roles.create"
  roles: RoleCapability[];
}

interface User {
  id: number;
  username: string;
  email: string;
  roles: UserRole[];
}
```

---

## 3. System Roles & Default Capability Sets

Three system roles are seeded automatically at startup via `ensure_default_capabilities()` in `src/services/role_service.py`. System roles cannot be renamed.

### 3.1 `owner` — Platform Owner (30 capabilities)

The highest privilege role. Has full control over users, roles, capabilities, system configuration, licensing, and recovery.

| Capability | Domain |
|-----------|--------|
| `auth.session.use` | Can authenticate and hold a session |
| `users.profile.read` | Read own profile |
| `users.profile.update` | Update own profile |
| `users.password.change_self` | Change own password |
| `users.password.recover_self` | Initiate password recovery |
| `analytics.view` | View analytics dashboards |
| `cameras.view` | View cameras |
| `media.view` | View media |
| `workflows.use` | Use workflow automation |
| `users.accounts.read` | Read any user account |
| `users.accounts.create` | Create user accounts |
| `users.accounts.update` | Update user accounts |
| `users.accounts.disable` | Disable user accounts |
| `users.accounts.delete` | Delete user accounts |
| `cameras.manage` | Manage camera configuration |
| `media.manage` | Manage media assets |
| `operations.execute` | Execute operational tasks |
| `auth.roles.read` | View role definitions |
| `auth.roles.create` | Create new roles |
| `auth.roles.update` | Update role names |
| `auth.roles.delete` | Delete roles |
| `auth.roles.assign` | Assign roles to users |
| `auth.roles.unassign` | Unassign roles from users |
| `auth.capabilities.read` | View capability definitions |
| `auth.capabilities.assign` | Assign capabilities to roles |
| `auth.capabilities.unassign` | Remove capabilities from roles |
| `auth.capabilities.manage` | Full capability management |
| `system.installation.manage` | Manage installation configuration |
| `system.licensing.manage` | Manage licenses |
| `system.recovery.manage` | System recovery operations |

### 3.2 `admin` — Administrator (21 capabilities)

Broad administrative access. Can manage user accounts and assign/unassign roles and capabilities, but cannot delete user accounts, create/rename/delete roles, or access system-level settings.

> Includes all `user` capabilities (lines marked below) **plus** the admin extensions:

| Capability | Notes |
|-----------|-------|
| `auth.session.use` | (user base) |
| `users.profile.read` | (user base) |
| `users.profile.update` | (user base) |
| `users.password.change_self` | (user base) |
| `users.password.recover_self` | (user base) |
| `analytics.view` | (user base) |
| `cameras.view` | (user base) |
| `media.view` | (user base) |
| `workflows.use` | (user base) |
| `users.accounts.read` | Read any user account |
| `users.accounts.create` | Create user accounts |
| `users.accounts.update` | Update user accounts |
| `users.accounts.disable` | Disable user accounts |
| `cameras.manage` | Manage camera configuration |
| `media.manage` | Manage media assets |
| `operations.execute` | Execute operational tasks |
| `auth.roles.read` | View role definitions |
| `auth.roles.assign` | Assign roles to users |
| `auth.roles.unassign` | Unassign roles from users |
| `auth.capabilities.assign` | Assign capabilities to roles |
| `auth.capabilities.unassign` | Remove capabilities from roles |

### 3.3 `user` — Basic User (9 capabilities)

The default role for all authenticated users. Provides core platform access without administrative privileges.

| Capability | Domain |
|-----------|--------|
| `auth.session.use` | Can authenticate and hold a session |
| `users.profile.read` | Read own profile |
| `users.profile.update` | Update own profile |
| `users.password.change_self` | Change own password |
| `users.password.recover_self` | Initiate password recovery |
| `analytics.view` | View analytics dashboards |
| `cameras.view` | View cameras |
| `media.view` | View media |
| `workflows.use` | Use workflow automation |

### 3.4 Capability Hierarchy

```
owner
├── admin (subset of owner)
│   └── user (subset of admin)
└── [owner-only capabilities]
    ├── users.accounts.delete
    ├── auth.roles.create
    ├── auth.roles.update
    ├── auth.roles.delete
    ├── auth.capabilities.read
    ├── auth.capabilities.manage
    ├── system.installation.manage
    ├── system.licensing.manage
    └── system.recovery.manage
```
---

## 4. Complete Capability Registry

All capabilities organized by namespace.

### 4.1 Auth & Session

| Capability | Description | Default Roles |
|-----------|-------------|---------------|
| `auth.session.use` | Authenticate and hold a JWT session | owner, admin, user |
| `auth.roles.read` | View role definitions | owner, admin |
| `auth.roles.create` | Create new roles | owner |
| `auth.roles.update` | Rename existing roles | owner |
| `auth.roles.delete` | Delete roles | owner |
| `auth.roles.assign` | Assign a role to a user | owner, admin |
| `auth.roles.unassign` | Remove a role from a user | owner, admin |
| `auth.capabilities.read` | View capability definitions | owner |
| `auth.capabilities.assign` | Add a capability to a role | owner, admin |
| `auth.capabilities.unassign` | Remove a capability from a role | owner, admin |
| `auth.capabilities.manage` | Full capability lifecycle management | owner |

### 4.2 User Accounts

| Capability | Description | Default Roles |
|-----------|-------------|---------------|
| `users.profile.read` | Read own profile | owner, admin, user |
| `users.profile.update` | Update own profile | owner, admin, user |
| `users.password.change_self` | Change own password | owner, admin, user |
| `users.password.recover_self` | Initiate self-service password recovery | owner, admin, user |
| `users.accounts.read` | Read any user's account details | owner, admin |
| `users.accounts.create` | Create new user accounts | owner, admin |
| `users.accounts.update` | Update any user's account | owner, admin |
| `users.accounts.disable` | Disable a user account | owner, admin |
| `users.accounts.delete` | Permanently delete a user account | owner |

### 4.3 Cameras

Camera capabilities underwent a format migration from `snake_case` to `cameras:` namespace prefix (see §4.9).

#### Current format (`cameras:*`)

| Capability | Description | Notes |
|-----------|-------------|-------|
| `cameras:detect` | Detect available cameras | Migrated from `detect_cameras` |
| `cameras:view` | View camera list and information | Migrated from `view_cameras` |
| `cameras:connect` | Connect to cameras | Migrated from `connect_camera` |
| `cameras:disconnect` | Disconnect from cameras | Migrated from `disconnect_camera` |
| `cameras:stream:start` | Start video streaming | Migrated from `start_stream` |
| `cameras:stream:stop` | Stop video streaming | Migrated from `stop_stream` |
| `cameras:stream:view` | Access video streams | Migrated from `view_stream` |
| `cameras:record:start` | Capture snapshots / start recording | Migrated from `capture_snapshot` |
| `cameras:sessions:manage` | Manage camera sessions | Migrated from `manage_sessions` |
| `cameras:settings:update` | Configure camera parameters | Migrated from `manage_camera_settings` |
| `cameras:admin` | Administrative camera operations | Migrated from `admin_*` and `full_admin_access` |
| `cameras:configure` | Configure camera setup | Added during format migration |
| `cameras.manage` | General camera management (dot-notation) | Default admin/owner capability |
| `cameras.view` | View cameras (dot-notation) | Default in all system roles |

### 4.4 Media

| Capability | Description | Default Roles |
|-----------|-------------|---------------|
| `media.view` | View media assets | owner, admin, user |
| `media.manage` | Manage media assets | owner, admin |

### 4.5 Analytics & Workflows

| Capability | Description | Default Roles |
|-----------|-------------|---------------|
| `analytics.view` | View analytics dashboards | owner, admin, user |
| `workflows.use` | Use workflow automation features | owner, admin, user |

### 4.6 Operations

| Capability | Description | Default Roles |
|-----------|-------------|---------------|
| `operations.execute` | Execute operational tasks | owner, admin |

### 4.7 System

| Capability | Description | Default Roles |
|-----------|-------------|---------------|
| `system.installation.manage` | Manage installation configuration | owner |
| `system.licensing.manage` | Manage licenses | owner |
| `system.recovery.manage` | System recovery operations | owner |

### 4.8 Vision

| Capability | Description | Default Roles |
|-----------|-------------|---------------|
| `vision` | Access vision/computer-vision features | `vision_user` (custom role) |

### 4.9 Legacy Camera Format (deprecated)

| Old Capability | New Capability |
|---------------|----------------|
| `detect_cameras` | `cameras:detect` |
| `view_cameras` | `cameras:view` |
| `connect_camera` | `cameras:connect` |
| `disconnect_camera` | `cameras:disconnect` |
| `view_stream` | `cameras:stream:view` |
| `start_stream` | `cameras:stream:start` |
| `stop_stream` | `cameras:stream:stop` |
| `capture_snapshot` | `cameras:record:start` |
| `manage_sessions` | `cameras:sessions:manage` |
| `view_capabilities` | `cameras:view` |
| `admin_disconnect_all` | `cameras:admin` |
| `view_active_connections` | `cameras:view` |
| `manage_camera_settings` | `cameras:settings:update` |
| `admin_camera_functions` | `cameras:admin` |
| `full_admin_access` | `cameras:admin` |

---

## 5. Custom Roles

In addition to the three system roles, domain-specific roles are created via startup scripts.

### 5.1 `camera_user`

Created by `src/scripts/add_camera_capabilities.py`. Designed for users who need access to camera service endpoints for cross-service authentication.

**Assigned capabilities (new format):**
- `cameras:detect`
- `cameras:view`
- `cameras:connect`
- `cameras:disconnect`
- `cameras:stream:view`
- `cameras:stream:start`
- `cameras:stream:stop`
- `cameras:record:start`
- `cameras:sessions:manage`
- `cameras:settings:update`
- `cameras:admin`

### 5.2 `vision_user`

Created by `src/scripts/add_vision_capability.py`. Designed for users who need access to vision/computer-vision features.

**Assigned capabilities:**
- `vision`

---

## 6. Role & Capability Assignment API

All role and capability management endpoints require authentication plus specific capabilities.

### 6.1 Role Management

| Method | Route | Description | Required Capability |
|--------|-------|-------------|-------------------|
| `POST` | `/roles/` | Create a new role | `auth.roles.create` |
| `GET` | `/roles/` | List all roles | `auth.roles.read` |
| `GET` | `/roles/{role_id}` | Get role by ID | `auth.roles.read` |
| `GET` | `/roles/by-name/{role_name}` | Get role by name | `auth.roles.read` |
| `PUT` | `/roles/{role_id}` | Update role name | `auth.roles.update` |
| `DELETE` | `/roles/{role_id}` | Delete a role | `auth.roles.delete` |

### 6.2 User-Role Assignment

| Method | Route | Description | Required Capability |
|--------|-------|-------------|-------------------|
| `POST` | `/roles/assign/?user_id=&role_id=` | Assign a role to a user | `auth.roles.assign` |
| `POST` | `/roles/unassign/?user_id=&role_id=` | Remove a role from a user | `auth.roles.unassign` |

### 6.3 Role-Capability Assignment

| Method | Route | Description | Required Capability |
|--------|-------|-------------|-------------------|
| `POST` | `/roles/add-capability/` | Add a capability to a role (body: `role_id`, `capability_id`) | `auth.capabilities.assign` |
| `POST` | `/roles/remove-capability/` | Remove a capability from a role (body: `role_id`, `capability_id`) | `auth.capabilities.unassign` |

### 6.4 Capability Queries

| Method | Route | Description | Required Capability |
|--------|-------|-------------|-------------------|
| `GET` | `/capabilities/by-role/{role_id}` | List capability names for a role | `auth.capabilities.read` |
| `GET` | `/capabilities/by-user/{user_id}` | Get roles & capabilities for a user | `users.accounts.read` |
| `GET` | `/capabilities/my-capabilities` | Get current user's own roles & capabilities | None (Bearer only) |

```
### 6.5 User Profile with Roles & Capabilities

| Method | Route | Description | Required Capability |
|--------|-------|-------------|-------------------|
| `GET` | `/api/v1/users/profile` | Get current user's profile with roles & capabilities | None (Bearer only) |
| `GET` | `/api/v1/users/debug-profile` | Debug view of profile with decoded token info | None (Bearer only) |
| `GET` | `/api/v1/users/user-profile/{user_id}` | Get full profile (roles + capabilities) for any user | `users.accounts.read` |
| `POST` | `/api/v1/users/toggle-capability/{user_id}` | Toggle a capability on/off for a user across all their roles | `auth.capabilities.assign` |

---

## 7. Authorization Flow

### 7.1 `require_capability()` Dependency

Every protected endpoint uses the `require_capability(capability_name)` dependency from `src/auth_utils.py`. The authorization flow is:

```
1. Client sends request with Authorization: Bearer <JWT>
        ↓
2. get_current_user() decodes JWT, extracts user_id from "sub" claim,
   fetches User from database
        ↓
3. get_user_capability_names(db, user_id) runs:
   SELECT DISTINCT capabilities.name
   FROM capabilities
   JOIN role_capabilities ON role_capabilities.capability_id = capabilities.id
   JOIN roles ON roles.id = role_capabilities.role_id
   JOIN user_roles ON user_roles.role_id = roles.id
   WHERE user_roles.user_id = :user_id
        ↓
4. If required capability IS in the set → return current_user (200)
   If required capability IS NOT in the set → raise HTTP 403
```

### 7.2 Code-Level Usage

```python
from src.auth_utils import require_capability

@router.post("/roles/")
def api_create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user = Depends(require_capability("auth.roles.create")),
):
    # Only users with "auth.roles.create" reach here
    ...
```

### 7.3 Capability Resolution

The `user_has_capability()` function in `src/services/capabilites_service.py` resolves capabilities by traversing:

```python
user_capabilities = set()
for user_role in user.roles:                      # UserRole junction
    for role_cap in user_role.role.capabilities:  # RoleCapability junction
        user_capabilities.add(role_cap.capability.name)
```

---

## 8. Bootstrap Process

At service startup (`src/main.py`), the system seeds roles and capabilities automatically.

### 8.1 Capability Seeding

`ensure_default_capabilities()` in `src/services/role_service.py`:

1. Creates system roles (`owner`, `admin`, `user`) if they don't exist
2. Creates all capabilities from `DEFAULT_ROLE_CAPABILITIES` if they don't exist
3. Creates `RoleCapability` junction records for every (role, capability) pair

### 8.2 User Role Assignment

`ensure_exact_system_roles(db, email, role_names)` ensures a user has exactly the specified system roles:

- Adds any missing roles
- Removes any extra system roles not in the requested set
- **Safeguard:** Cannot remove the final `owner` role assignment (at least one must exist)

### 8.3 Bootstrap Users

In development mode (`ENVIRONMENT=development`), the following users are created:

| Email | Roles | Purpose |
|-------|-------|---------|
| `fresh.user@example.com` | owner, admin, user | Primary dev admin |
| `nick.glezakos@gmail.com` | admin, user | Secondary dev admin |
| `nick.glezakos@outlook.com` | user | Basic test user |

### 8.4 Authority Integration

When Authority is configured, startup consults Authority for ownership approval:

- **If approved:** `fresh.user@example.com` gets `{owner, admin, user}`
- **If not approved:** Downgraded to `{admin, user}`, Authority's owner is used instead
- **If Authority not configured:** Falls back to local owner assignment

---

## 9. Management Scripts

Scripts in `ppl-meta-node/src/scripts/` for managing capabilities:

| Script | Purpose |
|--------|---------|
| `add_camera_capabilities.py` | Creates camera capabilities (legacy snake_case), creates `camera_user` role, assigns capabilities and role to `fresh.user@example.com` |
| `add_vision_capability.py` | Creates `vision` capability, creates `vision_user` role, assigns to `fresh.user@example.com` |
| `update_camera_capabilities.py` | Migrates camera capabilities from snake_case to `cameras:*` format, adds missing essential permissions |
| `cleanup_and_recreate_camera_capabilities.py` | Deletes all old camera capabilities and role-capability assignments, recreates in `cameras:*` format |

Run a script:

```bash
cd ppl-meta-node/src
python scripts/add_camera_capabilities.py
```

Scripts are **idempotent** — they check for existing records before creating duplicates.

---

## 10. Key Constraints & Rules

1. **System roles cannot be renamed.** Attempting to rename `owner`, `admin`, or `user` raises `ValueError("System roles cannot be renamed")`.
2. **System roles cannot be deleted.** The `delete_role()` function rejects deletion of system roles.
3. **At least one owner must always exist.** The system prevents removing the last `owner` role assignment.
4. **Role names must be unique.** Creating a role with an existing name raises `ValueError("Role already exists")`.
5. **Capability names must be unique.** Duplicate capability names are prevented at the database level.
6. **User-role pairs are unique.** A user cannot be assigned the same role twice (`UNIQUE(user_id, role_id)`).
7. **Role-capability pairs are unique.** A role cannot have the same capability assigned twice (`UNIQUE(role_id, capability_id)`).
8. **Capabilities are validated by name, not by ID.** Authorization checks compare capability names as strings.
9. **Cascading deletes.** Deleting a user cascades to `user_roles`. Deleting a role cascades to `user_roles` and `role_capabilities`. Deleting a capability cascades to `role_capabilities`.
10. **All role/capability changes are logged** to `user_actions` via `log_user_action()` for audit trail.

---

## 11. Naming Conventions

| Convention | Examples | Status |
|-----------|----------|--------|
| Dot-notation | `auth.roles.create`, `users.accounts.read`, `media.manage` | **Standard** — used by system roles and default capabilities |
| Colon-notation | `cameras:view`, `cameras:stream:start`, `cameras:admin` | **Newer** — adopted for cross-service camera capabilities |
| Underscore-notation | `detect_cameras`, `manage_sessions` | **Legacy** — deprecated, migrated to colon-notation |

> **Recommendation:** Use dot-notation for auth/user/system capabilities and colon-notation for cross-service resource capabilities. Existing queries match against exact string values, so migration scripts must update both the capability name and all `RoleCapability` references.

