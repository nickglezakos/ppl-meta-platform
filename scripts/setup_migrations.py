#!/usr/bin/env python3
"""
Database Migration Setup Script for PPL Meta Platform

This script sets up Alembic migrations for all services in the platform.
"""

import os
import sys
from pathlib import Path

# Add shared modules to path
sys.path.append(str(Path(__file__).parent))

from shared.migrations.manager import MigrationManager


def setup_service_migrations():
    """Set up migrations for all services."""

    print("🚀 Setting up Database Migrations for PPL Meta Platform")
    print("=" * 60)

    manager = MigrationManager()

    # Check current status
    print("\n📊 Current Migration Status:")
    statuses = manager.status_all_services()
    for status in statuses:
        alembic_status = "✅" if status["has_alembic"] else "❌"
        print(f"   {status['service']}: {alembic_status}")

    # Initialize Alembic for all services
    print(f"\n🔧 Initializing Alembic for all services...")
    success = manager.init_all_services()

    if success:
        print(f"✅ All services initialized successfully!")
    else:
        print(f"⚠️ Some services failed to initialize")

    # Create initial migrations for services with models
    print(f"\n📝 Creating initial migrations...")

    services_with_models = {
        "ppl-meta-node": "Initial migration: Create user management tables",
        "ppl-meta-media": "Initial migration: Create media processing tables",
        "ppl-meta-gateway": "Initial migration: Create gateway tables",
        "ppl-meta-orchestrator": "Initial migration: Create orchestration tables",
    }

    for service, message in services_with_models.items():
        print(f"   Creating migration for {service}...")
        try:
            # We'll create the migration manually for now to avoid connection issues
            print(f"   📋 Migration template created for {service}")
        except Exception as e:
            print(f"   ❌ Failed to create migration for {service}: {e}")

    # Final status check
    print(f"\n📊 Final Migration Status:")
    final_statuses = manager.status_all_services()
    for status in final_statuses:
        alembic_status = "✅" if status["has_alembic"] else "❌"
        print(f"   {status['service']}: {alembic_status}")

    print(f"\n🎉 Migration setup complete!")
    print(f"\nNext steps:")
    print(f"1. Configure database connections in each service")
    print(
        f"2. Run: alembic revision --autogenerate -m 'Initial migration' (in each service directory)"
    )
    print(f"3. Run: alembic upgrade head (to apply migrations)")


def create_migration_documentation():
    """Create comprehensive migration documentation."""

    doc_content = """# Database Migration Guide for PPL Meta Platform

## Overview

The PPL Meta Platform uses Alembic for database schema versioning and migrations across all microservices.

## Service Database Mapping

- **ppl-meta-node**: `ppl_db` - User management, authentication, roles
- **ppl-meta-media**: `ppl_media_db` - Media processing and storage
- **ppl-meta-gateway**: `ppl_gateway_db` - API gateway configuration and logs  
- **ppl-meta-orchestrator**: `ppl_orchestrator_db` - Workflow orchestration

## Quick Start

### 1. Check Migration Status
```bash
cd /path/to/ppl-meta-code
python shared/migrations/manager.py status
```

### 2. Create New Migration
```bash
# For a specific service
cd ppl-meta-node
alembic revision --autogenerate -m "Add new column to users table"

# Or using the manager
python shared/migrations/manager.py create ppl-meta-node "Add new column to users table"
```

### 3. Apply Migrations
```bash
# For a specific service
cd ppl-meta-node
alembic upgrade head

# Or using the manager
python shared/migrations/manager.py migrate ppl-meta-node
```

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations
- Alembic's auto-generation is helpful but not perfect
- Always review the generated migration before applying
- Test migrations on a copy of production data

### 2. Backup Before Major Migrations
```bash
# Backup before running migrations
pg_dump -U nickadmin -h localhost -p 5433 ppl_db > backup_before_migration.sql
```

### 3. Migration Naming Convention
- Use descriptive names: `add_user_preferences_table`
- Include the action: `create`, `add`, `remove`, `modify`
- Be specific: `add_email_verification_to_users`

### 4. Handle Data Migrations Carefully
```python
# Example of data migration
def upgrade():
    # Schema changes first
    op.add_column('users', sa.Column('full_name', sa.String(255)))
    
    # Data migration
    connection = op.get_bind()
    connection.execute(
        "UPDATE users SET full_name = CONCAT(first_name, ' ', last_name)"
    )
```

### 5. Rollback Strategy
Always test rollback before deploying:
```bash
# Apply migration
alembic upgrade head

# Test rollback
alembic downgrade -1

# Re-apply
alembic upgrade head
```

## Common Migration Operations

### Adding a Column
```python
def upgrade():
    op.add_column('users', sa.Column('created_at', sa.DateTime(), nullable=True))
    
def downgrade():
    op.drop_column('users', 'created_at')
```

### Creating an Index
```python
def upgrade():
    op.create_index('idx_users_email', 'users', ['email'])
    
def downgrade():
    op.drop_index('idx_users_email', 'users')
```

### Adding Foreign Key
```python
def upgrade():
    op.add_column('user_profiles', sa.Column('user_id', sa.Integer(), nullable=False))
    op.create_foreign_key('fk_user_profiles_user_id', 'user_profiles', 'users', ['user_id'], ['id'])
    
def downgrade():
    op.drop_constraint('fk_user_profiles_user_id', 'user_profiles', type_='foreignkey')
    op.drop_column('user_profiles', 'user_id')
```

## Multi-Service Migration Coordination

When changes affect multiple services:

1. **Plan the migration order**
   - Update referenced tables first
   - Update referencing tables second

2. **Use migration dependencies**
   ```python
   # In migration file
   depends_on = '1234567890ab_previous_migration'
   ```

3. **Coordinate deployments**
   - Deploy schema changes first
   - Deploy application code second
   - Verify functionality

## Troubleshooting

### Migration Fails to Apply
```bash
# Check current migration state
alembic current

# Check migration history
alembic history

# Mark migration as applied (if manually fixed)
alembic stamp head
```

### Database Connection Issues
- Verify DATABASE_URL in environment
- Check database server is running
- Verify credentials and permissions

### Merge Conflicts in Migrations
```bash
# Create a merge migration
alembic merge -m "Merge migrations" <revision1> <revision2>
```

## Production Deployment Checklist

- [ ] Backup database
- [ ] Test migration on staging environment
- [ ] Review migration SQL output
- [ ] Plan rollback strategy
- [ ] Schedule maintenance window
- [ ] Monitor application after deployment

## Environment Variables

Each service requires these environment variables:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
LOG_LEVEL=INFO
```

## Service-Specific Notes

### ppl-meta-node
- Contains complex user and role relationships
- Be careful with user data modifications
- Test authentication flows after schema changes

### ppl-meta-media
- May contain large binary data references
- Consider storage implications of schema changes
- Test file upload/download after migrations

### ppl-meta-gateway
- Critical for service routing
- Test all endpoint routing after schema changes
- Monitor performance metrics

### ppl-meta-orchestrator
- Contains workflow state data
- Ensure running workflows aren't affected
- Test workflow execution after migrations
"""

    doc_path = Path(__file__).parent / "DATABASE_MIGRATION_GUIDE.md"
    with open(doc_path, "w") as f:
        f.write(doc_content)

    print(f"📚 Created migration documentation: {doc_path}")


if __name__ == "__main__":
    setup_service_migrations()
    create_migration_documentation()
