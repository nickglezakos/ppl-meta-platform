# Node Service User Management Implementation Plan

**Date**: May 10, 2026  
**Status**: Draft  
**Depends On**: [docs/proposals/node-user-management-roles-capabilities-analysis.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-roles-capabilities-analysis.md), [docs/proposals/node-user-management-target-design.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-target-design.md)

---

## Purpose

This document turns the Node-service user-management target design into a concrete implementation plan.

It covers:

1. endpoint-by-endpoint required capabilities
2. proposed default system roles and seeded capabilities
3. FastAPI dependency patterns for authorization enforcement
4. migration and rollout steps

The goal is to improve the current system incrementally, without a disruptive rewrite.

---

## Implementation Goals

The implementation should:

1. preserve the Node service as the authority for identity and authorization metadata
2. unify authentication and authorization utilities
3. introduce reusable capability-based enforcement at the API layer
4. formalize system roles and default capability bundles
5. protect role and capability management endpoints with explicit policy
6. support downstream services with a clean authorization contract

---

## Proposed Delivery Structure

The implementation should be delivered in four parts:

1. authorization model and seed data
2. shared auth and authorization utilities
3. endpoint enforcement updates
4. rollout, audit, and migration hardening

---

## Part 1: Authorization Model And Seed Data

### 1.1 System Roles To Seed

The following roles should be treated as system roles and ensured during startup or migration.

#### `owner`

Purpose:

- installation-level or tenant-level highest privilege

Suggested rules:

- not deletable
- not renameable
- assignment restricted to owner-level governance flow

#### `admin`

Purpose:

- operational management role

Suggested rules:

- not deletable
- not renameable
- assignable only by `owner` or by explicit owner-approved capability

#### `user`

Purpose:

- default authenticated user role

Suggested rules:

- assigned to every active account unless explicitly excluded by design
- not deletable
- not renameable

### 1.2 Capability Catalog To Seed

A default capability seed should exist and be versioned in code.

Recommended initial capabilities:

#### User Profile

- `users.profile.read`
- `users.profile.update`

#### User Account Administration

- `users.accounts.read`
- `users.accounts.create`
- `users.accounts.update`
- `users.accounts.disable`
- `users.accounts.delete`

#### Roles

- `auth.roles.read`
- `auth.roles.create`
- `auth.roles.update`
- `auth.roles.delete`
- `auth.roles.assign`
- `auth.roles.unassign`

#### Capabilities

- `auth.capabilities.read`
- `auth.capabilities.assign`
- `auth.capabilities.unassign`
- `auth.capabilities.manage`

#### Platform Administration

- `system.installation.read`
- `system.installation.manage`
- `system.licensing.read`
- `system.licensing.manage`

#### Product Access Examples

- `analytics.view`
- `cameras.view`
- `cameras.manage`
- `media.manage`

### 1.3 Default Role Bundles

#### `user`

Suggested default bundle:

- `users.profile.read`
- `users.profile.update`
- `analytics.view`
- `cameras.view`

#### `admin`

Suggested default bundle:

- all `user` capabilities
- `users.accounts.read`
- `users.accounts.create`
- `users.accounts.update`
- `users.accounts.disable`
- `auth.roles.read`

Possible optional admin bundle, depending on policy:

- `auth.roles.assign`

#### `owner`

Suggested default bundle:

- all `admin` capabilities
- `auth.roles.create`
- `auth.roles.update`
- `auth.roles.delete`
- `auth.roles.assign`
- `auth.roles.unassign`
- `auth.capabilities.read`
- `auth.capabilities.assign`
- `auth.capabilities.unassign`
- `auth.capabilities.manage`
- `system.installation.read`
- `system.installation.manage`
- `system.licensing.read`
- `system.licensing.manage`

### 1.4 Seed Strategy

Recommended implementation:

1. ensure roles exist
2. ensure capabilities exist
3. ensure required role-capability mappings exist
4. avoid deleting user-customized non-system roles automatically

The seed logic should be idempotent.

---

## Part 2: Shared Auth And Authorization Utilities

### 2.1 Consolidate Authentication Utilities

Current duplication between:

- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)
- [ppl-meta-node/src/auth_utils.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/auth_utils.py)

should be consolidated into one shared path.

