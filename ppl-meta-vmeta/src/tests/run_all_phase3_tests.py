"""
Master Test Runner for MVR-People Phase 3 Components

Runs all test suites in sequence:
1. MVRRepository tests
2. MVRService tests
3. MVRMatcher tests
4. MVRBackgroundProcessor tests

This provides comprehensive testing of all Phase 3 components.
"""

import asyncio
import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def run_all_phase3_tests():
    """Run all Phase 3 test suites."""
    
    logger.info("\n" + "=" * 70)
    logger.info("MVR-PEOPLE PHASE 3 - COMPREHENSIVE TEST SUITE")
    logger.info("=" * 70)
    logger.info("Testing all Phase 3 components:")
    logger.info("  - Phase 3.1: MVRRepository (Database Layer)")
    logger.info("  - Phase 3.2: MVRService (Service Layer)")
    logger.info("  - Phase 3.3-3.4: MVRMatcher (Matching & Merging)")
    logger.info("  - Phase 3.5: MVRBackgroundProcessor (Background Tasks)")
    logger.info("=" * 70 + "\n")
    
    test_results = {
        "passed": [],
        "failed": []
    }
    
    # Test Suite 1: MVRRepository
    logger.info("\n" + "🔵" * 35)
    logger.info("TEST SUITE 1: MVRRepository")
    logger.info("🔵" * 35 + "\n")
    
    try:
        from tests.test_mvr_repository import run_all_tests as test_repository
        await test_repository()
        test_results["passed"].append("MVRRepository")
        logger.info("\n✅ MVRRepository tests: PASSED\n")
    except Exception as e:
        test_results["failed"].append(("MVRRepository", str(e)))
        logger.error(f"\n❌ MVRRepository tests: FAILED - {e}\n")
    
    # Test Suite 2: MVRService
    logger.info("\n" + "🟢" * 35)
    logger.info("TEST SUITE 2: MVRService")
    logger.info("🟢" * 35 + "\n")
    
    try:
        from tests.test_mvr_service import run_all_tests as test_service
        await test_service()
        test_results["passed"].append("MVRService")
        logger.info("\n✅ MVRService tests: PASSED\n")
    except Exception as e:
        test_results["failed"].append(("MVRService", str(e)))
        logger.error(f"\n❌ MVRService tests: FAILED - {e}\n")
    
    # Test Suite 3: MVRMatcher
    logger.info("\n" + "🟡" * 35)
    logger.info("TEST SUITE 3: MVRMatcher")
    logger.info("🟡" * 35 + "\n")
    
    try:
        from tests.test_mvr_matcher import run_all_tests as test_matcher
        await test_matcher()
        test_results["passed"].append("MVRMatcher")
        logger.info("\n✅ MVRMatcher tests: PASSED\n")
    except Exception as e:
        test_results["failed"].append(("MVRMatcher", str(e)))
        logger.error(f"\n❌ MVRMatcher tests: FAILED - {e}\n")
    
    # Test Suite 4: MVRBackgroundProcessor
    logger.info("\n" + "🟣" * 35)
    logger.info("TEST SUITE 4: MVRBackgroundProcessor")
    logger.info("🟣" * 35 + "\n")
    
    try:
        from tests.test_mvr_background_processor import (
            run_all_tests as test_background
        )
        await test_background()
        test_results["passed"].append("MVRBackgroundProcessor")
        logger.info("\n✅ MVRBackgroundProcessor tests: PASSED\n")
    except Exception as e:
        test_results["failed"].append(("MVRBackgroundProcessor", str(e)))
        logger.error(f"\n❌ MVRBackgroundProcessor tests: FAILED - {e}\n")
    
    # Print final summary
    logger.info("\n" + "=" * 70)
    logger.info("FINAL TEST RESULTS")
    logger.info("=" * 70)
    
    total_suites = len(test_results["passed"]) + len(test_results["failed"])
    passed_count = len(test_results["passed"])
    failed_count = len(test_results["failed"])
    
    logger.info(f"\nTotal Test Suites: {total_suites}")
    logger.info(f"✅ Passed: {passed_count}")
    logger.info(f"❌ Failed: {failed_count}")
    
    if test_results["passed"]:
        logger.info("\n✅ PASSED SUITES:")
        for suite in test_results["passed"]:
            logger.info(f"   - {suite}")
    
    if test_results["failed"]:
        logger.info("\n❌ FAILED SUITES:")
        for suite, error in test_results["failed"]:
            logger.info(f"   - {suite}")
            logger.info(f"     Error: {error[:100]}...")
    
    logger.info("\n" + "=" * 70)
    
    if failed_count == 0:
        logger.info("🎉 ALL TESTS PASSED! Phase 3 is ready for Phase 4!")
        logger.info("=" * 70 + "\n")
        return True
    else:
        logger.error(
            f"⚠️ {failed_count} test suite(s) failed. "
            "Please review and fix."
        )
        logger.info("=" * 70 + "\n")
        return False


