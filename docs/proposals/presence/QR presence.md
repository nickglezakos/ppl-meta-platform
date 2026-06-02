# QR Presence

**Date**: June 2, 2026  
**Status**: Proposal

---

## Purpose

This document proposes a richer QR contract for Presence so the QR is not only a transient token carrier, but a verifiable context object that can support both:

- station-generated Presence QR challenges scanned by the mobile camera client
- owner-generated personal Presence QRs scanned either by the mobile client or by a web station scanner

The current implementation only carries a minimal payload with `installation_uuid`, optional `device_reference`, `qr_token`, and optional `session_uuid`.

This proposal expands that model so the QR can represent the installation, optional local licence-reference metadata, the producing device, the active user, and optionally the owning user identity when the QR is used in reverse.

---

## Goals

- preserve the existing fast QR challenge flow for normal station-to-mobile Presence
- include enough stable identifiers in the QR payload to bind the challenge to the installation context
- align installation ownership and licence terminology with `ppl-meta-authority`
- support a reversible QR flow where a person can present their own QR from mobile or from a printable profile card
- keep the QR self-describing enough for offline rendering and debugging, while still requiring backend validation for grant issuance
- separate required identity fields from optional convenience metadata such as live location

---

## Authority Alignment

The authority service already owns the installation and entitlement vocabulary used across the platform.

The QR Presence contract should align with the authority-side records already mirrored into the local installation context, including:

- `installation_uuid`
- `application_key`
- `approved_owner_email`
- `licence_status`
- `tenant_name`

Presence should not invent a second installation ownership model.

Recommended rule:

- the QR payload may include optional installation-linked licence reference fields only when those fields are already present in the local node installation state
- QR rendering should not call the online authority service to enrich the payload
- QR fields such as `application_key`, `licence_status`, `approved_owner_email`, or entitlement identifiers are reference metadata only
- those QR fields must not be treated as software licence resolution or licence activation authority
- software licence resolution remains outside the QR contract and continues to belong to the existing local installation and authority synchronization flow

---

## Proposed QR Types

The QR contract should support two primary QR types.

### 1. Station Challenge QR

Produced by a web station or web Presence surface for a target installation.

Purpose:

- a logged-in mobile user scans it
- the backend binds the scan to the intended installation and station context
- the backend returns a Presence grant appropriate for the selected mode and policy

### 2. Owner Identity QR

Produced by the user from mobile or from their profile in web, with support for download and print.

Purpose:

- the user presents the QR to a station scanner or another mobile scanner
- the receiving side resolves the owner identity and installation linkage
- the backend can issue a reversed QR-based Presence grant or handoff into a stronger flow

---

## Proposed Payload Shape

The QR should carry a versioned JSON object.

Suggested top-level shape:

```json
{
  "schema": "ppl_meta_presence_qr/v1",
  "qr_type": "station_challenge",
  "challenge_uuid": "7d5b5c0b-1111-4ec2-9d3c-111111111111",
  "qr_token": "9c7d46e2-2222-4702-b0fd-222222222222",
  "created_at": "2026-06-02T12:00:00Z",
  "expires_at": "2026-06-02T12:05:00Z",
  "installation": {},
  "device": {},
  "actor": {},
  "owner": {},
  "location": {},
  "integrity": {}
}
```

Not every block needs to be populated for every QR type, but the schema should be stable.

---

## Required Fields For Station Challenge QR

The station-generated QR should contain at least the following data.

### Installation Block

Required fields:

- `installation.installation_uuid`

Recommended optional fields:

- `installation.application_key`
- `installation.licence_status`
- `installation.authority_entitlement_uuid`
- `installation.approved_owner_email`
- `installation.tenant_name`
- `installation.node_uuid`
- `installation.node_name`
- `installation.reference_source`

Rationale:

- `installation_uuid` is the main durable anchor already used by the node and authority service
- `application_key`, `licence_status`, owner email, and entitlement identifiers are optional local reference values that help correlation and support tooling when available
- these optional fields are descriptive only and are not the source of truth for licence approval at scan time
- node-level identifiers are useful when multiple stations exist under one installation

Reference source rule:

- when optional licence-reference fields are present, `installation.reference_source` should identify them as locally cached installation metadata, for example `node_installation_cache`
- the presence service should populate these fields from the local installation state that was previously synchronized from authority, not from a live authority lookup during QR creation

### Device Block

Required fields:

- `device.device_reference`
- `device.display_name`

Recommended optional fields:

- `device.device_uuid`
- `device.device_type`
- `device.platform`
- `device.registration_source`

Device naming rule:

- the station should allow a user-editable device name input
- when no custom value is provided, the system should fill a default name from the current code path
- current defaults already present in code can seed this behavior, such as `mobile-presence-station` for station device reference and `Presence Mobile Camera` for mobile display naming

### Actor Block

Required fields:

- `actor.user_email`
- `actor.user_uuid` when available

Rationale:

- this captures the currently logged-in user who generated the QR at the time of creation
- it supports audit trails and allows the QR to be explained to operators without additional lookup

### Timestamp Fields

Required fields:

- `created_at`

Recommended fields:

- `expires_at`
- `issued_at`

The creation timestamp is mandatory for auditability and replay protection.

### Location Block

Optional fields:

- `location.label`
- `location.latitude`
- `location.longitude`
- `location.accuracy_meters`
- `location.captured_at`

Rule:

- location should remain optional and nullable
- when live location is unavailable, permissions are denied, or the station is fixed infrastructure, the QR should still be valid without this block

---

## Optional Owner Block

The QR should support an optional `owner` block so the same contract can also represent user-owned or user-presented identity QRs.

Suggested fields:

- `owner.owner_user_uuid`
- `owner.owner_email`
- `owner.owner_display_name`
- `owner.owner_profile_uuid`
- `owner.owner_type`

Recommended semantics:

- for station challenge QRs, the `owner` block may be absent or may mirror the approved installation owner from the local installation record when useful
- for owner identity QRs, the `owner` block becomes the primary human identity anchor in the QR

This is the piece that enables the reversed flow.

---

## Reversed QR Flow

The QR Presence design should explicitly support the opposite direction from the current station challenge flow.

### Flow A. User Presents QR To A Station Scanner

1. the user opens their profile in mobile or web
2. the system generates a personal Presence QR with optional owner block populated
3. the user shows the QR on screen or uses a previously printed copy
4. the web station scanner reads the QR
5. the Presence backend validates the QR payload, session integrity, and local installation context
6. the backend issues a QR-based Presence grant or routes into a higher-assurance follow-up flow

Current manual validation path:

1. render an `owner_identity` QR from the mobile Presence screen
2. open the web Presence station in `qr_only` execution mode and launch the web scanner
3. let the dev PC camera scan the owner QR directly from the mobile screen
4. submit the scanned owner payload through the station scanner
5. the Presence backend completes the `qr_only` grant immediately in the `owner-qr-hit` path
6. the web station surfaces a granted notification for the active session
7. the mobile owner-QR screen polls recent grants for that owner and surfaces its own granted notification

### Flow B. User Presents QR To Another Mobile Scanner

1. the user opens their mobile Presence QR
2. another mobile client scans it
3. the scanning mobile client submits the payload to Presence
4. the backend resolves installation, owner, and policy context
5. the backend returns the resulting Presence grant decision

### Printable QR Support

The owner QR should be exportable so it can be:

- downloaded from a user profile
- stored locally by the user
- printed as a badge or card
- re-used at stations that support QR Presence intake

Because printed QRs can outlive short challenge windows, owner identity QRs should support either:

- a long-lived signed identity payload with revocation checks at scan time
- or a durable profile reference that must be resolved online by the backend

They should not rely on a five-minute transient challenge token alone.

---

## Grant Semantics

This proposal introduces the concept of a QR-based grant that can be reached from either direction.

Recommended rule:

- the QR itself should not directly equal a grant
- scanning the QR should create a validated claim submission to the Presence backend
- the backend should then issue the Presence grant after validating local installation context, user state, expiry, signature integrity, and policy

Suggested product wording:

- `station_challenge` QR consumed by mobile: `qr_check_in_grant`
- `owner_identity` QR consumed by station: `qr_owner_check_in_grant`
- either path may be upgraded by policy into `verified_presence` only when additional evidence is collected

This keeps QR-only behavior useful without overstating identity assurance.

---

## Integrity And Security Requirements

The richer QR payload should be treated as a signed claim object, not merely plain JSON with no protection.

Recommended integrity fields:

- `integrity.signature`
- `integrity.key_id`
- `integrity.algorithm`

Recommended protections:

- sign the QR payload server-side
- include `created_at` and, when applicable, `expires_at`
- require backend validation before any grant is finalized
- re-check local installation and owner reference state as exposed by the node or local installation context
- reject expired, tampered, revoked, or disabled-owner payloads

Privacy guidance:

- include only the minimum owner information needed for the intended flow
- avoid embedding sensitive profile data beyond identifiers and email unless product policy requires it
- prefer user UUID plus email rather than broader personal details

---

## Recommended Station Challenge Example

