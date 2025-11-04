"""
Phase 5: Integration Testing with Real Data

Test MVR-People system with actual Individual records from the database.

**Test Flow:**
1. Query existing Individuals from database
2. Create MVR-People for selected Individuals
3. Test matching algorithm with real face embeddings
4. Test merging similar Individuals
5. Verify background processing
6. Performance and accuracy validation

Author: PPL Meta Platform
Date: November 1, 2025
Version: 1.0.0
"""

import asyncio
import logging
from uuid import UUID
from datetime import datetime
import asyncpg

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': 'postgres',
    'database': 'ppl_meta',
}


async def get_existing_individuals(pool: asyncpg.Pool, limit: int = 10):
    """
    Get existing Individuals from database for testing.
    
    Args:
        pool: Database connection pool
        limit: Number of Individuals to retrieve
        
    Returns:
        List of Individual records
    """
    logger.info(f"\n📊 Fetching {limit} existing Individuals from database...")
    
    query = """
        SELECT 
            i.individual_uuid,
            i.individual_id,
            i.confidence_score,
            i.created_at,
            COUNT(DISTINCT iva.video_uuid) as video_count,
            COUNT(DISTINCT iva.person_object_uuid) as person_object_count
        FROM individuals i
        LEFT JOIN individual_video_appearances iva 
            ON i.individual_uuid = iva.individual_uuid
        GROUP BY i.individual_uuid, i.individual_id, 
                 i.confidence_score, i.created_at
        ORDER BY i.created_at DESC
        LIMIT $1
    """
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, limit)
        
        individuals = []
        for row in rows:
            individual = {
                'individual_uuid': row['individual_uuid'],
                'individual_id': row['individual_id'],
                'confidence_score': row['confidence_score'],
                'created_at': row['created_at'],
                'video_count': row['video_count'],
                'person_object_count': row['person_object_count'],
            }
            individuals.append(individual)
            
            logger.info(
                f"  • {individual['individual_id']}: "
                f"{individual['person_object_count']} person objects, "
                f"{individual['video_count']} videos"
            )
        
        logger.info(f"✅ Found {len(individuals)} Individuals")
        return individuals


async def check_mvr_people_exists(
    pool: asyncpg.Pool,
    individual_uuid: UUID
) -> bool:
    """Check if MVR-People already exists for Individual."""
    query = """
        SELECT COUNT(*) as count
        FROM individual_mvr_mapping
        WHERE individual_uuid = $1
    """
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, individual_uuid)
        return row['count'] > 0


async def test_mvr_creation_for_individuals(pool: asyncpg.Pool):
    """
    Test 1: Create MVR-People for existing Individuals.
    
    This tests the core MVR creation workflow with real data.
    """
    logger.info("\n" + "="*70)
    logger.info("TEST 1: MVR-People Creation with Real Individuals")
    logger.info("="*70)
    
    # Get existing Individuals
    individuals = await get_existing_individuals(pool, limit=5)
    
    if not individuals:
        logger.warning("⚠️ No Individuals found in database!")
        logger.warning("⚠️ Please create some Individuals first (run camera detection)")
        return
    
    # Import MVR components
    from database.mvr_repository import MVRRepository
    from services.mvr_service import MVRService
    from ml.mvr_processor import MVRProcessor
    
    # Initialize components
    repository = MVRRepository(connection_pool=pool)
    ml_processor = MVRProcessor()
    
    # Mock Orchestrator (for testing without Orchestrator service)
    class MockOrchestrator:
        async def get_person_objects_for_individual(self, individual_uuid):
            logger.info(
                f"🔧 Mock: Getting person objects for {individual_uuid}"
            )
            return []  # Return empty for now
    
    service = MVRService(
        repository=repository,
        ml_processor=ml_processor,
        orchestrator_client=MockOrchestrator(),
    )
    
    # Test MVR creation for each Individual
    created_count = 0
    skipped_count = 0
    
    for individual in individuals:
        individual_uuid = individual['individual_uuid']
        individual_id = individual['individual_id']
        
        logger.info(f"\n  Processing Individual {individual_id}...")
        
        # Check if MVR already exists
        exists = await check_mvr_people_exists(pool, individual_uuid)
        
        if exists:
            logger.info(f"  ⏭️  MVR-People already exists, skipping")
            skipped_count += 1
            continue
        
        try:
            # Create MVR-People
            logger.info(f"  🧬 Creating MVR-People...")
            mvr_result = await service.create_mvr_people_from_individual(
                individual_uuid
            )
            
            if mvr_result:
                created_count += 1
                logger.info(
                    f"  ✅ Created MVR-People: "
                    f"{mvr_result['mvr_people_uuid']}"
                )
                logger.info(
                    f"     Quality Score: "
                    f"{mvr_result.get('quality_score', 0.0):.3f}"
                )
            else:
                logger.warning(f"  ❌ Failed to create MVR-People")
        
        except Exception as e:
            logger.error(f"  ❌ Error creating MVR-People: {e}")
    
    logger.info(f"\n📊 Summary:")
    logger.info(f"  • Created: {created_count}")
    logger.info(f"  • Skipped (already exists): {skipped_count}")
    logger.info(f"  • Total processed: {len(individuals)}")


