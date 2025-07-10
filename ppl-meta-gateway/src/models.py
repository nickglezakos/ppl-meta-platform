"""
Database models for PPL Meta Gateway.
"""

from sqlalchemy import Column, DateTime, Integer, String, func

from .database import Base


class GatewayRequest(Base):
    """Log of gateway requests for analytics."""

    __tablename__ = "gateway_requests"

    id = Column(Integer, primary_key=True, index=True)
    method = Column(String(10), nullable=False)
    path = Column(String(500), nullable=False)
    user_id = Column(String(100), nullable=True)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
