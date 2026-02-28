"""
Trigger model for event-based notifications and alerts.
"""

import enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import BaseModel


class PersonCountOperator(str, enum.Enum):
    """Operators for person count comparison."""

    LESS_THAN = "less_than"
    MORE_THAN = "more_than"
    EQUALS = "equals"
    BETWEEN = "between"


class AgeRangeOperator(str, enum.Enum):
    """Operators for age range comparison."""

    LESS_THAN = "less_than"  # Age < threshold
    MORE_THAN = "more_than"  # Age > threshold
    BETWEEN = "between"  # threshold_min <= Age <= threshold_max
    ANY = "any"  # No age filtering


class GenderFilter(str, enum.Enum):
    """Gender filter options."""

    MALE = "male"
    FEMALE = "female"
    ANY = "any"  # No gender filtering


class TriggerAction(str, enum.Enum):
    """Actions to execute when trigger conditions are met."""

    ALERT = "alert"
    EMAIL = "email"
    WEBHOOK = "webhook"
    LOG = "log"


class Trigger(BaseModel):
    """
    Trigger entity for automated event-based notifications.
    
    Triggers monitor demographic conditions and execute actions when conditions are met.
    All condition logic is now unified in demographic_conditions array.
    """

    __tablename__ = "triggers"

    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4, index=True)
    
    # Demographic conditions - unified condition system
    demographic_conditions = Column(
        Text,
        nullable=False,
        comment='JSON array of demographic conditions: [{"field": "people_count|percent_male|percent_age_18_24|...", "operator": "gt|gte|lt|lte|eq", "value": number}]'
    )
    
    # Time conditions
    time_span = Column(
        String(100),
        nullable=False,
        comment="Time span when trigger is active (e.g., 'Mon-Fri 09:00-17:00', 'any')"
    )
    
    # Camera reference
    camera_device_id = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Device ID of the camera from Camera service (e.g., 'usb_camera_0', 'rtsp_192.168.1.76_554')"
    )
    camera_name = Column(
        String(255),
        nullable=True,
        comment="Friendly name of the camera (e.g., 'Front Door', 'Main Entrance')"
    )
    
    # Link to user-defined action (required)
    action_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey('user_trigger_actions.uuid', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment="UUID of the linked user action (supports alert, webhook, email, digital_signage, etc.)"
    )
    
    # Relationship to user action
    user_action = relationship("UserTriggerAction", foreign_keys=[action_uuid])

    # Trigger mode configuration
    trigger_mode = Column(
        String(30),
        nullable=False,
        default="demographic",
        index=True,
        comment="Trigger mode: demographic | ppl_match"
    )
    ppl_match_group_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Target individual group ID for ppl_match mode"
    )
    ppl_match_similarity_threshold = Column(
        Float,
        nullable=False,
        default=0.75,
        comment="Minimum similarity threshold for ppl_match mode"
    )
    ppl_match_top_k = Column(
        Integer,
        nullable=False,
        default=1,
        comment="Maximum number of top matches to keep for ppl_match mode"
    )
    
    # Tracking configuration
    tracking_duration = Column(
        String(50),
        nullable=False,
        default="10 minutes",
        index=True,
        comment='Time window for MVR search (e.g., "5 seconds", "10 minutes", "2 hours", "1 day")'
    )
    
    # Trigger state and behavior
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the trigger is currently active"
    )
    
    cooldown_seconds = Column(
        Integer,
        nullable=False,
        default=60,
        comment="Minimum seconds between trigger firings to prevent spam"
    )
    
    last_fired_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp of last trigger firing"
    )
    last_match_info = Column(
        Text,
        nullable=True,
        comment="JSON payload containing latest ppl_match metadata"
    )
    last_matched_at = Column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Timestamp of latest successful ppl_match evaluation"
    )
    
    # Metadata
    name = Column(
        String(255),
        nullable=True,
        comment="Optional friendly name for the trigger"
    )
    description = Column(
        String(500),
        nullable=True,
        comment="Optional description of what this trigger monitors"
    )
    
    def __repr__(self):
        conditions_count = 0
        try:
            import json
            conditions = json.loads(self.demographic_conditions) if isinstance(self.demographic_conditions, str) else self.demographic_conditions
            conditions_count = len(conditions) if conditions else 0
        except:
            pass
        return f"<Trigger {self.uuid} - {conditions_count} conditions, active={self.is_active}>"
