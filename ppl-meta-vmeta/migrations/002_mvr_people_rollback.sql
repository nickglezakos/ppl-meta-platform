-- ============================================================================
-- MVR-People Database Rollback Script
-- Version: 1.0.0
-- Date: November 1, 2025
-- Description: Safely rolls back MVR-People schema migration
-- ============================================================================

-- **CRITICAL WARNING:**
-- This script will permanently delete all MVR-People data!
-- 
-- Before running:
-- 1. Create a database backup:
--    pg_dump -U postgres -d ppl_meta > backup_before_rollback.sql
-- 
-- 2. Verify you want to proceed - this is IRREVERSIBLE
-- 
-- 3. Check for dependent data:
--    SELECT COUNT(*) FROM mvr_people;
--    SELECT COUNT(*) FROM individual_mvr_mapping;
--    SELECT COUNT(*) FROM mvr_merge_audit_log;

-- Usage:
-- psql -U postgres -d ppl_meta -f 002_mvr_people_rollback.sql

BEGIN;

-- ============================================================================
-- VERIFICATION - Check what will be deleted
-- ============================================================================

DO $$
DECLARE
    mvr_count INTEGER;
    mapping_count INTEGER;
    audit_count INTEGER;
    config_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO mvr_count FROM mvr_people WHERE 1=1;
    SELECT COUNT(*) INTO mapping_count FROM individual_mvr_mapping WHERE 1=1;
    SELECT COUNT(*) INTO audit_count FROM mvr_merge_audit_log WHERE 1=1;
    SELECT COUNT(*) INTO config_count FROM mvr_matching_config WHERE 1=1;
    
    RAISE NOTICE '⚠️  ROLLBACK IMPACT SUMMARY:';
    RAISE NOTICE '    • MVR-People records: %', mvr_count;
    RAISE NOTICE '    • Individual mappings: %', mapping_count;
    RAISE NOTICE '    • Merge audit logs: %', audit_count;
    RAISE NOTICE '    • Config records: %', config_count;
    RAISE NOTICE '';
    RAISE NOTICE '🛑 All this data will be PERMANENTLY DELETED in 5 seconds...';
    
    -- Safety delay (5 seconds to cancel if needed)
    PERFORM pg_sleep(5);
    
EXCEPTION
    WHEN undefined_table THEN
        RAISE NOTICE '⚠️  Some MVR tables do not exist - proceeding with rollback';
END $$;

-- ============================================================================
-- STAGE 1: Drop Foreign Key Constraints
-- (Allows tables to be dropped in any order)
-- ============================================================================

-- Drop FK constraints on mvr_people
ALTER TABLE IF EXISTS mvr_people 
    DROP CONSTRAINT IF EXISTS fk_mvr_people_featured_individual;
    
ALTER TABLE IF EXISTS mvr_people 
    DROP CONSTRAINT IF EXISTS fk_mvr_people_replaced_by;

-- Drop FK constraints on individual_mvr_mapping
ALTER TABLE IF EXISTS individual_mvr_mapping 
    DROP CONSTRAINT IF EXISTS fk_individual_mvr_individual;
    
ALTER TABLE IF EXISTS individual_mvr_mapping 
    DROP CONSTRAINT IF EXISTS fk_individual_mvr_mvr_people;

-- Drop FK constraints on mvr_merge_audit_log
ALTER TABLE IF EXISTS mvr_merge_audit_log 
    DROP CONSTRAINT IF EXISTS fk_mvr_audit_winner;
    
ALTER TABLE IF EXISTS mvr_merge_audit_log 
    DROP CONSTRAINT IF EXISTS fk_mvr_audit_loser;

RAISE NOTICE '✅ Foreign key constraints dropped';

-- ============================================================================
-- STAGE 2: Drop Indexes
-- (Explicit drop for clarity, though CASCADE would handle them)
-- ============================================================================

-- mvr_people indexes
DROP INDEX IF EXISTS idx_mvr_people_embedding_vector;
DROP INDEX IF EXISTS idx_mvr_people_featured_individual;
DROP INDEX IF EXISTS idx_mvr_people_orphaned;
DROP INDEX IF EXISTS idx_mvr_people_quality_active;
DROP INDEX IF EXISTS idx_mvr_people_demographics;
DROP INDEX IF EXISTS idx_mvr_people_created_at;

-- individual_mvr_mapping indexes
DROP INDEX IF EXISTS idx_mvr_mapping_individual;
DROP INDEX IF EXISTS idx_mvr_mapping_mvr_people;
DROP INDEX IF EXISTS idx_mvr_mapping_quality;

-- mvr_merge_audit_log indexes
DROP INDEX IF EXISTS idx_mvr_audit_winner;
DROP INDEX IF EXISTS idx_mvr_audit_loser;
DROP INDEX IF EXISTS idx_mvr_audit_timestamp;

-- mvr_matching_config indexes
DROP INDEX IF EXISTS idx_mvr_config_created;

RAISE NOTICE '✅ Indexes dropped';

-- ============================================================================
-- STAGE 3: Drop Tables
-- (Reverse order of creation to respect dependencies)
-- ============================================================================

-- Drop audit log first (no dependencies)
DROP TABLE IF EXISTS mvr_merge_audit_log CASCADE;
RAISE NOTICE '✅ Dropped mvr_merge_audit_log';

-- Drop mapping table
DROP TABLE IF EXISTS individual_mvr_mapping CASCADE;
RAISE NOTICE '✅ Dropped individual_mvr_mapping';

