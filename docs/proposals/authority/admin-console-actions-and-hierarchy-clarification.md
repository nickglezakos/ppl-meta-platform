# Authority Admin Console Actions And Hierarchy Clarification

**Date**: May 24, 2026  
**Status**: Proposed  
**Scope**: Define a consistent row-level actions pattern for the authority admin console and clarify the architectural distinction between user identities and hierarchy assignments  
**Related Documents**: [docs/proposals/authority/authority-policy.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/authority/authority-policy.md), [docs/proposals/node-user-management-roles-capabilities-analysis.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/node-user-management-roles-capabilities-analysis.md)

---

## Purpose

Two product questions need a single proposal answer:

1. How should row-level actions be exposed at [authority.eyenet-vision.com/admin/console](https://authority.eyenet-vision.com/admin/console) for each entity shown in tabular views.
2. Whether `users` and `hierarchy` are meaningfully different concepts, or whether one of them is redundant.

The authority service already defines lifecycle rules for users, invitations, entitlements, and assignments. The admin console should expose those rules through a consistent interaction model, and the information architecture should reflect the actual domain model instead of duplicating concepts.

---

## Problem Summary

### 1. Missing Row-Level Action Surface

The admin console currently lacks a predictable per-row actions entry point for entities shown in lists.

This creates three problems:

- lifecycle operations are harder to discover
- users must infer what can be done to a record from surrounding page context instead of the record itself
- role-scoped actions such as suspend, reinstate, remove, or reassign are not consistently surfaced at the point where operators inspect the entity

### 2. Unclear Separation Between Users And Hierarchy

The platform already distinguishes between:

- the identity of a person or actor
- the organizational scope to which that actor belongs
- the role and lifecycle state that govern what that actor may do

The confusion comes from treating `hierarchy` as if it were a second kind of user record. It should not be modeled that way.

The current RBAC analysis already notes that the role model has no built-in semantic hierarchy. That means hierarchy is not a property implicitly provided by the role table itself. If the system needs distributor to reseller to owner relationships, that structure must be represented explicitly as assignment or parent-scope metadata, not by duplicating user records.

---

## Proposal

## 1. Add An Actions Column To Every Entity Table

Every entity list in the authority admin console should include a final `Actions` column.

Requirements:

- the `Actions` column must be the last visible column in each row
- the cell should expose a compact trigger such as an icon button or `Actions` button
- activating the trigger should open a popup menu or dialog anchored to that row
- the menu contents must be entity-specific and actor-permission-aware
- unavailable actions should either be hidden or shown disabled with a clear reason
- the interaction must remain usable on mobile without requiring default horizontal table scrolling

This pattern should apply consistently to at least:

- users
- invitations
- entitlements
- assignments
- installations, if they are shown in admin-managed tables

### User Entity Example

For user rows, the popup should primarily expose lifecycle actions.

Examples:

- `Suspend user`
- `Reinstate user`
- `Soft remove user`
- `View audit history`
- `View assignments`
- `Reassign parent scope`, when the acting role is allowed to do so

The exact set should be derived from:

- the user's current lifecycle state
- the target user's role
- the acting operator's role and scope
- whether the target user is orphaned

Examples:

- a reseller viewing an owner should see suspend or reinstate actions within reseller scope
- a distributor viewing a reseller should see suspend or reinstate actions within distributor scope
- a distributor viewing an owner should not see direct suspend if policy disallows it
- a platform admin may additionally see remove and reassignment actions

### Why A Popup Menu Is The Right Surface

The actions popup keeps the table readable while still making row-level control explicit.

This is preferable to always-visible inline buttons because:

- lifecycle actions vary by entity and state
- some rows may have many possible actions
- destructive actions should feel intentional rather than casually exposed
- the same interaction can scale across multiple entity types

For destructive or irreversible flows, the popup action should open a second confirmation dialog that captures reason, actor, and audit metadata.

### Mobile And Responsive Table Behavior

The current mobile behavior, where the table simply scrolls horizontally, is not sufficient for an operational admin console.

Horizontal scrolling hides important state, makes row comparison slower, and makes the final `Actions` column easy to miss. On smaller screens, the interface should adapt its structure instead of preserving the desktop table unchanged.

Recommended responsive pattern:

- desktop and large tablet views may keep the standard multi-column table
- small tablet and mobile views should transform each row into a stacked record card
- each card should present the most important fields first, such as name, role, lifecycle state, and scope
- lower-priority fields can appear as labeled metadata rows inside the card
- the `Actions` trigger should remain visible without horizontal scrolling, preferably pinned in the card header or footer

Recommended mobile card structure for users:

- primary line: user name or email
- secondary line: role and parent scope
- status block: lifecycle state, orphaned state, or invitation state
- metadata block: created date, last activity, assignment summary, or entitlement summary as needed
- action area: always-visible `Actions` button opening the same permission-aware popup menu

This approach preserves one interaction model across breakpoints while changing only the presentation layer.

### Responsive Design Rules

The admin console should follow these rules for all entity tables:

- do not rely on horizontal scrolling as the primary mobile solution
- prioritize progressive disclosure rather than shrinking every column until it becomes unreadable
- preserve row identity and state visibility before showing secondary metadata
- keep destructive and lifecycle actions reachable within one tap from the visible entity card
- keep labels explicit on mobile so values are never shown without context

Horizontal scrolling may still exist as an emergency fallback for very dense internal views, but it should not be the main mobile pattern for authority administration.

### Actions Column In Responsive Layouts

On desktop, `Actions` remains the final table column.

On mobile, the same control should be represented as a stable action area inside the card layout. The product should preserve the concept of row-level actions even if the literal visual column disappears when the table collapses.

This distinction matters because the requirement is behavioral, not purely cosmetic:

- every entity still has a dedicated actions surface
- the actions stay attached to the specific entity being viewed
- the mobile layout avoids forcing users to pan sideways just to find the action trigger

---

## 2. Clarify That Users And Hierarchy Are Different Layers

### Recommended Definitions

`User` should mean the identity record for a person or actor that can authenticate, be invited, be suspended, and be audited.

`Hierarchy` should mean the organizational relationship model that places a user into a business scope such as:

- platform
- distributor
- reseller
- owner

Hierarchy answers questions like:

- who is the parent distributor of this reseller
- which reseller currently governs this owner
- whether a user is orphaned because a parent relationship was removed
- which records fall inside an operator's administrative scope

Users answer different questions:

- who is this actor
- what is their current lifecycle state
- what role do they hold
- can they authenticate
- what audit history exists for them

### Recommended Architectural Rule

Keep both concepts, but do not let them overlap in responsibility.

Recommended split:

- `users` hold identity, authentication, lifecycle state, and audit identity
- `hierarchy` holds parent-child scope relationships and organizational assignment
- `roles` hold permission meaning
- `assignments` hold cross-entity bindings such as owner to entitlement

This prevents a common failure mode where organizational restructuring is implemented by mutating or duplicating user records.

### Why Both Are Needed

The system needs both because a user can stay valid even when its place in the hierarchy changes.

Examples:

- an owner remains a valid user even if their reseller is removed
- a reseller remains a valid user record even if the distributor assignment changes
- a suspended parent may orphan child users without deleting those child users

This behavior is already consistent with the authority policy, which preserves child users and entitlements during parent removal and uses `orphaned` as an explicit state when assignments break.

If hierarchy were collapsed into the user record alone, the system would make reassignment, orphan handling, and scoped governance harder to reason about.

### When Hierarchy Becomes Redundant

Hierarchy becomes redundant only if the product intentionally abandons scoped administration and supports a flat tenant model.

That would mean:

- no distributor to reseller to owner chain
- no parent-based visibility rules
- no orphan recovery workflows
- no scope-based lifecycle authority

That is not the current authority direction. The current policy and lifecycle model depend on scoped governance, so hierarchy should remain as a first-class concept.

---

## UI And Domain Recommendations

### UI Recommendation

In the admin console navigation and page naming, avoid presenting `Users` and `Hierarchy` as if they are sibling copies of the same dataset.

Recommended framing:

- `Users`: identity and lifecycle management
- `Organization` or `Assignments`: parent-child scope relationships and reassignment workflows

`Hierarchy` is technically accurate, but `Organization` or `Scope Assignments` is easier for operators to understand.

### Domain Recommendation

If a separate hierarchy screen exists, it should not duplicate full user CRUD.

It should focus on:

- current parent assignment
- scope lineage
- orphan detection
- reassignment workflows
- scope impact preview for lifecycle actions

User-specific lifecycle controls should still remain reachable from the user row `Actions` menu, even when hierarchy data is shown elsewhere.

---

## Acceptance Criteria

The proposal is satisfied when all of the following are true:

1. Every authority admin table has a final `Actions` column.
2. Clicking or tapping the row action trigger opens an entity-specific popup menu.
3. User rows expose lifecycle actions appropriate to the acting role, target role, and target state.
4. Mobile and small-screen layouts do not depend on horizontal scrolling as the default way to operate entity lists.
5. In mobile view, each entity row collapses into a readable card or stacked layout with explicit field labels.
6. The entity-specific action trigger remains visible and usable on mobile without sideways panning.
7. Destructive actions require explicit confirmation and capture audit metadata.
8. Product terminology distinguishes identity management from organizational assignment.
9. `Users` and `Hierarchy` are no longer treated as duplicate concepts in the admin console.

---

## Final Recommendation

Adopt the row-level `Actions` column pattern for every authority-managed entity table.

Implement the tables as responsive record views rather than fixed desktop grids. Desktop can keep the tabular layout, but mobile should switch to stacked cards so operators can see status and open actions without horizontal scrolling.

Keep both `users` and `hierarchy`, but define them as different layers:

- users are identities with lifecycle state
- hierarchy is organizational scope structure

The right product change is not to remove one of them blindly. The right change is to make the separation explicit in both the UI and the domain model, so lifecycle actions happen on user records while scope and reassignment concerns happen in the organizational layer.