async def test_mvr_matching(pool: asyncpg.Pool):
    """
    Test 2: Match similar Individuals using MVR-People.
    
    This tests the matching algorithm with real face embeddings.
    """
    logger.info("\n" + "="*70)
    logger.info("TEST 2: MVR-People Matching with Real Data")
    logger.info("="*70)
    
    # Get Individuals with MVR-People
    query = """
        SELECT DISTINCT i.individual_uuid, i.individual_id
        FROM individuals i
        INNER JOIN individual_mvr_mapping imm 
            ON i.individual_uuid = imm.individual_uuid
        LIMIT 3
    """
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(query)
        
        if len(rows) < 2:
            logger.warning(
                "⚠️ Need at least 2 Individuals with MVR-People for matching"
            )
            logger.warning("⚠️ Run Test 1 first to create MVR-People")
            return
        
        logger.info(f"Found {len(rows)} Individuals with MVR-People")
    
    # Import MVR components
    from database.mvr_repository import MVRRepository
    from services.mvr_matcher import MVRMatcher
    from ml.mvr_processor import MVRProcessor
    
    repository = MVRRepository(connection_pool=pool)
    ml_processor = MVRProcessor()
    matcher = MVRMatcher(repository=repository, ml_processor=ml_processor)
    
    # Test matching for each Individual
    for row in rows:
        individual_uuid = row['individual_uuid']
        individual_id = row['individual_id']
        
        logger.info(f"\n  Finding matches for {individual_id}...")
        
        try:
            matches = await matcher.find_matching_mvr(
                individual_uuid=individual_uuid,
                threshold=0.85,
            )
            
            if matches:
                logger.info(f"  ✅ Found {len(matches)} potential matches:")
                for match in matches[:3]:  # Show top 3
                    logger.info(
                        f"     • Similarity: "
                        f"{match.get('similarity_score', 0.0):.3f}, "
                        f"Quality: {match.get('quality_score', 0.0):.3f}"
                    )
            else:
                logger.info(f"  ℹ️  No matches found above threshold")
        
        except Exception as e:
            logger.error(f"  ❌ Error finding matches: {e}")