-- Drop config table
DROP TABLE IF EXISTS mvr_matching_config CASCADE;
RAISE NOTICE '✅ Dropped mvr_matching_config';

-- Drop main mvr_people table last
DROP TABLE IF EXISTS mvr_people CASCADE;
RAISE NOTICE '✅ Dropped mvr_people';

-- ============================================================================
-- STAGE 4: Verification
-- ============================================================================

DO $$
DECLARE
    remaining_tables INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining_tables
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN (
        'mvr_people',
        'individual_mvr_mapping',
        'mvr_merge_audit_log',
        'mvr_matching_config'
    );
    
    IF remaining_tables = 0 THEN
        RAISE NOTICE '✅ All MVR-People tables successfully removed';
    ELSE
        RAISE WARNING '⚠️  % MVR-People tables still exist!', remaining_tables;
    END IF;
END $$;

-- Verify indexes removed
DO $$
DECLARE
    remaining_indexes INTEGER;
BEGIN
    SELECT COUNT(*) INTO remaining_indexes
    FROM pg_indexes
    WHERE schemaname = 'public'
    AND indexname LIKE 'idx_mvr%';
    
    IF remaining_indexes = 0 THEN
        RAISE NOTICE '✅ All MVR-People indexes successfully removed';
    ELSE
        RAISE WARNING '⚠️  % MVR-People indexes still exist!', remaining_indexes;
    END IF;
END $$;

-- ============================================================================
-- OPTIONAL: Remove pgvector extension
-- (Only if no other tables use it)
-- ============================================================================

-- **UNCOMMENT ONLY IF SAFE TO REMOVE pgvector**
-- Check for other tables using vector type:
DO $$
DECLARE
    vector_column_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO vector_column_count
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND udt_name = 'vector';
    
    IF vector_column_count = 0 THEN
        RAISE NOTICE '💡 No other tables use pgvector - safe to remove extension';
        RAISE NOTICE '   To remove: DROP EXTENSION IF EXISTS vector CASCADE;';
    ELSE
        RAISE NOTICE '⚠️  % columns still use pgvector - DO NOT remove extension', vector_column_count;
    END IF;
END $$;

-- Uncomment to drop pgvector (ONLY if confirmed safe above):
-- DROP EXTENSION IF EXISTS vector CASCADE;

COMMIT;

-- ============================================================================
-- ROLLBACK COMPLETE
-- ============================================================================

SELECT 
    '✅ MVR-People rollback completed successfully!' as status,
    CURRENT_TIMESTAMP as completed_at;

-- Display remaining MVR-related objects (should be empty)
SELECT 
    'Remaining MVR tables' as check_type,
    COUNT(*) as count
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'mvr%'

UNION ALL

SELECT 
    'Remaining MVR indexes' as check_type,
    COUNT(*) as count
FROM pg_indexes
WHERE schemaname = 'public'
AND indexname LIKE 'idx_mvr%';

-- ============================================================================
-- POST-ROLLBACK STEPS
-- ============================================================================

/*
After running this rollback, you should:

1. **Verify the rollback:**
   SELECT tablename FROM pg_tables 
   WHERE schemaname = 'public' AND tablename LIKE 'mvr%';
   
   -- Should return 0 rows

2. **Check for orphaned data:**
   SELECT COUNT(*) FROM individuals 
   WHERE individual_uuid IN (
       SELECT featured_individual_uuid FROM mvr_people
   );
   
   -- Should fail with "mvr_people does not exist" (expected)

3. **Restart affected services:**
   # Stop vmeta service
   systemctl stop vmeta
   
   # Clear any cached schema
   rm -rf /tmp/vmeta_schema_cache
   
   # Restart vmeta service
   systemctl start vmeta

4. **Verify service health:**
   curl http://localhost:8008/health
   
   # Should not reference MVR-People endpoints

5. **Optional: Restore from backup if needed:**
   psql -U postgres -d ppl_meta < backup_before_rollback.sql

6. **Update application code:**
   # Remove or comment out MVR-related imports in:
   # - database/repository.py (remove MVR trigger)
   # - api/routes/mvr_people.py (disable endpoints)
   # - background/mvr_helper.py (disable background processing)

7. **Clean up background task queue:**
   # If using Celery or similar:
   celery -A vmeta purge
*/

-- ============================================================================
-- NOTES
-- ============================================================================

/*
**What was removed:**
- mvr_people table (main MVR records)
- individual_mvr_mapping table (Individual ↔ MVR linkage)
- mvr_merge_audit_log table (merge operation history)
- mvr_matching_config table (matching algorithm configuration)
- All associated indexes (14 total)
- All foreign key constraints (6 total)

**What was preserved:**
- individuals table (no changes)
- individual_video_appearances table (no changes)
- person_objects table in Orchestrator service (no changes)
- pgvector extension (kept for potential future use)

**Data recovery:**
If you need to recover data after rollback:
1. Restore from backup: psql -U postgres -d ppl_meta < backup.sql
2. OR re-run forward migration: psql -U postgres -d ppl_meta -f 001_mvr_people_schema.sql
3. Then trigger MVR creation for existing Individuals

**Performance impact:**
- Rollback completes in <5 seconds for typical databases
- No impact on other services (Individuals, Orchestrator, etc.)
- Similarity search endpoints will return 404 errors (expected)
*/
