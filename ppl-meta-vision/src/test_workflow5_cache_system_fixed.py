#!/usr/bin/env python3
"""
Workflow 5 Cache System Test with Database Fixes
==============================================

Updated test suite that properly sets up the database environment
before testing the cache system functionality.
"""

import asyncio
import time
import uuid

from workflow5_cache_manager import Workflow5CacheManager
from workflow5_data_access import Workflow5DataAccess
from workflow5_database_fixes import Workflow5DatabaseFixer


async def test_cache_system_with_fixes():
    """
    Test the cache system with proper database setup.
    """
    print("🚀 Testing Workflow 5 Cache System with Database Fixes...")
    print("=" * 70)

    # Initialize components
    data_access = Workflow5DataAccess()
    fixer = Workflow5DatabaseFixer(data_access)
    cache_manager = Workflow5CacheManager()

    # Test media UUID
    test_media_uuid = str(uuid.uuid4())
    print(f"📋 Test Media UUID: {test_media_uuid}")

    try:
        # Step 1: Setup database environment
        print("\n📋 Step 1: Setting up database environment...")
        setup_success = await fixer.setup_test_environment(test_media_uuid)
        print(f"   Database Setup: {'✅ Success' if setup_success else '❌ Failed'}")

        if not setup_success:
            print("❌ Database setup failed, skipping cache tests")
            return False

        # Step 2: Test cache warming
        print("\n📋 Step 2: Testing cache warming...")
        start_time = time.perf_counter()
        warming_success = await cache_manager.warm_cache_for_media(test_media_uuid)
        warming_time = (time.perf_counter() - start_time) * 1000
        print(f"   Cache Warming: {'✅ Success' if warming_success else '❌ Failed'}")
        print(f"   Warming Time: {warming_time:.2f}ms")

        # Step 3: Test face data retrieval
        print("\n📋 Step 3: Testing face data retrieval...")
        start_time = time.perf_counter()
        face_data = await cache_manager.get_cached_faces(test_media_uuid, (0, 10))
        retrieval_time = (time.perf_counter() - start_time) * 1000
        print(f"   Data Retrieval: {'✅ Success' if face_data else '❌ Failed'}")
        print(f"   Retrieval Time: {retrieval_time:.2f}ms")
        print(f"   Faces Retrieved: {len(face_data) if face_data else 0}")

        # Step 4: Test cache performance metrics
        print("\n📋 Step 4: Testing cache performance...")
        metrics = await cache_manager.get_cache_performance_metrics()
        print(
            f"   Performance Metrics: {'✅ Available' if metrics else '❌ Unavailable'}"
        )
        if metrics:
            print(f"   Cache Hit Ratio: {metrics.cache_hit_ratio:.1f}%")
            print(f"   Average Retrieval: {metrics.average_retrieval_time_ms:.2f}ms")
            print(f"   Cache Size: {metrics.cache_size_mb:.2f} MB")

        # Step 5: Test cache invalidation
        print("\n📋 Step 5: Testing cache invalidation...")
        start_time = time.perf_counter()
        invalidation_success = await cache_manager.invalidate_cache(test_media_uuid)
        invalidation_time = (time.perf_counter() - start_time) * 1000
        print(
            f"   Cache Invalidation: {'✅ Success' if invalidation_success else '❌ Failed'}"
        )
        print(f"   Invalidation Time: {invalidation_time:.2f}ms")

        # Step 6: Performance assessment
        print("\n📋 Step 6: Performance Assessment...")
        performance_grade = "A+"
        if warming_time > 1000:
            performance_grade = "B"
        if retrieval_time > 10:
            performance_grade = "C"

        print(f"   Overall Performance Grade: {performance_grade}")
        print(
            f"   Cache Warming Target (<1000ms): {'✅ Met' if warming_time <= 1000 else '❌ Missed'}"
        )
        print(
            f"   Retrieval Target (<10ms): {'✅ Met' if retrieval_time <= 10 else '❌ Missed'}"
        )

        # Cleanup
        print("\n📋 Step 7: Cleaning up...")
        cleanup_success = await fixer.cleanup_test_data(test_media_uuid)
        print(f"   Cleanup: {'✅ Success' if cleanup_success else '❌ Failed'}")

        print("\n🎯 Cache System Test with Database Fixes Complete!")
        print(
            f"🏆 Overall Success: {'✅ Yes' if all([setup_success, warming_success, cleanup_success]) else '❌ No'}"
        )

        return True

    except Exception as e:
        print(f"\n❌ Cache system test failed: {e}")
        # Try to cleanup anyway
        try:
            await fixer.cleanup_test_data(test_media_uuid)
        except:
            pass
        return False

    finally:
        await data_access.close()


if __name__ == "__main__":
    asyncio.run(test_cache_system_with_fixes())
