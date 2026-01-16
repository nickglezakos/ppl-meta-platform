# Communications Microservice Integration with Trigger Actions

## Overview

This document outlines the implementation steps to integrate the new **ppl-meta-communications** microservice with the existing trigger actions system in ppl-meta-media.

**Key Principle**: The communications service operates autonomously. All other services interact with it exclusively via REST API endpoints - **NO direct database queries**.

### Multi-Tenant Logging (Edge Deployment Model)

The Communications Service supports **edge deployment multi-tenancy** where each tenant runs a complete independent installation of the ppl-meta-platform on their own hardware.

#### Architecture Model

Each installation includes:
- **Complete ppl-meta-platform** running locally on customer hardware
- **Own Communications Service** with dedicated database
- **Unique installation identifier** set during setup/provisioning
- **Optional internet exposure** via VPN, port forwarding, or cloud proxy

Future: Central licensing service will issue application keys per installation.

#### Installation Identification

Every communication log automatically includes:

- **installation_id**: Unique UUID for this specific edge installation (set in `.env` during setup)
- **tenant_name**: Human-readable customer/site name for this installation

These values are **configured once per installation** and automatically included in all logs—no need to pass them through API calls.

#### Configuration During Installation

Set these in the Communications Service `.env` file during platform setup:

```bash
# Generate unique installation ID during setup
# Run: python -c "import uuid; print(uuid.uuid4())"
INSTALLATION_ID=550e8400-e29b-41d4-a716-446655440000

# Set customer/site name
TENANT_NAME=Acme Corp - Main Office
```

Once configured, all communication logs from this installation will automatically include these identifiers.

#### Remote Support Scenarios

**Option A: Direct Connection**
```
Support Agent → VPN/SSH → Customer Installation → Query local API
```
Support connects directly to customer's installation and views logs via local Communications Service.

**Option B: Log Aggregation (Future)**
```
Each Installation → Pushes logs → Central Support Dashboard
```
Installations optionally forward logs to central monitoring service (filtered by installation_id).

**Option C: Manual Export**
```
Customer → Export logs via UI → Send to support → Analysis
```
Customer exports logs (including installation_id) and sends to support team.

## Architecture

```
┌─────────────────────┐
│  ppl-meta-media     │
│  (Trigger System)   │
│                     │
│  Redis Subscriber   │
│  ├─ Trigger Eval    │
│  └─ Action Execute  │
└──────────┬──────────┘
           │ HTTP REST API calls
           ▼
┌─────────────────────────────┐
│  ppl-meta-communications    │
│  (Port 8009)                │
│                             │
│  ├─ Email Service           │
│  ├─ Webhook Manager         │
│  ├─ Notification Service    │
│  └─ Audit Logging           │
│                             │
│  Database: ppl_communications_db │
└─────────────────────────────┘
```

## Implementation Steps

### Phase 1: Communications Service Setup ✅ COMPLETED

#### 1.1 Create Database ✅

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE ppl_communications_db;

# Grant permissions (if needed)
GRANT ALL PRIVILEGES ON DATABASE ppl_communications_db TO postgres;
```

**Status**: Database `ppl_communications_db` created with tables:
- `communication_logs` - Tracks all communications
- `email_templates` - Stores email templates  
- `webhook_configs` - Stores webhook configurations

#### 1.2 Install Dependencies ✅

```bash
cd ppl-meta-communications

# Create virtual environment with Python 3.11
python3.11 -m venv venv
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Install additional required packages
pip install 'pydantic[email]' email-validator
```

**Verified**: All packages installed successfully with Python 3.11.5

#### 1.3 Configure Environment ✅

The `.env` file is already configured with installation-specific values:

```bash
# ppl-meta-communications/.env

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ppl_communications_db
PORT=8009

# Communication Features
WEBHOOK_ENABLED=True
MAIL_ENABLED=False  # Enable when SMTP configured
AUDIT_LOG_ENABLED=True

# Installation Identification
INSTALLATION_ID=550e8400-e29b-41d4-a716-446655440000
TENANT_NAME=Example Customer - Main Site
```

**Note**: Installation identifiers are automatically included in all communication logs.

#### 1.4 Start the Service ✅

A startup script has been created for convenience:

```bash
# Use the startup script
./ppl-meta-communications/start_service.sh

