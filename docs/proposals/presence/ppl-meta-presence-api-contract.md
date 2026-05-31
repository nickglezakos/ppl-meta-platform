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

## Create Presence Session

```text
POST /api/v1/presence/mobile/sessions
```

Request body:

```json
{
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
    "status": "created",
    "expires_at": "2026-05-30T12:00:00Z"
  }
}
```

Compatibility note:

- `device_uuid` and related device fields should align with the device identity and registration conventions already used by `AutoCameraRegistrationService` in `ppl_meta_mobile_camera`

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
    "qr_status": "not_scanned"
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
    "reason_code": "presence_match",
    "trigger_type": "presence_match",
    "action_type": "presence_grant",
    "resolved_camera_uuid": "cam_presence_01",
    "resolved_collection_uuid": "col_presence_01"
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
        "camera_uuid": "cam_presence_01",
        "camera_type": "presence",
        "installation_uuid": "inst_123",
        "status": "reserved"
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
- `create`

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
    "matched_group_uuid": "grp_presence_user_123",
    "decision": "granted",
    "policy_source": "group_policy",
    "trigger_type": "group_presence_granted",
    "action_type": "group_open_door",
    "action_execution_status": "executed"
  }
}
```

Accepted `policy_source` values:

- `group_policy`
- `installation_policy`
- `default_policy`

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
      "policy_source": "group_policy",
      "trigger_type": "group_presence_granted",
      "action_type": "group_open_door"
    },
    "action_plan": {
      "session_uuid": "ps_123",
      "decision": "granted",
      "policy_source": "group_policy",
      "trigger_type": "group_presence_granted",
      "action_type": "group_open_door"
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
