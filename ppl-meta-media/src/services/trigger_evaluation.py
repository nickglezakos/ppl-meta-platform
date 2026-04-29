"""
Trigger Evaluation Service

Evaluates triggers against camera demographic data and determines if conditions are met.
Now uses unified demographic_conditions format.
"""

import json
import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.trigger import Trigger

logger = logging.getLogger(__name__)

AGE_COUNT_TO_PERCENT_FIELD = {
    'age_count_0_12': 'percent_age_0_12',
    'age_count_13_17': 'percent_age_13_17',
    'age_count_18_24': 'percent_age_18_24',
    'age_count_25_34': 'percent_age_25_34',
    'age_count_35_44': 'percent_age_35_44',
    'age_count_45_54': 'percent_age_45_54',
    'age_count_55_64': 'percent_age_55_64',
    'age_count_65_plus': 'percent_age_65_plus',
}

LEGACY_PERCENT_AGE_FIELDS = set(AGE_COUNT_TO_PERCENT_FIELD.values())

# Midpoint ages used for computing weighted-average age from bracket percentages
AGE_BRACKET_MIDPOINTS = {
    'percent_age_0_12': 6.0,
    'percent_age_13_17': 15.0,
    'percent_age_18_24': 21.0,
    'percent_age_25_34': 29.5,
    'percent_age_35_44': 39.5,
    'percent_age_45_54': 49.5,
    'percent_age_55_64': 59.5,
    'percent_age_65_plus': 70.0,
}


class DemographicData:
    """Data structure for camera demographic results."""
    
    def __init__(
        self,
        camera_device_id: str,
        people_count: int,
        demographics: Dict[str, any],
        timestamp: Optional[datetime] = None
    ):
        """
        Args:
            camera_device_id: Camera device identifier
            people_count: Total number of people detected
            demographics: Dictionary containing demographic data with keys:
                - percent_male: Percentage of males (0-100)
                - percent_female: Percentage of females (0-100)
                - percent_age_0_12 ... percent_age_65_plus: Legacy age percentages
                - age_count_0_12 ... age_count_65_plus: Canonical age bucket counts
            timestamp: When the data was captured
        """
        self.camera_device_id = camera_device_id
        self.people_count = people_count
        self.demographics = demographics
        self.timestamp = timestamp or datetime.utcnow()
        
    def get_field_value(self, field: str) -> Optional[float]:
        """Get value for a demographic field."""
        if field == 'people_count':
            return float(self.people_count)

        if field == 'age_threshold':
            # Prefer direct average_age (published by instant-detection pipeline)
            if self.demographics.get('average_age') is not None:
                return float(self.demographics['average_age'])
            # Fallback: compute weighted-average age from bracket percentages
            avg_age = sum(
                float(self.demographics.get(k, 0)) * mid / 100.0
                for k, mid in AGE_BRACKET_MIDPOINTS.items()
            )
            return avg_age

        if field in AGE_COUNT_TO_PERCENT_FIELD or field in LEGACY_PERCENT_AGE_FIELDS:
            percent_field = AGE_COUNT_TO_PERCENT_FIELD.get(field, field)
            age_count_value = self.demographics.get(field) if field in AGE_COUNT_TO_PERCENT_FIELD else None
            age_percent_value = self.demographics.get(percent_field)

            if age_count_value is not None:
                return float(age_count_value)
            if age_percent_value is not None:
                return (float(self.people_count) * float(age_percent_value)) / 100.0
            return None

        return self.demographics.get(field)
        
    def __repr__(self):
        return f"<DemographicData camera={self.camera_device_id} count={self.people_count}>"


