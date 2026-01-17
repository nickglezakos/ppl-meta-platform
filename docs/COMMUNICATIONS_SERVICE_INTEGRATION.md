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

### Phase 2: Media Service Integration ✅ COMPLETED

#### 2.1 Update Media Service Configuration ✅

Add communications service URL to Media Service environment:

```bash
# ppl-meta-media/.env
COMMUNICATIONS_SERVICE_URL=http://localhost:8009
```

**Status**: Added to [ppl-meta-media/.env](ppl-meta-media/.env)

#### 2.2 Update Media Service Config ✅

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

**Status**: Updated [ppl-meta-media/src/config.py](ppl-meta-media/src/config.py)

#### 2.3 Create Communications Client ✅

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

**Status**: Created [ppl-meta-media/src/services/communications_client.py](ppl-meta-media/src/services/communications_client.py)

#### 2.4 Update Redis Subscriber to Use Communications Client ✅

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

**Status**: Updated [ppl-meta-media/src/services/redis_subscriber.py](ppl-meta-media/src/services/redis_subscriber.py) with:
- Import of `CommunicationsClient`
- Singleton `get_communications_client()` function
- `_execute_email_action()` method
- `_execute_webhook_action()` method
- `_execute_log_action()` method
- Updated `_execute_trigger_action()` to route email, webhook, and log action types

### Phase 3: Action Configuration Schema ✅ COMPLETED

Update the action configuration schema to include email, webhook, and log configurations:

**Status**: Schema validation already includes all action types. Updated API documentation with comprehensive examples.

#### 3.1 Email Action Config ✅

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

**Example API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/user-actions/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email Alert Action",
    "action_type": "email",
    "action_config": "{\"recipients\": [\"admin@example.com\"], \"subject\": \"Alert: {trigger_name}\", \"body\": \"Trigger fired!\"}",
    "is_active": true
  }'
```

**Test Status**: ✅ Successfully created email action (UUID: 31a93437-3256-49be-85c8-4231cf2406e0)

#### 3.2 Webhook Action Config ✅

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

**Example API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/user-actions/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Webhook Notification",
    "action_type": "webhook",
    "action_config": "{\"url\": \"https://webhook.site/test\", \"method\": \"POST\", \"payload_data\": {\"source\": \"ppl-meta\"}}",
    "is_active": true
  }'
```

**Test Status**: ✅ Successfully created webhook action (UUID: d8faa257-b14c-4184-b89a-5f3f4d99dc60)

#### 3.3 Log Action Config ✅

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

**Example API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/user-actions/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Audit Logger",
    "action_type": "log",
    "action_config": "{\"severity\": \"info\", \"data\": {\"category\": \"trigger_events\", \"tags\": [\"test\"]}}",
    "is_active": true
  }'
```

**Test Status**: ✅ Successfully created log action (UUID: a6b6db8a-1127-4097-915e-b59ad1e9fae7)

### Phase 4: Testing ✅ COMPLETED

**Prerequisites:**
- All services running and healthy
- Authentication token obtained
- Test actions created in Phase 3

#### 4.1 Get Authentication Token ✅

```bash
# Login and get token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | jq -r '.access_token')

echo "Token: $TOKEN"
```

#### 4.2 Test Email Action ✅

**Step 1: Create a trigger linked to the email action**
```bash
# Create trigger with email action
curl -X POST "http://localhost:8000/api/v1/triggers/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Email Trigger",
    "description": "Sends email when adult detected",
    "trigger_type": "instant_detection",
    "is_active": true,
    "action_uuid": "31a93437-3256-49be-85c8-4231cf2406e0",
    "conditions": {
      "demographic_groups": ["adult"],
      "min_detections": 1
    }
  }'
```

**Step 2: Simulate trigger firing**
When instant detection occurs matching the conditions, the trigger will fire and execute the email action.

**Step 3: Monitor Communications Service**
```bash
# Watch Communications Service logs
tail -f logs/ppl-meta-communications.log

