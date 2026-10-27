# Staging Environment Deployment Guide
# PPL Meta Platform - vmeta Service
# Continuous Individuals and MVR Pipeline

## Overview

This guide covers deploying the complete vmeta service with batch processing pipeline to a staging environment for integration testing and validation before production rollout.

## Prerequisites

- Staging environment with all PPL Meta services deployed
- PostgreSQL database (separate from production)
- Prometheus and Grafana for monitoring
- Valid SSL certificates for staging domain
- Admin access to staging infrastructure

## Deployment Checklist

### 1. Database Setup

#### Run Migrations

```bash
# Connect to staging database
psql -h staging-db.ppl-meta.internal -U vmeta_user -d ppl_meta_vmeta_staging

# Run all batch processing migrations
\i migrations/006_batch_processing_state.sql
\i migrations/007_batch_video_assignments.sql
\i migrations/008_batch_processing_history.sql
\i migrations/009_batch_processing_config.sql

# Verify tables created
\dt batch_*

# Insert default configuration
INSERT INTO batch_processing_config (
    collection_id,
    batch_size_threshold,
    partial_batch_min_videos,
    partial_batch_timeout_minutes,
    max_concurrent_batches
) VALUES (
    NULL,  -- Global config
    5,     -- Default batch size
    2,     -- Min partial batch size
    10,    -- Timeout minutes
    3      -- Max concurrent batches
);
```

#### Verify Indexes

```sql
-- Check all indexes created
SELECT 
    tablename, 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename LIKE 'batch_%'
ORDER BY tablename, indexname;

-- Expected indexes:
-- batch_processing_state: 3 indexes
-- batch_video_assignments: 3 indexes
-- batch_processing_history: 2 indexes
```

### 2. Service Configuration

#### Environment Variables

Create `.env.staging` file:

```bash
# Database Configuration
DB_HOST=staging-db.ppl-meta.internal
DB_PORT=5432
DB_NAME=ppl_meta_vmeta_staging
DB_USER=vmeta_user
DB_PASSWORD=${STAGING_DB_PASSWORD}
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20

# Service URLs
ORCHESTRATOR_URL=https://orchestrator-staging.ppl-meta.internal
MEDIA_URL=https://media-staging.ppl-meta.internal
CAMERAS_URL=https://cameras-staging.ppl-meta.internal
VISION_URL=https://vision-staging.ppl-meta.internal
NODE_URL=https://node-staging.ppl-meta.internal

# Batch Processing Configuration
BATCH_SIZE_THRESHOLD=5
BATCH_TIMEOUT_MINUTES=10
MIN_PARTIAL_BATCH_SIZE=2
MAX_CONCURRENT_BATCHES=3
WORKER_POOL_SIZE=3

# Event Configuration
EVENT_TRIGGERING_ENABLED=true
WEBSOCKET_RECONNECT_INTERVAL=5
POLLING_INTERVAL_SECONDS=30
POLLING_ENABLED=true

# Resource Limits
MAX_BATCH_MEMORY_GB=2
MAX_BATCH_PROCESSING_TIME_SECONDS=300

# Monitoring
METRICS_ENABLED=true
METRICS_PORT=9090
LOG_LEVEL=INFO
LOG_FORMAT=json

# Feature Flags
BATCH_PROCESSING_ENABLED=true
TWO_LEVEL_CACHE_ENABLED=true
HYBRID_TRIGGER_ENABLED=true
```

#### Configuration File

Update `config/batch_processing.yml`:

```yaml
batch_processing:
  # Environment
  environment: staging
  
  # Batch sizing
  default_batch_size: 5
  min_batch_size: 2
  max_batch_size: 20
  
  # Timeouts
  batch_timeout_minutes: 10
  session_timeout_minutes: 5
  partial_batch_timeout_minutes: 10
  
  # Concurrency
  max_concurrent_batches: 3
  worker_pool_size: 3
  
  # Resource limits
  max_batch_memory_gb: 2
  max_videos_per_session: 10
  max_processing_time_seconds: 300
  
  # Triggering
  event_triggering:
    enabled: true
    websocket_enabled: true
    websocket_reconnect_interval_seconds: 5
    polling_enabled: true
    polling_interval_seconds: 30
  
  # Caching
  caching:
    level_1_enabled: true  # Individual cache
    level_2_enabled: true  # MVR cache
    session_wide_cache_enabled: true
  
  # Monitoring
  monitoring:
    metrics_enabled: true
    metrics_port: 9090
    log_level: INFO
    log_format: json
    
  # Collection-specific overrides
  collections:
    staging-test-camera:
      batch_size_threshold: 5
      partial_batch_timeout_minutes: 5
```

