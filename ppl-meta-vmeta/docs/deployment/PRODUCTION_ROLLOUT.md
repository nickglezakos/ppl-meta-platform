# Production Deployment with Gradual Rollout
# PPL Meta Platform - vmeta Service
# Continuous Individuals and MVR Pipeline

## Overview

This guide covers production deployment with feature flags and gradual rollout strategy. The deployment will start with a single collection (pilot), monitor for 48 hours, then gradually expand to all collections with validation at each stage.

## Deployment Strategy

### Phase 1: Feature Flag Implementation
### Phase 2: Single Collection Pilot (48 hours)
### Phase 3: Limited Rollout (20% collections, 7 days)
### Phase 4: Expanded Rollout (50% collections, 7 days)
### Phase 5: Full Rollout (100% collections)

## Phase 1: Feature Flag Implementation

### 1.1 Feature Flag Service

Create `src/services/feature_flags.py`:

```python
"""
Feature flag service for gradual rollout control.
"""

from typing import Dict, List, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FeatureFlag(Enum):
    """Feature flags for batch processing."""
    BATCH_PROCESSING_ENABLED = "batch_processing_enabled"
    HYBRID_TRIGGER_ENABLED = "hybrid_trigger_enabled"
    TWO_LEVEL_CACHE_ENABLED = "two_level_cache_enabled"


class RolloutStrategy(Enum):
    """Rollout strategies."""
    DISABLED = "disabled"
    PILOT = "pilot"          # Single collection
    LIMITED = "limited"      # 20% of collections
    EXPANDED = "expanded"    # 50% of collections
    FULL = "full"           # 100% of collections


class FeatureFlagService:
    """Manage feature flags for gradual rollout."""
    
    def __init__(self, db_pool):
        self.db_pool = db_pool
        self._cache = {}
    
    async def is_enabled(
        self,
        feature: FeatureFlag,
        collection_id: str
    ) -> bool:
        """Check if feature is enabled for collection."""
        
        # Get rollout configuration
        config = await self._get_rollout_config(feature)
        
        if config['strategy'] == RolloutStrategy.DISABLED.value:
            return False
        
        if config['strategy'] == RolloutStrategy.FULL.value:
            return True
        
        if config['strategy'] == RolloutStrategy.PILOT.value:
            # Only pilot collections
            return collection_id in config['pilot_collections']
        
        if config['strategy'] in [RolloutStrategy.LIMITED.value, RolloutStrategy.EXPANDED.value]:
            # Pilot + percentage rollout
            if collection_id in config['pilot_collections']:
                return True
            
            # Hash-based consistent rollout
            rollout_percentage = config['rollout_percentage']
            return self._is_in_rollout(collection_id, rollout_percentage)
        
        return False
    
    async def _get_rollout_config(self, feature: FeatureFlag) -> Dict:
        """Get rollout configuration from database."""
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT
                    strategy,
                    pilot_collections,
                    rollout_percentage,
                    enabled_at
                FROM feature_flags
                WHERE feature_name = $1
                """,
                feature.value
            )
            
            if not row:
                # Default: disabled
                return {
                    'strategy': RolloutStrategy.DISABLED.value,
                    'pilot_collections': [],
                    'rollout_percentage': 0
                }
            
            return {
                'strategy': row['strategy'],
                'pilot_collections': row['pilot_collections'] or [],
                'rollout_percentage': row['rollout_percentage'] or 0
            }
    
    def _is_in_rollout(self, collection_id: str, percentage: int) -> bool:
        """Determine if collection is in rollout based on hash."""
        
        # Consistent hash-based rollout
        hash_value = hash(collection_id) % 100
        return hash_value < percentage
    
    async def set_strategy(
        self,
        feature: FeatureFlag,
        strategy: RolloutStrategy,
        pilot_collections: Optional[List[str]] = None,
        rollout_percentage: Optional[int] = None
    ):
        """Update rollout strategy."""
        
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO feature_flags (
                    feature_name,
                    strategy,
                    pilot_collections,
                    rollout_percentage,
                    enabled_at
                ) VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (feature_name)
                DO UPDATE SET
                    strategy = $2,
                    pilot_collections = $3,
                    rollout_percentage = $4,
                    updated_at = NOW()
                """,
                feature.value,
                strategy.value,
                pilot_collections or [],
                rollout_percentage or 0
            )
        
        logger.info(
            f"Feature {feature.value} strategy updated to {strategy.value}"
        )
        
        # Clear cache
        self._cache = {}
```

