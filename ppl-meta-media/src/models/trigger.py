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
        filters = []
        if self.age_range_operator and self.age_range_operator != AgeRangeOperator.ANY:
            filters.append(f"age:{self.age_range_operator.value}:{self.age_range_value}")
        if self.gender_filter and self.gender_filter != GenderFilter.ANY:
            filters.append(f"gender:{self.gender_filter.value}")
        filter_str = f" [{', '.join(filters)}]" if filters else ""
        return f"<Trigger {self.uuid} - {self.person_count_operator.value} {self.person_count_value} persons{filter_str}, active={self.is_active}>"
