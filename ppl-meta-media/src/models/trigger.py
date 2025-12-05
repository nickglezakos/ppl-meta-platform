"""
Trigger model for event-based notifications and alerts.
"""

import enum
from uuid import uuid4

from sqlalchemy import Boolean, Column, Enum, String
from sqlalchemy.dialects.postgresql import UUID

from .base import BaseModel


class PersonCountOperator(str, enum.Enum):
    """Operators for person count comparison."""

    LESS_THAN = "less_than"
    MORE_THAN = "more_than"
    EQUALS = "equals"
    BETWEEN = "between"


class AgeRange(str, enum.Enum):
    """Age range categories."""

    UNDERAGE = "underage"  # < 18
    ADULTS = "adults"  # 18-64
    SENIORS = "seniors"  # 65+
    ALL = "all"  # Any age


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
        Enum(PersonCountOperator),
        nullable=False,
        default=PersonCountOperator.MORE_THAN,
        comment="Comparison operator for person count"
    )
    person_count_value = Column(
        String(50),
        nullable=False,
        comment="Person count threshold value (e.g., '5', '10-20' for BETWEEN)"
    )
    
    # Age range filter
    age_range = Column(
        Enum(AgeRange),
        nullable=False,
        default=AgeRange.ALL,
        comment="Target age range to monitor"
    )
    
    # Gender filter (optional)
    gender_filter = Column(
        String(50),
        nullable=True,
        comment="Gender filter (e.g., 'Any', '3M/2W', 'Male', 'Female')"
    )
    
    # Time conditions
    time_span = Column(
        String(100),
        nullable=False,
        comment="Time span when trigger is active (e.g., 'Mon-Fri 09:00-17:00', 'Daily 00:00-23:59')"
    )
    
    # Media source (camera/collection reference)
    media_source_uuid = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="UUID of the camera or media collection to monitor"
    )
    media_source_name = Column(
        String(255),
        nullable=True,
        comment="Friendly name of the media source (e.g., 'Camera 01, 03')"
    )
    
    # Action configuration
    action = Column(
        Enum(TriggerAction),
        nullable=False,
        default=TriggerAction.ALERT,
        comment="Action to execute when conditions are met"
    )
    action_config = Column(
        String(500),
        nullable=True,
        comment="Additional action configuration (JSON string for complex configs)"
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
    
    def __repr__(self):
        return f"<Trigger {self.uuid} - {self.person_count_operator.value} {self.person_count_value} persons, active={self.is_active}>"
