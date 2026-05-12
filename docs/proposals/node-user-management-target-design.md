# Node Service User Management Target Design

**Date**: May 10, 2026  
**Status**: Draft  
**Depends On**: [docs/proposals/node-user-management-roles-capabilities-analysis.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-roles-capabilities-analysis.md)

---

## Purpose

This proposal turns the current-state analysis into a target design for user management and authorization in the Node service.

It focuses on four areas:

1. system roles
2. capability naming and assignment model
3. protection of admin and authorization-management endpoints
4. cross-service authorization flow

The goal is to keep the Node service as the authority for user management while making authorization predictable, enforceable, and easier to extend across the platform.

---

## Design Goals

The target design should achieve the following:

1. keep identity, roles, and capabilities owned by the Node service
2. make capabilities the primary enforcement primitive
3. treat roles as stable bundles of capabilities
4. formalize system-role lifecycle rules
5. protect authorization-management operations with explicit policy
6. give other services a clear and safe way to consume user authorization context
7. support future expansion without relying on hardcoded string conventions everywhere

---

## Recommended Authorization Model

The recommended model is:

- **Users** are authenticated identities
- **Roles** are curated bundles of capabilities
- **Capabilities** are the actual permissions enforced at runtime

In other words:

- users do not directly define the security model
- role names do not directly define endpoint access
- capabilities are the final runtime authorization contract

This means a route should conceptually ask:

- does this user have capability `x`?

not:

- is this user an `admin`?

Roles still matter, but mainly for assignment and administration.

---

## System Roles

### Why System Roles Need To Be Explicit

The platform already behaves as if some roles are special, such as `owner`, `admin`, and `user`.

The target design should formalize them as **system roles** with explicit semantics and lifecycle rules.

### Proposed Core System Roles

#### 1. `owner`

Purpose:

- highest-privilege platform role
- intended for installation or tenant ownership, not daily operations by default

Semantics:

- can manage all roles, capabilities, and users
- can recover platform access when normal admin flows fail
- can manage licensing-sensitive and installation-sensitive operations

Lifecycle rules:

- bootstrap-assigned to the first user or explicit installation owner
- should not be casually reassigned
- should not be deletable from the system
- role rename should be disallowed
- removing the final owner should be blocked

#### 2. `admin`

Purpose:

- operational administration role for platform management

Semantics:

- can manage users and most configuration
- can assign many roles and capabilities depending on policy
- should not automatically equal `owner`

Lifecycle rules:

- assignable by `owner`
- optionally assignable by another `admin` only if a capability explicitly allows it
- role rename should be disallowed
- deletion should be disallowed if this is a system role

#### 3. `user`

Purpose:

- baseline authenticated platform user role

Semantics:

- grants default self-service and normal product access

Lifecycle rules:

- should normally be assigned to every active account
- role rename should be disallowed
- deletion should be disallowed if this is a system role

### Optional Future System Roles

Depending on product direction, the following may eventually become system roles or at least standardized roles:

- `support`
- `marketing`
- `operator`
- `viewer`
- `installer`

These should only become system roles if the platform truly depends on them semantically. Otherwise they can remain normal managed roles.

---

## Capability Naming Model

### Naming Principles

Capability names should be:

1. stable
2. action-oriented
3. domain-scoped
4. readable by humans and services

Recommended pattern:

```text
<domain>.<resource>.<action>
```

Examples:

- `users.profile.read`
- `users.profile.update`
- `users.accounts.create`
- `users.accounts.disable`
- `auth.roles.read`
- `auth.roles.assign`
- `auth.roles.manage`
- `auth.capabilities.read`
- `auth.capabilities.manage`
- `analytics.view`
- `cameras.control.start_detection`
- `cameras.control.stop_detection`
- `system.licensing.manage`
- `system.installation.manage`

### Capability Categories

For clarity and long-term governance, capabilities should fall into broad categories.

#### Identity And Account

- `users.profile.read`
- `users.profile.update`
- `users.accounts.read`
- `users.accounts.create`
- `users.accounts.update`
- `users.accounts.disable`
- `users.accounts.delete`

#### Role And Capability Governance

- `auth.roles.read`
- `auth.roles.create`
- `auth.roles.update`
- `auth.roles.delete`
- `auth.roles.assign`
- `auth.roles.unassign`
- `auth.capabilities.read`
- `auth.capabilities.assign`
- `auth.capabilities.unassign`
- `auth.capabilities.manage`

#### Administrative Or Installation Scope

- `system.installation.read`
- `system.installation.manage`
- `system.licensing.read`
- `system.licensing.manage`
- `system.support.impersonate`

#### Product Domains

Examples only, to be expanded per product area:

- `analytics.view`
- `media.manage`
- `cameras.view`
- `cameras.manage`
- `cameras.control.start_detection`
- `cameras.control.stop_detection`
- `signage.manage`

### Capability Rules

Recommended governance rules:

1. capability names should be immutable once introduced in stable use
2. roles may change membership, but capabilities should remain the durable contract
3. endpoints should require capabilities, not role names
4. capability names should be documented in one central reference

---

## Role Design Strategy

### Roles As Bundles

Each role should represent a deliberate bundle of capabilities.

Examples:

#### `user`

Could include:

- `users.profile.read`
- `users.profile.update`
- `analytics.view`
- `cameras.view`

#### `admin`

Could include:

- all `user` capabilities
- `users.accounts.read`
- `users.accounts.create`
- `users.accounts.update`
- `users.accounts.disable`
- `auth.roles.read`
- `auth.roles.assign`

#### `owner`

Could include:

- all `admin` capabilities
- `auth.roles.manage`
- `auth.capabilities.manage`
- `system.installation.manage`
- `system.licensing.manage`

### Recommended Constraints

