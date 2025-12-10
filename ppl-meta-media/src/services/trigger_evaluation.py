"""
Trigger Evaluation Service

Evaluates triggers against camera counter data and determines if conditions are met.
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.trigger import (
    Trigger,
    PersonCountOperator,
    AgeRangeOperator,
    GenderFilter
)

logger = logging.getLogger(__name__)


class CounterData:
    """Data structure for camera counter results."""
    
    def __init__(
        self,
        camera_device_id: str,
        total_count: int,
        age_distribution: Optional[Dict[str, int]] = None,
        gender_distribution: Optional[Dict[str, int]] = None,
        timestamp: Optional[datetime] = None
    ):
        self.camera_device_id = camera_device_id
        self.total_count = total_count
        self.age_distribution = age_distribution or {}
        self.gender_distribution = gender_distribution or {}
        self.timestamp = timestamp or datetime.utcnow()
        
    def __repr__(self):
        return f"<CounterData camera={self.camera_device_id} count={self.total_count}>"


class TriggerEvaluationService:
    """Service for evaluating triggers against counter data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_all_active_triggers(
        self,
        counter_data: CounterData
    ) -> List[Tuple[Trigger, bool, str]]:
        """
        Evaluate all active triggers for a given camera counter update.
        
        Args:
            counter_data: Counter data from camera
            
        Returns:
            List of tuples: (trigger, passed, reason)
        """
        # Get all active triggers for this camera
        triggers = self.db.query(Trigger).filter(
            Trigger.is_active == True,
            Trigger.camera_device_id == counter_data.camera_device_id
        ).all()
        
        results = []
        for trigger in triggers:
            passed, reason = self.evaluate_trigger(trigger, counter_data)
            results.append((trigger, passed, reason))
            
            if passed:
                logger.info(
                    f"✅ Trigger {trigger.uuid} ({trigger.name}) PASSED: {reason}"
                )
            else:
                logger.debug(
                    f"❌ Trigger {trigger.uuid} ({trigger.name}) FAILED: {reason}"
                )
        
        return results
    
    def evaluate_trigger(
        self,
        trigger: Trigger,
        counter_data: CounterData
    ) -> Tuple[bool, str]:
        """
        Evaluate a single trigger against counter data.
        
        Args:
            trigger: Trigger to evaluate
            counter_data: Counter data to check against
            
        Returns:
            Tuple of (passed: bool, reason: str)
        """
        # Step 1: Check time span
        if not self._check_time_span(trigger.time_span, counter_data.timestamp):
            return False, f"Outside time span: {trigger.time_span}"
        
        # Step 2: Apply filters to get filtered count
        filtered_count = self._apply_filters(
            counter_data,
            trigger.age_range_operator,
            trigger.age_range_value,
            trigger.gender_filter
        )
        
        # Step 3: Check person count threshold
        person_count_passed = self._check_person_count(
            filtered_count,
            trigger.person_count_operator,
            trigger.person_count_value
        )
        
        if person_count_passed:
            filter_desc = self._get_filter_description(
                trigger.age_range_operator,
                trigger.age_range_value,
                trigger.gender_filter
            )
            return True, f"Count {filtered_count} {trigger.person_count_operator} {trigger.person_count_value}{filter_desc}"
        else:
            return False, f"Count {filtered_count} does not meet threshold {trigger.person_count_operator} {trigger.person_count_value}"
    
    def _check_time_span(self, time_span: str, current_time: datetime) -> bool:
        """
        Check if current time falls within trigger's time span.
        
        Args:
            time_span: Time span string (e.g., "Mon-Fri 09:00-17:00", "any")
            current_time: Current timestamp
            
        Returns:
            True if within time span, False otherwise
        """
        # TODO: Implement full time span parsing
        # For now, accept "any" or assume always active
        if time_span.lower() == "any":
            return True
        
        # Simple implementation: check if current time is within specified hours
        # Format: "Mon-Fri 09:00-17:00" or "Daily 00:00-23:59"
        try:
            if ":" in time_span:
                # Extract time portion
                parts = time_span.split()
                time_part = parts[-1] if len(parts) > 1 else time_span
                
                if "-" in time_part:
                    start_str, end_str = time_part.split("-")
                    start_time = datetime.strptime(start_str.strip(), "%H:%M").time()
                    end_time = datetime.strptime(end_str.strip(), "%H:%M").time()
                    
                    current_time_only = current_time.time()
                    return start_time <= current_time_only <= end_time
        except Exception as e:
            logger.warning(f"Could not parse time span '{time_span}': {e}")
            return True  # Default to always active if can't parse
        
        return True  # Default to always active
    
    def _apply_filters(
        self,
        counter_data: CounterData,
        age_operator: Optional[AgeRangeOperator],
        age_value: Optional[str],
        gender: Optional[GenderFilter]
    ) -> int:
        """
        Apply age and gender filters to counter data.
        
        Args:
            counter_data: Raw counter data
            age_operator: Age comparison operator
            age_value: Age threshold value
            gender: Gender filter
            
        Returns:
            Filtered person count
        """
        count = counter_data.total_count
        
        # If no filters, return total
        if (not age_operator or age_operator == AgeRangeOperator.ANY) and \
           (not gender or gender == GenderFilter.ANY):
            return count
        
        # TODO: Implement actual filtering based on age_distribution and gender_distribution
        # For now, return total count
        # This requires access to individual detection data with ages and genders
        
        logger.warning(
            "Age/Gender filtering not yet implemented. "
            "Using total count. Filters: age=%s:%s, gender=%s",
            age_operator, age_value, gender
        )
        
        return count
    
    def _check_person_count(
        self,
        actual_count: int,
        operator: PersonCountOperator,
        threshold_value: str
    ) -> bool:
        """
        Check if person count meets threshold condition.
        
        Args:
            actual_count: Actual person count
            operator: Comparison operator
            threshold_value: Threshold value(s)
            
        Returns:
            True if condition met, False otherwise
        """
        try:
            if operator == PersonCountOperator.LESS_THAN:
                threshold = int(threshold_value)
                return actual_count < threshold
            
            elif operator == PersonCountOperator.MORE_THAN:
                threshold = int(threshold_value)
                return actual_count > threshold
            
            elif operator == PersonCountOperator.EQUALS:
                threshold = int(threshold_value)
                return actual_count == threshold
            
            elif operator == PersonCountOperator.BETWEEN:
                # Parse range: "5-15"
                if "-" in threshold_value:
                    min_val, max_val = threshold_value.split("-")
                    return int(min_val) <= actual_count <= int(max_val)
                else:
                    logger.warning(f"Invalid BETWEEN value: {threshold_value}")
                    return False
            
            else:
                logger.error(f"Unknown operator: {operator}")
                return False
                
        except ValueError as e:
            logger.error(f"Error parsing threshold value '{threshold_value}': {e}")
            return False
    
    def _get_filter_description(
        self,
        age_operator: Optional[AgeRangeOperator],
        age_value: Optional[str],
        gender: Optional[GenderFilter]
    ) -> str:
        """Generate human-readable filter description."""
        parts = []
        
        if age_operator and age_operator != AgeRangeOperator.ANY:
            parts.append(f"age {age_operator} {age_value}")
        
        if gender and gender != GenderFilter.ANY:
            parts.append(f"gender={gender}")
        
        if parts:
            return f" (filtered: {', '.join(parts)})"
        return ""
    
    def get_active_triggers_for_camera(self, camera_device_id: str) -> List[Trigger]:
        """Get all active triggers monitoring a specific camera."""
        return self.db.query(Trigger).filter(
            Trigger.is_active == True,
            Trigger.camera_device_id == camera_device_id
        ).all()
