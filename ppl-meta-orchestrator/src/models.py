"""
Database models for PPL Meta Orchestrator - Phase 1 Implementation.
Enhanced with camera integration, workflow tracking, and complete traceability.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import Base, SessionLocal
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship


class WorkflowExecution(Base):
    """Enhanced workflow execution tracking with camera integration."""

    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(100), nullable=False, unique=True, index=True)
    workflow_type = Column(
        String(50), nullable=False
    )  # bulk_processing, camera_triggered, etc.
    status = Column(
        String(20), nullable=False
    )  # created, queued, processing, completed, failed, cancelled
    user_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_media_count = Column(Integer, default=0)
    processed_media_count = Column(Integer, default=0)
    failed_media_count = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    workflow_metadata = Column(JSON, nullable=True)

    # Relationships
    method_lifecycles = relationship(
        "MethodLifecycle", back_populates="workflow", cascade="all, delete-orphan"
    )
    camera_workflows = relationship(
        "CameraWorkflow", back_populates="workflow", cascade="all, delete-orphan"
    )
    trace_logs = relationship(
        "TraceabilityLog", back_populates="workflow", cascade="all, delete-orphan"
    )


class MethodLifecycle(Base):
    """Track individual detection method lifecycle within workflows."""

    __tablename__ = "method_lifecycles"

    id = Column(Integer, primary_key=True, index=True)
    lifecycle_id = Column(String(100), nullable=False, unique=True, index=True)
    workflow_id = Column(
        String(100), ForeignKey("workflow_executions.workflow_id"), nullable=False
    )
    method = Column(String(50), nullable=False)  # mtcnn, opencv, etc.
    media_id = Column(String(100), nullable=False, index=True)
    camera_device_id = Column(String(100), nullable=True, index=True)
    status = Column(
        String(20), nullable=False
    )  # created, processing, completed, failed
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    processing_options = Column(JSON, nullable=True)
    results_count = Column(Integer, nullable=True)
    confidence_scores = Column(JSON, nullable=True)  # Store as JSON array
    trace_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=True, index=True)

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="method_lifecycles")


class CameraWorkflow(Base):
    """Track camera-specific workflow associations."""

    __tablename__ = "camera_workflows"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(
        String(100), ForeignKey("workflow_executions.workflow_id"), nullable=False
    )
    camera_device_id = Column(String(100), nullable=False, index=True)
    recording_session_id = Column(String(100), nullable=True, index=True)
    media_id = Column(String(100), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="camera_workflows")


class CameraSettings(Base):
    """Store user camera settings for automated workflows."""

    __tablename__ = "camera_settings"

    id = Column(Integer, primary_key=True, index=True)
    camera_device_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    auto_face_detection = Column(Boolean, default=True)
    detection_methods = Column(JSON, nullable=True)  # ["mtcnn", "opencv"]
    processing_options = Column(JSON, nullable=True)
    interval_minutes = Column(Integer, nullable=True)  # For scheduled recording
    notification_settings = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Composite unique constraint on camera + user
    __table_args__ = ({"sqlite_autoincrement": True},)


class IntervalSchedule(Base):
    """Track automated interval-based recording schedules."""

    __tablename__ = "interval_schedules"

    id = Column(Integer, primary_key=True, index=True)
    schedule_id = Column(String(100), nullable=False, unique=True, index=True)
    camera_device_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    interval_minutes = Column(Integer, nullable=False)
    recording_duration_seconds = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    next_execution = Column(DateTime(timezone=True), nullable=True)
    last_execution = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TraceabilityLog(Base):
    """Comprehensive traceability logging for audit trails."""

    __tablename__ = "traceability_logs"

    id = Column(Integer, primary_key=True, index=True)
    trace_id = Column(String(100), nullable=False, index=True)
    workflow_id = Column(
        String(100),
        ForeignKey("workflow_executions.workflow_id"),
        nullable=True,
        index=True,
    )
    parent_trace_id = Column(String(100), nullable=True, index=True)
    operation = Column(String(100), nullable=False)
    service_name = Column(String(50), nullable=False)
    endpoint = Column(String(200), nullable=True)
    user_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(100), nullable=True, index=True)
    camera_device_id = Column(String(100), nullable=True, index=True)
    media_id = Column(String(100), nullable=True, index=True)
    status = Column(String(20), nullable=False)  # success, error, timeout
    response_time_ms = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    trace_metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="trace_logs")


class ProcessingStatistics(Base):
    """Store processing statistics for analytics and optimization."""

    __tablename__ = "processing_statistics"

    id = Column(Integer, primary_key=True, index=True)
    statistic_id = Column(String(100), nullable=False, unique=True, index=True)
    camera_device_id = Column(String(100), nullable=True, index=True)
    method = Column(String(50), nullable=False, index=True)
    media_count = Column(Integer, default=0)
    total_faces_detected = Column(Integer, default=0)
    average_confidence = Column(Float, nullable=True)
    total_processing_time_seconds = Column(Float, default=0)
    average_processing_time_seconds = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)  # Percentage
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CameraEvent(Base):
    """Log camera events for audit and debugging."""

    __tablename__ = "camera_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), nullable=False, unique=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    camera_device_id = Column(String(100), nullable=False, index=True)
    recording_session_id = Column(String(100), nullable=True, index=True)
    video_file_path = Column(String(500), nullable=True)
    user_id = Column(String(100), nullable=True, index=True)
    recording_duration_seconds = Column(Float, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    workflow_id = Column(String(100), nullable=True, index=True)
    processed = Column(Boolean, default=False)
    processing_result = Column(String(20), nullable=True)  # success, failed, skipped
    error_message = Column(Text, nullable=True)
    stats_metadata = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


class MethodStatus(Base):
    """Track the persistent status and performance of detection methods per camera."""

    __tablename__ = "method_status"

    id = Column(Integer, primary_key=True, index=True)
    camera_device_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    method_name = Column(String(50), nullable=False, index=True)
    status = Column(String(20), nullable=False, index=True)
    enabled = Column(Boolean, default=True)
    priority = Column(Integer, default=2)

    # Performance metrics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    average_processing_time = Column(Float, default=0.0)
    reliability_score = Column(Float, default=1.0)
    error_rate = Column(Float, default=0.0)
    current_streak = Column(Integer, default=0)
    max_streak = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
    last_execution_time = Column(DateTime(timezone=True), nullable=True)
    last_success_time = Column(DateTime(timezone=True), nullable=True)
    last_failure_time = Column(DateTime(timezone=True), nullable=True)

    # Configuration and metadata
    configuration = Column(JSON, nullable=True)
    execution_metadata = Column(JSON, nullable=True)


class AutomationRule(Base):
    """Track automation rules for scheduled and event-driven workflows."""

    __tablename__ = "automation_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(String(100), nullable=False, unique=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    rule_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    # Trigger configuration
    trigger_type = Column(
        String(50), nullable=False
    )  # interval, time_of_day, event_based
    trigger_parameters = Column(JSON, nullable=True)
    trigger_conditions = Column(JSON, nullable=True)

    # Action configuration
    actions = Column(JSON, nullable=False)  # List of actions to execute

    # Status and control
    enabled = Column(Boolean, default=True, index=True)
    status = Column(String(20), default="active")  # active, paused, disabled, error

    # Metrics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    average_execution_time = Column(Float, default=0.0)
    success_rate = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
    last_execution_time = Column(DateTime(timezone=True), nullable=True)
    last_success_time = Column(DateTime(timezone=True), nullable=True)
    last_failure_time = Column(DateTime(timezone=True), nullable=True)
    next_scheduled_time = Column(DateTime(timezone=True), nullable=True)

    # Configuration metadata
    rule_metadata = Column(JSON, nullable=True)


class AutomationExecution(Base):
    """Track individual automation rule executions."""

    __tablename__ = "automation_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String(100), nullable=False, unique=True, index=True)
    rule_id = Column(
        String(100), ForeignKey("automation_rules.rule_id"), nullable=False
    )

    # Execution details
    trigger_source = Column(String(100), nullable=False)  # manual, scheduler, event
    trigger_metadata = Column(JSON, nullable=True)
    status = Column(
        String(20), nullable=False
    )  # pending, running, completed, failed, cancelled

    # Progress tracking
    actions_completed = Column(Integer, default=0)
    total_actions = Column(Integer, default=0)
    current_action = Column(String(200), nullable=True)

    # Results and errors
    execution_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    # Execution metadata
    execution_metadata = Column(JSON, nullable=True)
