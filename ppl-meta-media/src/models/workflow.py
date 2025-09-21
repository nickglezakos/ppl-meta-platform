"""
PPL Meta Media Service - Workflow Models
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

from .base import Base


class MediaWorkflow(Base):
    """Model for tracking face detection workflow status and progress."""

    __tablename__ = "media_workflows"

    # Primary identification
    workflow_id = Column(String(36), primary_key=True)  # UUID

    # Workflow metadata
    user_id = Column(String(36), nullable=False)
    method = Column(String(50), nullable=False, default="two_stage")
    confidence_threshold = Column(Float, nullable=False, default=0.5)
    processing_priority = Column(String(20), nullable=False, default="normal")

    # Status tracking
    status = Column(
        String(20), nullable=False, default="queued"
    )  # queued, processing, completed, failed
    progress = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0

    # Counts
    total_count = Column(Integer, nullable=False, default=0)
    processed_count = Column(Integer, nullable=False, default=0)
    successful_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)

    # Media tracking
    media_ids = Column(JSON, nullable=False)  # List of media IDs
    current_media_id = Column(String(36), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Results and metadata
    workflow_metadata = Column(JSON, nullable=True)
    results_summary = Column(JSON, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert workflow to dictionary for API responses."""
        return {
            "workflow_id": self.workflow_id,
            "status": self.status,
            "progress": self.progress,
            "processed_count": self.processed_count,
            "total_count": self.total_count,
            "current_media_id": self.current_media_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "error_message": self.error_message,
            "results_summary": self.results_summary or {},
            "method": self.method,
            "confidence_threshold": self.confidence_threshold,
        }

    def update_progress(
        self, processed_count: int, current_media_id: Optional[str] = None
    ):
        """Update workflow progress."""
        self.processed_count = processed_count
        self.progress = processed_count / max(self.total_count, 1)
        if current_media_id:
            self.current_media_id = current_media_id

    def mark_started(self):
        """Mark workflow as started."""
        self.status = "processing"
        self.started_at = datetime.utcnow()

    def mark_completed(self, results_summary: Optional[Dict[str, Any]] = None):
        """Mark workflow as completed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.progress = 1.0
        if results_summary:
            self.results_summary = results_summary

    def mark_failed(self, error_message: str):
        """Mark workflow as failed."""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
