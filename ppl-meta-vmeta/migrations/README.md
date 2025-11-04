# MVR-People Database Migrations

This directory contains database migration scripts for the MVR-People (Machine Vision Representation) system.

## Migration Files

### Forward Migration
**File:** `001_mvr_people_schema.sql`  
**Purpose:** Creates MVR-People schema (tables, indexes, constraints)  
**Tables Created:**
- `mvr_people` - Core MVR records with face embeddings
- `individual_mvr_mapping` - Links Individuals to their MVR
- `mvr_merge_audit_log` - Tracks merge operations
- `mvr_matching_config` - Configuration for matching algorithms

**Indexes Created:** 14 total (including pgvector similarity index)

### Rollback Migration
**File:** `002_mvr_people_rollback.sql`  
**Purpose:** Safely removes MVR-People schema  
**What It Does:**
- Drops all 4 MVR tables
- Removes all 14 indexes
- Removes foreign key constraints
- Preserves Individuals and other core data

## Prerequisites

Before running migrations:

1. **PostgreSQL Version:** 14.18 or higher
2. **Extensions Required:**
   - `uuid-ossp` (for UUID generation)
   - `pgvector` (for face embedding similarity search)
3. **Database Access:** 
   - User with CREATE TABLE privileges
   - User with CREATE INDEX privileges
4. **Backup:** Always create a backup before migration!

## Installation

### Step 1: Install pgvector Extension

```bash
# On Ubuntu/Debian
sudo apt-get install postgresql-14-pgvector

# On macOS (Homebrew)
brew install pgvector

# Or install from source
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install
```

### Step 2: Enable Extensions in Database

```sql
-- Connect to your database
psql -U postgres -d ppl_meta

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
```

## Usage

### Running Forward Migration

**Option 1: Using psql (Recommended)**

```bash
# Create backup first
pg_dump -U postgres -d ppl_meta > backup_before_mvr_migration_$(date +%Y%m%d_%H%M%S).sql

# Run migration
psql -U postgres -d ppl_meta -f 001_mvr_people_schema.sql

# Verify migration
psql -U postgres -d ppl_meta -c "SELECT COUNT(*) FROM mvr_people;"
```

**Option 2: Using Python (asyncpg)**

```python
import asyncpg
import asyncio

async def run_migration():
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='your_password',
        database='ppl_meta'
    )
    
    # Read migration script
    with open('migrations/001_mvr_people_schema.sql', 'r') as f:
        migration_sql = f.read()
    
    # Execute migration
    await conn.execute(migration_sql)
    
    # Verify
    count = await conn.fetchval('SELECT COUNT(*) FROM mvr_people')
    print(f"✅ Migration complete. MVR-People count: {count}")
    
    await conn.close()

asyncio.run(run_migration())
```

**Option 3: Using Migration Tool (Alembic/Flyway)**

```bash
# For Alembic (Python)
alembic revision --autogenerate -m "Add MVR-People schema"
alembic upgrade head

# For Flyway (Java)
flyway migrate -locations=filesystem:migrations
```

### Running Rollback Migration

**⚠️ WARNING:** Rollback will **permanently delete** all MVR-People data!

```bash
# Create backup first (CRITICAL!)
pg_dump -U postgres -d ppl_meta > backup_before_rollback_$(date +%Y%m%d_%H%M%S).sql

# Verify what will be deleted
psql -U postgres -d ppl_meta -c "SELECT COUNT(*) FROM mvr_people;"
psql -U postgres -d ppl_meta -c "SELECT COUNT(*) FROM individual_mvr_mapping;"

# Run rollback (only if you're sure!)
psql -U postgres -d ppl_meta -f 002_mvr_people_rollback.sql

# Verify rollback
psql -U postgres -d ppl_meta -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name LIKE 'mvr%';"
# Should return 0
```

## Verification

### Post-Migration Checks

**1. Verify Tables Created**

```sql
SELECT 
    tablename, 
    pg_size_pretty(pg_total_relation_size('public.' || tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
AND tablename IN (
    'mvr_people',
    'individual_mvr_mapping',
    'mvr_merge_audit_log',
    'mvr_matching_config'
)
ORDER BY tablename;
```

Expected output:
```
          tablename          |  size   
-----------------------------+---------
 individual_mvr_mapping      | 8192 bytes
 mvr_matching_config         | 8192 bytes
 mvr_merge_audit_log         | 8192 bytes
 mvr_people                  | 16 kB
```

**2. Verify Indexes Created**

```sql
SELECT 
    indexname, 
    tablename,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename LIKE 'mvr%'
ORDER BY tablename, indexname;
```

Expected: 14 indexes total

**3. Verify pgvector Extension**

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

Expected: 1 row with `vector` extension

**4. Verify Default Configuration**

```sql
SELECT 
    similarity_threshold,
    quality_weight,
    age_tolerance,
    gender_match_required,
    auto_merge_enabled
FROM mvr_matching_config
ORDER BY created_at DESC
LIMIT 1;
```

Expected output:
```
 similarity_threshold | quality_weight | age_tolerance | gender_match_required | auto_merge_enabled 
----------------------+----------------+---------------+-----------------------+--------------------
                 0.85 |            0.3 |             5 | f                     | t
```

**5. Test Similarity Search Index**

```sql
-- Insert a test record
INSERT INTO mvr_people (
    face_embedding, 
    featured_individual_uuid, 
    quality_score
)
SELECT 
    (SELECT ARRAY(SELECT random() FROM generate_series(1, 512)))::vector(512),
    individual_uuid,
    0.85
FROM individuals
LIMIT 1;

-- Test similarity search (should use index)
EXPLAIN ANALYZE
SELECT mvr_people_uuid, quality_score
FROM mvr_people
ORDER BY face_embedding <=> (SELECT face_embedding FROM mvr_people LIMIT 1)
LIMIT 10;

-- Check for index usage
-- Output should show "Index Scan using idx_mvr_people_embedding_vector"
```

