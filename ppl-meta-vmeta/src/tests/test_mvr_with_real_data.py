"""
Phase 5: MVR-People Integration Test with Real Data

Uses the documented Individual from VISION_SERVICE_ENDPOINTS_REFERENCE.md:
- Individual UUID: 5c73fd34-737a-48c7-a69a-f17b40adbead
- Individual ID: ind_5c73fd34
- Videos: 2 (with person objects and faces)
- Time Range: 2025-10-19 13:05:00 to 13:14:30

This test validates the complete MVR-People workflow with real person objects
and face data from the database.

Author: PPL Meta Platform
Date: November 1, 2025
Version: 1.0.0
"""

import asyncio
import logging
from uuid import UUID
import asyncpg
import httpx

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

# Known real data from documentation
REAL_INDIVIDUAL_UUID = UUID("5c73fd34-737a-48c7-a69a-f17b40adbead")
REAL_INDIVIDUAL_ID = "ind_5c73fd34"

# Authentication
NODE_SERVICE_URL = "http://localhost:8001"
ORCHESTRATOR_URL = "http://localhost:8002"
TEST_USER_EMAIL = "fresh.user@example.com"
TEST_USER_PASSWORD = "NewPassword234!"


async def get_auth_token() -> str:
    """Get JWT token from Node service."""
    logger.info("🔐 Authenticating with Node service...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{NODE_SERVICE_URL}/api/v1/users/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "username": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            }
        )
        
        if response.status_code == 200:
            token = response.json().get("access_token")
            logger.info("✅ Authentication successful")
            return token
        else:
            raise Exception(f"Authentication failed: {response.status_code}")


async def verify_individual_exists(pool: asyncpg.Pool) -> bool:
    """Verify the documented Individual exists in database."""
    logger.info(f"\n📊 Verifying Individual {REAL_INDIVIDUAL_ID} exists...")
    
    query = """
        SELECT 
            individual_uuid,
            individual_id,
            confidence_score,
            created_at
        FROM individuals
        WHERE individual_uuid = $1
    """
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, REAL_INDIVIDUAL_UUID)
        
        if row:
            logger.info(f"✅ Found Individual:")
            logger.info(f"   • UUID: {row['individual_uuid']}")
            logger.info(f"   • ID: {row['individual_id']}")
            logger.info(f"   • Confidence: {row['confidence_score']}")
            logger.info(f"   • Created: {row['created_at']}")
            return True
        else:
            logger.warning(f"⚠️ Individual {REAL_INDIVIDUAL_ID} not found!")
            return False


async def get_video_uuids_for_individual(
    pool: asyncpg.Pool,
    individual_uuid: UUID
) -> list:
    """Get video UUIDs for an Individual from database."""
    logger.info(f"\n📹 Fetching video UUIDs for Individual...")
    
    query = """
        SELECT video_uuid, start_timestamp
        FROM individual_video_appearances
        WHERE individual_uuid = $1
        ORDER BY start_timestamp
    """
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, individual_uuid)
        video_uuids = [row['video_uuid'] for row in rows]
        
        logger.info(f"✅ Found {len(video_uuids)} videos:")
        for video_uuid in video_uuids:
            logger.info(f"   • {video_uuid}")
        
        return video_uuids


async def get_person_objects_for_video(
    video_uuid: UUID,
    token: str
) -> dict:
    """Fetch person objects for a video from Orchestrator."""
    logger.info(f"\n🔍 Fetching person objects for video {video_uuid}...")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ORCHESTRATOR_URL}/person-objects/{video_uuid}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Found person objects:")
            logger.info(f"   • Total persons: {data.get('total_persons', 0)}")
            logger.info(f"   • Total faces: {data.get('total_faces', 0)}")
            return data
        else:
            logger.error(
                f"❌ Failed to fetch person objects: {response.status_code}"
            )
            logger.error(f"   Response: {response.text}")
            return {}