### 3. Deploy Service

#### Docker Deployment

```bash
# Build image
docker build -t ppl-meta-vmeta:staging -f docker/Dockerfile .

# Tag for staging registry
docker tag ppl-meta-vmeta:staging staging-registry.ppl-meta.internal/vmeta:latest

# Push to registry
docker push staging-registry.ppl-meta.internal/vmeta:latest

# Deploy container
docker run -d \
  --name ppl-meta-vmeta-staging \
  --env-file .env.staging \
  -p 8008:8008 \
  -p 9090:9090 \
  -v $(pwd)/config:/app/config:ro \
  -v $(pwd)/logs:/app/logs \
  --restart unless-stopped \
  staging-registry.ppl-meta.internal/vmeta:latest

# Check logs
docker logs -f ppl-meta-vmeta-staging
```

#### Kubernetes Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ppl-meta-vmeta
  namespace: ppl-meta-staging
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ppl-meta-vmeta
  template:
    metadata:
      labels:
        app: ppl-meta-vmeta
    spec:
      containers:
      - name: vmeta
        image: staging-registry.ppl-meta.internal/vmeta:latest
        ports:
        - containerPort: 8008
          name: http
        - containerPort: 9090
          name: metrics
        env:
        - name: DB_HOST
          value: "staging-db.ppl-meta.internal"
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: vmeta-db-secret
              key: password
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8008
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8008
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: ppl-meta-vmeta
  namespace: ppl-meta-staging
spec:
  selector:
    app: ppl-meta-vmeta
  ports:
  - name: http
    port: 8008
    targetPort: 8008
  - name: metrics
    port: 9090
    targetPort: 9090
```

Deploy:

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/ppl-meta-vmeta -n ppl-meta-staging
```

### 4. Configure Monitoring

#### Prometheus Scrape Config

Add to Prometheus configuration:

```yaml
scrape_configs:
  - job_name: 'ppl-meta-vmeta-staging'
    static_configs:
      - targets: ['vmeta-staging.ppl-meta.internal:9090']
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /metrics
    scheme: http
```

#### Import Grafana Dashboard

```bash
# Import dashboard JSON
curl -X POST \
  https://grafana-staging.ppl-meta.internal/api/dashboards/db \
  -H "Authorization: Bearer ${GRAFANA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @docs/monitoring/grafana-dashboard.json
```

#### Configure Alerting

```bash
# Copy alerting rules
cp docs/monitoring/prometheus-alerts.yml /etc/prometheus/rules/vmeta-staging.yml

# Reload Prometheus
curl -X POST https://prometheus-staging.ppl-meta.internal/-/reload
```

### 5. Verification Tests

#### Health Check

```bash
# Service health
curl https://vmeta-staging.ppl-meta.internal/health | jq '.'

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2025-11-13T10:00:00Z",
#   "version": "1.0.0"
# }
```

#### Database Connectivity

```bash
# Check database connection
curl https://vmeta-staging.ppl-meta.internal/api/v1/batch-processing/health | jq '.database'

# Expected:
# {
#   "status": "connected",
#   "pool_size": 20,
#   "active_connections": 2
# }
```

#### Metrics Endpoint

```bash
# Check Prometheus metrics
curl https://vmeta-staging.ppl-meta.internal/metrics | grep batch_processing_total

# Should see metrics exposed
```

### 6. Run Integration Tests

#### Configure Test Environment

```bash
# Set test environment variables
export TEST_VMETA_URL=https://vmeta-staging.ppl-meta.internal
export TEST_AUTH_TOKEN=${STAGING_AUTH_TOKEN}
export TEST_DB_HOST=staging-db.ppl-meta.internal
export TEST_DB_NAME=ppl_meta_vmeta_staging
```

#### Run E2E Tests

```bash
cd tests/integration

# Run end-to-end tests
pytest test_e2e_pipeline.py -v --tb=short

# Expected: All tests pass
# test_complete_workflow_5_videos ✅
# test_partial_batch_recording_stop ✅
# test_multi_collection_concurrent ✅
# test_failure_recovery_retry ✅
# test_cache_effectiveness ✅
```

#### Run Load Tests

```bash
cd tests/load

# Run performance tests
pytest test_performance.py -v -m load --tb=short

# Monitor results:
# - Processing time < 60s per batch
# - Throughput > 0.1 videos/second
# - Cache hit rate increases over time
# - Worker pool handles concurrency
```

### 7. Smoke Tests

#### Test Batch Accumulation