# Or run manually from the parent directory:
cd ppl-meta-communications
venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8009 --reload
```

**Verify service is running:**
- Health check: http://localhost:8009/health
- API docs: http://localhost:8009/docs
- Logs: `/Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-communications.log`

**Service Status**: Running successfully on port 8009 ✅

### Phase 2: Media Service Integration

#### 2.1 Update Media Service Configuration

Add communications service URL to Media Service environment:

```bash
# ppl-meta-media/.env
COMMUNICATIONS_SERVICE_URL=http://localhost:8009
```

#### 2.2 Update Media Service Config

```python
# ppl-meta-media/src/config.py

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Communications Service
    COMMUNICATIONS_SERVICE_URL: str = Field(
        default="http://localhost:8009",
        env="COMMUNICATIONS_SERVICE_URL"
    )
```

#### 2.3 Create Communications Client

Create a new file for the HTTP client:

```python
# ppl-meta-media/src/services/communications_client.py

import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class CommunicationsClient:
    """Client for interacting with Communications Service via REST API."""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    async def send_email(
        self,
        to: List[str],
        subject: str,
        text_body: str,
        html_body: Optional[str] = None,
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an email via Communications Service."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/email/send",
                    json={
                        "to": to,
                        "subject": subject,
                        "text_body": text_body,
                        "html_body": html_body,
                        "triggered_by": triggered_by,
                        "trigger_type": trigger_type,
                        "trigger_id": trigger_id,
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to send email via Communications Service: {e}")
            return {"success": False, "message": str(e)}
    
    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a webhook via Communications Service."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/webhook/send",
                    json={
                        "url": url,
                        "method": method,
                        "payload": payload,
                        "headers": headers,
                        "triggered_by": triggered_by,
                        "trigger_type": trigger_type,
                        "trigger_id": trigger_id,
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to send webhook via Communications Service: {e}")
            return {"success": False, "message": str(e)}
    
    async def send_webhook_from_config(
        self,
        config_name: str,
        payload: Dict[str, Any],
        triggered_by: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a webhook using a saved configuration."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/webhook/send/config/{config_name}",
                    json=payload,
                    params={
                        "triggered_by": triggered_by,
                        "trigger_type": trigger_type,
                        "trigger_id": trigger_id,
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to send webhook from config via Communications Service: {e}")
            return {"success": False, "message": str(e)}
    
    async def log_audit_event(
        self,
        event_type: str,
        event_source: str,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        severity: str = "info",
    ) -> Dict[str, Any]:
        """Create an audit log entry."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/audit/log",
                    json={
                        "event_type": event_type,
                        "event_source": event_source,
                        "event_data": event_data,
                        "user_id": user_id,
                        "ip_address": ip_address,
                        "severity": severity,
                    }
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to log audit event via Communications Service: {e}")
            return {"success": False, "message": str(e)}
```

#### 2.4 Update Redis Subscriber to Use Communications Client

Modify the trigger action execution in Redis subscriber:

```python
# ppl-meta-media/src/services/redis_subscriber.py

from src.services.communications_client import CommunicationsClient
from src.config import get_config

config = get_config()

# In the class initialization or as a module-level variable
_communications_client = None

def get_communications_client() -> CommunicationsClient:
    """Get or create communications client singleton."""
    global _communications_client
    if _communications_client is None:
        _communications_client = CommunicationsClient(
            base_url=config.COMMUNICATIONS_SERVICE_URL
        )
    return _communications_client


# In InstantDetectionSubscriber class, modify _execute_trigger_action:

async def _execute_trigger_action(self, trigger: Trigger, db: Session):
    """Execute the action associated with this trigger."""
    from src.models.user_trigger_action import UserTriggerAction
    
    logger.info(f"  🎬 Executing trigger action...")
    logger.info(f"     Action UUID: {trigger.action_uuid}")
    
    # Look up the action
    action = db.query(UserTriggerAction).filter(
        UserTriggerAction.uuid == trigger.action_uuid
    ).first()
    
    if not action:
        logger.error(f"     ❌ Action not found: {trigger.action_uuid}")
        return
    
    logger.info(f"     Action Type: {action.action_type}")
    logger.info(f"     Action Name: {action.name}")
    
    # Route to appropriate handler
    if action.action_type == "digital_signage":
        await self._execute_signage_action(action, db)
    elif action.action_type == "email":
        await self._execute_email_action(action, trigger, db)
    elif action.action_type == "webhook":
        await self._execute_webhook_action(action, trigger, db)
    elif action.action_type == "log":
        await self._execute_log_action(action, trigger, db)
    else:
        logger.warning(f"     ⚠️ Unsupported action type: {action.action_type}")


async def _execute_email_action(self, action, trigger: Trigger, db: Session):
    """Execute email action via Communications Service."""
    logger.info(f"  📧 Executing email action...")
    
    try:
        # Parse action_config
        config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
        
        recipients = config.get("recipients", [])  # List of email addresses
        subject = config.get("subject", "Trigger Alert")
        body_template = config.get("body", "Trigger '{trigger_name}' was fired.")
        
        # Substitute variables in template
        body = body_template.format(
            trigger_name=trigger.name,
            trigger_id=str(trigger.uuid),
        )
        
        logger.info(f"     Recipients: {recipients}")
        logger.info(f"     Subject: {subject}")
        
        # Call Communications Service
        # Note: installation_id and tenant_name are automatically included from Communications Service config
        comms_client = get_communications_client()
        result = await comms_client.send_email(
            to=recipients,
            subject=subject,
            text_body=body,
            triggered_by="media_service",
            trigger_type="trigger_action",
            trigger_id=str(trigger.uuid),
        )
        
        if result.get("success"):
            logger.info(f"     ✅ Email sent successfully. Log UUID: {result.get('log_uuid')}")
        else:
            logger.error(f"     ❌ Email failed: {result.get('message')}")
    
    except Exception as e:
        logger.error(f"     ❌ Error executing email action: {e}", exc_info=True)


async def _execute_webhook_action(self, action, trigger: Trigger, db: Session):
    """Execute webhook action via Communications Service."""
    logger.info(f"  🔗 Executing webhook action...")
    
    try:
        # Parse action_config
        config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
        
        webhook_url = config.get("url")
        method = config.get("method", "POST")
        
        # Build payload
        payload = {
            "event": "trigger_fired",
            "trigger_id": str(trigger.uuid),
            "trigger_name": trigger.name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": config.get("payload_data", {}),
        }
        
        logger.info(f"     Webhook URL: {webhook_url}")
        logger.info(f"     Method: {method}")
        
        # Call Communications Service
        # Note: installation_id and tenant_name are automatically included from Communications Service config
        comms_client = get_communications_client()
        result = await comms_client.send_webhook(
            url=webhook_url,
            payload=payload,
            method=method,
            triggered_by="media_service",
            trigger_type="trigger_action",
            trigger_id=str(trigger.uuid),
        )
        
        if result.get("success"):
            logger.info(f"     ✅ Webhook sent successfully. Log UUID: {result.get('log_uuid')}")
            logger.info(f"     Status Code: {result.get('status_code')}")
        else:
            logger.error(f"     ❌ Webhook failed: {result.get('message')}")
    
    except Exception as e:
        logger.error(f"     ❌ Error executing webhook action: {e}", exc_info=True)


async def _execute_log_action(self, action, trigger: Trigger, db: Session):
    """Execute audit log action via Communications Service."""
    logger.info(f"  📋 Executing audit log action...")
    
    try:
        # Parse action_config
        config = json.loads(action.action_config) if isinstance(action.action_config, str) else action.action_config
        
        event_data = {
            "trigger_id": str(trigger.uuid),
            "trigger_name": trigger.name,
            "action_name": action.name,
            "custom_data": config.get("data", {}),
        }
        
        # Call Communications Service
        # Note: installation_id and tenant_name are automatically included from Communications Service config
        comms_client = get_communications_client()
        result = await comms_client.log_audit_event(
            event_type="trigger_fired",
            event_source="media_service",
            event_data=event_data,
            severity=config.get("severity", "info"),
        )
        
        if result.get("success"):
            logger.info(f"     ✅ Audit log created. Log UUID: {result.get('log_uuid')}")
        else:
            logger.error(f"     ❌ Audit log failed: {result.get('message')}")
    
    except Exception as e:
        logger.error(f"     ❌ Error executing log action: {e}", exc_info=True)
```

### Phase 3: Action Configuration Schema

Update the action configuration schema to include email, webhook, and log configurations:

#### 3.1 Email Action Config

```json
{
  "action_type": "email",
  "action_config": {
    "recipients": ["admin@example.com", "alerts@example.com"],
    "subject": "Trigger Alert: {trigger_name}",
    "body": "Trigger '{trigger_name}' (ID: {trigger_id}) was fired at {timestamp}."
  }
}
```

#### 3.2 Webhook Action Config

```json
{
  "action_type": "webhook",
  "action_config": {
    "url": "https://webhook.site/your-endpoint",
    "method": "POST",
    "payload_data": {
      "custom_field": "value"
    }
  }
}
```

#### 3.3 Log Action Config

```json
{
  "action_type": "log",
  "action_config": {
    "severity": "info",
    "data": {
      "category": "trigger_events",
      "tags": ["marketing", "demo"]
    }
  }
}
```

### Phase 4: Testing

#### 4.1 Test Email Action

```bash
# 1. Create email action via API
curl -X POST http://localhost:8000/api/v1/actions \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email Alert",
    "action_type": "email",
    "action_config": "{\"recipients\": [\"test@example.com\"], \"subject\": \"Test Alert\", \"body\": \"Trigger fired!\"}",
    "is_active": true
  }'

# 2. Link to trigger
# 3. Fire trigger and check Communications Service logs
tail -f /Users/nickgklezakos/Documents/ppl-meta-code/logs/ppl-meta-communications.log
```

#### 4.2 Test Webhook Action

```bash
# Use webhook.site for testing
# 1. Go to https://webhook.site and get your unique URL
# 2. Create webhook action with that URL
# 3. Fire trigger
# 4. Check webhook.site to see the received payload
```

#### 4.3 Query Communication Logs

```bash
# Get all logs
curl http://localhost:8009/api/v1/audit/logs?page=1&page_size=50

# Filter by trigger ID
curl http://localhost:8009/api/v1/audit/logs?trigger_id=your-trigger-uuid

# Filter by type
curl http://localhost:8009/api/v1/audit/logs?type=email&status=delivered

# Filter by installation (for multi-tenant support)
curl http://localhost:8009/api/v1/audit/logs?installation_id=550e8400-e29b-41d4-a716-446655440000

# Search by tenant name
curl "http://localhost:8009/api/v1/audit/logs?tenant_name=Demo%20Customer"

# Combined filters for customer support troubleshooting
curl "http://localhost:8009/api/v1/audit/logs?installation_id=550e8400-e29b-41d4-a716-446655440000&type=webhook&status=failed"
```

### Phase 5: Production Considerations

#### 5.1 Error Handling

The Communications Service includes:
- Automatic retry logic (configurable)
- Error logging
- Status tracking (pending, sent, delivered, failed)
- Detailed error messages in communication logs

#### 5.2 Rate Limiting

Configure in Communications Service `.env`:

```bash
RATE_LIMIT_ENABLED=True
EMAIL_RATE_LIMIT_PER_MINUTE=10
WEBHOOK_RATE_LIMIT_PER_MINUTE=60
```

#### 5.3 Email Configuration

For production email:

```bash
# Gmail example
MAIL_ENABLED=True
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-specific-password
```

#### 5.4 Monitoring

Monitor Communications Service health:

```bash
# Health check
curl http://localhost:8009/health

# Check logs
tail -f logs/ppl-meta-communications.log

# Query recent communication attempts
curl http://localhost:8009/api/v1/audit/logs?status=failed
```

## Summary

**Key Integration Points:**

1. ✅ Communications Service runs independently on port 8009
2. ✅ Media Service calls Communications Service via HTTP REST API
3. ✅ No direct database access between services
4. ✅ All communication attempts are logged with tracking
5. ✅ Automatic retry logic for failed attempts
6. ✅ Comprehensive audit trail

**Benefits:**

- **Separation of Concerns**: Communications logic isolated in dedicated service
- **Reusability**: Any service can use communications endpoints
- **Scalability**: Communications Service can scale independently
- **Reliability**: Built-in retry logic and error tracking
- **Auditability**: Complete log of all communications
- **Maintainability**: Single place to update email/webhook/notification logic