### 1.2 Database Migration for Feature Flags

Create `migrations/010_feature_flags.sql`:

```sql
-- Feature flags table
CREATE TABLE feature_flags (
    id SERIAL PRIMARY KEY,
    feature_name VARCHAR(100) UNIQUE NOT NULL,
    strategy VARCHAR(50) NOT NULL DEFAULT 'disabled',
    pilot_collections TEXT[] DEFAULT '{}',
    rollout_percentage INTEGER DEFAULT 0,
    enabled_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT check_strategy CHECK (
        strategy IN ('disabled', 'pilot', 'limited', 'expanded', 'full')
    ),
    CONSTRAINT check_percentage CHECK (
        rollout_percentage >= 0 AND rollout_percentage <= 100
    )
);

-- Insert default features
INSERT INTO feature_flags (feature_name, strategy) VALUES
    ('batch_processing_enabled', 'disabled'),
    ('hybrid_trigger_enabled', 'disabled'),
    ('two_level_cache_enabled', 'disabled');

-- Index
CREATE INDEX idx_feature_flags_name ON feature_flags(feature_name);
```

### 1.3 Integrate Feature Flags into Services

Update `src/services/batch_monitor.py`:

```python
from src.services.feature_flags import FeatureFlagService, FeatureFlag

class BatchMonitor:
    def __init__(self, repository, config_service, feature_flags):
        self.repository = repository
        self.config_service = config_service
        self.feature_flags = feature_flags
    
    async def add_video_to_batch(self, collection_id, ...):
        """Add video to batch (with feature flag check)."""
        
        # Check if batch processing enabled for this collection
        if not await self.feature_flags.is_enabled(
            FeatureFlag.BATCH_PROCESSING_ENABLED,
            collection_id
        ):
            logger.info(
                f"Batch processing disabled for {collection_id}, skipping"
            )
            return
        
        # Proceed with normal batch processing
        ...
```

## Phase 2: Single Collection Pilot (48 hours)

### 2.1 Select Pilot Collection

Choose a low-risk collection for pilot:

```bash
# Recommended: Internal testing camera or low-traffic collection
PILOT_COLLECTION="security-camera-front-entrance"

# Criteria for pilot collection:
# - Low traffic (< 100 videos/day)
# - Non-critical use case
# - Easy to monitor
# - Can tolerate issues
```

### 2.2 Enable Feature Flag for Pilot

```bash
# Connect to production database
psql -h prod-db.ppl-meta.internal -U vmeta_user -d ppl_meta_vmeta_prod

# Enable batch processing for pilot collection
UPDATE feature_flags
SET
    strategy = 'pilot',
    pilot_collections = ARRAY['security-camera-front-entrance'],
    enabled_at = NOW()
WHERE feature_name = 'batch_processing_enabled';

# Verify
SELECT * FROM feature_flags WHERE feature_name = 'batch_processing_enabled';
```

Or via API:

```bash
curl -X POST https://vmeta.ppl-meta.com/api/v1/feature-flags/batch-processing \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "pilot",
    "pilot_collections": ["security-camera-front-entrance"]
  }'
```

### 2.3 Monitor Pilot (48 hours)

#### Monitoring Checklist

Create `monitoring/pilot-checklist.md`:

```markdown
# Pilot Monitoring Checklist - Day 1

## Every 4 Hours:

- [ ] Check Grafana dashboard for errors
- [ ] Review batch processing metrics
- [ ] Verify cache hit rates improving
- [ ] Check worker pool status
- [ ] Review application logs for errors
- [ ] Verify database connection pool healthy
- [ ] Check WebSocket connection status

## Metrics to Watch:

### Batch Processing
- Batches completed: Should be processing regularly
- Error rate: < 5%
- Processing time: < 60 seconds average
- Cache hit rate: Increasing (0% → 40%+)

### Worker Pool
- Active workers: 1-3 (depending on load)
- Idle workers: 0-2
- Queue size: < 5

### Database
- Connection pool: < 80% utilized
- Query latency: < 100ms P95
- No connection timeouts

### Alerts Fired
- Count: 0 critical alerts
- Review any warnings

## Issues Encountered:

| Time | Issue | Severity | Action Taken | Resolved |
|------|-------|----------|--------------|----------|
|      |       |          |              |          |

## Performance Summary:

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Avg Processing Time | < 60s | ___s | ✅ / ❌ |
| Error Rate | < 5% | ___% | ✅ / ❌ |
| Cache Hit Rate | > 20% | ___% | ✅ / ❌ |
| Batches Processed | > 0 | ___ | ✅ / ❌ |
```

