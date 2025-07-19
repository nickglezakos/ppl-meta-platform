# PPL Meta Platform - Standardized Logging Guide

## Overview

The PPL Meta Platform now uses a standardized logging system across all microservices to ensure consistent log formatting, structured data, and easy log aggregation for monitoring and debugging.

## Features

- **Consistent Formatting**: All services use the same log format structure
- **Structured Logging**: JSON format support for log aggregation systems
- **Configurable Log Levels**: Environment-based log level configuration
- **Service Context**: Automatic service, version, and environment tagging
- **Helper Functions**: Standardized logging for common operations
- **File and Console Output**: Support for both file logging and console output

## Quick Start

### 1. Import the Shared Logging Module

```python
import os
import sys

# Add path to shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from shared.logging import setup_logging
```

### 2. Initialize Logging in Your Service

```python
# In your main.py or application startup
logger = setup_logging(
    service_name="your-service-name",
    log_level=config.LOG_LEVEL.upper(),
    log_format=config.LOG_FORMAT.lower(),
    log_file="/app/logs/your-service.log"  # Optional
)
```

### 3. Use the Logger

```python
# Basic logging
logger.info("Service started successfully")
logger.error("Failed to connect to database")

# Structured logging with context
logger.info("User login", user_id="12345", ip_address="192.168.1.1")
logger.warning("High memory usage", usage_percent=85, threshold=80)
```

## Configuration

### Environment Variables

All services should support these logging environment variables:

```bash
# Required
LOG_LEVEL=info          # debug, info, warning, error, critical
LOG_FORMAT=console      # console, json

# Recommended for production
LOG_LEVEL=info
LOG_FORMAT=json
```

### Log Levels

| Level | When to Use |
|-------|-------------|
| `DEBUG` | Development debugging, verbose output |
| `INFO` | General information, service state changes |
| `WARNING` | Potentially harmful situations, degraded performance |
| `ERROR` | Error conditions that don't stop the application |
| `CRITICAL` | Serious errors that may cause the application to abort |

### Log Formats

#### Console Format (Development)
```
[INFO    ] 2025-07-07 17:41:34 ppl-meta-gateway: User login attempt [gateway] user_id=12345 ip=192.168.1.1
```

#### JSON Format (Production)
```json
{
  "timestamp": "2025-07-07T17:41:34.736612Z",
  "level": "INFO",
  "logger": "ppl-meta-gateway",
  "message": "User login attempt",
  "service": "ppl-meta-gateway",
  "version": "1.0.0",
  "environment": "production",
  "user_id": "12345",
  "ip": "192.168.1.1"
}
```

## Helper Functions

The shared logging module provides standardized helper functions for common logging scenarios:

### HTTP Request/Response Logging

```python
from shared.logging import log_request, log_response

# Log incoming HTTP request
log_request(logger, request_id="req-123", method="GET", path="/api/users", user_id="12345")

# Log outgoing HTTP response  
log_response(logger, request_id="req-123", status_code=200, duration_ms=45.2)
```

### Database Operation Logging

```python
from shared.logging import log_database_operation

log_database_operation(
    logger, 
    operation="SELECT", 
    table="users", 
    duration_ms=12.5, 
    affected_rows=5
)
```

### Error Logging

```python
from shared.logging import log_error

try:
    # Some operation
    pass
except Exception as e:
    log_error(logger, e, {"operation": "user_creation", "user_id": "12345"})
```

### External API Call Logging

```python
from shared.logging import log_external_api_call

log_external_api_call(
    logger,
    service="auth-service",
    endpoint="/validate",
    method="POST", 
    status_code=200,
    duration_ms=150.0
)
```

## Service Integration

### Gateway Service (ppl-meta-gateway)

**Configuration:**
```python
# src/config.py
log_level: str = "INFO"
log_format: str = "json"  # Production ready
```

**Usage:**
```python
# src/main.py
from shared.logging import setup_logging

logger = setup_logging(
    service_name="ppl-meta-gateway",
    log_level=settings.log_level.upper(),
    log_format=settings.log_format.lower()
)
```

### Node Service (ppl-meta-node)

**Configuration:**
```python
# src/config.py
LOG_LEVEL: str = "info"
LOG_FORMAT: str = "console"
```

