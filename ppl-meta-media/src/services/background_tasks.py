"""
Background job processing service for PPL Meta Platform.
Implements Celery-based task queue for heavy operations.
"""

import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Union

try:
    from celery import Celery, Task
    from celery.result import AsyncResult
    from celery.states import FAILURE, PENDING, RETRY, REVOKED, SUCCESS

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task status enumeration."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class BackgroundTaskService:
    """Background task processing service using Celery."""

    def __init__(
        self,
        broker_url: str = "redis://localhost:6379/1",
        result_backend: str = "redis://localhost:6379/1",
        app_name: str = "ppl_meta_tasks",
    ):
        if not CELERY_AVAILABLE:
            logger.warning("Celery not available - background tasks disabled")
            self.celery_app = None
            self.enabled = False
            return

        self.broker_url = broker_url
        self.result_backend = result_backend
        self.app_name = app_name
        self.enabled = True

        # Initialize Celery app
        self.celery_app = Celery(
            app_name,
            broker=broker_url,
            backend=result_backend,
        )

        # Configure Celery
        self.celery_app.conf.update(
            task_serializer="json",
            accept_content=["json"],
            result_serializer="json",
            timezone="UTC",
            enable_utc=True,
            task_track_started=True,
            task_time_limit=30 * 60,  # 30 minutes
            task_soft_time_limit=25 * 60,  # 25 minutes
            worker_prefetch_multiplier=1,
            task_acks_late=True,
            worker_max_tasks_per_child=1000,
            task_routes={
                "media_processing.*": {"queue": "media_processing"},
                "analytics.*": {"queue": "analytics"},
                "maintenance.*": {"queue": "maintenance"},
                "default": {"queue": "default"},
            },
        )

        self._register_tasks()

    def _register_tasks(self):
        """Register all background tasks."""
        if not self.enabled:
            return

        @self.celery_app.task(bind=True, name="media_processing.generate_thumbnails")
        def generate_thumbnails_task(task_self, media_id: str, sizes: List[int] = None):
            """Generate thumbnails for media file."""
            try:
                task_self.update_state(
                    state="PROGRESS", meta={"current": 0, "total": len(sizes or [])}
                )

                # Import here to avoid circular imports
                from services.media_service import MediaService

                media_service = MediaService()
                sizes = sizes or [150, 300, 600, 1200]

                results = []
                for i, size in enumerate(sizes):
                    try:
                        thumbnail_path = media_service.generate_thumbnail(
                            media_id, size
                        )
                        results.append({"size": size, "path": thumbnail_path})

                        # Update progress
                        task_self.update_state(
                            state="PROGRESS",
                            meta={
                                "current": i + 1,
                                "total": len(sizes),
                                "results": results,
                            },
                        )
                    except Exception as e:
                        logger.error("Error generating thumbnail size %s: %s", size, e)
                        results.append({"size": size, "error": str(e)})

                return {"media_id": media_id, "thumbnails": results}

            except Exception as e:
                logger.error("Error in thumbnail generation task: %s", e)
                raise

        @self.celery_app.task(bind=True, name="media_processing.extract_metadata")
        def extract_metadata_task(task_self, media_id: str):
            """Extract comprehensive metadata from media file."""
            try:
                task_self.update_state(state="PROGRESS", meta={"step": "starting"})

                from services.media_service import MediaService

                media_service = MediaService()

                # Extract EXIF data
                task_self.update_state(
                    state="PROGRESS", meta={"step": "extracting_exif"}
                )
                exif_data = media_service.extract_exif_data(media_id)

                # Extract file metadata
                task_self.update_state(
                    state="PROGRESS", meta={"step": "extracting_file_metadata"}
                )
                file_metadata = media_service.extract_file_metadata(media_id)

                # Generate content hash
                task_self.update_state(
                    state="PROGRESS", meta={"step": "generating_hash"}
                )
                content_hash = media_service.generate_content_hash(media_id)

                return {
                    "media_id": media_id,
                    "exif_data": exif_data,
                    "file_metadata": file_metadata,
                    "content_hash": content_hash,
                }

            except Exception as e:
                logger.error("Error in metadata extraction task: %s", e)
                raise

        @self.celery_app.task(bind=True, name="analytics.generate_usage_report")
        def generate_usage_report_task(
            task_self, start_date: str, end_date: str, user_id: str = None
        ):
            """Generate comprehensive usage analytics report."""
            try:
                task_self.update_state(state="PROGRESS", meta={"step": "initializing"})

                from services.analytics_service import AnalyticsService

                analytics_service = AnalyticsService()

                # Media upload statistics
                task_self.update_state(state="PROGRESS", meta={"step": "media_stats"})
                media_stats = analytics_service.get_media_upload_stats(
                    start_date, end_date, user_id
                )

                # Storage usage
                task_self.update_state(state="PROGRESS", meta={"step": "storage_stats"})
                storage_stats = analytics_service.get_storage_usage_stats(
                    start_date, end_date, user_id
                )

                # User activity
                task_self.update_state(state="PROGRESS", meta={"step": "user_activity"})
                user_activity = analytics_service.get_user_activity_stats(
                    start_date, end_date, user_id
                )

                # Popular content
                task_self.update_state(
                    state="PROGRESS", meta={"step": "popular_content"}
                )
                popular_content = analytics_service.get_popular_content(
                    start_date, end_date, user_id
                )

                return {
                    "report_period": {"start": start_date, "end": end_date},
                    "user_id": user_id,
                    "media_stats": media_stats,
                    "storage_stats": storage_stats,
                    "user_activity": user_activity,
                    "popular_content": popular_content,
                    "generated_at": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                logger.error("Error in usage report task: %s", e)
                raise

        @self.celery_app.task(bind=True, name="maintenance.cleanup_temp_files")
        def cleanup_temp_files_task(task_self, older_than_hours: int = 24):
            """Clean up temporary files older than specified hours."""
            try:
                task_self.update_state(state="PROGRESS", meta={"step": "scanning"})

                import os
                import tempfile
                from pathlib import Path

                temp_dir = Path(tempfile.gettempdir())
                cutoff_time = time.time() - (older_than_hours * 3600)

                deleted_count = 0
                deleted_size = 0

                for file_path in temp_dir.rglob("ppl_meta_*"):
                    try:
                        if file_path.stat().st_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_count += 1
                            deleted_size += file_size

                            if deleted_count % 100 == 0:
                                task_self.update_state(
                                    state="PROGRESS",
                                    meta={
                                        "step": "cleaning",
                                        "deleted_count": deleted_count,
                                        "deleted_size": deleted_size,
                                    },
                                )
                    except (OSError, IOError) as e:
                        logger.warning(
                            "Could not delete temp file %s: %s", file_path, e
                        )

                return {
                    "deleted_count": deleted_count,
                    "deleted_size": deleted_size,
                    "older_than_hours": older_than_hours,
                }

            except Exception as e:
                logger.error("Error in cleanup task: %s", e)
                raise

        @self.celery_app.task(bind=True, name="maintenance.optimize_database")
        def optimize_database_task(task_self):
            """Run database optimization tasks."""
            try:
                task_self.update_state(state="PROGRESS", meta={"step": "starting"})

                from services.database_optimizer import DatabaseOptimizer

                optimizer = DatabaseOptimizer()

                # Analyze query performance
                task_self.update_state(
                    state="PROGRESS", meta={"step": "analyzing_queries"}
                )
                query_analysis = optimizer.analyze_query_performance()

                # Update table statistics
                task_self.update_state(
                    state="PROGRESS", meta={"step": "updating_statistics"}
                )
                stats_updated = optimizer.get_table_statistics()

                # Run vacuum analyze
                task_self.update_state(
                    state="PROGRESS", meta={"step": "vacuum_analyze"}
                )
                vacuum_results = optimizer.vacuum_analyze_tables()

                return {
                    "query_analysis": query_analysis,
                    "statistics_updated": stats_updated,
                    "vacuum_results": vacuum_results,
                    "completed_at": datetime.utcnow().isoformat(),
                }

            except Exception as e:
                logger.error("Error in database optimization task: %s", e)
                raise

        # Store task references
        self.tasks = {
            "generate_thumbnails": generate_thumbnails_task,
            "extract_metadata": extract_metadata_task,
            "generate_usage_report": generate_usage_report_task,
            "cleanup_temp_files": cleanup_temp_files_task,
            "optimize_database": optimize_database_task,
        }

    def submit_task(self, task_name: str, *args, **kwargs) -> Optional[str]:
        """Submit a task for background processing."""
        if not self.enabled:
            logger.warning(
                "Background tasks disabled - task %s not submitted", task_name
            )
            return None

        if task_name not in self.tasks:
            logger.error("Unknown task: %s", task_name)
            return None

        try:
            task = self.tasks[task_name]
            result = task.delay(*args, **kwargs)
            logger.info("Submitted task %s with ID: %s", task_name, result.id)
            return result.id
        except Exception as e:
            logger.error("Error submitting task %s: %s", task_name, e)
            return None

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """Get the status of a background task."""
        if not self.enabled:
            return {"status": "DISABLED", "result": None}

        try:
            result = AsyncResult(task_id, app=self.celery_app)

            status_info = {
                "id": task_id,
                "status": result.status,
                "ready": result.ready(),
                "successful": result.successful(),
                "failed": result.failed(),
            }

            if result.ready():
                if result.successful():
                    status_info["result"] = result.result
                else:
                    status_info["error"] = str(result.result)
            else:
                # Get progress info if available
                if hasattr(result, "info") and result.info:
                    status_info["progress"] = result.info

            return status_info

        except Exception as e:
            logger.error("Error getting task status for %s: %s", task_id, e)
            return {"status": "ERROR", "error": str(e)}

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a background task."""
        if not self.enabled:
            return False

        try:
            self.celery_app.control.revoke(task_id, terminate=True)
            logger.info("Cancelled task: %s", task_id)
            return True
        except Exception as e:
            logger.error("Error cancelling task %s: %s", task_id, e)
            return False

    def get_active_tasks(self) -> List[Dict[str, Any]]:
        """Get list of currently active tasks."""
        if not self.enabled:
            return []

        try:
            inspect = self.celery_app.control.inspect()
            active_tasks = inspect.active()

            if not active_tasks:
                return []

            all_tasks = []
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    all_tasks.append(
                        {
                            "worker": worker,
                            "id": task["id"],
                            "name": task["name"],
                            "args": task.get("args", []),
                            "kwargs": task.get("kwargs", {}),
                            "time_start": task.get("time_start"),
                        }
                    )

            return all_tasks

        except Exception as e:
            logger.error("Error getting active tasks: %s", e)
            return []

    def get_task_stats(self) -> Dict[str, Any]:
        """Get task processing statistics."""
        if not self.enabled:
            return {"enabled": False}

        try:
            inspect = self.celery_app.control.inspect()

            # Get worker statistics
            stats = inspect.stats()
            active_tasks = inspect.active()
            scheduled_tasks = inspect.scheduled()

            worker_count = len(stats) if stats else 0
            active_task_count = sum(
                len(tasks) for tasks in (active_tasks or {}).values()
            )
            scheduled_task_count = sum(
                len(tasks) for tasks in (scheduled_tasks or {}).values()
            )

            return {
                "enabled": True,
                "worker_count": worker_count,
                "active_tasks": active_task_count,
                "scheduled_tasks": scheduled_task_count,
                "workers": stats or {},
            }

        except Exception as e:
            logger.error("Error getting task stats: %s", e)
            return {"enabled": True, "error": str(e)}

    def schedule_recurring_tasks(self):
        """Schedule recurring maintenance tasks."""
        if not self.enabled:
            return

        from celery.schedules import crontab

        # Add periodic tasks
        self.celery_app.conf.beat_schedule = {
            "cleanup-temp-files": {
                "task": "maintenance.cleanup_temp_files",
                "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
                "args": (24,),  # Clean files older than 24 hours
            },
            "optimize-database": {
                "task": "maintenance.optimize_database",
                "schedule": crontab(
                    hour=3, minute=0, day_of_week=0
                ),  # Weekly on Sunday at 3 AM
            },
        }

        logger.info("Scheduled recurring maintenance tasks")


# Global task service instance
task_service = None


def init_task_service(
    broker_url: str = "redis://localhost:6379/1",
    result_backend: str = "redis://localhost:6379/1",
    app_name: str = "ppl_meta_tasks",
) -> BackgroundTaskService:
    """Initialize global task service."""
    global task_service
    task_service = BackgroundTaskService(
        broker_url=broker_url,
        result_backend=result_backend,
        app_name=app_name,
    )
    return task_service


def get_task_service() -> Optional[BackgroundTaskService]:
    """Get global task service instance."""
    return task_service
