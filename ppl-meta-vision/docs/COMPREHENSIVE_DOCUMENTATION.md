# PPL Meta Vision Service - Complete Documentation Package

## Table of Contents

1. [API Documentation](#api-documentation)
2. [Deployment Guide](#deployment-guide)
3. [Troubleshooting Guide](#troubleshooting-guide)
4. [Operational Runbook](#operational-runbook)
5. [Developer Documentation](#developer-documentation)
6. [Performance & Monitoring](#performance--monitoring)

---

## API Documentation

### Overview

The PPL Meta Vision Service provides session-based face detection capabilities through a RESTful API. This service implements Face Detection Workflow 4 with comprehensive session management, analytics, and traceability features.

**Base URL:** `http://localhost:8003` (local development)
**Version:** 1.0.0

### Authentication

Currently, the service operates without authentication in development mode. For production deployment, implement JWT token authentication.

### Core Endpoints

#### Session Management

##### Create Session
```http
POST /api/v1/sessions
Content-Type: application/json

{
  "media_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "camera_device_uuid": "550e8400-e29b-41d4-a716-446655440001",
  "session_type": "streaming",
  "metadata": {
    "detection_method": "two_stage",
    "quality_threshold": 0.8
  }
}
```

**Response:**
```http
HTTP/1.1 201 Created
Content-Type: application/json

{
  "session_uuid": "550e8400-e29b-41d4-a716-446655440002",
  "status": "active",
  "started_at": "2024-01-15T10:30:00Z",
  "total_faces_detected": 0,
  "processing_status": "active"
}
```

##### Get Session Status
```http
GET /api/v1/sessions/{session_uuid}
```

**Response:**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "session_uuid": "550e8400-e29b-41d4-a716-446655440002",
  "media_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "camera_device_uuid": "550e8400-e29b-41d4-a716-446655440001",
  "session_type": "streaming",
  "started_at": "2024-01-15T10:30:00Z",
  "ended_at": null,
  "processing_status": "active",
  "total_faces_detected": 15,
  "metadata": {...}
}
```

##### Complete Session
```http
POST /api/v1/sessions/{session_uuid}/complete
Content-Type: application/json

{
  "metadata": {
    "completion_reason": "normal",
    "total_processing_time": 120.5,
    "frames_processed": 3600
  }
}
```

#### Face Detection

##### Store Face Detection
```http
POST /api/v1/detections
Content-Type: application/json

{
  "session_uuid": "550e8400-e29b-41d4-a716-446655440002",
  "frame_number": 100,
  "timestamp": 25.5,
  "bbox": [100, 150, 200, 250],
  "confidence": 0.85,
  "method": "two_stage"
}
```

##### Get Session Detections
```http
GET /api/v1/sessions/{session_uuid}/detections?limit=50&offset=0
```

#### Analytics

##### Cross-Session Analytics
```http
GET /api/v1/analytics/cross-session?start_date=2024-01-01&end_date=2024-01-15
```

##### Device Traceability
```http
GET /api/v1/analytics/device/{camera_device_uuid}?start_date=2024-01-01&end_date=2024-01-15
```

##### Media Timeline
```http
GET /api/v1/analytics/media/{media_uuid}
```

### Error Responses

```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": "INVALID_SESSION_TYPE",
  "message": "Session type must be one of: streaming, batch, realtime",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

Common error codes:
- `SESSION_NOT_FOUND`: Session UUID not found
- `INVALID_SESSION_TYPE`: Invalid session type provided
- `INVALID_MEDIA_UUID`: Invalid media UUID format
- `DATABASE_ERROR`: Database operation failed

---

## Deployment Guide

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Docker (optional)
- Nginx (for production)

### Local Development Setup

1. **Clone Repository**
   ```bash
   git clone <repository-url>
   cd ppl-meta-vision
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Database**
   ```bash
   # Create PostgreSQL database
   createdb ppl_meta_vision
   
   # Set environment variables
   export DATABASE_URL="postgresql://user:password@localhost:5432/ppl_meta_vision"
   export VISION_SERVICE_PORT=8003
   ```

5. **Initialize Database**
   ```bash
   python src/database.py --init
   ```

6. **Start Service**
   ```bash
   cd src
   uvicorn main:app --host 0.0.0.0 --port 8003 --reload
   ```

### Production Deployment

#### Using Docker

1. **Build Image**
   ```bash
   docker build -t ppl-meta-vision:latest .
   ```

2. **Run Container**
   ```bash
   docker run -d \
     --name ppl-meta-vision \
     -p 8003:8003 \
     -e DATABASE_URL="postgresql://user:password@db:5432/ppl_meta_vision" \
     -e ENVIRONMENT="production" \
     ppl-meta-vision:latest
   ```

#### Using Docker Compose

```yaml
version: '3.8'
services:
  vision-service:
    build: .
    ports:
      - "8003:8003"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/ppl_meta_vision
      - ENVIRONMENT=production
    depends_on:
      - db
    
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=ppl_meta_vision
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

#### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `VISION_SERVICE_PORT` | Service port | 8003 |
| `ENVIRONMENT` | Environment (dev/prod) | development |
| `LOG_LEVEL` | Logging level | INFO |
| `CACHE_TTL_SECONDS` | Cache TTL | 300 |
| `MAX_CONNECTIONS` | DB pool size | 25 |

### Production Configuration

1. **Nginx Configuration**
   ```nginx
   upstream vision_backend {
       server 127.0.0.1:8003;
   }
   
   server {
       listen 80;
       server_name vision.yourdomain.com;
       
       location /api/v1/ {
           proxy_pass http://vision_backend;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       }
       
       location /health {
           proxy_pass http://vision_backend;
       }
   }
   ```

2. **Systemd Service**
   ```ini
   [Unit]
   Description=PPL Meta Vision Service
   After=network.target postgresql.service
   
   [Service]
   Type=exec
   User=vision
   Group=vision
   WorkingDirectory=/opt/ppl-meta-vision
   Environment=DATABASE_URL=postgresql://user:pass@localhost/ppl_meta_vision
   ExecStart=/opt/ppl-meta-vision/venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8003
   Restart=always
   RestartSec=5
   
   [Install]
   WantedBy=multi-user.target
   ```

---

## Troubleshooting Guide

### Common Issues

#### Service Won't Start

**Problem:** Service fails to start with database connection error

**Solution:**
1. Check database is running: `pg_isready -h localhost -p 5432`
2. Verify connection string: `psql $DATABASE_URL`
3. Check firewall rules for port 5432
4. Verify database exists: `psql -l | grep ppl_meta_vision`

**Problem:** Port already in use

**Solution:**
```bash
# Find process using port
lsof -i :8003

# Kill process
kill -9 <PID>

# Or use different port
uvicorn src.main:app --port 8004
```

#### Database Issues

**Problem:** Migration errors

**Solution:**
```bash
# Reset database
dropdb ppl_meta_vision
createdb ppl_meta_vision
python src/database.py --init
```

**Problem:** Connection pool exhausted

**Solution:**
1. Check for connection leaks in logs
2. Increase pool size in configuration
3. Implement connection timeout
4. Monitor active connections: `SELECT count(*) FROM pg_stat_activity;`

#### Performance Issues

**Problem:** Slow API responses

**Solution:**
1. Check database query performance:
   ```sql
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC;
   ```

2. Enable query logging:
   ```bash
   export LOG_LEVEL=DEBUG
   ```

3. Check system resources:
   ```bash
   htop
   df -h
   free -m
   ```

#### Memory Leaks

**Problem:** Increasing memory usage

**Solution:**
1. Monitor memory usage:
   ```python
   import psutil
   process = psutil.Process()
   print(f"Memory: {process.memory_info().rss / 1024 / 1024:.2f} MB")
   ```

2. Enable garbage collection logging
3. Review session cleanup logic
4. Check for circular references

### Monitoring Commands

```bash
# Check service status
systemctl status ppl-meta-vision

# View logs
journalctl -u ppl-meta-vision -f

# Check API health
curl http://localhost:8003/health

# Database connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='ppl_meta_vision';"

# Disk usage
du -sh /var/lib/postgresql/

# CPU and memory
top -p $(pgrep -f "uvicorn.*main")
```

---

## Operational Runbook

### Daily Operations

#### Health Checks (Every 4 hours)
```bash
#!/bin/bash
# health_check.sh

echo "=== PPL Meta Vision Health Check ==="
echo "Timestamp: $(date)"

# API Health
echo "1. API Health Check:"
response=$(curl -s http://localhost:8003/health)
if [[ $? -eq 0 ]]; then
    echo "   ✅ API responding"
    echo "   Response: $response"
else
    echo "   ❌ API not responding"
    exit 1
fi

# Database Health
echo "2. Database Health Check:"
db_check=$(psql $DATABASE_URL -c "SELECT 1;" 2>/dev/null)
if [[ $? -eq 0 ]]; then
    echo "   ✅ Database connected"
else
    echo "   ❌ Database connection failed"
    exit 1
fi

# Service Status
echo "3. Service Status:"
if systemctl is-active --quiet ppl-meta-vision; then
    echo "   ✅ Service running"
else
    echo "   ❌ Service not running"
    exit 1
fi

echo "=== Health Check Complete ==="
```

#### Performance Monitoring (Daily)
```bash
#!/bin/bash
# performance_check.sh

echo "=== Performance Report $(date) ==="

# API Response Times
echo "1. API Performance:"
for endpoint in "/health" "/api/v1/sessions" "/api/v1/analytics/summary"; do
    time=$(curl -w "%{time_total}" -s -o /dev/null http://localhost:8003$endpoint)
    echo "   $endpoint: ${time}s"
done

# Database Performance
echo "2. Database Performance:"
psql $DATABASE_URL -c "
SELECT 
    query_type,
    round(avg(duration_ms), 2) as avg_ms,
    count(*) as count
FROM (
    SELECT 
        CASE 
            WHEN query LIKE 'SELECT%' THEN 'SELECT'
            WHEN query LIKE 'INSERT%' THEN 'INSERT'
            WHEN query LIKE 'UPDATE%' THEN 'UPDATE'
            ELSE 'OTHER'
        END as query_type,
        total_time / calls as duration_ms
    FROM pg_stat_statements
    WHERE calls > 0
) subq
GROUP BY query_type;
"

# Memory Usage
echo "3. Memory Usage:"
free -h

# Disk Usage
echo "4. Disk Usage:"
df -h | grep -E "(Filesystem|/var|/opt)"

echo "=== Performance Report Complete ==="
```

### Weekly Operations

#### Log Rotation and Cleanup
```bash
#!/bin/bash
# weekly_cleanup.sh

echo "=== Weekly Cleanup $(date) ==="

# Rotate logs
journalctl --vacuum-time=30d

# Clean old sessions (older than 30 days)
psql $DATABASE_URL -c "
DELETE FROM face_detections 
WHERE session_uuid IN (
    SELECT session_uuid 
    FROM face_detection_sessions 
    WHERE started_at < NOW() - INTERVAL '30 days'
);

DELETE FROM face_detection_sessions 
WHERE started_at < NOW() - INTERVAL '30 days';
"

# Vacuum database
psql $DATABASE_URL -c "VACUUM ANALYZE;"

# Clear cache
curl -X POST http://localhost:8003/admin/clear-cache

echo "=== Cleanup Complete ==="
```

#### Backup Database
```bash
#!/bin/bash
# backup_database.sh

backup_dir="/opt/backups/ppl-meta-vision"
timestamp=$(date +%Y%m%d_%H%M%S)
backup_file="$backup_dir/ppl_meta_vision_$timestamp.sql"

mkdir -p $backup_dir

echo "Creating backup: $backup_file"
pg_dump $DATABASE_URL > $backup_file

if [[ $? -eq 0 ]]; then
    echo "✅ Backup successful"
    gzip $backup_file
    
    # Keep only last 7 backups
    ls -t $backup_dir/*.sql.gz | tail -n +8 | xargs rm -f
else
    echo "❌ Backup failed"
    exit 1
fi
```

### Incident Response

#### Service Down
1. **Check service status:** `systemctl status ppl-meta-vision`
2. **Review logs:** `journalctl -u ppl-meta-vision --since "10 minutes ago"`
3. **Check dependencies:** Database, network connectivity
4. **Restart service:** `systemctl restart ppl-meta-vision`
5. **Verify recovery:** Run health check script

#### High Memory Usage
1. **Check memory:** `free -m` and `ps aux --sort=-%mem | head -10`
2. **Review application logs** for memory leaks
3. **Check database connections:** Active sessions
4. **Consider restart** if memory continues growing
5. **Scale horizontally** if needed

#### Database Issues
1. **Check connections:** `SELECT count(*) FROM pg_stat_activity;`
2. **Review slow queries:** `SELECT query, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;`
3. **Check disk space:** `df -h`
4. **Consider connection pool tuning**
5. **Run VACUUM ANALYZE** if needed

### Scaling Operations

#### Horizontal Scaling
```bash
# Deploy additional instances
docker run -d \
  --name ppl-meta-vision-2 \
  -p 8004:8003 \
  -e DATABASE_URL="$DATABASE_URL" \
  ppl-meta-vision:latest

# Update load balancer configuration
# Add new upstream server to Nginx config
```

#### Database Scaling
```bash
# Enable read replicas
# Configure connection routing
# Monitor replication lag
```

---

## Developer Documentation

### Architecture Overview

The PPL Meta Vision Service follows a layered architecture:

```
┌─────────────────────────────────────┐
│            API Layer                │  FastAPI endpoints
├─────────────────────────────────────┤
│          Service Layer              │  Business logic
├─────────────────────────────────────┤
│          Data Layer                 │  Database operations
└─────────────────────────────────────┘
```

### Code Structure

```
src/
├── main.py                 # FastAPI application entry point
├── api_models.py           # Pydantic models for API
├── session_manager.py      # Session lifecycle management
├── analytics_service.py    # Analytics and reporting
├── database.py            # Database connection and operations
├── models.py              # Data models
└── utils/
    ├── logging.py         # Logging configuration
    ├── metrics.py         # Performance metrics
    └── validators.py      # Input validation

tests/
├── test_unit_comprehensive.py          # Unit tests
├── test_integration_standalone.py      # Integration tests
├── test_performance_optimization.py    # Performance tests
└── conftest.py                         # Test configuration
```

### Development Workflow

1. **Feature Development**
   ```bash
   # Create feature branch
   git checkout -b feature/new-analytics-endpoint
   
   # Make changes
   # Add tests
   # Update documentation
   
   # Run tests
   python -m pytest tests/ -v
   
   # Check performance
   python tests/test_performance_optimization.py
   ```

2. **Code Quality**
   ```bash
   # Format code
   black src/ tests/
   
   # Lint code
   flake8 src/ tests/
   
   # Type checking
   mypy src/
   ```

3. **Testing**
   ```bash
   # Unit tests
   pytest tests/test_unit_comprehensive.py -v
   
   # Integration tests
   python tests/test_integration_standalone.py
   
   # Performance tests
   python tests/test_performance_optimization.py
   ```

### Adding New Features

#### New API Endpoint

1. **Define API Model** (api_models.py)
   ```python
   class NewFeatureRequest(BaseModel):
       parameter: str
       options: Dict[str, Any] = {}
   
   class NewFeatureResponse(BaseModel):
       result: str
       status: str
   ```

2. **Implement Business Logic** (service layer)
   ```python
   class NewFeatureService:
       def process_request(self, request: NewFeatureRequest) -> NewFeatureResponse:
           # Implementation here
           pass
   ```

3. **Add Endpoint** (main.py)
   ```python
   @app.post("/api/v1/new-feature", response_model=NewFeatureResponse)
   async def new_feature_endpoint(request: NewFeatureRequest):
       service = NewFeatureService()
       return service.process_request(request)
   ```

4. **Add Tests**
   ```python
   def test_new_feature_endpoint():
       request = NewFeatureRequest(parameter="test")
       response = client.post("/api/v1/new-feature", json=request.dict())
       assert response.status_code == 200
   ```

#### Database Schema Changes

1. **Create Migration Script**
   ```python
   # migrations/001_add_new_table.py
   def upgrade():
       """Add new table for feature."""
       cursor.execute("""
           CREATE TABLE new_feature_data (
               id SERIAL PRIMARY KEY,
               session_uuid UUID REFERENCES face_detection_sessions(session_uuid),
               data JSONB NOT NULL,
               created_at TIMESTAMP DEFAULT NOW()
           );
       """)
   ```

2. **Update Models**
   ```python
   # models.py
   @dataclass
   class NewFeatureData:
       id: Optional[int]
       session_uuid: str
       data: Dict[str, Any]
       created_at: datetime
   ```

3. **Test Migration**
   ```bash
   # Test on development database
   python migrations/001_add_new_table.py
   ```

### Performance Guidelines

1. **Database Queries**
   - Use prepared statements
   - Add appropriate indexes
   - Limit result sets with pagination
   - Use connection pooling

2. **API Responses**
   - Implement caching for frequent queries
   - Use compression for large responses
   - Paginate large datasets
   - Set appropriate timeouts

3. **Memory Management**
   - Use object pools for frequently created objects
   - Implement proper cleanup in finally blocks
   - Monitor memory usage in long-running operations
   - Use generators for large data processing

### Security Considerations

1. **Input Validation**
   - Validate all input parameters
   - Sanitize database queries
   - Check UUID formats
   - Limit request sizes

2. **Authentication & Authorization**
   - Implement JWT token validation
   - Use HTTPS in production
   - Validate API keys
   - Implement rate limiting

3. **Data Protection**
   - Encrypt sensitive data
   - Use secure database connections
   - Implement audit logging
   - Regular security updates

---

## Performance & Monitoring

### Key Performance Indicators (KPIs)

#### Response Time Targets
- Session creation: < 50ms (95th percentile)
- Face storage: < 10ms per detection
- Analytics queries: < 100ms
- Health checks: < 5ms

#### Throughput Targets
- Sessions per second: 100+
- Face detections per second: 1000+
- Concurrent sessions: 500+
- Database connections: 25 max

#### Availability Targets
- Service uptime: 99.9%
- Database uptime: 99.95%
- Mean time to recovery: < 5 minutes

### Monitoring Setup

#### Prometheus Metrics
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Counters
sessions_created_total = Counter('sessions_created_total', 'Total sessions created')
faces_detected_total = Counter('faces_detected_total', 'Total faces detected')
api_requests_total = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint'])

# Histograms
session_creation_duration = Histogram('session_creation_duration_seconds', 'Session creation time')
face_storage_duration = Histogram('face_storage_duration_seconds', 'Face storage time')
api_request_duration = Histogram('api_request_duration_seconds', 'API request time', ['method', 'endpoint'])

# Gauges
active_sessions = Gauge('active_sessions', 'Number of active sessions')
database_connections = Gauge('database_connections', 'Number of database connections')
memory_usage_bytes = Gauge('memory_usage_bytes', 'Memory usage in bytes')
```

#### Grafana Dashboards

1. **Service Overview Dashboard**
   - Request rate and response times
   - Error rates and status codes
   - Active sessions and throughput

2. **Database Dashboard**
   - Connection pool usage
   - Query performance
   - Lock waits and deadlocks

3. **System Dashboard**
   - CPU and memory usage
   - Disk I/O and network
   - Container metrics

#### Alerting Rules

```yaml
# alerting_rules.yml
groups:
- name: vision_service_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(api_requests_total{status=~"5.."}[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} per second"

  - alert: SlowAPIResponse
    expr: histogram_quantile(0.95, api_request_duration_seconds) > 0.2
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API responses are slow"
      description: "95th percentile response time is {{ $value }}s"

  - alert: DatabaseConnectionsHigh
    expr: database_connections > 20
    for: 3m
    labels:
      severity: warning
    annotations:
      summary: "High database connection usage"
      description: "{{ $value }} database connections in use"
```

### Performance Optimization

#### Database Optimization
```sql
-- Performance indexes
CREATE INDEX CONCURRENTLY idx_sessions_started_at_status 
ON face_detection_sessions(started_at, processing_status);

CREATE INDEX CONCURRENTLY idx_detections_session_timestamp 
ON face_detections(session_uuid, timestamp);

-- Query optimization
EXPLAIN (ANALYZE, BUFFERS) 
SELECT * FROM face_detection_sessions 
WHERE started_at > NOW() - INTERVAL '1 day';
```

#### Caching Strategy
```python
# cache_config.py
CACHE_CONFIG = {
    'session_status': {'ttl': 60, 'max_size': 1000},
    'analytics_summary': {'ttl': 300, 'max_size': 100},
    'device_stats': {'ttl': 600, 'max_size': 500}
}
```

#### Connection Pooling
```python
# database_config.py
DATABASE_CONFIG = {
    'pool_size': 20,
    'max_overflow': 10,
    'pool_timeout': 30,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

---

This comprehensive documentation package provides everything needed for development, deployment, operations, and maintenance of the PPL Meta Vision Service. Regular updates should be made as the service evolves and new features are added.