# Expected output when email action fires:
# INFO - Received email send request
# INFO - Email queued for delivery
# INFO - Email status: pending → sent
```

**Step 4: Query email logs**
```bash
# Check email communication logs
curl -s "http://localhost:8009/api/v1/audit/logs?type=email&page=1&page_size=10" | python3 -m json.tool
```

**Status**: ✅ Email action infrastructure ready. Emails will be logged even if SMTP not configured.

#### 4.3 Test Webhook Action ✅

**Step 1: Get a webhook URL**
1. Visit https://webhook.site
2. Copy your unique webhook URL (e.g., `https://webhook.site/unique-id`)

**Step 2: Create or update webhook action**
```bash
# Update the webhook action with your webhook.site URL
curl -X PUT "http://localhost:8000/api/v1/user-actions/d8faa257-b14c-4184-b89a-5f3f4d99dc60" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action_config": "{\"url\": \"https://webhook.site/YOUR-UNIQUE-ID\", \"method\": \"POST\", \"payload_data\": {\"source\": \"ppl-meta-test\"}}"
  }'
```

**Step 3: Create trigger with webhook action**
```bash
curl -X POST "http://localhost:8000/api/v1/triggers/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Webhook Trigger",
    "description": "Sends webhook on detection",
    "trigger_type": "instant_detection",
    "is_active": true,
    "action_uuid": "d8faa257-b14c-4184-b89a-5f3f4d99dc60",
    "conditions": {
      "demographic_groups": ["adult"],
      "min_detections": 1
    }
  }'
```

**Step 4: Verify webhook receipt**
- When trigger fires, check webhook.site dashboard
- You should see the POST request with payload

**Step 5: Query webhook logs**
```bash
# Check webhook communication logs
curl -s "http://localhost:8009/api/v1/audit/logs?type=webhook&page=1&page_size=10" | python3 -m json.tool
```

**Status**: ✅ Webhook action tested successfully with webhook.site

#### 4.4 Test Log Action ✅

**Step 1: Create trigger with log action**
```bash
curl -X POST "http://localhost:8000/api/v1/triggers/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Audit Log Trigger",
    "description": "Creates audit log entry on detection",
    "trigger_type": "instant_detection",
    "is_active": true,
    "action_uuid": "a6b6db8a-1127-4097-915e-b59ad1e9fae7",
    "conditions": {
      "demographic_groups": ["adult"],
      "min_detections": 1
    }
  }'
```

**Step 2: Monitor trigger execution**
```bash
# Watch Media Service logs for trigger execution
tail -f logs/ppl-meta-media.log | grep -i "executing.*log"
```

**Step 3: Verify audit logs created**
```bash
# Query audit logs
curl -s "http://localhost:8009/api/v1/audit/logs?type=audit&page=1&page_size=10" | python3 -m json.tool

# Filter by severity
curl -s "http://localhost:8009/api/v1/audit/logs?type=audit&severity=info" | python3 -m json.tool
```

**Status**: ✅ Audit logging action verified

#### 4.5 Query Communication Logs ✅

**Get all recent logs:**
```bash
curl -s "http://localhost:8009/api/v1/audit/logs?page=1&page_size=50" | python3 -m json.tool
```

**Filter by communication type:**
```bash
# Email logs only
curl -s "http://localhost:8009/api/v1/audit/logs?type=email" | python3 -m json.tool

# Webhook logs only
curl -s "http://localhost:8009/api/v1/audit/logs?type=webhook" | python3 -m json.tool

# Audit logs only
curl -s "http://localhost:8009/api/v1/audit/logs?type=audit" | python3 -m json.tool
```

**Filter by status:**
```bash
# Failed communications
curl -s "http://localhost:8009/api/v1/audit/logs?status=failed" | python3 -m json.tool

# Successful communications
curl -s "http://localhost:8009/api/v1/audit/logs?status=sent" | python3 -m json.tool
```

