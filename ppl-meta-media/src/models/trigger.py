"""
Trigger model for event-based notifications and alerts.
"""

import enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
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
    
    Triggers monitor specific conditions (person count, age range, time span, etc.)
    and execute actions when conditions are met.
    """

    __tablename__ = "triggers"

    uuid = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid4, index=True)
    
    # Person count conditions
    person_count_operator = Column(
        String(50),
        nullable=False,
        default="more_than",
        comment="Comparison operator for person count"
    )
    person_count_value = Column(
        String(50),
        nullable=False,
        comment="Person count threshold value (e.g., '5', '10-20' for BETWEEN)"
    )
    
    # Age range filter (optional)
    age_range_operator = Column(
        String(50),
        nullable=True,
        default=None,
        comment="Age comparison operator (optional filter)"
    )
    age_range_value = Column(
        String(50),
        nullable=True,
        comment="Age threshold value (e.g., '18', '65', '18-30' for BETWEEN)"
    )
    
    # Gender filter (optional)
    gender_filter = Column(
        String(50),
        nullable=True,
        default=GenderFilter.ANY,
        comment="Gender filter (male, female, any)"
    )
    
    # Time conditions
    time_span = Column(
        String(100),
        nullable=False,
        comment="Time span when trigger is active (e.g., 'Mon-Fri 09:00-17:00', 'Daily 00:00-23:59')"
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
    
    # Action configuration
    action = Column(
        String(50),
        nullable=False,
        default="alert",
        comment="Action to execute when conditions are met (deprecated - use action_uuid)"
    )
    action_config = Column(
        String(500),
        nullable=True,
        comment="Additional action configuration (JSON string for complex configs)"
    )
    
    # Link to user-defined action
    action_uuid = Column(
        UUID(as_uuid=True),
        ForeignKey('user_trigger_actions.uuid', ondelete='SET NULL'),
        nullable=True,
        index=True,
        comment="UUID of the linked user action"
    )
    
    # Relationship to user action
    user_action = relationship("UserTriggerAction", foreign_keys=[action_uuid])
    
    # Tracking configuration
    tracking_duration = Column(
        String(50),
        nullable=False,
        default="10 minutes",
        index=True,
        comment='Time window for MVR search (e.g., "5 seconds", "10 minutes", "2 hours", "1 day")'
    )
    
    # Trigger state
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether the trigger is currently active"
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
    
    # Demographic trigger fields
    enable_demographic_conditions = Column(
        Boolean,
        nullable=False,
        default=False,
        index=True,
        comment="Enable demographic-based trigger evaluation (percent_male, percent_female, etc.)"
    )
    demographic_conditions = Column(
        Text,
        nullable=True,
        comment='JSON array of demographic conditions: [{"field": "percent_male", "operator": "gte", "value": 60}]'
    )
    signage_device_ids = Column(
        Text,
        nullable=True,
        comment='JSON array of signage device UUIDs: ["device-uuid-1", "device-uuid-2"]'
    )
    signage_playlist_id = Column(
        String(255),
        nullable=True,
        comment="Playlist UUID to play when trigger fires"
    )
    signage_transition_mode = Column(
        String(50),
        nullable=False,
        default="immediate",
        comment="Playlist transition mode: immediate | after_current | fade"
    )
    signage_fade_duration_ms = Column(
        Integer,
        nullable=False,
        default=2000,
        comment="Fade duration in milliseconds for fade transition mode"
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
    
    def __repr__(self):
        filters = []
        if self.age_range_operator and self.age_range_operator != AgeRangeOperator.ANY:
            filters.append(f"age:{self.age_range_operator.value}:{self.age_range_value}")
        if self.gender_filter and self.gender_filter != GenderFilter.ANY:
            filters.append(f"gender:{self.gender_filter.value}")
        filter_str = f" [{', '.join(filters)}]" if filters else ""
        return f"<Trigger {self.uuid} - {self.person_count_operator.value} {self.person_count_value} persons{filter_str}, active={self.is_active}>"
