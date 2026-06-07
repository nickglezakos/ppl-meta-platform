# Camera Operations API Schemas

## Purpose
Define request and response contracts for camera operations status, policy management, and support analytics.

## Design Principles
- Keep live status reads fast with bounded payload sizes.
- Keep policy writes safe through strict validation, reason capture, and audit trails.
- Keep analytics queries support-friendly with clear filtering and time windows.

## API Versioning
- Base path: `/api/v1/cameras/operations`
- Content type: `application/json`
- Timestamps: ISO 8601 UTC (for example `2026-06-07T14:22:31Z`)

## Common Enums

### `camera_type`
- `usb`
- `mobile`
- `rtsp`
- `edge`

### `stream_state`
- `DISCONNECTED`
- `CONNECTING`
- `CONNECTED_NO_VIEWERS`
- `CONNECTED_WITH_VIEWERS`
- `STALE_CANDIDATE`
- `STALE_DISCONNECTED`

### `severity`
- `ok`
- `warn`
- `critical`

### `scope_type`
- `global`
- `camera_type`
- `camera`

## Error Envelope
All non-2xx responses should use:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Policy value is outside allowed range",
    "details": {
      "field": "stale_grace_seconds",
      "allowed_min": 5,
      "allowed_max": 120,
      "provided": 300
    },
    "request_id": "6f9c79cc-5ce2-4d08-a2e6-c81df9fb7d64"
  }
}
```

## 1) Live Operations Status

### GET `/status`
Returns current status and latest readings for streaming cameras.

### Query Parameters
- `camera_type` optional, enum list
- `site_id` optional, string
- `state` optional, enum list from `stream_state`
- `severity` optional, enum list from `severity`
- `cursor` optional, string
- `limit` optional, integer, default `50`, max `200`

### Response 200
```json
{
  "meta": {
    "request_id": "f38ba25e-6dd7-4b7d-a372-3589b8674d41",
    "generated_at": "2026-06-07T14:22:31Z",
    "next_cursor": "eyJvZmZzZXQiOjUwfQ=="
  },
  "summary": {
    "total": 124,
    "by_state": {
      "CONNECTED_WITH_VIEWERS": 83,
      "CONNECTED_NO_VIEWERS": 25,
      "STALE_CANDIDATE": 9,
      "STALE_DISCONNECTED": 7
    },
    "by_severity": {
      "ok": 101,
      "warn": 17,
      "critical": 6
    }
  },
  "items": [
    {
      "camera_id": "251263da-b850-4ca0-bc19-3f048664f035",
      "camera_name": "Lobby Mobile 1",
      "camera_type": "mobile",
      "site_id": "athens-hq",
      "state": "CONNECTED_WITH_VIEWERS",
      "severity": "warn",
      "last_transition_reason": "viewer_attached",
      "last_frame_at": "2026-06-07T14:22:29Z",
      "metrics": {
        "active_viewers": 3,
        "frame_gap_ms": 178,
        "effective_fps": 9.4,
        "read_failures_1m": 2,
        "timeouts_5m": 0,
        "reconnect_attempts_15m": 1,
        "stale_candidates_15m": 1
      },
      "policy": {
        "effective_scope": "camera_type",
        "profile": "mobile",
        "liveness_ttl_seconds": 20,
        "stale_grace_seconds": 45,
        "reconnect_cooldown_seconds": 10,
        "retry_cap": 5
      },
      "updated_at": "2026-06-07T14:22:30Z"
    }
  ]
}
```

## 2) Policy Discovery

### GET `/policies`
Returns effective policy values and editable ranges by scope.

### Query Parameters
- `scope_type` optional, enum
- `scope_id` optional, string

### Response 200
```json
{
  "meta": {
    "request_id": "61b2f2ca-7396-45a8-adbc-7d03e4f3fef4",
    "generated_at": "2026-06-07T14:23:01Z"
  },
  "policies": [
    {
      "scope_type": "camera_type",
      "scope_id": "mobile",
      "version": 12,
      "effective_values": {
        "liveness_ttl_seconds": 20,
        "stale_grace_seconds": 45,
        "reconnect_cooldown_seconds": 10,
        "retry_cap": 5,
        "post_viewer_attach_protection_seconds": 15
      },
      "editable_ranges": {
        "liveness_ttl_seconds": { "min": 8, "max": 60, "step": 1, "warn_high": 40 },
        "stale_grace_seconds": { "min": 10, "max": 180, "step": 5, "warn_high": 90 },
        "reconnect_cooldown_seconds": { "min": 1, "max": 60, "step": 1 },
        "retry_cap": { "min": 1, "max": 10, "step": 1 },
        "post_viewer_attach_protection_seconds": { "min": 0, "max": 60, "step": 1 }
      },
      "updated_by": "admin@company.com",
      "updated_at": "2026-06-07T13:10:44Z"
    }
  ]
}
```

## 3) Policy Update

### PATCH `/policies/{scope_type}/{scope_id}`
Updates policy values for a scope. Requires admin role.

### Request Body
```json
{
  "reason": "Reduce false stale teardown for mobile in branch office wifi jitter",
  "if_version": 12,
  "changes": {
    "stale_grace_seconds": 55,
    "reconnect_cooldown_seconds": 12
  }
}
```

### Validation Rules
- `reason` required, min length `8`, max length `500`.
- `if_version` required for optimistic concurrency.
- Every `changes` key must exist in editable ranges.
- Each value must be within min/max and aligned to step.

### Response 200
```json
{
  "meta": {
    "request_id": "8e32a2be-499b-4f57-9512-cba2f37d41f4",
    "generated_at": "2026-06-07T14:24:10Z"
  },
  "result": {
    "scope_type": "camera_type",
    "scope_id": "mobile",
    "previous_version": 12,
    "new_version": 13,
    "applied_changes": {
      "stale_grace_seconds": {
        "old": 45,
        "new": 55
      },
      "reconnect_cooldown_seconds": {
        "old": 10,
        "new": 12
      }
    },
    "audit_event_id": "7ef604d2-9620-4d18-9676-39f80ffbfd4b"
  }
}
```

## 4) Analytics Readings

### GET `/analytics/readings`
Returns time-windowed readings for support triage.

### Query Parameters
- `camera_id` optional, string
- `camera_type` optional, enum list
- `site_id` optional, string
- `from` required, ISO 8601 UTC
- `to` required, ISO 8601 UTC
- `resolution` optional, one of `raw`, `10s`, `1m`, `5m`, default `10s`
- `metrics` optional, comma-separated metric names
- `limit` optional, integer, default `2000`, max `10000`

### Response 200
```json
{
  "meta": {
    "request_id": "69470fe3-47af-44e7-b8be-15f3836c49b8",
    "from": "2026-06-07T13:00:00Z",
    "to": "2026-06-07T14:00:00Z",
    "resolution": "1m"
  },
  "series": [
    {
      "camera_id": "251263da-b850-4ca0-bc19-3f048664f035",
      "camera_type": "mobile",
      "points": [
        {
          "ts": "2026-06-07T13:01:00Z",
          "active_viewers": 2,
          "frame_gap_p95_ms": 240,
          "effective_fps_avg": 9.1,
          "timeouts": 0,
          "read_failures": 1,
          "reconnect_attempts": 0,
          "stale_candidates": 0
        }
      ]
    }
  ]
}
```

## 5) Analytics Aggregates

### GET `/analytics/aggregates`
Returns aggregated metrics for dashboards and support trend analysis.

### Query Parameters
- `group_by` required, one of `camera_id`, `camera_type`, `site_id`
- `from` required, ISO 8601 UTC
- `to` required, ISO 8601 UTC
- `bucket` optional, one of `1m`, `5m`, `15m`, `1h`, default `5m`

### Response 200
```json
{
  "meta": {
    "request_id": "15df1bd7-4d52-4ecf-af1b-61668ef7d90d",
    "from": "2026-06-07T08:00:00Z",
    "to": "2026-06-07T14:00:00Z",
    "bucket": "15m",
    "group_by": "camera_type"
  },
  "rows": [
    {
      "group": "mobile",
      "blank_rate": 0.006,
      "stale_events": 12,
      "recovery_success_rate": 0.94,
      "startup_latency_p95_ms": 1240,
      "frame_gap_p95_ms": 310
    }
  ]
}
```

## 6) Incident Timeline

### GET `/analytics/incidents/{camera_id}`
Returns an incident timeline that combines lifecycle transitions and policy edits.

### Query Parameters
- `from` required, ISO 8601 UTC
- `to` required, ISO 8601 UTC
- `include_policy_changes` optional, boolean, default `true`

### Response 200
```json
{
  "meta": {
    "request_id": "e4f3ad34-d9aa-41f1-af89-5b6f070850f5",
    "camera_id": "251263da-b850-4ca0-bc19-3f048664f035"
  },
  "events": [
    {
      "ts": "2026-06-07T13:11:05Z",
      "type": "lifecycle",
      "name": "stale_candidate",
      "details": {
        "frame_gap_ms": 1220,
        "active_viewers": 2
      }
    },
    {
      "ts": "2026-06-07T13:11:08Z",
      "type": "policy_change",
      "name": "camera_type.mobile.updated",
      "details": {
        "stale_grace_seconds": {
          "old": 45,
          "new": 55
        },
        "updated_by": "admin@company.com",
        "reason": "wifi jitter tolerance"
      }
    }
  ]
}
```

## Authorization Model
- Read endpoints: `platform_admin`, `support_admin`, `support_readonly`.
- Write endpoint (`PATCH /policies/...`): `platform_admin`, `support_admin`.
- Every response should include `request_id` for traceability.

## Audit Events (Required)
- `camera_operations.policy.updated`
- `camera_operations.policy.update_rejected`
- `camera_operations.policy.rollback`

Each event payload should include:
- actor id
- actor role
- scope
- old values
- new values
- reason
- request id
- timestamp

## Backward Compatibility
- Unknown metrics should be ignored by clients.
- New fields must be additive.
- Deprecated fields should be flagged in changelog before removal.
