# PPL Meta Communications Service

A microservice for handling all outbound communications in the PPL Meta platform, including email, webhooks, push notifications, and audit logging.

## Features

### ✉️ Email Service
- Send emails via SMTP with HTML and plain text support
- Template-based emails with variable substitution
- CC/BCC support
- Reusable email templates
- Delivery tracking and logging

### 🔗 Webhook Manager
- HTTP webhooks with configurable methods (GET, POST, PUT, DELETE)
- Automatic retry logic with exponential backoff
- Authentication support (Bearer, Basic, API Key)
- Custom headers and timeouts
- Reusable webhook configurations
- Success/failure tracking and statistics

### 📱 Push Notifications
- Firebase Cloud Messaging (FCM) for Android
- Apple Push Notification Service (APNS) for iOS
- Batch notification support
- Custom data payloads
- Badge and sound configuration

### 📋 Audit Logging
- Structured event logging
- Event source tracking
- User action auditing
- Configurable retention periods
- Comprehensive query API

### 📊 Communication Logs
- Centralized logging for all communications
- Status tracking (pending, sent, delivered, failed, retrying)
- Attempt counting and error tracking
- Trigger source tracking (trigger IDs, types)
- Paginated query API with filters

### 🏢 Edge Deployment Multi-Tenancy
- Installation-level identification for edge deployments
- Automatic inclusion of installation_id and tenant_name in all logs
- Support for remote troubleshooting and log aggregation
- No need to pass tenant info through API calls—configured once at installation

## Architecture

**Deployment Model**: Edge/On-Premise Multi-Instance

Each customer runs a complete independent installation of ppl-meta-platform on their own hardware. The Communications Service is part of each local installation and includes:

- Local database (ppl_communications_db)
- Installation-specific identification (INSTALLATION_ID, TENANT_NAME)
- All communication logs tagged with installation context
- Support for remote troubleshooting via VPN/SSH or log export

Future: Central licensing service will issue application keys per installation.

The service follows the standard PPL Meta microservice architecture:

```
ppl-meta-communications/
├── src/
│   ├── models/          # Database models (SQLAlchemy)
│   ├── schemas/         # Pydantic schemas for API
│   ├── services/        # Business logic
│   ├── routes/          # API endpoints
│   ├── api/             # Health check endpoints
│   ├── config.py        # Configuration management
│   ├── database.py      # Database connection
│   └── main.py          # FastAPI application
├── logs/                # Service logs
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variable template
```

## Setup

### 1. Create Virtual Environment

```bash
cd ppl-meta-communications
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

**IMPORTANT: Set Installation Identifiers**

During platform installation, generate and set unique installation identifiers:

```bash
# Generate unique installation ID
python -c "import uuid; print(uuid.uuid4())"
# Example output: 550e8400-e29b-41d4-a716-446655440000

# Edit .env and set:
INSTALLATION_ID=550e8400-e29b-41d4-a716-446655440000
TENANT_NAME=Customer Name - Site Location
```

These values will be automatically included in all communication logs for support and troubleshooting.

### 4. Configure Database

Create the PostgreSQL database:

```sql
CREATE DATABASE ppl_communications_db;
```

Update `.env` with your database credentials.

### 5. Run the Service

```bash
cd src
uvicorn main:app --host 0.0.0.0 --port 8009 --reload
```

The service will be available at:
- API: http://localhost:8009
- Docs: http://localhost:8009/docs
- Health: http://localhost:8009/health

## API Endpoints

### Email

- `POST /api/v1/email/send` - Send an email
- `POST /api/v1/email/send/template` - Send email using template
- `POST /api/v1/email/templates` - Create email template
- `GET /api/v1/email/templates/{name}` - Get email template
- `GET /api/v1/email/templates` - List email templates

### Webhooks

- `POST /api/v1/webhook/send` - Send webhook request
- `POST /api/v1/webhook/send/config/{name}` - Send webhook using config
- `POST /api/v1/webhook/configs` - Create webhook configuration
- `GET /api/v1/webhook/configs/{name}` - Get webhook configuration
- `GET /api/v1/webhook/configs` - List webhook configurations

### Notifications

- `POST /api/v1/notifications/push` - Send push notifications

### Audit & Logs

- `POST /api/v1/audit/log` - Create audit log entry
- `GET /api/v1/audit/logs` - Query communication logs (with filters)
- `GET /api/v1/audit/logs/{uuid}` - Get specific log by UUID

### Health

- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check (K8s)
- `GET /health/live` - Liveness check (K8s)

## Usage Examples

### Send Email

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8009/api/v1/email/send",
        json={
            "to": ["user@example.com"],
            "subject": "Test Email",
            "text_body": "This is a test email",
            "html_body": "<p>This is a <strong>test</strong> email</p>",
            "triggered_by": "trigger_service",
            "trigger_type": "trigger_action",
            "trigger_id": "trigger-uuid-123"
        }
    )
    print(response.json())
```