async def run_quick_smoke_test():
    """Run a quick smoke test to verify basic functionality."""
    
    logger.info("\n" + "=" * 70)
    logger.info("QUICK SMOKE TEST - Phase 3 Components")
    logger.info("=" * 70 + "\n")
    
    try:
        import asyncpg
        import os
        from database.mvr_repository import MVRRepository
        from services.mvr_service import MVRService
        from services.mvr_matcher import MVRMatcher
        from ml.mvr_processor import MVRProcessor
        from background.mvr_background_processor import (
            MVRBackgroundProcessor
        )
        import numpy as np
        from uuid import uuid4
        
        # Create connection pool
        logger.info("1. Creating database connection...")
        pool = await asyncpg.create_pool(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            user=os.getenv("DB_USER", "ppl_user"),
            password=os.getenv("DB_PASSWORD", "ppl_password"),
            database=os.getenv("DB_NAME", "ppl_meta"),
            min_size=2,
            max_size=10
        )
        logger.info("   ✅ Database connected")
        
        # Initialize components
        logger.info("2. Initializing MVR components...")
        repository = MVRRepository(connection_pool=pool)
        ml_processor = MVRProcessor()
        service = MVRService(
            repository=repository,
            ml_processor=ml_processor
        )
        matcher = MVRMatcher(
            repository=repository,
            ml_processor=ml_processor
        )
        background_processor = MVRBackgroundProcessor(
            mvr_service=service,
            mvr_matcher=matcher,
            max_retries=3,
            retry_delay=1.0
        )
        logger.info("   ✅ All components initialized")
        
        # Test basic operations
        logger.info("3. Testing basic operations...")
        
        # Create Individual first (required for FK)
        # Create test tracking session with all required fields
        session_uuid = uuid4()
        user_id = "test_user_" + session_uuid.hex[:8]
        now = datetime.now()
        algorithm_config = {
            "max_gap_seconds": 5.0,
            "iou_threshold": 0.3,
            "min_overlap_confidence": 0.5
        }
        await pool.execute("""
            INSERT INTO tracking_sessions (
                session_uuid, user_id, collections, start_time, end_time, 
                status, config_hash, algorithm_config
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
        """, session_uuid, user_id, ['test_collection'], now, 
             now + timedelta(hours=1), 'running', 'test_hash', json.dumps(algorithm_config))
        
        # Create Individual
        individual_uuid = uuid4()
        await pool.execute("""
            INSERT INTO individuals (
                individual_uuid,
                individual_id,
                confidence_score
            ) VALUES ($1, $2, $3)
        """, individual_uuid, f"ind_{individual_uuid.hex[:8]}", 0.85)
        
        # Link to session
        await pool.execute("""
            INSERT INTO session_individuals (
                session_uuid,
                individual_uuid,
                processing_type
            ) VALUES ($1, $2, $3)
        """, session_uuid, individual_uuid, 'new')  # valid: 'new', 'cached', 'merged', 'extended'
        
        logger.info(f"   ✅ Created test Individual: {individual_uuid}")
        
        # Create MVR
        embedding = np.random.randn(512).astype(np.float32)
        embedding = embedding / np.linalg.norm(embedding)
        
        mvr_result = await repository.create_mvr_people(
            face_embedding=embedding,
            featured_individual_uuid=individual_uuid,
            quality_score=0.85
        )
        mvr_uuid = mvr_result['mvr_people_uuid']
        logger.info(f"   ✅ Created MVR: {mvr_uuid}")
        
        # Retrieve MVR
        mvr = await repository.get_mvr_people_by_uuid(mvr_uuid)
        assert mvr is not None
        logger.info("   ✅ Retrieved MVR successfully")
        
        # Get config
        config = await repository.get_matching_config()
        assert config["similarity_threshold"] == 0.85
        logger.info("   ✅ Retrieved matching config")
        
        # Get statistics
        stats = await background_processor.get_statistics()
        logger.info(
            f"   ✅ Background processor stats: "
            f"{stats['completed']} completed, {stats['failed']} failed"
        )
        
        await pool.close()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ SMOKE TEST PASSED - All components working!")
        logger.info("=" * 70 + "\n")
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ SMOKE TEST FAILED: {e}", exc_info=True)
        logger.info("=" * 70 + "\n")
        return False


def main():
    """Main entry point."""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--smoke":
        # Run quick smoke test
        success = asyncio.run(run_quick_smoke_test())
    else:
        # Run full test suite
        success = asyncio.run(run_all_phase3_tests())
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