**Usage:**
```python
# src/main.py
logger = setup_logging(
    service_name="ppl-meta-node",
    log_level=settings.LOG_LEVEL.upper(),
    log_format=settings.LOG_FORMAT.lower()
)
```

### Media Service (ppl-meta-media)

**Configuration:**
```python
# src/config.py  
LOG_LEVEL: str = Field(default="info", env="LOG_LEVEL")
LOG_FORMAT: str = Field(default="console", env="LOG_FORMAT")
```

**Usage:**
```python
# src/main.py
logger = setup_logging(
    service_name="ppl-meta-media",
    log_level=config.LOG_LEVEL.upper(),
    log_format=config.LOG_FORMAT.lower()
)
```

### Orchestrator Service (ppl-meta-orchestrator)

**Configuration:**
```python
# src/config.py
LOG_LEVEL: str = Field(default="info", env="LOG_LEVEL")
LOG_FORMAT: str = Field(default="console", env="LOG_FORMAT")
```

**Usage:**
```python
# src/main.py
logger = setup_logging(
    service_name="ppl-meta-orchestrator", 
    log_level=settings.LOG_LEVEL.upper(),
    log_format=settings.LOG_FORMAT.lower()
)
```

## Production Deployment

### Recommended Production Settings

```bash
# .env production configuration
LOG_LEVEL=info
LOG_FORMAT=json
```

### Docker Configuration

Ensure log directories exist in your Dockerfiles:

```dockerfile
# Create log directory
RUN mkdir -p /app/logs

# Set log file permissions
RUN chown -R appuser:appuser /app/logs
```

### Log File Rotation

For production deployments, implement log rotation:

```yaml
# docker-compose.yml
services:
  ppl-meta-gateway:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Log Aggregation

### ELK Stack Integration

The JSON format is designed to work seamlessly with Elasticsearch, Logstash, and Kibana:

```json
{
  "timestamp": "2025-07-07T17:41:34.736612Z",
  "level": "INFO", 
  "service": "ppl-meta-gateway",
  "environment": "production",
  "message": "User login attempt",
  "user_id": "12345",
  "request_id": "req-123"
}
```

### Grafana Loki Integration

JSON logs can be easily ingested by Grafana Loki for visualization:

```yaml
# promtail configuration
- job_name: ppl-meta-services
  static_configs:
  - targets:
      - localhost
    labels:
      job: ppl-meta
      __path__: /app/logs/*.log
```

## Testing

Run the logging test suite to validate configuration:

```bash
python test_standardized_logging.py
```

This will test:
- Console and JSON formatting
- Log level filtering  
- Service-specific configurations
- Helper function functionality

## Migration from Old Logging

### Before (Inconsistent)

```python
# Different formats across services
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Inconsistent usage
logger.info("User login")  # No context
logger.error(f"Database error: {error}")  # String formatting
```

### After (Standardized)

```python
# Consistent setup
from shared.logging import setup_logging, log_error

logger = setup_logging(
    service_name="ppl-meta-service",
    log_level="INFO",
    log_format="json"
)

# Structured usage  
logger.info("User login", user_id="12345", session_id="abc123")
log_error(logger, error, {"operation": "database_query"})
```

## Benefits

1. **Consistency**: All services log in the same format
2. **Structured Data**: Easy to query and analyze logs
3. **Service Context**: Automatic service/version/environment tagging
4. **Environment Flexibility**: Easy to switch between console and JSON formats
5. **Log Aggregation Ready**: JSON format works with ELK, Loki, etc.
6. **Helper Functions**: Standardized logging for common operations
7. **Performance**: Efficient structured logging with minimal overhead

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the shared module path is correctly added
2. **Permission Errors**: Verify log directory permissions in Docker containers
3. **Log Level Not Working**: Check environment variable case sensitivity
4. **JSON Format Issues**: Validate JSON output with the test script

### Debug Logging

Enable debug logging to troubleshoot issues:

```python
logger = setup_logging(
    service_name="debug-service",
    log_level="DEBUG",
    log_format="console"
)
```

## Future Enhancements

- [ ] Automatic log rotation configuration
- [ ] Metrics integration (Prometheus)
- [ ] Distributed tracing correlation IDs
- [ ] Log sampling for high-volume services
- [ ] Audit logging for security events
