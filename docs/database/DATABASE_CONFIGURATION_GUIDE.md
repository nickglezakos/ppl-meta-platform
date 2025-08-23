# Database Configuration Standardization Guide

## Overview

This document describes the standardized database configuration for the PPL Meta Platform, implemented as part of resolving **ISSUE-006: Database Connection String Variations**.

## Standardized Configuration

### Connection String Format

All services now use a consistent PostgreSQL connection string format:

```
postgresql://username:password@host:port/database_name
```

### Standard Credentials

- **Username**: `nickadmin`
- **Password**: `Kodikos@23` (URL encoded as `Kodikos%4023`)
- **Host**: `localhost` (development) or `postgres` (Docker)
- **Port**: `5433` (external Docker port) or `5432` (internal Docker port)

### Service-Specific Database Names

| Service | Database Name | Purpose |
|---------|---------------|---------|
| ppl-meta-node | `ppl_db` | User management and authentication |
| ppl-meta-media | `ppl_media_db` | Media processing and storage |
| ppl-meta-orchestrator | `ppl_orchestrator_db` | Service coordination and workflows |
| ppl-meta-gateway | `ppl_gateway_db` | API gateway configuration (optional) |
| ppl-meta-code | `ppl_platform` | Shared platform data |

## Environment Configuration

### Development (Local)

For local development, use port `5433` to connect to the external Docker PostgreSQL port:

```bash
# Node Service
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@localhost:5433/ppl_db

# Media Service  
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@localhost:5433/ppl_media_db

# Orchestrator Service
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@localhost:5433/ppl_orchestrator_db

# Gateway Service (optional)
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@localhost:5433/ppl_gateway_db
```

### Docker Compose

For Docker deployments, use the internal service name `postgres` and port `5432`:

```bash
# Node Service
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@postgres:5432/ppl_db

# Media Service
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@postgres:5432/ppl_media_db

# Orchestrator Service  
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@postgres:5432/ppl_orchestrator_db

# Gateway Service (optional)
DATABASE_URL=postgresql://nickadmin:Kodikos%4023@postgres:5432/ppl_gateway_db
```

## Database Components Configuration

Each service also supports individual database component configuration for flexibility:

```bash
DB_HOST=localhost
DB_PORT=5433
DB_NAME=service_specific_db
DB_USER=nickadmin
DB_PASSWORD=Kodikos@23
```

## Validation and Connection Helpers

All service configurations now include database validation helpers:

### Validation Method

```python
def validate_database_url(self) -> bool:
    """Validate the database connection string format and components."""
    # Validates scheme, username, password, hostname, and database name
```

### Database Info Method

```python
def get_database_info(self) -> dict:
    """Get database connection information for debugging."""
    # Returns masked connection details for safe logging
```

### Connection URL Method

```python
def get_database_url(self) -> str:
    """Get database URL from DATABASE_URL or construct from components."""
    # Returns properly formatted PostgreSQL URL
```

## Database Initialization

The platform automatically creates all service-specific databases during PostgreSQL container startup:

```sql
-- Created databases
CREATE DATABASE ppl_db;                 -- Node service
CREATE DATABASE ppl_media_db;           -- Media service  
CREATE DATABASE ppl_orchestrator_db;    -- Orchestrator service
CREATE DATABASE ppl_gateway_db;         -- Gateway service (optional)

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

## Migration from Previous Configuration

### Issues Resolved

1. **Inconsistent Connection Strings**: All services now use identical format
2. **Port Mismatches**: Standardized on 5433 (external) and 5432 (internal)
3. **URL Encoding**: Password special characters properly encoded
4. **Database Names**: Service-specific databases prevent conflicts
5. **Validation**: Added comprehensive connection validation

### Breaking Changes

- Database URLs in `.env.example` files updated to use port `5433`
- Password URL encoding now consistent across all services
- Database names now service-specific (not shared `ppl_db`)

## Testing Database Connections

Use the provided test script to validate all database connections:

```bash
# Test all service database connections
./test_database_connections.py
```

Or test individual services:

```bash
# Test node service
cd ppl-meta-node
python -c "from src.config import settings; print(settings.validate_database_url())"

# Test media service
cd ppl-meta-media  
python -c "from src.config import config; print(config.validate_database_url())"
```

## Troubleshooting

### Common Issues

1. **Connection Refused**: Check that PostgreSQL is running on port 5433
2. **Authentication Failed**: Verify credentials match `nickadmin:Kodikos@23`
3. **Database Not Found**: Ensure database initialization script ran successfully
4. **URL Encoding**: Use `%40` for `@` and `%23` for `#` in passwords

### Debug Commands

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Connect to database manually
psql -h localhost -p 5433 -U nickadmin -d ppl_db

# Check database exists
psql -h localhost -p 5433 -U nickadmin -c "\l"

# Test connection from service
cd ppl-meta-node
python src/database.py
```

## Configuration Files Updated

### Environment Templates
- `ppl-meta-node/.env.example`
- `ppl-meta-media/.env.example`
- `ppl-meta-orchestrator/.env.example`
- `ppl-meta-gateway/.env.example`
- `ppl-meta-code/.env.example`

### Service Configurations
- `ppl-meta-node/src/config.py`
- `ppl-meta-media/src/config.py`
- `ppl-meta-orchestrator/src/config.py`
- `ppl-meta-gateway/src/config.py`

### Database Files
- `ppl-meta-node/src/database.py`
- `ppl-meta-node/database/init/01-init-multiple-databases.sh`

### Docker Compose
- `docker-compose.minimal.yml`
- `ppl-meta-node/docker-compose.infrastructure.yml`

## Best Practices

1. **Always use environment variables** for database credentials
2. **Validate connections** before application startup
3. **Use service-specific databases** to prevent data conflicts
4. **URL encode special characters** in connection strings
5. **Test connections** after configuration changes
6. **Log masked URLs only** to prevent credential exposure

## Security Considerations

- Database credentials are consistent across all services for development
- In production, use unique credentials per service
- Consider using secrets management for credential storage
- Database connections are validated before usage
- Connection details are logged with masked passwords

---

**Document Version**: 1.0  
**Last Updated**: January 2, 2025  
**Related Issue**: ISSUE-006 - Database Connection String Variations  
**Status**: ✅ Resolved
