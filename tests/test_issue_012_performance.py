#!/usr/bin/env python3
"""
Comprehensive test suite for Issue #012: Performance and Scalability.
Tests all implemented performance optimization components.
"""

import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), "ppl-meta-media", "src"))

try:
    import psycopg2
    import redis
except ImportError as e:
    print(f"Required dependencies not available: {e}")
    print("Please install: pip install psycopg2-binary redis")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceTestSuite:
    """Comprehensive test suite for performance optimizations."""

    def __init__(self):
        self.test_results = {}
        self.db_connection = None

    def setup_database_connection(self) -> bool:
        """Setup database connection for testing."""
        try:
            # Database configuration
            db_config = {
                "host": os.getenv("DB_HOST", "localhost"),
                "port": int(os.getenv("DB_PORT", 5432)),
                "database": os.getenv("DB_NAME", "ppl_meta"),
                "user": os.getenv("DB_USER", "postgres"),
                "password": os.getenv("DB_PASSWORD", "password"),
            }

            logger.info("Connecting to database...")
            self.db_connection = psycopg2.connect(**db_config)
            self.db_connection.autocommit = True

            # Test connection
            cursor = self.db_connection.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()

            logger.info(f"Connected to PostgreSQL: {version}")
            return True

        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False

    def test_database_optimizer(self) -> Dict[str, Any]:
        """Test database optimization functionality."""
        logger.info("Testing database optimizer...")

        try:
            from services.database_optimizer import DatabaseOptimizer

            optimizer = DatabaseOptimizer(self.db_connection)

            # Test index creation
            logger.info("Testing index creation...")
            index_results = optimizer.create_performance_indexes()

            # Test query analysis
            logger.info("Testing query analysis...")
            test_query = "SELECT COUNT(*) FROM information_schema.tables"

            with optimizer.query_timer() as timer:
                cursor = self.db_connection.cursor()
                cursor.execute(test_query)
                result = cursor.fetchone()
                cursor.close()

            execution_time = timer.execution_time

            # Test table statistics
            logger.info("Testing table statistics...")
            table_stats = optimizer.get_table_statistics()

            # Test vacuum analyze
            logger.info("Testing vacuum analyze...")
            vacuum_results = optimizer.vacuum_analyze_tables()

            return {
                "status": "success",
                "index_creation": len(index_results) > 0,
                "query_execution_time": execution_time,
                "table_stats_count": len(table_stats),
                "vacuum_completed": vacuum_results,
                "details": {
                    "indexes": index_results[:5],  # First 5 indexes
                    "table_count": len(table_stats),
                },
            }

        except Exception as e:
            logger.error(f"Database optimizer test failed: {e}")
            return {"status": "failed", "error": str(e)}

    def test_cache_service(self) -> Dict[str, Any]:
        """Test Redis cache service functionality."""
        logger.info("Testing cache service...")

        try:
            from services.cache_service import init_cache_service

            # Initialize cache service
            cache_service = init_cache_service(
                redis_host=os.getenv("REDIS_HOST", "localhost"),
                redis_port=int(os.getenv("REDIS_PORT", 6379)),
                redis_db=1,  # Use separate DB for testing
            )

            if not cache_service.is_connected:
                return {"status": "failed", "error": "Redis connection failed"}

            # Test basic operations
            test_key = "test_performance_cache"
            test_data = {
                "test_id": 12345,
                "data": "performance test data",
                "timestamp": datetime.utcnow().isoformat(),
                "numbers": [1, 2, 3, 4, 5],
            }

            # Test set operation
            set_result = cache_service.set(test_key, test_data, ttl=60)

            # Test get operation
            retrieved_data = cache_service.get(test_key)

            # Test search results caching
            search_params = {
                "media_type": "image",
                "limit": 10,
                "offset": 0,
            }

            mock_search_results = [
                {"id": 1, "filename": "test1.jpg", "size": 1024},
                {"id": 2, "filename": "test2.jpg", "size": 2048},
            ]

            cache_search_result = cache_service.cache_search_results(
                search_params, mock_search_results, ttl=300
            )

            cached_search = cache_service.get_cached_search_results(search_params)

            # Test cache statistics
            cache_stats = cache_service.get_cache_stats()

            # Clean up
            cache_service.delete(test_key)
            cache_service.flush_pattern("search:*")

            return {
                "status": "success",
                "connection": True,
                "basic_operations": {
                    "set_success": set_result,
                    "get_success": retrieved_data == test_data,
                },
                "search_caching": {
                    "cache_success": cache_search_result,
                    "retrieve_success": cached_search == mock_search_results,
                },
                "cache_stats": cache_stats,
            }

        except Exception as e:
            logger.error(f"Cache service test failed: {e}")
            return {"status": "failed", "error": str(e)}

    def test_background_tasks(self) -> Dict[str, Any]:
        """Test background task processing."""
        logger.info("Testing background task service...")

        try:
            from services.background_tasks import init_task_service

            # Initialize task service
            task_service = init_task_service(
                broker_url=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/2",
                result_backend=f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', 6379)}/2",
            )

            if not task_service.enabled:
                return {"status": "disabled", "reason": "Celery not available"}

            # Test task submission
            task_id = task_service.submit_task(
                "cleanup_temp_files", 1
            )  # Clean 1 hour old files

            # Wait a moment and check task status
            time.sleep(1)
            task_status = task_service.get_task_status(task_id) if task_id else None

            # Get task statistics
            task_stats = task_service.get_task_stats()

            # Get active tasks
            active_tasks = task_service.get_active_tasks()

            return {
                "status": "success",
                "enabled": True,
                "task_submission": {
                    "task_id": task_id,
                    "task_status": task_status,
                },
                "task_stats": task_stats,
                "active_tasks_count": len(active_tasks),
            }

        except Exception as e:
            logger.error(f"Background tasks test failed: {e}")
            return {"status": "failed", "error": str(e)}

    def test_cdn_service(self) -> Dict[str, Any]:
        """Test CDN service functionality."""
        logger.info("Testing CDN service...")

        try:
            from services.cdn_service import CDNConfig, init_cdn_service

            # Initialize CDN service with test configuration
            cdn_config = CDNConfig(
                distribution_domain=os.getenv("CDN_DOMAIN", "test.cloudfront.net"),
                s3_bucket=os.getenv("S3_BUCKET", "test-bucket"),
                aws_region=os.getenv("AWS_REGION", "us-east-1"),
            )

            cdn_service = init_cdn_service(cdn_config)

            # Test URL generation
            test_object_key = "media/test-image.jpg"
            cdn_url = cdn_service.generate_cdn_url(test_object_key, "image/jpeg")

            # Test signed URL generation
            signed_url = cdn_service.generate_signed_url(
                test_object_key, expires_in=3600
            )

            # Test delivery optimization
            optimized_urls = cdn_service.optimize_delivery(
                test_object_key, "image/jpeg"
            )

            # Test cache statistics
            cache_stats = cdn_service.get_cache_statistics()

            # Test content preloading
            preload_results = cdn_service.preload_content([test_object_key])

            return {
                "status": "success",
                "enabled": cdn_service.enabled,
                "url_generation": {
                    "cdn_url": cdn_url,
                    "signed_url": signed_url,
                    "optimized_urls": optimized_urls,
                },
                "cache_stats": cache_stats,
                "preload_results": preload_results,
            }

        except Exception as e:
            logger.error(f"CDN service test failed: {e}")
            return {"status": "failed", "error": str(e)}

    def test_performance_monitor(self) -> Dict[str, Any]:
        """Test performance monitoring functionality."""
        logger.info("Testing performance monitoring...")

        try:
            from services.cache_service import get_cache_service
            from services.performance_monitor import init_performance_monitor

            # Initialize performance monitor
            monitor = init_performance_monitor(collection_interval=60)

            # Collect system metrics
            system_metrics = monitor.collect_system_metrics()

            # Collect database metrics
            db_metrics = monitor.collect_database_metrics(self.db_connection)

            # Collect cache metrics
            cache_service = get_cache_service()
            cache_metrics = monitor.collect_cache_metrics(cache_service)

            # Store metrics
            if system_metrics:
                monitor.store_metrics("system", system_metrics)
            if db_metrics:
                monitor.store_metrics("database", db_metrics)
            if cache_metrics:
                monitor.store_metrics("cache", cache_metrics)

            # Test mock API metrics
            mock_api_stats = {
                "total_requests": 1500,
                "requests_per_second": 25.5,
                "avg_response_time": 150.0,
                "error_rate": 2.5,
                "status_codes": {"200": 1425, "404": 50, "500": 25},
                "endpoint_performance": {
                    "/api/media/search": {"avg_time": 120.0, "requests": 800},
                    "/api/media/upload": {"avg_time": 300.0, "requests": 200},
                },
            }

            api_metrics = monitor.collect_api_metrics(mock_api_stats)
            if api_metrics:
                monitor.store_metrics("api", api_metrics)

            # Get current metrics
            current_metrics = monitor.get_current_metrics()

            # Get performance summary
            performance_summary = monitor.get_performance_summary(hours=1)

            # Get alerts
            alerts = monitor.get_alerts()

            return {
                "status": "success",
                "enabled": monitor.enabled,
                "metrics_collected": {
                    "system": system_metrics is not None,
                    "database": db_metrics is not None,
                    "cache": cache_metrics is not None,
                    "api": api_metrics is not None,
                },
                "current_metrics": current_metrics,
                "performance_summary": performance_summary,
                "alerts_count": len(alerts),
                "alerts": alerts[:3],  # First 3 alerts
            }

        except Exception as e:
            logger.error(f"Performance monitoring test failed: {e}")
            return {"status": "failed", "error": str(e)}

    def test_integrated_performance_service(self) -> Dict[str, Any]:
        """Test integrated performance optimization service."""
        logger.info("Testing integrated performance service...")

        try:
            from services.cdn_service import CDNConfig
            from services.performance_optimization import init_performance_service

            # Initialize integrated service
            redis_config = {
                "redis_host": os.getenv("REDIS_HOST", "localhost"),
                "redis_port": int(os.getenv("REDIS_PORT", 6379)),
                "redis_db": 3,  # Use separate DB for integration testing
            }

            cdn_config = CDNConfig(
                distribution_domain=os.getenv("CDN_DOMAIN", "test.cloudfront.net"),
                s3_bucket=os.getenv("S3_BUCKET", "test-bucket"),
            )

            perf_service = init_performance_service(
                db_connection=self.db_connection,
                redis_config=redis_config,
                cdn_config=cdn_config,
                monitoring_interval=60,
            )

            # Test initial optimizations setup
            setup_results = perf_service.setup_initial_optimizations()

            # Test comprehensive status
            comprehensive_status = perf_service.get_comprehensive_status()

            # Test search optimization
            test_search_params = {
                "media_type": "image",
                "device_manufacturer": "Canon",
                "limit": 20,
            }

            search_optimization = perf_service.optimize_search_performance(
                test_search_params
            )

            # Test maintenance task scheduling
            maintenance_tasks = perf_service.schedule_maintenance_tasks()

            # Test performance recommendations
            recommendations = perf_service.get_performance_recommendations()

            return {
                "status": "success",
                "initialized": perf_service.initialized,
                "setup_results": setup_results,
                "comprehensive_status": comprehensive_status,
                "search_optimization": search_optimization,
                "maintenance_tasks": maintenance_tasks,
                "recommendations_count": len(recommendations),
                "recommendations": recommendations[:3],  # First 3 recommendations
            }

        except Exception as e:
            logger.error(f"Integrated performance service test failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all performance optimization tests."""
        logger.info("=" * 60)
        logger.info("PPL Meta Platform - Issue #012 Performance Test Suite")
        logger.info("=" * 60)

        # Setup database connection
        if not self.setup_database_connection():
            return {"status": "failed", "error": "Database connection failed"}

        # Run individual component tests
        tests = [
            ("database_optimizer", self.test_database_optimizer),
            ("cache_service", self.test_cache_service),
            ("background_tasks", self.test_background_tasks),
            ("cdn_service", self.test_cdn_service),
            ("performance_monitor", self.test_performance_monitor),
            ("integrated_service", self.test_integrated_performance_service),
        ]

        for test_name, test_func in tests:
            logger.info(f"\n--- Running {test_name} test ---")
            start_time = time.time()

            try:
                self.test_results[test_name] = test_func()
                self.test_results[test_name]["execution_time"] = (
                    time.time() - start_time
                )
            except Exception as e:
                logger.error(f"Test {test_name} failed with exception: {e}")
                self.test_results[test_name] = {
                    "status": "failed",
                    "error": str(e),
                    "execution_time": time.time() - start_time,
                }

        # Generate summary
        total_tests = len(tests)
        successful_tests = sum(
            1
            for result in self.test_results.values()
            if result.get("status") == "success"
        )
        failed_tests = total_tests - successful_tests

        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": failed_tests,
            "success_rate": (successful_tests / total_tests) * 100,
            "test_results": self.test_results,
        }

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Successful: {successful_tests}")
        logger.info(f"Failed: {failed_tests}")
        logger.info(f"Success Rate: {summary['success_rate']:.1f}%")

        for test_name, result in self.test_results.items():
            status = result.get("status", "unknown")
            exec_time = result.get("execution_time", 0)
            logger.info(f"  {test_name}: {status.upper()} ({exec_time:.2f}s)")

            if status == "failed" and "error" in result:
                logger.error(f"    Error: {result['error']}")

        logger.info("=" * 60)

        # Close database connection
        if self.db_connection:
            self.db_connection.close()

        return summary


async def main():
    """Main test execution function."""
    test_suite = PerformanceTestSuite()
    results = await test_suite.run_all_tests()

    # Return appropriate exit code
    if results.get("failed_tests", 0) == 0:
        logger.info("All tests passed! ✅")
        return 0
    else:
        logger.error(f"{results.get('failed_tests', 0)} tests failed! ❌")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
