# PPL Meta Presence API Contract

**Date**: May 30, 2026  
**Status**: Draft  
**Depends On**: [docs/proposals/presence/Eyenet presence.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/presence/Eyenet%20presence.md), [docs/proposals/presence/ppl-meta-presence-implementation-plan.md](/Users/nickgklezakos/Documents/ppl-meta-code/docs/proposals/presence/ppl-meta-presence-implementation-plan.md)

---

## Purpose

This document defines the initial API contract for `ppl-meta-presence`.

It is intended to make the backend service implementable without ambiguity and to provide a stable interface for:

- `ppl-meta-presence-mobile`
- future platform UI widgets
- admin tooling
- analytics consumers

This contract is deliberately scoped to the first release and reuses existing platform semantics for authentication, instant detection, groups, cameras, collections, and triggers/actions.

It should also remain compatible with the existing mobile camera client behavior in [ppl_meta_mobile_camera](/Users/nickgklezakos/Documents/ppl-meta-code/ppl_meta_mobile_camera), especially its current login, discovered platform-services, device registration, and feed submission conventions.

## Inherited Existing Contracts

The current mobile camera client already depends on the following concrete platform endpoints and persisted client keys. The presence contract should inherit them where practical instead of introducing parallel variants.

Existing auth and discovery endpoints:

- `GET /api/v1/services`
- `GET /api/v1/health`
- `POST /api/v1/users/login`
- `GET /api/v1/users/platform/services`
- `GET /api/v1/users/profile`

Existing mobile camera registration and lifecycle endpoints:

- `POST /api/v1/cameras/mobile`
- `GET /api/v1/cameras/{uuid}`
- `POST /api/v1/cameras/mobile/{camera_uuid}/heartbeat`
- `POST /api/v1/cameras/mobile/{device_id}/update-ip`
- `GET/PUT /api/v1/cameras/mobile/{uuid}/settings`
- `PUT /api/v1/cameras/mobile/{uuid}/name`
- `PUT /api/v1/cameras/mobile/{uuid}/collection`

Existing mobile feed transport endpoints:

- `POST /api/v1/streaming/mobile/{device_id}/frame`
- `WS /api/v1/cameras/mobile/{device_id}/stream`

Existing persisted client keys used by the mobile camera app:

- `ppl_meta_auth_token`
- `ppl_meta_user_data`
- `ppl_meta_device_data`
- `ppl_meta_server_config`
- `ppl_meta_discovered_services`
- `ppl_meta_platform_services`

The presence mobile client should treat these as the baseline inherited client contract unless a presence-specific requirement forces a controlled divergence.

---

## Conventions

## Base Path

All presence endpoints should be exposed under:

```text
/api/v1/presence
```

## Authentication

All protected endpoints require an authenticated bearer token from the existing platform auth model.

Client expectation:

- the first presence mobile client should obtain and persist this token through the same discovery-first login process already implemented in `ppl_meta_mobile_camera`

Concrete inherited login sequence:

1. discover a valid Node endpoint using `/api/v1/services` and `/api/v1/health`
2. authenticate with `POST /api/v1/users/login`
3. fetch discovered platform-service metadata from `GET /api/v1/users/platform/services`
4. fetch current user data from `GET /api/v1/users/profile`
5. persist the resulting token and platform-service payload using the same shared-preferences model already used by `ppl_meta_mobile_camera`

## Content Type

JSON requests and responses use:

```text
Content-Type: application/json
```

Burst upload endpoints may additionally support multipart form data if that proves operationally simpler for the mobile client.

## Common Response Envelope

Recommended successful envelope:

```json
{
  "success": true,
  "data": {}
}
```

Recommended error envelope:

```json
{
  "success": false,
  "error": {
    "code": "presence_session_not_found",
    "message": "Presence session was not found"
  }
}
```

## Common Error Codes

Suggested initial error codes:

- `presence_unauthorized`
- `presence_forbidden`
- `presence_session_not_found`
- `presence_session_expired`
- `presence_invalid_qr`
- `presence_qr_expired`
- `presence_resource_not_bound`
- `presence_detection_pending`
- `presence_detection_failed`
- `presence_action_failed`
- `presence_validation_error`

---

## Identity And Profile Endpoints

## Get Current Installation Presence Context

```text
GET /api/v1/presence/installations/current
```

Purpose:

- return the current installation-level presence context

Response shape:

```json
{
  "success": true,
  "data": {
    "installation_uuid": "inst_123",
    "presence_profile_uuid": "pp_001",
    "installation_name": "Main Lobby",
    "licence_status": "active",
    "reserved_camera_uuid": "cam_presence_01",
    "reserved_collection_uuid": "col_presence_01"
  }
}
```

## Get Current User Presence Profile

```text
GET /api/v1/presence/profiles/me
```

Purpose:

- return the authenticated user's presence profile and resolved resource bindings

Response shape:

```json
{
  "success": true,
  "data": {
    "user_uuid": "user_123",
    "presence_profile_uuid": "pp_user_01",
    "presence_enabled": true,
    "group_uuid": "grp_presence_user_123",
    "resolved_camera_uuid": "cam_presence_01",
    "resolved_collection_uuid": "col_presence_01"
  }
}
```

---

## Mobile Session Endpoints

## Presence Assurance Fields

The presence contract should expose explicit assurance metadata so clients and operators can distinguish lower-trust check-in results from stronger verified presence outcomes.

Suggested shared fields:

- `session_mode`: the requested or resolved session mode
- `assurance_level`: the normalized assurance level derived from the completed flow
- `grant_type`: the product-facing grant classification returned by the backend

Suggested `session_mode` values:

- `qr_only`
- `camera_only`
- `qr_plus_camera`

Suggested `assurance_level` values:

- `low`
- `medium`
- `high`

Suggested `grant_type` values:

- `check_in`
- `presence_match`
- `verified_presence`

Expected normalization:

- `qr_only` -> `low` -> `check_in`
- `camera_only` -> `medium` -> `presence_match`
- `qr_plus_camera` -> `high` -> `verified_presence`

## Create Presence Session

```text
POST /api/v1/presence/mobile/sessions
```

Request body:

```json
{
  "session_mode": "qr_plus_camera",
  "device_uuid": "device_123",
  "device_name": "Nick iPhone",
  "device_platform": "ios",
  "app_version": "1.0.0"
}
```

Response body:

```json
{
  "success": true,
  "data": {
    "session_uuid": "ps_123",
    "session_mode": "qr_plus_camera",
    "assurance_level": "high",
    "grant_type": "verified_presence",
    "status": "created",
    "expires_at": "2026-05-30T12:00:00Z",
    "external_assets": {
      "individual_group_id": "grp_123",
      "trigger_uuid": "trigger_123",
      "action_uuid": "action_123"
    }
  }
}
```

Compatibility note:

- `device_uuid` and related device fields should align with the device identity and registration conventions already used by `AutoCameraRegistrationService` in `ppl_meta_mobile_camera`
- `qr_only` sessions may skip front-camera burst capture entirely and move directly toward QR correlation
- `camera_only` sessions may complete without a QR hit
- `qr_plus_camera` sessions require both camera-backed evidence and a QR-bound session target before a high-assurance result may be returned

If the presence flow needs a registered mobile device anchor before session creation, the mobile client should first use the inherited mobile camera registration pattern:

- register with `POST /api/v1/cameras/mobile`
- persist the server-generated device UUID locally
- reuse that UUID as the primary device anchor for the presence session

## Get Presence Session

```text
GET /api/v1/presence/mobile/sessions/{session_uuid}
```

Response body:

```json
{
  "success": true,
  "data": {
    "session_uuid": "ps_123",
    "status": "awaiting_front_burst",
    "retry_allowed": true,
    "detection_status": "not_started",
    "qr_status": "not_scanned",
    "external_assets": {
      "individual_group_id": "grp_123",
      "trigger_uuid": "trigger_123",
      "action_uuid": "action_123"
    }
  }
}
```