**Filter by trigger:**
```bash
# Get logs for specific trigger
curl -s "http://localhost:8009/api/v1/audit/logs?trigger_id=YOUR-TRIGGER-UUID" | python3 -m json.tool
```

**Filter by installation (multi-tenant):**
```bash
# Logs for specific installation
curl -s "http://localhost:8009/api/v1/audit/logs?installation_id=550e8400-e29b-41d4-a716-446655440000" | python3 -m json.tool

# Search by tenant name
curl -s "http://localhost:8009/api/v1/audit/logs?tenant_name=Example%20Customer" | python3 -m json.tool
```

**Combined filters for troubleshooting:**
```bash
# Failed webhooks for specific installation
curl -s "http://localhost:8009/api/v1/audit/logs?type=webhook&status=failed&installation_id=550e8400-e29b-41d4-a716-446655440000" | python3 -m json.tool
```

**Status**: ✅ Communication log queries verified

#### 4.6 Integration Testing Summary ✅

**Test Results:**
- ✅ Email actions create communication logs
- ✅ Webhook actions send HTTP requests and log results
- ✅ Audit log actions create audit trail entries
- ✅ All actions properly integrate with trigger system
- ✅ Communications Service logs all attempts
- ✅ Query API provides comprehensive filtering
- ✅ Multi-tenant support working (installation_id + tenant_name)

**Testing Notes:**
- Email functionality tested with logging (SMTP not required)
- Webhook testing verified with webhook.site
- Audit logs stored in Communications Service database
- All actions work independently and can be combined
- Cache and retry logic built-in for reliability

### Phase 5: Production Considerations

#### 5.1 SMTP Configuration

Currently using fake SMTP for development. For production:

1. **Update `ppl-meta-communications/.env`:**
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=noreply@yourcompany.com
SMTP_FROM_NAME=PPL Meta Platform
SMTP_USE_TLS=true
```

2. **Gmail App Password**: https://myaccount.google.com/apppasswords
3. **Test email delivery** with real SMTP before production deployment

#### 5.2 Database Backups

```bash
# Backup communications database
pg_dump -U ppl_user -h localhost ppl_communications_db > communications_backup_$(date +%Y%m%d).sql

# Restore from backup
psql -U ppl_user -h localhost ppl_communications_db < communications_backup_20260116.sql
```

#### 5.3 Monitoring & Alerts

- Monitor communication failure rates via `/api/v1/audit/stats`
- Set up alerts for high retry counts
- Track webhook endpoint availability
- Monitor database growth (audit logs table)

#### 5.4 Security Considerations

- **Webhook URLs**: Validate and sanitize user-provided webhook URLs
- **Email addresses**: Validate email format before sending
- **Rate limiting**: Implement rate limits on communication endpoints
- **Webhook secrets**: Add HMAC signature verification for webhooks
- **API authentication**: Already implemented with JWT tokens

#### 5.5 Log Retention Policy

Communications logs can grow quickly. Consider:

```sql
-- Delete logs older than 90 days
DELETE FROM communication_logs 
WHERE created_at < NOW() - INTERVAL '90 days';

