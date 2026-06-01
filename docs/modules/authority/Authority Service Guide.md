# Authority Service Guide

> **Service**: `ppl-meta-authority`  
> **Role in Platform**: installation lifecycle control plane, user onboarding authority, and role-scoped admin workspace  
> **Primary UI**: `/admin` and `/admin/console`  
> **Primary Audience**: platform admins, distributors, resellers, owners, and support operators

---

## 1. Overview

The Authority service is the control plane for installation access, licensing, onboarding, and role-scoped administration in the PPL Meta platform.

At a high level, it answers five core questions:

1. Who is allowed to access the platform and in what role?
2. Which business scope does that user belong to?
3. Which entitlements and installations exist for that scope?
4. What is the current state of those installations?
5. Which administrative actions have happened, and who performed them?

Authority is where operators manage the lifecycle of users, invitations, entitlements, assignments, installation activation, and audit visibility. It is not just an authentication service. It is the governance surface for how commercial access and operational control are organized across the platform.

---

## 2. What The Service Manages

Authority manages the following areas:

| Area | What it means |
| --- | --- |
| **Users** | Identity records for people who can log in and act inside the authority workspace |
| **Sessions** | Session-based authentication for current signed-in authority users |
| **Invitations** | Controlled onboarding links used to bring new users into the correct role and scope |
| **Hierarchy** | Business relationships between platform admins, distributors, resellers, and owners |
| **Entitlements** | Licensing records that define whether an owner can activate and use an installation |
| **Assignments** | Links between users, entitlements, and installations where explicit binding is required |
| **Installation state** | Health and recent state reports coming from activated installations |
| **Update events** | Operational update records tied to installations |
| **Audit history** | Trace of who performed important governance and lifecycle actions |

---

## 3. Main User Roles

Authority uses role-aware dashboards and APIs. The same service behaves differently depending on who is signed in.

### Platform Admin

Platform admins have the broadest authority. They typically:

- bootstrap or maintain the authority environment
- invite distributors, resellers, owners, and support users
- view the full data console
- manage entitlements directly
- review audit and system-wide onboarding state
- correct hierarchy or licensing issues when downstream operators cannot

### Distributor

Distributors operate within a distributor scope. They typically:

- manage reseller relationships in their branch
- invite resellers and, when policy allows, owners
- review downstream owners and installations
- assign entitlements within their allowed scope
- monitor the state of their own branch only

### Reseller

Resellers operate within a reseller scope. They typically:

- invite owner users
- onboard customer organizations into their branch
- review owner records and entitlement state
- manage day-to-day customer onboarding within their own scope

### Owner

Owners represent the final customer or tenant-side operator. They typically:

- complete invitation acceptance
- access owner-scoped views
- activate or use licensed installations tied to their organization
- review the installations and licensing records relevant to their tenancy

### Support

Support users are operational helpers whose exact permissions depend on policy. In general, they are intended for troubleshooting, visibility, and controlled operational assistance rather than broad commercial administration.

---

## 4. How The Hierarchy Works

Authority separates **identity** from **organizational scope**.

That distinction matters:

- a **user** is a person or actor who can authenticate and be audited
- a **hierarchy relationship** describes where that user belongs in the business structure
- a **role** describes what that user is allowed to do

The current hierarchy model is:

```text
Platform Admin
  -> Distributor
    -> Reseller
      -> Owner
```

This means:

- a distributor can govern reseller and owner records inside its branch
- a reseller can govern owner onboarding inside its branch
- an owner exists as a real user, but with narrower authority and narrower visibility

A user can remain a valid user even if the hierarchy around them changes. For example, a reassignment, suspension, or parent removal may affect scope without deleting the user record itself.

---

## 5. Normal Onboarding Flow

Authority now follows a user-first onboarding model for owners.

### High-Level Operator Journey

1. An operator invites a new user into the correct role and scope.
2. The invited user opens the invitation link.
3. The user accepts the invitation and completes account creation.
4. If the new user is an owner and no entitlement exists yet, Authority auto-creates the required entitlement.
5. The owner is now onboarded into the correct branch.
6. Installation assignment or activation can happen afterward as a separate operational step.

### Why This Matters

This avoids the older entitlement-first workflow where operators had to understand licensing internals before the actual user was onboarded. Manual entitlement creation still exists, but it is now the advanced or exception path rather than the default onboarding path.

### Invitation Behavior

Invitations can be created by the appropriate upstream operator. Invitation acceptance is tied to the intended role and branch so the new user enters the correct organizational scope.

When SMTP settings are configured, Authority also sends invitation emails containing:

- an invitation acceptance link
- the raw invitation token as fallback

---

## 6. Licensing And Entitlements

Entitlements are the licensing records behind installation access.

At a high level, an entitlement describes whether a specific owner email or tenant is allowed to activate and operate an installation.

Typical entitlement fields include:

- approved owner email
- application key
- tenant name
- installation UUID when bound
- licence status
- owner enabled state
- offline grace settings

### Practical Meaning

For most operators:

- **users** represent people
- **entitlements** represent licence and installation rights
- **assignments** represent operational bindings between the two when needed

Manual entitlement creation is still useful for:

- pre-provisioning
- recovery workflows
- migration work
- exception handling
- platform-admin back-office control

But normal owner onboarding does not need to begin there anymore.