## Submit QR Hit

```text
POST /api/v1/presence/mobile/sessions/{session_uuid}/qr-hit
```

Request body:

```json
{
  "qr_token": "qr_tok_123",
  "installation_uuid": "inst_123",
  "scanned_at": "2026-05-30T11:58:30Z"
}
```

Response body:

```json
{
  "success": true,
  "data": {
    "session_uuid": "ps_123",
    "status": "qr_resolved",
    "decision_state": "pending_detection"
  }
}
```

## Get Presence Session Result

```text
GET /api/v1/presence/mobile/sessions/{session_uuid}/result
```

Response body:

```json
{
  "success": true,
  "data": {
    "session_uuid": "ps_123",
    "status": "completed",
    "decision": "granted",
    "session_mode": "qr_plus_camera",
    "assurance_level": "high",
    "grant_type": "verified_presence",
    "reason_code": "presence_ppl_match",
    "policy_source": "platform_trigger",
    "trigger_type": "group_presence_granted",
    "action_type": "group_open_door",
    "resolved_camera_uuid": "cam_presence_01",
    "resolved_collection_uuid": "col_presence_01",
    "external_assets": {
      "individual_group_id": "grp_123",
      "trigger_uuid": "trigger_123",
      "action_uuid": "action_123"
    }
  }
}
```

Possible `decision` values:

- `pending`
- `granted`
- `denied`
- `retry_required`
- `failed`

---

## Feed Upload Endpoints

## Upload First Front Burst

```text
POST /api/v1/presence/mobile/sessions/{session_uuid}/feeds/front-burst
```

Recommended request shape for JSON form:

```json
{
  "device_id": "device_123",
  "session_uuid": "ps_123",
  "capture_phase": "pre_qr",
  "frames": [
    {
      "frame_data": "...",
      "timestamp": 1717063095.245,
      "width": 320,
      "height": 240,
      "format": "jpeg",
      "orientation": "DeviceOrientation.portraitUp",
      "rotation_angle": 270,
      "fps": 8,
      "camera_facing": "front"
    }
  ],
  "captured_at": "2026-05-30T11:58:15Z",
  "transport_source": "mobile_streaming_service"
}
```

Alternative multipart contract may be adopted if frame size makes JSON transport impractical.

Compatibility note:

- the chosen upload format should stay as close as practical to the existing feed transport logic already implemented in `MobileStreamingService`

Concrete inherited transport baseline:

- current HTTP frame uploads use `POST /api/v1/streaming/mobile/{device_id}/frame`
- payload includes `device_id`, `frame_data`, `timestamp`, `width`, `height`, `format`, `orientation`, `rotation_angle`, and `fps`
- the first presence burst endpoint should prefer either:
  - the same JSON HTTP payload shape with presence-specific session metadata added, or
  - a thin adaptation that can be produced by the same frame packaging code path

Recommended reconciliation rule for first release:

- preserve the existing `MobileStreamingService` frame field names unchanged inside each burst frame item
- add presence-specific metadata only at the burst envelope level, such as `session_uuid`, `capture_phase`, and `transport_source`
- add `camera_facing` only if needed to make front-camera semantics explicit without changing the inherited core fields

This keeps the presence burst contract maximally compatible with the current frame packaging code path.

### First-Release Frozen Burst DTO

The following JSON shape should be treated as the first-release DTO contract for presence burst upload.

```json
{
  "device_id": "device_123",
  "session_uuid": "ps_123",
  "capture_phase": "pre_qr",
  "frames": [
    {
      "frame_data": "...",
      "timestamp": 1717063095.245,
      "width": 320,
      "height": 240,
      "format": "jpeg",
      "orientation": "DeviceOrientation.portraitUp",
      "rotation_angle": 270,
      "fps": 8,
      "camera_facing": "front"
    }
  ],
  "captured_at": "2026-05-30T11:58:15Z",
  "transport_source": "mobile_streaming_service"
}
```

