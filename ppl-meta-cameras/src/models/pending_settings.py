"""
Pending Camera Settings model for queuing setting updates when cameras are offline.

Supports hybrid architecture with both mobile-first and admin-driven settings:
- Mobile cameras can update their own settings
- Admins can remotely update settings (queued when offline)
- Admin override flag for enterprise policy enforcement
"""

from datetime import datetime
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Index
from sqlalchemy.sql import func
from src.database import Base


class PendingCameraSettings(Base):
    """
    Model for storing camera settings that should be applied when camera comes online.
    
    This allows administrators to update camera settings even when the camera is 
    offline (e.g., mobile cameras with intermittent connectivity). Settings are 
    applied on the next heartbeat or connection.
    
    Supports hybrid mobile + admin settings:
    - source: 'mobile' or 'admin' (who initiated the change)
    - admin_override: True = enterprise policy (mobile must apply)
    - priority: Higher values applied first (0-10 range)
    """

    __tablename__ = "pending_camera_settings"

    id = Column(Integer, primary_key=True, index=True)
    camera_device_id = Column(String(255), nullable=False, index=True)  # UUID of camera
    
    # Setting details
    setting_type = Column(String(100), nullable=False)  # 'name_update', 'workflow_settings', etc.
    setting_value = Column(JSON, nullable=False)  # The actual setting data
    
    # Hybrid settings support (Phase 3B)
    source = Column(String(20), default='admin', nullable=False)  # 'mobile' or 'admin'
    admin_override = Column(Boolean, default=False, nullable=False)  # Enterprise policy flag
    priority = Column(Integer, default=0, nullable=False)  # 0=low, 10=high
    
    # Metadata
    user_id = Column(String(100), nullable=False)  # User who requested the change
    created_at = Column(DateTime, default=func.now(), nullable=False)
    applied_at = Column(DateTime, nullable=True)  # When setting was applied (null until applied)
    
    # Status tracking
    is_applied = Column(String(20), default='pending')  # 'pending', 'applied', 'failed'
    error_message = Column(String(500), nullable=True)  # Error if application failed
    retry_count = Column(Integer, default=0)  # Number of application attempts

    # Composite indexes for efficient queries
    __table_args__ = (
        Index('ix_pending_camera_settings_lookup', 'camera_device_id', 'is_applied'),
        Index('ix_pending_settings_camera_applied', 'camera_device_id', 'applied_at'),
    )

    def __repr__(self):
        override_flag = " [OVERRIDE]" if self.admin_override else ""
        return (
            f"<PendingCameraSettings(id={self.id}, camera='{self.camera_device_id}', "
            f"type='{self.setting_type}', source='{self.source}', status='{self.is_applied}'{override_flag})>"
        )
