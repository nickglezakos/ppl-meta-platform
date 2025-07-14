"""
Performance optimization integration service for PPL Meta Platform.
Coordinates database optimization, caching, background processing, CDN, and monitoring.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from services.background_tasks import BackgroundTaskService, init_task_service
from services.cache_service import CacheService, init_cache_service
from services.cdn_service import CDNConfig, CDNService, init_cdn_service
from services.database_optimizer import DatabaseOptimizer
from services.performance_monitor import PerformanceMonitor, init_performance_monitor

logger = logging.getLogger(__name__)


class PerformanceOptimizationService:
    """Centralized performance optimization service."""

    def __init__(
        self,
        db_connection,
        redis_config: Optional[Dict[str, Any]] = None,
        cdn_config: Optional[CDNConfig] = None,
        monitoring_interval: int = 60,
    ):
        self.db_connection = db_connection
        self.initialized = False

        # Initialize database optimizer
        self.db_optimizer = DatabaseOptimizer(db_connection)

        # Initialize cache service
        redis_config = redis_config or {}
        self.cache_service = init_cache_service(**redis_config)

        # Initialize background task service
        self.task_service = init_task_service()

        # Initialize CDN service
        if cdn_config:
            self.cdn_service = init_cdn_service(cdn_config)
        else:
            self.cdn_service = None
            logger.warning("CDN service not configured")

        # Initialize performance monitor
        self.performance_monitor = init_performance_monitor(monitoring_interval)

        self.initialized = True
        logger.info("Performance optimization service initialized")

    def setup_initial_optimizations(self) -> Dict[str, Any]:
        """Set up initial performance optimizations."""
        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "database": None,
            "cache": None,
            "background_tasks": None,
            "cdn": None,
            "monitoring": None,
        }

        # Database optimizations
        try:
            logger.info("Setting up database optimizations...")

            # Create performance indexes
            index_results = self.db_optimizer.create_performance_indexes()

            # Analyze current query performance
            query_analysis = self.db_optimizer.analyze_query_performance(
                "SELECT COUNT(*) FROM media WHERE media_type = 'image'"
            )

            # Update table statistics
            self.db_optimizer.vacuum_analyze_tables()

            results["database"] = {
                "indexes_created": index_results,
                "initial_analysis": query_analysis,
                "status": "completed",
            }

        except Exception as e:
            logger.error("Database optimization setup failed: %s", e)
            results["database"] = {"status": "failed", "error": str(e)}

        # Cache service setup
        try:
            logger.info("Testing cache service...")
            if self.cache_service and self.cache_service.is_connected:
                # Test cache functionality
                test_key = "performance_test"
                test_value = {"test": True, "timestamp": datetime.utcnow().isoformat()}

                self.cache_service.set(test_key, test_value, ttl=60)
                retrieved = self.cache_service.get(test_key)

                cache_stats = self.cache_service.get_cache_stats()

                results["cache"] = {
                    "connected": True,
                    "test_successful": retrieved == test_value,
                    "stats": cache_stats,
                    "status": "completed",
                }

                # Clean up test key
                self.cache_service.delete(test_key)

            else:
                results["cache"] = {"connected": False, "status": "failed"}

        except Exception as e:
            logger.error("Cache service setup failed: %s", e)
            results["cache"] = {"status": "failed", "error": str(e)}

        # Background tasks setup
        try:
            logger.info("Testing background task service...")
            if self.task_service and self.task_service.enabled:
                # Submit a test cleanup task
                task_id = self.task_service.submit_task("cleanup_temp_files", 1)

                task_stats = self.task_service.get_task_stats()

                results["background_tasks"] = {
                    "enabled": True,
                    "test_task_id": task_id,
                    "stats": task_stats,
                    "status": "completed",
                }
            else:
                results["background_tasks"] = {"enabled": False, "status": "disabled"}

        except Exception as e:
            logger.error("Background task service setup failed: %s", e)
            results["background_tasks"] = {"status": "failed", "error": str(e)}

        # CDN service setup
        try:
            logger.info("Testing CDN service...")
            if self.cdn_service and self.cdn_service.enabled:
                # Test CDN URL generation
                test_url = self.cdn_service.generate_cdn_url("test/image.jpg")
                cdn_stats = self.cdn_service.get_cache_statistics()

                results["cdn"] = {
                    "enabled": True,
                    "test_url": test_url,
                    "stats": cdn_stats,
                    "status": "completed",
                }
            else:
                results["cdn"] = {"enabled": False, "status": "disabled"}

        except Exception as e:
            logger.error("CDN service setup failed: %s", e)
            results["cdn"] = {"status": "failed", "error": str(e)}

        # Performance monitoring setup
        try:
            logger.info("Setting up performance monitoring...")

            # Collect initial metrics
            system_metrics = self.performance_monitor.collect_system_metrics()
            db_metrics = self.performance_monitor.collect_database_metrics(
                self.db_connection
            )
            cache_metrics = self.performance_monitor.collect_cache_metrics(
                self.cache_service
            )

            # Store initial metrics
            if system_metrics:
                self.performance_monitor.store_metrics("system", system_metrics)
            if db_metrics:
                self.performance_monitor.store_metrics("database", db_metrics)
            if cache_metrics:
                self.performance_monitor.store_metrics("cache", cache_metrics)

            current_metrics = self.performance_monitor.get_current_metrics()

            results["monitoring"] = {
                "enabled": self.performance_monitor.enabled,
                "initial_metrics": current_metrics,
                "status": "completed",
            }

        except Exception as e:
            logger.error("Performance monitoring setup failed: %s", e)
            results["monitoring"] = {"status": "failed", "error": str(e)}

        return results

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive performance status across all services."""
        status = {
            "timestamp": datetime.utcnow().isoformat(),
            "overall_status": "healthy",
            "services": {},
        }

        # Database status
        try:
            db_stats = self.db_optimizer.get_table_statistics()
            slow_queries = self.db_optimizer.get_slow_queries()

            status["services"]["database"] = {
                "status": "healthy",
                "table_count": len(db_stats),
                "slow_queries": len(slow_queries),
                "details": {
                    "table_stats": db_stats[:5],  # Top 5 tables
                    "slow_queries": len(slow_queries),
                },
            }
        except Exception as e:
            status["services"]["database"] = {"status": "error", "error": str(e)}
            status["overall_status"] = "degraded"

        # Cache status
        try:
            if self.cache_service and self.cache_service.is_connected:
                cache_stats = self.cache_service.get_cache_stats()
                status["services"]["cache"] = {
                    "status": "healthy",
                    "connected": True,
                    "hit_rate": cache_stats.get("hit_rate", 0),
                    "memory_usage": cache_stats.get("used_memory_human", "0B"),
                    "details": cache_stats,
                }
            else:
                status["services"]["cache"] = {
                    "status": "disconnected",
                    "connected": False,
                }
                status["overall_status"] = "degraded"
        except Exception as e:
            status["services"]["cache"] = {"status": "error", "error": str(e)}
            status["overall_status"] = "degraded"

        # Background tasks status
        try:
            if self.task_service and self.task_service.enabled:
                task_stats = self.task_service.get_task_stats()
                active_tasks = self.task_service.get_active_tasks()

                status["services"]["background_tasks"] = {
                    "status": "healthy",
                    "enabled": True,
                    "worker_count": task_stats.get("worker_count", 0),
                    "active_tasks": task_stats.get("active_tasks", 0),
                    "details": task_stats,
                }
            else:
                status["services"]["background_tasks"] = {
                    "status": "disabled",
                    "enabled": False,
                }
        except Exception as e:
            status["services"]["background_tasks"] = {
                "status": "error",
                "error": str(e),
            }

        # CDN status
        try:
            if self.cdn_service and self.cdn_service.enabled:
                cdn_stats = self.cdn_service.get_cache_statistics()
                status["services"]["cdn"] = {
                    "status": "healthy",
                    "enabled": True,
                    "domain": self.cdn_service.config.distribution_domain,
                    "details": cdn_stats,
                }
            else:
                status["services"]["cdn"] = {
                    "status": "disabled",
                    "enabled": False,
                }
        except Exception as e:
            status["services"]["cdn"] = {"status": "error", "error": str(e)}

        # Performance monitoring status
        try:
            if self.performance_monitor and self.performance_monitor.enabled:
                current_metrics = self.performance_monitor.get_current_metrics()
                alerts = self.performance_monitor.get_alerts()

                # Determine health based on alerts
                critical_alerts = [a for a in alerts if a.get("level") == "critical"]
                warning_alerts = [a for a in alerts if a.get("level") == "warning"]

                monitor_status = "healthy"
                if critical_alerts:
                    monitor_status = "critical"
                    status["overall_status"] = "critical"
                elif warning_alerts:
                    monitor_status = "warning"
                    if status["overall_status"] == "healthy":
                        status["overall_status"] = "warning"

                status["services"]["monitoring"] = {
                    "status": monitor_status,
                    "enabled": True,
                    "alerts_count": len(alerts),
                    "critical_alerts": len(critical_alerts),
                    "warning_alerts": len(warning_alerts),
                    "details": {
                        "current_metrics": current_metrics,
                        "alerts": alerts[:5],  # Top 5 alerts
                    },
                }
            else:
                status["services"]["monitoring"] = {
                    "status": "disabled",
                    "enabled": False,
                }
        except Exception as e:
            status["services"]["monitoring"] = {"status": "error", "error": str(e)}

        return status

    def optimize_search_performance(
        self, search_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize search performance using cache and database optimization."""
        optimization_results = {
            "cache_hit": False,
            "db_optimization": None,
            "cdn_urls": None,
            "execution_time": 0,
        }

        start_time = datetime.utcnow()

        try:
            # Try to get results from cache first
            if self.cache_service and self.cache_service.is_connected:
                cached_results = self.cache_service.get_cached_search_results(
                    search_params
                )
                if cached_results:
                    optimization_results["cache_hit"] = True
                    optimization_results["results"] = cached_results

                    # Generate CDN URLs for cached results
                    if self.cdn_service and self.cdn_service.enabled:
                        for result in cached_results:
                            if "file_path" in result:
                                result["cdn_urls"] = self.cdn_service.optimize_delivery(
                                    result["file_path"], result.get("content_type")
                                )

                    end_time = datetime.utcnow()
                    optimization_results["execution_time"] = (
                        end_time - start_time
                    ).total_seconds() * 1000

                    return optimization_results

            # If not in cache, execute database query with optimization
            # This would integrate with your actual search service
            optimization_results["cache_hit"] = False

            # Note: In a real implementation, you would execute the actual search query here
            # and then cache the results

            end_time = datetime.utcnow()
            optimization_results["execution_time"] = (
                end_time - start_time
            ).total_seconds() * 1000

        except Exception as e:
            logger.error("Search optimization failed: %s", e)
            optimization_results["error"] = str(e)

        return optimization_results

    def schedule_maintenance_tasks(self) -> Dict[str, Any]:
        """Schedule regular maintenance tasks for optimal performance."""
        scheduled_tasks = {}

        try:
            if self.task_service and self.task_service.enabled:
                # Schedule database optimization
                db_task_id = self.task_service.submit_task("optimize_database")
                if db_task_id:
                    scheduled_tasks["database_optimization"] = db_task_id

                # Schedule cleanup tasks
                cleanup_task_id = self.task_service.submit_task(
                    "cleanup_temp_files", 24
                )
                if cleanup_task_id:
                    scheduled_tasks["temp_file_cleanup"] = cleanup_task_id

                # Set up recurring tasks
                self.task_service.schedule_recurring_tasks()
                scheduled_tasks["recurring_tasks"] = "configured"

        except Exception as e:
            logger.error("Failed to schedule maintenance tasks: %s", e)
            scheduled_tasks["error"] = str(e)

        return scheduled_tasks

    def get_performance_recommendations(self) -> List[Dict[str, Any]]:
        """Get performance optimization recommendations based on current metrics."""
        recommendations = []

        try:
            # Get current performance summary
            summary = self.performance_monitor.get_performance_summary(hours=1)

            # Database recommendations
            if summary.get("database", {}).get("available"):
                db_summary = summary["database"]

                if db_summary.get("cache_hit_ratio", 0) < 80:
                    recommendations.append(
                        {
                            "category": "database",
                            "priority": "high",
                            "title": "Low Database Cache Hit Ratio",
                            "description": f"Cache hit ratio is {db_summary.get('cache_hit_ratio', 0):.1f}%. Consider increasing shared_buffers or adding more indexes.",
                            "action": "Review query patterns and consider additional indexing strategies.",
                        }
                    )

                if db_summary.get("avg_query_time", 0) > 1000:
                    recommendations.append(
                        {
                            "category": "database",
                            "priority": "medium",
                            "title": "Slow Average Query Time",
                            "description": f"Average query time is {db_summary.get('avg_query_time', 0):.1f}ms.",
                            "action": "Analyze slow queries and optimize indexes or query structure.",
                        }
                    )

            # Cache recommendations
            if summary.get("cache", {}).get("available"):
                cache_summary = summary["cache"]

                if cache_summary.get("avg_hit_rate", 0) < 70:
                    recommendations.append(
                        {
                            "category": "cache",
                            "priority": "medium",
                            "title": "Low Cache Hit Rate",
                            "description": f"Cache hit rate is {cache_summary.get('avg_hit_rate', 0):.1f}%.",
                            "action": "Review caching strategy and increase TTL for frequently accessed data.",
                        }
                    )

            # System recommendations
            if summary.get("system", {}).get("available"):
                system_summary = summary["system"]

                if system_summary.get("memory", {}).get("avg", 0) > 80:
                    recommendations.append(
                        {
                            "category": "system",
                            "priority": "high",
                            "title": "High Memory Usage",
                            "description": f"Average memory usage is {system_summary['memory']['avg']:.1f}%.",
                            "action": "Consider scaling up memory or optimizing memory-intensive operations.",
                        }
                    )

                if system_summary.get("cpu", {}).get("avg", 0) > 70:
                    recommendations.append(
                        {
                            "category": "system",
                            "priority": "medium",
                            "title": "High CPU Usage",
                            "description": f"Average CPU usage is {system_summary['cpu']['avg']:.1f}%.",
                            "action": "Consider scaling out compute resources or optimizing CPU-intensive tasks.",
                        }
                    )

        except Exception as e:
            logger.error("Failed to generate recommendations: %s", e)

        return recommendations


# Global performance optimization service instance
performance_service = None


def init_performance_service(
    db_connection,
    redis_config: Optional[Dict[str, Any]] = None,
    cdn_config: Optional[CDNConfig] = None,
    monitoring_interval: int = 60,
) -> PerformanceOptimizationService:
    """Initialize global performance optimization service."""
    global performance_service
    performance_service = PerformanceOptimizationService(
        db_connection=db_connection,
        redis_config=redis_config,
        cdn_config=cdn_config,
        monitoring_interval=monitoring_interval,
    )
    return performance_service


def get_performance_service() -> Optional[PerformanceOptimizationService]:
    """Get global performance optimization service instance."""
    return performance_service
