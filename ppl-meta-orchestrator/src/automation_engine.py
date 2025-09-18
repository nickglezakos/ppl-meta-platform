"""
PPL Meta Orchestrator - Automation Engine
Phase 2.4 Implementation: Time-based triggers and automated workflow execution
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union
from uuid import uuid4

from database import SessionLocal
from models import (
    AutomationExecution,
    AutomationRule,
    CameraSettings,
    WorkflowExecution,
)
from service_clients import ServiceClientManager
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of automation triggers"""

    INTERVAL = "interval"
    TIME_OF_DAY = "time_of_day"
    EVENT_BASED = "event_based"
    CONDITIONAL = "conditional"
    MANUAL = "manual"


class AutomationStatus(Enum):
    """Status of automation rules"""

    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


class ExecutionStatus(Enum):
    """Status of automation executions"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TriggerCondition:
    """Defines conditions for automation triggers"""

    trigger_type: TriggerType
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AutomationAction:
    """Defines actions to execute when triggered"""

    action_type: str  # workflow_execute, camera_record, method_execute, etc.
    target: str  # camera_device_id, workflow_id, method_name
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1=low, 5=high


@dataclass
class AutomationMetrics:
    """Performance metrics for automation rules"""

    rule_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time: float = 0.0
    last_execution_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    last_failure_time: Optional[datetime] = None
    success_rate: float = 1.0
    next_scheduled_time: Optional[datetime] = None


class AutomationEngine:
    """
    Comprehensive automation engine for PPL Meta Platform
    Handles time-based triggers, workflow automation, and intelligent processing
    """

    def __init__(self, service_manager: ServiceClientManager):
        self.service_manager = service_manager
        self.automation_rules: Dict[str, Dict[str, Any]] = {}
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self.scheduled_tasks: Dict[str, asyncio.Task] = {}
        self.automation_metrics: Dict[str, AutomationMetrics] = {}
        self.is_running = False

        # Configuration
        self.max_concurrent_executions = 10
        self.execution_timeout_seconds = 300  # 5 minutes
        self.cleanup_interval_hours = 24
        self.metrics_retention_days = 30

        logger.info("Automation Engine initialized")

    async def start_engine(self):
        """Start the automation engine and load existing rules"""
        try:
            self.is_running = True

            # Load automation rules from database
            await self._load_automation_rules()

            # Start scheduler for time-based triggers
            await self._start_scheduler()

            # Start cleanup task
            asyncio.create_task(self._periodic_cleanup())

            logger.info("✅ Automation Engine started successfully")

        except Exception as e:
            logger.error(f"Failed to start automation engine: {str(e)}")
            raise

    async def stop_engine(self):
        """Stop the automation engine and cleanup resources"""
        try:
            self.is_running = False

            # Cancel all scheduled tasks
            for task_id, task in self.scheduled_tasks.items():
                if not task.done():
                    task.cancel()
                    logger.info(f"Cancelled scheduled task: {task_id}")

            # Wait for active executions to complete or timeout
            await self._wait_for_active_executions()

            logger.info("✅ Automation Engine stopped successfully")

        except Exception as e:
            logger.error(f"Error stopping automation engine: {str(e)}")

    async def create_automation_rule(
        self,
        user_id: str,
        rule_name: str,
        trigger_condition: TriggerCondition,
        actions: List[AutomationAction],
        enabled: bool = True,
        description: Optional[str] = None,
    ) -> str:
        """Create a new automation rule"""
        rule_id = str(uuid4())

        automation_rule = {
            "rule_id": rule_id,
            "user_id": user_id,
            "rule_name": rule_name,
            "description": description,
            "trigger_condition": trigger_condition,
            "actions": actions,
            "enabled": enabled,
            "status": AutomationStatus.ACTIVE if enabled else AutomationStatus.DISABLED,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        self.automation_rules[rule_id] = automation_rule

        # Initialize metrics
        self.automation_metrics[rule_id] = AutomationMetrics(rule_id=rule_id)

        # Schedule the rule if it's time-based
        if trigger_condition.trigger_type in [
            TriggerType.INTERVAL,
            TriggerType.TIME_OF_DAY,
        ]:
            await self._schedule_rule(rule_id, automation_rule)

        # Persist to database
        await self._persist_automation_rule(automation_rule)

        logger.info(f"Created automation rule: {rule_name} ({rule_id})")
        return rule_id

    async def execute_automation_rule(
        self,
        rule_id: str,
        trigger_source: str = "manual",
        trigger_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Execute an automation rule"""
        if rule_id not in self.automation_rules:
            raise ValueError(f"Automation rule not found: {rule_id}")

        rule = self.automation_rules[rule_id]

        if rule["status"] != AutomationStatus.ACTIVE:
            logger.warning(f"Automation rule {rule_id} is not active")
            return ""

        # Check concurrent execution limit
        if len(self.active_executions) >= self.max_concurrent_executions:
            logger.warning(f"Max concurrent executions reached, queuing rule {rule_id}")
            # Could implement queuing here
            return ""

        execution_id = str(uuid4())
        execution_start = datetime.utcnow()

        execution_record = {
            "execution_id": execution_id,
            "rule_id": rule_id,
            "trigger_source": trigger_source,
            "trigger_metadata": trigger_metadata or {},
            "status": ExecutionStatus.RUNNING,
            "started_at": execution_start,
            "actions_completed": 0,
            "total_actions": len(rule["actions"]),
        }

        self.active_executions[execution_id] = execution_record

        try:
            # Execute all actions in the rule
            for i, action in enumerate(rule["actions"]):
                await self._execute_action(action, execution_id, rule["user_id"])
                execution_record["actions_completed"] = i + 1

            # Mark execution as completed
            execution_record["status"] = ExecutionStatus.COMPLETED
            execution_record["completed_at"] = datetime.utcnow()

            # Update metrics
            await self._update_automation_metrics(
                rule_id,
                True,
                (execution_record["completed_at"] - execution_start).total_seconds(),
            )

            logger.info(
                f"Automation rule {rule_id} executed successfully: {execution_id}"
            )

        except Exception as e:
            execution_record["status"] = ExecutionStatus.FAILED
            execution_record["error_message"] = str(e)
            execution_record["completed_at"] = datetime.utcnow()

            # Update metrics
            await self._update_automation_metrics(rule_id, False, 0.0)

            logger.error(f"Automation rule {rule_id} execution failed: {str(e)}")

        finally:
            # Persist execution record
            await self._persist_automation_execution(execution_record)

            # Remove from active executions
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

        return execution_id

    async def _execute_action(
        self, action: AutomationAction, execution_id: str, user_id: str
    ):
        """Execute a specific automation action"""
        action_type = action.action_type
        target = action.target
        parameters = action.parameters

        logger.info(f"Executing action {action_type} for {target}")

        if action_type == "workflow_execute":
            # Execute face detection workflow
            await self._execute_workflow_action(target, parameters, user_id)

        elif action_type == "camera_record":
            # Trigger camera recording
            await self._execute_camera_recording(target, parameters, user_id)

        elif action_type == "method_execute":
            # Execute specific detection method
            await self._execute_method_action(target, parameters, user_id)

        elif action_type == "notification_send":
            # Send notification (placeholder)
            await self._send_notification(target, parameters, user_id)

        else:
            logger.warning(f"Unknown action type: {action_type}")

    async def _execute_workflow_action(
        self, target: str, parameters: Dict[str, Any], user_id: str
    ):
        """Execute a face detection workflow"""
        try:
            # Use existing workflow orchestrator functionality
            workflow_params = {
                "user_id": user_id,
                "source_type": "automation",
                "camera_device_id": parameters.get("camera_device_id"),
                "media_id": parameters.get("media_id"),
                "processing_options": parameters.get("processing_options", {}),
            }

            # This would integrate with existing workflow orchestrator
            logger.info(
                f"Would execute workflow for user {user_id} with params: {workflow_params}"
            )

        except Exception as e:
            logger.error(f"Failed to execute workflow action: {str(e)}")
            raise

    async def _execute_camera_recording(
        self, target: str, parameters: Dict[str, Any], user_id: str
    ):
        """Trigger camera recording via Camera Service"""
        try:
            duration = parameters.get("duration_seconds", 30)
            recording_params = {
                "user_id": user_id,
                "duration_seconds": duration,
                "trigger_face_detection": parameters.get(
                    "trigger_face_detection", True
                ),
            }

            # Use service client to trigger recording
            response = await self.service_manager.camera_client.start_recording(
                target, recording_params
            )

            logger.info(f"Camera recording triggered for {target}: {response}")

        except Exception as e:
            logger.error(f"Failed to execute camera recording: {str(e)}")
            raise

    async def _execute_method_action(
        self, target: str, parameters: Dict[str, Any], user_id: str
    ):
        """Execute a specific detection method"""
        try:
            method_params = {
                "camera_device_id": parameters.get("camera_device_id"),
                "method_name": parameters.get("method_name"),
                "media_id": parameters.get("media_id"),
                "user_id": user_id,
            }

            # This would integrate with method lifecycle manager
            logger.info(f"Would execute method {target} with params: {method_params}")

        except Exception as e:
            logger.error(f"Failed to execute method action: {str(e)}")
            raise

    async def _send_notification(
        self, target: str, parameters: Dict[str, Any], user_id: str
    ):
        """Send notification (placeholder)"""
        try:
            message = parameters.get("message", "Automation executed")
            notification_type = parameters.get("type", "info")

            logger.info(
                f"Notification to {target}: {message} (type: {notification_type})"
            )

        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            raise

    async def _schedule_rule(self, rule_id: str, rule: Dict[str, Any]):
        """Schedule a time-based automation rule"""
        trigger = rule["trigger_condition"]

        if trigger.trigger_type == TriggerType.INTERVAL:
            # Schedule interval-based execution
            interval_seconds = trigger.parameters.get("interval_seconds", 3600)
            task = asyncio.create_task(
                self._interval_scheduler(rule_id, interval_seconds)
            )
            self.scheduled_tasks[rule_id] = task

        elif trigger.trigger_type == TriggerType.TIME_OF_DAY:
            # Schedule time-of-day execution
            target_time = trigger.parameters.get("time", "09:00")
            task = asyncio.create_task(
                self._time_of_day_scheduler(rule_id, target_time)
            )
            self.scheduled_tasks[rule_id] = task

    async def _interval_scheduler(self, rule_id: str, interval_seconds: int):
        """Run interval-based scheduling for a rule"""
        while self.is_running and rule_id in self.automation_rules:
            try:
                await asyncio.sleep(interval_seconds)

                if rule_id in self.automation_rules:
                    rule = self.automation_rules[rule_id]
                    if rule["status"] == AutomationStatus.ACTIVE:
                        await self.execute_automation_rule(
                            rule_id, trigger_source="interval_scheduler"
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error in interval scheduler for rule {rule_id}: {str(e)}"
                )
                await asyncio.sleep(60)  # Wait before retrying

    async def _time_of_day_scheduler(self, rule_id: str, target_time: str):
        """Run time-of-day scheduling for a rule"""
        while self.is_running and rule_id in self.automation_rules:
            try:
                # Calculate next execution time
                now = datetime.now()
                target_hour, target_minute = map(int, target_time.split(":"))

                next_execution = now.replace(
                    hour=target_hour, minute=target_minute, second=0, microsecond=0
                )

                if next_execution <= now:
                    next_execution += timedelta(days=1)

                # Wait until target time
                wait_seconds = (next_execution - now).total_seconds()
                await asyncio.sleep(wait_seconds)

                if rule_id in self.automation_rules:
                    rule = self.automation_rules[rule_id]
                    if rule["status"] == AutomationStatus.ACTIVE:
                        await self.execute_automation_rule(
                            rule_id, trigger_source="time_of_day_scheduler"
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"Error in time-of-day scheduler for rule {rule_id}: {str(e)}"
                )
                await asyncio.sleep(3600)  # Wait an hour before retrying

    async def _update_automation_metrics(
        self, rule_id: str, success: bool, execution_time: float
    ):
        """Update metrics for an automation rule"""
        if rule_id not in self.automation_metrics:
            self.automation_metrics[rule_id] = AutomationMetrics(rule_id=rule_id)

        metrics = self.automation_metrics[rule_id]
        metrics.total_executions += 1

        if success:
            metrics.successful_executions += 1
            metrics.last_success_time = datetime.utcnow()
        else:
            metrics.failed_executions += 1
            metrics.last_failure_time = datetime.utcnow()

        metrics.last_execution_time = datetime.utcnow()

        # Update success rate
        metrics.success_rate = (
            metrics.successful_executions / metrics.total_executions
            if metrics.total_executions > 0
            else 1.0
        )

        # Update average execution time (exponential moving average)
        if execution_time > 0:
            alpha = 0.2
            if metrics.average_execution_time == 0:
                metrics.average_execution_time = execution_time
            else:
                metrics.average_execution_time = (
                    alpha * execution_time
                    + (1 - alpha) * metrics.average_execution_time
                )

    async def get_automation_status(self) -> Dict[str, Any]:
        """Get overall automation engine status"""
        return {
            "engine_status": "running" if self.is_running else "stopped",
            "total_rules": len(self.automation_rules),
            "active_rules": len(
                [
                    r
                    for r in self.automation_rules.values()
                    if r["status"] == AutomationStatus.ACTIVE
                ]
            ),
            "active_executions": len(self.active_executions),
            "scheduled_tasks": len(self.scheduled_tasks),
            "metrics_summary": {
                rule_id: {
                    "total_executions": metrics.total_executions,
                    "success_rate": metrics.success_rate,
                    "average_execution_time": metrics.average_execution_time,
                }
                for rule_id, metrics in self.automation_metrics.items()
            },
        }

    async def get_rule_analytics(self, rule_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific automation rule"""
        if rule_id not in self.automation_rules:
            raise ValueError(f"Automation rule not found: {rule_id}")

        rule = self.automation_rules[rule_id]
        metrics = self.automation_metrics.get(
            rule_id, AutomationMetrics(rule_id=rule_id)
        )

        return {
            "rule_id": rule_id,
            "rule_name": rule["rule_name"],
            "status": rule["status"].value,
            "created_at": rule["created_at"].isoformat(),
            "metrics": {
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "success_rate": metrics.success_rate,
                "average_execution_time": metrics.average_execution_time,
                "last_execution_time": (
                    metrics.last_execution_time.isoformat()
                    if metrics.last_execution_time
                    else None
                ),
                "last_success_time": (
                    metrics.last_success_time.isoformat()
                    if metrics.last_success_time
                    else None
                ),
                "last_failure_time": (
                    metrics.last_failure_time.isoformat()
                    if metrics.last_failure_time
                    else None
                ),
            },
            "trigger_condition": {
                "type": rule["trigger_condition"].trigger_type.value,
                "parameters": rule["trigger_condition"].parameters,
            },
            "actions": [
                {
                    "type": action.action_type,
                    "target": action.target,
                    "priority": action.priority,
                }
                for action in rule["actions"]
            ],
        }

    async def _load_automation_rules(self):
        """Load automation rules from database"""
        try:
            with SessionLocal() as db:
                # Load automation rules (placeholder - would use actual DB model)
                logger.info("Loading automation rules from database")
                # Implementation would load from AutomationRule table

        except Exception as e:
            logger.error(f"Failed to load automation rules: {str(e)}")

    async def _persist_automation_rule(self, rule: Dict[str, Any]):
        """Persist automation rule to database"""
        try:
            with SessionLocal() as db:
                # Persist automation rule (placeholder - would use actual DB model)
                logger.info(f"Persisting automation rule: {rule['rule_id']}")
                # Implementation would save to AutomationRule table

        except Exception as e:
            logger.error(f"Failed to persist automation rule: {str(e)}")

    async def _persist_automation_execution(self, execution: Dict[str, Any]):
        """Persist automation execution record to database"""
        try:
            with SessionLocal() as db:
                # Persist execution record (placeholder - would use actual DB model)
                logger.info(
                    f"Persisting automation execution: {execution['execution_id']}"
                )
                # Implementation would save to AutomationExecution table

        except Exception as e:
            logger.error(f"Failed to persist automation execution: {str(e)}")

    async def _start_scheduler(self):
        """Start the main scheduler"""
        logger.info("Starting automation scheduler")

        # Schedule existing rules
        for rule_id, rule in self.automation_rules.items():
            if rule["enabled"] and rule["trigger_condition"].trigger_type in [
                TriggerType.INTERVAL,
                TriggerType.TIME_OF_DAY,
            ]:
                await self._schedule_rule(rule_id, rule)

    async def _periodic_cleanup(self):
        """Periodic cleanup of old executions and metrics"""
        while self.is_running:
            try:
                await asyncio.sleep(self.cleanup_interval_hours * 3600)

                # Cleanup old execution records
                cutoff_date = datetime.utcnow() - timedelta(
                    days=self.metrics_retention_days
                )

                logger.info(
                    f"Running periodic cleanup for records older than {cutoff_date}"
                )

                # Implementation would clean up old database records

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {str(e)}")

    async def _wait_for_active_executions(self, timeout_seconds: int = 30):
        """Wait for active executions to complete"""
        start_time = datetime.utcnow()

        while (
            self.active_executions
            and (datetime.utcnow() - start_time).total_seconds() < timeout_seconds
        ):
            await asyncio.sleep(1)

        if self.active_executions:
            logger.warning(
                f"Timeout waiting for {len(self.active_executions)} active executions"
            )
