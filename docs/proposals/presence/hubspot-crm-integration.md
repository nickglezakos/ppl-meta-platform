# HubSpot ↔ Presence CRM Integration

**Status:** Implemented (MVP)  
**Scope:** Private App token in Presence Settings; one-way HubSpot → PPP import; real-time grant Notes + `last_presence_*` properties.

## APIs

| Method | Path | Role |
|--------|------|------|
| GET | `/api/v1/presence/installations/current/crm/hubspot` | Admin — masked config |
| PUT | `/api/v1/presence/installations/current/crm/hubspot` | Admin — save config |
| POST | `/api/v1/presence/installations/current/crm/hubspot/test` | Admin — connection test + property ensure |
| POST | `/api/v1/presence/installations/current/crm/hubspot/sync` | Admin — import contacts → PPP |

Config is stored on the installation profile metadata key `crm_hubspot`. Access tokens are never returned on GET.

## Identity

- HubSpot contact `id` → PPP `external_ref`
- Upsert prefers `external_ref`, then email
- Grants resolve PPP via `matched_ppp_uuid` / member link / `linked_user_uuid`

## Grant outbound

Called from `_grant_presence_match`, `_grant_qr_check_in`, and trigger-match immediate grants. Posts a HubSpot Note (body includes `session_uuid=…`) and PATCHes contact properties. Marked on `session.external_assets.hubspot_posted` for idempotency.

## UI

Presence → **Settings** → **HubSpot CRM** card (enable, token, hub/list ids, grant types, Test / Sync / Save).

## Operator wiki

See [Presence and attendance — HubSpot CRM](../../documentation/wiki/owners-admins/presence-attendance.md#hubspot-crm).