1. do not make every role a special case in code
2. keep system roles documented and protected
3. allow non-system custom roles for business-specific delegation
4. prevent mutation of critical platform roles without explicit owner-level permission

---

## Admin And Authorization Management Endpoints

### Problem To Solve

Endpoints that create roles, assign roles, or attach capabilities are themselves security-critical operations.

They must not be protected only by being obscure or by ad hoc assumptions.

### Recommended Protection Rules

The following endpoint groups should require explicit capabilities.

#### User Account Management

- list users: `users.accounts.read`
- create user: `users.accounts.create`
- update user: `users.accounts.update`
- disable/block user: `users.accounts.disable`
- delete user: `users.accounts.delete`

#### Role Management

- list roles: `auth.roles.read`
- create role: `auth.roles.create`
- update role: `auth.roles.update`
- delete role: `auth.roles.delete`
- assign role: `auth.roles.assign`
- unassign role: `auth.roles.unassign`

#### Capability Management

- view capabilities: `auth.capabilities.read`
- add capability to role: `auth.capabilities.assign`
- remove capability from role: `auth.capabilities.unassign`
- create or redefine capabilities: `auth.capabilities.manage`

### Additional Governance Rules

These operations should also have policy rules beyond simple capability checks.

Examples:

1. an `admin` may assign normal operational roles but not `owner`
2. only `owner` may modify system-role definitions
3. deletion of system roles should be blocked entirely
4. role assignment changes should be auditable

---

## Cross-Service Authorization Flow

### Current Need

Other services in the platform already depend on Node-issued authentication or user context. The target design should make that consumption model explicit.

### Recommended Flow

#### Step 1. Node Authenticates The User

Node remains responsible for:

- login
- token issuance
- token refresh if applicable
- recovery of authoritative user identity

#### Step 2. Node Resolves Effective Authorization Context

At request-time or token-issue time, Node should be able to resolve:

- user identity
- assigned roles
- effective capabilities

#### Step 3. Services Consume Trusted Identity Context

Other services should not invent their own role or capability semantics.

Recommended model:

- Node remains the authority
- downstream services consume trusted user claims or call a central authorization context endpoint if needed

### Two Viable Patterns

#### Pattern A. Rich JWT Claims

JWT contains:

- user ID
- role list
- capability list or compact capability claims

Advantages:

- fast local authorization in downstream services
- fewer lookup calls per request

Tradeoffs:

- token size grows
- privilege changes may not reflect until token refresh or reissue

#### Pattern B. Thin JWT + Server-Side Authorization Resolution

JWT contains only identity basics, and services resolve capabilities from Node or a shared auth layer.

Advantages:

- changes take effect immediately or faster
- claims stay smaller

Tradeoffs:

- more runtime coupling
- more latency if every service must call back for authorization context

### Recommended Hybrid Model

Use a hybrid model:

1. token contains identity and compact role claims
2. critical services can resolve effective capabilities from Node when needed
3. high-risk operations should prefer live server-side authorization checks

This gives reasonable performance while avoiding stale-privilege problems on the most sensitive operations.

---

## Recommended Shared Authorization Utilities

The Node service should eventually expose a clean internal utility model like this:

- `get_current_user()`
- `get_current_user_roles()`
- `get_current_user_capabilities()`
- `require_capability(capability_name)`
- `require_any_capability([...])`
- `require_role(role_name)` only when role semantics are truly intended

This gives endpoint authors a standard enforcement path.

---

## Audit And Change Tracking

Privilege changes should be auditable.

Recommended events to log:

- role created
- role updated
- role deleted
- role assigned to user
- role removed from user
- capability assigned to role
- capability removed from role
- system-role modification attempt

Minimum audit fields:

- actor user ID
- target user ID or target role ID
- action type
- timestamp
- old value
- new value
- request correlation or trace ID if available

Without this, role and capability governance will remain operationally weak even if the data model improves.

---

## Recommended Rollout Phases

### Phase 1. Stabilize The Contract

1. document system roles
2. define initial capability namespace
3. consolidate auth utility code paths

### Phase 2. Protect Critical Endpoints

1. add explicit capability checks to roles and capabilities endpoints
2. add explicit capability checks to user-management admin endpoints
3. block deletion or mutation of protected system roles

### Phase 3. Add Effective Authorization Context

1. centralize role and capability resolution
2. expose reusable dependency helpers
3. make services consume the same effective authorization contract

### Phase 4. Add Auditability And Recovery Rules

1. privilege-change audit trail
2. owner recovery flow
3. explicit rules for protected role lifecycle

---

## Target-State Outcome

If the target design is followed, the platform should end up with:

1. Node as the undisputed authority for users, roles, and capabilities
2. roles used for delegation and administration
3. capabilities used for actual access enforcement
4. protected system roles with clear lifecycle rules
5. explicit admin endpoint protection
6. a consistent cross-service authorization consumption model

This is the right maturity direction for the existing Node-based user-management architecture.

---

## Proposed Next Concrete Deliverables

The most practical next implementation proposals after this document are:

1. a system-roles specification with immutable-role policy
2. a capability catalog for current platform domains
3. an authorization dependency design for FastAPI endpoints in Node
4. an audit model for privilege changes

---

## Reference Baseline

This target design builds on:

- [docs/proposals/node-user-management-roles-capabilities-analysis.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-roles-capabilities-analysis.md)
- [ppl-meta-node/src/models/user.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/user.py)
- [ppl-meta-node/src/models/role.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/role.py)
- [ppl-meta-node/src/services/user_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/user_service.py)
- [ppl-meta-node/src/services/role_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/role_service.py)
- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)
- [ppl-meta-node/src/api/roles.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/roles.py)
- [ppl-meta-node/src/auth_utils.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/auth_utils.py)