Recommended target module:

- `src/auth_utils.py` or `src/security/auth.py`

Move into the shared utility layer:

1. token creation
2. token decoding
3. current-user retrieval
4. current-user role resolution
5. current-user capability resolution

### 2.2 Add Effective Authorization Context Helpers

Recommended helpers:

```python
def get_current_user(...):
    ...

def get_current_user_roles(...):
    ...

def get_current_user_capabilities(...):
    ...
```

The role and capability helpers should return normalized string sets, not ORM-heavy structures.

For example:

```python
{"admin", "user"}
```

and:

```python
{"users.accounts.read", "auth.roles.assign"}
```

### 2.3 Add FastAPI Capability Dependencies

Recommended dependency factory:

```python
def require_capability(capability_name: str):
    def dependency(capabilities = Depends(get_current_user_capabilities)):
        if capability_name not in capabilities:
            raise HTTPException(status_code=403, detail="Insufficient capability")
        return True
    return dependency
```

Recommended variants:

- `require_any_capability([...])`
- `require_all_capabilities([...])`

Optional and limited:

- `require_role(role_name)`

Role-based checks should be used only when the semantics are truly role-specific rather than permission-specific.

### 2.4 Protect System Roles In Service Layer

Role-service methods should reject invalid operations on protected system roles.

Examples:

- cannot delete `owner`
- cannot rename `admin`
- cannot remove the last `owner`

This protection should exist in the service layer even if API checks also exist.

---

## Part 3: Endpoint-Level Capability Plan

### 3.1 Users API

Primary file:

- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)

Recommended capability map:

#### Self-Service Endpoints

- current user profile read: `users.profile.read`
- current user profile update: `users.profile.update`
- current user password update: authenticated self-service, optionally no extra capability beyond authenticated user

#### Admin User Management Endpoints

- list users: `users.accounts.read`
- get arbitrary user by ID or GUID: `users.accounts.read`
- create user on behalf of others: `users.accounts.create`
- admin-set password: `users.accounts.update`
- block or disable user: `users.accounts.disable`
- delete user: `users.accounts.delete`

#### Public Auth Endpoints

These should remain accessible without existing auth context:

- register
- login
- forgot password
- reset password confirm
- email verification confirm

But they still need input validation, rate limiting, and auditability.

### 3.2 Roles API

Primary file:

- [ppl-meta-node/src/api/roles.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/roles.py)

Recommended capability map:

- list roles: `auth.roles.read`
- get role: `auth.roles.read`
- create role: `auth.roles.create`
- update role: `auth.roles.update`
- delete role: `auth.roles.delete`
- assign role to user: `auth.roles.assign`
- unassign role from user: `auth.roles.unassign`
- add capability to role: `auth.capabilities.assign`
- remove capability from role: `auth.capabilities.unassign`

### 3.3 Additional Node Administration Endpoints

Any future endpoints for:

- capability catalog management
- installation settings
- licensing-sensitive operations

should be protected from day one with explicit capabilities, not informal admin assumptions.

---

## Part 4: Concrete FastAPI Pattern

### 4.1 Example Endpoint Pattern

Recommended endpoint style:

```python
@router.get("/roles")
def api_list_roles(
    db: Session = Depends(get_db),
    _: bool = Depends(require_capability("auth.roles.read")),
):
    return list_roles(db)
```

This keeps:

- enforcement explicit
- endpoint code readable
- policy centralized in dependency helpers

### 4.2 Example Service-Layer Guard

Recommended service-layer protection for system roles:

```python
SYSTEM_ROLES = {"owner", "admin", "user"}

def ensure_mutable_role(role_name: str):
    if role_name in SYSTEM_ROLES:
        raise ValueError("System role cannot be modified this way")
```

This prevents unsafe state changes even if an endpoint is accidentally left too open.

### 4.3 Example Effective Capability Resolution

The current user’s effective capabilities should be resolved by:

1. loading user roles via `UserRole`
2. loading linked `RoleCapability` entries
3. flattening them into a deduplicated set of capability names

This should happen in one shared helper instead of being reimplemented per endpoint.

---

## Part 5: Migration And Rollout Steps

### Phase 1. Prepare The Data Model