async def test_mvr_creation_with_real_individual(
    pool: asyncpg.Pool,
    token: str
):
    """
    Test 1: Create MVR-People from real Individual with person objects.
    
    This is the core test - create MVR-People using actual face data
    from the Orchestrator service.
    """
    logger.info("\n" + "="*70)
    logger.info("TEST 1: Create MVR-People from Real Individual")
    logger.info("="*70)
    
    # Verify Individual exists
    if not await verify_individual_exists(pool):
        logger.error("❌ Cannot proceed without real Individual data")
        return False
    
    # Get video UUIDs for this Individual
    video_uuids = await get_video_uuids_for_individual(
        pool,
        REAL_INDIVIDUAL_UUID
    )
    
    if not video_uuids:
        logger.error("❌ No videos found for Individual")
        return False
    
    # Get person objects for first video
    person_data = await get_person_objects_for_video(
        video_uuids[0],
        token
    )
    
    if not person_data or not person_data.get('total_persons'):
        logger.error("❌ No person objects found in video")
        logger.warning(
            "⚠️ You may need to run person objects workflow first"
        )
        return False
    
    # Import MVR components (without Orchestrator client for now)
    from database.mvr_repository import MVRRepository
    from services.mvr_service import MVRService
    from ml.mvr_processor import MVRProcessor
    
    # Initialize components WITHOUT Orchestrator client
    # We'll use direct HTTP calls instead
    repository = MVRRepository(connection_pool=pool)
    ml_processor = MVRProcessor()
    
    service = MVRService(
        repository=repository,
        ml_processor=ml_processor,
        orchestrator_client=None  # Not needed for this test
    )
    
    # Check if MVR already exists
    logger.info(f"\n🔍 Checking for existing MVR-People...")
    
    query = """
        SELECT mvr_people_uuid, quality_score, created_at
        FROM individual_mvr_mapping
        WHERE individual_uuid = $1
    """
    
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(query, REAL_INDIVIDUAL_UUID)
        
        if existing:
            logger.info(f"⏭️  MVR-People already exists:")
            logger.info(f"   • MVR UUID: {existing['mvr_people_uuid']}")
            logger.info(f"   • Quality: {existing['quality_score']:.3f}")
            logger.info(f"   • Created: {existing['created_at']}")
            return True
    
    # Create MVR-People
    logger.info(f"\n🧬 Creating MVR-People from Individual...")
    
    try:
        mvr_result = await service.create_mvr_people_from_individual(
            REAL_INDIVIDUAL_UUID
        )
        
        if mvr_result:
            logger.info(f"✅ Successfully created MVR-People!")
            logger.info(f"   • MVR UUID: {mvr_result.get('mvr_people_uuid')}")
            logger.info(
                f"   • Quality Score: "
                f"{mvr_result.get('quality_score', 0.0):.3f}"
            )
            logger.info(
                f"   • Age Range: "
                f"{mvr_result.get('age_min')}-{mvr_result.get('age_max')}"
            )
            logger.info(
                f"   • Gender: {mvr_result.get('gender_estimate')}"
            )
            return True
        else:
            logger.error(f"❌ Failed to create MVR-People")
            return False
    
    except Exception as e:
        logger.error(f"❌ Error creating MVR-People: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_mvr_matching_with_real_data(pool: asyncpg.Pool):
    """
    Test 2: Find matching MVR-People using real embeddings.
    
    Tests the similarity search with actual face embeddings.
    """
    logger.info("\n" + "="*70)
    logger.info("TEST 2: MVR-People Matching with Real Data")
    logger.info("="*70)
    
    # Get MVR for the real Individual
    query = """
        SELECT 
            imm.mvr_people_uuid,
            mvr.face_embedding,
            mvr.quality_score
        FROM individual_mvr_mapping imm
        JOIN mvr_people mvr ON mvr.mvr_people_uuid = imm.mvr_people_uuid
        WHERE imm.individual_uuid = $1
    """
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, REAL_INDIVIDUAL_UUID)
        
        if not row:
            logger.warning(
                f"⚠️ No MVR-People found for {REAL_INDIVIDUAL_ID}"
            )
            logger.warning("⚠️ Run Test 1 first to create MVR-People")
            return False
    
    mvr_uuid = row['mvr_people_uuid']
    logger.info(f"✅ Found MVR-People: {mvr_uuid}")
    
    # Import matcher
    from database.mvr_repository import MVRRepository
    from services.mvr_matcher import MVRMatcher
    from ml.mvr_processor import MVRProcessor
    
    repository = MVRRepository(connection_pool=pool)
    ml_processor = MVRProcessor()
    matcher = MVRMatcher(
        repository=repository,
        ml_processor=ml_processor
    )
    
    # Find matches
    logger.info(f"\n🔍 Searching for similar MVR-People...")
    
    try:
        matches = await matcher.find_matching_mvr(
            individual_uuid=REAL_INDIVIDUAL_UUID,
            threshold=0.85
        )
        
        if matches:
            logger.info(f"✅ Found {len(matches)} potential matches:")
            for i, match in enumerate(matches[:5], 1):
                logger.info(
                    f"   {i}. Similarity: "
                    f"{match.get('similarity_score', 0.0):.3f}, "
                    f"Quality: {match.get('quality_score', 0.0):.3f}"
                )
        else:
            logger.info(f"ℹ️  No matches found above threshold (0.85)")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error finding matches: {e}")
        return False


