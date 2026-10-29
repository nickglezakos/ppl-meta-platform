"""
Instant Detection flush logs (Automation domain).

Separate from trigger_execution_logs and action delivery logs.
Analytics for Instant Detection should read from this table.
"""

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.types import JSON

from .base import BaseModel


class InstantDetectionLog(BaseModel):
    """Flushed Instant Detection window after Y-cycle re-group + hierarchical merge."""

    __tablename__ = "instant_detection_logs"

    camera_device_id = Column(String(255), nullable=False, index=True)
    session_uuid = Column(UUID(as_uuid=True), nullable=True, index=True)
    flush_started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    flush_ended_at = Column(DateTime(timezone=True), nullable=False)
    cycle_count = Column(Integer, nullable=False, default=0)
    frames_per_cycle = Column(Integer, nullable=False, default=3)
    merge_threshold = Column(Float, nullable=True)
    people_count = Column(Integer, nullable=False, default=0)
    payload_json = Column(JSONB().with_variant(JSON, "sqlite"), nullable=False)
    log_type = Column(String(64), nullable=False, default="instant_detection", index=True)