class TriggerEvaluationService:
    """Service for evaluating triggers against demographic data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_all_active_triggers(
        self,
        demographic_data: DemographicData
    ) -> List[Tuple[Trigger, bool, str]]:
        """
        Evaluate all active triggers for a given camera demographic update.
        
        Args:
            demographic_data: Demographic data from camera
            
        Returns:
            List of tuples: (trigger, passed, reason)
        """
        # Get all active triggers for this camera
        triggers = self.db.query(Trigger).filter(
            Trigger.is_active == True,
            Trigger.camera_device_id == demographic_data.camera_device_id
        ).all()
        
        results = []
        for trigger in triggers:
            passed, reason = self.evaluate_trigger(trigger, demographic_data)
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
        demographic_data: DemographicData
    ) -> Tuple[bool, str]:
        """
        Evaluate a single trigger against demographic data.
        
        Args:
            trigger: Trigger to evaluate
            demographic_data: Demographic data to check against
            
        Returns:
            Tuple of (passed: bool, reason: str)
        """
        # Step 1: Check time span
        if not self._check_time_span(trigger.time_span, demographic_data.timestamp):
            return False, f"Outside time span: {trigger.time_span}"
        
        # Step 2: Parse demographic conditions
        try:
            conditions = json.loads(trigger.demographic_conditions) if isinstance(trigger.demographic_conditions, str) else trigger.demographic_conditions
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse demographic_conditions: {e}")
            return False, "Invalid demographic conditions format"
        
        if not conditions or not isinstance(conditions, list):
            return False, "No demographic conditions defined"
        
        # Step 3: Evaluate all conditions (all must pass)
        failed_conditions = []
        passed_conditions = []
        
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            threshold = condition.get('value')
            
            if not all([field, operator, threshold is not None]):
                failed_conditions.append(f"Invalid condition: {condition}")
                continue
            
            actual_value = demographic_data.get_field_value(field)
            
            if actual_value is None:
                failed_conditions.append(f"{field}: no data")
                continue
            
            condition_met = self._evaluate_condition(actual_value, operator, threshold)
            
            if condition_met:
                passed_conditions.append(f"{field} {operator} {threshold} (actual: {actual_value})")
            else:
                failed_conditions.append(f"{field} {operator} {threshold} (actual: {actual_value})")
        
        # All conditions must pass
        if failed_conditions:
            return False, f"Conditions failed: {'; '.join(failed_conditions)}"
        else:
            return True, f"All conditions met: {'; '.join(passed_conditions)}"
    
    def _evaluate_condition(self, actual: float, operator: str, threshold: float) -> bool:
        """
        Evaluate a single demographic condition.
        
        Args:
            actual: Actual value from demographic data
            operator: Comparison operator (gt, gte, lt, lte, eq)
            threshold: Threshold value
            
        Returns:
            True if condition met, False otherwise
        """
        try:
            if operator == 'gt':
                return actual > threshold
            elif operator == 'gte':
                return actual >= threshold
            elif operator == 'lt':
                return actual < threshold
            elif operator == 'lte':
                return actual <= threshold
            elif operator == 'eq':
                return actual == threshold
            else:
                logger.error(f"Unknown operator: {operator}")
                return False
        except (ValueError, TypeError) as e:
            logger.error(f"Error evaluating condition: {e}")
            return False
    
    def _check_time_span(self, time_span: str, current_time: datetime) -> bool:
        """
        Check if current time falls within trigger's time span.
        
        Args:
            time_span: Time span string (e.g., "Mon-Fri 09:00-17:00", "any")
            current_time: Current timestamp
            
        Returns:
            True if within time span, False otherwise
        """
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
                    
                    # Handle overnight time spans (e.g., 22:00-06:00)
                    if start_time <= end_time:
                        return start_time <= current_time_only <= end_time
                    else:
                        return current_time_only >= start_time or current_time_only <= end_time
        except Exception as e:
            logger.warning(f"Could not parse time span '{time_span}': {e}")
            return True  # Default to always active if can't parse
        
        return True  # Default to always active
    
    def get_active_triggers_for_camera(self, camera_device_id: str) -> List[Trigger]:
        """Get all active triggers monitoring a specific camera."""
        return self.db.query(Trigger).filter(
            Trigger.is_active == True,
            Trigger.camera_device_id == camera_device_id
        ).all()