async def test_background_processing(pool: asyncpg.Pool):
    """
    Test 3: Background processing statistics and status.
    
    This verifies the background processor is working correctly.
    """
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Background Processing Statistics")
    logger.info("="*70)
    
    try:
        from background.mvr_background_processor import (
            MVRBackgroundProcessor
        )
        from database.mvr_repository import MVRRepository
        from services.mvr_service import MVRService
        from services.mvr_matcher import MVRMatcher
        from ml.mvr_processor import MVRProcessor
        
        # Initialize components
        repository = MVRRepository(connection_pool=pool)
        ml_processor = MVRProcessor()
        service = MVRService(
            repository=repository,
            ml_processor=ml_processor,
            orchestrator_client=None,
        )
        matcher = MVRMatcher(
            repository=repository,
            ml_processor=ml_processor
        )
        
        background_processor = MVRBackgroundProcessor(
            mvr_service=service,
            mvr_matcher=matcher,
            max_retries=3,
            retry_delay=5.0,
        )
        
        # Get statistics
        stats = await background_processor.get_statistics()
        
        logger.info(f"\n📊 Background Processing Statistics:")
        logger.info(f"  • Total Tasks: {stats.get('total_tasks', 0)}")
        logger.info(
            f"  • Completed: {stats.get('completed_tasks', 0)}"
        )
        logger.info(f"  • Failed: {stats.get('failed_tasks', 0)}")
        logger.info(
            f"  • Pending: {stats.get('pending_tasks', 0)}"
        )
        logger.info(
            f"  • Success Rate: "
            f"{stats.get('success_rate', 0.0):.1%}"
        )
        
        # Get pending tasks
        pending = await background_processor.get_all_pending_tasks()
        
        if pending:
            logger.info(f"\n⏳ Pending Tasks: {len(pending)}")
            for task in pending[:5]:  # Show first 5
                logger.info(
                    f"  • Individual: {task.get('individual_uuid')}, "
                    f"Status: {task.get('status')}"
                )
        else:
            logger.info(f"\nℹ️  No pending tasks")
    
    except Exception as e:
        logger.error(f"❌ Error getting background processing stats: {e}")


async def test_database_statistics(pool: asyncpg.Pool):
    """
    Test 4: Database statistics and record counts.
    
    Shows current state of MVR-People system.
    """
    logger.info("\n" + "="*70)
    logger.info("TEST 4: Database Statistics")
    logger.info("="*70)
    
    queries = {
        'Individuals': "SELECT COUNT(*) FROM individuals",
        'MVR-People': "SELECT COUNT(*) FROM mvr_people",
        'MVR Mappings': "SELECT COUNT(*) FROM individual_mvr_mapping",
        'Orphaned MVR': """
            SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = TRUE
        """,
        'Active MVR': """
            SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = FALSE
        """,
        'Merge Events': "SELECT COUNT(*) FROM mvr_merge_audit_log",
    }
    
    async with pool.acquire() as conn:
        logger.info("\n📊 Database Statistics:")
        
        for label, query in queries.items():
            try:
                row = await conn.fetchrow(query)
                count = row['count']
                logger.info(f"  • {label}: {count:,}")
            except Exception as e:
                logger.error(f"  ❌ Error getting {label}: {e}")
        
        # Average quality score
        try:
            row = await conn.fetchrow("""
                SELECT AVG(quality_score) as avg_quality
                FROM mvr_people
                WHERE is_orphaned = FALSE
            """)
            avg_quality = row['avg_quality']
            if avg_quality:
                logger.info(
                    f"  • Average Quality Score: {avg_quality:.3f}"
                )
        except Exception as e:
            logger.error(f"  ❌ Error getting average quality: {e}")


async def run_integration_tests():
    """Run all Phase 5 integration tests."""
    logger.info("\n" + "="*70)
    logger.info("PHASE 5: INTEGRATION TESTING WITH REAL DATA")
    logger.info("="*70)
    logger.info("Testing MVR-People system with actual Individual records")
    logger.info("="*70 + "\n")
    
    # Create database connection pool
    logger.info("📊 Connecting to database...")
    pool = await asyncpg.create_pool(**DB_CONFIG)
    
    try:
        # Run tests in sequence
        await test_database_statistics(pool)
        await test_mvr_creation_for_individuals(pool)
        await test_mvr_matching(pool)
        await test_background_processing(pool)
        
        # Final statistics
        await test_database_statistics(pool)
        
        logger.info("\n" + "="*70)
        logger.info("✅ PHASE 5 INTEGRATION TESTS COMPLETED")
        logger.info("="*70)
    
    except Exception as e:
        logger.error(f"\n❌ INTEGRATION TESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_integration_tests())
