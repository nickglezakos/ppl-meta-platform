# Metrics Implementation Guide - PPL Meta Platform

This guide documents the comprehensive Prometheus metrics implementation across all PPL Meta Platform services, resolving **ISSUE-012: Missing Service Metrics**.

## Overview

The PPL Meta Platform now includes standardized metrics collection across all microservices:
- **ppl-meta-gateway** (Port 8080)
- **ppl-meta-node** (Port 8001) 
- **ppl-meta-media** (Port 8000)
- **ppl-meta-orchestrator** (Port 8002)

## Architecture

### Shared Metrics Module

Location: `shared/metrics/__init__.py`

The shared metrics module provides:
- **MetricsCollector**: Centralized metrics collection and management
- **PrometheusMiddleware**: Automatic FastAPI request/response metrics
- **Standardized Metrics**: Common metrics across all services
- **Custom Registry**: Isolated metrics per service instance

### Metrics Categories

#### 1. HTTP Request Metrics
- `http_requests_total` - Total HTTP requests by method, endpoint, status code
- `http_request_duration_seconds` - Request processing time
- `http_request_size_bytes` - Request payload size
- `http_response_size_bytes` - Response payload size
- `http_active_connections` - Currently active connections

#### 2. System Metrics
- `system_cpu_usage_percent` - Current CPU usage
- `system_memory_usage_bytes` - Memory usage in bytes
- `system_memory_usage_percent` - Memory usage percentage
- `system_disk_usage_bytes` - Disk usage in bytes
- `system_disk_usage_percent` - Disk usage percentage

#### 3. Database Metrics
- `database_connections_active` - Active database connections
- `database_query_duration_seconds` - Query execution time
- `database_queries_total` - Total database queries by type and status

#### 4. Error Metrics
- `errors_total` - Total errors by service, type, and endpoint

#### 5. Business Metrics
- `business_operations_total` - Service-specific business operations
- `business_operation_duration_seconds` - Business operation duration

#### 6. Service Information
- `service_info` - Static service metadata (name, version, Python version)

## Implementation Details

### Automatic Metrics Collection

The `PrometheusMiddleware` automatically collects metrics for all HTTP requests:

```python
from shared.metrics import init_metrics, PrometheusMiddleware, create_metrics_endpoint

# Initialize metrics
metrics_collector = init_metrics(
    service_name="my-service",
    service_version="1.0.0"
)

# Add middleware
app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

# Add metrics endpoint
metrics_router = create_metrics_endpoint()
app.include_router(metrics_router, tags=["Metrics"])
```

### System Metrics Collection

System metrics are collected automatically in a background thread every 30 seconds:
- CPU usage via `psutil.cpu_percent()`
- Memory usage via `psutil.virtual_memory()`
- Disk usage via `psutil.disk_usage('/')`

### Path Normalization

To prevent high cardinality metrics, the middleware normalizes endpoint paths:
- Numeric IDs: `/users/123` → `/users/{id}`
- UUIDs: `/users/550e8400-...` → `/users/{uuid}`

## Service Integration

### Gateway Service (Port 8080)

```python
# ppl-meta-gateway/src/main.py
from shared.metrics import init_metrics, PrometheusMiddleware, create_metrics_endpoint

# In create_app():
metrics_collector = init_metrics(
    service_name=settings.service_name,
    service_version=settings.service_version
)
app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

metrics_router = create_metrics_endpoint()
app.include_router(metrics_router, tags=["Metrics"])
```

### Node Service (Port 8001)

```python
# ppl-meta-node/src/main.py
from shared.metrics import init_metrics, PrometheusMiddleware, create_metrics_endpoint

metrics_collector = init_metrics(
    service_name=settings.APP_NAME,
    service_version=settings.APP_VERSION
)
app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

metrics_router = create_metrics_endpoint()
app.include_router(metrics_router, tags=["Metrics"])
```

### Media Service (Port 8000)

```python
# ppl-meta-media/src/main.py
from shared.metrics import init_metrics, PrometheusMiddleware, create_metrics_endpoint

metrics_collector = init_metrics(
    service_name="ppl-meta-media",
    service_version="1.0.0"
)
app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

metrics_router = create_metrics_endpoint()
app.include_router(metrics_router, tags=["Metrics"])
```

### Orchestrator Service (Port 8002)

```python
# ppl-meta-orchestrator/src/main.py
from shared.metrics import init_metrics, PrometheusMiddleware, create_metrics_endpoint

metrics_collector = init_metrics(
    service_name=settings.APP_NAME,
    service_version=settings.APP_VERSION
)
app.add_middleware(PrometheusMiddleware, metrics_collector=metrics_collector)

metrics_router = create_metrics_endpoint()
app.include_router(metrics_router, tags=["Metrics"])
```

## Metrics Endpoints

Each service exposes metrics at:
- **Gateway**: `http://localhost:8080/metrics`
- **Node**: `http://localhost:8001/metrics`
- **Media**: `http://localhost:8000/metrics`
- **Orchestrator**: `http://localhost:8002/metrics`

## Dependencies Added

All services now include:
```
prometheus-client>=0.19.0
psutil>=5.9.0
```

## Custom Business Metrics

Services can record custom business metrics:

```python
from shared.metrics import get_metrics_collector

collector = get_metrics_collector()

# Record business operation
start_time = time.time()
# ... business logic ...
duration = time.time() - start_time

collector.record_business_operation(
    operation_type="user_registration",
    duration=duration,
    status="success"
)

# Record database operation
collector.record_db_query(
    query_type="user_lookup",
    duration=0.05,
    status="success"
)

# Record error
collector.record_error(
    error_type="ValidationError",
    endpoint="/api/v1/users"
)
```

## Testing

Use the provided test script to validate metrics:

```bash
python test_metrics_implementation.py
```

The script tests:
1. Service health endpoints
2. Metrics endpoint availability
3. Required metrics presence
4. Load generation and metrics collection

## Monitoring Integration

### Prometheus Configuration

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'ppl-meta-gateway'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'ppl-meta-node'
    static_configs:
      - targets: ['localhost:8001']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'ppl-meta-media'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'ppl-meta-orchestrator'
    static_configs:
      - targets: ['localhost:8002']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Grafana Dashboards

Key metrics to monitor:
- Request rate: `rate(http_requests_total[5m])`
- Error rate: `rate(http_requests_total{status_code=~"5.."}[5m])`
- Response time: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`
- CPU usage: `system_cpu_usage_percent`
- Memory usage: `system_memory_usage_percent`

## Benefits Achieved

✅ **Request/Response Tracking**: All HTTP requests automatically tracked  
✅ **Error Monitoring**: Comprehensive error tracking by type and endpoint  
✅ **Resource Utilization**: Real-time system metrics (CPU, memory, disk)  
✅ **Custom Business Metrics**: Framework for service-specific metrics  
✅ **Standardized Format**: Consistent metrics across all services  
✅ **Production Ready**: Path normalization prevents cardinality explosion  
✅ **Zero Configuration**: Automatic setup with shared module import  

## Issue Resolution

This implementation fully resolves **ISSUE-012: Missing Service Metrics** by providing:

1. ✅ **Request/response times** - Tracked via `http_request_duration_seconds`
2. ✅ **Error rates** - Tracked via `errors_total` and status code metrics
3. ✅ **Resource utilization** - CPU, memory, and disk metrics
4. ✅ **Custom business metrics** - Framework for service-specific operations

The metrics system is now production-ready and provides comprehensive observability across the entire PPL Meta Platform ecosystem.
