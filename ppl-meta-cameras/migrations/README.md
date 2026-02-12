# Database Migrations for PPL Meta Cameras Service

This directory contains SQL migration scripts for the Cameras service database.

## Running Migrations

### Option 1: Using psql (Recommended)

```bash
# Run all migrations in order
psql -h localhost -U your_user -d ppl_meta_cameras -f migrations/001_add_hardware_identifier.sql
psql -h localhost -U your_user -d ppl_meta_cameras -f migrations/002_create_pending_settings_table.sql
```

### Option 2: Using Python script

```bash
cd ppl-meta-cameras
python -c "
from src.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Run migration 001
    with open('migrations/001_add_hardware_identifier.sql', 'r') as f:
        conn.execute(text(f.read()))
    conn.commit()
    
    # Run migration 002
    with open('migrations/002_create_pending_settings_table.sql', 'r') as f:
        conn.execute(text(f.read()))
    conn.commit()
    
print('✅ Migrations completed!')
"
```

### Option 3: Using Docker (if running in container)

```bash
docker exec -i ppl-meta-cameras-db psql -U postgres -d ppl_meta_cameras < migrations/001_add_hardware_identifier.sql
docker exec -i ppl-meta-cameras-db psql -U postgres -d ppl_meta_cameras < migrations/002_create_pending_settings_table.sql
```

## Migration Files

| File | Description | Status |
|------|-------------|--------|
| 001_add_hardware_identifier.sql | Adds hardware_identifier column to cameras table | ⏳ Pending |
| 002_create_pending_settings_table.sql | Creates pending_camera_settings table | ⏳ Pending |

## Rollback

### Rollback Migration 001
```sql
ALTER TABLE cameras DROP COLUMN IF EXISTS hardware_identifier;
DROP INDEX IF EXISTS idx_cameras_hardware_identifier;
```

### Rollback Migration 002
```sql
DROP TABLE IF EXISTS pending_camera_settings CASCADE;
```

## Future: Alembic Setup

Consider setting up Alembic for automated migration management:

```bash
pip install alembic
alembic init alembic
# Configure alembic.ini and env.py
alembic revision --autogenerate -m "migration_name"
alembic upgrade head
```