```json
{
  "schema": "ppl_meta_presence_qr/v1",
  "qr_type": "station_challenge",
  "challenge_uuid": "1fd6a0fb-2b76-4b7f-9380-b8c9ac3de111",
  "qr_token": "7d8060f7-6f6e-4d8c-a0cd-44a85a981222",
  "created_at": "2026-06-02T12:00:00Z",
  "expires_at": "2026-06-02T12:05:00Z",
  "installation": {
    "installation_uuid": "inst-1234",
    "application_key": "ppl-meta-platform",
    "licence_status": "active",
    "authority_entitlement_uuid": "ent-4567",
    "approved_owner_email": "owner@example.com",
    "tenant_name": "Demo Tenant",
    "node_uuid": "node-8910",
    "node_name": "Front Desk Station",
    "reference_source": "node_installation_cache"
  },
  "device": {
    "device_reference": "front-desk-station",
    "display_name": "Front Desk Station",
    "device_uuid": "dev-1111",
    "device_type": "web_station",
    "platform": "web"
  },
  "actor": {
    "user_uuid": "user-2222",
    "user_email": "operator@example.com"
  },
  "location": {
    "label": "Athens Lobby"
  },
  "integrity": {
    "algorithm": "ed25519",
    "key_id": "presence-signing-key-1",
    "signature": "base64-signature"
  }
}
```

---

## Recommended Owner Identity Example

```json
{
  "schema": "ppl_meta_presence_qr/v1",
  "qr_type": "owner_identity",
  "challenge_uuid": "6ee603a4-f1f2-42dc-badb-d77681b6c333",
  "created_at": "2026-06-02T12:00:00Z",
  "installation": {
    "installation_uuid": "inst-1234",
    "application_key": "ppl-meta-platform",
    "licence_status": "active",
    "approved_owner_email": "owner@example.com",
    "reference_source": "node_installation_cache"
  },
  "owner": {
    "owner_user_uuid": "user-9999",
    "owner_email": "owner@example.com",
    "owner_display_name": "Owner Name",
    "owner_profile_uuid": "profile-5555",
    "owner_type": "approved_owner"
  },
  "integrity": {
    "algorithm": "ed25519",
    "key_id": "presence-signing-key-1",
    "signature": "base64-signature"
  }
}
```

---

## API And Product Impact

The Presence service should add explicit QR creation modes instead of overloading one small payload shape.

Recommended additions:

- station challenge QR render endpoint that returns the enriched station payload
- owner identity QR render endpoint for profile export and print
- QR validation endpoint that understands both `station_challenge` and `owner_identity`
- QR scan submission endpoints usable by both mobile and web station scanners
- `owner-qr-hit` should complete `qr_only` grants immediately when the scanned payload is a valid `owner_identity` QR for the local installation

Frontend impact:

- web Presence station screen should capture editable device name and optional location label
- mobile profile and web profile should offer “show my Presence QR” and “download printable QR” actions
- scanner UI on both mobile and web should display the resolved installation, device, owner, and timestamp context before final submission when appropriate
- both the web station and the owner QR renderer should surface a positive granted notification when the reversed QR grant succeeds

Authority impact:

- Presence should resolve QR installation metadata from the local node installation context using `installation_uuid`
- authority remains the upstream source for the data that the local installation may already have synchronized, but QR rendering should not depend on a live authority lookup
- optional licence-related fields in the QR are reference-only metadata and not licence-resolution outputs

---

## Recommended First Implementation Slice

To keep delivery practical, the first slice should implement the following.

1. enrich station challenge QR with `installation`, `device`, `actor`, `created_at`, and optional `location`
2. source `installation_uuid` from the local installation context and include `application_key`, `approved_owner_email`, and `licence_status` only when those values already exist locally
3. add editable device display name with stable default naming from current code paths
4. keep owner block optional in station-generated QR
5. add a second QR type for owner identity export from user profile
6. require backend signature verification and local installation-context validation before grant issuance

This first slice would satisfy the immediate requirement without blocking on the full printable-card product surface.

---

## Open Questions

- should `approved_owner_email` always be embedded when locally available, or only resolved server-side after scan?
- should owner identity QRs be short-lived signed claims or long-lived revocable profile references?
- should live GPS coordinates be allowed for station-generated QR payloads, or only a user-entered location label?
- should node identity be represented as `node_uuid`, `station_uuid`, or `device_uuid` in the canonical QR schema?
- should signing keys live in Presence, Authority, or a shared platform trust service?

---

## Recommendation

Presence QR should evolve from a minimal token wrapper into a signed, versioned context object with two supported modes:

- installation-bound station challenge QR
- owner-presented identity QR

The QR must include at minimum the installation UUID, editable device identity with stable defaults, current actor email, and creation timestamp.

It should optionally include locally cached licence-reference metadata, location, and owner identity data, but grants must always be issued only after backend validation against the current local installation context.
