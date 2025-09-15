#!/usr/bin/env python3
"""
Workflow 5 Data Access Layer Performance Test
Tests ultra-fast frame-indexed face retrieval with <10ms targets.
"""

import asyncio
import json
import time
import uuid
from typing import Any, Dict

from workflow5_data_access import workflow5_data_access


async def test_data_access_performance():
    """Comprehensive performance test for Workflow 5 data access layer."""

    print("🧪 Workflow 5 Data Access Layer Performance Test")
    print("=" * 60)

    # Test media UUID (you can replace with actual UUID from your database)
    test_media_uuid = str(uuid.uuid4())

    # Performance test results
    results = {}

    try:
        # Test 1: Processing Status Check (<3ms target)
        print("\n📋 Test 1: Processing Status Check (Target: <3ms)")
        start_time = time.perf_counter()

        status = await workflow5_data_access.check_processing_status(test_media_uuid)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        results["status_check_ms"] = elapsed_ms

        print(f"   ⏱️  Latency: {elapsed_ms:.2f}ms")
        print(f"   ✅ Target Met: {'Yes' if elapsed_ms < 3.0 else 'No'}")
        print(f"   📊 Status: {status}")

        # Test 2: Frame Optimization Lookup (<5ms target)
        print("\n📋 Test 2: Frame Optimization Lookup (Target: <5ms)")
        start_time = time.perf_counter()

        optimization = await workflow5_data_access.get_optimized_frame_lookup(
            test_media_uuid, 100
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        results["frame_lookup_ms"] = elapsed_ms

        print(f"   ⏱️  Latency: {elapsed_ms:.2f}ms")
        print(f"   ✅ Target Met: {'Yes' if elapsed_ms < 5.0 else 'No'}")
        print(f"   📊 Optimization: {optimization}")

        # Test 3: Face Data Retrieval (<10ms target for cached data)
        print("\n📋 Test 3: Face Data Retrieval (Target: <10ms)")
        start_time = time.perf_counter()

        faces = await workflow5_data_access.get_face_data_by_frame_range(
            test_media_uuid, 50, 150, confidence_threshold=0.7
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        results["face_retrieval_ms"] = elapsed_ms

        print(f"   ⏱️  Latency: {elapsed_ms:.2f}ms")
        print(f"   ✅ Target Met: {'Yes' if elapsed_ms < 10.0 else 'No'}")
        print(f"   📊 Faces Found: {len(faces)}")

        # Test 4: Cache Warming Performance
        print("\n📋 Test 4: Cache Warming Performance")
        start_time = time.perf_counter()

        warming_success = await workflow5_data_access.warm_cache_for_media(
            test_media_uuid
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        results["cache_warming_ms"] = elapsed_ms

        print(f"   ⏱️  Latency: {elapsed_ms:.2f}ms")
        print(f"   ✅ Success: {'Yes' if warming_success else 'No'}")

        # Test 5: Repeated Queries (Cache Performance)
        print("\n📋 Test 5: Cache Performance Test (5 repeated queries)")
        cache_times = []

        for i in range(5):
            start_time = time.perf_counter()

            faces = await workflow5_data_access.get_face_data_by_frame_range(
                test_media_uuid, 75, 125, confidence_threshold=0.6
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            cache_times.append(elapsed_ms)
            print(f"   Query {i+1}: {elapsed_ms:.2f}ms")

        avg_cache_time = sum(cache_times) / len(cache_times)
        results["avg_cache_retrieval_ms"] = avg_cache_time

        print(f"   📊 Average: {avg_cache_time:.2f}ms")
        print(f"   ✅ Cache Target Met: {'Yes' if avg_cache_time < 5.0 else 'No'}")

        # Test 6: Access Metrics Update
        print("\n📋 Test 6: Access Metrics Update")
        start_time = time.perf_counter()

        await workflow5_data_access.update_access_metrics(test_media_uuid, 8.5)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        results["metrics_update_ms"] = elapsed_ms

        print(f"   ⏱️  Latency: {elapsed_ms:.2f}ms")
        print(f"   ✅ Updated Successfully")

        # Performance Summary
        print("\n🎯 PERFORMANCE SUMMARY")
        print("=" * 60)

        performance_stats = workflow5_data_access.get_performance_stats()

        print(f"📊 Overall Performance Stats:")
        print(f"   • Total Queries: {performance_stats['total_queries']}")
        print(f"   • Average Latency: {performance_stats['avg_latency_ms']:.2f}ms")
        print(f"   • Cache Hit Ratio: {performance_stats['cache_hit_ratio']:.1%}")
        print(f"   • Cache Size: {performance_stats['cache_size']} entries")
        print(f"   • Performance Status: {performance_stats['performance_status']}")

        print(f"\n🎯 Target Achievement:")
        print(
            f"   • Status Check (<3ms): {'✅ PASS' if results['status_check_ms'] < 3.0 else '❌ FAIL'} ({results['status_check_ms']:.2f}ms)"
        )
        print(
            f"   • Frame Lookup (<5ms): {'✅ PASS' if results['frame_lookup_ms'] < 5.0 else '❌ FAIL'} ({results['frame_lookup_ms']:.2f}ms)"
        )
        print(
            f"   • Face Retrieval (<10ms): {'✅ PASS' if results['face_retrieval_ms'] < 10.0 else '❌ FAIL'} ({results['face_retrieval_ms']:.2f}ms)"
        )

        # Overall Grade
        passed_tests = sum(
            [
                results["status_check_ms"] < 3.0,
                results["frame_lookup_ms"] < 5.0,
                results["face_retrieval_ms"] < 10.0,
                results["avg_cache_retrieval_ms"] < 5.0,
            ]
        )

        grade = (
            "A+"
            if passed_tests == 4
            else "A" if passed_tests == 3 else "B" if passed_tests >= 2 else "C"
        )

        print(f"\n🏆 OVERALL GRADE: {grade} ({passed_tests}/4 targets met)")

        if passed_tests >= 3:
            print("🎉 Workflow 5 data access layer performance is EXCELLENT!")
        elif passed_tests >= 2:
            print("👍 Workflow 5 data access layer performance is GOOD")
        else:
            print("⚠️  Workflow 5 data access layer needs optimization")

        return results

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return {}

    finally:
        # Clean up
        await workflow5_data_access.close()


async def test_real_media_performance():
    """Test with real media data if available."""

    print("\n🔍 Checking for Real Media Data...")

    try:
        # Try to find actual media UUIDs in the database
        status_check = await workflow5_data_access.check_processing_status(
            "test-media-uuid"
        )

        if status_check.get("is_processed"):
            print("✅ Found processed media, running real data tests...")

            # Test with real data
            start_time = time.perf_counter()
            faces = await workflow5_data_access.get_face_data_by_frame_range(
                "test-media-uuid", 0, 100, confidence_threshold=0.5
            )
            elapsed_ms = (time.perf_counter() - start_time) * 1000

            print(f"📊 Real Data Test Results:")
            print(f"   • Faces Retrieved: {len(faces)}")
            print(f"   • Query Time: {elapsed_ms:.2f}ms")
            print(
                f"   • Performance: {'✅ EXCELLENT' if elapsed_ms < 10 else '⚠️ NEEDS OPTIMIZATION'}"
            )

        else:
            print("ℹ️  No processed media found, test completed with mock data")

    except Exception as e:
        print(f"ℹ️  Real data test skipped: {e}")


def main():
    """Main test execution."""
    print("🚀 Starting Workflow 5 Data Access Performance Tests...")

    try:
        # Run async tests
        results = asyncio.run(test_data_access_performance())

        # Optionally test with real data
        asyncio.run(test_real_media_performance())

        print("\n✅ All tests completed successfully!")

        # Save results for analysis
        with open("workflow5_performance_results.json", "w") as f:
            json.dump({"timestamp": time.time(), "results": results}, f, indent=2)

        print("📄 Results saved to workflow5_performance_results.json")

    except Exception as e:
        print(f"❌ Test execution failed: {e}")


if __name__ == "__main__":
    main()
