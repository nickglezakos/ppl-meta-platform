# PPL Meta Platform - Installation Identification Implementation Guide

## Overview

This document outlines the standard pattern for implementing installation-level identification across all ppl-meta microservices. This pattern enables edge deployment multi-tenancy where each customer runs an independent installation of the platform on their own hardware.

## Rationale

### Architecture Model

**Edge/On-Premise Multi-Instance Deployment:**
- Each customer runs a complete ppl-meta-platform installation on their own hardware
- Each installation is independent with its own databases and services
- Installations may be exposed via VPN, port forwarding, or cloud proxy
- Future: Central licensing service will issue application keys per installation

### Business Value

1. **Remote Support**: Support agents can identify which customer installation generated logs/events
2. **Log Aggregation**: Optional centralized monitoring filtered by installation
3. **Troubleshooting**: Quickly isolate issues to specific customer sites
4. **Reporting**: Generate per-customer usage and performance reports
5. **Licensing**: Track installations for future license key management

## Installation Identification Fields

### Required Fields

**INSTALLATION_ID** (string, UUID format)
- Unique identifier for this specific edge installation
- Generated once during platform setup/provisioning
- Never changes for the lifetime of the installation
- Format: UUID v4 (e.g., `550e8400-e29b-41d4-a716-446655440000`)

**TENANT_NAME** (string, human-readable)
- Customer/site name for this installation
- Human-readable for easier log searching and reporting
- Can be updated if customer name changes
- Format: Free text (e.g., `"Acme Corp - Main Office"`)

### Storage Location

**Environment Variables (Preferred)**
```bash
# Set in each service's .env file during installation
INSTALLATION_ID=550e8400-e29b-41d4-a716-446655440000
TENANT_NAME=Acme Corp - Main Office
```

**Alternative: Central Configuration Service**
- Store in ppl-meta-discovery or configuration management
- Services query on startup and cache locally

## Implementation Steps

### Phase 1: Configuration Layer

#### 1.1 Update Configuration Class

Add installation fields to service config:

```python
# src/config.py

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # ... existing settings ...
    
    # Installation/Tenant Configuration (for edge deployment multi-tenancy)
    INSTALLATION_ID: Optional[str] = Field(default=None, env="INSTALLATION_ID")
    TENANT_NAME: Optional[str] = Field(default=None, env="TENANT_NAME")
    
    # ... rest of settings ...
```

#### 1.2 Update Environment Files

Add to `.env`:
```bash
# Installation/Tenant Configuration
# IMPORTANT: Set these during installation to identify this specific edge deployment
# INSTALLATION_ID should be a unique UUID generated during platform setup
# TENANT_NAME should be the customer/site name for this installation
INSTALLATION_ID=
TENANT_NAME=
```

Add to `.env.example`:
```bash
# Installation/Tenant Configuration (Edge Deployment Multi-Tenancy)
# IMPORTANT: Set these during platform installation to identify this specific edge deployment
# INSTALLATION_ID: Unique UUID for this installation (generate with: python -c "import uuid; print(uuid.uuid4())")
# TENANT_NAME: Customer/site name for this installation (e.g., "Acme Corp - Main Office")
# These values are automatically included in relevant logs/events for support/troubleshooting
INSTALLATION_ID=550e8400-e29b-41d4-a716-446655440000
TENANT_NAME=Example Customer - Main Site
```

### Phase 2: Database Schema Updates

#### 2.1 Add Installation Columns to Key Tables

Add to tables that need tenant tracking (events, logs, transactions, etc.):

```python
# Example: src/models/your_event_model.py

from sqlalchemy import Column, String, Index

class YourEventModel(Base):
    __tablename__ = "your_events"
    
    # ... existing columns ...
    
    # Installation identification
    installation_id = Column(String(200), nullable=True, index=True)
    tenant_name = Column(String(200), nullable=True)
```

**Which Tables to Update:**
- ✅ Event logs
- ✅ Audit trails
- ✅ User actions
- ✅ System events
- ✅ Transaction records
- ✅ Error logs
- ❌ Configuration tables (not needed)
- ❌ Static reference data (not needed)

#### 2.2 Create Database Migration

