"""
Trigger execution log model for audit and ppl_match observability.
"""

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class TriggerExecutionLog(BaseModel):
    """Audit log for trigger evaluations and executions."""

    __tablename__ = "trigger_execution_logs"

    trigger_uuid = Column(UUID(as_uuid=True), nullable=False, index=True)
    trigger_id = Column(Integer, ForeignKey("triggers.id", ondelete="SET NULL"), nullable=True, index=True)
    trigger_name = Column(String(255), nullable=True)
    trigger_mode = Column(String(30), nullable=False, default="demographic", index=True)
    camera_device_id = Column(String(255), nullable=False, index=True)

    source_mvr_uuid = Column(String(255), nullable=True, index=True)
    matched_group_id = Column(String(255), nullable=True, index=True)
    matched_member_uuid = Column(String(255), nullable=True, index=True)
    similarity_score = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    match_details_json = Column(Text, nullable=True)

    passed = Column(Boolean, nullable=False, default=False, index=True)
    reason = Column(String(500), nullable=True)
    action_executed = Column(Boolean, nullable=False, default=False)
    evaluated_at = Column(DateTime(timezone=True), nullable=False, index=True)

    trigger = relationship("Trigger", foreign_keys=[trigger_id])
