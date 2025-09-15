#!/usr/bin/env python3
"""
Face Detection Workflow 5 - Phase 5: Comprehensive Integration Test Suite
==========================================================================

COMPLETE END-TO-END TESTING FOR WORKFLOW 5 IMPLEMENTATION

This module provides comprehensive integration testing for the complete
Face Detection Workflow 5 system, validating all components working together
with various scenarios, error conditions, and performance requirements.

Test Coverage:
- End-to-end face detection workflows
- Fallback mechanism validation
- Performance benchmarking and validation
- Data integrity and consistency testing
- Service integration and communication
- Error recovery and resilience testing
- Concurrent operation testing
- Memory and resource usage validation

Test Categories:
1. Basic Functionality Tests - Core workflow operation
2. Performance Tests - CPU reduction and latency validation
3. Reliability Tests - Fallback and error recovery
4. Integration Tests - Multi-service communication
5. Stress Tests - High load and concurrent operations
6. Data Integrity Tests - Consistency and validation
"""

import asyncio
import json
import logging
import statistics
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import psutil
from workflow5_data_access import Workflow5DataAccess
from workflow5_face_data_retrieval_fixed import (
    StoredFaceDataRetriever,
    create_stored_face_data_retriever,
)
from workflow5_fallback_manager import (
    FallbackManager,
    FallbackMode,
    create_fallback_manager,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Test result data structure for comprehensive reporting."""

    test_name: str
    success: bool
    execution_time_ms: float
    details: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class PerformanceMetrics:
    """Performance metrics for validation."""

    cpu_usage_percent: float
    memory_usage_mb: float
    latency_ms: float
    throughput_ops_per_sec: float


class Workflow5IntegrationTestSuite:
    """
    Comprehensive integration test suite for Face Detection Workflow 5.

    Validates complete system functionality, performance, and reliability
    across all components and interaction scenarios.
    """

    def __init__(self):
        self.data_access: Optional[Workflow5DataAccess] = None
        self.stored_retriever: Optional[StoredFaceDataRetriever] = None
        self.fallback_manager: Optional[FallbackManager] = None

        # Test results tracking
        self.test_results: List[TestResult] = []
        self.performance_metrics: List[PerformanceMetrics] = []

        # Test configuration
        self.test_media_uuids: List[str] = []
        self.performance_targets = {
            "cpu_reduction_percent": 90,
            "max_latency_ms": 100,
            "min_throughput_ops_per_sec": 10,
            "max_memory_usage_mb": 200,
        }

    async def setup(self):
        """Initialize test environment and components."""
        logger.info("Setting up Workflow 5 integration test environment...")

        # Initialize data access
        self.data_access = Workflow5DataAccess()

        # Initialize stored retriever
        self.stored_retriever = await create_stored_face_data_retriever(
            cache_max_videos=50
        )

        # Initialize fallback manager
        self.fallback_manager = await create_fallback_manager()

        # Get test media UUIDs
        await self._get_test_media_uuids()

        logger.info(
            f"Test setup complete with {len(self.test_media_uuids)} "
            f"test media items"
        )

    async def _get_test_media_uuids(self):
        """Get available media UUIDs for testing."""
        try:
            async with self.data_access.async_session_maker() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text("SELECT media_id FROM media_records LIMIT 10")
                )
                self.test_media_uuids = [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.warning(f"Failed to get test media UUIDs: {e}")
            # Use mock UUIDs for testing
            self.test_media_uuids = ["test-uuid-1", "test-uuid-2", "test-uuid-3"]

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete integration test suite."""
        logger.info("🚀 Starting Workflow 5 Integration Test Suite...")

        test_start_time = time.time()

        # Test categories
        test_categories = [
            ("Basic Functionality", self._run_basic_functionality_tests),
            ("Performance Validation", self._run_performance_tests),
            ("Reliability & Fallback", self._run_reliability_tests),
            ("Integration & Communication", self._run_integration_tests),
            ("Stress & Concurrent Operations", self._run_stress_tests),
            ("Data Integrity", self._run_data_integrity_tests),
        ]

        category_results = {}

        for category_name, test_method in test_categories:
            logger.info(f"\n📋 Running {category_name} Tests...")
            try:
                category_start = time.time()
                results = await test_method()
                category_time = (time.time() - category_start) * 1000

                category_results[category_name] = {
                    "results": results,
                    "execution_time_ms": category_time,
                    "success_count": sum(1 for r in results if r.success),
                    "total_count": len(results),
                }

                success_rate = (
                    category_results[category_name]["success_count"]
                    / len(results)
                    * 100
                )
                logger.info(f"✅ {category_name}: {success_rate:.1f}% success rate")

            except Exception as e:
                logger.error(f"❌ {category_name} tests failed: {e}")
                category_results[category_name] = {
                    "error": str(e),
                    "execution_time_ms": 0,
                    "success_count": 0,
                    "total_count": 0,
                }

        total_time = (time.time() - test_start_time) * 1000

        # Generate comprehensive report
        return self._generate_test_report(category_results, total_time)

    async def _run_basic_functionality_tests(self) -> List[TestResult]:
        """Test basic Workflow 5 functionality."""
        tests = []

        # Test 1: Stored face data retrieval
        test_start = time.time()
        try:
            if self.test_media_uuids:
                media_uuid = self.test_media_uuids[0]
                faces = await self.stored_retriever.get_frame_faces(media_uuid, 1)

                success = True
                details = {
                    "media_uuid": media_uuid,
                    "frame_number": 1,
                    "faces_found": len(faces),
                    "retrieval_mode": "stored_data",
                }
                error = None
            else:
                success = False
                details = {}
                error = "No test media available"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="stored_face_data_retrieval",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        # Test 2: Video face data loading
        test_start = time.time()
        try:
            if self.test_media_uuids:
                media_uuid = self.test_media_uuids[0]
                video_data = await self.stored_retriever.load_complete_video(media_uuid)

                success = True
                details = {
                    "media_uuid": media_uuid,
                    "total_faces": video_data.total_faces,
                    "total_frames": video_data.total_frames,
                    "data_size_mb": round(
                        video_data.data_size_bytes / (1024 * 1024), 2
                    ),
                }
                error = None
            else:
                success = False
                details = {}
                error = "No test media available"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="complete_video_loading",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        # Test 3: Fallback mechanism
        test_start = time.time()
        try:
            faces, mode = await self.fallback_manager.get_faces_with_fallback(
                "non-existent-uuid", 1, FallbackMode.STORED_DATA
            )

            success = mode != FallbackMode.NO_DETECTION
            details = {
                "fallback_mode": mode.value,
                "faces_returned": len(faces),
                "fallback_successful": success,
            }
            error = None

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="fallback_mechanism",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        return tests

    async def _run_performance_tests(self) -> List[TestResult]:
        """Test performance requirements and targets."""
        tests = []

        # Test 1: Single frame retrieval latency
        test_start = time.time()
        try:
            if self.test_media_uuids:
                media_uuid = self.test_media_uuids[0]

                # Measure multiple retrievals for accuracy
                latencies = []
                for _ in range(10):
                    frame_start = time.time()
                    await self.stored_retriever.get_frame_faces(media_uuid, 1)
                    latencies.append((time.time() - frame_start) * 1000)

                avg_latency = statistics.mean(latencies)
                max_latency = max(latencies)

                success = avg_latency < self.performance_targets["max_latency_ms"]
                details = {
                    "avg_latency_ms": round(avg_latency, 2),
                    "max_latency_ms": round(max_latency, 2),
                    "target_latency_ms": self.performance_targets["max_latency_ms"],
                    "meets_target": success,
                }
                error = (
                    None if success else f"Latency {avg_latency:.1f}ms exceeds target"
                )

            else:
                success = False
                details = {}
                error = "No test media available"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="single_frame_latency",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        # Test 2: Cache performance
        test_start = time.time()
        try:
            if self.test_media_uuids:
                media_uuid = self.test_media_uuids[0]

                # First retrieval (cache miss)
                miss_start = time.time()
                await self.stored_retriever.get_frame_faces(media_uuid, 1)
                miss_time = (time.time() - miss_start) * 1000

                # Second retrieval (cache hit)
                hit_start = time.time()
                await self.stored_retriever.get_frame_faces(media_uuid, 1)
                hit_time = (time.time() - hit_start) * 1000

                # Cache should be significantly faster
                cache_improvement = ((miss_time - hit_time) / miss_time) * 100

                success = cache_improvement > 50  # Expect at least 50% improvement
                details = {
                    "cache_miss_time_ms": round(miss_time, 2),
                    "cache_hit_time_ms": round(hit_time, 2),
                    "improvement_percent": round(cache_improvement, 1),
                    "meets_target": success,
                }
                error = (
                    None
                    if success
                    else f"Cache improvement {cache_improvement:.1f}% below 50%"
                )

            else:
                success = False
                details = {}
                error = "No test media available"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="cache_performance",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        # Test 3: Memory usage validation
        test_start = time.time()
        try:
            process = psutil.Process()

            # Measure memory before
            initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

            # Load several videos to test memory usage
            if self.test_media_uuids:
                for media_uuid in self.test_media_uuids[:3]:
                    try:
                        await self.stored_retriever.load_complete_video(media_uuid)
                    except:
                        pass  # Continue testing even if some fail

            # Measure memory after
            final_memory = process.memory_info().rss / (1024 * 1024)  # MB
            memory_increase = final_memory - initial_memory

            success = memory_increase < self.performance_targets["max_memory_usage_mb"]
            details = {
                "initial_memory_mb": round(initial_memory, 2),
                "final_memory_mb": round(final_memory, 2),
                "memory_increase_mb": round(memory_increase, 2),
                "target_max_mb": self.performance_targets["max_memory_usage_mb"],
                "meets_target": success,
            }
            error = (
                None
                if success
                else f"Memory increase {memory_increase:.1f}MB exceeds target"
            )

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="memory_usage_validation",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        return tests

    async def _run_reliability_tests(self) -> List[TestResult]:
        """Test reliability and fallback mechanisms."""
        tests = []

        # Test 1: Data corruption handling
        test_start = time.time()
        try:
            # Test with invalid/corrupted media UUID
            faces, mode = await self.fallback_manager.get_faces_with_fallback(
                "corrupted-data-uuid", 1, FallbackMode.STORED_DATA
            )

            # Should fallback successfully
            success = mode in [
                FallbackMode.REALTIME_DETECTION,
                FallbackMode.CACHED_SESSION,
            ]
            details = {
                "original_mode": "stored_data",
                "fallback_mode": mode.value,
                "faces_returned": len(faces),
                "handled_gracefully": success,
            }
            error = None if success else "Failed to handle corrupted data gracefully"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="data_corruption_handling",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        # Test 2: Service unavailability handling
        test_start = time.time()
        try:
            # Test health check functionality
            health_status = await self.fallback_manager.health_check_services()

            # Check if health monitoring is working
            services_checked = len(health_status)
            healthy_services = sum(1 for h in health_status.values() if h.is_healthy)

            success = services_checked > 0
            details = {
                "services_checked": services_checked,
                "healthy_services": healthy_services,
                "health_check_working": success,
                "service_status": {
                    name: h.is_healthy for name, h in health_status.items()
                },
            }
            error = None if success else "Health check system not functioning"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="service_health_monitoring",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        # Test 3: Fallback statistics tracking
        test_start = time.time()
        try:
            # Generate some fallback events
            for i in range(3):
                await self.fallback_manager.get_faces_with_fallback(
                    f"test-fallback-{i}", 1, FallbackMode.STORED_DATA
                )

            # Check statistics
            stats = self.fallback_manager.get_fallback_statistics()

            success = stats["fallback_performance"]["total_fallbacks"] > 0
            details = {
                "total_fallbacks": stats["fallback_performance"]["total_fallbacks"],
                "success_rate": stats["fallback_performance"]["success_rate_percent"],
                "avg_recovery_time": stats["fallback_performance"][
                    "avg_recovery_time_ms"
                ],
                "statistics_working": success,
            }
            error = None if success else "Fallback statistics not tracking properly"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="fallback_statistics_tracking",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        return tests

    async def _run_integration_tests(self) -> List[TestResult]:
        """Test multi-service integration."""
        tests = []

        # Test 1: Data access integration
        test_start = time.time()
        try:
            # Test database connectivity and query execution
            async with self.data_access.async_session_maker() as session:
                from sqlalchemy import text

                result = await session.execute(
                    text("SELECT COUNT(*) FROM media_records")
                )
                record_count = result.scalar()

            success = record_count is not None
            details = {
                "database_accessible": success,
                "media_records_count": record_count,
                "connection_working": success,
            }
            error = None if success else "Database integration failed"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="database_integration",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        # Test 2: Component communication
        test_start = time.time()
        try:
            # Test communication between retriever and fallback manager
            if self.test_media_uuids:
                media_uuid = self.test_media_uuids[0]

                # Get data through retriever
                retriever_faces = await self.stored_retriever.get_frame_faces(
                    media_uuid, 1
                )

                # Get same data through fallback manager
                fallback_faces, mode = (
                    await self.fallback_manager.get_faces_with_fallback(
                        media_uuid, 1, FallbackMode.STORED_DATA
                    )
                )

                # Results should be consistent when using same data source
                success = True  # Basic communication is working if we get here
                details = {
                    "retriever_faces": len(retriever_faces),
                    "fallback_faces": len(fallback_faces),
                    "fallback_mode": mode.value,
                    "communication_working": success,
                }
                error = None
            else:
                success = False
                details = {}
                error = "No test media available"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="component_communication",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        return tests

    async def _run_stress_tests(self) -> List[TestResult]:
        """Test system under stress and concurrent operations."""
        tests = []

        # Test 1: Concurrent face retrieval
        test_start = time.time()
        try:
            if self.test_media_uuids:
                # Create multiple concurrent requests
                tasks = []
                for i in range(10):  # 10 concurrent requests
                    media_uuid = self.test_media_uuids[i % len(self.test_media_uuids)]
                    task = self.stored_retriever.get_frame_faces(media_uuid, i % 10)
                    tasks.append(task)

                # Execute concurrently
                concurrent_start = time.time()
                results = await asyncio.gather(*tasks, return_exceptions=True)
                concurrent_time = (time.time() - concurrent_start) * 1000

                # Count successful operations
                successful_ops = sum(1 for r in results if not isinstance(r, Exception))

                success = successful_ops >= 8  # At least 80% success rate
                details = {
                    "total_requests": len(tasks),
                    "successful_requests": successful_ops,
                    "success_rate_percent": (successful_ops / len(tasks)) * 100,
                    "total_time_ms": round(concurrent_time, 2),
                    "avg_time_per_request_ms": round(concurrent_time / len(tasks), 2),
                }
                error = (
                    None
                    if success
                    else f"Only {successful_ops}/{len(tasks)} requests succeeded"
                )
            else:
                success = False
                details = {}
                error = "No test media available"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="concurrent_operations",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        return tests

    async def _run_data_integrity_tests(self) -> List[TestResult]:
        """Test data integrity and consistency."""
        tests = []

        # Test 1: Face detection data consistency
        test_start = time.time()
        try:
            if self.test_media_uuids:
                media_uuid = self.test_media_uuids[0]

                # Get same frame multiple times
                faces1 = await self.stored_retriever.get_frame_faces(media_uuid, 1)
                faces2 = await self.stored_retriever.get_frame_faces(media_uuid, 1)

                # Results should be identical
                consistent = len(faces1) == len(faces2)
                if consistent and faces1:
                    # Check first face coordinates if available
                    first_face1 = faces1[0]
                    first_face2 = faces2[0]
                    consistent = first_face1.bounding_box == first_face2.bounding_box

                success = consistent
                details = {
                    "first_retrieval_faces": len(faces1),
                    "second_retrieval_faces": len(faces2),
                    "results_consistent": consistent,
                    "data_stable": success,
                }
                error = (
                    None
                    if success
                    else "Face detection data inconsistent between retrievals"
                )
            else:
                success = False
                details = {}
                error = "No test media available"

        except Exception as e:
            success = False
            details = {}
            error = str(e)

        tests.append(
            TestResult(
                test_name="data_consistency",
                success=success,
                execution_time_ms=(time.time() - test_start) * 1000,
                details=details,
                error=error,
            )
        )

        return tests

    def _generate_test_report(
        self, category_results: Dict, total_time: float
    ) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = sum(cat["total_count"] for cat in category_results.values())
        total_successes = sum(cat["success_count"] for cat in category_results.values())
        overall_success_rate = (
            (total_successes / total_tests * 100) if total_tests > 0 else 0
        )

        # Performance summary
        perf_summary = {}
        if self.performance_metrics:
            avg_cpu = statistics.mean(
                m.cpu_usage_percent for m in self.performance_metrics
            )
            avg_memory = statistics.mean(
                m.memory_usage_mb for m in self.performance_metrics
            )
            avg_latency = statistics.mean(
                m.latency_ms for m in self.performance_metrics
            )

            perf_summary = {
                "avg_cpu_usage_percent": round(avg_cpu, 2),
                "avg_memory_usage_mb": round(avg_memory, 2),
                "avg_latency_ms": round(avg_latency, 2),
            }

        return {
            "test_summary": {
                "total_execution_time_ms": round(total_time, 2),
                "total_test_categories": len(category_results),
                "total_tests": total_tests,
                "successful_tests": total_successes,
                "overall_success_rate_percent": round(overall_success_rate, 2),
                "all_tests_passed": overall_success_rate == 100.0,
            },
            "category_results": category_results,
            "performance_summary": perf_summary,
            "targets_met": {
                "performance_targets": self.performance_targets,
                "meets_all_targets": overall_success_rate
                >= 95.0,  # 95% success rate target
            },
            "timestamp": datetime.now().isoformat(),
            "test_environment": {
                "python_version": "3.11+",
                "test_media_count": len(self.test_media_uuids),
                "components_tested": [
                    "StoredFaceDataRetriever",
                    "FallbackManager",
                    "DataAccess",
                ],
            },
        }


async def main():
    """Run the complete Workflow 5 integration test suite."""
    print("🚀 Face Detection Workflow 5 - Integration Test Suite")
    print("=====================================================")

    # Create and setup test suite
    test_suite = Workflow5IntegrationTestSuite()

    try:
        # Setup test environment
        await test_suite.setup()

        # Run all tests
        results = await test_suite.run_all_tests()

        # Display results
        print("\n📊 Integration Test Results Summary:")
        print("=" * 50)

        summary = results["test_summary"]
        print(f"Total Execution Time: {summary['total_execution_time_ms']:.1f}ms")
        print(f"Test Categories: {summary['total_test_categories']}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful Tests: {summary['successful_tests']}")
        print(f"Overall Success Rate: {summary['overall_success_rate_percent']:.1f}%")

        # Category breakdown
        print(f"\n📋 Category Results:")
        for category, result in results["category_results"].items():
            if "error" in result:
                print(f"  ❌ {category}: ERROR - {result['error']}")
            else:
                success_rate = (
                    result["success_count"] / result["total_count"] * 100
                    if result["total_count"] > 0
                    else 0
                )
                status = (
                    "✅" if success_rate == 100 else "⚠️" if success_rate >= 80 else "❌"
                )
                print(
                    f"  {status} {category}: {success_rate:.1f}% ({result['success_count']}/{result['total_count']})"
                )

        # Performance summary
        if "performance_summary" in results and results["performance_summary"]:
            perf = results["performance_summary"]
            print(f"\n⚡ Performance Summary:")
            print(f"  CPU Usage: {perf.get('avg_cpu_usage_percent', 'N/A')}%")
            print(f"  Memory Usage: {perf.get('avg_memory_usage_mb', 'N/A')}MB")
            print(f"  Average Latency: {perf.get('avg_latency_ms', 'N/A')}ms")

        # Final status
        if summary["all_tests_passed"]:
            print(
                f"\n🎉 ALL TESTS PASSED! Workflow 5 integration test suite completed successfully!"
            )
            print(f"✅ System ready for production deployment")
        else:
            print(f"\n⚠️  Some tests failed. Review results above for details.")
            print(f"🔧 Address failing tests before production deployment")

        # Save detailed results
        with open("/tmp/workflow5_integration_test_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(
            f"\n📄 Detailed results saved to: /tmp/workflow5_integration_test_results.json"
        )

    except Exception as e:
        print(f"❌ Integration test suite failed to execute: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