---

## 7. Installation Lifecycle

Authority is part of the installation lifecycle, not only user administration.

It tracks and governs:

- activation readiness
- installation identity
- installation health or state reports
- update events
- who the installation belongs to
- whether the owner is allowed to operate it

This makes Authority the operational bridge between licensing, user scope, and live installation state.

### In Practice

An installation moves through a business lifecycle such as:

1. Owner is onboarded
2. Entitlement exists or is auto-created
3. Installation is assigned or activated
4. Installation begins reporting state
5. Operators can inspect health, updates, and audit context through Authority

---

## 8. Main UI Surfaces

Authority currently exposes two major operator-facing web surfaces.

### `/admin`

This is the main authority workspace.

It supports high-level administration flows such as:

- login and logout
- first-time admin bootstrap when explicitly enabled
- invitation acceptance
- guided owner onboarding
- role-aware dashboard views
- invitations and downstream user management
- advanced licensing workflows
- recent activity and operational summaries

This is the main screen most operators should think of as the authority application.

### `/admin/console`

This is the data console.

It is intended for structured inspection and action across authority records. It supports filtered views for records such as:

- users
- hierarchy or organization rows
- invitations
- entitlements
- assignments
- installation health
- update events
- audit events

Recent console UX changes make this screen more operator-friendly by:

- using row-level `Actions`
- improving responsive behavior on smaller screens
- making the leading `Record` column human-readable instead of UUID-first
- keeping licensing-heavy references in more appropriate columns

The console is best understood as the detailed operations and inspection surface, while `/admin` is the broader working dashboard.

---

## 9. Actions And Daily Operations

Authority is built around row-level operational actions.

Depending on record type and operator permissions, an operator may be able to:

- invite a user
- accept an invitation
- suspend or reinstate a user
- soft remove a user
- inspect hierarchy relationships
- create or review entitlements
- assign installations
- review audit history
- inspect installation health or update history

The available actions depend on:

- the current record type
- the target user’s role
- current lifecycle state
- the acting operator’s role and scope

This is important because Authority is designed for scoped governance, not flat unrestricted administration.

---

## 10. Authentication Model

Authority uses session-based authentication for authority users.

Key behaviors:

- users log in through Authority itself
- the current session can be queried server-side
- logout invalidates the session
- first-time bootstrap admin creation is gated behind an explicit runtime flag

This means the service supports both:

- controlled first-run setup
- normal ongoing role-based operational use

Bootstrap mode is intentionally temporary and should not remain enabled as part of normal steady-state production use.

---

## 11. Audit And Traceability

Authority records important governance events in audit history.

This matters because onboarding, entitlement creation, reassignment, suspension, and other actions are not just UI actions. They are business and security events.

Audit visibility helps answer questions such as:

- who invited this owner?
- when was this entitlement created?
- was the entitlement created automatically during onboarding?
- who suspended or reinstated this user?
- what changed in this installation’s administrative history?

This traceability is especially important in multi-level governance where platform admins, distributors, and resellers all participate in downstream onboarding.

---

## 12. Typical Use Cases

### Use Case 1: First-Time Platform Setup

A new environment starts with bootstrap-admin enabled, a first platform admin is created, bootstrap is disabled, and the environment moves into normal session-based administration.

### Use Case 2: Distributor Branch Creation

A platform admin invites a distributor user, who accepts the invitation and begins managing reseller and owner relationships inside that branch.

### Use Case 3: Reseller Onboards A New Owner

A reseller sends an owner invitation. The owner accepts it. Authority creates the owner account and auto-creates an entitlement if needed. The owner can then be assigned or activated against a real installation later.

### Use Case 4: Investigating A Customer Issue

An operator opens the authority console to inspect the owner record, entitlement status, installation health, update events, and audit trail in one place.

### Use Case 5: Correcting Organizational Changes

A higher-scope operator reviews hierarchy and lifecycle state when a reseller relationship changes, an owner becomes orphaned, or a scope reassignment is needed.

---

## 13. What Authority Is Not

Authority is not intended to replace every downstream product UI.

It is not:

- the end-customer business application itself
- a full device management suite for every service in the platform
- a generic identity provider for unrelated services
- only a licence database
- only a login page

Its purpose is narrower and more important than that: it governs who is onboarded, how they are scoped, what they are licensed to do, and what installation lifecycle state exists around them.

---

## 14. Operational Notes

### Local Development

The service runs locally on port `8010` in the current documented setup and uses PostgreSQL.

Important local URLs:

- `http://localhost:8010/health`
- `http://localhost:8010/admin`

### Deployment

The service is deployed through the repository’s authority release and Hetzner deployment workflows.

### Email Delivery

Invitation email delivery is optional but supported when SMTP-related environment variables are configured.

### Validation

The authority module includes focused validation scripts for:

- auth and dashboard behavior
- bootstrap gate behavior
- invitation and assignment flows
- reseller scope
- distributor scope
- admin UI behavior
- end-to-end admin onboarding workflows

---

## 15. Summary

The Authority service is the platform’s governance and lifecycle layer for user onboarding, business hierarchy, licensing, installation control, and operational traceability.

If you need to understand Authority in one sentence:

**Authority decides who belongs where, what they are allowed to operate, how installations are licensed and tracked, and how operators govern that lifecycle over time.**