**6. Verify Foreign Key Constraints**

```sql
SELECT
    tc.table_name, 
    tc.constraint_name, 
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
WHERE tc.table_schema = 'public'
AND tc.table_name LIKE 'mvr%'
AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name, tc.constraint_name;
```

Expected: 6 foreign key constraints

## Troubleshooting

### Issue 1: pgvector Extension Not Found

**Error:**
```
ERROR:  extension "vector" is not available
```

**Solution:**
```bash
# Install pgvector
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Restart PostgreSQL
sudo systemctl restart postgresql

# Try migration again
psql -U postgres -d ppl_meta -f 001_mvr_people_schema.sql
```

### Issue 2: Permission Denied

**Error:**
```
ERROR:  permission denied to create table "mvr_people"
```

**Solution:**
```sql
-- Grant necessary privileges
GRANT CREATE ON DATABASE ppl_meta TO your_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_user;

-- Or run migration as superuser
psql -U postgres -d ppl_meta -f 001_mvr_people_schema.sql
```

### Issue 3: Duplicate Key Error (Re-running Migration)

**Error:**
```
ERROR:  relation "mvr_people" already exists
```

**Solution:**
```sql
-- Migration is idempotent, but if you need a clean slate:

-- Option 1: Run rollback first
psql -U postgres -d ppl_meta -f 002_mvr_people_rollback.sql

-- Then run forward migration
psql -U postgres -d ppl_meta -f 001_mvr_people_schema.sql

-- Option 2: Drop manually (if rollback fails)
DROP TABLE IF EXISTS mvr_merge_audit_log CASCADE;
DROP TABLE IF EXISTS individual_mvr_mapping CASCADE;
DROP TABLE IF EXISTS mvr_people CASCADE;
DROP TABLE IF EXISTS mvr_matching_config CASCADE;
```

### Issue 4: Slow Index Creation

**Error:**
```
(Migration hangs on creating idx_mvr_people_embedding_vector)
```

**Solution:**
```sql
-- Check if index is building
SELECT * FROM pg_stat_progress_create_index;

-- If index creation is slow, increase work_mem temporarily
SET work_mem = '256MB';

-- Then re-run migration
psql -U postgres -d ppl_meta -f 001_mvr_people_schema.sql
```

### Issue 5: Foreign Key Constraint Violation

**Error:**
```
ERROR:  insert or update on table "mvr_people" violates foreign key constraint "fk_mvr_people_featured_individual"
```

**Solution:**
```sql
-- Verify Individuals table exists
SELECT COUNT(*) FROM individuals;

-- Check if the Individual UUID exists
SELECT individual_uuid FROM individuals WHERE individual_uuid = 'your-uuid-here';

-- Ensure you're inserting valid Individual UUIDs
INSERT INTO mvr_people (featured_individual_uuid, face_embedding, quality_score)
SELECT 
    individual_uuid,
    (SELECT ARRAY(SELECT random() FROM generate_series(1, 512)))::vector(512),
    0.85
FROM individuals
LIMIT 1;
```

## Migration History

| Version | Date       | Description                          | Status |
|---------|------------|--------------------------------------|--------|
| 001     | 2025-11-01 | Initial MVR-People schema creation   | ✅ Active |
| 002     | 2025-11-01 | Rollback script for schema removal   | ✅ Available |

## Rollback Strategy

### When to Rollback

Rollback if:
- Migration fails midway through
- Application errors after migration
- Performance degradation detected
- Need to revert to previous schema

### Rollback Checklist

Before rollback:
- [ ] Create full database backup
- [ ] Stop vmeta service (`systemctl stop vmeta`)
- [ ] Verify no active MVR processing jobs
- [ ] Note down current MVR-People count
- [ ] Inform team of rollback plan

After rollback:
- [ ] Verify all MVR tables removed
- [ ] Check Individuals table intact
- [ ] Restart vmeta service
- [ ] Test Individual creation workflow
- [ ] Monitor logs for errors

## Performance Optimization

### Index Tuning

**pgvector IVFFlat Index:**
```sql
-- Default: lists = 100 (good for 10K-100K embeddings)
-- For larger datasets:
CREATE INDEX idx_mvr_people_embedding_vector 
    ON mvr_people 
    USING ivfflat (face_embedding vector_cosine_ops)
    WITH (lists = 500);  -- For 100K-1M embeddings
```

**Rule of thumb:** `lists = sqrt(row_count)`

### Query Performance

**Similarity Search Optimization:**
```sql
-- Set probes for search (default: 1)
SET ivfflat.probes = 10;  -- Higher = more accurate, slower

-- Test query performance
EXPLAIN (ANALYZE, BUFFERS)
SELECT mvr_people_uuid
FROM mvr_people
WHERE is_orphaned = FALSE
ORDER BY face_embedding <=> $1::vector(512)
LIMIT 10;

-- Target: <100ms for 10K embeddings
```

## Support

For migration issues:
1. Check PostgreSQL logs: `/var/log/postgresql/postgresql-14-main.log`
2. Check vmeta service logs: `/var/log/vmeta/mvr_service.log`
3. Review deployment guide: `docs/vision-vmeta/MVR_PEOPLE_DEPLOYMENT_GUIDE.md`
4. Contact: Platform team (#ppl-meta-platform)

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/14/)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [MVR-People Deployment Guide](../docs/vision-vmeta/MVR_PEOPLE_DEPLOYMENT_GUIDE.md)
- [MVR-People API Documentation](../docs/vision-vmeta/MVR_PEOPLE_API.md)