```python
# Example Alembic migration

def upgrade():
    op.add_column('your_events', sa.Column('installation_id', sa.String(200), nullable=True))
    op.add_column('your_events', sa.Column('tenant_name', sa.String(200), nullable=True))
    op.create_index('ix_your_events_installation_id', 'your_events', ['installation_id'])

def downgrade():
    op.drop_index('ix_your_events_installation_id', 'your_events')
    op.drop_column('your_events', 'tenant_name')
    op.drop_column('your_events', 'installation_id')
```

### Phase 3: Business Logic Updates

#### 3.1 Update Service Methods

Automatically include installation fields from config:

```python
# src/services/your_service.py

class YourService:
    def __init__(self, db: Session):
        self.db = db
        self.config = get_config()
    
    async def log_event(
        self,
        event_type: str,
        event_data: dict,
        user_id: Optional[str] = None,
    ):
        """Log an event with automatic installation identification."""
        event = YourEventModel(
            event_type=event_type,
            event_data=event_data,
            user_id=user_id,
            # Automatically include from config
            installation_id=self.config.INSTALLATION_ID,
            tenant_name=self.config.TENANT_NAME,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(event)
        self.db.commit()
        return event
```

**Key Principle**: Services should automatically include installation fields from config, NOT require them as parameters in every method call.

#### 3.2 Update Query Methods

Add installation filtering capability:

```python
def get_events(
    self,
    installation_id: Optional[str] = None,
    tenant_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[List[YourEventModel], int]:
    """Query events with optional installation filtering."""
    query = self.db.query(YourEventModel)
    
    # Apply filters
    if installation_id:
        query = query.filter(YourEventModel.installation_id == installation_id)
    if tenant_name:
        query = query.filter(YourEventModel.tenant_name.ilike(f"%{tenant_name}%"))
    if start_date:
        query = query.filter(YourEventModel.created_at >= start_date)
    
    total = query.count()
    offset = (page - 1) * page_size
    events = query.order_by(YourEventModel.created_at.desc()).offset(offset).limit(page_size).all()
    
    return events, total
```

### Phase 4: API Schema Updates

#### 4.1 Response Schemas

Include installation fields in responses for filtering/reporting:

```python
# src/schemas/your_schema.py

class EventResponse(BaseModel):
    id: int
    event_type: str
    event_data: Dict[str, Any]
    user_id: Optional[str]
    installation_id: Optional[str]  # Include in response
    tenant_name: Optional[str]      # Include in response
    created_at: str
    
    class Config:
        from_attributes = True


class EventQueryParams(BaseModel):
    """Query parameters for event listing."""
    installation_id: Optional[str] = Field(None, description="Filter by installation ID")
    tenant_name: Optional[str] = Field(None, description="Filter by tenant name")
    start_date: Optional[str] = Field(None, description="Filter by start date")
    page: int = Field(1, ge=1)
    page_size: int = Field(50, ge=1, le=500)
```

**Important**: Do NOT include installation_id/tenant_name in REQUEST schemas for create/update operations. These come from config automatically.

#### 4.2 Update API Routes

Add filtering parameters:

```python
# src/routes/your_routes.py

@router.get("/events", response_model=EventListResponse)
async def get_events(
    installation_id: Optional[str] = Query(None, description="Filter by installation"),
    tenant_name: Optional[str] = Query(None, description="Filter by tenant name"),
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Query events with installation filtering."""
    service = YourService(db)
    
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    events, total = service.get_events(
        installation_id=installation_id,
        tenant_name=tenant_name,
        start_date=start_dt,
        page=page,
        page_size=page_size,
    )
    
    # Convert to response models...
    return EventListResponse(events=event_responses, total=total, page=page, page_size=page_size)
```

### Phase 5: Logging and Monitoring

#### 5.1 Include in Structured Logs

```python
import logging
import structlog

logger = structlog.get_logger()

# Include installation context in all log messages
logger.info(
    "event_created",
    event_type=event_type,
    installation_id=self.config.INSTALLATION_ID,
    tenant_name=self.config.TENANT_NAME,
    user_id=user_id,
)
```

#### 5.2 Health Check Endpoint

Include installation info in health check:

```python
@router.get("/health")
async def health_check():
    """Health check endpoint with installation identification."""
    config = get_config()
    return {
        "status": "healthy",
        "service": "your-service-name",
        "version": "1.0.0",
        "installation_id": config.INSTALLATION_ID,
        "tenant_name": config.TENANT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
```

## Installation Procedure

### Step 1: Generate Installation ID

During platform installation, generate a unique UUID:

```bash
# Run once per installation
python -c "import uuid; print(uuid.uuid4())"
# Example output: 550e8400-e29b-41d4-a716-446655440000
```

### Step 2: Set in All Service .env Files

Update each service's `.env` file:

```bash
# In each service directory
nano ppl-meta-media/.env
nano ppl-meta-cameras/.env
nano ppl-meta-communications/.env
# ... etc for all services

# Set the SAME values in all services:
INSTALLATION_ID=550e8400-e29b-41d4-a716-446655440000
TENANT_NAME=Customer Name - Site Location
```

**Critical**: Use the SAME installation_id and tenant_name across all services in a single installation.

### Step 3: Create Installation Config Script

Create a setup script for installers:

```bash
#!/bin/bash
# setup-installation-id.sh

echo "PPL Meta Platform - Installation Setup"
echo "======================================="
echo ""

# Generate installation ID
INSTALLATION_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
echo "Generated Installation ID: $INSTALLATION_ID"
echo ""

# Prompt for tenant name
read -p "Enter customer/site name (e.g., 'Acme Corp - Main Office'): " TENANT_NAME
echo ""

# List of services to update
SERVICES=(
    "ppl-meta-node"
    "ppl-meta-media"
    "ppl-meta-cameras"
    "ppl-meta-gateway"
    "ppl-meta-orchestrator"
    "ppl-meta-vision"
    "ppl-meta-vmeta"
    "ppl-meta-discovery"
    "ppl-meta-bootcore"
    "ppl-meta-communications"
)

echo "Updating service configuration files..."
for service in "${SERVICES[@]}"; do
    if [ -f "$service/.env" ]; then
        # Remove old values if they exist
        sed -i.bak '/^INSTALLATION_ID=/d' "$service/.env"
        sed -i.bak '/^TENANT_NAME=/d' "$service/.env"
        
        # Add new values
        echo "" >> "$service/.env"
        echo "# Installation Identification" >> "$service/.env"
        echo "INSTALLATION_ID=$INSTALLATION_ID" >> "$service/.env"
        echo "TENANT_NAME=$TENANT_NAME" >> "$service/.env"
        
        echo "✓ Updated $service/.env"
    else
        echo "⚠ Skipped $service (no .env file found)"
    fi
done

echo ""
echo "Installation setup complete!"
echo ""
echo "Installation ID: $INSTALLATION_ID"
echo "Tenant Name: $TENANT_NAME"
echo ""
echo "Please restart all services for changes to take effect."
```

### Step 4: Document in Installation Guide

Add to main installation documentation:

```markdown
## Installation Identification Setup

During installation, set up unique identification for this edge deployment:

1. Run the installation setup script:
   ```bash
   cd /path/to/ppl-meta-code
   chmod +x setup-installation-id.sh
   ./setup-installation-id.sh
   ```

2. Follow the prompts to set customer/site name

3. Restart all services:
   ```bash
   ./manage-services.sh restart
   ```

4. Verify installation ID is set:
   ```bash
   curl http://localhost:8009/health | jq '.installation_id'
   ```
```

## Service-by-Service Checklist

For each microservice, implement the following:

- [ ] Add INSTALLATION_ID and TENANT_NAME to config.py
- [ ] Add fields to .env and .env.example
- [ ] Add columns to relevant database tables
- [ ] Create database migration
- [ ] Update service methods to use config values automatically
- [ ] Add installation filtering to query methods
- [ ] Update response schemas to include installation fields
- [ ] Add installation query parameters to API routes
- [ ] Include in structured logging
- [ ] Update health check endpoint
- [ ] Test installation filtering
- [ ] Update service README

## Testing

### Unit Tests