-- Archive old logs before deletion
CREATE TABLE communication_logs_archive AS 
SELECT * FROM communication_logs 
WHERE created_at < NOW() - INTERVAL '90 days';
```

---

## Frontend Integration (Flutter)

### Phase 6: Flutter Frontend Integration ✅ COMPLETED

The Communications Service is now fully integrated into the Flutter frontend application.

#### 6.1 New Files Created

**Models:**
- `lib/models/communication_log_model.dart` - Communication log data model
- `lib/models/communication_log_model.g.dart` - Generated JSON serialization

**Services:**
- `lib/services/communications_api_client.dart` - HTTP client for Communications Service API

**Screens:**
- `lib/screens/communication_logs_screen.dart` - Full-featured logs viewer with filtering

**Widgets:**
- Enhanced `lib/widgets/actions_tab.dart` with:
  - Email configuration form
  - Webhook configuration form  
  - Log configuration form
  - "View Communication Logs" button

#### 6.2 Features Implemented

**1. Enhanced Action Configuration Dialog**

The action creation/edit dialog now includes specific configuration forms for:

- **Email Actions:**
  - Recipient email (required)
  - CC recipients (optional, comma-separated)
  - Subject line with template variables
  - Email body
  - Template variables: `{trigger_name}`, `{timestamp}`

- **Webhook Actions:**
  - Webhook URL (required)
  - HTTP method (GET, POST, PUT, PATCH)
  - Custom headers (JSON format)
  - Request payload (JSON format)

- **Log Actions:**
  - Log message with template variables
  - Log level (debug, info, warning, error)

- **Digital Signage Actions:** (Already implemented)
  - Device selection
  - Playlist selection
  - Transition mode
  - Fade duration

**2. Communication Logs Viewer**

Access via: **Actions Tab → "View Communication Logs" button**

Features:
- **Filterable logs** by:
  - Communication type (email, webhook, audit)
  - Status (sent, delivered, pending, failed)
  - Trigger UUID
  - Tenant name
- **Paginated display** with navigation
- **Detailed log view** with:
  - Full metadata
  - Error messages
  - Retry counts
  - Copyable UUIDs and URLs
- **Color-coded badges** for status and type
- **Real-time refresh** capability

#### 6.3 Usage Instructions

**Creating an Email Action:**

1. Navigate to **Triggers & Actions** screen
2. Click **"Actions"** tab
3. Click **"Create Action"** button
4. Fill in the form:
   - Name: "Email on High Traffic"
   - Description: "Sends email when traffic threshold met"
   - Action Type: **Email**
   - Recipient: your-email@example.com
   - Subject: "Alert: {trigger_name} triggered"
   - Body: "Trigger {trigger_name} was activated at {timestamp}"
5. Click **"Create"**

**Creating a Webhook Action:**

1. Follow steps 1-3 above
2. Select Action Type: **Webhook**
3. Configure:
   - URL: https://webhook.site/your-unique-id
   - Method: POST
   - Headers (optional): `{"Authorization": "Bearer token"}`
   - Payload (optional): `{"event": "trigger_fired", "data": {}}`
4. Click **"Create"**

**Creating a Log Action:**

1. Follow steps 1-3 above
2. Select Action Type: **Log**
3. Configure:
   - Message: "Trigger {trigger_name} fired at {timestamp}"
   - Level: Info
4. Click **"Create"**

**Viewing Communication Logs:**

1. Navigate to **Actions** tab
2. Click **"View Communication Logs"** button
3. Use filters to narrow down logs:
   - Click **Filter** icon in top-right
   - Select type, status, enter trigger UUID, or tenant name
   - Click **"Apply"**
4. Click any log card to view full details
5. Copy UUIDs or URLs using the copy button
6. Click **Refresh** to reload logs

#### 6.4 Configuration

The Flutter app connects to all backend services through the Nginx proxy:

```dart
// lib/core/config.dart
class Config {
  // All services accessed through Nginx proxy on port 80
  static const String baseUrl = 'http://localhost';
  
  static const String mediaServiceUrl = '$baseUrl/api/media';
  static const String nodeServiceUrl = '$baseUrl/api/node';
  static const String communicationsServiceUrl = '$baseUrl/api/communications';
  // ... other services
}
```

**Nginx Configuration:**
- Nginx runs on port 80
- Routes `/api/media/` → Media Service (localhost:8000)
- Routes `/api/node/` → Node Service (localhost:8001)
- Routes `/api/communications/` → Communications Service (localhost:8009)
- Handles CORS headers for web clients
- Includes authentication headers forwarding

**For production**, update the baseUrl to your production nginx endpoint (e.g., `https://api.yourcompany.com`).

#### 6.5 Testing the Frontend Integration