Required envelope fields:

- `device_id`
- `session_uuid`
- `capture_phase`
- `frames`
- `captured_at`
- `transport_source`

Required frame fields:

- `frame_data`
- `timestamp`
- `width`
- `height`
- `format`
- `orientation`
- `rotation_angle`
- `fps`

Optional frame fields:

- `camera_facing`

Allowed initial values:

- `capture_phase`: `pre_qr` or `post_qr_retry`
- `format`: `jpeg`
- `transport_source`: `mobile_streaming_service`
- `camera_facing`: `front`

First-release compatibility rule:

- no inherited frame field names should be renamed in the first release
- any future additions should be additive and should not break the inherited frame packaging path

### Field Mapping To Existing Frame Contract

The inherited frame payload fields should map as follows:

- `device_id`: unchanged
- `frame_data`: unchanged
- `timestamp`: unchanged
- `width`: unchanged
- `height`: unchanged
- `format`: unchanged
- `orientation`: unchanged
- `rotation_angle`: unchanged
- `fps`: unchanged

Presence-only envelope additions:

- `session_uuid`
- `capture_phase`
- `captured_at`
- `transport_source`

Optional presence-only frame addition:

- `camera_facing`

Recommended server-side validation rules for first release:

- reject requests with empty `frames`
- reject requests where any frame omits one of the required inherited fields
- accept `camera_facing` as optional
- reject unsupported `capture_phase` values
- reject unsupported `format` values

If a WebSocket transport is later needed, it should align with the existing mobile stream path at `WS /api/v1/cameras/mobile/{device_id}/stream`.

Response body:

```json
{
  "success": true,
  "data": {
    "attempt_uuid": "attempt_1",
    "attempt_index": 1,
    "instant_detection_request_id": "id_req_123",
    "status": "submitted"
  }
}
```

## Get Current QR Payload

```text
GET /api/v1/presence/qr/current?installation_uuid=&device_reference=
```

Purpose:

- return the current session-backed QR payload for a device without minting a new QR token
- support backend widgets that need to poll current QR state safely

Response body when a current session-backed QR exists:

```json
{
  "success": true,
  "data": {
    "found": true,
    "installation_uuid": "inst_123",
    "device_reference": "kiosk_a",
    "qr_token": "qr_tok_123",
    "expires_at": "2026-05-30T12:00:00Z",
    "payload": {
      "installation_uuid": "inst_123",
      "device_reference": "kiosk_a",
      "qr_token": "qr_tok_123",
      "session_uuid": "ps_123"
    },
    "session_uuid": "ps_123",
    "session_status": "awaiting_front_burst",
    "qr_status": "not_scanned"
  }
}
```

Response body when no current session-backed QR exists:

```json
{
  "success": true,
  "data": {
    "found": false,
    "installation_uuid": "inst_123",
    "device_reference": "kiosk_a",
    "qr_token": null,
    "expires_at": null,
    "payload": null,
    "session_uuid": null,
    "session_status": null,
    "qr_status": null
  }
}
```

## Upload Retry Front Burst

```text
POST /api/v1/presence/mobile/sessions/{session_uuid}/feeds/front-burst/retry
```

Request contract is the same as the first burst endpoint, but `capture_phase` should be `post_qr_retry`.

The same inherited frame field preservation rules should apply to retry bursts.

## Get Instant Detection Status

```text
GET /api/v1/presence/mobile/sessions/{session_uuid}/instant-detection-status
```

Response body:

```json
{
  "success": true,
  "data": {
    "session_uuid": "ps_123",
    "latest_attempt_index": 1,
    "instant_detection_status": "completed",
    "presence_decision_state": "retry_required"
  }
}
```

Possible `instant_detection_status` values:

- `not_started`
- `submitted`
- `processing`
- `completed`
- `failed`

