"""
Performance monitoring and metrics dashboard for PPL Meta Platform.
Provides comprehensive performance tracking and visualization.
"""

import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""

    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_available: int
    disk_usage_percent: float
    disk_free: int
    network_bytes_sent: int
    network_bytes_recv: int
    load_average: List[float]


@dataclass
class DatabaseMetrics:
    """Database performance metrics."""

    timestamp: str
    active_connections: int
    idle_connections: int
    total_queries: int
    slow_queries: int
    avg_query_time: float
    cache_hit_ratio: float
    index_usage: Dict[str, float]
    table_sizes: Dict[str, int]


@dataclass
class CacheMetrics:
    """Cache performance metrics."""

    timestamp: str
    hit_rate: float
    miss_rate: float
    total_keys: int
    memory_usage: int
    operations_per_second: float
    avg_response_time: float


@dataclass
class APIMetrics:
    """API performance metrics."""

    timestamp: str
    total_requests: int
    requests_per_second: float
    avg_response_time: float
    error_rate: float
    status_codes: Dict[str, int]
    endpoint_performance: Dict[str, Dict[str, float]]


class PerformanceMonitor:
    """Main performance monitoring service."""

    def __init__(self, collection_interval: int = 60):
        self.collection_interval = collection_interval
        self.enabled = PSUTIL_AVAILABLE
        self.metrics_history: Dict[str, List[Dict]] = {
            "system": [],
            "database": [],
            "cache": [],
            "api": [],
        }
        self.max_history_size = 1440  # 24 hours at 1-minute intervals

        if not self.enabled:
            logger.warning("Performance monitoring disabled - psutil not available")

    def collect_system_metrics(self) -> Optional[SystemMetrics]:
        """Collect current system performance metrics."""
        if not self.enabled:
            return None

        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()

            # Disk usage (root partition)
            disk = psutil.disk_usage("/")

            # Network statistics
            network = psutil.net_io_counters()

            # Load average (Unix-like systems)
            try:
                load_avg = list(psutil.getloadavg())
            except (AttributeError, OSError):
                load_avg = [0.0, 0.0, 0.0]  # Windows fallback

            return SystemMetrics(
                timestamp=datetime.utcnow().isoformat(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_available=memory.available,
                disk_usage_percent=disk.percent,
                disk_free=disk.free,
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                load_average=load_avg,
            )

        except Exception as e:
            logger.error("Error collecting system metrics: %s", e)
            return None

    def collect_database_metrics(self, db_connection) -> Optional[DatabaseMetrics]:
        """Collect database performance metrics."""
        try:
            cursor = db_connection.cursor()

            # Active connections
            cursor.execute(
                """
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'active'
            """
            )
            active_connections = cursor.fetchone()[0]

            # Idle connections
            cursor.execute(
                """
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'idle'
            """
            )
            idle_connections = cursor.fetchone()[0]

            # Query statistics
            cursor.execute(
                """
                SELECT 
                    sum(calls) as total_queries,
                    avg(mean_exec_time) as avg_query_time
                FROM pg_stat_statements
            """
            )
            result = cursor.fetchone()
            total_queries = result[0] if result[0] else 0
            avg_query_time = result[1] if result[1] else 0.0

            # Slow queries (> 1 second)
            cursor.execute(
                """
                SELECT count(*) FROM pg_stat_statements 
                WHERE mean_exec_time > 1000
            """
            )
            slow_queries = cursor.fetchone()[0]

            # Cache hit ratio
            cursor.execute(
                """
                SELECT 
                    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
                FROM pg_statio_user_tables
            """
            )
            cache_hit_ratio = cursor.fetchone()[0] or 0.0

            # Index usage
            cursor.execute(
                """
                SELECT 
                    schemaname||'.'||tablename as table_name,
                    CASE WHEN seq_tup_read + idx_tup_fetch > 0 
                         THEN idx_tup_fetch::float / (seq_tup_read + idx_tup_fetch) 
                         ELSE 0 END as index_usage_ratio
                FROM pg_stat_user_tables
                ORDER BY seq_tup_read + idx_tup_fetch DESC
                LIMIT 10
            """
            )
            index_usage = {row[0]: float(row[1]) for row in cursor.fetchall()}

            # Table sizes
            cursor.execute(
                """
                SELECT 
                    schemaname||'.'||tablename as table_name,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """
            )
            table_sizes = {row[0]: int(row[1]) for row in cursor.fetchall()}

            cursor.close()

            return DatabaseMetrics(
                timestamp=datetime.utcnow().isoformat(),
                active_connections=active_connections,
                idle_connections=idle_connections,
                total_queries=int(total_queries),
                slow_queries=slow_queries,
                avg_query_time=float(avg_query_time),
                cache_hit_ratio=float(cache_hit_ratio) * 100,
                index_usage=index_usage,
                table_sizes=table_sizes,
            )

        except Exception as e:
            logger.error("Error collecting database metrics: %s", e)
            return None

    def collect_cache_metrics(self, cache_service) -> Optional[CacheMetrics]:
        """Collect cache performance metrics."""
        try:
            if not cache_service or not cache_service.is_connected:
                return None

            stats = cache_service.get_cache_stats()

            return CacheMetrics(
                timestamp=datetime.utcnow().isoformat(),
                hit_rate=stats.get("hit_rate", 0.0),
                miss_rate=100.0 - stats.get("hit_rate", 0.0),
                total_keys=stats.get("keyspace_hits", 0)
                + stats.get("keyspace_misses", 0),
                memory_usage=stats.get("used_memory", 0),
                operations_per_second=stats.get("total_commands_processed", 0),
                avg_response_time=0.0,  # Would need additional monitoring
            )

        except Exception as e:
            logger.error("Error collecting cache metrics: %s", e)
            return None

    def collect_api_metrics(
        self, request_stats: Dict[str, Any]
    ) -> Optional[APIMetrics]:
        """Collect API performance metrics from request statistics."""
        try:
            timestamp = datetime.utcnow().isoformat()

            return APIMetrics(
                timestamp=timestamp,
                total_requests=request_stats.get("total_requests", 0),
                requests_per_second=request_stats.get("requests_per_second", 0.0),
                avg_response_time=request_stats.get("avg_response_time", 0.0),
                error_rate=request_stats.get("error_rate", 0.0),
                status_codes=request_stats.get("status_codes", {}),
                endpoint_performance=request_stats.get("endpoint_performance", {}),
            )

        except Exception as e:
            logger.error("Error collecting API metrics: %s", e)
            return None

    def store_metrics(self, metrics_type: str, metrics: Any) -> None:
        """Store metrics in memory history."""
        if metrics is None:
            return

        # Convert dataclass to dict
        metrics_dict = asdict(metrics)

        # Add to history
        self.metrics_history[metrics_type].append(metrics_dict)

        # Trim history to max size
        if len(self.metrics_history[metrics_type]) > self.max_history_size:
            self.metrics_history[metrics_type] = self.metrics_history[metrics_type][
                -self.max_history_size :
            ]

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get the most recent metrics for all categories."""
        current = {}

        for metrics_type, history in self.metrics_history.items():
            if history:
                current[metrics_type] = history[-1]
            else:
                current[metrics_type] = None

        return current

    def get_metrics_history(
        self, metrics_type: str, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Get historical metrics for a specific time period."""
        if metrics_type not in self.metrics_history:
            return []

        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        cutoff_timestamp = cutoff_time.isoformat()

        return [
            metric
            for metric in self.metrics_history[metrics_type]
            if metric.get("timestamp", "") >= cutoff_timestamp
        ]

    def get_performance_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get performance summary for the specified time period."""
        summary = {
            "period_hours": hours,
            "timestamp": datetime.utcnow().isoformat(),
            "system": self._summarize_system_metrics(hours),
            "database": self._summarize_database_metrics(hours),
            "cache": self._summarize_cache_metrics(hours),
            "api": self._summarize_api_metrics(hours),
        }

        return summary

    def _summarize_system_metrics(self, hours: int) -> Dict[str, Any]:
        """Summarize system metrics for the time period."""
        history = self.get_metrics_history("system", hours)

        if not history:
            return {"available": False}

        cpu_values = [m["cpu_percent"] for m in history]
        memory_values = [m["memory_percent"] for m in history]
        disk_values = [m["disk_usage_percent"] for m in history]

        return {
            "available": True,
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values),
                "max": max(cpu_values),
                "min": min(cpu_values),
            },
            "memory": {
                "avg": sum(memory_values) / len(memory_values),
                "max": max(memory_values),
                "min": min(memory_values),
            },
            "disk": {
                "avg": sum(disk_values) / len(disk_values),
                "max": max(disk_values),
                "min": min(disk_values),
            },
            "samples": len(history),
        }

    def _summarize_database_metrics(self, hours: int) -> Dict[str, Any]:
        """Summarize database metrics for the time period."""
        history = self.get_metrics_history("database", hours)

        if not history:
            return {"available": False}

        query_times = [m["avg_query_time"] for m in history if m["avg_query_time"] > 0]
        hit_ratios = [m["cache_hit_ratio"] for m in history]

        return {
            "available": True,
            "avg_query_time": sum(query_times) / len(query_times) if query_times else 0,
            "cache_hit_ratio": sum(hit_ratios) / len(hit_ratios) if hit_ratios else 0,
            "slow_queries": sum(m["slow_queries"] for m in history),
            "total_queries": sum(m["total_queries"] for m in history),
            "samples": len(history),
        }

    def _summarize_cache_metrics(self, hours: int) -> Dict[str, Any]:
        """Summarize cache metrics for the time period."""
        history = self.get_metrics_history("cache", hours)

        if not history:
            return {"available": False}

        hit_rates = [m["hit_rate"] for m in history]

        return {
            "available": True,
            "avg_hit_rate": sum(hit_rates) / len(hit_rates) if hit_rates else 0,
            "samples": len(history),
        }

    def _summarize_api_metrics(self, hours: int) -> Dict[str, Any]:
        """Summarize API metrics for the time period."""
        history = self.get_metrics_history("api", hours)

        if not history:
            return {"available": False}

        response_times = [
            m["avg_response_time"] for m in history if m["avg_response_time"] > 0
        ]
        error_rates = [m["error_rate"] for m in history]

        return {
            "available": True,
            "avg_response_time": (
                sum(response_times) / len(response_times) if response_times else 0
            ),
            "avg_error_rate": sum(error_rates) / len(error_rates) if error_rates else 0,
            "total_requests": sum(m["total_requests"] for m in history),
            "samples": len(history),
        }

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get performance alerts based on current metrics."""
        alerts = []
        current = self.get_current_metrics()

        # System alerts
        if current.get("system"):
            system = current["system"]
            if system["cpu_percent"] > 80:
                alerts.append(
                    {
                        "type": "system",
                        "level": "warning",
                        "message": f"High CPU usage: {system['cpu_percent']:.1f}%",
                        "metric": "cpu_percent",
                        "value": system["cpu_percent"],
                        "threshold": 80,
                    }
                )

            if system["memory_percent"] > 85:
                alerts.append(
                    {
                        "type": "system",
                        "level": (
                            "critical" if system["memory_percent"] > 95 else "warning"
                        ),
                        "message": f"High memory usage: {system['memory_percent']:.1f}%",
                        "metric": "memory_percent",
                        "value": system["memory_percent"],
                        "threshold": 85,
                    }
                )

            if system["disk_usage_percent"] > 90:
                alerts.append(
                    {
                        "type": "system",
                        "level": "critical",
                        "message": f"High disk usage: {system['disk_usage_percent']:.1f}%",
                        "metric": "disk_usage_percent",
                        "value": system["disk_usage_percent"],
                        "threshold": 90,
                    }
                )

        # Database alerts
        if current.get("database"):
            db = current["database"]
            if db["cache_hit_ratio"] < 80:
                alerts.append(
                    {
                        "type": "database",
                        "level": "warning",
                        "message": f"Low cache hit ratio: {db['cache_hit_ratio']:.1f}%",
                        "metric": "cache_hit_ratio",
                        "value": db["cache_hit_ratio"],
                        "threshold": 80,
                    }
                )

            if db["avg_query_time"] > 1000:  # > 1 second
                alerts.append(
                    {
                        "type": "database",
                        "level": "warning",
                        "message": f"Slow average query time: {db['avg_query_time']:.1f}ms",
                        "metric": "avg_query_time",
                        "value": db["avg_query_time"],
                        "threshold": 1000,
                    }
                )

        # Cache alerts
        if current.get("cache"):
            cache = current["cache"]
            if cache["hit_rate"] < 70:
                alerts.append(
                    {
                        "type": "cache",
                        "level": "warning",
                        "message": f"Low cache hit rate: {cache['hit_rate']:.1f}%",
                        "metric": "hit_rate",
                        "value": cache["hit_rate"],
                        "threshold": 70,
                    }
                )

        # API alerts
        if current.get("api"):
            api = current["api"]
            if api["error_rate"] > 5:
                alerts.append(
                    {
                        "type": "api",
                        "level": "critical" if api["error_rate"] > 10 else "warning",
                        "message": f"High API error rate: {api['error_rate']:.1f}%",
                        "metric": "error_rate",
                        "value": api["error_rate"],
                        "threshold": 5,
                    }
                )

            if api["avg_response_time"] > 2000:  # > 2 seconds
                alerts.append(
                    {
                        "type": "api",
                        "level": "warning",
                        "message": f"Slow API response time: {api['avg_response_time']:.1f}ms",
                        "metric": "avg_response_time",
                        "value": api["avg_response_time"],
                        "threshold": 2000,
                    }
                )

        return alerts

    async def start_monitoring(
        self, db_connection=None, cache_service=None, request_stats_callback=None
    ):
        """Start continuous performance monitoring."""
        logger.info(
            "Starting performance monitoring (interval: %ds)", self.collection_interval
        )

        while True:
            try:
                # Collect system metrics
                system_metrics = self.collect_system_metrics()
                if system_metrics:
                    self.store_metrics("system", system_metrics)

                # Collect database metrics
                if db_connection:
                    db_metrics = self.collect_database_metrics(db_connection)
                    if db_metrics:
                        self.store_metrics("database", db_metrics)

                # Collect cache metrics
                if cache_service:
                    cache_metrics = self.collect_cache_metrics(cache_service)
                    if cache_metrics:
                        self.store_metrics("cache", cache_metrics)

                # Collect API metrics
                if request_stats_callback:
                    api_stats = request_stats_callback()
                    if api_stats:
                        api_metrics = self.collect_api_metrics(api_stats)
                        if api_metrics:
                            self.store_metrics("api", api_metrics)

                await asyncio.sleep(self.collection_interval)

            except Exception as e:
                logger.error("Error in monitoring loop: %s", e)
                await asyncio.sleep(self.collection_interval)


# Global performance monitor instance
performance_monitor = None


def init_performance_monitor(collection_interval: int = 60) -> PerformanceMonitor:
    """Initialize global performance monitor."""
    global performance_monitor
    performance_monitor = PerformanceMonitor(collection_interval)
    return performance_monitor


def get_performance_monitor() -> Optional[PerformanceMonitor]:
    """Get global performance monitor instance."""
    return performance_monitor