```python
def test_event_includes_installation_id(db_session):
    """Test that events automatically include installation_id from config."""
    config = get_config()
    service = YourService(db_session)
    
    event = service.log_event(
        event_type="test_event",
        event_data={"test": "data"},
    )
    
    assert event.installation_id == config.INSTALLATION_ID
    assert event.tenant_name == config.TENANT_NAME


def test_filter_by_installation(db_session):
    """Test filtering events by installation_id."""
    service = YourService(db_session)
    
    # Create test events with different installation IDs
    # (override config for testing)
    
    # Query with installation_id filter
    events, total = service.get_events(installation_id="test-uuid")
    
    # Verify all returned events have matching installation_id
    assert all(e.installation_id == "test-uuid" for e in events)
```

### Integration Tests

```bash
# Test installation ID is included in API responses
curl -X POST http://localhost:8000/api/v1/events \
  -H "Content-Type: application/json" \
  -d '{"event_type": "test"}' | jq '.installation_id'

# Test filtering by installation ID
curl "http://localhost:8000/api/v1/events?installation_id=550e8400-e29b-41d4-a716-446655440000"

# Test health check includes installation info
curl http://localhost:8000/health | jq '{installation_id, tenant_name}'
```

## Migration Strategy

### For Existing Installations

**Option 1: Backfill (Recommended)**
```sql
-- Set installation_id for all existing records
UPDATE your_events 
SET installation_id = '550e8400-e29b-41d4-a716-446655440000',
    tenant_name = 'Customer Name - Site'
WHERE installation_id IS NULL;
```

**Option 2: Leave Historical Data**
```sql
-- Only new records will have installation_id
-- Historical data remains with NULL values
-- This is acceptable for logs/events that are already in production
```

### For New Installations

1. Generate installation_id during setup
2. Set in all service .env files before first run
3. All data created will have installation_id from day one

## Best Practices

### DO:
✅ Generate installation_id once during setup and never change it
✅ Use the same installation_id across all services in an installation
✅ Include installation fields automatically from config
✅ Index installation_id columns for performance
✅ Include in health checks and structured logs
✅ Document in installation guides

### DON'T:
❌ Pass installation_id as API parameters (it comes from config)
❌ Use different installation_ids for services in same installation
❌ Use user UUIDs as installation_id
❌ Store installation config in database (use .env files)
❌ Allow installation_id to be changed via API
❌ Forget to set installation_id during initial setup

## Future Enhancements

### Central Licensing Service

```python
# Future: Validate installation_id with central licensing service
async def validate_installation_license(installation_id: str) -> bool:
    """Check if installation has valid license key."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://license.pplmeta.com/api/validate",
            json={"installation_id": installation_id}
        )
        return response.json()["valid"]
```

### Log Aggregation

```python
# Future: Push logs to central monitoring
async def push_logs_to_central(
    events: List[Event],
    installation_id: str,
    tenant_name: str
):
    """Push events to central log aggregation service."""
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://logs.pplmeta.com/api/ingest",
            json={
                "installation_id": installation_id,
                "tenant_name": tenant_name,
                "events": [e.dict() for e in events]
            }
        )
```

## Support and Troubleshooting

### Common Issues

**Issue**: Services show NULL installation_id
- **Solution**: Check .env file has INSTALLATION_ID set, restart service

**Issue**: Different services show different installation_ids
- **Solution**: Ensure all .env files use the same UUID

**Issue**: Installation_id not included in logs
- **Solution**: Verify service code uses self.config.INSTALLATION_ID

**Issue**: Cannot filter by installation in API
- **Solution**: Check query parameters are defined in route

### Verification Checklist

```bash
# 1. Check config is loaded
curl http://localhost:8000/health | jq '.installation_id'

# 2. Check database has values
psql -d your_db -c "SELECT DISTINCT installation_id FROM your_events LIMIT 5;"

# 3. Check API filtering works
curl "http://localhost:8000/api/v1/events?installation_id=YOUR-UUID&page_size=1"

# 4. Check logs include installation
tail -f logs/service.log | grep installation_id
```

## Reference Implementation

**Complete Example**: ppl-meta-communications service
- Location: `/ppl-meta-communications/`
- Demonstrates full implementation of this pattern
- Review for reference when implementing in other services

## Conclusion

This installation identification pattern enables:
- Clear tenant isolation in edge deployments
- Effective remote support and troubleshooting
- Future central licensing and monitoring
- Consistent architecture across all services

Implement this pattern in all services that handle user data, events, or logs to maintain consistency across the platform.
