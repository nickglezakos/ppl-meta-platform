# Node Service User Management: Roles And Capabilities Analysis

**Date**: May 10, 2026  
**Status**: Draft  
**Scope**: Current-state analysis and proposal for user-management, role assignment, and capability assignment in the Node service

---

## Purpose

This proposal analyses the current user-management implementation in the Node service and focuses specifically on:

1. where user management currently lives
2. how roles are modeled and assigned
3. how capabilities are modeled and assigned
4. where enforcement currently happens and where it does not
5. what architectural and operational gaps exist
6. what a safer next-step direction should be

This is a current-state and improvement proposal, not an implementation plan for a full authorization rewrite.

---

## Executive Summary

The Node service is the authoritative service for user management, authentication, and the current RBAC data model.

Today the implementation provides a usable structural base for authorization:

- users exist as first-class records
- roles exist as separate records
- capabilities exist as separate records
- user-to-role and role-to-capability relations exist in the database
- login is JWT-based and user identity is recoverable from tokens

However, the current system is only partially realized as a true authorization model.

The main issue is that the data model supports roles and capabilities, but most runtime authorization still behaves like plain authentication plus a few implicit conventions. In practical terms:

- the system knows what roles and capabilities are
- the system can assign them
- but the system does not consistently enforce them at endpoint and service boundaries

This creates a gap between the intended access-control design and the currently effective behavior.

---

## Current Ownership And Service Boundary

User management currently lives in the Node service.

Primary implementation surfaces:

- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)
- [ppl-meta-node/src/services/user_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/user_service.py)
- [ppl-meta-node/src/models/user.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/user.py)

Primary role and capability surfaces:

- [ppl-meta-node/src/models/role.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/role.py)
- [ppl-meta-node/src/services/role_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/role_service.py)
- [ppl-meta-node/src/api/roles.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/roles.py)

Authentication utilities also exist in:

- [ppl-meta-node/src/auth_utils.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/auth_utils.py)

This means the Node service is already the natural authority for:

- identity records
- login and token issuance
- role membership
- capability membership

That is the correct service boundary. The main problems are inside consistency and enforcement, not service placement.

---

## Current Data Model

### User Model

The `User` entity includes standard account fields such as:

- `guid`
- `username`
- `email`
- password hash
- profile fields
- active and blocked flags
- login metadata

Reference:

- [ppl-meta-node/src/models/user.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/user.py)

Observations:

- the user model is adequate for core account management
- the model is identity-focused rather than authorization-focused
- authorization context is delegated to linked role records

### Role Model

The current role model consists of:

- `Role`
- `UserRole`

Reference:

- [ppl-meta-node/src/models/role.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/role.py)

This is a normal many-to-many RBAC structure.

Observations:

- role names are stored as mutable strings
- there is no built-in hierarchy or semantic classification of roles
- role semantics are implicit in service logic and naming conventions

### Capability Model

The current capability model consists of:

- `Capability`
- `RoleCapability`

Reference:

- [ppl-meta-node/src/models/role.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/role.py)

This is structurally the right direction for fine-grained authorization.

Observations:

- capabilities are modeled as assignable units
- capabilities are attached to roles, not directly to users
- the data model supports fine-grained permissions better than the runtime currently uses them

---

## Current Assignment Flow

### User Creation

The user-creation path is implemented in:

- [ppl-meta-node/src/services/user_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/user_service.py)

Important behavior:

- standard user creation hashes the password and writes the user
- `create_user_with_licensing` adds special first-user handling
- the first user is treated as the owner path when licensing is available

This is an important current system rule:

- the platform bootstraps its first privileged identity implicitly

This is convenient operationally, but it also means the highest-privilege assignment path is partly encoded as startup or first-user behavior rather than an explicit governance workflow.

### Role Assignment

Role assignment is managed in:

- [ppl-meta-node/src/services/role_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/role_service.py)
- [ppl-meta-node/src/api/roles.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/roles.py)

Current capabilities include:

- create role
- list role
- update role
- delete role
- assign role to user
- unassign role from user

There are also implicit/default bootstrap helpers such as:

- `ensure_admin_role`
- `ensure_user_role`

Observations:

- roles can be managed centrally
- default role assignment behavior exists
- but role governance rules are not clearly expressed as policy

Examples of missing policy clarity:

- who is allowed to assign `admin`
- who is allowed to assign `owner`
- whether some roles are system roles that should not be renamed or deleted
- whether every user must always have a base role

### Capability Assignment

Capability assignment is also handled in the role service and roles API.

Current operations include:

- add capability to role
- remove capability from role

There is also a startup/default helper:

- `ensure_default_capabilities`

Observations:

- capabilities are intended to be centrally managed through roles
- this is conceptually sound
- but the capability layer is still more declarative than operative in day-to-day enforcement

---

## Current Authentication Flow

JWT token creation and current-user recovery are implemented in two places:

- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)
- [ppl-meta-node/src/auth_utils.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/auth_utils.py)

This is one of the clearest current consistency issues.

Observations:

- token creation logic exists in more than one place
- `get_current_user` exists in more than one place
- this creates drift risk between auth behavior and authorization behavior

The practical consequence is not only duplication. It also makes it harder to establish one authoritative access-control dependency stack such as:

- authenticate user
- resolve effective roles
- resolve effective capabilities
- enforce route requirement

At the moment the system reliably authenticates the user, but it does not yet consistently elevate that into unified authorization context.

---

## Current Enforcement Reality

### What Is Working

The current implementation already supports:

- account creation
- password hashing
- email-oriented identity
- JWT-based authentication
- persistent role assignment
- persistent capability assignment through roles

### What Is Not Fully Working As Authorization

The capability and role model are not yet consistently enforced as runtime policy.

This is the main gap.

More specifically:

1. there is no clear central authorization dependency that checks required capabilities
2. role membership does not appear to be the standard enforcement primitive on protected endpoints
3. capabilities exist in the schema but are not yet clearly the normal access gate for service operations
4. role and capability data are easier to assign than to trust as effective policy

This means the system is currently closer to:

- authenticated user management with RBAC metadata

than to:

- fully enforced role-and-capability authorization

---

## Specific Current-State Issues

### 1. Authentication And Authorization Are Too Tightly Blended

Current `get_current_user` flows mainly answer:

- who is this user?

They do not consistently answer:

- what is this user allowed to do?

That distinction is critical.

Proposal implication:

- authentication dependencies should remain simple
- authorization dependencies should become explicit and reusable

### 2. Duplicate Auth Utilities Create Drift Risk

There is duplicated token and current-user logic between:

- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)
- [ppl-meta-node/src/auth_utils.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/auth_utils.py)

Risks:

- inconsistent token contents
- inconsistent decode rules
- inconsistent future role/capability enrichment

Proposal implication:

- consolidate onto one shared authentication and authorization utility path

### 3. Role Semantics Are Convention-Based

Roles such as `admin`, `user`, and `owner` appear to be treated specially by convention.

That is workable in an early system, but weak for long-term governance.

Risks:

- hidden privilege assumptions
- hardcoded role-name dependence
- inability to reason cleanly about what a role guarantees

Proposal implication:

- preserve system roles, but explicitly define them as platform-controlled roles with stable semantics

### 4. Capability Layer Is Under-Enforced

The schema already supports capabilities, but the runtime model does not yet appear to rely on them as the standard authorization contract.

Risks:

- false confidence that fine-grained authorization exists because the tables exist
- role explosion if teams compensate by creating more coarse roles instead of enforcing capabilities
- inconsistent access checks across services

Proposal implication:

- capabilities should become the preferred enforcement primitive
- roles should remain grouping and delegation mechanisms

### 5. Bootstrap Rules Need Policy Definition

The first-user or startup bootstrap logic is useful, but it also encodes privilege rules operationally.

Questions that should become explicit policy:

- what exactly does `owner` mean?
- can there be more than one owner?
- who can create another owner?
- can owner be removed or renamed?
- what happens in recovery scenarios?

Proposal implication:

- keep bootstrap logic, but formalize it with system-role rules and recovery procedures

### 6. Roles API Governance Is Not Clearly Protected

The roles API currently exposes powerful operations:

- create roles
- delete roles
- assign roles
- attach capabilities

Those operations are structurally important enough that they should be protected by explicit authorization rules. The current code path shown here does not itself demonstrate such enforcement.

Proposal implication:

- the roles and capability management endpoints should become some of the most tightly protected endpoints in the platform

### 7. Validation Is Partly Transitional

The users API currently includes simplified validation replacement helpers.

Reference:

- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)

This suggests that validation consistency is not fully stabilized.

Proposal implication:

- authorization reform should not be built on partially ad hoc validation paths
- user, role, and capability management inputs should use one stable schema validation approach

---

## Capability And Role Assignment Assessment

### Current Strengths

The current assignment design already has several good properties:

1. user-to-role assignment is explicit and relational
2. role-to-capability assignment is explicit and relational
3. the design can support least-privilege access if enforcement is added consistently
4. the model is service-owned in the right place, the Node service

### Current Weaknesses

The current design also has major operational weaknesses:

1. assignment is easier than policy enforcement
2. system-critical roles are not clearly protected as immutable or semi-immutable platform roles
3. effective permissions are not clearly surfaced in auth context
4. the platform likely still depends on endpoint-local conventions more than centralized authorization policy

### Net Assessment

The current role/capability assignment model is good enough as a storage model, but not yet good enough as the platform’s final authorization model.

The architecture should evolve, but it should evolve by strengthening enforcement and governance around the existing model rather than replacing it wholesale.

---

## Proposed Direction

### Principle 1. Keep Node As The Authority

Do not move user, role, or capability ownership away from Node.

Node should remain authoritative for:

- user lifecycle
- login and token issuance
- role membership
- capability membership
- authorization context construction

### Principle 2. Make Capabilities The Enforcement Primitive

Recommended model:

- roles are bundles of capabilities
- capabilities are what endpoints and services actually require

This avoids overloading role names as the real security policy.

### Principle 3. Preserve System Roles, But Define Them Explicitly

Roles such as `owner`, `admin`, and `user` should be treated as system roles with documented semantics.

At minimum, define:

- intended meaning
- allowed assigners
- whether rename is allowed
- whether delete is allowed
- whether multiple assignments are allowed

### Principle 4. Centralize Authorization Dependencies

Introduce one canonical dependency chain that can support:

1. `get_current_user`
2. `get_current_user_roles`
3. `get_current_user_capabilities`
4. `require_role(...)`
5. `require_capability(...)`

Even if implementation is phased, this should be the target structure.

### Principle 5. Separate Bootstrap From Daily Governance

The first-user bootstrap rule can remain, but it should be clearly documented as initialization behavior, not as the general model for privilege assignment.

### Principle 6. Protect Role And Capability Management Endpoints

Management endpoints for roles and capabilities should require explicit privileged capabilities, for example:

- `user.roles.read`
- `user.roles.assign`
- `user.roles.manage`
- `user.capabilities.manage`

The exact names can be decided later, but the pattern should be explicit.

---

## Recommended Next-Step Work Packages

### Work Package 1. Current-State Documentation

Document:

- system roles
- current default capabilities
- bootstrap behavior
- ownership rules for assigning high-privilege roles

### Work Package 2. Auth Utility Consolidation

Unify duplicated auth/token utilities into one shared implementation path.

### Work Package 3. Effective Authorization Context

Add a central mechanism that resolves a user’s effective roles and capabilities at request time.

### Work Package 4. Protected Management Endpoints

Require explicit authorization for:

- role creation
- role deletion
- role assignment
- capability assignment

### Work Package 5. System Role Governance

Define the lifecycle rules for:

- `owner`
- `admin`
- `user`

### Work Package 6. Cross-Service Consumption Contract

Define how other services should consume Node-issued identity and authorization context, especially if services need either:

- direct capability checks
- or trusted forwarded user claims from Gateway or Node

---

## Suggested Policy Questions To Resolve

Before implementation changes, the platform should answer these questions explicitly:

1. Is `owner` a bootstrap-only role or a normal assignable role?
2. Can the platform have multiple owners?
3. Is `admin` global across all services, or scoped to selected domains?
4. Are capabilities the source of truth for authorization, or only metadata on roles?
5. Should services trust JWT claims for capabilities, or should they resolve capabilities server-side?
6. Which role and capability operations are allowed in production versus only at initialization time?
7. What audit trail is required for privilege changes?

---

## Proposed Conclusion

The current Node-service user-management architecture is directionally correct but operationally incomplete.

It already has the right ownership boundary and the right relational building blocks:

- users
- roles
- capabilities
- assignment tables

The key limitation is that runtime enforcement and governance have not yet caught up with the model.

So the recommendation is not to redesign the system from scratch. The recommendation is to mature the current design by:

1. consolidating auth utilities
2. formalizing system-role policy
3. shifting enforcement toward capabilities
4. protecting role and capability management endpoints
5. documenting and governing bootstrap privilege behavior

That path preserves current investment while making role and capability assignment trustworthy as actual platform controls.

---

## Reference Files

- [ppl-meta-node/src/models/user.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/user.py)
- [ppl-meta-node/src/models/role.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/models/role.py)
- [ppl-meta-node/src/services/user_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/user_service.py)
- [ppl-meta-node/src/services/role_service.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/services/role_service.py)
- [ppl-meta-node/src/api/v1/users.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/v1/users.py)
- [ppl-meta-node/src/api/roles.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/api/roles.py)
- [ppl-meta-node/src/auth_utils.py](/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-node/src/auth_utils.py)