1. verify roles and capabilities tables are present and consistent
2. add or confirm uniqueness constraints where required
3. add a `system` or equivalent marker to roles if needed

Possible enhancement:

- add `is_system` boolean to `roles`

This is not strictly required, but it would make protected role governance much cleaner than relying only on names.

### Phase 2. Seed Default Roles And Capabilities

1. ensure the capability catalog exists
2. ensure `owner`, `admin`, and `user` exist
3. ensure default mappings exist
4. ensure existing users receive a safe base role where policy requires it

### Phase 3. Consolidate Auth Utilities

1. move duplicate token and current-user logic into one shared path
2. update callers to consume the shared path
3. remove duplicate implementations after validation

### Phase 4. Introduce Capability Dependencies

1. implement `require_capability(...)`
2. implement role/capability resolution helpers
3. add tests for successful and forbidden access

### Phase 5. Protect Admin Endpoints

1. apply capability dependencies to roles API
2. apply capability dependencies to admin user endpoints
3. enforce service-layer protection for system roles

### Phase 6. Add Audit Trail

1. log privilege changes
2. log role assignment changes
3. log capability assignment changes
4. log blocked attempts on protected system roles

### Phase 7. Cross-Service Integration

1. define the downstream service contract
2. decide whether services use rich JWT, live lookup, or hybrid
3. keep sensitive operations capable of live authorization revalidation

---

## Part 6: Recommended Tests

### Authorization Unit Tests

Add tests for:

1. user with required capability succeeds
2. user without required capability gets `403`
3. system role cannot be deleted
4. last owner cannot be removed
5. capability resolution correctly aggregates through multiple roles

### API Integration Tests

Add tests for:

1. login returns valid token
2. protected role endpoints reject unauthenticated access
3. protected role endpoints reject underprivileged users
4. owner-level operations succeed for owners
5. self-service endpoints remain usable for baseline users

### Migration Safety Tests

Add tests for:

1. seeding is idempotent
2. existing custom roles are preserved
3. existing users are not orphaned from baseline access

---

## Part 7: Risks And Mitigations

### Risk 1. Breaking Existing Admin Flows

If capability checks are introduced too abruptly, existing admin screens or automation may break.

Mitigation:

- seed admin capabilities before enforcement
- roll out in phases
- test current admin workflows before lock-down

### Risk 2. Hidden Dependencies On Role Names

Current code may depend on role-name conventions in more places than are obvious.

Mitigation:

- search for role-name string usage before rollout
- preserve current names while moving enforcement to capabilities

### Risk 3. Over-Centralizing Slow Lookups

If every service must call back to Node for every request, latency may grow.

Mitigation:

- use hybrid authorization context
- keep high-risk operations capable of live revalidation

### Risk 4. Privilege Escalation Through Misconfigured Role Assignment

Even with capabilities, role assignment itself is a privileged operation.

Mitigation:

- strictly protect assignment endpoints
- audit changes
- service-layer protect system roles

---

## Recommended First Implementation Slice

The smallest valuable first slice is:

1. consolidate auth utilities
2. seed `owner`, `admin`, `user`
3. seed the initial capability catalog
4. add `require_capability(...)`
5. protect the roles API with capability checks
6. block deletion or rename of system roles

This slice gives immediate security value without requiring full downstream service redesign.

---

## Proposed Outcome

After implementation, the platform should have:

1. one shared authentication and authorization utility layer in Node
2. capability-based enforcement on sensitive endpoints
3. protected system roles with explicit lifecycle rules
4. seeded and documented default role bundles
5. a clean path for downstream services to consume authorization context

That is the practical next maturity step for the current Node-service user-management system.

---

## Reference Files

- [docs/proposals/node-user-management-roles-capabilities-analysis.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-roles-capabilities-analysis.md)
- [docs/proposals/node-user-management-target-design.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-target-design.md)
- [ppl-meta-node/src/models/user.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/user.py)
- [ppl-meta-node/src/models/role.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/role.py)
- [ppl-meta-node/src/services/user_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/user_service.py)
- [ppl-meta-node/src/services/role_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/role_service.py)
- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)
- [ppl-meta-node/src/api/roles.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/roles.py)
- [ppl-meta-node/src/auth_utils.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/auth_utils.py)