### Send Webhook

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8009/api/v1/webhook/send",
        json={
            "url": "https://webhook.site/your-endpoint",
            "method": "POST",
            "payload": {
                "event": "trigger_fired",
                "data": {"count": 10, "demographics": {}}
            },
            "triggered_by": "media_service",
            "trigger_id": "trigger-uuid-123"
        }
    )
    print(response.json())
```

### Create Audit Log

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8009/api/v1/audit/log",
        json={
            "event_type": "trigger_fired",
            "event_source": "media_service",
            "event_data": {
                "trigger_name": "Marketing Demo",
                "people_count": 5
            },
            "user_id": "user-123",
            "severity": "info"
        }
    )
    print(response.json())
```

## Integration with Trigger Actions

To integrate with Media Service triggers, modify the `redis_subscriber.py` in Media Service:

```python
# In _execute_trigger_action method, add handlers for other action types:

if action.action_type == "email":
    await self._execute_email_action(action, trigger_data, db)
elif action.action_type == "webhook":
    await self._execute_webhook_action(action, trigger_data, db)
elif action.action_type == "log":
    await self._execute_log_action(action, trigger_data, db)
```

## Configuration

### Email (SMTP)

Configure in `.env`:
```env
MAIL_ENABLED=True
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833).

### Webhooks

Webhooks are enabled by default. Configure retry behavior:
```env
WEBHOOK_ENABLED=True
WEBHOOK_MAX_RETRIES=3
WEBHOOK_RETRY_DELAY=5
```

### Push Notifications

#### Firebase (Android)
```env
PUSH_ENABLED=True
FCM_SERVER_KEY=your-fcm-server-key
FCM_PROJECT_ID=your-project-id
```

#### APNS (iOS)
```env
APNS_ENABLED=True
APNS_KEY_PATH=/path/to/key.p8
APNS_KEY_ID=your-key-id
APNS_TEAM_ID=your-team-id
```

## Database Schema

### communication_logs
- Tracks all communications (email, webhook, push, audit)
- Stores delivery status, attempts, errors
- Links to trigger sources

### email_templates
- Reusable email templates
- Variable substitution support
- Categorization

### webhook_configs
- Reusable webhook configurations
- Authentication settings
- Retry policies
- Usage statistics

## Development

### Run Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
flake8 src/
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## Service Discovery

The service automatically registers with the Discovery Service if available. Configure in `.env`:

```env
SERVICE_DISCOVERY_ENABLED=true
DISCOVERY_SERVICE_URL=http://localhost:8006
```

## Monitoring

The service exposes Prometheus metrics at `/metrics` (when enabled).

## Security

- All sensitive data (passwords, tokens) should be encrypted in production
- Use environment variables for secrets, never hardcode
- Enable rate limiting in production
- Use HTTPS for webhook endpoints
- Validate webhook signatures when possible

## License

Proprietary - PPL Meta Platform
