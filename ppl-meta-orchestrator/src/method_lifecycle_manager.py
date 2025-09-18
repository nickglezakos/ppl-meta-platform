"""
PPL Meta Orchestrator - Method Lifecycle Management
Phase 2.3 Implementation: Separate processing tracking for each detection method per camera
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from database import SessionLocal
from models import CameraSettings, MethodStatus
from service_clients import ServiceClientManager
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class MethodExecutionStatus(Enum):
    """Status tracking for individual detection methods."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERING = "recovering"
    DISABLED = "disabled"


class MethodPriority(Enum):
    """Priority levels for method execution."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class MethodPerformanceMetrics:
    """Performance tracking for detection methods."""

    method_name: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_processing_time: float = 0.0
    last_execution_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    current_streak: int = 0  # Success streak
    max_streak: int = 0
    error_rate: float = 0.0
    reliability_score: float = 1.0


@dataclass
class MethodConfiguration:
    """Configuration settings for individual methods."""

    method_name: str
    enabled: bool = True
    priority: MethodPriority = MethodPriority.NORMAL
    max_retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    timeout_seconds: float = 30.0
    fallback_methods: List[str] = field(default_factory=list)
    quality_threshold: float = 0.7
    confidence_threshold: float = 0.5


class MethodLifecycleManager:
    """
    Manages the lifecycle of individual detection methods per camera.
    Tracks status, performance, and handles method-specific processing.
    """

    def __init__(self, service_manager: ServiceClientManager):
        """Initialize the method lifecycle manager."""
        self.service_manager = service_manager
        self.method_states: Dict[str, Dict[str, MethodExecutionStatus]] = {}
        self.method_metrics: Dict[str, Dict[str, MethodPerformanceMetrics]] = {}
        self.method_configs: Dict[str, Dict[str, MethodConfiguration]] = {}
        self.active_tasks: Dict[str, Set[str]] = (
            {}
        )  # camera_id -> set of active methods
        self.processing_lock = asyncio.Lock()

        # Available detection methods
        self.available_methods = ["haar", "dlib", "mtcnn", "two_stage"]

        logger.info("Method Lifecycle Manager initialized")

    async def initialize_camera_methods(
        self,
        camera_device_id: str,
        user_id: str,
        enabled_methods: Optional[List[str]] = None,
    ) -> Dict[str, MethodConfiguration]:
        """
        Initialize method configurations for a camera.

        Args:
            camera_device_id: Camera device identifier
            user_id: User identifier
            enabled_methods: List of methods to enable (default: all available)

        Returns:
            Dictionary of method configurations
        """
        if enabled_methods is None:
            enabled_methods = self.available_methods.copy()

        logger.info(
            "Initializing methods for camera %s: %s", camera_device_id, enabled_methods
        )

        # Initialize camera in tracking dictionaries
        if camera_device_id not in self.method_states:
            self.method_states[camera_device_id] = {}
            self.method_metrics[camera_device_id] = {}
            self.method_configs[camera_device_id] = {}
            self.active_tasks[camera_device_id] = set()

        # Create configurations for each method
        configs = {}
        for method_name in enabled_methods:
            if method_name in self.available_methods:
                config = await self._create_method_configuration(
                    camera_device_id, method_name, user_id
                )
                configs[method_name] = config
                self.method_configs[camera_device_id][method_name] = config
                self.method_states[camera_device_id][
                    method_name
                ] = MethodExecutionStatus.IDLE
                self.method_metrics[camera_device_id][method_name] = (
                    MethodPerformanceMetrics(method_name)
                )

        await self._persist_method_lifecycles(camera_device_id, user_id, configs)

        logger.info(
            "Initialized %d methods for camera %s", len(configs), camera_device_id
        )
        return configs

    async def _create_method_configuration(
        self, camera_device_id: str, method_name: str, user_id: str
    ) -> MethodConfiguration:
        """Create method configuration with intelligent defaults."""

        # Method-specific configurations
        method_defaults = {
            "haar": MethodConfiguration(
                method_name="haar",
                priority=MethodPriority.HIGH,  # Fast, good for initial detection
                timeout_seconds=15.0,
                fallback_methods=["dlib"],
                quality_threshold=0.6,
            ),
            "dlib": MethodConfiguration(
                method_name="dlib",
                priority=MethodPriority.NORMAL,
                timeout_seconds=25.0,
                fallback_methods=["haar", "mtcnn"],
                quality_threshold=0.7,
            ),
            "mtcnn": MethodConfiguration(
                method_name="mtcnn",
                priority=MethodPriority.NORMAL,
                timeout_seconds=35.0,
                fallback_methods=["dlib", "haar"],
                quality_threshold=0.8,
            ),
            "two_stage": MethodConfiguration(
                method_name="two_stage",
                priority=MethodPriority.LOW,  # Most accurate but slower
                timeout_seconds=45.0,
                fallback_methods=["dlib", "mtcnn"],
                quality_threshold=0.9,
            ),
        }

        config = method_defaults.get(method_name, MethodConfiguration(method_name))

        # Load user preferences from database if available
        try:
            with SessionLocal() as db:
                camera_settings = (
                    db.query(CameraSettings)
                    .filter(
                        and_(
                            CameraSettings.camera_device_id == camera_device_id,
                            CameraSettings.user_id == user_id,
                        )
                    )
                    .first()
                )

                if camera_settings and camera_settings.preferred_methods:
                    # Adjust priority based on user preferences
                    if method_name in camera_settings.preferred_methods:
                        config.priority = MethodPriority.HIGH

        except Exception as e:
            logger.warning(
                "Could not load user preferences for camera %s: %s",
                camera_device_id,
                str(e),
            )

        return config

    async def execute_method_processing(
        self,
        camera_device_id: str,
        method_name: str,
        media_id: str,
        processing_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute processing for a specific method with lifecycle tracking.

        Args:
            camera_device_id: Camera device identifier
            method_name: Detection method to execute
            media_id: Media file identifier
            processing_params: Processing parameters

        Returns:
            Processing results with method-specific metrics
        """
        start_time = datetime.utcnow()
        execution_id = str(uuid4())

        logger.info(
            "Starting method %s execution for camera %s, media %s",
            method_name,
            camera_device_id,
            media_id,
        )

        async with self.processing_lock:
            # Update method status
            if camera_device_id in self.method_states:
                self.method_states[camera_device_id][
                    method_name
                ] = MethodExecutionStatus.PROCESSING
                self.active_tasks[camera_device_id].add(method_name)

        try:
            # Get method configuration
            config = self.method_configs.get(camera_device_id, {}).get(method_name)
            if not config or not config.enabled:
                raise ValueError(f"Method {method_name} not enabled for camera")

            # Execute processing with timeout
            result = await asyncio.wait_for(
                self._execute_vision_processing(
                    method_name, media_id, processing_params, config
                ),
                timeout=config.timeout_seconds,
            )

            # Calculate processing time
            processing_time = (datetime.utcnow() - start_time).total_seconds()

            # Update success metrics
            await self._update_method_metrics(
                camera_device_id, method_name, True, processing_time
            )

            # Update status
            async with self.processing_lock:
                if camera_device_id in self.method_states:
                    self.method_states[camera_device_id][
                        method_name
                    ] = MethodExecutionStatus.COMPLETED
                    self.active_tasks[camera_device_id].discard(method_name)

            logger.info(
                "Method %s completed for camera %s in %.2f seconds",
                method_name,
                camera_device_id,
                processing_time,
            )

            return {
                "execution_id": execution_id,
                "method_name": method_name,
                "status": "success",
                "processing_time_seconds": processing_time,
                "results": result,
                "timestamp": start_time.isoformat(),
            }

        except asyncio.TimeoutError:
            await self._handle_method_timeout(camera_device_id, method_name, config)
            raise
        except Exception as e:
            await self._handle_method_error(
                camera_device_id, method_name, str(e), config
            )
            raise
        finally:
            async with self.processing_lock:
                if (
                    camera_device_id in self.active_tasks
                    and method_name in self.active_tasks[camera_device_id]
                ):
                    self.active_tasks[camera_device_id].discard(method_name)

    async def _execute_vision_processing(
        self,
        method_name: str,
        media_id: str,
        processing_params: Dict[str, Any],
        config: MethodConfiguration,
    ) -> Dict[str, Any]:
        """Execute the actual vision processing with method-specific parameters."""

        # Prepare method-specific parameters
        vision_params = {
            "media_id": media_id,
            "method": method_name,
            "confidence_threshold": config.confidence_threshold,
            "quality_threshold": config.quality_threshold,
            **processing_params,
        }

        # Call Vision Service
        vision_client = await self.service_manager.get_vision_client()
        result = await vision_client.process_face_detection(vision_params)

        return result

    async def _update_method_metrics(
        self,
        camera_device_id: str,
        method_name: str,
        success: bool,
        processing_time: float,
    ):
        """Update performance metrics for a method."""

        if camera_device_id not in self.method_metrics:
            return

        metrics = self.method_metrics[camera_device_id].get(method_name)
        if not metrics:
            return

        # Update execution counts
        metrics.total_executions += 1
        if success:
            metrics.successful_executions += 1
            metrics.last_success_time = datetime.utcnow()
            metrics.current_streak += 1
            metrics.max_streak = max(metrics.max_streak, metrics.current_streak)
        else:
            metrics.failed_executions += 1
            metrics.last_failure_time = datetime.utcnow()
            metrics.current_streak = 0

        metrics.last_execution_time = datetime.utcnow()

        # Update averages
        if metrics.total_executions > 0:
            metrics.error_rate = metrics.failed_executions / metrics.total_executions

        # Update average processing time (exponential moving average)
        if metrics.average_processing_time == 0:
            metrics.average_processing_time = processing_time
        else:
            alpha = 0.1  # Smoothing factor
            metrics.average_processing_time = (
                alpha * processing_time + (1 - alpha) * metrics.average_processing_time
            )

        # Calculate reliability score
        success_rate = (
            metrics.successful_executions / metrics.total_executions
            if metrics.total_executions > 0
            else 1.0
        )
        streak_factor = min(metrics.current_streak / 10.0, 1.0)
        metrics.reliability_score = success_rate * 0.7 + streak_factor * 0.3

    async def _handle_method_timeout(
        self, camera_device_id: str, method_name: str, config: MethodConfiguration
    ):
        """Handle method execution timeout."""

        logger.warning(
            "Method %s timed out for camera %s after %d seconds",
            method_name,
            camera_device_id,
            config.timeout_seconds,
        )

        # Update metrics
        await self._update_method_metrics(
            camera_device_id, method_name, False, config.timeout_seconds
        )

        # Update status
        async with self.processing_lock:
            if camera_device_id in self.method_states:
                self.method_states[camera_device_id][
                    method_name
                ] = MethodExecutionStatus.FAILED

    async def _handle_method_error(
        self,
        camera_device_id: str,
        method_name: str,
        error_message: str,
        config: MethodConfiguration,
    ):
        """Handle method execution error with potential recovery."""

        logger.error(
            "Method %s failed for camera %s: %s",
            method_name,
            camera_device_id,
            error_message,
        )

        # Update metrics
        await self._update_method_metrics(camera_device_id, method_name, False, 0.0)

        # Check if method should be disabled due to high error rate
        metrics = self.method_metrics.get(camera_device_id, {}).get(method_name)
        if metrics and metrics.error_rate > 0.8 and metrics.total_executions > 5:
            logger.warning(
                "Disabling method %s for camera %s due to high error rate: %.2f",
                method_name,
                camera_device_id,
                metrics.error_rate,
            )
            config.enabled = False

            async with self.processing_lock:
                if camera_device_id in self.method_states:
                    self.method_states[camera_device_id][
                        method_name
                    ] = MethodExecutionStatus.DISABLED
        else:
            async with self.processing_lock:
                if camera_device_id in self.method_states:
                    self.method_states[camera_device_id][
                        method_name
                    ] = MethodExecutionStatus.FAILED

    async def get_method_status(
        self, camera_device_id: str, method_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get status information for methods on a camera.

        Args:
            camera_device_id: Camera device identifier
            method_name: Specific method name (optional, returns all if None)

        Returns:
            Method status information
        """

        if camera_device_id not in self.method_states:
            return {"error": "Camera not initialized"}

        camera_states = self.method_states[camera_device_id]
        camera_metrics = self.method_metrics.get(camera_device_id, {})
        camera_configs = self.method_configs.get(camera_device_id, {})

        if method_name:
            if method_name not in camera_states:
                return {"error": f"Method {method_name} not found"}

            return {
                "method_name": method_name,
                "status": camera_states[method_name].value,
                "metrics": (
                    camera_metrics.get(method_name).__dict__
                    if camera_metrics.get(method_name)
                    else {}
                ),
                "configuration": (
                    camera_configs.get(method_name).__dict__
                    if camera_configs.get(method_name)
                    else {}
                ),
                "is_active": method_name
                in self.active_tasks.get(camera_device_id, set()),
            }
        else:
            # Return all methods
            methods_status = {}
            for method in camera_states:
                methods_status[method] = {
                    "status": camera_states[method].value,
                    "metrics": (
                        camera_metrics.get(method).__dict__
                        if camera_metrics.get(method)
                        else {}
                    ),
                    "configuration": (
                        camera_configs.get(method).__dict__
                        if camera_configs.get(method)
                        else {}
                    ),
                    "is_active": method
                    in self.active_tasks.get(camera_device_id, set()),
                }

            return {
                "camera_device_id": camera_device_id,
                "methods": methods_status,
                "active_methods_count": len(
                    self.active_tasks.get(camera_device_id, set())
                ),
                "total_methods_count": len(camera_states),
            }

    async def _persist_method_lifecycles(
        self,
        camera_device_id: str,
        user_id: str,
        configs: Dict[str, MethodConfiguration],
    ):
        """Persist method lifecycle information to database."""

        try:
            with SessionLocal() as db:
                for method_name, config in configs.items():
                    # Check if lifecycle record exists
                    existing = (
                        db.query(MethodStatus)
                        .filter(
                            and_(
                                MethodStatus.camera_device_id == camera_device_id,
                                MethodStatus.method_name == method_name,
                            )
                        )
                        .first()
                    )

                    if existing:
                        # Update existing record
                        existing.status = MethodExecutionStatus.IDLE.value
                        existing.enabled = config.enabled
                        existing.priority = config.priority.value
                        existing.last_updated = datetime.utcnow()
                    else:
                        # Create new record
                        lifecycle = MethodStatus(
                            camera_device_id=camera_device_id,
                            user_id=user_id,
                            method_name=method_name,
                            status=MethodExecutionStatus.IDLE.value,
                            enabled=config.enabled,
                            priority=config.priority.value,
                            created_at=datetime.utcnow(),
                            last_updated=datetime.utcnow(),
                        )
                        db.add(lifecycle)

                db.commit()

        except Exception as e:
            logger.error(
                "Failed to persist method lifecycles for camera %s: %s",
                camera_device_id,
                str(e),
            )

    async def get_camera_analytics(self, camera_device_id: str) -> Dict[str, Any]:
        """Get comprehensive analytics for all methods on a camera."""

        if camera_device_id not in self.method_metrics:
            return {"error": "Camera not found"}

        analytics = {
            "camera_device_id": camera_device_id,
            "timestamp": datetime.utcnow().isoformat(),
            "methods": {},
            "summary": {
                "total_methods": 0,
                "active_methods": 0,
                "enabled_methods": 0,
                "disabled_methods": 0,
                "average_reliability": 0.0,
                "total_executions": 0,
                "overall_success_rate": 0.0,
            },
        }

        total_executions = 0
        total_successes = 0
        total_reliability = 0.0
        method_count = 0

        for method_name, metrics in self.method_metrics[camera_device_id].items():
            config = self.method_configs[camera_device_id].get(method_name)
            status = self.method_states[camera_device_id].get(method_name)

            analytics["methods"][method_name] = {
                "metrics": metrics.__dict__,
                "status": status.value if status else "unknown",
                "enabled": config.enabled if config else False,
                "is_active": method_name
                in self.active_tasks.get(camera_device_id, set()),
            }

            total_executions += metrics.total_executions
            total_successes += metrics.successful_executions
            total_reliability += metrics.reliability_score
            method_count += 1

            if config and config.enabled:
                analytics["summary"]["enabled_methods"] += 1
            else:
                analytics["summary"]["disabled_methods"] += 1

            if method_name in self.active_tasks.get(camera_device_id, set()):
                analytics["summary"]["active_methods"] += 1

        analytics["summary"]["total_methods"] = method_count
        analytics["summary"]["total_executions"] = total_executions
        analytics["summary"]["overall_success_rate"] = (
            total_successes / total_executions if total_executions > 0 else 0.0
        )
        analytics["summary"]["average_reliability"] = (
            total_reliability / method_count if method_count > 0 else 0.0
        )

        return analytics