```bash
# Configure batch size
curl -X PUT https://vmeta-staging.ppl-meta.internal/api/v1/batch-processing/batch-size \
  -H "Authorization: Bearer ${STAGING_AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 5,
    "collection_id": "staging-test-camera"
  }'

# Monitor batch status
watch -n 5 'curl -s https://vmeta-staging.ppl-meta.internal/api/v1/batch-processing/status \
  -H "Authorization: Bearer ${STAGING_AUTH_TOKEN}" | jq .'
```

#### Test Partial Batch Trigger

```bash
# Add 3 videos (below threshold)
# Then simulate recording stop
curl -X POST https://cameras-staging.ppl-meta.internal/api/v1/recordings/stop \
  -H "Authorization: Bearer ${STAGING_AUTH_TOKEN}" \
  -d '{
    "collection_id": "staging-test-camera"
  }'

# Verify partial batch triggered
curl -s https://vmeta-staging.ppl-meta.internal/api/v1/batch-processing/history?limit=1 \
  -H "Authorization: Bearer ${STAGING_AUTH_TOKEN}" \
  | jq '.batches[0] | {is_partial: .is_partial_batch, trigger: .trigger_reason}'
```

### 8. Monitoring Verification

#### Check Grafana Dashboard

1. Navigate to: https://grafana-staging.ppl-meta.internal
2. Open "PPL Meta Batch Processing" dashboard
3. Verify panels showing data:
   - Batches processed 24h
   - Processing duration
   - Cache hit rates
   - Worker pool status
   - Camera events

#### Verify Alerts

```bash
# Check alert rules loaded
curl https://prometheus-staging.ppl-meta.internal/api/v1/rules | jq '.data.groups[] | select(.name=="batch_processing")'

# Expected alerts:
# - HighBatchErrorRate
# - WorkerPoolExhausted
# - WebSocketDisconnected
# - BatchProcessingSlowdown
# - DatabaseConnectionIssues
```

### 9. Rollback Plan

If issues occur, rollback procedure:

```bash
# Stop new service
docker stop ppl-meta-vmeta-staging

# Revert database migrations (if needed)
psql -h staging-db.ppl-meta.internal -U vmeta_user -d ppl_meta_vmeta_staging < migrations/rollback.sql

# Restart previous version
docker start ppl-meta-vmeta-staging-previous

# Verify old service running
curl https://vmeta-staging.ppl-meta.internal/health
```

### 10. Sign-Off Criteria

Before promoting to production, verify:

- [ ] All database migrations applied successfully
- [ ] Service starts and health check returns healthy
- [ ] All integration tests pass (100% success rate)
- [ ] Load tests show acceptable performance
- [ ] Prometheus metrics being collected
- [ ] Grafana dashboard displaying data
- [ ] Alerting rules configured and tested
- [ ] Logs flowing to centralized logging (ELK/Loki)
- [ ] No critical errors in logs for 24 hours
- [ ] Worker pool handling concurrent batches
- [ ] Cache hit rates improving over time
- [ ] Partial batch triggering working
- [ ] Database connections stable
- [ ] Memory usage within limits
- [ ] CPU usage acceptable
- [ ] Documentation updated

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker logs ppl-meta-vmeta-staging

# Common issues:
# 1. Database connection failed
#    - Verify DB_HOST and credentials
#    - Check network connectivity
#    - Ensure migrations ran

# 2. Port already in use
#    - Check existing processes: lsof -i:8008
#    - Stop conflicting service

# 3. Configuration error
#    - Validate config/batch_processing.yml
#    - Check environment variables
```

### Tests Failing

```bash
# Reset test database
psql -h staging-db.ppl-meta.internal -U vmeta_user -d ppl_meta_vmeta_staging \
  -c "DELETE FROM batch_processing_state; DELETE FROM batch_video_assignments; DELETE FROM batch_processing_history;"

# Re-run specific test
pytest tests/integration/test_e2e_pipeline.py::TestEndToEndPipeline::test_complete_workflow_5_videos -v
```

### Metrics Not Appearing

```bash
# Check metrics endpoint
curl https://vmeta-staging.ppl-meta.internal/metrics

# Verify Prometheus scraping
curl https://prometheus-staging.ppl-meta.internal/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job=="ppl-meta-vmeta-staging")'

# Check for scrape errors
```

## Next Steps

After successful staging deployment:

1. Monitor for 48 hours minimum
2. Run load tests daily
3. Review all alerts and false positives
4. Document any issues encountered
5. Update runbook based on learnings
6. Schedule production deployment
7. Prepare rollback plan for production
8. Brief operations team on new features

## Contact

For deployment issues:
- DevOps Team: devops@ppl-meta.internal
- Platform Team: platform@ppl-meta.internal
- On-Call: +1-XXX-XXX-XXXX