async def test_database_stats(pool: asyncpg.Pool):
    """
    Test 3: Database statistics before and after MVR creation.
    """
    logger.info("\n" + "="*70)
    logger.info("TEST 3: Database Statistics")
    logger.info("="*70)
    
    queries = {
        'Total Individuals': "SELECT COUNT(*) FROM individuals",
        'Individuals with MVR': """
            SELECT COUNT(DISTINCT individual_uuid) 
            FROM individual_mvr_mapping
        """,
        'Total MVR-People': "SELECT COUNT(*) FROM mvr_people",
        'Active MVR-People': """
            SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = FALSE
        """,
        'Orphaned MVR-People': """
            SELECT COUNT(*) FROM mvr_people WHERE is_orphaned = TRUE
        """,
        'Merge Events': "SELECT COUNT(*) FROM mvr_merge_audit_log",
    }
    
    async with pool.acquire() as conn:
        logger.info("\n📊 Database Statistics:")
        
        for label, query in queries.items():
            try:
                row = await conn.fetchrow(query)
                count = row['count']
                logger.info(f"   • {label}: {count:,}")
            except Exception as e:
                logger.error(f"   ❌ Error getting {label}: {e}")
        
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
                    f"   • Average Quality Score: {avg_quality:.3f}"
                )
        except Exception as e:
            logger.error(f"   ❌ Error getting average quality: {e}")


async def run_real_data_tests():
    """Run all integration tests with real data."""
    logger.info("\n" + "="*70)
    logger.info("PHASE 5: MVR-PEOPLE INTEGRATION WITH REAL DATA")
    logger.info("="*70)
    logger.info(f"Testing with Individual: {REAL_INDIVIDUAL_ID}")
    logger.info(f"UUID: {REAL_INDIVIDUAL_UUID}")
    logger.info("="*70 + "\n")
    
    # Get authentication token
    try:
        token = await get_auth_token()
    except Exception as e:
        logger.error(f"❌ Authentication failed: {e}")
        return
    
    # Create database connection pool
    logger.info("📊 Connecting to database...")
    pool = await asyncpg.create_pool(**DB_CONFIG)
    
    try:
        # Run tests in sequence
        await test_database_stats(pool)
        
        success1 = await test_mvr_creation_with_real_individual(pool, token)
        success2 = await test_mvr_matching_with_real_data(pool)
        
        await test_database_stats(pool)
        
        # Summary
        logger.info("\n" + "="*70)
        if success1 and success2:
            logger.info("✅ ALL INTEGRATION TESTS PASSED")
        else:
            logger.info("⚠️ SOME TESTS FAILED")
        logger.info("="*70)
    
    except Exception as e:
        logger.error(f"\n❌ INTEGRATION TESTS FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_real_data_tests())