---

## Camera And Collection Endpoints

## List Presence Cameras

```text
GET /api/v1/presence/cameras
```

Purpose:

- list presence-bound or presence-eligible cameras

Response body:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "device_id": "cam_presence_01",
        "name": "Presence Camera",
        "camera_type": "USB",
        "status": "available",
        "reserved_for_presence": true,
        "reserved_resource_uuid": "presence_resource_123",
        "reserved_installation_uuid": "inst_123",
        "linked_collection_uuid": "col_presence_01"
      }
    ]
  }
}
```

## Reserve Presence Camera

```text
POST /api/v1/presence/cameras/reserve
```

Request body:

```json
{
  "installation_uuid": "inst_123",
  "camera_uuid": "cam_existing_or_new",
  "mode": "bind"
}
```

Possible `mode` values:

- `bind`

Current implementation note:

- only `bind` is currently supported
- unsupported modes fail fast with a validation error instead of being silently accepted
- the current frontend presence module does not expose direct collection reservation yet because this route currently operates on explicit UUID input and the backend does not yet expose a browsable platform collection inventory through the presence service
- the preferred operator flow remains reserving a camera through `POST /api/v1/presence/cameras/reserve`, which auto-binds the linked media collection when the backend can resolve one

## List Presence Collections

```text
GET /api/v1/presence/collections
```

## Reserve Presence Collection

```text
POST /api/v1/presence/collections/reserve
```

Request body:

```json
{
  "installation_uuid": "inst_123",
  "collection_uuid": "col_existing_or_new",
  "mode": "bind"
}
```

Current implementation note:

- only `bind` is currently supported
- unsupported modes fail fast with a validation error instead of being silently accepted

## Bind Presence Resources To Session

```text
POST /api/v1/presence/mobile/sessions/{session_uuid}/bind-resources
```

Request body:

```json
{
  "camera_uuid": "cam_presence_01",
  "collection_uuid": "col_presence_01"
}
```

Response body:

```json
{
  "success": true,
  "data": {
    "session_uuid": "ps_123",
    "resolved_camera_uuid": "cam_presence_01",
    "resolved_collection_uuid": "col_presence_01",
    "status": "resources_bound"
  }
}
```

Current implementation note:

- explicit resource binding is validation-backed
- `camera_uuid` and `collection_uuid` must resolve to resources already reserved for presence
- the session stores the validated platform resource UUIDs after binding, not arbitrary request strings

---

## QR Endpoints

## Render QR Payload

```text
POST /api/v1/presence/qr/render
```

Request body:

```json
{
  "installation_uuid": "inst_123",
  "device_reference": "kiosk_a"
}
```

Response body:

```json
{
  "success": true,
  "data": {
    "qr_token": "qr_tok_123",
    "expires_at": "2026-05-30T12:00:00Z",
    "payload": "{signed payload}"
  }
}
```

## Validate QR Payload

```text
POST /api/v1/presence/qr/validate
```

Request body:

```json
{
  "qr_token": "qr_tok_123"
}
```

Response body:

```json
{
  "success": true,
  "data": {
    "valid": true,
    "installation_uuid": "inst_123",
    "expires_at": "2026-05-30T12:00:00Z"
  }
}
```

---

## Analytics Endpoints

## Get Presence Analytics Summary

```text
GET /api/v1/presence/analytics/summary
```

Purpose:

- return top-level presence counts for dashboards and operator overviews

## Get Presence Analytics By User

```text
GET /api/v1/presence/analytics/by-user
```

Purpose:

- return per-user event counts

## Get Presence Analytics By Device

```text
GET /api/v1/presence/analytics/by-device
```

Purpose:

- return per-device event counts

## Get Presence Analytics Outcomes

```text
GET /api/v1/presence/analytics/outcomes
```

Purpose:

- return outcome distribution across granted, denied, retry, and failed sessions

## Get Presence Analytics By Policy Source

```text
GET /api/v1/presence/analytics/by-policy-source
```

Purpose:

- return counts grouped by the policy source that determined the action path

## Get Presence Analytics By Installation

```text
GET /api/v1/presence/analytics/by-installation
```

Purpose:

- return per-installation event counts for multi-site dashboards and support tooling

## Get Presence Analytics By Session Mode

```text
GET /api/v1/presence/analytics/by-session-mode
```

Purpose:

- return counts grouped by `session_mode`
- make it explicit how much traffic is landing as `qr_only`, `camera_only`, or `qr_plus_camera`

Current implementation note:

- this endpoint is now exposed by the presence API router

## Get Presence Analytics By Grant Type

```text
GET /api/v1/presence/analytics/by-grant-type
```

Purpose:

- return counts grouped by `grant_type`
- let dashboards distinguish lower-assurance check-ins from medium-trust presence matches and high-trust verified presence results

Current implementation note:

- this endpoint is now exposed by the presence API router

## Get Presence Analytics By Reserved Collection

```text
GET /api/v1/presence/analytics/by-reserved-collection
```

Purpose:

- return counts grouped by the resolved presence collection used during the session
- sessions without a resolved collection are grouped under `unbound`

## Get Presence Analytics Action Outcomes

```text
GET /api/v1/presence/analytics/action-outcomes
```

Purpose:

- return counts grouped by `action_type` and `action_execution_status`
- surface operator-visible action fan-out and downstream execution outcomes without reading raw traces

## Presence Analytics Repair Endpoint

```text
POST /api/v1/presence/analytics/repair
```

Purpose:

- trigger metadata backfill for persisted analytics events that are missing normalized policy or action fields
- return current breakdowns so operators can verify the repaired analytics shape in the same call

## Get Presence Action Plan

```text
GET /api/v1/presence/mobile/sessions/{session_uuid}/action-plan
```

Purpose:

- return the resolved trigger/action plan before or after execution
- expose the policy provenance that selected the action path

Response body:

```json
{
  "success": true,
  "data": {
    "session_uuid": "ps_123",
    "session_mode": "qr_plus_camera",
    "assurance_level": "high",
    "grant_type": "verified_presence",
    "matched_group_uuid": "grp_presence_user_123",
    "decision": "granted",
    "policy_source": "platform_trigger",
    "trigger_type": "group_presence_granted",
    "action_type": "group_open_door",
    "action_execution_status": "executed",
    "external_assets": {
      "individual_group_id": "grp_123",
      "trigger_uuid": "trigger_123",
      "action_uuid": "action_123"
    },
    "trigger_observation": {
      "trigger_uuid": "trigger_123",
      "configured_action_uuids": [
        "action_123",
        "email_action_456"
      ],
      "configured_action_names": [
        "Presence Action 7",
        "email notification"
      ],
      "last_fired_at": "2026-05-31T10:41:41Z",
      "last_matched_at": "2026-05-31T10:41:37Z",
      "ppl_match_group_id": "grp_123"
    }
  }
}
```

Current implementation note:

- `trigger_observation` is an operational visibility surface derived from the provisioned trigger metadata currently visible to presence
- it is intended to help operators verify which action UUIDs and names were configured on the presence trigger during debugging of multi-action fan-out or delivery issues
- `session_mode`, `assurance_level`, and `grant_type` should make the returned outcome class explicit so low-assurance QR-only results are not confused with camera-backed verified presence

Accepted `policy_source` values:

- `group_policy`
- `installation_policy`
- `default_policy`

## Policy And Grant Rules

The contract should distinguish which backend outcomes are appropriate for each session mode.

Recommended first-release rules:

- `qr_only`
  - may produce `grant_type=check_in`
  - should not require camera-backed `ppl_match`
  - should not be treated as high-confidence identity verification
- `camera_only`
  - may produce `grant_type=presence_match`
  - requires successful camera-backed presence evaluation
  - may drive medium-trust actions allowed by policy
- `qr_plus_camera`
  - may produce `grant_type=verified_presence`
  - requires both successful camera-backed evaluation and QR-bound installation correlation
  - may drive the strongest actions allowed by policy

Mode-specific policy override note:

- installation and group policy may now override trigger/action mapping per session mode
- expected override buckets are `qr_only`, `camera_only`, and `qr_plus_camera`
- each override bucket may define its own decision-specific mapping such as `granted`, `denied`, `retry_required`, or `failed`

Recommended first-release action semantics by mode:

- `qr_only`: check-in, notify, log, low-risk session enablement
- `camera_only`: presence grant, notify, log, medium-trust automation
- `qr_plus_camera`: verified grant, notify, log, highest-trust automation

## Get Presence Decision History

```text
GET /api/v1/presence/mobile/sessions/{session_uuid}/decision-history
```

Purpose:

- return persisted decision records for the session
- include the provenance and action metadata used for audit and debugging

## Query Presence Decision History

```text
GET /api/v1/presence/decision-history?session_uuid=&user_uuid=&installation_uuid=&policy_source=&limit=
```

Purpose:

- return persisted decision records across sessions for operational debugging and support workflows
- allow operators to narrow history by session, user, installation, and resolved policy provenance

Query parameters:

- `session_uuid` optional exact session filter
- `user_uuid` optional exact user filter
- `installation_uuid` optional exact installation filter
- `policy_source` optional exact provenance filter using `group_policy`, `installation_policy`, or `default_policy`
- `limit` optional max item count, newest first

Response shape:

- `items` filtered decision records
- `total` total matching records before any `limit` is applied
- `returned` number of records included in `items`
- `limit` echoed limit value when provided
- `has_more` whether additional matching records exist beyond the returned slice

## Get Presence Session Trace

```text
GET /api/v1/presence/mobile/sessions/{session_uuid}/trace
```

Purpose:

- return the current session, action plan, decision history, and audit log trace in one response

Response body:

```json
{
  "success": true,
  "data": {
    "session": {
      "session_uuid": "ps_123",
      "decision": "granted",
      "matched_group_uuid": "grp_presence_user_123",
      "policy_source": "platform_trigger",
      "trigger_type": "group_presence_granted",
      "action_type": "group_open_door",
      "external_assets": {
        "individual_group_id": "grp_123",
        "trigger_uuid": "trigger_123",
        "action_uuid": "action_123"
      }
    },
    "action_plan": {
      "session_uuid": "ps_123",
      "decision": "granted",
      "policy_source": "group_policy",
      "trigger_type": "group_presence_granted",
      "action_type": "group_open_door",
      "external_assets": {
        "individual_group_id": "grp_123",
        "trigger_uuid": "trigger_123",
        "action_uuid": "action_123"
      },
      "trigger_observation": {
        "trigger_uuid": "trigger_123",
        "configured_action_uuids": [
          "action_123",
          "email_action_456"
        ],
        "configured_action_names": [
          "Presence Action 7",
          "email notification"
        ],
        "last_fired_at": "2026-05-31T10:41:41Z",
        "last_matched_at": "2026-05-31T10:41:37Z",
        "ppl_match_group_id": "grp_123"
      }
    },
    "decision_history": [
      {
        "decision_uuid": "pd_123",
        "session_uuid": "ps_123",
        "decision": "granted",
        "reason_code": "presence_match",
        "policy_source": "group_policy",
        "trigger_type": "group_presence_granted",
        "action_type": "group_open_door"
      }
    ],
    "audit_log": {
      "log_uuid": "log_123",
      "found": true,
      "payload": {}
    }
  }
}
```

## Query Presence Session Traces

```text
GET /api/v1/presence/mobile/session-traces?session_uuid=&user_uuid=&installation_uuid=&policy_source=&limit=
```

Purpose:

- return full trace payloads across sessions for targeted operational review
- support filtering by the same dimensions used for decision-history queries

Query parameters:

- `session_uuid` optional exact session filter
- `user_uuid` optional exact user filter
- `installation_uuid` optional exact installation filter
- `policy_source` optional exact provenance filter using `group_policy`, `installation_policy`, or `default_policy`
- `limit` optional max item count, newest sessions first

Response shape:

- `items` filtered trace payloads
- `total` total matching sessions before any `limit` is applied
- `returned` number of trace payloads included in `items`
- `limit` echoed limit value when provided
- `has_more` whether additional matching sessions exist beyond the returned slice

## Get Presence Summary

```text
GET /api/v1/presence/analytics/summary
```

Response body:

```json
{
  "success": true,
  "data": {
    "attempts": 120,
    "granted": 98,
    "denied": 12,
    "failed": 10,
    "retry_count": 18
  }
}
```

## Get Presence Outcomes

```text
GET /api/v1/presence/analytics/outcomes
```

Purpose:

- return outcome aggregates grouped by time or action semantics

## Get Presence Policy Source Analytics

```text
GET /api/v1/presence/analytics/by-policy-source
```

Purpose:

- return aggregate counts by policy provenance so operators can see which rule layer is driving actions

Response body:

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "policy_source": "group_policy",
        "event_count": 24
      },
      {
        "policy_source": "installation_policy",
        "event_count": 18
      },
      {
        "policy_source": "unknown",
        "event_count": 3
      }
    ]
  }
}
```

