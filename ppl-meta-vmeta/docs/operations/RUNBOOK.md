# Operations Runbook
## PPL Meta Platform - vmeta Service
### Continuous Individuals and MVR Batch Processing Pipeline

**Version**: 1.0  
**Last Updated**: November 13, 2025  
**On-Call Contact**: platform@ppl-meta.internal  

---

## Table of Contents

1. [Service Overview](#service-overview)
2. [Architecture Quick Reference](#architecture-quick-reference)
3. [Alert Response Guides](#alert-response-guides)
4. [Common Issues and Solutions](#common-issues-and-solutions)
5. [Troubleshooting Procedures](#troubleshooting-procedures)
6. [Monitoring Dashboard Guide](#monitoring-dashboard-guide)
7. [Escalation Procedures](#escalation-procedures)
8. [Disaster Recovery](#disaster-recovery)
9. [Maintenance Procedures](#maintenance-procedures)
10. [FAQ](#faq)

---

## Service Overview

### What is the Batch Processing Pipeline?

The vmeta service processes recorded video segments in batches to create:
- **Individuals**: Face detections from single videos
- **MVR People**: Merged identities across multiple videos using face similarity

**Key Features**:
- Automatic batch triggering when threshold reached (default: 5 videos)
- Hybrid partial batch handling (recording stop + timeout fallback)
- Two-level caching (individual + MVR)
- Concurrent processing for multiple collections

### Service Dependencies

```
vmeta Service
  ├─> PostgreSQL Database (batch state, history)
  ├─> Orchestrator Service (tracking sessions, individuals)
  ├─> Media Service (video queries)
  ├─> Vision Service (embeddings, implicit via Orchestrator)
  └─> Camera Service (WebSocket events, recording notifications)
```

### Key Metrics

| Metric | Normal Range | Alert Threshold |
|--------|--------------|-----------------|
| Batch Processing Time (P95) | 30-60s | > 120s (warning) |
| Error Rate | < 2% | > 10% (critical) |
| Cache Hit Rate | 40-70% | < 20% (warning) |
| Worker Pool Utilization | 30-60% | > 90% (critical) |
| Database Connections | 2-10 | > 18/20 (critical) |

---

## Architecture Quick Reference

### Batch Processing Flow

```
1. Video Recording Complete
   ↓
2. Face Detection Completes
   ↓
3. Video Added to Batch (BatchMonitor)
   ↓
4. Threshold Check
   ├─> If threshold met (5 videos) → Trigger Batch
   └─> If below threshold → Continue accumulating
   ↓
5. Hybrid Trigger Logic
   ├─> Recording stops → Immediate trigger (PRIMARY)
   └─> Timeout (10min) → Fallback trigger
   ↓
6. Pipeline Execution (PipelineExecutor)
   ├─> Query videos from Media Service
   ├─> Check Individual Cache (Level 1)
   ├─> Create new individuals via Orchestrator
   ├─> Check MVR Cache (Level 2)
   ├─> Run merge operation
   └─> Store results
   ↓
7. Batch Completion
   └─> Update history, emit metrics
```

### Key Components

| Component | Responsibility | Location |
|-----------|---------------|----------|
| BatchMonitor | Track video count, detect threshold | `src/services/batch_monitor.py` |
| HybridBatchTrigger | Trigger logic (threshold/recording stop/timeout) | `src/services/hybrid_batch_trigger.py` |
| PipelineExecutor | Execute tracking session, create objects | `src/services/pipeline_executor.py` |
| CameraEventIntegration | Subscribe to Camera Service events | `src/services/event_integration.py` |
| BatchRepository | Database operations | `src/database/batch_repository.py` |

---

## Alert Response Guides

### 🚨 CRITICAL: HighBatchErrorRate

**Alert**: > 10% of batches failing in last 5 minutes

**Immediate Actions**:

1. Check application logs for error patterns:
```bash
kubectl logs -n ppl-meta deployment/ppl-meta-vmeta --tail=100 | grep ERROR
```

2. Verify dependent services:
```bash
# Orchestrator health
curl https://orchestrator.ppl-meta.com/health

# Media Service health
curl https://media.ppl-meta.com/health

# Database connectivity
kubectl exec -it ppl-meta-vmeta-xxx -- psql -h db-host -U vmeta_user -c "SELECT 1"
```

3. Check recent batch failures:
```bash
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/history?status=failed&limit=10 \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Common Causes & Solutions**:

| Cause | Symptoms | Solution |
|-------|----------|----------|
| Orchestrator unavailable | Connection timeout errors | Restart Orchestrator service |
| Media Service timeout | "Failed to query videos" | Check Media Service load |
| Database deadlock | "Could not acquire lock" | Restart vmeta service |
| Invalid video data | "Video UUID not found" | Check data integrity |

**Escalation**: If error rate > 25%, escalate immediately to Platform Lead.

---

### 🚨 CRITICAL: WorkerPoolExhausted

**Alert**: All workers busy + queue size > 10

**Immediate Actions**:

1. Check worker pool status:
```bash
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/health \
  -H "Authorization: Bearer $TOKEN" | jq '.worker_pool'
```

2. Check if batches are stuck:
```bash
# Get processing batches
SELECT 
    batch_uuid,
    collection_id,
    video_count,
    triggered_at,
    NOW() - triggered_at AS processing_duration
FROM batch_processing_state
WHERE status = 'processing'
ORDER BY triggered_at;
```

3. Identify slow batches:
```bash
# Prometheus query
rate(batch_processing_duration_seconds_sum[5m])
/ 
rate(batch_processing_duration_seconds_count[5m])
```

**Solutions**:

**If batches are stuck** (> 10 minutes):
```bash
# Reset stuck batches
UPDATE batch_processing_state
SET status = 'failed', error_message = 'Timeout - manual reset'
WHERE status = 'processing'
  AND triggered_at < NOW() - INTERVAL '10 minutes';
```

**If load is genuinely high**:
```bash
# Scale up workers (Kubernetes)
kubectl scale deployment ppl-meta-vmeta --replicas=5 -n ppl-meta

# Or update worker pool size
kubectl set env deployment/ppl-meta-vmeta WORKER_POOL_SIZE=5 -n ppl-meta
```

**Escalation**: If queue continues growing after 30 minutes, escalate.

---

### 🚨 CRITICAL: WebSocketDisconnected

**Alert**: WebSocket to Camera Service disconnected > 2 minutes

**Impact**:
- Recording stop events not received
- Partial batch triggering degraded
- Falls back to timeout-based triggering (slower)

**Immediate Actions**:

1. Check Camera Service health:
```bash
curl https://cameras.ppl-meta.com/health
```

2. Check WebSocket reconnection attempts:
```bash
kubectl logs deployment/ppl-meta-vmeta | grep "WebSocket" | tail -20
```

3. Force reconnection:
```bash
# Restart vmeta service (triggers reconnection)
kubectl rollout restart deployment/ppl-meta-vmeta -n ppl-meta
```

**Solutions**:

| Issue | Logs Show | Fix |
|-------|-----------|-----|
| Camera Service down | "Connection refused" | Restart Camera Service |
| Network issue | "Timeout" | Check network connectivity |
| Auth issue | "401 Unauthorized" | Refresh auth token |
| WebSocket limit | "Too many connections" | Increase Camera Service limits |

**Escalation**: If Camera Service is down, escalate to Infrastructure team.

---

### 🚨 CRITICAL: BatchProcessingStalled

**Alert**: No batch completed in 10 minutes, but batches accumulating

**Immediate Actions**:

1. Check last batch completion:
```bash
# Query database
SELECT 
    batch_uuid,
    collection_id,
    completed_at,
    processing_time_seconds
FROM batch_processing_history
ORDER BY completed_at DESC
LIMIT 5;
```

2. Check active batches:
```bash
SELECT * FROM batch_processing_state WHERE status = 'processing';
```

3. Check worker health:
```bash
# Check for worker crashes
kubectl logs deployment/ppl-meta-vmeta --previous
```

**Solutions**:

**If database connection lost**:
```bash
# Check database connectivity
kubectl exec -it ppl-meta-vmeta-xxx -- psql -h db-host -U vmeta_user -c "SELECT NOW()"

# If failed, restart vmeta
kubectl rollout restart deployment/ppl-meta-vmeta
```

**If worker deadlock**:
```bash
# Restart service (will reset workers)
kubectl rollout restart deployment/ppl-meta-vmeta -n ppl-meta
```

**Escalation**: If restart doesn't resolve in 5 minutes, escalate immediately.

---

### ⚠️ WARNING: BatchProcessingSlowdown

**Alert**: P95 processing time > 2 minutes

**Investigation Steps**:

1. Check current processing times:
```bash
# Prometheus query
histogram_quantile(0.95, 
  rate(batch_processing_duration_seconds_bucket[10m])
)
```

2. Identify slow collections:
```bash
# By collection
sum by (collection_id) (
  rate(batch_processing_duration_seconds_sum[10m])
  /
  rate(batch_processing_duration_seconds_count[10m])
)
```

3. Check dependent services:
```bash
# Orchestrator response time
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket{service="orchestrator"}[10m])
)
```

**Common Causes**:

- **High load**: More collections enabled → Scale workers
- **Large batches**: Video count > 10 → Review batch size config
- **Slow cache**: Cache hit rate low → Warm cache
- **Orchestrator slow**: High P95 latency → Scale Orchestrator

**Actions**:
- Monitor for 30 minutes
- If persists, consider scaling workers or optimizing batch size
- Review with team during next standup

---

### ⚠️ WARNING: CacheHitRateLow

**Alert**: Cache hit rate < 20% for 30 minutes

**Investigation**:

1. Check cache metrics:
```bash
# Individual cache hit rate by collection
avg by (collection_id) (cache_hit_rate{cache_level="individual"})
```

2. Check if new collections:
```bash
# Count batches per collection
sum by (collection_id) (batch_processing_total)
```

3. Verify cache is enabled:
```bash
# Check config
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/config | jq '.caching'
```

**Common Causes**:

| Cause | Indicator | Action |
|-------|-----------|--------|
| New collections | Low batch count | Expected, will improve |
| Cache disabled | Config shows disabled | Enable in config |
| High face turnover | Many unique faces | Expected, no action |
| Cache eviction too aggressive | Cache size config | Increase cache size |

**No Immediate Action Required** - Monitor for improvement over 24 hours.

---

## Common Issues and Solutions

### Issue: Batch Not Triggering

**Symptoms**:
- Videos accumulating but batch not processing
- Batch counter stuck

**Diagnosis**:
```bash
# Check accumulating batches
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/status | jq '.'

# Check threshold config
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/config | jq '.batch_size_threshold'
```

**Solutions**:

1. **Threshold not reached**: Wait for more videos or manually trigger
```bash
curl -X POST https://vmeta.ppl-meta.com/api/v1/batch-processing/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"collection_id": "xxx", "force_trigger": true}'
```

2. **Event subscription broken**: Check WebSocket connection
```bash
kubectl logs deployment/ppl-meta-vmeta | grep "WebSocket"
```

3. **Feature flag disabled**: Check feature flags
```bash
SELECT * FROM feature_flags WHERE feature_name = 'batch_processing_enabled';
```

---

### Issue: Partial Batches Not Triggering

**Symptoms**:
- Recording stops but remaining videos not processed
- Incomplete batches accumulating

**Diagnosis**:
```bash
# Check incomplete batches
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/incomplete \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

**Solutions**:

1. **Recording stop event not received**:
```bash
# Check WebSocket status
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/health | jq '.websocket'

# If disconnected, restart service
kubectl rollout restart deployment/ppl-meta-vmeta
```

2. **Timeout not configured**:
```bash
# Check timeout setting
SELECT 
    partial_batch_timeout_minutes
FROM batch_processing_config
WHERE collection_id IS NULL;

# If NULL or 0, update
UPDATE batch_processing_config
SET partial_batch_timeout_minutes = 10
WHERE collection_id IS NULL;
```

3. **Min partial batch size not met**:
```bash
# Check if below minimum (default: 2)
# If 1 video remaining, it won't trigger
# Either lower minimum or wait for more videos
```

---

### Issue: High Memory Usage

**Symptoms**:
- Service memory > 80%
- OOM kills in logs

**Diagnosis**:
```bash
# Check memory usage
kubectl top pod -n ppl-meta | grep vmeta

# Check batch sizes
SELECT 
    collection_id,
    video_count,
    processing_time_seconds
FROM batch_processing_history
ORDER BY video_count DESC
LIMIT 20;
```

**Solutions**:

1. **Reduce batch size**:
```bash
curl -X PUT https://vmeta.ppl-meta.com/api/v1/batch-processing/batch-size \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"batch_size": 3}'  # Reduce from 5 to 3
```

2. **Increase memory limits**:
```bash
# Update deployment
kubectl set resources deployment ppl-meta-vmeta \
  --limits=memory=4Gi \
  -n ppl-meta
```

3. **Check for memory leaks**:
```bash
# Monitor over time
watch -n 10 'kubectl top pod -n ppl-meta | grep vmeta'

# If continuously increasing, restart
kubectl rollout restart deployment/ppl-meta-vmeta
```

---

### Issue: Database Connection Errors

**Symptoms**:
- "Connection refused" errors
- "Too many connections" errors
- Batch operations failing

**Diagnosis**:
```bash
# Check database connections
SELECT 
    count(*) as current_connections,
    max_connections
FROM pg_stat_activity, pg_settings
WHERE name = 'max_connections'
GROUP BY max_connections;

# Check vmeta connections
SELECT count(*) 
FROM pg_stat_activity 
WHERE usename = 'vmeta_user';
```

**Solutions**:

1. **Connection pool exhausted**:
```bash
# Increase pool size
kubectl set env deployment/ppl-meta-vmeta \
  DB_POOL_MAX_SIZE=30 \
  -n ppl-meta
```

2. **Database overloaded**:
```bash
# Check slow queries
SELECT 
    pid,
    now() - query_start as duration,
    query
FROM pg_stat_activity
WHERE state = 'active'
ORDER BY duration DESC
LIMIT 10;

# Kill long-running queries if needed
SELECT pg_terminate_backend(pid);
```

3. **Connection leaks**:
```bash
# Restart service to reset connections
kubectl rollout restart deployment/ppl-meta-vmeta
```

---

## Troubleshooting Procedures

### Procedure: Investigate Batch Failure

1. **Get batch details**:
```bash
BATCH_UUID="<batch-uuid>"

curl "https://vmeta.ppl-meta.com/api/v1/batch-processing/history?batch_uuid=$BATCH_UUID" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
```

2. **Check error message**:
```sql
SELECT 
    batch_uuid,
    error_message,
    retry_count,
    triggered_at,
    completed_at
FROM batch_processing_history
WHERE batch_uuid = '<batch-uuid>';
```

3. **Check videos in batch**:
```sql
SELECT 
    video_uuid,
    video_start_time,
    faces_detected
FROM batch_video_assignments
WHERE batch_uuid = '<batch-uuid>'
ORDER BY sequence_number;
```

4. **Check application logs**:
```bash
kubectl logs deployment/ppl-meta-vmeta \
  --since=1h \
  | grep "$BATCH_UUID"
```

5. **Retry batch** (if transient error):
```bash
curl -X POST https://vmeta.ppl-meta.com/api/v1/batch-processing/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "collection_id": "<collection-id>",
    "force_trigger": true
  }'
```

---

### Procedure: Reset Stuck Batch

**WARNING**: Only use if batch genuinely stuck (> 15 minutes processing)

```sql
-- 1. Identify stuck batch
SELECT 
    batch_uuid,
    collection_id,
    NOW() - triggered_at AS stuck_duration
FROM batch_processing_state
WHERE status = 'processing'
  AND triggered_at < NOW() - INTERVAL '15 minutes';

-- 2. Reset to accumulating
UPDATE batch_processing_state
SET 
    status = 'accumulating',
    triggered_at = NULL,
    session_uuid = NULL,
    error_message = 'Reset from stuck state',
    retry_count = retry_count + 1
WHERE batch_uuid = '<batch-uuid>';

-- 3. Manually trigger
-- Use API or wait for next video
```

---

### Procedure: Drain Collection (Maintenance)

To stop processing for a collection during maintenance:

```sql
-- 1. Disable feature flag for collection
INSERT INTO feature_flag_overrides (collection_id, feature_name, enabled)
VALUES ('<collection-id>', 'batch_processing_enabled', false)
ON CONFLICT (collection_id, feature_name)
DO UPDATE SET enabled = false;

-- 2. Wait for active batches to complete
SELECT * FROM batch_processing_state 
WHERE collection_id = '<collection-id>' 
  AND status = 'processing';

-- 3. After complete, perform maintenance

-- 4. Re-enable after maintenance
UPDATE feature_flag_overrides
SET enabled = true
WHERE collection_id = '<collection-id>'
  AND feature_name = 'batch_processing_enabled';
```

---

## Monitoring Dashboard Guide

### Grafana Dashboard: PPL Meta Batch Processing

**URL**: https://grafana.ppl-meta.com/d/batch-processing

**Key Panels**:

#### Row 1: Overview Metrics

- **Batches Processed (24h)**: Total batches completed in last 24 hours
  - **Normal**: Varies by load (50-500/day)
  - **Alert**: If 0 for > 1 hour

- **Avg Processing Time (P50)**: Median processing time
  - **Normal**: 30-45 seconds
  - **Alert**: > 60 seconds

- **Cache Hit Rate**: Individual cache effectiveness
  - **Normal**: 40-70%
  - **Alert**: < 20% (after warmup)

- **WebSocket Status**: Connection to Camera Service
  - **Normal**: 1 (connected)
  - **Alert**: 0 (disconnected)

#### Row 2: Processing Trends

- **Processing Rate per Collection**: Batches/hour by collection
  - Use to identify active collections
  - Spot unusual patterns

- **Partial Batch Triggers**: Why partial batches triggered
  - **recording_stopped**: Normal (primary trigger)
  - **timeout**: Fallback (acceptable)
  - **manual**: Operator intervention

#### Row 3: Performance Analysis

- **Processing Duration Distribution**: P50/P95/P99 over time
  - Watch for increasing trends
  - P95 should be < 2 minutes

- **Objects Created**: Individuals and MVR people created
  - **new**: Freshly created
  - **cached**: Reused from cache
  - Ratio shows cache effectiveness

#### Row 4: Worker Pool

- **Active Workers**: Currently processing batches
  - **Normal**: 1-3 (depending on load)
  - **Alert**: Equal to pool size + queue > 0

- **Queue Size**: Batches waiting for workers
  - **Normal**: 0-2
  - **Alert**: > 10

---

## Escalation Procedures

### Escalation Matrix

| Severity | Initial Response | Escalate After | Escalate To |
|----------|------------------|----------------|-------------|
| Critical (Service Down) | Immediate | 15 minutes | Platform Lead + On-Call Manager |
| Critical (High Error Rate) | < 10 minutes | 30 minutes | Platform Lead |
| Warning | < 30 minutes | 2 hours | Platform Team (Slack) |
| Info | Next business day | N/A | N/A |

### Contact Information

**Platform Team**:
- Slack: #platform-team
- Email: platform@ppl-meta.internal
- PagerDuty: platform-oncall

**Platform Lead**:
- Name: [Lead Name]
- Phone: +1-XXX-XXX-XXXX
- Email: lead@ppl-meta.internal

**Database Team**:
- Slack: #database-team
- On-Call: database-oncall (PagerDuty)

**Infrastructure Team**:
- Slack: #infrastructure
- On-Call: infra-oncall (PagerDuty)

### Escalation Decision Tree

```
Issue Detected
  ↓
Can you resolve in 10 minutes?
  ├─> Yes → Resolve and document
  └─> No → Is service degraded?
       ├─> Yes (Critical)
       │    └─> Escalate immediately to Platform Lead
       └─> No (Warning)
            └─> Post in #platform-team
                 ↓
            Resolution found in 2 hours?
              ├─> Yes → Document and close
              └─> No → Escalate to Platform Lead
```

---

## Disaster Recovery

### Scenario 1: Database Corruption

**Detection**: Batch operations failing, database errors in logs

**Recovery Steps**:

1. **Assess damage**:
```sql
-- Check table integrity
SELECT * FROM batch_processing_state LIMIT 1;
SELECT * FROM batch_video_assignments LIMIT 1;
SELECT * FROM batch_processing_history LIMIT 1;
```

2. **If tables accessible** (constraint violation, bad data):
```sql
-- Reset problem batches
DELETE FROM batch_video_assignments WHERE batch_uuid IN (
    SELECT batch_uuid FROM batch_processing_state WHERE status = 'error'
);
DELETE FROM batch_processing_state WHERE status = 'error';
```

3. **If tables corrupted** (cannot read):
```bash
# Stop vmeta service
kubectl scale deployment ppl-meta-vmeta --replicas=0

# Restore from backup (contact DBA team)
# After restore, verify data
psql -h db-host -U vmeta_user -d ppl_meta_vmeta_prod \
  -c "SELECT COUNT(*) FROM batch_processing_state;"

# Restart vmeta
kubectl scale deployment ppl-meta-vmeta --replicas=2
```

**RPO**: 1 hour (database backup frequency)  
**RTO**: 2 hours (restore + verification)

---

### Scenario 2: Service Complete Failure

**Detection**: All health checks failing, service not responding

**Recovery Steps**:

1. **Check service status**:
```bash
kubectl get pods -n ppl-meta | grep vmeta
kubectl describe pod ppl-meta-vmeta-xxx
```

2. **Check logs for crash reason**:
```bash
kubectl logs ppl-meta-vmeta-xxx --previous
```

3. **Restart service**:
```bash
kubectl rollout restart deployment/ppl-meta-vmeta -n ppl-meta
```

4. **If restart fails**, rollback to previous version:
```bash
kubectl rollout undo deployment/ppl-meta-vmeta -n ppl-meta
```

5. **Verify recovery**:
```bash
curl https://vmeta.ppl-meta.com/health
```

**RTO**: 15 minutes (restart + verification)

---

## Maintenance Procedures

### Rolling Restart (Zero Downtime)

```bash
# Scale up for redundancy
kubectl scale deployment ppl-meta-vmeta --replicas=3 -n ppl-meta

# Perform rolling restart
kubectl rollout restart deployment/ppl-meta-vmeta -n ppl-meta

# Monitor rollout
kubectl rollout status deployment/ppl-meta-vmeta -n ppl-meta

# Scale back to normal
kubectl scale deployment ppl-meta-vmeta --replicas=2 -n ppl-meta
```

### Database Migration

```bash
# 1. Create backup
pg_dump -h db-host -U vmeta_user ppl_meta_vmeta_prod > backup.sql

# 2. Test migration in staging
psql -h staging-db -U vmeta_user ppl_meta_vmeta_staging < migration.sql

# 3. Schedule maintenance window
# 4. Run migration in production
psql -h db-host -U vmeta_user ppl_meta_vmeta_prod < migration.sql

# 5. Verify migration
psql -h db-host -U vmeta_user -d ppl_meta_vmeta_prod \
  -c "\dt batch_*"

# 6. Restart service to pick up schema changes
kubectl rollout restart deployment/ppl-meta-vmeta
```

---

## FAQ

**Q: How do I manually trigger a batch?**

A: Use the API endpoint:
```bash
curl -X POST https://vmeta.ppl-meta.com/api/v1/batch-processing/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "collection_id": "<collection-id>",
    "force_trigger": true,
    "min_videos": 1
  }'
```

**Q: Can I change batch size for a specific collection?**

A: Yes:
```bash
curl -X PUT https://vmeta.ppl-meta.com/api/v1/batch-processing/batch-size \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "batch_size": 10,
    "collection_id": "<collection-id>"
  }'
```

**Q: How do I disable batch processing temporarily?**

A: Update feature flag:
```sql
UPDATE feature_flags
SET strategy = 'disabled'
WHERE feature_name = 'batch_processing_enabled';
```

**Q: Where are the logs?**

A: 
- **Kubernetes**: `kubectl logs deployment/ppl-meta-vmeta -n ppl-meta`
- **File**: `/app/logs/vmeta.log` (inside container)
- **Centralized**: Grafana Loki or ELK stack

**Q: How do I check cache effectiveness?**

A: Query Prometheus:
```
avg(cache_hit_rate{cache_level="individual"})
```

Or API:
```bash
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/health | jq '.cache'
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-13 | Platform Team | Initial version |

---

**Questions?** Contact platform@ppl-meta.internal or #platform-team on Slack
