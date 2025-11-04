# MVR-People Deployment Guide

**PPL Meta Platform - vmeta Service**  
**Feature:** Machine Vision Representation - People (MVR-People)  
**Version:** 1.0.0  
**Date:** November 1, 2025  
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Database Migration](#database-migration)
5. [Service Configuration](#service-configuration)
6. [Deployment Steps](#deployment-steps)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Rollback Procedures](#rollback-procedures)
9. [Testing Checklist](#testing-checklist)
10. [Troubleshooting](#troubleshooting)

---

## Overview

### What is MVR-People?

MVR-People is a machine learning-powered system that creates persistent, deduplicated representations of people detected across multiple videos. It combines face embeddings, demographic estimates, and quality scoring to enable:

- **Cross-video person tracking** - Link the same person across different videos
- **Automatic deduplication** - Merge duplicate detections into single identity
- **Similarity search** - Find similar people using pgvector face embeddings
- **Demographic analytics** - Age and gender estimation
- **Quality optimization** - Always use the best quality face representation

### Key Features

✅ **512-dimensional face embeddings** using FaceNet  
✅ **Age estimation** with ±5 year tolerance  
✅ **Gender classification** with 0.6 confidence threshold  
✅ **pgvector similarity search** for efficient matching  
✅ **Automatic background processing** with retry logic  
✅ **RESTful API** with 14 endpoints and JWT authentication  
✅ **Merge audit trail** for compliance and debugging  
✅ **Non-blocking integration** with Individual workflow

### Components Deployed

| Component | Type | Lines of Code | Purpose |
|-----------|------|---------------|---------|
| Database Schema | PostgreSQL + pgvector | ~500 | 4 tables, 28 indexes |
| ML Models | Python | ~400 | FaceNet, Age, Gender |
| Repository Layer | Python | ~1,000 | Database operations |
| Service Layer | Python | ~2,200 | Business logic |
| Background Processor | Python | ~1,100 | Async task queue |
| REST API | FastAPI | ~2,500 | 14 endpoints |
| Tests | pytest | ~2,300 | 28+ test cases |
| **Total** | | **~9,000** | Complete system |

---

## Prerequisites

### Infrastructure Requirements

**Database:**
- PostgreSQL 14.18+ with pgvector extension
- Minimum 4GB RAM allocated to PostgreSQL
- SSD storage recommended for vector operations
- Database backups configured

**Compute:**
- Python 3.11+
- Minimum 8GB RAM for ML models (FaceNet, Age, Gender)
- 4+ CPU cores recommended
- GPU optional (CPU inference works fine)

**Storage:**
- Minimum 50GB free space for ML models and face crops
- SSD recommended for database and model storage

**Network:**
- Access to Orchestrator service (port 8002)
- Access to Gateway service (port 8080)
- Access to Node service (port 8001) for authentication

### Software Dependencies

**Python Packages:**
```bash
# Core dependencies (already in requirements.txt)
asyncpg>=0.29.0          # Async PostgreSQL
psycopg2-binary>=2.9.9   # PostgreSQL adapter
fastapi>=0.104.1         # REST API framework
uvicorn>=0.24.0          # ASGI server
pydantic>=2.5.0          # Data validation
httpx>=0.25.1            # HTTP client
numpy>=1.26.2            # Numerical operations
pyjwt>=2.8.0             # JWT authentication

# ML models (specific versions)
facenet-pytorch==2.5.3   # Face embeddings
torch>=2.1.0             # PyTorch
torchvision>=0.16.0      # Vision models
```

**Database Extensions:**
```sql
-- Must be installed before migration
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
```

### Service Dependencies

The MVR-People system requires these services to be running:

1. **PostgreSQL Database** - Storage for MVR-People records
2. **Orchestrator Service** - Provides person objects and appearances
3. **Node Service** - JWT authentication
4. **Gateway Service** - Optional (for proxied access)

---

## Architecture

### System Flow

```
┌─────────────┐
│   Camera    │ Records video → Detects people
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Individual Creation (database/repository.py) │
│                                              │
│  ✅ NEW: MVR-People Creation Trigger Added  │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Background Processing (MVRBackgroundProcessor)│
│                                              │
│  • Fetch person objects from Orchestrator   │
│  • Select best quality face                 │
│  • Extract 512D face embedding (FaceNet)    │
│  • Estimate age and gender                  │
│  • Store in mvr_people table                │
│  • Create mapping to Individual             │
└──────┬──────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────┐
│ Matching & Merging (MVRMatcher)             │
│                                              │
│  • Find similar MVR using pgvector          │
│  • Compare quality scores                   │
│  • Auto-merge duplicates if threshold met   │
│  • Create audit log entry                   │
└─────────────────────────────────────────────┘
```

### Database Schema

**Tables Created:**
1. `mvr_people` - Core MVR-People records with face embeddings
2. `individual_mvr_mapping` - Links Individuals to MVR-People
3. `mvr_merge_audit_log` - Tracks merge operations
4. `mvr_matching_config` - Configurable matching thresholds

**Indexes Created:** 28 total
- Primary keys and foreign keys
- **pgvector GIN index** on `face_embedding` for similarity search
- Composite indexes for common queries
- Partial indexes for active (non-orphaned) MVR

### API Endpoints

**Base URL:** `http://localhost:8008/api/v1/mvr-people`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/individuals/{uuid}/create` | Create MVR-People |
| GET | `/individuals/{uuid}` | Get MVR for Individual |
| GET | `/{uuid}` | Get MVR by UUID |
| POST | `/search/similar` | Similarity search |
| POST | `/search/demographics` | Search by age/gender |
| POST | `/{uuid}/link-individual` | Link Individual |
| POST | `/batch/create` | Batch creation |
| GET | `/{uuid}/status` | Processing status |
| POST | `/individuals/{uuid}/match` | Match Individuals |
| POST | `/merge` | Merge Individuals |
| GET | `/individuals/{uuid}/merge-history` | Merge history |
| GET | `/orphaned` | Get orphaned MVR |
| PUT | `/config/matching` | Update config |
| GET | `/config/matching` | Get config |

---

## Database Migration

### Step 1: Backup Database

**CRITICAL:** Always backup before migration!

```bash
# Create full database backup
pg_dump -U postgres -d ppl_meta -F c -f ppl_meta_backup_$(date +%Y%m%d_%H%M%S).dump

# Verify backup
pg_restore --list ppl_meta_backup_*.dump | head -20
```

### Step 2: Verify pgvector Extension

```sql
-- Connect to database
psql -U postgres -d ppl_meta

-- Check if pgvector is installed
SELECT * FROM pg_extension WHERE extname = 'pgvector';

-- If not installed, install it
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify version (should be 0.5.0+)
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

### Step 3: Run Migration Script

The migration script is located at: `ppl-meta-vmeta/migrations/001_mvr_people_schema.sql`

```bash
# Review migration script first
cat ppl-meta-vmeta/migrations/001_mvr_people_schema.sql

# Run migration
psql -U postgres -d ppl_meta -f ppl-meta-vmeta/migrations/001_mvr_people_schema.sql

# Verify tables created
psql -U postgres -d ppl_meta -c "\dt mvr*"

# Verify indexes created
psql -U postgres -d ppl_meta -c "\di mvr*"
```

**Expected Output:**
```
                    List of relations
 Schema |           Name            | Type  |  Owner   
--------+---------------------------+-------+----------
 public | mvr_matching_config       | table | postgres
 public | mvr_merge_audit_log       | table | postgres
 public | mvr_people                | table | postgres
 public | individual_mvr_mapping    | table | postgres

Indexes:
- idx_mvr_people_embedding_vector (GIN index for similarity search)
- idx_mvr_people_quality_active
- idx_mvr_mapping_individual
- ... (25+ more indexes)
```

### Step 4: Insert Default Configuration

```sql
-- Insert default matching configuration
INSERT INTO mvr_matching_config (
    config_uuid,
    similarity_threshold,
    quality_weight,
    age_tolerance,
    gender_match_required,
    auto_merge_enabled,
    created_at,
    updated_at
) VALUES (
    gen_random_uuid(),
    0.85,           -- 85% similarity threshold
    0.3,            -- 30% weight to quality score
    5,              -- ±5 years age tolerance
    false,          -- Don't require gender match
    true,           -- Enable auto-merge
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP
);

-- Verify configuration
SELECT * FROM mvr_matching_config;
```

---

## Service Configuration

### Step 1: Environment Variables

Create `.env` file in `ppl-meta-vmeta/`:

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=ppl_meta
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=50

# Service Configuration
VMETA_HOST=0.0.0.0
VMETA_PORT=8008
VMETA_ENVIRONMENT=production
VMETA_LOG_LEVEL=INFO

# ML Model Configuration
FACENET_MODEL_PATH=/path/to/models/facenet
AGE_MODEL_PATH=/path/to/models/age
GENDER_MODEL_PATH=/path/to/models/gender
ML_DEVICE=cpu  # or 'cuda' for GPU

# Orchestrator Integration
ORCHESTRATOR_BASE_URL=http://localhost:8002
ORCHESTRATOR_TIMEOUT=30

# JWT Authentication
JWT_SECRET_KEY=your-secure-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Background Processing
MVR_BACKGROUND_ENABLED=true
MVR_MAX_RETRIES=3
MVR_RETRY_DELAY=5
MVR_WORKER_THREADS=4

# Matching Configuration
MVR_SIMILARITY_THRESHOLD=0.85
MVR_AUTO_MERGE_ENABLED=true
MVR_QUALITY_WEIGHT=0.3
MVR_AGE_TOLERANCE=5

# Monitoring
METRICS_ENABLED=true
METRICS_PORT=9090
```

### Step 2: Update main.py

The MVR-People router is already integrated in `main.py`:

```python
# MVR-People API router (Phase 4 - Already added)
try:
    from api.routes.mvr_people import router as mvr_people_router
    app.include_router(
        mvr_people_router,
        tags=["mvr-people"]
    )
    logger.info("✅ MVR-People API router added successfully (14 endpoints)")
except ImportError as e:
    logger.warning(f"⚠️ MVR-People API router not available: {e}")
except Exception as e:
    logger.error(f"❌ Error adding MVR-People API router: {e}")
```

### Step 3: Install ML Models

```bash
# Download FaceNet model (if not already downloaded)
cd ppl-meta-vmeta
mkdir -p models/facenet
# FaceNet model downloads automatically on first use via facenet-pytorch

# Verify models can be loaded
python -c "from ml.facenet_processor import FaceNetProcessor; p = FaceNetProcessor(); print('FaceNet OK')"
python -c "from ml.age_estimator import AgeEstimator; a = AgeEstimator(); print('Age OK')"
python -c "from ml.gender_classifier import GenderClassifier; g = GenderClassifier(); print('Gender OK')"
```

---

## Deployment Steps

### Development Environment

```bash
# 1. Navigate to vmeta directory
cd ppl-meta-vmeta

# 2. Activate virtual environment
source venv/bin/activate

# 3. Install dependencies (if not already installed)
pip install -r requirements.txt
pip install pyjwt  # JWT authentication

# 4. Verify database migration
psql -U postgres -d ppl_meta -c "SELECT COUNT(*) FROM mvr_people;"

# 5. Start vmeta service
cd src
PYTHONPATH=/Users/nickgklezakos/Documents/ppl-meta-code/ppl-meta-vmeta/src \
  uvicorn main:app --host 0.0.0.0 --port 8008 --reload

# 6. Verify service health
curl http://localhost:8008/health | jq
```

**Expected Output:**
```json
{
  "status": "healthy",
  "service": "vmeta",
  "version": "1.0.0",
  "description": "Vector-based facial embeddings and analytics",
  "mvr_people_enabled": true,
  "ml_models_loaded": true
}
```

### Production Environment

```bash
# 1. Use production ASGI server (gunicorn + uvicorn workers)
pip install gunicorn

# 2. Start with multiple workers
cd ppl-meta-vmeta/src
gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8008 \
  --timeout 120 \
  --access-logfile /var/log/vmeta/access.log \
  --error-logfile /var/log/vmeta/error.log \
  --log-level info

# 3. Or use systemd service (recommended)
sudo systemctl start vmeta
sudo systemctl enable vmeta
sudo systemctl status vmeta
```

**systemd service file** (`/etc/systemd/system/vmeta.service`):

```ini
[Unit]
Description=PPL Meta vmeta Service
After=network.target postgresql.service

[Service]
Type=notify
User=ppl-meta
Group=ppl-meta
WorkingDirectory=/opt/ppl-meta/ppl-meta-vmeta/src
Environment="PATH=/opt/ppl-meta/ppl-meta-vmeta/venv/bin"
Environment="PYTHONPATH=/opt/ppl-meta/ppl-meta-vmeta/src"
ExecStart=/opt/ppl-meta/ppl-meta-vmeta/venv/bin/gunicorn main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8008 \
  --timeout 120 \
  --access-logfile /var/log/vmeta/access.log \
  --error-logfile /var/log/vmeta/error.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Monitoring & Health Checks

### Health Check Endpoint

```bash
# Basic health check
curl http://localhost:8008/health

# Detailed MVR-People stats
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8008/api/v1/mvr-people/config/matching
```

### Key Metrics to Monitor

**1. Database Metrics:**
```sql
-- Total MVR-People count
SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = FALSE;

-- Average quality score
SELECT AVG(quality_score) FROM mvr_people WHERE is_orphaned = FALSE;

-- Individuals with MVR mappings
SELECT COUNT(DISTINCT individual_uuid) FROM individual_mvr_mapping;

-- Merge activity
SELECT COUNT(*) FROM mvr_merge_audit_log 
WHERE merge_timestamp > NOW() - INTERVAL '24 hours';

-- Orphaned MVR count
SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = TRUE;
```

**2. Background Processing:**
```sql
-- Pending MVR creation tasks
SELECT COUNT(*) FROM mvr_background_tasks 
WHERE status = 'pending';

-- Failed tasks in last 24h
SELECT COUNT(*) FROM mvr_background_tasks 
WHERE status = 'failed' 
AND created_at > NOW() - INTERVAL '24 hours';
```

**3. API Performance:**
```bash
# Response time for similarity search
time curl -s -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"face_embedding": [...], "threshold": 0.85}' \
  http://localhost:8008/api/v1/mvr-people/search/similar
```

### Prometheus Metrics (Future Enhancement)

Add these custom metrics to monitor MVR-People:

- `mvr_people_total` - Total active MVR-People
- `mvr_people_created_total` - Counter of MVR creations
- `mvr_people_merged_total` - Counter of merge operations
- `mvr_similarity_search_duration_seconds` - Histogram of search times
- `mvr_background_queue_size` - Gauge of pending tasks
- `mvr_ml_inference_duration_seconds` - Histogram of ML processing time

### Grafana Dashboard

Recommended panels:
1. **MVR-People Growth** - Line chart of total MVR over time
2. **Quality Distribution** - Histogram of quality scores
3. **Merge Activity** - Bar chart of daily merges
4. **Search Performance** - P50/P95/P99 latency
5. **Background Queue** - Pending vs processed tasks
6. **Error Rate** - Failed operations per hour

---

## Rollback Procedures

### Database Rollback

If migration causes issues, rollback using this script:

```sql
-- Save this as rollback_mvr_people.sql
BEGIN;

-- Drop tables in reverse order (handle FK constraints)
DROP TABLE IF EXISTS mvr_merge_audit_log CASCADE;
DROP TABLE IF EXISTS individual_mvr_mapping CASCADE;
DROP TABLE IF EXISTS mvr_people CASCADE;
DROP TABLE IF EXISTS mvr_matching_config CASCADE;

COMMIT;
```

**Execute rollback:**
```bash
# Rollback database changes
psql -U postgres -d ppl_meta -f rollback_mvr_people.sql

# Restore from backup
pg_restore -U postgres -d ppl_meta -c ppl_meta_backup_*.dump
```

### Code Rollback

Remove MVR-People integration hook from `database/repository.py`:

```python
# Remove this block from create_individual() method:
# Trigger MVR-People creation (Phase 5 Integration)
try:
    from background.mvr_helper import trigger_mvr_creation
    await trigger_mvr_creation(individual_uuid)
    logger.info(f"🧬 Triggered MVR-People creation for Individual {individual_uuid}")
except Exception as mvr_error:
    logger.warning(f"⚠️ MVR-People creation trigger failed for {individual_uuid}: {mvr_error}")
```

### Service Rollback

```bash
# Stop vmeta service
sudo systemctl stop vmeta

# Switch to previous commit
cd ppl-meta-vmeta
git checkout <previous-commit-hash>

# Restart service
sudo systemctl start vmeta
```

---

## Testing Checklist

### Pre-Deployment Tests

- [ ] **Database Migration**
  - [ ] Migration script runs without errors
  - [ ] All 4 tables created
  - [ ] All 28 indexes created
  - [ ] pgvector extension loaded
  - [ ] Default configuration inserted

- [ ] **Service Startup**
  - [ ] vmeta service starts without errors
  - [ ] Health endpoint returns `healthy`
  - [ ] All ML models load successfully
  - [ ] 14 API endpoints registered

- [ ] **Integration Tests**
  - [ ] Run `test_integration_phase5.py` - all pass
  - [ ] Run `test_mvr_with_real_data.py` - validates real data
  - [ ] Background processor initializes
  - [ ] Database connections healthy

### Post-Deployment Smoke Tests

```bash
# 1. Health check
curl http://localhost:8008/health | jq '.status'
# Expected: "healthy"

# 2. Get JWT token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  jq -r '.access_token')

# 3. Get matching configuration
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8008/api/v1/mvr-people/config/matching | jq

# 4. Check database stats
psql -U postgres -d ppl_meta -c "
  SELECT 
    (SELECT COUNT(*) FROM mvr_people) as total_mvr,
    (SELECT COUNT(*) FROM individual_mvr_mapping) as total_mappings,
    (SELECT AVG(quality_score) FROM mvr_people WHERE is_orphaned = FALSE) as avg_quality;
"

# 5. Test MVR creation (optional - creates real MVR)
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  http://localhost:8008/api/v1/mvr-people/individuals/<individual-uuid>/create | jq
```

### Continuous Monitoring (First 24 Hours)

- [ ] Monitor error logs: `tail -f /var/log/vmeta/error.log`
- [ ] Check database growth: Query `mvr_people` count every hour
- [ ] Monitor background queue: Check pending tasks
- [ ] Verify auto-creation: New Individuals should trigger MVR creation
- [ ] Check merge activity: Monitor `mvr_merge_audit_log`

---

## Troubleshooting

### Issue: Service Won't Start

**Symptoms:** vmeta service fails to start

**Diagnosis:**
```bash
# Check service logs
journalctl -u vmeta -n 50 -f

# Check if port 8008 is in use
lsof -i :8008

# Verify Python environment
source venv/bin/activate
python -c "import fastapi; import asyncpg; print('OK')"
```

**Solutions:**
- Kill process using port 8008: `kill -9 $(lsof -t -i:8008)`
- Reinstall dependencies: `pip install -r requirements.txt`
- Check database connection: `psql -U postgres -d ppl_meta`

### Issue: pgvector Extension Missing

**Symptoms:** Migration fails with "type vector does not exist"

**Diagnosis:**
```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

**Solutions:**
```bash
# Install pgvector (Ubuntu/Debian)
sudo apt-get install postgresql-14-pgvector

# Install pgvector (macOS)
brew install pgvector

# Then restart PostgreSQL
sudo systemctl restart postgresql
```

### Issue: MVR Creation Failing

**Symptoms:** Background processor shows errors, MVR not being created

**Diagnosis:**
```sql
-- Check failed tasks
SELECT * FROM mvr_background_tasks 
WHERE status = 'failed' 
ORDER BY created_at DESC 
LIMIT 5;

-- Check error messages
SELECT error_message FROM mvr_background_tasks 
WHERE status = 'failed';
```

**Solutions:**
- Verify Orchestrator service is running: `curl http://localhost:8002/health`
- Check person objects exist: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8002/person-objects/{video_uuid}`
- Verify ML models loaded: Check vmeta service logs
- Increase retry count in configuration

### Issue: Similarity Search Slow

**Symptoms:** `/search/similar` endpoint takes >5 seconds

**Diagnosis:**
```sql
-- Check if GIN index exists
\d mvr_people

-- Check index usage
EXPLAIN ANALYZE 
SELECT * FROM mvr_people 
ORDER BY face_embedding <-> '[0,0,...]'::vector 
LIMIT 10;
```

**Solutions:**
```sql
-- Rebuild index if needed
REINDEX INDEX idx_mvr_people_embedding_vector;

-- Increase shared_buffers in postgresql.conf
shared_buffers = 4GB

-- Vacuum analyze
VACUUM ANALYZE mvr_people;
```

### Issue: Memory Usage High

**Symptoms:** vmeta service using >4GB RAM

**Diagnosis:**
```bash
# Check process memory
ps aux | grep uvicorn | awk '{print $6}'

# Check Python object count
python -c "import gc; print(len(gc.get_objects()))"
```

**Solutions:**
- Reduce worker count in gunicorn configuration
- Add memory limits to systemd service: `MemoryMax=4G`
- Implement model caching instead of loading per request
- Use CPU inference instead of GPU if GPU memory limited

---

## Success Criteria

### Deployment Considered Successful When:

1. ✅ **Service Health**
   - vmeta service running and healthy
   - Health endpoint returns 200 OK
   - All 14 API endpoints accessible

2. ✅ **Database Migration**
   - All 4 tables created
   - All 28 indexes created
   - pgvector extension working
   - Default configuration present

3. ✅ **Integration Working**
   - New Individuals trigger MVR creation
   - Background processor running
   - Person objects fetched successfully

4. ✅ **Core Functionality**
   - MVR-People can be created
   - Similarity search returns results <2s
   - Matching algorithm finds duplicates
   - Merge operations complete successfully

5. ✅ **Monitoring Active**
   - Error logs being written
   - Database stats queryable
   - Health checks passing

---

## Support & Contacts

**Documentation:**
- This guide: `docs/vision-vmeta/MVR_PEOPLE_DEPLOYMENT_GUIDE.md`
- API Reference: `docs/vision-vmeta/VISION_SERVICE_ENDPOINTS_REFERENCE.md`
- Architecture: `docs/vision-vmeta/MVR_PEOPLE_ARCHITECTURE.md`

**Code Locations:**
- Database: `ppl-meta-vmeta/migrations/`
- Service: `ppl-meta-vmeta/src/`
- Tests: `ppl-meta-vmeta/src/tests/`
- API: `ppl-meta-vmeta/src/api/routes/mvr_people.py`

**Logs:**
- Service: `/var/log/vmeta/`
- PostgreSQL: `/var/log/postgresql/`
- System: `journalctl -u vmeta`

---

## Appendix A: Quick Reference Commands

```bash
# Start vmeta service
cd ppl-meta-vmeta/src
source ../venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8008

# Check service health
curl http://localhost:8008/health

# Get auth token
TOKEN=$(curl -s -X POST 'http://localhost:8001/api/v1/users/login' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=fresh.user@example.com&password=NewPassword234!' | \
  jq -r '.access_token')

# Database stats
psql -U postgres -d ppl_meta -c "
  SELECT COUNT(*) FROM mvr_people;
  SELECT AVG(quality_score) FROM mvr_people;
"

# View recent MVR creations
psql -U postgres -d ppl_meta -c "
  SELECT mvr_people_uuid, quality_score, created_at 
  FROM mvr_people 
  ORDER BY created_at DESC 
  LIMIT 5;
"

# Check background queue
psql -U postgres -d ppl_meta -c "
  SELECT status, COUNT(*) 
  FROM mvr_background_tasks 
  GROUP BY status;
"

# Monitor logs
tail -f /var/log/vmeta/error.log
journalctl -u vmeta -f
```

---

**Document Version:** 1.0.0  
**Last Updated:** November 1, 2025  
**Deployment Status:** ✅ Production Ready  
**Maintained by:** PPL Meta Platform Team
