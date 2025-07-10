"""
Database models for PPL Meta Orchestrator.
"""

from sqlalchemy import Column, DateTime, Integer, String, Text, func

from .database import Base


class WorkflowExecution(Base):
    """Track workflow execution history."""

    __tablename__ = "workflow_executions"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # pending, running, completed, failed
    input_data = Column(Text, nullable=True)
    output_data = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