Operational note:

- `unknown` can appear for older analytics events created before policy provenance was added
- the current backend repairs those older analytics payloads lazily on service startup by backfilling from decision history or the saved session when possible
- the current non-simulated completion contract is trigger-backed: a successful session should finish with `reason_code=presence_ppl_match` and `policy_source=platform_trigger`, not with a grant based only on raw instant-detection transport success
- multiple media triggers may evaluate against the same camera stream; local validation confirmed presence can complete on its provisioned `ppl_match` trigger while a separate alert trigger on the same camera also fires independently
- current session, result, and trace responses also expose the provisioned external group, trigger, and action UUIDs directly through `external_assets`
- current action-plan and result responses also expose `trigger_observation` so operators can see the trigger's configured action UUIDs and names from the presence debugging surface

## Repair Presence Analytics Metadata

```text
POST /api/v1/presence/analytics/repair
```

Purpose:

- trigger the existing analytics metadata backfill on demand through an authenticated API route
- return a repair summary that operators can use to confirm whether any rows were updated

Authorization:

- requires authenticated admin-level access
- presence resolves access from embedded token roles or permissions when available
- for standard login tokens that only carry `sub`, presence resolves roles and capabilities from node's service-side `user-permissions` endpoint using `SERVICE_SECRET`
- non-admin users must receive `403`

Response body:

```json
{
  "success": true,
  "data": {
    "analytics_event_count": 36,
    "repaired_event_count": 0,
    "policy_source_breakdown": [
      {
        "policy_source": "default_policy",
        "event_count": 13
      }
    ],
    "requested_by": "presence-admin"
  }
}
```

---

## Authorization Expectations

Suggested capability gates:

- `presence.sessions.create`
- `presence.sessions.read`
- `presence.feeds.upload`
- `presence.qr.read`
- `presence.qr.validate`
- `presence.resources.read`
- `presence.resources.manage`
- `presence.analytics.read`
- `presence.config.manage`

The exact capability names should be aligned with the broader platform naming scheme before implementation.

---

## Open Contract Questions

1. Should burst upload use JSON base64 frames, multipart JPEGs, or a short-lived binary upload session?
2. Should QR validation be fully server-side via `qr-hit`, making `/qr/validate` optional for clients?
3. Should resource binding be explicit via `/bind-resources`, or should the backend always auto-resolve the reserved camera and collection?
4. Which existing instant detection result fields should be preserved verbatim in the presence response model?
5. Which of the inherited mobile camera payload fields can remain unchanged so that `MobileStreamingService` packaging logic can be reused directly?