#### Monitoring Commands

```bash
# Check pilot collection batch status
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/status?collection_id=security-camera-front-entrance \
  -H "Authorization: Bearer ${TOKEN}" | jq '.'

# Check batch history
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/history?collection_id=security-camera-front-entrance&limit=20 \
  -H "Authorization: Bearer ${TOKEN}" | jq '.'

# Check recent errors
curl https://vmeta.ppl-meta.com/api/v1/batch-processing/health \
  -H "Authorization: Bearer ${TOKEN}" | jq '.recent_failures'

# Query Prometheus for pilot metrics
curl -G https://prometheus.ppl-meta.com/api/v1/query \
  --data-urlencode 'query=rate(batch_processing_total{collection_id="security-camera-front-entrance"}[1h])'
```

### 2.4 Pilot Success Criteria

After 48 hours, verify:

- [ ] No critical incidents
- [ ] Error rate < 5%
- [ ] Processing time < 60s average
- [ ] Cache hit rate increasing
- [ ] No memory leaks (memory stable)
- [ ] No database connection issues
- [ ] All batches eventually complete
- [ ] Worker pool not exhausted
- [ ] Logs show no critical errors
- [ ] No user-reported issues

### 2.5 Pilot Go/No-Go Decision

**GO** - Proceed to Phase 3 if:
- All success criteria met
- No critical issues encountered
- Performance acceptable
- Team confident in stability

**NO-GO** - Rollback if:
- Critical errors occurred
- Performance unacceptable
- Data integrity issues
- Stability concerns

**Rollback Procedure**:

```bash
# Disable feature flag
UPDATE feature_flags
SET strategy = 'disabled'
WHERE feature_name = 'batch_processing_enabled';

# Verify disabled
SELECT * FROM feature_flags;

# Monitor for 1 hour to ensure rollback successful
```

## Phase 3: Limited Rollout (20% collections, 7 days)

### 3.1 Expand to 20% of Collections

```bash
# Keep pilot collection + add 20% rollout
UPDATE feature_flags
SET
    strategy = 'limited',
    pilot_collections = ARRAY['security-camera-front-entrance'],
    rollout_percentage = 20,
    updated_at = NOW()
WHERE feature_name = 'batch_processing_enabled';
```

This will enable batch processing for:
- Pilot collection (always enabled)
- 20% of other collections (consistent hash)

### 3.2 Monitor Limited Rollout

#### Daily Monitoring (7 days)

```bash
# Daily metrics check
./scripts/rollout-daily-check.sh

# Example script:
#!/bin/bash
echo "📊 Daily Rollout Metrics - $(date)"
echo "=================================="

# Count collections with feature enabled
TOTAL_COLLECTIONS=$(curl -s https://vmeta.ppl-meta.com/api/v1/collections | jq '. | length')
ENABLED_COUNT=$(curl -s https://prometheus.ppl-meta.com/api/v1/query \
  --data-urlencode 'query=count(batch_processing_total)' | jq -r '.data.result[0].value[1]')

echo "Collections with batch processing: $ENABLED_COUNT / $TOTAL_COLLECTIONS"

# Error rate
ERROR_RATE=$(curl -s https://prometheus.ppl-meta.com/api/v1/query \
  --data-urlencode 'query=rate(batch_processing_total{status="failed"}[24h]) / rate(batch_processing_total[24h])' \
  | jq -r '.data.result[0].value[1]')

echo "24h Error Rate: $(echo "$ERROR_RATE * 100" | bc)%"

# Processing time P95
P95_TIME=$(curl -s https://prometheus.ppl-meta.com/api/v1/query \
  --data-urlencode 'query=histogram_quantile(0.95, rate(batch_processing_duration_seconds_bucket[24h]))' \
  | jq -r '.data.result[0].value[1]')

echo "P95 Processing Time: ${P95_TIME}s"

# Cache hit rate
CACHE_RATE=$(curl -s https://prometheus.ppl-meta.com/api/v1/query \
  --data-urlencode 'query=avg(cache_hit_rate)' \
  | jq -r '.data.result[0].value[1]')

echo "Avg Cache Hit Rate: ${CACHE_RATE}%"
```

