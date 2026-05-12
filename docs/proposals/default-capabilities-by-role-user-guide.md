# Default Capabilities By Role User Guide

**Date**: May 10, 2026  
**Status**: Draft  
**Related Documents**: [docs/proposals/node-user-management-roles-capabilities-analysis.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-roles-capabilities-analysis.md), [docs/proposals/node-user-management-target-design.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-target-design.md), [docs/proposals/node-user-management-implementation-plan.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-implementation-plan.md)

---

## Purpose

This guide explains the default platform roles and the capabilities each role is expected to have.

It is written from a user and administrator point of view rather than an API point of view.

The goal is to make it clear:

1. what a normal user can do by default
2. what an administrator can do by default
3. what only an owner should be allowed to do

This guide is intended to help product, operations, and engineering teams align on role expectations before or during implementation.

---

## How To Read This Guide

The platform authorization model should be understood in three layers:

1. **Users** are the people who sign in to the platform
2. **Roles** are default bundles of access
3. **Capabilities** are the specific permissions granted to a role

In practice, a role answers this question:

- what is this type of user allowed to do by default?

Capabilities are the precise permissions used to enforce that answer.

---

## Default Roles

The default platform role model should contain three core roles:

1. `user`
2. `admin`
3. `owner`

These roles represent increasing levels of authority.

### `user`

This is the baseline role for a normal authenticated person using the platform.

This role should allow the user to:

- sign in
- manage their own account details
- view the parts of the product they are expected to use
- access normal workflows without being able to administer other users or the platform

### `admin`

This is the operational management role.

This role should allow the user to:

- do everything a normal user can do
- manage other user accounts
- manage shared platform resources and operational settings
- perform day-to-day administrative work

This role should not automatically imply platform ownership.

### `owner`

This is the highest-privilege platform role.

This role should allow the user to:

- do everything an admin can do
- govern roles and capabilities
- control installation-level and licensing-sensitive settings
- recover or re-establish platform control when needed

This role should be tightly controlled.

---

## Functional Areas

Default capabilities should be derived from user-facing functional areas rather than from backend routes alone.

The main functional areas are:

1. account and identity
2. product usage
3. operational administration
4. authorization governance
5. installation and recovery governance

---

## Role Summary

### What A `user` Can Do By Default

A default `user` should be able to:

- sign in and use the platform
- view and update their own profile
- change their own password
- recover access to their own account
- view dashboards and analytics they are allowed to see
- view cameras, collections, media, and results they are allowed to access
- use ordinary product workflows

A default `user` should not be able to:

- create or manage other user accounts
- disable users
- assign roles
- change role definitions
- change capability definitions
- manage installation-level settings

### What An `admin` Can Do By Default

A default `admin` should be able to:

- do everything a `user` can do
- view user accounts
- create user accounts
- update user accounts
- disable user accounts
- manage shared operational resources such as cameras, media, and platform settings that are part of normal administration

A default `admin` may also be allowed to:

- view roles
- assign or remove selected roles

That depends on governance policy.

A default `admin` should not automatically be allowed to:

- create or delete system roles
- manage the full capability catalog
- take installation-ownership actions
- perform licensing or recovery governance actions reserved for `owner`

### What An `owner` Can Do By Default

A default `owner` should be able to:

- do everything an `admin` can do
- create, update, and delete roles according to platform rules
- assign and remove roles from users
- assign and remove capabilities from roles
- manage the capability catalog
- manage installation-level settings
- manage licensing-sensitive settings
- perform recovery or ownership-level governance actions

---

## Default Capabilities Matrix

The following table gives a high-level mapping from user-facing functionality to default role access.

