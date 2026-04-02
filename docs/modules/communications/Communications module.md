# Communications Module

> **Service**: `ppl-meta-communications`  
> **Version**: 1.0.0  
> **Port**: 8009  
> **Database**: `ppl_communications_db` (PostgreSQL)  
> **Framework**: FastAPI + SQLAlchemy + Pydantic v2  

---

## Table of Contents

1. [Overview](#1-overview)
2. [Architecture](#2-architecture)
3. [Features](#3-features)
   - 3.1 [Email Service](#31-email-service)
   - 3.2 [Webhook Manager](#32-webhook-manager)
   - 3.3 [Push Notifications](#33-push-notifications)
   - 3.4 [Audit Logging](#34-audit-logging)
   - 3.5 [Communication Logs](#35-communication-logs)
   - 3.6 [Email Settings Management](#36-email-settings-management)
4. [Data Model](#4-data-model)
5. [API Reference](#5-api-reference)
6. [Configuration](#6-configuration)
7. [Service Discovery & Registration](#7-service-discovery--registration)
8. [Edge Deployment Multi-Tenancy](#8-edge-deployment-multi-tenancy)
9. [Integration with Platform Services](#9-integration-with-platform-services)
10. [Health Checks](#10-health-checks)
11. [Security Considerations](#11-security-considerations)
12. [Dependencies](#12-dependencies)

---

## 1. Overview

The Communications Service is the centralized outbound communications hub for the PPL Meta platform. It handles all forms of external and internal messaging — email, HTTP webhooks, mobile push notifications, and structured audit logging — behind a unified REST API. Every communication is tracked in a single `communication_logs` table, providing full delivery visibility and trigger traceability.

### Key Responsibilities

| Capability | Description |
|---|---|
| **Email** | SMTP-based delivery with HTML/text support, template engine, CC/BCC, and configurable SMTP settings stored in DB |
| **Webhooks** | HTTP requests to external endpoints with automatic retry, exponential back-off, authentication, and reusable configurations |
| **Push Notifications** | FCM (Android) and APNS (iOS) notifications with batch support, custom data payloads, badge/sound |
| **Audit Logging** | Structured event logging with severity levels, event source/type/data tracking |
| **Communication Logs** | Centralized log of all communications with status tracking, pagination, and multi-filter query API |
| **Email Settings** | Runtime-configurable SMTP settings persisted in the database, with test-email endpoint |

### Deployment Model

Each customer runs a complete independent installation on their own hardware. The Communications Service is part of each local installation with:

- Local PostgreSQL database (`ppl_communications_db`)
- Installation-specific identification (`INSTALLATION_ID`, `TENANT_NAME`)
- All communication logs tagged with installation context for remote troubleshooting

---

## 2. Architecture

### Directory Structure

```
ppl-meta-communications/
├── src/
│   ├── main.py                     # FastAPI application entry point, lifespan, CORS, routers
│   ├── config.py                   # Pydantic Settings (env + .env loading)
│   ├── database.py                 # SQLAlchemy engine, SessionLocal, get_db dependency
│   ├── microservice_config.py      # Consul and service registry constants
│   ├── __init__.py
│   ├── api/
│   │   └── health.py               # /health, /health/ready, /health/live
│   ├── models/
│   │   ├── communication_log.py    # CommunicationLog model + enums
│   │   ├── email_template.py       # EmailTemplate model
│   │   ├── webhook_config.py       # WebhookConfig model
│   │   └── email_settings.py       # EmailSettings model (runtime SMTP config)
│   ├── schemas/
│   │   ├── email.py                # Email request/response schemas
│   │   ├── email_settings.py       # Email settings CRUD schemas
│   │   ├── webhook.py              # Webhook request/response schemas
│   │   └── notification.py         # Push notification + audit log schemas
│   ├── services/
│   │   ├── email_service.py        # EmailService (SMTP send, template support)
│   │   ├── webhook_service.py      # WebhookService (HTTP requests, retry, config)
│   │   └── notification_service.py # NotificationService, AuditLogService, CommunicationLogService
│   └── routes/
│       ├── email.py                # /api/v1/email/* endpoints
│       ├── email_settings.py       # /api/v1/settings/email/* endpoints
│       ├── webhook.py              # /api/v1/webhook/* endpoints
│       ├── notification.py         # /api/v1/notifications/* endpoints
│       └── audit.py                # /api/v1/audit/* endpoints
├── .env.example                    # Environment variable template
├── init_db.py                      # Database initialization script
├── requirements.txt                # Python dependencies
├── start_service.sh                # Service start script
└── logs/                           # Rotating log files
```

### Application Startup Flow

```
main.py lifespan()
    │
    ├── Register with Discovery Service (if available)
    │   └── Detect network IP → register_service("ppl-meta-communications", ...)
    │
    ├── Log configuration (email/webhook/push/audit enabled states)
    │
    ├── Test database connection (up to 5 retries with 2s delay)
    │
    └── Create database tables via Base.metadata.create_all()
```

### Router Registration

| Router | Prefix | Tags |
|---|---|---|
| `health_router` | `/` (root) | `health` |
| `email_router` | `/api/v1/email` | `email` |
| `webhook_router` | `/api/v1/webhook` | `webhook` |
| `notification_router` | `/api/v1/notifications` | `notifications` |
| `audit_router` | `/api/v1/audit` | `audit` |
| `email_settings_router` | `/api/v1/settings/email` | `email-settings` |

### Database

- **Engine**: SQLAlchemy with `postgresql+psycopg` driver
- **Connection Pool**: `QueuePool` with `pool_size=10`, `max_overflow=20`, `pool_pre_ping=True`
- **Session**: `SessionLocal` via `get_db()` dependency injection
- **Tables**: Auto-created on startup via `Base.metadata.create_all()`

---

## 3. Features

### 3.1 Email Service

**Implementation**: `services/email_service.py` → `EmailService`

The email service supports sending emails via SMTP with two modes: direct send and template-based send. It uses a dual-source configuration strategy — database settings take priority over environment variables.

#### Configuration Priority

1. **Database settings** (`email_settings` table) — if a record exists and `mail_enabled=True`
2. **Environment variables** (`MAIL_*`) — fallback if no DB settings

#### Direct Email Send

```
EmailService.send_email(to, subject, text_body, html_body?, cc?, bcc?, ...)
```

- Constructs a `MIMEMultipart("alternative")` message with plain-text and optional HTML parts
- Supports CC/BCC recipients
- Two SMTP transports: SSL/TLS (port 465) or STARTTLS (port 587)
- Creates a `CommunicationLog` record before sending; updates status to `SENT` or `FAILED` after
- Returns `(success, message, log_uuid)`

#### Template-Based Email Send

```
EmailService.send_email_with_template(to, template_name, variables, cc?, bcc?, ...)
```

- Retrieves an active `EmailTemplate` by name from the database
- Performs variable substitution in subject, HTML body, and text body
- Delegates to `send_email()` with the rendered content

#### Email Templates

Templates are stored in the `email_templates` table with:
- Unique `name` identifier
- `subject`, `html_body`, `text_body` fields supporting `{{variable}}` placeholders
- `variables` JSON array listing expected variable names
- `category` for grouping (e.g., `trigger_notification`, `user_notification`)
- `is_active` flag for soft-disable

### 3.2 Webhook Manager

**Implementation**: `services/webhook_service.py` → `WebhookService`

The webhook manager sends HTTP requests to external endpoints with built-in retry logic, authentication support, and reusable configurations.

#### Direct Webhook Send

```
WebhookService.send_webhook(url, payload, method?, headers?, timeout?, max_retries?, retry_delay?, ...)
```

- Supports HTTP methods: GET, POST, PUT, DELETE
- **Retry Logic**: Configurable `max_retries` (default 3) with `retry_delay` seconds between attempts
- Uses `httpx.AsyncClient` for async HTTP requests
- Response body stored (truncated to 5000 chars)
- Status transitions: `PENDING` → `RETRYING` → `DELIVERED` or `FAILED`
- Returns `(success, message, log_uuid, status_code, response_body)`

#### Configuration-Based Webhook Send

```
WebhookService.send_webhook_from_config(config_name, payload, ...)
```

- Loads a saved `WebhookConfig` by name
- Applies authentication headers based on `auth_type`:
  - **Bearer**: `Authorization: Bearer {token}`
  - **API Key**: `X-API-Key: {token}`
  - **Basic Auth**: supported via `auth_username`/`auth_password`
- Uses the config's `timeout_seconds`, `max_retries`, `retry_delay_seconds`
- Updates config statistics: `total_calls`, `successful_calls`, `failed_calls`, timestamps

#### Webhook Configurations

Stored in the `webhook_configs` table with:
- Unique `name` identifier and `url`
- `method` (GET/POST/PUT/DELETE)
- Authentication: `auth_type`, `auth_token`, `auth_username`, `auth_password`
- Custom `headers` (JSON)
- Retry policy: `max_retries`, `retry_delay_seconds`, `timeout_seconds`
- Event filtering: `event_types` JSON array
- Usage statistics: call counts, last success/failure timestamps
- `is_active` flag

### 3.3 Push Notifications

**Implementation**: `services/notification_service.py` → `NotificationService`

Push notifications support FCM (Android) and APNS (iOS). The current implementation provides the full API contract and logging infrastructure, with the actual FCM/APNS integration marked as a placeholder for production deployment.

#### Capabilities

- Batch notification to multiple device tokens
- Custom `data` payload (key-value pairs)
- iOS-specific: `badge` count, `sound` name
- Priority levels: `high`, `normal`
- Full logging in `communication_logs`

#### Planned Integration Points

- **Firebase Admin SDK** (`firebase-admin`) for FCM
- **aioapns** for Apple Push Notification Service
- Batch request optimization
- Per-device success/failure tracking

### 3.4 Audit Logging

**Implementation**: `services/notification_service.py` → `AuditLogService`

The audit logging service creates structured event records for compliance, debugging, and operational monitoring. Audit entries are stored in the same `communication_logs` table with `type=AUDIT_LOG`.

```
AuditLogService.log_audit_event(event_type, event_source, event_data, user_id?, ip_address?, severity?)
```

- **Event Types**: `trigger_fired`, `user_login`, `config_changed`, etc. (free-form string)
- **Severity Levels**: `info`, `warning`, `error`, `critical`
- **Installation Context**: Automatically includes `INSTALLATION_ID` and `TENANT_NAME` from config
- Audit logs are immediately marked as `DELIVERED` (no external send step)
- Configurable via `AUDIT_LOG_ENABLED` and `AUDIT_LOG_RETENTION_DAYS`

### 3.5 Communication Logs

**Implementation**: `services/notification_service.py` → `CommunicationLogService`

A unified query service for all communication records in the platform.

```
CommunicationLogService.get_logs(type?, status?, recipient?, triggered_by?, trigger_id?,
                                  installation_id?, tenant_name?, start_date?, end_date?,
                                  page=1, page_size=50)
```

#### Filter Capabilities

| Filter | Type | Matching |
|---|---|---|
| `type` | exact | `email`, `webhook`, `push_notification`, `sms`, `audit_log` |
| `status` | exact | `pending`, `sent`, `delivered`, `failed`, `retrying` |
| `recipient` | partial (ILIKE) | Substring match on recipient field |
| `triggered_by` | exact | Service or user that triggered the communication |
| `trigger_id` | exact | UUID of the trigger/action |
| `installation_id` | exact | Installation UUID |
| `tenant_name` | partial (ILIKE) | Substring match on tenant name |
| `start_date` / `end_date` | range | ISO 8601 datetime bounds |

#### Pagination

- Page-based with configurable `page_size` (1–500, default 50)
- Returns `logs`, `total`, `page`, `page_size`, `total_pages`

### 3.6 Email Settings Management

**Implementation**: `routes/email_settings.py`

A dedicated CRUD API for managing SMTP configuration at runtime without restarting the service. Settings are stored in the `email_settings` database table and take priority over environment variables when sending emails.

#### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/settings/email` | Get current SMTP settings (creates defaults if none exist) |
| `PUT` | `/api/v1/settings/email` | Update SMTP settings (partial update supported) |
| `POST` | `/api/v1/settings/email/test` | Send a test email to verify configuration |

#### Security

- Passwords are masked as `"********"` in all API responses
- The test endpoint validates that email is enabled and required fields are configured before sending

---

## 4. Data Model

### 4.1 `communication_logs` Table

The central tracking table for all communications.

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `uuid` | UUID | Unique identifier for external reference |
| `type` | Enum | `email`, `webhook`, `push_notification`, `sms`, `audit_log` |
| `status` | Enum | `pending`, `sent`, `delivered`, `failed`, `retrying` |
| `recipient` | String(500) | Email address, webhook URL, device token |
| `subject` | String(500) | Email subject or notification title |
| `content` | Text | Main content body |
| `payload` | JSON | Additional structured data |
| `triggered_by` | String(200) | Source service/user |
| `trigger_type` | String(100) | `trigger_action`, `manual`, `scheduled`, `audit_event` |
| `trigger_id` | String(200) | ID of the originating trigger |
| `installation_id` | String(200) | Edge installation UUID |
| `tenant_name` | String(200) | Human-readable tenant/site name |
| `attempts` | Integer | Number of delivery attempts |
| `last_attempt_at` | DateTime(tz) | Timestamp of last attempt |
| `delivered_at` | DateTime(tz) | Successful delivery timestamp |
| `failed_at` | DateTime(tz) | Final failure timestamp |
| `error_message` | Text | Error details on failure |
| `response_status_code` | Integer | HTTP status code (webhooks) |
| `response_body` | Text | HTTP response body (webhooks, truncated to 5000 chars) |
| `created_at` | DateTime(tz) | Record creation timestamp |
| `updated_at` | DateTime(tz) | Last update timestamp |

**Indexes**: `uuid`, `type`, `status`, `recipient`, `triggered_by`, `trigger_id`, `installation_id`

### 4.2 `email_templates` Table

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `uuid` | UUID | Unique identifier |
| `name` | String(200) | Unique template name |
| `description` | Text | Template description |
| `subject` | String(500) | Subject line (supports variable substitution) |
| `html_body` | Text | HTML content |
| `text_body` | Text | Plain text content |
| `variables` | JSON | Array of expected variable names |
| `category` | String(100) | Grouping category |
| `is_active` | Boolean | Soft-enable/disable flag |
| `created_by` / `updated_by` | String(200) | Audit fields |
| `created_at` / `updated_at` | DateTime(tz) | Timestamps |

### 4.3 `webhook_configs` Table

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `uuid` | UUID | Unique identifier |
| `name` | String(200) | Unique config name |
| `description` | Text | Config description |
| `url` | String(2000) | Endpoint URL |
| `method` | String(10) | HTTP method |
| `auth_type` | String(50) | `bearer`, `basic`, `api_key`, `none` |
| `auth_token` | String(500) | Token/API key |
| `auth_username` / `auth_password` | String(200) | Basic auth credentials |
| `headers` | JSON | Custom headers dictionary |
| `max_retries` | Integer | Max retry attempts (default 3) |
| `retry_delay_seconds` | Integer | Delay between retries (default 5) |
| `timeout_seconds` | Integer | Request timeout (default 30) |
| `event_types` | JSON | Array of event types that trigger this webhook |
| `is_active` | Boolean | Active/inactive flag |
| `total_calls` / `successful_calls` / `failed_calls` | Integer | Usage counters |
| `last_called_at` / `last_success_at` / `last_failure_at` | DateTime(tz) | Timing stats |
| `created_by` / `updated_by` | String(200) | Audit fields |
| `created_at` / `updated_at` | DateTime(tz) | Timestamps |

### 4.4 `email_settings` Table

| Column | Type | Description |
|---|---|---|
| `id` | Integer (PK) | Auto-increment primary key |
| `mail_enabled` | Boolean | Enable/disable email (default `False`) |
| `mail_server` | String(255) | SMTP server (default `smtp.gmail.com`) |
| `mail_port` | Integer | SMTP port (default `587`) |
| `mail_username` | String(255) | SMTP username |
| `mail_password` | String(500) | SMTP password (encrypted in production) |
| `mail_from` | String(255) | Sender email address |
| `mail_from_name` | String(255) | Sender display name |
| `mail_starttls` | Boolean | Use STARTTLS (default `True`) |
| `mail_ssl_tls` | Boolean | Use SSL/TLS (default `False`) |
| `use_credentials` | Boolean | Use authentication (default `True`) |
| `created_at` / `updated_at` | DateTime(tz) | Timestamps |

---

## 5. API Reference

### 5.1 Email Endpoints

#### `POST /api/v1/email/send`

Send a direct email.

**Request Body** (`EmailSendRequest`):
```json
{
  "to": ["user@example.com"],
  "subject": "Alert: Trigger Fired",
  "text_body": "A trigger was fired in zone A.",
  "html_body": "<p>A trigger was fired in <b>zone A</b>.</p>",
  "cc": ["manager@example.com"],
  "bcc": [],
  "from_email": "alerts@pplmeta.com",
  "from_name": "PPL Meta Alerts",
  "payload": {"trigger_name": "Zone A Traffic", "people_count": 12},
  "triggered_by": "media_service",
  "trigger_type": "trigger_action",
  "trigger_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response** (`EmailSendResponse`):
```json
{
  "success": true,
  "message": "Email sent to 2 recipients",
  "log_uuid": "a1b2c3d4-...",
  "recipients_count": 2
}
```

#### `POST /api/v1/email/send/template`

Send an email using a stored template with variable substitution.

**Request Body** (`EmailTemplateRequest`):
```json
{
  "to": ["user@example.com"],
  "template_name": "trigger_notification",
  "variables": {
    "trigger_name": "Zone A Traffic",
    "people_count": "12",
    "timestamp": "2026-03-20T14:30:00Z"
  },
  "triggered_by": "media_service",
  "trigger_id": "trigger-uuid-123"
}
```

#### `POST /api/v1/email/templates`

Create an email template.

**Request Body** (`EmailTemplateCreate`):
```json
{
  "name": "trigger_notification",
  "description": "Notification sent when a media trigger fires",
  "subject": "Trigger Alert: {{trigger_name}}",
  "text_body": "Trigger {{trigger_name}} fired with {{people_count}} people detected.",
  "html_body": "<p>Trigger <b>{{trigger_name}}</b> fired with {{people_count}} people.</p>",
  "variables": ["trigger_name", "people_count", "timestamp"],
  "category": "trigger_notification",
  "is_active": true
}
```

#### `GET /api/v1/email/templates/{template_name}`

Get a single template by name.

#### `GET /api/v1/email/templates`

List all templates. Optional query parameter: `category`.

### 5.2 Webhook Endpoints

#### `POST /api/v1/webhook/send`

Send a direct webhook request.

**Request Body** (`WebhookSendRequest`):
```json
{
  "url": "https://hooks.external-service.com/callback",
  "method": "POST",
  "payload": {
    "event": "trigger_fired",
    "data": {"count": 10, "demographics": {"male": 4, "female": 6}}
  },
  "headers": {"X-Custom-Header": "value"},
  "timeout": 30,
  "triggered_by": "media_service",
  "trigger_id": "trigger-uuid-123"
}
```

**Response** (`WebhookSendResponse`):
```json
{
  "success": true,
  "message": "Webhook sent successfully",
  "log_uuid": "b2c3d4e5-...",
  "status_code": 200,
  "response_body": "{\"received\": true}"
}
```

#### `POST /api/v1/webhook/send/config/{config_name}`

Send a webhook using a saved configuration. Only the payload is required in the body.

#### `POST /api/v1/webhook/configs`

Create a reusable webhook configuration.

**Request Body** (`WebhookConfigCreate`):
```json
{
  "name": "signage-update-hook",
  "description": "Notify signage system when trigger fires",
  "url": "https://signage.example.com/api/webhook",
  "method": "POST",
  "auth_type": "bearer",
  "auth_token": "sk-abc123...",
  "headers": {"X-Source": "ppl-meta"},
  "max_retries": 5,
  "retry_delay_seconds": 10,
  "timeout_seconds": 15,
  "event_types": ["trigger_fired", "trigger_updated"],
  "is_active": true
}
```

#### `GET /api/v1/webhook/configs/{config_name}`

Get a single webhook config by name.

#### `GET /api/v1/webhook/configs`

List all webhook configs. Optional query parameter: `is_active`.

### 5.3 Push Notification Endpoints

#### `POST /api/v1/notifications/push`

Send push notifications to device tokens.

**Request Body** (`PushNotificationRequest`):
```json
{
  "device_tokens": ["fcm-token-1", "fcm-token-2"],
  "title": "Motion Detected",
  "body": "Camera 1 detected movement in Zone A",
  "data": {"camera_id": "cam-001", "zone": "A"},
  "badge": 1,
  "sound": "default",
  "priority": "high",
  "triggered_by": "cameras_service",
  "trigger_id": "detection-uuid-123"
}
```

**Response** (`PushNotificationResponse`):
```json
{
  "success": true,
  "message": "Push notification sent to 2 devices",
  "log_uuid": "c3d4e5f6-...",
  "devices_count": 2,
  "successful_count": 2,
  "failed_count": 0
}
```

### 5.4 Audit & Log Endpoints

#### `POST /api/v1/audit/log`

Create an audit log entry.

**Request Body** (`AuditLogRequest`):
```json
{
  "event_type": "trigger_fired",
  "event_source": "media_service",
  "event_data": {
    "trigger_name": "Marketing Demo",
    "people_count": 5,
    "zone": "entrance"
  },
  "user_id": "user-123",
  "ip_address": "192.168.1.100",
  "severity": "info"
}
```

#### `GET /api/v1/audit/logs`

Query communication logs with filters and pagination.

**Query Parameters**:

| Parameter | Type | Description |
|---|---|---|
| `type` | string | `email`, `webhook`, `push_notification`, `sms`, `audit_log` |
| `status` | string | `pending`, `sent`, `delivered`, `failed`, `retrying` |
| `recipient` | string | Partial match on recipient |
| `triggered_by` | string | Exact match on trigger source |
| `trigger_id` | string | Exact match on trigger UUID |
| `installation_id` | string | Exact match on installation UUID |
| `tenant_name` | string | Partial match on tenant name |
| `start_date` | ISO 8601 | Start of date range |
| `end_date` | ISO 8601 | End of date range |
| `page` | int (≥1) | Page number (default: 1) |
| `page_size` | int (1–500) | Results per page (default: 50) |

**Response** (`CommunicationLogListResponse`):
```json
{
  "logs": [{ "id": 1, "uuid": "...", "type": "email", "status": "delivered", ... }],
  "total": 142,
  "page": 1,
  "page_size": 50,
  "total_pages": 3
}
```

#### `GET /api/v1/audit/logs/{log_uuid}`

Get a single communication log by UUID.

### 5.5 Email Settings Endpoints

#### `GET /api/v1/settings/email`

Get current SMTP settings. Returns defaults if none configured.

#### `PUT /api/v1/settings/email`

Update SMTP settings (partial update — only provided fields are changed).

**Request Body** (`EmailSettingsUpdate`):
```json
{
  "mail_enabled": true,
  "mail_server": "smtp.gmail.com",
  "mail_port": 587,
  "mail_username": "alerts@company.com",
  "mail_password": "app-specific-password",
  "mail_from": "alerts@company.com",
  "mail_from_name": "PPL Meta Alerts"
}
```

#### `POST /api/v1/settings/email/test?test_email=admin@company.com`

Send a test email to verify SMTP settings are working.

---

## 6. Configuration

All configuration is managed via the `Settings` class (Pydantic v2 BaseSettings) in `config.py`, loaded from environment variables and `.env` file.

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| **Application** | | |
| `APP_NAME` | `ppl-meta-communications` | Service name |
| `APP_VERSION` | `1.0.0` | Service version |
| `ENVIRONMENT` | `development` | Environment (`development`, `production`) |
| `DEBUG` | `False` | Debug mode (enables SQL echo logging) |
| `LOG_LEVEL` | `info` | Log level |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `8009` | Bind port |
| **Database** | | |
| `DATABASE_URL` | — | Full PostgreSQL URL (overrides component fields) |
| `DB_HOST` | `localhost` | Database host |
| `DB_PORT` | `5432` | Database port |
| `DB_NAME` | `ppl_communications_db` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| **Email (SMTP)** | | |
| `MAIL_ENABLED` | `False` | Enable email sending |
| `MAIL_SERVER` | `smtp.gmail.com` | SMTP server |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USERNAME` | — | SMTP username |
| `MAIL_PASSWORD` | — | SMTP password |
| `MAIL_FROM` | `noreply@pplmeta.com` | Sender email |
| `MAIL_FROM_NAME` | `PPL Meta Platform` | Sender display name |
| `MAIL_STARTTLS` | `True` | Use STARTTLS |
| `MAIL_SSL_TLS` | `False` | Use SSL/TLS |
| `USE_CREDENTIALS` | `True` | Authenticate with SMTP server |
| **Webhooks** | | |
| `WEBHOOK_ENABLED` | `True` | Enable webhooks |
| `WEBHOOK_TIMEOUT` | `30` | Request timeout (seconds) |
| `WEBHOOK_MAX_RETRIES` | `3` | Max retry attempts |
| `WEBHOOK_RETRY_DELAY` | `5` | Delay between retries (seconds) |
| **Push Notifications** | | |
| `PUSH_ENABLED` | `False` | Enable push notifications |
| `FCM_SERVER_KEY` | — | Firebase Cloud Messaging server key |
| `FCM_PROJECT_ID` | — | Firebase project ID |
| `APNS_ENABLED` | `False` | Enable Apple push notifications |
| `APNS_KEY_PATH` | — | Path to APNS `.p8` key file |
| `APNS_KEY_ID` | — | APNS key ID |
| `APNS_TEAM_ID` | — | Apple team ID |
| `APNS_TOPIC` | — | APNS topic (app bundle ID) |
| **Audit** | | |
| `AUDIT_LOG_ENABLED` | `True` | Enable audit logging |
| `AUDIT_LOG_RETENTION_DAYS` | `90` | Log retention period |
| **Multi-Tenancy** | | |
| `INSTALLATION_ID` | — | Unique UUID for this edge installation |
| `TENANT_NAME` | — | Human-readable tenant/site name |
| **Redis** | | |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_ENABLED` | `True` | Enable Redis integration |
| **Rate Limiting** | | |
| `RATE_LIMIT_ENABLED` | `True` | Enable rate limiting |
| `EMAIL_RATE_LIMIT_PER_MINUTE` | `10` | Max emails per minute |
| `WEBHOOK_RATE_LIMIT_PER_MINUTE` | `60` | Max webhooks per minute |
| **External Services** | | |
| `USER_SERVICE_URL` | `http://localhost:8001` | User service URL |
| `DISCOVERY_SERVICE_URL` | `http://localhost:8006` | Discovery service URL |
| **Security** | | |
| `SECRET_KEY` | — | Application secret key |
| `JWT_SECRET` | — | JWT signing key |

---

## 7. Service Discovery & Registration

On startup, the service attempts to register itself with the PPL Meta Discovery Service using the shared `register_service()` function:

```python
await register_service(
    name="ppl-meta-communications",
    service_type="backend",
    version="1.0.0",
    host=<detected_network_ip>,
    port=8009,
    health_endpoint="/health",
    capabilities=["email", "webhooks", "notifications", "audit-logging"],
    metadata={
        "version": "1.0.0",
        "environment": config.ENVIRONMENT,
        "features": "email,webhooks,push_notifications,audit_logging",
    },
)
```

The service also supports Consul-based discovery via `microservice_config.py`:
- Consul is configured via `CONSUL_HOST`, `CONSUL_PORT`, `CONSUL_ENABLED`
- Service tags: `communications`, `email`, `webhook`, `notifications`, `microservice`
- Circuit breaker config: `CIRCUIT_BREAKER_THRESHOLD=5`, `CIRCUIT_BREAKER_TIMEOUT=60`

Registration failures are non-fatal — the service continues operating without discovery.

---

## 8. Edge Deployment Multi-Tenancy

The Communications Service is designed for edge deployments where each customer site runs its own isolated instance of the platform.

### Installation Identity

Two environment variables identify each deployment:

| Variable | Example | Purpose |
|---|---|---|
| `INSTALLATION_ID` | `550e8400-e29b-41d4-a716-446655440000` | Unique UUID generated during installation |
| `TENANT_NAME` | `Acme Corp - Main Office` | Human-readable site identifier |

### Automatic Context Injection

- `installation_id` and `tenant_name` are automatically included in all `communication_logs` records
- This enables:
  - **Remote troubleshooting** via VPN/SSH or log export
  - **Log aggregation** across multiple customer sites
  - **Filtering** logs by installation in the query API

### No API-Level Tenant Passing

Tenant identity is configured once at the environment level — services calling the Communications API do not need to include tenant information in their requests.

---

## 9. Integration with Platform Services

### Trigger Actions (Media Service)

The Communications Service is designed to be called by the Media Service when trigger actions fire. Trigger actions can specify:

- `action_type: "email"` → calls `POST /api/v1/email/send`
- `action_type: "webhook"` → calls `POST /api/v1/webhook/send`
- `action_type: "log"` → calls `POST /api/v1/audit/log`

Each request includes `triggered_by`, `trigger_type`, and `trigger_id` for full traceability back to the triggering event.

### Cameras Service

The Cameras Service can trigger communications via the instant detection pipeline — for example, sending webhook notifications when a known person is identified.

### Service Connectivity

| Service | URL Config | Purpose |
|---|---|---|
| Discovery Service | `DISCOVERY_SERVICE_URL` (port 8006) | Service registration |
| User Service | `USER_SERVICE_URL` (port 8001) | User lookup (future) |
| Redis | `REDIS_URL` (port 6379) | Queuing and rate limiting |

---

## 10. Health Checks

### `GET /health`

Full health check including database connectivity.

```json
{
  "status": "healthy",
  "service": "ppl-meta-communications",
  "version": "1.0.0",
  "database": {
    "status": "connected",
    "database": "ppl_communications_db"
  }
}
```

### `GET /health/ready`

Kubernetes readiness probe. Returns `ready` only if the database is connected.

### `GET /health/live`

Kubernetes liveness probe. Always returns `alive` if the process is running.

---

## 11. Security Considerations

- **Password masking**: SMTP passwords are never returned in API responses; displayed as `"********"`
- **Input validation**: Pydantic v2 schemas enforce email format (`EmailStr`), URL format (`HttpUrl`), string lengths, and field constraints
- **CORS**: Configured via FastAPI middleware — should be restricted from `allow_origins=["*"]` in production
- **Secrets**: All sensitive data (`SECRET_KEY`, `JWT_SECRET`, `MAIL_PASSWORD`, `auth_token`) should use environment variables, never hardcoded
- **Webhook response truncation**: Response bodies are limited to 5000 characters to prevent storage abuse
- **Rate limiting**: Configurable per-minute limits for email (10) and webhooks (60) via Redis
- **Global exception handler**: Catches unhandled exceptions and returns generic error responses without leaking internals in production

---

## 12. Dependencies

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | 0.103.0 | Web framework |
| `uvicorn[standard]` | 0.23.2 | ASGI server |
| `pydantic` | ≥2.4.0 | Data validation |
| `pydantic-settings` | ≥2.0.0 | Environment configuration |
| `python-dotenv` | 1.0.0 | `.env` file loading |
| `SQLAlchemy` | ≥2.0.25 | ORM and database engine |
| `psycopg[binary]` | ≥3.1.0 | PostgreSQL driver |
| `alembic` | 1.11.1 | Database migrations |
| `httpx` | ≥0.24.0 | Async HTTP client (webhooks) |
| `aiosmtplib` | ≥3.0.0 | Async SMTP client |
| `redis` / `aioredis` | ≥5.0.0 / ≥2.0.0 | Queuing and rate limiting |
| `PyJWT` | ≥2.8.0 | JWT token handling |
| `passlib[bcrypt]` | ≥1.7.4 | Password hashing |
| `cryptography` | ≥41.0.0 | Encryption utilities |
| `prometheus-client` | ≥0.19.0 | Metrics export |
| `psutil` | ≥5.9.0 | System monitoring |

---

## Logging

The service uses Python's `logging` module with a `RotatingFileHandler`:

- **Log file**: `<workspace>/logs/ppl-meta-communications.log`
- **Max size**: 10 MB per file
- **Backup count**: 5 rotated files
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Console output**: Simultaneous `StreamHandler` for terminal visibility

---

## Running the Service

```bash
cd ppl-meta-communications
source venv/bin/activate
cd src
uvicorn main:app --host 0.0.0.0 --port 8009 --reload
```

- **API**: http://localhost:8009
- **Interactive Docs**: http://localhost:8009/docs
- **ReDoc**: http://localhost:8009/redoc
- **Health**: http://localhost:8009/health