### 3.3 Limited Rollout Success Criteria

After 7 days:

- [ ] Error rate < 5% across all enabled collections
- [ ] No increase in user-reported issues
- [ ] Performance remains acceptable
- [ ] No resource exhaustion
- [ ] All alerts within acceptable thresholds
- [ ] Database performance stable
- [ ] Memory usage stable

## Phase 4: Expanded Rollout (50% collections, 7 days)

### 4.1 Expand to 50%

```bash
UPDATE feature_flags
SET
    strategy = 'expanded',
    rollout_percentage = 50,
    updated_at = NOW()
WHERE feature_name = 'batch_processing_enabled';
```

### 4.2 Monitor Expanded Rollout

Same monitoring as Phase 3, but watch for:
- Increased load on worker pool
- Database connection pool utilization
- Memory usage trends
- Error patterns across more collections

### 4.3 Expanded Rollout Success Criteria

After 7 days:

- [ ] All Phase 3 criteria still met
- [ ] System handles increased load
- [ ] Worker pool scaling effective
- [ ] No performance degradation
- [ ] Cache effectiveness maintained

## Phase 5: Full Rollout (100% collections)

### 5.1 Enable for All Collections

```bash
UPDATE feature_flags
SET
    strategy = 'full',
    rollout_percentage = 100,
    updated_at = NOW()
WHERE feature_name = 'batch_processing_enabled';
```

### 5.2 Monitor Full Rollout

First 48 hours: intensive monitoring
- Check metrics every 2 hours
- Review all alerts
- Watch for any anomalies

After 7 days: standard monitoring

### 5.3 Full Rollout Success Criteria

After 14 days:

- [ ] All previous criteria met
- [ ] System stable at full load
- [ ] No critical incidents
- [ ] User satisfaction maintained
- [ ] Performance targets met

## Rollback Procedures

### Emergency Rollback (Critical Issue)

```bash
# Immediate disable
UPDATE feature_flags
SET strategy = 'disabled'
WHERE feature_name = 'batch_processing_enabled';

# Alert team
./scripts/send-alert.sh "EMERGENCY ROLLBACK: Batch processing disabled due to critical issue"

# Monitor for 1 hour
```

### Partial Rollback (Non-Critical)

```bash
# Roll back to previous phase
UPDATE feature_flags
SET
    strategy = 'limited',  # or 'pilot'
    rollout_percentage = 20
WHERE feature_name = 'batch_processing_enabled';
```

### Collection-Specific Disable

```bash
# Disable for specific collection
./scripts/disable-collection.sh security-camera-back-entrance

# Or via API
curl -X POST https://vmeta.ppl-meta.com/api/v1/feature-flags/batch-processing/disable-collection \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  -d '{"collection_id": "security-camera-back-entrance"}'
```

## Rollout Timeline

| Phase | Duration | Collections | Monitoring Frequency | Go/No-Go |
|-------|----------|-------------|---------------------|----------|
| 1. Feature Flags | 2 days | 0 | N/A | Code review |
| 2. Pilot | 48 hours | 1 | Every 4 hours | After 48h |
| 3. Limited | 7 days | ~20% | Daily | After 7 days |
| 4. Expanded | 7 days | ~50% | Daily | After 7 days |
| 5. Full | 14+ days | 100% | Standard | After 14 days |

**Total Timeline**: ~30 days from start to full rollout

## Communication Plan

### Pre-Rollout
- Announce to engineering team
- Brief operations team
- Update on-call runbook
- Prepare user communications

### During Rollout
- Daily status updates to team
- Weekly stakeholder summary
- Immediate notification of critical issues

### Post-Rollout
- Completion announcement
- Lessons learned document
- Update documentation
- Celebrate success! 🎉

## Success Metrics

Final success criteria after full rollout:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Batch Processing Time | < 60s P95 | Prometheus |
| Error Rate | < 2% | Prometheus |
| Cache Hit Rate | > 40% | Prometheus |
| Worker Pool Utilization | < 80% | Grafana |
| User-Reported Issues | 0 critical | Support tickets |
| System Uptime | > 99.9% | Monitoring |
| Database Performance | No degradation | Database metrics |

## Contact

For rollout questions or issues:
- Rollout Lead: [rollout-lead@ppl-meta.internal]
- Platform Team: [platform@ppl-meta.internal]
- On-Call: [Use PagerDuty]