| Functionality | `user` | `admin` | `owner` | Example Capability |
|---|---:|---:|---:|---|
| Sign in and use session | Yes | Yes | Yes | `auth.session.use` |
| View own profile | Yes | Yes | Yes | `users.profile.read` |
| Update own profile | Yes | Yes | Yes | `users.profile.update` |
| Change own password | Yes | Yes | Yes | `users.password.change_self` |
| Recover own access | Yes | Yes | Yes | `users.password.recover_self` |
| View dashboards and analytics | Yes | Yes | Yes | `analytics.view` |
| View assigned cameras and collections | Yes | Yes | Yes | `cameras.view` |
| View allowed media and results | Yes | Yes | Yes | `media.view` |
| Use ordinary workflows | Yes | Yes | Yes | `workflows.use` |
| Execute allowed operations | No | Yes | Yes | `operations.execute` |
| View user list | No | Yes | Yes | `users.accounts.read` |
| Create users | No | Yes | Yes | `users.accounts.create` |
| Update other users | No | Yes | Yes | `users.accounts.update` |
| Disable users | No | Yes | Yes | `users.accounts.disable` |
| Delete users | No | Optional | Yes | `users.accounts.delete` |
| View roles | No | Optional | Yes | `auth.roles.read` |
| Assign roles to users | No | Optional | Yes | `auth.roles.assign` |
| Remove roles from users | No | Optional | Yes | `auth.roles.unassign` |
| Create roles | No | No | Yes | `auth.roles.create` |
| Update role definitions | No | No | Yes | `auth.roles.update` |
| Delete roles | No | No | Yes | `auth.roles.delete` |
| View capability catalog | No | Optional | Yes | `auth.capabilities.read` |
| Assign capabilities to roles | No | No | Yes | `auth.capabilities.assign` |
| Remove capabilities from roles | No | No | Yes | `auth.capabilities.unassign` |
| Manage capability catalog | No | No | Yes | `auth.capabilities.manage` |
| Manage cameras and shared operational settings | No | Yes | Yes | `cameras.manage` |
| Manage media and shared operational settings | No | Yes | Yes | `media.manage` |
| Manage installation-wide settings | No | No | Yes | `system.installation.manage` |
| Manage licensing | No | No | Yes | `system.licensing.manage` |
| Perform platform recovery governance | No | No | Yes | `system.recovery.manage` |

---

## Suggested Default Capability Bundles

### Default Bundle For `user`

Suggested baseline capabilities:

- `auth.session.use`
- `users.profile.read`
- `users.profile.update`
- `users.password.change_self`
- `users.password.recover_self`
- `analytics.view`
- `cameras.view`
- `media.view`
- `workflows.use`

This bundle is intended to support normal platform usage without any administrative authority.

### Default Bundle For `admin`

Suggested baseline capabilities:

- all `user` capabilities
- `users.accounts.read`
- `users.accounts.create`
- `users.accounts.update`
- `users.accounts.disable`
- `cameras.manage`
- `media.manage`
- `operations.execute`

Optional administrative capabilities, depending on policy:

- `users.accounts.delete`
- `auth.roles.read`
- `auth.roles.assign`
- `auth.roles.unassign`
- `auth.capabilities.read`

This bundle is intended for operational management, not full platform governance.

### Default Bundle For `owner`

Suggested baseline capabilities:

- all `admin` capabilities
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
- `system.installation.manage`
- `system.licensing.manage`
- `system.recovery.manage`

This bundle is intended for platform governance and ownership-level control.

---

## Recommended Governance Rule

The safest default governance rule is:

- `user` handles self-service and ordinary product usage
- `admin` handles operations and account administration
- `owner` handles authorization governance, installation control, licensing, and recovery

This avoids giving normal administrators silent control over the platform security model.

If the platform later needs delegated security administration, that should be introduced deliberately through additional capabilities rather than by broadening `admin` by default.

---

## Typical Questions

### Should every authenticated account get the `user` role?

Usually yes.

That keeps the baseline experience predictable and avoids repeated special-case checks for ordinary access.

### Should `admin` be able to assign roles?

Only if the platform explicitly wants delegated authorization administration.

The safer default is to keep role and capability governance with `owner`.

### Should `owner` be treated as a normal daily-use role?

No.

The `owner` role should exist for governance, recovery, and installation-sensitive control. Daily operational work should usually happen through `admin`.

### Should capability names match backend endpoints?

Not directly.

Capabilities should describe stable business permissions. Multiple endpoints may depend on the same capability.

---

## Recommended Next Step

Use this guide as the human-readable reference, then implement the technical seed data and enforcement rules described in:

- [docs/proposals/node-user-management-target-design.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-target-design.md)
- [docs/proposals/node-user-management-implementation-plan.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-implementation-plan.md)

This keeps the user-facing role model and the backend authorization implementation aligned.