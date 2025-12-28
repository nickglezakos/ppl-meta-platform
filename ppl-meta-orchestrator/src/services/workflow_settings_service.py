"""
PPL Meta Orchestrator - Workflow Settings Service
Manages workflow-level configuration settings stored in database.

This service provides access to configurable workflow parameters like
velocity_sensitivity for face tracking temporal grouping.
"""

import logging
from typing import Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger(__name__)


class WorkflowSettingsService:
    """Service for managing workflow settings."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    async def get_setting(self, key: str) -> Optional[float]:
        """
        Retrieve a workflow setting value by key.
        
        Args:
            key: Setting key (e.g., 'velocity_sensitivity')
            
        Returns:
            Setting value as float, or None if not found
        """
        try:
            result = self.db.execute(
                text("SELECT setting_value FROM workflow_settings WHERE setting_key = :key"),
                {"key": key}
            )
            row = result.fetchone()
            
            if row:
                value = float(row[0])
                logger.info(f"Retrieved setting {key}: {value}")
                return value
            else:
                logger.warning(f"Setting not found: {key}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving setting {key}: {e}")
            return None
    
    async def update_setting(
        self, 
        key: str, 
        value: float, 
        updated_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a workflow setting value with validation.
        
        Args:
            key: Setting key to update
            value: New value
            updated_by: Optional identifier of who made the change
            
        Returns:
            Dict with success status and message
        """
        try:
            # Fetch current setting to validate bounds
            result = self.db.execute(
                text("SELECT min_value, max_value FROM workflow_settings WHERE setting_key = :key"),
                {"key": key}
            )
            row = result.fetchone()
            
            if not row:
                return {
                    "success": False,
                    "message": f"Setting '{key}' not found"
                }
            
            min_value, max_value = row[0], row[1]
            
            # Validate value against min/max
            if min_value is not None and value < min_value:
                return {
                    "success": False,
                    "message": f"Value {value} below minimum {min_value}"
                }
            
            if max_value is not None and value > max_value:
                return {
                    "success": False,
                    "message": f"Value {value} above maximum {max_value}"
                }
            
            # Update setting
            self.db.execute(
                text("""UPDATE workflow_settings 
                    SET setting_value = :value, 
                        updated_at = NOW(), 
                        updated_by = :updated_by 
                    WHERE setting_key = :key"""),
                {"value": value, "updated_by": updated_by or "system", "key": key}
            )
            self.db.commit()
            
            logger.info(f"Updated setting {key} to {value} by {updated_by or 'system'}")
            
            return {
                "success": True,
                "message": f"Setting '{key}' updated to {value}",
                "value": value
            }
            
        except Exception as e:
            logger.error(f"Error updating setting {key}: {e}")
            self.db.rollback()
            return {
                "success": False,
                "message": f"Database error: {str(e)}"
            }
    
    async def get_velocity_sensitivity(self) -> float:
        """
        Get velocity sensitivity setting with fallback to default.
        
        Returns:
            Velocity sensitivity percentage (default: 20.0)
        """
        value = await self.get_setting('velocity_sensitivity')
        return value if value is not None else 20.0
    
    async def get_all_settings(self) -> Dict[str, Any]:
        """
        Retrieve all workflow settings.
        
        Returns:
            Dict mapping setting keys to their details
        """
        try:
            result = self.db.execute(
                text("""SELECT setting_key, setting_value, min_value, max_value, 
                          description, updated_at, updated_by 
                   FROM workflow_settings""")
            )
            
            settings = {}
            for row in result.fetchall():
                settings[row[0]] = {
                    "value": float(row[1]),
                    "min_value": float(row[2]) if row[2] is not None else None,
                    "max_value": float(row[3]) if row[3] is not None else None,
                    "description": row[4],
                    "updated_at": row[5].isoformat() if row[5] else None,
                    "updated_by": row[6]
                }
            
            logger.info(f"Retrieved {len(settings)} workflow settings")
            return settings
            
        except Exception as e:
            logger.error(f"Error retrieving all settings: {e}")
            return {}
