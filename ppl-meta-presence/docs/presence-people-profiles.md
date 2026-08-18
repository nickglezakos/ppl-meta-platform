# Presence People Profiles (PPP)

**Date**: 2026-08-18
**Status**: ✅ **Completed — implemented and shipped**
**Version**: `2.25.55` (repo `VERSION`)
**Depends on**: Individual Groups module, Presence service (`ppl-meta-presence`), MVR people naming

> ### ✅ Implementation Status — Completed (2026-08-18) · `v2.25.55`
>
> Phase 1 (backend PPP service + presence session flow) and Phase 2 (frontend UI + individual-groups member picker) are now **fully implemented** in the codebase.
>
> **Implemented in `ppl-meta-presence`:**
> - `PresencePeopleProfile` / `PresencePeopleProfileLink` persistence with CRUD, member `lookup`, link/unlink, soft-deactivate (`status=inactive`), and merge-ready wiring (`parent_ppp_uuid`).
> - REST endpoints: `GET/POST /people-profiles`, `GET/PUT/DELETE /people-profiles/{ppp_uuid}`, `POST /people-profiles/{ppp_uuid}/links`, `GET /people-profiles/lookup`, plus people-profile delete/deactivate.
> - Match pipeline integration: on `ppl_match` / `vprofile_match`, the linked PPP is resolved and the session records `matched_ppp_uuid`, `matched_individual_group_name`, and `matched_member_name` (PPP `name` is the sole source of truth for display, per §9/Decision #1).
> - Session trace querying now filters sessions by **profile (PPP) name**, **group name**, and **group member name** via `profile_names`, `group_names`, `member_names` query params.
> - `list_people_profiles` search (`query` param) matches **name, external ref, email, and phone** server-side on the full profile list.
>
> **Implemented in `ppl-meta-frontend`:**
> - Models `PresencePeopleProfile`, `PresencePeopleProfileLink`, and `matchedPppUuid` on `PresenceSessionTraceSummary` / `PresenceSessionDetails`.
> - `PresenceApiClient` methods: `listPeopleProfiles`, `getPeopleProfile`, `lookupPeopleProfileByMember`, `createPeopleProfile`, `updatePeopleProfile`, `deletePeopleProfile`, `linkMemberToPeopleProfile`.
> - Presence **People Profiles** section with profile cards and a create/edit/delete dialog (`_showPeopleProfileDialog`), backed by `_loadPeopleProfiles` / `_buildPeopleCard`.
> - **People Profiles tab search** — a debounced search bar (`_onPeopleSearchChanged`, 350 ms) filters the profile list by name/email/phone/external ref, with clear-button suffix, "Showing results for …", and search-aware empty state.
> - `people_profile_picker.dart` (`PeopleProfilePicker`) to create-or-pick a PPP and link a group member from the individual-groups member flow (§10.5).
> - Session filter dialog extended with **Group / Member / Profile** filter categories (groups from the available individual-groups list, member names lazily fetched per group, profiles from the loaded PPPs) — wired end-to-end to the backend filters above.

---

## 1. Purpose

Presence People Profiles (PPPs) are **people-centric identity records** that live inside the Presence service and serve as the canonical way to name and describe a real person across the platform. A PPP replaces the current per-record `mvr_people.name` as the **user-assigned name** for group members — a single PPP can be linked to many members in many different individual groups, so editing a person's name once updates it everywhere.

---

## 2. Problem Statement

Currently, the user-assigned name for a group member is stored on `mvr_people.name` — a field that is **per-record, per-MVR-person**, not per real person. This causes two concrete problems:

### 2.1 Disconnected naming across groups
The same real person can appear as members in multiple individual groups, but because each is a separate `mvr_people` record, naming one member in Group A does not carry over to the same person's member record in Group B. The operator must set the name repeatedly in each group.

### 2.2 Identity fragmentation between presence and individual groups
The presence service matches a `mvr_people_uuid` and attempts to display the member's name (`matched_member_name`). But this name is tied to the MVR record, not to the person. If the matched member has no name set (or the name was set on a different merged/related record — e.g. the real diagnosis from the Aug 18 session where "Nick" lived on `b24ad688` not `78c287cf`), the presence session shows blanks. There is no single place to set and retrieve the real person's identity.

---

## 3. Entity Model — `PresencePeopleProfile`

The PPP sits alongside the existing `PresenceProfile` hierarchy (installation, device, user) as a new `profile_type = "people"`.

### 3.1 Core fields

| Field | Type | Required | Description |
|---|---|---|---|
| `ppp_uuid` | `UUID` | yes (auto) | Unique identifier |
| `profile_type` | `str` | yes (fixed `"people"`) | Distinguishes from `"installation"`, `"device"`, `"user"` profiles |
| `name` | `str` (max 255) | **yes** | Canonical display name (e.g. "Nick") — the replacement for `mvr_people.name` |
| `email` | `str?` | no | Primary contact email |
| `phone` | `str?` | no | Phone number |
| `notes` | `str?` | no | Free-text operator notes |
| `external_ref` | `str?` | no | External system ID (HR ID, visitor badge, etc.) |
| `parent_ppp_uuid` | `UUID?` | no | For future merge; if a PPP is merged into another, this points to the surviving record |
| `installation_uuid` | `str` | yes (default `"local-installation"`) | Scope / tenant (see §9 constraints) |
| `linked_member_count` | `int` | no (default 0) | How many group members this PPP is linked to (derived) |
| `status` | `str` | yes (default `"active"`) | `active`, `inactive`, `merged` |
| `metadata` | `dict` | no | Extensible annotations |
| `created_at` / `updated_at` | `datetime` | auto | Timestamps |

### 3.2 Comparison with `mvr_people.name`

| Aspect | `mvr_people.name` (current) | PPP (proposed) |
|---|---|---|
| Scope | Per MVR record | Per real person |
| Cross-group | No — each group links a separate MVR record | Yes — one PPP links many group members |
| Used by presence | Reads name from `best_match.existing_member_name` | Reads name from PPP linked to the matched member |
| Edit impact | Only that one MVR record | All linked group members immediately reflect the new name |
| Extra fields | No (just name) | Email, phone, notes, external ref |
| Source of truth | Per-record artifact | **Sole source of truth for display** (see §7) |

---

## 4. Linkage — PPP ↔ Group Members

A PPP can be linked to **many** group members across **many** individual groups.

### 4.1 Linkage model

```
PresencePeopleProfile (ppp_uuid = PPP-123, name = "Nick")
        │
        ├──→ GroupMember (group = "Presence Individuals 7", individual_id = 78c287cf)
        ├──→ GroupMember (group = "VIP Customers",         individual_id = b24ad688)
        └──→ GroupMember (group = "TMA",                   individual_id = cbf5fb63)
```

A **link record** stores:
- `ppp_uuid` — which PPP
- `group_id` — which individual group
- `individual_id` — which member in that group
- `linked_at` / `linked_by` — operator audit

A member can be linked to **at most one** PPP. Linking to a PPP replaces typing a name directly on the member.

### 4.2 Creating links

**Option A — Manual**: In the individual-groups member view, instead of a free-text name field, show an autocomplete/selector to pick an existing PPP or create a new one on the spot.

**Option B — Automatic (presence)** : When a presence session matches a member (`matched_member_uuid`), the user can promote that match to a PPP (with operator-supplied name/fields), and the link is created retrospectively from the presence sessions tab.

**Decision (interaction points)**: With the user's answer, **both** flows are supported:
- **From presence sessions tab**: a matched session row offers a "Create Profile" action that pre-fills the matched member UUID + name and creates the PPP + link.
- **From individual-groups member view**: the member name control offers a PPP autocomplete/creator and links on selection.

---

## 5. PPP Impact on the Presence Session Flow

Currently, the presence session stores `matched_member_name` extracted from `best_match.existing_member_name` (from the trigger's match payload). With PPPs, the flow changes:

```
Trigger fires (vprofile_match or ppl_match)
   │  best_match.matched_member_uuid = 78c287cf
   ▼
process_trigger_match() / _grant_presence_match()
   │  NEW: look up PPP by linked member individual_id
   │   → if found: ppp.name = "Nick", ppp.email, ppp.ppp_uuid
   │   → if not found: fall back to best_match.name (legacy) + offer auto-creation
   ▼
PresenceSession stores:
   matched_member_name     = "Nick"          (from PPP)
   matched_ppp_uuid        = PPP-123         (new field)
   matched_individual_group_id  = grp_...
```

The **PPP name is the sole source of truth for display** (Decision #1). If a PPP is linked, its `name` wins and `mvr_people.name` is ignored. If no PPP is linked, the old `best_match.existing_member_name` is only a legacy fallback (not authoritative).

---

## 6. API Endpoints (all inside `ppl-meta-presence`)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/presence/people-profiles` | List PPPs (search, paginate) |
| `POST` | `/api/v1/presence/people-profiles` | Create a PPP |
| `GET` | `/api/v1/presence/people-profiles/{ppp_uuid}` | Get PPP detail (includes list of linked group members) |
| `PUT` | `/api/v1/presence/people-profiles/{ppp_uuid}` | Update PPP fields |
| `DELETE` | `/api/v1/presence/people-profiles/{ppp_uuid}` | Deactivate (or merge) a PPP |
| `POST` | `/api/v1/presence/people-profiles/{ppp_uuid}/links` | Link a group member to this PPP |
| `DELETE` | `/api/v1/presence/people-profiles/{ppp_uuid}/links/{group_id}/{individual_id}` | Unlink a group member |
| `GET` | `/api/v1/presence/people-profiles/lookup?individual_id=...` | Find the PPP linked to a specific group member (used by the match pipeline) |

---

## 7. Migration Path

### 7.1 Phase 1 — PPP service (backend only)
- Add `PresencePeopleProfile` model + DB table in presence service.
- Add the CRUD + linkage endpoints.
- Add `matched_ppp_uuid` field to `PresenceSession` and `PresenceAnalyticsEvent` (nullable).
- Add the PPP lookup in `process_trigger_match` and `_grant_presence_match`.
- **Name resolution rule**: look up the PPP link → use `ppp.name`; no link → fall back to `best_match.existing_member_name` (legacy only). `mvr_people.name` is **not** authoritative.

### 7.2 Phase 2 — Individual-groups integration
- In individual-groups member view, replace the text-field name input with a PPP autocomplete/creator.
- When a PPP is linked to a member, display the PPP name and a badge showing linked count.
- Members without a PPP still show the stored `mvr_people.name` as a legacy display, and can be migrated to a PPP manually.

### 7.3 Phase 3 — Presence session display
- In presence session cards and inspector, show the PPP name, an icon/indicator distinguishing PPP-backed vs legacy name, and (optionally) a "View Profile" link.
- Presence analytics gain `ppp_uuid` grouping (show all sessions attributed to the same PPP).

---

## 8. Edge Cases & Validation

| Case | Behavior |
|---|---|
| Group member has both a PPP link AND `mvr_people.name` | **PPP wins** (sole source of truth); `mvr_people.name` is ignored for display |
| PPP is deleted/deactivated | Linked members revert to the legacy `mvr_people.name` fallback; the PPP is soft-deactivated (`status=inactive`), not hard-deleted |
| Two PPPs are found to be the same person | Manual merge: one PPP absorbs the other's links, the absorbed PPP gets `status=merged`, `parent_ppp_uuid` set |
| A group member is removed from a group | The link to the PPP becomes dangling — PPP keeps it as a stale ref, and the derived `linked_member_count` decreases |
| Duplicate PPPs created for the same person | `external_ref` helps; a future dedup tool compares names + linked member embeddings |
| Member has no PPP | Presence uses the legacy name; UI shows "no profile" state and offers "Create Profile" |

---

## 9. Open Questions — Resolved

1. **Should linking a PPP auto-update `mvr_people.name`?**
   **Answer**: No. The **PPP is the sole source of truth for display**. We do not auto-sync to `mvr_people.name`, and the PPP name takes precedence whenever a link exists. This keeps ownership clear and avoids write contention on MVR records.

2. **Where can PPPs be created?**
   **Answer**: **Both** the presence sessions tab (a "Create Profile" action on a matched session, pre-filling member UUID + name) and the individual-groups member view (autocomplete/creator). Both flows create the PPP and its link.

3. **PPP scope — install, global, or external?**
   **Answer**: **Scoped to the installation** (`installation_uuid` = the profile's tenant). PPPs belong to the local installation's presence domain. Foreign/other installations are **not** directly exposed; cross-installation PPPs are intended to be accessed through a future **connector middleware**, exactly like any other external system integration (a controlled, authenticated adapter), rather than a searchable global store.

---

---

## 10. Frontend Wiring — Implemented

This section describes how PPPs are wired into the Flutter frontend, now implemented in the codebase. All paths live in `ppl-meta-frontend` and follow the existing `ConsumerStatefulWidget` + Riverpod + `PresenceApiClient`/`IndividualGroupsApiClient` patterns.

### 10.1 API client additions

**`lib/services/presence_api_client.dart`** — add methods mirroring the §6 endpoints, returning typed models:
- `Future<ApiResponse<PresencePeopleProfile>> getPeopleProfile(String pppUuid)`
- `Future<ApiResponse<List<PresencePeopleProfile>>> listPeopleProfiles({String? query, int limit, int offset})`
- `Future<ApiResponse<PresencePeopleProfile>> createPeopleProfile({required String name, String? email, String? phone, String? notes})`
- `Future<ApiResponse<PresencePeopleProfile>> updatePeopleProfile(String pppUuid, {String? name, ...})`
- `Future<ApiResponse<void>> linkMemberToPeopleProfile({required String pppUuid, required String groupId, required String individualId})`
- `Future<ApiResponse<PresencePeopleProfile?>> lookupPeopleProfileByMember(String individualId)` — `GET /people-profiles/lookup?individual_id=...`

These POSTs will use the internal endpoint base (`/api/v1/presence/...`). Follow the existing `_unwrapData` + `ApiResponse` error handling pattern already in the file.

### 10.2 Models

**`lib/models/presence_models.dart`**:
- Add `PresencePeopleProfile` (fields shown in §3.1) and `PresencePeopleProfileLink` (`ppp_uuid`, `group_id`, `individual_id`, `linked_at`, `linked_by`).
- Add `String? matchedPppUuid` to `PresenceSessionTraceSummary` and `PresenceSessionDetails` (`fromJson: json['matched_ppp_uuid']?.toString()`), so sessions carry the attached PPP id.

### 10.3 Presence sessions tab — "Create / Link Profile" action

**`lib/screens/presence_screen.dart`** (use the existing chip/inspector surfaces):
- In `_matchedPersonChips()` and `_SessionOverviewCard` (the "Matched Person" metadata), when a session has a matched member (`matchedMemberName != null` or `matchedMemberUuid present`) but **no** `matchedPppUuid`, add a `TextButton.icon(Icons.person_add, 'Create Profile')` that opens a small PPP create form (name pre-filled with `matchedMemberName`, plus email/phone/notes), calls `createPeopleProfile`, then `linkMemberToPeopleProfile(groupId: matchedIndividualGroupId, individualId: matchedMemberUuid)`, then refreshes the sessions list.
- When a session **does** have `matchedPppUuid`, render a "View Profile" affordance (chip or link) that opens a PPP detail bottom sheet, and display the PPP name as the `Member Name` (the backend already resolves the PPP name for `matched_member_name`).
- This fulfills the "Create Profile from presence sessions tab" decision (#2).

### 10.4 Session inspector

**`lib/screens/presence_screen.dart` → `_PresenceSessionInspector` / `_SessionOverviewCard`**:
- Add a `_InspectorRow(label: 'People Profile', value: matchedPppUuid ?? 'None')`.
- If a PPP exists, include contact fields (email/phone) in the "Matched Person" metadata block.
- Add the same "Create Profile" affordance when no PPP is linked.

### 10.5 Individual-groups member view — PPP autocomplete/creator

**`lib/screens/individual_group_detail_screen.dart`** currently edits member names through the `EditableMVRName` widget (`lib/widgets/editable_mvr_name.dart`), which calls `MVRApiClient.updateMVRPersonName(mvrPersonUuid, name)`.

Per decision #2, member name editing should be re-pointed to PPPs:
- **Option (recommended, least disruptive):** Add a parallel `PeopleProfilePicker` widget and surface it in `_showMemberDetail()` (`individual_group_detail_screen.dart:206`) — an autocomplete based on `listPeopleProfiles(query)`. Picking a profile calls `linkMemberToPeopleProfile(groupId, member.mvrPersonUuid)`.
- Keep the existing free-text `EditableMVRName` for **legacy** members with no PPP (it still writes `mvr_people.name` as the migration fallback), and show a distinct visual state ("Legacy name", no profile) so operators can promote a member to a PPP.
- When a member is PPP-backed, show the PPP name and a badge with the linked-count, and keep the "Group Member NN" numbering from `_formatGroupMemberLabel` unchanged.

### 10.6 Providers / state

- Add simple Riverpod providers for the new `PeopleProfileApiClient`-style service (or extend `PresenceApiClient`), consistent with `apiClientProvider` in `core/api/api_client.dart`.
- After any PPP create/link/unlink, invalidate the presence sessions provider and the individual-group members provider so both screens refresh immediately (mirror the existing "reload group data to refresh member list with new name" flow at `individual_group_detail_screen.dart`).

### 10.7 Screens & interactions summary checklist

| Surface | Change | File/hook |
|---|---|---|
| Presence sessions list | chip + "Create Profile" button when no PPP | `lib/screens/presence_screen.dart` `_matchedPersonChips()` |
| Presence session inspector | "People Profile" row + contact fields + create/view | `_PresenceSessionInspector` `_SessionOverviewCard` |
| Presence analytics | optional `ppp_uuid` grouping/filter chips | `presence_screen.dart` analytics section |
| Individual-groups member | `PeopleProfilePicker` autocomplete + creator, legacy fallback | `individual_group_detail_screen.dart` `_showMemberDetail()` |
| Shared name widget | add a `PeopleProfileView`-style chip (name + linked-count + edit) | `lib/widgets/` |
| API + models + providers | presence people-profile methods/models, Riverpod providers | `presence_api_client.dart`, `presence_models.dart`, `core/api` |

---

## 11. Conclusion — Completed

Presence People Profiles give the platform a **single, canonical identity record per real person**, replacing the fragmented per-record naming on `mvr_people`. A PPP links many group members across many individual groups, so a person's name, contact details, and metadata are stored once and reflected everywhere — in the individual-groups UI, in presence session cards, in analytics, and in future downstream workflows. This directly solves the disjointed naming problem that caused "Nick" to appear on the wrong record, and makes the matched-member display in presence sessions reliable.

This design is now **implemented and shipped (2026-08-18, `v2.25.55`)**: the backend PPP service, endpoints, and match-pipeline integration are live, the frontend People Profiles section, member picker, and per-session `matched_ppp_uuid` display are wired up, and the sessions filter system has been extended to filter by **profile name, group name, and group member name**.

Key constraints established:
- PPP name is the **sole source of truth** for display where a link exists.
- PPP creation is available from **both** the presence sessions tab and the individual-groups member view.
- PPPs are **installation-scoped**; foreign-installation profiles are reached only through a future connector middleware.