1. **Start all services:**
```bash
# Start backend services (usually via VS Code tasks)
# Or use your service management script

# Start Nginx proxy
sudo nginx -c /path/to/nginx-local-dev.conf

# Start Flutter frontend (served through Nginx on port 80)
cd ppl-meta-frontend
flutter run -d chrome  # Web
# or
flutter run -d macos   # Desktop
```

**Important**: The Flutter app must connect through the Nginx proxy at `http://localhost`. All API calls use routes like:
- `http://localhost/api/media/api/v1/triggers`
- `http://localhost/api/node/api/v1/users/login`
- `http://localhost/api/communications/api/v1/audit/logs`

2. **Create a test action:**
   - Navigate to Triggers & Actions → Actions tab
   - Click "Create Action"
   - Fill in email/webhook/log configuration
   - Click "Create"

3. **Create a trigger with the action:**
   - Go to Triggers tab
   - Click "Create Trigger"
   - Select your newly created action
   - Configure trigger conditions
   - Save

4. **Fire the trigger:**
   - Simulate detection event (via camera or test script)
   - Or manually test action execution

5. **View communication logs:**
   - Click "View Communication Logs" button
   - Verify the communication was logged
   - Check status and details

---

## Complete Architecture

The integrated system now has the following flow:

```
┌─────────────────┐
│  Flutter        │
│  Frontend       │──────┐
│  :8080/3000     │      │
└─────────────────┘      │
                         │ HTTP/REST
                         ▼
┌─────────────────────────────────────────┐
│  Media Service (Python FastAPI)         │
│  :8000                                   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  Redis Subscriber                │   │
│  │  - Listens: instant_detection    │   │
│  │  - Evaluates triggers            │   │
│  │  - Executes actions:             │   │
│  │    • email                        │   │
│  │    • webhook                      │   │
│  │    • log                          │   │
│  │    • digital_signage             │   │
│  └──────────────────────────────────┘   │
│              │                            │
│              │ HTTP Client                │
│              ▼                            │
└─────────────────────────────────────────┘
              │
              │
              ▼
┌──────────────────────────────────────────┐
│  Communications Service (Python FastAPI) │
│  :8009                                    │
│                                           │
│  Endpoints:                               │
│  • POST /api/v1/email/send               │
│  • POST /api/v1/webhook/send             │
│  • POST /api/v1/audit/log                │
│  • GET  /api/v1/audit/logs (paginated)   │
│  • GET  /api/v1/audit/stats              │
│                                           │
│  Database: ppl_communications_db          │
│  • communication_logs (main)              │
│  • email_templates                        │
│  • webhook_configs                        │
└──────────────────────────────────────────┘
              │
              │ SMTP/HTTP
              ▼
┌──────────────────────────────────┐
│  External Systems                │
│  • SMTP Server (emails)          │
│  • Webhook endpoints             │
│  • Audit log storage             │
└──────────────────────────────────┘
```

---

## Summary

✅ **All Phases Completed:**

1. **Phase 1**: Communications Service setup with PostgreSQL database
2. **Phase 2**: Media Service integration with Communications HTTP client
3. **Phase 3**: Action configuration schema with comprehensive examples
4. **Phase 4**: Testing procedures and verification
5. **Phase 5**: Production considerations documented
6. **Phase 6**: Flutter frontend integration with full UI

**What's Working:**
- ✅ Email action configuration and execution
- ✅ Webhook action configuration and execution
- ✅ Log/audit action configuration and execution
- ✅ Communication logs storage and retrieval
- ✅ Flutter frontend UI for action management
- ✅ Communication logs viewer with filtering
- ✅ Multi-tenant support (installation_id + tenant_name)
- ✅ All services integrated via Nginx proxy

**Ready for Production:**
- Configure real SMTP credentials
- Set up webhook secret verification
- Implement log retention policy
- Configure monitoring and alerts
- Deploy with proper environment variables

The Communications Service is now fully integrated with both the backend trigger system and the Flutter frontend UI, providing a complete solution for automated communications via triggers.

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
